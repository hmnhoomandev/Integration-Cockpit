FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 COCKPIT_DB=/tmp/cockpit.sqlite
WORKDIR /app
COPY cockpit cockpit
COPY static static
USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["python", "-m", "cockpit.server"]
CMD ["serve", "--hosted", "--bind", "0.0.0.0", "--port", "8080"]
