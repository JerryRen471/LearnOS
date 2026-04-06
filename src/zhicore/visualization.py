"""Knowledge graph visualization utilities for Phase 2."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from zhicore.kg import KnowledgeGraph, KnowledgeNode


def render_knowledge_graph_html(
    graph_path: str,
    output_path: str,
    concept: str | None = None,
    query: str | None = None,
    hops: int = 1,
    max_nodes: int = 180,
) -> dict[str, str | int]:
    """Render knowledge graph (or subgraph) into a self-contained HTML file."""
    if max_nodes <= 0:
        raise ValueError("max_nodes must be > 0")
    graph = KnowledgeGraph.load(graph_path)
    selected = _select_graph_payload(
        graph=graph,
        concept=concept,
        query=query,
        hops=hops,
        max_nodes=max_nodes,
    )
    elements = _to_cytoscape_elements(selected)
    html = _build_html(
        elements=elements,
        node_count=len(selected["nodes"]),
        edge_count=len(selected["edges"]),
        scope=f"subgraph({concept or query})" if (concept or query) else "global",
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return {
        "output_path": str(path),
        "nodes": len(selected["nodes"]),
        "edges": len(selected["edges"]),
    }


def _select_graph_payload(
    graph: KnowledgeGraph,
    concept: str | None,
    query: str | None,
    hops: int,
    max_nodes: int,
) -> dict[str, list[dict]]:
    if concept or query:
        seeds = graph.find_concepts(concept or query or "", max_results=16)
        return graph.subgraph(seed_node_ids=seeds, hops=hops, max_nodes=max_nodes)

    if len(graph.nodes) <= max_nodes:
        node_payload = [asdict(node) for node in sorted(graph.nodes.values(), key=lambda item: item.node_id)]
        selected_ids = {node["node_id"] for node in node_payload}
        edge_payload = [
            asdict(edge)
            for edge in sorted(graph.edges, key=lambda item: item.edge_id)
            if edge.source_id in selected_ids and edge.target_id in selected_ids
        ]
        return {"nodes": node_payload, "edges": edge_payload}

    ranked = _rank_nodes(graph.nodes, graph.edges)
    selected_ids = set(ranked[:max_nodes])
    node_payload = [asdict(graph.nodes[node_id]) for node_id in ranked[:max_nodes]]
    edge_payload = [
        asdict(edge)
        for edge in sorted(graph.edges, key=lambda item: item.edge_id)
        if edge.source_id in selected_ids and edge.target_id in selected_ids
    ]
    return {"nodes": node_payload, "edges": edge_payload}


def _rank_nodes(nodes: dict[str, KnowledgeNode], edges: list) -> list[str]:
    degrees: dict[str, int] = {node_id: 0 for node_id in nodes}
    for edge in edges:
        degrees[edge.source_id] = degrees.get(edge.source_id, 0) + 1
        degrees[edge.target_id] = degrees.get(edge.target_id, 0) + 1
    return sorted(
        nodes.keys(),
        key=lambda node_id: (-degrees.get(node_id, 0), nodes[node_id].name.lower(), node_id),
    )


def _to_cytoscape_elements(payload: dict[str, list[dict]]) -> list[dict]:
    elements: list[dict] = []
    for node in payload.get("nodes", []):
        elements.append(
            {
                "data": {
                    "id": node["node_id"],
                    "label": node["name"],
                    "node_type": node["node_type"],
                    "description": node.get("description", ""),
                }
            }
        )
    for edge in payload.get("edges", []):
        elements.append(
            {
                "data": {
                    "id": edge["edge_id"],
                    "source": edge["source_id"],
                    "target": edge["target_id"],
                    "label": edge["edge_type"],
                    "edge_type": edge["edge_type"],
                    "evidence_chunk_id": edge.get("evidence_chunk_id", ""),
                }
            }
        )
    return elements


def _build_html(elements: list[dict], node_count: int, edge_count: int, scope: str) -> str:
    elements_json = json.dumps(elements, ensure_ascii=False)
    metadata_json = json.dumps(
        {"nodes": node_count, "edges": edge_count, "scope": scope},
        ensure_ascii=False,
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ZhiCore Knowledge Graph</title>
  <style>
    body {{
      margin: 0;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0b0f16;
      color: #dbe7ff;
    }}
    .topbar {{
      height: 52px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px;
      border-bottom: 1px solid #243046;
      background: #111826;
    }}
    .title {{
      font-size: 15px;
      font-weight: 600;
      letter-spacing: .2px;
    }}
    .controls button {{
      margin-left: 8px;
      border: 1px solid #2e3d5c;
      background: #152033;
      color: #dbe7ff;
      border-radius: 8px;
      padding: 6px 10px;
      cursor: pointer;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 1fr 280px;
      height: calc(100vh - 52px);
    }}
    #cy {{
      width: 100%;
      height: 100%;
    }}
    .panel {{
      border-left: 1px solid #243046;
      background: #0f1522;
      padding: 12px;
      overflow: auto;
      font-size: 13px;
      line-height: 1.5;
    }}
    .section {{
      margin-bottom: 14px;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      color: #a6b6d8;
      word-break: break-all;
    }}
  </style>
  <script src="https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
</head>
<body>
  <div class="topbar">
    <div class="title">ZhiCore Knowledge Graph Visualization</div>
    <div class="controls">
      <button id="fit-btn">Fit</button>
      <button id="layout-btn">Relayout</button>
    </div>
  </div>
  <div class="layout">
    <div id="cy"></div>
    <aside class="panel">
      <div class="section">
        <strong>Summary</strong>
        <div id="summary" class="mono"></div>
      </div>
      <div class="section">
        <strong>Legend</strong>
        <div class="mono">
          Node: Concept(blue), Entity(green), Definition(orange), Formula(purple)<br/>
          Edge: related-to(gray), is-a(teal), derived-from(pink), used-in(yellow)
        </div>
      </div>
      <div class="section">
        <strong>Selection</strong>
        <div id="details" class="mono">Click node/edge to inspect details.</div>
      </div>
    </aside>
  </div>
  <script>
    const elements = {elements_json};
    const meta = {metadata_json};
    const nodeColors = {{
      "Concept": "#60a5fa",
      "Entity": "#34d399",
      "Definition": "#f59e0b",
      "Formula": "#a78bfa"
    }};
    const edgeColors = {{
      "related-to": "#a3a3a3",
      "is-a": "#2dd4bf",
      "derived-from": "#f472b6",
      "used-in": "#fde047"
    }};

    const cy = cytoscape({{
      container: document.getElementById("cy"),
      elements,
      style: [
        {{
          selector: "node",
          style: {{
            "label": "data(label)",
            "font-size": 10,
            "text-wrap": "wrap",
            "text-max-width": 110,
            "text-valign": "center",
            "text-halign": "center",
            "color": "#e6eefc",
            "background-color": ele => nodeColors[ele.data("node_type")] || "#94a3b8",
            "width": 20,
            "height": 20,
            "border-width": 1,
            "border-color": "#1f2937"
          }}
        }},
        {{
          selector: "edge",
          style: {{
            "curve-style": "bezier",
            "line-color": ele => edgeColors[ele.data("edge_type")] || "#64748b",
            "target-arrow-color": ele => edgeColors[ele.data("edge_type")] || "#64748b",
            "target-arrow-shape": "triangle",
            "width": 1.6,
            "opacity": 0.8
          }}
        }},
        {{
          selector: ":selected",
          style: {{
            "border-width": 3,
            "border-color": "#eab308",
            "line-color": "#facc15",
            "target-arrow-color": "#facc15"
          }}
        }}
      ],
      layout: {{
        name: "cose",
        animate: false,
        fit: true,
        padding: 20,
        nodeRepulsion: 450000,
        idealEdgeLength: 80
      }}
    }});

    document.getElementById("summary").textContent =
      `scope=${{meta.scope}} | nodes=${{meta.nodes}} | edges=${{meta.edges}}`;

    const details = document.getElementById("details");
    cy.on("tap", "node", evt => {{
      const n = evt.target.data();
      details.textContent =
        `Node\\nid=${{n.id}}\\nname=${{n.label}}\\ntype=${{n.node_type}}\\ndescription=${{n.description || ""}}`;
    }});
    cy.on("tap", "edge", evt => {{
      const e = evt.target.data();
      details.textContent =
        `Edge\\nid=${{e.id}}\\n${{e.source}} --${{e.edge_type}}--> ${{e.target}}\\nevidence_chunk=${{e.evidence_chunk_id}}`;
    }});

    document.getElementById("fit-btn").addEventListener("click", () => cy.fit(undefined, 30));
    document.getElementById("layout-btn").addEventListener("click", () => {{
      cy.layout({{
        name: "cose",
        animate: true,
        fit: true,
        padding: 20,
        nodeRepulsion: 450000,
        idealEdgeLength: 80
      }}).run();
    }});
  </script>
</body>
</html>
"""
