from pydantic import BaseModel, Field
from typing import Literal

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    status: Literal["needs_clarification", "completed", "error"] = Field(description="The status of the message")
    message: str = Field(description="The response of the model")
    bpmn_xml: str | None = Field(description="The BPMN 2.0 in a valid sintaxis")