#!/bin/bash
deactivate
export PYTHONPATH=$(pwd):$(pwd)/www:$(pwd)/easyocr:$PYTHONPATH
source .venv/bin/activate
source email_settings.sh
