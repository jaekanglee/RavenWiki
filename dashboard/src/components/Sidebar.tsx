import { useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { NewPageButton } from "./NewPageButton";
import type { TreeNode as TNode, VaultMeta } from "../types";

interface SidebarProps {
  vaults: VaultMeta[];
  trees: Record<string, TNode | null>;
  activeVault: string;
  onSelectVault: (name: string) => void;
  onRefresh?: () => void;
  /** Reserved for future tree-mutation refresh hooks; not used in the
   *  off-canvas-drawer flow. */
  onTreeChange?: () => void;
  /** Controlled drawer state owned by Layout. On desktop the off-canvas
   *  CSS only takes effect inside @media (max-width: 744px), so this is
   *  effectively a no-op above the breakpoint. */
  open: boolean;
  /** Called by the leaf Link onClick and (in Layout) by backdrop/Escape. */
  onClose: () => void;
}

/**
 * contentRoot (v0.6.15 sidebar cleanup)
 * ─────────────────────────────────────────────────
 * 모든 vault에 공통으로 있는 `content/` 같은 single-child 디렉토리는
 * 사용자에게 노이즈다. TreeNode에서 이걸 자동 감지해서 그 자식들만 노출한다.
 *
 * 예: vault tree = {content/ → [concept/, decision/]}
 *     → sidebar에 "content/" 자체를 숨기고 concept/, decision/가 root로 표시
 *
 * v1 heuristic: root.children 중 단일 child만 있고, 그 child의 slug가
 * `content` (case-insensitive)이면 그 child의 children을 root로 올림.
 * 다른 디렉토리(`notes/`, `wiki/`)는 vault에 따라 다르므로 압축 안 함.
 */
function flattenCommonRoot(tree: TNode | null): TNode | null {
  if (!tree || !tree.children || tree.children.length === 0) return tree;
  const SINGLE_CHILD_NAMES = new Set(["content"]);
  if (
    tree.children.length === 1 &&
    SINGLE_CHILD_NAMES.has(tree.children[0].slug.toLowerCase())
  ) {
    const inner = tree.children[0];
    return { ...inner, children: inner.children ?? [] };
  }
  return tree;
}

export function Sidebar({
  vaults,
  trees,
  activeVault,
  onSelectVault,
  onRefresh,
  open,
  onClose,
}: SidebarProps) {
  return (
    <aside
      id="primary-sidebar"
      className={clsx(
        "layout-sidebar",
        "sidebar-offcanvas",
        open && "sidebar-offcanvas-open"
      )}
      style={{
        borderRight: "1px solid var(--color-hairline)",
        width: 288,
        overflowY: "auto",
        padding: "24px 20px",
        background: "var(--color-canvas)",
        flexShrink: 0,
      }}
    >
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ flex: 1 }}>
          <NewPageButton />
        </div>
      </div>

      {/*
        "Vaults (N)" label: 1개일 땐 의미 없어서 숨김. 2개+일 때만 카운트 표시.
        각 vault는 자체 row에서 vault name + mode badge로 충분히 식별 가능.
      */}
      {vaults.length > 1 && (
        <div
          className="sidebar-label"
          style={{
            padding: "8px 0 4px",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.32px",
            textTransform: "uppercase",
            color: "var(--color-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          Vaults ({vaults.length})
        </div>
      )}

      {vaults.length === 0 && (
        <div
          style={{
            padding: 8,
            fontSize: 13,
            color: "var(--color-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          vault 없음
        </div>
      )}

      {vaults.map((v) => (
        <VaultTreeGroup
          key={v.name}
          vault={v}
          tree={flattenCommonRoot(trees[v.name] ?? null)}
          isActive={v.name === activeVault}
          onSelect={() => onSelectVault(v.name)}
          onClose={onClose}
          onRefresh={onRefresh}
        />
      ))}
    </aside>
  );
}

// ─── display title helper ────────────────────────────────────
// Vault filenames are slugs — turn "2026-06-28-pwa-cache" into "Pwa Cache",
// "index" into "Index", keep "_template" as-is. Strips leading
// date prefix and replaces separators with spaces.
function displayTitle(slug: string): string {
  const last = slug.split("/").pop() || slug;
  const base = last.replace(/\.md$/, "");
  // strip leading YYYY-MM-DD- prefix
  const dated = base.replace(/^\d{4}-\d{2}-\d{2}-/, "");
  if (dated === "") return base;
  return dated
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Vault tree group ────────────────────────────────────────
function VaultTreeGroup({
  vault,
  tree,
  isActive,
  onSelect,
  onClose,
  onRefresh,
}: {
  vault: VaultMeta;
  tree: TNode | null;
  isActive: boolean;
  onSelect: () => void;
  onClose: () => void;
  onRefresh?: () => void;
}) {
  // 기본 닫힘 (v0.6.10 UX 강화).
  const [open, setOpen] = useState(false);

  // 묶음 A (Plan v1, Tasks 2-3): title 영역 클릭 = toggle, arrow 클릭 = toggle.
  // 둘 다 동일한 toggle 동작. 단, vault 선택(setActive)은 별도 액션.
  // 모바일(<744px) 터치 영역 32px 유지를 위해 min-height 적용.
  const toggleVault = () => setOpen(!open);

  return (
    <div
      style={{
        marginBottom: 2,
        background: isActive ? "var(--cds-field-01, #f4f4f4)" : "transparent",
        borderRadius: 4,
        padding: "2px 0",
      }}
    >
      <button
        onClick={onSelect}
        className="sidebar-vault-row"
        aria-label={`switch to vault ${vault.name}`}
        title={`${vault.path}`}
      >
        {/* arrow: 16px 컨테이너 + 12px chevron + 90° rotation transition. */}
        <span
          role="button"
          tabIndex={-1}
          onClick={(e) => {
            e.stopPropagation();
            toggleVault();
          }}
          aria-hidden
          className={clsx("sidebar-chevron", open && "sidebar-chevron-open")}
        >
          <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden>
            <path
              d="M4 2 L8 6 L4 10"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        {vault.default && (
          <span className="sidebar-vault-default" aria-label="default">
            ★
          </span>
        )}
        {isActive && (
          <span className="sidebar-vault-active" aria-label="active">
            ●
          </span>
        )}
        <span className="sidebar-vault-name">{vault.name}</span>
        <span className="sidebar-vault-mode">{vault.mode}</span>
      </button>

      {open && (
        <div style={{ paddingLeft: 8, paddingTop: 2 }}>
          {tree ? (
            tree.children?.length ? (
              tree.children.map((child) => (
                <TreeLeaf
                  key={child.slug}
                  node={child}
                  vault={vault.name}
                  onClose={onClose}
                />
              ))
            ) : (
              <div
                style={{
                  padding: "4px 8px",
                  fontSize: 12,
                  color: "var(--color-muted)",
                }}
              >
                empty
              </div>
            )
          ) : (
            <div
              style={{
                padding: "4px 8px",
                fontSize: 12,
                color: "var(--color-muted)",
              }}
            >
              loading…
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Tree leaf (recursive for nested dirs) ───────────────────
function TreeLeaf({
  node,
  vault,
  onClose,
  depth = 0,
}: {
  node: TNode;
  vault: string;
  onClose: () => void;
  depth?: number;
}) {
  const [isOpen, setIsOpen] = useState(false);

  if (!node.children || node.children.length === 0) {
    // leaf page
    return (
      <Link
        to={`/page/${vault}/${node.slug}`}
        onClick={onClose}
        className="link-ink sidebar-tree-leaf"
        style={{ marginLeft: depth * 14 }}
      >
        {displayTitle(node.title || node.slug)}
      </Link>
    );
  }

  // dir node — chevron + transition + IBM Plex Sans.
  return (
    <div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="link-ink sidebar-tree-dir"
        style={{ marginLeft: depth * 14 }}
      >
        <span
          aria-hidden
          className={clsx("sidebar-chevron sidebar-chevron-sm", isOpen && "sidebar-chevron-open")}
        >
          <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden>
            <path
              d="M4 2 L8 6 L4 10"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        {displayTitle(node.title || node.slug)}
      </button>
      {isOpen &&
        node.children.map((c) => (
          <TreeLeaf
            key={c.slug}
            node={c}
            vault={vault}
            onClose={onClose}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}