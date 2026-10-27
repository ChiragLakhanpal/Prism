// "Drafts from this check" (ticket 36; the 36 brief, sections 3.6, 4.9 and 5.7): the quiet panel at the end of Check a
// plan that offers the procurement summary for the Project Paper as a secondary action, and says before the click what
// it draws on: this check, the agency's track record and the PPSD rows the team checked for the project's packages,
// counted by the server. An open summary on this plan version shows as a notice with a link to it. Only World Bank
// staff see it, and only on today's populated check outside a preview; as of a past date it says why it offers no
// draft.
import { useEffect, useId, useState } from "react";
import { copy } from "../copy";
import { ApiError, getJson } from "../lib/api";
import { draftHref, startProjectPaper, type ExistingDraft, type Writing } from "../lib/drafts";
import { formatCount, formatDate } from "../lib/format";
import { staffRole } from "../lib/following";
import { navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { TextLink } from "./TextLink";

const words = copy.checkPlan.ppAction;

type Inputs = { qualifying_ppsd_rows: { count: number; draft_ids: string[] }; agencies_with_plans: number | null };

export function ProjectPaperPanel({ plan, preview, asOf }: {
  plan: NonNullable<Writing["summaryPlan"]>;
  preview: boolean;
  asOf: boolean;
}) {
  const staff = useStore(staffRole);
  const headingId = useId();
  const feedforwardId = useId();
  const [inputs, setInputs] = useState<Inputs | null>(null);
  const [refused, setRefused] = useState(false);
  const [existing, setExisting] = useState<ExistingDraft | null>(null);
  const shown = staff === true && !preview;

  useEffect(() => {
    if (!shown || asOf) return;
    const controller = new AbortController();
    getJson<Inputs>(`/api/drafts/project-paper-inputs?${new URLSearchParams({ project_id: plan.project_id }).toString()}`,
      { signal: controller.signal }).then(setInputs, (error) => {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) setRefused(true);
    });
    const query = new URLSearchParams({ kind: "project_paper", project_id: plan.project_id, agency_id: plan.agency_id, plan_date: plan.plan_date });
    getJson<{ draft: ExistingDraft | null }>(`/api/drafts/existing?${query.toString()}`, { signal: controller.signal }).then(
      (found) => setExisting(found.draft),
      () => undefined,
    );
    return () => controller.abort();
  }, [shown, asOf, plan.project_id, plan.agency_id, plan.plan_date]);

  if (!shown || refused) return null;
  const rows = inputs?.qualifying_ppsd_rows.count ?? null;
  const body = rows === null
    ? words.bodyUnknown
    : rows === 0 ? words.bodyNoRows : words.body(rows);
  return (
    <section aria-labelledby={headingId} className="max-w-[72ch] rounded-md border border-line bg-surface p-4 md:p-6" data-pp-panel>
      <h2 id={headingId} className="text-h2 text-ink-heading">
        {words.title}
      </h2>
      <p className="mt-2 text-body text-ink" data-pp-body>
        <Fill template={body} slots={{ agency: plan.implementing_agency, rows: rows === null ? "" : formatCount(rows) }} />
      </p>
      {asOf ? (
        <p className="mt-4 text-caption text-ink-muted" data-pp-asof>
          {words.asof}
        </p>
      ) : (
        <>
          {existing && (
            <div className="mt-4">
              <Alert state="info" action={<TextLink href={draftHref(existing.draft_id)}>{words.existingLink}</TextLink>}>
                <span data-existing-pp>
                  {existing.author.you
                    ? words.existingYou(formatDate(existing.created_at.slice(0, 10)))
                    : words.existingTeammate(existing.author.name ?? "", formatDate(existing.created_at.slice(0, 10)))}
                </span>
              </Alert>
            </div>
          )}
          <div className="mt-4">
            <Button variant="secondary" aria-describedby={feedforwardId} onClick={() => navigate(startProjectPaper(plan))} data-pp-action>
              {words.button}
            </Button>
          </div>
          <p id={feedforwardId} className="mt-2 text-caption text-ink-muted">
            {words.feedforward}
          </p>
        </>
      )}
    </section>
  );
}
