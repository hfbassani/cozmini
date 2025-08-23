from pocketsphinx import Decoder, get_model_path, Config
from google.cloud import speech, texttospeech
import pyaudio
import struct
import os
from event_messages import event_log, EventType
import threading
import time

def init_voice_input():
    # Loading the access key and keyword path from environment variables
    return VoiceInput()

class VoiceInput:

    RECORD_TIME = 10

    def __init__(self):
        self.audio_stream = None
        self.pa = None
        self.rate = 16000
        self.frame_length = 1024
        self.wake_word = "hey cosmo"

        # --- PocketSphinx Configuration ---
        
        # Get paths in a portable way
        model_path = get_model_path()
        hmm_path = os.path.join(model_path, 'en-us', 'en-us')
        dict_path = os.path.join(model_path, 'en-us', 'cmudict-en-us.dict')

        # Create a configuration object for keyword spotting.
        # This replaces Decoder.default_config() and avoids the conflict.
        config = Config(
            hmm = hmm_path,
            dict = dict_path,
            keyphrase = self.wake_word,
            kws_threshold = 1e-20,
            logfn = os.devnull  # Suppress verbose logging
        )

        os.environ['KMP_WARNINGS'] = 'off'

        # Initialize the decoder with the new configuration
        self.decoder = Decoder(config)
        self.decoder.start_utt()
        print("✅ PocketSphinx decoder initialized successfully for keyword spotting.")


        # --- Initializing Google Cloud Speech-to-Text client --- 
        self.speech_client = speech.SpeechClient()

        # Initializing PyAudio
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            format=pyaudio.paInt16,
            frames_per_buffer=self.frame_length,
            rate=self.rate,
            channels=1,
            input=True,
        )

        self.trigger_listen = False
        self.user_input = ''

        # Initializing Google Cloud TTS API client
        self.tts_client = texttospeech.TextToSpeechClient()

    def _record_audio(self, stream, rate, frame_length, record_seconds):
        event_log.message(EventType.VOICE_EVENT_LISTENING, "Listening...")
        frames = []
        for _ in range(0, int(rate / frame_length * record_seconds)):
            try:
                data = stream.read(frame_length, exception_on_overflow=False) 
                frames.append(data)
            except IOError as e:
                if e.errno == pyaudio.paInputOverflowed:
                    # Handling overflow
                    continue  # Proceed to the next frame
        event_log.message(EventType.VOICE_EVENT_FINISHED, "Stopped listening")
        return b''.join(frames)

    def _transcribe_audio(self, client, audio_data):
        """Function to convert speech to text using Google Speech-to-Text."""
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            # language_code="pt-BR",
        )
        response = client.recognize(config=config, audio=audio)

        # Return text only if there are results
        if response.results:
            return response.results[0].alternatives[0].transcript
        else:
            return ''

    def wait_input_finish(self):
        while self.trigger_listen:
                time.sleep(0.1)

    def capture_user_input(self, block=False):
        self.trigger_listen = True

        if block:
            self.wait_input_finish()            
        return self.user_input
   

    def _listen(self):

        # Recording voice input and converting it to text
        audio_data = self._record_audio(self.audio_stream, self.rate, self.frame_length, VoiceInput.RECORD_TIME)
        user_input = self._transcribe_audio(self.speech_client, audio_data)

        return user_input

    def start_loop(self):
        threading.Thread(target=self.wait_keyword_loop, daemon=True).start()

    def detect_wake_word(self, pcm):
        # Process the raw audio data
        self.decoder.process_raw(pcm, False, False)
        
        # Check if the wake word was hypothesized
        if self.decoder.hyp() and self.decoder.hyp().hypstr == self.wake_word:
            # Wake word detected
            print("Wake word detected!")
            
            # End the current utterance and start a new one for the next listen cycle
            self.decoder.end_utt()
            self.decoder.start_utt()
            
            return True
        return False

    def wait_keyword_loop(self):
        while True:
            # Reading raw audio data from PyAudio stream
            pcm = self.audio_stream.read(self.frame_length, exception_on_overflow=False)
            
            if self.detect_wake_word(pcm):
                self.trigger_listen = True
                self.user_input = self._listen()
                if self.user_input:
                    # Note: You might want to remove the hardcoded "Hey, Cozmo" here
                    # since it was already detected as the wake word.
                    self.user_input = "Hey, Cozmo. " + self.user_input
                    event_log.message(EventType.USER_MESSAGE, self.user_input)
                self.trigger_listen = False

            # Otherwise, if listen was triggered externally
            elif self.trigger_listen:
                self.user_input = self._listen()
                if self.user_input:
                    event_log.message(EventType.USER_MESSAGE, self.user_input)
                self.trigger_listen = False


    def __del__(self):
        if self.audio_stream:
            self.audio_stream.close()
        if self.pa:
            self.pa.terminate()
