// How Strata works (the 16 design brief, section 8): its purpose until ticket 47 draws its figures.
// No illustration, no placeholder image, and no link to /present. Its last section, "What I don't do"
// (ticket 24; the 24 brief, section 4.7), lists each refusal's lead with its why, from the same copy
// keys the answer panel renders, so the link under every refusal keeps its promise. Ticket 47's
// figures go above it.
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import { DATA_HREF, WHAT_I_DONT_DO } from "../../routes";

const words = copy.dataReadiness.howPage;

export function HowStrataWorks() {
  return (
    <div className="flex max-w-prose flex-col gap-4">
      <p tabIndex={-1} data-lead className="text-body outline-none">
        {words.lead}
      </p>
      <p className="text-body">
        {words.next.before}
        <TextLink href={DATA_HREF.data}>{words.next.readiness}</TextLink>
        {words.next.middle}
        <TextLink href={DATA_HREF.dataSources}>{words.next.sources}</TextLink>
        {words.next.after}
      </p>
      <section aria-labelledby={WHAT_I_DONT_DO.id} className="mt-4">
        <h2 id={WHAT_I_DONT_DO.id} tabIndex={-1} className="text-h2 text-ink-heading outline-none">
          {words.dontDo.heading}
        </h2>
        <p className="mt-2 text-body">{words.dontDo.intro}</p>
        <dl data-dont-do className="mt-4 flex flex-col gap-4">
          {Object.entries(copy.refusals).map(([key, refusal]) => (
            <div key={key}>
              <dt className="text-body font-semibold text-ink">{refusal.lead}</dt>
              <dd className="mt-1 text-body text-ink">{refusal.why}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
