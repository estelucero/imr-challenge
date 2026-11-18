from app.services.bpmn_syntax import validate_bpmn_syntax


VALID_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" name="Proceso" isExecutable="false">
    <bpmn:laneSet id="LaneSet_1">
      <bpmn:lane id="Lane_1" name="Responsable">
        <bpmn:flowNodeRef>Start_1</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Task_1</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>End_1</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="Start_1" name="Inicio">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:task id="Task_1" name="Procesar solicitud">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:task>
    <bpmn:endEvent id="End_1" name="Fin">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="Start_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="End_1" />
  </bpmn:process>
  <bpmn:collaboration id="Collaboration_1">
    <bpmn:participant id="Participant_1" name="Organizacion" processRef="Process_1" />
  </bpmn:collaboration>
  <bpmndi:BPMNDiagram id="Diagram_1">
    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Collaboration_1">
      <bpmndi:BPMNShape id="Participant_1_di" bpmnElement="Participant_1" isHorizontal="true">
        <dc:Bounds x="100" y="100" width="700" height="200" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Lane_1_di" bpmnElement="Lane_1" isHorizontal="true">
        <dc:Bounds x="100" y="100" width="700" height="200" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Start_1_di" bpmnElement="Start_1">
        <dc:Bounds x="150" y="182" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">
        <dc:Bounds x="250" y="160" width="120" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="End_1_di" bpmnElement="End_1">
        <dc:Bounds x="450" y="182" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="186" y="200" />
        <di:waypoint x="250" y="200" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
        <di:waypoint x="370" y="200" />
        <di:waypoint x="450" y="200" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>"""


def codes(result):
    return [error["code"] for error in result["errors"]]


def test_accepts_valid_bpmn():
    result = validate_bpmn_syntax(VALID_XML)

    assert result["valid"], result["errors"]


def test_rejects_malformed_xml():
    result = validate_bpmn_syntax("<bpmn:definitions>")

    assert not result["valid"]
    assert "MALFORMED_XML" in codes(result)


def test_rejects_empty_xml():
    result = validate_bpmn_syntax("   ")

    assert not result["valid"]
    assert "EMPTY_XML" in codes(result)


def test_rejects_wrong_root():
    result = validate_bpmn_syntax("<root/>")

    assert not result["valid"]
    assert "INVALID_ROOT" in codes(result)


def test_rejects_duplicate_id():
    xml = VALID_XML.replace(
        '<bpmn:endEvent id="End_1"',
        '<bpmn:endEvent id="Task_1"',
    )

    result = validate_bpmn_syntax(xml)

    assert not result["valid"]
    assert "DUPLICATE_ID" in codes(result)


def test_rejects_dangling_target_ref():
    xml = VALID_XML.replace('targetRef="Task_1"', 'targetRef="Missing_Task"', 1)

    result = validate_bpmn_syntax(xml)

    assert not result["valid"]
    assert "DANGLING_REFERENCE" in codes(result)


def test_rejects_dangling_di_reference():
    xml = VALID_XML.replace('bpmnElement="Task_1"', 'bpmnElement="Missing_Node"', 1)

    result = validate_bpmn_syntax(xml)

    assert not result["valid"]
    assert "DANGLING_DI_REFERENCE" in codes(result)


def test_rejects_missing_diagram():
    index = VALID_XML.index("<bpmndi:BPMNDiagram")
    xml = VALID_XML[:index] + "</bpmn:definitions>"

    result = validate_bpmn_syntax(xml)

    assert not result["valid"]
    assert "MISSING_DI" in codes(result)


def test_rejects_invalid_plane_reference_type():
    xml = VALID_XML.replace('bpmnElement="Collaboration_1"', 'bpmnElement="Task_1"')
    assert "INVALID_REFERENCE_TYPE" in codes(validate_bpmn_syntax(xml))


def test_rejects_sequence_flow_outside_process():
    xml = VALID_XML.replace('targetRef="Task_1"', 'targetRef="Participant_1"', 1)
    assert "INVALID_SEQUENCE_SCOPE" in codes(validate_bpmn_syntax(xml))
