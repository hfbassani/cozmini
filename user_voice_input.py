from pocketsphinx import Decoder, get_model_path, Config
from google.cloud import speech, texttospeech
import pyaudio
import struct
import os
from event_messages import event_log, EventType
import threading
import time
import numpy as np
import torch
import torchaudio
from typing import Optional, Tuple
import user_profiles

def init_voice_input():
    # Loading the access key and keyword path from environment variables
    return VoiceInput()

class VoiceInput:

    RECORD_TIME = 5

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

        # --- Initialize SpeechBrain speaker recognition model ---
        try:
            from speechbrain.pretrained import EncoderClassifier
            self.speaker_model = EncoderClassifier.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="user_data/models/speaker_recognition"
            )
            print("✅ SpeechBrain speaker recognition model loaded successfully.")
            self.speaker_recognition_enabled = True
        except Exception as e:
            print(f"⚠️  Speaker recognition disabled: {e}")
            self.speaker_model = None
            self.speaker_recognition_enabled = False

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
        self.current_speaker_embedding = None
        self.profile_manager = user_profiles.get_profile_manager()

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
    
    def _extract_speaker_embedding(self, audio_data: bytes) -> Optional[np.ndarray]:
        """Extract speaker embedding from raw audio data."""
        if not self.speaker_recognition_enabled or self.speaker_model is None:
            return None
        
        try:
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Convert to tensor and ensure correct shape
            audio_tensor = torch.from_numpy(audio_np).unsqueeze(0)
            
            # Extract embedding
            with torch.no_grad():
                embedding = self.speaker_model.encode_batch(audio_tensor)
                embedding_np = embedding.squeeze().cpu().numpy()
            
            return embedding_np
        except Exception as e:
            print(f"Error extracting speaker embedding: {e}")
            return None
    
    def _identify_speaker(self, audio_embedding: Optional[np.ndarray]) -> Optional[str]:
        """Identify speaker from embedding."""
        if audio_embedding is None:
            return None
        
        # Match against known profiles
        matched_profile = self.profile_manager.match_by_voice(audio_embedding)
        if matched_profile:
            return matched_profile.name
        return None

    def wait_input_finish(self):
        while self.trigger_listen:
                time.sleep(0.1)

    def capture_user_input(self, block=False):
        self.trigger_listen = True

        if block:
            self.wait_input_finish()            
        return self.user_input
   

    def _listen(self) -> Tuple[str, Optional[str]]:
        """Listen and return both transcription and identified speaker."""
        # Recording voice input and converting it to text
        audio_data = self._record_audio(self.audio_stream, self.rate, self.frame_length, VoiceInput.RECORD_TIME)
        user_input = self._transcribe_audio(self.speech_client, audio_data)
        
        # Extract speaker embedding and identify
        speaker_embedding = self._extract_speaker_embedding(audio_data)
        self.current_speaker_embedding = speaker_embedding
        speaker_name = self._identify_speaker(speaker_embedding)
        
        return user_input, speaker_name
    
    def enroll_voice(self, user_id: str, name: str, num_samples: int = 3) -> bool:
        """Enroll a new user's voice by capturing multiple samples."""
        if not self.speaker_recognition_enabled:
            print("Speaker recognition is not enabled")
            return False
        
        print(f"Enrolling voice for {name}. Please speak {num_samples} times when prompted.")
        embeddings = []
        
        for i in range(num_samples):
            print(f"Sample {i+1}/{num_samples}: Please speak now...")
            audio_data = self._record_audio(self.audio_stream, self.rate, self.frame_length, 3)
            embedding = self._extract_speaker_embedding(audio_data)
            
            if embedding is not None:
                embeddings.append(embedding)
            else:
                print(f"Failed to extract embedding for sample {i+1}")
        
        if len(embeddings) < 2:
            print("Not enough valid samples for enrollment")
            return False
        
        # Average the embeddings
        avg_embedding = np.mean(embeddings, axis=0)
        
        # Store in user profile
        success = self.profile_manager.update_profile(
            user_id,
            voice_embedding=avg_embedding.tolist()
        )
        
        if success:
            print(f"✅ Voice enrollment successful for {name}")
        else:
            print(f"❌ Failed to save voice embedding for {name}")
        
        return success

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
                user_input, speaker_name = self._listen()
                if user_input:
                    # Add speaker identification to the message itself
                    speaker_prefix = f"{speaker_name}: " if speaker_name else "[unrecognized]: "
                    self.user_input = speaker_prefix + "Hey, Cozmo. " + user_input
                    event_log.message(EventType.USER_MESSAGE, self.user_input)
                self.trigger_listen = False

            # Otherwise, if listen was triggered externally
            elif self.trigger_listen:
                user_input, speaker_name = self._listen()
                if user_input:
                    # Add speaker identification to the message itself
                    speaker_prefix = f"{speaker_name}: " if speaker_name else "[unrecognized]: "
                    event_log.message(EventType.USER_MESSAGE, speaker_prefix + user_input)
                self.trigger_listen = False


    def __del__(self):
        if self.audio_stream:
            self.audio_stream.close()
        if self.pa:
            self.pa.terminate()
