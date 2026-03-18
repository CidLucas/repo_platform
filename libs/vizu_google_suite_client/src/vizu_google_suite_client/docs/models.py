from pydantic import BaseModel


class DocReadResult(BaseModel):
    document_id: str
    title: str
    body_text: str
    revision_id: str | None = None


class DocWriteResult(BaseModel):
    document_id: str
    title: str
    replies: int
