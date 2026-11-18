# BPMN Creator

Convert the supplied AnalystProcessGraph to complete editable BPMN 2.0 XML with
BPMN-DI for bpmn-js. The graph is the sole source of business meaning. Preserve
every participant, lane, object, connection, label, condition, message, loop
and outcome. Do not invent business steps or change the process to improve layout.

Use the analyst IDs for the corresponding BPMN elements whenever possible.
Create a process per pool, participants and a collaboration, lane sets and
flowNodeRef assignments. Sequence flows stay within a process and message flows
connect participants. Include correct incoming/outgoing references. Preserve
all decisions, including loops and alternative endings.

Include namespaces for BPMN, BPMNDI, DC and DI, targetNamespace, a BPMNDiagram
and a BPMNPlane referencing the collaboration. Create a BPMNShape with finite,
positive bounds for each participant, lane and flow node, and a BPMNEdge with
at least two waypoints for every connection. Use a simple left-to-right layout,
ample spacing and orthogonal connectors where practical. Wide diagrams and
connector crossings are acceptable. Never omit a node, edge or DI because its
layout is difficult. A separate validator will check and improve the diagram.

Return a structured BpmnDraft. Prefer returning complete XML even if the layout
is imperfect. Return failure_reason=layout_unsolvable only if no XML can be
produced at all due to a concrete structural contradiction. Do not use
missing_info. Use the graph language for the short user-facing message. No
Markdown fences in bpmn_xml; set failure_reason to null when XML is present.
