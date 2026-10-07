FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for NLTK and scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY Step\ 12\ -\ Packaging/package/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install/download required NLTK resources deterministically during build
RUN python -c "
import nltk
nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('averaged_perceptron_tagger_eng', quiet=True)
nltk.download('wordnet', quiet=True)
print('NLTK resources installed')
"

# Copy application code and package
COPY api/ /app/api/
COPY Step\ 12\ -\ Packaging/package/ /app/package/
COPY .env.example /app/.env

# Ensure package is importable
ENV PYTHONPATH=/app/package:$PYTHONPATH
ENV ARTIFACTS_DIR=/app/package/mental_health_screening/artifacts
ENV SERVICE_VERSION=0.1.0
ENV PORT=8000
ENV HOST=0.0.0.0
ENV LOG_LEVEL=INFO

# Session auth. These carry the documented research demo values so the image
# runs as-is; override MENTAL_AI_AUTH_USER, MENTAL_AI_AUTH_PASSWORD and
# MENTAL_AI_TOKEN_SECRET at run time for any real deployment.
ENV MENTAL_AI_AUTH_USER=admin
ENV MENTAL_AI_AUTH_PASSWORD=password
ENV MENTAL_AI_SESSION_TTL=43200

# Expose the service port
EXPOSE 8000

# Health check using API endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "
import urllib.request, os
try:
    resp = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
    print(resp.status)
except Exception as e:
    print('HEALTHCHECK FAIL:', e)
    exit(1)
" || exit 1

# Start the API
CMD ["python", "-m", "uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
