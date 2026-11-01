// Every word of the deck at /present, its speaker notes and the figures it shares with How Strata works (ticket 47;
// the second draft's brief, .notes/deck2/brief.md). The copy lint reads this file as it reads web/src/copy.ts
// (COPY_FILES in web/lint/run.ts).
//
// Voice: slides name Strata in the third person, because the presenter speaks as "I"; speaker notes are the
// presenter's "I"; How Strata works keeps Strata's own "I" (DESIGN.md section 7, rule 5). Figure text versions name
// no speaker, so the deck and the page share them.
//
// {name} slots are filled through Fill. A slot that holds a number is filled by the deck's number components, which
// bind it to its key in the measures snapshot, a setting or the rubric, so the number check can trace it. Nothing
// here is a number Strata measured: the words "one" to "nine" that count something come from a setting.

// What a figure says about itself wherever it draws, on a slide or on How Strata works. It sits apart from deckCopy,
// so How Strata works, which is in the app's first download, carries no slide's words.
export const figureStates = {
  failed: "This figure didn't load, so here it is as text.",
};

// A slide's cue and the panel's likely questions (deckCopy.speaker).
export type Speaker = { cue?: string; adds?: (string | null)[]; asked?: { q: string; a: string }[]; diagrams?: string[] };

export const deckCopy = {
  title: (n: string, total: string) => `Slide ${n} of ${total} | Strata deck`,
  readingTitle: "Strata deck",
  notesTitle: (n: string, total: string) => `Speaker notes, slide ${n} of ${total} | Strata deck`,
  // The deck's chrome, which the number check leaves out (data-chrome): the counter, the slide and press lines, and
  // the agenda's and openers' topic numbers.
  counter: (n: string, total: string) => `${n} of ${total}`,
  slideOf: (n: string, total: string) => `Slide ${n} of ${total}`,
  pressOf: (k: string, total: string) => `Press ${k} of ${total}`,
  noPresses: "No presses on this slide",
  announce: (n: string, total: string, title: string) => `Slide ${n} of ${total}: ${title}`,
  roleSlide: "slide",
  wordmark: "Strata",
  // The artwork reads WORLD BANK GROUP, so its text alternative names the Group (DESIGN.md section 9).
  logo: "World Bank Group logo",
  topicsLabel: "Topics of the talk",
  money: (amount: string) => `US$${amount}`,
  percent: (amount: string) => `${amount} percent`,
  sourceLead: "Source:",
  noteLead: "Note:",

  bar: {
    label: "Deck",
    showTable: "Show the table",
    showChart: "Show the chart",
  },

  states: {
    note: "Note:",
    loadError: "The deck didn't load. Check your connection, then reload the page.",
    reload: "Reload the page",
    notMeasured: "Not measured yet",
  },

  reading: {
    present: "Present these slides",
    showText: "Show the figure as text",
    hideText: "Hide the text",
    showNotes: "Show the speaker notes",
    hideNotes: "Hide the speaker notes",
    showTable: "Show the table",
    hideTable: "Hide the table",
    scrolls: (title: string) => `${title}, scrolls sideways`,
    scrollHint: "Scroll the drawing sideways to see all of it.",
    tableRegion: (title: string) => `Table: ${title}`,
  },

  notesView: {
    timerName: "Time since the notes opened",
    restart: "Restart the timer",
    next: "Next: {title}",
    last: "This is the last slide.",
    noDeck: "The deck isn't open in this browser, so these notes move on their own.",
    openDeck: "Open the deck",
    previous: "Back a press",
    nextButton: "Forward a press",
    outline: "Every slide",
    goTo: (title: string) => `Go to ${title}`,
    // The notes' three parts and the previews beside them.
    say: "Say",
    press: "Press",
    onScreen: "On screen:",
    diagrams: "Diagrams from the study guide",
    asYouPress: "As you press",
    cue: "Do",
    asked: "If they ask",
    now: "On screen",
    then: "Next",
  },

  // A demo slide's controls: the link opens the screen in a new tab, so closing the tab returns to the deck.
  demo: {
    opens: "(opens in a new tab)",
    copy: "Copy the question",
    copied: "Copied the question",
    copyFailed: "Select the question and copy it",
    // The planning demo's recorded answer, for when the App is down (ticket 116).
    showRecorded: "Show the recorded answer",
    hideRecorded: "Hide the recorded answer",
  },

  // A number's tooltip and its window (the 46 brief, section 9.2; the 16 brief, section 6): what it counts, its
  // source kind and when it was measured.
  num: {
    ratio: (n: string, d: string, noun: string, kind: string, date: string) => `${n} of ${d} ${noun}. ${kind}, measured ${date}.`,
    count: (n: string, noun: string, kind: string, date: string) => `${n} ${noun}. ${kind}, measured ${date}.`,
    setting: (name: string, where: string) => `${name}. Set in ${where}.`,
    rubric: "Points the assessment brief gives this dimension, in its section 5.",
    definition: (kind: string, table: string) => `${kind}, read from ${table} in the measures snapshot the proposal cites.`,
    settingDefinition: (kind: string) => `${kind}: a value Strata is set to, read from the file that sets it.`,
    rows: {
      counted: "Counted",
      outOf: "Out of",
      measured: "Measured",
      run: "Run",
      table: "Counted in",
      where: "Set in",
      kind: "Source kind",
    },
    kinds: { Count: "Count", Setting: "Setting" } as Record<string, string>,
  },

  // The talk's five topics, in order: the tracker shows each name, and the agenda each name with its line.
  topics: {
    strata: {
      name: "Three strata",
      line: "A procurement plan needs records, operational documents and evaluations, and today they sit apart.",
    },
    work: {
      name: "Strata at work",
      line: "Strata checks a borrower's plan, sizes a package it marks Watch and answers a question about it, live.",
    },
    built: {
      name: "How it is built",
      line: "World Bank open data and documents become one dated knowledge model on Databricks.",
    },
    answers: {
      name: "How it answers",
      line: "The agent picks its tools, and the verifier checks every sentence before anyone sees it.",
    },
    grows: {
      name: "How it grows",
      line: "Strata learns while people decide each change, and a pilot would grow in phases.",
    },
  },

  slides: {
    welcome: {
      statement: "Procurement intelligence on World Bank open data, with every claim cited",
      line: "Built for the World Bank Group's procurement intelligence assessment.",
      figure: "A core sample with its layers one under the other, for the three strata of evidence.",
      notes:
        "Thank you for having me. I built Strata to answer a question procurement specialists ask all the time: " +
        "what happened to packages like this one before? I'll show it working on a live project first, then open " +
        "the hood and walk you through the data, the agent, the checks, and the tradeoffs I made along the way.",
    },
    agenda: {
      title: "The problem, a live demo, then how Strata is built, answers and grows",
      notes:
        "Here's the plan. A few minutes on the problem, then a live demo, which is the spine of the talk. " +
        "Everything after the demo explains what you just saw.",
    },

    // ── Three strata ──
    strata: {
      title: "A procurement plan needs three strata of evidence, and today they sit apart",
      source: "the assessment brief, section 1.",
      notes:
        "Procurement evidence comes in three strata, like the layers in a core sample. The evidence exists. The " +
        "problem is that each layer lives in a different system, in a different shape, and today a person " +
        "stitches them together by hand.",
    },
    cost: {
      title: "Today the evidence reaches a plan too late to change it",
      lines: [
        "Teams set schedules without knowing how long comparable packages took.",
        "Packages are advertised again, or canceled, for reasons a past report already named.",
        "Specifications miss what the market can deliver.",
        "Lessons sit in PDF archives, so the same mistakes repeat.",
      ],
      ask: "How does your team find what a completion report said about packages like this one?",
      source: "the assessment brief, section 1.",
      notes:
        "So why does this matter? The evidence exists, but it reaches a plan after the decisions are already " +
        "made.",
    },
    who: {
      title: "The borrower owns the plan, and Strata helps both sides check it",
      tiles: [
        {
          head: "World Bank staff",
          body: "Procurement specialists and task team leaders review a borrower's plan and prepare missions. They leave with review notes and a mission brief.",
        },
        {
          head: "Implementing agency officers",
          body: "They draft the Procurement Plan and check it before they send it. They leave with a planned date for each step, and risks with their sources.",
        },
        {
          head: "The public, read-only",
          body: "They follow a contract from its notice to its completion report, in neutral words. Active projects show them no signals or estimates.",
        },
      ],
      closing: "Strata drafts, and people decide. Exporting sends nothing, and nothing Strata writes is a World Bank decision.",
      notes:
        "The borrower owns the plan, and Strata never changes that. It helps both sides look at the same " +
        "evidence.",
    },
    idea: {
      title: "Strata joins the three strata once, so one question gets one cited answer",
      notes:
        "The idea is easy to say and hard to build. Join the three strata once, so one question gets one answer, " +
        "and every sentence in that answer can be checked.",
    },

    // ── Strata at work ──
    workOpener: {
      notes:
        "Enough slides. Let me show you one real package, from the plan to a checked answer.",
    },
    demoPlan: {
      title: "Checking a borrower's Procurement Plan, row by row",
      box: "{agency}'s Procurement Plan of {date}, {project}",
      action: "Open the plan check",
      lines: [
        "Strata checks each activity against past ranges, review thresholds and the plan's own dates.",
        "A signal is a reason to look, never a finding, and it names the record behind it.",
      ],
      source: "the Procurement Plan of {date} for {project}, as published in Systematic Tracking of Exchanges in Procurement (STEP).",
      notes:
        "Here's an agency's Procurement Plan, read row by row from its latest published version. Strata checks " +
        "every activity, and one of them, {step}, is marked Watch. That's the package we'll follow for the rest " +
        "of the talk.",
    },
    demoPackage: {
      title: "Comparing that package with the packages that came before it",
      box: "Package {step}, which the plan check marks Watch",
      action: "Open the package",
      lines: [
        "Each comparable package is a dot on a month axis, from its notice to its signed contract.",
        "Hollow dots are still open, and the range counts them, so the slow cases stay in.",
        "The time estimate comes from a survival model. With no model or too few packages, it says why instead of " +
          "guessing.",
      ],
      note: "STEP is Systematic Tracking of Exchanges in Procurement, where Procurement Plans are kept.",
      notes:
        "Now the package itself, next to the packages that came before it. Every dot is a real package, and you " +
        "can click through to its records.",
      // The recorded answer (ticket 116): the comparable packages Strata found for the demo plan's package, recorded
      // on the workspace. This line goes first under its chart, before the package workspace's own lines.
      recorded: "Recorded on {date}, for {step}, a package in the Procurement Plan Strata checked.",
      cueRecorded:
        "Click Open the package, then come back and press. If the App is down, press Show the recorded answer " +
        "instead. It's the same chart for {step}, recorded on {date}.",
    },
    demoAnswer: {
      title: "Asking about the package, with every number checked against the records",
      question: "How long did comparable packages take from notice to signed contract?",
      action: "Open the package",
      lines: [
        "Every sentence names its source, and one click opens the record behind it.",
        "The verifier checks every number against the records before the answer shows.",
        "A sentence it cannot back is removed and shown, with the reason.",
      ],
      note: "the verifier runs on every answer and is never bypassed.",
      notes:
        "Last part of the demo. I'll ask Strata a question about this package and let it answer live. Watch the " +
        "steps it shows while it works.",
    },

    // ── How it is built ──
    builtOpener: {
      notes:
        "So that's what it does. Now let me show you how it's built, from the layers down to how a single PDF " +
        "becomes evidence.",
    },
    layers: {
      title: "The data, search and tools run on Databricks, and the agent and its models run in Microsoft Foundry",
      notes:
        "Here's the system as layers. The short version: the data, search and tools run on Databricks, the agent " +
        "and its models run in Microsoft Foundry, and the app in between runs every tool as the person asking.",
    },
    architecture: {
      title: "The whole system, from the public sources to the person asking",
      notes:
        "Here's the same system as a map, in the order the data travels, from the public sources on the left to " +
        "the person asking on the right.",
    },
    pipeline: {
      title: "Every night, World Bank open data become one dated knowledge model",
      notes:
        "Every night, World Bank open data becomes one dated knowledge model. The design rule I cared about most " +
        "is that every row remembers the day it became public.",
    },
    reading: {
      title: "Every document becomes numbered passages, each with its paragraph and page",
      passages: "{passages} passages from {documents} documents, each with its paragraph number and page.",
      passagesNone: "Strata has not counted its passages yet.",
      pages: "Strata read {ratio} pages without errors.",
      pagesNone: "Strata has not measured how well it read its pages yet.",
      // Neither measured yet: one sentence, not two that start the same way.
      bothNone: "Strata has not counted its passages or measured how well it read its pages yet.",
      source: "Strata's data readiness measures, taken {date}.",
      notes:
        "Here's how a PDF becomes evidence you can cite. The trick is to treat each page on its merits, and to " +
        "end with numbered passages that keep their paragraph and their page.",
    },

    // ── How it answers ──
    answersOpener: {
      notes:
        "Now the part I took the most care over: how an answer is made, and why you can trust it.",
    },
    retrieval: {
      title: "The agent picks the tools, and the app runs them as the person asking",
      notes:
        "Here's one question's whole path, in order. The agent decides what to look up, but it never touches the " +
        "data. The app runs every tool, as you.",
    },
    languages: {
      title: "A question in one language can find evidence in another, and every quote stays in its own words",
      action: "Open P127203 in Strata",
      notes:
        "I know you wanted to see the cross-language side, so here it is. The rule is simple: search across " +
        "languages, answer in yours, and never translate a quote.",
    },
    estimate: {
      title: "Comparable packages give the past range, and a survival model gives the time estimate",
      few: "Under {min} comparable packages, Strata shows every package and gives no range.",
      backtest: "In {year}, {ratio} packages that Strata had not seen were signed within its 8-in-10 point.",
      backtestNone: "The backtest has not run on the workspace yet, so the model's track record is not shown here.",
      source: "Strata's backtest, measured {date}.",
      notes:
        "Now the models. A time estimate starts from comparable packages, and every step is allowed to say it " +
        "doesn't know. Under {min} comparable packages, there's no range at all.",
    },
    checks: {
      title: "Every sentence meets {checks} checks before anyone sees it",
      heading: "In the latest benchmark run,",
      passed: "{ratio} benchmark questions passed.",
      refused: "Strata turned down {ratio} questions it must refuse.",
      none: "The benchmark has not run with all {checks} checks yet, so there are no results to show.",
      source: "Strata's benchmark run of {date}.",
      notes:
        "Every sentence passes these checks before anyone sees it. Let me walk a pair of sentences through them, " +
        "one that passes and one that doesn't.",
    },
    ladder: {
      title: "When reports disagree, both stay on screen, and Strata says which it leans on",
      point:
        "For how a project turned out, Strata leans on the most independent report written after the project " +
        "closed. For a fact about a moment, the record made at that moment wins.",
      // {project} is the showcase project (config/slice.toml [showcase]), whose disagreement the slide quotes.
      example:
        "In {project}, a status report rated progress toward the objective Satisfactory in August 2016. The " +
        "completion report later said the mid-term review had found part of the objective compromised by major " +
        "delays. Strata shows both and leans on the completion report.",
      action: "Open the timeline",
      source:
        "Implementation Status and Results Report 7, {project}, August 26, 2016; Implementation Completion and " +
        "Results Report, {project}, October 10, 2019, paragraph 78, page 27.",
      notes:
        "Reports disagree more often than you'd think. Strata doesn't pick a side quietly. Both sides stay on " +
        "screen, and it says which one it leans on, and why.",
    },

    // ── How it grows ──
    growsOpener: {
      notes:
        "Last section: how Strata gets better without anyone retraining it by hand, and how I'd roll it out.",
    },
    loops: {
      title: "{loops} loops learn on their own schedules, and people decide each change",
      notes:
        "Strata improves through loops that run on their own schedules, and a person decides every change. " +
        "Nothing updates itself quietly.",
    },
    rollout: {
      title: "The pilot grows in {phases} phases, each measured before the next",
      phases: [
        {
          name: "First",
          who: "World Bank procurement specialists and task team leaders in {countries} countries",
          measured: "Weekly users, drafts checked and exported, and Wrong passage reports for the sources opened",
        },
        {
          name: "Second",
          who: "Implementing agencies in the same countries",
          measured: "Plan accuracy with Strata's ranges against plans made without them, and days from a new completion report to a decided lesson",
        },
        {
          name: "Third",
          who: "The public, read-only",
          measured: "Contract trails opened for closed projects. Active projects show the public no signals, estimates or disagreements.",
        },
      ],
      whoLabel: "Who uses Strata",
      measuredLabel: "Measured before the next phase",
      measuredLastLabel: "Measured during this phase",
      notes:
        "I'd roll it out in phases, starting with World Bank staff in {countries} countries, and each phase has " +
        "to earn the next with something measured.",
    },
    limits: {
      title: "What is designed but not built yet",
      empty: "Everything in this deck is built and runs in the app.",
      itemAt: "{name}, labeled at {route}",
      notes:
        "Here's what I designed but didn't build, so nothing in the demo pretends otherwise. The same list is in the " +
        "proposal, and the app labels each one where it would appear.",
      notesEmpty: "Everything on these slides is built and runs in the app, and you can open any of it now.",
    },
    data: {
      title: "What the data looks like, and where it breaks",
      tiles: [
        {
          head: "The awards datasets, and the gap",
          body: "{since} award rows since fiscal 2020 and {old} for 2001 to 2016. None cover 2017 to 2019, so Strata " +
            "built {gap} contracts from award notices.",
          results: { since: "award-rows-since-2020", old: "award-rows-2001-2016", gap: "gap-contracts" },
          counts: ["since", "old", "gap"],
        },
        {
          head: "The missing key",
          body: "Only {linked} contract award rows since fiscal 2020 share their STEP reference with a procurement notice.",
          results: { linked: "linked-notice" },
        },
        {
          head: "Suppliers",
          body: "{suppliers} awarded bidders give one name and one STEP supplier ID across their award rows. The rest need resolving.",
          results: { suppliers: "supplier-ids" },
        },
        {
          head: "Contact details",
          body: "Ingestion removed contact details from {removed} procurement notices, and the latest nightly check found {left} left.",
          results: { removed: "contacts-removed", left: "contacts-left" },
          counts: ["left"],
        },
        {
          head: "Reports",
          body: "{passages} numbered passages, and {disagreements} disagreements between reports and records.",
          results: { passages: "passages", disagreements: "disagreements" },
          counts: ["passages", "disagreements"],
        },
      ] as { head: string; body: string; results: Record<string, string>; counts?: string[] }[],
      link: "Open the Data readiness page",
      figure: "The awards record year by year, with a break that only award notices fill.",
      source: "Strata's Data readiness measures, pulled {date}.",
      notes:
        "Before any model touches this data, here's what it really looks like, including where it breaks. I'd " +
        "rather show you the gaps than have you find them.",
    },
    nextReach: {
      title: "Next: more languages, more countries and more of the record",
      tiles: [
        {
          head: "Spanish and Portuguese",
          body: "Strata can already write both. A speaker still has to review each word list, French's too, and the slice " +
            "needs reports in them.",
        },
        {
          head: "More countries and sectors",
          body: "The slice is one file. A new country or sector is one entry, and the same job, tools and checks apply.",
        },
        {
          head: "Closing the data gaps",
          body: "The fixes Data readiness ranks first: STEP references for contracts without one, US dollars for the gap years, older plan versions.",
        },
        {
          head: "The whole portfolio",
          body: "A higher daily page cap reads the rest of the reports, through the same page router and the same checks.",
        },
      ],
      notes:
        "Here's where I'd take it next, starting with reach: more languages, more countries and more of the " +
        "record.",
    },
    nextProduct: {
      title: "Next: features for the people who plan and review",
      tiles: [
        {
          head: "Amendment risk",
          body: "The assessment asks for it, but no public record lists contract amendments. With STEP's records, the same " +
            "survival setup could estimate it.",
        },
        {
          head: "Answers that stream",
          body: "Today the whole answer waits for every check. Next, each sentence shows the moment it passes, so long " +
            "answers start sooner.",
        },
        {
          head: "Signals that reach people",
          body: "A weekly digest of new signals on the projects a person follows, sent where they already work.",
        },
        {
          head: "The agent beside the data",
          body: "When Databricks' agent tools are generally available, the orchestrator can move next to the data. The tools and checks stay.",
        },
      ],
      notes:
        "And the features I'd build next, the ones I think would matter most to the people who plan and review.",
    },
    thanks: {
      title: "Thank you",
      figure: "Every night, new reports settle on the core as a new layer, and Strata keeps every layer.",
      ask: "What would you like to ask?",
      links: { app: "Open Strata", proposal: "Read the proposal", dashboard: "Open the dashboard", repo: "Read the code" },
      notes:
        "That's Strata: one question, three strata, and one answer you can check. Thank you. I'd love your " +
        "questions, and if you'd like a change made live, I'm ready.",
      notesAfterLimits:
        "Thank you. I'm glad to take your questions, or to make a change live, here in the room.",
    },
  },

  // The presenter's side of each slide, by slide id: a cue for what to do on it, and the questions a technical
  // panel may ask about it, each with an answer to give as written. What to say is each slide's notes.
  speaker: {
    "welcome": {
      cue:
        "Press F for full screen. Keep /present/notes open on your laptop. Check that the App's view pill says " +
        "English. Aim for about 30 minutes, then questions. If the App restarts, the deck asks for its password " +
        "again.",
      asked: [
        {
          q:
            "What is Strata, in one sentence?",
          a:
            "A procurement assistant on World Bank open data that answers questions about projects and packages, " +
            "and checks every number and quote against the records before you see the answer.",
        },
        {
          q:
            "Is this real, or a mockup?",
          a:
            "It's real. It runs as a Databricks App on a paid workspace, a nightly job reads World Bank open " +
            "data, and the agent runs in Microsoft Foundry. A few parts are built and tested but haven't run live" +
            " yet, and I'll point each one out when we get there.",
        },
        {
          q:
            "Who is it for?",
          a:
            "World Bank procurement staff first, then implementing agencies, then the public, read-only. That " +
            "order is the rollout plan too.",
        },
      ],
    },
    "agenda": {
      adds: [
        "The problem first, because every design choice later traces back to it.",
        "Then a live demo on one real package in Kenya. The rest of the talk explains it.",
        "How it's built: the lakehouse on Databricks, the nightly job, and how a PDF becomes passages you can " +
        "cite.",
        "How it answers: the agent, the tools, the verifier, the cross-language case, and the models.",
        "And how it grows: the loops that improve it, the rollout, and what I'd build next.",
      ],
    },
    "strata": {
      adds: [
        "Records are rows. Contract awards from Finances One, notices and projects from the search APIs, " +
        "governance indicators. Clean, but they only tell you what happened, never why.",
        "Operational documents are the Procurement Plans in STEP and the status reports. The planned dates live " +
        "here, so this is where a delay shows up first.",
        "Evaluations are the PDFs: appraisal documents, completion reports, IEG's reviews. They explain why, but " +
        "they're long, sometimes scanned, and they never point to a contract ID.",
        "So the join is the hard part. The whole design is about making that join once and reliably, with keys " +
        "where they exist and passages where they don't.",
      ],
      asked: [
        {
          q:
            "Where does each stratum's data come from?",
          a:
            "Records come from Finances One and the World Bank's search APIs. Plans, status reports and " +
            "evaluations come through the Documents API. All public, all read by the nightly job.",
        },
      ],
      diagrams: ["three_strata", "sources_map"],
    },
    "cost": {
      adds: [
        "When a team sets a schedule, the real question is how long comparable packages took, notice to signed " +
        "contract. Today that means pulling award data by hand, if anyone does it at all.",
        "Every package advertised again costs time, and often a completion report already named the reason, in a " +
        "paragraph nobody searched.",
        "A specification that misses the market gets few bids or none. What the market can deliver is written in " +
        "past awards, if you can find the comparable ones.",
        "Lessons are written with care and read rarely. That's the gap Strata closes.",
        "Ask it, then pause and let them answer. The usual honest answer is from memory, or from a colleague who " +
        "was there.",
      ],
      asked: [
        {
          q:
            "How often does this happen?",
          a:
            "I won't quote a rate I haven't measured. What Strata shows is per package: the comparable packages, " +
            "how long they took, and the paragraphs that explain the slow ones.",
        },
      ],
      diagrams: ["lifecycle"],
    },
    "who": {
      adds: [
        "Staff review plans and prepare missions. Strata drafts their review notes and mission brief, every line " +
        "cited, and a draft stays a draft until a person exports it.",
        "Agency officers write the plan. They get a planned date for each step and the risks other projects ran " +
        "into, with the paragraph behind each one.",
        "The public gets a read-only trail from notice to completion report. On active projects they see no " +
        "signals or time estimates. Signals are for the people who can act on them.",
        "And the boundary: Strata drafts, people decide. Exporting sends nothing anywhere. That's held in the " +
        "copy by a lint, and in the agent by a fixed list of refusals.",
      ],
      asked: [
        {
          q:
            "What if someone asks it to evaluate a bid?",
          a:
            "It refuses and says why. Refusals are a fixed list of ten keys, like supplier scores or review " +
            "decisions. The agent can only return the key, and the app writes the words from the copy file, so " +
            "nobody can talk a refusal into another shape. Each key has a must-refuse question in the benchmark.",
        },
        {
          q:
            "How are the views kept apart?",
          a:
            "Each view is a set of capabilities in config/roles.toml, and the server checks it on every API call," +
            " not only in the screens.",
        },
      ],
      diagrams: ["roles"],
    },
    "idea": {
      adds: [
        "It always starts from a package and its STEP reference. That reference is the key that holds everything " +
        "together.",
        "From the records: comparable packages, chosen by plain SQL on stated criteria, and how long each took " +
        "from notice to signed contract.",
        "From the plans: each step's planned and actual dates, read from every published version, so you can see " +
        "when a date moved.",
        "From the evaluations: what went wrong and what helped, quoted word for word, with paragraph and page.",
        "And they meet in one answer where every sentence carries the IDs of its evidence. That last part is most" +
        " of the engineering.",
      ],
      asked: [
        {
          q:
            "Why not just put a chatbot over the documents?",
          a:
            "Because a chatbot over PDFs can't count. These questions are about durations, amounts and dates, and" +
            " those live in records. A language model is good at choosing what to look up and at writing. It's a " +
            "poor source for a number. So numbers come from tools, and a verifier checks every one.",
        },
        {
          q:
            "What's a STEP reference?",
          a:
            "STEP is Systematic Tracking of Exchanges in Procurement, where Procurement Plans are kept. Each " +
            "package has a reference like KE-NWWDA-541055-CW-RFB, and notices and awards carry it too. When it's " +
            "there it's an exact key. When it isn't, Strata says so instead of guessing.",
        },
      ],
      diagrams: ["lifecycle", "step_flow"],
    },
    "work": {
      cue:
        "About 8 minutes for the demo. Have the App open in a second tab. Check the view pill says English.",
    },
    "demo-plan": {
      cue:
        "Click Open the plan check. Scroll to KE-NWWDA-541055-CW-RFB and point at its Watch mark and its reason. " +
        "Come back and press.",
      adds: [
        "This is the check_plan tool. It reads the plan from strata.silver.plan_rows and plan_versions, each " +
        "step's dates from plan_steps, and its baselines from strata.ops.plan_baselines. Each row is checked " +
        "against the past range for comparable packages, the review thresholds, and the plan's own dates.",
        "This one says Watch because it's still pending after its project closed on October 31. Notice the words." +
        " There's a list of words Strata never writes about an agency, and a lint over every copy file fails the " +
        "build if one appears.",
      ],
      asked: [
        {
          q:
            "Where do the plan's rows come from?",
          a:
            "From the Procurement Plans the World Bank publishes. The reader turns each version into rows in " +
            "strata.silver.plan_rows, and keeps every version, so a moved date shows up as a change between " +
            "versions, never an overwrite.",
        },
        {
          q:
            "Is a signal a finding against the agency?",
          a:
            "No. A signal is a reason to look. It names the record behind it, and a person decides what it means.",
        },
        {
          q:
            "How would an agency officer use this?",
          a:
            "Before sending the plan in. Open the plan check, see which rows look tight next to comparable " +
            "packages, and fix them before the review instead of after.",
        },
      ],
      diagrams: ["plan_reader", "signals_status"],
    },
    "demo-package": {
      adds: [
        "This is find_comparables: plain SQL over strata.gold.package, notice and contract, matching method, " +
        "category and country, from July 2019 on. No embedding, no model. I chose exact matching so a reviewer " +
        "can see exactly why each package is in.",
        "Hollow dots are packages still open. Most tools drop them, and every range looks shorter than it was. " +
        "Strata keeps them with a Kaplan-Meier estimate, so an open package counts as not signed yet.",
        "And the time estimate lane is empty here, on purpose. No model has been trained on this workspace yet, " +
        "so it says why instead of showing a number it can't back. I'd rather show you that than hide it.",
      ],
      asked: [
        {
          q:
            "How do you pick comparable packages?",
          a:
            "Exact matches on stated criteria: the package's method, category and country by default, plus market" +
            " approach, review type and a size band if you set them, over notices since July 2019. It's stricter " +
            "than a fuzzy match, but every package in the set is explainable. Under 20 matches, Strata shows the " +
            "packages and gives no range.",
        },
        {
          q:
            "Why keep packages that are still open?",
          a:
            "Because dropping them makes every range too short. A package open for 300 days tells you it took at " +
            "least 300 days. Kaplan-Meier uses that as a censored observation, so the slow cases stay in.",
        },
        {
          q:
            "Which tables does this page read?",
          a:
            "strata.gold.package, notice and contract for the comparables, gold.project and country for the " +
            "region, silver.plan_versions and plan_rows for the plan's dates, and gold.time_estimate_score for " +
            "the time estimate. All as the viewer, as of the page's date.",
        },
        {
          q:
            "Why is the time estimate empty?",
          a:
            "No model has been trained on this workspace yet. When I ran the backtests on October 25, the notice " +
            "search API's paging limit meant the notice history started in 2024, and every backtest year had " +
            "fewer than 20 packages to size a range on, so the model abstained. The model and its gates are built" +
            " and tested offline. It needs a longer notice history to train live.",
        },
      ],
      diagrams: ["two_lane", "time_estimate_flow"],
    },
    "demo-answer": {
      cue:
        "Click Copy the question, switch to the package tab, paste it in the ask box and press Enter. Point at " +
        "the steps as they run: tools, writing, checks. If it's slow, keep talking. It checks before it shows " +
        "anything.",
      adds: [
        "Behind this, the agent in Foundry asked for find_comparables, the app ran it with my own token, and " +
        "every row came back with an evidence ID. Each sentence carries those IDs, so a click lands on the exact " +
        "record.",
        "Nothing appeared until the verifier finished. Every number in the answer was matched against a row a " +
        "tool returned, at the same rounding. That's plain code, not a model, so it can't be talked out of a " +
        "mismatch.",
        "A sentence that fails is removed and listed with its reason, never hidden. And the whole run is logged: " +
        "strata.ops.agent_runs, each tool call, each table version it read, and each removal.",
      ],
      asked: [
        {
          q:
            "What stops it from making a number up?",
          a:
            "Numbers only come from tools, and the agent is told never to compute or round one. Then the verifier" +
            " matches every number and date in every sentence against the rows the tools returned, at the same " +
            "rounding. A number with no matching row removes the sentence, and the verifier is never bypassed.",
        },
        {
          q:
            "What if the model is down or slow?",
          a:
            "The stream sends a heartbeat every 15 seconds, so the connection stays open. If Foundry fails you " +
            "get a named error, never half an answer. And if the judge model doesn't respond, every sentence it " +
            "was meant to judge is removed. Nothing is ever shown unchecked.",
        },
        {
          q:
            "Can people outside the World Bank see this?",
          a:
            "The App sits behind the workspace's sign-in, and every tool runs with the viewer's own Databricks " +
            "token, so Unity Catalog's grants decide what each person can read.",
        },
        {
          q:
            "How long does an answer take?",
          a:
            "It depends on the tool rounds: at most three, plus at most one rewrite and one batched judge call. I" +
            " traded speed for correctness here, since nothing shows until every check passes. Streaming sentence" +
            " by sentence is on my list.",
        },
      ],
      diagrams: ["question_sequence", "verifier_flow"],
    },
    "built": {
      cue:
        "About 7 minutes for this section.",
    },
    "layers": {
      adds: [
        "At the bottom, the lakehouse: bronze, silver and gold Delta tables in Unity Catalog, filled by a nightly" +
        " job. More on that in a minute.",
        "The knowledge model is just tables: projects, packages, contracts, passages, dated assertions, and an " +
        "edge table for links. I looked at Neo4j and said no. The graph walks I need are a few hops, recursive " +
        "SQL handles them, and one governance model beats two. That's ADR 0004.",
        "Tools are the only way the agent touches data: fixed, parameterized SQL on gold, hybrid search over " +
        "passages, a Genie space, and the precomputed time estimates. Fifteen of them, all read-only, in one " +
        "registry, config/tools.toml.",
        "The agent is a prompt agent in Foundry on gpt-5.4. It started on gpt-5.4-mini. I switched on October 27 " +
        "because the small model's quotes were too loose to pass the verifier. The verifier told me something " +
        "useful there.",
        "The verifier sits between the agent and the person, in plain Python. Every sentence passes it or is " +
        "removed.",
        "The app is a Databricks App, React in front and FastAPI behind. It runs each tool with the viewer's own " +
        "forwarded token, so Unity Catalog applies to the agent exactly as it does to the person.",
        "So data and governance live on Databricks, the agent runtime in Foundry, and the models on Azure OpenAI." +
        " Here's the full wiring.",
      ],
      asked: [
        {
          q:
            "Why split Databricks and Foundry?",
          a:
            "When I made the call, Foundry's agent service and its evaluations were generally available. " +
            "Databricks had just marked Knowledge Assistant and Supervisor Agent legacy, and its code-first agent" +
            " runtime was in Beta. All Databricks meant building on a Beta. All Azure meant giving up the " +
            "lakehouse. So data stays on Databricks, the agent runs in Foundry, and the boundary between them is " +
            "a small, typed tool list. That's ADR 0001.",
        },
        {
          q:
            "How does it know who the viewer is?",
          a:
            "The Databricks App proxy forwards the person's identity and an access token on every request. The " +
            "server binds a viewer per request, never in a global, and every tool runs with that token. The token" +
            " never goes to Foundry.",
        },
        {
          q:
            "What's the stack?",
          a:
            "Databricks: Delta Lake, Unity Catalog, serverless jobs, AI Search, Genie, MLflow, Lakebase and " +
            "Databricks Apps. Azure: Foundry for the agent, Azure OpenAI for gpt-5.4 and the embeddings, Content " +
            "Safety for Prompt Shields. The app is React, TypeScript and Vite in front, FastAPI behind.",
        },
        {
          q:
            "How do you stop a document from steering the agent?",
          a:
            "Prompt Shields screens every passage when it's read, and a passage with an attack, or not screened " +
            "yet, is held back from search. The message to the agent carries only data, so the rules live in its " +
            "instructions where no document can reach them. And Foundry's guardrail blocks jailbreaks and " +
            "indirect attacks on the way in and out.",
        },
      ],
      diagrams: ["platform_map", "identity_flow"],
    },
    "architecture": {
      adds: [
        "Four public sources, all World Bank open data. No private data goes in. The only private thing in the " +
        "system is a borrower's own uploaded plan, and only their team sees it.",
        "A serverless job at 3 a.m. Eastern, a chain of tasks that fetches only what changed. Serverless because " +
        "the load is a few hours a night and nothing in between.",
        "Bronze keeps each page exactly as received, so I can always reprocess. Silver types the rows and holds " +
        "the passages. Gold is the knowledge model. Ops keeps every run, answer, removal and human decision.",
        "Everything that reads gold sits on it: the AI Search index, a Genie space over metric views, the models " +
        "in MLflow, the AI/BI dashboard. One set of tables, so the dashboard and the agent can't disagree about a" +
        " number.",
        "The Databricks App runs the tools as the viewer and runs the verifier. Lakebase, Databricks' managed " +
        "Postgres, keeps the app's state, where a click needs milliseconds, not a warehouse query.",
        "Foundry runs the orchestrator agent and the writers on Azure OpenAI, behind a guardrail. The app and the" +
        " agent only trade tool calls and results. The agent never touches a table.",
      ],
      asked: [
        {
          q:
            "Why is the agent outside Databricks?",
          a:
            "The agent runtime I needed was generally available in Foundry and in Beta on Databricks when I built" +
            " this. The cost is one more boundary, so I kept it narrow: a fixed tool list, typed arguments, " +
            "data-only messages. If Databricks' agent tools go GA, the orchestrator can move, and the tools and " +
            "checks stay.",
        },
        {
          q:
            "What's Lakebase for?",
          a:
            "App state: drafts, saved choices, whatever a click changes. Those need fast reads and writes, and a " +
            "SQL warehouse is built for scans. Lakebase gives me Postgres under the same governance. That's ADR " +
            "0005.",
        },
        {
          q:
            "Why serverless for the nightly job?",
          a:
            "It runs a few hours a night and nothing else. No cluster to size or keep warm, and I pay only for " +
            "the run.",
        },
        {
          q:
            "What's champion and challenger?",
          a:
            "The model serving live is the champion, an alias in Unity Catalog's model registry. A new version is" +
            " a challenger until it wins its backtest and a quarter in shadow and two people sign off. Then the " +
            "alias moves. Rolling back is moving it back.",
        },
        {
          q:
            "What does it cost to run?",
          a:
            "On the October 27 snapshot, Azure spend was about 26 US dollars of a 197-dollar credit. Cost is " +
            "capped, not just watched: every model deployment has a token limit, document reading has a daily " +
            "page cap, the app's replicas are capped, and bulk model work runs on a cheaper batch deployment.",
        },
      ],
      diagrams: ["arch_overview", "platform_map", "sql_everywhere"],
    },
    "pipeline": {
      adds: [
        "The fetch resumes from where each source stopped, so a night reads only what changed. The sources are " +
        "one registry, config/sources.toml.",
        "Bronze is the raw page as it arrived. If I fix a parser next month, I rebuild silver from bronze without" +
        " calling a single API again.",
        "Silver is where cleaning happens: typed rows, passages, supplier matching. Contact details are stripped " +
        "here, at ingestion, before anything downstream can see them, and a nightly check counts any email or " +
        "phone number that got through.",
        "Gold is the knowledge model: projects, packages, contracts, suppliers, passages, assertions, " +
        "disagreements, and the edge table.",
        "One copy of the truth. The app, the dashboard, Genie and the agent all read the same gold tables, so " +
        "they can't drift apart.",
        "And every row carries public_from, the date the World Bank made it public. I can replay any answer as of" +
        " any date, and a backtest can't see the future, because the reader raises an error on any row public " +
        "after its cutoff. That's ADR 0002.",
      ],
      asked: [
        {
          q:
            "Which tables are those?",
          a:
            "strata.bronze for raw pages. strata.silver for typed rows like plan_rows, notices and passages. " +
            "strata.gold for project, package, contract, supplier, passage, assertion, disagreement and edge. " +
            "strata.ops for runs, tool calls, removals and decisions.",
        },
        {
          q:
            "Why strip contact details?",
          a:
            "Notices carry names, emails and phone numbers, and Strata needs none of them to answer anything, so " +
            "they never get past ingestion. A nightly check counts any that got through, and the data slide shows" +
            " both numbers.",
        },
        {
          q:
            "What does as of a date mean?",
          a:
            "A question asked as of a date sees only rows public by then. That's enforced in the SQL, in the " +
            "search filter, and again in the tool registry, which raises an error if a later row ever comes back.",
        },
      ],
      diagrams: ["medallion", "nightly_dag", "fetch_flow", "record_journey"],
    },
    "reading": {
      adds: [
        "Documents come from the Documents API. Each document type has a template, so the reader knows how that " +
        "type numbers its paragraphs.",
        "The router decides page by page, not document by document. A clean report with one scanned annex " +
        "shouldn't pay for the scan.",
        "Clean pages keep the text the World Bank publishes, word for word. Run a clean page through a parser " +
        "again and the words can drift, and then a quote won't match its page.",
        "Scans, data sheets and risk tables go to Databricks' layout parser, ai_parse_document. It's slower and " +
        "costs more, so it gets only the pages that need it, under a daily page cap.",
        "Both roads end in numbered passages with paragraph, page and section. Before embedding, each passage " +
        "gets a short header with its report, project, country and section, so no passage is searched alone.",
        "Passages go into the hybrid search index. One rule I'm strict about: a table's summary helps search find" +
        " the table, but only its rows can back a number.",
        "Every passage is also screened by Prompt Shields when it's read. A passage that reads like an " +
        "instruction, or that wasn't screened, is held back from search.",
      ],
      asked: [
        {
          q:
            "What is the layout parser?",
          a:
            "ai_parse_document, a Databricks SQL function that reads a page's layout: text blocks, tables and " +
            "their cells. Strata sends it only the pages the router picks: scans, data sheets and tables.",
        },
        {
          q:
            "How do you know a quote is real?",
          a:
            "The verifier finds it word for word in the cited passage, in the passage's own language. It forgives" +
            " only whitespace, line-end hyphens, curly versus straight quote marks and a capital first letter. A " +
            "quote that isn't on its page removes the sentence.",
        },
        {
          q:
            "Where do the passages live?",
          a:
            "In strata.gold.passage, each with an ID like strata.gold.passage:31525018/v1/54, the document, its " +
            "version and the paragraph. The AI Search index, strata.gold.passage_index, syncs from that table.",
        },
        {
          q:
            "Why not send every page to the layout parser?",
          a:
            "Cost and accuracy. It's billed per page and slower, and on a clean page it can only drift from what " +
            "the World Bank published.",
        },
        {
          q:
            "Why hybrid search?",
          a:
            "Keyword search is exact on names, IDs and amounts. Vector search finds meaning when the words " +
            "differ. A STEP reference has to match exactly, and a question about bidding delays has to find a " +
            "paragraph that never uses those words. A reranker orders the merged list.",
        },
      ],
      diagrams: ["doc_pipeline", "page_router", "passage_anatomy"],
    },
    "data": {
      adds: [
        "The awards come as two separate datasets, one since fiscal 2020 and one for 2001 to 2016, and each row " +
        "keeps the dataset it came from. Between them is a hole: no dataset covers 2017 to 2019. Award notices " +
        "do, so Strata built contracts from them, in local currency, kept apart from the US-dollar awards.",
        "Here's that hole as a picture: the record year by year, with the base broken where only award notices " +
        "fill it. Why not interpolate, or convert the currency? Either way I'd be putting my own numbers into the" +
        " record.",
        "The missing key is the abnormality that shaped the most design. When I dug in on October 26 there were " +
        "two causes: many awards carry no STEP reference, and the notice search API stops paging at 100,000 " +
        "results, so the notices we held started in 2024. Strata never guesses that join. No reference, no link, " +
        "and the coverage line says so.",
        "For suppliers, a STEP supplier ID always wins, and two IDs are never merged by name. For names without " +
        "an ID, a Splink model scores pairs, a language model looks at the uncertain middle, and anything still " +
        "unsure goes to a person.",
        "Contact details are stripped at ingestion, and the second number is the nightly check that looks for any" +
        " that got through.",
        "The passage count grows as the nightly job reads more reports, and the disagreements come from the batch" +
        " model's dated assertions. The source line dates the whole slide, and that matters, because these " +
        "numbers move every night.",
      ],
      asked: [
        {
          q:
            "Why not convert the local currency?",
          a:
            "A conversion is a modeling choice: which rate, on which date. I'd be putting my number into a " +
            "record. So the gap-year contracts stay in local currency and say so, and converting them with a " +
            "documented rate is near the top of the Data readiness list.",
        },
        {
          q:
            "What's the coverage line?",
          a:
            "Every tool returns one: what it could and couldn't measure, and why. find_comparables lists the " +
            "matches it left out for no STEP reference, no notice, canceled, signed before the notice, and so on." +
            " The agent sees it, and so does the person.",
        },
        {
          q:
            "Why is the link rate so low?",
          a:
            "When I dug in on October 26, two causes. Many award rows carry no STEP reference, and the notice " +
            "search API only pages back 100,000 results, so the notices we held started in 2024. A bulk notice " +
            "export would fix most of it.",
        },
        {
          q:
            "Where are these numbers from?",
          a:
            "Data readiness measures that the nightly job writes to strata.ops.data_readiness, pulled into the " +
            "deck on October 27. The dashboard reads the same table.",
        },
      ],
      diagrams: ["sources_map", "record_journey", "supplier_resolution", "knowledge_graph", "link_score"],
    },
    "answers": {
      cue:
        "About 8 minutes for this section.",
    },
    "retrieval": {
      adds: [
        "The browser posts to /api/ask with the question, the page's scope and its as-of date. The app binds the " +
        "viewer from the headers the proxy forwards, on each request. Nothing about a viewer lives in a global.",
        "The app sends Foundry exactly one JSON message: question, scope, as-of, view and language. The " +
        "instructions and the fifteen tool schemas are stored in the agent's version, synced from the repo. " +
        "Prompt Shields refuses data that contains rules, so the rules live in the instructions and the message " +
        "stays pure data.",
        "The agent asks for tools by name with typed arguments. The app checks the arguments, clamps the as-of " +
        "date, and runs each tool with the viewer's token: SQL with named parameters, never built from strings, " +
        "or hybrid search on AI Search.",
        "Every row comes back with an evidence ID, its public date and a coverage line. The agent gets three " +
        "rounds of tools, and the app enforces it: a fourth request isn't run.",
        "Then it answers in claims, not prose: JSON where each sentence has a kind, its evidence IDs, its " +
        "numbers, its dates and any quote. That structure is what makes checking possible.",
        "Before the full verifier, the app runs the cheap checks. A sentence that would fail goes back once with " +
        "its reasons, and the agent resends the whole answer with no tools.",
        "Then the verifier: IDs, quotes, numbers and dates, then advice and disagreements, and last the model " +
        "judge, gpt-5.4, in one batched call for only the sentences code couldn't prove.",
        "Then the stream, as server-sent events. And the run log, written as the app's own principal so it lands " +
        "even if you close the tab: agent_runs, tool_calls, tool_call_reads with the Delta version of each table " +
        "read, and answer_removals.",
      ],
      asked: [
        {
          q:
            "Why fixed tools instead of letting the model write SQL?",
          a:
            "Correctness, safety and explainability. Each tool has a contract and a benchmark question, so I know" +
            " what it returns. They're read-only, parameterized and run as the viewer, so there's no injection " +
            "path and no privilege escalation. And every result comes with a coverage line and, when it can't " +
            "answer, a reason. For open questions over the records there's still Genie, also run as the viewer.",
        },
        {
          q:
            "What does an evidence ID look like?",
          a:
            "Table, colon, key. strata.gold.passage:31525018/v1/54 is document 31525018, version 1, paragraph 54." +
            " strata.gold.package:KE-NWWDA-541055-CW-RFB is a package.",
        },
        {
          q:
            "Can the agent run its own SQL?",
          a:
            "No. It can only call the fifteen tools. Genie writes SQL, but inside a space limited to metric " +
            "views, run as the viewer, and its rows get evidence IDs like any other tool's.",
        },
        {
          q:
            "Where are runs logged?",
          a:
            "strata.ops.agent_runs, one row per run with the verifier's counts. tool_calls per call, " +
            "tool_call_reads per table and Delta version, answer_removals per removed sentence. Traces go to " +
            "Application Insights with a W3C traceparent, so Foundry's spans join the app's trace.",
        },
        {
          q:
            "Do you use an SDK for Foundry?",
          a:
            "No. It's a few small functions on Python's standard library that call the Responses API as the app's" +
            " service principal. Fewer dependencies, and I control retries and tracing.",
        },
        {
          q:
            "Does the scope chip restrict the search?",
          a:
            "It's a hint to the agent, not a filter. What's enforced is the as-of date and the view. The app " +
            "replaces any as-of the agent writes, and the registry clamps it again.",
        },
      ],
      diagrams: ["question_sequence", "identity_flow", "verifier_flow"],
    },
    "languages": {
      cue:
        "Optional live demo, if there's time. With answers in English, open P127203 and ask: What delayed the " +
        "launch of project activities, the bidding documents and the procurement processes? It quotes the French " +
        "ICR at paragraph 60. Then set answers to French, open P130164 and ask: Les autorisations forestières " +
        "devaient-elles être obtenues avant l'attribution des marchés de travaux ? It answers in French with " +
        "English quotes from ICR paragraph 55, page 23. Set answers back to English afterwards.",
      adds: [
        "The person picks the language of answers in the view settings: English, French, Spanish or Portuguese. " +
        "The screens stay English, from one copy file. A detector notes the question's language, but the person's" +
        " choice decides the answer's.",
        "Same hybrid search. text-embedding-3-large is multilingual, so a French paragraph and an English " +
        "question land near each other by meaning, while the keyword side still matches names and IDs. There's no" +
        " translation step anywhere. Last night's live run scored it: English questions over the French Haiti " +
        "report had a recall at 20 of 0.85.",
        "The agent writes in the person's language. Quotes stay in the language they were written in, by " +
        "instruction and by check.",
        "The verifier runs the same checks in every language. config/languages.toml teaches it how French writes " +
        "numbers and dates, like 1 245 092,76 and 22 juin 2026, so a French sentence's numbers are checked " +
        "against the same rows.",
        "That's why quotes are never translated. A translated quote can't be found word for word on its page, so " +
        "nobody could check it.",
      ],
      asked: [
        {
          q:
            "How well does it work across languages?",
          a:
            "Measured live last night, in run retrieval-20261101T035520Z-7dec094c. English questions over the " +
            "French Haiti completion report: recall at 20 of 0.85 and nDCG at 10 of 0.76, on 25 questions with 60" +
            " labeled passages. French questions over the English India report: recall at 20 of 0.80, but that's " +
            "only 5 questions, so I treat it as a smoke test. For comparison, ICR Review citations score 0.96. " +
            "Precision at 10 is low by construction, because most questions have one or two labeled passages.",
        },
        {
          q:
            "Does it translate anything?",
          a:
            "No. Not the documents, not the query, not the quotes. Search by meaning crosses the language gap, " +
            "and the writer writes in your language. Translating would put a model's words where the source's " +
            "words should be.",
        },
        {
          q:
            "Why text-embedding-3-large?",
          a:
            "It's multilingual and it sits on Azure OpenAI next to the agent's models. I use it at 1,024 " +
            "dimensions, cut down from its full 3,072, to keep the index small. OpenAI's launch numbers put its " +
            "multilingual retrieval score on MIRACL at about 55 percent, against about 31 for the older ada " +
            "model.",
        },
        {
          q:
            "What about Spanish and Portuguese?",
          a:
            "Strata can write both, and the number and date readers are there. But no report in the current " +
            "projects is in either, and no speaker has reviewed the word lists yet, French's included. So French " +
            "is end to end, and the other two are ready but unproven.",
        },
        {
          q:
            "What does the person see when a source is in another language?",
          a:
            "The evidence drawer says In French on a French passage. Under a passage in a different language from" +
            " the answer, it says Strata quotes sources only in the language they were written in. And the check " +
            "line says when a model-judged sentence cites a source in another language.",
        },
      ],
      diagrams: ["passage_anatomy", "question_sequence"],
    },
    "estimate": {
      adds: [
        "Comparable packages come from exact-match SQL, as you saw in the demo. No model here on purpose: the set" +
        " has to make sense to a reviewer.",
        "The floor is 20, in config/thresholds.toml. Under it, Strata shows every package and gives no range. The" +
        " same floor covers subgroups and the calibration set. It's a defensible minimum, and it's one line to " +
        "change.",
        "The past range is Kaplan-Meier, written by hand with exact fractions so a share that lands exactly on a " +
        "quartile isn't read as 0.4999. Open packages are censored. I checked the quartiles once against " +
        "lifelines and statsmodels.",
        "The time estimate is XGBoost with the survival:aft objective, accelerated failure time. Thirteen " +
        "features, all as of the notice date: method, category, market approach, review type, prequalification, " +
        "country, region, estimated amount, planned days, the agency's package count and median days, and a pair " +
        "of governance scores. Open packages go in as right-censored labels.",
        "Ranges are conformal. Every fourth training package is held out of the fit and used only to size the " +
        "ranges, with Kaplan-Meier over the residuals so open packages stay censored there too. So 8 in 10 is " +
        "calibrated on packages it never trained on.",
        "Backtests roll: freeze on January 1 of each year from 2021 to 2025, train on the past, test on the next " +
        "twelve months. The 8-in-10 point has to cover between 75 and 85 percent, and the model has to beat the " +
        "past range and the plan's own planned days.",
        "Promotion has five gates, reported together: win the backtest, win a quarter in shadow on at least 20 " +
        "signed packages, hold coverage for every procurement rules edition, and sign-off from the model owner " +
        "and a lead procurement specialist, who must be different people. Then the champion alias moves in Unity " +
        "Catalog.",
        "Each night the champion scores every package and every what-if into strata.gold.time_estimate_score, so " +
        "the chart answers within 100 milliseconds. The app doesn't even install XGBoost. A small portable " +
        "learner walks the trees from the model's JSON, tested against XGBoost on every fixture package.",
        "And the honest part: no champion exists on this workspace yet. When I ran the backtests on October 25, " +
        "every year abstained because the notice history was too short. That's the pipeline doing its job. It " +
        "refused to size a range on fewer than 20 packages.",
      ],
      asked: [
        {
          q:
            "Why a survival model?",
          a:
            "Because the target is a duration with open cases. A regression on signed packages alone drops the " +
            "slow ones and makes every time estimate too short. A survival model uses open packages as censored " +
            "observations. XGBoost AFT gives me gradient-boosted trees and survival analysis in one, which is " +
            "also what the assessment asked for.",
        },
        {
          q:
            "How do you know it works?",
          a:
            "Rolling backtests on years it hadn't seen, coverage of the 8-in-10 point inside 75 to 85 percent, " +
            "and it must beat the past range and the plan's own dates. On the fixture all of that runs in the " +
            "tests. Live, it hasn't trained yet, and the slide says so.",
        },
        {
          q:
            "Where does the model live?",
          a:
            "In the MLflow experiment /Shared/strata/time_estimate, registered in Unity Catalog as " +
            "strata.gold.time_estimate with champion and challenger aliases. The scores live in " +
            "strata.gold.time_estimate_score, which the estimate_time tool reads.",
        },
        {
          q:
            "Why conformal instead of the model's own intervals?",
          a:
            "AFT gives a distribution, but its width rests on an assumed scale. Conformal calibration sizes the " +
            "ranges on held-out packages instead, so coverage is measured, not assumed. Mine is a censoring-aware" +
            " variant, so I check coverage in the backtests rather than claim a guarantee.",
        },
        {
          q:
            "Why not let the language model give the time estimate?",
          a:
            "It can't show its work on a number, and the verifier would remove any number a tool didn't return. " +
            "Numbers come from tools. The model chooses the tools and writes.",
        },
        {
          q:
            "What other models are there?",
          a:
            "Splink, a Fellegi-Sunter model, for supplier names, with a language model on the uncertain band. An " +
            "experimental rebidding model, logistic regression against calibrated XGBoost, scored on Brier and " +
            "calibration error. And a discrete-time hazard model for project delay, in shadow only. On the " +
            "October 27 snapshot it caught 27 of 82 cases against 12 for the fixed signals, but it stays in " +
            "shadow until it passes its release test.",
        },
      ],
      diagrams: ["time_estimate_flow", "backtest_timeline", "promotion_gates", "two_lane", "rebidding_flow"],
    },
    "checks": {
      adds: [
        "Sentence A cites a passage a tool returned. Sentence B has a number no tool returned, which is the " +
        "classic way a model goes wrong: a believable number with nothing behind it.",
        "The exact checks run in code. Every cited ID must have come back from a tool in this answer, and every " +
        "number and date must match a cited row at the same rounding. Sentence B fails here. Units count, and a " +
        "frequency like 8 in 10 has to come from the record.",
        "Quotes must be on their page, word for word. Then the one model-judged check, whether the sentence " +
        "follows from its sources. It's gpt-5.4 in one batched call, it sees only what code couldn't prove, and " +
        "it can remove sentences but never add them.",
        "Advice needs a lesson or comparable packages behind it. Only get_lessons and find_comparables can back " +
        "advice. And when sources disagree, both sides show, with the side Strata leans on and why.",
        "Sentence A is shown. Sentence B is removed and listed under the answer with its reason. I think that's " +
        "the most important choice in the product: failure is visible.",
        "The benchmark is 43 questions across SQL, time estimates, documents and refusals, with a must-refuse " +
        "question for every refusal key. It hasn't been scored on the live stack yet, and the slide says so.",
      ],
      asked: [
        {
          q:
            "What are the checks, in order?",
          a:
            "As numbered: numbers and dates, IDs, quotes, the judge, advice, disagreements. In code they run " +
            "cheapest first: IDs, quotes, numbers and dates, then advice, disagreements, and the judge last. A " +
            "sentence already removed isn't sent on.",
        },
        {
          q:
            "Isn't a model judging a model weak?",
          a:
            "It would be if it were the only check. It's one of six, it sees only sentences code couldn't prove, " +
            "and it can only remove. Numbers, dates, IDs and quotes never depend on it. If it fails to answer, " +
            "its sentences are removed, not waved through.",
        },
        {
          q:
            "Can the agent fix a removed sentence?",
          a:
            "Once, and only for the cheap checks. Before the full verifier, the app runs IDs, quotes and numbers," +
            " and failures go back with reasons for a single rewrite. Removals by the judge, advice or " +
            "disagreement checks aren't sent back. They're shown.",
        },
        {
          q:
            "How do you evaluate retrieval?",
          a:
            "Precision at 10, recall at 20 and nDCG at 10 on labeled query sets. The job is scheduled weekly on " +
            "the live stack and paused since October 29 to save the Azure credit, so I ran it by hand last night." +
            " Run retrieval-20261101T035520Z-7dec094c gave recall at 20 of 0.96 on ICR Review citations, 0.85 for" +
            " English questions over the French Haiti report, and 0.80 for French questions over the English " +
            "India report, on only 5 questions. Precision at 10 is low by construction, since most questions have" +
            " one or two labeled passages.",
        },
      ],
      diagrams: ["verifier_flow", "eval_layers", "retrieval_eval"],
    },
    "ladder": {
      cue:
        "Optional: open P130164's timeline, click the reports-disagree mark, then Open at page to show the " +
        "paragraph.",
      adds: [
        "The appraisal document is written before the project starts. It's a plan, so it's the weakest evidence " +
        "of what happened.",
        "Status reports are written during the project by the team. Timely, but self-reported.",
        "The completion report comes after closing, with hindsight.",
        "IEG's review is independent and last. For how a project turned out, the highest report that speaks to " +
        "the question wins.",
        "But for a fact about a moment, like a rating on a date, the record made at that moment wins. A " +
        "completion report can't overrule what a status report said in 2016 about 2016. Both rules live in " +
        "config/evidence_ladder.toml.",
        "How they're found: a batch model, gpt-5.4-mini on a Global Batch deployment, reads completion reports, " +
        "reviews and appraisal documents into dated assertions, each kept only if its quote is on its page. Then " +
        "plain code decides whether a pair of assertions can both be true. The model reads, and code judges.",
        "Here's a real one on P130164: a status report rated progress Satisfactory in August 2016, and the " +
        "completion report later said part of the objective was compromised. Both show, with the lean.",
      ],
      asked: [
        {
          q:
            "Why not just take the newest report?",
          a:
            "Newest isn't always best. For how a project turned out, the most independent report wins, which is " +
            "usually the newest. For what was true at a moment, the record made then wins. A single newest-wins " +
            "rule gets one of those wrong every time.",
        },
        {
          q:
            "When does the warning show?",
          a:
            "When a sentence in an answer rests on one side of a disagreement, the disagreement shows under it " +
            "with both sides, the lean, the rule, and what changes if you keep the other side. The person can " +
            "keep the other side. That choice is logged, and it never rewrites the answer.",
        },
        {
          q:
            "How many disagreements are there?",
          a:
            "The data slide shows the count on the latest snapshot. The October 29 nightly run alone found 65 " +
            "across the projects it read.",
        },
      ],
      diagrams: ["disagreement_flow"],
    },
    "grows": {
      cue:
        "About 4 minutes for this section. Leave at least 10 minutes for questions.",
    },
    "loops": {
      adds: [
        "Every night new plans, awards and reports arrive. That's the raw material for every loop.",
        "Weekly, the knowledge loop. A batch model proposes lessons from new completion reports and reviews, each" +
        " with an exact quote. A quote that isn't on its page is rejected, never repaired.",
        "Monthly, the retrieval loop. When someone reports a wrong passage, a person checks it, and it becomes a " +
        "labeled example. A search change ships only if it loses nothing on held-out tests.",
        "Quarterly, the estimates loop, with the promotion gates you just saw. Retraining also starts early if " +
        "coverage leaves its band for 2 months, if the error trails the past range by more than 10 percent, if " +
        "the inputs drift, or if new procurement rules come out.",
        "One dated store keeps every version. Answers and drafts cite the version they used, so an old answer can" +
        " be reproduced even after a lesson changes.",
        "And a subtle one: plans made from the time estimates change the outcomes the models later learn from. So" +
        " Strata logs every time estimate it shows, in strata.ops.exposures, so retraining can account for it.",
      ],
      asked: [
        {
          q:
            "What does in shadow mean?",
          a:
            "The challenger scores every package alongside the champion, but nobody sees its numbers. After a " +
            "quarter, with at least 20 packages signed under both, we compare their errors on real outcomes.",
        },
        {
          q:
            "Who decides a lesson?",
          a:
            "A procurement specialist recommends, and a lead procurement specialist decides. The model only " +
            "proposes, and only with a quote that's on its page word for word.",
        },
        {
          q:
            "How would you swap the language model?",
          a:
            "One line in config/models.toml, then the benchmark in the same change. For the time estimate, train " +
            "a challenger and let the gates decide.",
        },
        {
          q:
            "Why keep the hazard model in shadow if it caught more?",
          a:
            "Catching more isn't enough. It has to pass its release test, and fixed signals are easy to explain. " +
            "Equal-weight rules hold up well, an old result from Dawes in 1979. The model earns its way in or it " +
            "doesn't.",
        },
      ],
      diagrams: ["three_loops", "lesson_flow", "feedback_flow", "exposure_anchor", "promotion_gates"],
    },
    "rollout": {
      adds: [
        "First, World Bank procurement specialists and task team leaders. We measure weekly users, drafts checked" +
        " and exported, and Wrong passage reports. If people don't come back weekly, nothing else matters.",
        "Second, implementing agencies in the same countries. The measure that matters is whether plans made with" +
        " Strata's ranges turn out more accurate than plans made without them.",
        "Third, the public, read-only, with contract trails for closed projects. Active projects show the public " +
        "no signals, time estimates or disagreements.",
      ],
      asked: [
        {
          q:
            "How would you measure the pilot?",
          a:
            "Use first: weekly users, drafts checked and exported. Then quality: Wrong passage reports and " +
            "sentences removed per answer. Then the outcome: plan accuracy against plans made without Strata's " +
            "ranges.",
        },
        {
          q:
            "Which countries come first?",
          a:
            "The ones in config/slice.toml today: Kenya, Bangladesh, Vietnam and Pakistan, in water and " +
            "transport. Adding a country is one entry in that file.",
        },
      ],
      diagrams: ["exposure_anchor"],
    },
    "next-reach": {
      adds: [
        "Spanish and Portuguese are wired: writer instructions, number and date readers. What's missing is " +
        "reports in those languages in the current projects, and a native speaker to review the word lists. " +
        "French needs that review too.",
        "Countries and sectors are one file, config/slice.toml. The nightly job, the tools and the checks don't " +
        "change.",
        "The Data readiness page ranks the gaps. First on my list: STEP references for contracts without one, US " +
        "dollars for the gap years with a documented rate, and older plan versions.",
        "And the whole portfolio. The reader is held back by a daily page cap, which is a cost choice, not a " +
        "design limit.",
      ],
      asked: [
        {
          q:
            "What would it take to add a language?",
          a:
            "Word lists for its numbers, dates and never-write terms in config/languages.toml, reviewed by a " +
            "speaker. A reader template if its reports number paragraphs differently. And benchmark questions in " +
            "that language. Search and the checks are already language-neutral.",
        },
      ],
      diagrams: ["sources_map"],
    },
    "next-product": {
      adds: [
        "Amendment risk. The assessment asked for it, and I didn't fake it, because no public record lists " +
        "contract amendments. With STEP's amendment records it's the same survival setup: time to first " +
        "amendment, censored by contracts still running.",
        "Streaming. Today nothing shows until every check passes. The judge is one batched call, so streaming " +
        "means judging sentence by sentence and paying for more calls. It's a real latency-versus-cost tradeoff, " +
        "and I'd measure it before choosing.",
        "A weekly digest of new signals on the projects a person follows, sent where they already work.",
        "And the agent beside the data. When Databricks' agent runtime is generally available, the orchestrator " +
        "can move next to the tables. The tools and the verifier are plain code behind a narrow interface, so the" +
        " move doesn't touch them.",
      ],
      asked: [
        {
          q:
            "What would you build first?",
          a:
            "Evaluation in the loop. The first live retrieval run was last night, by hand. Its weekly job is " +
            "paused to save the Azure credit, so I'd turn it back on, and run the benchmark against the live " +
            "agent every week too, so every change comes with a number. Then amendment risk, if the records are " +
            "there.",
        },
      ],
      diagrams: ["change_flow", "gate_lanes"],
    },
    "thanks": {
      cue:
        "Leave this slide up for questions. For a live change, open the repo: most changes are one registry or " +
        "config file, and the gate runs before every commit.",
      asked: [
        {
          q:
            "What's the gate?",
          a:
            "The pre-commit hook. It runs the ground-truth SQL and the offline test suite, Python and Playwright," +
            " in under 150 seconds. A failed check stops the commit.",
        },
        {
          q:
            "Where do the extension points live?",
          a:
            "Sources in config/sources.toml, tools in config/tools.toml, thresholds in config/thresholds.toml, " +
            "the countries in config/slice.toml, models in config/models.toml, copy in web/src/copy.ts, benchmark" +
            " questions in evals/benchmark.yaml. Changing a measure means changing its benchmark question in the " +
            "same commit.",
        },
        {
          q:
            "What broke along the way?",
          a:
            "My favorite: search_passages failed for every viewer from October 28, because the App wasn't asking " +
            "for the vector-search scope, so the viewer's token couldn't query the index. The fix was one added " +
            "scope in the deploy. Running every tool as the viewer means every permission has to be granted on " +
            "purpose.",
        },
        {
          q:
            "What would you do differently?",
          a:
            "Get a long notice history in on day one. The search API's paging limit cost the time estimate its " +
            "live training data, and I found it late. And I'd score the evaluation sets live earlier, so every " +
            "change since had a number.",
        },
      ],
      diagrams: ["change_flow", "gate_lanes"],
    },
  } as Record<string, Speaker>,
};

// The structural figures (ticket 47; the second draft's brief, section 5), which the deck and How Strata works
// share. title is the SVG's <title> (60 characters at most); steps its text version in reading order, one line per
// press on the slide, voice-neutral; heading the page section's h2; caption the first-person paragraph How Strata
// works sets above it. A step text holds no number: the number check reads it on the slide.
export const figureCopy = {
  "core-sample": {
    title: "Three strata of evidence",
    heading: "Three kinds of evidence",
    readout: { what: "what", how: "how", why: "why", rest: "rest" },
    steps: [
      "Records show what happened, such as contract awards and procurement notices.",
      "Operational documents show how it was done, such as Procurement Plans and status reports.",
      "Evaluations explain why it worked or not, such as completion reports and their reviews.",
    ],
    caption:
      "I read three kinds of evidence, and I call them strata. Records show what happened, such as contract awards and " +
      "procurement notices. Operational documents show how it was done, such as Procurement Plans and Implementation " +
      "Status and Results Reports (ISRs). Evaluations explain why it worked or not, such as completion reports and " +
      "their independent reviews.",
  },
  strata: {
    title: "Where the three strata live today",
    heading: "Where each kind of evidence lives today",
    steps: [
      "Records show what happened: contract awards, procurement notices, projects and governance indicators.",
      "Operational documents show how it was done: Procurement Plans kept in STEP, and Implementation Status and Results Reports.",
      "Evaluations show why it worked or not: appraisal documents, completion reports and the Independent Evaluation Group's reviews.",
      "Each lives in a different place, so today a specialist joins them by hand.",
    ],
    caption:
      "Records of what happened, operational documents on how it was done, and evaluations of why it worked or not " +
      "each live in a different place. Today a procurement specialist joins them by hand. I join them once, on the " +
      "project ID and the package's STEP reference, and keep the join current every night.",
  },
  "one-answer": {
    title: "One question, three strata, one cited answer",
    heading: "How one question uses all three",
    steps: [
      "It starts from a question about a package.",
      "Records of what happened give comparable packages, and how long each took.",
      "Operational documents give each step's planned and actual dates.",
      "Evaluations give what went wrong and what helped, quoted with paragraph and page.",
      "They meet in one answer, and every sentence in it names its source.",
    ],
    caption:
      "When you ask about a package, I look in all three at once. Records give me comparable packages. Operational " +
      "documents give me each step's planned and actual dates. Evaluations give me what went wrong and what helped. I " +
      "put them into one answer, and every sentence names its source.",
  },
  layers: {
    title: "Strata's layers and where each runs",
    heading: "Where I run",
    steps: [
      "World Bank open data and documents arrive every night and land in bronze, silver and gold tables on Databricks.",
      "The knowledge model is a set of Unity Catalog tables with an edge table, numbered passages and dated assertions.",
      "The tools are fixed SQL on the gold tables, hybrid search over passages, a Genie space for open questions, and the time estimates.",
      "The Strata agent in Microsoft Foundry picks the tools and writes each claim with the IDs of its evidence.",
      "The verifier checks every sentence against the rows and passages before anyone sees it.",
      "The Strata app, a Databricks App, runs each tool with the viewer's own permissions.",
      "The data, search and tools run on Databricks. The agent runs in Microsoft Foundry, and the language models are Azure OpenAI.",
    ],
    caption:
      "The data and the search index stay in Databricks. The agent that decides what to look up runs in Microsoft " +
      "Foundry, and the language models are Azure OpenAI. I run every lookup with your own permissions, so you see " +
      "only what your account may see, and I keep every row an answer used so that I can check it.",
    caption2:
      "Each time you open a page, I record who you are, which page and view you opened, and when. When you ask a " +
      "question, I also keep the steps I took, so the people who run Strata can check my work.",
  },
  pipeline: {
    title: "Where the knowledge model comes from",
    heading: "Where my data come from",
    steps: [
      "Each night a job reads World Bank open data from where it stopped: awards, notices, projects, documents, plans and indicators.",
      "Bronze keeps every page as the source sent it.",
      "Silver types and cleans the rows, strips contact details and matches keys.",
      "Gold joins them into the knowledge model: projects, packages, contracts and passages.",
      "The app, the dashboard, Genie and the agent all read the same gold tables.",
      "Every row keeps the date it became public, so any answer can be replayed as of its date.",
    ],
    caption:
      "Every night I read the World Bank's open data from where I stopped the night before. I keep what arrived as it " +
      "came. Then I clean it, strip contact details and join it into one knowledge model. The app, the dashboard and " +
      "the agent all read that model. Every row keeps the date it became public, so I can answer as of a past date.",
  },
  reading: {
    title: "How a document becomes numbered passages",
    heading: "How I read a document",
    steps: [
      "A document arrives: an appraisal document, a status report, a completion report or a Procurement Plan.",
      "The page router checks each page.",
      "Clean pages use the text the World Bank already publishes, word for word.",
      "Scanned pages and tables go through a layout parser, a tool that reads page layouts.",
      "Both roads end in numbered passages, each with its paragraph number and page.",
      "The passages go into the hybrid search index. A table's summary never backs a number; its rows do.",
    ],
    caption:
      "I split every report into its numbered paragraphs and keep each one's page, because that is how the World " +
      "Bank's evaluators cite reports. For clean pages I use the text the World Bank already publishes. Scanned pages " +
      "and tables first go through a tool that reads page layouts.",
  },
  "knowledge-model": {
    title: "Strata's knowledge model",
    heading: "How records and documents connect",
    steps: [
      "A project has packages. Each package has its STEP reference and becomes contracts. Strata matches each contract's supplier on its STEP supplier ID. They are strata.gold.project, package, contract and supplier.",
      "Documents describe a project, and each document has numbered passages, in strata.silver.documents and strata.gold.passage.",
      "A lesson quotes a passage, word for word. Its versions are in strata.ops.lesson_versions.",
      "A passage can be the source of an assertion, such as a rating on a date. Two assertions about the same thing, for the same time, that cannot both be true make a disagreement. They are strata.gold.assertion and strata.gold.disagreement.",
      "A contract and a passage about the same work appeared together, a row in strata.gold.edge. The link never says one caused the other.",
      "Every row keeps the date it became public.",
    ],
    caption:
      "A project ID links everything about a project. A package links its plan row, its notice and its contracts " +
      "through its reference in Systematic Tracking of Exchanges in Procurement (STEP). When a contract and a " +
      "paragraph of a completion report are about the same work, I say they appeared together. I never say one caused " +
      "the other. Every row keeps the date it became public, so I can answer as of a past date.",
  },
  architecture: {
    title: "How Strata fits together",
    heading: "How Strata fits together",
    steps: [
      "Public sources: Finances One for awards, IEG ratings, loans and credits, the search APIs for procurement" +
        " notices and projects, the Documents API for appraisal documents, status reports, completion reports and" +
        " plans, and the Indicators API for CPIA and WGI.",
      "A nightly job on serverless compute fetches only what changed, in a chain of tasks, and writes it to " +
        "bronze.",
      "On Databricks, bronze keeps each page as received, silver types the rows and holds the passages, gold is" +
        " the knowledge model, and ops keeps runs, answers and decisions.",
      "On gold sit the AI Search index for hybrid search over gold.passage, the Genie space over the metric " +
        "views, the time estimate models in MLflow as champion and challenger, and the AI/BI dashboard.",
      "The Databricks App serves the web app and its API, runs the tools as the viewer with SQL on gold and " +
        "search on the index, checks every sentence with the verifier and keeps drafts. Lakebase holds the app's " +
        "state.",
      "Microsoft Foundry runs the orchestrator agent and the writers on Azure OpenAI models, behind a " +
        "guardrail, and trades tool calls and results with the app. People ask in the app.",
    ],
    caption:
      "World Bank sources come in every night, and only what changed. Everything I know lives in one set of " +
      "Databricks tables, and the search index, the Genie space and my models sit on them. I run every tool as you," +
      " so you only see what you're allowed to see, and my verifier checks every sentence before you read it.",
  },
  languages: {
    title: "One question, any language",
    heading: "How I work across languages",
    steps: [
      "The question comes in French or English. The person picks the language of answers, and the screens" +
        " stay in English.",
      "Hybrid search on strata.gold.passage_index: the embedding carries the meaning across languages, " +
        "the keyword side matches names and IDs, and a reranker orders the matches.",
      "The agent writes in the person's language, and every quote stays in the language its source was " +
        "written in.",
      "The verifier runs the same checks. It reads French numbers and dates through " +
        "config/languages.toml, and finds each quote word for word on its page.",
      "The answer comes back in French, and the English report's quotes stay in English. A translated " +
        "quote couldn't be found on its page, so none is translated.",
    ],
    caption:
      "Ask me in French or English. I search by meaning, so a paragraph can match your question even when" +
        " it's written in another language, and I answer in yours. I never translate a quote, because a " +
        "translated quote can't be found on its page, so you couldn't check it.",
  },
  retrieval: {
    title: "What happens behind one answer",
    heading: "How I check an answer before you see it",
    steps: [
      "The person asks in the app. The request carries the question, the page's scope and as-of date, and" +
        " the view, and the app knows the viewer from the headers the Databricks App proxy forwards.",
      "The app sends the Strata agent in Microsoft Foundry one message of data. Its instructions and tool" +
        " list live in a versioned prompt agent synced from the repo, never in the message.",
      "The agent asks for tools, such as find_comparables. The app runs each one with the viewer's own " +
        "token: fixed SQL on the warehouse, hybrid search on strata.gold.passage_index, or the Genie space.",
      "Every row comes back with an evidence ID and the date it became public, and the app hands the " +
        "results back to the agent, for a fixed number of rounds.",
      "The agent answers in claims: each sentence with its kind, its evidence IDs, its numbers and dates," +
        " and any quote.",
      "The app runs the quick checks first. A sentence that would fail goes back to the agent once, with " +
        "its reasons.",
      "Then the verifier runs every check: numbers and dates, IDs, quotes, a model judge, advice and " +
        "disagreements. It removes any sentence it can't back.",
      "The app streams the kept sentences, their evidence and each removed sentence with its reason, and " +
        "logs the run to strata.ops.",
    ],
    caption:
      "I decide which tools to call, but the app runs them as you, so I only see rows you're allowed to " +
        "see. Every sentence I write carries the IDs of its evidence, and the verifier tests each one " +
        "before you read it. If it can't back a sentence, it removes it and shows you why.",
  },
  estimate: {
    title: "How a time estimate is made",
    heading: "How I size a package's schedule",
    steps: [
      "Comparable packages come from exact-match SQL on the stated criteria, over strata.gold.package, " +
        "notice and contract. No model picks them, so anyone can see why a package is in.",
      "If there are too few comparable packages, Strata shows every one and gives no range.",
      "Otherwise the past range is a Kaplan-Meier curve. Packages still open stay in as not signed yet, " +
        "so the slow cases don't drop out.",
      "The time estimate is an XGBoost survival model, an accelerated failure time model, trained only on" +
        " what was known at each package's notice date.",
      "Conformal calibration sizes its ranges on packages held out of training, so the 8-in-10 point is " +
        "tested, not assumed.",
      "Rolling backtests freeze the data each January and test the model on the next year's packages it " +
        "had not seen.",
      "A challenger replaces the champion only after it wins its backtest and a quarter in shadow, holds " +
        "its coverage for each rules edition, and the model owner and a lead specialist sign off.",
      "Each night the champion scores every package and what-if into strata.gold.time_estimate_score. The" +
        " package page shows the past range and the time estimate, or why there is none.",
    ],
    caption:
      "I find comparable packages with plain SQL on the criteria you state, so you can see why each one " +
        "is in. Packages still open stay in my past range as not signed yet, so the slow cases don't " +
        "vanish. My time estimate comes from a survival model that has to win its backtest and a quarter in" +
        " shadow before it replaces the old one, and with too few packages I give no range at all.",
  },
  checks: {
    title: "The checks every sentence passes",
    heading: "The checks every sentence passes",
    steps: [
      "Sentence A cites a passage the tools returned. Sentence B has a number no tool returned.",
      "The verifier checks the numbers, then the cited IDs. Sentence B fails, because no row holds its number.",
      "Next it checks the quotes, and whether each sentence follows from its passages, the one check a model judges.",
      "Last, advice needs a lesson or comparable packages behind it, and a disagreement must show both sides.",
      "The verifier shows sentence A. It removes sentence B and lists it under the answer with the reason.",
    ],
    caption:
      "Before you see an answer, every sentence in it meets my checks in order. A number has to match a row a tool " +
      "returned, a citation has to come from this answer's lookups, and a quote has to be on its page. A sentence " +
      "that fails is taken out, and I list it under the answer with the reason.",
  },
  ladder: {
    title: "Which report Strata leans on",
    heading: "When two reports disagree",
    steps: [
      "At the bottom is the appraisal document, written before the project started.",
      "Next is the last status report, written during the project.",
      "Next is the completion report, written after the project closed.",
      "At the top is a review by the Independent Evaluation Group (IEG), written after the project closed. For how a project turned out, the highest report that speaks to the question wins.",
      "For a fact about a moment, such as a rating on a date, the record made at that moment wins.",
    ],
    caption:
      "Sometimes two reports say different things about the same project for the same time. I show both, in the " +
      "order they were written, and I say which one I lean on and why. For how a project turned out, I lean on the " +
      "most independent report written after it closed. For a fact about a moment, such as a rating on a date, I lean " +
      "on the record made at that moment.",
  },
  loops: {
    title: "Three loops, one dated store",
    heading: "How I learn, and who decides",
    steps: [
      "Plans, awards and new reports arrive every night.",
      "The knowledge loop runs weekly. A new completion report gives a proposed lesson with its exact quote. A specialist recommends it, and a lead procurement specialist decides.",
      "The retrieval loop runs monthly. A report of a wrong passage becomes a label only after a person checks it. Search changes only if it loses nothing on held-out tests.",
      "The estimates loop runs quarterly. A new model replaces the old one only after it wins its backtest and a quarter in shadow.",
      "One dated store keeps every version, and answers and drafts cite the version they used.",
      "Plans made from the time estimates change the outcomes the models later learn from, so Strata logs every estimate it shows.",
    ],
    caption:
      "New reports arrive every night. When one holds a lesson, I propose it with its exact quote and page, and two " +
      "people decide whether it enters the library. When you report a wrong passage, a person checks your report " +
      "before it changes anything. My time estimates change only after a new model does better than the old one on " +
      "years it had not seen.",
  },
};

export type FigureCopyId = keyof typeof figureCopy;
