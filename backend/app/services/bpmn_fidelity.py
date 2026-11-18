"""Check that the generated BPMN still contains the analyst's graph."""

import xml.etree.ElementTree as ET

from app.services.bpmn_syntax import MODEL_NS

NS = f"{{{MODEL_NS}}}"
KINDS = {
    "start_event": {"startEvent"},
    "end_event": {"endEvent"},
    "intermediate_event": {"intermediateCatchEvent", "intermediateThrowEvent"},
    "activity": {"task", "userTask", "serviceTask", "sendTask", "receiveTask", "manualTask",
                 "businessRuleTask", "scriptTask", "subProcess", "callActivity", "transaction", "adHocSubProcess"},
    "gateway": {"exclusiveGateway", "inclusiveGateway", "parallelGateway", "eventBasedGateway", "complexGateway"},
}


def validate_graph_fidelity(xml: str, graph: dict) -> list[str]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    elements = [element for element in root.iter() if element.tag.startswith(NS)]
    by_id = {element.get("id"): element for element in elements if element.get("id")}
    errors = []
    used = set()

    def match(item, tags, label_key, name_matches=None):
        name = item.get(label_key) or ""
        name_matches = name_matches or (lambda element: element.get("name", "") == name)
        element = by_id.get(item.get("id"))
        if element is None:
            matches = [candidate for candidate in elements if candidate.tag.removeprefix(NS) in tags
                       and name_matches(candidate) and candidate.get("id") not in used]
            element = matches[0] if len(matches) == 1 else None
        if element is None or element.tag.removeprefix(NS) not in tags or not name_matches(element):
            errors.append(f"Missing or changed {item.get('id')} ({name}).")
            return None
        used.add(element.get("id"))
        return element

    pools = {item["id"]: match(item, {"participant"}, "name") for item in graph.get("pools", [])}

    def lane_name_matches(item, lane):
        name = item.get("name") or ""
        if lane.get("name", "") == name:
            return True
        pool = pools.get(item.get("pool_id"))
        normalize = lambda value: " ".join((value or "").split()).casefold()
        if lane.get("name") or pool is None or not normalize(name) or normalize(name) != normalize(pool.get("name")):
            return False
        process = by_id.get(pool.get("processRef"))
        graph_lanes = [candidate for candidate in graph.get("swimlanes", []) if candidate.get("pool_id") == item.get("pool_id")]
        return process is not None and len(graph_lanes) == 1 and list(process.iter(NS + "lane")) == [lane]

    lanes = {item["id"]: match(item, {"lane"}, "name", lambda element, item=item: lane_name_matches(item, element))
             for item in graph.get("swimlanes", [])}
    nodes = {item["id"]: match(item, KINDS.get(item.get("kind"), set()), "label")
             for item in graph.get("objects", [])}

    for item in graph.get("objects", []):
        node = nodes.get(item["id"])
        pool = pools.get(item.get("pool_id"))
        lane = lanes.get(item.get("lane_id"))
        if node is None:
            continue
        gateway_type = item.get("gateway_type")
        if gateway_type and node.tag != NS + {
            "exclusive": "exclusiveGateway", "inclusive": "inclusiveGateway",
            "parallel": "parallelGateway", "event_based": "eventBasedGateway",
        }.get(gateway_type, ""):
            errors.append(f"Object {item['id']} has a different gateway type.")
        event_type = item.get("event_type")
        if event_type and not any(child.tag == NS + event_type + "EventDefinition" for child in node):
            errors.append(f"Object {item['id']} is missing its {event_type} event definition.")
        if lane is not None and node.get("id") not in {
            (ref.text or "").strip() for ref in lane.findall(NS + "flowNodeRef")
        }:
            errors.append(f"Object {item['id']} is not assigned to its analyst lane.")
        if pool is not None:
            process = by_id.get(pool.get("processRef"))
            if process is None or node not in list(process.iter()):
                errors.append(f"Object {item['id']} is not in its analyst pool's process.")

    for item in graph.get("swimlanes", []):
        lane, pool = lanes.get(item["id"]), pools.get(item.get("pool_id"))
        if lane is not None and pool is not None:
            process = by_id.get(pool.get("processRef"))
            if process is None or lane not in list(process.iter()):
                errors.append(f"Lane {item['id']} is not in its analyst pool's process.")

    matched_nodes = {node.get("id") for node in nodes.values() if node is not None}
    for element in elements:
        if element.tag in {NS + "participant", NS + "lane"} and element.get("id") not in used:
            errors.append(f"Unexpected participant or lane {element.get('id')}.")
        if element.tag.removeprefix(NS) in set().union(*KINDS.values()) and element.get("id") not in matched_nodes:
            errors.append(f"Unexpected process object {element.get('id')}.")

    flows = [element for element in elements if element.tag in {NS + "sequenceFlow", NS + "messageFlow"}]
    matched_flows = set()
    for item in graph.get("connections", []):
        source, target = nodes.get(item.get("source_id")), nodes.get(item.get("target_id"))
        if source is None or target is None:
            continue
        tag = NS + ("sequenceFlow" if item.get("kind") == "sequence" else "messageFlow")
        candidates = [flow for flow in flows if flow.get("id") not in matched_flows and flow.tag == tag and
                      flow.get("sourceRef") == source.get("id") and flow.get("targetRef") == target.get("id")]
        if not candidates:
            errors.append(f"Missing or changed connection {item['id']}.")
            continue
        value = item.get("condition") or item.get("message")
        def preserves_value(flow):
            message = by_id.get(flow.get("messageRef"))
            return (value == flow.get("name") or (message is not None and value == message.get("name"))
                    or any(value == (child.text or "").strip() for child in flow.iter()))

        matching = [flow for flow in candidates if not value or preserves_value(flow)]
        if not matching:
            errors.append(f"Missing condition or message on connection {item['id']}: {value}.")
        else:
            matched_flows.add(matching[0].get("id"))
    for flow in flows:
        if flow.get("id") not in matched_flows:
            errors.append(f"Unexpected process connection {flow.get('id')}.")
    return errors
