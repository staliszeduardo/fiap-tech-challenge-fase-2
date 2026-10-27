FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 'Werkzeug<3'
COPY app.py ./
RUN useradd --create-home app
USER app
EXPOSE 8003
CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8003", "app:app"]
