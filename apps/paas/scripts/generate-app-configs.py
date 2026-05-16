#!/usr/bin/env python3
"""
Supervisor 配置生成器
从 app.yaml 生成 Supervisor 配置文件
"""
import os
import sys
from app_config import load_all_apps

def generate_supervisor_config(app, supervisor_dir: str, workroot: str):
    """为单个应用生成 Supervisor 配置"""
    program_name = f"app-{app.name}"
    config_file = os.path.join(supervisor_dir, f"{program_name}.conf")
    
    # 获取配置
    command = app.get_start_command()
    workdir = app.get_workdir()
    env_vars = app.get_env()
    supervisor_cfg = app.get_supervisor_config()
    
    # 构建环境变量字符串
    env_str = f'HOME="{workroot}",USER="root",WORKROOT="{workroot}"'
    for key, value in env_vars.items():
        env_str += f',{key}="{value}"'
    
    # 生成配置
    config = f"""[program:{program_name}]
command={command}
directory={workdir}
environment={env_str}
autostart={str(supervisor_cfg['autostart']).lower()}
autorestart={str(supervisor_cfg['autorestart']).lower()}
startsecs={supervisor_cfg['startsecs']}
startretries={supervisor_cfg['startretries']}
stopwaitsecs={supervisor_cfg['stopwaitsecs']}
stdout_logfile={workroot}/logs/{program_name}.log
stderr_logfile={workroot}/logs/{program_name}.err.log
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
"""
    
    # 写入文件
    with open(config_file, 'w') as f:
        f.write(config)
    
    print(f"[OK] Generated config for: {app.name}")
    return config_file


def main():
    # 环境变量
    workroot = os.getenv('WORKROOT', '/tmp/workroot')
    supervisor_dir = os.path.join(workroot, 'supervisor', 'conf.d')
    apps_dir = os.path.join(os.path.expanduser('~'), 'apps')
    
    # 确保目录存在
    os.makedirs(supervisor_dir, exist_ok=True)
    os.makedirs(os.path.join(workroot, 'logs'), exist_ok=True)
    
    # 加载所有应用
    print(f"[Info] Loading apps from: {apps_dir}")
    apps = load_all_apps(apps_dir)
    
    if not apps:
        print("[Warning] No apps found")
        return
    
    # 生成配置
    print(f"[Info] Generating Supervisor configs...")
    for app in apps:
        try:
            generate_supervisor_config(app, supervisor_dir, workroot)
        except Exception as e:
            print(f"[Error] Failed to generate config for {app.name}: {e}")
    
    print(f"[Done] Generated {len(apps)} app configs")


if __name__ == '__main__':
    main()
