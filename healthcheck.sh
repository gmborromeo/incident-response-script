#!/bin/bash

# Quick health summary — exit 0 = healthy, exit 1 = issues found

ISSUES=0

CPU=$(./venv/bin/python3 -c "import psutil; print(int(psutil.cpu_percent(interval=1)))")
MEM=$(./venv/bin/python3 -c "import psutil; print(int(psutil.virtual_memory().percent))")
DISK=$(./venv/bin/python3 -c "import psutil; print(int(psutil.disk_usage('/').percent))")

echo "=== System Health Check ==="
echo "CPU:      ${CPU}%"
echo "Memory:   ${MEM}%"
echo "Disk:     ${DISK}%"

[ "$CPU" -gt 80 ] && echo "WARN: CPU above threshold" && ISSUES=1
[ "$MEM" -gt 85 ] && echo "WARN: Memory above threshold" && ISSUES=1
[ "$DISK" -gt 90 ] && echo "WARN: Disk above threshold" && ISSUES=1

if [ $ISSUES -eq 0 ]; then
  echo "Status: Healthy"
else
  echo "Status: Degraded"
fi

exit $ISSUES