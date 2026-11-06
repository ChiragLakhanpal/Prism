// Field photos (ticket 150): the photos a World Bank staff viewer's team took on a mission and added to a project's
// Deep research tab, from GET /api/projects/{pid}/field-photos, and one more added with POST, the photo itself as the
// request's body and its name and caption percent-encoded in headers, never in the address.
import { ApiError } from "./api";
import { withPageParams } from "./view";

export type FieldPhoto = {
  photo_id: string;
  project_id: string;
  file_name: string;
  caption: string;
  taken_on: string | null;
  place: string | null;
  latitude: number | null;
  longitude: number | null;
  uploaded_at: string;
  uploader: { name: string | null; you: boolean };
  url: string;
};

export type FieldPhotoList = {
  project_id: string;
  photos: FieldPhoto[];
  may_add: boolean;
  preview: boolean;
  limits: { accept: string[]; max_size_bytes: number; max_per_project: number; max_caption: number };
};

export const fieldPhotosPath = (pid: string) => `/api/projects/${encodeURIComponent(pid)}/field-photos`;

export async function sendFieldPhoto(pid: string, file: File, caption: string): Promise<{ kept: boolean; photo: FieldPhoto }> {
  const path = fieldPhotosPath(pid);
  const response = await fetch(withPageParams(path), {
    method: "POST",
    headers: {
      "Content-Type": "application/octet-stream",
      Accept: "application/json",
      "X-Strata-File-Name": encodeURIComponent(file.name),
      "X-Strata-Caption": encodeURIComponent(caption),
    },
    body: file,
  });
  const body = await response.json().catch(() => ({ code: "service" }));
  if (!response.ok) throw new ApiError(response.status, path, body);
  return body;
}
