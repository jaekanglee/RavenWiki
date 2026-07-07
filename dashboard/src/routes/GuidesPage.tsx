// v0.7.89+ — GuidesPage: Lite bootstrap 3종 read-only viewer (split view).
//
// thin wrapper: PageHeader + GuidesViewer. 본체 (split view, fetch, state)는
// GuidesViewer 컴포넌트에 있고, drawer (VaultManage 우측) 에서도 재사용.
//
// 진입:
//   - TOP nav에 두지 않음 (탭 9 → 8, surgical). VaultManage 행 액션 "📖 지침 보기"가
//     우측 drawer로 inline expand.
//   - /guides 직접 진입 가능 (?vault=X deep-link). 향후 자동화/외부 link용.
//   - 편집 ❌ — Lite bootstrap 3종은 Raven이 vault create 시 자동 주입 (AGENTS.md §4
//     Tier 2 표면) → 운영자는 "이 vault의 지침이 뭐지?"를 즉시 확인만 가능.

import { useEffect, useState } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import { fetchVaults, type VaultInfo } from "../lib/api";
import { GuidesViewer } from "../components/GuidesViewer";
import { PageHeader } from "../components/ui/PageHeader";

interface OutletCtx {
  vault: string;
  refresh: () => void;
}

export function GuidesPage() {
  const { vault: ctxVault } = useOutletContext<OutletCtx>();
  const [searchParams] = useSearchParams();
  // v0.7.89+: ?vault=X 쿼리로 진입 시 (VaultManage '지침 보기' 액션) 즉시 그 vault로 선택.
  const queryVault = searchParams.get("vault") || "";
  const [vaults, setVaults] = useState<VaultInfo[]>([]);

  useEffect(() => {
    fetchVaults()
      .then(setVaults)
      .catch(() => setVaults([]));
  }, []);

  const activeVault = queryVault || ctxVault;

  return (
    <div style={{ maxWidth: 1280 }}>
      <PageHeader
        title="지침"
        subtitle={`Lite bootstrap 3종 (read-only) — ${activeVault ? `in ${activeVault}` : ""}`}
      />
      <GuidesViewer
        vaults={vaults}
        activeVault={activeVault}
        vaultLocked={Boolean(queryVault)}
      />
    </div>
  );
}
