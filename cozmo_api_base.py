from cozmo_custom import cozmo
from event_messages import event_log, EventType
import ast
import traceback
from datetime import datetime
import inspect
import user_profiles


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
            message = self.monitored_events[event_type](kwargs)
            
            # Enhance face detection events with user identification
            if event_type == cozmo.faces.EvtFaceObserved:
                face_id = int(kwargs['face'].face_id)
                profile_manager = user_profiles.get_profile_manager()
                matched_profile = profile_manager.match_by_face(face_id)
                if matched_profile:
                    message = f"Cozmo saw {matched_profile.name}! face_id: {face_id}."
                else:
                    message = f"Cozmo saw an unknown person! face_id: {face_id}."
            
            event_log.message(EventType.SYSTEM_MESSAGE, message)

        now = datetime.now()
        delta = (now - self.last_events[event_name]).total_seconds()
        if delta > 5:
            message = self.monitored_events[event_type](kwargs)
            
            # Enhance face detection events with user identification
            if event_type == cozmo.faces.EvtFaceObserved:
                face_id = int(kwargs['face'].face_id)
                profile_manager = user_profiles.get_profile_manager()
                matched_profile = profile_manager.match_by_face(face_id)
                if matched_profile:
                    message = f"Cozmo saw {matched_profile.name}! face_id: {face_id}."
                else:
                    message = f"Cozmo saw an unknown person! face_id: {face_id}."
            
            event_log.message(EventType.SYSTEM_MESSAGE, message)
            self.last_events[event_name] = now


class CozmoAPIBase:
    """Base class for the API interface to Cozmo."""

    def __init__(self, robot: cozmo.robot.Robot, user_input=None):
        self.robot = robot
        self.user_input = user_input
        self.cozmo_events = CozmoEvents(robot)
        self.image = None
        self.backpack_light = None
        self.profile_manager = user_profiles.get_profile_manager()

    def set_user_input(self, user_input):
        self.user_input = user_input
   
    def set_backpack_lights(self, light: cozmo.lights.Light):
        """Set the backpack lights without the API internal light state so that it can be restored later."""
        self.robot.set_all_backpack_lights(light)

    def restore_backpack_lights(self):
        if self.backpack_light:
            self.robot.set_all_backpack_lights(self.backpack_light)
        else:
            self.robot.set_backpack_lights_off()

    def execute_tool_calls(self, tool_calls):
        """
        Executes the tool calls requested by the model.

        This function iterates through the function calls, looking for
        FunctionCall objects. For each function call, it dynamically retrieves
        the corresponding method from the provided class instance and
        executes it with the arguments provided by the model.

        Args:
            instance: An instance of the class that contains the methods
                    to be called (e.g., an instance of WeatherService).
            tool_calls: tools to be called.

        Returns:
            A list of results from the executed function calls.
            Returns an empty list if no tool calls are found.
        """
        self.image = None
        results = []

        # Check if the model response contains tool calls
        if not tool_calls:
            print("No tool calls found in the model response.")
            return results, None

        # Iterate through each tool call in the response
        for tool_call in tool_calls:
            # Get the name of the function to be called
            function_name = tool_call.name
            
            # Get the arguments for the function call
            function_args = tool_call.args

            try:
                valid_args = {}
                # Dynamically get the method from the class instance
                if hasattr(self, function_name) and callable(getattr(self, function_name)):
                    method_to_call = getattr(self, function_name)
                    
                    # Use inspect to get the method's signature for argument validation
                    sig = inspect.signature(method_to_call)
                    
                    # Validate and prepare arguments
                    for param_name, param in sig.parameters.items():
                        if param_name in function_args:
                            try:
                                arg = float(function_args[param_name])  # Try converting to float
                            except ValueError:
                                arg = f"\"{function_args[param_name]}\""  # Keep it as string

                            valid_args[param_name] = arg
                        elif param.default is inspect.Parameter.empty:
                            # If a required parameter is missing, raise an error
                            raise ValueError(f"Required parameter '{param_name}' missing for function '{function_name}'.")

                    # Execute the method with the prepared arguments
                    result = method_to_call(**valid_args)

                    tool_call = {
                        "function_name": function_name,
                        "args": valid_args,
                        "success": True,
                        "result": result
                    }
                    event_log.message(EventType.API_RESULT, format_tool_call(tool_call))
                    results.append(tool_call)
                else:
                    raise AttributeError(f"Class instance does not have a callable method named '{function_name}'.")

            except Exception as e:
                tool_call = {
                    "function_name": function_name,
                    "args": function_args,
                    "success": False,
                    "error": str(e)
                }
                event_log.message(EventType.API_RESULT, format_tool_call(tool_call))
                traceback.print_exc()
                results.append(tool_call)

        return results, self.image

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