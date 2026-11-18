"""Code-driven routing between the business-process agents."""

import json
import logging
from functools import lru_cache
from time import perf_counter
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, ValidationError

from app.agents.bpmn_creator import get_bpmn_creator
from app.agents.bpmn_validator import get_bpmn_validator
from app.agents.clarifier import get_clarifier
from app.agents.model_config import DEFAULT_PROVIDER, resolve_model
from app.agents.process_analyst import get_process_analyst
from app.models.chat_request import ChatResponse
from app.models.process import AnalystProcessGraph, ClarifierResult
from app.services.bpmn_syntax import validate_bpmn_syntax
from app.services.bpmn_layout import check_and_repair_layout, semantic_signature
from app.services.bpmn_fidelity import validate_graph_fidelity

logger = logging.getLogger("app.orchestrator")

MAX_REPAIRS = 2

# All graph instances share conversation threads; the frontend session ID is the thread ID.
checkpointer = InMemorySaver()


class OrchestratorState(TypedDict, total=False):
    # Only user-visible turns persist. Agent-to-agent context is ephemeral per node.
    messages: Annotated[list, add_messages]
    request_id: str

    analysis: dict | None
    analysis_error: str | None
    process_spec: dict | None
    clarification: dict | None
    clarification_error: str | None
    draft: dict | None
    validation_errors: list[str] | None
    layout_warnings: list[str] | None
    repair_attempts: int
    review_attempts: int
    fallback_draft: dict | None
    response: ChatResponse | None


def _as_dict(structured: object) -> dict:
    """Normalize a Pydantic model or mapping to a plain dictionary."""
    if isinstance(structured, BaseModel):
        return structured.model_dump()
    return dict(structured or {})


def _timed_node(name: str, node):
    """Log elapsed time for each graph node without logging its contents."""
    async def run(state: OrchestratorState) -> dict:
        started = perf_counter()
        try:
            return await node(state)
        finally:
            logger.info(
                "node_timing request_id=%s node=%s elapsed_ms=%.1f",
                state.get("request_id", "unknown"),
                name,
                (perf_counter() - started) * 1000,
            )

    return run


def build_orchestrator(model_name: str | None = None, provider: str = DEFAULT_PROVIDER):
    """Build the graph with the clarifier, analyst, creator and validator."""
    model_name = resolve_model(model_name, provider)
    creator = get_bpmn_creator(model_name, provider)
    validator = get_bpmn_validator(model_name, provider)
    analyst = get_process_analyst(model_name, provider)
    clarifier = get_clarifier(model_name, provider)
    async def analyze(state: OrchestratorState) -> dict:
        """Build a connected process graph from the Clarifier's textual summary."""
        summary = (state.get("clarification") or {}).get("message", "")
        inputs: list[BaseMessage] = [
            HumanMessage(
                content=(
                    "Clarifier's confirmed business-process summary:\n\n"
                    + summary
                )
            ),
        ]
        try:
            result = await analyst.ainvoke({"messages": inputs})
            structured = result.get("structured_response")
            if structured is None:
                raise ValueError("process analyst returned no structured_response")

            analyst_payload = _as_dict(structured)
            try:
                analyst_graph = AnalystProcessGraph.model_validate(analyst_payload)
                
            except (ValidationError, ValueError) as validation_error:
                logger.warning(
                    "analyze: graph validation failed; asking analyst to repair once | error=%s",
                    validation_error,
                )
                repair_message = HumanMessage(
                    content=(
                        "Correct the invalid AnalystProcessGraph below. Preserve "
                        "the business facts and make only changes needed to fix "
                        "the validator error. In particular, message connections "
                        "must join existing activity objects in different pools. "
                        "Return the complete corrected AnalystProcessGraph.\n\n"
                        "Original business-process summary:\n"
                        + summary
                        + "\n\nInvalid AnalystProcessGraph JSON:\n"
                        + json.dumps(analyst_payload, ensure_ascii=False, indent=2)
                        + "\n\nOrchestrator validation error:\n"
                        + str(validation_error)
                    )
                )
                repair_result = await analyst.ainvoke({"messages": [repair_message]})
                repair_structured = repair_result.get("structured_response")
                if repair_structured is None:
                    raise ValueError("process analyst returned no repaired structured_response")
                analyst_graph = AnalystProcessGraph.model_validate(
                    _as_dict(repair_structured)
                )
                
                logger.info("analyze: graph repair passed validation")

            process_spec = analyst_graph.model_dump()
            analysis = {"process": process_spec}
        except Exception:
            logger.exception("process analyst failed; refusing to create from raw chat")
            return {
                "analysis": None,
                "analysis_error": "process analyst failed",
                "process_spec": None,
                "clarification": None,
                "clarification_error": None,
                "draft": None,
                "validation_errors": None,
            }

        updates: dict = {
            "analysis": analysis,
            "analysis_error": None,
            "process_spec": process_spec,
            "clarification": None,
            "clarification_error": None,
            "draft": None,
            "validation_errors": None,
            "layout_warnings": None,
            "repair_attempts": 0,
            "review_attempts": 0,
            "fallback_draft": None,
        }
        logger.info("analyze: detailed process graph is ready; going to the creator")
        return updates

    async def clarify(state: OrchestratorState) -> dict:
        """Route a user-facing response or a business summary to the analyst."""
        try:
            result = await clarifier.ainvoke({"messages": state["messages"]})
            structured = result.get("structured_response")
            if structured is None:
                raise ValueError("clarifier returned no structured response")
            clarification = ClarifierResult.model_validate(structured).model_dump()
            message = clarification["message"].strip()
            questions = [question.strip() for question in clarification["questions"]]
            if any(not question for question in questions):
                raise ValueError("clarifier returned an empty question")
            if clarification["recipient"] == "analyst" and (not message or questions):
                raise ValueError("clarifier returned an invalid analyst handoff")
            if clarification["recipient"] == "client" and not message and not questions:
                raise ValueError("clarifier returned an empty client response")
            clarification["message"] = message
            clarification["questions"] = questions
        except Exception:
            logger.exception("clarifier failed; refusing to analyze an invalid handoff")
            return {
                "clarification": None,
                "clarification_error": "clarifier failed",
                "analysis_error": None,
            }

        logger.info(
            "clarify: recipient=%s questions=%d",
            clarification["recipient"],
            len(clarification["questions"]),
        )
        return {
            "clarification": clarification,
            "clarification_error": None,
            "analysis_error": None,
        }

    async def respond_clarification(state: OrchestratorState) -> dict:
        """Terminal response containing questions for the user."""
        clarification = state.get("clarification") or {}
        questions = clarification.get("questions") or []
        parts = [clarification.get("message", "").strip()]
        if questions:
            parts.append("\n".join(f"- {question}" for question in questions))
        message = "\n\n".join(part for part in parts if part)
        logger.info("respond_clarification: %d questions", len(questions))
        return {
            "response": ChatResponse(
                status="needs_clarification", message=message, bpmn_xml=None
            ),
            "messages": [AIMessage(content=message)],
            "draft": None,
            "validation_errors": None,
            "analysis": None,
            "process_spec": None,
            "clarification": None,
        }

    async def create(state: OrchestratorState) -> dict:
        """Create BPMN using the analyst's graph, retrying if no XML is produced."""
        attempts = state.get("repair_attempts", 0) + 1
        process_spec = state.get("process_spec") or {}
        inputs: list[BaseMessage] = [
            HumanMessage(
                content=(
                    "AnalystProcessGraph (JSON):\n"
                    + json.dumps(process_spec, ensure_ascii=False, indent=2)
                )
            )
        ]

        if attempts > 1:
            previous = state.get("draft") or {}
            inputs.append(
                HumanMessage(
                    content="The previous attempt produced no XML. Generate the complete BPMN XML "
                    "now using a simple spacious layout. Imperfect geometry is acceptable; "
                    "the separate validator can repair it. Do not omit process elements.\n"
                    "Previous explanation: " + str(previous.get("message") or "none")
                )
            )

        try:
            result = await creator.ainvoke({"messages": inputs})
            structured = result.get("structured_response")
        except Exception:
            logger.exception("creator failed on attempt %d", attempts)
            result, structured = {}, None

        if structured is None:
            last = result.get("messages", [])[-1:] and result["messages"][-1]
            logger.error(
                "creator: no structured_response (attempt %d) | last=%s finish=%s tool_calls=%s content=%r",
                attempts,
                type(last).__name__ if last else None,
                getattr(last, "response_metadata", {}).get("finish_reason"),
                getattr(last, "tool_calls", None),
                str(getattr(last, "content", ""))[:300],
            )
            draft = {
                "bpmn_xml": None,
                "message": "No pude generar el diagrama. Probá de nuevo en un momento.",
                "layout_plan": None,
                "failure_reason": None,
                "missing_info": [],
            }
        else:
            draft = _as_dict(structured)

        logger.info(
            "create: attempt %d | failure_reason=%s | xml=%s",
            attempts,
            draft.get("failure_reason"),
            bool(draft.get("bpmn_xml")),
        )
        return {
            "draft": draft,
            "repair_attempts": attempts,
            "validation_errors": None,
        }

    async def validate(state: OrchestratorState) -> dict:
        """Validate syntax, fidelity and DI; repair geometric routes deterministically."""
        def check(draft):
            draft = dict(draft)
            xml = draft.get("bpmn_xml")
            result = validate_bpmn_syntax(xml)
            errors = [error["message"] for error in result.get("errors", [])]
            warnings = []
            if not errors and xml:
                xml, layout_errors, warnings = check_and_repair_layout(xml)
                draft["bpmn_xml"] = xml
                errors.extend(layout_errors)
                errors.extend(validate_graph_fidelity(xml, state.get("process_spec") or {}))
            return draft, errors, warnings

        draft, errors, warnings = check(state.get("draft") or {})
        fallback = state.get("fallback_draft")
        if errors and fallback:
            logger.warning("validator candidate failed checks; retaining last valid draft")
            draft, errors, warnings = check(fallback)
        logger.info("validate: errors=%d layout_warnings=%d", len(errors), len(warnings))
        if errors or warnings:
            logger.warning("validate: diagnostics=%s", (errors + warnings)[:10])
        return {"draft": draft, "validation_errors": errors, "layout_warnings": warnings}

    async def review(state: OrchestratorState) -> dict:
        """Have the separate validator review or repair the exact previous XML."""
        attempts = state.get("review_attempts", 0) + 1
        draft = state.get("draft") or {}
        errors = state.get("validation_errors") or []
        warnings = state.get("layout_warnings") or []
        fallback = state.get("fallback_draft") or (dict(draft) if not errors else None)
        prompt = (
            "AnalystProcessGraph (JSON):\n"
            + json.dumps(state.get("process_spec") or {}, ensure_ascii=False, indent=2)
            + "\n\nXML to review and repair:\n" + (draft.get("bpmn_xml") or "")
            + "\n\nBlocking errors:\n" + ("\n".join(errors) or "None")
            + "\n\nLayout warnings:\n" + ("\n".join(warnings) or "None")
        )
        candidate = None
        try:
            result = await validator.ainvoke({"messages": [HumanMessage(content=prompt)]})
            if result.get("structured_response") is not None:
                candidate = _as_dict(result["structured_response"])
        except Exception:
            logger.exception("diagram validator failed on attempt %d", attempts)
        if not candidate or not candidate.get("bpmn_xml"):
            logger.warning("diagram validator returned no XML; retaining previous draft")
            candidate = draft
        elif not errors and semantic_signature(candidate["bpmn_xml"]) != semantic_signature(draft["bpmn_xml"]):
            logger.warning("diagram validator changed business semantics; rejecting candidate")
            candidate = draft
        else:
            candidate["message"] = draft.get("message") or candidate.get("message", "")
            candidate["layout_plan"] = draft.get("layout_plan")
        return {"draft": candidate, "review_attempts": attempts, "fallback_draft": fallback}

    async def respond_completed(state: OrchestratorState) -> dict:
        """Terminal success response."""
        draft = state.get("draft") or {}
        logger.info("respond_completed: xml len=%d", len(draft.get("bpmn_xml") or ""))
        message = draft.get("message", "")
        warnings = state.get("layout_warnings") or []
        if any("no safe Manhattan route" in warning for warning in warnings):
            message += "\n\nNo pude asegurar una ruta ortogonal sin cruces con nodos para todas las conexiones; revisá el diagrama."
        elif warnings:
            message += "\n\nEl diagrama puede tener detalles visuales que requieran ajuste."
        return {
            "response": ChatResponse(
                status="completed",
                message=message,
                bpmn_xml=draft.get("bpmn_xml"),
                layout_plan=draft.get("layout_plan"),
            ),
            "messages": [AIMessage(content=message)],
            "repair_attempts": 0,
            "review_attempts": 0,
            "fallback_draft": None,
            "layout_warnings": None,
            "draft": None,
            "validation_errors": None,
            "analysis": None,
            "process_spec": None,
            "clarification": None,
        }

    async def respond_error(state: OrchestratorState) -> dict:
        """Terminal error response for failed agents or unresolved basic gaps."""
        draft = state.get("draft") or {}
        if state.get("analysis_error"):
            message = "No pude organizar la información del proceso. Probá de nuevo en un momento."
        elif state.get("clarification_error"):
            message = "No pude formular las preguntas de aclaración. Probá de nuevo en un momento."
        elif draft.get("failure_reason") == "layout_unsolvable" and draft.get("message"):
            message = draft["message"]
        elif state.get("validation_errors"):
            message = (
                "No pude generar un diagrama válido para este proceso después de "
                "intentar corregirlo. Probá de nuevo en un momento."
            )
        else:
            message = "No pude generar el diagrama. Probá de nuevo en un momento."

        logger.info("respond_error: reason=%s", draft.get("failure_reason"))
        return {
            "response": ChatResponse(status="error", message=message, bpmn_xml=None),
            "messages": [AIMessage(content=message)],
            "repair_attempts": 0,
            "review_attempts": 0,
            "fallback_draft": None,
            "layout_warnings": None,
            "draft": None,
            "validation_errors": None,
            "analysis": None,
            "process_spec": None,
            "clarification": None,
        }

    def after_analyze(state: OrchestratorState) -> str:
        if state.get("analysis_error"):
            return "respond_error"
        analysis = state.get("analysis") or {}
        if not analysis:
            return "respond_error"
        return "create"

    def after_clarify(state: OrchestratorState) -> str:
        if state.get("clarification_error"):
            return "respond_error"
        clarification = state.get("clarification") or {}
        if clarification.get("recipient") == "analyst":
            return "analyze"
        if clarification.get("recipient") == "client":
            return "respond_clarification"
        return "respond_error"

    def after_create(state: OrchestratorState) -> str:
        draft = state.get("draft") or {}
        if not draft.get("bpmn_xml"):
            return "create" if state.get("repair_attempts", 0) < MAX_REPAIRS else "respond_error"
        return "validate"

    def after_validate(state: OrchestratorState) -> str:
        if not state.get("review_attempts"):
            return "review"
        if not state.get("validation_errors"):
            return "respond_completed"
        if state.get("review_attempts", 0) >= MAX_REPAIRS:
            return "respond_error"
        return "review"

    graph = StateGraph(OrchestratorState)
    graph.add_node("analyze", _timed_node("analyze", analyze))
    graph.add_node("clarify", _timed_node("clarify", clarify))
    graph.add_node(
        "respond_clarification",
        _timed_node("respond_clarification", respond_clarification),
    )
    graph.add_node("create", _timed_node("create", create))
    graph.add_node("validate", _timed_node("validate", validate))
    graph.add_node("review", _timed_node("review", review))
    graph.add_node("respond_completed", _timed_node("respond_completed", respond_completed))
    graph.add_node("respond_error", _timed_node("respond_error", respond_error))

    graph.add_edge(START, "clarify")
    graph.add_conditional_edges(
        "analyze", after_analyze, ["respond_error", "create"]
    )
    graph.add_conditional_edges(
        "clarify", after_clarify, ["analyze", "respond_clarification", "respond_error"]
    )
    graph.add_conditional_edges("create", after_create, ["create", "respond_error", "validate"])
    graph.add_conditional_edges(
        "validate", after_validate, ["respond_completed", "respond_error", "review"]
    )
    graph.add_edge("review", "validate")
    graph.add_edge("respond_clarification", END)
    graph.add_edge("respond_completed", END)
    graph.add_edge("respond_error", END)

    return graph.compile(checkpointer=checkpointer)


@lru_cache(maxsize=16)
def get_orchestrator(model_name: str | None = None, provider: str = DEFAULT_PROVIDER):
    """Return a graph cached by the selected model and provider."""
    return build_orchestrator(resolve_model(model_name, provider), provider)
