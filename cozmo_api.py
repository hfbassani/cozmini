import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps
import re

class CozmoAPI:
    """
    A simplified text-based API interface for controlling Cozmo robot.
    """

    def __init__(self, robot: cozmo.robot.Robot, user_input):
        self.robot = robot
        self.user_input = user_input

    def cozmo_listens(self):
        """
        Waits for user to say something for 10 seconds.
        
        Returns:
            A possibly imperfect, tanscription of what the user said.
        """
        user_said = self.user_input.capture_user_input()
        if user_said:
            return 'User says: ' + user_said
        else:
            return "User didn't say anithing."

    def cozmo_says(self, text: str) -> str:
        """
        Makes Cozmo say the provided text.

        Args:
            text: The text for Cozmo to speak.

        Returns:
            A string indicating the result, e.g., "Cozmo said: [text]"
        """
        self.robot.say_text(text).wait_for_completed()
        return f"Cozmo said: {text}"

    def cozmo_drives(self, distance: float, speed: float) -> str:
        """
        Makes Cozmo drive straight for a specified distance at a specific speed.

        Args:
            distance: The distance to drive in millimeters (positive for forward, negative for backward).
            speed: The speed to drive in millimeters per second (positive value).

        Returns:
            A string indicating the result, e.g., "Cozmo drove [distance] mm at [speed] mmps."
        """
        self.robot.drive_straight(distance_mm(distance), speed_mmps(speed)).wait_for_completed()
        return f"Cozmo drove {distance} mm at {speed} mmps."

    # ... (Implementations for other functions follow a similar pattern)

    def cozmo_pop_a_wheelie(self, object_id: int) -> str:
        """
        Makes Cozmo attempt to pop a wheelie using a specific cube.
        Before doing this, Cozmo needs to find a cube with cozmo_search_light_cube() which returns the get the object_id.

        Args:
            object_id: The ID of the LightCube to use for the wheelie.

        Returns:
            A string indicating the result, e.g., "Cozmo has performed a wheel stand" or "Wheelie failed."
        """
        cube = self.robot.world.get_light_cube(object_id)
        if cube:
            action = self.robot.pop_a_wheelie(cube)
            action.wait_for_completed()
            if action.has_succeeded:
                return "Cozmo has performed a wheel stand!"
            else:
                return "Wheelie failed."
        else:
            return f"Cube with ID {object_id} not found."

    def cozmo_turns(self, angle: float) -> str:
        """
        Makes Cozmo turn in place by a specific angle.

        Args:
            angle: The angle to turn in degrees (positive for left, negative for right).

        Returns:
            A string indicating the result, e.g., "Cozmo turned [angle] degrees."
        """
        self.robot.turn_in_place(degrees(angle)).wait_for_completed()
        return f"Cozmo turned {angle} degrees."

    def cozmo_lifts(self, height: float) -> str:
        """
        Makes Cozmo raise or lower his lift to a specific height.

        Args:
            height: The desired lift height as a ratio (0.0 for bottom, 1.0 for top).

        Returns:
            A string indicating the result, e.g., "Cozmo's lift is now at [height] ratio."
        """
        self.robot.set_lift_height(height).wait_for_completed()
        return f"Cozmo's lift is now at {height} ratio."

    def cozmo_head(self, angle: float) -> str:
        """
        Makes Cozmo move his head to a specific angle.

        Args:
            angle: The desired head angle in degrees (within Cozmo's head movement range).

        Returns:
            A string indicating the result, e.g., "Cozmo's head is now at [angle] degrees."
        """
        self.robot.set_head_angle(degrees(angle)).wait_for_completed()
        return f"Cozmo's head is now at {angle} degrees."

    def cozmo_play_animation(self, animation_name: str) -> str:
        """
        Makes Cozmo play a specific animation.

        Args:
            animation_name: The name of the animation to play.

        Returns:
            A string indicating the result, e.g., "Cozmo played animation: [animation_name]"
        """
        try:
            anim = self.robot.anim_names[animation_name]
            anim.play()
            return f"Cozmo played animation: {animation_name}"
        except KeyError:
            return f"Animation '{animation_name}' not found."

    def cozmo_play_song(self, song_notes: list) -> str:
        """
        Makes Cozmo play a song composed of provided notes.

        Args:
            song_notes: A list of SongNote objects representing the song.

        Returns:
            A string indicating the result, e.g., "Cozmo played the song."
        """
        self.robot.play_song(song_notes).wait_for_completed()
        return "Cozmo played the song."

    def cozmo_search_light_cube(self) -> str:
        """
        Makes Cozmo search for a light cube.

        Returns:
            A string indicating the result, e.g., "Found cube with ID: [object_id]" or "No cube found."
        """
        cube = self.robot.world.wait_for_observed_light_cube(timeout=5)
        if cube:
            return f"Found cube with ID: {cube.object_id}"
        else:
            return "No cube found."

    def cozmo_go_to_object(self, object_id: int, distance: float) -> str:
        """
        Makes Cozmo drive to a specific object and stop at a specific distance from it.

        Args:
            object_id: The ID of the object to approach.
            distance: The distance from the object to stop (in millimeters).

        Returns:
            A string indicating the result, e.g., "Cozmo went to object [object_id]."
        """
        obj = self.robot.world.get_light_cube(object_id)
        if obj:
            self.robot.go_to_object(obj, distance_mm(distance)).wait_for_completed()
            return f"Cozmo went to object {object_id}."
        else:
            return f"Object with ID {object_id} not found."

    def cozmo_pickup_object(self, object_id: int) -> str:
        """
        Makes Cozmo pick up a specific object.

        Args:
            object_id: The ID of the LightCube to pick up.

        Returns:
            A string indicating the result, e.g., "Cozmo picked up object [object_id]."
        """
        cube = self.robot.world.get_light_cube(object_id)
        if cube:
            self.robot.pickup_object(cube).wait_for_completed()
            return f"Cozmo picked up object {object_id}."
        else:
            return f"Cube with ID {object_id} not found."

    def cozmo_place_object(self, object_id: int) -> str:
        """
        Makes Cozmo place the object he is carrying on the ground.

        Args:
            object_id: The ID of the object to place (currently only supports LightCubes).

        Returns:
            A string indicating the result, e.g., "Cozmo placed object [object_id]."
        """
        if self.robot.is_carrying_block:
            cube = self.robot.world.get_light_cube(object_id)
            if cube:
                self.robot.place_object_on_ground_here(cube).wait_for_completed()
                return f"Cozmo placed object {object_id}."
            else:
                return f"Cube with ID {object_id} not found."
        else:
            return "Cozmo is not carrying an object."

    def cozmo_dock_with_cube(self, object_id: int) -> str:
        """
        Makes Cozmo dock with a specific cube.

        Args:
            object_id: The ID of the LightCube to dock with.

        Returns:
            A string indicating the result, e.g., "Cozmo docked with cube [object_id]."
        """
        cube = self.robot.world.get_light_cube(object_id)
        if cube:
            self.robot.dock_with_cube(cube).wait_for_completed()
            return f"Cozmo docked with cube {object_id}."
        else:
            return f"Cube with ID {object_id} not found."

    def cozmo_roll_cube(self, object_id: int) -> str:
        """
        Makes Cozmo roll a specific cube.

        Args:
            object_id: The ID of the LightCube to roll.

        Returns:
            A string indicating the result, e.g., "Cozmo rolled cube [object_id]."
        """
        cube = self.robot.world.get_light_cube(object_id)
        if cube:
            self.robot.roll_cube(cube).wait_for_completed()
            return f"Cozmo rolled cube {object_id}."
        else:
            return f"Cube with ID {object_id} not found."

    def cozmo_start_behavior(self, behavior_name: str) -> str:
        """
        Starts a specific behavior for Cozmo to perform autonomously.

        Args:
            behavior_name: The name of the behavior to start.

        Returns:
            A string indicating the result, e.g., "Cozmo started behavior: [behavior_name]"
        """
        try:
            behavior = getattr(cozmo.behavior.BehaviorTypes, behavior_name)
            self.robot.start_behavior(behavior)
            return f"Cozmo started behavior: {behavior_name}"
        except AttributeError:
            return f"Behavior '{behavior_name}' not found."

    def cozmo_stop_behavior(self, behavior_name: str) -> str:
        """
        Stops a specific behavior that Cozmo is currently performing.

        Args:
            behavior_name: The name of the behavior to stop.

        Returns:
            A string indicating the result, e.g., "Cozmo stopped behavior: [behavior_name]"
        """
        behavior = self.robot.current_behavior
        if behavior and behavior.behavior_type.name == behavior_name:
            behavior.stop()
            return f"Cozmo stopped behavior: {behavior_name}"
        else:
            return f"Behavior '{behavior_name}' not running."

    def cozmo_start_freeplay(self) -> str:
        """
        Starts Cozmo's freeplay mode where he explores and interacts autonomously.

        Returns:
            A string indicating the result, e.g., "Cozmo entered freeplay mode."
        """
        self.robot.start_freeplay_behaviors()
        return "Cozmo entered freeplay mode."

    def cozmo_stop_freeplay(self) -> str:
        """
        Stops Cozmo's freeplay mode.

        Returns:
            A string indicating the result, e.g., "Cozmo exited freeplay mode."
        """
        self.robot.stop_freeplay_behaviors()
        return "Cozmo exited freeplay mode."

    def cozmo_battery_level(self) -> str:
        """
        Returns Cozmo's current battery level.

        Returns:
            A string indicating the battery level, e.g., "Cozmo's battery level is [level]."
        """
        level = self.robot.battery_voltage
        return f"Cozmo's battery level is {level}."

    def cozmo_is_charging(self) -> str:
        """
        Checks if Cozmo is currently charging.

        Returns:
            A string indicating the charging status, e.g., "Cozmo is charging." or "Cozmo is not charging."
        """
        if self.robot.is_charging:
            return "Cozmo is charging."
        else:
            return "Cozmo is not charging."

    def cozmo_is_carrying_object(self) -> str:
        """
        Checks if Cozmo is currently carrying an object.

        Returns:
            A string indicating the carrying status, e.g., "Cozmo is carrying an object." or "Cozmo is not carrying an object."
        """
        if self.robot.is_carrying_block:
            return "Cozmo is carrying an object."
        else:
            return "Cozmo is not carrying an object."

    def cozmo_is_localized(self) -> str:
        """
        Checks if Cozmo knows his location in the environment.

        Returns:
            A string indicating the localization status, e.g., "Cozmo is localized." or "Cozmo is not localized."
        """
        if self.robot.is_localized:
            return "Cozmo is localized."
        else:
            return "Cozmo is not localized."

    def cozmo_set_backpack_lights(self, color: str) -> str:
        """
        Sets the color of Cozmo's backpack lights.

        Args:
            color: The desired color (e.g., "red", "green", "blue", "white", "off").

        Returns:
            A string indicating the result, e.g., "Cozmo's backpack lights set to [color]."
        """
        color = color.lower()
        if color == "off":
            self.robot.set_backpack_lights_off()
        else:
            try:
                light = getattr(cozmo.lights.Light, color)
                self.robot.set_all_backpack_lights(light)
            except AttributeError:
                return f"Invalid color: {color}"
        return f"Cozmo's backpack lights set to {color}."

    def cozmo_set_headlight(self, on_off: str) -> str:
        """
        Turns Cozmo's headlight on or off.

        Args:
            on_off: "on" to turn the headlight on, "off" to turn it off.

        Returns:
            A string indicating the result, e.g., "Cozmo's headlight turned on."
        """
        on_off = on_off.lower()
        if on_off == "on":
            self.robot.set_head_light(True)
            return "Cozmo's headlight turned on."
        elif on_off == "off":
            self.robot.set_head_light(False)
            return "Cozmo's headlight turned off."
        else:
            return f"Invalid option: {on_off}"

    def cozmo_set_volume(self, volume: float) -> str:
        """
        Sets Cozmo's speaker volume.

        Args:
            volume: The desired volume (0.0 = mute, 1.0 = max).

        Returns:
            A string indicating the result, e.g., "Cozmo's volume set to [volume]."
        """
        self.robot.set_robot_volume(volume)
        return f"Cozmo's volume set to {volume}."

    def execute_commands(self, command_string: str) -> str:
        """
        Receives a text string with a list of commands and executes them in order.

        Args:
            command_string: A string containing CozmoAPI function calls separated by newlines.

        Returns:
            A string summarizing the results of the executed commands.
        """
        results = []
        for line in command_string.splitlines():
            line = line.strip()  # Remove leading/trailing whitespace
            if line:  # Ignore empty lines
                try:
                    # Split command into function name and arguments, handling commas within strings
                    match = re.match(r'(\w[\w\d_]*)\((.*)\)$', line)
                    if match:
                        parts = list(match.groups())
                    else:
                        parts = [line]
                        print(line)
                    function_name = parts[0].strip()
                    args = [arg for arg in parts[1:] if arg]

                    # Get the corresponding function from CozmoAPI
                    function = getattr(self, function_name)

                    # Check if the function exists
                    if not hasattr(self, function_name):
                        results.append(f"Error: Function '{function_name}' does not exist.")
                        continue

                    # Check if the function is callable
                    if not callable(function):
                        results.append(f"Error: '{function_name}' is not callable.")
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
                    results.append(result)
                except Exception as e:
                    results.append(f"Error: {e}")

        return "\n".join(results)  # Combine results into a single string

def get_api_description() -> str:
    """
    Returns a description of all available functions, including parameters and return values.
    """
    description = "CozmoAPI Functions:\n\n"

    for name, method in CozmoAPI.__dict__.items():
        if callable(method) and name.startswith('cozmo_'):
            docstring = method.__doc__
            args_names = ', '.join([arg for arg in method.__code__.co_varnames[:method.__code__.co_argcount] if arg!='self'])
            if docstring:
                description += f"{name}({args_names}):\n{docstring}\n\n"

    return description


if __name__ == "__main__":
    # print(get_api_description())
    robot_api = CozmoAPI(None, None)
    command = """
    cozmo_search_light_cube()
    cozmo_says("Nice to meet you, Alan!")
    """
    results = robot_api.execute_commands(command)
    print(results)