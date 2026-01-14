from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
from dotenv import load_dotenv

from .routers import guests, categories, menu_items, orders, voice_sessions
from .database import get_db, create_tables

load_dotenv()

app = FastAPI(
    title="Hotel Voice AI Concierge API",
    description="REST API for hotel room service voice AI concierge system",
    version="1.0.0",
    redirect_slashes=False,  # Disable automatic slash redirects
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(guests.router, prefix="/api/v1/guests", tags=["guests"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(menu_items.router, prefix="/api/v1/menu-items", tags=["menu-items"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(voice_sessions.router, prefix="/api/v1/voice-sessions", tags=["voice-sessions"])

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    create_tables()

@app.get("/")
async def root():
    return {"message": "Hotel Voice AI Concierge API", "status": "active"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "hotel-voice-ai-concierge"}