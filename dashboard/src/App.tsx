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

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/page/:vault/*" element={<PageView />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/log" element={<LogPage />} />
          <Route path="/lint" element={<LintPage />} />
          <Route path="/vault/new" element={<NewVaultPage />} />
          <Route path="/vault/manage" element={<VaultManage />} />
          <Route path="/digest" element={<DashboardDigest />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
