# Cozmini
The [Gemini](https://gemini.google.com/) language model powers Cozmo's mind!

# Features:
 - Speech-text and text-to-speech.
 - "Hey, Cozmo" keyword detection.
 - API with support for several Cozmo tricks, including grabbing images from Cozmo's camera.
 - Easy to customize Cozmini's personality. Just edit [cozmo_instructions.txt](https://github.com/hfbassani/cozmini/blob/main/cozmo_instructions.txt).
 - Dev mode that simulates Cozmo for when you don't have it at hand.

## API made accessible to Gemini:

**Speech and Listening:**

* `cozmo_listens()`: Listens for user input for 15 seconds and returns transcribed text (if any).
* `cozmo_says(text: str)`: Makes Cozmo say the provided text and returns a success/failure message.

**Movement:**

* `cozmo_drives(distance: float, speed: float)`: Makes Cozmo drive straight for a specified distance and speed, returning a success/failure message.
* `cozmo_turns(angle: float)`: Makes Cozmo turn by a specified angle, returning a success/failure message.
* `cozmo_lifts(height: float)`: Raises or lowers Cozmo's lift to a specific height, returning a success/failure message.
* `cozmo_go_to_object(object_id: int, distance: float)`: Makes Cozmo drive to a specific object (using its ID) and stop at a certain distance, returning a success/failure message.

**Object Interaction:**

* `cozmo_pops_a_wheelie(object_id: int)`: Makes Cozmo attempt a wheelie using a light cube (specified by ID), returning a success/failure message.
* `cozmo_pickup_object(object_id: int)`: Makes Cozmo pick up a light cube (specified by ID), returning a success/failure message.
* `cozmo_place_object(object_id: int)`: Makes Cozmo place the carried object on a light cube (specified by ID), returning a success/failure message.
* `cozmo_dock_with_cube(object_id: int)`: Makes Cozmo dock with a light cube (specified by ID), returning a success/failure message.
* `cozmo_roll_cube(object_id: int)`: Makes Cozmo roll a light cube (specified by ID), returning a success/failure message.
* `cozmo_search_light_cube()`: Makes Cozmo search for a light cube and returns its ID or a message indicating no cube was found.
* `cozmo_is_carrying_object()`: Checks if Cozmo is currently carrying an object, returning a confirmation or denial message.

**Animations and Sounds:**

* `cozmo_plays_animation(animation_name: str)`: Makes Cozmo play a specified animation, returning a success/failure message or indicating the animation is not found.
* `cozmo_plays_song(song_notes: str)`: Makes Cozmo play a song with provided notes, returning a success/failure message or indicating a note is not supported.

**Behaviors:**

* `cozmo_start_behavior(behavior_name: str)`: Starts a specific Cozmo behavior, returning a success/failure message or indicating the behavior is not found.
* `cozmo_stop_behavior(behavior_name: str)`: Stops a specific Cozmo behavior, returning a success/failure message or indicating the behavior is not running.
* `cozmo_start_freeplay()`: Starts Cozmo's freeplay mode, returning a success/failure message.
* `cozmo_stop_freeplay()`: Stops Cozmo's freeplay mode, returning a success/failure message.

**Information and Status:**

* `cozmo_battery_level()`: Returns Cozmo's current battery level.
* `cozmo_is_charging()`: Checks if Cozmo is currently charging, returning a confirmation or denial message.
* `cozmo_is_localized()`: Checks if Cozmo knows its location, returning a confirmation or denial message.
* `cozmo_sees()`: Makes Cozmo take a picture and describe what it sees (success/failure message, description provided elsewhere).

**Lights and Volume:**

* `cozmo_set_backpack_lights(R: int, G: int, B: int)`: Sets the color of Cozmo's backpack lights (or turns them off), returning a success message.
* `cozmo_set_headlight(on_off: str)`: Turns Cozmo's headlight on or off, returning a success message or indicating an invalid option.
* `cozmo_set_volume(volume: float)`: Sets Cozmo's speaker volume, returning a success message.


# Requirements:
 - An Android or IOS device with the Cozmo App connected via USB to your PC or Mac
 - A [Gemini](https://ai.google.dev/) developer key
 - A [GCP](https://cloud.google.com/) project with billing enabled for speech-text (you can stay in the free tier)
 - A [Picovoice](https://picovoice.ai/) key and a [Porcupine](https://picovoice.ai/platform/porcupine/) keyword file for the "Hey, Cozmo" keyword detection.

# Setting up and running:
 - Run `./setup/install_packs.sh` to install the required packages and create
   the virtual environment.
 - Get a Gemini dev key: https://ai.google.dev/
 - Get your Picovoice keys and keyword file here: https://picovoice.ai/
 - Install gcloud CLI: https://cloud.google.com/sdk/docs/install
 - Run `gcloud init` to set it up and follow the instructions
 - Run `gcloud auth application-default login` to get credentials
 - Edit the `keys/env_keys.sh` with your keys and Picovoice keyword file:
 ```
 export PICOVOICE_KEYWORD_PATH=./keys/[enter your hey-cozmo*.ppn here]
 export PICOVOICE_ACCESS_KEY=[enter your Picovoice key here]
 export GOOGLE_API_KEY=[enter your google API key here]
 ```
 - Finally, run `./start_cozmini.sh` and start interacting with Cozmini by voice or on the web browser UI.
