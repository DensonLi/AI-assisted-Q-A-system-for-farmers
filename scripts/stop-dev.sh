#!/bin/bash

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "▶ 停止 Docker 基础设施..."
docker compose -f docker-compose.infra.yml down
echo "  ✓ PostgreSQL + Redis 已停止"

echo "▶ 停止本地进程..."
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "  ✓ 后端已停止" || echo "  - 后端未在运行"
pkill -f "vite" 2>/dev/null && echo "  ✓ 前端已停止" || echo "  - 前端未在运行"

echo ""
echo "  ✓ 开发环境已全部停止"
