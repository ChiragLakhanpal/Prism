// Every string a person reads in Strata, in one place (DESIGN.md section 7), so it can be
// reviewed and translated together. Components take their words from here; the gate's string
// lint fails when a component renders text of its own, and its copy lint checks every string
// below against DESIGN.md section 7 and GLOSSARY.md (web/lint/run.ts).
//
// Strata says "I" and the reader is "you". Evidence is in the past tense, and Strata's own
// state in the present. Numbers come from tools and are written by web/src/lib/format.ts.
// The one exception: Term shows GLOSSARY.md's definitions, read by web/src/glossary.ts, so
// each definition keeps one home.

const plural = (count: number, one: string, many: string) => (count === 1 ? one : many);
// STEP spelled out, as a screen writes it the first time it names STEP (DESIGN.md section 7, rule 10).
const STEP_SPELLED = "Systematic Tracking of Exchanges in Procurement (STEP)";

export const copy = {
  appName: "Strata",
  skipLink: "Skip to main content",
  // DESIGN.md section 8, word for word.
  footer:
    "Strata is an independent demo built on World Bank open data. It is not a World Bank product, " +
    "and the World Bank has not reviewed or endorsed it.",
  // The browser tab's title: the page's h1, then the app's name.
  pageTitle: (title: string) => `${title} | Strata`,

  // Every route's title, its purpose of one or two short sentences, and its empty state (the 06 design brief, with
  // design-lead's round 1 wording for the empty states). Until a route's own ticket fills it, a
  // page reads nothing, so its empty state says what the page can't show yet and never claims
  // what the data hold: the stamp in the band may already show a date. {pid}, {stepRef} and {id}
  // come from the address and show in Roboto Mono. Each page's link goes where web/src/routes.ts
  // says; data has none, and the not-found pages have no card.
  pages: {
    home: {
      title: "Your briefing",
      purpose:
        "This page lists what changed in the plans and projects you work on, and the drafts waiting for you to " +
        "check. It comes from fixed checks on public records, and no model writes it.",
      emptyTitle: "I have nothing to brief you on yet.",
      emptyBody:
        "When my fixed checks find a change in a plan or project you work on, I list it here, with the drafts " +
        "waiting for you.",
      link: "Go to Data",
    },
    packages: {
      title: "Packages",
      purpose: "Check a borrower's Procurement Plan against comparable past packages, or plan a new package from one sentence.",
      emptyTitle: "There are no plans or packages here yet.",
      emptyBody:
        "Plans you check and packages you plan appear here, each with its reference from Systematic Tracking of " +
        "Exchanges in Procurement (STEP).",
      link: "Go to Data",
    },
    package: {
      title: "Package",
      purpose:
        "This page shows one package: the past range of comparable packages, a planned date for each step, its " +
        "risks and its approach options.",
      emptyTitle: "I can't show package {id} on this page yet.",
      emptyBody: "A package appears here after you plan it or check the plan it belongs to.",
      link: "Go to Packages",
    },
    // All projects, the project page and Check a plan have their own words below (the 10 brief):
    // these titles name the browser tab, and the purposes are the pages' own.
    projects: {
      title: "Projects",
      purpose: "These are the projects I have records for. Open a project ID to see its Procurement Plans.",
    },
    project: {
      title: "Project {pid}",
      purpose: "This page shows what I hold about one project. Each tab shows one part of it.",
    },
    checkPlan: {
      title: "Plan check, {pid}",
      purpose: "I check every activity in one implementing agency's Procurement Plan.",
    },
    activity: {
      title: "Activity {stepRef}",
      purpose: "This page traces one activity from its row in the Procurement Plan to its notice, bids and signed contract.",
      emptyTitle: "I can't trace activity {stepRef} on this page yet.",
      emptyBody:
        "When I can, this page follows the activity from its row in the Procurement Plan to its signed contract.",
      link: "Go to project {pid}",
    },
    document: {
      title: "Document",
      purpose: "This page opens one project document at the page and paragraph a citation points to.",
      emptyTitle: "I can't open this document here yet.",
      emptyBody: "When I can, each citation opens here at its paragraph and page.",
      link: "Go to project {pid}",
    },
    lessons: {
      title: "Lessons",
      purpose:
        "Each lesson comes from a completion report or its review, quoted word for word with its page. A lead " +
        "procurement specialist decides which lessons enter the library.",
      emptyTitle: "There are no lessons in the library yet.",
      emptyBody:
        "A lesson appears here after I read a completion report and a lead procurement specialist decides it belongs.",
      link: "Go to Data",
    },
    drafts: {
      title: "Drafts",
      purpose:
        "I write drafts for you to check, such as review notes and suggested rows for the borrower's Project " +
        "Procurement Strategy for Development (PPSD). Only you can mark a draft as checked or export it, and " +
        "exporting sends nothing.",
      emptyTitle: "You have no drafts to check.",
      emptyBody:
        "When you check a plan or plan a package, I can draft review notes or PPSD rows, and they wait here for you " +
        "to check.",
      link: "Go to Packages",
    },
    // The Data tab's three pages share one title and purpose, and each names itself in the browser
    // tab (the 16 design brief, section 2).
    data: {
      title: "Data",
      documentTitle: "Data readiness",
      purpose: "See how far each source can support answers, where each dataset comes from, and how I read them.",
    },
    dataSources: {
      title: "Data",
      documentTitle: "Sources and licenses",
      purpose: "See how far each source can support answers, where each dataset comes from, and how I read them.",
    },
    dataHow: {
      title: "Data",
      documentTitle: "How Strata works",
      purpose: "See how far each source can support answers, where each dataset comes from, and how I read them.",
    },
    notFound: {
      title: "Page not found",
      purpose: "I don't have a page at this address. Check the address, or go to Home.",
      link: "Go to Home",
    },
    notAProject: {
      title: "Page not found",
      purpose: "This address doesn't name a project. A project ID is the letter P followed by six digits.",
      link: "Go to Projects",
    },
  },

  // The alert slot above every page's title. Each alert is one sentence; errors come first.
  alerts: {
    noAccess: "Your account can't read the data I hold yet; ask the person who shared Strata with you for access.",
    noIdentity: "I can't tell who you are, so I can't read any data; open Strata from its link in the workspace.",
    viewPiu: "I can't show the implementing agency preview yet, so you are seeing the World Bank staff view.",
    viewPublic: "I can't show the public preview yet, so you are seeing the World Bank staff view.",
    viewUnknown: "I don't know the view in this link, so you are seeing the World Bank staff view.",
    asOf: (date: string) => `I can't show pages as of ${date} yet, so you are seeing today's data.`,
    asOfUnreadable: "I can't read the date in this link, so you are seeing today's data.",
  },

  // The navy bar (DESIGN.md section 5, Top navigation). Nouns navigate.
  nav: {
    // worldbank.org's white mark is the World Bank Group logo (web/src/assets/world-bank-logo.md).
    logo: "World Bank Group logo",
    label: "Main",
    tabs: {
      packages: "Packages",
      projects: "Projects",
      lessons: "Lessons",
      drafts: "Drafts",
      data: "Data",
    },
    menu: "Menu",
    view: {
      pill: "View: World Bank staff",
      dialog: "Your view",
      signedIn: (email: string) => `Signed in as ${email}`,
      identityError: "I can't tell which account you signed in with.",
      signedOut: "You are not signed in.",
      current: "You are seeing the World Bank staff view.",
      notReady: "Previews of what an implementing agency officer or the public sees are not ready yet.",
    },
  },

  // The white band under the bar: the one box and the data-freshness stamp.
  box: {
    label: "Search a project, check a plan, describe a package, or ask",
    placeholderWide: "Search a project, check a plan, describe a package, or ask",
    placeholderMedium: "Search a project, check a plan, or ask",
    placeholderNarrow: "Search a project, or ask",
    notReady: "I can't open projects or answer questions from this box yet.",
  },
  stamp: {
    loading: "Reading the data date",
    ready: (date: string) => `Data through ${date}`,
    empty: "No data loaded yet",
    error: "I can't read the data date.",
    // The stamp's link description. It names where the link goes and promises nothing the Data
    // page can't show yet; tickets 16 and 17 may say more once that page lists each source's date.
    description: "Open the Data page.",
  },

  loading: "Loading",
  // The bold start of every source line: under a table, a card or a passage.
  source: "Source:",

  // Status badges (DESIGN.md section 5). The word always names the state.
  badge: {
    needsALook: "Needs a look",
    watch: "Watch",
    noSignals: "No signals",
    dataNote: "Data note",
    partial: "Partial",
    gap: "Gap",
  },

  // The citation marker's accessible name, such as "Source 1: Implementation Completion and
  // Results Report, June 30, 2021, paragraph 54".
  citation: {
    name: (n: number, source: string, opened: boolean) => `Source ${n}: ${source}${opened ? ", opened" : ""}`,
  },

  // The check line (DESIGN.md section 5): neutral, and it says what was not checked.
  checkLine: {
    checked: "Checked:",
    notChecked: "Not checked:",
    numbers: (matched: string, total: number, totalText: string) =>
      plural(total, `${matched} of ${totalText} number matches records`, `${matched} of ${totalText} numbers match records`),
    quotes: (found: string, total: number, totalText: string) =>
      plural(total, `${found} of ${totalText} quote is on its page`, `${found} of ${totalText} quotes are on their pages`),
    sourcesOnly: "every source I cite came back from this search",
    notCheckedJoin: ", or ",
    clauseJoin: "; ",
    end: ".",
    notCheckedClauses: {
      sentences: "whether each sentence follows from its sources",
      comparables: "whether these are the right comparables",
      passages: "whether I found every passage that matters",
    },
  },

  // The coverage line: a sentence with its denominator, linked to Data readiness.
  coverage: {
    // "Based on {37 of 52} {matching packages}": the ratio is a Num, so it can be checked.
    // Then "; " and the gap sentence, which ends with its own period, or "." when nothing
    // was missing.
    basedOn: "Based on",
    join: "; ",
    end: ".",
    link: "See data readiness for these sources",
  },

  // The removed box: open under "In short", never behind a link.
  removed: {
    none: "I removed no sentences.",
    one: "I removed one sentence.",
    several: (count: string) => `I removed ${count} sentences.`,
    allOne: "I removed the one sentence I wrote.",
    all: (count: string) => `I removed all ${count} sentences.`,
    itSaid: (sentence: string, reason: string) => `It said ${sentence}, and ${reason}.`,
    firstSaid: (sentence: string, reason: string) => `The first said ${sentence}, and ${reason}.`,
    others: "The others:",
    item: (sentence: string, reason: string) => `"${sentence}" ${reason}`,
    // Each reason the verifier gives, keyed by its code (REASONS in src/strata/agent/verifier.py):
    // as a list item, and as the clause that follows "It said ..., and". A test fails when a code
    // lacks either.
    reasons: {
      number_not_in_records: {
        item: "No record supports this number.",
        joined: "no record supports that number",
      },
      date_not_in_records: {
        item: "No record supports this date.",
        joined: "no record supports that date",
      },
      id_not_returned: {
        item: "It cited a source I did not retrieve for this question.",
        joined: "it cited a source I did not retrieve for this question",
      },
      no_source: {
        item: "It cited no source.",
        joined: "it cited no source",
      },
      quote_not_on_page: {
        item: "The quote is not on the page it cites.",
        joined: "the quote is not on the page it cited",
      },
      quote_not_in_sentence: {
        item: "It cited a quote but did not show the quoted words.",
        joined: "it cited a quote but did not show the quoted words",
      },
    },
  },

  // Steps while an answer is built, and the answer itself.
  steps: {
    stillWorking: "I'm still working on this step.",
    show: (count: string) => `Show the ${count} steps I took`,
    showOne: "Show the step I took",
    hide: "Hide the steps",
    answerId: "Answer ID",
  },
  answer: {
    inShort: "In short",
    // Ticket 14's live region says this last, once the answer is on screen (its brief).
    ready: "The answer is ready.",
    tryAgain: "Try again",
    // Why an answer stopped, keyed by the code its stream's error event carries (ERROR_CODES in
    // src/strata/harness/turn.py). A test fails when a code has no sentence here.
    errors: {
      no_agent: "I can't answer questions yet, because the model that writes my answers isn't connected.",
      agent_unavailable: "I can't reach the model that writes my answers right now; try again in a few minutes.",
      content_filter: "A safety filter stopped this answer, so I can't show it; try asking in other words.",
      agent_output: "I wrote an answer I couldn't check, so I'm not showing it; try asking again.",
      data_service: "I can't reach the data right now, so I can't answer; try again in a few minutes.",
      internal: "Something went wrong on my side, so I can't answer; try again, and if it happens again, share the answer ID.",
    },
  },

  // Term and DefinitionWindow.
  definition: {
    close: "Close the definition",
  },

  // A document's passage, as the evidence drawer and the document page show it.
  document: {
    // The source line's words on each side of the project ID, which shows in mono:
    // "Implementation Completion and Results Report, " P000000 ", June 30, 2021, paragraph 54,
    // page 23."
    sourceLine: (docType: string, date: string, para: string, page: string) => ({
      before: `${docType}, `,
      after: `, ${date}, paragraph ${para}, page ${page}.`,
    }),
    highlightStarts: "Highlight starts.",
    highlightEnds: "Highlight ends.",
    openAtPage: (page: string) => `Open at page ${page} in the World Bank's PDF`,
    newTab: ", opens in a new tab",
    failed: "I couldn't load this source.",
    missing: "I have no source with this ID, so the link may be incomplete.",
  },

  // Tables (DESIGN.md section 5): a title sentence, a count line and a source line.
  // The title, count and source lines show only with the rows. While the rows load, skeleton
  // lines hold their places; an empty or failed table shows only its own card or alert.
  table: {
    showing: (from: string, to: string, total: string, noun: string) => `Showing ${from}–${to} of ${total} ${noun}`,
    showingAll: (total: string, noun: string) => `Showing all ${total} ${noun}`,
    showingOne: (noun: string) => `Showing 1 ${noun}`,
  },

  // A list in a sentence: "A", "A and B", or "A, B and C", with no serial comma.
  list: {
    comma: ", ",
    and: " and ",
  },
  // External links end their accessible name with this (DESIGN.md section 10).
  newTab: "(opens in a new tab)",

  // A blank STEP value. Never an em dash or an en dash.
  notInPlan: "Not in the plan",
  // A blank in a projects API record.
  notInRecord: "Not in the record",

  // The trail above a project's pages (the 10 brief, sections 2 and 3).
  breadcrumb: {
    label: "Breadcrumb",
    projects: "Projects",
    project: "{name} ({pid})",
    // While the project's name loads, or when it could not load.
    projectId: "Project {pid}",
    procurement: "Procurement",
    plan: (date: string) => `Plan of ${date}`,
  },

  // A request every page can meet: the data service did not answer, or the viewer can't read.
  service: {
    reference: "If it fails again, send the data team this reference: {reference}.",
    permissionBody: "Ask your workspace admin for read access to the strata catalog.",
  },

  // All projects (the 10 brief, section 4).
  projectsPage: {
    tableTitle: "All projects",
    noun: "projects",
    loading: "Loading projects.",
    columns: { project: "Project", country: "Country", status: "Status" },
    // The page size, from PAGE_SIZE in web/src/pages/ProjectsPage.tsx.
    more: (count: string) => `Show ${count} more`,
    source: "World Bank projects API, records through {date}.",
    sourceUndated: "World Bank projects API.",
    emptyTitle: "I don't have any project records yet.",
    emptyBody:
      "Projects appear here after the next data run reads them from the World Bank's projects API. Data readiness " +
      "shows when each source last ran.",
    emptyLink: "Data readiness",
    error: "I couldn't load the list of projects because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't list the projects.",
  },

  // A project's page and its Procurement tab (the 10 brief, section 3).
  projectPage: {
    label: { id: "Project ID", country: "Country", status: "Status", agency: "Implementing agency", agencies: "Implementing agencies" },
    // Two agency names hold commas, so the agencies are set apart with semicolons.
    agencyJoin: "; ",
    // The agencies keep to two lines; these open and close the rest.
    allAgencies: "Show all agencies",
    fewerAgencies: "Show fewer agencies",
    sections: "Project sections",
    tab: { procurement: "Procurement" },
    loading: "Loading this project.",
    error: "I couldn't load this project's Procurement Plans because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show this project.",
    notFoundTitle: "I don't have a project with the ID {pid}.",
    notFoundBody: "Check the ID, or find the project in All projects.",
    notFoundLink: "All projects",
  },
  procurement: {
    title: "Procurement Plans",
    purpose:
      "Each implementing agency keeps its own Procurement Plan and updates it. When you open a version, I check every " +
      "activity in it.",
    noun: "versions",
    nounOne: "version",
    columns: { version: "Version", disclosed: "Disclosed", activities: "Activities" },
    versionLink: (date: string) => `Plan of ${date}`,
    latest: "Latest",
    notRead: "Not read",
    unreadNote:
      "I read the latest version, the one before it and the earliest version that lists each activity. I list the " +
      "other versions but haven't read them.",
    source: "World Bank documents and reports API, Procurement Plans for {pid}, through {date}.",
    sourceUndated: "World Bank documents and reports API, Procurement Plans for {pid}.",
    agencyEmpty: "I don't have a Procurement Plan from this agency yet.",
    // Two or more agencies with no plan share one block after the agencies with plans.
    otherAgencies: "Other implementing agencies",
    othersEmpty: "I don't have a Procurement Plan from these agencies yet:",
    projectEmptyTitle: "I don't have a Procurement Plan for this project yet.",
    projectEmptyBody:
      "I can check a plan only after the World Bank discloses it and I have read it. Data readiness shows how much of " +
      "each source I have read.",
    projectEmptyLink: "Data readiness",
  },

  // Check a plan (the 10 brief, section 2). Counts are the tool's; the screen counts nothing.
  checkPlan: {
    // The plan's date, under the agency's name. {date} stays on one line.
    subtitle: "Procurement Plan of {date}",
    // The h1 when the agency's name is not known.
    agencyUnknown: "Procurement Plan",
    pill: (total: number, totalText: string) => (total === 1 ? "1 activity checked" : `${totalText} activities checked`),
    pillPartial: (checked: string, total: string) => `${checked} of ${total} activities fully checked`,
    // The finding: the first part, then the notes part, then the full stop. {look}, {watch} and
    // {notes} are the tool's counts, in words.
    finding: {
      lookAndWatch: (look: number, watch: number) =>
        `{look} ${look === 1 ? "needs" : "need"} a look and {watch} ${watch === 1 ? "is" : "are"} worth watching`,
      lookOnly: (look: number) => `{look} ${look === 1 ? "needs" : "need"} a look`,
      watchOnly: (watch: number) => `No activity needs a look, but {watch} ${watch === 1 ? "is" : "are"} worth watching`,
      none: "No activity needs a look or is worth watching",
      notes: (notes: number) => (notes === 1 ? "; {notes} has a data note" : "; {notes} have data notes"),
      end: ".",
    },
    method:
      "I checked every activity against {checks}. I measure delay from the first published planned date, because " +
      "each plan update can move the planned dates.",
    checks: {
      own_dates: "its own dates",
      estimate: "its estimate",
      closing_date: "the project's closing date",
    },
    partial: (count: number) =>
      count === 1
        ? "I couldn't fully check {count} activity; its row says why."
        : "I couldn't fully check {count} activities; their rows say why.",
    noClosingDate: "I didn't check any activity against the project's closing date, because the project record has none.",
    countLine: (shown: string, total: string) => `Showing ${shown} of ${total} activities`,
    noun: "activities",
    caption: (agency: string, date: string) => `Activities in the ${agency} plan of ${date}, marked activities first`,
    columns: {
      activity: "Activity",
      method: "Method · market approach",
      review: "Review",
      estimated: "Estimated (US$)",
      status: "Process status",
      found: "What Strata found",
    },
    // "Request for Bids · Open - National", as STEP gives the two values. The dot is tied to the
    // Method with a no-break space, so a line never starts with it.
    methodDot: "\u00a0·",
    noSignals: "No signals.",
    foundDefinition:
      "Needs a look and Watch are signals. A signal is a fixed check on public records. It gives a reason to look, " +
      "never a finding. {lookRule} {watchRule} A data note means the record is missing a value or contradicts itself.",
    // {amount} is the threshold in rule 11's text form ("1 million"), since no one looks it up in STEP.
    lookRule:
      "An activity needs a look when its planned completion passed with no signed contract. I mark it only when its " +
      "estimate is US${amount} or more, or when the plan gives no estimate.",
    watchRule:
      "An activity is worth watching when it is still pending {days} days or fewer before the project closes, or " +
      "after the project closed. It is also worth watching when it was signed at {ratio} times its estimate or more.",
    // The fold under the marked rows. Up to fold.listUpTo references are named in the sentence.
    fold: {
      listUpTo: 3,
      listed: (count: number) =>
        count === 1 ? "{count} more activity has no signals: {refs}." : "{count} more activities have no signals: {refs}.",
      counted: "{count} more activities have no signals.",
      show: (count: number) => (count === 1 ? "Show it" : "Show them"),
      hide: (count: number) => (count === 1 ? "Hide it" : "Hide them"),
    },
    notVisible:
      "Not visible to Strata: the prior-review queue, complaints, contract amendments and contract management reports. " +
      "Those stay in STEP.",
    source: {
      plan: "Procurement Plan, {agency}, {pid}, version of {date}, disclosed {disclosed}.",
      closing: "Project closing date from the World Bank's projects API, record of {date}.",
      // {date} is the date the page reads the records as of, not a date the checks ran.
      marks: "Marks from Strata's fixed checks, as of {date}.",
      open: "The plan on the World Bank's documents site",
    },
    // The visually hidden status that announces steps, not rows.
    status: {
      checking: "Checking this plan.",
      checked: (count: string) => `Checked ${count} activities.`,
      checkedOne: "Checked 1 activity.",
    },
    stillChecking: "Still checking this plan.",
    // What each number in a reason or the finding is, in its tooltip.
    explain: {
      firstPlannedSigning: "Planned signing date, as first published",
      inPlanOf: "{date}, in the plan of {plan}",
      signed: "Contract signed",
      daysBetween: "Days between them",
      actual: "Actual Amount (US$)",
      estimated: "Estimated Amount (US$)",
      divided: "Actual divided by estimated",
      closing: "Project closing date",
      closingRecord: "{date}, from the projects API record of {record}",
      asOf: "Checked as of",
      counted: "The activities I counted:",
    },
    // One sentence per reason code check_plan returns (config/tools.toml, [tools.check_plan.result]).
    reason: {
      completion_passed_no_contract: "Planned completion {date} passed with no signed contract.",
      projectCloses: "The project closes {date}.",
      projectClosed: "The project closed {date}.",
      pending_near_closing: (days: number) =>
        days === 1 ? "Still pending, {days} day before the project closes." : "Still pending, {days} days before the project closes.",
      pending_on_closing_day: "Still pending on the day the project closes.",
      pending_after_closing: "Still pending after the project closed on {date}.",
      signed_late_over_estimate: (days: number) =>
        (days === 1 ? "Signed {date}, {days} day after its planned date, " : "Signed {date}, {days} days after its planned date, ") +
        "at US${actual}, about {ratio} times its estimate.",
      signed_over_estimate: "Signed {date} at US${actual}, about {ratio} times its estimate.",
      method_differs_from_reference:
        "The reference ends in {code} ({referenceMethod}), but the Method column says {method}. I use the Method column.",
      actual_amount_zero: "{status}, but Actual Amount reads {actual}.",
      no_planned_date: "The plan gives no planned date for {step}, so I couldn't check its timing.",
      no_estimate: "The plan gives no Estimated Amount, so I couldn't compare the signed amount with it.",
    },
    // The states a plan check can end in, other than its rows (the 10 brief, section 6).
    noPlanTitle: (agency: string) => `I don't have a Procurement Plan from ${agency} yet.`,
    noPlanTitleUnnamed: "I don't have a Procurement Plan from this agency yet.",
    noPlanBody: "I can check a plan only after the World Bank discloses it and I have read it.",
    allPlans: "All Procurement Plans for this project",
    noActivitiesTitle: "I found no activities in this plan.",
    noActivitiesBody:
      "The plan may have no activity table, or I may have misread its pages. Data readiness shows how well I read the " +
      "documents from each source.",
    dataReadiness: "Data readiness",
    notFoundTitle: (date: string) => `I don't have a plan from this agency dated ${date}.`,
    notFoundBody: (date: string) => `The latest plan I have from this agency is dated ${date}.`,
    notPublicTitle: (date: string) => `I can't show this plan as of ${date}.`,
    notPublicBody: (date: string) => `The World Bank disclosed it on ${date}, after that date.`,
    noPlanAsOfTitle: (date: string) => `I have no plan from this agency that was public on ${date}.`,
    latestLink: (date: string) => `Plan of ${date}`,
    error: "I couldn't load this plan's check because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show this plan.",
  },

  // The Data readiness page (the 16 design brief). Every number on it comes from the
  // data_readiness_for tool, and the page computes none.
  dataReadiness: {
    tabs: {
      label: "Data pages",
      readiness: "Data readiness",
      sources: "Sources and licenses",
      how: "How Strata works",
    },
    // The info alert above the headline when a coverage line opened the page. The noun comes from
    // server.fromNouns, by the tool the link names, never from the link's own words.
    // Templates whose {slots} the page fills with Num, so each number keeps its form and its check.
    filtered: {
      many: "I'm showing only the {count} sources behind {fromNoun}.",
      one: "I'm showing only the source behind {fromNoun}.",
      unknown: "I didn't recognize {count} of the sources in this link.",
      noneKnown: "I couldn't find the sources this link names. They may have been renamed since the link was made.",
      showAll: "Show all sources",
    },
    provenance: "I built this from the measures below, taken {date}. No model wrote it.",
    provenanceRange: "I built this from the measures below, taken {from} to {to}. No model wrote it.",
    // Under a headline Strata doesn't give, where "this" would point at nothing.
    provenanceAbstained: "I took the measures below on {date}.",
    provenanceAbstainedRange: "I took the measures below from {from} to {to}.",
    // The source line under each table.
    sourceLine: "Strata's data readiness measures, taken {date}.",
    kinds: {
      title: "What you can ask",
      caption: "Each kind of question, what it can draw on, and what holds it back.",
      kind: "What you can ask",
      readyFor: "Ready for",
      readyForAbout: "records it can draw on",
      readyForDefinition:
        "What each kind of question can draw on, counted from the latest measures. A badge says the answers are " +
        "Partial, or that a Gap leaves nothing to draw on.",
      holds: "What holds it back",
      holdsAbout: "gaps that limit answers",
      holdsDefinition:
        "The gaps in the sources each kind of question draws on. The biggest gaps come first: the ones whose fix " +
        "would add evidence to the most projects.",
      // Each kind, by the key its tool gives in config/tools.toml, and what its number counts.
      names: {
        plan_check: "Checking a plan against its own dates",
        document_search: "What project documents say",
      } as Record<string, string>,
      // The plan check's count words STEP's format as the Procurement Plans row does.
      counts: {
        plan_check: "activity entries in the latest plan versions with rows in STEP's format",
        document_search: "passages you can search",
      } as Record<string, string>,
      // The same, for a count of one.
      countsOne: {
        plan_check: "activity entry in the latest plan versions with rows in STEP's format",
        document_search: "passage you can search",
      } as Record<string, string>,
      // A count that names STEP first on its view spells it out, when the tool marks its kind
      // spell_out: the plan check's view, and a view whose headline it leaves out (DESIGN.md
      // section 7, rule 10).
      countsSpelled: {
        plan_check: `activity entries in the latest plan versions with rows in the format of ${STEP_SPELLED}`,
      } as Record<string, string>,
      countsSpelledOne: {
        plan_check: `activity entry in the latest plan versions with rows in the format of ${STEP_SPELLED}`,
      } as Record<string, string>,
    },
    sources: {
      title: "Sources",
      showing: "Showing {shown} of {total} sources.",
      source: "Source",
      columns: {
        coverage: { label: "Coverage", about: "rows and fiscal years" },
        linked: { label: "Linked", about: "to projects and other records" },
        read_well: { label: "Read well", about: "read without errors" },
        fresh: { label: "Fresh", about: "latest data, how often" },
      },
      definitions: {
        coverage:
          "How many rows or documents I hold for this source, and which fiscal years they span. Fiscal years run " +
          "from July to June.",
        linked:
          "How many of these rows I could join to the record they need: a project, a notice, a Procurement Plan, " +
          "a sector or a borrower country. A row that doesn't join can't count in answers that need the join.",
        read_well:
          "How many pages or rows I read without losing their paragraph numbers or table rows. Records the World " +
          "Bank publishes as tables need no reading.",
        fresh:
          "The date of the latest data I fetched, and how often the source updates. A frozen source no longer changes.",
      },
      scope: {
        every_country: "All countries",
        projects: "For {count} projects",
        oneProject: "For one project",
        join: ", ",
        lastJoin: " and ",
      },
      years: "in {count} fiscal years",
      yearsOne: "in {count} fiscal year",
      yearsOf: "in {count} of {total} fiscal years",
      // What a fiscal-years count counts, in its tooltip.
      yearsNoun: "fiscal years",
      yearsNounOne: "fiscal year",
      gapYears: (from: string, to: string) => `fiscal ${from}–${to}`,
      publishedAsTable: "Published as a table",
      notMeasured: "Not measured yet",
      // A column the registry gives this row no measure for, so no run will measure it.
      noMeasure: "No measure",
      // A row with no freshness measure whose documents arrive as their authors publish them.
      asPublished: "As published",
      notMeasuredRow: "Not measured yet. The next data run measures it.",
      nonePublished: "None published",
      // A no-break space keeps the dot with the date, so a narrow cell breaks only after it:
      // "Jun 30 ·" on one line and "as published" on the next.
      fresh: "{date}\u00a0· {schedule}",
      late: "{days} days late",
      lateOne: "{days} day late",
    },
    failures: {
      title: "Plan pages the layout parser couldn't read",
      none: "The layout parser read every Procurement Plan page it tried.",
      page: "page {page}, last tried {date}",
      document: "Document",
    },
    fixes: {
      title: "Fixes that would unlock the most",
      caption: "Ranked by how many projects each fix would add evidence to.",
      projects: "Would add evidence to {count} projects.",
      oneProject: "Would add evidence to {count} project.",
      projectsNoun: "projects",
      projectsNounOne: "project",
      // With no fix to rank: the first only when nothing in view falls short, and the second (the
      // third with one source in view) when something does but the registry lists no fix for it.
      none: "Nothing I measured falls short, so there are no fixes to rank.",
      noneKnown: "I don't have a fix to suggest for these sources.",
      noneKnownOne: "I don't have a fix to suggest for this source.",
    },
    // The window a number opens, by its measure, for each measure that fills no column of the
    // Sources table: a source's checks and the measures behind its fixes (config/sources.toml). A
    // number from a column's measure opens that column's window instead. web/tests/lint.spec.ts
    // fails when a check or a fix's own measure has no entry here.
    measureWindows: {
      latest_activities_with_confirmed_first_listing_read: {
        title: "First listing confirmed",
        definition:
          "How many activity entries in the latest plan versions I could trace back to the plan version that first " +
          "listed them, and then read in that version's table. I confirm a first listing only when I have read " +
          "every older or undated plan version in the project's document list.",
      },
      projects_with_contracts_lacking_step_reference: {
        title: "Projects with contracts that lack a STEP reference",
        definition:
          "How many projects have at least one contract with no STEP reference, out of every project with a " +
          "contract in the Contract awards source.",
      },
      gap_years_contracts_in_local_currency: {
        title: "Award-notice contracts in local currency",
        definition:
          "How many contracts built from award notices, for the fiscal years no awards dataset covers, have their " +
          "amount in local currency, out of every contract built from those notices.",
      },
      gap_years_projects_in_local_currency: {
        title: "Projects with award-notice contracts in local currency",
        definition:
          "How many projects have a contract built from award notices, for the fiscal years no awards dataset " +
          "covers, whose amount is in local currency, out of the projects of every contract built from those notices.",
      },
    } as Record<string, { title: string; definition: string }>,
    loading: {
      slow: "I'm still loading the measures. The database may be starting up, which can take up to a minute.",
    },
    // DESIGN.md's Empty-state card, before the first data run.
    empty: {
      title: "I haven't measured any sources yet.",
      body: "The measures appear here after the first data run.",
      link: "See the datasets I'm set up to read",
    },
    abstain: {
      unmeasured: "I'm not giving a headline: {count} of the {total} sources below have no measures yet. Their rows say so.",
      unmeasuredOne: "I'm not giving a headline: {count} of the {total} sources below has no measures yet. Its row says so.",
      // When no source in view has measures: the second when the view holds one source.
      unmeasuredAll: "I'm not giving a headline: none of the sources below has measures yet. Their rows say so.",
      unmeasuredAllOne: "I'm not giving a headline: the source below has no measures yet. Its row says so.",
      beforeFirst: "I have no measures taken on or before {asked}. I took my first measures on {first}.",
      showToday: "Show today's measures",
    },
    errors: {
      timeout: "I couldn't load the measures, because the database didn't answer within {seconds} seconds. Try again in a minute.",
      permission:
        "I couldn't load the measures, because your account doesn't have access to them. Ask the person who runs " +
        "Strata to give your account access.",
      other:
        "I couldn't load the measures, because the server returned an error. Try again. If it fails again, tell the " +
        "person who runs Strata.",
      tryAgain: "Try again",
    },
    // Each number's tooltip and the window a click opens (the 16 brief, section 5.8).
    number: {
      ratio: (part: string, whole: string, noun: string, date: string) => `${part} of ${whole} ${noun}. Measured ${date}.`,
      count: (count: string, noun: string, date: string) => `${count} ${noun}. Measured ${date}.`,
      day: (day: string, date: string) => `The latest data are from ${day}. Measured ${date}.`,
      // A shortfall: how many of the whole lack what the gap names.
      missing: (part: string, whole: string, noun: string, lack: string, date: string) =>
        `${part} of ${whole} ${noun} lack ${lack}. Measured ${date}.`,
      missingOne: (part: string, whole: string, noun: string, lack: string, date: string) =>
        `${part} of ${whole} ${noun} lacks ${lack}. Measured ${date}.`,
      kinds: "Counted from the table of what you can ask, below.",
      sources: "Counted from the rows of the Sources table below.",
      moreGaps: "Counted from the gaps listed under Sources, below.",
      // A fix's project count that no measure counted: the projects whose rows fall short.
      projects: (count: string, date: string) => `The records behind this gap come from ${count} projects. Measured ${date}.`,
      projectsOne: (count: string, date: string) => `The records behind this gap come from ${count} project. Measured ${date}.`,
      // A number the reader clicked that is neither the measure's count nor its denominator.
      missingLabel: "Missing",
      days: "Days late",
      numerator: "Counted",
      denominator: "Out of",
      measured: "Measured",
      countedIn: "Counted in",
      latest: "Latest data",
    },
    // The Sources and licenses page (the 16 brief, section 7). Dataset names come only from the
    // source registry; DESIGN.md section 8 gives every fixed sentence here word for word.
    sourcesPage: {
      lead: "Here is every dataset and document I use, credited the way the World Bank asks.",
      datasets: "Datasets",
      datasetCount: "{count} datasets.",
      attribution: { before: "The World Bank: ", after: (source: string, license: string) => `: ${source}. License: ${license}.` },
      documents: "Documents and rules",
      collection: (name: string, publisher: string, origin: string) => `${name}, published by ${publisher}, from ${origin}.`,
      authorizes: {
        before: "The World Bank Group authorizes the use of this material subject to the terms and conditions on its website, ",
        link: "Legal",
        after: ".",
      },
      terms: { before: "Terms of use: ", link: "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets" },
      changes: "Strata joined these records, read the documents, and summarized them. These changes are Strata's own.",
      caveat: "The World Bank does not guarantee the accuracy of the data.",
      empty: "I haven't been set up to read any datasets yet.",
      emptyBody: "Each dataset appears here, credited the way the World Bank asks, once I'm set up to read it.",
      failed: "I couldn't load the list of sources, because the server didn't answer. Try again.",
    },
    howPage: {
      lead:
        "This page is for the figures that show how I turn World Bank records and documents into cited answers. They " +
        "are not drawn yet.",
      next: {
        before: "Until they are, ",
        readiness: "Data readiness",
        middle: " shows what each source covers, and ",
        sources: "Sources and licenses",
        after: " lists every dataset I use.",
      },
    },
    // The sentences the tool builds on the server: the headline, the gaps and what holds each kind
    // of question back. src/strata/tools/data_readiness_for.py fills each {slot} from the measures
    // and reads these words from src/strata/tools/data_readiness_copy.json, which
    // `node web/lint/server-copy.ts --write` writes from this object. The lint lane fails when that
    // file is out of date, so the words have one home. No model writes these sentences.
    server: {
      kinds: "Of the {kindCount} kinds of question below, I can answer {clauses}.",
      kindsAllFull: "I can answer all {kindCount} kinds of question below in full.",
      kindsAllPartial: "I can answer each of the {kindCount} kinds of question below in part.",
      kindsAllGap: "I can't answer any of the {kindCount} kinds of question below yet.",
      kindsOne: "I can answer the one kind of question below {clause}.",
      clauseFull: "{n} in full",
      clausePart: "{n} in part",
      clauseNone: "{n} not at all",
      oneFull: "in full",
      onePart: "in part",
      oneNone: "not at all",
      clauseJoin: ", ",
      clauseLastJoin: " and ",
      gapsTwo: "The biggest gaps are {gap1} and {gap2}.",
      gapsOne: "The biggest gap is {gap1}.",
      gapsNone: "Nothing I measured holds these answers back.",
      filteredOne: "One source is behind {fromNoun}.",
      filteredFew: "{SourceCount} sources are behind {fromNoun}.",
      filteredMany: "The {sourceCount} sources below are behind {fromNoun}.",
      // What holds a kind of question back: its top two gaps, each as a sentence, then how many more.
      moreOne: "I list one more gap under Sources.",
      more: "I list {n} more gaps under Sources.",
      nothingHolds: "Nothing I measured holds it back.",
      // The gap phrases, by what kind of gap it is. A shortfall has a form for one record short
      // (One), for every record short (All) and for the only record, which falls short (Only); the
      // tool uses a form only when holds has it too, and otherwise the plain form.
      gap: {
        published: "the {sourceNoun} for fiscal {fromYear} to {toYear}, which no World Bank dataset publishes",
        linked: "the {missing} of {total} {noun} that lack {lack}",
        linkedOne: "the {missing} of {total} {noun} that lacks {lack}",
        linkedAll: "the {total} {noun}, none of which has {lack}",
        linkedOnly: "the {total} {noun} that lacks {lack}",
        check: "the {missing} of {total} {noun} that lack {lack}",
        checkOne: "the {missing} of {total} {noun} that lacks {lack}",
        checkAll: "the {total} {noun}, none of which has {lack}",
        checkOnly: "the {total} {noun} that lacks {lack}",
        readWell: "the {missing} of {total} {noun} I couldn't read without errors",
        late: "the {sourceNoun}, last fetched {date}, {days} days behind their {schedule} update",
        lateOneDay: "the {sourceNoun}, last fetched {date}, one day behind their {schedule} update",
        declared: "the {sourceNoun}, which cover {note}",
        noRows: "the {sourceNoun}, of which I hold no rows yet",
      },
      // The same gaps as full sentences, under "What holds it back", filled from the same slots.
      holds: {
        published: "No World Bank dataset publishes the {sourceNoun} for fiscal {fromYear} to {toYear}.",
        linked: "Of {total} {noun}, {missing} lack {lack}.",
        linkedOne: "Of {total} {noun}, {missing} lacks {lack}.",
        linkedAll: "None of the {total} {noun} has {lack}.",
        linkedOnly: "The {total} {noun} lacks {lack}.",
        check: "Of {total} {noun}, {missing} lack {lack}.",
        checkOne: "Of {total} {noun}, {missing} lacks {lack}.",
        checkAll: "None of the {total} {noun} has {lack}.",
        checkOnly: "The {total} {noun} lacks {lack}.",
        readWell: "I couldn't read {missing} of {total} {noun} without errors.",
        late: "I last fetched the {sourceNoun} on {date}, {days} days behind their {schedule} update.",
        lateOneDay: "I last fetched the {sourceNoun} on {date}, one day behind their {schedule} update.",
        declared: "The {sourceNoun} cover {note}.",
        noRows: "I hold no rows of the {sourceNoun} yet.",
      },
      // STEP spelled out (DESIGN.md section 7, rule 10). A kind's count spells STEP out only when the
      // headline above it doesn't already hold these words (kinds.countsSpelled).
      stepSpelled: STEP_SPELLED,
      // What a late source's count of days counts, in its tooltip.
      daysLate: "days late",
      dayLate: "day late",
      // The coverage line a reader opened the page from, by the tool that wrote it. The page never
      // shows words from its address.
      fromNouns: {
        find_comparables: "the past range",
        check_plan: "the plan check",
        search_passages: "the document search",
        ask: "the answer",
        unknown: "the coverage line you opened",
      },
      // How often each source updates, as its registry cadence or a readiness row's schedule says.
      schedules: {
        daily: "daily",
        weekly: "weekly",
        monthly: "monthly",
        quarterly: "quarterly",
        yearly: "yearly",
        frozen: "frozen",
        "as published": "as published",
      },
      months: [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
      ],
      // The dashboard's Data readiness page (the 16 design brief, section 10), which
      // src/strata/dashboard builds from code. Each chart's title names what it measures and never
      // states a number, because a title is fixed when the dashboard is deployed; the day's finding
      // is the headline in its own tile. DESIGN.md section 6 records why.
      dashboard: {
        name: "Strata",
        page: "Data readiness",
        introHeading: "Data readiness",
        intro:
          "How fit each source is to support answers. These are the same measures as the Data readiness page in " +
          "Strata. Pick a measure date to compare the two.",
        measureDate: "Measure date",
        measureDateAbout: "Every tile shows the newest measures taken on or before this date. It starts on today's date.",
        headline: "What the measures say",
        headlineAbout: "The day's headline, written by the same code as the Data readiness page in Strata.",
        measuredOn: "Measured on",
        headlineColumn: "Headline",
        awardRows: "Contract-award rows per fiscal year, by dataset",
        awardRowsAbout:
          "Rows per fiscal year. Each awards dataset's rows are counted as the Coverage column in Strata counts " +
          "them, one for each joint-venture member. The award notices for fiscal 2017 to 2019 count one row for " +
          "each contract, because Strata shows those years as a Gap with no count. A missing bar means no rows.",
        fiscalYear: "Fiscal year",
        rows: "Rows",
        dataset: "Dataset",
        sourceRows: "Rows per fiscal year, by source",
        sourceRowsAbout:
          "Rows in each fiscal year for the contract awards, the procurement notices, the projects and the " +
          "Independent Evaluation Group (IEG) ratings, with exact counts. Each source's rows are counted as its " +
          "Coverage column in Strata counts them, so its years add up to that number on the same date. The award " +
          "notices for fiscal 2017 to 2019 count one row for each contract. It is the table for the chart of " +
          "contract-award rows.",
        source: "Source",
        links: "Share of rows that link, by link",
        // {fewest} is config/thresholds.toml's data_readiness.fewest_for_a_percentage, filled in when
        // src/strata/dashboard writes the dashboard file.
        linksAbout:
          "Each link with {fewest} rows or more, as the share of its rows that link. The table of freshness and " +
          "link counts lists every link with its counts.",
        link: "Link",
        share: "Share (%)",
        routes: "Share of pages read well, by route",
        routesAbout:
          "Each reading route with {fewest} Procurement Plan pages or more, as the share of its pages it read " +
          "without losing their table rows.",
        route: "Route",
        freshness: "Freshness, links and pages read well, by source",
        freshnessAbout:
          "Each source's latest data, how often it updates, how late it is, its link counts and its status. The " +
          "last rows give the Procurement Plan pages each reading route read well. It is the table for the two " +
          "charts of shares.",
        latestData: "Latest data",
        updates: "Updates",
        daysLate: "Days late",
        linked: "Linked",
        readWell: "Read well",
        status: "Status",
        fixes: "Fixes ranked by what they would unlock",
        fixesAbout: "Ranked by how many projects each fix would add evidence to, as on the Data readiness page.",
        rank: "Rank",
        fix: "Fix",
        projects: "Projects it would add evidence to",
        notes: "Source: Strata's data readiness measures in strata.ops.",
        // What each dataset is, by its name in src/strata/dashboard, as AI/BI shows it in its data panel.
        datasets: {
          readiness_headline: "The day's headline",
          award_rows_by_year: "Contract-award rows per fiscal year",
          rows_by_year: "Rows per fiscal year, by source",
          readiness_links: "Shares of rows that link",
          readiness_routes: "Shares of pages read well",
          readiness_sources: "Freshness, links and pages read well",
          readiness_fixes: "Fixes",
        } as Record<string, string>,
        // The rows of the chart and the table of rows per fiscal year, in their order: each source by
        // its key in config/sources.toml, and a known gap by its id. The snapshot counts each source's
        // rows as its Coverage cell counts them (strata.dashboard.snapshot), and the table of freshness
        // and links names the awards datasets with these same labels.
        years: {
          awards: "Contract awards, since FY2020",
          awards_fy2001_2016: "Contract awards, FY2001–16",
          fy2017_2019: "Award notices, FY2017–19",
          notices: "Procurement notices",
          projects: "Projects",
          ieg_ratings: "IEG ratings",
        } as Record<string, string>,
        // A fiscal year as the dashboard writes it, with its last two digits, such as FY20, and the
        // column for rows with none.
        fiscalYearLabel: "FY{year}",
        noYear: "No fiscal year",
        // The snapshot's row names: a source with what its rows span, a known gap, and a link.
        sourceLabel: "{label}, {covers}",
        gapLabel: "{label}, FY{fromYear}–{toYear}",
        linkLabel: "{label}: {counts}",
        // A link's counts in the table of freshness and link counts, in numerals, as tables write them.
        linkedCount: "{count} of {denominator}",
      },
    },
  },

  // Words for numbers (DESIGN.md section 7, rules 6, 11, 12 and 15). web/src/lib/format.ts
  // decides which one a number gets.
  num: {
    words: ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine"],
    of: (part: string, whole: string) => `${part} of ${whole}`,
    inTen: (n: number) => `${n} in 10`,
    aboutInTen: (n: number) => `about ${n} in 10`,
    fewerThanOneInTen: "fewer than 1 in 10",
    moreThanNineInTen: "more than 9 in 10",
    percent: (n: number) => `${n} percent`,
    percentShort: (n: number) => `${n}%`,
    // A share that rounds to 0 or 100 but is neither.
    underOnePercent: "less than 1 percent",
    underOnePercentShort: "<1%",
    overNinetyNinePercent: "more than 99 percent",
    overNinetyNinePercentShort: ">99%",
    countWithFrequency: (count: string, frequency: string) => `${count}, ${frequency}`,
    // An amount in a sentence (rule 11): "12.5 million", "2 billion".
    million: (n: string) => `${n} million`,
    billion: (n: string) => `${n} billion`,
  },
} as const;
