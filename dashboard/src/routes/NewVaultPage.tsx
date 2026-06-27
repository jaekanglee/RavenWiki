import { NewVaultWizard } from "../components/NewVaultWizard";

export function NewVaultPage() {
  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      <h1 style={{ marginBottom: 8 }}>새 vault 만들기</h1>
      <p className="text-muted" style={{ fontSize: 14, marginBottom: 24 }}>
        vault 이름과 경로, 모드, 템플릿을 선택하세요.
      </p>
      <NewVaultWizard />
    </div>
  );
}
