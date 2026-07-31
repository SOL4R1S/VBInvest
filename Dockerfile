FROM python:3.14-slim AS backend
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/ scripts/
COPY postgres/ postgres/

FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM backend
COPY --from=frontend-build /app/frontend/out /app/frontend/out
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "scripts.api:app", "--host", "0.0.0.0", "--port", "8000"]
