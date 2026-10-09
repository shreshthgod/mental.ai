"""Existing Vercel service entrypoint; same authenticated application at /api."""
from fastapi import FastAPI
from api.api import app as screening_app

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/api', screening_app)
