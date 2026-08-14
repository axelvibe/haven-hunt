#!/usr/bin/env bash
# Runs both the web API and the Telegram bot in one container.
set -e

echo "Starting HavenHunt web API on :8000 ..."
uvicorn product.web.api:app --host 0.0.0.0 --port 8000 &
API_PID=$!

echo "Starting HavenHunt Telegram bot ..."
python run_bot.py &
BOT_PID=$!

trap "kill $API_PID $BOT_PID 2>/dev/null" EXIT
wait -n $API_PID $BOT_PID
