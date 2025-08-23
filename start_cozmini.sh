# /bin/sh

if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Activating virtual environment"
    source venv_cozmini/bin/activate
fi
source setup/set_env.sh
source keys/env_keys.sh 
python3 cozmini.py