import xml.etree.ElementTree as ET

from app.services.bpmn_layout import (
    BPMNDI_NS, DC_NS, DI_NS, MODEL_NS, _intersects, _route_between, _segment_problem, check_and_repair_layout, semantic_signature,
)
from app.services.bpmn_fidelity import validate_graph_fidelity
from app.services.bpmn_syntax import validate_bpmn_syntax
from test_bpmn_syntax import VALID_XML


def points(xml, edge_id="Flow_1_di"):
    root = ET.fromstring(xml)
    edge = root.find(f".//{{{BPMNDI_NS}}}BPMNEdge[@id='{edge_id}']")
    return [(float(p.get("x")), float(p.get("y"))) for p in edge.findall(f"{{{DI_NS}}}waypoint")]


def bounds(xml, shape_id):
    root = ET.fromstring(xml)
    shape = root.find(f".//{{{BPMNDI_NS}}}BPMNShape[@id='{shape_id}']")
    b = shape.find(f"{{{DC_NS}}}Bounds")
    x, y, width, height = (float(b.get(attr)) for attr in ("x", "y", "width", "height"))
    return x, y, x + width, y + height


def on_boundary(point, rect):
    x, y = point
    x1, y1, x2, y2 = rect
    return ((x == x1 or x == x2) and y1 <= y <= y2) or ((y == y1 or y == y2) and x1 <= x <= x2)


def manhattan(route):
    return all(a != b and (a[0] == b[0] or a[1] == b[1]) for a, b in zip(route, route[1:]))


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
    assert on_boundary(route[0], bounds(repaired, "Start_1_di"))
    assert on_boundary(route[-1], bounds(repaired, "Task_1_di"))
    assert manhattan(route)
    assert not any(_intersects(a, b, (205, 180, 235, 220)) for a, b in zip(route, route[1:]))
    assert semantic_signature(xml) == semantic_signature(repaired)


def test_route_does_not_pass_back_through_its_own_source():
    xml = VALID_XML.replace('x="186" y="200"', 'x="150" y="200"')
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    route = points(repaired)
    assert route[0] == (186, 200) and route[-1] == (250, 200)
    assert not any(_intersects(a, b, (150, 182, 186, 218)) for a, b in zip(route, route[1:]))


def test_overlapping_nodes_are_separated():
    xml = VALID_XML.replace('x="250" y="160"', 'x="160" y="160"')
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    start, task = bounds(repaired, "Start_1_di"), bounds(repaired, "Task_1_di")
    assert task[0] >= start[2] + 15
    assert points(repaired)[-1][0] == task[0]
    assert semantic_signature(xml) == semantic_signature(repaired)


def test_reroutes_horizontal_lane_border_overlap():
    xml = VALID_XML.replace('x="150" y="182"', 'x="150" y="100"').replace(
        'x="250" y="160"', 'x="250" y="100"'
    ).replace('x="186" y="200"', 'x="168" y="100"').replace(
        'x="250" y="200"', 'x="310" y="100"', 1
    ).replace('x="370" y="200"', 'x="370" y="140"')
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    route = points(repaired)
    assert manhattan(route)
    assert all(not (a[1] == b[1] == 100) for a, b in zip(route, route[1:]))
    assert points(check_and_repair_layout(repaired)[0]) == route


def test_perpendicular_lane_crossing_is_allowed():
    assert _segment_problem((200, 50), (200, 350), [], [(100, 800, 100), (100, 800, 300)]) is None


def test_diagonal_and_unnecessarily_long_routes_become_short_manhattan_routes():
    xml = VALID_XML.replace(
        '<di:waypoint x="186" y="200" />\n        <di:waypoint x="250" y="200" />',
        '<di:waypoint x="186" y="195" /><di:waypoint x="190" y="110" />'
        '<di:waypoint x="240" y="110" /><di:waypoint x="250" y="205" />',
    )
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    assert points(repaired) == [(186, 200), (250, 200)]
    assert manhattan(points(repaired))
    assert check_and_repair_layout(repaired)[0] == repaired


def test_aligned_anchors_allow_short_direct_route_between_rectangles():
    source, target = (0, 0, 100, 100), (200, 80, 300, 180)
    route = _route_between(source, target, [source, target], [])
    assert route == [(100, 90), (200, 90)]


def test_container_expands_when_separated_nodes_need_more_room():
    xml = VALID_XML.replace('x="250" y="160" width="120"', 'x="160" y="160" width="700"')
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    task, end = bounds(repaired, "Task_1_di"), bounds(repaired, "End_1_di")
    lane, pool = bounds(repaired, "Lane_1_di"), bounds(repaired, "Participant_1_di")
    assert end[0] >= task[2] + 15
    assert lane[2] >= end[2] + 15 and pool[2] >= lane[2]
    for edge in ("Flow_1_di", "Flow_2_di"):
        assert manhattan(points(repaired, edge))


def test_single_lane_matching_pool_hides_only_duplicate_name_and_keeps_ownership():
    xml = VALID_XML.replace('name="Organizacion"', 'name="Responsable"')
    graph = {
        "pools": [{"id": "Participant_1", "name": "Responsable"}],
        "swimlanes": [{"id": "Lane_1", "name": "Responsable", "pool_id": "Participant_1"}],
        "objects": [
            {"id": "Start_1", "kind": "start_event", "label": "Inicio", "pool_id": "Participant_1", "lane_id": "Lane_1"},
            {"id": "Task_1", "kind": "activity", "label": "Procesar solicitud", "pool_id": "Participant_1", "lane_id": "Lane_1"},
            {"id": "End_1", "kind": "end_event", "label": "Fin", "pool_id": "Participant_1", "lane_id": "Lane_1"},
        ],
        "connections": [
            {"id": "Flow_1", "kind": "sequence", "source_id": "Start_1", "target_id": "Task_1"},
            {"id": "Flow_2", "kind": "sequence", "source_id": "Task_1", "target_id": "End_1"},
        ],
    }
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    root = ET.fromstring(repaired)
    lane = root.find(f".//{{{MODEL_NS}}}lane[@id='Lane_1']")
    assert lane.get("name") is None
    assert len(lane.findall(f"{{{MODEL_NS}}}flowNodeRef")) == 3
    assert root.find(f".//{{{MODEL_NS}}}participant[@id='Participant_1']").get("name") == "Responsable"
    assert validate_bpmn_syntax(repaired)["valid"]
    assert validate_graph_fidelity(repaired, graph) == []
    assert check_and_repair_layout(repaired)[0] == repaired


def test_lane_with_distinct_name_is_preserved():
    repaired, errors, warnings = check_and_repair_layout(VALID_XML)
    assert not errors and not warnings
    lane = ET.fromstring(repaired).find(f".//{{{MODEL_NS}}}lane[@id='Lane_1']")
    assert lane.get("name") == "Responsable"


def test_matching_lane_name_is_not_hidden_if_pool_has_multiple_lanes():
    xml = VALID_XML.replace('name="Organizacion"', 'name="Responsable"').replace(
        '</bpmn:laneSet>', '<bpmn:lane id="Lane_2" name="Otra" /></bpmn:laneSet>'
    ).replace(
        '<bpmndi:BPMNShape id="Start_1_di"',
        '<bpmndi:BPMNShape id="Lane_2_di" bpmnElement="Lane_2">'
        '<dc:Bounds x="100" y="100" width="700" height="200" />'
        '</bpmndi:BPMNShape><bpmndi:BPMNShape id="Start_1_di"',
    )
    repaired, errors, _ = check_and_repair_layout(xml)
    assert not errors
    lane = ET.fromstring(repaired).find(f".//{{{MODEL_NS}}}lane[@id='Lane_1']")
    assert lane.get("name") == "Responsable"


def test_unroutable_moved_endpoint_is_a_blocking_error(monkeypatch):
    monkeypatch.setattr("app.services.bpmn_layout._route_between", lambda *args, **kwargs: None)
    xml = VALID_XML.replace('x="250" y="160"', 'x="160" y="160"')
    _, errors, warnings = check_and_repair_layout(xml)
    assert any("disconnected endpoints" in error for error in errors)
    assert any("no safe Manhattan route" in warning for warning in warnings)


def test_self_loop_is_orthogonal_and_goes_around_its_node():
    xml = VALID_XML.replace('targetRef="Task_1"', 'targetRef="Start_1"', 1)
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors and not warnings
    route, rect = points(repaired), bounds(repaired, "Start_1_di")
    assert on_boundary(route[0], rect) and on_boundary(route[-1], rect) and route[0] != route[-1]
    assert manhattan(route)
    assert all(not _segment_problem(a, b, [rect], []) for a, b in zip(route, route[1:]))


def test_message_between_pools_crosses_lanes_perpendicularly():
    root = ET.fromstring(VALID_XML)
    b, bd, dc, di = (f"{{{ns}}}" for ns in (MODEL_NS, BPMNDI_NS, DC_NS, DI_NS))
    process = ET.SubElement(root, b + "process", {"id": "Process_2"})
    lane_set = ET.SubElement(process, b + "laneSet", {"id": "LaneSet_2"})
    lane = ET.SubElement(lane_set, b + "lane", {"id": "Patient_lane", "name": "Paciente"})
    ET.SubElement(lane, b + "flowNodeRef").text = "Task_2"
    ET.SubElement(process, b + "task", {"id": "Task_2", "name": "Recibir mensaje"})
    collaboration = root.find(b + "collaboration")
    ET.SubElement(collaboration, b + "participant", {"id": "Patient", "name": "Paciente", "processRef": "Process_2"})
    ET.SubElement(collaboration, b + "messageFlow", {"id": "Message_1", "sourceRef": "Task_1", "targetRef": "Task_2"})
    plane = root.find(f".//{bd}BPMNPlane")
    for ref, x, y, w, h in (("Patient", 100, 400, 700, 200), ("Patient_lane", 100, 400, 700, 200),
                            ("Task_2", 400, 460, 100, 80)):
        shape = ET.SubElement(plane, bd + "BPMNShape", {"id": ref + "_di", "bpmnElement": ref})
        ET.SubElement(shape, dc + "Bounds", {"x": str(x), "y": str(y), "width": str(w), "height": str(h)})
    edge = ET.SubElement(plane, bd + "BPMNEdge", {"id": "Message_1_di", "bpmnElement": "Message_1"})
    ET.SubElement(edge, di + "waypoint", {"x": "310", "y": "240"})
    ET.SubElement(edge, di + "waypoint", {"x": "450", "y": "460"})
    repaired, errors, warnings = check_and_repair_layout(ET.tostring(root, encoding="unicode"))
    assert not errors and not warnings
    route = points(repaired, "Message_1_di")
    assert manhattan(route)
    obstacles = [bounds(repaired, ref) for ref in ("Start_1_di", "Task_1_di", "End_1_di", "Task_2_di")]
    lane_borders = [(100, 800, y) for y in (100, 300, 400, 600)]
    assert all(not _segment_problem(a, b, obstacles, lane_borders) for a, b in zip(route, route[1:]))
    assert ET.fromstring(repaired).find(f".//{b}lane[@id='Patient_lane']").get("name") is None
    assert validate_bpmn_syntax(repaired)["valid"]


def test_missing_shapes_and_bad_waypoints_are_blocking():
    xml = VALID_XML.replace('x="186" y="200"', 'x="NaN" y="200"').replace(
        '<bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">',
        '<bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1" />\n      <unused>'
    ).replace('</bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="End_1_di"',
              '</unused>\n      <bpmndi:BPMNShape id="End_1_di"')
    _, errors, _ = check_and_repair_layout(xml)
    assert any("invalid bounds" in error for error in errors)
    assert any("invalid waypoints" in error for error in errors)


def test_unresolvable_route_produces_warning_instead_of_corrupting_diagram(monkeypatch):
    monkeypatch.setattr("app.services.bpmn_layout.MAX_GRID_POINTS", 1)
    xml = VALID_XML.replace(
        '<bpmn:task id="Task_1"', '<bpmn:task id="Blocker" name="Bloqueo" />\n    <bpmn:task id="Task_1"'
    ).replace(
        '<bpmndi:BPMNShape id="Task_1_di"',
        '<bpmndi:BPMNShape id="Blocker_di" bpmnElement="Blocker">'
        '<dc:Bounds x="205" y="180" width="30" height="40" />'
        '</bpmndi:BPMNShape><bpmndi:BPMNShape id="Task_1_di"'
    )
    repaired, errors, warnings = check_and_repair_layout(xml)
    assert not errors
    assert any("no safe Manhattan route" in warning for warning in warnings)
    assert points(repaired) == points(xml)
