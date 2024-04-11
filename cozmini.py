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
from collections import OrderedDict

_CHAT_MODE = False
_API_PROMPT = 'API calls'

def generate_reply(models, context, prompt, model_log=None):

    if not _CHAT_MODE:
        prompt = context + prompt

    output = ''
    for retrie in range(4):
        try:
            if _CHAT_MODE:
                response = models['chat'].send_message(prompt)
            else:
                response = models['text_model'].generate_content(prompt)
                response.resolve()

            output = response.text

            if model_log:
                model_log.write('\n======== PROMPT ========\n')
                model_log.write("..." + prompt[-1000:])
                model_log.write('\n======== OUTPUT ========\n')
                model_log.write(response.text + '\n')
                model_log.flush()

            return output
        except BlockedPromptException as e:
            print("AI response was blocked due to safety concerns. Please try a different input.")
        
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        
        except Exception as e: 
            print(f"Generation error: {e}\nTrying again: {retrie}.")

    return output
    
def get_image_description(models, input_image, model_log=None):
    image_description = ''
    if input_image:
        for retrie in range(4):
            try:
                for retrie in range(4):
                    image_prompt = "Anki Cozmo robot captured this image. Describe what cozmo sees in the image."
                    response = models['text_image_model'].generate_content([image_prompt, input_image], stream=False)
                    response.resolve()
                    image_description = response.text.strip()

                    if model_log:
                        model_log.write('\n======== IMAGE PROMPT ========\n')
                        model_log.write(image_prompt+'\n')
                        model_log.write('\n======== IMAGE OUTPUT ========\n')
                        model_log.write(image_description)
                        model_log.flush()

            except BlockedPromptException as e:
                print("AI response was blocked due to safety concerns. Please try a different input.")
        
            except KeyboardInterrupt:
                raise KeyboardInterrupt

            except Exception as e: 
                print(f"Generation error: {e}\nTrying again: {retrie}.")

    return image_description

def filter_response(response):
    commands = ''
    for line in response.splitlines():
        line = line.strip()
        if not line.startswith((_API_PROMPT, 'cozmo_')):
          event_log.message(EventType.API_RESULT, f'Got an invalid API call (Ignored): "{line}".\n')
          break
        elif line.startswith('cozmo_'):
            commands += line.strip() + '\n'
        elif line.startswith(_API_PROMPT):
            commands += line[len(f"{_API_PROMPT}: "):].strip() + '\n'

    return commands

def process_response(response: str, robot_api: cozmo_api.CozmoAPI, user_input):
    user_prompt = ''
    system_messages = ''
    commands = ''
    for cmd in response.splitlines():
        if cmd.startswith(_API_PROMPT):
            commands += f'{cmd[len(f"{_API_PROMPT}: "):].strip()}\n'

    if commands:
        result = robot_api.execute_commands(commands)
        user_prompt = ''
        for line in result.splitlines():
            if line.startswith('User says:'):
                user_prompt += f'{line[len("User says:"):].strip()}\n'
            else:
                system_messages += f'{line}\n'

    return user_prompt, system_messages

def process_events(event_log, image_description=''):
    global _system_messages
    events = event_log.pop_all_events()
    time = datetime.now().strftime("%H:%M:%S")
    context = ''
    stop = False

    if image_description:
        context = f'System message ({time}): Result of cozmo_captures_image(): {image_description}\n'

    _system_messages = set()
    for message_type, message in events:
        message = message.strip()
        if message_type == EventType.USER_MESSAGE:
            if message.lower() == 'bye':
                stop = True
            context += 'User says: ' + message + '\n'
        elif message_type == EventType.API_CALL:
            context += f'{_API_PROMPT}: {message}\n'
        elif message_type == EventType.API_RESULT:
                context += f'System message ({time}): {message}\n'
        elif message_type == EventType.SYSTEM_MESSAGE and message not in _system_messages:
            context += f'System message ({time}): {message}\n'
            _system_messages.add(message)

    return context, stop

def cozmo_program(robot: cozmo.robot.Robot):
    voice_input = user_voice_input.VoiceInput()

    now = datetime.now().strftime("%d/%m/%Y")
    event_log.message(EventType.SYSTEM_MESSAGE, "Today's date is: " + now)

    if robot:
        cozmo_robot_api = cozmo_api.CozmoAPI(robot, voice_input)
        user_interface = user_ui.UserInterface(cozmo_robot_api.get_image_from_camera)
    else:
        cozmo_robot_api = cozmo_api_stubby.CozmoAPIStubby(None, voice_input)
        user_interface = user_ui.UserInterface(None)

    models = {
        'text_model': genai.GenerativeModel('gemini-pro'),
        # 'text_model': genai.GenerativeModel('gemini-1.5-pro'),
        'text_image_model': genai.GenerativeModel('gemini-pro-vision'),
    }

    model_log = None
    model_log = open('user_data/model_log.txt', 'w')

    prompt_instructions = ''
    with open('cozmo_instructions.txt') as file:
        prompt_instructions = file.read().replace('{API DEFINITION}', cozmo_api.get_api_description())

    with open('user_data/conversation_history.txt', 'a+') as history:
        history.seek(0)
        conversation_history = history.read()
        # TODO: Use the LLM to summarize conversation history if it's too long

        if _CHAT_MODE:
            models['chat'] = models['text_model'].start_chat(history=[])
            models['chat'].send_message(prompt_instructions)
            # TODO: Add conversation history support to chat model

        user_interface.start_ui_loop()
        voice_input.start_voice_input_loop()
        image = None
        image_description = None
        while True:

            voice_input.wait_listening_finish() # let user finish talikng to include their input
            new_context, stop = process_events(event_log, image_description)
            if stop:
                break

            context = prompt_instructions + conversation_history
            prompt = new_context + f"{_API_PROMPT}: "
            user_interface.output_messges(prompt)

            print("Cozmo is thinking...")
            cozmo_robot_api.set_backpack_lights(cozmo.lights.white_light)
            commands = filter_response(generate_reply(models, context, prompt, model_log=model_log))
            user_interface.output_messges(commands)

            remember = prompt + commands
            conversation_history += remember
            history.write(remember)
            history.flush()

            cozmo_robot_api.restore_backpack_lights()
            try:
                _, image = cozmo_robot_api.execute_commands(commands)
                if image:
                    print("Cozmo is thinking about the image...")
                    cozmo_robot_api.set_backpack_lights(cozmo.lights.white_light)
                    image = image.annotate_image()
                    image_description = get_image_description(models, image, model_log)
                    cozmo_robot_api.restore_backpack_lights()                   
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
