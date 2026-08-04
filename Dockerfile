FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a dedicated non-root user for the app and its writable volume.
RUN useradd --create-home --uid 1000 --shell /bin/sh authorlite \
	&& mkdir -p /app/data \
	&& chown -R authorlite:authorlite /app/data

# Copy source code
COPY app.py .
COPY .env .
# Copy repository README for dashboard route
COPY README.md .
# Copy favicon served by /favicon.ico route
COPY favicon.ico .
# Copy static assets (including local marked.min.js)
COPY static ./static
# Copy templates for the web UI
COPY templates ./templates
# Copy prompt and skill sources used by the book planning flow
COPY prompts ./prompts
COPY skills ./skills
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 3846

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "app.py"]