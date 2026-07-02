"use client";

import { useEffect, useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  Edge,
  MarkerType,
  MiniMap,
  Node,
  Position,
  ReactFlow,
  useNodesState
} from "@xyflow/react";

export type MindMapTree = {
  title: string;
  detail: string;
  children: MindMapTree[];
};

type MindMapNodeData = {
  label: string;
  detail: string;
  depth: number;
};

const NODE_WIDTH = 190;
const NODE_HEIGHT = 72;

function buildGraph(tree: MindMapTree): {
  nodes: Node<MindMapNodeData>[];
  edges: Edge[];
} {
  const nodes: Node<MindMapNodeData>[] = [];
  const edges: Edge[] = [];

  function visit(node: MindMapTree, parentId: string | null, depth: number, path: number[]) {
    const id = path.join("-");
    nodes.push({
      id,
      position: { x: 0, y: 0 },
      data: { label: node.title, detail: node.detail, depth },
      className: `mind-map-node depth-${Math.min(depth, 3)}`,
      sourcePosition: Position.Right,
      targetPosition: Position.Left
    });

    if (parentId) {
      edges.push({
        id: `${parentId}-${id}`,
        source: parentId,
        target: id,
        markerEnd: { type: MarkerType.ArrowClosed },
        type: "smoothstep"
      });
    }

    node.children.forEach((child, index) => {
      visit(child, id, depth + 1, [...path, index]);
    });
  }

  visit(tree, null, 0, [0]);

  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 28, ranksep: 80, marginx: 24, marginy: 24 });

  nodes.forEach((node) => {
    graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);

  nodes.forEach((node) => {
    const position = graph.node(node.id);
    node.position = {
      x: position.x - NODE_WIDTH / 2,
      y: position.y - NODE_HEIGHT / 2
    };
  });

  return { nodes, edges };
}

export default function MindMapView({ tree }: { tree: MindMapTree }) {
  const graph = useMemo(() => buildGraph(tree), [tree]);
  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes);
  const [selectedNode, setSelectedNode] = useState<Node<MindMapNodeData> | null>(
    graph.nodes[0] ?? null
  );

  useEffect(() => {
    setNodes(graph.nodes);
    setSelectedNode(graph.nodes[0] ?? null);
  }, [graph, setNodes]);

  return (
    <div className="mind-map-view">
      <div className="mind-map-canvas">
        <ReactFlow
          edges={graph.edges}
          fitView
          fitViewOptions={{ padding: 0.18 }}
          minZoom={0.25}
          nodes={nodes}
          nodesDraggable
          nodesFocusable
          onNodeClick={(_, node) => setSelectedNode(node)}
          onNodesChange={onNodesChange}
        >
          <Background color="#d8dee8" gap={20} size={1} />
          <MiniMap pannable zoomable />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      {selectedNode ? (
        <div className="mind-map-detail">
          <strong>{String(selectedNode.data.label)}</strong>
          <p>{String(selectedNode.data.detail || "No additional detail.")}</p>
        </div>
      ) : null}
    </div>
  );
}
