from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class AskQuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class ConfigureApiKeyRequest(BaseModel):
    api_key: str

class DocumentFragment(BaseModel):
    text: str
    document_name: str
    score: float
    page_number: int = None
    text_position: dict = None

class AskQuestionResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]
