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
export type Speaker = { cue?: string; adds?: (string | null)[]; asked?: { q: string; a: string }[] };

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
        "Thank you for having me. This is Strata, a working demo I built for this assessment, only on World Bank open" +
        " data. Every number you'll see came from a measured run or a setting, and you can point at any of them to " +
        "see which. Please stop me anywhere.",
    },
    agenda: {
      title: "The problem, a live demo, then how Strata is built, answers and grows",
      notes:
        "I'll follow one real case the whole way through, a water works package in Kenya that's still pending after " +
        "its project closed.",
    },

    // ── Three strata ──
    strata: {
      title: "A procurement plan needs three strata of evidence, and today they sit apart",
      source: "the assessment brief, section 1.",
      notes:
        "The assessment talks about three strata of evidence, and Strata is named for them.",
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
        "These are the assessment's own pains.",
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
        "Strata respects who owns what.",
    },
    idea: {
      title: "Strata joins the three strata once, so one question gets one cited answer",
      notes:
        "Here's the whole idea in one picture, on the Kenya water package.",
    },

    // ── Strata at work ──
    workOpener: {
      notes:
        "Let me show you Strata at work, on live World Bank records.",
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
        "Here's a real Procurement Plan from a Kenyan water agency, and Strata checks every row of it. This package, " +
        "{step}, is marked Watch. It's still pending, and its project has closed.",
    },
    demoPackage: {
      title: "Comparing that package with the packages that came before it",
      box: "Package {step}, which the plan check marks Watch",
      action: "Open the package",
      lines: [
        "Each comparable package is a dot on a month axis, from its notice to its signed contract.",
        "Hollow dots are still open, and the range counts them, so the slow cases stay in.",
        "The time estimate dates each STEP step, with its track record from years it had not seen.",
      ],
      note: "STEP is Systematic Tracking of Exchanges in Procurement, where Procurement Plans are kept.",
      notes:
        "Here's that same package, next to the packages that came before it.",
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
        "Now I'll ask Strata about this package, in plain words.",
    },

    // ── How it is built ──
    builtOpener: {
      notes:
        "That was the surface. Here's what sits underneath it, from the data up.",
    },
    layers: {
      title: "The data, search and tools run on Databricks, and the agent and its models run in Microsoft Foundry",
      notes:
        "I'll build the system from the bottom, one layer at a time.",
    },
    architecture: {
      title: "The whole system, from the public sources to the person asking",
      notes:
        "Here's every part on one page, in the order the data travels.",
    },
    pipeline: {
      title: "Every night, World Bank open data become one dated knowledge model",
      notes:
        "Here's how the data gets in, every night.",
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
        "Documents are the hard part, so here's how Strata reads them.",
    },
    knowledge: {
      title: "Records and documents meet at the passage, joined on STEP's keys",
      note: "STEP is Systematic Tracking of Exchanges in Procurement, where Procurement Plans are kept.",
      notes:
        "This is the knowledge model, and every box is a table.",
    },
    gap: {
      title: "No dataset publishes contract awards for fiscal {start} to {end}",
      titleNoGap: "Contract awards are published for every fiscal year Strata reads",
      titleNone: "Strata has not measured its contract award rows yet",
      gapNote: "Award notices cover the gap years, in local currency, so Strata keeps them apart from awards in US dollars.",
      linked:
        "{ratio} contract award rows since fiscal 2020 share their Systematic Tracking of Exchanges in Procurement (STEP) " +
        "reference with a procurement notice. That reference is the key that joins an award to its notice.",
      noneLine: "This slide fills in once the workspace job counts the award rows.",
      link: "Open Data readiness",
      source: "Strata's data readiness measures, taken {date}.",
      knownSource: "the known gaps in Strata's source registry, which the Data readiness page shows.",
      chartAlt: "Bars show contract award rows for each fiscal year from {first} to {last}, by the dataset or the award notices they came from.",
      chartGap: "Neither awards dataset covers fiscal {start} to {end}.",
      gapLabel: "No awards dataset",
      // The chart's key: a source's name and the first and last fiscal years the chart draws from it.
      keyName: (source: string, first: string, last: string) => `${source}, ${first} to ${last}`,
      table: { year: "Fiscal year", rows: "Contract award rows", from: "From" },
      notes:
        "I'd rather show you a gap than hide it. Neither contract awards dataset covers fiscal {start} to {end}.",
      notesGap:
        "I'd rather show you a gap than hide it. Neither contract awards dataset covers fiscal {start} to {end}.",
      notesNone:
        "Strata hasn't measured the award rows yet, so I'll show you the Data readiness page instead.",
    },

    // ── How it answers ──
    answersOpener: {
      notes:
        "Next, how Strata answers, and how it checks itself before you see anything.",
    },
    retrieval: {
      title: "The agent picks the tools, and the app runs them as the person asking",
      notes:
        "Here's the Kenya answer from the inside, one message at a time.",
    },
    estimate: {
      title: "A time estimate starts from comparable packages, and gives no range when there are too few",
      few: "Under {min} comparable packages, Strata shows every package and gives no range.",
      backtest: "In {year}, {ratio} packages that Strata had not seen were signed within its 8-in-10 point.",
      backtestNone: "The backtest has not run on the workspace yet, so the model's track record is not shown here.",
      source: "Strata's backtest, measured {date}.",
      notes:
        "Same package, now the model behind its estimate.",
    },
    checks: {
      title: "Every sentence meets {checks} checks before anyone sees it",
      heading: "In the latest benchmark run,",
      passed: "{ratio} benchmark questions passed.",
      refused: "Strata turned down {ratio} questions it must refuse.",
      none: "The benchmark has not run with all {checks} checks yet, so there are no results to show.",
      source: "Strata's benchmark run of {date}.",
      notes:
        "This is the verifier, the part I'd defend hardest. It's plain code, and it runs on every answer.",
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
        "The assessment asks what to do when a completion report and the supervision ratings disagree. Kenya water " +
        "has no completion report yet, so here's a closed roads project in India, P130164.",
    },
    hindsight: {
      title: "Strata showed {ratio} risks that completion reports later blamed",
      titleNone: "Strata's hindsight test has not run yet",
      method:
        "The test froze Strata at each closed pilot project's approval date. Strata listed its top risks for each " +
        "main package, and {coders} people compared them with the risks the completion report blamed.",
      // Before the test has run, the slide says what it does, in the present tense: nothing has happened yet.
      methodPlanned:
        "The test freezes Strata at each closed pilot project's approval date. Strata lists its top risks for each " +
        "main package, and {coders} people compare them with the risks the completion report blamed.",
      checklist:
        "That was at {top} risks per package. A checklist of the sector's {checklist} most common risks showed " +
        "{ratio} of the same blamed risks.",
      none: "The test runs on the workspace. Until it has, there is no result to show.",
      source: "Strata's hindsight test of {date}.",
      notes:
        "This is the test I trust more than any demo. Freeze Strata at a project's approval date, let it build its " +
        "risk table, and {coders} people compare it with what the completion report later blamed.",
      notesInterval: "With {level} confidence, the share it caught lies between {low} and {high} percent.",
    },

    // ── How it grows ──
    growsOpener: {
      notes:
        "Last part: how Strata learns and grows, without drifting.",
    },
    loops: {
      title: "{loops} loops learn on their own schedules, and people decide each change",
      notes:
        "Each loop runs on its own clock.",
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
        "The rollout follows who carries the risk of a wrong answer.",
    },
    spend: {
      title: "Hard caps limit the cost, because a budget only sends alerts",
      spent: "Azure spend to {date} was {spent}, against a budget of {budget} for {period}.",
      noSpend: "Strata has not recorded its Azure spend yet.",
      caps: [
        "Every model deployment has a token limit.",
        "Reading documents has a daily page cap.",
        "The app has a limit on its replicas.",
      ],
      source: "Azure cost records to {date}.",
      notes:
        "Budgets only send alerts, and cost data can arrive a day late, so Strata uses hard caps.",
    },
    change: {
      title: "A change request touches one file, and the gate checks it before every commit",
      lines: [
        "Sources, tools, signals, thresholds, the pilot projects, models, copy and benchmark questions each live in one registry or config file.",
        "Before every commit, the gate runs the ground-truth SQL and the offline tests.",
        "A failed check stops the commit, so what you see is the code that passed.",
      ],
      ask: "What change would you like to see made, live?",
      notes:
        "This is where you test me.",
    },
    rubric: {
      title: "Where Strata earns each point of the rubric",
      caption: "The rubric map",
      columns: { dimension: "Dimension", points: "Points", where: "Where Strata earns it", open: "What you can open" },
      where: {
        architecture: "Numbered passages, a page router, a knowledge model with dated assertions, and STEP keys first",
        method: "A survival model with backtests, retrieval over SQL, search and the graph, and {checks} checks",
        domain: "Plans checked row by row in STEP's own words, the 2025 Regulations, and data gaps stated",
        operations: "Nightly jobs, gated learning loops, adoption measures, a phased rollout, cost caps and the change drill",
      } as Record<string, string>,
      open: {
        readiness: "Data readiness",
        connections: "Connections for {project}",
        workspace: "The package workspace",
        checkPlan: "Check a plan",
        dashboard: "The dashboard",
      },
      source: "the assessment brief, section 5, for the dimensions and points. STEP is Systematic Tracking of Exchanges in Procurement.",
      notes:
        "This maps the assessment's rubric to what you can open.",
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
    thanks: {
      title: "Thank you",
      figure: "Every night, new reports settle on the core as a new layer, and Strata keeps every layer.",
      ask: "What would you like to ask?",
      links: { app: "Open Strata", proposal: "Read the proposal", dashboard: "Open the dashboard", repo: "Read the code" },
      notes:
        "Thank you. Everything on these slides is built and runs in the app, and you can open any of it right now. " +
        "I'm glad to take your questions, or to make a change live, here in the room.",
      notesAfterLimits:
        "Thank you. I'm glad to take your questions, or to make a change live, here in the room.",
    },
  },

  // The presenter's side of each slide, by slide id: a cue for what to do on it, and the questions a technical
  // panel may ask about it, each with an answer to give as written. What to say is each slide's notes.
  speaker: {
    "welcome": {
      cue:
        "Press F for full screen. Keep /present/notes open in a second window.",
      asked: [
        {
          q:
            "What is Strata, in one sentence?",
          a:
            "A procurement assistant that answers questions about World Bank projects, and checks every number and quote " +
            "against the records before you see the answer.",
        },
        {
          q:
            "Is this real, or a mockup?",
          a:
            "It's real. It runs as a Databricks App on a paid workspace and reads World Bank open data every night. " +
            "Everything on these slides is built, except what I list near the end as designed but not built.",
        },
        {
          q:
            "Who is it for?",
          a:
            "World Bank procurement staff first, then implementing agencies, then the public, read-only. That order " +
            "follows who can judge a wrong answer.",
        },
      ],
    },
    "agenda": {
      adds: [
        "First, why this problem matters.",
        "Then Strata at work, live, on that Kenya package.",
        "Then what sits under it: the data, the tables and the tools.",
        "Then how it answers, and how it checks every number before you see it.",
        "And last, how it learns and grows without drifting.",
      ],
    },
    "strata": {
      adds: [
        null,
        null,
        null,
        "That join by hand is the job Strata takes on.",
      ],
      asked: [
        {
          q:
            "Where does each stratum's data come from?",
          a:
            "Records come from the World Bank's contract awards and procurement notices datasets. Plans come from STEP, " +
            "the Systematic Tracking of Exchanges in Procurement. Status and completion reports come from the Documents " +
            "and Reports API. All of it is public.",
        },
      ],
    },
    "cost": {
      cue:
        "On the last press, ask the room the question and wait for an answer.",
    },
    "who": {
      adds: [
        null,
        null,
        null,
        "So ask it about bid evaluation, awards or complaints, and it turns the question down and says why.",
      ],
      asked: [
        {
          q:
            "What if someone asks it to evaluate a bid?",
          a:
            "It turns the question down and says that bid evaluation, awards and complaints belong to people under the " +
            "Procurement Regulations. Those questions sit in the benchmark as must-refuse questions, so every run " +
            "measures whether it still says no.",
        },
      ],
    },
    "idea": {
      adds: [
        null,
        "For the Kenya package, that's every comparable water works package and how long it took.",
        null,
        null,
        "The rest of this talk is that picture, made real.",
      ],
      asked: [
        {
          q:
            "Why not just put a chatbot over the documents?",
          a:
            "Because a chatbot can't tell you where a number came from. Strata's agent can only cite rows and passages " +
            "its tools returned, and the verifier removes any sentence it can't match to them.",
        },
      ],
    },
    "work": {
      cue:
        "Let the figure play a few seconds, then press on.",
    },
    "demo-plan": {
      cue:
        "Click Open the plan check. In the App, find the package's row and click its signal to show the record behind" +
        " it. Then come back and press.",
      adds: [
        null,
        "If the awards data show it signed after all, Strata shows both records instead of quietly picking one.",
      ],
      asked: [
        {
          q:
            "Where do the plan's rows come from?",
          a:
            "From STEP. The nightly job reads each plan version into strata.silver.plan_rows and " +
            "strata.silver.plan_versions, so Strata can hold a plan against its own earlier versions.",
        },
        {
          q:
            "What does the plan check look at?",
          a:
            "Each row against past ranges for packages like it, against the review thresholds, and against the plan's own" +
            " dates. Each hit is a signal that names the record behind it.",
        },
        {
          q:
            "Is a signal a finding against the agency?",
          a:
            "No. A signal is a reason to look, never a finding. Strata never ranks, colors or scores agencies by their " +
            "signals.",
        },
      ],
    },
    "demo-package": {
      cue:
        "Click Open the package. Then come back and press.",
      adds: [
        "Comparable means the same method, category, market approach and review type, a similar size, the same region" +
        " and a recent period.",
        "Dropping the open ones would make every estimate look faster than reality.",
        "Each estimate is backtested on years the model never saw.",
      ],
      asked: [
        {
          q:
            "How do you pick comparable packages?",
          a:
            "By stated criteria, not by a model: the same method, category, market approach and review type, a similar " +
            "size, the same region and a recent period. The page shows the criteria, so anyone can check them.",
        },
        {
          q:
            "Why keep packages that are still open?",
          a:
            "Because dropping them makes every estimate look faster than reality, and the slowest packages are the ones " +
            "still open. The survival model counts each open package as at least as long as it has run so far.",
        },
        {
          q:
            "Which tables does this page read?",
          a:
            "find_comparables reads strata.gold.package, notice and contract, with the plan's rows from " +
            "strata.silver.plan_rows. The time estimate reads strata.gold.time_estimate_score.",
        },
      ],
    },
    "demo-answer": {
      cue:
        "Click Ask Strata about this package at the foot of the page, paste the question and press Enter. Watch the " +
        "steps, then come back and press. If the App stalls, go back one slide and show the recorded answer.",
      adds: [
        null,
        "That's the check line under the answer. It counts the numbers that matched a record.",
        "Kenya water is still running, so this answer rests on records. The report paragraphs come with a closed " +
        "project in a few minutes.",
      ],
      asked: [
        {
          q:
            "What stops it from making a number up?",
          a:
            "The verifier. For every number in a sentence, it looks for the same value, at the same rounding, in a row a " +
            "tool returned for this answer. If no row has it, the sentence is removed and listed with the reason.",
        },
        {
          q:
            "What if the model is down or slow?",
          a:
            "The answer says so and offers to try again. It never fills the gap with a guess. For this talk, the slide " +
            "before this one also holds a recorded answer.",
        },
        {
          q:
            "Can people outside the World Bank see this?",
          a:
            "Not yet. The rollout starts with World Bank staff, and the public comes last, read-only.",
        },
      ],
    },
    "built": {
      cue:
        "Let the figure play a few seconds, then press on.",
    },
    "layers": {
      adds: [
        null,
        "Plain Delta tables plus one edge table, so search and SQL share one set of permissions.",
        "The agent can't write its own SQL. It can only call these tools.",
        "All the model does is pick tools and write claims.",
        "Exact matching in code, except one check a model judges.",
        "Each tool runs with the viewer's own token, so Unity Catalog decides what they can see.",
        "So the data never leaves Databricks, and the model never touches the warehouse.",
      ],
      asked: [
        {
          q:
            "Why split Databricks and Foundry?",
          a:
            "The data and its permissions live in one place, Unity Catalog, so every query runs as the person asking. The" +
            " model lives in Foundry, behind Azure's quotas and content safety. The agent never holds a credential to the" +
            " data, because the app runs each tool for it.",
        },
        {
          q:
            "How does it know who the viewer is?",
          a:
            "The Databricks App forwards the viewer's own token with each request, and the app binds it to that request " +
            "only. Nothing about a viewer stays in the server between requests.",
        },
        {
          q:
            "What's the stack?",
          a:
            "A FastAPI server and a React app, deployed as a Databricks App. Python for the pipeline and the tools, Delta" +
            " tables in Unity Catalog, Databricks AI Search for passages, and Azure OpenAI models in Microsoft Foundry.",
        },
        {
          q:
            "How do you stop a document from steering the agent?",
          a:
            "Every passage is screened by Prompt Shields when it's read in. A passage with an attack in it is held back " +
            "from search, and the coverage line counts it.",
        },
      ],
    },
    "architecture": {
      adds: [
        "Everything Strata knows comes from these public APIs. Nothing is private.",
        "It's one Databricks job that fetches only what changed since the last run.",
        "The medallion tables in Unity Catalog. Gold is what every answer reads.",
        "The search index, Genie and the models all sit on the same gold tables, so they can't disagree.",
        "The app runs every tool as the viewer, and the verifier checks every sentence before anyone sees it.",
        "The agent lives in Foundry and never touches the data. It asks, and the app runs the tool.",
      ],
      asked: [
        {
          q: "Why is the agent outside Databricks?",
          a:
            "So the model never holds a credential to the data. Foundry gives the agent, Azure OpenAI's quotas and the " +
            "guardrail; Databricks keeps the data and its permissions. The app is the only bridge, and it runs every " +
            "tool as the person asking.",
        },
        {
          q: "What's Lakebase for?",
          a:
            "Postgres for the app's own state, like planned packages and clicks, so every page is fast. Analytical reads " +
            "stay on the warehouse.",
        },
        {
          q: "Why serverless for the nightly job?",
          a:
            "It runs once a night and only fetches what changed, so paying for an always-on cluster makes no sense. " +
            "Each task picks up where the last run stopped.",
        },
        {
          q: "What's champion and challenger?",
          a:
            "The time estimate model in production is the champion, and a new one is the challenger. The challenger only " +
            "replaces it after winning the backtest and a quarter in shadow, and MLflow keeps both versions.",
        },
      ],
    },
    "pipeline": {
      adds: [
        null,
        "That's strata.bronze.api_pages, kept exactly as it came.",
        "Silver is where contact details come out, at ingestion.",
        "Tables like strata.gold.package, notice and contract.",
        "One copy of the truth, read by everything.",
        "That's what lets us test Strata honestly on the past.",
      ],
      asked: [
        {
          q:
            "Which tables are those?",
          a:
            "Bronze is strata.bronze.api_pages. Silver has tables like strata.silver.plan_rows and strata.silver.notices." +
            " Gold has strata.gold.package, notice, contract, passage, and the edge table, strata.gold.edge.",
        },
        {
          q:
            "Why strip contact details?",
          a:
            "Notices carry names, emails and phone numbers, and Strata has no use for them. Silver removes them at " +
            "ingestion, and a nightly check looks for any pattern the stripper should have caught.",
        },
        {
          q:
            "What does as of a date mean?",
          a:
            "Every row keeps the date it became public. Ask a question as of a past date, and Strata only uses what was " +
            "public then. That's how we test it honestly on the past.",
        },
      ],
    },
    "reading": {
      adds: [
        null,
        null,
        "It's free, and it keeps the exact words the quote check needs.",
        "Only these pages cost money, and a daily page cap limits them.",
        "That's the citation you'll see under every answer.",
        "That's strata.gold.passage, indexed in Databricks AI Search.",
        null,
      ],
      asked: [
        {
          q:
            "What is the layout parser?",
          a:
            "A reader for pages the published text can't be trusted with, like scans, tables and figures. It reads the " +
            "page's rows, columns and text. A daily page cap keeps its cost down.",
        },
        {
          q:
            "How do you know a quote is real?",
          a:
            "The verifier finds every quote word for word on its cited page before the answer shows. A quote that isn't " +
            "there is removed, with the reason.",
        },
        {
          q:
            "Where do the passages live?",
          a:
            "In strata.gold.passage, one row per numbered paragraph, with its document, page and public date. Databricks " +
            "AI Search keeps an index over it for hybrid search, by words and by meaning.",
        },
        {
          q:
            "Why not send every page to the layout parser?",
          a:
            "Cost and fidelity. The published text is free and keeps the exact words, which the quote check needs. The " +
            "parser only gets the pages where that text can't be trusted, under a daily page cap.",
        },
        {
          q:
            "Why hybrid search?",
          a:
            "Procurement text is full of codes and names, which keyword search finds exactly, and questions come in plain" +
            " words, which vectors match by meaning. AI Search runs both, fuses them and reranks the best.",
        },
      ],
    },
    "knowledge": {
      adds: [
        null,
        null,
        "A lesson can't drift from its source, because its quote has to be on the page.",
        "This is how Strata spots reports that disagree.",
        "It never says one caused the other.",
        "So any answer can be asked as of a past date.",
      ],
      asked: [
        {
          q:
            "Why not a graph database?",
          a:
            "One copy of the data, one set of permissions and one place to audit. The links Strata needs are shallow, so " +
            "an edge table, strata.gold.edge, does the job, and SQL joins across it.",
        },
        {
          q:
            "What's an assertion?",
          a:
            "A dated claim a document makes about one thing, like a rating for a period, with its source passage. Two " +
            "assertions about the same thing, for the same time, that can't both be true make a disagreement.",
        },
        {
          q:
            "How do you link a contract to a paragraph?",
          a:
            "By what they share, such as the project, the work and the time, scored part by part. The drawer shows each " +
            "part, the score and the threshold, so a reviewer can see why they're linked.",
        },
      ],
    },
    "gap": {
      adds: [
        "Converting them would mean choosing exchange rates the source doesn't give.",
        "That's why every answer carries a coverage line.",
        null,
      ],
      asked: [
        {
          q:
            "Why not convert the local currency?",
          a:
            "Converting means choosing exchange rates and dates the source doesn't give, and every number Strata states " +
            "has to come from a record. So it keeps them apart and says so.",
        },
        {
          q:
            "What's the coverage line?",
          a:
            "A sentence under each answer that says how many packages it could use out of how many matched, and why the " +
            "rest fell out. It turns a hidden gap into a stated one.",
        },
      ],
    },
    "answers": {
      cue:
        "Let the figure play a few seconds, then press on.",
    },
    "retrieval": {
      adds: [
        null,
        "No table is read at this step. The app only sends the question and the package it's about.",
        "Plain SQL with the viewer's own token, so Unity Catalog decides what they can see.",
        "Every claim has to cite an ID it was given.",
        "Exact matching in code, except one check a model judges.",
        "Every run lands in strata.ops.agent_runs, so anyone can trace an answer afterward.",
      ],
      asked: [
        {
          q:
            "Why fixed tools instead of letting the model write SQL?",
          a:
            "Fixed tools run the same query for the same question, with the viewer's permissions, and return rows the " +
            "verifier can check. The tradeoff is coverage, so open questions go to one Genie tool, which also runs as the" +
            " viewer.",
        },
        {
          q:
            "What does an evidence ID look like?",
          a:
            "The table and the row's key, like strata.gold.package followed by the package's STEP reference. The verifier" +
            " only accepts IDs a tool returned in this same answer.",
        },
        {
          q:
            "Can the agent run its own SQL?",
          a:
            "No. The tools are fixed, each defined once in config/tools.toml with its parameters and result shape. For " +
            "open questions, one tool asks a Genie space, and that also runs with the viewer's token.",
        },
        {
          q:
            "How many rounds can it take?",
          a:
            "A fixed number of tool rounds, set in config/thresholds.toml. If it still can't answer, it says what it " +
            "couldn't find instead of guessing.",
        },
        {
          q:
            "Where are runs logged?",
          a:
            "Each run is a row in strata.ops.agent_runs, with its tool calls in strata.ops.tool_calls and any removed " +
            "sentence in strata.ops.answer_removals. It keeps the viewer's user ID, never their email.",
        },
      ],
    },
    "estimate": {
      adds: [
        null,
        null,
        "Too few to trust, so no range at all.",
        "Dropping them would make every estimate look faster than reality.",
        "Its track record comes from backtests on years it never saw.",
        "That's the count you saw on the package page.",
        null,
      ],
      asked: [
        {
          q:
            "Why a survival model?",
          a:
            "Because many packages are still open, and a plain average would drop them or treat them as done. A survival " +
            "model uses how long each open package has already run, so the estimate isn't too hopeful.",
        },
        {
          q:
            "How do you know it works?",
          a:
            "Backtests. For each test year, the model learns only from packages before that year. Then Strata counts how " +
            "many of that year's packages were signed within its 8-in-10 point. The slide shows that track record.",
        },
        {
          q:
            "Where does the model live?",
          a:
            "The fitted models are in strata.gold.time_estimate_model, and each package's scores are in " +
            "strata.gold.time_estimate_score.",
        },
      ],
    },
    "checks": {
      adds: [
        null,
        "For a number it looks for the row, and never asks a model.",
        "That's the one place a model judges, and the answer says so.",
        null,
        "Strata would rather say less than say something it can't back.",
        null,
      ],
      asked: [
        {
          q:
            "What are the checks, in order?",
          a:
            "Numbers and dates match a cited row. Every cited ID came back from a tool in this answer. Every quote is " +
            "word for word on its page. Each sentence follows from its passages, judged by a model. Advice needs a lesson" +
            " or comparable packages behind it. And a disagreement must show both sides.",
        },
        {
          q:
            "Isn't a model judging a model weak?",
          a:
            "It's the one place Strata uses one, and the answer says when it did. Every other check is exact matching in " +
            "code, and the judge can only remove a sentence, never add one.",
        },
        {
          q:
            "Can the agent fix a removed sentence?",
          a:
            "Once. It gets its removed sentences back for a single rewrite, and the verifier checks the rewrite too. " +
            "Whatever still fails is removed and shown.",
        },
        {
          q:
            "What did the benchmark show?",
          a:
            "The numbers on this slide are the measured run: how many benchmark questions passed, and how many " +
            "must-refuse questions it turned down.",
        },
        {
          q:
            "How do you evaluate retrieval?",
          a:
            "With precision at 10, recall at 20 and nDCG at 10 on a fixed set of questions, from a replay harness, and " +
            "the dashboard tracks them over time.",
        },
      ],
    },
    "ladder": {
      cue:
        "After the last press, click Open the timeline, then the chip that says the reports disagree. Show both " +
        "passages, then click Open at page.",
      adds: [
        null,
        null,
        null,
        "Hindsight wins for how a project turned out.",
        null,
        null,
        "Let me open that paragraph itself.",
      ],
      asked: [
        {
          q:
            "Why not just take the newest report?",
          a:
            "Newer isn't always more reliable. A completion report or an independent review is written after the project " +
            "closed, with hindsight. A status report is the best record of what people knew at the time.",
        },
        {
          q:
            "When does the warning show?",
          a:
            "Only when the disagreement changes a number or a claim in the answer. Constant warnings get ignored, so " +
            "Strata saves them for when they matter.",
        },
        {
          q:
            "What's a trajectory?",
          a:
            "A rating that moves over time, like progress falling from Satisfactory to Moderately Satisfactory. That's a " +
            "story over time, so Strata draws it as a band, not as a disagreement.",
        },
      ],
    },
    "hindsight": {
      adds: [
        "Every new version has to beat a plain checklist of the sector's most common risks.",
      ],
      asked: [
        {
          q:
            "Has this test run yet?",
          a:
            "The slide says so either way. If it shows a result, that's the measured run. If it says planned, it hasn't " +
            "run on the workspace yet, and I won't claim it has.",
        },
        {
          q:
            "Why compare against a checklist?",
          a:
            "A good checklist is cheap, and a model that can't beat it isn't worth its cost. Beating the checklist is the" +
            " bar for shipping.",
        },
        {
          q:
            "Who are the coders?",
          a:
            "People who read each completion report, code the causes it blamed, and match them against Strata's risk " +
            "table.",
        },
      ],
    },
    "grows": {
      cue:
        "Let the figure play a few seconds, then press on.",
    },
    "loops": {
      adds: [
        null,
        "Nothing enters the library on a model's word alone.",
        "A report becomes a label only after a person checks it.",
        "Shadow means it answers beside the live model, unseen, until it proves better.",
        "So any old answer can be replayed exactly.",
        "A time estimate can change the future it predicts, so every estimate shown is logged.",
      ],
      asked: [
        {
          q:
            "What does in shadow mean?",
          a:
            "The new model runs beside the current one on real questions, but its answers aren't shown. Strata compares " +
            "them, and the new model only takes over if it does better.",
        },
        {
          q:
            "Who decides a lesson?",
          a:
            "A specialist and a lead both decide, and every version of the lesson is kept in strata.ops.lesson_versions.",
        },
        {
          q:
            "How would you swap the model?",
          a:
            "One line in config/models.toml. The new model has to win the backtest and spend a quarter in shadow before " +
            "it takes over.",
        },
      ],
    },
    "rollout": {
      adds: [
        "They can judge a wrong answer, so they go first.",
        "Only once the drafts hold up.",
        "And when a plan copies Strata's range, those plans are scored apart, so Strata never grades its own " +
        "homework.",
      ],
      asked: [
        {
          q:
            "How would you measure the pilot?",
          a:
            "Plan accuracy: how often packages are signed within the planned time, against countries not yet using " +
            "Strata. Plans that copied Strata's range are counted apart.",
        },
        {
          q:
            "Which countries come first?",
          a:
            "That's the owner's call. The slice holds Kenya, Bangladesh, Vietnam and Pakistan, and adding a country is " +
            "one entry in config/slice.toml.",
        },
      ],
    },
    "spend": {
      adds: [
        null,
        null,
        null,
        "That number is measured, from strata.ops.azure_costs.",
      ],
      asked: [
        {
          q:
            "What does it cost to run?",
          a:
            "The number on this slide is measured, from strata.ops.azure_costs, and each cost has a hard cap behind it.",
        },
        {
          q:
            "What happens when a cap is hit?",
          a:
            "The capped work waits instead of overspending. The token limit slows model calls, the page cap stops reading" +
            " for the day, and the replica limit stops the app from scaling out.",
        },
        {
          q:
            "Why run some model work in batch?",
          a:
            "Bulk extraction, like proposing lessons from reports, doesn't need an answer now, so it runs on Azure's " +
            "batch lane at a lower price. The agent runs live.",
        },
      ],
    },
    "change": {
      cue:
        "On the last press, take their change. Open the file, change it, run the gate, then refresh the app.",
      asked: [
        {
          q:
            "What's the gate?",
          a:
            "The offline test suite and the ground-truth SQL, run before every commit, in a couple of minutes. A change " +
            "that breaks a rule can't be committed.",
        },
        {
          q:
            "Where do the extension points live?",
          a:
            "Sources, tools, signals, thresholds, the slice, models, copy and benchmark questions each live in one " +
            "registry or config file. That's why a change request lands in minutes.",
        },
      ],
    },
    "rubric": {
      cue:
        "Click any link they want to see. Each opens in a new tab.",
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
  retrieval: {
    title: "What happens behind one answer",
    heading: "How I check an answer before you see it",
    steps: [
      "The viewer asks how long packages like this one took.",
      "The app sends the question, scoped to this package, to the Strata agent in Microsoft Foundry, which " +
        "picks a tool: find_comparables.",
      "The app runs it as the viewer, as SQL on strata.gold.package, notice and contract, and keeps each " +
        "comparable package's row with its evidence ID.",
      "The agent writes its claims, each citing the IDs behind it. It can go back for more, up to a fixed " +
        "number of rounds.",
      "The verifier checks every sentence, and every number against its row.",
      "The viewer reads the answer, with any removed sentence and its reason. Strata keeps each run in " +
        "strata.ops.agent_runs.",
    ],
    caption:
      "I decide which records and passages to look up, and I write each claim with the source behind it. Then my " +
      "verifier, written in plain code, tests every sentence. If a number doesn't match a record, or a quote " +
      "isn't on its page, I remove the sentence and show you what I removed and why.",
  },
  estimate: {
    title: "How a time estimate is made",
    heading: "How I size a package's schedule",
    steps: [
      "Stated criteria pick comparable packages: method, category, market approach, review type, size, region and period.",
      "The comparable packages are past packages that match on those criteria.",
      "With too few comparable packages, Strata shows every one and gives no range.",
      "Otherwise the past range counts packages still open, so the slowest cases do not drop out.",
      "A survival model gives the time estimate, with its track record from years it had not seen.",
      "Then Strata counts how many comparable packages were signed by the plan's date.",
    ],
    caption:
      "I pick comparable packages by criteria you can see and change. When there are too few, I show you every one and " +
      "give no range. Otherwise I count the packages still open too, so the slow ones are not lost. My time estimate " +
      "comes with its track record from years the model had not seen.",
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
