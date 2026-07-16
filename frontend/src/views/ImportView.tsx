import { useState } from "react";
import { importLink, type ImportResult } from "../api";

interface Props {
  entities: string[];
  areas: string[];
  docTypes: string[];
}

export default function ImportView({ entities, areas, docTypes }: Props) {
  const [url, setUrl] = useState("");
  const [entity, setEntity] = useState("");
  const [area, setArea] = useState("");
  const [docType, setDocType] = useState("Other");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      setResult(await importLink(url.trim(), entity, area, docType));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Import from a SharePoint link</h2>
      <p className="hint">
        Paste a SharePoint/OneDrive link to a file or folder. The tool fetches everything
        under it <strong>using your own Microsoft permissions</strong> and indexes it for
        search (the originals stay where they are). Large folders can take a while.
      </p>

      <form onSubmit={onSubmit} className="form">
        <label>
          <span className="label-text">SharePoint link</span>
          <input
            type="text"
            placeholder="https://…sharepoint.com/…"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </label>

        <div className="grid-2">
          <label>
            <span className="label-text">Entity</span>
            <select value={entity} onChange={(e) => setEntity(e.target.value)}>
              <option value="">Select entity…</option>
              {entities.map((x) => (
                <option key={x} value={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            <span className="label-text">Area</span>
            <select value={area} onChange={(e) => setArea(e.target.value)}>
              <option value="">Select area…</option>
              {areas.map((x) => (
                <option key={x} value={x}>{x}</option>
              ))}
            </select>
          </label>
        </div>

        <details className="optional">
          <summary>Optional details</summary>
          <div className="optional-body">
            <label>
              Document type
              <select value={docType} onChange={(e) => setDocType(e.target.value)}>
                {docTypes.map((x) => (
                  <option key={x} value={x}>{x}</option>
                ))}
              </select>
            </label>
          </div>
        </details>

        <button type="submit" disabled={busy || !url.trim()}>
          {busy ? "Importing… (please wait)" : "Import"}
        </button>
      </form>

      {error && <div className="banner error">{error}</div>}

      {result && (
        <div className={`banner ${result.errors ? "warn" : "success"}`}>
          Found <strong>{result.total}</strong> file(s): {result.imported} imported
          {result.duplicates > 0 && <> · {result.duplicates} duplicate(s)</>}
          {result.skipped > 0 && <> · {result.skipped} skipped (unsupported)</>}
          {result.errors > 0 && <> · {result.errors} error(s)</>}.
        </div>
      )}
    </section>
  );
}
