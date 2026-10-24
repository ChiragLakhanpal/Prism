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
    // Lessons > Waiting for review and one item's review page (ticket 29): the frame keeps the Lessons h1.
    lessonsQueue: {
      title: "Lessons",
      documentTitle: "Waiting for review, Lessons",
      purpose:
        "Each lesson comes from a completion report or its review, quoted word for word with its page. A lead " +
        "procurement specialist decides which lessons enter the library.",
    },
    lessonReview: {
      title: "Waiting for review",
      documentTitle: "Waiting for review, Lessons",
      purpose: "One lesson waiting for review, with its evidence, its history and your part in deciding it.",
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
    // A draft's page and the page that writes one (ticket 35). Each names itself in the browser tab with
    // its kind's title once the draft loads, such as "Review notes on the ... plan of Oct 9, 2026".
    draft: {
      title: "Draft",
      purpose: "I wrote this draft for you to check. Only its author can mark it as checked or export it.",
    },
    draftNew: {
      title: "Review notes",
      purpose: "I'm writing review notes for you to check. I save the draft when I finish.",
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
    // The page's reads take no date yet, but /api/ask does, so the alert says which part uses it.
    // Ticket 40 replaces it with its as-of banner.
    asOf: (date: string) => `I can't show this page as of ${date} yet, so it shows today's data. Questions you ask from the box, and sources opened from a link, use ${date}.`,
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
  // The one box (the 14 brief, section 5.1). The placeholder names only what the box can do now;
  // ticket 15 adds "describe a package" back. {id}, {pcode}, {loan} and {step_ref} show in Roboto Mono.
  box: {
    label: "Open a project or package, or ask a question",
    placeholderWide: "Open a project or package, or ask a question",
    placeholderNarrow: "Open a project, or ask",
    placeholderProject: "Ask about this project",
    placeholderPackage: "Ask about this package",
    // {pid} is hintId, set in Roboto Mono.
    hint: "Type a project ID such as {pid}, a STEP reference, a loan number, or a question.",
    hintId: "P130164",
    listName: "What Enter will do",
    enter: "Enter",
    option: {
      project: "Open {pcode}",
      projectLine: (name: string, country: string | null) => (country ? `${name}, ${country}` : name),
      loan: "Open the project for {loan}",
      loanLine: "{pcode}, {name}",
      activity: "Show {step_ref} in its plan",
      activityLine: (agency: string, date: string) => `In the ${agency} plan of ${date}, {pcode}`,
      ask: "Ask this",
      askWithin: "Within {id}",
      askAcross: "Across all projects",
      lookingUp: "Looking up {id}",
    },
    notFound: {
      project: "I have no project {id}.",
      loan: "I have no loan or credit {id} in the records.",
      activity: "I have no activity {id} in a published plan.",
    },
    lookupFailed: "I couldn't look up {id} just now. You can still ask about it.",
    chipWithin: "Within",
    chipRemove: (id: string) => `Remove the scope ${id}`,
    scoped: (id: string) => `Questions you ask here cover ${id} only.`,
    scopeRemoved: "The scope is removed. Questions now cover all projects.",
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
  // Its parts are templates, {part} of {whole}, one form for a whole of one and one for more, so the
  // server writes the same line into a draft's evidence pack (src/strata/drafts/copy.json).
  checkLine: {
    checked: "Checked:",
    notChecked: "Not checked:",
    numbers: { one: "{part} of {whole} number matches records", many: "{part} of {whole} numbers match records" },
    quotes: { one: "{part} of {whole} quote is on its page", many: "{part} of {whole} quotes are on their pages" },
    dates: { one: "{part} of {whole} date matches records", many: "{part} of {whole} dates match records" },
    sourcesOnly: "every source I cite came back from this search",
    // Two clauses take ", or " ("A, or B"); three or more take commas, with ", or " before the last
    // ("A, B, or C"), as the 24 brief joins them.
    notCheckedJoin: ", or ",
    notCheckedComma: ", ",
    clauseJoin: "; ",
    end: ".",
    // Keyed by what was not checked: "sentences" until ticket 24 adds the fourth check, then the
    // tools that ran (config/tools.toml), so a new tool adds one line, then a draft kind's writer
    // (config/drafts.toml's not_checked).
    notCheckedClauses: {
      sentences: "whether each sentence follows from its sources",
      find_comparables: "whether these are the right comparables",
      search_passages: "whether I found every passage that matters",
      check_plan: "whether the plan's published records are complete",
      writer_review_notes: "whether these notes are what you would tell the borrower",
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
    other: "The other:",
    // The sentence's own double quotes turn single inside the outer pair, so the marks never pile up.
    item: (sentence: string, reason: string) => `"${sentence.replace(/"([^"]*)"/g, "'$1'")}" ${reason}`,
    // A reason code with no sentence below: it makes no claim about why.
    unknownReason: { item: "It failed a check.", joined: "it failed a check" },
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
      // Ticket 18: a number that only Strata's own summary of a table holds, not the table's rows.
      number_only_in_table_summary: {
        item: "This number came only from my summary of a table, not from the table's rows.",
        joined: "that number came only from my summary of a table, not from the table's rows",
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
    // Each step's line while it runs, which the live region says once, and once it is done (the 14
    // brief, section 5.2). Tool steps are keyed by the tool registry's name (config/tools.toml), so a
    // new tool needs two lines here. Counts are words from one to nine (DESIGN.md section 7).
    read: { running: "I'm reading your question.", done: "I read your question." },
    tools: {
      search_passages: {
        running: (scope: string | null) => (scope ? `I'm searching the documents for ${scope}.` : "I'm searching the documents."),
        done: (count: number, countText: string, scope: string | null) =>
          `I found ${count === 0 ? "no" : countText} ${count === 1 ? "passage" : "passages"}${scope ? ` for ${scope}` : ""}.`,
      },
      check_plan: {
        running: () => "I'm checking the plan.",
        done: (count: number, countText: string) => `I checked ${countText} ${count === 1 ? "activity" : "activities"} in the plan.`,
      },
      find_comparables: {
        running: () => "I'm finding comparable packages.",
        done: (count: number, countText: string) => `I found ${countText} comparable ${count === 1 ? "package" : "packages"}.`,
      },
      ask_genie: {
        running: () => "I'm looking through the records.",
        done: (count: number, countText: string) => `I found ${countText} matching ${count === 1 ? "record" : "records"}.`,
      },
      get_lessons: {
        running: () => "I'm looking for lessons.",
        done: (count: number, countText: string) => `I found ${countText} ${count === 1 ? "lesson" : "lessons"}.`,
      },
    },
    otherTool: { running: (tool: string) => `I'm using ${tool}.`, done: (tool: string) => `I used ${tool}.` },
    write: {
      running: "I'm writing the answer.",
      done: (count: number, countText: string) =>
        count === 0 ? "I wrote no sentences." : `I wrote ${countText} ${count === 1 ? "sentence" : "sentences"}.`,
      // A step still to come, listed in ink-muted so the block keeps its height (02's round 7 critique).
      todo: "To do: write the answer.",
    },
    check: {
      running: "I'm checking each number and quote against the sources.",
      done: "I checked each number and quote against the sources.",
      doneCounted: (numbers: string, quotes: string, removed: string) => `I checked ${numbers} and ${quotes}, and removed ${removed}.`,
      numbers: (count: number, countText: string) => (count === 1 ? "one number" : `${countText} numbers`),
      quotes: (count: number, countText: string) => (count === 1 ? "one quote" : `${countText} quotes`),
      removed: (count: number, countText: string) => (count === 0 ? "none" : count === 1 ? "one sentence" : `${countText} sentences`),
      todo: "To do: check each number and quote against the sources.",
    },
  },
  answer: {
    inShort: "In short",
    // Ticket 14's live region says this last, once the answer is on screen (its brief).
    ready: "The answer is ready.",
    readyRemoved: (count: number, countText: string) =>
      count === 1
        ? "The answer is ready. I removed one sentence that failed a check."
        : `The answer is ready. I removed ${countText} sentences that failed a check.`,
    tryAgain: "Try again",
    // The answer panel's header (the 14 brief, section 5.3). {id} shows in Roboto Mono.
    panel: "Answer",
    close: "Close the answer",
    askedWithin: "Asked within {id}",
    askedAcross: "Asked across all projects",
    askedAsOf: (date: string) => `, as of ${date}`,
    // No view is named: until ticket 40 applies a view's rules on the server, every answer is the
    // World Bank staff view's. Ticket 40 adds ", in a preview of the {view} view" back.
    askedEnd: ".",
    // Every sentence the agent wrote failed a check (the 14 brief, section 5.7).
    nothingSurvived: (count: number, countText: string) =>
      count === 1
        ? "I don't have an answer I can support with a source. I wrote one sentence, and it failed a check."
        : `I don't have an answer I can support with a source. I wrote ${countText} sentences, and each one failed a check.`,
    // The agent found nothing to cite (section 5.6).
    emptyScoped: "I found nothing in the records or documents for {id} that answers this. You can ask the same question across all projects.",
    emptyUnscoped: "I found nothing in the records or documents that answers this. {link} shows which sources and years I have read so far.",
    emptyLink: "Data readiness",
    askAcross: "Ask across all projects",
    // A refusal is an answer, not an error (section 5.8): a content filter's is errors.content_filter
    // below, shown as plain text. Ticket 24 adds the refusal list's own lines.
    refusalNote: "{link} lists what I don't do, and why.",
    refusalLink: "How Strata works",
    // The stream ended before its done event (section 5.9).
    dropped: "The connection dropped before the answer was ready.",
    stillInBox: "Your question is still in the box.",
    // Why an answer stopped, keyed by the code its stream's error event carries (ERROR_CODES in
    // src/strata/harness/turn.py). A test fails when a code has no sentence here.
    // One idea a sentence: the "Try again" button carries the instruction, and stillInBox follows
    // each. no_agent gets no button, because trying again cannot connect the model.
    errors: {
      no_agent: "I can't answer questions yet, because the model that writes my answers isn't connected.",
      agent_unavailable: "I couldn't reach the model that writes my answers.",
      content_filter: "I can't answer this as written, because a content filter stopped the question. Try asking it in different words.",
      agent_output: "I wrote an answer I couldn't check, so I'm not showing it.",
      data_service: "I can't reach the data right now, so I can't answer.",
      internal: "Something went wrong on my side, so I can't answer. If it happens again, share the answer ID below.",
    },
    // internal, when the stream never opened and so has no answer ID to share.
    internalNoId: "Something went wrong on my side, so I can't answer.",
  },

  // Term and DefinitionWindow.
  definition: {
    close: "Close the definition",
  },

  // A document's passage, as the evidence drawer and the document page show it.
  document: {
    // The source line's words on each side of the project ID, which shows in mono:
    // "Implementation Completion and Results Report, " P000000 ", June 30, 2021, paragraph 54,
    // page 23." A no-break space keeps each word with its number, so no line ends on "paragraph".
    sourceLine: (docType: string, date: string, para: string, page: string) => ({
      before: `${docType}, `,
      after: `, ${date}, paragraph\u00a0${para}, page\u00a0${page}.`,
    }),
    // A passage with no paragraph number, such as an ISR's, is cited by its section: "...,
    // February 22, 2014, section Project Development Objective Indicators, page 2."
    sourceLineSection: (docType: string, date: string, section: string, page: string) => ({
      before: `${docType}, `,
      after: `, ${date}, section\u00a0${section}, page\u00a0${page}.`,
    }),
    highlightStarts: "Highlight starts.",
    highlightEnds: "Highlight ends.",
    openAtPage: (page: string) => `Open at page ${page} in the World Bank's PDF`,
    newTab: ", opens in a new tab",
    failed: "I couldn't load this source.",
    missing: "I have no source with this ID. The link may be incomplete.",
    // The server gives the same answer for a source not public by the address's as-of date.
    missingAsOf: (date: string) => `I have no source with this ID as of ${date}. It may not have been public yet, or the link may be incomplete.`,
  },

  // Languages by their ISO 639-1 codes, by their English names (ticket 18; brief 42 reuses these keys).
  language: {
    name: { en: "English", fr: "French", es: "Spanish", pt: "Portuguese" } as Record<string, string>,
  },

  // The evidence card and the evidence drawer (the 14 brief, sections 5.11 to 5.13). Each source's
  // stratum and its document's short name come from the answer stream.
  evidence: {
    eyebrow: { What: "What · record", How: "How · operations", Why: "Why · evaluation" },
    // The heading names the source, not the claim, so a drawer opened from a link still reads.
    title: "{project}, paragraph {para}",
    titleSection: "{project}, section {section}",
    recordTitle: "{kind} {reference}",
    // What a record is called, by the table its evidence id names (web/src/lib/sources.ts).
    recordKinds: {
      "strata.silver.plan_rows": "Activity",
      "strata.gold.contract": "Contract",
      "strata.gold.package": "Package",
      "strata.ops.lesson_versions": "Lesson",
    } as Record<string, string>,
    recordKindOther: "Record",
    // The record view's fields keep STEP's own names; the description's is STEP's "Description".
    recordDescription: "Description",
    // The record view's source line, as the plan check writes a plan's: "Source: Procurement Plan,
    // Northern Water Works Development Agency, P156634, version of October 9, 2026, page 3."
    // "page" and its number never part at a line end: a no-break space joins them (DESIGN.md section 7).
    recordSource: "{doc}, {agency}, {pid}, version of {date}, page\u00a0{page}.",
    recordSourceShort: "{doc}, {pid}, {date}.",
    // The heading when no source could be shown.
    untitled: "Source",
    visited: "You have opened this source.",
    // The excerpt sits in straight quotes, as the paragraph's own words.
    quoteOpen: '"',
    quoteClose: '"',
    // Where an excerpt longer than the card's limit was cut, between words.
    cut: "…",
    close: "Close the source",
    fromAnswer: "From the answer",
    switcher: "Sources for this sentence",
    // A switcher tab reads "ICR ¶54", and a screen reader hears "ICR paragraph 54". A section reads
    // "ISR, Project Development Objective Indicators".
    paraMark: "¶",
    paraSpoken: "paragraph ",
    switcherSection: (short: string, section: string) => `${short}, ${section}`,
    // The meta line, word for word as the ticket writes it: "Implementation Completion and Results
    // Report · Rajasthan Road Sector Modernization (P130164) · October 10, 2019 · Section III.B · ¶54 ·
    // PDF page 23 of 66". The project ID shows in Roboto Mono.
    meta: {
      // A no-break space keeps the project's name with its ID.
      project: "{project}\u00a0({pcode})",
      section: (section: string) => `Section ${section}`,
      para: (para: string) => `¶${para}`,
      page: (page: string, pages: string) => `PDF page ${page} of ${pages}`,
      // A table's summary covers every page of its table.
      pageRange: (page: string, last: string, pages: string) => `PDF pages ${page} to ${last} of ${pages}`,
      pageOnly: (page: string) => `PDF page ${page}`,
      // The dot ends each part with a no-break space before it, so a line breaks only after a dot,
      // never inside "PDF page 23 of 66" or before a dot.
      dot: "\u00a0·",
    },
    noHighlight: "This sentence does not quote the paragraph, so no words are highlighted.",
    noHighlightSection: "This sentence does not quote the section, so no words are highlighted.",
    noHighlightRow: "This sentence does not quote the row, so no words are highlighted.",
    whole: "The whole paragraph, word for word.",
    wholeSection: "The whole section, word for word.",
    // The passages ticket 18 adds (the 18 brief, section 7). The layout parser's text can differ from
    // the page, so these never say "word for word".
    wholeScanned: "The whole paragraph, as the layout parser read it from a scanned page. The PDF page has the exact words.",
    tableTitle: "{project}, {table}",
    tableTitleUntitled: "{project}, table on page {page}",
    summaryTitle: "{project}, summary of {table}",
    rowOf: (row: string) => `Row ${row}`,
    rowNote: "This row as the layout parser read it from the table. The PDF page has the original.",
    // The row's cells: its column heads and its values.
    rowField: "Column",
    rowValue: "Value",
    // The summary itself starts with the table, so who wrote it is said once, here, with the table's pages
    // (design review r2 P2).
    summaryNote: (page: string, last: string | null) =>
      `I wrote this summary of the table on ${last ? `PDF pages ${page} to ${last}` : `PDF page ${page}`}. It is not the document's own words, and I never use it to back a number.`,
    noticeTitle: "Notice {id}",
    noticeEyebrow: "What · notice",
    noticeWhole: "The whole section, word for word, without contact details.",
    // Where a notice's contact details were removed at ingestion.
    contactRemoved: "(contact details removed)",
    openNotice: "Open this notice on the World Bank's site",
    inLanguage: (language: string) => `In ${language}`,
    preview: "The address asks for a preview, so I'm not recording the sources you open.",
    // The citation marker's name: "Source 1: Implementation Completion and Results Report, October 10,
    // 2019, paragraph 54".
    markerSource: (docType: string, date: string, para: string) => `${docType}, ${date}, paragraph ${para}`,
    markerSourceSection: (docType: string, date: string, section: string) => `${docType}, ${date}, section ${section}`,
    markerRecord: (kind: string, reference: string) => `${kind} ${reference}`,
    // A number in a sentence says which source the verifier matched it to.
    // Templates for Fill, so the project ID or the reference is set in Roboto Mono.
    numTooltip: "Matches paragraph {para} of the {kind} for {pid}.",
    numTooltipSection: "Matches the section {section} of the {kind} for {pid}.",
    numTooltipRecord: "Matches the {kind} record {reference}.",
    // A date a passage backs because it is its report's date, not because the paragraph holds it.
    numTooltipReportDate: "Matches the date of the {kind} for {pid}.",
    // What a number's tooltip calls each kind of document, by its short name.
    docKinds: {
      ICR: "completion report",
      "ICR Review": "review of the completion report",
      PAD: "appraisal document",
      ISR: "status report",
    } as Record<string, string>,
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
  // Pagination (the 21 design brief; built early by ticket 29): links that move a list a page at a time.
  pagination: {
    label: "Pages",
    previous: "Previous page",
    next: "Next page",
    page: "Page {page} of {pages}",
  },

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
    // The draft action in the header's free slot (the 35 brief, section 5.1). {n} is check_plan's count of
    // the activities with a signal.
    draftAction: {
      button: (count: number, countText: string) => (count === 1 ? "Draft review notes (1 row)" : `Draft review notes (${countText} rows)`),
      feedforward: "The draft waits in Drafts for you to check. I send nothing.",
      description: "I write one note for each activity that needs a look or is worth watching.",
      none: "No activity needs a look or is worth watching, so I have no review notes to draft.",
      asof: "I draft review notes only from today's check, not from a past date.",
      existingYou: (date: string) => `You started review notes on this plan on ${date}.`,
      existingTeammate: (author: string, date: string) => `${author} started review notes on this plan on ${date}.`,
      existingLink: "Open the draft",
      stopped: "I stopped writing the review notes and saved nothing.",
    },
  },

  // Drafts (the 35 brief): the writing page, a draft's page with its bar, its files and the Drafts tab.
  // Every count comes from the draft runtime or a tool; the browser counts nothing. Each kind of draft
  // (config/drafts.toml) has its words under kinds, by its key.
  draft: {
    kinds: {
      review_notes: {
        title: "Review notes",
        // The breadcrumb's last step and the Drafts tab's row title, with the short date.
        crumb: (date: string) => `Review notes on the plan of ${date}`,
        rowTitle: (agency: string, date: string) => `Review notes on the ${agency} plan of ${date}`,
        // The browser tab, before " | Strata".
        pageTitle: (agency: string, date: string) => `Review notes on the ${agency} plan of ${date}`,
        // Under the h1: "Northern Water Works Development Agency, Procurement Plan of October 9, 2026".
        subtitle: "{agency}, Procurement Plan of {date}",
        // The lede, an h2: {count} is a Num whose popover lists the activities.
        lede: (count: number) =>
          count === 1
            ? "I drafted a note on the one activity that needs a look or is worth watching."
            : "I drafted a note on each of the {count} activities that need a look or are worth watching.",
        ledePartial: "I drafted notes on {written} of the {count} activities that need a look or are worth watching.",
        method:
          "I wrote each note from {check} and cited the records behind every sentence. Open a source number to see " +
          "its record beside the note.",
        methodLink: "my check of this plan",
        countLine: (count: number, countText: string) =>
          count === 1 ? "Showing the 1 activity with a signal" : `Showing all ${countText} activities with a signal`,
        columns: { activity: "Activity", note: "Review note" },
        tableCaption: (agency: string, date: string) =>
          `Review notes on the ${agency} plan of ${date}, one row per activity with a signal`,
        // A note cell with nothing that passed the checks.
        abstain:
          "I couldn't write a note on this activity that passed my checks. The sentences I removed are listed " +
          "above, with the reason for each.",
        // A note cell the writer refused, by its refusal code. Ticket 24 adds its refusal keys here.
        refused: {
          out_of_scope: "I didn't write a note on this activity, because a note would need more than the plan's record shows.",
        } as Record<string, string>,
        refusedOther: "I didn't write a note on this activity.",
        metaYou: (date: string) => `I drafted these notes for you on ${date}.`,
        metaTeammate: (author: string, date: string) => `I drafted these notes for ${author} on ${date}.`,
        // The draft bar: the kind's lead sentence, before the fixed consequence sentence.
        barLead: "A working draft of your review notes on the borrower's Procurement Plan.",
        barLeadTeammate: (author: string) => `A working draft of ${author}'s review notes on the borrower's Procurement Plan.`,
        holdNotChecked: "Mark the notes as checked before you export them.",
        readOnly: (author: string) => `Only ${author} can mark these notes as checked or export them.`,
        markedChecked: "You marked these notes as checked. You can export them now.",
        discarded: "You discarded these review notes, so your team no longer sees them in Drafts.",
        // A removed sentence's reason, where the answer's words would say "question": each note may cite
        // only its own activity's row (src/strata/drafts/runtime.py, compose).
        removedReasons: {
          id_not_returned: {
            item: "It cited a source other than this activity's row in my check of the plan.",
            joined: "it cited a source other than this activity's row in my check of the plan",
          },
        } as Record<string, { item: string; joined: string }>,
        // The Drafts tab's row: {project} is "Water and Sanitation Development Project (P156634)".
        rowNotes: (count: number, countText: string) => (count === 1 ? "One note." : `${countText} notes.`),
        // The writing page (section 5.2).
        steps: {
          read: { running: "I'm reading my check of the plan.", done: (date: string) => `I read my check of the plan of ${date}.` },
          write: {
            running: (count: number, countText: string) =>
              count === 1 ? "I'm writing a note on the one activity." : `I'm writing a note on each of the ${countText} activities.`,
            done: (sentences: number, sentencesText: string, notes: number, notesText: string) =>
              `I wrote ${sentences === 1 ? "one sentence" : `${sentencesText} sentences`} in ${notes === 1 ? "one note" : `${notesText} notes`}.`,
          },
          save: { running: "I'm saving the draft.", done: "I saved the draft." },
        },
        ready: (count: number, countText: string) =>
          count === 1 ? "The draft is ready. I wrote one note." : `The draft is ready. I wrote ${countText} notes.`,
        writeErrors: {
          no_agent: "I can't write review notes yet, because the model that writes my drafts isn't connected. I saved nothing.",
          agent_unavailable:
            "I couldn't write the review notes, because the model that writes my drafts did not respond. I saved nothing.",
          content_filter: "I couldn't write the review notes, because a content filter stopped the writer. I saved nothing.",
          agent_output: "I wrote review notes I couldn't check, so I saved nothing.",
          data_service: "I couldn't read my check of the plan, because the data service didn't answer. I saved nothing.",
          // The app's own account could not save the draft: nothing the viewer can fix.
          draft_store: "I couldn't save the draft, because I can't write to my drafts tables right now. I saved nothing.",
          no_plan: "I couldn't find this version of the plan, so I wrote nothing and saved nothing.",
          nothing_marked: "No activity in this plan needs a look or is worth watching, so I saved nothing.",
          // The viewer's own read of the plan's check was refused.
          permission:
            "Your account can't read this plan's check in Strata's tables, so I can't write review notes. Ask your " +
            "workspace admin for read access to the strata catalog.",
          internal: "Something went wrong on my side, so I couldn't write the review notes. I saved nothing.",
          dropped: "The connection dropped before I finished the review notes. I saved nothing.",
        } as Record<string, string>,
        nothingTitle: "I couldn't write a note that passed my checks, so I saved no draft.",
        nothingBody: "The sentences I removed are below, with the reason for each.",
        previewPiuTitle: "I don't show review notes in this preview, because they are a World Bank staff draft.",
        previewPiuBody: "Leave the preview to see them. Nothing about the draft changed.",
      },
    },
    // The writing page (`/drafts/new`).
    writing: {
      state: "I'm writing. I save the draft when I finish.",
      stop: "Stop writing",
      // The verifier's step, with the number of checks it ran from its checks event.
      checkRunning: "I'm checking each sentence against its sources.",
      checkDone: (checks: string, written: number, writtenText: string, removed: number, removedText: string) =>
        `I ran ${checks} checks on the ${written === 1 ? "one sentence" : `${writtenText} sentences`} I wrote and removed ${
          removed === 0 ? "none" : removed === 1 ? "one" : removedText
        }.`,
      tryAgain: "Try again",
      backToPlan: "Back to the plan check",
      reloadTitle: "I'm not writing a draft right now.",
      reloadBody: "If you reloaded this page while I was writing, I stopped and saved nothing. Start again from the plan check.",
      reloadLink: "Go to Drafts",
    },
    // A draft's page (section 5.3).
    state: {
      label: "State of this draft",
      draft: "Draft",
      checkedYou: "Checked by you",
      checkedOther: (author: string) => `Checked by ${author}`,
      exported: "Exported",
      doneSuffix: ", done",
      discarded: (date: string) => `Discarded on ${date}`,
    },
    // Under the steps I took, before the draft's ID in Roboto Mono.
    idLabel: "Draft ID",
    // Sources (section 5.4).
    sources: {
      title: "Sources",
      caption: (opened: string, total: string, citations: number, citationsText: string) =>
        citations === 1
          ? `You opened ${opened} of ${total}. In the Word file, the one citation becomes a footnote.`
          : `You opened ${opened} of ${total}. In the Word file, each of the ${citationsText} citations becomes a footnote.`,
      citedIn: (count: number) => (count === 1 ? "Cited in the note on {refs}." : "Cited in the notes on {refs}."),
      opened: "You opened this.",
      notOpened: "You haven't opened this yet.",
    },
    // The draft bar (section 5.5). The consequence sentence is fixed for every kind: the one place
    // rule 19's "clearance" and "no-objection" appear (web/lint/rules.ts, FIXED_TERMS).
    bar: {
      label: "Check and export",
      consequence: "Exporting sends nothing and is not a World Bank review, clearance or no-objection.",
      opened: (opened: string, total: string) => `You opened ${opened} of ${total} sources`,
      end: ".",
      // Each hold's line by its copy key (config/drafts.toml, [holds.<key>].copy). notChecked is the kind's
      // own (copy.draft.kinds.<kind>.holdNotChecked); tests/test_drafts.py checks every key has a line.
      hold: {
        preview: "This is a preview, so you can't mark drafts as checked or export them.",
      } as Record<string, string>,
      discard: "Discard",
      export: "Export to Word",
      check: "Mark as checked",
      busy: { discard: "Discarding", export: "Exporting", check: "Saving", restore: "Restoring" },
      failed: {
        check: "I couldn't save your check just now. The notes are still a draft.",
        export: "I couldn't make the files just now. The notes are still checked, and I exported nothing.",
        discard: "I couldn't discard the draft just now. It is unchanged.",
        restore: "I couldn't restore the draft just now. It is still discarded.",
      },
      exportStarted: "I'm making the Word file and the evidence pack.",
      restored: "You restored the draft.",
      restoredChecked: "You restored the draft. It is still marked as checked.",
    },
    conflict: "This draft changed in another tab or window, so I reloaded it.",
    // The export success panel and the discarded notice (section 5.6).
    exported: {
      title: (count: number, countText: string) =>
        count === 1
          ? "Exported. I made a Word file with 1 footnote and an evidence pack."
          : `Exported. I made a Word file with ${countText} footnotes and an evidence pack.`,
      // The reason clause shows only when the author kept another source, with a reason (ticket 23).
      body: (count: number, countText: string, disagreed: boolean) =>
        `The evidence pack lists ${count === 1 ? "the one source" : `all ${countText} sources`}${disagreed ? "," : " and"} whether you opened ${
          count === 1 ? "it" : "each one"
        }${disagreed ? ", and the reason you gave for keeping another source" : ""}. Your browser downloaded the Word file, ` +
        "and the evidence pack's files are below. I keep all three with this draft for your team. I sent nothing to anyone.",
      revisitTitle: (date: string, count: number, countText: string) =>
        `Exported on ${date}. I made a Word file with ${count === 1 ? "1 footnote" : `${countText} footnotes`} and an evidence pack.`,
      revisitBody: "You can download the same files again. I sent nothing to anyone.",
      // In place of revisitBody when the export's files are gone.
      revisitBodyMissing: "I sent nothing to anyone.",
      revisitTeammate: (author: string, date: string, count: number, countText: string) =>
        `${author} exported these notes on ${date}. I made a Word file with ${count === 1 ? "1 footnote" : `${countText} footnotes`} and an evidence pack.`,
      word: (count: number, countText: string) => (count === 1 ? "Word file, 1 footnote" : `Word file, ${countText} footnotes`),
      pdf: "Evidence pack, PDF",
      csv: "Evidence pack, CSV",
      filesLabel: "The exported files",
      // A file link's name: its file name, then what it is.
      fileName: (name: string, caption: string) => `${name}, ${caption}`,
      filesMissing:
        "I can't find the files from this export. I kept the record of the export, so the data team can restore the " +
        "files from Draft ID {id}.",
    },
    discarded: {
      restore: "Restore the draft",
      link: "Go to Drafts",
    },
    // The other states of a draft's page (section 5.9).
    page: {
      loading: "Loading this draft.",
      notFoundTitle: "I can't find this draft.",
      notFoundBody: "The link may be incomplete, or the draft may belong to another team.",
      notFoundLink: "Go to Drafts",
      error: "I couldn't load this draft because the data service didn't answer.",
      draftStore: "I can't show this draft, because I can't read my drafts tables right now.",
      permission: "Your account can't read Strata's tables, so I can't show this draft.",
      publicTitle: "The public view has no drafts.",
      publicBody: "Drafts belong to the team that made them. Leave the preview to see yours.",
    },
    // The Drafts tab (section 5.8). Its title, purpose and empty card are pages.drafts.
    tab: {
      groups: { to_check: "To check", checked: "Checked", exported: "Exported" },
      count: (count: number, countText: string) => (count === 1 ? "One draft." : `${countText} drafts, newest first.`),
      // Line 2's sentences, after the project.
      draftedYou: (date: string) => `Drafted by you on ${date}.`,
      draftedOther: (author: string, date: string) => `Drafted by ${author} on ${date}.`,
      checkedYou: (date: string) => `Checked by you on ${date}.`,
      checkedOther: (author: string, date: string) => `Checked by ${author} on ${date}.`,
      exportedYou: (date: string) => `Exported by you on ${date}.`,
      exportedOther: (author: string, date: string) => `Exported by ${author} on ${date}.`,
      discardedYou: (date: string) => `Discarded by you on ${date}.`,
      project: "{name} ({pid}).",
      opened: (opened: string, total: string) => `You opened ${opened} of ${total} sources.`,
      empty: {
        to_check: "No drafts are waiting to be checked.",
        checked: "No checked drafts are waiting to be exported.",
        exported: "Nobody on your team has exported a draft yet.",
      },
      discardedFold: (count: number, countText: string) =>
        count === 1 ? "You discarded one draft." : `You discarded ${countText} drafts.`,
      showDiscarded: (count: number) => (count === 1 ? "Show it" : "Show them"),
      hideDiscarded: (count: number) => (count === 1 ? "Hide it" : "Hide them"),
      more: (count: string) => `Show ${count} more`,
      loading: "Loading your team's drafts.",
      error: "I couldn't load your team's drafts because the data service didn't answer.",
      draftStore: "I can't list your team's drafts, because I can't read my drafts tables right now.",
      permission: "Your account can't read Strata's tables, so I can't list your team's drafts.",
    },
    // The export's files (section 6.7), which the server writes from src/strata/drafts/copy.json
    // (node web/lint/server-copy.ts --write). Word's text speaks in the document's voice: no "I" or
    // "you". {braces} are filled from the draft.
    files: {
      word: {
        review_notes: {
          heading: "Review notes on the {agency} plan of {date}",
          line: "{project_name} ({project_id}). Procurement Plan of {date}.",
          origin:
            "Drafted with Strata on {created} and checked by {checker} on {checked}. Strata is an independent demo " +
            "built on World Bank open data. These notes are not a World Bank review, clearance or no-objection.",
          columns: ["Activity", "Review note"],
        },
      },
      pack: {
        title: "Evidence pack",
        draftId: "Draft ID {id}",
        drafted: "Drafted on {date} for {author}.",
        checked: "Checked by {author} on {date}.",
        exported: "Exported by {author} on {date}.",
        opened: "{author} opened {opened} of {total} sources before exporting.",
        removedTitle: "Sentences I removed",
        removedNone: "I removed no sentences.",
        removedItem: '"{sentence}" {reason}',
        sourcesTitle: "Sources",
        columns: ["Number", "Source", "Cited in", "Opened", "Last opened (UTC)", "Kept another source, and why"],
        csvColumns: ["Number", "Evidence ID", "Source", "Cited in", "Opened before export", "Last opened (UTC)", "Kept another source", "Reason"],
        yes: "Yes",
        no: "No",
        // The column heading already says UTC.
        moment: "{date}, {time}",
        citedJoin: ", ",
        dataCaveat: "The World Bank does not guarantee the accuracy of the data.",
      },
    },
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
        lessons: "Lessons from completion reports",
      } as Record<string, string>,
      // The plan check's count words STEP's format as the Procurement Plans row does.
      counts: {
        plan_check: "activity entries in the latest plan versions with rows in STEP's format",
        document_search: "passages you can search",
        lessons: "proposed lessons with their quote found on the page they cite",
      } as Record<string, string>,
      // The same, for a count of one.
      countsOne: {
        plan_check: "activity entry in the latest plan versions with rows in STEP's format",
        document_search: "passage you can search",
        lessons: "proposed lesson with its quote found on the page it cites",
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
        // A document collection's slice (config/slice.toml): "Water and transport projects in Kenya,
        // Bangladesh, Vietnam and Pakistan, fiscal 2012 to 2025".
        slice: (sectors: string, countries: string, from: string, to: string) => `${sectors} projects in ${countries}, fiscal ${from} to ${to}`,
        // When "The hardest documents I read" shows below: their projects are read too (design review r2 B1).
        sliceShelf: "and the projects of the hardest documents below",
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
      // A row whose records arrive as text, such as notices' text, with nothing to read well.
      publishedAsText: "Published as text",
      // A document collection's Coverage (the 18 brief, section 6.1, as design review r2 B1 changed it):
      // its documents and the projects they belong to, then, on its own line, the pilot projects whose
      // documents I read, out of every pilot project.
      documentsFor: "documents for {projects} projects",
      documentsForOneProject: "documents for {projects} project",
      documentForOneProject: "document for {projects} project",
      // What the projects count counts, in its tooltip.
      projectsNoun: "projects with documents I read",
      projectsNounOne: "project with documents I read",
      pilot: "{read} pilot projects",
      pilotOne: "{read} pilot project",
      pilotNoun: "pilot projects",
      pilotNounOne: "pilot project",
      // The Read well window of a document collection: its share across both routes, split by route.
      routes: {
        published_text: "Published text",
        layout_parser: "Layout parser",
      } as Record<string, string>,
      routeRead: (part: string, whole: string) => `${part} of ${whole} pages read well`,
      // What a route counts as read well, under the split, since the published text's pages count once
      // placed on their PDF page, which the paragraph-number check goes beyond (review r2 P2).
      routeCounts: "What counts",
      routeCountsNote:
        "A page of published text counts once I have placed its text on its PDF page. A page I sent to the " +
        "layout parser counts when it gave back a table or text. Whether I found a report's paragraph numbers " +
        "is a separate check.",
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
    // The stress shelf (the 18 design brief, section 4): "The hardest documents I read". The screen
    // never says "stress shelf", our own name for it; the code and the slice file keep it.
    shelf: {
      title: "The hardest documents I read",
      caption:
        "I use these documents as a stress test for my reading. Each row says what makes the document hard, what I " +
        "recovered, and the page where you can compare the two.",
      sourceLine: "Strata's reading records, taken {date}. Documents from the World Bank's Documents and Reports.",
      columns: {
        document: { label: "Document" },
        hard: { label: "What makes it hard", about: "why I chose it" },
        parser: {
          label: "Layout parser",
          about: "pages sent to it",
          definition:
            "I read most pages from the text the World Bank publishes. I send scanned pages, tables and figures to a " +
            "layout parser instead, because the published text loses their rows and columns.",
        },
        outcome: {
          label: "Outcome",
          about: "checked against the document",
          definition:
            "What I recovered from the hard part, counted against what the document holds. Open a number to see what " +
            "I counted it against.",
        },
        page: { label: "Page", about: "where the hard part starts" },
      },
      // The Document cell: the type spelled out, then the project with its ID in mono, then the date and pages.
      project: "{project} ({pid})",
      dated: "{date}, {pages} pages",
      // Before a rule has picked a document, or before a fixed one is read: what the entry is.
      entries: {
        scan_annex: "Project Appraisal Document",
        longest_pad: "The longest Project Appraisal Document",
        large_plan: "Procurement Plan",
        other_language: "Implementation Completion and Results Report",
        over_parser_limit: "Any document over the parser's limit",
      } as Record<string, string>,
      // Line 2 of a rule's entry before the reading, when no document is chosen yet (critique r2).
      chosenLater: "I choose it when I read the documents.",
      // What makes each kind hard, one sentence each, with no number (the 18 brief, section 4.2). The
      // risk annex's says what its outcome checks, so the row claims no more than it measured (design
      // review r2 B2).
      hard: {
        scan_annex: "A scanned document whose {part} is set in two columns. I check its risks and ratings, not the text beside them.",
        longest_pad: "The longest Project Appraisal Document I read for the pilot projects.",
        large_plan: "A long Procurement Plan whose columns scramble in the published text.",
        other_language: "A completion report written in {languageName}.",
        over_parser_limit: "More pages than the layout parser takes at once.",
      } as Record<string, string>,
      // A rule's entry before the reading, so the row never says I read what I haven't (critique r2).
      hardBefore: {
        longest_pad: "The longest Project Appraisal Document of the pilot projects.",
      } as Record<string, string>,
      // A rule's entry that found no document: what I looked for (design review r2 P5).
      lookedFor: {
        longest_pad: "I looked for the longest Project Appraisal Document of the pilot projects.",
        over_parser_limit: "I looked for a document longer than the layout parser takes at once.",
      } as Record<string, string>,
      // The Layout parser cell: "{count} of {total}", then "pages".
      of: "{count} of {total}",
      pages: "pages",
      // What each kind's outcome counts, under its number.
      counts: {
        scan_annex: "rated risks recovered",
        longest_pad: "pages read well",
        large_plan: "activities became STEP rows",
        other_language: "passages marked as {languageName}",
        over_parser_limit: "page numbers match the PDF, across {parts} parts",
      } as Record<string, string>,
      // What each outcome's numbers count, in their tooltips.
      nouns: {
        scan_annex: "rated risks",
        longest_pad: "pages",
        large_plan: "activities",
        other_language: "passages",
        over_parser_limit: "pages",
        parser: "pages",
        read: "pages",
        longest: "pages",
      } as Record<string, string>,
      // Where each outcome's denominator comes from, in its window.
      denominators: {
        hand_count: "{denominator} rated risks in the annex, counted by hand from the PDF on {date}",
        pdf_pages: "{denominator} pages in the PDF",
        text_references: "{denominator} activity references I found in its text",
        passages_made: "{denominator} passages I made from it",
      } as Record<string, string>,
      // The windows the shelf's numbers open.
      windows: {
        parser: { title: "Pages sent to the layout parser", definition: "How many of the document's pages I sent to the layout parser, out of its pages in the PDF." },
        outcome: { title: "Outcome", definition: "What I recovered from the hard part, counted against what the document holds." },
        // An outcome's own definition, by kind, where the general one would claim more than it counts.
        outcomeKinds: {
          scan_annex:
            "A risk counts when I read its name and its rating from the risk table. I don't check the description and " +
            "mitigation text beside them, which the scan sets in two columns. Open the page to compare.",
        } as Record<string, string>,
        read: { title: "Pages read so far", definition: "How many of the document's pages I have read, from either route, out of its pages in the PDF." },
        longest: { title: "The longest document I read", definition: "How many pages the longest document I read has, in its PDF." },
        // Strata's own settings, not measures, so each has a tooltip and no window (design review r2 P4).
        limit: "The most pages I send the layout parser at once. It is my own setting, not a measure.",
        cap: "The most pages I send the layout parser in one day. It is my own setting, not a measure.",
      },
      windowRows: { from: "Counted against", parser: "Layout parser" },
      noHandCount: "I have no count of the annex's risks to check this against.",
      noDocumentOver: "No document I read has more than {limit} pages, so none needed dividing. The longest has {maxPages} pages.",
      noDocument: "I found no {description} among the documents I read.",
      // A kind's description in "I found no ... among the documents I read."
      descriptions: {
        scan_annex: "scanned Project Appraisal Document",
        longest_pad: "Project Appraisal Document of the pilot projects",
        large_plan: "Procurement Plan",
        other_language: "completion report in {languageName}",
      } as Record<string, string>,
      // "{read} of {pages}" is one number, as every pair on the shelf is (design review r2 P4).
      stopped: "{read} pages read so far",
      // The limit covers the whole run, so a reader doesn't ask why I stopped short of it (critique r2).
      stoppedNote: "I stopped at today's limit of {cap} pages, which covers every document in the run. The next run reads the rest.",
      notRead: "Not read yet. The next document run reads it.",
      // The Page cell: the link, then where it lands.
      pageLink: "Open at page {page}",
      // The rest of the link's name, after its words on screen, so five "Open at page" links are told
      // apart: "Open at page 65 of the Project Appraisal Document for P130164 in the World Bank's PDF".
      pageLinkMore: (docType: string, pid: string) => ` of the ${docType} for ${pid} in the World Bank's PDF`,
      pageLines: {
        scan_annex: "where the {part} starts",
        longest_pad: "the first page I sent to the parser",
        large_plan: "where the plan's table starts",
        other_language: "where the first numbered paragraph is",
        over_parser_limit: "where part 2 starts, to check the page numbers",
      } as Record<string, string>,
      // A spanning note's place in a card, for a screen reader.
      spanName: "Layout parser, outcome and page",
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
      // The quote check on proposed lessons (ticket 29), which Lessons > Waiting for review links to.
      lessons_verified: {
        title: "Proposed lessons with their quote found",
        definition:
          "How many of the lessons I proposed from completion reports and their reviews had their quote word for " +
          "word on the page and in the passage they cite, out of every lesson I proposed. I drop the others and " +
          "never change a quote to make it fit.",
      },
      latest_activities_with_confirmed_first_listing_read: {
        title: "First listing confirmed",
        definition:
          "How many activity entries in the latest plan versions I could trace back to the plan version that first " +
          "listed them. I count an entry only when I also read that version's whole table. I confirm a first " +
          "listing only when I have read every older or undated plan version in the project's document list.",
      },
      // Three datasets share the name Contract awards, so this one names its years, as the dashboard
      // does; the measure counts only that dataset (design review r6 P2).
      projects_with_contracts_lacking_step_reference: {
        title: "Projects with contracts that lack a STEP reference",
        definition:
          "How many projects have at least one contract with no STEP reference. I count them out of every project " +
          "with a contract in Contract awards since fiscal 2020.",
      },
      // The fiscal years stay in the registry's known gap, so these name no years (CLAUDE.md rule 9).
      gap_years_contracts_in_local_currency: {
        title: "Award-notice contracts in local currency",
        definition:
          "How many of the contracts I built from award notices have their amount in local currency. I build " +
          "these contracts only for the fiscal years that no awards dataset covers.",
      },
      gap_years_projects_in_local_currency: {
        title: "Projects with award-notice contracts in local currency",
        definition:
          "How many projects have a contract with its amount in local currency, among the contracts I built from " +
          "award notices. I count them out of every project with a contract I built from those notices. I build " +
          "these contracts only for the fiscal years that no awards dataset covers.",
      },
      // The document search's Ready for number: its title repeats the cell's own words (review r7 B1).
      passages_embedded: {
        title: "Passages you can search",
        definition: "How many of the passages I read you can search. I count them out of every passage I read.",
      },
      // The project reports' check (ticket 18): their Read well column counts pages across both routes.
      document_pages_paragraph_numbering_found: {
        title: "Paragraph numbers found",
        definition:
          "How many body pages of the reports that number their paragraphs show a paragraph number I could find. " +
          "A passage keeps its paragraph's number, so a citation can name it as the report does.",
      },
      // A document collection's projects, in its Coverage cell (the 18 brief, section 6.1; design review
      // r2 B1): the projects its documents belong to, and the pilot projects I read documents for. The
      // pilot projects are those of the sectors, countries and fiscal years that config/slice.toml names,
      // which the row's caption shows, so these words name none of them (CLAUDE.md rule 9).
      documents_read_projects: {
        title: "Projects with documents read",
        definition: "How many projects the documents I read belong to. I count a project once when I read at least one of its documents.",
      },
      slice_projects_read: {
        title: "Pilot projects read",
        definition:
          "How many pilot projects I read at least one document of, out of every pilot project. The pilot projects " +
          "are those of the sectors, countries and fiscal years the row's caption names, by their Board date. I read " +
          "the documents of each one I can, within my daily page limit, so some wait for a later run.",
      },
      slice_projects: {
        title: "Pilot projects",
        definition:
          "The projects of the sectors, countries and fiscal years the row's caption names, by their Board date. I " +
          "read the documents of each one I can, within my daily page limit.",
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
      // A Read well shortfall lacks nothing the registry names, so it says what went wrong, as the
      // gap's sentence does: "30 of 175 body pages I couldn't read without errors."
      unread: (part: string, whole: string, noun: string, date: string) =>
        `${part} of ${whole} ${noun} I couldn't read without errors. Measured ${date}.`,
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
      // A hard document whose hard part I couldn't read (a stress shelf outcome of Gap), as one more
      // sentence under "What holds it back", after the top two gaps. {link} is an in-page link to the
      // section "The hardest documents I read"; {pid} is set in mono (the 18 brief, section 6.2).
      shelfGapOne: "I couldn't read the {part} in the {docType} for {pid}, one of {link}.",
      shelfGapMany: "I couldn't read parts of {count} of {link}, such as the {part} in the {docType} for {pid}.",
      shelfLink: "the hardest documents I read",
      // The part of a stress shelf document I couldn't read: the hard part a scan_annex entry names in
      // config/slice.toml, or, for the other kinds, what that kind reads.
      shelfParts: {
        risk_annex: "risk annex",
        longest_pad: "pages",
        large_plan: "table",
        other_language: "text",
        over_parser_limit: "pages",
      } as Record<string, string>,
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
        get_lessons: "the quote check on proposed lessons",
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
          "Independent Evaluation Group (IEG) ratings, with exact counts, then the documents I read of each type, " +
          "by the fiscal year they were disclosed. Each source's rows are counted as its Coverage column in Strata " +
          "counts them, so its years add up to that number on the same date. The award notices for fiscal 2017 to " +
          "2019 count one row for each contract. It is the table for the chart of contract-award rows.",
        // A row of documents of one type, after the sources' rows (ticket 18).
        documentRows: "{type}, documents read",
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
        // Three short sentences, so the reader never backtracks (design review r2 P10).
        routesAbout:
          "The share of pages each reading route read well, for routes with {fewest} pages or more. The routes are " +
          "the published text and the layout parser, which reads scans and tables. The pages come from Procurement " +
          "Plans and project reports.",
        route: "Route",
        freshness: "Freshness, links and pages read well, by source",
        freshnessAbout:
          "Each source's latest data, how often it updates, how late it is, its link counts and its status. The " +
          "last rows give the Procurement Plan and project report pages each reading route read well. It is the " +
          "table for the two charts of shares.",
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

  // The Lessons pages (ticket 29; the 29 design brief, section 5): the library of lesson cards, the review
  // queue only lesson reviewers see, and the review page for one item. Lesson statements, quotes and
  // reasons are data from the server, never words here. Templates' {slots} are filled with values the
  // server returns, each number by Num, so the browser counts nothing.
  lessons: {
    // Spells out ICR, IEG and PPAR once on each Lessons screen (DESIGN.md section 7, rule 10).
    sourcesNote:
      "Lessons come from Implementation Completion and Results Reports (ICRs), and from ICR Reviews and Project " +
      "Performance Assessment Reports (PPARs) by the Independent Evaluation Group (IEG).",
    tabs: {
      label: "Lesson pages",
      library: "Lessons",
      queue: "Waiting for review ({waiting})",
      showingLibrary: "Showing Lessons.",
      showingQueue: "Showing Waiting for review.",
    },
    queueTitle: "Waiting for review",
    // The kinds, stages and risk factors come from config/lessons.toml with the server's answers.
    kinds: { new: "New lesson", recheck: "Re-check", cross_check: "Cross-check" } as Record<string, string>,
    // The evidence badges (DESIGN.md section 5, Status badge), by the server's ieg_status.
    badges: {
      restated: "Restated by IEG",
      ieg_lesson: "IEG's lesson",
      awaiting: "Awaiting IEG review",
      not_restated: "Rests on the ICR alone",
      mayRepeat: "May repeat a lesson",
      overdue: "Overdue",
      rechecking: "Being re-checked",
    },
    // The library (section 5.2).
    library: {
      loading: "Loading the library.",
      countAll: "Showing all {total} lessons in the library, newest first.",
      countOne: "Showing the one lesson in the library.",
      countRange: "Showing {from}–{to} of {total} lessons in the library, newest first.",
      reviewerLink: "Go to Waiting for review",
      outOfRangeTitle: "There is no page {page} in the library.",
      outOfRangeBody: "The library has {pages} pages.",
      outOfRangeBodyOne: "The library has one page.",
      firstPage: "Go to the first page",
      error: "I couldn't load the library because the data service didn't answer.",
      permission:
        "Your account can't read Strata's tables, so I can't show the library. Ask your workspace admin for read " +
        "access to the strata catalog.",
      list: "Lessons in the library",
    },
    card: {
      eyebrow: "{kind} · {stage}",
      quote: '"{quote}"',
      decided: "A lead procurement specialist decided version {version} on {date}, after an accredited procurement specialist recommended it.",
      rules: "Its projects followed {edition}.",
      rulesUnknown: "I couldn't tell which rules the project followed.",
      rechecking: "Reviewers started a re-check on {date}.",
      compactDecided: "Version {version}, decided on {date}.",
      sources: "Sources",
      moreSources: "Show {count} more sources",
      moreSource: "Show one more source",
      fewerSources: "Show fewer sources",
      // A source chip's words: "ICR ¶54", "ICR Review 10.b", and its accessible name.
      chipParagraph: "{doc} ¶{para}",
      chipSection: "{doc} {section}",
      // A chip's accessible name is its own words, then these, so it reads "ICR ¶54, opens the source: ...".
      chipNameJoin: ", ",
      chipNameParagraph: "opens the source: {doc} for {pid}, paragraph {para}, page {page}",
      chipNameSection: "opens the source: {doc} for {pid}, section {section}, page {page}",
      // One source in a source line: "ICR, P130164, October 10, 2019, paragraph 54, page 23".
      sourceParagraph: "{doc}, {pid}, {date}, paragraph {para}, page {page}",
      sourceSection: "{doc}, {pid}, {date}, section {section}, page {page}",
      sourceJoin: "; ",
      sourceEnd: ".",
      tags: "Tags",
    },
    recheck: {
      button: "Ask for a re-check",
      label: "Why should reviewers re-check this lesson?",
      helper:
        "Your reason and your name go to the lesson reviewers for {region}. The lesson stays in the library while " +
        "they re-check it.",
      submit: "Ask for a re-check",
      cancel: "Cancel",
      empty: "Write a reason, so the reviewers know what to look at.",
      saving: "Saving",
      saved: "You asked for a re-check on {date}.",
      announced: "Saved. The re-check is now in the review queue for {region}.",
      open: "Someone already asked for a re-check of this lesson on {date}.",
      failed: "I couldn't ask for a re-check just now. Your text is still here.",
      tryAgain: "Try again",
    },
    // Waiting for review (section 5.3).
    queue: {
      purpose:
        "I propose lessons from Implementation Completion and Results Reports (ICRs), and from ICR Reviews and " +
        "Project Performance Assessment Reports (PPARs) by the Independent Evaluation Group (IEG). An accredited " +
        "procurement specialist recommends each lesson, and a different lead procurement specialist decides within " +
        "{limit} business days. This page lists lessons for {regions}, and only lesson reviewers can open it.",
      checkLink: "See this measure on Data readiness",
      groups: { you: "Waiting for you", others: "With other reviewers" } as Record<string, string>,
      order: "Oldest first.",
      loading: "Loading the review queue.",
      emptyTitle: "I have no lessons waiting for review.",
      emptyBody:
        "When a new ICR, ICR Review or PPAR comes in, the lessons I propose from it wait here for a recommendation " +
        "and a decision.",
      emptyLink: "Go to Lessons",
      error: "I couldn't load the review queue because the data service didn't answer.",
      permission:
        "Your account can't read Strata's tables, so I can't show the review queue. Ask your workspace admin for " +
        "read access to the strata catalog.",
      noAccessTitle: "I show this page only to lesson reviewers.",
      noAccessBody:
        "Lesson reviewers are the accredited and lead procurement specialists named for each region. Your account " +
        "isn't one of them, so the lessons waiting for review stay hidden from you.",
      noAccessLink: "Go to Lessons",
      decidedTitle: "Decided in the last {days} days",
      decidedNone: "No lesson was decided in the last {days} days.",
      // The count line's noun: "Showing 1–20 of 34 decisions, newest first" (copy.table).
      decidedNoun: "decisions, newest first",
      decidedNounOne: "decision, newest first",
      decidedCaption: "Lessons decided in the last {days} days",
      decidedSource: "Strata's lesson review records.",
      columns: { lesson: "Lesson", outcome: "Outcome", decided: "Decided", days: "Days from publication" },
      daysDefinition: "report public to decision",
      recheckDays: "Re-check",
      project: "{name} ({pid})",
      outcomes: {
        added: "Added as version 1",
        merged: "Added as evidence",
        rejected: "Rejected",
        kept: "Kept at version {version}",
        changed: "Changed to version {version}",
        retired_wrong: "Retired as wrong",
        retired_outdated: "Retired as out of date",
      } as Record<string, string>,
    },
    // A queue row (section 5.4), and the same status and clock lines on the review page.
    row: {
      statusYou: {
        recommendation: "{kind} · needs your recommendation",
        decision: "{kind} · needs your decision",
        cross_check: "{kind} · needs your cross-check",
      } as Record<string, string>,
      statusOthers: {
        recommendation: "{kind} · needs a recommendation",
        decision: "{kind} · needs a decision",
        cross_check: "{kind} · needs a cross-check",
      } as Record<string, string>,
      statusDecided: "{kind} · decided",
      sourceIcr: "From the ICR for {name} ({pid}), paragraph {para}, page {page}. {region}.",
      sourceIcrReview: "From IEG's ICR Review for {name} ({pid}), section {section}, page {page}. {region}.",
      sourcePpar: "From IEG's PPAR for {name} ({pid}), paragraph {para}, page {page}. {region}.",
      sourceCrossCheck: "A lead in {region} decided this on {date}.",
      clock: "Day {day} of {limit} business days, due {due}.",
      clockLastDay: "Day {limit} of {limit} business days, due today.",
      clockOverdue: "Due {due}, {days} business days ago.",
      clockOverdueOne: "Due {due}, one business day ago.",
      clockCrossCheck: "Due {due}.",
      clockTooltip: "Business days since {start}. Weekends and World Bank holidays don't count.",
      nextRecommend: "Waiting for an accredited procurement specialist to recommend it.",
      nextDecide: "{name} recommended {phrase} on {date}.",
      nextAsked: "{name} asked for a re-check on {date}.",
      nextCrossCheck: "{name} in {region} disagreed with the decision on {date}, so a re-check started.",
      nextEdition: "I started a re-check on {date} because {edition} took effect.",
      phrases: {
        add: "adding it",
        repeat: "adding it as evidence to another lesson",
        reject: "rejecting it",
        keep: "keeping it as it is",
        change: "changing it",
        retire_wrong: "retiring it",
        retire_outdated: "retiring it",
      } as Record<string, string>,
      // Why you can't act (section 5.4), by the server's reason code.
      whyNot: {
        same_person: "You recommended it, so a different lead decides.",
        own_project: "You work on {name} ({pid}), so another reviewer takes this one.",
        not_a_lead: "Only a lead procurement specialist can decide it.",
        no_lead_free: "No lead for {region} can decide it, because each one works on {name} ({pid}).",
        same_region: "Reviewers outside {region} cross-check this decision.",
        other_region: "Lesson reviewers for {region} recommend and decide this lesson.",
      } as Record<string, string>,
    },
    // The review page (sections 5.5 to 5.13).
    review: {
      breadcrumbBack: "Waiting for review",
      loading: "Loading this lesson.",
      notFoundTitle: "I have no lesson review with the ID {id}.",
      notFoundBody: "Check the link, or find the lesson in Waiting for review.",
      notFoundLink: "Go to Waiting for review",
      error: "I couldn't load this lesson because the data service didn't answer.",
      permission:
        "Your account can't read Strata's tables, so I can't show this lesson. Ask your workspace admin for read " +
        "access to the strata catalog.",
      pageTitle: "{statement}, Waiting for review",
      clockRegion: "{clock} {region}.",
      decidedOn: "Decided on {date}, {days} days after the report became public.",
      decidedOnRecheck: "Decided on {date}.",
      decidedTooltip: "Days from {published}, when the report became public, to the decision on {date}.",
      evidenceTitle: "The evidence",
      eyebrow: "Why · evaluation",
      titleIcr: "Implementation Completion and Results Report, paragraph {para}",
      titleIcrReview: "ICR Review, section {section}",
      titlePpar: "Project Performance Assessment Report, paragraph {para}",
      restatedCaption: "IEG's review of this ICR restated the lesson.",
      checkedOnPage: "I found this quote word for word on page {page}.",
      notCheckedLesson: "whether the lesson follows from it.",
      awaitingNote: "IEG has not published its review of this ICR yet, so the lesson rests on the ICR alone.",
      aloneNote: "I found no restatement of this lesson in IEG's ICR Review of {date}, so it rests on the ICR alone.",
      tagsTitle: "How I tagged it",
      tagsCaption: "I chose these from fixed lists when I proposed the lesson.",
      tagsCaptionVersion: "These are the lesson's tags at version {version}.",
      terms: {
        risk_factors: "Risk factors",
        stage: "Stage",
        kind: "Kind",
        rules: "Rules followed",
        project: "Project",
        sector: "Sector",
      },
      summaryTitle: "My summary of the evidence",
      summaryWriting: "I'm still writing my summary. The quotes above are complete, so you can decide without it.",
      summaryReady: "My summary is ready.",
      summaryShow: "Show my summary",
      summaryNothing: "I have nothing to add to the quotes above.",
      summaryNoneSurvived: "I removed every sentence of my summary, because none passed my checks.",
      summaryFailed:
        "I couldn't write a summary of this evidence. The quotes above are complete, so you can still decide.",
      summaryRewriting: "I'm writing my summary.",
      summaryTryAgain: "Try again",
      repeatsTitle: "This may repeat a lesson in the library",
      repeatsNone: "I found no lesson in the library that this repeats.",
      historyOpen: "What has happened so far",
      historyDone: "What happened",
      roles: {
        accredited: "accredited procurement specialist",
        lead: "lead procurement specialist",
      },
      history: {
        proposed: "I proposed this lesson from the {doc} for {name} ({pid}). The report became public on {date}.",
        restatement: "I attached IEG's restatement from its ICR Review of {date}.",
        recommended: "{name}, {role}, recommended {phrase}.",
        recommendedChange: "{name}, {role}, recommended changing it.",
        decided: "{name}, lead procurement specialist, {phrase}.",
        asked: "{name} asked for a re-check.",
        edition: "I started a re-check because {edition} took effect for the lesson's projects.",
        crossCheckStarted: "{name} disagreed with a decision in a cross-check, so a re-check started.",
        agreed: "{name}, {region}, agreed with the decision.",
        disagreed: "{name}, {region}, disagreed with the decision.",
        reason: 'Reason: "{reason}"',
        was: "Was: {value}",
        now: "Now: {value}",
        wordingChanged: "{name} changed the wording before adding it.",
        merged: "Rested on {quotes} quotes from {reports} reports.",
        mergedNow: "Rests on {quotes} quotes from {reports} reports.",
        decisions: {
          add: "added it to the library as version 1",
          repeat: 'added its quote as evidence to "{target}", which became version {version}',
          reject: "rejected it",
          keep: "kept it at version {version}",
          change: "changed it, which became version {version}",
          retire_wrong: "retired it because it was wrong",
          retire_outdated: "retired it because it no longer applies",
        } as Record<string, string>,
      },
      // When you can't act (section 5.11), by reason code: the same sentences as the row's, in full.
      cannot: {
        same_person: "You recommended this lesson, so a different lead procurement specialist decides it.",
        own_project: "You work on {name} ({pid}), so you can't recommend or decide on this lesson.",
        not_a_lead: "Only a lead procurement specialist can decide this lesson.",
        same_region: "Reviewers outside {region} cross-check this decision.",
        other_region: "Lesson reviewers for {region} recommend and decide this lesson.",
        no_lead_free: "No lead for {region} can decide this lesson, because each one works on {name} ({pid}).",
      } as Record<string, string>,
    },
    // The decision form (section 5.10), by the item's kind and the viewer's act.
    form: {
      recommendTitle: "Your recommendation",
      decideTitle: "Your decision",
      crossCheckTitle: "Your cross-check",
      isNew: "Is this a new lesson?",
      yesNew: "Yes, it is new",
      repeats: 'No, it repeats "{statement}" (version {version})',
      repeatFeedforward: 'If a lead agrees, I add its quote to "{statement}" as more evidence.',
      whatShouldHappen: "What should happen to this lesson?",
      keep: "Keep it as it is",
      change: "Change its wording or tags",
      retireWrong: "Retire it, because it was wrong",
      retireOutdated: "Retire it, because it no longer applies",
      agreeLegend: "Do you agree with the decision?",
      agree: "Yes, I agree",
      disagree: "No, I disagree",
      crossCheckIntro:
        "A lead in {region} decided this on {date}. Each quarter, reviewers outside a region check {percent} " +
        "percent of its decisions, so regions decide alike.",
      reasonLabel: "Your reason",
      reasonHelperRecommend: "The lead reads your reason before deciding. It stays in the record with your name.",
      reasonHelperDecide: "It stays in the record with your name, beside the recommendation.",
      reasonHelperCrossCheck: "Optional if you agree. If you disagree, the reviewers for {region} read it, and a re-check starts.",
      counter: "{count} characters left.",
      counterOne: "One character left.",
      editorToggle: "Change the wording or tags first",
      editor: {
        statement: "Lesson statement",
        riskFactors: "Risk factors",
        stage: "Stage",
        kind: "Kind",
        fixed: "Quotes and pages can't be changed. They are the record.",
      },
      recommendAdd: "Recommend adding it",
      recommendReject: "Recommend rejecting it",
      add: "Add to the library",
      reject: "Reject, with a reason",
      recommend: "Recommend",
      saveDecision: "Save this decision",
      saveCrossCheck: "Save the cross-check",
      saving: "Saving",
      feedforwardRecommend:
        "Either way, a different lead procurement specialist decides next. Nothing enters the library until a lead " +
        "decides.",
      feedforwardAdd: "Adding it makes it version 1. From then on I can cite it in answers and drafts.",
      feedforwardRepeat:
        'Adding it puts its quote under "{statement}" as more evidence, and that lesson becomes version {version}.',
      feedforwardRecheckRecommend:
        "A different lead procurement specialist decides next. The lesson stays in the library while reviewers " +
        "re-check it.",
      feedforwardKeep: "The lesson stays at version {version}, and the re-check ends.",
      feedforwardChange:
        "I save your change as version {next}. Version {version} stays on record, and drafts that cite it keep " +
        "citing it until their authors update them.",
      feedforwardRetire: "I stop citing it in new answers. Older drafts that cite it can still open it.",
      errors: {
        noReasonRecommend: "Write your reason first. The lead reads it before deciding.",
        noReasonDecide: "Write your reason first. It stays in the record with your name.",
        noReasonCrossCheck: "Write your reason first. The reviewers for {region} read it.",
        noChoiceNew: "Choose whether this lesson is new or repeats one in the library.",
        noChoiceRecheck: "Choose what should happen to this lesson.",
        noChoiceCrossCheck: "Choose whether you agree with the decision.",
        statement: "Write the lesson in one sentence.",
        statementLong: "Use at most {count} characters.",
        riskFactors: "Choose at least one risk factor.",
        stage: "Choose a stage.",
        kind: "Choose a kind.",
      },
      failed: "I couldn't save your {act} just now. Your reason is still here.",
      acts: { recommend: "recommendation", decide: "decision", cross_check: "cross-check" } as Record<string, string>,
      tryAgain: "Try again",
      staleLead: "{name} {act} this lesson on {date}, while you had it open.",
      staleActs: { recommend: "recommended", decide: "decided on", cross_check: "cross-checked" } as Record<string, string>,
      staleBody: "Your reason was not sent. You can copy it from the box below.",
      staleReason: "Your reason, not sent",
      lostRole: "Your account is no longer on the list of lesson reviewers, so I couldn't save this.",
      nextItem: "Open the next lesson waiting for you",
      backToQueue: "Back to Waiting for review",
      seeInLibrary: "See it in the library",
    },
    // The outcome panel (section 5.12, after your act; 5.13, on a decided record).
    outcome: {
      recommended: { lead: "You recommended adding this lesson.", body: "A different lead procurement specialist decides next, by {date}." },
      recommendedRepeat: { lead: 'You recommended adding this as evidence to "{target}".', body: "A different lead procurement specialist decides next, by {date}." },
      recommendedReject: { lead: "You recommended rejecting this lesson.", body: "A different lead procurement specialist decides next, by {date}." },
      recommendedRecheck: { lead: "You recommended {phrase}.", body: "A different lead procurement specialist decides next, by {date}." },
      added: { lead: "You added this lesson to the library as version 1.", body: "From now on I can cite it in answers and drafts." },
      merged: { lead: 'You added this quote to "{target}" as evidence.', body: "That lesson is now version {version}." },
      rejected: { lead: "You rejected this lesson.", body: "It stays out of the library, and I keep it with both reasons in the record." },
      kept: { lead: "You kept this lesson at version {version}.", body: "The re-check is over." },
      changed: { lead: "You saved version {version} of this lesson.", body: "Version {previous} stays on record." },
      retired_wrong: { lead: "You retired this lesson because it was wrong.", body: "I no longer cite it in new answers. Older drafts that cite it can still open it." },
      retired_outdated: { lead: "You retired this lesson because it no longer applies.", body: "I no longer cite it in new answers. Older drafts that cite it can still open it." },
      agree: { lead: "You agreed with this decision.", body: "I saved your cross-check." },
      disagree: { lead: "You disagreed with this decision.", body: "A re-check is now waiting for the reviewers for {region}, with your reason." },
      record: {
        added: { lead: "Added to the library as version 1 on {date}.", body: "See the history for both reasons." },
        merged: { lead: 'Added as evidence to "{target}" on {date}.', body: "That lesson became version {version}." },
        rejected: { lead: "Rejected on {date}.", body: "It stays out of the library, with both reasons in the record." },
        kept: { lead: "Kept at version {version} on {date}.", body: "See the history for both reasons." },
        changed: { lead: "Changed to version {version} on {date}.", body: "See the history for both reasons." },
        retired_wrong: { lead: "Retired because it was wrong, on {date}.", body: "See the history for both reasons." },
        retired_outdated: { lead: "Retired because it no longer applies, on {date}.", body: "See the history for both reasons." },
        agree: { lead: "A reviewer in {region} agreed with this decision on {date}.", body: "See the history for the reasons." },
        disagree: { lead: "A reviewer in {region} disagreed with this decision on {date}.", body: "A re-check started in the region that decided." },
      } as Record<string, { lead: string; body: string }>,
    },
    // Ticket 40's previews and as-of view (section 5.15): copy it can use when it lands.
    preview: {
      title: "You are previewing the {view} view, which has no review queue.",
      body: "Implementing agency officers and the public see only the lessons in the library.",
      asOf: "You are seeing this as of {date}, so you can't recommend or decide here.",
    },
    // The words the server writes into the queue's sentences (src/strata/knowledge/lessons/copy.json, written
    // by web/lint/server-copy.ts), so it chooses each count's form and marks each number for Num.
    server: {
      lead: {
        both: "{you} {lessonsYou} {beYou} waiting for you, and {others} {beOthers} with other reviewers.",
        youOnly: "{you} {lessonsYou} {beYou} waiting for you.",
        othersOnly: "Nothing is waiting for you. {others} {lessonsOthers} {beOthers} with other reviewers.",
        oldest: " The oldest has used {day} of its {limit} business days.",
        overdue: " {overdue} {have} passed {itsTheir} {limit} business days.",
      },
      check: {
        dropped:
          "Every lesson here has a quote I found word for word on the page it cites. In the last {days} days I " +
          "dropped {dropped} proposed {lessons} whose quote was not on {itsTheir} cited page.",
        none:
          "Every lesson here has a quote I found word for word on the page it cites. In the last {days} days, every " +
          "lesson I proposed passed that check.",
      },
      forms: {
        lesson: { one: "lesson", many: "lessons" },
        be: { one: "is", many: "are" },
        have: { one: "has", many: "have" },
        itsTheir: { one: "its", many: "their" },
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
