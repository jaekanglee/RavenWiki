export interface Page {
  slug: string;
  title: string;
  type: string;
  path: string;
  filePath?: string;
  created: string;
  updated: string;
  tags: string;
  content: string;
  backlinks?: { source_slug: string; source_title: string }[];
}

// v0.6.16+: 폴더는 1차 시민. OS 파일시스템을 SOT로 한다.
// type: "dir" = OS 디렉토리, type: "page" = .md 파일.
// 빈 폴더도 children: []으로 그대로 표현.
export interface TreeNode {
  type: "dir" | "page";
  /** vault-relative 경로. dir은 'content/concept', page는 slug. */
  path: string;
  /** page only — `/page/<vault>/<slug>` URL. */
  slug?: string;
  /** page only — frontmatter title. */
  title?: string;
  /** page only — frontmatter type (8종). */
  pageType?: string;
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
