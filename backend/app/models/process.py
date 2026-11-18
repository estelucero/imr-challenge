"""Internal high-level business-process graph shared by the agents."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProcessScope(BaseModel):
    business: str | None = Field(default=None, description="Business or area owning the process")
    purpose: str | None = Field(default=None, description="Why the process exists")
    start: str | None = Field(default=None, description="Trigger or event that starts the process")
    end_condition: str | None = Field(default=None, description="Condition that closes the process")
    includes: list[str] = Field(default_factory=list, description="Work included in this process scope")
    excludes: list[str] = Field(default_factory=list, description="Work explicitly outside this scope")
    outcome: str | None = Field(default=None, description="Expected result of a successful process")


class ProcessEntity(BaseModel):
    """Pool-level participant: an organization, independent person, or system."""

    id: str = Field(description="Unique ID referenced by swimlanes and flow objects")
    name: str = Field(description="Independent participant name")
    kind: Literal["organization", "person", "system"] = Field(
        default="organization", description="Participant category"
    )
    external: bool | None = Field(
        default=None,
        description="Whether it is external to the organization owning the process, if known",
    )


class ProcessSwimlane(BaseModel):
    """Responsibility lane contained by one entity/pool."""

    id: str = Field(description="Unique lane ID")
    entity_id: str = Field(description="ID of the parent pool/entity")
    name: str = Field(description="Responsibility or department name")
    kind: Literal["department", "role", "person", "system", "activity"] = Field(
        default="department", description="Type of responsibility represented by the lane"
    )


class ProcessFlowObject(BaseModel):
    """High-level event, activity, or gateway; never a BPMN XML element."""

    id: str = Field(description="Unique flow-object ID referenced by connections")
    kind: Literal[
        "start_event", "intermediate_event", "end_event", "activity", "gateway"
    ]
    label: str = Field(description="Concise business-language event, activity, or decision label")
    entity_id: str | None = Field(default=None, description="Owning entity/pool ID, when known")
    swimlane_id: str | None = Field(default=None, description="Responsible swimlane ID, when known")
    event_type: Literal["message", "timer", "error", "signal"] | None = Field(
        default=None, description="Event trigger/type, only when relevant and known"
    )
    activity_type: Literal[
        "task", "subprocess", "loop", "multiple_instance", "compensation",
        "ad_hoc", "transaction", "call_activity",
    ] | None = Field(default=None, description="Activity pattern, only when stated or clearly implied")
    gateway_type: Literal["exclusive", "inclusive", "parallel", "event_based"] | None = Field(
        default=None, description="Decision/split semantics, if the process describes them"
    )
    description: str | None = Field(default=None, description="Additional business context")


class ProcessArtifact(BaseModel):
    """Optional data or explanatory artifact; does not control process order."""

    id: str = Field(description="Unique artifact ID referenced by associations")
    kind: Literal["data_object", "data_store", "annotation", "group"]
    label: str = Field(description="Business name of the data or explanatory artifact")
    direction: Literal["input", "output", "collection", "stored"] | None = Field(
        default=None, description="Data-object direction/purpose when known"
    )
    description: str | None = Field(default=None, description="Additional data or annotation context")


class ProcessConnection(BaseModel):
    """A typed relation between flow objects, or an artifact and flow object."""

    id: str = Field(description="Unique connection ID")
    source_id: str = Field(description="Source flow-object or artifact ID")
    target_id: str = Field(description="Target flow-object or artifact ID")
    kind: Literal["sequence", "message", "association"]
    condition: str | None = Field(default=None, description="Decision outcome/condition on a sequence")
    message: str | None = Field(default=None, description="Information exchanged on a message connection")


class ClarifierResult(BaseModel):
    """Clarifier's recipient, plain-text message, and optional questions."""

    recipient: Literal["client", "analyst"]
    message: str
    questions: list[str] = Field(default_factory=list, max_length=3)


class AnalystPool(BaseModel):
    """Compact pool/participant emitted by the Process Analyst."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    kind: Literal["organization", "person", "system"] = "organization"
    external: bool | None = None


class AnalystSwimlane(BaseModel):
    """Compact responsibility lane emitted by the Process Analyst."""

    model_config = ConfigDict(extra="forbid")

    id: str
    pool_id: str
    name: str
    kind: Literal["department", "role", "person", "system", "activity"] = "department"


class AnalystObject(BaseModel):
    """Event, activity, or gateway in the analyst's compact graph."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal[
        "start_event", "intermediate_event", "end_event", "activity", "gateway"
    ]
    label: str
    pool_id: str | None = None
    lane_id: str | None = None
    event_type: Literal["message", "timer", "error", "signal"] | None = None
    activity_type: Literal[
        "task", "subprocess", "loop", "multiple_instance", "compensation",
        "ad_hoc", "transaction", "call_activity",
    ] | None = None
    gateway_type: Literal["exclusive", "inclusive", "parallel", "event_based"] | None = None
    description: str | None = None


class AnalystConnection(BaseModel):
    """Sequence or inter-pool message connection in the compact graph."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_id: str
    target_id: str
    kind: Literal["sequence", "message"]
    condition: str | None = None
    message: str | None = None


class AnalystProcessGraph(BaseModel):
    """Small graph contract passed from the Process Analyst to the creator."""

    model_config = ConfigDict(extra="forbid")

    title: str
    language: str
    pools: list[AnalystPool] = Field(default_factory=list)
    swimlanes: list[AnalystSwimlane] = Field(default_factory=list)
    objects: list[AnalystObject] = Field(default_factory=list)
    connections: list[AnalystConnection] = Field(default_factory=list)
    diagram_preference: Literal["combined", "separate"] | None = None


class BusinessProcessSpec(BaseModel):
    """Legacy graph contract retained for existing test fixtures."""

    title: str
    language: str
    scope: ProcessScope = Field(default_factory=ProcessScope)
    entities: list[ProcessEntity] = Field(default_factory=list)
    swimlanes: list[ProcessSwimlane] = Field(default_factory=list)
    flow_objects: list[ProcessFlowObject] = Field(default_factory=list)
    artifacts: list[ProcessArtifact] = Field(default_factory=list)
    connections: list[ProcessConnection] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    diagram_preference: Literal["combined", "separate"] | None = None

    @model_validator(mode="after")
    def validate_graph_references(self):
        entities = {entity.id for entity in self.entities}
        lanes = {lane.id: lane for lane in self.swimlanes}
        objects = {obj.id: obj for obj in self.flow_objects}
        artifacts = {artifact.id for artifact in self.artifacts}

        id_groups = [
            [entity.id for entity in self.entities],
            [lane.id for lane in self.swimlanes],
            [obj.id for obj in self.flow_objects],
            [artifact.id for artifact in self.artifacts],
            [connection.id for connection in self.connections],
        ]
        all_ids = [item_id for group in id_groups for item_id in group]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("process element IDs must be globally unique")

        for lane in self.swimlanes:
            if lane.entity_id not in entities:
                raise ValueError(f"swimlane {lane.id} references an unknown entity")

        for obj in self.flow_objects:
            if obj.entity_id is not None and obj.entity_id not in entities:
                raise ValueError(f"flow object {obj.id} references an unknown entity")
            if obj.swimlane_id is not None:
                lane = lanes.get(obj.swimlane_id)
                if lane is None:
                    raise ValueError(f"flow object {obj.id} references an unknown swimlane")
                if obj.entity_id is not None and lane.entity_id != obj.entity_id:
                    raise ValueError(f"flow object {obj.id} owner conflicts with its swimlane")

        for connection in self.connections:
            source_object = objects.get(connection.source_id)
            target_object = objects.get(connection.target_id)
            if connection.kind in {"sequence", "message"}:
                if source_object is None or target_object is None:
                    raise ValueError(
                        f"{connection.kind} connection {connection.id} must join flow objects"
                    )
                if connection.kind == "sequence":
                    if (
                        source_object.entity_id is not None
                        and target_object.entity_id is not None
                        and source_object.entity_id != target_object.entity_id
                    ):
                        raise ValueError("sequence connections must stay within one entity/pool")
                elif source_object.kind != "activity" or target_object.kind != "activity":
                    raise ValueError("message connections must join sending/receiving activities")
            elif not (
                (connection.source_id in artifacts and target_object is not None)
                or (source_object is not None and connection.target_id in artifacts)
            ):
                raise ValueError(
                    f"association {connection.id} must join one artifact and one flow object"
                )

            if connection.kind == "message" and source_object and target_object:
                if (
                    source_object.entity_id is not None
                    and target_object.entity_id is not None
                    and source_object.entity_id == target_object.entity_id
                ):
                    raise ValueError("message connections must cross entity/pool boundaries")
        return self


class ProcessAnalysis(BaseModel):
    """Legacy wrapper; the Process Analyst now returns AnalystProcessGraph."""

    process: BusinessProcessSpec
    gaps: list[str] = Field(
        default_factory=list,
        description="Minimal business uncertainties that could make the flow incorrect",
    )


def validate_analyst_graph(graph: AnalystProcessGraph) -> None:
    """Validate the analyst's graph without transforming the creator's input."""
    if not graph.pools:
        raise ValueError("analyst graph must contain at least one pool")
    if not graph.objects:
        raise ValueError("analyst graph must contain at least one process object")

    ids = [
        item.id
        for group in (graph.pools, graph.swimlanes, graph.objects, graph.connections)
        for item in group
    ]
    if len(ids) != len(set(ids)):
        raise ValueError("process element IDs must be globally unique")

    pools = {pool.id for pool in graph.pools}
    lanes = {lane.id: lane for lane in graph.swimlanes}
    objects = {obj.id: obj for obj in graph.objects}

    for lane in graph.swimlanes:
        if lane.pool_id not in pools:
            raise ValueError(f"swimlane {lane.id} references an unknown pool")

    for obj in graph.objects:
        if obj.pool_id is not None and obj.pool_id not in pools:
            raise ValueError(f"object {obj.id} references an unknown pool")
        if obj.lane_id is not None:
            lane = lanes.get(obj.lane_id)
            if lane is None:
                raise ValueError(f"object {obj.id} references an unknown swimlane")
            if obj.pool_id is not None and lane.pool_id != obj.pool_id:
                raise ValueError(f"object {obj.id} conflicts with its swimlane's pool")

    def object_pool(obj: AnalystObject) -> str | None:
        return obj.pool_id or (lanes[obj.lane_id].pool_id if obj.lane_id else None)

    for connection in graph.connections:
        source = objects.get(connection.source_id)
        target = objects.get(connection.target_id)
        if source is None or target is None:
            raise ValueError(f"connection {connection.id} references an unknown object")
        source_pool, target_pool = object_pool(source), object_pool(target)
        if connection.kind == "sequence":
            if (
                source_pool is not None
                and target_pool is not None
                and source_pool != target_pool
            ):
                raise ValueError("sequence connections must stay within one pool")
        elif source.kind != "activity" or target.kind != "activity":
            raise ValueError("message connections must join sending/receiving activities")
        elif (
            source_pool is not None
            and target_pool is not None
            and source_pool == target_pool
        ):
            raise ValueError("message connections must cross pool boundaries")
