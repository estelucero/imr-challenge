"""Deterministic BPMN-DI checks and conservative orthogonal edge routing."""

from __future__ import annotations

import heapq
import math
import xml.etree.ElementTree as ET

from app.services.bpmn_syntax import BPMNDI_NS, DC_NS, DI_NS, MODEL_NS

SHAPE = f"{{{BPMNDI_NS}}}BPMNShape"
EDGE = f"{{{BPMNDI_NS}}}BPMNEdge"
BOUNDS = f"{{{DC_NS}}}Bounds"
WAYPOINT = f"{{{DI_NS}}}waypoint"
MODEL = f"{{{MODEL_NS}}}"
FLOW_TAGS = {"sequenceFlow", "messageFlow"}
NODE_TAGS = {
    "startEvent", "endEvent", "intermediateCatchEvent", "intermediateThrowEvent",
    "boundaryEvent", "task", "userTask", "serviceTask", "sendTask", "receiveTask",
    "manualTask", "businessRuleTask", "scriptTask", "subProcess", "callActivity",
    "transaction", "adHocSubProcess", "exclusiveGateway", "inclusiveGateway",
    "parallelGateway", "eventBasedGateway", "complexGateway",
}
EPS = 0.01
MARGIN = 15.0
MAX_GRID_POINTS = 20000


def _number(element: ET.Element, name: str) -> float:
    value = float(element.attrib[name])
    if not math.isfinite(value):
        raise ValueError("non-finite coordinate")
    return value


def _intersects(a, b, rect) -> bool:
    """Whether a segment enters a rectangle's interior (Liang-Barsky)."""
    x, y, right, bottom = rect
    x += EPS
    y += EPS
    right -= EPS
    bottom -= EPS
    if x >= right or y >= bottom:
        return False
    dx, dy = b[0] - a[0], b[1] - a[1]
    low, high = 0.0, 1.0
    for p, q in ((-dx, a[0] - x), (dx, right - a[0]),
                 (-dy, a[1] - y), (dy, bottom - a[1])):
        if abs(p) < EPS:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                low = max(low, r)
            else:
                high = min(high, r)
            if low > high:
                return False
    return True


def _segment_problem(a, b, obstacles, lane_borders):
    for rect in obstacles:
        if _intersects(a, b, rect):
            return "crosses a node"
    if abs(a[1] - b[1]) < EPS and abs(a[0] - b[0]) > EPS:
        for left, right, y in lane_borders:
            if abs(a[1] - y) < EPS and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right) - EPS:
                return "overlaps a lane border"
    return None


def _route(start, end, obstacles, lane_borders):
    """Find a short orthogonal route on a bounded visibility grid."""
    xs = {start[0], end[0]}
    ys = {start[1], end[1]}
    for x1, y1, x2, y2 in obstacles:
        xs.update((x1 - MARGIN, x2 + MARGIN))
        ys.update((y1 - MARGIN, y2 + MARGIN))
    for x1, x2, y in lane_borders:
        xs.update((x1 - MARGIN, x2 + MARGIN))
        ys.update((y - MARGIN, y + MARGIN))
    xs, ys = sorted(xs), sorted(ys)
    if len(xs) * len(ys) > MAX_GRID_POINTS:
        return None
    origin = (xs.index(start[0]), ys.index(start[1]))
    destination = (xs.index(end[0]), ys.index(end[1]))
    queue = [(0.0, origin)]
    distance = {origin: 0.0}
    previous = {}
    while queue:
        cost, current = heapq.heappop(queue)
        if cost != distance[current]:
            continue
        if current == destination:
            break
        i, j = current
        a = (xs[i], ys[j])
        for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                continue
            b = (xs[ni], ys[nj])
            if _segment_problem(a, b, obstacles, lane_borders):
                continue
            new_cost = cost + abs(a[0] - b[0]) + abs(a[1] - b[1])
            neighbor = (ni, nj)
            if new_cost < distance.get(neighbor, math.inf):
                distance[neighbor] = new_cost
                previous[neighbor] = current
                heapq.heappush(queue, (new_cost, neighbor))
    if destination not in distance:
        return None
    path = []
    node = destination
    while True:
        path.append((xs[node[0]], ys[node[1]]))
        if node == origin:
            break
        node = previous[node]
    path.reverse()
    compact = []
    for point in path:
        if len(compact) >= 2 and (
            (compact[-2][0] == compact[-1][0] == point[0]) or
            (compact[-2][1] == compact[-1][1] == point[1])
        ):
            compact[-1] = point
        else:
            compact.append(point)
    return compact if len(compact) >= 2 else None


def check_and_repair_layout(xml: str) -> tuple[str, list[str], list[str]]:
    """Return XML, blocking DI errors and unresolved cosmetic warnings.

    Only edge waypoints are changed; business semantics and anchors are retained.
    Call after the basic XML syntax validator has accepted the document.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml, [], []  # the syntax validator reports this
    semantic = {el.get("id"): el for el in root.iter() if el.tag.startswith(MODEL) and el.get("id")}
    shapes, edges = {}, {}
    errors, warnings = [], []
    lane_borders = []
    for shape in root.iter(SHAPE):
        ref = shape.get("bpmnElement")
        if ref in shapes:
            errors.append(f"Duplicate BPMNShape for {ref}.")
            continue
        bounds = shape.find(BOUNDS)
        try:
            if bounds is None:
                raise ValueError("missing bounds")
            x, y, w, h = (_number(bounds, attr) for attr in ("x", "y", "width", "height"))
            if w <= 0 or h <= 0:
                raise ValueError("non-positive bounds")
        except (KeyError, ValueError):
            errors.append(f"BPMNShape {ref} has missing or invalid bounds.")
            continue
        shapes[ref] = (x, y, x + w, y + h)
        if ref in semantic and semantic[ref].tag == MODEL + "lane":
            lane_borders.extend(((x, x + w, y), (x, x + w, y + h)))
    for edge in root.iter(EDGE):
        ref = edge.get("bpmnElement")
        if ref in edges:
            errors.append(f"Duplicate BPMNEdge for {ref}.")
        edges[ref] = edge
    for ref, element in semantic.items():
        tag = element.tag.removeprefix(MODEL)
        if tag in NODE_TAGS | {"participant", "lane"} and ref not in shapes:
            errors.append(f"Missing BPMNShape for {ref}.")
        if tag in FLOW_TAGS and ref not in edges:
            errors.append(f"Missing BPMNEdge for {ref}.")

    nodes = [(ref, rect) for ref, rect in shapes.items()
             if ref in semantic and semantic[ref].tag.removeprefix(MODEL) in NODE_TAGS]
    for index, (first_id, first) in enumerate(nodes):
        for second_id, second in nodes[index + 1:]:
            if (min(first[2], second[2]) - max(first[0], second[0]) <= EPS or
                    min(first[3], second[3]) - max(first[1], second[1]) <= EPS):
                continue
            # Expanded subprocesses are allowed to contain their own flow nodes.
            if ((semantic[first_id].tag == MODEL + "subProcess" and
                 semantic[second_id] in list(semantic[first_id].iter())) or
                (semantic[second_id].tag == MODEL + "subProcess" and
                 semantic[first_id] in list(semantic[second_id].iter()))):
                continue
            warnings.append(f"BPMNShapes {first_id} and {second_id} overlap.")

    changed = False
    for ref, edge in edges.items():
        flow = semantic.get(ref)
        if flow is None or flow.tag.removeprefix(MODEL) not in FLOW_TAGS:
            continue
        waypoints = edge.findall(WAYPOINT)
        try:
            points = [(_number(p, "x"), _number(p, "y")) for p in waypoints]
            if len(points) < 2:
                raise ValueError("too few waypoints")
        except (KeyError, ValueError):
            errors.append(f"BPMNEdge {ref} has missing or invalid waypoints.")
            continue
        obstacles = [rect for node_id, rect in shapes.items()
                     if node_id in semantic and semantic[node_id].tag.removeprefix(MODEL) in NODE_TAGS]
        for endpoint, node_id in ((points[0], flow.get("sourceRef")), (points[-1], flow.get("targetRef"))):
            rect = shapes.get(node_id)
            if rect:
                x, y, right, bottom = rect
                on_vertical = (abs(endpoint[0] - x) < EPS or abs(endpoint[0] - right) < EPS) and y - EPS <= endpoint[1] <= bottom + EPS
                on_horizontal = (abs(endpoint[1] - y) < EPS or abs(endpoint[1] - bottom) < EPS) and x - EPS <= endpoint[0] <= right + EPS
                if not (on_vertical or on_horizontal):
                    warnings.append(f"BPMNEdge {ref} endpoint is not on the boundary of {node_id}.")
        problem = next((_segment_problem(a, b, obstacles, lane_borders)
                        for a, b in zip(points, points[1:])
                        if _segment_problem(a, b, obstacles, lane_borders)), None)
        if not problem:
            continue
        route = _route(points[0], points[-1], obstacles, lane_borders)
        if not route:
            warnings.append(f"BPMNEdge {ref} {problem}; automatic routing could not resolve it.")
            continue
        for waypoint in waypoints:
            edge.remove(waypoint)
        for index, (x, y) in enumerate(route):
            edge.insert(index, ET.Element(WAYPOINT, {"x": str(x), "y": str(y)}))
        changed = True

    if changed:
        for prefix, uri in (("bpmn", MODEL_NS), ("bpmndi", BPMNDI_NS), ("dc", DC_NS), ("di", DI_NS)):
            ET.register_namespace(prefix, uri)
        xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
    return xml, errors, warnings


def semantic_signature(xml: str):
    """Compare business semantics independently of BPMN-DI and XML formatting."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return None

    def visit(element):
        return (element.tag, tuple(sorted(element.attrib.items())), (element.text or "").strip(),
                tuple(sorted((visit(child) for child in element if child.tag.startswith(MODEL)), key=repr)))

    return visit(root)
