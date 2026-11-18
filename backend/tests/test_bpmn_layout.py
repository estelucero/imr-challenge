import xml.etree.ElementTree as ET

from app.services.bpmn_layout import (
    BPMNDI_NS, DC_NS, DI_NS, _intersects, _segment_problem, check_and_repair_layout, semantic_signature,
)
from test_bpmn_syntax import VALID_XML


def points(xml, edge_id="Flow_1_di"):
    root = ET.fromstring(xml)
    edge = root.find(f".//{{{BPMNDI_NS}}}BPMNEdge[@id='{edge_id}']")
    return [(float(p.get("x")), float(p.get("y"))) for p in edge.findall(f"{{{DI_NS}}}waypoint")]


def test_reroutes_segment_crossing_an_unrelated_activity():
    xml = VALID_XML.replace(
        '<bpmn:task id="Task_1"', '<bpmn:task id="Blocker" name="Bloqueo" />\n    <bpmn:task id="Task_1"'
    ).replace(
        '<bpmndi:BPMNShape id="Task_1_di"',
        '<bpmndi:BPMNShape id="Blocker_di" bpmnElement="Blocker">'
        '<dc:Bounds x="205" y="180" width="30" height="40" />'
        '</bpmndi:BPMNShape><bpmndi:BPMNShape id="Task_1_di"'
    )
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    route = points(repaired)
    assert len(route) > 2
    assert route[0] == (186, 200) and route[-1] == (250, 200)
    assert not any(_intersects(a, b, (205, 180, 235, 220)) for a, b in zip(route, route[1:]))
    assert semantic_signature(xml) == semantic_signature(repaired)


def test_route_does_not_pass_back_through_its_own_source():
    xml = VALID_XML.replace('x="186" y="200"', 'x="150" y="200"')
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    route = points(repaired)
    assert route[0] == (150, 200) and route[-1] == (250, 200)
    assert not any(_intersects(a, b, (150, 182, 186, 218)) for a, b in zip(route, route[1:]))


def test_overlapping_nodes_are_reported_for_agent_review():
    xml = VALID_XML.replace('x="250" y="160"', 'x="160" y="160"')
    _, _, warnings = check_and_repair_layout(xml)
    assert any("Start_1 and Task_1 overlap" in warning for warning in warnings)


def test_reroutes_horizontal_lane_border_overlap():
    xml = VALID_XML.replace('x="150" y="182"', 'x="150" y="100"').replace(
        'x="250" y="160"', 'x="250" y="100"'
    ).replace('x="186" y="200"', 'x="168" y="100"').replace(
        'x="250" y="200"', 'x="310" y="100"', 1
    ).replace('x="370" y="200"', 'x="370" y="140"')
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    route = points(repaired)
    assert len(route) > 2
    assert all(not (a[1] == b[1] == 100) for a, b in zip(route, route[1:]))
    assert points(check_and_repair_layout(repaired)[0]) == route


def test_perpendicular_lane_crossing_is_allowed():
    assert _segment_problem((200, 50), (200, 350), [], [(100, 800, 100), (100, 800, 300)]) is None


def test_missing_shapes_and_bad_waypoints_are_blocking():
    xml = VALID_XML.replace('x="186" y="200"', 'x="NaN" y="200"').replace(
        '<bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">',
        '<bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1" />\n      <unused>'
    ).replace('</bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="End_1_di"',
              '</unused>\n      <bpmndi:BPMNShape id="End_1_di"')
    _, errors, _ = check_and_repair_layout(xml)
    assert any("invalid bounds" in error for error in errors)
    assert any("invalid waypoints" in error for error in errors)


def test_unresolvable_route_produces_warning_instead_of_corrupting_diagram():
    xml = VALID_XML.replace(
        '<bpmn:task id="Task_1"', '<bpmn:task id="Blocker" name="Bloqueo" />\n    <bpmn:task id="Task_1"'
    ).replace(
        '<bpmndi:BPMNShape id="Task_1_di"',
        '<bpmndi:BPMNShape id="Blocker_di" bpmnElement="Blocker">'
        '<dc:Bounds x="180" y="190" width="20" height="20" />'
        '</bpmndi:BPMNShape><bpmndi:BPMNShape id="Task_1_di"'
    )
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors
    assert any("automatic routing could not resolve" in warning for warning in warnings)
    assert points(repaired) == points(xml)
