"""Syntax validation for generated BPMN 2.0 XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET

MODEL_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
REQUIRED_NAMESPACE_URIS = (MODEL_NS, BPMNDI_NS, DC_NS, DI_NS)

MAX_XML_BYTES = 1_000_000

FLOW_TAGS = (
    f"{{{MODEL_NS}}}sequenceFlow",
    f"{{{MODEL_NS}}}messageFlow",
)
DI_VISUAL_TAGS = (
    f"{{{BPMNDI_NS}}}BPMNShape",
    f"{{{BPMNDI_NS}}}BPMNEdge",
)
REFERENCE_ATTRIBUTES = {
    f"{{{MODEL_NS}}}participant": ("processRef",),
    f"{{{BPMNDI_NS}}}BPMNPlane": ("bpmnElement",),
}
REFERENCE_TEXT_TAGS = {
    f"{{{MODEL_NS}}}flowNodeRef", f"{{{MODEL_NS}}}incoming", f"{{{MODEL_NS}}}outgoing",
}


def validate_bpmn_syntax(xml: str | None) -> dict:
    """Return {"valid": bool, "errors": [{"code", "message"}]} for the given XML."""
    errors: list[dict[str, str]] = []
    root = _parse(xml, errors)
    if root is not None:
        _check_document(root, xml or "", errors)
        ids = _collect_ids(root, errors)
        _check_references(root, ids, errors)
    return {"valid": not errors, "errors": errors}


def _add_error(errors: list[dict[str, str]], code: str, message: str) -> None:
    errors.append({"code": code, "message": message})


def _parse(xml: str | None, errors: list[dict[str, str]]) -> ET.Element | None:
    if not xml or not xml.strip():
        _add_error(errors, "EMPTY_XML", "The BPMN XML is empty.")
        return None
    if len(xml.encode("utf-8")) > MAX_XML_BYTES:
        _add_error(errors, "XML_TOO_LARGE", "The BPMN XML exceeds the maximum allowed size.")
        return None
    upper = xml.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        _add_error(errors, "UNSAFE_XML", "DTD and entity declarations are not allowed.")
        return None
    try:
        return ET.fromstring(xml)
    except ET.ParseError as exc:
        _add_error(errors, "MALFORMED_XML", f"The XML is not well formed: {exc}")
        return None


def _check_document(root: ET.Element, raw: str, errors: list[dict[str, str]]) -> None:
    if root.tag != f"{{{MODEL_NS}}}definitions":
        _add_error(errors, "INVALID_ROOT", "The document root must be bpmn:definitions.")
        return
    if not root.get("targetNamespace"):
        _add_error(errors, "MISSING_TARGET_NAMESPACE", "definitions must declare targetNamespace.")
    for uri in REQUIRED_NAMESPACE_URIS:
        if uri not in raw:
            _add_error(errors, "MISSING_NAMESPACE", f"The required namespace {uri} is not declared.")
    if not any(child.tag == f"{{{MODEL_NS}}}process" for child in root):
        _add_error(errors, "MISSING_PROCESS", "The document must contain at least one bpmn:process.")
    has_plane = any(
        diagram.tag == f"{{{BPMNDI_NS}}}BPMNDiagram"
        and any(child.tag == f"{{{BPMNDI_NS}}}BPMNPlane" for child in diagram)
        for diagram in root
    )
    if not has_plane:
        _add_error(errors, "MISSING_DI", "The document must contain BPMNDiagram with a BPMNPlane.")


def _collect_ids(root: ET.Element, errors: list[dict[str, str]]) -> dict[str, ET.Element]:
    ids: dict[str, ET.Element] = {}
    for element in root.iter():
        element_id = element.get("id")
        if element_id is None:
            continue
        if element_id in ids:
            _add_error(errors, "DUPLICATE_ID", f"The id '{element_id}' is used more than once.")
        else:
            ids[element_id] = element
    return ids


def _check_references(
    root: ET.Element,
    ids: dict[str, ET.Element],
    errors: list[dict[str, str]],
) -> None:
    processes = {}
    for process in root.iter(f"{{{MODEL_NS}}}process"):
        for child in process.iter():
            if child.get("id"):
                processes[child.get("id")] = process.get("id")

    for element in root.iter():
        if element.tag in FLOW_TAGS:
            for attribute in ("sourceRef", "targetRef"):
                ref = element.get(attribute)
                if not ref or ref not in ids:
                    _add_error(
                        errors,
                        "DANGLING_REFERENCE",
                        f"{attribute} '{ref}' does not reference an existing id.",
                    )
            if element.tag == f"{{{MODEL_NS}}}sequenceFlow":
                source, target = element.get("sourceRef"), element.get("targetRef")
                if source in ids and target in ids:
                    source_process, target_process = processes.get(source), processes.get(target)
                    if source_process is None or target_process is None or source_process != target_process:
                        _add_error(errors, "INVALID_SEQUENCE_SCOPE", f"Sequence flow '{element.get('id')}' must connect nodes in the same process.")
        elif element.tag in DI_VISUAL_TAGS:
            ref = element.get("bpmnElement")
            if not ref or ref not in ids:
                _add_error(
                    errors,
                    "DANGLING_DI_REFERENCE",
                    f"bpmnElement '{ref}' does not reference an existing id.",
                )
        for attribute in REFERENCE_ATTRIBUTES.get(element.tag, ()):
            ref = element.get(attribute)
            # A black-box participant may omit processRef; a plane may not.
            if (ref or element.tag == f"{{{BPMNDI_NS}}}BPMNPlane") and ref not in ids:
                _add_error(errors, "DANGLING_REFERENCE", f"{attribute} '{ref}' does not reference an existing id.")
            elif ref in ids:
                allowed = ({f"{{{MODEL_NS}}}process"} if element.tag == f"{{{MODEL_NS}}}participant"
                           else {f"{{{MODEL_NS}}}process", f"{{{MODEL_NS}}}collaboration"})
                if ids[ref].tag not in allowed:
                    _add_error(errors, "INVALID_REFERENCE_TYPE", f"{attribute} '{ref}' references an invalid element type.")
        if element.tag in REFERENCE_TEXT_TAGS:
            ref = (element.text or "").strip()
            if ref not in ids:
                _add_error(errors, "DANGLING_REFERENCE", f"{element.tag.split('}')[-1]} '{ref}' does not reference an existing id.")
