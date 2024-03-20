import google.generativeai as genai
from google.generativeai.types.generation_types import BlockedPromptException
import cozmo
import cozmo_api
from datetime import datetime
from user_input_keyboard import UserInput
# from user_input_voice import UserInput
from system_events import SystemEvents
import traceback

def generate_reply(models, user_text, input_image=None):
    if input_image:
        model = models['text_image_model']
        prompt = [user_text, input_image]
    else:
        model = models['text_model']
        prompt = [user_text]

    try:
        response = model.generate_content(prompt, stream=False)
        response.resolve()

        return response.text
    except BlockedPromptException as e:
        print("AI response was blocked due to safety concerns. Please try a different input.")
        return ""

def event_callback(event_list):
    print(event_list[-1])

def filter_response(response):
    filtered_response = ""
    system_messages = ''
    for line in response.split('\n'):
        if not line.startswith('cozmo_'):
          system_messages += f'Got an invalid API call: "{line}".\n'
          break
        else:
            filtered_response += line + '\n'

    return filtered_response, system_messages

def process_response(response: str, robot_api: cozmo_api.CozmoAPI, user_input):

    if not robot_api:
        print(response)
        if 'cozmo_listens()' in response:
            return '', user_input.capture_user_input()
        if 'cozmo_search_light_cube()' in response:
            return 'Found cube with ID: 1', ''
        return '', ''
    
    response, system_messages = filter_response(response)
    if response:
        result = robot_api.execute_commands(response)
        user_prompt = ''
        print('Result: ', result)
        for line in result.split('\n'):
            print('Line:', line)
            if line.startswith('User says:'):
                user_prompt += f'{line}\n'

    return system_messages, user_prompt

def fake_reply():
    return (
        'cozmo_says("Okey dokey")\n'
        'cozmo_search_light_cube()\n'
        'System message: Found cube with ID: 3\n'
        'cozmo_pop_a_wheelie(3)\n'
        'System message: Cozmo has performed a wheel stand\n'
    )

def cozmo_program(robot: cozmo.robot.Robot):
    event_log = SystemEvents(event_callback)
    user_input = UserInput()

    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    system_message = "Today's date and time: " + now

    if robot:
        cozmo_robot_api = cozmo_api.CozmoAPI(robot, user_input)
    else:
        cozmo_robot_api = None

    models = {
        'text_model': genai.GenerativeModel('gemini-pro'),
        'text_image_model': genai.GenerativeModel('gemini-pro'),
    }

    prompt_instructions = ''
    with open('cozmo_instructions.txt') as file:
        prompt_instructions = file.read().replace('{API DEFINITION}', cozmo_api.get_api_description())

    with open('conversation_history.txt', 'r+') as history:
        conversation_history = history.read()
        print(prompt_instructions)
        print(conversation_history)

        user_prompt = user_input.wait_keyword()
        while user_prompt.lower()!='bye':

            prompt = prompt_instructions
            prompt += conversation_history

            new_prompt = ''
            for line in system_message.split('\n'):
                new_prompt += f'System message: {line}\n'
            system_message = ''

            if user_prompt:
                new_prompt += f'User says: {user_prompt}\n'

            prompt += new_prompt

            response = generate_reply(models, prompt)
            # response = fake_reply()

            remember = new_prompt + response
            conversation_history += remember
            history.write(remember)
            history.flush()

            try:
                system_message, user_prompt = process_response(response, cozmo_robot_api, user_input) 
                print(system_message, user_prompt)
            except Exception as e:
                traceback.print_exc()

            if not user_prompt:
                user_prompt = ''
                if not system_message:
                    user_prompt = user_input.wait_keyword()

try:
    cozmo.run_program(cozmo_program, exit_on_connection_error=False)
except Exception as e:
    traceback.print_exc()
    print('#### Robot not found. Using text mode! ###')
    cozmo_program(None)