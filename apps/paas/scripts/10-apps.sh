#!/bin/bash
# Apps 管理 - 基于 app.yaml 配置

echo "==> 配置 Apps..."

# 使用 Python 脚本生成 Supervisor 配置
SCRIPT_PATH="$WORKROOT/scripts/generate-app-configs.py"
if [ -f "$SCRIPT_PATH" ]; then
  echo "  使用 app.yaml 生成配置..."
  python3 "$SCRIPT_PATH"
else
  echo "  [Warning] generate-app-configs.py not found at $SCRIPT_PATH"
fi

echo "✓ Apps 配置完成"
