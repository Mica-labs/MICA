#!/usr/bin/env bash
touch server.log
nohup python -u server.py > server.log 2>&1 &
tail -f server.log