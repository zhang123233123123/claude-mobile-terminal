#!/bin/bash
set -e
cd "$(dirname "$0")"

# Load .env if present
[ -f .env ] && export $(grep -v '^#' .env | xargs)

if [ -z "$AUTH_PASS" ]; then
  echo "❌ 请先设置 AUTH_PASS，例如在 .env 文件里写: AUTH_PASS=yourpassword"
  exit 1
fi

PORT=$(python3 -c "import json; print(json.load(open('config.json')).get('port', 8080))" 2>/dev/null || echo 8080)

echo "▶ 启动服务 (端口 $PORT)..."
uvicorn server:app --host 0.0.0.0 --port "$PORT" --reload &
SERVER_PID=$!
trap "echo '⏹ 关闭服务...'; kill $SERVER_PID 2>/dev/null; exit" EXIT INT TERM

sleep 1
echo "▶ 启动 Cloudflare Tunnel..."
cloudflared tunnel --url "http://localhost:$PORT"
