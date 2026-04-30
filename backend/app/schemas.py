from pydantic import BaseModel

class StatusUpdate(BaseModel):
    status: str


class RCACreate(BaseModel):
    root_cause: str
    fix: str