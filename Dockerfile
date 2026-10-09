FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for NLTK and scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY Step\ 12\ -\ Packaging/package/requirements.txt /app/requirements.txt
COPY api/requirements-runtime.txt /app/api-requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/api-requirements.txt

# Install/download required NLTK resources deterministically during build
RUN python -c "import nltk; resources = ['vader_lexicon', 'punkt', 'punkt_tab', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng', 'wordnet']; assert all(nltk.download(resource, quiet=True, raise_on_error=True) for resource in resources), 'NLTK resource installation failed'"

# Copy application code and package
COPY api/ /app/api/
COPY Step\ 12\ -\ Packaging/package/ /app/package/

# Ensure package is importable
ENV PYTHONPATH=/app/package:$PYTHONPATH
ENV ARTIFACTS_DIR=/app/package/mental_health_screening/artifacts
ENV SERVICE_VERSION=0.1.0
ENV PORT=8000
ENV HOST=0.0.0.0
ENV LOG_LEVEL=INFO

# Identity and storage. Authentication is Supabase Auth and screening history is
# Supabase Postgres, so there are no credentials baked into this image: the three
# SUPABASE_* values must be supplied at run time. The image starts and reports its
# configuration state through /health and /ready, and rejects authentication with
# 503 while they are missing, rather than pretending to be signed in.
#
#   SUPABASE_URL               https://<project>.supabase.co
#   SUPABASE_SECRET_KEY        secret / service_role key   (server only)
#   SUPABASE_PUBLISHABLE_KEY   publishable / anon key      (GoTrue requires it)
ENV MENTAL_AI_SESSION_TTL=3600

# Expose the service port
EXPOSE 8000

# Required capability check; bounded/freshness-aware, optional degradation visible.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import json, urllib.request; response = urllib.request.urlopen('http://localhost:8000/ready', timeout=5); assert json.load(response)['ready'] is True" || exit 1

# Start the API
CMD ["python", "-m", "uvicorn", "api.api:app", "--host", "0.0.0.0", "--port", "8000"]
