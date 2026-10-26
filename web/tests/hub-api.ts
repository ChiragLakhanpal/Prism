// The recorded answers the project hub's screen tests share (ticket 21): P130164's project, Summary,
// Documents and source view pages, as tests/record_api.py wrote them from the server on the fixture.
import { recorded, viewAnswers } from "./mocked";

type Answer = { status?: number; body: string };

// The Kenya National Highways Authority's plan of September 24, 2026, whose page 3 holds 13 STEP rows.
export const KENHA_PLAN = "procurement-plan-kenya-national-highways-authority-2026-09-24";

export async function hubApi(): Promise<Record<string, Answer>> {
  const file = async (name: string) => ({ body: await recorded(name) });
  return {
    ...(await viewAnswers()),
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
    "/api/projects/P130164/documents/pad-2013-10-01?page=65": await file("source-pad-p130164-65.json"),
    [`/api/projects/P161305/documents/${KENHA_PLAN}?page=3`]: await file("source-plan-p161305-3.json"),
    "/api/evidence": await file("evidence-icr-p130164-54.json"),
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  };
}

