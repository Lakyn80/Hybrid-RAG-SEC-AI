from fastapi import APIRouter

from app.services.question_bank_service import build_question_bank

router = APIRouter()


@router.get("/api/question-bank")
def get_question_bank():
    return {
        "questions": build_question_bank(),
    }
