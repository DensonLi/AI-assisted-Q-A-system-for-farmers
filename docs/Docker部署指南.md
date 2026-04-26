# 农户种植技巧AI辅助问答系统 — Docker 部署指南

> 适用环境：Ubuntu 20.04 / 22.04 / 24.04 LTS（amd64）  
> 部署方式：Docker + Docker Compose，无需本地编译

---

## 目录

1. [服务器要求](#1-服务器要求)
2. [安装 Docker](#2-安装-docker)
3. [获取代码](#3-获取代码)
4. [配置环境变量](#4-配置环境变量)
5. [启动服务](#5-启动服务)
6. [验证部署](#6-验证部署)
7. [常用运维命令](#7-常用运维命令)
8. [数据备份与恢复](#8-数据备份与恢复)
9. [升级更新](#9-升级更新)
10. [配置 HTTPS（可选）](#10-配置-https可选)
11. [故障排查](#11-故障排查)

---

## 1. 服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 20 GB | 40 GB SSD |
| 系统 | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| 网络 | 能访问外网（调用 LLM API） | — |

**开放端口：**
- `80` — HTTP 访问（前端 + API 反向代理）
- `443` — HTTPS（可选，配置 SSL 后使用）
- `22` — SSH 管理

---

## 2. 安装 Docker

> 如果服务器已安装 Docker，跳过此步骤。

```bash
# 一键安装 Docker（官方脚本）
curl -fsSL https://get.docker.com | sh

# 将当前用户加入 docker 组（避免每次 sudo）
sudo usermod -aG docker $USER

# 重新加载权限（或重新登录 SSH）
newgrp docker

# 验证安装
docker version
docker compose version
```

> **国内服务器**如果 Docker Hub 拉取慢，可配置镜像加速：
> ```bash
> sudo tee /etc/docker/daemon.json <<'EOF'
> {
>   "registry-mirrors": [
>     "https://docker.1ms.run",
>     "https://dockerpull.org"
>   ]
> }
> EOF
> sudo systemctl restart docker
> ```

---

## 3. 获取代码

### 方式一：Git 克隆（推荐）

```bash
# 克隆仓库（替换为您的实际地址）
git clone https://github.com/yourname/farming-qa-system.git
cd farming-qa-system
```

### 方式二：上传压缩包

```bash
# 在本地打包（Mac/Linux）
zip -r farming-qa.zip . \
  --exclude "*/node_modules/*" \
  --exclude "*/.venv/*" \
  --exclude "*/__pycache__/*" \
  --exclude "*/.git/*"

# 上传到服务器
scp farming-qa.zip user@your-server-ip:/opt/

# 在服务器上解压
ssh user@your-server-ip
cd /opt && unzip farming-qa.zip -d farming-qa-system
cd farming-qa-system
```

---

## 4. 配置环境变量

这是部署最关键的一步。复制模板文件并按实际情况填写：

```bash
cp .env.example .env
nano .env        # 或 vim .env
```

### 完整配置说明

```bash
# ════════════════════════════════════════════
# 数据库配置（PostgreSQL）
# ════════════════════════════════════════════
POSTGRES_USER=postgres
# 设置一个强密码，只含字母和数字，避免特殊字符
POSTGRES_PASSWORD=MyStr0ngPass2024

# 数据库连接字符串（将 MyStr0ngPass2024 替换为上面的密码）
DATABASE_URL=postgresql+psycopg2://postgres:MyStr0ngPass2024@postgres:5432/farming_qa
ASYNC_DATABASE_URL=postgresql+asyncpg://postgres:MyStr0ngPass2024@postgres:5432/farming_qa

# ════════════════════════════════════════════
# Redis 缓存（保持默认即可）
# ════════════════════════════════════════════
REDIS_URL=redis://redis:6379/0

# ════════════════════════════════════════════
# JWT 密钥（必须修改！）
# ════════════════════════════════════════════
# 生成随机密钥：openssl rand -hex 32
SECRET_KEY=请替换为一个随机字符串_至少32位

# ════════════════════════════════════════════
# 知识库 API（可选，不配置则不使用 RAG 增强）
# ════════════════════════════════════════════
KNOWLEDGE_API_BASE_URL=https://center.ziiku.cn/api/aibot/openapi/conversation/chat
KNOWLEDGE_API_KEY=           # 留空则跳过知识库检索
KNOWLEDGE_BOT_ID=            # 留空则跳过知识库检索

# ════════════════════════════════════════════
# LLM 大模型 API（必须配置！）
# 支持 DeepSeek / OpenAI / 其他 OpenAI 兼容服务
# ════════════════════════════════════════════

# ── DeepSeek（推荐，性价比高）──
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# ── 或者使用 OpenAI ──
# LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
# LLM_BASE_URL=                           # 留空，使用官方 OpenAI 地址
# LLM_MODEL=gpt-4o-mini

LLM_MAX_TOKENS=1500
LLM_TEMPERATURE=0.3
LLM_HISTORY_TURNS=5
LLM_TIMEOUT_SEC=60

# ════════════════════════════════════════════
# 初始管理员账号（首次启动自动创建）
# ════════════════════════════════════════════
FIRST_ADMIN_USERNAME=admin
FIRST_ADMIN_PASSWORD=Admin@123456   # 建议修改为更强的密码
FIRST_ADMIN_EMAIL=admin@example.com
```

### 快速生成安全密钥

```bash
# 生成 JWT SECRET_KEY
openssl rand -hex 32

# 生成数据库密码（纯字母数字，避免特殊字符引起 URL 解析问题）
openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24
```

> **注意**：`.env` 文件含有敏感信息，确保权限正确：
> ```bash
> chmod 600 .env
> ```

---

## 5. 启动服务

```bash
# 在项目根目录执行（首次启动会拉取镜像并构建，约需 3~8 分钟）
docker compose up -d

# 查看启动日志
docker compose logs -f
```

首次启动时，系统会自动完成：
- 拉取 PostgreSQL 16、Redis 7 官方镜像
- 构建后端（安装 Python 依赖）和前端（npm 构建 → Nginx）
- 执行数据库迁移（`alembic upgrade head`）
- 创建初始管理员账号

### 服务启动顺序

```
PostgreSQL → Redis → Backend（含迁移） → Frontend（Nginx）
```

等待所有服务 `healthy` 后即可访问：

```bash
# 检查所有容器状态
docker compose ps
```

正常输出：
```
NAME                        STATUS          PORTS
farming-qa-postgres-1       Up (healthy)
farming-qa-redis-1          Up (healthy)
farming-qa-backend-1        Up              8000/tcp
farming-qa-frontend-1       Up              0.0.0.0:80->80/tcp
```

---

## 6. 验证部署

```bash
# 1. 测试后端 API 是否正常
curl http://localhost/api/v1/health

# 期望输出：
# {"status":"ok"}
```

```bash
# 2. 打开浏览器访问
# http://your-server-ip

# 3. 使用初始管理员账号登录
# 用户名：admin
# 密码：.env 中 FIRST_ADMIN_PASSWORD 的值
```

---

## 7. 常用运维命令

```bash
# ── 查看服务状态 ──────────────────────────────────────
docker compose ps

# ── 查看实时日志 ──────────────────────────────────────
docker compose logs -f              # 所有服务
docker compose logs -f backend      # 仅后端
docker compose logs -f frontend     # 仅前端（Nginx）

# ── 重启服务 ──────────────────────────────────────────
docker compose restart backend      # 重启后端
docker compose restart              # 重启所有

# ── 停止服务 ──────────────────────────────────────────
docker compose stop                 # 停止（保留容器和数据）
docker compose down                 # 停止并删除容器（数据卷保留）

# ── 进入容器调试 ──────────────────────────────────────
docker compose exec backend bash    # 进入后端容器
docker compose exec postgres psql -U postgres farming_qa  # 进入数据库

# ── 手动执行数据库迁移 ────────────────────────────────
docker compose exec backend alembic upgrade head

# ── 查看磁盘占用 ──────────────────────────────────────
docker system df
```

---

## 8. 数据备份与恢复

### 备份数据库

```bash
# 备份到当前目录（文件名含时间戳）
docker compose exec postgres pg_dump \
  -U postgres farming_qa \
  > backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩备份（节省空间）
docker compose exec postgres pg_dump \
  -U postgres farming_qa \
  | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 恢复数据库

```bash
# 从 SQL 文件恢复
cat backup_20241201_120000.sql | \
  docker compose exec -T postgres psql -U postgres farming_qa

# 从压缩文件恢复
gunzip -c backup_20241201_120000.sql.gz | \
  docker compose exec -T postgres psql -U postgres farming_qa
```

### 定时自动备份（推荐）

```bash
# 创建备份脚本
sudo tee /opt/backup-farming-qa.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups/farming-qa"
mkdir -p $BACKUP_DIR
cd /opt/farming-qa-system

docker compose exec -T postgres pg_dump \
  -U postgres farming_qa \
  | gzip > $BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz

# 只保留最近 7 天的备份
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +7 -delete

echo "备份完成：$(ls -lh $BACKUP_DIR | tail -1)"
EOF

chmod +x /opt/backup-farming-qa.sh

# 设置每天凌晨 2 点自动备份
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/backup-farming-qa.sh >> /var/log/farming-qa-backup.log 2>&1") | crontab -
```

---

## 9. 升级更新

当代码有更新时，按以下步骤操作：

```bash
cd /opt/farming-qa-system

# 1. 拉取最新代码（如使用 Git）
git pull

# 2. 重新构建并启动（--build 强制重新构建镜像）
docker compose up -d --build

# 如果有数据库结构变更，迁移会在 backend 启动时自动执行
# 也可手动触发：
docker compose exec backend alembic upgrade head
```

> **数据安全**：`--build` 只重新构建应用镜像，数据卷（`postgres_data`、`redis_data`）不受影响，数据不会丢失。

---

## 10. 配置 HTTPS（可选）

如果服务器有域名，建议配置 HTTPS。推荐使用 Caddy 作为反向代理（自动申请 Let's Encrypt 证书）：

```bash
# 安装 Caddy
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

修改 Docker Compose，让 frontend 只监听本地端口：

```yaml
# docker-compose.yml（修改 frontend 的 ports）
frontend:
  ports:
    - "127.0.0.1:8080:80"    # 改为只监听本地
```

创建 Caddy 配置：

```bash
sudo tee /etc/caddy/Caddyfile <<'EOF'
your-domain.com {
    reverse_proxy localhost:8080
}
EOF

sudo systemctl reload caddy
```

替换 `your-domain.com` 为您的实际域名，Caddy 会自动申请并续期 SSL 证书。

---

## 11. 故障排查

### 问题：启动后无法访问

```bash
# 检查容器是否都在运行
docker compose ps

# 检查 80 端口是否被占用
sudo ss -tlnp | grep :80

# 检查防火墙
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### 问题：后端一直重启（Restarting）

```bash
# 查看后端日志找原因
docker compose logs backend

# 常见原因：
# 1. .env 中数据库密码含特殊字符，导致 URL 解析失败
#    解决：使用纯字母数字密码
#
# 2. LLM_API_KEY 未配置（不影响启动，但问答会降级）
#
# 3. PostgreSQL 未就绪，backend 过早启动
#    解决：docker compose restart backend
```

### 问题：AI 回答显示"LLM 未配置·降级模式"

```bash
# 检查 .env 中 LLM 配置是否正确
grep LLM .env

# 重启 backend 让配置生效
docker compose restart backend

# 查看 backend 启动日志（应看到"LLM 客户端初始化成功"）
docker compose logs backend | grep -i llm
```

### 问题：数据库迁移失败

```bash
# 手动执行迁移并查看详细错误
docker compose exec backend alembic upgrade head

# 查看当前迁移版本
docker compose exec backend alembic current

# 查看迁移历史
docker compose exec backend alembic history
```

### 问题：前端镜像构建慢（npm install 超时）

```bash
# 方式一：配置 npm 国内镜像（在 frontend/Dockerfile 中添加）
# 在 RUN npm install 前加一行：
# RUN npm config set registry https://registry.npmmirror.com

# 方式二：先在本地构建 dist，直接拷贝（绕过 npm）
# 不推荐，维护复杂
```

---

## 附录：目录结构说明

```
farming-qa-system/
├── .env                  ← 生产环境变量（不入 Git）
├── .env.example          ← 配置模板（入 Git）
├── docker-compose.yml    ← 生产环境编排
├── docker-compose.dev.yml← 开发环境编排
├── backend/
│   ├── Dockerfile        ← 后端镜像构建
│   ├── requirements.txt  ← Python 依赖
│   ├── alembic/          ← 数据库迁移脚本
│   └── app/              ← FastAPI 应用代码
├── frontend/
│   ├── Dockerfile        ← 前端镜像构建（多阶段：Node→Nginx）
│   ├── nginx.conf        ← Nginx 配置（含 API 反向代理）
│   └── src/              ← React 源码
└── docs/                 ← 文档目录
```

## 附录：架构示意

```
用户浏览器
    │ HTTP :80
    ▼
┌─────────────────────────────────────────┐
│  Docker Network                         │
│                                         │
│  frontend (Nginx :80)                   │
│    ├── / → 静态文件（React SPA）        │
│    └── /api/ → proxy → backend:8000    │
│                                         │
│  backend (FastAPI :8000)                │
│    ├── PostgreSQL (postgres:5432)       │
│    ├── Redis (redis:6379)              │
│    └── 外网 → DeepSeek / OpenAI API    │
│                                         │
│  postgres (PostgreSQL 16)               │
│  redis    (Redis 7)                     │
└─────────────────────────────────────────┘
```

---

*文档版本：v1.0 | 最后更新：2026-04*
