"use client";

import { useEffect, useRef } from "react";
import * as d3 from "d3";
import { CompanyGraph, GraphEdge, GraphNode } from "@/lib/api";

interface GraphViewProps {
  graph: CompanyGraph;
  centerSymbol: string;
  onSelect: (symbol: string) => void;
  insights?: string | null;
  insightsLoading?: boolean;
}

type SimNode = GraphNode & d3.SimulationNodeDatum;
type SimEdge = d3.SimulationLinkDatum<SimNode> & { type: string };

const EDGE_STYLE: Record<string, { color: string; dash: string }> = {
  SUBSIDIARY_OF: { color: "#71717a", dash: "" },
  HAS_CONTRACT: { color: "#d97706", dash: "4,3" },
  SUPPLIES_TO: { color: "#10b981", dash: "" },
  COMPETES_WITH: { color: "#f43f5e", dash: "4,3" },
  PARTNERS_WITH: { color: "#8b5cf6", dash: "" },
};

const EDGE_LABELS: Record<string, string> = {
  SUBSIDIARY_OF: "Subsidiary",
  HAS_CONTRACT: "Gov't contract",
  SUPPLIES_TO: "Supplies to",
  COMPETES_WITH: "Competes with",
  PARTNERS_WITH: "Partners with",
};

export default function GraphView({ graph, centerSymbol, onSelect, insights, insightsLoading }: GraphViewProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!svgRef.current || !containerRef.current) return;
    if (graph.nodes.length === 0) return;

    const width = containerRef.current.clientWidth || 600;
    const nodeCount = graph.nodes.length;
    const height = Math.min(640, Math.max(360, nodeCount * 22));

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    const nodes: SimNode[] = graph.nodes.map((n) => ({ ...n }));
    const edges: SimEdge[] = graph.edges.map((e) => ({ source: e.source, target: e.target, type: e.type }));

    const linkDistance = Math.min(160, 70 + nodeCount * 3);

    const simulation = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimEdge>(edges)
          .id((d) => d.id)
          .distance(linkDistance)
      )
      .force("charge", d3.forceManyBody().strength(-320))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(38))
      .force("x", d3.forceX(width / 2).strength(0.05))
      .force("y", d3.forceY(height / 2).strength(0.05));

    const link = svg
      .append("g")
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", (d) => EDGE_STYLE[d.type]?.color ?? "#a1a1aa")
      .attr("stroke-dasharray", (d) => EDGE_STYLE[d.type]?.dash ?? "")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.7);

    link.append("title").text((d) => EDGE_LABELS[d.type] ?? d.type);

    const drag = d3
      .drag<SVGGElement, SimNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    const nodeGroup = svg
      .append("g")
      .selectAll<SVGGElement, SimNode>("g")
      .data(nodes)
      .join("g")
      .style("cursor", (d) => (d.symbol ? "pointer" : "default"))
      .call(drag)
      .on("click", (_event, d) => {
        if (d.symbol) onSelect(d.symbol);
      });

    nodeGroup.each(function (d) {
      const g = d3.select(this);
      const isCenter = d.id === centerSymbol;
      const isClickable = Boolean(d.symbol) && !isCenter;
      const color = d.type === "GovEntity" ? "#d97706" : isCenter ? "#0891b2" : isClickable ? "#38bdf8" : "#a1a1aa";
      const radius = isCenter ? 15 : 9;

      if (d.type === "GovEntity") {
        g.append("rect")
          .attr("x", -radius)
          .attr("y", -radius)
          .attr("width", radius * 2)
          .attr("height", radius * 2)
          .attr("rx", 3)
          .attr("fill", color)
          .attr("fill-opacity", 0.85)
          .attr("stroke", "#ffffff")
          .attr("stroke-width", 1.5);
      } else {
        g.append("circle")
          .attr("r", radius)
          .attr("fill", color)
          .attr("fill-opacity", 0.9)
          .attr("stroke", "#ffffff")
          .attr("stroke-width", isCenter ? 2 : 1.5);
      }

      g.append("title").text(`${d.label} (${d.type})`);
    });

    const label = svg
      .append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d) => (d.label.length > 22 ? d.label.slice(0, 20) + "…" : d.label))
      .attr("font-size", 9)
      .attr("fill", "currentColor")
      .attr("dx", 12)
      .attr("dy", 3);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as SimNode).x ?? 0)
        .attr("y1", (d) => (d.source as SimNode).y ?? 0)
        .attr("x2", (d) => (d.target as SimNode).x ?? 0)
        .attr("y2", (d) => (d.target as SimNode).y ?? 0);

      nodeGroup.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
      label.attr("x", (d) => d.x ?? 0).attr("y", (d) => d.y ?? 0);
    });

    return () => {
      simulation.stop();
    };
  }, [graph, centerSymbol, onSelect]);

  const usedEdgeTypes = Array.from(new Set(graph.edges.map((e) => e.type)));
  const hasGovEntity = graph.nodes.some((n) => n.type === "GovEntity");
  const hasClickableCompany = graph.nodes.some((n) => n.type === "Company" && n.id !== centerSymbol && n.symbol);
  const hasNonClickableCompany = graph.nodes.some((n) => n.type === "Company" && n.id !== centerSymbol && !n.symbol);

  if (graph.nodes.length <= 1) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/60">
        No graph connections found yet for this company.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <h3 className="mb-1 text-sm font-medium text-zinc-500 dark:text-zinc-400">Company Graph</h3>
      <p className="mb-3 text-xs text-zinc-400 dark:text-zinc-600">
        Subsidiaries pulled from SEC filings, federal contracts from USASpending.gov, and
        related companies inferred from recent news. The Ask box above is also grounded in
        this graph, so you can ask about it directly.
      </p>

      {(insightsLoading || insights) && (
        <div className="mb-4 rounded-md border border-violet-200 bg-violet-50 px-3 py-2.5 text-xs dark:border-violet-900/60 dark:bg-violet-950/20">
          <div className="mb-1 flex items-center gap-1.5 font-medium text-violet-700 dark:text-violet-400">
            <span aria-hidden>✦</span> Graph Insights
            {insightsLoading && (
              <span className="flex items-center gap-1 font-normal text-violet-500">
                <span className="h-1 w-1 animate-pulse rounded-full bg-violet-500" />
                analyzing…
              </span>
            )}
          </div>
          {insightsLoading && !insights && (
            <div className="h-3 w-4/5 animate-pulse rounded bg-violet-200/60 dark:bg-violet-900/40" />
          )}
          {insights && <p className="text-zinc-700 dark:text-zinc-300">{insights}</p>}
        </div>
      )}

      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-2 rounded-md bg-zinc-50 px-3 py-2 text-xs dark:bg-zinc-950/40">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="font-medium text-zinc-500 dark:text-zinc-500">Nodes:</span>
          <span className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-400">
            <span className="inline-block h-3 w-3 rounded-full border border-white" style={{ backgroundColor: "#0891b2" }} />
            {centerSymbol} (this company)
          </span>
          {hasClickableCompany && (
            <span className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-400">
              <span className="inline-block h-2.5 w-2.5 rounded-full border border-white" style={{ backgroundColor: "#38bdf8" }} />
              Related company (click to explore)
            </span>
          )}
          {hasNonClickableCompany && (
            <span className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-400">
              <span className="inline-block h-2.5 w-2.5 rounded-full border border-white" style={{ backgroundColor: "#a1a1aa" }} />
              Subsidiary (no public ticker)
            </span>
          )}
          {hasGovEntity && (
            <span className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-400">
              <span className="inline-block h-2.5 w-2.5 rounded-sm border border-white" style={{ backgroundColor: "#d97706" }} />
              Government agency
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="font-medium text-zinc-500 dark:text-zinc-500">Relationships:</span>
          {usedEdgeTypes.map((type) => (
            <span key={type} className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-400">
              <span
                className="inline-block h-0.5 w-4"
                style={{
                  backgroundColor: EDGE_STYLE[type]?.color ?? "#a1a1aa",
                  opacity: 0.9,
                  backgroundImage: EDGE_STYLE[type]?.dash
                    ? `repeating-linear-gradient(to right, ${EDGE_STYLE[type]?.color} 0 3px, transparent 3px 6px)`
                    : undefined,
                }}
              />
              {EDGE_LABELS[type] ?? type}
            </span>
          ))}
        </div>
      </div>

      <div ref={containerRef} className="w-full text-zinc-600 dark:text-zinc-400">
        <svg ref={svgRef} className="w-full" style={{ height: 420 }} />
      </div>
      <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-600">
        Drag nodes to rearrange · click a blue node to explore that company · hover any node or line for detail
      </p>
    </div>
  );
}
