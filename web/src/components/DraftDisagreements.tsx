// The disagreement cards check 6 attached to a draft (ticket 36; the 36 brief, 4.8; ticket 23's card). A warning card
// ("Two reports disagree") changes a claim the draft makes, so its author chooses which report the draft keeps before
// export: "Keep {lean}" saves at once, "Keep {other} instead" asks for a reason, and either resolves the card. An info
// card ("Sources differ") changes nothing and holds nothing, and keeps ticket 23's single "Keep {other} instead". Each
// card's anchor is the one the bar's hold line links to. A choice never rewrites the draft; the evidence pack
// records it. A teammate, a preview and a draft past Checked by you see the cards without choices.
import { useId } from "react";
import { copy } from "../copy";
import type { DisagreementEvent } from "../lib/answer";
import { changesLine, ruleSentence, sideFull, sideInSentence, sideMeta, sideOpen, sideShort, subjectOf, whatChanges, type SideData } from "../lib/disagreement";
import type { Draft } from "../lib/drafts";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { DisagreementCard, SideSaid, type CardSide, type KeepState } from "./DisagreementCard";

// The id a card is kept by: strata.gold.disagreement's disagreement_id (src/strata/drafts/holds.py, disagreement_key).
export function disagreementKey(found: Pick<DisagreementEvent, "id" | "disagreement_id">): string {
  return found.disagreement_id ?? found.id.split(":").pop() ?? found.id;
}

export function DraftDisagreements({ draft, choosing, preview, onChange }: {
  draft: Draft;
  // Its author, in Draft or Checked by you, outside a preview: the cards offer their choices.
  choosing: boolean;
  preview: boolean;
  // A choice was saved: the page reads the draft again, so the bar's hold line follows.
  onChange: () => void;
}) {
  const headingId = useId();
  const found = (draft.disagreements ?? []) as DisagreementEvent[];
  if (found.length === 0) return null;
  const words = copy.disagreement;
  return (
    <section aria-labelledby={headingId} data-draft-disagreements>
      <h2 id={headingId} className="text-h2 text-ink-heading">
        {copy.draft.disagreements.title}
      </h2>
      <p className="mt-2 max-w-[72ch] text-small text-ink">{copy.draft.disagreements.lede}</p>
      <div className="mt-4 flex flex-col gap-4">
        {found.map((one) => {
          const key = disagreementKey(one);
          const sides = one.sides as SideData[];
          const lean = sides.find((side) => side.leaned);
          const other = sides.find((side) => !side.leaned);
          const cardSides = sides.map((side) => ({
            title: sideFull(side),
            titleText: sideFull(side),
            meta: sideMeta(side),
            leaned: side.leaned,
            assertionId: side.assertion_id ?? undefined,
            said: <SideSaid side={side} />,
            open: {
              label: sideOpen(side),
              href: evidenceHref(side.evidence_id),
              onOpen: (element: HTMLElement) => openEvidence(side.evidence_id, { serial: null, sentence: null, marker: element, runId: null }),
            },
          })) as [CardSide, CardSide];
          const badge = one.changes_answer ? copy.badge.twoReportsDisagree : copy.badge.sourcesDiffer;
          const choice = (draft.choices ?? []).find((entry) => entry.disagreement_id === key);
          const initial: KeepState = !choice || !choice.at ? { phase: "idle" }
            : choice.kept === "other" ? { phase: "kept", madeAt: choice.at, reason: choice.reason ?? "" }
              : { phase: "keptLean", madeAt: choice.at };
          const canKeep = (choosing || preview) && lean?.assertion_id && other?.assertion_id;
          return (
            <div key={key} id={`disagreement-${key}`} tabIndex={-1} className="focus:outline-none" data-draft-card={key}>
              {sides.length === 2 && (
                <DisagreementCard
                  warning={one.changes_answer}
                  name={words.groupName(badge, sideShort(sides[0]), sideShort(sides[1]))}
                  subject={subjectOf(one.attribute, one.period_event ?? null)}
                  level={3}
                  sides={cardSides}
                  rule={ruleSentence(one.rule_id, sides)}
                  whatChanges={whatChanges(sides, one.if_you_keep)}
                  changes={one.changes_count != null ? changesLine(one.changes_count, "draft") : undefined}
                  initialKept={initial}
                  keep={
                    canKeep
                      ? {
                          other: sideInSentence(other!),
                          otherAssertionId: other!.assertion_id!,
                          leanAssertionId: lean!.assertion_id!,
                          target: { disagreementId: key, runId: null, draftId: draft.draft_id, preview },
                          draftChoice: one.changes_answer ? { lean: sideInSentence(lean!), onChange } : undefined,
                        }
                      : undefined
                  }
                />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
