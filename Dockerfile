FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY app.py .
COPY .env .
# Copy templates for the web UI
COPY templates ./templates
RUN mkdir -p data

EXPOSE 3846

CMD ["python", "app.py"]