"""AI workspace: task services (rewrite, continue, summarize) + thread chat.

Exposes AiTaskService, AiThreadService, and RewriteService from the container.
Long-running AI calls are synchronous with extended timeout (handled by frontend).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import get_container
from writer.app.container import AppContainer
from writer.domain.models.ai_thread import AiThread as DomainThread
from writer.services.ai.task_types import AiTaskType

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ---- DTOs ----
class AiTaskRequest(BaseModel):
    task_type: str  # 'rewrite', 'continue', 'summarize', etc.
    text: str
    instructions: Optional[str] = None
    context: Optional[str] = None


class AiTaskResponse(BaseModel):
    result: str
    task_type: str


class ThreadOut(BaseModel):
    id: str
    title: str
    created_at: Optional[str]
    updated_at: Optional[str]


class ThreadCreate(BaseModel):
    title: str = "New Conversation"


class MessageOut(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str]


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ChatResponse(BaseModel):
    thread_id: str
    user_message: MessageOut
    assistant_message: MessageOut


def _thread_to_dto(t: DomainThread) -> ThreadOut:
    return ThreadOut(
        id=t.id,
        title=t.title,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# ---- Task endpoints (synchronous, long timeout) ----
@router.post("/task", response_model=AiTaskResponse)
def run_ai_task(
    request: AiTaskRequest,
    container: AppContainer = Depends(get_container),
) -> AiTaskResponse:
    """Run an AI task (rewrite, continue, summarize, etc).

    This is SYNCHRONOUS and may take 30-120s. The frontend must set a long
    timeout when calling this endpoint.
    """
    task_type_map = {
        'polish': AiTaskType.POLISH,
        'rewrite': AiTaskType.REWRITE,
        'expand': AiTaskType.EXPAND,
        'continue': AiTaskType.CONTINUE_WRITING,
        'style_transfer': AiTaskType.STYLE_TRANSFER,
        'summarize': AiTaskType.SUMMARIZE,
        'outline': AiTaskType.OUTLINE,
        'title': AiTaskType.TITLE,
        'structure_diagnose': AiTaskType.STRUCTURE_DIAGNOSE,
        'consistency_check': AiTaskType.CONSISTENCY_CHECK,
    }
    task_enum = task_type_map.get(request.task_type)
    if not task_enum:
        raise HTTPException(400, f"Unknown task_type: {request.task_type}")

    try:
        result = container.ai_task_service.run_task(
            task_type=task_enum,
            text=request.text,
            instructions=request.instructions,
            context=request.context,
        )
        return AiTaskResponse(result=result, task_type=request.task_type)
    except Exception as e:
        raise HTTPException(500, f"AI task failed: {str(e)}")


# ---- Thread management ----
@router.get("/threads", response_model=list[ThreadOut])
def list_threads(
    container: AppContainer = Depends(get_container),
) -> list[ThreadOut]:
    threads = container.ai_thread_repository.list_recent(limit=50)
    return [_thread_to_dto(t) for t in threads]


@router.post("/threads", response_model=ThreadOut, status_code=201)
def create_thread(
    data: ThreadCreate,
    container: AppContainer = Depends(get_container),
) -> ThreadOut:
    thread = container.ai_thread_repository.create(title=data.title)
    return _thread_to_dto(thread)


@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(
    thread_id: str,
    container: AppContainer = Depends(get_container),
):
    success = container.ai_thread_repository.delete(thread_id)
    if not success:
        raise HTTPException(404, "Thread not found")


# ---- Chat (synchronous) ----
@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    container: AppContainer = Depends(get_container),
) -> ChatResponse:
    """Send a message to a thread and get the assistant's reply.

    Synchronous. May take 10-60s depending on the model.
    """
    try:
        # Store user message
        thread = container.ai_thread_repository.get(request.thread_id)
        if not thread:
            raise HTTPException(404, "Thread not found")

        # Call AI service (this is where the long blocking call happens)
        response = container.ai_thread_service.send_message(
            thread_id=request.thread_id,
            user_message=request.message,
        )

        return ChatResponse(
            thread_id=request.thread_id,
            user_message=MessageOut(
                role="user",
                content=request.message,
                timestamp=None,
            ),
            assistant_message=MessageOut(
                role="assistant",
                content=response,
                timestamp=None,
            ),
        )
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {str(e)}")
