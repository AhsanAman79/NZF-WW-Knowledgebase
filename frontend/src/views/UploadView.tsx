import { useState } from "react";
import { uploadDocument, type UploadResponse } from "../api";

interface Props {
  entities: string[];
  areas: string[];
}

export default function UploadView({ entities, areas }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [entity, setEntity] = useState("");
  const [area, setArea] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = file && entity && area && !busy;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !entity || !area) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadDocument(file, entity, area);
      setResult(res);
      setFile(null);
      (document.getElementById("file-input") as HTMLInputElement).value = "";
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Upload a document</h2>
      <p className="hint">
        Select a file and tell us which entity and area it belongs to. The file is
        stored on the central SharePoint and indexed for search. Supported: PDF, DOCX,
        XLSX, PPTX, HTML, VTT, TXT.
      </p>

      <form onSubmit={onSubmit} className="form">
        <label>
          Entity
          <select value={entity} onChange={(e) => setEntity(e.target.value)}>
            <option value="">Select entity…</option>
            {entities.map((x) => (
              <option key={x} value={x}>{x}</option>
            ))}
          </select>
        </label>

        <label>
          Area
          <select value={area} onChange={(e) => setArea(e.target.value)}>
            <option value="">Select area…</option>
            {areas.map((x) => (
              <option key={x} value={x}>{x}</option>
            ))}
          </select>
        </label>

        <label>
          File
          <input
            id="file-input"
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>

        <button type="submit" disabled={!canSubmit}>
          {busy ? "Uploading & indexing…" : "Upload"}
        </button>
      </form>

      {error && <div className="banner error">{error}</div>}

      {result && (
        <div className="banner success">
          <strong>{result.filename}</strong> uploaded for {result.entity} / {result.area}.
          <br />
          Indexed {result.chunks_indexed} chunk(s) from {result.extracted_chars} characters.
          {result.sharepoint_uploaded
            ? result.sharepoint_url && (
                <>
                  {" "}
                  <a href={result.sharepoint_url} target="_blank" rel="noreferrer">
                    Open in SharePoint
                  </a>
                </>
              )
            : " (SharePoint not configured — indexed locally only.)"}
        </div>
      )}
    </section>
  );
}
