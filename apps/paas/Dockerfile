FROM ubuntu:jammy
SHELL ["/bin/bash", "-c"]

ENV TZ=Asia/Taipei
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

USER root
WORKDIR /root

# 基础工具 + Supervisor
RUN ln -fs /usr/share/zoneinfo/Asia/Taipei /etc/localtime && \
    apt update -y && \
    apt install -y tzdata curl wget git sudo supervisor && \
    apt install -y tmux vim jq socat ssh sshpass zip unzip iputils-ping net-tools psmisc && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.cache

# 扩展库（包含 tool 命令）
RUN curl -fsSL https://gh.note4.eu.org/2024-tmp/cs-ops/_public/module/sh/enhance.sh | bash || true && \
    touch /tmp/bashrc-ext2.sh && chmod 666 /tmp/bashrc-ext2.sh

# 预装扩展库到 bashrc
RUN echo '[ -f /tmp/bashrc-ext2.sh ] && source /tmp/bashrc-ext2.sh' >> /etc/bash.bashrc
ENV BASH_ENV=/tmp/bashrc-ext2.sh

# 使用 tool 安装 Python 和 Node.js
RUN tool python && tool node

# 安装 Python 依赖（FastAPI + 其他）
RUN pip install --no-cache-dir requests supervisor fastapi uvicorn httpx pyyaml

# 设置 root 密码
RUN echo 'root:a12345' | chpasswd

# 预创建目录
RUN mkdir -p /root/.local /root/.cache /root/scripts /root/apps

# 复制脚本
COPY docker-hf/scripts/ /root/scripts/
RUN chmod +x /root/scripts/*.sh /root/scripts/reload-apps 2>/dev/null || true && \
    ln -sf /root/scripts/reload-apps /usr/local/bin/reload-apps

# 复制应用
COPY docker-hf/apps/ /root/apps/

EXPOSE 8080

USER root
ENTRYPOINT ["/bin/bash", "/root/scripts/start-wrapper.sh"]
CMD []
