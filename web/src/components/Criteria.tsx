// The "What I understood" card of a package planned from a sentence (the 15 brief, sections 4, 5 and 7.4):
// the sentence the person wrote, then what Strata read from it as criterion chips in three groups (What,
// Where, How), then the computed note with its source line. Nothing here names a field: each chip is one
// field of the package form schema (config/package_form.toml), drawn in its group and order by its kind, so
// adding a field to the schema adds a chip and removing it removes the chip.
//
// A chip is a 32 px pill whose state is in its words, never only its look (DESIGN.md section 10): a typed
// value as itself, a computed one ending " · computed", a guess ending " · guess" with a dashed border, and an
// empty field as "Add {field}" with a plus. Choosing a chip opens its editor: a popover from a window of 768
// px, a bottom sheet below that (ChipEditor.tsx).
import { useId, type ReactNode, type Ref } from "react";
import { Plus } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatAmountText, formatCount, formatNumber } from "../lib/format";
import type { FieldValue, FormField, PackageForm, PlannedPackage } from "../lib/packages";
import { Alert } from "./Alert";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { Skeleton } from "./Skeleton";
import { Source } from "./Source";

const words = copy.packageWorkspace;

// A plan's months as a chip writes them: whole months bare, half months with their decimal.
export const monthsText = (months: number) => formatNumber(months, { decimals: Number.isInteger(months) ? 0 : 1, compact: false });

// A value in the chip's words: an option's label, a country's name as the World Bank lists it, an amount
// as "US$15 million" ("About US$15 million" when the sentence said about), a count with its unit.
export function valueText(field: FormField, value: string | number | null, form: PackageForm, approximate = false): string {
  if (value === null) return field.add_label;
  if (field.kind === "choice") return field.options.find((option) => option.value === value)?.label ?? String(value);
  if (field.kind === "amount") {
    const amount = formatAmountText(Number(value));
    return approximate ? words.chip.amountAbout(amount) : words.chip.amount(amount);
  }
  if (field.kind === "count") {
    const count = Number(value);
    return words.chip.count(formatNumber(count, { compact: false }), (count === 1 ? field.unit_one : field.unit) ?? "");
  }
  if (field.kind === "country") return form.countries.find((country) => country.code === value)?.name ?? String(value);
  if (field.kind === "months") return monthsText(Number(value));
  return String(value);
}

// STEP's value word for word, for the editor's STEP line: a choice's own value, an amount with its cents.
export function stepValue(field: FormField, value: string | number | null): string | null {
  if (value === null || !field.step_field) return null;
  if (field.kind === "amount") return formatNumber(Number(value), { decimals: 2, compact: false });
  return String(value);
}

type Look = "typed" | "computed" | "guess" | "empty";

export function lookOf(value: FieldValue): Look {
  if (value.value === null) return "empty";
  if (value.provenance === "computed") return "computed";
  if (value.provenance === "guess") return "guess";
  return "typed";
}

// The words a chip shows, which are also its accessible name (WCAG 2.5.3).
export function chipWords(field: FormField, value: FieldValue, form: PackageForm, approximate: boolean): ReactNode {
  const look = lookOf(value);
  if (look === "empty") return field.add_label;
  const text = valueText(field, value.value, form, field.kind === "amount" && approximate);
  if (field.kind === "months") {
    return <Fill template={words.chip.plan} slots={{ yours: <span className="font-semibold">{words.chip.planYours}</span>, months: text }} />;
  }
  if (look === "computed") return words.chip.computed(text);
  if (look === "guess") return words.chip.guess(text);
  return text;
}

const LOOKS: Record<Look, string> = {
  typed: "border-line-strong bg-surface text-ink hover:bg-tint-hover",
  computed: "border-info-icon bg-tint text-info hover:border-primary",
  guess: "border-dashed border-info-icon bg-info-bg text-info hover:border-primary",
  empty: "border-line-strong bg-surface text-primary hover:bg-tint-hover",
};

export function CriterionChip({
  field,
  value,
  form,
  approximate,
  open,
  buttonRef,
  onChoose,
  ...trigger
}: {
  field: FormField;
  value: FieldValue;
  form: PackageForm;
  approximate: boolean;
  open: boolean;
  buttonRef?: Ref<HTMLButtonElement>;
  onChoose?: () => void;
} & Record<`data-${string}` | `aria-${string}`, string | boolean | undefined>) {
  const descriptionId = useId();
  const look = lookOf(value);
  const from = value.value === null ? words.chip.from.empty : words.chip.from[value.provenance ?? "sentence"];
  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-describedby={descriptionId}
        data-chip={field.key}
        data-look={look}
        onClick={onChoose}
        {...trigger}
        className={cx(
          "inline-flex min-h-8 max-w-full items-center gap-1 rounded-pill border px-3 py-1 text-left text-small transition-paint duration-150",
          LOOKS[look],
          open && "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]",
        )}
      >
        {look === "empty" && <Plus aria-hidden="true" className="size-4 shrink-0" />}
        <span className="min-w-0 wrap-break-word">{chipWords(field, value, form, approximate)}</span>
      </button>
      <span id={descriptionId} hidden>
        {words.chip.described(field.label, from)}
      </span>
    </>
  );
}

// The card's groups: a 64 px label column and chips that wrap beside it from a page area of 768 px, the label
// above its chips below that. Each group is a role="group" with its longer name, so a screen reader never
// takes the chip group "What" for the What stratum.
export function ChipGroups({ form, chip }: { form: PackageForm; chip: (field: FormField) => ReactNode }) {
  return (
    <div className="flex flex-col gap-3" data-chip-groups>
      {form.groups.map((group) => {
        const fields = form.fields.filter((field) => field.group === group.key);
        if (fields.length === 0) return null;
        return (
          <div key={group.key} role="group" aria-label={group.name} data-group={group.key} className="grid gap-x-3 gap-y-2 @md/page:grid-cols-[64px_1fr]">
            <p aria-hidden="true" className="flex text-label text-ink-muted @md/page:min-h-8 @md/page:items-center @md/page:self-start">
              {group.label}
            </p>
            <div className="flex min-w-0 flex-wrap gap-2">{fields.map((field) => chip(field))}</div>
          </div>
        );
      })}
    </div>
  );
}

// The chips while the sentence is read: static surface-2 pills at the brief's fixed widths, under the labels.
const SKELETON_WIDTHS: Record<string, string[]> = {
  what: ["w-24", "w-28", "w-40", "w-20"],
  where: ["w-18"],
  how: ["w-44", "w-50", "w-46", "w-36", "w-38"],
};

export function ChipSkeletons({ form }: { form: PackageForm | null }) {
  const groups = form?.groups ?? [];
  return (
    <div aria-hidden="true" className="flex flex-col gap-3" data-chip-skeletons>
      {(groups.length ? groups : [{ key: "what", label: "" }, { key: "where", label: "" }, { key: "how", label: "" }]).map((group) => (
        <div key={group.key} className="grid gap-x-3 gap-y-2 @md/page:grid-cols-[64px_1fr]">
          <p className="flex text-label text-ink-muted @md/page:min-h-8 @md/page:items-center @md/page:self-start">{group.label}</p>
          <div className="flex flex-wrap gap-2">
            {(SKELETON_WIDTHS[group.key] ?? ["w-24", "w-32"]).map((width, index) => (
              <Skeleton key={index} className={cx("h-8", width)} radius="rounded-pill" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

const lower = (text: string) => text.charAt(0).toLowerCase() + text.slice(1);

// A computed field's rule as the note's second line states it, in plain text with its threshold, for the chip
// editor's provenance (the 15 brief, section 7.6): "Works of US$10 million or more go to prior review."
export function ruleSentence(field: FormField, pkg: PlannedPackage, form: PackageForm): ReactNode {
  const n = words.note;
  const named = (key: string, value: string) => {
    const found = form.fields.find((one) => one.key === key);
    return found ? valueText(found, value, form) : value;
  };
  if (field.rule === "review" && pkg.rules.review) {
    const rule = pkg.rules.review;
    return <Fill template={n.review} slots={{ category: named("category", rule.category), threshold: n.threshold(formatAmountText(rule.threshold_usd)) }} />;
  }
  if (field.rule === "market_approach" && pkg.rules.market_approach) {
    const rule = pkg.rules.market_approach;
    return (
      <Fill
        template={n.market}
        slots={{ country: named("country", rule.country), category: lower(named("category", rule.category)), threshold: n.threshold(formatAmountText(rule.threshold_usd)) }}
      />
    );
  }
  return null;
}

// The computed note under the chips (the 15 brief, section 7.4), in its order: what a recompute changed, the
// rules and their thresholds from the thresholds file, the risk rating assumed, each computed field the person
// set themselves, then the source line.
// In a panel's foot strip, the strip gives it its place, so it takes no margin of its own (inStrip).
export function ComputedNote({ pkg, form, inStrip = false }: { pkg: PlannedPackage; form: PackageForm; inStrip?: boolean }) {
  const n = words.note;
  const field = (key: string) => form.fields.find((one) => one.key === key);
  const text = (key: string, value: string | number | null) => {
    const found = field(key);
    return found ? valueText(found, value, form) : String(value ?? "");
  };
  const review = pkg.rules.review;
  const market = pkg.rules.market_approach;
  const category = (value: string) => {
    const found = field("category");
    return found ? valueText(found, value, form) : value;
  };
  // The amount is written with its "US$", so the two never split across lines and the check's underline
  // covers both.
  const threshold = (amount: number, entry: string, source: string) => (
    <Num written={n.threshold(formatAmountText(amount))} check={{ tooltip: n.thresholdTip(entry, source) }} inCaption />
  );
  const yours = pkg.fields.filter((value) => field(value.key)?.source === "computed" && value.provenance === "you" && value.computed !== null);
  const sources = [review, market].filter((rule): rule is NonNullable<typeof rule> => Boolean(rule));
  return (
    <div className={cx("flex flex-col gap-1 text-caption text-ink-muted", !inStrip && "mt-4")} data-computed-note>
      {pkg.changed.map((change) => (
        <p key={change.field} data-recomputed className="text-ink">
          {change.to === null
            ? n.emptied(field(change.field)?.label ?? change.field, lower(field(change.cause)?.label ?? change.cause))
            : n.changed(field(change.field)?.label ?? change.field, text(change.field, change.from), text(change.field, change.to),
                lower(field(change.cause)?.label ?? change.cause))}
        </p>
      ))}
      {review || market ? (
        <p data-numbers>
          {/* Says only what I computed: both, or the one the thresholds give (ticket 58). */}
          {review && market ? n.intro : review ? n.introReview : n.introMarket}{" "}
          {review && (
            <>
              <Fill
                template={n.review}
                slots={{
                  category: category(review.category),
                  threshold: threshold(review.threshold_usd, `review.prior_from_usd.${review.risk_rating}`, review.source),
                }}
              />{" "}
            </>
          )}
          {market && (
            <Fill
              template={n.market}
              slots={{
                country: text("country", market.country),
                category: lower(category(market.category)),
                threshold: threshold(market.threshold_usd, `market_approach.international_from_usd.${market.country}`, market.source),
              }}
            />
          )}
        </p>
      ) : (
        <p>{n.noRule}</p>
      )}
      {review?.risk_rating && <p>{n.assumed(review.risk_rating)}</p>}
      {yours.map((value) => {
        const name = lower(field(value.key)?.label ?? value.key);
        // A value an old method name set, such as ICB's market approach, names what you chose (ticket 58).
        return (
          <p key={value.key} data-set-by-you>
            {value.via
              ? value.value === value.computed
                ? n.youChoseSame(value.via, name, text(value.key, value.value))
                : n.youChose(value.via, name, text(value.key, value.value), text(value.key, value.computed))
              : value.value === value.computed
                ? n.youSetSame(name, text(value.key, value.value))
                : n.youSet(name, text(value.key, value.value), text(value.key, value.computed))}
          </p>
        );
      })}
      {sources.length > 0 && (
        <Source className="mt-1">
          {sources.map((rule, index) => (
            <span key={index}>
              {index > 0 && " "}
              {rule.as_of ? (
                <Fill template={n.source} slots={{ source: rule.source, date: <Num date={rule.as_of} /> }} />
              ) : (
                <Fill template={n.sourceUndated} slots={{ source: rule.source }} />
              )}
            </span>
          ))}
        </Source>
      )}
    </div>
  );
}

// The card's top: its heading, the sentence the person wrote, and the instruction with the guess count. In a
// preview nothing can be changed, so the instruction says so instead.
// named: the card draws its own h2; in a Task zone (ticket 101) the zone's name is the heading, so it draws none.
export function CardTop({
  sentence,
  guesses,
  headingId,
  preview = false,
  named = true,
}: {
  sentence: string;
  guesses: number | null;
  headingId?: string;
  preview?: boolean;
  named?: boolean;
}) {
  return (
    <>
      {named && (
        <h2 id={headingId} className="text-h2 text-ink-heading">
          {words.card.heading}
        </h2>
      )}
      <p className={named ? "mt-2 text-small text-ink" : "text-small text-ink"} data-you-wrote>
        <span className="text-ink-muted">{words.card.youWrote}</span> {words.card.quoted(sentence)}
      </p>
      {guesses !== null && <CardInstruction guesses={guesses} preview={preview} />}
    </>
  );
}

// The instruction with the guess count, which follows the sentence: on its own where the sentence is a folded panel's
// summary (ticket 101).
export function CardInstruction({ guesses, preview = false }: { guesses: number; preview?: boolean }) {
  return (
    <p className="mt-1 text-small text-ink" data-instruction>
      {preview ? words.preview : words.card.instruction}
      {!preview && guesses > 0 && <> {words.card.guesses(guesses, formatCount(guesses, { capital: true }))}</>}
    </p>
  );
}

// The guess count alone, after the sentence in a folded What I understood, so the row keeps its one call to act while
// the chips are out of sight (ticket 101's review and design review, round 2).
export function GuessCount({ guesses }: { guesses: number }) {
  return (
    <p className="mt-1 text-small text-ink" data-guess-count>
      {words.card.guesses(guesses, formatCount(guesses, { capital: true }))}
    </p>
  );
}

export function RefusalAlert() {
  return (
    <Alert state="info" className="mt-4">
      {words.refusal}
    </Alert>
  );
}
