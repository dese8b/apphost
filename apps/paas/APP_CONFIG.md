# App 配置规范：app.yaml

每个应用一个 `app.yaml`，统一管理安装、启动、路由、隧道等配置。

## 最小配置

```yaml
name: hello-world
start:
  command: python3 -m http.server 3000
routes:
  - path: /
    target: http://localhost:3000
```

## 完整配置

```yaml
# 基本信息
name: hello-world
version: 1.0.0
description: 应用描述
author: your-name

# 依赖安装（可选）
install:
  command: npm install  # 单行命令
  # 或
  script: ./install.sh  # 脚本路径
  # 或
  commands:             # 多行命令
    - npm install
    - pip install -r requirements.txt

# 启动配置（必需）
start:
  command: python3 -m http.server 3000  # 单行命令
  # 或
  script: ./start.sh                    # 脚本路径
  # 或详细配置
  exec:
    command: python3 -m http.server
    args: ["3000"]
    workdir: .        # 相对于 app 目录
    env:              # 环境变量
      PORT: 3000
      DEBUG: "1"

# 本地路由（必需）
routes:
  - path: /           # 相对路径，实际为 /apps/{name}/
    target: http://localhost:3000
    strip_prefix: false
  - path: /api
    target: http://localhost:3001
    strip_prefix: true

# 远程隧道（可选）
tunnels:
  - name: cloudflared-main
    type: cloudflared
    enabled: false
    target: http://localhost:3000
    config:
      no_tls_verify: false
  
  - name: frp-main
    type: frp
    enabled: false
    target: http://localhost:3000
    config:
      server_addr: frp.example.com
      server_port: 7000
      token: xxx
      subdomain: myapp

# 健康检查（可选）
health:
  enabled: true
  http:
    url: http://localhost:3000/health
    method: GET
    timeout: 5
    interval: 30
    healthy_threshold: 2
    unhealthy_threshold: 3
  # 或 TCP 检查
  tcp:
    host: localhost
    port: 3000
    timeout: 3
    interval: 30

# Supervisor 配置（可选，覆盖默认）
supervisor:
  autostart: true
  autorestart: true
  startsecs: 3
  startretries: 3
  stopwaitsecs: 10

# 元数据（可选）
metadata:
  tags: [web, demo]
  homepage: https://example.com
  repository: https://github.com/user/repo
```

## 字段说明

### name（必需）
应用名称，用于生成路由 `/apps/{name}/` 和 Supervisor 进程名 `app-{name}`

### start（必需）
三选一：
- `command`: 单行启动命令
- `script`: 启动脚本路径（相对于 app 目录）
- `exec`: 详细配置（命令、参数、工作目录、环境变量）

### routes（必需）
本地路由映射，至少一条：
- `path`: 相对路径，自动加前缀 `/apps/{name}`
- `target`: 目标地址（通常是 `http://localhost:端口`）
- `strip_prefix`: 是否去掉路径前缀（默认 false）

### install（可选）
依赖安装，三选一：
- `command`: 单行命令
- `script`: 安装脚本路径
- `commands`: 多行命令数组

### tunnels（可选）
远程隧道配置，支持：
- `cloudflared`: Cloudflare Tunnel
- `frp`: Fast Reverse Proxy
- 每个隧道可独立启用/禁用

### health（可选）
健康检查配置：
- `http`: HTTP 端点检查
- `tcp`: TCP 端口检查

### supervisor（可选）
覆盖默认 Supervisor 配置

### metadata（可选）
应用元数据，用于展示和管理

## 实现优先级

### ✅ 阶段 1（已实现）
- `name`
- `start.command` / `start.script`
- `routes`

### 🔶 阶段 2（重要）
- `install`
- `start.env`
- `supervisor` 覆盖

### 🔷 阶段 3（扩展）
- `tunnels`
- `health`
- `metadata`

## 示例

### 简单 HTTP 服务
```yaml
name: static-site
start:
  command: python3 -m http.server 8080
routes:
  - path: /
    target: http://localhost:8080
```

### Node.js 应用
```yaml
name: express-app
install:
  command: npm install
start:
  command: npm start
  env:
    PORT: 3000
    NODE_ENV: production
routes:
  - path: /
    target: http://localhost:3000
  - path: /api
    target: http://localhost:3001
```

### 带隧道的应用
```yaml
name: webhook-receiver
start:
  command: python3 app.py
routes:
  - path: /
    target: http://localhost:5000
tunnels:
  - name: public-tunnel
    type: cloudflared
    enabled: true
    target: http://localhost:5000
```

## 迁移指南

### 旧方式（废弃）
```
apps/hello-world/
├── start.sh
├── proxy.yaml
└── caddy.conf
```

### 新方式
```
apps/hello-world/
├── app.yaml      # 统一配置
└── index.html
```

如果需要复杂启动逻辑，仍可使用脚本：
```yaml
name: hello-world
start:
  script: ./start.sh  # 引用脚本
routes:
  - path: /
    target: http://localhost:3000
```
