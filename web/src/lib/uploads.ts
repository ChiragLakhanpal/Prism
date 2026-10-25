// An implementing agency's private uploads in the browser (ticket 38): the shapes the upload routes answer with
// (src/strata/server/uploads.py), the officer's agency, and the one request that sends a file. Every count comes from
// the server; nothing here reads the file.
import { ApiError, type CheckPlanResult } from "./api";
import { createStore } from "./store";

// The implementing agency whose team the viewer is on, from /api/me: null for anyone else, undefined until it is known.
export const officerAgency = createStore<{ name: string; agency_id: string } | null | undefined>(undefined);

export type UploadForm = {
  officer: boolean;
  agency: { name: string; agency_id: string } | null;
  projects: {
    project_id: string;
    project_name: string;
    display_name: string | null;
    latest_plan: { plan_date: string; disclosed_on: string | null; agency_id: string } | null;
  }[];
  earlier: number;
  preview: boolean;
  // STEP's column names, from the STEP column registry, never from the copy file.
  columns: { needed: string[]; optional: string[] };
  limits: { accept: string[]; max_size_bytes: number; max_rows: number };
  format: "step_export" | "published_tables";
};

export type UploadListing = {
  upload_id: string;
  uploaded_at: string;
  uploaded_on: string;
  uploader: { name: string | null; you: boolean };
  project_id: string;
  implementing_agency: string;
  agency_id: string;
  file_name: string;
  activities: number;
};

export type Reading = {
  sheets: string[];
  used: { header: string; as: string | null }[];
  unused: string[];
  activities: number;
  unread_values: number;
  file_name: string;
};

// GET /api/uploads/{id}: check_plan's result on the upload, with the upload itself.
export type UploadCheck = CheckPlanResult & { upload: UploadListing & { reading: Reading } };

// Why a file was not kept, as the server says it: the reading's code and the values its sentence names.
export type UploadRefusal = {
  code: string;
  kept?: boolean;
  file_name?: string;
  extension?: string | null;
  size?: number;
  max_size?: number;
  missing?: string[];
  n?: number;
  max_rows?: number;
};

export const uploadHref = (uploadId: string) => `/packages/uploads/${encodeURIComponent(uploadId)}`;
export const CHECK_MY_PLAN = "/packages/check";

// One upload: the file itself is the request's body, so the server holds it only while it reads it.
export async function sendUpload(file: File, projectId: string, key: string): Promise<UploadCheck & { upload_id: string }> {
  const query = new URLSearchParams({ project_id: projectId, file_name: file.name, idempotency_key: key });
  const response = await fetch(`/api/uploads?${query.toString()}`, {
    method: "POST",
    headers: { "Content-Type": "application/octet-stream", Accept: "application/json" },
    body: file,
  });
  const body = await response.json().catch(() => ({ code: "service" }));
  if (!response.ok) throw new ApiError(response.status, "/api/uploads", body);
  return body;
}

// The file's ending, as the uploads config lists them, such as .xlsx.
export function endingOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}
