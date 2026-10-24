// Sources and licenses (the 16 design brief, section 7): every dataset Strata reads, credited in the
// World Bank's format, the document collections, the terms of use, the sentence on Strata's own
// changes and the data caveat, word for word from DESIGN.md section 8. It reads only the source
// registry (GET /api/data/sources), so it renders while the warehouse is down.
import { useEffect } from "react";
import { Alert } from "../../components/Alert";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/Card";
import { Num } from "../../components/Num";
import { SkeletonText } from "../../components/Skeleton";
import { Template } from "../../components/Template";
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import { readRegistry, registry } from "../../lib/dataPages";
import { useStore } from "../../lib/store";

const words = copy.dataReadiness.sourcesPage;
// The World Bank's Legal page, which the sentence on other World Bank material names.
const LEGAL = "https://www.worldbank.org/en/about/legal";

export function SourcesAndLicenses() {
  const state = useStore(registry);
  useEffect(() => readRegistry(), []);
  const empty = state.status === "ready" && state.registry.datasets.length === 0;

  return (
    <div data-sources-page={state.status} className="flex max-w-prose flex-col">
      {/* With no datasets, the empty-state card stands alone, and takes the lead's focus, rather than
          sit under "Here is every dataset". */}
      {!empty && (
        <p tabIndex={-1} data-lead className="mb-12 text-body outline-none">
          {words.lead}
        </p>
      )}
      <section aria-labelledby="data-datasets">
        <h2 id="data-datasets" className="text-title text-ink-heading">
          {words.datasets}
        </h2>
        {state.status === "loading" && (
          <div aria-busy="true">
            <span className="clip-visually">{copy.loading}</span>
            <SkeletonText className="mt-3 text-body" widths={["w-full", "w-4/5", "w-full", "w-3/5"]} />
          </div>
        )}
        {state.status === "error" && (
          <Alert
            state="error"
            live="alert"
            className="mt-3"
            action={
              <Button variant="primary" onClick={() => readRegistry(true)}>
                {copy.dataReadiness.errors.tryAgain}
              </Button>
            }
          >
            {words.failed}
          </Alert>
        )}
        {empty && (
          <div tabIndex={-1} data-lead className="mt-3 outline-none">
            <EmptyState level={3} title={words.empty} body={words.emptyBody} />
          </div>
        )}
        {state.status === "ready" && state.registry.datasets.length > 0 && (
          <>
            <p className="mt-1 text-caption text-ink-muted">
              <Template text={words.datasetCount} values={{ count: <Num count={state.registry.datasets.length} /> }} />
            </p>
            <ul className="mt-3 flex flex-col gap-3">
              {state.registry.datasets.map((dataset) => (
                <li key={dataset.key} data-dataset={dataset.key} className="text-body wrap-anywhere">
                  {words.attribution.before}
                  <TextLink href={dataset.catalog_url}>{dataset.dataset_name}</TextLink>
                  {words.attribution.after(dataset.data_source, dataset.license)}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
      {state.status === "ready" && state.registry.collections.length > 0 && (
        <section aria-labelledby="data-documents" className="mt-12">
          <h2 id="data-documents" className="text-title text-ink-heading">
            {words.documents}
          </h2>
          <ul className="mt-3 flex list-disc flex-col gap-2 pl-6 text-body">
            {state.registry.collections.map((collection) => (
              <li key={collection.name}>{words.collection(collection.name, collection.publisher, collection.origin)}</li>
            ))}
          </ul>
          <p className="mt-3 text-body">
            {words.authorizes.before}
            <TextLink href={LEGAL}>{words.authorizes.link}</TextLink>
            {words.authorizes.after}
          </p>
        </section>
      )}
      <div className="mt-12 flex flex-col gap-4 text-body">
        <p className="wrap-anywhere" data-terms>
          {words.terms.before}
          <TextLink href={words.terms.link}>{words.terms.link}</TextLink>
        </p>
        <p data-changes>{words.changes}</p>
        <p data-caveat>{words.caveat}</p>
      </div>
    </div>
  );
}
