import cozmo
from cozmo.util import degrees, distance_mm, speed_mmps
from cozmo.song import NoteTypes, SongNote, NoteDurations
import user_voice_input
import ast
import traceback
import asyncio
from event_messages import event_log, EventType
import time
from datetime import datetime

_WAIT_TIMEOUT = 15 # seconds
_WAIT_LATENCY = 0.1 # seconds
_DEFAULT_TIMEOUT = 10 # seconds

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


class CozmoAPI:
    """
    A simplified text-based API interface for controlling Cozmo robot.
    """

    def __init__(self, robot: cozmo.robot.Robot, voice_input):
        self.robot = robot
        self.voice_input = voice_input
        self.new_user_input_provided = False
        self.cozmo_events = CozmoEvents(robot)
        event_log.add_callback(self._event_calback)
        self.image = None

    def _event_calback(self, event):
        event_type, event_message = event
        if event_type == EventType.USER_MESSAGE:
            self.new_user_input_provided = True
        
        elif event_type == EventType.VOICE_EVENT_LISTENING:
            self.robot.set_all_backpack_lights(cozmo.lights.blue_light)
        elif event_type == EventType.VOICE_EVENT_FINISHED:
            self.robot.set_backpack_lights_off()

    def _wait_user_input(self):
        self.new_user_input_provided = False
        self.voice_input.capture_user_input()
        wait = 0
        while wait < _WAIT_TIMEOUT:
            time.sleep(_WAIT_LATENCY)
            if self.new_user_input_provided:
                return True
            wait += _WAIT_LATENCY

        return False

    def cozmo_listens(self):
        """
        Waits for user to say something for 15 seconds. This will block you for 15s. Avoid using cozmo_listens(), unless you really need feedback from the user.
        
        Returns:
            A possibly imperfect, transcription of what the user said.
        """
        # user_said = self._wait_user_input()
        self.voice_input.capture_user_input()
        return ""

    def cozmo_says(self, text: str) -> str:
        """
        Makes Cozmo say the provided text.

        Args:
            text: The text for Cozmo to speak.

        Returns:
            A string indicating the result, e.g., "Cozmo said: [text]"
        """
        action = self.robot.say_text(text)
        action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
        if action.has_succeeded:
            return f"succeeded."
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
            action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
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

    def cozmo_plays_animation(self, animation_name: str) -> str:
        """
        Makes Cozmo play a specific animation.

        Args:
            animation_name: The name of the animation to play. Supported animations are: anim_energy_eat_lvl1_07, anim_energy_liftoncube_01, anim_vc_reaction_nofaceheardyou_01, anim_pyramid_reacttocube_happy_high_02, anim_guarddog_getout_timeout_01, anim_energy_successgetout_02, anim_explorer_driving01_turbo_01, anim_cozmosays_badword_01_head_angle_20, anim_memorymatch_solo_failhand_player_01, anim_reacttocliff_turtlerollfail_03, anim_rtpmemorymatch_request_02, anim_pounce_drive_01, anim_pyramid_reacttocube_frustrated_low_01, anim_explorer_idle_03, anim_workout_mediumenergy_weak_01, anim_freeplay_reacttoface_identified_03, anim_loco_driving01_start_02, anim_freeplay_reacttoface_identified_03_head_angle_40, anim_keepaway_winhand_03, anim_meetcozmo_lookface_interrupt, anim_explorer_driving01_loop_01_head_angle_-20, anim_reacttoblock_triestoreach_01, anim_explorer_driving01_loop_01_head_angle_-10, anim_cozmosays_getin_long_01_head_angle_40, anim_memorymatch_point_player_audio, anim_cozmosays_getin_short_01_head_angle_20, anim_vc_reaction_yesfaceheardyou_01, anim_codelab_lion_01_head_angle_20, anim_energy_cubeshake_01, anim_rtpkeepaway_playeryes_03, anim_energy_liftoncube_02, anim_explorer_driving01_end_01, anim_dizzy_reaction_medium_03, anim_rtpkeepaway_playerno_02, anim_codelab_tinyorchestra_takataka_01, anim_petdetection_cat_01_head_angle_40, anim_fistbump_requesttwice_01, anim_repair_severe_idle_03, anim_lookinplaceforfaces_keepalive_long, anim_cozmosays_getin_long_01, anim_meetcozmo_reenrollment_sayname_03, anim_sparking_driving_loop_01, anim_repair_severe_fix_lift_up_01, anim_launch_wakeup_03, anim_reacttoblock_ask_01, anim_cozmosays_getout_short_01_head_angle_-20, anim_explorer_driving01_start_02_head_angle_-20, anim_repair_react_fall_01, anim_freeplay_reacttoface_like_01, anim_explorer_idle_01_head_angle_20, anim_fistbump_idle_03, anim_explorer_idle_01_head_angle_10, anim_keepaway_getready_02, anim_hiking_driving_loop_01, anim_hiccup_withreaction_01, anim_dizzy_pickup_03, anim_codelab_cow_01_head_angle_-20, anim_reacttoblock_react_short_02_head_angle_20, anim_hiking_rtnewarea_02, anim_launch_idle_03, anim_reacttoblock_lifteffortpickup_01, anim_petdetection_dog_01_head_angle_-20, anim_explorer_driving01_start_02_head_angle_40, anim_repair_severe_fix_head_down_01, anim_bouncer_getin_01, anim_pyramid_lookinplaceforfaces_short_head_angle_-20, anim_guarddog_fakeout_03, anim_launch_firsttimewakeup_helloplayer_head_angle_-20, anim_explorer_idle_03_head_angle_-20, anim_launch_lifteffortplacehigh_01, anim_pyramid_thankyou_01_head_angle_40, anim_reacttoface_unidentified_01_head_angle_40, anim_factory_audio_test_02, anim_hiking_edgesquintloop_01, anim_bouncer_rerequest_01, anim_laser_drive_03, anim_reacttoblock_frustrated_int2_01, anim_repair_severe_fix_roundreaction_01, anim_meetcozmo_lookface_getin_head_angle_40, anim_rollblock_fail_01, anim_launch_startsleeping_01, anim_meetcozmo_getin_head_angle_40, anim_lookinplaceforfaces_keepalive_medium, anim_reacttocliff_turtleroll_05, anim_memorymatch_reacttopattern_standard_01, anim_freeplay_reacttoface_sayname_02_head_angle_20, anim_reacttocliff_faceplantroll_armup_02, anim_launch_wakeup_drivingloop_01, anim_cozmosays_getout_long_01_head_angle_-20, anim_mm_thinking, anim_play_driving_start_01, anim_reacttocliff_edgeliftup_01, anim_pyramid_lookinplaceforfaces_long_head_angle_20, anim_energy_cubeshake_lv2_03, anim_freeplay_reacttoface_sayname_02_head_angle_-20, anim_petdetection_cat_02_head_angle_40, anim_explorer_drvback_start_02, anim_reacttoface_unidentified_02_head_angle_-20, anim_explorer_idle_01_head_angle_30, anim_fistbump_idle_01, anim_sparking_idle_03, anim_speedtap_ask2play_01, anim_cozmosays_getout_long_01_head_angle_20, anim_launch_wakeup_05, anim_driving_upset_loop_01, anim_peekaboo_idle_01, anim_memorymatch_solo_reacttopattern_01, anim_rtpkeepaway_ideatoplay_01, anim_pyramid_reacttocube_frustrated_high_01, anim_reacttoblock_lifteffortplacelow_01, anim_speedtap_lookatplayer, anim_energy_cubedonelvl1_02, anim_driving_upset_end_01, anim_explorer_driving01_loop_02, anim_reacttocliff_turtlerollfail_02, anim_reacttocliff_turtlerollfail_01, anim_bouncer_intoscore_01, anim_speedtap_wingame_intensity03_01, anim_speedtap_losehand_02, anim_memorymatch_pointsmallright_fast_02, anim_speedtap_drivingloop_02, anim_speedtap_tap_01, anim_meetcozmo_sayname_01_head_angle_-20, anim_explorer_getout_01, anim_cozmosays_badword_01, anim_launch_firsttimewakeup_helloplayer, anim_guarddog_settle_01, anim_pyramid_lookinplaceforfaces_medium, anim_explorer_idle_02_head_angle_-20, anim_launch_search_head_angle_40, anim_energy_wakeup_01, anim_reacttocliff_huh_01, anim_launch_wakeup_enddriving_01, anim_memorymatch_pointcenter_fast_03, anim_workout_mediumenergy_getin_01, anim_hiking_driving_start_02, anim_gif_gleeserious_01, anim_pyramid_thankyou_01_head_angle_-20, anim_energy_react_stop_01, anim_explorer_driving01_start_01_head_angle_30, anim_driving_upset_loop_03, anim_meetcozmo_reenrollment_sayname_01, anim_explorer_idle_03_head_angle_-10, anim_pounce_success_04, anim_repair_mild_fix_tread_01, anim_pyramid_lookinplaceforfaces_long, anim_gif_no_01, anim_play_idle_03, anim_hiking_driving_loop_06, anim_codelab_cow_01_head_angle_40, anim_repair_severe_driving_loop_01, anim_memorymatch_idle_02, anim_launch_drivingloop_02, anim_driving_upset_loop_02, anim_freeplay_reacttoface_sayname_03_head_angle_40, anim_codelab_tiger_01, anim_meetcozmo_getin_head_angle_20, anim_launch_reacttocubepickup, anim_petdetection_dog_02, anim_energy_eat_lvl2_05, anim_hiking_getin_01, anim_rtpmemorymatch_no_02, anim_explorer_drvback_loop_03, anim_hiccup_faceplant_01, anim_explorer_driving01_end_01_head_angle_40, anim_vc_reaction_yesfaceheardyou_01_head_angle_40, anim_explorer_driving01_loop_03_head_angle_10, anim_pounce_success_01, anim_vc_alrighty_01, anim_vc_laser_lookdown_01, anim_reacttoblock_happydetermined_02, anim_speedtap_wingame_intensity02_01, anim_launch_sleeping_01, anim_petdetection_cat_01_head_angle_20, anim_pounce_fail_04, anim_reacttoblock_react_short_02, anim_energy_requestshortlvl2_01, anim_repair_severe_driving_loop_03, anim_rtpkeepaway_askforgame_01, anim_explorer_huh_01_head_angle_-10, anim_codelab_lion_01_head_angle_40, anim_loco_driving01_loop_03, anim_energy_cubeshakelvl1_03, anim_keepaway_pounce_03, anim_workout_lowenergy_strong_01, anim_sparking_fail_01, anim_codelab_kitchen_eating_01, anim_explorer_driving01_loop_01_head_angle_30, anim_explorer_driving01_turbo_01_head_angle_-20, anim_freeplay_reacttoface_identified_03_head_angle_-20, anim_rtpmemorymatch_request_03, anim_pounce_lookloop_02, anim_explorer_driving01_start_01_head_angle_10, anim_explorer_idle_03_head_angle_20, anim_cozmosays_getin_long_01_head_angle_20, anim_keepaway_fakeout_01, anim_energy_eat_04, anim_energy_idlel2_06, anim_hiking_react_05, anim_cozmosays_getin_medium_01_head_angle_-20, anim_rtpkeepaway_reacttocube_02, anim_memorymatch_solo_successgame_player_03, anim_pokedreaction_01, anim_workout_mediumenergy_getout_01, anim_reacttoblock_focusedeyes_01, anim_codelab_zombiecrawl_01, anim_explorer_driving01_end_01_head_angle_10, anim_dizzy_reaction_soft_02, anim_cozmosays_getout_long_01, anim_speedtap_enddriving_01, anim_sparking_getin_01, anim_energy_idlel2_03, anim_meetcozmo_celebration_02_head_angle_-20, anim_hiking_react_02, anim_vc_reaction_alreadyhere_01_head_angle_-20, anim_guarddog_interruption_01, anim_explorer_driving01_loop_03_head_angle_-20, anim_play_requestplay_level1_01, anim_reacttoblock_react_short_02_head_angle_-20, anim_explorer_drvback_loop_01, anim_repair_severe_wakeup_01, anim_explorer_idle_02_head_angle_10, anim_explorer_idle_02_head_angle_30, anim_explorer_driving01_turbo_01_head_angle_-10, anim_cozmosays_getout_short_01, anim_petdetection_misc_01, anim_energy_cubedown_02, anim_memorymatch_pointbigleft_02, anim_bouncer_ideatoplay_01, anim_meetcozmo_sayname_01_head_angle_20, anim_hiking_lookaround_01, anim_rtpkeepaway_idle_01, anim_energy_idlel2_02_nohead, anim_freeplay_reacttoface_identified_02_head_angle_40, anim_explorer_driving01_loop_01_head_angle_40, anim_reacttocliff_turtleroll_06, anim_bored_event_01, anim_repair_severe_reaction_01, anim_codelab_getin_01, anim_energy_idlel2_01, anim_memorymatch_pointsmallleft_02, anim_reacttocliff_stuckrightside_01, anim_freeplay_reacttoface_sayname_01_head_angle_-20, anim_memorymatch_pointsmallleft_fast_02, anim_codelab_123go, anim_energy_idlel2_05, anim_reacttoblock_react_short_01_head_angle_20, anim_greeting_happy_03, anim_repair_mild_fix_lift_02, anim_explorer_huh_01_head_angle_40, anim_reacttoblock_ask_01_head_angle_20, anim_workout_highenergy_trans_01, anim_energy_driveloop_03, anim_vc_refuse_repair_01, anim_majorwin, anim_launch_firsttimewakeup_helloworld, anim_keepaway_wingame_03, anim_memorymatch_successhand_player_03, anim_bouncer_getout_01, anim_meetcozmo_celebration, anim_codelab_lion_01_head_angle_-20, anim_pyramid_lookinplaceforfaces_medium_head_angle_20, anim_meetcozmo_celebration_02_head_angle_20, anim_hiccup_01, anim_poked_giggle, anim_vc_listening_01, anim_guarddog_pulse_01, anim_rtpkeepaway_reacttocube_01, anim_energy_cubedown_01, anim_codelab_vampirebite_01, anim_meetcozmo_lookface_getin, anim_cozmosings_120_song_01, anim_memorymatch_pointbigright_fast_02, anim_memorymatch_pointbigright_01, anim_reacttocliff_wheely_01, anim_energy_cubeshake_02, anim_hiking_react_04, anim_play_idle_01, anim_codelab_lightshow_idle, anim_lookinplaceforfaces_keepalive_long_head_angle_-20, anim_memorymatch_pointsmallleft_01, anim_fistbump_success_02, anim_workout_lowenergy_getready_01, anim_laser_drive_01, anim_reacttocliff_pickup_05, anim_peekaboo_success_02, anim_sparking_idle_02, anim_cozmosays_getout_short_01_head_angle_40, anim_repair_severe_fix_getin_01, anim_cozmosays_speakloop_03, anim_fistbump_requestonce_02, anim_meetcozmo_lookface_getin_head_angle_-20, anim_cozmosings_80_song_01, anim_gamesetup_getin_01_head_angle_20, anim_codelab_cow_01, anim_explorer_driving01_loop_02_head_angle_-20, anim_workout_lowenergy_weak_01, anim_gamesetup_getin_01, anim_repair_fix_idle_03, anim_energy_idlel1_03, anim_petdetection_shortreaction_02_head_angle_40, anim_explorer_driving01_start_02_head_angle_10, anim_reacttocliff_edge_01, anim_cozmosays_getout_short_01_head_angle_20, anim_bored_02, anim_speedtap_loseround_intensity02_02, anim_meetcozmo_lookface_head_angle_20, anim_explorer_idle_02_head_angle_-10, anim_petdetection_shortreaction_01_head_angle_-20, anim_launch_altwakeup_01, anim_sparking_idle_01, anim_reacttoface_unidentified_03_head_angle_40, anim_codelab_bored_01, anim_launch_firsttimewakeup_helloplayer_head_angle_20, anim_pounce_long_01, anim_bored_event_04, anim_pounce_04, anim_pause_idle_03, anim_workout_lowenergy_trans_01, anim_repair_fix_head_up_01, anim_sparking_success_01, anim_petdetection_shortreaction_02_head_angle_20, anim_cozmosays_app_getout_02, anim_reacttocliff_stuckleftside_01, anim_keepaway_winhand_01, anim_freeplay_reacttoface_identified_01_head_angle_-20, anim_repair_fix_getout_02, anim_petdetection_dog_03_head_angle_20, anim_dizzy_pickup_01, anim_hiking_driving_loop_02, anim_memorymatch_successhand_cozmo_02, anim_cozmosays_getout_medium_01_head_angle_40, anim_poked_01, anim_qa_firmwaremessaging_01, anim_energy_successgetout_01, anim_speedtap_look4block_01, anim_rtpkeepaway_playerno_01, anim_codelab_rooster_01_head_angle_40, anim_memorymatch_solo_successgame_player_01, anim_factory_audio_test_01, anim_peekaboo_idle_02, anim_explorer_driving01_turbo_01_head_angle_10, anim_repair_severe_driving_start_01, anim_meetcozmo_celebration_02, anim_lookinplaceforfaces_keepalive_medium_head_angle_40, anim_launch_reacttoputdown, anim_hiccup_playercure_pickupreact, anim_explorer_driving01_loop_03_head_angle_40, anim_rtpkeepaway_playerno_03, anim_reacttoblock_react_01_0, anim_cozmosings_getin_03, anim_meetcozmo_sayname_02_head_angle_20, anim_workout_mediumenergy_trans_01, anim_vc_reaction_alreadyhere_01_head_angle_40, anim_speedtap_player_idle_01, anim_keepaway_wingame_02, anim_hiking_getin_02, anim_explorer_huh_01_head_angle_-20, anim_guarddog_fakeout_01, anim_speedtap_wait_short, anim_reacttocliff_stuckleftside_03, anim_reacttocliff_pickup_02, anim_keepaway_losehand_03, anim_freeplay_reacttoface_identified_02, anim_keepaway_losegame_03, anim_launch_cubediscovery, anim_codelab_chicken_01_head_angle_-20, anim_speedtap_winhand_02, anim_petdetection_cat_02, anim_explorer_idle_03_head_angle_30, anim_explorer_driving01_start_02_head_angle_-10, anim_energy_getin_01, anim_hiking_react_03, anim_launch_startdriving_01, anim_repair_fix_idle_fullyfull_01, anim_energy_eat_lvl1_06, anim_explorer_driving01_loop_03_head_angle_-10, anim_explorer_driving01_loop_01_head_angle_20, anim_explorer_driving01_end_01_head_angle_30, anim_meetcozmo_reenrollment_sayname_02, anim_cozmosays_badword_01_head_angle_40, anim_cozmosays_badword_02_head_angle_20, anim_speedtap_winhand_03, anim_workout_highenergy_getready_01, anim_bored_getout_02, anim_keepaway_fakeout_04, anim_explorer_driving01_loop_03, anim_reacttocliff_turtleroll_03, anim_meetcozmo_celebration_02_head_angle_40, anim_explorer_driving01_turbo_01_head_angle_20, anim_freeplay_reacttoface_identified_01_head_angle_40, anim_codelab_tiger_01_head_angle_-20, anim_pyramid_thankyou_01, anim_reacttoface_unidentified_02_head_angle_20, anim_explorer_idle_01_head_angle_40, anim_rtpkeepaway_idle_03, anim_workout_lowenergy_getout_02, anim_keepaway_getout_03, anim_petdetection_dog_02_head_angle_20, anim_pause_idle_01, anim_memorymatch_successhand_cozmo_04, anim_explorer_driving01_loop_01_head_angle_10, anim_memorymatch_failgame_cozmo_03, anim_rtpmemorymatch_yes_01, anim_codelab_tinyorchestra_conducting, anim_repair_severe_driving_end_01, anim_rtpkeepaway_idle_02, anim_workout_mediumenergy_strong_01, anim_explorer_driving01_start_02, anim_reacttppl_surprise, anim_peekaboo_requestshorts_01, anim_cozmosings_getin_02, anim_repair_severe_driving_loop_02, anim_lookinplaceforfaces_keepalive_short, anim_cozmosays_getin_short_01_head_angle_-20, anim_keepaway_idle_03, anim_speedtap_wait_medium, anim_gamesetup_idle_02, anim_repair_severe_fix_getready_01, anim_reacttoface_unidentified_03_head_angle_20, anim_memorymatch_idle_03, anim_motiontrack_turnsmall, anim_cozmosays_getout_medium_01, anim_energy_eat_lvl1_09, anim_explorer_driving01_start_02_head_angle_20, anim_hiccup_02, anim_cozmosays_badword_02_head_angle_-20, anim_pounce_lookgetout_01, anim_keepaway_fakeout_02, anim_pyramid_reacttocube_frustrated_mid_01, anim_vc_refuse_energy_01, anim_codelab_ghoulish_creeping_01, anim_hiking_driving_loop_05, anim_peekaboo_fail_01, anim_pyramid_reacttocube_happy_mid_01, anim_memorymatch_failhand_player_02, anim_explorer_driving01_loop_03_head_angle_30, anim_petdetection_dog_02_head_angle_-20, anim_keepalive_eyes_01_updown, anim_energy_eat_lvl1_03, anim_play_driving_loop_03, anim_guarddog_cubedisconnect_01, anim_repair_severe_reaction_02, anim_speedtap_losehand_03, anim_codelab_cow_01_head_angle_20, anim_reacttoblock_success_01, anim_speedtap_losegame_intensity02_02, anim_freeplay_reacttoface_sayname_02_head_angle_40, anim_hiking_getin_03, anim_guarddog_getout_playersucess_01, anim_freeplay_reacttoface_wiggle_01, anim_energy_requestlvltwo_01, anim_repair_fix_wheels_forward_01, anim_energy_requestlvlone_01, anim_dizzy_reaction_soft_01, anim_petdetection_misc_01_head_angle_40, anim_reacttoblock_placeblock_01, anim_rtpmemorymatch_yes_02, anim_speedtap_losegame_intensity02_01, anim_energy_failgetout_01, anim_lookinplaceforfaces_keepalive_medium_head_angle_-20, anim_explorer_driving01_loop_02_head_angle_20, anim_meetcozmo_lookface_getout_head_angle_40, anim_triple_backup, anim_play_driving_loop_02, anim_play_idle_02, anim_explorer_huh_01_head_angle_10, anim_reacttocliff_wheely_02, anim_memorymatch_reacttopattern_01, anim_explorer_driving01_turbo_01_head_angle_40, anim_repair_fix_wheels_back_01, anim_memorymatch_solo_failhand_player_03, anim_repair_reaction_01, anim_launch_wakeup_01, anim_pounce_03, anim_meetcozmo_sayname_01, anim_repair_severe_fix_wheels_forward_01, anim_pyramid_success_01, anim_pounce_success_03, anim_petdetection_cat_02_head_angle_20, anim_vc_reaction_alreadyhere_01, anim_sparking_driving_stop_01, anim_repair_severe_fix_getout_03, anim_keepaway_getout_01, anim_play_driving_loop_01, anim_pyramid_reacttocube_happy_low_01, anim_repair_severe_idle_02, anim_petdetection_shortreaction_02_head_angle_-20, anim_explorer_idle_02_head_angle_20, anim_launch_backpackidle, anim_repair_mild_fix_lift_01, anim_reacttoblock_ask_01_head_angle_40, anim_meetcozmo_lookface_head_angle_-20, anim_guarddog_getout_timeout_02, anim_fistbump_fail_01, anim_reacttocliff_turtleroll_01, anim_meetcozmo_lookface_getout_head_angle_20, anim_gamesetup_getin_01_head_angle_-20, anim_cozmosays_app_getin, anim_meetcozmo_lookface_02, anim_bouncer_wait_03, anim_petdetection_dog_01_head_angle_20, anim_energy_idlel2_search_02, anim_codelab_chicken_01, anim_memorymatch_successhand_cozmo_01, anim_dizzy_reaction_medium_01, anim_peekaboo_successgetout_01, anim_pyramid_rt2blocks_01, anim_memorymatch_failhand_player_01, anim_speedtap_fakeout_01, anim_lookinplaceforfaces_keepalive_long_head_angle_20, anim_speedtap_losehand_01, anim_vc_reaction_yesfaceheardyou_01_head_angle_20, anim_explorer_driving01_loop_02_head_angle_-10, anim_greeting_happy_03_head_angle_-20, anim_launch_enddriving_01, anim_codelab_chicken_01_head_angle_40, anim_reacttocliff_faceplantroll_armup_01, anim_speedtap_playerno_01, anim_keepaway_getin_01, anim_repair_react_stop_01, anim_reacttoblock_react_01_head_angle_-20, anim_codelab_rooster_01_head_angle_20, anim_driving_upset_start_01, anim_rtpmemorymatch_no_01, anim_repair_fix_idle_02, anim_memorymatch_pointsmallright_02, anim_bouncer_wait_01, anim_keepaway_pounce_04, anim_memorymatch_pointsmallleft_fast_01, anim_petdetection_dog_02_head_angle_40, anim_explorer_drvback_loop_02, anim_rtpkeepaway_askforgame_02, anim_memorymatch_solo_reacttopattern_03, anim_pounce_01, anim_energy_stuckonblock_lv2, anim_reacttoblock_success_01_head_angle_-20, anim_lookinplaceforfaces_keepalive_short_head_angle_-20, anim_launch_lifteffortplacelow_01, anim_loco_driving01_loop_01, anim_memorymatch_solo_successgame_player_02, anim_play_driving_end_01, anim_reacttoblock_success_01_head_angle_20, anim_repair_severe_getout_01, anim_memorymatch_pointsmallright_fast_01, anim_poked_02, anim_cozmosays_getin_medium_01_head_angle_20, anim_dancing_mambo_01, anim_workout_lowenergy_getin_01, anim_pounce_fail_03, anim_repair_react_hit_01, anim_peekaboo_requestonce_01, anim_reacttocliff_faceplantroll_01, anim_cozmosays_getout_long_01_head_angle_40, anim_bored_event_03, anim_speedtap_drivingloop_01, anim_codelab_tiger_01_head_angle_20, anim_meetcozmo_lookface, anim_keepaway_fakeout_03, anim_memorymatch_failhand_03, anim_hiking_driving_loop_04, anim_speedtap_idle_01, anim_play_requestplay_level2_02, anim_pounce_lookloop_01, anim_reacttoblock_frustrated_int1_01, anim_reacttocliff_wheely_03, anim_repair_fix_idle_01, anim_repair_severe_interruption_edge_01, anim_gotosleep_sleeping_01, anim_gotosleep_getin_01, anim_speedtap_loseround_intensity01_01, anim_speedtap_loseround_intensity02_01, anim_petdetection_shortreaction_01_head_angle_40, anim_repair_fix_getout_03, anim_explorer_driving01_turbo_01_head_angle_30, anim_explorer_idle_02, anim_cozmosays_speakloop_01, anim_codelab_rooster_01_head_angle_-20, anim_cozmosays_getin_short_01_head_angle_40, anim_greeting_happy_03_head_angle_20, anim_memorymatch_failgame_cozmo_02, anim_codelab_duck_01, anim_meetcozmo_sayname_02_head_angle_40, anim_peekaboo_success_03, anim_memorymatch_pointbigleft_01, anim_petdetection_cat_01, anim_petdetection_dog_03_head_angle_-20, anim_bored_01, anim_energy_idlel1_01, anim_pounce_drive_02, anim_hiking_driving_start_04, anim_memorymatch_pointbigright_02, anim_repair_fix_lift_down_01, anim_memorymatch_pointbigleft_fast_01, anim_codelab_elephant_01, anim_bored_event_02, anim_pyramid_lookinplaceforfaces_long_head_angle_40, anim_speedtap_wingame_intensity02_04, anim_cozmosays_badword_02_head_angle_40, anim_explorer_idle_03_head_angle_10, anim_launch_drivingloop_03, anim_speedtap_losegame_intensity03_03, anim_hiking_driving_loop_03, anim_speedtap_startdriving_01, anim_energy_cubenotfound_01, anim_bouncer_wait_02, anim_petdetection_dog_03_head_angle_40, anim_meetcozmo_lookface_getout_head_angle_-20, anim_explorer_driving01_end_01_head_angle_20, anim_explorer_huh_01_head_angle_20, anim_speedtap_wingame_intensity02_03, anim_memorymatch_failhand_player_03, anim_keepaway_idle_01, anim_speedtap_wait_medium_03, anim_rtpkeepaway_reacttocube_03, anim_memorymatch_getout_01, anim_gamesetup_idle_01, anim_bouncer_requesttoplay_01, anim_repair_severe_idle_01, anim_cozmosays_badword_01_head_angle_-20, anim_gotosleep_off_01, anim_rtpmemorymatch_request_01, anim_petdetection_cat_02_head_angle_-20, anim_speedtap_losegame_intensity03_02, anim_speedtap_wingame_intensity03_03, anim_explorer_idle_01, anim_bouncer_timeout_01, anim_keepaway_fakeout_05, anim_loco_driving01_start_01, anim_petdetection_shortreaction_02, anim_repair_mild_fix_head_02, anim_reacttoface_unidentified_02, anim_speedtap_winhand_01, anim_play_requestplay_level1_02, anim_energy_idlel2_04, anim_energy_idlel2_search_01, anim_codelab_cubetap, anim_explorer_huh_01, anim_keepaway_losegame_01, anim_keepalive_eyesonly_loop_03, anim_memorymatch_successhand_player_02, anim_vc_refuse_nosparks_01, anim_launch_blankscreen, anim_repair_severe_fix_wheels_back_01, anim_repair_severe_fix_getout_01, anim_freeplay_reacttoface_identified_01_head_angle_20, anim_repair_fix_lowerlift_01, anim_freeplay_reacttoface_identified_03_head_angle_20, anim_fistbump_success_03, anim_pyramid_lookinplaceforfaces_short, anim_petdetection_shortreaction_01_head_angle_20, anim_keepaway_getin_02, anim_reacttocliff_pickup_03, anim_energy_shortreact_lvl2_01, anim_cozmosays_getin_medium_01, anim_sparking_driving_loop_03, anim_hiccup_turtleroll_01, anim_pounce_success_02, anim_speedtap_findsplayer_01, anim_dizzy_reaction_soft_03, anim_keepaway_pounce_02, anim_repair_fix_roundreact_01, anim_freeplay_reacttoface_sayname_01_head_angle_20, anim_rtpkeepaway_ideatoplay_03, anim_speedtap_playeryes_01, anim_repair_mild_reaction_02, anim_hiking_rtpmarker_01, anim_launch_search, anim_speedtap_getout_01, anim_peekaboo_failgetout_01, anim_memorymatch_failgame_player_01, anim_launch_drivingloop_01, anim_reacttoblock_success_01_head_angle_40, anim_codelab_tasmanian_devil_01, anim_energy_reacttocliff_lv2_01, anim_hiking_edgesquintgetin_01, anim_memorymatch_pointbigleft_fast_02, anim_lookinplaceforfaces_keepalive_short_head_angle_40, anim_bored_getout_01, anim_memorymatch_reacttopattern_02, anim_launch_wakeup_04, anim_memorymatch_reacttopattern_struggle_03, anim_keepalive_eyesonly_loop_02, anim_reacttoblock_react_short_02_head_angle_40, anim_hiking_lookaround_03, anim_gamesetup_idle_03, anim_pyramid_lookinplaceforfaces_medium_head_angle_-20, anim_launch_wakeup_drivingloop_02, anim_speedtap_wingame_intensity03_02, anim_energy_cubedownlvl2_02, anim_speedtap_winround_intensity02_02, anim_pyramid_lookinplaceforfaces_short_head_angle_20, anim_launch_search_head_angle_-20, anim_sparking_driving_start_01, anim_neutral_eyes_01, anim_hiking_driving_end_02, anim_vc_reaction_yesfaceheardyou_01_head_angle_-20, anim_reacttoblock_react_01, anim_keepaway_losegame_02, anim_dizzy_pickup_02, anim_meetcozmo_lookface_getout, anim_pyramid_thankyou_01_head_angle_20, anim_reacttoblock_frustrated_01, anim_reacttoface_unidentified_03, anim_sparking_earnsparks_01, anim_fistbump_idle_02, anim_peekaboo_idle_03, anim_explorer_idle_03_head_angle_40, anim_keepalive_blink_01, anim_energy_driveloop_01, anim_freeplay_reacttoface_identified_02_head_angle_-20, anim_speedtap_idle_02, anim_reacttoblock_success_01_0, anim_reacttoblock_reacttotopple_01, anim_gotosleep_getout_02, anim_memorymatch_solo_failhand_player_02, anim_meetcozmo_sayname_02_head_angle_-20, anim_energy_eat_03, anim_gotosleep_getout_03, anim_reacttoface_unidentified_02_head_angle_40, anim_codelab_getout_01, anim_reacttoblock_audioblockcrash, anim_petdetection_dog_01_head_angle_40, anim_memorymatch_pointbigright_fast_01, anim_keepaway_wingame_01, anim_explorer_idle_01_head_angle_-20, anim_reacttocliff_pickup_04, anim_keepaway_losehand_02, anim_codelab_kitchen_yucky_01, anim_explorer_drvback_end_01, anim_cozmosays_app_getout_01, anim_meetcozmo_getin, anim_reacttoface_unidentified_01_head_angle_20, anim_lookinplaceforfaces_keepalive_long_head_angle_40, anim_launch_firsttimewakeup, anim_cozmosays_getin_short_01, anim_keepalive_eyes_01_right, anim_keepaway_getready_03, anim_workout_lowenergy_getout_01, anim_hiccup_selfcure_getout, anim_codelab_staring_loop, anim_reacttocliff_stuckrightside_02, soundTestAnim, anim_reacttoblock_admirecubetower_01, anim_energy_failgetout_02, anim_gotosleep_getout_01, anim_keepaway_getready_01, anim_petdetection_misc_01_head_angle_20, anim_explorer_driving01_end_01_head_angle_-20, anim_play_getin_01, anim_repair_mild_fix_fail_01, anim_explorer_getin_01, anim_keepaway_losehand_01, anim_greeting_happy_02, anim_repair_mild_fix_tread_02, anim_explorer_driving01_loop_01, anim_energy_cubedone_01, anim_codelab_frightenedcozmo_01, anim_codelab_tiger_01_head_angle_40, anim_petdetection_dog_03, anim_pyramid_reacttocube_happy_high_01, anim_peekaboo_success_01, anim_hiking_react_01, anim_pyramid_lookinplaceforfaces_medium_head_angle_40, anim_speedtap_tap_02, anim_keepalive_eyes_01_forward, anim_repair_severe_fix_lift_down_01, anim_freeplay_reacttoface_sayname_03, anim_meetcozmo_lookface_head_angle_40, anim_keepaway_getout_02, anim_cozmosays_getin_long_01_head_angle_-20, anim_freeplay_reacttoface_longname_01, anim_cozmosays_getout_medium_01_head_angle_20, anim_guarddog_fakeout_02, anim_greeting_happy_03_head_angle_40, anim_codelab_magicfortuneteller_inquistive, anim_reacttoface_unidentified_01_head_angle_-20, anim_reacttoblock_react_short_01_head_angle_40, anim_energy_eat_01, anim_workout_highenergy_getout_01, anim_greeting_happy_01, anim_bouncer_intoscore_02, anim_energy_idlel2_02, anim_repair_mild_fix_head_01, anim_launch_reacttocube, anim_hiking_rtnewarea_01, anim_pounce_fail_02, anim_sparking_success_02, anim_explorer_driving01_loop_02_head_angle_30, anim_gif_idk_01, anim_memorymatch_failhand_01, anim_launch_lifteffortpickup_01, anim_codelab_sheep_01, anim_reacttoblock_lifteffortroll_01, anim_launch_search_head_angle_20, anim_freeplay_reacttoface_sayname_01, anim_vc_reaction_alreadyhere_01_head_angle_20, anim_memorymatch_failhand_02, anim_launch_wakeup_startdriving_01, anim_repair_severe_interruption_offcube_01, anim_explorer_driving01_loop_02_head_angle_10, anim_dizzy_reaction_medium_02, anim_gamesetup_reaction_01, anim_vc_reaction_nofaceheardyou_getout_01, anim_cozmosays_badword_02, anim_memorymatch_idle_01, anim_pounce_fail_01, anim_reacttocliff_stuckrightside_03, anim_memorymatch_reacttopattern_struggle_02, anim_repair_fix_getout_01, anim_meetcozmo_sayname_01_head_angle_40, anim_repair_severe_getin_01, anim_hiking_edgesquintgetout_01, anim_explorer_driving01_start_01_head_angle_40, anim_freeplay_reacttoface_sayname_03_head_angle_-20, anim_reacttocliff_stuckleftside_02, anim_explorer_driving01_start_02_head_angle_30, anim_hiking_lookaround_02, anim_energy_cubedownlvl1_03, anim_speedtap_winround_intensity02_01, anim_mm_newidea, anim_explorer_driving01_loop_03_head_angle_20, anim_keepaway_pounce_01, anim_guarddog_getout_touched_01, anim_repair_fix_lift_up_01, anim_energy_cubedownlvl2_03, anim_upgrade_reaction_lift_01, anim_memorymatch_successhand_player_01, anim_play_requestplay_level2_01, anim_codelab_rooster_01, anim_speedtap_winround_intensity01_01, anim_rtpkeepaway_playeryes_01, anim_rtc_react_01, anim_hiking_observe_01, anim_freeplay_reacttoface_sayname_02, anim_freeplay_reacttoface_sayname_01_head_angle_40, anim_explorer_idle_01_head_angle_-10, anim_cozmosays_getout_medium_01_head_angle_-20, anim_pounce_lookloop_03, anim_codelab_lion_01, anim_pyramid_lookinplaceforfaces_long_head_angle_-20, anim_laser_drive_02, anim_endmambo, anim_repair_severe_fix_head_up_01, anim_repair_severe_fix_getout_02, anim_test_shiver, anim_workout_highenergy_strong_01, anim_speedtap_wait_medium_02, anim_pounce_02, anim_explorer_driving01_start_01_head_angle_-20, anim_rtpkeepaway_ideatoplay_02, anim_react2block_02, anim_bouncer_intoscore_03, anim_speedtap_foundblock_01, anim_reacttocliff_pickup_06, anim_keepaway_idle_02, anim_memorymatch_solo_reacttopattern_02, anim_memorymatch_pointcenter_03, anim_guarddog_getout_untouched_02, anim_reacttoblock_putdown2nd_01, anim_keepalive_eyesonly_loop_01, anim_rtpmemorymatch_yes_04, anim_freeplay_reacttoface_identified_02_head_angle_20, anim_pounce_drive_03, anim_dizzy_shake_loop_01, anim_energy_idlel1_02, anim_launch_eyeson_01, anim_cozmosays_speakloop_02, anim_fistbump_requestonce_01, anim_dizzy_reaction_hard_01, anim_reacttoblock_ask_01_0, anim_cozmosings_getin_01, anim_loco_driving01_loop_02, anim_reacttocliff_turtleroll_02, anim_memorymatch_pointcenter_01, anim_cozmosays_getin_medium_01_head_angle_40, anim_repair_fix_head_down_01, anim_speedtap_losegame_intensity02_03, anim_launch_firsttimewakeup_helloplayer_head_angle_40, anim_reacttoblock_happydetermined_01, anim_explorer_driving01_start_01_head_angle_20, anim_hiking_driving_start_01, anim_majorfail, anim_sdk_speak_01, anim_memorymatch_pointcenter_02, anim_memorymatch_failgame_cozmo_01, anim_gamesetup_getin_01_head_angle_40, anim_memorymatch_reacttopattern_struggle_01, anim_repair_fix_getready_01, anim_workout_mediumenergy_getready_01, anim_petdetection_cat_01_head_angle_-20, anim_petdetection_misc_01_head_angle_-20, anim_speedtap_losegame_intensity03_01, anim_guarddog_sleeploop_01, anim_launch_wakeup_02, anim_pounce_reacttoobj_01_shorter, anim_freeplay_reacttoface_sayname_03_head_angle_20, anim_energy_drivegeout_01, anim_vc_reaction_whatwasthat_01, anim_gamesetup_getout_01, anim_energy_driveloop_02, anim_speedtap_wingame_intensity02_02, anim_explorer_driving01_start_01, anim_reacttoblock_stuckonblock_01, anim_memorymatch_successhand_cozmo_03, anim_energy_idlel2_03_nohead, anim_hiking_driving_start_03, anim_pyramid_lookinplaceforfaces_short_head_angle_40, anim_energy_drivegetin_01, anim_peekaboo_requestthrice_01, anim_peekaboo_getin_01, anim_launch_idle_02, anim_hiking_rtnewarea_03, anim_petdetection_dog_01, anim_energy_cubeshakelvl1_02, anim_memorymatch_pointcenter_fast_02, anim_reacttoblock_react_01_head_angle_40, anim_energy_getout_01, anim_energy_cubedownlvl1_02, anim_meetcozmo_getin_head_angle_-20, anim_peekaboo_requesttwice_01, anim_memorymatch_pointcenter_fast_01, anim_repair_fix_getin_01, anim_sparking_getout_01, anim_gotosleep_sleeploop_01, anim_guarddog_sleeploop_02, anim_codelab_frog_01, anim_workout_highenergy_getin_01, anim_reacttoblock_react_01_head_angle_20, anim_explorer_driving01_start_01_head_angle_-10, anim_repair_fix_raiselift_01, anim_hiking_driving_end_01, anim_energy_eat_02, anim_lookinplaceforfaces_keepalive_short_head_angle_20, anim_energy_idlel2_01_nohead, anim_hiccup_faceplant_02, anim_fistbump_success_01, anim_codelab_scarycozmo_01, anim_cozmosings_getout_01, anim_gotosleep_getout_04, anim_explorer_driving01_end_01_head_angle_-10, anim_workout_highenergy_weak_01, anim_energy_idlel2_search_03, anim_fistbump_requestoncelong_01, anim_explorer_drvback_start_01, anim_codelab_chicken_01_head_angle_20, anim_energy_cubedone_02, anim_repair_fix_idle_fullyfull_03, anim_reacttoface_unidentified_03_head_angle_-20, anim_sparking_driving_loop_02, anim_lookinplaceforfaces_keepalive_medium_head_angle_20, anim_memorymatch_pointsmallright_01, anim_reacttocliff_pickup_01, anim_reacttoblock_react_short_01_head_angle_-20, anim_loco_driving01_end_01, anim_reacttocliff_turtleroll_04, anim_speedtap_tap_03, anim_repair_severe_fix_fail_01, anim_freeplay_reacttoface_identified_01, anim_hiccup_getin, anim_keepaway_winhand_02, anim_repair_severe_fix_lowerlift_01, anim_guarddog_getout_untouched_01, ANIMATION_TEST, anim_meetcozmo_lookface_getin_head_angle_20, anim_hiccup_playercure_getout, anim_energy_requestshortlvl1_01, anim_dizzy_shake_stop_01, anim_petdetection_shortreaction_01, anim_reacttoblock_lifteffortplacehigh_01, anim_memorymatch_failgame_player_03, anim_play_getout_01, anim_energy_cubeshake_lv2_02, anim_reacttocliff_faceplantroll_02, anim_memorymatch_failgame_player_02, anim_reacttoblock_ask_01_head_angle_-20, anim_codelab_rattle_snake_01, anim_explorer_idle_02_head_angle_40, anim_explorer_driving01_loop_02_head_angle_40, anim_keepaway_getin_03, anim_repair_fix_idle_fullyfull_02, anim_energy_eat_lvl1_08, anim_rtpmemorymatch_yes_03, anim_keepaway_fakeout_06, anim_reacttoblock_react_short_01, anim_guarddog_getout_busted_01, anim_cozmosings_100_song_01, anim_repair_severe_fix_raiselift_01, anim_reacttoface_unidentified_01, anim_pause_idle_02, anim_upgrade_reaction_tracks_01, anim_meetcozmo_sayname_02, anim_explorer_huh_01_head_angle_30, anim_energy_cubenotfound_02, anim_launch_idle_01, anim_speedtap_wait_long, anim_rtpkeepaway_playeryes_02

        Returns:
            A string indicating the result, e.g., "Cozmo played animation: [animation_name]"
        """
        try:
            action = self.robot.play_anim(name=animation_name)
            action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo played animation: {animation_name}"
            else:
                return f"Failed: {action.failure_reason}"
        except KeyError:
            return f"Animation '{animation_name}' not found."

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

    def cozmo_search_light_cube(self) -> str:
        """
        Makes Cozmo search for a light cube and returns an object_id that can be used for other actions such as pop a wheely, pick up, roll, etc.

        Returns:
            A string indicating the result, e.g., "Found cube with ID: [object_id]" or "No cube found."
        """
        look_around = self.robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
        cube = None
        try:
            cube = self.robot.world.wait_for_observed_light_cube(timeout=_DEFAULT_TIMEOUT)

        except asyncio.TimeoutError:
            self.robot.play_anim_trigger(cozmo.robot.anim.Triggers.MajorFail)

        finally:
            # whether we find it or not, we want to stop the behavior
            look_around.stop()

        if cube:
            return f"Found cube with ID: {cube.object_id}"
        else:
            return "No cube found."

    def cozmo_go_to_object(self, object_id: int, distance: float) -> str:
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
            action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo went to object {object_id}."
            else:
                return f"Failed: {action.failure_reason}"
        else:
            return f"Object with ID {object_id} not found."

    def cozmo_pickup_object(self, object_id: int) -> str:
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
            action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo picked up object {object_id}."
            else:
                return f"Failed: {action.failure_reason}"

        return f"Cube with ID {object_id} not found."

    def cozmo_place_object(self, object_id: int) -> str:
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
                action = self.robot.place_object_on_ground_here(cube)
                action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
                if action.has_succeeded:
                    return f"Cozmo placed object {object_id}."
                else:
                    return f"Failed: {action.failure_reason}"
            else:
                return f"Cube with ID {object_id} not seen."
        else:
            return "Failed. Cozmo is not carrying an object."

    def cozmo_dock_with_cube(self, object_id: int) -> str:
        """
        Makes Cozmo dock with a specific cube. Cozmo needs to find a cube first, using cozmo_search_light_cube() which returns the object_id of the cube to dock with.

        Args:
            object_id: The ID of the LightCube to dock with.

        Returns:
            A string indicating the result, e.g., "Cozmo docked with cube [object_id]."
        """
        object_id = int(object_id)
        cube = self.robot.world.wait_for_observed_light_cube(timeout=_DEFAULT_TIMEOUT)
        if cube and cube.object_id == object_id:
            action = self.robot.dock_with_cube(cube)
            action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo docked with cube {object_id}."
            else:
                return f"Failed: {action.failure_reason}"
        else:
            return f"Cube with ID {object_id} not seen."

    def cozmo_roll_cube(self, object_id: int) -> str:
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
            action.wait_for_completed(timeout=_DEFAULT_TIMEOUT)
            if action.has_succeeded:
                return f"Cozmo rolled cube {object_id}."
            else:
                return f"Failed: {action.failure_reason}"
        else:
            return f"Cube with ID {object_id} not seen."

    def cozmo_start_behavior(self, behavior_name: str) -> str:
        """
        Starts a specific behavior for Cozmo to perform autonomously.
        You shouldn't attempt to drive Cozmo during this, as it will clash
        with whatever the current behavior is attempting to do and the calls will fail.
        Use cozmo_stop_behavior() before using other functions.
  
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

    def cozmo_stop_freeplay(self) -> str:
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

    def cozmo_set_backpack_lights(self, R: int, G: int, B: int) -> str:
        """
        Sets the color of Cozmo's backpack lights. Set all channels to 0 to turn them off.

        Args:
            R: Red channel from 0-255.
            G: Green channel from 0-255.
            B: Blue channel from 0-255.

        Returns:
            A string indicating the result, e.g., "Cozmo's backpack lights set to (R, G, B)."
        """
        if R == 0 and G == 0 and B == 0:
            self.robot.set_backpack_lights_off()
        else:
            try:
                light = cozmo.lights.Light(cozmo.lights.Color(rgb=(int(R), int(G), int(B))))
                self.robot.set_all_backpack_lights(light)
            except AttributeError:
                return f"Failed."
        return f"Cozmo's backpack lights set to (R, G, B)."

    def cozmo_set_headlight(self, on_off: str) -> str:
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
    
    def cozmo_captures_image(self):
        """
        Makes Cozmo take a picture from his front camera.

        Returns:
            A string indicating success or failure. 
            A description of the image will be provided in the system messages.
        """
        wait = 0
        while wait < _WAIT_TIMEOUT:
            self.image = self.get_annotated_image()
            if self.image:
                break
            wait += _WAIT_LATENCY

        if self.image:
            return "" # Result will be provide by the generative model
        else:
            return "Failed."

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
                    message = f"Result of {line}: API Call Error: {e}"
                    event_log.message(EventType.API_RESULT, message)
                    results.append(message)

        return "\n".join(results), self.image
    
    def get_annotated_image(self):
        '''Convert PIL image and return it'''
        self.robot.camera.color_image_enabled = True
        self.robot.camera.image_stream_enabled = True
        return self.robot.world.latest_image


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


def print_events(event):
    print(event)

def _cozmo_test_program(robot: cozmo.robot.Robot):
    print(get_api_description())
    event_log.add_callback(print_events)
    voice_input = user_voice_input.VoiceInput()
    robot_api = CozmoAPI(robot, voice_input)
    commands = (
        # 'cozmo_search_light_cube()',
        # 'cozmo_says("Nice to meet you, Alan!")',
        # 'cozmo_drives(5, 5)',
        # 'cozmo_turns(-30.5)',
        # 'cozmo_lifts(0.5)',
        # 'cozmo_head(-0.3)',
        # 'cozmo_play_animation("anim_peekaboo_success_02")',
        # 'cozmo_plays_song("C2, C2_Sharp, D2, D2_Sharp, E2, F2, F2_Sharp, G2, G2_Sharp, A2, A2_Sharp, B2")',
        'cozmo_go_to_object(1, 65)',
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
        time.sleep(1)

if __name__ == "__main__":
    cozmo.run_program(_cozmo_test_program, exit_on_connection_error=False)

