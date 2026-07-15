// API client for the NZF WW Knowledgebase backend.
// Uses relative paths so it works both behind the Vite dev proxy and when the
// static build is served directly by FastAPI.

export interface SearchResultItem {
  document_id: string;
  filename: string;
  entity: string;
  area: string;
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
  entity: string;
  area: string;
  sharepoint_url: string | null;
  chunks_indexed: number;
  extracted_chars: number;
  sharepoint_uploaded: boolean;
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

export async function getEntities(): Promise<string[]> {
  const res = await fetch("/api/entities");
  if (!res.ok) return asError(res);
  return res.json();
}

export async function getAreas(): Promise<string[]> {
  const res = await fetch("/api/areas");
  if (!res.ok) return asError(res);
  return res.json();
}

export async function uploadDocument(
  file: File,
  entity: string,
  area: string
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("entity", entity);
  form.append("area", area);
  const res = await fetch("/api/upload", { method: "POST", body: form });
  if (!res.ok) return asError(res);
  return res.json();
}

export async function search(
  query: string,
  entity?: string,
  area?: string
): Promise<SearchResponse> {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      entity: entity || null,
      area: area || null,
    }),
  });
  if (!res.ok) return asError(res);
  return res.json();
}
