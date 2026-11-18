"""Agent tool for BPMN syntax validation."""

from langchain_core.tools import tool

from app.services.bpmn_syntax import validate_bpmn_syntax


@tool
def validate_bpmn_tool(bpmn_xml: str) -> dict:
    """Validate that the BPMN 2.0 XML is syntactically correct.

    Call this tool with the final XML before answering with status
    'completed'. If it reports errors, fix the XML and call it again.
    """
    return validate_bpmn_syntax(bpmn_xml)
