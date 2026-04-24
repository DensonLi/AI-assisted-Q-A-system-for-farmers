#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# ── 检查虚拟环境 ─────────────────────────────────
if [ ! -f "backend/.venv/bin/activate" ]; then
  echo "✗ 虚拟环境未初始化，请先运行：./scripts/setup-dev.sh"
  exit 1
fi

# ── 清理函数（Ctrl+C 退出时停止所有子进程）────────
PIDS=()
cleanup() {
  echo ""
  echo "▶ 正在停止所有服务..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  docker compose -f docker-compose.infra.yml down
  echo "  ✓ 全部服务已停止"
  exit 0
}
trap cleanup INT TERM

echo ""
echo "══════════════════════════════════════════════"
echo "  农户种植技巧AI辅助问答系统 — 开发环境启动"
echo "══════════════════════════════════════════════"
echo ""

# ── 1. 启动数据库基础设施 ─────────────────────────
echo "▶ 启动 PostgreSQL + Redis（Docker）..."
docker compose -f docker-compose.infra.yml up -d
echo "  ✓ 等待数据库就绪..."
sleep 3

# ── 2. 数据库迁移 ────────────────────────────────
echo ""
echo "▶ 执行数据库迁移..."
cd backend
source .venv/bin/activate
export $(grep -v '^#' ../.env | xargs) 2>/dev/null || true
alembic upgrade head
deactivate
cd ..
echo "  ✓ 数据库迁移完成"

# ── 3. 启动后端（热重载）────────────────────────
echo ""
echo "▶ 启动后端 API（http://localhost:8000）..."
(
  cd backend
  source .venv/bin/activate
  export $(grep -v '^#' ../.env | xargs) 2>/dev/null || true
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &
PIDS+=($!)

sleep 2

# ── 4. 启动前端（热重载）────────────────────────
echo ""
echo "▶ 启动前端（http://localhost:3000）..."
(cd frontend && npm run dev) &
PIDS+=($!)

echo ""
echo "══════════════════════════════════════════════"
echo "  ✓ 开发环境已启动"
echo ""
echo "  前端：http://localhost:3000"
echo "  后端 API：http://localhost:8000"
echo "  API 文档：http://localhost:8000/docs"
echo ""
echo "  默认管理员：admin / Admin@123456"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "══════════════════════════════════════════════"
echo ""

wait
