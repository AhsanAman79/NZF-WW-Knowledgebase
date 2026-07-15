import { useState } from "react";
import { search, type SearchResponse } from "../api";

interface Props {
  entities: string[];
  areas: string[];
  docTypes: string[];
}

export default function SearchView({ entities, areas, docTypes }: Props) {
  const [query, setQuery] = useState("");
  const [entity, setEntity] = useState("");
  const [area, setArea] = useState("");
  const [docType, setDocType] = useState("");
  const [busy, setBusy] = useState(false);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setData(await search(query.trim(), entity, area, docType));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Search the knowledgebase</h2>
      <p className="hint">
        Ask in natural language. Results are ranked by meaning, not just keywords, across
        all NZF entities. Optionally narrow down by entity, area or type.
      </p>

      <form onSubmit={onSubmit} className="form search-form">
        <input
          className="query"
          type="text"
          placeholder="e.g. How is zakat distributed to refugees?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="filters">
          <select value={entity} onChange={(e) => setEntity(e.target.value)}>
            <option value="">All entities</option>
            {entities.map((x) => (
              <option key={x} value={x}>{x}</option>
            ))}
          </select>
          <select value={area} onChange={(e) => setArea(e.target.value)}>
            <option value="">All areas</option>
            {areas.map((x) => (
              <option key={x} value={x}>{x}</option>
            ))}
          </select>
          <select value={docType} onChange={(e) => setDocType(e.target.value)}>
            <option value="">All types</option>
            {docTypes.map((x) => (
              <option key={x} value={x}>{x}</option>
            ))}
          </select>
          <button type="submit" disabled={busy || !query.trim()}>
            {busy ? "Searching…" : "Search"}
          </button>
        </div>
      </form>

      {error && <div className="banner error">{error}</div>}

      {data?.answer && (
        <div className="answer">
          <h3>Answer</h3>
          <p>{data.answer}</p>
        </div>
      )}

      {data && (
        <div className="results">
          <h3>
            {data.results.length} result{data.results.length === 1 ? "" : "s"}
          </h3>
          {data.results.length === 0 && (
            <p className="hint">No matches yet. Try different wording or upload more documents.</p>
          )}
          {data.results.map((r, i) => (
            <article className="result" key={`${r.document_id}-${i}`}>
              <div className="result-head">
                <span className="filename">{r.title || r.filename}</span>
                <span className="tags">
                  <span className="tag">{r.entity}</span>
                  <span className="tag">{r.area}</span>
                  {r.doc_type && <span className="tag">{r.doc_type}</span>}
                  <span className="score">{(r.score * 100).toFixed(0)}%</span>
                </span>
              </div>
              <p className="snippet">{r.snippet}</p>
              <div className="result-foot">
                {r.upload_date && (
                  <span className="date">{r.upload_date.slice(0, 10)}</span>
                )}
                {r.sharepoint_url && (
                  <a href={r.sharepoint_url} target="_blank" rel="noreferrer">
                    Open in SharePoint
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
