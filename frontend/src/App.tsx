import { useEffect, useState } from "react";
import { getAreas, getEntities } from "./api";
import UploadView from "./views/UploadView";
import SearchView from "./views/SearchView";

type View = "search" | "upload";

export default function App() {
  const [view, setView] = useState<View>("search");
  const [entities, setEntities] = useState<string[]>([]);
  const [areas, setAreas] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getEntities(), getAreas()])
      .then(([e, a]) => {
        setEntities(e);
        setAreas(a);
      })
      .catch((err) => setLoadError(err.message));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="logo">NZF</span>
          <div>
            <h1>Worldwide Knowledgebase</h1>
            <p className="subtitle">Central document search across all NZF entities</p>
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
        </nav>
      </header>

      <main className="main">
        {loadError && (
          <div className="banner error">
            Could not reach the backend: {loadError}. Is the API running on port 8000?
          </div>
        )}
        {view === "search" ? (
          <SearchView entities={entities} areas={areas} />
        ) : (
          <UploadView entities={entities} areas={areas} />
        )}
      </main>

      <footer className="footer">
        NZF Worldwide · Internal knowledgebase · Handle documents according to data-protection policy.
      </footer>
    </div>
  );
}
