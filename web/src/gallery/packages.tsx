// The gallery's planned packages page (ticket 15): every new component of the package workspace in each of its
// states, from the packages the server saved on the fixture (tests/record_packages_api.py), so each sample is a
// real package with the server's own values. Hover, keyboard focus, the editors' errors and the bottom sheet are
// captured from the app (web/capture/shots.ts).
import rural from "../../../tests/fixtures/api/planned-package-rural-roads.json";
import amount from "../../../tests/fixtures/api/planned-package-change-amount.json";
import reviewPost from "../../../tests/fixtures/api/planned-package-change-review-post.json";
import planned from "../../../tests/fixtures/api/planned-package-change-plan.json";
import dividing from "../../../tests/fixtures/api/planned-package-dividing.json";
import yourself from "../../../tests/fixtures/api/planned-package-yourself.json";
import comparables from "../../../tests/fixtures/api/comparables-planned-works-rfb-ke.json";
import signed from "../../../tests/fixtures/api/evidence-package-ke-mowi-47509.json";
import stillOpen from "../../../tests/fixtures/api/evidence-package-ke-icta-571738.json";
import list from "../../../tests/fixtures/api/planned-packages-list.json";
import emptyList from "../../../tests/fixtures/api/planned-packages-empty.json";
import { useId, type ReactNode } from "react";
import { ChipGroups, ChipSkeletons, CardTop, ComputedNote, CriterionChip, RefusalAlert } from "../components/Criteria";
import { EditorBody } from "../components/ChipEditor";
import { ComparableRecords } from "../components/ComparableRecords";
import { POPOVER } from "../components/Popover";
import { Steps } from "../components/Steps";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { ComparablesResult } from "../lib/api";
import { cx } from "../lib/cx";
import type { FieldValue, FormField, PackageForm, PlannedList, PlannedPackage } from "../lib/packages";
import { PackagesList } from "../pages/PackagesPage";
import { PlanPrompt, SavedStamp } from "../pages/PlannedPackagePage";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const ps = galleryCopy.plannedStates;
const FORM = rural.form as unknown as PackageForm;
const RURAL = rural.package as unknown as PlannedPackage;
const AMOUNT = amount.package as unknown as PlannedPackage;
const REVIEW_POST = reviewPost.package as unknown as PlannedPackage;
const PLANNED = planned.package as unknown as PlannedPackage;
const DIVIDING = dividing.package as unknown as PlannedPackage;
const YOURSELF = yourself.package as unknown as PlannedPackage;
const RESULT = comparables as unknown as ComparablesResult;
const nothing = () => undefined;

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

// A sample as wide as the workspace's column at 1440 px: columns 1 to 7.
function Column({ children }: { children: ReactNode }) {
  return <div className="@container/page max-w-[46.5rem]">{children}</div>;
}

const field = (key: string) => FORM.fields.find((one) => one.key === key)!;
const valueOf = (pkg: PlannedPackage, key: string): FieldValue => pkg.fields.find((one) => one.key === key)!;

function Chip({ pkg, target, open = false }: { pkg: PlannedPackage; target: FormField; open?: boolean }) {
  return <CriterionChip field={target} value={valueOf(pkg, target.key)} form={FORM} approximate={pkg.approximate} open={open} />;
}

// The "What I understood" card as the workspace draws it, with chips that open nothing here.
function UnderstoodCard({ pkg }: { pkg: PlannedPackage }) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <CardTop sentence={pkg.sentence} guesses={pkg.guesses} headingId={headingId} />
      {pkg.refusal === "dividing" && <RefusalAlert />}
      <div className="mt-4">
        <ChipGroups form={FORM} chip={(target) => <Chip key={target.key} pkg={pkg} target={target} />} />
      </div>
      <ComputedNote pkg={pkg} form={FORM} />
    </section>
  );
}

function ReadingCard() {
  const headingId = useId();
  const steps = copy.packageWorkspace.steps;
  return (
    <section aria-labelledby={headingId} className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <CardTop sentence={RURAL.sentence} guesses={null} headingId={headingId} />
      <div className="mt-4">
        <Steps
          announce={false}
          reserveLines={4}
          steps={[
            { key: "read", running: steps.read.running, done: steps.read.done, state: "done" },
            { key: "compute", running: steps.compute.running, done: steps.compute.done, state: "running" },
          ]}
        />
      </div>
      <div className="mt-4">
        <ChipSkeletons form={FORM} />
      </div>
    </section>
  );
}

// An editor as its popover shows it, in the popover's frame.
function Editor({ pkg, target, preview = false }: { pkg: PlannedPackage; target: FormField; preview?: boolean }) {
  const headingId = useId();
  return (
    <div role="group" aria-labelledby={headingId} className={cx(POPOVER, "w-[min(320px,calc(100vw-32px))] p-4")}>
      <EditorBody field={target} value={valueOf(pkg, target.key)} form={FORM} approximate={pkg.approximate} preview={preview} headingId={headingId} onCommit={nothing} />
    </div>
  );
}

const minutesAgo = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString();

export function packagesPage(): GalleryPage {
  return {
    slug: "planned-packages",
    current: "packages",
    sections: [
      {
        id: "chips",
        title: ps.chips,
        body: (
          <div className="flex flex-col gap-4">
            <Labeled label={ps.typed}>
              <div className="flex flex-wrap gap-2">
                <Chip pkg={RURAL} target={field("category")} />
                <Chip pkg={RURAL} target={field("estimated_amount_usd")} />
                <Chip pkg={RURAL} target={field("method")} />
              </div>
            </Labeled>
            <Labeled label={ps.computed}>
              <div className="flex flex-wrap gap-2">
                <Chip pkg={RURAL} target={field("market_approach")} />
                <Chip pkg={RURAL} target={field("review_type")} />
              </div>
            </Labeled>
            <Labeled label={ps.guess}>
              <div className="flex flex-wrap gap-2">
                <Chip pkg={RURAL} target={field("lots")} />
              </div>
            </Labeled>
            <Labeled label={ps.empty}>
              <div className="flex flex-wrap gap-2">
                <Chip pkg={RURAL} target={field("plan_months")} />
                <Chip pkg={YOURSELF} target={field("category")} />
              </div>
            </Labeled>
            <Labeled label={ps.plan}>
              <div className="flex flex-wrap gap-2">
                <Chip pkg={PLANNED} target={field("plan_months")} />
              </div>
            </Labeled>
            <Labeled label={ps.open}>
              <div className="flex flex-wrap gap-2">
                <Chip pkg={RURAL} target={field("method")} open />
              </div>
            </Labeled>
          </div>
        ),
      },
      {
        id: "card",
        title: ps.card,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={ps.withGuess}>
              <Column>
                <UnderstoodCard pkg={RURAL} />
              </Column>
            </Labeled>
            <Labeled label={ps.recomputed}>
              <Column>
                <UnderstoodCard pkg={AMOUNT} />
              </Column>
            </Labeled>
            <Labeled label={ps.setByYou}>
              <Column>
                <UnderstoodCard pkg={REVIEW_POST} />
              </Column>
            </Labeled>
            <Labeled label={ps.dividing}>
              <Column>
                <UnderstoodCard pkg={DIVIDING} />
              </Column>
            </Labeled>
            <Labeled label={ps.nothingRead}>
              <Column>
                <UnderstoodCard pkg={YOURSELF} />
              </Column>
            </Labeled>
            <Labeled label={ps.reading}>
              <Column>
                <ReadingCard />
              </Column>
            </Labeled>
          </div>
        ),
      },
      {
        id: "editors",
        title: ps.editors,
        body: (
          <div className="flex flex-wrap items-start gap-6">
            <Labeled label={ps.choice}>
              <Editor pkg={RURAL} target={field("review_type")} />
            </Labeled>
            <Labeled label={ps.method}>
              <Editor pkg={RURAL} target={field("method")} />
            </Labeled>
            <Labeled label={ps.amount}>
              <Editor pkg={RURAL} target={field("estimated_amount_usd")} />
            </Labeled>
            <Labeled label={ps.count}>
              <Editor pkg={RURAL} target={field("lots")} />
            </Labeled>
            <Labeled label={ps.country}>
              <Editor pkg={RURAL} target={field("country")} />
            </Labeled>
            <Labeled label={ps.months}>
              <Editor pkg={PLANNED} target={field("plan_months")} />
            </Labeled>
            <Labeled label={ps.editorPreview}>
              <Editor pkg={RURAL} target={field("method")} preview />
            </Labeled>
          </div>
        ),
      },
      {
        id: "stamp",
        title: ps.stamp,
        body: (
          <div className="flex flex-col gap-3">
            <Labeled label={ps.unsaved}>
              <SavedStamp saving={{ status: "unsaved" }} preview={false} />
            </Labeled>
            <Labeled label={ps.saving}>
              <SavedStamp saving={{ status: "saving" }} preview={false} />
            </Labeled>
            <Labeled label={ps.justNow}>
              <SavedStamp saving={{ status: "saved", at: minutesAgo(0) }} preview={false} />
            </Labeled>
            <Labeled label={ps.minutes}>
              <SavedStamp saving={{ status: "saved", at: minutesAgo(5) }} preview={false} />
            </Labeled>
            <Labeled label={ps.earlier}>
              <SavedStamp saving={{ status: "saved", at: RURAL.saved_at }} preview={false} />
            </Labeled>
            <Labeled label={ps.failed}>
              <SavedStamp saving={{ status: "failed" }} preview={false} onRetry={nothing} />
            </Labeled>
            <Labeled label={ps.preview}>
              <SavedStamp saving={{ status: "saved", at: RURAL.saved_at }} preview />
            </Labeled>
          </div>
        ),
      },
      {
        id: "prompt",
        title: ps.prompt,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={ps.primary}>
              <Column>
                <PlanPrompt result={RESULT} maxMonths={FORM.max_months} preview={false} onPlan={nothing} onWithout={nothing} />
              </Column>
            </Labeled>
            <Labeled label={ps.secondary}>
              <Column>
                <PlanPrompt result={RESULT} maxMonths={FORM.max_months} preview={false} onPlan={nothing} onWithout={nothing} showRangeVariant="secondary" />
              </Column>
            </Labeled>
            <Labeled label={ps.promptPreview}>
              <Column>
                <PlanPrompt result={RESULT} maxMonths={FORM.max_months} preview onPlan={nothing} onWithout={nothing} />
              </Column>
            </Labeled>
          </div>
        ),
      },
      {
        id: "records",
        title: ps.records,
        body: (
          <div className="flex flex-wrap items-start gap-6">
            <Labeled label={ps.signed}>
              <div className="max-w-[36rem]">
                <ComparableRecords evidence={signed as unknown as EvidenceEvent} />
              </div>
            </Labeled>
            <Labeled label={ps.stillOpen}>
              <div className="max-w-[36rem]">
                <ComparableRecords evidence={stillOpen as unknown as EvidenceEvent} />
              </div>
            </Labeled>
          </div>
        ),
      },
      {
        id: "list",
        title: ps.list,
        body: (
          <div className="flex flex-col gap-8">
            <Labeled label={ps.listReady}>
              <PackagesList load={{ status: "ready", data: list as unknown as PlannedList, afterRetry: false }} onRetry={nothing} />
            </Labeled>
            <Labeled label={ps.listEmpty}>
              <PackagesList load={{ status: "ready", data: emptyList as unknown as PlannedList, afterRetry: false }} onRetry={nothing} />
            </Labeled>
            <Labeled label={ps.listLoading}>
              <PackagesList load={{ status: "loading", slow: false }} onRetry={nothing} />
            </Labeled>
            <Labeled label={ps.listError}>
              <PackagesList load={{ status: "error", error: null, retrying: false, attempt: 0 }} onRetry={nothing} />
            </Labeled>
          </div>
        ),
      },
    ],
  };
}
