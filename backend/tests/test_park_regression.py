import asyncio
import xml.etree.ElementTree as ET
from uuid import uuid4

import app.agents.orchestrator as orchestrator
from app.models.chat_request import BpmnDraft
from app.services.bpmn_fidelity import validate_graph_fidelity
from app.services.bpmn_syntax import validate_bpmn_syntax
from app.services.bpmn_layout import (
    BPMNDI_NS, DC_NS, DI_NS, MODEL_NS, NODE_TAGS, _overlap, _segment_problem, check_and_repair_layout,
)
from park_fixture import PARK_REQUEST, park_graph, park_xml


class Agent:
    def __init__(self, *responses):
        self.responses = responses
        self.calls = []

    async def ainvoke(self, payload):
        self.calls.append(payload)
        response = self.responses[min(len(self.calls) - 1, len(self.responses) - 1)]
        if isinstance(response, Exception):
            raise response
        return {"structured_response": response}


def draft(xml, message="Armé el diagrama del parque."):
    return BpmnDraft(bpmn_xml=xml, message=message)


def setup(monkeypatch, creator, validator, analyst=None):
    clarifier = Agent({"recipient": "analyst", "message": PARK_REQUEST, "questions": []})
    analyst = analyst or Agent(park_graph())
    monkeypatch.setattr(orchestrator, "get_clarifier", lambda *_: clarifier)
    monkeypatch.setattr(orchestrator, "get_process_analyst", lambda *_: analyst)
    monkeypatch.setattr(orchestrator, "get_bpmn_creator", lambda *_: creator)
    monkeypatch.setattr(orchestrator, "get_bpmn_validator", lambda *_: validator)
    return orchestrator.build_orchestrator("test-model", "openai")


def invoke(graph, thread_id=None):
    return asyncio.run(graph.ainvoke(
        {"messages": [("user", PARK_REQUEST)], "request_id": "park-regression"},
        config={"configurable": {"thread_id": thread_id or uuid4().hex}},
    ))["response"]


def test_park_graph_keeps_branches_loop_and_outcomes():
    graph, xml = park_graph(), park_xml()
    assert validate_bpmn_syntax(xml)["valid"]
    assert validate_graph_fidelity(xml, graph) == []
    connections = {(c["source_id"], c["target_id"], c["condition"]) for c in graph["connections"]}
    assert ("prohibido", "pedir", "Sí") in connections
    assert ("prohibido", "pasar", "No") in connections
    assert ("altura", "avisar", "Menos de 1,20 m") in connections
    assert ("altura", "revisar_lugar", "1,20 m o más") in connections
    assert ("lugar", "esperar", "No hay lugar") in connections
    assert ("esperar", "revisar_lugar", None) in connections
    assert ("liberar", "fin", None) in connections
    assert validate_graph_fidelity(xml.replace('name="No hay lugar"', 'name="Sin dato"'), graph)


def test_park_layout_has_no_overlaps_or_non_manhattan_edges():
    xml, errors, warnings = check_and_repair_layout(park_xml())
    assert not errors and not warnings
    root = ET.fromstring(xml)
    semantic = {element.get("id"): element for element in root.iter()
                if element.tag.startswith(f"{{{MODEL_NS}}}") and element.get("id")}
    nodes = []
    for shape in root.iter(f"{{{BPMNDI_NS}}}BPMNShape"):
        ref = shape.get("bpmnElement")
        if ref not in semantic or semantic[ref].tag.split("}")[-1] not in NODE_TAGS:
            continue
        b = shape.find(f"{{{DC_NS}}}Bounds")
        x, y, w, h = (float(b.get(attr)) for attr in ("x", "y", "width", "height"))
        nodes.append((ref, (x, y, x + w, y + h)))
    for index, (ref, rect) in enumerate(nodes):
        assert all(not _overlap(rect, other) for _, other in nodes[index + 1:]), ref
    for edge in root.iter(f"{{{BPMNDI_NS}}}BPMNEdge"):
        points = [(float(point.get("x")), float(point.get("y")))
                  for point in edge.findall(f"{{{DI_NS}}}waypoint")]
        for a, b in zip(points, points[1:]):
            assert a != b and (a[0] == b[0] or a[1] == b[1]), edge.get("id")
            assert not _segment_problem(a, b, [rect for _, rect in nodes], []), edge.get("id")
    assert validate_graph_fidelity(xml, park_graph()) == []
    assert check_and_repair_layout(xml)[0] == xml


def test_no_xml_retries_creator_then_reviews_complete_park(monkeypatch):
    creator = Agent(BpmnDraft(message="No pude ubicar los elementos", failure_reason="layout_unsolvable"),
                    draft(park_xml()))
    validator = Agent(draft(park_xml()))
    response = invoke(setup(monkeypatch, creator, validator))
    assert response.status == "completed"
    assert len(creator.calls) == 2 and len(validator.calls) == 1
    assert "simple spacious layout" in creator.calls[1]["messages"][1].content
    assert "XML to review and repair" in validator.calls[0]["messages"][0].content
    assert validate_graph_fidelity(response.bpmn_xml, park_graph()) == []


def test_validator_receives_broken_xml_and_repairs_it(monkeypatch):
    broken = park_xml().replace('targetRef="atender"', 'targetRef="missing"')
    creator = Agent(draft(broken))
    validator = Agent(draft(park_xml()))
    response = invoke(setup(monkeypatch, creator, validator))
    assert response.status == "completed"
    prompt = validator.calls[0]["messages"][0].content
    assert 'targetRef="missing"' in prompt and "does not reference an existing id" in prompt
    assert validate_bpmn_syntax(response.bpmn_xml)["valid"]
    assert validate_graph_fidelity(response.bpmn_xml, park_graph()) == []


def test_rejects_validator_business_change_and_keeps_original(monkeypatch):
    xml = park_xml()
    changed = xml.replace('name="Liberar asiento"', 'name="Cambiar proceso"')
    response = invoke(setup(monkeypatch, Agent(draft(xml)), Agent(draft(changed))))
    assert response.status == "completed"
    assert "Liberar asiento" in response.bpmn_xml
    assert "Cambiar proceso" not in response.bpmn_xml


def test_rejects_broken_review_and_keeps_valid_draft(monkeypatch):
    response = invoke(setup(monkeypatch, Agent(draft(park_xml())), Agent(draft("<broken"))))
    assert response.status == "completed"
    assert validate_bpmn_syntax(response.bpmn_xml)["valid"]


def test_overlapping_park_activities_are_fixed_before_review(monkeypatch):
    xml = park_xml().replace('x="900" y="260"', 'x="700" y="260"')
    validator = Agent(None)
    response = invoke(setup(monkeypatch, Agent(draft(xml)), validator))
    assert response.status == "completed"
    assert "detalles visuales" not in response.message
    assert "overlap" not in validator.calls[0]["messages"][0].content


def test_unresolved_routes_are_explicitly_reported(monkeypatch):
    monkeypatch.setattr("app.services.bpmn_layout._route_between", lambda *args, **kwargs: None)
    response = invoke(setup(monkeypatch, Agent(draft(park_xml())), Agent(None)))
    assert response.status == "completed"
    assert "ruta ortogonal sin cruces con nodos" in response.message


def test_failure_limits_and_turn_state_reset(monkeypatch):
    creator = Agent(BpmnDraft(message="No se pudo", failure_reason="layout_unsolvable"))
    validator = Agent(None)
    graph = setup(monkeypatch, creator, validator)
    thread_id = uuid4().hex
    assert invoke(graph, thread_id).status == "error"
    assert invoke(graph, thread_id).status == "error"
    assert len(creator.calls) == 4
    assert not validator.calls


def test_creator_exception_is_retried_without_calling_it_unsolvable(monkeypatch):
    creator = Agent(RuntimeError("provider unavailable"), draft(park_xml()))
    response = invoke(setup(monkeypatch, creator, Agent(None)))
    assert response.status == "completed"
    assert len(creator.calls) == 2


def test_reviewer_extra_business_activity_is_not_accepted(monkeypatch):
    xml = park_xml()
    assert validate_graph_fidelity(xml.replace(
        '<bpmn:task id="liberar"', '<bpmn:task id="inventada" name="Inventada"/><bpmn:task id="liberar"'
    ), park_graph())


def test_invalid_xml_never_returned_after_review_limit(monkeypatch):
    validator = Agent(draft("<still-broken"))
    response = invoke(setup(monkeypatch, Agent(draft("<broken")), validator))
    assert response.status == "error" and response.bpmn_xml is None
    assert len(validator.calls) == 2
