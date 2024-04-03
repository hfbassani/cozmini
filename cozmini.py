import google.generativeai as genai
from google.generativeai.types.generation_types import BlockedPromptException
import cozmo
import cozmo_api
import cozmo_api_stubby
from datetime import datetime
import user_interface as user_ui
import user_voice_input
from event_messages import event_log, EventType
import traceback
import time

def generate_reply(models, prompt, input_image=None, model_log=None):
    if input_image:
        model = models['text_image_model']
        prompt = [prompt, input_image]
    else:
        model = models['text_model']
        prompt = [prompt]

    for retrie in range(4):
        try:
            response = model.generate_content(prompt, stream=False)
            response.resolve()

            if model_log:
                model_log.write('\n======== PROMPT ========\n')
                model_log.write(prompt[max(-len(prompt) + 1, -200)])
                model_log.write('\n======== OUTPUT ========\n')
                model_log.write(response.text+'\n')
                model_log.flush()

            return response.text
        except BlockedPromptException as e:
            print("AI response was blocked due to safety concerns. Please try a different input.")
            return ""
        
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        
        except Exception as e: 
            print(f"Generation error: {e}\nTrying again: {retrie}.")
    

def filter_response(response):
    commands = ''
    for line in response.split('\n'):
        line = line.strip()
        if not line.startswith(('API call:', 'cozmo_')):
          event_log.message(EventType.API_RESULT, f'Got an invalid API call (Ignored): "{line}".\n')
          break
        elif line.startswith('cozmo_'):
            commands += line.strip() + '\n'
        elif line.startswith('API call:'):
            commands += line[len('API call:'):].strip() + '\n'

    return commands

def process_response(response: str, robot_api: cozmo_api.CozmoAPI, user_input):

    user_prompt = ''
    system_messages = ''
    commands = ''
    for cmd in response.split('\n'):
        if cmd.startswith('API call: '):
            commands += f'{cmd[len("API call: "):].strip()}\n'

    if commands:
        result = robot_api.execute_commands(commands)
        user_prompt = ''
        for line in result.split('\n'):
            if line.startswith('User says:'):
                user_prompt += f'{line[len("User says:"):].strip()}\n'
            else:
                system_messages += f'{line}\n'

    return user_prompt, system_messages

def process_events(event_log):
    events = event_log.pop_all_events()

    context = ''
    stop = False
    for message_type, message in events:
        message = message.strip()
        if message_type == EventType.USER_MESSAGE:
            if message.lower() == 'bye':
                stop = True
            context += 'User says: ' + message + '\n'
        elif message_type == EventType.API_CALL:
            context += 'API call: ' + message + '\n'
        elif message_type == EventType.API_RESULT:
            time = datetime.now().strftime("%H:%M:%S")
            context += f'System message ({time}): {message}\n'
        elif message_type == EventType.SYSTEM_MESSAGE:
            time = datetime.now().strftime("%H:%M:%S")
            context += f'System message ({time}): {message}\n'
        else:
            print(message_type, message)

    return context, stop

def cozmo_program(robot: cozmo.robot.Robot):
    voice_input = user_voice_input.VoiceInput()

    now = datetime.now().strftime("%d/%m/%Y")
    event_log.message(EventType.SYSTEM_MESSAGE, "Today's date is: " + now)

    if robot:
        cozmo_robot_api = cozmo_api.CozmoAPI(robot, voice_input)
        user_interface = user_ui.UserInterface(cozmo_robot_api.get_annotated_image)
    else:
        cozmo_robot_api = cozmo_api_stubby.CozmoAPIStubby(None, voice_input)
        user_interface = user_ui.UserInterface(None)

    models = {
        'text_model': genai.GenerativeModel('gemini-pro'),
        # 'text_model': genai.GenerativeModel('gemini-1.5-pro-latest'),
        'text_image_model': genai.GenerativeModel('gemini-pro-vision'),
    }

    model_log = None
    model_log = open('user_data/model_log.txt', 'w')

    prompt_instructions = ''
    with open('cozmo_instructions.txt') as file:
        prompt_instructions = file.read().replace('{API DEFINITION}', cozmo_api.get_api_description())

    with open('user_data/conversation_history.txt', 'a+') as history:
        history.seek()
        conversation_history = history.read()
        if not conversation_history.startswith("Below is the last exchanges you had with the user, for context.\n\n"):
            conversation_history = "Below is the last exchanges you had with the user, for context.\n\n" + conversation_history

        print(prompt_instructions)
        print(conversation_history)

        user_interface.start_ui_loop()
        voice_input.start_voice_input_loop()
        while True:

            context, stop = process_events(event_log)
            if stop:
                break
            
            if not context:
                time.sleep(0.1)
                continue

            user_interface.output_messges(context)
            prompt = prompt_instructions
            prompt += conversation_history
            context += 'API call: '
            prompt += context

            print("Cozmo is thinking...")
            cozmo_robot_api.cozmo_set_backpack_lights("white_light")
            commands = filter_response(generate_reply(models, prompt, model_log=model_log))

            user_interface.output_messges(commands)
            remember = context + commands
            conversation_history += remember
            history.write(remember)
            history.flush()

            cozmo_robot_api.cozmo_set_backpack_lights("off")
            try:
                cozmo_robot_api.execute_commands(commands)
            except Exception as e:
                traceback.print_exc()

        if model_log:
            model_log.close()

try:
    cozmo.run_program(cozmo_program, exit_on_connection_error=False)
except Exception as e:
    traceback.print_exc()
    print('#### Robot not found. Using text mode! ###')
    cozmo_program(None)
