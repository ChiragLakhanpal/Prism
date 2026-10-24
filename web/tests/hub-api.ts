// The recorded answers the project hub's screen tests share (ticket 21): P130164's project, Summary,
// Documents and source view pages, as tests/record_api.py wrote them from the server on the fixture.
import { recorded } from "./mocked";

type Answer = { status?: number; body: string };

export async function hubApi(): Promise<Record<string, Answer>> {
  const file = async (name: string) => ({ body: await recorded(name) });
  return {
    "/api/me": await file("me.json"),
    "/api/freshness": await file("freshness.json"),
    "/api/projects/P130164": await file("project-p130164.json"),
    "/api/projects/P130164/summary": await file("summary-p130164.json"),
    "/api/projects/P130164/documents": await file("documents-p130164.json"),
    "/api/projects/P130164/documents/icr-2019-10-10?page=23&para=54": await file("source-icr-p130164-23-54.json"),
    "/api/projects/P130164/documents/icr-2019-10-10?page=23": await file("source-icr-p130164-23.json"),
    "/api/projects/P130164/documents/icr?page=23&para=54": await file("source-icr-p130164-short.json"),
    "/api/projects/P130164/documents/icr-2019-10-10?page=22&para=54": await file("source-icr-p130164-moved.json"),
    "/api/projects/P130164/documents/icr-2019-10-10?page=23&para=999": await file("source-icr-p130164-no-para.json"),
    "/api/projects/P130164/documents/icr-2019-10-10?page=80": await file("source-icr-p130164-page-range.json"),
    "/api/projects/P130164/documents/icr-2019-10-10?page=66": await file("source-icr-p130164-page-range.json"),
    "/api/projects/P130164/documents/icr-2019-10-10?page=5": await file("source-icr-p130164-page-unread.json"),
    "/api/projects/P130164/documents/icr-review-2023-05-04?page=1": await file("source-icr-review-p130164-reissue.json"),
    "/api/projects/P130164/documents/isr": await file("source-p130164-ambiguous.json"),
    "/api/projects/P130164/documents/not-a-document": await file("source-p130164-not-found.json"),
    "/api/projects/P130164/documents/30152361": await file("source-p130164-doc-unread.json"),
    "/api/evidence": await file("evidence-icr-p130164-54.json"),
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  };
}

