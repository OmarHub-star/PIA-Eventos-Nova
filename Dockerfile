FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home nova
COPY --chown=nova:nova src ./src
COPY --chown=nova:nova data ./data
COPY --chown=nova:nova scripts ./scripts
COPY --chown=nova:nova tests ./tests
COPY --chown=nova:nova pyproject.toml .
RUN mkdir -p /app/docs/evidencias && chown -R nova:nova /app
USER nova
EXPOSE 8000
CMD ["python", "scripts/serve.py"]
