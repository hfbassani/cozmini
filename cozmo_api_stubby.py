import cozmo_api
from cozmo_custom import cozmo
from event_messages import event_log, EventType
import user_voice_input
import time
import cv2
from PIL import Image

class CozmoAPIStubby(cozmo_api.CozmoAPI):
    """
    A simplified text-based API interface for controlling Cozmo robot (stub version).

    This version allows simulating success/failure of calls through the succeed
    parameter in the init method.
    """

    def __init__(self, robot: cozmo.robot.Robot=None, user_input=None, succeed=True):
        self.succeed = succeed  # Flag to simulate success/failure
        self.robot = robot
        self.user_input = user_input
        event_log.add_callback(self._event_calback)
        self.image = None
        self.video_capture = cv2.VideoCapture(0)
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 200)

    def set_user_input(self, user_input):
        self.user_input = user_input

    def _event_calback(self, event):
        event_type, event_message = event
        if event_type == EventType.VOICE_EVENT_LISTENING:
            print("Cozmo is listening...")
        elif event_type == EventType.VOICE_EVENT_FINISHED:
            print("Cozmo has finished listening.")

        return False

    def set_backpack_lights(self, light: cozmo.lights.Light):
        """Set the backpack lights without the API internal light state so that it can be restored later."""
        print("Backpack lights set.")

    def restore_backpack_lights(self):
        print("Backpack lights restored.")

    ### The API functions start here all of them start with cozmo_ ###

    def cozmo_listens(self):
        """
        Listens to the user for 10 seconds.
        
        Returns:
            A possibly imperfect, transcription of what the user said will be provided as system message.
        """
        if self.user_input:
            self.user_input.capture_user_input()
        return ""

    def cozmo_says(self, text: str) -> str:
        """
        Simulates Cozmo saying text (success or failure based on init flag).

        Args:
            text: The text for Cozmo to speak.

        Returns:
            A string indicating the result.
        """
        if self.succeed:
            return f"succeeded."
        else:
            return "failed."
        time.sleep(0.1*len(text))  # Simulate some delay for speaking

    def cozmo_drives(self, distance: float, speed: float) -> str:
        """
        Simulates driving Cozmo (success or failure based on init flag).

        Args:
            distance: The distance to drive in millimeters (positive for forward, negative for backward).
            speed: The speed to drive in millimeters per second (positive value).

        Returns:
            A string indicating the result.
        """
        time.sleep(0.1*(distance/speed))  # Simulate some delay for driving
        if self.succeed:
            return f"Cozmo drove {distance} mm at {speed} mmps."
        else:
            return "Cozmo failed to drive."

    def cozmo_pops_a_wheelie(self, object_id: int) -> str:
        """
        Simulates making Cozmo pop a wheelie (success or failure based on init flag).

        Args:
            object_id: The ID of the LightCube to use for the wheelie (ignored in this stub).

        Returns:
            A string indicating the result.
        """
        time.sleep(5)  # Simulate some delay for popping a wheelie
        if self.succeed:
            return "Cozmo has performed a wheel stand!"
        else:
            return "Wheelie failed."

    def cozmo_turns(self, angle: float) -> str:
        """
        Simulates turning Cozmo (success or failure based on init flag).

        Args:
            angle: A float representing the angle to turn in degrees (positive for left, negative for right).

        Returns:
            A string indicating the result.
        """
        time.sleep(0.1*abs(angle))  # Simulate some delay for turning
        if self.succeed:
            return f"Cozmo turned {angle} degrees."
        else:
            return "Cozmo failed to turn."

    def cozmo_lifts(self, height: float) -> str:
        """
        Simulates raising/lowering Cozmo's lift (success or failure based on init flag).

        Args:
            height: A float representing the desired lift height as a ratio (0.0 for bottom, 1.0 for top).

        Returns:
            A string indicating the result.
        """
        if self.succeed:
            return f"Cozmo's lift is now at {height} ratio."
        else:
            return "Cozmo failed to adjust lift."

    def cozmo_head(self, angle: float) -> str:
        """
        Simulates moving Cozmo's head (success or failure based on init flag).

        Args:
            angle: The desired head angle in degrees (within Cozmo's head movement range).

        Returns:
            A string indicating the result.
        """
        time.sleep(0.1*abs(angle))  # Simulate some delay for head movement
        if self.succeed:
            return f"Cozmo's head is now at {angle} degrees."
        else:
            return "Cozmo failed to move head."

    def cozmo_plays_animation(self, animation_name: str) -> str:
        """
        Makes Cozmo play a specific animation.

        Args:
            animation_name: The name of the animation to play. Supported animation names:
                Happy/Excited: anim_pyramid_reacttocube_happy_high_02, anim_energy_successgetout_02, anim_explorer_driving01_turbo_01, anim_memorymatch_solo_successgame_player_01, anim_fistbump_success_02, anim_majorwin, anim_keepaway_wingame_03, anim_meetcozmo_celebration, anim_pounce_success_04, anim_speedtap_wingame_intensity03_01
                
                Sad/Frustrated: anim_pyramid_reacttocube_frustrated_low_01, anim_memorymatch_solo_failhand_player_01, anim_reacttocliff_turtlerollfail_03, anim_driving_upset_loop_01, anim_speedtap_losehand_02, anim_memorymatch_failgame_cozmo_03, anim_reacttoblock_frustrated_int2_01, anim_rollblock_fail_01, anim_reacttocliff_stuckrightside_01, anim_majorfail, anim_speedtap_losegame_intensity02_02
                
                Angry/Scared: anim_guarddog_getout_timeout_01, anim_cozmosays_badword_01, anim_repair_severe_idle_03, anim_reacttoblock_triestoreach_01, anim_repair_react_fall_01, anim_sparking_fail_01, anim_reacttoface_unidentified_01, anim_pounce_fail_04, anim_repair_severe_driving_loop_01
                
                Calm/Neutral: anim_explorer_idle_03, anim_lookinplaceforfaces_keepalive_long, anim_sparking_idle_03, anim_hiking_driving_loop_01, anim_launch_idle_03, anim_play_idle_03, anim_memorymatch_idle_02, anim_explorer_drvback_start_02, anim_pause_idle_03, anim_rtpkeepaway_idle_01, anim_energy_idlel2_01, anim_speedtap_player_idle_01, anim_gamesetup_idle_02, anim_neutral_eyes_01
                
                Playful/Curious: anim_pounce_drive_01, anim_fistbump_idle_03, anim_keepaway_getready_02, anim_petdetection_cat_01, anim_explorer_getout_01, anim_peekaboo_idle_01, anim_speedtap_ask2play_01, anim_rtpkeepaway_askforgame_01, anim_pounce_lookloop_02, anim_energy_eat_04, anim_play_driving_start_01, anim_petdetection_dog_02, anim_pounce_long_01, anim_speedtap_look4block_01, anim_hiking_lookaround_01, anim_pounce_04, anim_explorer_huh_01, anim_pounce_reacttoobj_01_shorter
                
                Sleepy/Tired: anim_launch_startsleeping_01, anim_guarddog_sleeploop_01, anim_gotosleep_sleeping_01, anim_gotosleep_off_01, anim_gotosleep_sleeploop_01
                
                Confused/Surprised: anim_reacttocliff_huh_01, anim_dizzy_reaction_medium_03, anim_hiccup_withreaction_01, anim_reacttppl_surprise, anim_explorer_huh_01_head_angle_-10, anim_dizzy_reaction_soft_02, anim_hiccup_faceplant_01, anim_keepalive_eyes_01_updown

        Returns:
            A string indicating the result, e.g., "Cozmo played animation: [animation_name]"
        """
        time.sleep(3)  # Simulate some delay for playing animation
        if self.succeed:
            return f"Cozmo played animation: {animation_name}"
        else:
            return f"failed"

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
        time.sleep(0.25*len(song_notes))  # Simulate some delay for playing song
        if self.succeed:
            return "Cozmo played the song."
        else:
            return "Cozmo failed to play the song."

    def cozmo_searches_light_cube(self) -> str:
        """
        Simulates searching for a light cube (success or failure based on init flag).

        Returns:
            A string indicating the result (always finds a cube in this stub).
        """
        time.sleep(5)  # Simulate some delay for searching
        if self.succeed:
            return "Found cube with ID: 1"
        else:
            return "Cozmo failed to search for a cube."

    def cozmo_goes_to_object(self, object_id: int, distance: float) -> str:
        """
        Simulates driving to an object (success or failure based on init flag).

        Args:
            object_id: The ID of the object to approach (ignored in this stub).
            distance: The distance from the object to stop (in millimeters).

        Returns:
            A string indicating the result.
        """
        time.sleep(0.1*(distance/100))  # Simulate some delay for driving
        if self.succeed:
            return f"Cozmo went to object {object_id}."
        else:
            return "Cozmo failed to go to the object."

    def cozmo_picksup_object(self, object_id: int) -> str:
        """
        Simulates picking up an object (success or failure based on init flag).

        Args:
            object_id: The ID of the LightCube to pick up (ignored in this stub).

        Returns:
            A string indicating the result.
        """
        time.sleep(3)  # Simulate some delay for picking up object
        if self.succeed:
            return f"Cozmo picked up object {object_id}."
        else:
            return "failed"

    def cozmo_places_object(self, object_id: int) -> str:
        """
        Simulates placing an object (success or failure based on init flag).

        Args:
            object_id: The ID of the object to place (ignored in this stub).

        Returns:
            A string indicating the result (always succeeds in this stub since carrying is not simulated).
        """
        time.sleep(2)  # Simulate some delay for placing object
        if self.succeed:
            return f"Cozmo placed object {object_id}."
        else:
            return "failed"

    def cozmo_docks_with_cube(self, object_id: int) -> str:
        """
        Simulates docking with a cube (success or failure based on init flag).

        Args:
            object_id: The ID of the LightCube to dock with (ignored in this stub).

        Returns:
            A string indicating the result.
        """
        time.sleep(3)  # Simulate some delay for docking
        if self.succeed:
            return f"Cozmo docked with cube {object_id}."
        else:
            return "failed."

    def cozmo_rolls_cube(self, object_id: int) -> str:
        """
        Simulates rolling a cube (success or failure based on init flag).

        Args:
            object_id: The ID of the LightCube to roll (ignored in this stub).

        Returns:
            A string indicating the result.
        """
        time.sleep(3)  # Simulate some delay for rolling
        if self.succeed:
            return f"Cozmo rolled cube {object_id}."
        else:
            return "failed"

    def cozmo_starts_behavior(self, behavior_name: str) -> str:
        """
        Simulates starting a behavior (success or failure based on init flag).

        Args:
            behavior_name: The name of the behavior to start among: FindFaces, KnockOverCubes, LookAroundInPlace, PounceOnMotion, RollBlock, StackBlocks, EnrollFace

        Returns:
            A string indicating the result.
        """
        if self.succeed:
            return f"Cozmo started behavior: {behavior_name}"
        else:
            return "Cozmo failed to start the behavior."

    def cozmo_stops_behavior(self, behavior_name: str) -> str:
        """
        Simulates stopping a behavior (success or failure based on init flag).

        Args:
            behavior_name: The name of the behavior to stop (ignored in this stub).

        Returns:
            A string indicating the result (always succeeds in this stub).
        """
        if self.succeed:
            return f"Cozmo stopped behavior: {behavior_name}"
        else:
            return "Cozmo failed to stop the behavior."

    def cozmo_starts_freeplay(self) -> str:
        """
        Simulates starting freeplay mode (success or failure based on init flag).

        Returns:
            A string indicating the result.
        """
        if self.succeed:
            return "Cozmo entered freeplay mode."
        else:
            return "Cozmo failed to enter freeplay mode."

    def cozmo_stops_freeplay(self) -> str:
        """
        Simulates stopping freeplay mode (success or failure based on init flag).

        Returns:
            A string indicating the result.
        """
        if self.succeed:
            return "Cozmo exited freeplay mode."
        else:
            return "Cozmo failed to exit freeplay mode."

    def cozmo_battery_level(self) -> str:
        """
        Simulates reporting battery level (always succeeds in this stub, level set to 1.0).

        Returns:
            A string indicating the battery level.
        """
        if self.succeed:
            return "Cozmo's battery level is 3.2v out of 3.7 volts"
        else:
            return "Cozmo failed to get battery level."

    def cozmo_is_charging(self) -> str:
        """
        Simulates reporting charging status (always returns 'charging' in this stub).

        Returns:
            A string indicating the charging status.
        """
        return "Cozmo is charging."  # Always charging in this stub

    def cozmo_is_carrying_object(self) -> str:
        """
        Simulates reporting carrying status (always returns 'not carrying' in this stub).

        Returns:
            A string indicating the carrying status.
        """
        return "Cozmo is not carrying an object."  # Always not carrying in this stub

    def cozmo_is_localized(self) -> str:
        """
        Simulates reporting localization status (always succeeds in this stub).

        Returns:
            A string indicating the localization status.
        """
        if self.succeed:
            return "Cozmo is localized."
        else:
            return "Cozmo failed to check localization."

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
        if self.succeed:
            return f"Cozmo's backpack lights set to ({r}, {g}, {b})."
        else:
            return f"Failed."
        
    def cozmo_sets_headlight(self, state: bool) -> str:
        """
        Simulates setting the Cozmo's headlight (success or failure based on init flag).

        Args:
            state: True to turn the headlight on, False to turn it off.

        Returns:
            A string indicating the result, e.g., "Cozmo's headlight turned on."
        """
        on_off = on_off.lower()
        if on_off == "on":
            return "Cozmo's headlight turned on."
        elif on_off == "off":
            return "Cozmo's headlight turned off."
        else:
            return f"Invalid option: {on_off}"

    def cozmo_sets_volume(self, volume: int) -> str:
        """
        Simulates setting the Cozmo's volume (success or failure based on init flag).

        Args:
            volume: The desired volume level (0 to 100, ignored in this stub).

        Returns:
            A string indicating the result.
        """
        if self.succeed:
            return f"Cozmo's volume is set to {volume}."  # Volume not actually set in stub
        else:
            return "Cozmo failed to set volume."
        
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

    def get_image_from_camera(self):
        if self.video_capture.isOpened():
            ret, frame = self.video_capture.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.image = Image.fromarray(frame_rgb)

        if not self.image:
            # fallback to a default image
            self.image = Image.open('assets/lightcube.png')

        return self.image


if __name__ == "__main__":
    def print_events(event):
        print(event)

    event_log.add_callback(print_events)
    voice_input = user_voice_input.init_voice_input()
    if not voice_input:
        voice_input.start_voice_input_loop()
    robot_api = CozmoAPIStubby(None, voice_input)
    commands = (
        # 'cozmo_search_light_cube()',
        # 'cozmo_says("Nice to meet you, Alan!")',
        # 'cozmo_drives(5, 5)',
        # 'cozmo_turns(-30.5)',
        # 'cozmo_lifts(0.5)',
        # 'cozmo_head(-0.3)',
        # 'cozmo_play_animation("anim_peekaboo_success_02")',
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
        # 'cozmo_set_backpack_lights(255, 0, 0)',
        'cozmo_sees()',
    )
    results = robot_api.execute_commands("\n".join(commands))
    print(results)
    while True:
        print(event_log.event_list)
        time.sleep(1)