# 用轻量的官方Python镜像即可，不需要额外的系统依赖
FROM python:3.12-slim

WORKDIR /app

# 先只拷贝requirements，方便Docker层缓存——代码变了不用重新装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝其余代码
COPY . .

RUN chmod +x entrypoint.sh

# app.py 里 Flask 监听的是 5000 端口
EXPOSE 5000

ENV FLASK_RUN_HOST=0.0.0.0

ENTRYPOINT ["./entrypoint.sh"]