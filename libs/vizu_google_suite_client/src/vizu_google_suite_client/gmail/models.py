
from pydantic import BaseModel


class EmailMessage(BaseModel):
    id: str
    thread_id: str | None = None
    subject: str = ""
    sender: str = ""
    to: str = ""
    date: str = ""
    snippet: str = ""
    body: str = ""
    labels: list[str] = []

    def to_dict(self) -> dict:
        return self.model_dump()


class SendResult(BaseModel):
    message_id: str
    thread_id: str | None = None
