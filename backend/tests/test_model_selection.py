"""The model selected in /chat must reach every agent, without API calls."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.agents.bpmn_creator as creator_module
import app.agents.bpmn_validator as validator_module
import app.agents.clarifier as clarifier_module
import app.agents.orchestrator as orchestrator_module
import app.agents.process_analyst as analyst_module
from app.agents.model_config import DEFAULT_MODELS, resolve_model
from app.main import app
from app.models.chat_request import BpmnDraft
from park_fixture import park_graph, park_xml


@pytest.fixture
def fake_models(monkeypatch):
    created = []
    invoked = []
    factories = (
        ("clarifier", clarifier_module, clarifier_module.get_clarifier),
        ("analyst", analyst_module, analyst_module.get_process_analyst),
        ("creator", creator_module, creator_module.get_bpmn_creator),
        ("validator", validator_module, validator_module.get_bpmn_validator),
    )
    orchestrator_module.get_orchestrator.cache_clear()
    for role, module, factory in factories:
        factory.cache_clear()

        def init_model(model_id, *, _role=role, **kwargs):
            created.append((_role, model_id))
            return model_id

        def make_agent(*, model, _role=role, **kwargs):
            class FakeAgent:
                async def ainvoke(self, request):
                    invoked.append((_role, model))
                    response = {
                        "clarifier": {"recipient": "analyst", "message": "Visita al parque", "questions": []},
                        "analyst": park_graph(),
                        "creator": BpmnDraft(bpmn_xml=park_xml(), message="Diagrama del parque"),
                        "validator": BpmnDraft(bpmn_xml=park_xml(), message="Diagrama del parque"),
                    }[_role]
                    return {"structured_response": response}

            return FakeAgent()

        monkeypatch.setattr(module, "init_chat_model", init_model)
        monkeypatch.setattr(module, "create_agent", make_agent)

    yield created, invoked

    orchestrator_module.get_orchestrator.cache_clear()
    for _, _, factory in factories:
        factory.cache_clear()


def request(client, provider, model, session_id):
    response = client.post("/chat", json={
        "provider": provider, "model": model, "session_id": session_id,
        "message": "Diagrama de la visita al parque",
    })
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"


def test_request_model_and_provider_reach_all_agents_and_caches_are_isolated(fake_models, monkeypatch):
    created, invoked = fake_models
    monkeypatch.setenv("CLARIFIER_MODEL", "old-model-that-must-not-override-the-request")
    client = TestClient(app)
    session = uuid4().hex
    combinations = [
        ("openrouter", "openai/gpt-6-luna"),
        ("openrouter", "openai/gpt-6-luna"),  # reuse the cached agents
        ("openai", "gpt-6-luna"),
        ("openrouter", "gpt-6-luna"),  # same model ID as above, different provider
        ("openrouter", "openai/gpt-6.1-terra"),
    ]
    roles = {"clarifier", "analyst", "creator", "validator"}
    for provider, model in combinations:
        start = len(invoked)
        request(client, provider, model, session)
        assert set(invoked[start:]) == {(role, f"{provider}:{model}") for role in roles}
        assert len(invoked[start:]) == len(roles)

    assert len(created) == 4 * len(set(combinations))
    for provider, model in set(combinations):
        assert {(role, f"{provider}:{model}") for role in roles} <= set(created)


@pytest.mark.parametrize("provider", ["openrouter", "openai"])
def test_missing_model_uses_same_provider_specific_fallback_for_all_agents(fake_models, provider):
    created, invoked = fake_models
    request(TestClient(app), provider, None, uuid4().hex)
    expected = f"{provider}:{DEFAULT_MODELS[provider]}"
    assert {model for _, model in created} == {expected}
    assert {model for _, model in invoked} == {expected}
    assert len(created) == len(invoked) == 4


def test_model_resolution_only_falls_back_when_missing():
    assert resolve_model(None, "openrouter") == DEFAULT_MODELS["openrouter"]
    assert resolve_model("  ", "openai") == DEFAULT_MODELS["openai"]
    assert resolve_model("custom/model", "openrouter") == "custom/model"
