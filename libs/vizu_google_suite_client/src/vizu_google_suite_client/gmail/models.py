from pydantic import BaseModel
from typing import List, Optional


class EmailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    subject: str = ""
    sender: str = ""
    to: str = ""
    date: str = ""
    snippet: str = ""
    body: str = ""
    labels: List[str] = []

    def to_dict(self) -> dict:
        return self.model_dump()


class SendResult(BaseModel):
    message_id: str
    thread_id: Optional[str] = None
