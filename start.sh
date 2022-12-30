#!/bin/bash
export FLASK_APP=/usr/src/longclick/longclick.py
export FLASH_DEBUG=0
flask run --host=0.0.0.0 --port=8080
