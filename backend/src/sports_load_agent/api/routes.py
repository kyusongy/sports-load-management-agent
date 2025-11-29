"""
API routes for the sports load management agent.

Provides endpoints for file upload, processing, chat, and result retrieval.
"""

import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from sports_load_agent.agent_graph import create_graph
from sports_load_agent.agent_state import create_initial_state
from sports_load_agent.chat_agent import get_or_create_chat_agent, remove_chat_agent
from sports_load_agent.settings import OUTPUTS_DIR, UPLOADS_DIR
from sports_load_agent.utils.llm_factory import LLMFactory


router = APIRouter()

# In-memory session storage (for demo purposes - use Redis/DB in production)
_sessions: Dict[str, Dict[str, Any]] = {}


class ProcessResponse(BaseModel):
    """Response model for process endpoint."""

    session_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    session_id: str
    status: str
    current_stage: Optional[str] = None
    error_message: Optional[str] = None


class ResultsResponse(BaseModel):
    """Response model for results endpoint."""

    session_id: str
    status: str
    report_markdown: Optional[str] = None
    visualization_files: List[str] = []
    processed_csv_path: Optional[str] = None
    processed_excel_path: Optional[str] = None
    token_usage: Dict[str, int] = {}
    error_message: Optional[str] = None


class UploadResponse(BaseModel):
    """Response model for upload endpoint."""

    session_id: str
    uploaded_files: List[str]
    message: str


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    session_id: str
    response: str
    tool_calls: List[Dict[str, Any]] = []
    generated_files: List[str] = []
    error: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Response model for chat history endpoint."""

    session_id: str
    history: List[Dict[str, Any]]


@router.post("/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)) -> UploadResponse:
    """
    Upload one or more CSV files for processing.

    Args:
        files: List of CSV files to upload.

    Returns:
        Session ID and list of uploaded file paths.
    """
    session_id = str(uuid.uuid4())
    session_dir = UPLOADS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    uploaded_paths = []

    for file in files:
        if not file.filename:
            continue

        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only CSV files are supported.",
            )

        # Save file
        file_path = session_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        uploaded_paths.append(str(file_path))
        logger.info(f"Uploaded: {file_path}")

    if not uploaded_paths:
        raise HTTPException(status_code=400, detail="No valid files uploaded")

    # Store session info
    _sessions[session_id] = {
        "uploaded_files": uploaded_paths,
        "status": "uploaded",
        "state": None,
    }

    return UploadResponse(
        session_id=session_id,
        uploaded_files=uploaded_paths,
        message=f"Successfully uploaded {len(uploaded_paths)} file(s)",
    )


@router.post("/process/{session_id}", response_model=ProcessResponse)
async def process_files(session_id: str) -> ProcessResponse:
    """
    Start processing uploaded files through the LangGraph workflow.

    Args:
        session_id: Session ID from upload.

    Returns:
        Processing status.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]

    if session["status"] not in ["uploaded", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot process session in status: {session['status']}",
        )

    uploaded_files = session["uploaded_files"]

    try:
        logger.info(f"Starting processing for session {session_id}")
        session["status"] = "processing"

        # Create initial state
        initial_state = create_initial_state(session_id, uploaded_files)

        # Create and run graph
        graph = create_graph(session_id)

        # Run the graph (no checkpointing for single-pass workflow)
        final_state = graph.invoke(initial_state)

        # Store final state
        session["state"] = final_state
        session["status"] = final_state.get("status", "completed")

        logger.info(f"Processing complete for session {session_id}: {session['status']}")

        return ProcessResponse(
            session_id=session_id,
            status=session["status"],
            message="Processing complete" if session["status"] == "completed" else "Processing failed",
        )

    except Exception as e:
        logger.exception(f"Processing failed for session {session_id}: {e}")
        session["status"] = "failed"
        session["error"] = str(e)

        return ProcessResponse(
            session_id=session_id,
            status="failed",
            message=f"Processing error: {str(e)}",
        )


@router.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str) -> StatusResponse:
    """
    Get processing status for a session.

    Args:
        session_id: Session ID.

    Returns:
        Current processing status.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    state = session.get("state", {})

    return StatusResponse(
        session_id=session_id,
        status=session["status"],
        current_stage=state.get("current_stage") if state else None,
        error_message=state.get("error_message") if state else session.get("error"),
    )


@router.get("/results/{session_id}", response_model=ResultsResponse)
async def get_results(session_id: str) -> ResultsResponse:
    """
    Get processing results for a session.

    Args:
        session_id: Session ID.

    Returns:
        Processing results including report and file paths.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    state = session.get("state", {})

    if not state:
        return ResultsResponse(
            session_id=session_id,
            status=session["status"],
            error_message="No results available yet",
        )

    # Convert file paths to download URLs
    viz_files = state.get("visualization_files", [])
    viz_urls = [f"/api/download/{session_id}/{Path(f).name}" for f in viz_files]

    csv_path = state.get("processed_csv_path")
    excel_path = state.get("processed_excel_path")

    return ResultsResponse(
        session_id=session_id,
        status=state.get("status", "unknown"),
        report_markdown=state.get("report_markdown"),
        visualization_files=viz_urls,
        processed_csv_path=f"/api/download/{session_id}/{Path(csv_path).name}" if csv_path else None,
        processed_excel_path=f"/api/download/{session_id}/{Path(excel_path).name}" if excel_path else None,
        token_usage=state.get("token_usage", {}),
        error_message=state.get("error_message"),
    )


@router.get("/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str) -> FileResponse:
    """
    Download a generated file.

    Args:
        session_id: Session ID.
        filename: Name of file to download.

    Returns:
        File download response.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check outputs directory
    file_path = OUTPUTS_DIR / filename
    if file_path.exists():
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/octet-stream",
        )

    # Check session-specific output
    session_output = OUTPUTS_DIR / session_id / filename
    if session_output.exists():
        return FileResponse(
            path=str(session_output),
            filename=filename,
            media_type="application/octet-stream",
        )

    raise HTTPException(status_code=404, detail="File not found")


@router.get("/token-stats")
async def get_token_stats() -> Dict[str, Any]:
    """
    Get global token usage statistics.

    Returns:
        Token usage statistics.
    """
    return LLMFactory.get_global_stats()


@router.get("/token-stats/{session_id}")
async def get_session_token_stats(session_id: str) -> Dict[str, Any]:
    """
    Get token usage statistics for a specific session.

    Args:
        session_id: Session ID.

    Returns:
        Session token usage statistics.
    """
    stats = LLMFactory.get_session_stats(session_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Session token stats not found")
    return stats


@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """
    Delete a session and its associated files.

    Args:
        session_id: Session ID.

    Returns:
        Deletion confirmation.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Clean up uploads
    session_dir = UPLOADS_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)

    # Clean up token tracker
    LLMFactory.clear_session_tracker(session_id)

    # Clean up chat agent
    remove_chat_agent(session_id)

    # Remove from sessions
    del _sessions[session_id]

    return {"message": f"Session {session_id} deleted"}


# ============================================================================
# Chat Endpoints - Conversational Tool-Calling Interface
# ============================================================================


@router.post("/chat/{session_id}", response_model=ChatResponse)
async def chat(session_id: str, request: ChatRequest) -> ChatResponse:
    """
    Send a message to the conversational agent and get a response.

    The agent uses Claude Sonnet 4.5 with tool calling to:
    - Query processed training load data
    - Generate visualizations on demand
    - Provide insights about athlete load and injury risk

    Args:
        session_id: Session ID (must have completed data processing).
        request: Chat request with user message.

    Returns:
        Agent response with any tool calls and generated files.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    state = session.get("state")

    if not state or state.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail="Data processing must be completed before using chat. "
            "Please call /process/{session_id} first.",
        )

    processed_data = state.get("processed_data")
    if processed_data is None:
        raise HTTPException(
            status_code=400,
            detail="No processed data available for this session.",
        )

    try:
        # Get or create chat agent for this session
        agent = get_or_create_chat_agent(session_id, processed_data)

        # Process the chat message
        result = agent.chat(request.message)

        # Convert file paths to download URLs
        generated_urls = []
        for file_path in result.get("generated_files", []):
            filename = Path(file_path).name
            generated_urls.append(f"/api/download/{session_id}/{filename}")

        return ChatResponse(
            session_id=session_id,
            response=result["response"],
            tool_calls=result.get("tool_calls", []),
            generated_files=generated_urls,
            error=result.get("error"),
        )

    except ValueError as e:
        # Handle missing API key or configuration errors
        logger.error(f"Chat configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.exception(f"Chat error for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}",
        )


@router.get("/chat/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str) -> ChatHistoryResponse:
    """
    Get the conversation history for a session.

    Args:
        session_id: Session ID.

    Returns:
        List of messages in the conversation.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    state = session.get("state")

    if not state or state.get("status") != "completed":
        return ChatHistoryResponse(session_id=session_id, history=[])

    processed_data = state.get("processed_data")
    if processed_data is None:
        return ChatHistoryResponse(session_id=session_id, history=[])

    try:
        agent = get_or_create_chat_agent(session_id, processed_data)
        history = agent.get_history()

        return ChatHistoryResponse(
            session_id=session_id,
            history=history,
        )

    except Exception as e:
        logger.exception(f"Error getting chat history: {e}")
        return ChatHistoryResponse(session_id=session_id, history=[])


@router.delete("/chat/{session_id}/history")
async def clear_chat_history(session_id: str) -> Dict[str, str]:
    """
    Clear the conversation history for a session.

    This resets the chat agent while keeping the processed data available.

    Args:
        session_id: Session ID.

    Returns:
        Confirmation message.
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]
    state = session.get("state")

    if state and state.get("status") == "completed":
        processed_data = state.get("processed_data")
        if processed_data:
            try:
                agent = get_or_create_chat_agent(session_id, processed_data)
                agent.clear_history()
            except Exception as e:
                logger.warning(f"Error clearing chat history: {e}")

    return {"message": f"Chat history cleared for session {session_id}"}


__all__ = ["router"]

