from cozmo_custom import cozmo
from cozmo_custom.cozmo.util import degrees, distance_mm, speed_mmps
from cozmo_custom.cozmo.song import NoteTypes, SongNote, NoteDurations
import asyncio
import time
import traceback
import inspect
import re

from cozmo_api_base import CozmoAPIBase
from event_messages import event_log
import user_voice_input


_DEFAULT_TIMEOUT = 10 # seconds


def get_api_description() -> str:
    """
    Returns a description of all available cozmo_* API functions in this class, including parameters and return values.
    """
    description = "CozmoAPI Functions:\n\n"

    for name, method in CozmoAPI.__dict__.items():
        if callable(method) and name.startswith('cozmo_'):
            docstring = method.__doc__
            args_names = ', '.join([arg for arg in method.__code__.co_varnames[:method.__code__.co_argcount] if arg!='self'])
            if docstring:
                description += f"{name}({args_names}):\n{docstring}\n\n"

    return description

def is_snake_case(s: str) -> bool:
    """
    Checks if a string is in snake_case format.
    
    A string is considered snake_case if it is all lowercase
    and words are separated by underscores.
    """
    if not isinstance(s, str):
        return False
    # Check for empty string or strings with leading/trailing underscores
    if not s or s.startswith('_') or s.endswith('_'):
        return False
    # Check if the string contains any uppercase letters
    if any(c.isupper() for c in s):
        return False
    # Check if words are separated by underscores
    return re.match(r'^[a-z_]+$', s) is not None and '__' not in s

def get_function_declarations():
    """
    Returns a list of FunctionDeclaration objects for all public methods of a class.
    
    Raises a ValueError if any method name is not in snake_case.
    The description is taken from the method's docstring.
    Parameters and their types are inferred from the method's signature.
    
    Args:
        cls: The class to inspect.
        
    Returns:
        A list of dictionaries representing the FunctionDeclaration objects.
    """
    function_declarations = []
    
    for name, method in inspect.getmembers(CozmoAPI, inspect.isfunction):
        if name.startswith('cozmo_'):
            if not is_snake_case(name):
                raise ValueError(f"Method name '{name}' is not in snake_case format.")

            description = inspect.getdoc(method) or ""
            signature = inspect.signature(method)
            
            properties = {}
            for param_name, param in signature.parameters.items():
                if param_name != 'self':
                    # Validate parameter name is also snake_case
                    if not is_snake_case(param_name):
                        raise ValueError(f"Parameter name '{param_name}' for method '{name}' is not in snake_case format.")
                        
                    param_type = "string"
                    if param.annotation is not inspect.Parameter.empty:
                        if param.annotation == int:
                            param_type = "integer"
                        elif param.annotation == bool:
                            param_type = "boolean"
                        # Additional types can be added here
                    
                    properties[param_name] = {
                        "type": param_type,
                        "description": ""
                    }
                    
            function_declarations.append({
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                }
            })
            
    return function_declarations

class CozmoAPI(CozmoAPIBase):
    """
    A simplified text-based API interface for controlling Cozmo robot.
    """

    def cozmo_listens(self):
        """
        Listens to the user for 10 seconds.
        
        Returns:
            A possibly imperfect, transcription of what the user said will be provided as system message.
        """
        if self.user_input:
            self.user_input.capture_user_input(block=False)
            return 'cozmo started listening'
        return 'error'

    def cozmo_says(self, text: str) -> str:
        """
        Makes Cozmo say the provided text.

        Args:
            text: The text for Cozmo to speak.

        Returns:
            A string indicating the result, e.g., "Cozmo said: [text]"
        """
        if self.user_input:
            self.user_input.wait_input_finish() # don't interrupt speech
        action = self.robot.say_text(text)
        action.wait_for_completed(timeout=2*_DEFAULT_TIMEOUT)
        if action.has_succeeded:
            return f""
        else:
            return f"Failed: {action.failure_reason}"

    def cozmo_drives(self, distance: float, speed: float) -> str:
        """
        Makes Cozmo drive straight for a specified distance at a specific speed.

        Args:
            distance: The distance to drive in millimeters (positive for forward, negative for backward).
            speed: The speed to drive in millimeters per second (positive value).

        Returns:
            A string indicating the result, e.g., "Cozmo drove [distance] mm at [speed] mmps."
        """
        action = self.robot.drive_straight(distance_mm(distance), speed_mmps(speed))
        action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
        if action.has_succeeded:
            return f"Cozmo drove {distance} mm at {speed} mmps."
        else:
            return f"Failed: {action.failure_reason}"

    def cozmo_pops_a_wheelie(self, object_id: int) -> str:
        """
        Makes Cozmo attempt to pop a wheelie using a specific cube. Cozmo needs to find a cube first, using cozmo_search_light_cube() which returns the object_id.

        Args:
            object_id: The ID of the LightCube to use for the wheelie.

        Returns:
            A string indicating the result, e.g., "Cube with ID {object_id} not seen." if the cube was not found, "Cozmo has performed a wheel stand" or "Failed."
        """
        object_id = int(object_id)
        cube = self.robot.world.wait_for_observed_light_cube(timeout=_DEFAULT_TIMEOUT)
        if cube and cube.object_id == object_id:
            action = self.robot.pop_a_wheelie(cube)
            action.wait_for_completed(timeout=3*_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return "Cozmo has performed a wheel stand!"
            else:
                return f"Failed: {action.failure_reason}"
        else:
            return f"Cube with ID {object_id} not seen."

    def cozmo_turns(self, angle: float) -> str:
        """
        Makes Cozmo turn in place by a specific angle.

        Args:
            angle: The angle to turn in degrees (positive for left, negative for right).

        Returns:
            A string indicating the result, e.g., "Cozmo turned [angle] degrees."
        """
        action = self.robot.turn_in_place(degrees(angle))
        action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
        if action.has_succeeded:
            return f"Cozmo turned {angle} degrees."
        else:
            return f"Failed: {action.failure_reason}"

    def cozmo_lifts(self, height: float) -> str:
        """
        Makes Cozmo raise or lower his lift to a specific height.

        Args:
            height: The desired lift height as a ratio (0.0 for bottom, 1.0 for top).

        Returns:
            A string indicating the result, e.g., "Cozmo's lift is now at [height] ratio."
        """
        action = self.robot.set_lift_height(height)
        action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
        if action.has_succeeded:
            return f"Cozmo's lift is now at {height} ratio."
        else:
            return f"Failed: {action.failure_reason}"

    def cozmo_head(self, angle: float) -> str:
        """
        Makes Cozmo move his head to a specific angle.

        Args:
            angle: The desired head angle in degrees (within Cozmo's head movement range).

        Returns:
            A string indicating the result, e.g., "Cozmo's head is now at [angle] degrees."
        """
        action = self.robot.set_head_angle(degrees(angle))
        action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
        if action.has_succeeded:
            return f"Cozmo's head is now at {angle} degrees."
        else:
            return f"Failed: {action.failure_reason}"

    def cozmo_plays_animation(self, animation_name: str, block: bool = True) -> str:
        """
        Makes Cozmo play a specific animation or animation trigger.

        Args:
            animation_name: The name of the animation or trigger name to play. Supported animation names:
                Happy/Excited: anim_greeting_happy_03, anim_pyramid_reacttocube_happy_high_02, anim_energy_successgetout_02, anim_explorer_driving01_turbo_01, anim_memorymatch_solo_successgame_player_01, anim_fistbump_success_02, anim_majorwin, anim_keepaway_wingame_03, anim_meetcozmo_celebration, anim_pounce_success_04, anim_speedtap_wingame_intensity03_01
                
                Sad/Frustrated: anim_pyramid_reacttocube_frustrated_low_01, anim_memorymatch_solo_failhand_player_01, anim_reacttocliff_turtlerollfail_03, anim_driving_upset_loop_01, anim_speedtap_losehand_02, anim_memorymatch_failgame_cozmo_03, anim_reacttoblock_frustrated_int2_01, anim_rollblock_fail_01, anim_reacttocliff_stuckrightside_01, anim_majorfail, anim_speedtap_losegame_intensity02_02
                
                Angry/Scared: anim_guarddog_getout_timeout_01, anim_cozmosays_badword_01, anim_repair_severe_idle_03, anim_reacttoblock_triestoreach_01, anim_repair_react_fall_01, anim_sparking_fail_01, anim_reacttoface_unidentified_01, anim_pounce_fail_04, anim_repair_severe_driving_loop_01
                
                Calm/Neutral: anim_explorer_idle_03, anim_lookinplaceforfaces_keepalive_long, anim_sparking_idle_03, anim_hiking_driving_loop_01, anim_launch_idle_03, anim_play_idle_03, anim_memorymatch_idle_02, anim_explorer_drvback_start_02, anim_pause_idle_03, anim_rtpkeepaway_idle_01, anim_energy_idlel2_01, anim_speedtap_player_idle_01, anim_gamesetup_idle_02, anim_neutral_eyes_01
                
                Playful/Curious: anim_pounce_drive_01, anim_fistbump_idle_03, anim_keepaway_getready_02, anim_petdetection_cat_01, anim_explorer_getout_01, anim_peekaboo_idle_01, anim_speedtap_ask2play_01, anim_rtpkeepaway_askforgame_01, anim_pounce_lookloop_02, anim_energy_eat_04, anim_play_driving_start_01, anim_petdetection_dog_02, anim_pounce_long_01, anim_speedtap_look4block_01, anim_hiking_lookaround_01, anim_pounce_04, anim_explorer_huh_01, anim_pounce_reacttoobj_01_shorter
                
                Sleepy/Tired: anim_launch_startsleeping_01, anim_guarddog_sleeploop_01, anim_gotosleep_sleeping_01, anim_gotosleep_off_01, anim_gotosleep_sleeploop_01
                
                Confused/Surprised: anim_reacttocliff_huh_01, anim_dizzy_reaction_medium_03, anim_hiccup_withreaction_01, anim_reacttppl_surprise, anim_explorer_huh_01_head_angle_-10, anim_dizzy_reaction_soft_02, anim_hiccup_faceplant_01, anim_keepalive_eyes_01_updown

        Returns:
            A string indicating the result, e.g., "Cozmo played animation: [animation_name]"
        """
        try:
            # Check if it's a trigger first
            if hasattr(cozmo.anim.Triggers, animation_name):
                trigger = getattr(cozmo.anim.Triggers, animation_name)
                action = self.robot.play_anim_trigger(trigger)
                action_type = "animation trigger"
            else:
                action = self.robot.play_anim(name=animation_name)
                action_type = "animation"

            if block:
                action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
                if action.has_succeeded:
                    return f"Cozmo played animation: {animation_name}"
                else:
                    return f"Failed: {action.failure_reason}"
        except:
            return f"Animation {animation_name} not found."

    def cozmo_plays_song(self, song_notes: str) -> str:
        """
        Makes Cozmo play a song composed of provided notes.
        All notes will be played with a fixed duration

        Args:
            song_notes:
                String containing song notes. Ex.: "C2, D2, E2, F2, G2, A2".
                Available notes are: C2, C2_Sharp, D2, D2_Sharp, E2, F2, F2_Sharp, G2, G2_Sharp, A2, A2_Sharp, B2, C3, C3_Sharp, Rest.

        Returns:
            A string indicating the result, e.g., "Cozmo played the song."
        """
        song_notes = song_notes.replace('"', '').replace("'", '')
        if ',' not in song_notes:
            song_notes = song_notes.replace(' ', ',')

        try:
            notes = []
            for note in song_notes.split(','):
                try:
                    note = note.strip()
                    song_note = SongNote(getattr(NoteTypes, note), NoteDurations.Quarter)
                    notes.append(song_note)
                except:
                    return f"Failed: Note '{note}' is not supported! Use only: C2, C2_Sharp, D2, D2_Sharp, E2, F2, F2_Sharp, G2, G2_Sharp, A2, A2_Sharp, B2, C3, C3_Sharp, Rest."

            action = self.robot.play_song(notes)
            action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return "Cozmo played the song."
            else:
                return f"Failed: {action.failure_reason}"         
        except Exception as e:
            traceback.print_exc()
            return "Cozmo failed to play the song."

    def cozmo_searches_light_cube(self) -> str:
        """
        Makes Cozmo search for a light cube and returns an object_id that can be used for other actions such as pop a wheely, pick up, roll, etc.

        Returns:
            A string indicating the result, e.g., "Found cube with ID: [object_id]" or "No cube found."
        """
        look_around = self.robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
        cube = None
        try:
            cube = self.robot.world.wait_for_observed_light_cube(timeout=4*_DEFAULT_TIMEOUT)

        except asyncio.TimeoutError:
            self.robot.play_anim_trigger(cozmo.robot.anim.Triggers.MajorFail)

        finally:
            # whether we find it or not, we want to stop the behavior
            look_around.stop()

        if cube:
            return f"Found cube with ID: {cube.object_id}"
        else:
            return "No cube found."

    def cozmo_goes_to_object(self, object_id: int, distance: float) -> str:
        """
        Makes Cozmo drive to a specific object and stop at a specific distance from is center. Cozmo needs to find a cube first, using cozmo_search_light_cube() which returns the object_id. 

        Args:
            object_id: The ID of the object to approach.
            distance: The distance from the object to stop (in millimeters).

        Returns:
            A string indicating the result, e.g., "Cozmo went to object [object_id]."
        """
        object_id = int(object_id)
        distance = distance + 64  # This is as close as Cozmo can get from cubes.
        cube = self.robot.world.wait_for_observed_light_cube(timeout=_DEFAULT_TIMEOUT)
        if cube and cube.object_id == object_id:
            action = self.robot.go_to_object(cube, distance_mm(distance), num_retries=2)
            action.wait_for_completed(timeout=2*_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo went to object {object_id}."
            else:
                return f"Failed: {action.failure_reason}"
        else:
            return f"Object with ID {object_id} not found."

    def cozmo_picksup_object(self, object_id: int) -> str:
        """
        Makes Cozmo pick up a specific object. Cozmo needs to find a cube first, using cozmo_search_light_cube() which returns the object_id.

        Args:
            object_id: The ID of the LightCube to pick up.

        Returns:
            A string indicating the result, e.g., "Cozmo picked up object [object_id]." or a Failure message.
        """

        if self.robot.is_carrying_block:
            return "Failed. Cozmo is already carrying an object."

        object_id = int(object_id)
        cube = self.robot.world.wait_for_observed_light_cube(timeout=_DEFAULT_TIMEOUT)
        if cube and cube.object_id == object_id:
            action = self.robot.pickup_object(cube, num_retries=3)
            action.wait_for_completed(timeout=3*_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo picked up object {object_id}."
            else:
                return f"Failed: {action.failure_reason}"

        return f"Cube with ID {object_id} not found."

    def cozmo_places_object(self, object_id: int) -> str:
        """
        Makes Cozmo place the object he is carrying on top of the cube indicated by object_id. Cozmo needs to find a cube first, using cozmo_search_light_cube() which returns the object_id and it needs to be carrying an object in order to place it on top of the object_id passed as argument.

        Args:
            object_id: The ID of the object to place (currently only supports LightCubes).

        Returns:
            A string indicating the result, e.g., "Cozmo placed object [object_id]."
        """
        if self.robot.is_carrying_block:
            object_id = int(object_id)
            cube = self.robot.world.wait_for_observed_light_cube(timeout=_DEFAULT_TIMEOUT)
            if cube and cube.object_id == object_id:
                action = self.robot.place_on_object(cube)
                action.wait_for_completed(timeout=3*_DEFAULT_TIMEOUT)
                if action.has_succeeded:
                    return f"Cozmo placed object {object_id}."
                else:
                    return f"Failed: {action.failure_reason}"
            else:
                return f"Cube with ID {object_id} not seen."
        else:
            return "Failed. Cozmo is not carrying an object."

    def cozmo_docks_with_cube(self, object_id: int) -> str:
        """
        Makes Cozmo dock with a specific cube. Cozmo needs to find a cube first, using cozmo_search_light_cube() which returns the object_id of the cube to dock with.

        Args:
            object_id: The ID of the LightCube to dock with.

        Returns:
            A string indicating the result, e.g., "Cozmo docked with cube [object_id]."
        """
        object_id = int(object_id)
        cube = self.robot.world.wait_for_observed_light_cube(timeout=2*_DEFAULT_TIMEOUT)
        if cube and cube.object_id == object_id:
            action = self.robot.dock_with_cube(cube)
            action.wait_for_completed(timeout=2*_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo docked with cube {object_id}."
            else:
                return f"Failed: {action.failure_reason}"
        else:
            return f"Cube with ID {object_id} not seen."

    def cozmo_rolls_cube(self, object_id: int) -> str:
        """
        Makes Cozmo roll a specific cube. Cozmo needs to find a cube first, using cozmo_search_light_cube() which returns the object_id of the cube to roll.

        Args:
            object_id: The ID of the LightCube to roll.

        Returns:
            A string indicating the result, e.g., "Cozmo rolled cube [object_id]."
        """
        object_id = int(object_id)
        cube = self.robot.world.wait_for_observed_light_cube(timeout=_DEFAULT_TIMEOUT)
        if cube and cube.object_id == object_id:
            action = self.robot.roll_cube(cube)
            action.wait_for_completed(timeout=3*_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo rolled cube {object_id}."
            else:
                return f"Failed: {action.failure_reason}"
        else:
            return f"Cube with ID {object_id} not seen."

    def cozmo_starts_behavior(self, behavior_name: str) -> str:
        """
        Starts a specific behavior for Cozmo to perform autonomously. 
        You should stop the behavior with cozmo_stop_behavior() before using any other API calls.
        Any other API call made while a behavior is running will fail with a TimeoutError or other exception.
  
        Args:
            behavior_name: The name of the behavior to start among: FindFaces, KnockOverCubes, LookAroundInPlace, PounceOnMotion, RollBlock, StackBlocks, EnrollFace

        Returns:
            A string indicating the result, e.g., "Cozmo started behavior: [behavior_name]"
        """
        try:
            behavior = getattr(cozmo.behavior.BehaviorTypes, behavior_name)
            self.robot.start_behavior(behavior)
            return f"Cozmo started behavior: {behavior_name}"
        except AttributeError:
            return f"Behavior '{behavior_name}' not found."

    def cozmo_stops_behavior(self, behavior_name: str) -> str:
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

    def cozmo_starts_freeplay(self) -> str:
        """
        Starts Cozmo's freeplay mode where he explores and interacts autonomously.
        You shouldn't attempt to drive Cozmo during this, as it will clash
        with whatever the current behavior is attempting to do and the calls will fail.
        Use cozmo_stop_freeplay() before using other functions.

        Returns:
            A string indicating the result, e.g., "Cozmo entered freeplay mode."
        """
        self.robot.start_freeplay_behaviors()
        if self.robot.is_freeplay_mode_active:
            return "Cozmo entered freeplay mode."
        else:
            return f"Failed."

    def cozmo_stops_freeplay(self) -> str:
        """
        Stops Cozmo's freeplay mode.

        Returns:
            A string indicating the result, e.g., "Cozmo exited freeplay mode."
        """
        self.robot.stop_freeplay_behaviors()
        if not self.robot.is_freeplay_mode_active:
            return "Cozmo exited freeplay mode."
        else:
            return f"failed to stop freeplay mode."

    def cozmo_battery_level(self) -> str:
        """
        Returns Cozmo's current battery level.

        Returns:
            A string indicating the battery level, e.g., "Cozmo's battery level is [level]."
        """
        level = self.robot.battery_voltage
        return f"Cozmo's battery level is {level:.2f} out of 3.7 volts."

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

    def cozmo_sets_backpack_lights(self, r: int, g: int, b: int) -> str:
        """
        Sets the color of Cozmo's backpack lights. Set all channels to 0 to turn them off.

        Args:
            R: Red channel from 0-255.
            G: Green channel from 0-255.
            B: Blue channel from 0-255.

        Returns:
            A string indicating the result, e.g., "Cozmo's backpack lights set to (R, G, B)."
        """
        if r == 0 and g == 0 and b == 0:
            self.robot.set_backpack_lights_off()
            self.backpack_light = None
        else:
            try:
                self.backpack_light = cozmo.lights.Light(cozmo.lights.Color(rgb=(int(r), int(g), int(b))))
                self.robot.set_all_backpack_lights(self.backpack_light)
            except AttributeError:
                return f"Failed."
        return f"Cozmo's backpack lights set to ({r}, {g}, {b})."

    def cozmo_sets_headlight(self, on_off: str) -> str:
        """
        Turns Cozmo's headlight on or off.

        Args:
            on_off: string "on" to turn the headlight on, "off" to turn it off.

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

    def cozmo_sets_volume(self, volume: float) -> str:
        """
        Sets Cozmo's speaker volume.

        Args:
            volume: The desired volume (0.0 = mute, 1.0 = max).

        Returns:
            A string indicating the result, e.g., "Cozmo's volume set to [volume]."
        """
        self.robot.set_robot_volume(volume)
        return f"Cozmo's volume set to {volume}."
    
    def cozmo_sees(self):
        """
        Makes Cozmo take a picture from his front camera and describe what he sees in the image.

        Returns:
            A string indicating success or failure. A description of the image will be provided in the system messages.
        """
        self.image = self.get_image_from_camera()
        if self.image:
            return "an image was captured"
        else:
            return "Failed."
    
    def cozmo_enrolls_face(self, name: str) -> str:
        """
        Enrolls a new face for the specified person using Cozmo's face recognition.
        The person should be looking at Cozmo during enrollment.
        
        Args:
            name: The name of the person to enroll
            
        Returns:
            Success message with face_id or error message
        """
        try:
            # Check if user profile already exists
            existing_profile = self.profile_manager.match_by_name(name)
            if not existing_profile:
                # Create new profile
                profile = self.profile_manager.create_profile(name)
                user_id = profile.user_id
            else:
                user_id = existing_profile.user_id
                profile = existing_profile
            
            # Start EnrollFace behavior
            self.robot.say_text(f"Hi {name}! Let me learn your face.").wait_for_completed()
            behavior = self.robot.start_behavior(cozmo.behavior.BehaviorTypes.EnrollFace)
            
            # Wait for face enrollment to complete (with timeout)
            time.sleep(10)  # Give time for enrollment
            
            # Stop the behavior
            behavior.stop()
            
            # Get the most recently observed face
            # Note: This is a simplified approach. In practice, you might want to
            # use face events to capture the exact face_id that was enrolled
            latest_face = None
            for face in self.robot.world.visible_faces:
                latest_face = face
                break
            
            if latest_face:
                face_id = latest_face.face_id
                # Add face ID to profile
                self.profile_manager.add_face_id(user_id, face_id)
                return f"Successfully enrolled {name} with face_id: {face_id}"
            else:
                return f"Enrollment started but no face detected. Please try again."
                
        except Exception as e:
            traceback.print_exc()
            return f"Failed to enroll face: {str(e)}"
    
    def cozmo_identifies_user(self) -> str:
        """
        Attempts to identify the current user through recent face detection and voice.
        
        Returns:
            The identified user's name or 'unknown'
        """
        # Check for recent face detection
        identified_name = None
        confidence = "low"
        
        # Look at visible faces
        for face in self.robot.world.visible_faces:
            profile = self.profile_manager.match_by_face(face.face_id)
            if profile:
                identified_name = profile.name
                confidence = "high (face)"
                break
        
        # If we have voice input module, check speaker identification
        if hasattr(self, 'user_input') and self.user_input:
            try:
                if hasattr(self.user_input, 'current_speaker_embedding'):
                    embedding = self.user_input.current_speaker_embedding
                    if embedding is not None:
                        voice_profile = self.profile_manager.match_by_voice(embedding)
                        if voice_profile:
                            if identified_name and identified_name != voice_profile.name:
                                # Conflict between face and voice
                                return f"Uncertain: face says {identified_name}, voice says {voice_profile.name}"
                            identified_name = voice_profile.name
                            confidence = "high (voice)" if not identified_name else "very high (face+voice)"
            except Exception as e:
                print(f"Error checking voice identification: {e}")
        
        if identified_name:
            return f"{identified_name} (confidence: {confidence})"
        else:
            return "unknown"
    
    def cozmo_enrolls_new_user(self, name: str) -> str:
        """
        Enrolls a completely new user with both face and voice recognition.
        Guides the user through the enrollment process.
        
        Args:
            name: The name of the person to enroll
            
        Returns:
            Success message or error
        """
        try:
            # Check if user already exists
            existing = self.profile_manager.match_by_name(name)
            if existing:
                return f"{name} is already enrolled. Use cozmo_enrolls_face to add another face view."
            
            # Create profile first
            profile = self.profile_manager.create_profile(name)
            
            # Step 1: Enroll face
            self.robot.say_text(f"Nice to meet you, {name}! First, let me learn your face.").wait_for_completed()
            face_result = self.cozmo_enrolls_face(name)
            
            # Step 2: Enroll voice (if available)
            if hasattr(self, 'user_input') and self.user_input:
                if hasattr(self.user_input, 'enroll_voice'):
                    self.robot.say_text("Now, let me learn your voice. Please speak after I beep.").wait_for_completed()
                    time.sleep(1)
                    voice_result = self.user_input.enroll_voice(profile.user_id, name)
                    if voice_result:
                        return f"Successfully enrolled {name} with both face and voice!"
                    else:
                        return f"Enrolled {name}'s face, but voice enrollment failed. Face result: {face_result}"
            
            return f"Enrolled {name}'s face: {face_result}. Voice enrollment not available."
            
        except Exception as e:
            traceback.print_exc()
            return f"Failed to enroll {name}: {str(e)}"

    def get_image_from_camera(self):
        self.robot.camera.color_image_enabled = True
        self.robot.camera.image_stream_enabled = True
        return self.robot.world.latest_image

### End of CozmoAPI class ###


def _cozmo_test_program(robot: cozmo.robot.Robot):

    def print_events(event):
        print(event)

    print(get_api_description())
    event_log.add_callback(print_events)
    voice_input = user_voice_input.VoiceInput()
    if voice_input:
        voice_input.start_loop()
    robot_api = CozmoAPI(robot, voice_input)
    commands = (
        # 'cozmo_search_light_cube()',
         'cozmo_says("Nice to meet you, Alan!")',
        # 'cozmo_drives(5, 5)',
        # 'cozmo_turns(-30.5)',
        # 'cozmo_lifts(0.5)',
        # 'cozmo_head(-0.3)',
        'cozmo_plays_animation("anim_greeting_happy_03")',
        # 'cozmo_plays_song("C2, C2_Sharp, D2, D2_Sharp, E2, F2, F2_Sharp, G2, G2_Sharp, A2, A2_Sharp, B2")',
        # 'cozmo_go_to_object(1, 65)',
        # 'cozmo_pickup_object(1)',
        # 'cozmo_place_object(2)',
        # 'cozmo_dock_with_cube(1)',
        # 'cozmo_roll_cube(1)',
        # 'cozmo_start_behavior("behaviour")',
        # 'cozmo_stop_behavior("behaviour")',
        # 'cozmo_start_freeplay()',
        # 'cozmo_listens()',        
        # 'cozmo_stop_freeplay()',
        # 'cozmo_battery_level()',
        # 'cozmo_is_charging()',
        # 'cozmo_is_carrying_object()',
        # 'cozmo_is_localized()',
        # 'cozmo_set_headlight("On")',
        # 'cozmo_set_volume(50)',
        # 'cozmo_pops_a_wheelie(1)',
        # 'cozmo_listens()',
        # 'cozmo_set_backpack_lights(255, 0, 0)',
    )
    results = robot_api.execute_commands("\n".join(commands))
    print(results)
    while True:
        print(event_log.event_list)
        time.sleep(1)

if __name__ == "__main__":
    cozmo.run_program(_cozmo_test_program, exit_on_connection_error=False)

