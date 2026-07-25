# 灵宝爬虫服务 Dockerfile
# 基于 Python + Playwright（Chromium）实现 Scrapling 反爬

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 系统依赖（Playwright Chromium 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright Chromium 浏览器
RUN playwright install chromium --with-deps

# 复制应用代码
COPY app.py .

# 暴露端口（Render 默认 10000）
ENV PORT=10000
EXPOSE 10000

# 启动命令
CMD ["python", "app.py"]
