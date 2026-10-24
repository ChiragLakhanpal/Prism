// Every string the design gallery shows: its labels and the sample content its components
// display. The gallery is never shipped, so these strings stay out of web/src/copy.ts, but
// the gate's copy lint checks them the same way (DESIGN.md section 7). Sample IDs such as
// P000000 and names such as Sample Water Agency are made up on purpose, so no sample can be
// mistaken for a record. Within each sample, the counts agree: a sentence, its table, its
// check line and its steps count the same things.

export const galleryCopy = {
  title: "Design gallery",
  purpose:
    "This page shows every Strata component in each of its states, for building screens and for design reviews. Only development builds have it.",
  sampleNote: "Everything on this page is sample content for checking the design. None of it is a finding.",
  listLabel: "Components",
  allComponents: "All components",
  sampleEmail: "ana.example@worldbank.org",
  sampleDate: "2026-10-21",

  pages: {
    navigation: {
      title: "Navigation, box band and footer",
      purpose: "Every page shares this frame. This page shows Projects as the selected tab.",
    },
    pages: {
      title: "Page header and page alerts",
      purpose:
        "Every page starts with its title and one or two sentences that say what it is for. Alerts above the title say what I can't show, errors first.",
    },
    buttons: {
      title: "Buttons",
      purpose: "Buttons act and links navigate. Each screen has one primary button at most.",
    },
    links: {
      title: "Links and tabs",
      purpose:
        "Text links are always underlined. Tabs on a light surface use a primary underline. On a phone they stay on one row, and you scroll it sideways.",
    },
    cards: {
      title: "Cards and empty states",
      purpose: "Cards hold a group of facts. An empty state says what will appear and what to do next.",
    },
    alerts: {
      title: "Alerts",
      purpose: "An alert is one sentence in a state's colors, with its icon and a left border.",
    },
    badges: {
      title: "Status badges",
      purpose: "Each badge has its own icon shape and names its state in words.",
    },
    numbers: {
      title: "Numbers and terms",
      purpose:
        "Num writes every number by DESIGN.md's rules, and each table here shows the value a tool sent, the rule and what Num shows. A number you can check has a dotted underline. A term opens its definition from GLOSSARY.md.",
    },
    citations: {
      title: "Citations and checks",
      purpose: "Markers name their source. The check line, coverage line and removed box say how far to trust an answer.",
    },
    answer: {
      title: "Answer",
      purpose:
        "This page shows the body of a cited answer in each of its states. In each sample, the sentences, the table, the check line and the steps count the same things.",
    },
    box: {
      title: "The one box",
      purpose:
        "As you type, the box lists what Enter will do. An ID opens its page, and anything else offers Ask this. On a project or package page it holds a scope chip you can remove.",
    },
    "answer-panel": {
      title: "Answer panel",
      purpose:
        "The answer to a question asked from the box, in the page under the band. Each sample plays an answer stream the server wrote, recorded in tests/fixtures/api.",
    },
    evidence: {
      title: "Evidence card and drawer",
      purpose:
        "A marker's hover or focus shows the evidence card. A click opens the drawer beside the page, at the whole paragraph with the matching words highlighted. Below 768 px the drawer fills the screen.",
    },
    document: {
      title: "Document passage",
      purpose: "A passage is one numbered paragraph, word for word, with the matching words highlighted.",
    },
    table: {
      title: "Table",
      purpose:
        "A table has a title sentence, a count line, units in the column heads and a source line. The title, count and source show only with the rows. Below 768 px each row becomes a card. A table with wide columns becomes cards below 1024 px instead.",
    },
    skeleton: {
      title: "Skeleton",
      purpose:
        "Skeletons are static blocks sized to the content they stand in for. Each line is as tall as the line of text it holds a place for, so nothing moves when the content arrives.",
    },
    "plan-check": {
      title: "Plan check",
      purpose:
        "Check a plan's parts: the trail above it, the check pill, and the plan check as a table from 1024 px and as activity cards below it. Activities with no signals fold behind a button.",
    },
    icons: {
      title: "Icons",
      purpose:
        "Strata uses these lucide icons at 16 px. Each one is hidden from screen readers when a word beside it says the same thing.",
    },
  },

  states: {
    default: "Default",
    disabled: "Disabled",
    loading: "Loading",
    withIcon: "With an icon",
    iconOnly: "Icon only",
    empty: "Empty",
    error: "Error",
    ready: "Ready",
    streaming: "Streaming",
    abstained: "Abstention",
    refused: "Refusal",
    missing: "Missing",
    slow: "Loading, after one second",
    slowTwo: "Loading, after two seconds",
    withText: "With text",
    opened: "Opened before",
    active: "Open in the drawer",
    withLink: "With a link",
    withoutLink: "Without a link",
    withGap: "With a gap",
    withoutGap: "With nothing missing",
    french: "A passage in French",
    hint: "Focused and empty: the hint",
    project: "A project ID",
    loan: "A loan number",
    loanPending: "A bare number, before its lookup finds a loan",
    activity: "A STEP reference",
    activityPending: "A STEP reference, while it is looked up",
    question: "A question",
    questionWithId: "A question that holds a project ID",
    notFound: "An ID no record holds",
    lookupFailed: "A lookup that failed",
    scoped: "On a project page, with its scope chip",
    streamingSteps: "Streaming: two steps done, one running, one to do",
    allChecked: "Ready, with every check passed",
    readyRemoved: "Ready, with one sentence removed",
    unsupported: "Every sentence failed a check",
    emptyScoped: "Nothing found, within a project",
    emptyUnscoped: "Nothing found, across all projects",
    dropped: "The connection dropped",
    asOf: "Asked as of a date",
    preview: "Asked in a preview of the public view",
    card: "Evidence card",
    cardVisited: "Evidence card, for a source opened before",
    fromAnswer: "Opened from the answer",
    switcher: "A sentence with two sources",
    fromLink: "Opened from a link",
    record: "A record",
    unknown: "An ID no source has",
    drawerPreview: "In a preview",
  },

  notes: {
    bar:
      "The navy bar at the top of this page is the sample. Below 1024 px its tabs and the view switch move into the Menu. The box band under it is the sample of the box and the stamp, and the footer is the same on every page.",
  },

  sections: {
    header: "A page with an ID in its title, and its empty state",
    notFound: "Not found",
    pageAlerts: "The alert slot, with every alert a page can show",
    bar: "Navy bar",
    box: "The one box",
    stamp: "Data-freshness stamp",
    variants: "Primary, secondary and ghost",
    flush: "A ghost button under text",
    onPage: "A ghost button on the page background",
    textLink: "Text link",
    tabs: "Tabs on a light surface",
    tabsLater: "Tabs with a later one selected",
    cardsBelowLg: "Cards below 1024 px, for a table with wide columns",
    card: "Card",
    emptyState: "Empty state",
    signals: "Signals",
    readiness: "Data readiness",
    planChecks: "Plan checks",
    breadcrumb: "The trail above a project's pages",
    pill: "Check pill",
    planReady: "A checked plan, with two activities folded",
    planOpen: "The fold open",
    planPartial: "A partial check: one activity the plan gives no planned date for",
    ratios: "Ratios",
    formats: "Thousands, K, M and B, and decimals",
    counts: "Counts, years and dates",
    checkable: "A number you can check",
    terms: "A term with its definition",
    markers: "Citation markers",
    checkLine: "Check line",
    coverage: "Coverage line",
    removed: "Removed box",
    steps: "Steps",
    states: "States",
  },

  // The Numbers page's three tables: the value a tool sent, the rule Num follows and what it
  // shows (DESIGN.md sections 6 and 7).
  reference: {
    source: "DESIGN.md sections 6 and 7.",
    headers: {
      part: "Part",
      whole: "Whole",
      style: "Style",
      value: "Value the tool sent",
      rule: "Rule",
      shows: "Num shows",
    },
    sentence: "Sentence",
    table: "Table",
    ratios: {
      title: "Num never writes a frequency or a percentage from fewer than 20 cases.",
      noun: "ratios",
      rules: [
        "Under 20 cases, Num shows only the count.",
        "From 20 to 49 cases, it adds about N in 10.",
        "From 50 cases, it adds a whole percentage.",
        "In a table or a chart, it writes % for percent.",
        "A share that rounds to 0 but is not 0 reads less than 1 percent.",
      ],
    },
    formats: {
      title: "Num shortens large numbers with K, M and B, and rounds each number by its size.",
      noun: "numbers",
      rules: [
        "Below 10,000, Num writes comma thousands.",
        "From 10,000, it writes K, with one decimal below 100K.",
        "From 100K, it drops the decimal.",
        "From a million, it writes M.",
        "From a billion, it writes B.",
        "Below 1, it keeps two decimals.",
        "From 1 to 100, it keeps one decimal.",
        "Above 100, it keeps no decimals.",
        "A STEP amount in a table keeps STEP's form, cents included, so it matches the record.",
      ],
    },
    counts: {
      title: "Num writes small counts as words, and dates by where they appear.",
      noun: "values",
      rules: [
        "A count from one to nine is a word.",
        "From 10, a count is a numeral.",
        "A year has no comma.",
        "In a sentence, a date has the full month.",
        "In a table, a date has the short month.",
      ],
    },
  },

  sample: {
    // The questions the recorded answer streams answer (tests/fixtures/agent/cases.toml).
    showcaseQuestion: "Why were works contracts in P130164 advertised again?",
    bridgesQuestion: "Which firms built the bridges in P130164?",
    boxQuestion: "Why were works contracts advertised again?",
    unknownProject: "P999999",
    boxProject: "P130164",
    boxLoan: "IDA-60290",
    primary: "Mark as checked",
    secondary: "Export to Word",
    ghost: "Show them",
    flushText: "Two of the 24 packages were advertised again.",
    icon: "Close the source",
    textLink: "See which data I hold",
    tabsLabel: "Project sections",
    tabs: ["Summary", "Procurement", "Timeline", "Documents", "Connections"],
    cardTitle: "Sample Water Agency, Procurement Plan of October 9, 2026",
    cardBody: "Eight activities were checked. One needs a look and two are worth watching.",
    cardSource: "A sample plan check made for the gallery, in STEP's columns.",
    emptyTitle: "I have nothing to brief you on yet.",
    emptyBody:
      "When my fixed checks find a change in a plan or project you work on, I list it here, with the drafts waiting for you.",
    emptyLink: "Go to Data",
    info: "I can't show the public preview yet, so you are seeing the World Bank staff view.",
    success: "You exported the draft to Word.",
    warning: "Two reports disagree about the closing date.",
    error: "Your account can't read the data I hold yet, so ask the person who shared Strata with you for access.",
    neutral: "I removed one sentence because no record supports its number.",
    numTooltip: "Matches paragraph 54 of the completion report for P000000.",
    term: "Comparable",
    measureTitle: "Linked to a project",
    measureBody: "The share of contract awards that carry a project ID I can join on.",
    measureRows: ["Linked", "All rows", "Measured"],
    markerSource: "Implementation Completion and Results Report, June 30, 2021, paragraph 54",
    markerSecond: "Implementation Status and Results Report, March 4, 2020, paragraph 12",
    // Each sentence says only what its own source says. Marker 1's preview quotes paragraph 54,
    // the passage on the Document page, and marker 2 cites a later status report.
    markerPreview:
      "The works contracts were advertised again in 2017 after all bids were rejected. The contracts were signed in March 2018, five months after the date in the first Procurement Plan.",
    sentenceBefore: "The works contracts were advertised again after all bids were rejected, and they were signed five months late.",
    sentenceAfter: "The works were still under way in March 2020.",
    // The Answer page's own sentences, so a change to the Citations sample cannot change what
    // the Answer's check line counts. They hold three numbers: five, three and four. "A later
    // status report", not "the latest": a saved answer keeps its words after a newer report
    // arrives, and marker 2's source line gives the report's date.
    answerSentences: [
      "All bids for the works contracts were rejected, and the contracts were signed five months late.",
      "A later status report found that three of the four works contracts were complete.",
    ],
    coverageNoun: "matching packages",
    coverageGap: "15 lacked the STEP reference that links notice to contract.",
    removed: [
      {
        sentence: "Bids were usually opened within 45 days.",
        reason: "No record supports this number.",
        reasonJoined: "no record supports that number",
      },
      {
        sentence: "IDA financed the second phase in 2019.",
        reason: "No record supports this date.",
        reasonJoined: "no record supports that date",
      },
      {
        sentence: "The ICR called the delay avoidable.",
        reason: "The quote is not on the page it cites.",
        reasonJoined: "the quote is not on the page it cited",
      },
    ],
    // Words that stay capitalized when a removed sentence is reported.
    removedNames: ["IDA", "ICR"],

    // The steps each answer sample took. Each list matches its sample: the ready answer wrote
    // three sentences and removed one, the abstention found 12 packages and checked their 12
    // numbers, and the empty answer found nothing.
    steps: {
      read: { key: "read", running: "I'm reading your question.", done: "I read your question." },
      searchDocuments: {
        key: "search",
        running: "I'm searching the documents for P000000.",
        done: "I found 14 passages for P000000.",
      },
      searchNothing: {
        key: "search",
        running: "I'm searching the records and documents for P000000.",
        done: "I found no record or passage that answers this.",
      },
      searchComparables: {
        key: "search",
        running: "I'm looking for packages like this one.",
        done: "I found 12 comparable packages.",
      },
      write: { key: "write", running: "I'm writing the answer.", done: "I wrote three sentences." },
      verify: {
        key: "verify",
        running: "I'm checking each number against the records.",
        done: "I checked the numbers against the records and removed one sentence.",
      },
      verifyComparables: {
        key: "verify",
        running: "I'm checking each number against the records.",
        done: "I checked the 12 numbers in the table against the records.",
      },
    },
    runId: "run-0001",
    abstention: "I'm not giving a range: only 12 comparable packages. Here are all 12.",
    abstentionTitle: "The 12 comparable packages",
    abstentionNoun: "comparable packages",
    abstentionHeaders: ["Activity Reference No.", "Method", "Months from notice to contract"],
    abstentionRows: [
      ["KE-SAMPLE-000101-CW-RFB", "Request for Bids", "7.2"],
      ["KE-SAMPLE-000102-CW-RFB", "Request for Bids", "8.4"],
      ["KE-SAMPLE-000103-CW-RFB", "Request for Bids", "9.1"],
      ["KE-SAMPLE-000104-CW-RFB", "Request for Bids", "9.6"],
      ["KE-SAMPLE-000105-CW-RFB", "Request for Bids", "10.3"],
      ["KE-SAMPLE-000106-CW-RFB", "Request for Bids", "10.9"],
      ["KE-SAMPLE-000107-CW-RFB", "Request for Bids", "11.4"],
      ["KE-SAMPLE-000108-CW-RFB", "Request for Bids", "12.0"],
      ["KE-SAMPLE-000109-CW-RFB", "Request for Bids", "13.5"],
      ["KE-SAMPLE-000110-CW-RFB", "Request for Bids", "14.2"],
      ["KE-SAMPLE-000111-CW-RFB", "Request for Bids", "16.8"],
      ["KE-SAMPLE-000112-CW-RFB", "Request for Bids", "19.1"],
    ],
    emptyLead: "I found nothing in the records or documents that answers this.",
    emptyLinkText: "Data readiness",
    emptyTail: " shows which sources and years I have read so far.",
    refusal:
      "I don't score or rank suppliers. I can list the contracts a supplier signed on World Bank-financed projects, each with its award notice.",
    refusalLinkText: "How Strata works",
    refusalTail: " lists what I don't do, and why.",
    answerError:
      "I couldn't answer because the model that writes my answers did not respond, but your question is still in the box.",
    docType: "Implementation Completion and Results Report",
    pcode: "P000000",
    docDate: "2021-06-30",
    passage:
      "The works contracts were advertised again in 2017 after all bids were rejected. The second round drew five bids, and the contracts were signed in March 2018, five months after the date in the first Procurement Plan.",
    passageMatch: "advertised again in 2017 after all bids were rejected",
    passageFrench:
      "Les marchés de travaux ont été relancés en 2017 après le rejet de toutes les offres. Le second appel a reçu cinq offres.",
    passageFrenchMatch: "relancés en 2017",
    tableTitle: "Three of the four sample activities were signed after their planned date.",
    tableNoun: "activities",
    tableSource: "Sample rows made for the gallery, in STEP's columns.",
    tableHeaders: ["Activity Reference No.", "Method", "Estimated Amount (US$)", "Days late"],
    tableRows: [
      ["KE-SAMPLE-000001-CW-RFB", "Request for Bids", "1230000", "64"],
      ["KE-SAMPLE-000002-GO-RFQ", "Request for Quotations", "84500", "0"],
      ["KE-SAMPLE-000003-CS-QCBS", "Quality- and Cost-Based Selection", "312000", "131"],
      ["KE-SAMPLE-000004-CW-RFB", "Request for Bids", "2450000", "12"],
    ],
    tableEmptyTitle: "I have no activities for this plan yet.",
    tableEmptyBody: "Activities appear here once the plan's rows load from STEP.",
    tableError: "I couldn't load the activities in this plan.",
    // A plan check in check_plan's shape (web/src/lib/api.ts). The agency, the project and the
    // references are made up; the methods, statuses and the shape of each reason are STEP's and
    // check_plan's. Its counts agree with its rows.
    planCheck: {
      crumbProject: "Sample Water Project",
      crumbPlan: "Plan of Oct 9, 2026",
      pillPartial: { checked: 4, total: 5 },
      // The partial sample: KE-SAMPLE-000204-GO-RFQ gets a data note for its missing date.
      partialRef: "KE-SAMPLE-000204-GO-RFQ",
      partialMark: {
        mark: "data_note",
        reasons: [{ code: "no_planned_date", mark: "data_note", step: "Contract Completion", evidence_ids: ["sample-4"] }],
      },
      partialCounts: { checked: 4, not_fully_checked: 1, data_note: 2, marked: 4, unmarked: 1 },
      result: {
        tool: "check_plan",
        as_of: "2026-10-21",
        view: "staff",
        abstention: null,
        checks_run: ["own_dates", "estimate", "closing_date"],
        thresholds: { completion_passed_min_estimated_usd: "1000000.00", days_before_closing: 90, actual_to_estimate_ratio: "2.0" },
        counts: { activities: 5, checked: 5, not_fully_checked: 0, needs_a_look: 1, watch: 1, data_note: 1, marked: 3, unmarked: 2 },
        plan: {
          document_id: "sample-plan",
          project_id: "P000000",
          implementing_agency: "Sample Water Agency",
          agency_id: "sample-water-agency",
          plan_date: "2026-10-09",
          disclosed_on: "2026-10-09",
          public_from: "2026-10-09",
          is_latest: true,
          pdf_url: null,
        },
        project: {
          project_id: "P000000",
          project_name: "Sample Water Project",
          status: "Active",
          closing_date: "2026-12-31",
          record_date: "2025-06-30",
          days_to_close: 71,
        },
        rows: [
          {
            evidence_id: "sample-1",
            public_from: "2026-10-09",
            activity_reference_no: "KE-SAMPLE-000201-CW-RFB",
            section: "WORKS",
            description: "Construction of a sample water intake and treatment works",
            review_type: "Prior",
            method: "Request for Bids",
            market_approach: "Open - International",
            estimated_amount_usd: "2450000.00",
            actual_amount_usd: "0.00",
            process_status: "Pending Implementation",
            marks: [{ mark: "needs_a_look", reasons: [{ code: "completion_passed_no_contract", mark: "needs_a_look", planned_completion_on: "2026-06-30", closing_date: "2026-12-31", days_to_close: 71, evidence_ids: ["sample-1"] }] }],
          },
          {
            evidence_id: "sample-2",
            public_from: "2026-10-09",
            activity_reference_no: "KE-SAMPLE-000202-CW-RFQ",
            section: "WORKS",
            description: "Rehabilitation of two sample boreholes",
            review_type: "Post",
            method: "Request for Quotations",
            market_approach: "Limited - National",
            estimated_amount_usd: "120000.00",
            actual_amount_usd: "360000.00",
            process_status: "Signed",
            marks: [{ mark: "watch", reasons: [{ code: "signed_late_over_estimate", mark: "watch", signed_on: "2025-03-14", actual_amount_usd: "360000.00", estimated_amount_usd: "120000.00", ratio: 3, ratio_exact: "3.00", days_late: 41, planned_signing_on: "2025-02-01", planned_signing_plan_date: "2024-11-20", evidence_ids: ["sample-2"] }] }],
          },
          {
            evidence_id: "sample-3",
            public_from: "2026-10-09",
            activity_reference_no: "KE-SAMPLE-000203-GO-RFB",
            section: "GOODS",
            description: "Supply of sample water meters",
            review_type: "Post",
            method: "Request for Quotations",
            market_approach: "Limited",
            estimated_amount_usd: "84500.00",
            actual_amount_usd: "0.00",
            process_status: "Completed",
            marks: [{ mark: "data_note", reasons: [{ code: "method_differs_from_reference", mark: "data_note", reference_method_code: "RFB", reference_method: "Request for Bids", method: "Request for Quotations", evidence_ids: ["sample-3"] }, { code: "actual_amount_zero", mark: "data_note", process_status: "Completed", actual_amount_usd: "0.00", evidence_ids: ["sample-3"] }] }],
          },
          {
            evidence_id: "sample-4",
            public_from: "2026-10-09",
            activity_reference_no: "KE-SAMPLE-000204-GO-RFQ",
            section: "GOODS",
            description: "Supply of sample laptops",
            review_type: "Post",
            method: "Request for Quotations",
            market_approach: "Limited",
            estimated_amount_usd: "15000.00",
            actual_amount_usd: "14200.00",
            process_status: "Completed",
            marks: [],
          },
          {
            evidence_id: "sample-5",
            public_from: "2026-10-09",
            activity_reference_no: "KE-SAMPLE-000205-CS-QCBS",
            section: "CONSULTING FIRMS",
            description: "Design and supervision of the sample water works",
            review_type: "Prior",
            method: "Quality And Cost-Based Selection",
            market_approach: "Open - International",
            estimated_amount_usd: "640000.00",
            actual_amount_usd: "612300.00",
            process_status: "Signed",
            marks: [],
          },
        ],
      },
    },
    iconNames: [
      "search",
      "menu",
      "x",
      "chevron-down",
      "circle-dashed",
      "circle",
      "circle-x",
      "info",
      "triangle-alert",
      "check",
      "loader-circle",
      "file-down",
    ],
  },
} as const;
