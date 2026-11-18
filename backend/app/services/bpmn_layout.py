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
NODE_GAP = 15.0
LANE_HEADER = 35.0


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
        x1, y1, x2, y2 = rect
        if (abs(a[1] - b[1]) < EPS and
                (abs(a[1] - y1) < EPS or abs(a[1] - y2) < EPS) and
                min(max(a[0], b[0]), x2) - max(min(a[0], b[0]), x1) > EPS):
            return "overlaps a node boundary"
        if (abs(a[0] - b[0]) < EPS and
                (abs(a[0] - x1) < EPS or abs(a[0] - x2) < EPS) and
                min(max(a[1], b[1]), y2) - max(min(a[1], b[1]), y1) > EPS):
            return "overlaps a node boundary"
    if abs(a[1] - b[1]) < EPS and abs(a[0] - b[0]) > EPS:
        for left, right, y in lane_borders:
            if abs(a[1] - y) < EPS and max(min(a[0], b[0]), left) < min(max(a[0], b[0]), right) - EPS:
                return "overlaps a lane border"
    return None


def _anchors(rect, other, flexible):
    x1, y1, x2, y2 = rect
    anchors = [(x1, (y1 + y2) / 2), (x2, (y1 + y2) / 2),
               ((x1 + x2) / 2, y1), ((x1 + x2) / 2, y2)]
    if flexible:
        ox1, oy1, ox2, oy2 = other
        # Stay away from rounded task corners while aligning facing edges.
        padding = min(8.0, (x2 - x1) / 4, (y2 - y1) / 4)
        ys = ((oy1 + oy2) / 2, (max(y1, oy1) + min(y2, oy2)) / 2)
        xs = ((ox1 + ox2) / 2, (max(x1, ox1) + min(x2, ox2)) / 2)
        for y in ys:
            if y1 + padding <= y <= y2 - padding and oy1 <= y <= oy2:
                anchors.extend(((x1, y), (x2, y)))
        for x in xs:
            if x1 + padding <= x <= x2 - padding and ox1 <= x <= ox2:
                anchors.extend(((x, y1), (x, y2)))
    return tuple(dict.fromkeys(anchors))


def _on_boundary(point, rect):
    x, y = point
    x1, y1, x2, y2 = rect
    return (((abs(x - x1) < EPS or abs(x - x2) < EPS) and y1 - EPS <= y <= y2 + EPS) or
            ((abs(y - y1) < EPS or abs(y - y2) < EPS) and x1 - EPS <= x <= x2 + EPS))


def _route_between(source, target, obstacles, lane_borders, self_loop=False,
                   source_flexible=True, target_flexible=True):
    """Shortest Manhattan route on a bounded grid, breaking ties by bend count."""
    starts = _anchors(source, target, source_flexible)
    ends = _anchors(target, source, target_flexible)
    pairs = [(start, end) for start in starts for end in ends if start != end]
    if not pairs:
        return None
    lower_bound = min(abs(start[0] - end[0]) + abs(start[1] - end[1]) for start, end in pairs)
    direct = []
    for start, end in pairs:
        if abs(start[0] - end[0]) + abs(start[1] - end[1]) != lower_bound:
            continue
        for corner in ((start[0], end[1]), (end[0], start[1])):
            path = [start] + ([corner] if corner != start and corner != end else []) + [end]
            if all(not _segment_problem(a, b, obstacles, lane_borders) for a, b in zip(path, path[1:])):
                direct.append(path)
    if direct:
        return min(direct, key=lambda path: (len(path), path))
    xs = {point[0] for point in starts + ends}
    ys = {point[1] for point in starts + ends}
    for x1, y1, x2, y2 in obstacles:
        xs.update((x1 - MARGIN, x2 + MARGIN))
        ys.update((y1 - MARGIN, y2 + MARGIN))
    for x1, x2, y in lane_borders:
        xs.update((x1 - MARGIN, x2 + MARGIN))
        ys.update((y - MARGIN, y + MARGIN))
    xs, ys = sorted(xs), sorted(ys)
    if len(xs) * len(ys) > MAX_GRID_POINTS:
        return None
    destinations = {(xs.index(x), ys.index(y)) for x, y in ends}
    queue = []
    distance = {}
    previous = {}
    for index, (x, y) in enumerate(starts):
        state = (xs.index(x), ys.index(y), 0, index if self_loop else 0)
        distance[state] = (0.0, 0)
        heapq.heappush(queue, (0.0, 0, state))
    destination = None
    while queue:
        length, bends, current = heapq.heappop(queue)
        if (length, bends) != distance[current]:
            continue
        i, j, direction, origin = current
        if (i, j) in destinations and length > EPS and (
            not self_loop or (xs[i], ys[j]) != starts[origin]
        ):
            destination = current
            break
        a = (xs[i], ys[j])
        for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                continue
            b = (xs[ni], ys[nj])
            if _segment_problem(a, b, obstacles, lane_borders):
                continue
            new_direction = 1 if ni != i else 2
            new_cost = (length + abs(a[0] - b[0]) + abs(a[1] - b[1]),
                        bends + int(direction != 0 and direction != new_direction))
            neighbor = (ni, nj, new_direction, origin)
            if new_cost < distance.get(neighbor, (math.inf, math.inf)):
                distance[neighbor] = new_cost
                previous[neighbor] = current
                heapq.heappush(queue, (*new_cost, neighbor))
    if destination is None:
        return None
    path = []
    node = destination
    while True:
        path.append((xs[node[0]], ys[node[1]]))
        if node not in previous:
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


def _overlap(first, second):
    return (min(first[2], second[2]) - max(first[0], second[0]) > EPS and
            min(first[3], second[3]) - max(first[1], second[1]) > EPS)


def _intentional_overlap(first, second, semantic):
    a, b = semantic[first], semantic[second]
    return (a.get("attachedToRef") == second or b.get("attachedToRef") == first or
            (a.tag == MODEL + "subProcess" and b in list(a.iter())) or
            (b.tag == MODEL + "subProcess" and a in list(b.iter())))


def _write_rect(shape, old, new):
    bounds = shape.find(BOUNDS)
    x1, y1, x2, y2 = new
    bounds.attrib.update({"x": str(x1), "y": str(y1), "width": str(x2 - x1), "height": str(y2 - y1)})
    dx, dy = x1 - old[0], y1 - old[1]
    if dx or dy:
        for label in shape.findall(f"{{{BPMNDI_NS}}}BPMNLabel"):
            label_bounds = label.find(BOUNDS)
            if label_bounds is not None:
                try:
                    label_bounds.set("x", str(_number(label_bounds, "x") + dx))
                    label_bounds.set("y", str(_number(label_bounds, "y") + dy))
                except (KeyError, ValueError):
                    pass


def _normalize_label(value):
    return " ".join((value or "").split()).casefold()


def _suppress_redundant_lane_names(semantic):
    changed = False
    participants = [element for element in semantic.values() if element.tag == MODEL + "participant"]
    for participant in participants:
        process = semantic.get(participant.get("processRef"))
        if process is None or sum(p.get("processRef") == participant.get("processRef") for p in participants) != 1:
            continue
        lanes = list(process.iter(MODEL + "lane"))
        if len(lanes) == 1 and _normalize_label(participant.get("name")) and (
            _normalize_label(participant.get("name")) == _normalize_label(lanes[0].get("name"))
        ):
            lanes[0].attrib.pop("name", None)
            changed = True
    return changed


def _separate_nodes(semantic, shapes, shape_elements):
    """Move overlapping ordinary nodes horizontally, expanding their containers."""
    warnings = []
    changed = False
    lane_for_node = {}
    pool_for_node = {}
    lane_pool = {}
    for pool_id, participant in semantic.items():
        if participant.tag != MODEL + "participant":
            continue
        process = semantic.get(participant.get("processRef"))
        if process is None:
            continue
        for element in process.iter():
            ref = element.get("id")
            if ref and element.tag.removeprefix(MODEL) in NODE_TAGS:
                pool_for_node[ref] = pool_id
            if element.tag == MODEL + "lane" and ref in shapes:
                lane_pool[ref] = pool_id
                for child in element.findall(MODEL + "flowNodeRef"):
                    node_id = (child.text or "").strip()
                    previous = lane_for_node.get(node_id)
                    if previous is None or ((shapes[ref][2] - shapes[ref][0]) * (shapes[ref][3] - shapes[ref][1]) <
                                            (shapes[previous][2] - shapes[previous][0]) * (shapes[previous][3] - shapes[previous][1])):
                        lane_for_node[node_id] = ref

    nodes = [ref for ref in shapes if ref in semantic and semantic[ref].tag.removeprefix(MODEL) in NODE_TAGS]
    locked = set()
    for ref in nodes:
        element = semantic[ref]
        if element.tag == MODEL + "boundaryEvent" and element.get("attachedToRef"):
            locked.update((ref, element.get("attachedToRef")))
        if element.tag == MODEL + "subProcess":
            children = {child.get("id") for child in element.iter() if child.get("id") in shapes and child is not element}
            if children:
                locked.add(ref)
                locked.update(children)

    placed = sorted((ref for ref in nodes if ref in locked), key=lambda ref: (*shapes[ref][:2], ref))
    movable = sorted((ref for ref in nodes if ref not in locked), key=lambda ref: (*shapes[ref][:2], ref))
    for ref in movable:
        old = shapes[ref]
        x, y, right, bottom = old
        width, height = right - x, bottom - y
        lane_id = lane_for_node.get(ref)
        container_id = lane_id or pool_for_node.get(ref)
        container = shapes.get(container_id)
        if container:
            x = max(x, container[0] + LANE_HEADER)
            if height + 2 * NODE_GAP <= container[3] - container[1]:
                y = min(max(y, container[1] + NODE_GAP), container[3] - NODE_GAP - height)
            else:
                warnings.append(f"Node {ref} does not fit vertically in its lane or pool.")
        while True:
            blockers = [shapes[other] for other in placed if not _intentional_overlap(ref, other, semantic)
                        and min(y + height, shapes[other][3]) - max(y, shapes[other][1]) > EPS
                        and x < shapes[other][2] + NODE_GAP - EPS
                        and x + width > shapes[other][0] - NODE_GAP + EPS]
            if not blockers:
                break
            x = max(rect[2] + NODE_GAP for rect in blockers)
        new = (x, y, x + width, y + height)
        if new != old:
            _write_rect(shape_elements[ref], old, new)
            shapes[ref] = new
            changed = True
        placed.append(ref)

    # Keep every lane of a pool the same width when a node requires more space.
    for pool_id in set(lane_pool.values()) | set(pool_for_node.values()):
        if pool_id not in shapes:
            continue
        related = [ref for ref in nodes if pool_for_node.get(ref) == pool_id]
        lanes = [ref for ref, owner in lane_pool.items() if owner == pool_id]
        right = max([shapes[pool_id][2]] + [shapes[ref][2] for ref in lanes] +
                    [shapes[ref][2] + NODE_GAP for ref in related])
        for ref in [pool_id] + lanes:
            old = shapes[ref]
            if right > old[2] + EPS:
                new = (old[0], old[1], right, old[3])
                _write_rect(shape_elements[ref], old, new)
                shapes[ref] = new
                changed = True

    for index, first in enumerate(nodes):
        for second in nodes[index + 1:]:
            if _overlap(shapes[first], shapes[second]) and not _intentional_overlap(first, second, semantic):
                warnings.append(f"BPMNShapes {first} and {second} overlap and could not be moved safely.")
    for ref in nodes:
        container_id = lane_for_node.get(ref) or pool_for_node.get(ref)
        if container_id in shapes:
            node, container = shapes[ref], shapes[container_id]
            if (node[0] < container[0] - EPS or node[1] < container[1] - EPS or
                    node[2] > container[2] + EPS or node[3] > container[3] + EPS):
                warnings.append(f"Node {ref} is not fully inside {container_id}.")
    for lane_id, pool_id in lane_pool.items():
        if pool_id in shapes:
            lane, pool = shapes[lane_id], shapes[pool_id]
            if (lane[0] < pool[0] - EPS or lane[1] < pool[1] - EPS or
                    lane[2] > pool[2] + EPS or lane[3] > pool[3] + EPS):
                warnings.append(f"Lane {lane_id} is not fully inside pool {pool_id}.")
    pools = [ref for ref in shapes if ref in semantic and semantic[ref].tag == MODEL + "participant"]
    for index, first in enumerate(pools):
        for second in pools[index + 1:]:
            if _overlap(shapes[first], shapes[second]):
                warnings.append(f"Pools {first} and {second} overlap.")
    return changed, warnings


def check_and_repair_layout(xml: str) -> tuple[str, list[str], list[str]]:
    """Return XML, blocking DI errors and unresolved cosmetic warnings.

    Preserve business objects and connections while adjusting redundant labels,
    node bounds, containers, edge anchors and Manhattan routes.
    Call after the basic XML syntax validator has accepted the document.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml, [], []  # the syntax validator reports this
    semantic = {el.get("id"): el for el in root.iter() if el.tag.startswith(MODEL) and el.get("id")}
    shapes, shape_elements, edges = {}, {}, {}
    errors, warnings = [], []
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
        shape_elements[ref] = shape
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

    changed = _suppress_redundant_lane_names(semantic)
    moved, placement_warnings = _separate_nodes(semantic, shapes, shape_elements)
    changed |= moved
    warnings.extend(placement_warnings)
    lane_borders = []
    for ref, rect in shapes.items():
        if ref in semantic and semantic[ref].tag == MODEL + "lane":
            lane_borders.extend(((rect[0], rect[2], rect[1]), (rect[0], rect[2], rect[3])))

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
        source_id, target_id = flow.get("sourceRef"), flow.get("targetRef")
        source, target = shapes.get(source_id), shapes.get(target_id)
        if source is None or target is None:
            warnings.append(f"BPMNEdge {ref} cannot be routed because an endpoint has no shape.")
            continue
        endpoints = [semantic.get(source_id), semantic.get(target_id)]
        obstacles = [rect for node_id, rect in shapes.items()
                     if node_id in semantic and semantic[node_id].tag.removeprefix(MODEL) in NODE_TAGS
                     and not (semantic[node_id].tag == MODEL + "subProcess" and
                              any(endpoint is not None and endpoint is not semantic[node_id] and
                                  endpoint in list(semantic[node_id].iter()) for endpoint in endpoints))]
        def flexible_anchor(node_id):
            element = semantic.get(node_id)
            if element is None:
                return False
            kind = element.tag.removeprefix(MODEL)
            return not (kind.endswith("Event") or kind.endswith("Gateway"))

        route = _route_between(source, target, obstacles, lane_borders, source_id == target_id,
                               flexible_anchor(source_id), flexible_anchor(target_id))
        if not route:
            warnings.append(f"BPMNEdge {ref} has no safe Manhattan route within the routing limit.")
            if not _on_boundary(points[0], source) or not _on_boundary(points[-1], target):
                errors.append(f"BPMNEdge {ref} has disconnected endpoints and could not be rerouted.")
            continue
        if route == points:
            continue
        for waypoint in waypoints:
            edge.remove(waypoint)
        for index, (x, y) in enumerate(route):
            edge.insert(index, ET.Element(WAYPOINT, {"x": str(x), "y": str(y)}))
        longest = max(zip(route, route[1:]), key=lambda pair: abs(pair[0][0] - pair[1][0]) + abs(pair[0][1] - pair[1][1]))
        for label in edge.findall(f"{{{BPMNDI_NS}}}BPMNLabel"):
            bounds = label.find(BOUNDS)
            if bounds is not None:
                try:
                    width, height = _number(bounds, "width"), _number(bounds, "height")
                    bounds.set("x", str((longest[0][0] + longest[1][0] - width) / 2))
                    bounds.set("y", str((longest[0][1] + longest[1][1]) / 2 - height - 5))
                except (KeyError, ValueError):
                    pass
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
