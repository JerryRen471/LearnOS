from pathlib import Path

from zhicore.phase2 import build_or_update_kg
from zhicore.visualization import render_knowledge_graph_html


def test_render_knowledge_graph_html(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "FastAPI is framework.\nRAG used in LearnOS.\nKnowledge Graph derived from chunk.\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "graph.json"
    index_path = tmp_path / "index.json"
    output_path = tmp_path / "graph_visualization.html"

    build_or_update_kg(
        inputs=[str(source)],
        graph_path=str(graph_path),
        index_path=str(index_path),
        incremental=False,
    )
    result = render_knowledge_graph_html(
        graph_path=str(graph_path),
        output_path=str(output_path),
        concept="FastAPI",
        hops=1,
        max_nodes=60,
    )

    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "cytoscape.min.js" in html
    assert "ZhiCore Knowledge Graph Visualization" in html
    assert "FastAPI" in html
    assert int(result["nodes"]) > 0
