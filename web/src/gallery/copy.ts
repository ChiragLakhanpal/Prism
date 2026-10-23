// Every string the design gallery shows: its labels and the sample content its components
// display. The gallery is never shipped, so these strings stay out of web/src/copy.ts, but
// the gate's copy lint checks them the same way (DESIGN.md section 7). Sample IDs such as
// P000000 are made up on purpose, so no sample can be mistaken for a record.

export const galleryCopy = {
  title: "Design gallery",
  purpose:
    "Every Strata component in each of its states, for building screens and for design reviews. Only development builds have this page.",
  sampleNote: "Everything on this page is sample content for checking the design. None of it is a finding.",
  listLabel: "Components",
  allComponents: "All components",
  sampleEmail: "ana.example@worldbank.org",
  sampleDate: "2026-10-21",

  pages: {
    navigation: {
      title: "Navigation, box band and footer",
      purpose:
        "The frame every page shares. This page shows Projects as the selected tab. The dashed box stands for the World Bank logo, which ticket 06 adds.",
    },
    buttons: {
      title: "Buttons",
      purpose: "Buttons act and links navigate. Each screen has one primary button at most.",
    },
    links: {
      title: "Links and tabs",
      purpose: "Text links are always underlined. Tabs on a light surface use a primary underline.",
    },
    cards: {
      title: "Cards and empty states",
      purpose: "Cards hold a group of facts. An empty state says what will appear and what to do next.",
    },
    alerts: {
      title: "Alerts",
      purpose: "One sentence in a state's colours, with its icon and a left border.",
    },
    badges: {
      title: "Status badges",
      purpose: "Each badge has its own icon shape and names its state in words.",
    },
    numbers: {
      title: "Numbers and terms",
      purpose:
        "Num writes every number by DESIGN.md's rules. A number you can check has a dotted underline. A term opens its definition from GLOSSARY.md.",
    },
    citations: {
      title: "Citations and checks",
      purpose: "Markers name their source. The check line, coverage line and removed box say how far to trust an answer.",
    },
    answer: {
      title: "Answer",
      purpose: "The body of a cited answer in each of its states.",
    },
    document: {
      title: "Document passage",
      purpose: "One numbered paragraph, word for word, with the matching words highlighted.",
    },
    table: {
      title: "Table",
      purpose: "A title sentence, a count line, units in the column heads and a source line. Below 768 px each row becomes a card.",
    },
    skeleton: {
      title: "Skeleton",
      purpose: "Static blocks sized to the content they stand in for. Nothing moves when the content arrives.",
    },
    icons: {
      title: "Icons",
      purpose: "The lucide icons Strata uses, at 16 px. Each one is hidden from screen readers when a word beside it says the same thing.",
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
    french: "A passage in French",
  },

  notes: {
    bar:
      "The navy bar at the top of this page is the sample. Below 1024 px its tabs and the view switch move into the Menu. The box band under it is the sample of the box and the stamp, and the footer is the same on every page.",
  },

  sections: {
    bar: "Navy bar",
    box: "The one box",
    stamp: "Data-freshness stamp",
    variants: "Primary, secondary and ghost",
    textLink: "Text link",
    tabs: "Tabs on a light surface",
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

  sample: {
    primary: "Mark as checked",
    secondary: "Export to Word",
    ghost: "Show them",
    icon: "Close the source",
    textLink: "See which data I hold",
    tabsLabel: "Project sections",
    tabs: ["Summary", "Procurement", "Timeline", "Documents", "Connections"],
    cardTitle: "Northern water works, plan of October 9, 2026",
    cardBody: "Eight activities were checked. One needs a look and two are worth watching.",
    emptyTitle: "I have nothing to brief you on yet.",
    emptyBody:
      "Once I load plans and projects, this page lists the plans that changed, the activities that need a look and the drafts waiting for you.",
    emptyLink: "See which data I hold",
    info: "I can't show the public preview yet, so you are seeing the World Bank staff view.",
    success: "You exported the draft to Word.",
    warning: "Two reports disagree about the closing date.",
    error: "Your account can't read the data I hold yet. Ask the person who shared Strata with you for access.",
    neutral: "I removed one sentence because no record supports its number.",
    numTooltip: "Matches paragraph 54 of the completion report for P000000.",
    numOpened: "You opened the rows behind this number.",
    term: "Comparable",
    measureTitle: "Linked to a project",
    measureBody: "The share of contract awards that carry a project ID I can join on.",
    measureRows: ["Linked", "All rows", "Measured"],
    markerSource: "Implementation Completion and Results Report, June 30, 2021, paragraph 54",
    markerSecond: "Implementation Status and Results Report, March 4, 2024, paragraph 12",
    markerPreview:
      "The contracts were advertised again after all bids were rejected, and the works started five months late.",
    sentenceBefore: "Packages like this took 7 to 11 months from notice to signed contract.",
    sentenceAfter: "Two of them were advertised again.",
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
    steps: [
      { key: "read", running: "I'm reading your question.", done: "I read your question." },
      { key: "search", running: "I'm searching the documents for P000000.", done: "I found 14 passages for P000000." },
      { key: "write", running: "I'm writing the answer.", done: "I wrote three sentences." },
      {
        key: "verify",
        running: "I'm checking each number and quote against the sources.",
        done: "I checked 23 numbers and 14 quotes, and removed one sentence.",
      },
    ],
    runId: "run-0001",
    abstention: "I'm not giving a range: only 12 comparable packages. Here are all 12.",
    empty:
      "I found nothing in the records or documents that answers this. Data readiness shows which sources and years I have read so far.",
    refusal:
      "I don't score or rank suppliers. I can list the contracts a supplier signed on World Bank-financed projects, each with its award notice.",
    refusalNote: "How Strata works lists what I don't do, and why.",
    answerError:
      "I couldn't answer, because the model that writes my answers did not respond. Your question is still in the box.",
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
    tableCount: "Showing all 4 activities",
    tableSource: "Sample rows made for the gallery, in STEP's columns.",
    tableHeaders: ["Activity Reference No.", "Method", "Estimated Amount (US$)", "Days late"],
    tableRows: [
      ["KE-SAMPLE-000001-CW-RFB", "Request for Bids", "1230000", "64"],
      ["KE-SAMPLE-000002-GO-RFQ", "Request for Quotations", "84500", "0"],
      ["KE-SAMPLE-000003-CS-QCBS", "Quality- and Cost-Based Selection", "312000", "131"],
      ["KE-SAMPLE-000004-CW-RFB", "Request for Bids", "2450000", "12"],
    ],
    tableEmptyTitle: "There are no activities in this plan yet.",
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
    ],
  },
} as const;
