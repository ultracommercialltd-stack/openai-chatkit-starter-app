# LoveGenie ChatKit adapter — persistent server image (Render / Railway / Fly).
# The adapter is an always-on FastAPI/uvicorn process: it keeps ChatKit thread
# state in-memory, so it must run as ONE persistent instance (not serverless).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies from pyproject (fastapi, uvicorn, openai-chatkit, httpx, pyjwt).
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# Hosts inject $PORT; default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
