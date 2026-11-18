from pydantic import BaseModel, Field
from typing import Literal

class ChatRequest(BaseModel):
    session_id: str
    model: str | None = None
    provider: Literal["openrouter", "openai"] = "openrouter"
    message: str

class ChatResponse(BaseModel):
    status: Literal["needs_clarification", "completed", "error"] = Field(description="The status of the message")
    message: str = Field(description="The response of the model")
    bpmn_xml: str | None = Field(description="The BPMN 2.0 in a valid sintaxis")
    layout_plan: str | None = Field(
        default=None,
        description="Short layout plan (main-path trace, column table, pool/lane order). Debug only; the frontend ignores it.",
    )

class Clarification(BaseModel):
    """Salida del agente aclarador: ¿alcanza la info para modelar?"""

    enough_info: bool = Field(description="True when the conversation has everything needed to model the process")
    questions: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="At most 3 clarification questions, in the user's language, empty when enough_info",
    )

class BpmnDraft(BaseModel):
    """Salida del agente creador: XML (o el motivo por el que no lo produjo)."""

    bpmn_xml: str | None = Field(
        default=None,
        description="The complete BPMN 2.0 XML with BPMN-DI, or null when it could not be produced",
    )
    message: str = Field(description="User-facing summary in business language (or the failure explanation)")
    layout_plan: str | None = Field(
        default=None,
        description="Short layout plan: numbered main-path trace, column table, pool/lane order. Null unless bpmn_xml is present",
    )
    failure_reason: Literal["missing_info", "layout_unsolvable"] | None = Field(
        default=None,
        description="Why no XML was produced: essential information is missing, or the layout rules cannot be met",
    )
    missing_info: list[str] = Field(
        default_factory=list,
        description="The concrete gaps, in the user's language, only when failure_reason is missing_info",
    )