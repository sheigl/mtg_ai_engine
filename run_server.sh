#!/bin/bash
cd /home/sheigl/code/mtg_ai_engine
exec .venv/bin/python -m uvicorn mtg_engine.api.main:app --port 8085 --host 0.0.0.0