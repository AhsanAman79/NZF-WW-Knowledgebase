// API client for the NZF WW Knowledgebase backend.
// Relative paths work behind the Vite dev proxy and when FastAPI serves the build.

export interface SearchResultItem {
  document_id: string;
  filename: string;
  title: string | null;
  entity: string;
  area: string;
  doc_type: string | null;
  upload_date: string | null;
  sharepoint_url: string | null;
  snippet: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  answer: string | null;
  results: SearchResultItem[];
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  stored_filename: string;
  entity: string;
  area: string;
  doc_type: string;
  title: string | null;
  sharepoint_url: string | null;
  chunks_indexed: number;
  extracted_chars: number;
  sharepoint_uploaded: boolean;
  duplicate: boolean;
}

async function asError(res: Response): Promise<never> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail ?? detail;
  } catch {
    /* ignore */
  }
  throw new Error(detail);
}

async function getList(path: string): Promise<string[]> {
  const res = await fetch(path);
  if (!res.ok) return asError(res);
  return res.json();
}

export const getEntities = () => getList("/api/entities");
export const getAreas = () => getList("/api/areas");
export const getDocTypes = () => getList("/api/doctypes");

export async function uploadDocument(
  file: File,
  entity: string,
  area: string,
  docType: string,
  title: string,
  description: string
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("entity", entity);
  form.append("area", area);
  form.append("doc_type", docType);
  form.append("title", title);
  form.append("description", description);
  const res = await fetch("/api/upload", { method: "POST", body: form });
  if (!res.ok) return asError(res);
  return res.json();
}

export async function search(
  query: string,
  entity?: string,
  area?: string,
  docType?: string
): Promise<SearchResponse> {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      entity: entity || null,
      area: area || null,
      doc_type: docType || null,
    }),
  });
  if (!res.ok) return asError(res);
  return res.json();
}

export interface ImportResult {
  total: number;
  imported: number;
  duplicates: number;
  skipped: number;
  errors: number;
}

export async function importLink(
  url: string,
  entity?: string,
  area?: string,
  docType?: string
): Promise<ImportResult> {
  const res = await fetch("/api/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      entity: entity || null,
      area: area || null,
      doc_type: docType || null,
    }),
  });
  if (!res.ok) return asError(res);
  return res.json();
}
