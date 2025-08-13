#!/bin/bash

# 查找包含 "action.py" 的正在运行的进程并终止
pid=$(pgrep -f "action.py")
if [ ! -z "$pid" ]; then
    echo "Killing process with PID: $pid"
    kill -9 $pid
else
    echo "No running process found with 'action.py'"
fi

# 在后台重新启动 action.py
echo "Restarting action.py..."
nohup python action/action.py > action.log 2>&1 &