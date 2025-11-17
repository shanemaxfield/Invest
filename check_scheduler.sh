#!/bin/bash
# Check if scheduler is running

cd "$(dirname "$0")"

if [ -f logs/scheduler.pid ]; then
    PID=$(cat logs/scheduler.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "✓ Scheduler is RUNNING (PID: $PID)"
        echo ""
        echo "Recent logs:"
        tail -n 10 logs/scheduler.log 2>/dev/null || echo "  (no logs yet)"
    else
        echo "✗ Scheduler is NOT running (PID file exists but process not found)"
        rm logs/scheduler.pid
    fi
else
    echo "✗ Scheduler is NOT running (no PID file)"
fi

