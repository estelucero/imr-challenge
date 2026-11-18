import asyncio
from uuid import uuid4

import app.agents.orchestrator as orchestrator_module
from app.models.chat_request import BpmnDraft, Clarification
from app.models.process import (
    BusinessProcessSpec,
    ProcessEntity,
    ProcessAnalysis,
    ProcessFlowObject,
    ProcessConnection,
    ProcessScope,
    ProcessSwimlane,
)
from park_fixture import park_graph, park_xml


class StubAgent:
    def __init__(self, result):
        self.result = result
        self.inputs = []

    async def ainvoke(self, request):
        self.inputs.append(request)
        return {"structured_response": self.result}


def complete_process_analysis(gaps=None):
    return ProcessAnalysis(
        process=BusinessProcessSpec(
            title="Pedido",
            language="Spanish",
            scope=ProcessScope(
                business="Tienda",
                purpose="Procesar un pedido",
                start="Pedido recibido",
                end_condition="Pedido despachado",
                outcome="Pedido despachado",
            ),
            entities=[
                ProcessEntity(id="ENT_STORE", name="Tienda", kind="organization")
            ],
            swimlanes=[
                ProcessSwimlane(
                    id="LANE_WAREHOUSE",
                    entity_id="ENT_STORE",
                    name="Depósito",
                    kind="department",
                )
            ],
            flow_objects=[
                ProcessFlowObject(
                    id="OBJ_START",
                    kind="start_event",
                    label="Pedido recibido",
                    entity_id="ENT_STORE",
                ),
                ProcessFlowObject(
                    id="OBJ_PREPARE",
                    kind="activity",
                    label="Preparar pedido",
                    entity_id="ENT_STORE",
                    swimlane_id="LANE_WAREHOUSE",
                    activity_type="task",
                ),
                ProcessFlowObject(
                    id="OBJ_END",
                    kind="end_event",
                    label="Pedido despachado",
                    entity_id="ENT_STORE",
                ),
            ],
            connections=[
                ProcessConnection(
                    id="CONN_START_PREPARE",
                    source_id="OBJ_START",
                    target_id="OBJ_PREPARE",
                    kind="sequence",
                ),
                ProcessConnection(
                    id="CONN_PREPARE_END",
                    source_id="OBJ_PREPARE",
                    target_id="OBJ_END",
                    kind="sequence",
                ),
            ],
        ),
        gaps=gaps or [],
    )


def test_gaps_route_to_clarifier_without_calling_creator(monkeypatch):
    analyst = StubAgent(
        complete_process_analysis(["No se definió cuándo termina el proceso"])
    )
    clarifier = StubAgent(
        {"recipient": "client", "message": "Necesito una aclaración.",
         "questions": ["¿Cuándo se considera terminado el proceso?"]}
    )
    creator = StubAgent(None)

    monkeypatch.setattr(orchestrator_module, "get_process_analyst", lambda _model, _provider: analyst)
    monkeypatch.setattr(orchestrator_module, "get_clarifier", lambda _model, _provider: clarifier)
    monkeypatch.setattr(orchestrator_module, "get_bpmn_validator", lambda *_: StubAgent(None))
    monkeypatch.setattr(
        orchestrator_module,
        "get_bpmn_creator",
        lambda _model, _provider: creator,
    )

    graph = orchestrator_module.build_orchestrator(provider="openai")
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [("user", "Quiero modelar el proceso de pedidos.")],
                "request_id": "test-gap-route",
            },
            config={"configurable": {"thread_id": uuid4().hex}},
        )
    )

    assert result["response"].status == "needs_clarification"
    assert "¿Cuándo se considera terminado" in result["response"].message
    assert len(analyst.inputs) == 0
    assert len(clarifier.inputs) == 1
    assert creator.inputs == []


def test_complete_spec_routes_to_creator_without_clarifier(monkeypatch):
    analyst = StubAgent(park_graph())
    clarifier = StubAgent({"recipient": "analyst", "message": "Visita al parque", "questions": []})
    creator = StubAgent(
        BpmnDraft(
            bpmn_xml=park_xml(),
            message="Armé el proceso de pedidos.",
            layout_plan="1. Pedido recibido -> preparar -> despachar",
        )
    )

    monkeypatch.setattr(orchestrator_module, "get_process_analyst", lambda _model, _provider: analyst)
    monkeypatch.setattr(orchestrator_module, "get_clarifier", lambda _model, _provider: clarifier)
    monkeypatch.setattr(orchestrator_module, "get_bpmn_validator", lambda *_: StubAgent(None))
    monkeypatch.setattr(
        orchestrator_module,
        "get_bpmn_creator",
        lambda _model, _provider: creator,
    )
    monkeypatch.setattr(
        orchestrator_module,
        "validate_bpmn_syntax",
        lambda _xml: {"valid": True, "errors": []},
    )

    graph = orchestrator_module.build_orchestrator(provider="openai")
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [("user", "Quiero modelar el proceso de pedidos.")],
                "request_id": "test-complete-route",
            },
            config={"configurable": {"thread_id": uuid4().hex}},
        )
    )

    assert result["response"].status == "completed"
    assert len(analyst.inputs) == 1
    assert len(clarifier.inputs) == 1
    assert len(creator.inputs) == 1
    creator_input = creator.inputs[0]["messages"][0].content
    assert "AnalystProcessGraph" in creator_input
    assert "Quiero modelar el proceso de pedidos" not in creator_input


def test_analyst_failure_does_not_fall_through_to_creator(monkeypatch):
    analyst = StubAgent(None)
    clarifier = StubAgent({"recipient": "analyst", "message": "Proceso de pedidos", "questions": []})
    creator = StubAgent(None)

    monkeypatch.setattr(orchestrator_module, "get_process_analyst", lambda _model, _provider: analyst)
    monkeypatch.setattr(orchestrator_module, "get_clarifier", lambda _model, _provider: clarifier)
    monkeypatch.setattr(orchestrator_module, "get_bpmn_validator", lambda *_: StubAgent(None))
    monkeypatch.setattr(
        orchestrator_module,
        "get_bpmn_creator",
        lambda _model, _provider: creator,
    )

    graph = orchestrator_module.build_orchestrator(provider="openai")
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [("user", "Proceso de pedidos")],
                "request_id": "test-analyst-failure",
            },
            config={"configurable": {"thread_id": uuid4().hex}},
        )
    )

    assert result["response"].status == "error"
    assert len(clarifier.inputs) == 1
    assert creator.inputs == []
