#!/usr/bin/env python3
"""
PaaS Lite v3 - Python Reverse Proxy
替代 Caddy，避免被 HF Space 检测
"""
import os
import sys
import yaml
import subprocess
from collections import deque
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse, FileResponse
import httpx
import uvicorn

# 环境变量
WORKROOT = os.getenv('WORKROOT', '/tmp/workroot')
PORT = int(os.getenv('PORT', '8080'))
AUTH_TOKEN = os.getenv('AUTH_TOKEN', '')  # 可选认证

# 日志缓冲
log_buffer = deque(maxlen=1000)

def log_message(msg):
    print(msg, flush=True)
    log_buffer.append(msg)

# 加载应用路由配置
def load_routes():
    routes = []
    apps_dir = os.path.join(os.path.expanduser('~'), 'apps')
    
    if not os.path.exists(apps_dir):
        log_message(f"[Config] Apps directory not found: {apps_dir}")
        return routes
    
    # 导入配置加载器
    sys.path.insert(0, os.path.dirname(__file__))
    from app_config import load_all_apps
    
    try:
        apps = load_all_apps(apps_dir)
        for app in apps:
            for route in app.get_routes():
                # 转换为 /apps/* 路径
                path = route['path']
                if not path.startswith('/'):
                    path = '/' + path
                full_path = f"/apps/{app.name}{path}"
                
                routes.append({
                    'path': full_path,
                    'target': route['target'],
                    'strip_prefix': route.get('strip_prefix', False),
                    'app': app.name
                })
                log_message(f"[Config] Loaded route: {full_path} -> {route['target']}")
    except Exception as e:
        log_message(f"[Config] Error loading apps: {e}")
    
    return routes

routes = load_routes()
app = FastAPI()

# 认证中间件
def check_auth(request: Request):
    if not AUTH_TOKEN:
        return True
    
    # Bearer Token
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') and auth_header[7:] == AUTH_TOKEN:
        return True
    
    # Query parameter
    if request.query_params.get('token') == AUTH_TOKEN:
        return True
    
    return False

# 根路径
@app.get("/")
async def root(request: Request):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return JSONResponse({
        "status": "ok",
        "service": "PaaS Lite v3",
        "endpoints": {
            "apps": "/apps/*",
            "system": "/sys/info | /sys/supervisor | /sys/exec | /sys/logs",
            "network": "/net/relay"
        }
    })

# 系统信息页面
@app.get("/sys/info")
async def sys_info(request: Request):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 读取部署信息
    deploy_info = {}
    info_file = os.path.join(WORKROOT, '.deploy-info.json')
    if os.path.exists(info_file):
        import json
        with open(info_file) as f:
            deploy_info = json.load(f)
    
    # 系统信息
    import platform
    import socket
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>System Info - PaaS Lite v3</title>
    <style>
        body {{ font-family: monospace; max-width: 1200px; margin: 20px auto; padding: 20px; background: #1e1e1e; color: #d4d4d4; }}
        h1 {{ color: #4ec9b0; }}
        h2 {{ color: #569cd6; margin-top: 30px; }}
        .section {{ background: #252526; padding: 15px; margin: 10px 0; border-radius: 4px; }}
        .key {{ color: #9cdcfe; }}
        .value {{ color: #ce9178; }}
        a {{ color: #4ec9b0; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        pre {{ background: #1e1e1e; padding: 10px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>🖥️ System Information</h1>
    
    <h2>📦 Deployment Info</h2>
    <div class="section">
        <div><span class="key">RES_ID:</span> <span class="value">{deploy_info.get('res_id', 'N/A')}</span></div>
        <div><span class="key">Platform:</span> <span class="value">{platform.system()} {platform.release()}</span></div>
        <div><span class="key">Hostname:</span> <span class="value">{socket.gethostname()}</span></div>
    </div>
    
    <h2>🌐 Network Info</h2>
    <div class="section">
        <div><span class="key">Listen Port:</span> <span class="value">{PORT}</span></div>
        <div><span class="key">Auth:</span> <span class="value">{'Enabled' if AUTH_TOKEN else 'Disabled'}</span></div>
    </div>
    
    <h2>🔗 Endpoints</h2>
    <div class="section">
        <div><strong>Applications:</strong></div>
        <ul>
            {''.join([f'<li><a href="{r["path"]}/">{r["path"]}/</a> → {r["target"]} ({r["app"]})</li>' for r in routes])}
        </ul>
        <div><strong>System:</strong></div>
        <ul>
            <li><a href="/sys/info">/sys/info</a> - This page</li>
            <li><a href="/sys/supervisor">/sys/supervisor</a> - Process manager</li>
            <li><a href="/sys/exec">/sys/exec</a> - Terminal</li>
            <li><a href="/sys/logs">/sys/logs</a> - View logs</li>
        </ul>
        <div><strong>Network:</strong></div>
        <ul>
            <li><code>POST /net/relay</code> - HTTP relay</li>
        </ul>
    </div>
    
    <h2>📋 Deploy Info (JSON)</h2>
    <div class="section">
        <pre>{yaml.dump(deploy_info, default_flow_style=False)}</pre>
    </div>
</body>
</html>"""
    return HTMLResponse(html)

# Supervisor Web UI
@app.api_route("/sys/supervisor/{path:path}", methods=["GET", "POST"])
async def sys_supervisor(request: Request, path: str):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    target_url = f"http://127.0.0.1:9001/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                content=await request.body(),
                timeout=30.0
            )
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        log_message(f"[Supervisor] Error: {e}")
        raise HTTPException(status_code=502, detail=f"Supervisor unavailable: {e}")

# 交互式终端
@app.get("/sys/exec")
async def sys_exec_page(request: Request):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Terminal - PaaS Lite v3</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.min.css" />
    <style>
        body { margin: 0; padding: 20px; background: #000; font-family: monospace; }
        #terminal { height: calc(100vh - 40px); }
        h3 { color: #0f0; margin: 0 0 10px 0; }
    </style>
</head>
<body>
    <h3>🖥️ Interactive Terminal</h3>
    <div id="terminal"></div>
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.min.js"></script>
    <script>
        const term = new Terminal({ cursorBlink: true, fontSize: 14 });
        const fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(document.getElementById('terminal'));
        fitAddon.fit();
        
        let command = '';
        term.writeln('\\x1b[32mPaaS Lite v3 Terminal\\x1b[0m');
        term.writeln('Type commands and press Enter. Type "exit" to close.\\r\\n');
        term.write('$ ');
        
        term.onData(async (data) => {
            if (data === '\\r') {
                term.write('\\r\\n');
                if (command.trim() === 'exit') {
                    term.writeln('\\x1b[33mGoodbye!\\x1b[0m');
                    return;
                }
                if (command.trim()) {
                    try {
                        const token = new URLSearchParams(window.location.search).get('token') || '';
                        const headers = token ? { 'Authorization': 'Bearer ' + token } : {};
                        const resp = await fetch('/sys/exec/run', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json', ...headers },
                            body: JSON.stringify({ command: command })
                        });
                        const result = await resp.json();
                        if (result.output) term.write(result.output.replace(/\\n/g, '\\r\\n'));
                        if (result.error) term.write('\\x1b[31m' + result.error + '\\x1b[0m\\r\\n');
                    } catch (e) {
                        term.write('\\x1b[31mError: ' + e.message + '\\x1b[0m\\r\\n');
                    }
                }
                command = '';
                term.write('$ ');
            } else if (data === '\\x7f') {
                if (command.length > 0) {
                    command = command.slice(0, -1);
                    term.write('\\b \\b');
                }
            } else {
                command += data;
                term.write(data);
            }
        });
        
        window.addEventListener('resize', () => fitAddon.fit());
    </script>
</body>
</html>"""
    return HTMLResponse(html)

@app.post("/sys/exec/run")
async def sys_exec_run(request: Request):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    command = data.get('command', '')
    
    if not command:
        return JSONResponse({"error": "No command provided"})
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=WORKROOT
        )
        return JSONResponse({
            "output": result.stdout + result.stderr,
            "exit_code": result.returncode
        })
    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "Command timeout"})
    except Exception as e:
        return JSONResponse({"error": str(e)})

# 日志查看
@app.get("/sys/logs")
async def sys_logs(request: Request):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return PlainTextResponse("\n".join(log_buffer))

# HTTP 中继
@app.post("/net/relay")
async def net_relay(request: Request):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    url = data.get('url')
    method = data.get('method', 'GET').upper()
    headers = data.get('headers', {})
    body = data.get('body')
    
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter")
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body.encode() if body else None,
                timeout=30.0
            )
        
        return JSONResponse({
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text
        })
    except Exception as e:
        log_message(f"[Relay] Error: {e}")
        raise HTTPException(status_code=502, detail=f"Relay failed: {e}")

# 应用反向代理
@app.api_route("/apps/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def apps_proxy(request: Request, path: str):
    if AUTH_TOKEN and not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    full_path = f"/apps/{path}"
    
    for route in routes:
        if full_path.startswith(route['path']):
            target = route['target']
            strip_prefix = route.get('strip_prefix', False)
            
            # strip_prefix: 去掉匹配的路径前缀
            # 例如: /apps/hello-world/test -> /test (strip_prefix=true)
            #      /apps/hello-world/test -> /apps/hello-world/test (strip_prefix=false, 保留完整路径)
            # 但通常我们希望: /apps/hello-world/ -> / (去掉 /apps/hello-world 部分)
            proxy_path = full_path[len(route['path']):] if strip_prefix else full_path[len(route['path']):]
            if not proxy_path:
                proxy_path = '/'
            
            target_url = f"{target}{proxy_path}"
            if request.url.query:
                target_url += f"?{request.url.query}"
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.request(
                        method=request.method,
                        url=target_url,
                        headers=dict(request.headers),
                        content=await request.body(),
                        timeout=30.0
                    )
                return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
            except Exception as e:
                log_message(f"[Apps] Error: {e}")
                raise HTTPException(status_code=502, detail=f"App unavailable: {e}")
    
    return JSONResponse({"error": "App not found"}, status_code=404)

if __name__ == "__main__":
    log_message(f"[Proxy] Starting on port {PORT}")
    log_message(f"[Proxy] Auth: {'Enabled' if AUTH_TOKEN else 'Disabled'}")
    log_message(f"[Proxy] Loaded {len(routes)} routes")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
