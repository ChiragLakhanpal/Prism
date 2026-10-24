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
    // The package workspace has its own words below (the 12 brief); this title names the browser tab.
    package: {
      title: "Package {id}",
      purpose: "This page shows how comparable packages went, so you can judge whether this package's plan is realistic.",
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
    data: {
      title: "Data",
      purpose:
        "This page shows what the data I hold are ready for, where each source comes from and its license. It also " +
        "explains how I turn records and documents into answers.",
      emptyTitle: "I can't show data readiness on this page yet.",
      emptyBody:
        "When I can, this page shows what each source is ready for, how complete and fresh it is, and its license. " +
        "The date at the top of every page says how recent the data I hold are.",
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
    // Each activity's link to its package workspace (the 12 brief). Its accessible name adds the
    // reference, so a list of links tells the activities apart.
    pastRangeLink: "See the past range",
    pastRangeLabel: (ref: string) => `See the past range for ${ref}`,
  },

  // The package workspace's frame (the 12 brief): the header, the package's facts in STEP's field
  // names, and the states of the whole page.
  packagePage: {
    breadcrumbPackages: "Packages",
    facts: {
      method: "Method",
      marketApproach: "Market Approach",
      reviewType: "Review Type",
      estimated: "Estimated Amount (US$)",
      processStatus: "Process Status",
      inPlan: "In the plan",
    },
    // The "In the plan" value, a link back to the plan check with this row in view.
    inPlan: "{agency} plan of {date}",
    missing: "Not in the plan row",
    loading: "Loading this package.",
    error: "I couldn't load this package.",
    permission: "Your account can't read Strata's tables, so I can't show this package.",
    notFoundTitle: "I can't find a package with this reference",
    notFoundBody: "No package in Strata has the reference {ref}. Check the reference in STEP, or find its project in All projects.",
    notFoundLink: "All projects",
  },

  // Section 1 of the package workspace, "How long it took": the past range of comparable packages
  // (the 12 brief). Every number is find_comparables', written by web/src/lib/format.ts; the screen
  // only counts rows for the plan line's readout. Strings with {slots} are filled with Num elements.
  pastRange: {
    eyebrow: "Planning",
    // Hidden from screen readers, so the heading reads "How long it took".
    number: "1 ·",
    heading: "How long it took",
    loading: "Loading the comparable packages.",
    error: "I couldn't load the comparable packages for this section.",
    permission: "Your account can't read Strata's tables, so I can't show the comparable packages.",
    // The finding, at the plan row's own months.
    title: {
      about: "{within} of {total} comparable packages, about {in10} in 10, were signed within the plan's {plan} months.",
      none: "None of the {total} comparable packages were signed within the plan's {plan} months.",
      all: "All {total} comparable packages were signed within the plan's {plan} months.",
      fewerThanOne: "{within} of {total} comparable packages, fewer than 1 in 10, were signed within the plan's {plan} months.",
      moreThanNine: "{within} of {total} comparable packages, more than 9 in 10, were signed within the plan's {plan} months.",
      noPlan: "The middle half of the {total} comparable packages took {q25} to {q75} months from notice to signature.",
      noPlanNoRange: "I found {total} comparable packages, but so many are still open that I can't place their middle half.",
      abstain: "I'm not giving a range: only {n} comparable packages. Here are all {n}.",
      abstainOne: "I'm not giving a range: only one comparable package. Here it is.",
    },
    subtitle: "Each dot is one package, placed by the months from its specific procurement notice to its signed contract.",
    subtitleDots:
      "Each dot is 1 in 20 of the {total} packages, placed by the months from specific procurement notice to signed contract.",
    summary: {
      middle: "The middle half of these packages took {q25} to {q75} months, and the middle one took {q50}.",
      in10: "8 in 10 were signed within {q80} months.",
      noIn10: "Fewer than 8 in 10 of these packages have been signed so far, so I can't say when 8 in 10 were signed.",
      noUpper: "So many of these packages are still open that I can't place the upper edge of the middle half.",
      openMany: "{open} of the {total} are still open. I kept them in the range as not signed yet, so the range does not look shorter than it was.",
      openOne: "One of the {total} is still open. I kept it in the range as not signed yet, so the range does not look shorter than it was.",
      abstain: "I give a range only from {min} or more comparable packages, because a range from fewer can mislead. Each dot is one real package, and the table lists them all.",
      abstainOpenMany: "{open} of them are still open.",
      abstainOpenOne: "One of them is still open.",
    },
    // The note on what "comparable" meant: the criteria find_comparables used.
    note: {
      label: "Note:",
      same: "I compared packages with the same {fields}.",
      they: "They {parts}.",
      field: "{field} ({value})",
      category: "Category",
      size: "had signed contracts of US${from} to US${to}",
      sizeFrom: "had signed contracts of US${from} or more",
      sizeTo: "had signed contracts of US${to} or less",
      region: "were in {region}",
      period: "had notices from {from} to {to}",
    },
    // The coverage line's noun and one phrase per reason code find_comparables returns
    // (config/tools.toml, [tools.find_comparables.result]).
    coverageNoun: "matching packages",
    // A phrase that changes with its count is a function of it.
    reasons: {
      no_step_reference: () => "{count} lacked the STEP reference that links notice to contract",
      no_notice: () => "{count} had no specific procurement notice in the records I hold",
      canceled: (count: number) => (count === 1 ? "{count} was canceled before a contract was signed" : "{count} were canceled before a contract was signed"),
      signed_before_notice: (count: number) =>
        count === 1 ? "{count} was signed before the date of its notice" : "{count} were signed before the date of their notice",
      no_review_type: () => "{count} had no review type in any record",
      no_market_approach: () => "{count} had no market approach in any record",
      no_amount: () => "{count} had no signed amount in US dollars",
    },
    reasonsEnd: ".",
    source: "{sources}. Records run through {date}.",
    sourceUndated: "{sources}.",
    // The plan control above the chart.
    control: {
      label: "Planned months",
      unit: "months",
      helper: "The plan row puts the notice on {notice} and the signed contract on {signing}.",
      helperNoPlan:
        "The plan row has no planned notice date or signing date, so there is no plan line yet. Type a number of months to compare.",
      invalid: (max: string) => `Type a number of months from 0.5 to ${max}.`,
      reset: (plan: string) => `Use the plan's ${plan} months`,
    },
    // The range chart's words. Numbers arrive written by web/src/lib/format.ts.
    chart: {
      lane: "What happened",
      keySigned: (count: string) => `${count} signed`,
      keyOpen: (count: string) => `${count} still open`,
      keyDots: (total: string) => `Each dot is 1 in 20 of the ${total} packages`,
      plan: "Plan",
      readout: (within: string, total: string, months: string) => `${within} of ${total} signed within ${months} months`,
      middle: (q25: string, q75: string, q50: string) => `Middle half ${q25} to ${q75}, middle ${q50}`,
      in10: (q80: string) => `8 in 10 within ${q80}`,
      axisLast: (months: string) => `${months} months`,
      group: (total: string) => `${total} comparable packages, one dot each`,
      groupDots: (total: string) => `20 dots, each 1 in 20 of the ${total} comparable packages`,
      groupHelp: "Use the arrow keys to move between packages. Press Escape to hide the details.",
      dotSigned: (ref: string, country: string, months: string, date: string, index: string, total: string) =>
        `${ref}, ${country}. Signed after ${months} months, on ${date}. Dot ${index} of ${total}.`,
      dotOpen: (ref: string, country: string, months: string, index: string, total: string) =>
        `${ref}, ${country}. Still open after ${months} months. Dot ${index} of ${total}.`,
      dotQuantile: (k: string, total: string, months: string) =>
        `Dot ${k} of 20. Each dot is 1 in 20 of the ${total} comparable packages. This one is at ${months} months.`,
      dotQuantileOpen: (k: string, total: string, months: string) =>
        `Dot ${k} of 20. Each dot is 1 in 20 of the ${total} comparable packages. Too many of these packages are still open to place this dot, so it sits past ${months} months.`,
      tipMonths: (months: string) => `${months} months`,
      tipPast: (months: string) => `Past ${months} months`,
      tipSigned: (signed: string, notice: string, country: string) => `Signed ${signed}. Notice published ${notice}. ${country}.`,
      tipOpen: (notice: string, country: string) => `Still open. Notice published ${notice}. ${country}.`,
      tipQuantile: (k: string) => `Dot ${k} of 20`,
      tipQuantileLine: (total: string) => `Each dot is 1 in 20 of the ${total} comparable packages.`,
      tipQuantileOpen: "Too many of these packages are still open to place this dot.",
      slider: "Planned months",
      valueText: (months: string, within: string, total: string) =>
        `${months} months. ${within} of ${total} were signed within ${months} months.`,
      valueTextPlan: (months: string, within: string, total: string) =>
        `${months} months, the plan's own figure. ${within} of ${total} were signed within ${months} months.`,
      announce: (within: string, total: string, months: string) => `${within} of ${total} were signed within ${months} months.`,
      // The text alternative: the same numbers the chart draws.
      alt: (total: string, axisMax: string, signed: string, open: string) =>
        `Dot chart of ${total} comparable packages on a month axis from 0 to ${axisMax} months: ${signed} signed and ${open} still open.`,
      altDots: (total: string, axisMax: string) =>
        `Dot chart of 20 dots, each 1 in 20 of the ${total} comparable packages, on a month axis from 0 to ${axisMax} months.`,
      altRange: (q25: string, q75: string, q50: string, q80: string) =>
        `The middle half took ${q25} to ${q75} months, the middle one took ${q50}, and 8 in 10 were signed within ${q80}.`,
      altMiddle: (q25: string, q75: string, q50: string) => `The middle half took ${q25} to ${q75} months, and the middle one took ${q50}.`,
      altNoIn10: "Fewer than 8 in 10 have been signed so far.",
      altNoUpper: "Too many are still open to place the upper edge of the middle half.",
      altAbstain: "I'm not giving a range for so few.",
      altPlan: (months: string, within: string, total: string) => `A line marks ${months} months, and ${within} of ${total} were signed within it.`,
      altCanceledLeftOut: (count: number, text: string) =>
        count === 1 ? "I left out the one canceled package, because it is not still open." : `I left out the ${text} canceled packages, because they are not still open.`,
      altCanceledCounted: (count: number, text: string) =>
        count === 1 ? "I counted the one canceled package as still open." : `I counted the ${text} canceled packages as still open.`,
    },
    // What each checkable number counts, in its tooltip.
    explain: {
      counts: (plan: string, total: string, open: string) =>
        `Packages signed in ${plan} months or less, out of all ${total}, counting the ${open} still open. Select to see the rows.`,
      quantiles: (total: string, open: string) =>
        `Worked out from all ${total} comparable packages, with the ${open} still open counted as not signed yet. This is the Kaplan-Meier method. Select to see the rows.`,
      plan: (agency: string, date: string) => `From the planned dates in the ${agency} plan of ${date}.`,
      coverage: "Counted from the records behind this section. Data readiness lists them by source.",
    },
    // The table twin under the chart.
    table: {
      show: "Show the table",
      hide: "Hide the table",
      caption: (total: string) => `All ${total} comparable packages, shortest first.`,
      captionOne: "The one comparable package.",
      noun: "packages",
      nounOne: "package",
      columns: {
        package: "Package (STEP reference)",
        country: "Country",
        notice: "Notice published",
        signed: "Contract signed",
        months: "Months",
        monthsNote: "From notice to signature, or so far if still open",
        within: (months: string) => `Signed within ${months} months`,
      },
      stillOpen: "Still open",
      yes: "Yes",
      no: "No",
      notYet: "Not yet",
      previous: "Previous 20",
      next: "Next 20",
    },
    // The states with no chart.
    empty: {
      noneTitle: "No past package matched this one, so I have nothing to compare it with.",
      noneLooked: "I looked for packages with the same {fields}.",
      noneHadTo: "They had to {parts}.",
      noneSize: "have signed contracts of US${from} to US${to}",
      noneSizeFrom: "have signed contracts of US${from} or more",
      noneSizeTo: "have signed contracts of US${to} or less",
      noneRegion: "be in {region}",
      nonePeriod: "have notices from {from} to {to}",
      noneEnd: "Data readiness shows which records I hold for this region and period.",
      noneLink: "Open Data readiness",
      unmeasuredTitle: (matched: number) =>
        matched === 1
          ? "{matched} past package matched this one, but I can't measure how long it took."
          : "{matched} past packages matched this one, but I can't measure how long any of them took.",
      notMeasurableTitle: "I can't measure procurement cycle time for this package.",
      notMeasurableBody:
        "I measure it from the specific procurement notice to the signed contract. Packages with the {field} {value} had no public notice to start from.",
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
