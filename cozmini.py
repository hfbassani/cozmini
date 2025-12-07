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
import argparse


_CHAT_MODE = True
_API_PROMPT = 'API calls'
_COZMO_TOOLS = types.Tool(function_declarations=cozmo_api.get_function_declarations())
_GEMINI_MODEL = 'gemini-2.5-flash'
_MEMORY_MODEL = 'gemini-2.5-pro'
_CONVERSATION_HISTORY_FILE = 'user_data/robot_memory/conversation_history.txt'
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
        # if _user_interface:
        #     _user_interface.output_messges("Cozmo is listening...\n")
        print("Cozmo is listening...")
    elif message_type == EventType.VOICE_EVENT_FINISHED:
        if _cozmo_robot_api:
            _cozmo_robot_api.restore_backpack_lights()
        # if _user_interface:
        #     _user_interface.output_messges("Cozmo has stopped listening.\n")
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
            # Check if message already has speaker identification (e.g., "Hans: " or "[unrecognized]: ")
            # Speaker-identified messages have format: "Name: message" or "[unrecognized]: message"
            has_speaker_id = False
            if ': ' in message:
                potential_speaker = message.split(': ', 1)[0]
                # Valid speaker identification is either:
                # 1. Enclosed in brackets like [unrecognized]
                # 2. A short name (not starting with "User")
                if (potential_speaker.startswith('[') and potential_speaker.endswith(']')) or \
                   (len(potential_speaker) < 30 and not potential_speaker.startswith('User')):
                    has_speaker_id = True
            
            if has_speaker_id:
                context += message + '\n'
            else:
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


def consolidate_memory():
    """
    Consolidate conversation history into long-term memory using LLM.
    
    Returns:
        str: The memory content (new or existing)
    """
    memory_file = 'user_data/robot_memory/memory.txt'
    prompt_file = 'memory_prompt.txt'
    consolidation_error_file = 'user_data/robot_memory/consolidation_error.txt'
    
    # Generate timestamped backup filename
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    backup_file = f'user_data/robot_memory/memory_{timestamp}.txt'
    
    # Read previous memory
    previous_memory = ""
    try:
        with open(memory_file, 'r') as f:
            previous_memory = f.read().strip()
    except FileNotFoundError:
        print("No existing memory file found. Starting with empty memory.")
    
    # Read conversation history
    session_log = ""
    try:
        with open(_CONVERSATION_HISTORY_FILE, 'r') as f:
            session_log = f.read().strip()
    except FileNotFoundError:
        print("No conversation history found. Skipping memory consolidation.")
        return previous_memory
    
    # Skip if no conversation history
    if not session_log:
        print("Conversation history is empty. Skipping memory consolidation.")
        return previous_memory
    
    print("Consolidating memory from conversation history...")

    # Read prompt template
    try:
        with open(prompt_file, 'r') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        print(f"Error: {prompt_file} not found. Cannot consolidate memory.")
        with open(consolidation_error_file, 'w') as f:
            f.write(f"Consolidation of session {timestamp} failed: prompt file {prompt_file} not found.")
        return previous_memory
    
    # Format the prompt
    prompt = prompt_template.replace('{PREVIOUS_MEMORY}', previous_memory if previous_memory else '(No previous memory)')
    prompt = prompt.replace('{SESSION_LOG}', session_log)
    
    # Call LLM for summarization
    try:
        client = genai.Client()
        model = client.models.generate_content(
            model=_MEMORY_MODEL,
            contents=prompt
        )
        
        new_memory = ""
        if model.candidates and model.candidates[0].content and model.candidates[0].content.parts:
            for part in model.candidates[0].content.parts:
                if part.text:
                    new_memory += part.text
        
        new_memory = new_memory.strip()

        if new_memory.startswith("Error"):
            print(f"Error: {new_memory}")
            with open(consolidation_error_file, 'w') as f:
                f.write(f"Consolidation of session {timestamp} failed: {new_memory}")
            return previous_memory  
        
        # Validate new memory (must be > 50% of old memory size to avoid corruption)
        min_size = len(previous_memory) * 0.5
        if len(new_memory) < min_size and previous_memory:
            print(f"Warning: New memory size ({len(new_memory)}) is less than 50% of old memory ({len(previous_memory)}). Keeping old memory.")
            with open(consolidation_error_file, 'w') as f:
                f.write(f"Consolidation of session {timestamp} failed: New memory size is less than 50% of old memory. Keeping old memory.")
                f.write(new_memory + "\n\n")
            return previous_memory
        
        if not new_memory:
            print("Warning: Generated memory is empty. Keeping old memory.")
            return previous_memory

        print(f"Memory consolidation successful. New memory size: {len(new_memory)} chars")
        
        # Backup old memory
        if previous_memory:
            try:
                with open(backup_file, 'w') as f:
                    f.write(previous_memory)
            except Exception as e:
                print(f"Warning: Could not backup memory: {e}")

        # Write new memory
        with open(memory_file, 'w') as f:
            f.write(new_memory)
        
        # Clear conversation history
        with open(_CONVERSATION_HISTORY_FILE, 'w') as f:
            f.write('')
        
        return new_memory
        
    except Exception as e:
        print(f"Error during memory consolidation: {e}")
        traceback.print_exc()
        with open(consolidation_error_file, 'w') as f:
            f.write(f"Consolidation of session {timestamp} failed: {e}")
        return previous_memory


def cozmo_program(robot: cozmo.robot.Robot, skip_memory=False):
    global _cozmo_robot_api, _user_interface, _user_input

    event_log.add_callback(handle_event)

    now = datetime.now().strftime("%d/%m/%Y")
    event_log.message(EventType.SYSTEM_MESSAGE, "Today's date is: " + now)

    model_log = None
    model_log = open('user_data/model_log.txt', 'w')

    if robot:
        _cozmo_robot_api = cozmo_api.CozmoAPI(robot)
    else:
        _cozmo_robot_api = cozmo_api_stubby.CozmoAPIStubby()

    # Play wake up animation
    if _cozmo_robot_api:
        try:
            _cozmo_robot_api.cozmo_plays_animation("ConnectWakeUp", block=False)
            print("Cozmo is waking up...")
        except Exception as e:
            print(f"Failed to play wake up animation: {e}")

    # Consolidate memory from previous session
    if skip_memory:
        print("Skipping memory consolidation (--no-memory flag set)")
        memory_content = ""
        try:
            with open('user_data/robot_memory/memory.txt', 'r') as f:
                memory_content = f.read().strip()
        except FileNotFoundError:
            print("No existing memory file found.")
    else:
        memory_content = consolidate_memory()

    system_instructions = ''
    with open('cozmo_instructions.txt') as file:
        system_instructions = file.read()
        system_instructions = system_instructions.replace('{API_DEFINITION}', cozmo_api.get_api_description())
        system_instructions = system_instructions.replace('{MEMORY_FILE_INSERTED_HERE}', memory_content if memory_content else '(No memory yet)')

    with open(_CONVERSATION_HISTORY_FILE, 'a') as history:
        conversation_history = ""

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
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Cozmo Robot Control System')
    parser.add_argument('--no-memory', action='store_true', 
                        help='Skip memory consolidation at startup')
    args = parser.parse_args()
    
    try:
        cozmo.run_program(lambda robot: cozmo_program(robot, skip_memory=args.no_memory), 
                         exit_on_connection_error=False)
    except Exception as e:
        traceback.print_exc()
        print('#### Robot not found. Using text mode! ###')
        cozmo_program(None, skip_memory=args.no_memory)
