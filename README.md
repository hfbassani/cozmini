# Cozmini
The [Gemini](https://gemini.google.com/) language model powers Cozmo's mind!

Based on [Cozmo SDK](https://github.com/anki/cozmo-python-sdk)

# Features:
 - Speech-text and text-to-speech.
 - "Hey, Cozmo" keyword detection.
 - API with support for several Cozmo tricks, including grabbing images from Cozmo's camera.
 - It's easy to customize Cozmini's personality. Just edit [cozmo_instructions.txt](https://github.com/hfbassani/cozmini/blob/main/cozmo_instructions.txt).
 - Dev mode that simulates Cozmo for when you don't have it at hand.

## API made accessible to Gemini:

**Speech and Listening:**

* `cozmo_listens()`: Listens for user input for 15 seconds.
* `cozmo_says(text: str)`: Makes Cozmo say the provided text.

**Movement:**

* `cozmo_drives(distance: float, speed: float)`: Makes Cozmo drive straight for a specified distance and speed.
* `cozmo_turns(angle: float)`: Makes Cozmo turn by a specified angle.
* `cozmo_lifts(height: float)`: Raises or lowers Cozmo's lift to a specific height.
* `cozmo_goes_to_object(object_id: int, distance: float)`: Makes Cozmo drive to a specific object (using its ID) and stop at a certain distance.

**Object Interaction:**

* `cozmo_searches_light_cube()`: Makes Cozmo search for a light cube and returns its ID or a message indicating no cube was found.
* `cozmo_pops_a_wheelie(object_id: int)`: Makes Cozmo attempt a wheelie using a light cube (specified by ID).
* `cozmo_picksup_object(object_id: int)`: Makes Cozmo pick up a light cube (specified by ID).
* `cozmo_places_object(object_id: int)`: Makes Cozmo place the carried object on a light cube (specified by ID).
* `cozmo_docks_with_cube(object_id: int)`: Makes Cozmo dock with a light cube (specified by ID).
* `cozmo_rolls_cube(object_id: int)`: Makes Cozmo roll a light cube (specified by ID).
* `cozmo_is_carrying_object()`: Checks if Cozmo is currently carrying an object, returning a confirmation or denial message.

**Animations and Sounds:**

* `cozmo_plays_animation(animation_name: str)`: Makes Cozmo play a specified animation.
* `cozmo_plays_song(song_notes: str)`: Makes Cozmo play a song with provided notes.

**Behaviors:**

* `cozmo_starts_behavior(behavior_name: str)`: Starts a specific Cozmo behavior
* `cozmo_stops_behavior(behavior_name: str)`: Stops a specific Cozmo behavior.
* `cozmo_starts_freeplay()`: Starts Cozmo's freeplay mode.
* `cozmo_stops_freeplay()`: Stops Cozmo's freeplay mode.

**Information and Status:**

* `cozmo_battery_level()`: Returns Cozmo's current battery level.
* `cozmo_is_charging()`: Checks if Cozmo is currently charging, returning a confirmation or denial message.
* `cozmo_is_localized()`: Checks if Cozmo knows its location, returning a confirmation or denial message.
* `cozmo_sees()`: Makes Cozmo take a picture and describe what it sees (success/failure message, description provided elsewhere).

**Lights and Volume:**

* `cozmo_set_backpack_lights(R: int, G: int, B: int)`: Sets the color of Cozmo's backpack lights (or turns them off).
* `cozmo_set_headlight(on_off: str)`: Turns Cozmo's headlight on or off.
* `cozmo_set_volume(volume: float)`: Sets Cozmo's speaker volume.


# Requirements:
 - An Android or IOS device with the Cozmo App connected via USB to your PC or Mac;
 - A [Gemini](https://ai.google.dev/) developer key;
 - A [GCP](https://cloud.google.com/) project with billing enabled for speech-text (you can stay in the free tier);
 - A [Picovoice](https://picovoice.ai/) key and a [Porcupine](https://picovoice.ai/platform/porcupine/) keyword file for the "Hey, Cozmo" keyword detection;
 - [ADB](https://developer.android.com/tools/releases/platform-tools) (Android Platform Tools) if using an Android device.

# Setting up and running:
 - Run `./setup/install_packs.sh` to install the required packages and create
   the virtual environment.
 - Get a Gemini dev key: https://ai.google.dev/
 - Get your Picovoice keys and keyword file here: https://picovoice.ai/
 - Install gcloud CLI: https://cloud.google.com/sdk/docs/install
 - Run `gcloud init` to set it up and follow the instructions.
 - Run `gcloud auth application-default login` to get credentials.
 - Edit the `keys/env_keys.sh` with your keys and Picovoice keyword file:
 ```
 export PICOVOICE_KEYWORD_PATH=./keys/[enter your hey-cozmo*.ppn here]
 export PICOVOICE_ACCESS_KEY=[enter your Picovoice key here]
 export GOOGLE_API_KEY=[enter your google API key here]
 ```
 - [If using an Android Device] Install [ADB](https://developer.android.com/tools/releases/platform-tools) and edit `/setup/set_env.sh` to point the variable ADB_PATH to the platform-tools directory on the ADB installation path.
 - Finally, run `./start_cozmini.sh` and start interacting with Cozmini by voice or on the web browser UI at http://127.0.0.1:5000.

# Limitations
- At some point, the `user_data/conversation_history.txt` file will become too large and won't fit into the Gemini context window. This will result in Error 500. Delete the contents of this file (or a portion of it) to fix the error. Cozmini will forget the things you deleted.

# Disclaimer

- Note that text, audio, and images captured will be sent to Gemini, so look at their [terms of service](https://ai.google.dev/terms)
