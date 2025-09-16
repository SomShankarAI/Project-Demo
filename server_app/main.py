from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dotenv import load_dotenv
from typing import Dict
import uvicorn
from contextlib import asynccontextmanager

from ..shared.models import ChatMessage, ChatResponse, OnboardingState
from .workflow import OnboardingWorkflow

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store session states (in production, use Redis or database)
session_states: Dict[str, OnboardingState] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the workflow on startup
    logger.info("Starting up and initializing workflow...")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    app.state.workflow = await OnboardingWorkflow.create(openai_api_key)
    logger.info("Workflow initialized successfully.")

    yield

    # Clean up the workflow on shutdown
    logger.info("Shutting down and closing workflow...")
    await app.state.workflow.close()
    logger.info("Workflow closed successfully.")


# Initialize FastAPI app
app = FastAPI(title="LLM Onboarding Server", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "LLM Onboarding Server is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, request: Request):
    """Process chat message and return response"""
    try:
        workflow: OnboardingWorkflow = request.app.state.workflow

        # Get or create session state
        session_id = message.session_id or "default"
        current_state = session_states.get(session_id, OnboardingState())
        
        # Process message through workflow
        response, updated_state, completed = workflow.process_message(
            message.message, current_state
        )
        
        # Update session state
        session_states[session_id] = updated_state
        
        return ChatResponse(
            response=response,
            state=updated_state,
            completed=completed
        )
    
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/state", response_model=OnboardingState)
async def get_session_state(session_id: str):
    """Get current session state"""
    return session_states.get(session_id, OnboardingState())


@app.delete("/session/{session_id}")
async def reset_session(session_id: str):
    """Reset session state"""
    if session_id in session_states:
        del session_states[session_id]
    return {"message": "Session reset successfully"}


if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "localhost")
    port = int(os.getenv("SERVER_PORT", "8000"))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("server_app.main:app", host=host, port=port, reload=True)