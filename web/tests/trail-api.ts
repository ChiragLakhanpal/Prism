// The recorded answers the contract trail's and the Connections tab's screen tests share (ticket 22), as
// tests/record_api.py wrote them from the server on the fixture, which tests/test_project_hub.py checks the
// server against.
import { recorded } from "./mocked";

type Answer = { status?: number; body: string };

export const KENYA = "KE-NWWDA-229129-CW-RFB";
export const SHOWCASE = "IN-RRSMP-7431-CW-RFB";
export const ICR_54 = "strata.gold.passage:31525018/v1/54";

export async function trailApi(): Promise<Record<string, Answer>> {
  const file = async (name: string) => ({ body: await recorded(name) });
  return {
    "/api/me": await file("me.json"),
    "/api/freshness": await file("freshness.json"),
    "/api/projects/P130164": await file("project-p130164.json"),
    "/api/projects/P156634": await file("project-p156634.json"),
    "/api/projects/P127203": await file("project-p130164.json"),
    [`/api/projects/P156634/packages/${KENYA}`]: await file("activity-ke-nwwda-229129.json"),
    [`/api/projects/P156634/packages/${KENYA}?asof=2022-01-02`]: await file("activity-ke-nwwda-229129-before-signing.json"),
    [`/api/projects/P130164/packages/${KENYA}`]: await file("activity-ke-nwwda-229129-moved.json"),
    [`/api/projects/P130164/packages/${SHOWCASE}`]: await file("activity-in-rrsmp-7431.json"),
    "/api/projects/P156634/packages/KE-MAWASCO-501974-CS-INDV": await file("activity-ke-mawasco-501974-indv.json"),
    "/api/projects/P156634/packages/KE-NWWDA-000000-CW-RFB": { status: 404, body: await recorded("activity-unknown.json") },
    "/api/projects/P156634/packages/KE-KIMAWASCO-372408-GO-RFQ": await file("activity-ke-kimawasco-372408.json"),
    "/api/projects/P156634/packages/KE-NWWDA-503455-CW-RFQ": await file("activity-ke-nwwda-503455.json"),
    "/api/projects/P156634/packages/KE-WASREB-235524-CS-QCBS": await file("activity-ke-wasreb-235524.json"),
    "/api/projects/P156634/packages/KE-CWSB-102977-CS-QCBS": await file("activity-ke-cwsb-102977.json"),
    "/api/projects/P130164/connections?asof=2017-06-14": await file("connections-p130164-2017-06-14.json"),
    "/api/projects/P130164/connections": await file("connections-p130164.json"),
    "/api/projects/P156634/connections": await file("connections-p156634.json"),
    "/api/projects/P127203/connections": await file("connections-p127203.json"),
    "/api/evidence": await file("evidence-icr-p130164-54.json"),
    [`/api/evidence?id=${ICR_54}&step_ref=${SHOWCASE}`]: await file("evidence-icr-p130164-54-why.json"),
    "/api/evidence?id=strata.gold.notice:OP00146683": await file("evidence-notice-op00146683.json"),
    "/api/evidence?id=strata.gold.notice:OP00164589": await file("evidence-award-notice-op00164589.json"),
    "/api/evidence?id=strata.gold.contract:1686165": await file("evidence-contract-1686165.json"),
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  };
}
