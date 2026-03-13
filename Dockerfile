FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p /app/data/backups

# 동기화 cron 설정
# 장비: 매일 새벽 3시 / 이벤트: 매월 1일, 15일 새벽 4시
RUN printf "0 3 * * * cd /app && python -m equipment.sync >> /var/log/sync.log 2>&1\n0 4 1,15 * * cd /app && python -m events.sync --start-month \$(date +\\%%m) --end-month \$(( \$(date +\\%%m) + 1 )) >> /var/log/events_sync.log 2>&1\n" > /etc/cron.d/sync-cron \
    && chmod 0644 /etc/cron.d/sync-cron \
    && crontab /etc/cron.d/sync-cron

# 시작 스크립트
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8501

ENTRYPOINT ["/entrypoint.sh"]
