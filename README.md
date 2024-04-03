# Cozmini
The [Gemini](https://gemini.google.com/) language model powers Cozmo's mind!

Setting up:

 - Create a `env_keys.sh` file in the `keys` directory, with the content below:

 ```
 export PICOVOICE_KEYWORD_PATH=./keys/[enter your hey-cozmo*.ppn here]
 export PICOVOICE_ACCESS_KEY=[enter your Picovoice key here]
 export GOOGLE_API_KEY=[enter your google API key here]
 ```

 - Get google.ai dev keys: https://ai.google.dev/
 - Get your picovoice keys and keyword file here: https://picovoice.ai/
 - Install gcloud CLI: https://cloud.google.com/sdk/docs/install
 - Run `gcloud init` to set it up and follow the instructions
 - Run `gcloud auth application-default login` to get credentials
