// How Strata works (the 16 design brief, section 8): its purpose until ticket 47 draws its figures.
// No illustration, no placeholder image, and no link to /present.
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import { DATA_HREF } from "../../routes";

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
    </div>
  );
}
