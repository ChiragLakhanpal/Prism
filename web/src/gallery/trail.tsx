// The gallery's contract trail, one-hop neighbourhood and "Why this source" (ticket 22): each component in the
// states a sample can show without a server, from the answers the server wrote on the fixture (tests/
// record_api.py), so each sample is a real activity's or project's. The pages' own states, such as loading and
// errors, are captured from the production build (web/capture/shots.ts).
import kenya from "../../../tests/fixtures/api/activity-ke-nwwda-229129.json";
import beforeSigning from "../../../tests/fixtures/api/activity-ke-nwwda-229129-before-signing.json";
import showcase from "../../../tests/fixtures/api/activity-in-rrsmp-7431.json";
import individual from "../../../tests/fixtures/api/activity-ke-mawasco-501974-indv.json";
import several from "../../../tests/fixtures/api/activity-ke-kimawasco-372408.json";
import proposals from "../../../tests/fixtures/api/activity-ke-cwsb-102977.json";
import p130164 from "../../../tests/fixtures/api/connections-p130164.json";
import p156634 from "../../../tests/fixtures/api/connections-p156634.json";
import p127203 from "../../../tests/fixtures/api/connections-p127203.json";
import whyOne from "../../../tests/fixtures/api/evidence-icr-p130164-54-why.json";
import whyOthers from "../../../tests/fixtures/api/evidence-isr-p156634-s4-why.json";
import type { ReactNode } from "react";
import { ContractTrail } from "../components/ContractTrail";
import { WhyThisSource } from "../components/WhyThisSource";
import type { Neighbourhood, Trail, Why } from "../lib/trail";
import { NeighbourhoodDiagram } from "../pages/project/ConnectionsTab";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.sections;

// A sample as wide as the activity page's columns 1 to 7 at 1440 px.
function Column({ children }: { children: ReactNode }) {
  return <div className="max-w-[46.5rem]">{children}</div>;
}

// A sample as wide as the evidence drawer.
function Drawer({ children }: { children: ReactNode }) {
  return <div className="max-w-[36rem] rounded-md border border-line bg-surface p-4">{children}</div>;
}

const trail = (answer: unknown) => (
  <Column>
    <ContractTrail trail={answer as Trail} />
  </Column>
);

export function trailPage(): GalleryPage {
  return {
    slug: "trail",
    current: "projects",
    sections: [
      { id: "trail-kenya", title: t.trailKenya, body: trail(kenya) },
      { id: "trail-showcase", title: t.trailShowcase, body: trail(showcase) },
      { id: "trail-as-of", title: t.trailAsOf, body: trail(beforeSigning) },
      { id: "trail-individual", title: t.trailIndividual, body: trail(individual) },
      { id: "trail-several", title: t.trailSeveral, body: trail(several) },
      { id: "trail-proposals", title: t.trailProposals, body: trail(proposals) },
      { id: "neighbourhood", title: t.neighbourhood, body: <NeighbourhoodDiagram data={p130164 as unknown as Neighbourhood} list={false} /> },
      { id: "neighbourhood-list", title: t.neighbourhoodList, body: <NeighbourhoodDiagram data={p130164 as unknown as Neighbourhood} list /> },
      { id: "neighbourhood-none", title: t.neighbourhoodNone, body: <NeighbourhoodDiagram data={p127203 as unknown as Neighbourhood} list={false} /> },
      { id: "neighbourhood-cap", title: t.neighbourhoodCap, body: <NeighbourhoodDiagram data={p156634 as unknown as Neighbourhood} list={false} /> },
      { id: "why-one", title: t.whyOne, body: <Drawer><WhyThisSource why={(whyOne as unknown as { why: Why }).why} /></Drawer> },
      { id: "why-others", title: t.whyOthers, body: <Drawer><WhyThisSource why={(whyOthers as unknown as { why: Why }).why} /></Drawer> },
    ],
  };
}
