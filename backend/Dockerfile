FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

COPY app ./app

ENV STORAGE_PATH=/data/projects
EXPOSE 8000
# --proxy-headers lets uvicorn derive the real client scheme/IP from the
# reverse proxy's X-Forwarded-* headers (correct scheme → Secure session cookie
# on HTTPS; real client IP → per-IP anti-fraud/brute-force limits).
#
# FORWARDED_ALLOW_IPS MUST name the reverse proxy's IP or subnet. It is NEVER
# "*": a wildcard tells uvicorn to trust X-Forwarded-For from ANY peer, so any
# client could spoof its source IP and defeat the per-IP signup/login limits and
# poison audit logs. Default 127.0.0.1 (same-host proxy); override to the proxy
# container/LB subnet in production (see docker-compose.yml / DEPLOY.md).
ENV FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips \"$FORWARDED_ALLOW_IPS\""]
