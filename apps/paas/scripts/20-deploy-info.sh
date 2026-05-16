#!/bin/bash
# 部署信息收集脚本

INFO_FILE="$WORKROOT/.deploy-info.json"
SUB_DIR="$WORKROOT/.sub"

echo "==> 收集部署信息..."

# 提取主机名
HOST="${EXTERNAL_URL#https://}"
HOST="${HOST#http://}"
HOST="${HOST%%/*}"
PASS="${TROJAN_PASS:-a12345}"

# 如果没有 EXTERNAL_URL，使用默认值
if [ -z "$HOST" ]; then
  HOST="localhost"
fi
NAME="${HOST%%.*}"

cat > "$INFO_FILE" <<EOF
{
  "res_id": "${RES_ID:-unknown}",
  "ext_info": "${EXT_INFO:-}",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "hostname": "$(hostname)",
  "platform": "$(echo ${RES_ID:-} | cut -d: -f1)",
  "account": "$(echo ${RES_ID:-} | cut -d: -f2)",
  "resource": "$(echo ${RES_ID:-} | cut -d: -f3)",
  "external_url": "${EXTERNAL_URL:-}",
  "env": {
    "trojan_pass": "${TROJAN_PASS:-}",
    "exec_token": "${EXEC_TOKEN:-}"
  }
}
EOF

# 生成 Trojan 订阅配置
mkdir -p "$SUB_DIR"

# Clash 订阅
cat > "$SUB_DIR/clash.yaml" <<EOF
proxies:
  - name: $NAME
    type: trojan
    server: $HOST
    port: 443
    password: $PASS
    network: ws
    ws-opts:
      path: /
      headers:
        Host: $HOST
    sni: $HOST
    skip-cert-verify: false

proxy-groups:
  - name: auto
    type: select
    proxies:
      - $NAME

rules:
  - MATCH,auto
EOF

# V2Ray 订阅 (URI)
echo "trojan://${PASS}@${HOST}:443?security=tls&type=ws&host=${HOST}&path=%2F#${NAME}" > "$SUB_DIR/uri.txt"

# 配置信息页面 (HTML) - 简化版
cat > "$SUB_DIR/info.html" <<'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PaaS Lite - 配置信息</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #666; margin-top: 30px; }
        .info { background: #e8f4f8; padding: 15px; border-radius: 4px; margin: 15px 0; }
        .config { background: #f4f4f4; padding: 15px; border-radius: 4px; margin: 15px 0; font-family: monospace; white-space: pre-wrap; word-break: break-all; }
        .btn { display: inline-block; padding: 10px 20px; margin: 5px; background: #4CAF50; color: white; text-decoration: none; border-radius: 4px; }
        .btn:hover { background: #45a049; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 PaaS Lite - 配置信息</h1>
        
        <div class="info">
            <h3>📦 部署信息</h3>
            <p><strong>外部地址:</strong> <code>__EXTERNAL_URL__</code></p>
            <p><strong>部署时间:</strong> <code>__DEPLOYED_AT__</code></p>
            <p><strong>主机名:</strong> <code>__HOSTNAME__</code></p>
        </div>

        <h2>🔐 Trojan 配置</h2>
        <div class="info">
            <p><strong>服务器:</strong> <code>__SERVER__</code></p>
            <p><strong>端口:</strong> <code>443</code></p>
            <p><strong>密码:</strong> <code>__PASSWORD__</code></p>
            <p><strong>传输:</strong> WebSocket (path: /)</p>
        </div>

        <h3>📥 订阅链接</h3>
        <p>
            <a href="/info/clash.yaml" class="btn">Clash 配置</a>
            <a href="/info/uri.txt" class="btn">V2Ray URI</a>
        </p>

        <h3>📋 Clash 配置</h3>
        <div class="config">__CLASH_CONFIG__</div>

        <h3>🔗 V2Ray URI</h3>
        <div class="config">__V2RAY_URI__</div>
    </div>
</body>
</html>
HTMLEOF

# 替换占位符
sed -i "s|__EXTERNAL_URL__|${EXTERNAL_URL:-N/A}|g" "$SUB_DIR/info.html"
sed -i "s|__DEPLOYED_AT__|$(date -u +%Y-%m-%dT%H:%M:%SZ)|g" "$SUB_DIR/info.html"
sed -i "s|__HOSTNAME__|$(hostname)|g" "$SUB_DIR/info.html"
sed -i "s|__SERVER__|${HOST}|g" "$SUB_DIR/info.html"
sed -i "s|__PASSWORD__|${PASS}|g" "$SUB_DIR/info.html"
sed -i "s|__CLASH_CONFIG__|$(cat $SUB_DIR/clash.yaml | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')|g" "$SUB_DIR/info.html"
sed -i "s|__V2RAY_URI__|$(cat $SUB_DIR/uri.txt)|g" "$SUB_DIR/info.html"

echo "✓ Trojan 订阅已生成"

echo "✓ 部署信息已保存到 $INFO_FILE"
cat "$INFO_FILE"
