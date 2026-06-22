"""
main.py
-------------------------------------------------
FastAPI entry point for Online Medical Store & Rx Screening System
-------------------------------------------------
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from routes import router  # your single APIRouter

# ================================
# Create DB Tables (if not exist)
# ================================
models.Base.metadata.create_all(bind=engine)

# ================================
# FastAPI App Init
# ================================
app = FastAPI(
    title="Online Medical Store & Rx Screening API",
    description="Complete pharmacy + prescription + safety system",
    version="1.0.0"
)

# ================================
# CORS (Frontend support)
# ================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # production me specific domain rakhna
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
# Include Routes
# ================================
app.include_router(router)

# ================================
# Root Endpoint
# ================================
@app.get("/")
def root():
    return {
        "message": "API is running successfully 🚀",
        "status": "healthy"
    }

# ================================
# Health Check
# ================================
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "connected (if no error in startup)"
    }