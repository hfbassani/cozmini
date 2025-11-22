from google import genai
from google.genai import types
from cozmo_custom import cozmo
import cozmo_api
import cozmo_api_stubby
from datetime import datetime
import user_interface as user_ui
import user_voice_input
from event_messages import event_log, EventType
import traceback
from collections import OrderedDict
import time
from io import BytesIO
from collections import namedtuple


_CHAT_MODE = True
_API_PROMPT = 'API calls'
_COZMO_TOOLS = types.Tool(function_declarations=cozmo_api.get_function_declarations())
_GEMINI_MODEL = 'gemini-2.5-flash'
ToolCall = namedtuple("ToolCalls", ["name", "args"])

# APIs:
_cozmo_robot_api = None
_user_interface = None
_user_input = None


def generate_response(model, prompt, image, context, model_log=None):

    if not _CHAT_MODE:
        prompt = context + prompt

    prompt_parts = [prompt]
    if image:
        prompt_parts.append(image)

    for retrie in range(5):
        output = ''
        tool_calls = []

        try:
            if _CHAT_MODE:
                response = model.send_message(prompt_parts)
            else:
                response = model.generate_content(prompt_parts)

            if not response.candidates[0].content or not response.candidates[0].content.parts:
                continue

            for part in response.candidates[0].content.parts:
                if part.function_call:
                    tool_calls.append(part.function_call)
                if part.text:
                    output += part.text

            if model_log:
                model_log.write("\n======== PROMPT ========\n")
                if not _CHAT_MODE:
                    model_log.write("...\n" + prompt[-1000:])
                else:
                    model_log.write("...\n" + context[-1000:] + prompt)

                model_log.write("\n======== OUTPUT ========\n")
                model_log.write(output + '\n')
                model_log.write("Function calls: " + ', '.join(f"{call.name}({str(call.args)})" for call in tool_calls) + '\n')
                model_log.flush()

            return output, tool_calls
        except Exception as e:
            print(f"Error generating response: {e}\nFull prompt: {prompt}")

        except KeyboardInterrupt:
            raise KeyboardInterrupt
        
        except Exception as e: 
            print(f"Generation error: {e}\nTrying again in 15s: {retrie}/5.")
            time.sleep(15)

    return output, tool_calls

def handle_event(event):
    global _cozmo_robot_api, _user_interface

    message_type, message = event
    if message_type == EventType.VOICE_EVENT_LISTENING:
        if _cozmo_robot_api:
            _cozmo_robot_api.set_backpack_lights(cozmo.lights.green_light)
        if _user_interface:
            _user_interface.output_messges("Cozmo is listening...\n")
        print("Cozmo is listening...")
    elif message_type == EventType.VOICE_EVENT_FINISHED:
        if _cozmo_robot_api:
            _cozmo_robot_api.restore_backpack_lights()
        if _user_interface:
            _user_interface.output_messges("Cozmo has stopped listening.\n")
        print("Cozmo has stopped listening.")
    elif message_type == EventType.USER_MESSAGE:
        # Handle user messages
        pass
    elif message_type == EventType.API_CALL:
        # Handle API calls
        pass
    elif message_type == EventType.SYSTEM_MESSAGE:
        # Handle system messages
        pass

def process_events(event_log):
    global _system_messages
    events = event_log.pop_all_events()
    time = datetime.now().strftime("%H:%M:%S")
    context = ''
    stop = False

    _system_messages = set()
    for message_type, message in events:
        message = message.strip()
        if message_type == EventType.USER_MESSAGE:
            if message.lower() == 'bye':
                stop = True
            context += 'User says: ' + message + '\n'
        elif message_type == EventType.API_CALL:
            context += f'{_API_PROMPT}: {message}\n'
        # elif message_type == EventType.API_RESULT:
        #         context += f'System message ({time}): {message}\n'
        elif message_type == EventType.SYSTEM_MESSAGE and message not in _system_messages:
            context += f'System message ({time}): {message}\n'
            _system_messages.add(message)
        elif message_type == EventType.VOICE_EVENT_FINISHED:
             context += f'System message ({time}): Cozmo stopped listening.\n'

    return context, stop


def format_tool_call(tool_call: dict) -> str:
    tool_call_output = ""
    if tool_call["success"]:
        if tool_call["result"] is None:
            tool_call_output = "succeeded"
        else:
            tool_call_output = str(tool_call["result"])
    else:
        tool_call_output = f"error: {str(tool_call['error'])}"

    if tool_call["args"]:
        args = ", ".join(f"{k}={str(v)}" for k, v in tool_call["args"].items())
    else:
        args = ""

    return f"    {tool_call['function_name']}({args}) -> {tool_call_output}\n"


def cozmo_program(robot: cozmo.robot.Robot):
    global _cozmo_robot_api, _user_interface, _user_input

    event_log.add_callback(handle_event)

    now = datetime.now().strftime("%d/%m/%Y")
    event_log.message(EventType.SYSTEM_MESSAGE, "Today's date is: " + now)

    model_log = None
    model_log = open('user_data/model_log.txt', 'w')

    system_instructions = ''
    with open('cozmo_instructions.txt') as file:
        system_instructions = file.read().replace('{API DEFINITION}', cozmo_api.get_api_description())

    with open('user_data/conversation_history.txt', 'a+') as history:
        history.seek(0)
        # conversation_history = history.read()
        conversation_history = ""
        # TODO: Use the LLM to summarize conversation history if it's too long

        client = genai.Client()
        if _CHAT_MODE:
            chat_model = client.chats.create(
                model=_GEMINI_MODEL,
                history=[],  # TODO: Add conversation history support to chat model
                config=types.GenerateContentConfig(
                    system_instruction=system_instructions,
                    tools=[_COZMO_TOOLS])
            )
        else:
            chat_model = client.models.create(
                model=_GEMINI_MODEL,
                history=[],  # TODO: Add conversation history support to model
                config=types.GenerateContentConfig(
                    system_instruction=system_instructions,
                    tools=[_COZMO_TOOLS]
                )
            )

        
        if robot:
            _cozmo_robot_api = cozmo_api.CozmoAPI(robot)
        else:
            _cozmo_robot_api = cozmo_api_stubby.CozmoAPIStubby()

        _user_interface = user_ui.UserInterface(_cozmo_robot_api.get_image_from_camera)
        _user_input = user_voice_input.VoiceInput()
        if not _user_input:
            _user_input = _user_interface

        _cozmo_robot_api.set_user_input(_user_input)
        _user_interface.start_loop()
        if _user_input and _user_input != _user_interface:
            _user_input.start_loop()

        image = None
        while True:
            if _user_input:
                _user_input.wait_input_finish() # let user finish talikng to include their input
            event_context, stop = process_events(event_log)
            if stop:
                break

            new_prompt = event_context + f"{_API_PROMPT}:\n"
            _user_interface.output_messges(new_prompt)
            history.write(new_prompt)

            print("Cozmo is thinking...")
            _cozmo_robot_api.set_backpack_lights(cozmo.lights.white_light)
            response, tool_calls = generate_response(model=chat_model, prompt=new_prompt, image=image, context=conversation_history, model_log=model_log)
            if response:
                cozmo_says_tool_call = ToolCall(name="cozmo_says", args={"text": response})
                tool_calls.insert(0, cozmo_says_tool_call)

            results = []
            try:
                results, image = _cozmo_robot_api.execute_tool_calls(tool_calls)
                if image and hasattr(image, 'annotate_image'):
                    image = image.annotate_image()
            except Exception as e:
                traceback.print_exc()
            _cozmo_robot_api.restore_backpack_lights()

            result_context = ""
            if results:
                result_message = "".join(format_tool_call(result) for result in results)
                result_context += result_message

            conversation_history += new_prompt + result_context
            _user_interface.output_messges(result_context)
            history.write(result_context)
            history.flush()

        if model_log:
            model_log.close()

if __name__ == "__main__":
    try:
        cozmo.run_program(cozmo_program, exit_on_connection_error=False)
    except Exception as e:
        traceback.print_exc()
        print('#### Robot not found. Using text mode! ###')
        cozmo_program(None)
