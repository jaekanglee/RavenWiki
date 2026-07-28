import { useEffect, useState } from "react";
import {
  getHosts,
  getActiveHostId,
  setActiveHostId,
  addHost,
  removeHost,
  testHostConnection,
  getActiveHost,
  type HostConnection,
} from "../lib/api";
import { TextField } from "./ui/TextField";
import { Button } from "./ui/Button";

export function HostPicker() {
  const [hosts, setHosts] = useState<HostConnection[]>([]);
  const [activeId, setActiveId] = useState<string>("local");
  const [modalOpen, setModalOpen] = useState(false);
  const [hostName, setHostName] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setHosts(getHosts());
    setActiveId(getActiveHostId());
  }, []);

  function handleSelectHost(id: string) {
    setActiveHostId(id);
    setActiveId(id);
    // Reload dashboard to apply active host endpoint across all stores
    window.location.href = "/";
  }

  function handleRemove(id: string) {
    if (confirm("이 호스트 연결을 삭제하시겠습니까?")) {
      removeHost(id);
      setHosts(getHosts());
      setActiveId(getActiveHostId());
      if (activeId === id) {
        window.location.href = "/";
      }
    }
  }

  async function handleTest() {
    if (!endpoint.trim()) {
      setTestResult({ ok: false, message: "IP 또는 URL 주소를 입력하세요." });
      return;
    }
    setTesting(true);
    setTestResult(null);
    const res = await testHostConnection(endpoint);
    setTesting(false);
    if (res.ok) {
      setTestResult({ ok: true, message: `✅ 연결 성공! (${res.vaultsCount}개 보관소 발견)` });
    } else {
      setTestResult({ ok: false, message: `❌ 연결 실패: ${res.error}` });
    }
  }

  function handleSave() {
    if (!endpoint.trim()) {
      setTestResult({ ok: false, message: "IP 또는 URL 주소를 입력하세요." });
      return;
    }
    setSubmitting(true);
    const newHost = addHost({
      name: hostName.trim() || endpoint.trim(),
      endpoint: endpoint.trim(),
      isLocal: false,
    });
    setHosts(getHosts());
    setSubmitting(false);
    setModalOpen(false);
    setHostName("");
    setEndpoint("");
    setTestResult(null);
    
    // Switch to newly added host
    handleSelectHost(newHost.id);
  }

  const currentHost = getActiveHost();

  return (
    <div className="sidebar-host-selector-container" style={{ marginTop: 12 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0 4px 6px",
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.32px",
            color: "var(--color-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          호스트 PC ({hosts.length})
        </span>
        <button
          type="button"
          onClick={() => setModalOpen(true)}
          style={{
            fontSize: 11,
            color: "var(--color-primary)",
            background: "none",
            border: "none",
            cursor: "pointer",
            fontWeight: 600,
          }}
          title="새 호스트 연결 추가"
        >
          + 추가
        </button>
      </div>

      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <select
          className="input-base"
          value={activeId}
          onChange={(e) => handleSelectHost(e.target.value)}
          aria-label="호스트 PC 선택"
          style={{ flex: 1, margin: 0 }}
        >
          {hosts.map((h) => (
            <option key={h.id} value={h.id}>
              {h.isLocal ? "💻 " : "🌐 "}
              {h.name} {!h.isLocal ? `(${h.endpoint})` : ""}
            </option>
          ))}
        </select>
        {!currentHost.isLocal && (
          <button
            type="button"
            onClick={() => handleRemove(currentHost.id)}
            className="sidebar-favorite-btn"
            title="현재 원격 호스트 삭제"
            style={{ color: "var(--color-danger-text)" }}
          >
            🗑
          </button>
        )}
      </div>

      {modalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.4)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16,
          }}
        >
          <div
            style={{
              background: "var(--color-canvas)",
              border: "1px solid var(--color-hairline)",
              borderRadius: "var(--radius-lg)",
              padding: 24,
              width: "100%",
              maxWidth: 440,
              boxShadow: "var(--shadow-overlay)",
            }}
          >
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>원격 Raven 호스트 추가</h2>
            <p style={{ fontSize: 13, color: "var(--color-muted)", marginBottom: 16 }}>
              다른 PC에서 실행 중인 Raven 백엔드(IP/Port)를 연결하여 해당 기기의 ~/Raven/ 보관소들을 열람합니다.
            </p>

            <TextField
              label="호스트 이름"
              placeholder="예: 집 데스크톱, 회사 NAS"
              value={hostName}
              onChange={(e) => setHostName(e.target.value)}
            />

            <TextField
              label="IP 주소 또는 URL"
              required
              placeholder="예: 192.168.0.15:8765 또는 http://100.x.y.z:8765"
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              style={{ marginTop: 12 }}
            />

            {testResult && (
              <div
                style={{
                  marginTop: 12,
                  fontSize: 13,
                  color: testResult.ok ? "var(--color-primary)" : "var(--color-danger-text)",
                }}
              >
                {testResult.message}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
              <Button variant="pill" onClick={handleTest} disabled={testing}>
                {testing ? "테스트 중..." : "연결 테스트"}
              </Button>
              <div style={{ display: "flex", gap: 8 }}>
                <Button variant="pill" onClick={() => setModalOpen(false)}>
                  취소
                </Button>
                <Button variant="pillPrimary" onClick={handleSave} disabled={submitting}>
                  추가 및 전환
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
