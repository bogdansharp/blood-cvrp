FROM node:24-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./
RUN npm run build


FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY storage storage
COPY --from=frontend-build /app/frontend/build frontend/build

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn backend.src.main:app --host 0.0.0.0 --port ${PORT}"]