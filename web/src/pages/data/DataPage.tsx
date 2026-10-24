// The Data tab (the 16 design brief, section 2): one header for its three pages, the sub-tabs as
// links in a nav labelled "Data pages", and the page the address names. Each page's lead takes
// focus when a sub-tab moves to it (web/src/App.tsx).
import { PageHeader } from "../../components/PageHeader";
import { Tabs } from "../../components/Tabs";
import { copy } from "../../copy";
import { DATA_HREF, type Match } from "../../routes";
import { DataReadiness } from "./DataReadiness";
import { HowStrataWorks } from "./HowStrataWorks";
import { SourcesAndLicenses } from "./SourcesAndLicenses";

const words = copy.dataReadiness.tabs;

export function DataPage({ match, search }: { match: Match; search: string }) {
  const key = match.key as "data" | "dataSources" | "dataHow";
  return (
    <>
      <PageHeader title={copy.pages[key].title} purpose={copy.pages[key].purpose} />
      <div className="mt-6">
        <Tabs
          label={words.label}
          tabs={[
            { key: "data", label: words.readiness, href: DATA_HREF.data, current: key === "data" },
            { key: "dataSources", label: words.sources, href: DATA_HREF.dataSources, current: key === "dataSources" },
            { key: "dataHow", label: words.how, href: DATA_HREF.dataHow, current: key === "dataHow" },
          ]}
        />
      </div>
      <div className="mt-8">
        {key === "data" ? <DataReadiness search={search} /> : key === "dataSources" ? <SourcesAndLicenses /> : <HowStrataWorks />}
      </div>
    </>
  );
}
