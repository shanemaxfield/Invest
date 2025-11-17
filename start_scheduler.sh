#!/bin/bash
# Start the trading scheduler in the background

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Start scheduler in background with nohup (survives terminal close)
nohup python main.py --mode schedule > logs/scheduler.log 2>&1 &

# Get the process ID
PID=$!

# Save PID to file for easy stopping
echo $PID > logs/scheduler.pid

echo "✓ Trading scheduler started in background"
echo "  PID: $PID"
echo "  Logs: logs/scheduler.log"
echo "  To stop: ./stop_scheduler.sh"
echo ""
echo "Current status:"
tail -n 20 logs/scheduler.log 2>/dev/null || echo "  (logs will appear after first run)"

