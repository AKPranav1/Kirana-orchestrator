FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
COPY requirements-providers.txt .
ARG INSTALL_PROVIDERS=false
RUN pip install --no-cache-dir -r requirements.txt
RUN if [ "$INSTALL_PROVIDERS" = "true" ]; then pip install --no-cache-dir -r requirements-providers.txt; fi
COPY backend ./backend
COPY ingestion ./ingestion
COPY db_alerts ./db_alerts
COPY webhook ./webhook
RUN useradd --uid 10001 --create-home kirana
USER kirana
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--limit-concurrency", "64", "--backlog", "128", "--timeout-keep-alive", "5"]
