import { useEffect, useState } from "react";
import { getAreas, getDocTypes, getEntities } from "./api";
import UploadView from "./views/UploadView";
import SearchView from "./views/SearchView";
import ImportView from "./views/ImportView";
import logo from "./assets/zd-logo-red.png";

type View = "search" | "upload" | "import";

export default function App() {
  const [view, setView] = useState<View>("search");
  const [entities, setEntities] = useState<string[]>([]);
  const [areas, setAreas] = useState<string[]>([]);
  const [docTypes, setDocTypes] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getEntities(), getAreas(), getDocTypes()])
      .then(([e, a, d]) => {
        setEntities(e);
        setAreas(a);
        setDocTypes(d);
      })
      .catch((err) => setLoadError(err.message));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <img src={logo} alt="Zakat Deutschland" className="logo" />
          <div className="brand-text">
            <h1>Worldwide Knowledgebase</h1>
          </div>
        </div>
        <nav className="nav">
          <button
            className={view === "search" ? "active" : ""}
            onClick={() => setView("search")}
          >
            Search
          </button>
          <button
            className={view === "upload" ? "active" : ""}
            onClick={() => setView("upload")}
          >
            Upload
          </button>
          <button
            className={view === "import" ? "active" : ""}
            onClick={() => setView("import")}
          >
            Import
          </button>
        </nav>
      </header>

      <main className="main">
        {loadError && (
          <div className="banner error">
            Could not reach the backend: {loadError}
          </div>
        )}
        {view === "search" && <SearchView entities={entities} areas={areas} docTypes={docTypes} />}
        {view === "upload" && <UploadView entities={entities} areas={areas} docTypes={docTypes} />}
        {view === "import" && <ImportView entities={entities} areas={areas} docTypes={docTypes} />}
      </main>

      <footer className="footer">
        NZF Worldwide · Internal knowledgebase · Handle documents according to the
        data-protection policy.
      </footer>
    </div>
  );
}
