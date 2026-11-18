"""Regression graph and deterministic BPMN fixture for the amusement park."""

import xml.etree.ElementTree as ET

from app.services.bpmn_syntax import MODEL_NS, BPMNDI_NS, DC_NS, DI_NS

PARK_REQUEST = """Necesito el diagrama de cómo es la visita de una persona a mi parque de atracciones hasta que se sube a una atracción. El visitante llega al parque y va a la boletería. Ahí lo atienden, le cobran la entrada y le dan una pulsera. Después pasa por Seguridad, que revisa su mochila. Si lleva algo prohibido, como botellas de vidrio, Seguridad le pide que lo deje en el guardarropa y recién entonces lo deja pasar. Si no lleva nada prohibido, lo deja pasar directamente. Adentro, el visitante va a la atracción que quiere y le muestra la pulsera al operador de la atracción. El operador mide al visitante. Si mide menos de 1,20 m, le avisa que no puede subir y ahí termina su visita a esa atracción. Si mide 1,20 m o más, el operador revisa si hay lugar en el próximo turno. Si no hay lugar, el visitante espera y se vuelve a revisar en el turno siguiente, tantas veces como haga falta. Cuando hay lugar, el operador lo sienta, le ajusta el cinturón y arranca la atracción. Cuando termina el recorrido, el operador libera el asiento. El proceso termina cuando el operador libera el asiento."""

LANES = [("visitante", "Visitante"), ("boleteria", "Boletería"),
         ("seguridad", "Seguridad"), ("operador", "Operador")]
NODES = [
    ("inicio", "start_event", "Llegada al parque", "visitante"),
    ("ir_boleteria", "activity", "Ir a la boletería", "visitante"),
    ("atender", "activity", "Atender al visitante", "boleteria"),
    ("cobrar", "activity", "Cobrar entrada", "boleteria"),
    ("pulsera", "activity", "Entregar pulsera", "boleteria"),
    ("mochila", "activity", "Revisar mochila", "seguridad"),
    ("prohibido", "gateway", "¿Lleva algo prohibido?", "seguridad"),
    ("pedir", "activity", "Pedir dejar objeto en guardarropa", "seguridad"),
    ("guardar", "activity", "Dejar objeto en guardarropa", "visitante"),
    ("pasar", "activity", "Dejar pasar", "seguridad"),
    ("ir_atraccion", "activity", "Ir a la atracción", "visitante"),
    ("mostrar", "activity", "Mostrar pulsera", "visitante"),
    ("medir", "activity", "Medir al visitante", "operador"),
    ("altura", "gateway", "¿Alcanza la altura?", "operador"),
    ("avisar", "activity", "Avisar que no puede subir", "operador"),
    ("fin_rechazo", "end_event", "Visita a la atracción terminada", "operador"),
    ("revisar_lugar", "activity", "Revisar lugar en próximo turno", "operador"),
    ("lugar", "gateway", "¿Hay lugar?", "operador"),
    ("esperar", "activity", "Esperar siguiente turno", "visitante"),
    ("sentar", "activity", "Sentar al visitante", "operador"),
    ("cinturon", "activity", "Ajustar cinturón", "operador"),
    ("arrancar", "activity", "Arrancar atracción", "operador"),
    ("recorrido", "intermediate_event", "Termina el recorrido", "operador"),
    ("liberar", "activity", "Liberar asiento", "operador"),
    ("fin", "end_event", "Asiento liberado", "operador"),
]
LINKS = [
    ("inicio", "ir_boleteria", None), ("ir_boleteria", "atender", None),
    ("atender", "cobrar", None), ("cobrar", "pulsera", None),
    ("pulsera", "mochila", None), ("mochila", "prohibido", None),
    ("prohibido", "pedir", "Sí"), ("pedir", "guardar", None),
    ("guardar", "pasar", None), ("prohibido", "pasar", "No"),
    ("pasar", "ir_atraccion", None), ("ir_atraccion", "mostrar", None),
    ("mostrar", "medir", None), ("medir", "altura", None),
    ("altura", "avisar", "Menos de 1,20 m"), ("avisar", "fin_rechazo", None),
    ("altura", "revisar_lugar", "1,20 m o más"), ("revisar_lugar", "lugar", None),
    ("lugar", "esperar", "No hay lugar"), ("esperar", "revisar_lugar", None),
    ("lugar", "sentar", "Hay lugar"), ("sentar", "cinturon", None),
    ("cinturon", "arrancar", None), ("arrancar", "recorrido", None),
    ("recorrido", "liberar", None), ("liberar", "fin", None),
]


def park_graph():
    return {
        "title": "Visita al parque de atracciones", "language": "Spanish",
        "pools": [{"id": "parque", "name": "Parque", "kind": "organization"}],
        "swimlanes": [{"id": lane, "name": name, "pool_id": "parque"} for lane, name in LANES],
        "objects": [{"id": id_, "kind": kind, "label": label, "pool_id": "parque", "lane_id": lane,
                     "gateway_type": "exclusive" if kind == "gateway" else None}
                    for id_, kind, label, lane in NODES],
        "connections": [{"id": f"f{i}", "source_id": source, "target_id": target,
                         "kind": "sequence", "condition": condition}
                        for i, (source, target, condition) in enumerate(LINKS)],
    }


def park_xml():
    b, bd, dc, di = (f"{{{ns}}}" for ns in (MODEL_NS, BPMNDI_NS, DC_NS, DI_NS))
    for prefix, ns in (("bpmn", MODEL_NS), ("bpmndi", BPMNDI_NS), ("dc", DC_NS), ("di", DI_NS)):
        ET.register_namespace(prefix, ns)
    root = ET.Element(b + "definitions", {"id": "defs", "targetNamespace": "http://bpmn.io/schema/bpmn"})
    process = ET.SubElement(root, b + "process", {"id": "process", "isExecutable": "false"})
    lane_set = ET.SubElement(process, b + "laneSet", {"id": "lanes"})
    for lane_id, name in LANES:
        lane = ET.SubElement(lane_set, b + "lane", {"id": lane_id, "name": name})
        for id_, _, _, owner in NODES:
            if owner == lane_id:
                ET.SubElement(lane, b + "flowNodeRef").text = id_
    tags = {"start_event": "startEvent", "end_event": "endEvent", "activity": "task",
            "gateway": "exclusiveGateway", "intermediate_event": "intermediateCatchEvent"}
    for id_, kind, label, _ in NODES:
        ET.SubElement(process, b + tags[kind], {"id": id_, "name": label})
    for i, (source, target, condition) in enumerate(LINKS):
        attrs = {"id": f"f{i}", "sourceRef": source, "targetRef": target}
        if condition:
            attrs["name"] = condition
        ET.SubElement(process, b + "sequenceFlow", attrs)
    collab = ET.SubElement(root, b + "collaboration", {"id": "collab"})
    ET.SubElement(collab, b + "participant", {"id": "parque", "name": "Parque", "processRef": "process"})
    diagram = ET.SubElement(root, bd + "BPMNDiagram", {"id": "diagram"})
    plane = ET.SubElement(diagram, bd + "BPMNPlane", {"id": "plane", "bpmnElement": "collab"})

    def shape(id_, x, y, w, h):
        s = ET.SubElement(plane, bd + "BPMNShape", {"id": id_ + "_di", "bpmnElement": id_})
        ET.SubElement(s, dc + "Bounds", {"x": str(x), "y": str(y), "width": str(w), "height": str(h)})

    shape("parque", 0, 0, 6000, 800)
    for index, (lane_id, _) in enumerate(LANES):
        shape(lane_id, 30, index * 200, 5970, 200)
    positions = {}
    for index, (id_, kind, _, lane) in enumerate(NODES):
        y = next(i for i, (lane_id, _) in enumerate(LANES) if lane_id == lane) * 200 + 60
        x = 100 + 200 * index
        w, h = (100, 80) if kind == "activity" else (36, 36)
        positions[id_] = (x, y, w, h)
        shape(id_, x, y, w, h)
    for i, (source, target, _) in enumerate(LINKS):
        edge = ET.SubElement(plane, bd + "BPMNEdge", {"id": f"f{i}_di", "bpmnElement": f"f{i}"})
        sx, sy, sw, sh = positions[source]
        tx, ty, tw, th = positions[target]
        ET.SubElement(edge, di + "waypoint", {"x": str(sx + sw), "y": str(sy + sh / 2)})
        ET.SubElement(edge, di + "waypoint", {"x": str(tx), "y": str(ty + th / 2)})
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
