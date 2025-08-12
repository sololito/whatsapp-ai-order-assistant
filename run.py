#!/usr/bin/env python3
"""
Run the SmartShopBot Telegram bot with an HTTP server.

This script starts both the Telegram bot and a simple HTTP server
that can be used for health checks and monitoring.
"""
import argparse
import asyncio
import os
import sys
import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from frontend.chat_interface import SmartShopBot

# Create FastAPI app
app = FastAPI(title="SmartShopBot API",
              description="API for SmartShopBot Telegram bot",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "service": "smartshopbot"}
    )

# Import the M-Pesa callback router
from backend.mpesa_callback import router as mpesa_router

# Include the M-Pesa router
app.include_router(mpesa_router, prefix="/api/v1")
app.include_router(mpesa_router, prefix="/api/v1", tags=["M-Pesa"])

@app.get("/health")
async def health():
    """Health check endpoint with more details."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "smartshopbot",
            "version": "1.0.0",
            "environment": os.getenv("ENV", "development")
        }
    )

def start_server(port: int):
    """Start the FastAPI server."""
    logger.info(f"Starting HTTP server on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the SmartShopBot Telegram bot with HTTP server')
    parser.add_argument('--port', type=int, default=8000,
                       help='Port to run the HTTP server on (default: 8000)')
    return parser.parse_args()

async def run_bot():
    """Initialize and run the Telegram bot."""
    bot = SmartShopBot()
    logger.info("Starting SmartShopBot...")
    # Since we're running in an async context, we'll use polling
    await bot.run()

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    try:
        # Start the HTTP server in a separate thread
        server_thread = threading.Thread(
            target=start_server,
            args=(args.port,),
            daemon=True
        )
        server_thread.start()
        
        # Run the bot in the main thread
        logger.info("SmartShopBot is running. Press Ctrl+C to stop.")
        asyncio.run(run_bot())
        
    except KeyboardInterrupt:
        logger.info("Shutting down SmartShopBot...")
    except Exception as e:
        logger.error(f"Error starting SmartShopBot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
