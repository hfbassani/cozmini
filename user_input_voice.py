import pvporcupine
from google.cloud import speech, texttospeech
import pyaudio
import struct
import os

class UserInput:

    def __init__(self) -> None:
        # Loading the access key and keyword path from environment variables
        self.access_key = os.environ.get('PICOVOICE_ACCESS_KEY')
        self.keyword_path = os.environ.get('PICOVOICE_KEYWORD_PATH')

        # Creating a Porcupine instance
        self.porcupine = pvporcupine.create(access_key=self.access_key, keyword_paths=[self.keyword_path])

        # Initializing Google Cloud Speech-to-Text client
        self.speech_client = speech.SpeechClient()

        # Initializing PyAudio
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

        # Initializing Google Cloud TTS API client
        self.tts_client = texttospeech.TextToSpeechClient()

    def _record_audio(self, stream, rate, frame_length, record_seconds):
        print("Recording...")
        frames = []
        for _ in range(0, int(rate / frame_length * record_seconds)):
            try:
                data = stream.read(frame_length, exception_on_overflow=False) 
                frames.append(data)
            except IOError as e:
                if e.errno == pyaudio.paInputOverflowed:
                    # Handling overflow
                    continue  # Proceed to the next frame
        print("Recording stopped.")
        return b''.join(frames)

    def _transcribe_audio(self, client, audio_data):
        """Function to convert speech to text using Google Speech-to-Text."""
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            # language_code="ja-JP",
        )
        response = client.recognize(config=config, audio=audio)
        # Return text only if there are results
        if response.results:
            for result in response.results:
                print("Transcribed text: {}".format(result.alternatives[0].transcript))
            return response.results[0].alternatives[0].transcript
        else:
            print("No transcription results.")
            return None

    def capture_user_input(self):

        # Recording voice input and converting it to text
        audio_data = self._record_audio(self.audio_stream, self.porcupine.sample_rate, self.porcupine.frame_length, 5)
        user_input = self._transcribe_audio(self.speech_client, audio_data)

        return user_input

    def wait_keyword(self):
        print("Waiting for keyword")
        while True:
            # Reading audio data from PyAudio stream
            pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)

            # Detecting wake word using Porcupine
            keyword_index = self.porcupine.process(pcm)
            if keyword_index >= 0:  # If wake word is detected
                print("Wake word detected!")
                return "Hey, Cozmo. " +  self.capture_user_input()

    def __del__(self):
        self.audio_stream.close()
        self.pa.terminate()
        self.porcupine.delete()