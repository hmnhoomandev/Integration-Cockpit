FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 COCKPIT_DB=/data/cockpit.sqlite
RUN apt-get update && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir /data && chown 65532:65532 /data
WORKDIR /app
COPY cockpit cockpit
COPY static static
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "-m", "cockpit.server"]
CMD ["serve", "--hosted", "--bind", "0.0.0.0", "--port", "8080"]
