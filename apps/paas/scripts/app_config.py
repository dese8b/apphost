#!/usr/bin/env python3
"""
App 配置加载器
解析 app.yaml 并提供配置访问接口
"""
import os
import yaml
from typing import Dict, List, Optional

class AppConfig:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.app_dir = os.path.dirname(config_path)
        self.config = self._load()
        self._validate()
    
    def _load(self) -> dict:
        """加载 YAML 配置"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config not found: {self.config_path}")
        
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        if not config:
            raise ValueError(f"Empty config: {self.config_path}")
        
        return config
    
    def _validate(self):
        """验证必需字段"""
        required = ['name', 'start', 'routes']
        for field in required:
            if field not in self.config:
                raise ValueError(f"Missing required field: {field}")
        
        # 验证 start
        start = self.config['start']
        if not isinstance(start, dict):
            raise ValueError("'start' must be a dict")
        if 'command' not in start and 'script' not in start and 'exec' not in start:
            raise ValueError("'start' must have 'command', 'script', or 'exec'")
        
        # 验证 routes
        routes = self.config['routes']
        if not isinstance(routes, list) or len(routes) == 0:
            raise ValueError("'routes' must be a non-empty list")
        for route in routes:
            if 'path' not in route or 'target' not in route:
                raise ValueError("Each route must have 'path' and 'target'")
    
    @property
    def name(self) -> str:
        return self.config['name']
    
    @property
    def version(self) -> str:
        return self.config.get('version', '1.0.0')
    
    @property
    def description(self) -> str:
        return self.config.get('description', '')
    
    def get_start_command(self) -> str:
        """获取启动命令"""
        start = self.config['start']
        
        # 简单命令
        if 'command' in start:
            return start['command']
        
        # 脚本
        if 'script' in start:
            script_path = os.path.join(self.app_dir, start['script'])
            if not os.path.exists(script_path):
                raise FileNotFoundError(f"Start script not found: {script_path}")
            return f"bash {script_path}"
        
        # 详细配置
        if 'exec' in start:
            exec_cfg = start['exec']
            cmd = exec_cfg['command']
            if 'args' in exec_cfg:
                cmd += ' ' + ' '.join(exec_cfg['args'])
            return cmd
        
        raise ValueError("Invalid start configuration")
    
    def get_workdir(self) -> str:
        """获取工作目录"""
        start = self.config['start']
        if 'exec' in start and 'workdir' in start['exec']:
            workdir = start['exec']['workdir']
            if workdir == '.':
                return self.app_dir
            return os.path.join(self.app_dir, workdir)
        return self.app_dir
    
    def get_env(self) -> Dict[str, str]:
        """获取环境变量"""
        start = self.config['start']
        if 'exec' in start and 'env' in start['exec']:
            return start['exec']['env']
        return {}
    
    def get_routes(self) -> List[Dict]:
        """获取路由配置"""
        routes = []
        for route in self.config['routes']:
            routes.append({
                'path': route['path'],
                'target': route['target'],
                'strip_prefix': route.get('strip_prefix', False)
            })
        return routes
    
    def get_supervisor_config(self) -> Dict:
        """获取 Supervisor 配置"""
        default = {
            'autostart': True,
            'autorestart': True,
            'startsecs': 3,
            'startretries': 3,
            'stopwaitsecs': 10
        }
        
        if 'supervisor' in self.config:
            default.update(self.config['supervisor'])
        
        return default


def load_all_apps(apps_dir: str) -> List[AppConfig]:
    """加载所有应用配置"""
    apps = []
    
    if not os.path.exists(apps_dir):
        return apps
    
    for app_name in os.listdir(apps_dir):
        app_dir = os.path.join(apps_dir, app_name)
        if not os.path.isdir(app_dir):
            continue
        
        config_path = os.path.join(app_dir, 'app.yaml')
        if not os.path.exists(config_path):
            print(f"[Warning] No app.yaml found for: {app_name}")
            continue
        
        try:
            app = AppConfig(config_path)
            apps.append(app)
            print(f"[OK] Loaded app: {app.name}")
        except Exception as e:
            print(f"[Error] Failed to load {app_name}: {e}")
    
    return apps


if __name__ == '__main__':
    # 测试
    import sys
    if len(sys.argv) > 1:
        config = AppConfig(sys.argv[1])
        print(f"Name: {config.name}")
        print(f"Command: {config.get_start_command()}")
        print(f"Workdir: {config.get_workdir()}")
        print(f"Routes: {config.get_routes()}")
    else:
        apps = load_all_apps(os.path.expanduser('~/apps'))
        print(f"Loaded {len(apps)} apps")
