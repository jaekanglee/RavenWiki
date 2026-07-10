import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { HomePage } from "./routes/HomePage";
import { PageView } from "./routes/PageView";
import { SearchPage } from "./routes/SearchPage";
import { GraphPage } from "./routes/GraphPage";
import { LogPage } from "./routes/LogPage";
import { LintPage } from "./routes/LintPage";
import { NewVaultPage } from "./routes/NewVaultPage";
import { DashboardDigest } from "./routes/DashboardDigest";
import { VaultManage } from "./routes/VaultManage";
import { GardenPage } from "./routes/GardenPage";
import { RawPanel } from "./routes/RawPanel";
import { WorkspacePage } from "./routes/WorkspacePage";
import { GuidesPage } from "./routes/GuidesPage";
import { DraftPage } from "./routes/DraftPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/page/:vault/*" element={<PageView />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/draft" element={<DraftPage />} />
          <Route path="/log" element={<LogPage />} />
          <Route path="/lint" element={<LintPage />} />
          <Route path="/garden" element={<GardenPage />} />
          <Route path="/workspace" element={<WorkspacePage />} />
          <Route path="/vault/new" element={<NewVaultPage />} />
          <Route path="/vault/manage" element={<VaultManage />} />
          <Route path="/digest" element={<DashboardDigest />} />
          {/* v0.7.89+: Lite bootstrap 3종 read-only viewer (split view). */}
          <Route path="/guides" element={<GuidesPage />} />
          {/* v0.7.50+: raw/ folder panel */}
          <Route path="/raw/:vault/*" element={<RawPanel />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
