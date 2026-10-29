// The Data section (the 16 design brief, section 2; ticket 104): one header for its two pages, and the page the address
// names. Data readiness and Sources and licenses are the sidebar's items under Data (web/src/components/sections.ts), as
// Following and All projects are under Projects, so the page draws no sub-tab row. Each page's lead takes focus when a
// sidebar item moves to it (web/src/App.tsx). How Strata works left the section in ticket 97; its old address opens
// Data readiness (web/src/routes.ts).
import { PageHeader } from "../../components/PageHeader";
import { copy } from "../../copy";
import type { Match } from "../../routes";
import { DataReadiness } from "./DataReadiness";
import { SourcesAndLicenses } from "./SourcesAndLicenses";

export function DataPage({ match, search }: { match: Match; search: string }) {
  const key = match.key as "data" | "dataSources";
  return (
    <>
      <PageHeader title={copy.pages[key].title} purpose={copy.pages[key].purpose} />
      <div className="mt-8">{key === "data" ? <DataReadiness search={search} /> : <SourcesAndLicenses />}</div>
    </>
  );
}
