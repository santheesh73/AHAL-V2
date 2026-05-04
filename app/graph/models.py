"""Pydantic models for Phase 3 knowledge graph results."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low"]
NodeType = Literal[
    "file", "module", "framework", "dependency", "api_endpoint", "database",
    "entrypoint", "function", "class", "workflow_step", "unknown",
]
EdgeType = Literal[
    "contains", "imports", "depends_on", "defines", "calls", "handles",
    "routes_to", "uses_database", "belongs_to", "entrypoint_of",
    "part_of_workflow", "related_to",
]


class GraphEvidence(BaseModel):
    file: str
    reason: str
    snippet: Optional[str] = None
    confidence: ConfidenceLevel


class GraphNode(BaseModel):
    id: str
    type: NodeType
    name: str
    label: str
    path: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    evidence: list[GraphEvidence] = Field(default_factory=list)
    confidence: ConfidenceLevel


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: EdgeType
    label: str
    metadata: dict = Field(default_factory=dict)
    evidence: list[GraphEvidence] = Field(default_factory=list)
    confidence: ConfidenceLevel


class GraphStats(BaseModel):
    node_count: int = 0
    edge_count: int = 0
    files: int = 0
    modules: int = 0
    api_endpoints: int = 0
    databases: int = 0
    dependencies: int = 0
    orphan_nodes: int = 0
    confidence_score: float = 0.0


class KnowledgeGraphResult(BaseModel):
    session_id: Optional[str] = None
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    stats: GraphStats = Field(default_factory=GraphStats)
    warnings: list[str] = Field(default_factory=list)
    evidence_count: int = 0


class GraphQueryResult(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

