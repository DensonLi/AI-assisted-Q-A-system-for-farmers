#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "══════════════════════════════════════════════"
echo "  农户种植技巧AI辅助问答系统 — 开发环境初始化"
echo "══════════════════════════════════════════════"
echo ""

# ── 1. Python 虚拟环境 ────────────────────────────
echo "▶ 创建 Python 虚拟环境（Python 3.12）..."
PYTHON=$(pyenv which python3.12 2>/dev/null || which python3.12)
if [ -z "$PYTHON" ]; then
  echo "  ✗ 未找到 Python 3.12，请先执行：pyenv install 3.12.11"
  exit 1
fi

if [ ! -d "backend/.venv" ]; then
  "$PYTHON" -m venv backend/.venv
  echo "  ✓ 虚拟环境已创建：backend/.venv"
else
  echo "  ✓ 虚拟环境已存在，跳过创建"
fi

# ── 2. 安装后端依赖 ──────────────────────────────
echo ""
echo "▶ 安装后端 Python 依赖..."
backend/.venv/bin/pip install --upgrade pip -q
backend/.venv/bin/pip install -r backend/requirements.txt -q
echo "  ✓ 后端依赖安装完成"

# ── 3. 安装前端依赖 ──────────────────────────────
echo ""
echo "▶ 安装前端 Node 依赖..."
cd frontend && npm install --silent && cd ..
echo "  ✓ 前端依赖安装完成"

# ── 4. 复制环境变量 ──────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.local .env
  echo ""
  echo "  ✓ 已从 .env.local 生成 .env（后端读取此文件）"
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  初始化完成！运行以下命令启动开发环境："
echo "  ./scripts/start-dev.sh"
echo "══════════════════════════════════════════════"
echo ""
