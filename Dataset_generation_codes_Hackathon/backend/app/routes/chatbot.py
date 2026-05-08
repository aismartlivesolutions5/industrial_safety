from fastapi import APIRouter, HTTPException

from app.schemas import (
    ChatbotAskRequest,
    ChatbotAskResponse,
    ChatbotSummaryRequest,
    ChatbotSummaryResponse,
)
from app.services.chatbot_service import answer_question, generate_summary

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])


@router.post("/summary", response_model=ChatbotSummaryResponse)
def chatbot_summary(req: ChatbotSummaryRequest):
    try:
        summary = generate_summary(mode=req.mode)
        return {"summary": summary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate chatbot summary: {exc}")


@router.post("/ask", response_model=ChatbotAskResponse)
def chatbot_ask(req: ChatbotAskRequest):
    try:
        result = answer_question(req.question)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to answer chatbot question: {exc}")