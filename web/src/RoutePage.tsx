// What each route shows until its own ticket fills it (the 06 design brief): its title, the one
// sentence that says what it is for, and an empty-state card that says, in the first person,
// what will appear there and what fills it. The not-found pages have no card: their purpose
// already says what to do, and their one link follows it.
import { EmptyState } from "./components/Card";
import { PageHeader, WithIds } from "./components/PageHeader";
import { TextLink } from "./components/TextLink";
import { copy } from "./copy";
import type { Match } from "./routes";

export function RoutePage({ match }: { match: Match }) {
  const words: { title: string; purpose: string; emptyTitle?: string; emptyBody?: string; link?: string } = copy.pages[match.key];
  const link = words.link && match.linkHref ? { href: match.linkHref, text: <WithIds template={words.link} values={match.values} /> } : undefined;
  return (
    <>
      <PageHeader title={<WithIds template={words.title} values={match.values} />} purpose={words.purpose} />
      {words.emptyTitle && words.emptyBody ? (
        <EmptyState
          className="mt-6 lg:mt-8"
          title={<WithIds template={words.emptyTitle} values={match.values} />}
          body={words.emptyBody}
          link={link}
        />
      ) : (
        link && (
          <p className="mt-4 text-body">
            <TextLink href={link.href}>{link.text}</TextLink>
          </p>
        )
      )}
    </>
  );
}
