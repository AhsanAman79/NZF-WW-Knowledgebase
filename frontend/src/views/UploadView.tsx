import { useRef, useState } from "react";
import { uploadDocument, type UploadResponse } from "../api";

interface Props {
  entities: string[];
  areas: string[];
  docTypes: string[];
}

export default function UploadView({ entities, areas, docTypes }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [entity, setEntity] = useState("");
  const [area, setArea] = useState("");
  const [docType, setDocType] = useState("Other");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const canSubmit = !!file && !!entity && !!area && !busy;

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) setFile(e.dataTransfer.files[0]);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !entity || !area) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadDocument(file, entity, area, docType, title, description);
      setResult(res);
      setFile(null);
      setTitle("");
      setDescription("");
      if (inputRef.current) inputRef.current.value = "";
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
        Only <strong>Entity</strong> and <strong>Area</strong> are required. The file is
        stored on the central SharePoint and indexed for search.
      </p>

      <form onSubmit={onSubmit} className="form">
        <div
          className={`dropzone${dragging ? " dragging" : ""}${file ? " has-file" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <input
            ref={inputRef}
            type="file"
            hidden
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <div className="dz-file">
              <span className="dz-icon">📄</span>
              <span className="dz-name">{file.name}</span>
              <span className="dz-size">{(file.size / 1024).toFixed(0)} KB</span>
            </div>
          ) : (
            <div className="dz-empty">
              <span className="dz-icon">⬆</span>
              <span>
                <strong>Drag &amp; drop</strong> a file here, or click to choose
              </span>
            </div>
          )}
        </div>

        <div className="grid-2">
          <label>
            <span className="label-text">Entity <span className="req">*</span></span>
            <select value={entity} onChange={(e) => setEntity(e.target.value)}>
              <option value="">Select entity…</option>
              {entities.map((x) => (
                <option key={x} value={x}>{x}</option>
              ))}
            </select>
          </label>
          <label>
            <span className="label-text">Area <span className="req">*</span></span>
            <select value={area} onChange={(e) => setArea(e.target.value)}>
              <option value="">Select area…</option>
              {areas.map((x) => (
                <option key={x} value={x}>{x}</option>
              ))}
            </select>
          </label>
        </div>

        <details className="optional">
          <summary>Optional details (improve search)</summary>
          <div className="optional-body">
            <label>
              Document type
              <select value={docType} onChange={(e) => setDocType(e.target.value)}>
                {docTypes.map((x) => (
                  <option key={x} value={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Title
              <input
                type="text"
                placeholder="e.g. Annual Impact Report 2025"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Description
              <textarea
                rows={2}
                placeholder="Short summary or keywords"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
          </div>
        </details>

        <button type="submit" disabled={!canSubmit}>
          {busy ? "Uploading & indexing…" : "Upload"}
        </button>
      </form>

      {error && <div className="banner error">{error}</div>}

      {result && result.duplicate && (
        <div className="banner warn">
          This document already exists in the knowledgebase (identical content) — not
          uploaded again.
        </div>
      )}

      {result && !result.duplicate && (
        <div className="banner success">
          <strong>{result.filename}</strong> uploaded for {result.entity} / {result.area}.
          <br />
          Stored as <code>{result.stored_filename}</code> · indexed {result.chunks_indexed}{" "}
          chunk(s).
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
