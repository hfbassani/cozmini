#!/usr/bin/env bash

if [ "$(uname)" == "Darwin" ]; then
  # MacOS:
  brew install ffmpeg
  brew install portaudio
  # Create venv (requires python3.10 or later):
  python3 -m venv ./venv_cozmini
  source ./venv_cozmini/bin/activate
  pip3 install -r requirements.txt
elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
  # debian based only:
  sudo apt install python3.10-dev
  sudo apt install portaudio19-dev
  # Create venv (requires python3.10 or later):
  python3.10 -m venv ./venv_cozmini
  source ./venv_cozmini/bin/activate
  pip install -r requirements.txt
else
  echo "Sorry, this operating system is not supported yet." 
fi
