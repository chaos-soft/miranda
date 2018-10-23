#!/bin/bash
cd /miranda
pip install --no-cache-dir --upgrade -r requirements.txt
python app/core.py
