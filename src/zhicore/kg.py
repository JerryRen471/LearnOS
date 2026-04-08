"""Knowledge graph extraction and local persistence for Phase 2."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from zhicore.types import Chunk

NODE_TYPES = {"Concept", "Entity", "Definition", "Formula"}
EDGE_TYPES = {"related-to", "is-a", "derived-from", "used-in"}
TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]*|[\u4e00-\u9fff]{2,}")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "using",
    "used",
    "this",
    "these",
    "those",
    "we",
    "you",
    "it",
    "通过",
    "以及",
    "用于",
    "一种",
    "一个",
    "这个",
    "进行",
    "支持",
    "相关",
    "可以",
    "系统",
}

_GENERIC_TERMS = {
    "system",
    "method",
    "methods",
    "result",
    "results",
    "paper",
    "approach",
    "model",
    "models",
    "algorithm",
    "algorithms",
    "framework",
    "analysis",
    "experiment",
    "experiments",
    "data",
    "process",
    "performance",
    "effective",
    "robust",
    "general",
    "introduction",
    "conclusion",
    "related",
    "work",
    "section",
    "figure",
    "table",
    "example",
    "examples",
    "problem",
    "problems",
    "task",
    "tasks",
    "study",
    "studies",
    "support",
    "using",
}

_EN_WORD = r"[A-Za-z][A-Za-z0-9_-]{1,40}"
_ZH_WORD = r"[\u4e00-\u9fff]{2,20}"
_WORD = rf"(?:{_EN_WORD}|{_ZH_WORD})"

_PATTERNS = {
    "is-a": [
        re.compile(
            rf"(?P<src>{_WORD})\s+is\s+(?:a|an)\s+(?:type|kind)\s+of\s+(?P<dst>{_WORD})",
            re.IGNORECASE,
        ),
        re.compile(rf"(?P<src>{_WORD})\s+is\s+(?:a|an)\s+(?P<dst>{_WORD})", re.IGNORECASE),
        re.compile(rf"(?P<src>{_WORD})\s*是\s*(?:一种|一类|一个)\s*(?P<dst>{_WORD})"),
    ],
    "used-in": [
        re.compile(rf"(?P<src>{_WORD})\s+used\s+in\s+(?P<dst>{_WORD})", re.IGNORECASE),
        re.compile(rf"(?P<src>{_WORD})\s*用于\s*(?P<dst>{_WORD})"),
    ],
    "derived-from": [
        re.compile(rf"(?P<src>{_WORD})\s+derived\s+from\s+(?P<dst>{_WORD})", re.IGNORECASE),
    ],
    "related-to": [
        re.compile(rf"(?P<src>{_WORD})\s+relate(?:d)?\s+to\s+(?P<dst>{_WORD})", re.IGNORECASE),
        re.compile(rf"(?P<src>{_WORD})\s+associated\s+with\s+(?P<dst>{_WORD})", re.IGNORECASE),
        re.compile(rf"(?P<src>{_WORD})\s+depends\s+on\s+(?P<dst>{_WORD})", re.IGNORECASE),
        re.compile(rf"(?P<src>{_WORD})\s*相关(?:于|)\s*(?P<dst>{_WORD})"),
        re.compile(rf"(?P<src>{_WORD})\s*关联(?:于|)\s*(?P<dst>{_WORD})"),
        re.compile(rf"(?P<src>{_WORD})\s*依赖\s*(?P<dst>{_WORD})"),
        re.compile(rf"(?P<src>{_WORD})\s*基于\s*(?P<dst>{_WORD})"),
    ],
}


@dataclass(slots=True)
class KnowledgeNode:
    node_id: str
    node_type: str
    name: str
    description: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class KnowledgeEdge:
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str
    evidence_chunk_id: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class KnowledgeGraph:
    nodes: dict[str, KnowledgeNode] = field(default_factory=dict)
    edges: list[KnowledgeEdge] = field(default_factory=list)
    chunk_concepts: dict[str, list[str]] = field(default_factory=dict)

    def add_node(
        self,
        node_type: str,
        name: str,
        description: str = "",
        metadata: dict[str, str] | None = None,
    ) -> str:
        if node_type not in NODE_TYPES:
            raise ValueError(f"Unsupported node type: {node_type}")
        node_id = _stable_id(node_type, _normalize_key(name))
        if node_id not in self.nodes:
            self.nodes[node_id] = KnowledgeNode(
                node_id=node_id,
                node_type=node_type,
                name=name.strip(),
                description=description.strip(),
                metadata=metadata or {},
            )
        return node_id

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        evidence_chunk_id: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"Unsupported edge type: {edge_type}")
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError("Edge references unknown node ids.")
        edge_id = _stable_id(edge_type, f"{source_id}|{target_id}|{evidence_chunk_id}")
        if any(edge.edge_id == edge_id for edge in self.edges):
            return edge_id
        self.edges.append(
            KnowledgeEdge(
                edge_id=edge_id,
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type,
                evidence_chunk_id=evidence_chunk_id,
                metadata=metadata or {},
            )
        )
        return edge_id

    def map_chunk_concepts(self, chunk_id: str, concept_ids: list[str]) -> None:
        unique_ids = sorted({item for item in concept_ids if item in self.nodes})
        self.chunk_concepts[chunk_id] = unique_ids

    def concepts_for_chunks(self, chunk_ids: list[str]) -> list[str]:
        concept_ids: set[str] = set()
        for chunk_id in chunk_ids:
            concept_ids.update(self.chunk_concepts.get(chunk_id, []))
        return sorted(concept_ids)

    def resolve_concept_ids(self, text: str, max_results: int = 8) -> list[str]:
        lowered = text.lower()
        matches: list[str] = []
        for node in self.nodes.values():
            if node.node_type not in {"Concept", "Entity", "Formula"}:
                continue
            name = node.name.lower()
            if name and (name in lowered or lowered in name):
                matches.append(node.node_id)
        return sorted(set(matches))[:max_results]

    def subgraph(
        self,
        seed_node_ids: list[str],
        hops: int = 1,
        max_nodes: int = 80,
        max_edges_per_node: int = 12,
    ) -> dict[str, list[dict]]:
        if hops < 0:
            raise ValueError("hops must be >= 0")
        if not seed_node_ids:
            return {"nodes": [], "edges": []}

        frontier = [node_id for node_id in seed_node_ids if node_id in self.nodes]
        visited = set(frontier)
        sub_edges: list[KnowledgeEdge] = []
        edge_counts: dict[str, int] = {node_id: 0 for node_id in frontier}
        remaining_hops = hops
        edge_priority = {"is-a": 0, "used-in": 1, "derived-from": 2, "related-to": 3}
        while frontier and remaining_hops > 0 and len(visited) < max_nodes:
            next_frontier: list[str] = []
            edges_sorted = sorted(
                self.edges,
                key=lambda item: (edge_priority.get(item.edge_type, 9), item.edge_id),
            )
            for edge in edges_sorted:
                source_in = edge.source_id in frontier
                target_in = edge.target_id in frontier
                if not source_in and not target_in:
                    continue
                anchor = edge.source_id if source_in else edge.target_id
                if edge_counts.get(anchor, 0) >= max_edges_per_node:
                    continue
                edge_counts[anchor] = edge_counts.get(anchor, 0) + 1
                sub_edges.append(edge)
                if source_in and edge.target_id not in visited and len(visited) < max_nodes:
                    visited.add(edge.target_id)
                    edge_counts.setdefault(edge.target_id, 0)
                    next_frontier.append(edge.target_id)
                if target_in and edge.source_id not in visited and len(visited) < max_nodes:
                    visited.add(edge.source_id)
                    edge_counts.setdefault(edge.source_id, 0)
                    next_frontier.append(edge.source_id)
            frontier = next_frontier
            remaining_hops -= 1

        node_payload = [asdict(self.nodes[node_id]) for node_id in sorted(visited)]
        edge_payload = [asdict(edge) for edge in sorted(sub_edges, key=lambda item: item.edge_id)]
        return {"nodes": node_payload, "edges": edge_payload}

    def save(self, graph_path: str) -> None:
        path = Path(graph_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "nodes": [asdict(node) for node in sorted(self.nodes.values(), key=lambda item: item.node_id)],
            "edges": [asdict(edge) for edge in sorted(self.edges, key=lambda item: item.edge_id)],
            "chunk_concepts": self.chunk_concepts,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def stats(self, top_hubs: int = 12) -> dict[str, object]:
        edge_type_counts: dict[str, int] = {}
        degrees: dict[str, int] = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            edge_type_counts[edge.edge_type] = edge_type_counts.get(edge.edge_type, 0) + 1
            degrees[edge.source_id] = degrees.get(edge.source_id, 0) + 1
            degrees[edge.target_id] = degrees.get(edge.target_id, 0) + 1

        hubs = sorted(degrees.items(), key=lambda item: (-item[1], item[0]))[: max(0, int(top_hubs))]
        hub_payload: list[dict[str, object]] = []
        for node_id, degree in hubs:
            node = self.nodes.get(node_id)
            if node is None:
                continue
            hub_payload.append(
                {
                    "node_id": node_id,
                    "name": node.name,
                    "node_type": node.node_type,
                    "degree": degree,
                }
            )
        total_edges = len(self.edges)
        related_edges = int(edge_type_counts.get("related-to", 0))
        related_ratio = round((related_edges / total_edges), 4) if total_edges else 0.0
        return {
            "nodes": len(self.nodes),
            "edges": total_edges,
            "edge_types": dict(sorted(edge_type_counts.items(), key=lambda item: (-item[1], item[0]))),
            "related_to_ratio": related_ratio,
            "top_hubs": hub_payload,
        }

    @classmethod
    def load(cls, graph_path: str) -> "KnowledgeGraph":
        path = Path(graph_path)
        if not path.exists():
            raise FileNotFoundError(f"Knowledge graph file not found: {graph_path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        graph = cls()
        for node_item in raw.get("nodes", []):
            node = KnowledgeNode(**node_item)
            graph.nodes[node.node_id] = node
        for edge_item in raw.get("edges", []):
            graph.edges.append(KnowledgeEdge(**edge_item))
        graph.chunk_concepts = {
            chunk_id: sorted(set(concepts))
            for chunk_id, concepts in raw.get("chunk_concepts", {}).items()
        }
        return graph

    def merge(self, other: "KnowledgeGraph") -> None:
        for node_id, node in other.nodes.items():
            if node_id not in self.nodes:
                self.nodes[node_id] = node
        existing_edge_ids = {edge.edge_id for edge in self.edges}
        for edge in other.edges:
            if edge.edge_id not in existing_edge_ids:
                self.edges.append(edge)
                existing_edge_ids.add(edge.edge_id)
        for chunk_id, concept_ids in other.chunk_concepts.items():
            merged = sorted(set(self.chunk_concepts.get(chunk_id, [])) | set(concept_ids))
            self.chunk_concepts[chunk_id] = merged

    def find_concepts(self, name_or_query: str, max_results: int = 8) -> list[str]:
        keyword = name_or_query.lower().strip()
        if not keyword:
            return []
        exact = [
            node.node_id
            for node in self.nodes.values()
            if node.node_type in {"Concept", "Entity", "Formula"}
            and node.name.lower() == keyword
        ]
        if exact:
            return sorted(set(exact))[:max_results]
        return self.resolve_concept_ids(name_or_query, max_results=max_results)


def build_knowledge_graph(chunks: list[Chunk]) -> KnowledgeGraph:
    graph = KnowledgeGraph()
    for chunk in chunks:
        schema = extract_chunk_schema(chunk.text)
        concept_ids: list[str] = []

        for concept in schema["concepts"]:
            concept_ids.append(graph.add_node("Concept", concept))
        for entity in schema["entities"]:
            concept_ids.append(graph.add_node("Entity", entity))
        for formula in schema["formulas"]:
            concept_ids.append(graph.add_node("Formula", formula, description=formula))

        for definition in schema["definitions"]:
            term = definition["term"]
            meaning = definition["definition"]
            term_id = graph.add_node("Concept", term)
            definition_id = graph.add_node("Definition", f"{term} definition", description=meaning)
            graph.add_edge(term_id, definition_id, "related-to", evidence_chunk_id=chunk.chunk_id)
            concept_ids.append(term_id)

        for relation in schema["relations"]:
            source_id = graph.add_node("Concept", relation["source"])
            target_id = graph.add_node("Concept", relation["target"])
            graph.add_edge(
                source_id,
                target_id,
                relation["type"],
                evidence_chunk_id=chunk.chunk_id,
            )
            concept_ids.extend([source_id, target_id])

        graph.map_chunk_concepts(chunk.chunk_id, concept_ids)
    return graph


def extract_chunk_schema(text: str) -> dict[str, list]:
    """Extract concept/entity/relation in a JSON-schema-like shape."""
    concepts, entities = _extract_terms(text)
    definitions = _extract_definitions(text)
    formulas = _extract_formulas(text)
    relations = _extract_relations(text, concepts=concepts, entities=entities)
    return {
        "concepts": concepts,
        "entities": entities,
        "definitions": definitions,
        "formulas": formulas,
        "relations": relations,
    }


def _extract_terms(text: str) -> tuple[list[str], list[str]]:
    counts: dict[str, int] = {}
    original_case: dict[str, str] = {}
    for token in TOKEN_PATTERN.findall(text):
        key = _normalize_key(token)
        if not key:
            continue
        if key in _STOPWORDS or key in _GENERIC_TERMS:
            continue
        if _is_low_signal_term(key):
            continue
        counts[key] = counts.get(key, 0) + 1
        original_case.setdefault(key, token)

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    concepts: list[str] = []
    entities: list[str] = []
    for key, _ in ranked[:12]:
        value = original_case[key]
        if _looks_like_entity(value):
            entities.append(value)
        else:
            concepts.append(value)
    return concepts[:8], entities[:6]


def _extract_definitions(text: str) -> list[dict[str, str]]:
    definitions: list[dict[str, str]] = []
    for pattern in _PATTERNS["is-a"]:
        for match in pattern.finditer(text):
            source = match.group("src").strip()
            target = match.group("dst").strip()
            if source.lower() in _STOPWORDS or target.lower() in _STOPWORDS:
                continue
            definitions.append({"term": source, "definition": target})
    return _dedupe_dicts(definitions)


def _extract_formulas(text: str) -> list[str]:
    formulas: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if "=" not in cleaned:
            continue
        if len(cleaned) > 120:
            continue
        if re.search(r"[A-Za-z\u4e00-\u9fff]", cleaned):
            formulas.append(cleaned)
    return sorted(set(formulas))[:8]


def _extract_relations(text: str, concepts: list[str], entities: list[str]) -> list[dict[str, str]]:
    relations: list[dict[str, str]] = []
    for edge_type in ("is-a", "used-in", "derived-from"):
        for pattern in _PATTERNS[edge_type]:
            for match in pattern.finditer(text):
                source = match.group("src").strip()
                target = match.group("dst").strip()
                source_key = _normalize_key(source)
                target_key = _normalize_key(target)
                if not source_key or not target_key:
                    continue
                if (
                    source_key in _STOPWORDS
                    or target_key in _STOPWORDS
                    or source_key in _GENERIC_TERMS
                    or target_key in _GENERIC_TERMS
                ):
                    continue
                relations.append({"source": source, "target": target, "type": edge_type})

    for pattern in _PATTERNS["related-to"]:
        for match in pattern.finditer(text):
            source = match.group("src").strip()
            target = match.group("dst").strip()
            source_key = _normalize_key(source)
            target_key = _normalize_key(target)
            if not source_key or not target_key:
                continue
            if (
                source_key in _STOPWORDS
                or target_key in _STOPWORDS
                or source_key in _GENERIC_TERMS
                or target_key in _GENERIC_TERMS
            ):
                continue
            relations.append({"source": source, "target": target, "type": "related-to"})

    return _dedupe_dicts(relations)


def _looks_like_entity(text: str) -> bool:
    if text.isupper():
        return True
    return bool(re.match(r"^[A-Z][A-Za-z0-9_-]{1,}$", text))


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix.lower()}-{digest}"


def _normalize_key(text: str) -> str:
    cleaned = text.strip().strip("“”\"'`.,;:()[]{}<>")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.replace("_", "-")
    cleaned = cleaned.lower()
    cleaned = cleaned.strip("-")
    if not cleaned:
        return ""
    if re.fullmatch(r"[0-9._-]+", cleaned):
        return ""
    if cleaned.endswith("s") and len(cleaned) > 3 and cleaned[-2].isalpha():
        cleaned = cleaned[:-1]
    return cleaned


def _is_low_signal_term(normalized: str) -> bool:
    if len(normalized) < 3 and re.fullmatch(r"[a-z0-9-]+", normalized):
        return True
    if "-" in normalized and len(normalized.replace("-", "")) < 3:
        return True
    if sum(ch.isalpha() for ch in normalized) == 0 and sum("\u4e00" <= ch <= "\u9fff" for ch in normalized) == 0:
        return True
    return False


def _dedupe_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_dicts(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for item in items:
        key = "|".join([item.get("source", ""), item.get("target", ""), item.get("type", ""), item.get("term", ""), item.get("definition", "")]).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
