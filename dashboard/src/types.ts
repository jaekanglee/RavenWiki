export interface Page {
  slug: string;
  title: string;
  type: string;
  path: string;
  created: string;
  updated: string;
  tags: string;
  content: string;
  backlinks?: { source_slug: string; source_title: string }[];
}

export interface TreeNode {
  slug: string;
  title: string;
  type: string;
  children?: TreeNode[];
}

export interface VaultMeta {
  name: string;
  path: string;
  mode: string;
  owner: string;
  default: boolean;
}

export interface GraphNode {
  slug: string;
  id?: string;
  title: string;
  type?: string;
  weight?: number;
  x?: number;
  y?: number;
  /** v0.6.15+ — Louvain-style community id (0..K-1) when ?community=modularity. */
  community?: number;
}

export interface GraphEdge {
  source_slug: string;
  target_slug: string;
  intent?: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
