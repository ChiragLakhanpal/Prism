// The Data tab (the 16 design brief, section 2): one header for its two pages, the sub-tabs as
// links in a nav labelled "Data pages", and the page the address names. Each page's lead takes
// focus when a sub-tab moves to it (web/src/App.tsx). How Strata works left the tab in ticket 97;
// its old address opens Data readiness (web/src/routes.ts).
import { PageHeader } from "../../components/PageHeader";
import { Tabs } from "../../components/Tabs";
import { copy } from "../../copy";
import { DATA_HREF, type Match } from "../../routes";
import { DataReadiness } from "./DataReadiness";
import { SourcesAndLicenses } from "./SourcesAndLicenses";

const words = copy.dataReadiness.tabs;

export function DataPage({ match, search }: { match: Match; search: string }) {
  const key = match.key as "data" | "dataSources";
  return (
    <>
      <PageHeader title={copy.pages[key].title} purpose={copy.pages[key].purpose} />
      <div className="mt-6">
        <Tabs
          label={words.label}
          tabs={[
            { key: "data", label: words.readiness, href: DATA_HREF.data, current: key === "data" },
            { key: "dataSources", label: words.sources, href: DATA_HREF.dataSources, current: key === "dataSources" },
          ]}
        />
      </div>
      <div className="mt-8">{key === "data" ? <DataReadiness search={search} /> : <SourcesAndLicenses />}</div>
    </>
  );
}
