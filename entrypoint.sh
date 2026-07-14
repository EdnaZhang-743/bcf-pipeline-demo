#!/bin/sh
# 容器启动时：如果数据库还不存在，先跑一遍pipeline；然后启动API服务。
set -e

if [ ! -f "data/health.db" ]; then
    echo "[entrypoint] no database found, running pipeline..."
    python fetch.py
    python clean.py
    python store.py
else
    echo "[entrypoint] database already exists, skipping pipeline"
fi

echo "[entrypoint] starting Flask app..."
exec python app.py