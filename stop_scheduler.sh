#!/bin/bash
# Stop the trading scheduler

cd "$(dirname "$0")"

if [ -f logs/scheduler.pid ]; then
    PID=$(cat logs/scheduler.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✓ Scheduler stopped (PID: $PID)"
        rm logs/scheduler.pid
    else
        echo "Scheduler process not found (may have already stopped)"
        rm logs/scheduler.pid
    fi
else
    echo "No scheduler PID file found"
    echo "Trying to find and kill any running scheduler processes..."
    pkill -f "python main.py --mode schedule"
    echo "Done"
fi

