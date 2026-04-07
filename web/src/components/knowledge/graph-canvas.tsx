"use client";

import { useEffect, useRef } from "react";

import type { SubgraphData } from "@/types/api";

type Props = {
  data: SubgraphData;
  onSelectNode: (nodeId: string, name: string) => void;
};

function nodeId(n: SubgraphData["nodes"][number]): string {
  return (n.node_id as string | undefined) ?? (n.id as string) ?? "";
}

function nodeLabel(n: SubgraphData["nodes"][number]): string {
  return (n.name as string | undefined) ?? (n.label as string | undefined) ?? nodeId(n);
}

export function GraphCanvas({ data, onSelectNode }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<{ destroy: () => void } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) {
      return;
    }

    let cancelled = false;

    void import("cytoscape").then((mod) => {
      if (cancelled || !containerRef.current) {
        return;
      }
      const Cy = mod.default;
      cyRef.current?.destroy();

      const elements: Array<{ data: Record<string, string> }> = [];

      for (const n of data.nodes) {
        const id = nodeId(n);
        if (!id) {
          continue;
        }
        elements.push({
          data: { id, label: nodeLabel(n) },
        });
      }

      for (let i = 0; i < data.edges.length; i += 1) {
        const e = data.edges[i];
        const src = (e.source_id as string | undefined) ?? (e.source as string | undefined);
        const tgt = (e.target_id as string | undefined) ?? (e.target as string | undefined);
        if (!src || !tgt) {
          continue;
        }
        elements.push({
          data: {
            id: `e-${i}-${src}-${tgt}`,
            source: src,
            target: tgt,
          },
        });
      }

      const cy = Cy({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              label: "data(label)",
              "font-size": "10px",
              "text-wrap": "wrap",
              "text-max-width": "80px",
              width: 28,
              height: 28,
              "background-color": "#3b82f6",
              color: "#0f172a",
            },
          },
          {
            selector: "node:selected",
            style: {
              "background-color": "#f59e0b",
              "border-width": 2,
              "border-color": "#b45309",
            },
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "#94a3b8",
              "target-arrow-color": "#94a3b8",
              "target-arrow-shape": "triangle",
              "curve-style": "bezier",
            },
          },
        ],
        layout: { name: "cose", animate: false, randomize: true },
        minZoom: 0.2,
        maxZoom: 3,
        wheelSensitivity: 0.35,
      });

      cy.on("tap", "node", (evt) => {
        const id = evt.target.id();
        const label = String(evt.target.data("label") ?? id);
        onSelectNode(id, label);
      });

      cyRef.current = cy;
    });

    return () => {
      cancelled = true;
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, [data, onSelectNode]);

  return <div ref={containerRef} className="graph-canvas" role="application" aria-label="Knowledge graph" />;
}
