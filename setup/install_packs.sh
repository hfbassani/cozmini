# MacOS:
brew install ffmpeg
brew install portaudio

# debian based:
sudo apt install python-dev
sudo apt install portaudio19-dev

# Create venv (requires python3.10 or later):
python3.10 -m venv ./venv_cozmini
source ./venv_cozmini/bin/activate
pip install -r requirements.txt