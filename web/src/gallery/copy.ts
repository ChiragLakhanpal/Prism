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
    withText: "With text",
    opened: "Opened before",
    active: "Open in the drawer",
    withLink: "With a link",
    withoutLink: "Without a link",
    withGap: "With a gap",
    withoutGap: "With nothing missing",
    french: "A passage in French",
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
    textLink: "Text link",
    tabs: "Tabs on a light surface",
    tabsLater: "Tabs with a later one selected",
    cardsBelowLg: "Cards below 1024 px, for a table with wide columns",
    card: "Card",
    emptyState: "Empty state",
    signals: "Signals",
    readiness: "Data readiness",
    planChecks: "Plan checks",
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
    emptyLink: "See which data I hold",
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
