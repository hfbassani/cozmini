import cozmo
from event_messages import event_log, EventType
import ast
import traceback
from datetime import datetime

class CozmoEvents:

    def __init__(self, robot) -> None:
        self.monitored_events = {
            cozmo.objects.EvtObjectTapped: lambda kwargs: f"Cube was tapped! object_id: {int(kwargs['obj'].object_id)}, intensity: {kwargs['tap_intensity']}.",
            cozmo.objects.EvtObjectMoving: lambda kwargs: f"Cube was moved! object_id: {int(kwargs['obj'].object_id)}.",
            cozmo.objects.EvtObjectObserved: lambda kwargs: f"Cozmo saw a cube! object_id: {int(kwargs['obj'].object_id)}.",
            cozmo.faces.EvtFaceObserved: lambda kwargs: f"Cozmo saw a person! face_id: {int(kwargs['face'].face_id)}{', name: ' + kwargs['name'] if kwargs['name'] else ''}.",
            cozmo.pets.EvtPetObserved: lambda kwargs: f"Cozmo saw a pet! pet_id: {int(kwargs['pet'].pet_id)}.",
        }

        self.last_events = {}

        for event in self.monitored_events:
            robot.add_event_handler(event, self.event_handler)

    def event_handler(self, cozmo_event, **kwargs):
        event_type = type(cozmo_event)
        event_name = type(cozmo_event).__name__
        if event_name not in self.last_events:
            self.last_events[event_name] = datetime.now()
            event_log.message(EventType.SYSTEM_MESSAGE, self.monitored_events[event_type](kwargs))

        now = datetime.now()
        delta = (now - self.last_events[event_name]).total_seconds()
        if delta > 5:
            event_log.message(EventType.SYSTEM_MESSAGE, self.monitored_events[event_type](kwargs))
            self.last_events[event_name] = now


class CozmoAPIBase:
    """Base class for the API interface to Cozmo."""

    def __init__(self, robot: cozmo.robot.Robot, voice_input):
        self.robot = robot
        self.voice_input = voice_input
        self.cozmo_events = CozmoEvents(robot)
        event_log.add_callback(self._event_calback)
        self.image = None
        self.backpack_light = None

    def _event_calback(self, event):
        event_type, event_message = event
        if event_type == EventType.VOICE_EVENT_LISTENING:
            # Set backpack lights to blue to indicate that Cozmo is listening
            self.robot.set_all_backpack_lights(cozmo.lights.blue_light)
        elif event_type == EventType.VOICE_EVENT_FINISHED:
            # Restor previous color when finished listening
            self.restore_backpack_lights()
   
    def set_backpack_lights(self, light: cozmo.lights.Light):
        """Set the backpack lights without the API internal light state so that it can be restored later."""
        self.robot.set_all_backpack_lights(light)

    def restore_backpack_lights(self):
        if self.backpack_light:
            self.robot.set_all_backpack_lights(self.backpack_light)
        else:
            self.robot.set_backpack_lights_off()

    def execute_commands(self, command_string: str) -> str:
        """
        Receives a text string with a list of commands and executes them in order.

        Args:
            command_string: A string containing CozmoAPI function calls separated by newlines.

        Returns:
            A string summarizing the results of the executed commands and an image, if an image was captured.
        """
        
        self.image = None
        results = []
        for line in command_string.splitlines():
            line = line.strip()  # Remove leading/trailing whitespace
            if line:  # Ignore empty lines
                try:
                    # Split command into function name and arguments, handling commas within strings
                    function_name, args = _parse_api_call(line)

                    # Get the corresponding function from CozmoAPI
                    function = getattr(self, function_name)

                    # Check if the function exists
                    if not hasattr(self, function_name):
                        message = f"Result of {line}: Error: Function '{function_name}' does not exist."
                        event_log.message(EventType.API_RESULT, message)
                        results.append(message)
                        continue

                    # Check if the function is callable
                    if not callable(function):
                        message = f"Result of {line}: Error: '{function_name}' is not callable."
                        event_log.message(EventType.API_RESULT, message)
                        results.append(message)
                        continue

                    # Convert arguments to appropriate types (if needed)
                    converted_args = []
                    for arg in args:
                        try:
                            converted_args.append(float(arg))  # Try converting to float
                        except ValueError:
                            converted_args.append(arg)  # Keep as string

                    # Call the function and store the result
                    result = function(*converted_args)
                    if result:
                        message = f"Result of {line}: {result}"
                        event_log.message(EventType.API_RESULT, message)
                        results.append(message)
                except Exception as e:
                    traceback.print_exc()
                    message = f"Result of {line}: API Call Error: {type(e).__name__} {e}."
                    event_log.message(EventType.API_RESULT, message)
                    results.append(message)

        return "\n".join(results), self.image
    
    def get_image_from_camera(self):
        self.robot.camera.color_image_enabled = True
        self.robot.camera.image_stream_enabled = True
        return self.robot.world.latest_image
    
### End of CozmoAPIBase class

def _parse_api_call(api_call: str):
    parsed = ast.parse(api_call)

    function_name = parsed.body[0].value.func.id

    arguments = []
    for arg in parsed.body[0].value.args:
        if isinstance(arg, ast.Tuple) or isinstance(arg, ast.List):
            # If the argument is a tuple or list, extract its values
            arg_values = []
            for elem in arg.elts:
                if isinstance(elem, ast.UnaryOp):
                    # Handle unary operations within tuples
                    if isinstance(elem.op, ast.USub):  # Check if it's a unary subtraction
                        arg_values.append(-elem.operand.value)  # Negate the value
                    else:
                        raise ValueError("Unsupported unary operation")
                else:
                    arg_values.append(elem.value)
            arguments.append(arg_values)
        elif isinstance(arg, ast.UnaryOp):
            # If the argument is a unary operation, extract its value
            if isinstance(arg.op, ast.USub):  # Check if it's a unary subtraction
                arg_value = -arg.operand.value  # Negate the value
            else:
                raise ValueError("Unsupported unary operation")
            arguments.append(arg_value)
        else:
            # If the argument is not a tuple or unary operation, extract its value directly
            if arg.value is not None:
                arguments.append(arg.value)
            else:
                print(f'invalid arg: {arg}.')

    return function_name, arguments