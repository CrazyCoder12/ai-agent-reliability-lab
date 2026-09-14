FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 lab
USER lab
EXPOSE 8787
CMD ["uvicorn", "agent_reliability_lab.api:app", "--host", "0.0.0.0", "--port", "8787"]
