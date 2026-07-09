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
  workspace_path?: string;
}

// v0.7.67 (평가 B#9): 백엔드 실응답(server.py get_graph)과 필드를 맞춤.
// 이전엔 `slug`/`source_slug`/`target_slug`가 필수로 선언돼 있었으나 실제
// 응답은 `id`/`source`/`target`이라 소비처 전역에 `(n as any).id ?? n.slug`
// 캐스트가 산재했다 (types.ts가 실제와 반대로 거짓말을 하던 상태).
export interface GraphNode {
  id: string;
  slug?: string;
  /** Present in all-vault graph scope; omitted for legacy/current-vault payloads. */
  vault?: string;
  title: string;
  type?: string;
  weight?: number;
  x?: number;
  y?: number;
  /** v0.6.15+ — Louvain-style community id (0..K-1) when ?community=modularity. */
  community?: number;
  folder_group?: string;
  folder_label?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  intent?: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
