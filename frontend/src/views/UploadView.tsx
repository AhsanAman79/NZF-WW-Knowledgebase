import { useRef, useState } from "react";
import { uploadDocument } from "../api";

interface Props {
  entities: string[];
  areas: string[];
  docTypes: string[];
}

type Result = { name: string; status: "ok" | "duplicate" | "error"; detail?: string };

export default function UploadView({ entities, areas, docTypes }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [entity, setEntity] = useState("");
  const [area, setArea] = useState("");
  const [docType, setDocType] = useState("Other");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
  const [results, setResults] = useState<Result[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const folderRef = useRef<HTMLInputElement>(null);

  const canSubmit = files.length > 0 && !busy;

  function addFiles(incoming: File[]) {
    setFiles((prev) => {
      const seen = new Set(prev.map((f) => f.name + ":" + f.size));
      const merged = [...prev];
      for (const f of incoming) {
        const key = f.name + ":" + f.size;
        if (!seen.has(key)) {
          seen.add(key);
          merged.push(f);
        }
      }
      return merged;
    });
  }

  // --- Recursive folder traversal (drag & drop) ---
  async function readAll(reader: any): Promise<any[]> {
    const out: any[] = [];
    for (;;) {
      const batch: any[] = await new Promise((res, rej) => reader.readEntries(res, rej));
      if (!batch.length) break;
      out.push(...batch);
    }
    return out;
  }
  async function entryToFiles(entry: any): Promise<File[]> {
    if (!entry) return [];
    if (entry.isFile) {
      return await new Promise((res) => entry.file((f: File) => res([f]), () => res([])));
    }
    if (entry.isDirectory) {
      const entries = await readAll(entry.createReader());
      const nested = await Promise.all(entries.map(entryToFiles));
      return nested.flat();
    }
    return [];
  }

  async function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const items = e.dataTransfer.items;
    if (items && items.length && (items[0] as any).webkitGetAsEntry) {
      const entries: any[] = [];
      for (let i = 0; i < items.length; i++) {
        const en = (items[i] as any).webkitGetAsEntry();
        if (en) entries.push(en);
      }
      const all = await Promise.all(entries.map(entryToFiles));
      addFiles(all.flat());
    } else if (e.dataTransfer.files?.length) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!files.length) return;
    setBusy(true);
    setError(null);
    setResults(null);
    const res: Result[] = [];
    setProgress({ done: 0, total: files.length });
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      try {
        const r = await uploadDocument(
          f,
          entity,
          area,
          docType,
          files.length === 1 ? title : "",
          description
        );
        res.push({ name: f.name, status: r.duplicate ? "duplicate" : "ok" });
      } catch (err) {
        res.push({ name: f.name, status: "error", detail: (err as Error).message });
      }
      setProgress({ done: i + 1, total: files.length });
    }
    setResults(res);
    setBusy(false);
    setProgress(null);
    setFiles([]);
    setTitle("");
    if (inputRef.current) inputRef.current.value = "";
    if (folderRef.current) folderRef.current.value = "";
  }

  const okCount = results?.filter((r) => r.status === "ok").length ?? 0;
  const dupCount = results?.filter((r) => r.status === "duplicate").length ?? 0;
  const errCount = results?.filter((r) => r.status === "error").length ?? 0;

  return (
    <section className="card">
      <h2>Upload documents</h2>
      <p className="hint">
        Drag in <strong>multiple files or whole folders</strong> (subfolders included).
        All fields are optional and apply to every file in this batch. Files are stored on
        the central SharePoint and indexed for search.
      </p>

      <form onSubmit={onSubmit} className="form">
        <div
          className={`dropzone${dragging ? " dragging" : ""}${files.length ? " has-file" : ""}`}
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
            multiple
            hidden
            onChange={(e) => e.target.files && addFiles(Array.from(e.target.files))}
          />
          <input
            ref={folderRef}
            type="file"
            multiple
            hidden
            onChange={(e) => e.target.files && addFiles(Array.from(e.target.files))}
            {...({ webkitdirectory: "", directory: "" } as any)}
          />
          {files.length ? (
            <div className="dz-file">
              <span className="dz-icon">📄</span>
              <span className="dz-name">
                {files.length} file{files.length === 1 ? "" : "s"} selected
              </span>
            </div>
          ) : (
            <div className="dz-empty">
              <span className="dz-icon">⬆</span>
              <span>
                <strong>Drag &amp; drop</strong> files or folders here, or click to choose
                files
              </span>
            </div>
          )}
        </div>

        <div className="row-links">
          <button type="button" className="linkbtn" onClick={() => folderRef.current?.click()}>
            Choose a folder…
          </button>
          {files.length > 0 && (
            <button type="button" className="linkbtn" onClick={() => setFiles([])}>
              Clear ({files.length})
            </button>
          )}
        </div>

        {files.length > 0 && files.length <= 12 && (
          <ul className="file-list">
            {files.map((f, i) => (
              <li key={f.name + i}>
                {f.name} <span className="dz-size">{(f.size / 1024).toFixed(0)} KB</span>
              </li>
            ))}
          </ul>
        )}

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
            {files.length <= 1 && (
              <label>
                Title
                <input
                  type="text"
                  placeholder="e.g. Annual Impact Report 2025"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </label>
            )}
            <label>
              Description
              <textarea
                rows={2}
                placeholder="Short summary or keywords (applied to all files)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </label>
          </div>
        </details>

        <button type="submit" disabled={!canSubmit}>
          {busy && progress
            ? `Uploading ${progress.done}/${progress.total}…`
            : `Upload${files.length ? ` ${files.length} file${files.length === 1 ? "" : "s"}` : ""}`}
        </button>
      </form>

      {error && <div className="banner error">{error}</div>}

      {results && (
        <div className={`banner ${errCount ? "warn" : "success"}`}>
          <strong>{okCount}</strong> uploaded
          {dupCount > 0 && <> · {dupCount} duplicate(s) skipped</>}
          {errCount > 0 && <> · {errCount} failed</>}.
          {errCount > 0 && (
            <ul className="file-list">
              {results
                .filter((r) => r.status === "error")
                .map((r, i) => (
                  <li key={i}>
                    {r.name}: {r.detail}
                  </li>
                ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
