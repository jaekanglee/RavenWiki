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
  title: string;
  type: string;
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
