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
    previous: "Previous",
    next: "Next",
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
      line: "Strata checks a borrower's plan, plans a new package and opens the paragraph behind an answer, live.",
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
        "Strata is a working demo built only on World Bank open data, and I built it for this assessment. One rule " +
        "holds everywhere. Every number comes from a measured run or a setting, and you can point at any number to " +
        "see which. Stop me anywhere. I'd rather take a question than finish a slide.",
    },
    agenda: {
      title: "The problem, a live demo, then how Strata is built, answers and grows",
      notes:
        "One real case runs through the whole talk: a water works package in Kenya whose planned date passed with no " +
        "signed contract. You'll see Strata check its plan live. Then I open the hood, the tables, the tools and the " +
        "checks behind every answer, and end with how it grows. A press per part.",
    },

    // ── Three strata ──
    strata: {
      title: "A procurement plan needs three strata of evidence, and today they sit apart",
      source: "the assessment brief, section 1.",
      notes:
        "Strata is named for the assessment's three strata, a press each. What happened lives in records like " +
        "contract awards. How it was done lives in Procurement Plans and status reports. Why it worked, or didn't, " +
        "lives in completion reports. Last press: today a specialist joins these by hand, one project at a time. " +
        "That's the job Strata takes on.",
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
        "These are the assessment's own pains, a press each. Schedules that aren't realistic. Packages advertised " +
        "again or canceled. Specifications that miss. Lessons nobody finds in time. On the last press, ask the room " +
        "how they find a completion report's lesson today, and let the pause do the work.",
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
        "Strata respects who owns what, a press per view. The borrower prepares the plan, and World Bank staff review" +
        " it. Then the rule under all of them. Strata never takes part in bid evaluation, awards or complaints. Ask " +
        "it about one, and it turns the question down and says why.",
    },
    idea: {
      title: "Strata joins the three strata once, so one question gets one cited answer",
      notes:
        "The whole idea in one picture, a press each. Take the Kenya water package. Records give its comparable " +
        "packages and how long each took. Plans give each step's planned and actual dates. Completion reports give " +
        "what went wrong and what helped, quoted with paragraph and page. Last press, one answer, and every sentence " +
        "names its source. Everything after this slide is that picture, made real.",
    },

    // ── Strata at work ──
    workOpener: {
      notes:
        "Strata at work, on live World Bank records. Let the figure play for a few seconds, then go to the plan " +
        "check.",
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
        "Open the plan check in the new tab. Strata reads the agency's Procurement Plan row by row. Find {step}. It " +
        "needs a look, because its planned completion passed with no signed contract in the plan. Click its signal to" +
        " open the record behind it. If the awards data already show it signed, say so out loud, because Strata shows" +
        " that kind of disagreement instead of hiding it. If asked, the rows come from strata.silver.plan_rows, read " +
        "from STEP.",
    },
    demoPackage: {
      title: "Comparing the package that needs a look with the packages that came before it",
      box: "Package {step}, which the plan check says needs a look",
      action: "Open the package",
      lines: [
        "Each comparable package is a dot on a month axis, from its notice to its signed contract.",
        "Hollow dots are still open, and the range counts them, so the slow cases stay in.",
        "The time estimate dates each STEP step, with its track record from years it had not seen.",
      ],
      note: "STEP is Systematic Tracking of Exchanges in Procurement, where Procurement Plans are kept.",
      notes:
        "Open the package the plan check said needs a look. Each dot is a comparable package with the same method, " +
        "category, market approach, review type, size, region and period. When there are many, each dot stands for an" +
        " equal share of them. Hollow dots were still open, and the range counts them, so the slowest cases don't " +
        "quietly drop out. Below it, the time estimate dates each STEP step, with a track record from years the model" +
        " never saw. If asked, the comparables come from strata.gold.package, notice and contract.",
      // The recorded answer (ticket 116): the comparable packages Strata found for the demo plan's package, recorded
      // on the workspace. This line goes first under its chart, before the package workspace's own lines.
      recorded: "Recorded on {date}, for {step}, a package in the Procurement Plan Strata checked.",
      notesRecorded:
        "If the App is down, press Show the recorded answer. It's the same chart for {step}, recorded on {date}. The " +
        "next press moves on.",
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
        "Click Ask Strata about this package at the foot of the page. The chip keeps the answer inside this package. " +
        "Copy the question here, paste it and press Enter. While it runs, the steps show which tools it called. Under" +
        " the answer, the check line counts the numbers that matched a record. If the verifier removed a sentence, " +
        "open it and read the reason aloud. That's the product working, not failing. If the App stalls, go back one " +
        "slide and show the recorded answer.",
    },

    // ── How it is built ──
    builtOpener: {
      notes:
        "That was the surface. Here's what sits under it, from the data up. Let the figure play for a few seconds.",
    },
    layers: {
      title: "The data, search and tools run on Databricks, and the agent and its models run in Microsoft Foundry",
      notes:
        "A press per layer, from the bottom. The data, the knowledge model and the tools stay on Databricks, under " +
        "Unity Catalog. The agent runs in Microsoft Foundry, and all it does is pick tools and write claims. The app " +
        "runs each tool with the viewer's own permissions and keeps the rows, and the verifier checks every sentence " +
        "against them. Last press, where each layer runs. The model never queries the warehouse itself.",
    },
    pipeline: {
      title: "Every night, World Bank open data become one dated knowledge model",
      notes:
        "A press each. A nightly job reads every source from where it stopped. Bronze keeps each page as it arrived, " +
        "in strata.bronze.api_pages. Silver types and cleans, strips contact details and matches keys, in tables like" +
        " strata.silver.plan_rows. Gold is the knowledge model everything reads, like strata.gold.package. Last " +
        "press, every row keeps the date it became public, so any answer can be replayed as of its date.",
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
        "A press each. A page router sends each page down one of two roads. Clean pages use the text the World Bank " +
        "already publishes, which costs nothing and keeps the exact words. Scans and tables go to the layout parser. " +
        "Either way, Strata cites the numbered paragraph and its page, the way the Independent Evaluation Group cites" +
        " a report. The passages land in strata.gold.passage.",
    },
    knowledge: {
      title: "Records and documents meet at the passage, joined on STEP's keys",
      note: "STEP is Systematic Tracking of Exchanges in Procurement, where Procurement Plans are kept.",
      notes:
        "The knowledge model, a press each, and every box names its table. It's Unity Catalog tables plus an edge " +
        "table, not a separate graph database, so search and SQL read the same rows under one set of permissions. The" +
        " dashed line is the link the assessment asks for: a contract and a completion report paragraph that appeared" +
        " together, kept in strata.gold.edge. If asked why not a graph database, the answer is one copy of the data, " +
        "one set of permissions and one place to audit.",
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
        "I'd rather show you a gap than hide it. Neither contract awards dataset covers fiscal {start} to {end}. " +
        "Award notices cover those years, but in local currency, so Strata keeps them apart and says so whenever an " +
        "answer leans on them. And only {ratio} recent award rows share their STEP reference with a notice. That " +
        "ratio is why every answer carries a coverage line.",
      notesGap:
        "I'd rather show you a gap than hide it. Neither contract awards dataset covers fiscal {start} to {end}. " +
        "Award notices cover those years, but in local currency, so Strata keeps them apart and says so whenever an " +
        "answer leans on them. The workspace job counts the rows themselves.",
      notesNone:
        "This slide shows the contract award rows for each fiscal year, and the years no awards dataset covers. " +
        "Strata hasn't measured them yet, so open the Data readiness page instead.",
    },

    // ── How it answers ──
    answersOpener: {
      notes:
        "Next, how Strata answers, and how it checks itself before you see anything. Let the figure play for a few " +
        "seconds.",
    },
    retrieval: {
      title: "The agent picks the tools, and the app runs them as the person asking",
      notes:
        "Back to the Kenya water answer, under the hood, a press each. The agent in Foundry picks the tools. " +
        "find_comparables and estimate_time run fixed SQL on strata.gold.package, notice and contract. " +
        "search_passages asks AI Search over strata.gold.passage, and get_disagreements reads strata.gold.assertion. " +
        "The app runs every call with the viewer's own token, so Unity Catalog decides what each person sees, and it " +
        "keeps every row with its evidence ID. The agent writes claims that cite those IDs, and the verifier checks " +
        "each one before anything reaches the screen. Every run lands in strata.ops.agent_runs, so anyone can trace " +
        "an answer afterward.",
    },
    estimate: {
      title: "A time estimate starts from comparable packages, and gives no range when there are too few",
      few: "Under {min} comparable packages, Strata shows every package and gives no range.",
      backtest: "In {year}, {ratio} packages that Strata had not seen were signed within its 8-in-10 point.",
      backtestNone: "The backtest has not run on the workspace yet, so the model's track record is not shown here.",
      source: "Strata's backtest, measured {date}.",
      notes:
        "Same package, now the model behind its estimate, a press each. Stated criteria choose the comparable " +
        "packages. Under {min}, Strata shows every one and gives no range, because that's too few to trust. Otherwise" +
        " the past range keeps the packages still open, so the slow cases count. A survival model gives the time " +
        "estimate, tested on years it had not seen. Then Strata counts how many were signed by the plan's date. If " +
        "asked, the model and its scores live in strata.gold.time_estimate_model and time_estimate_score.",
    },
    checks: {
      title: "Every sentence meets {checks} checks before anyone sees it",
      heading: "In the latest benchmark run,",
      passed: "{ratio} benchmark questions passed.",
      refused: "Strata turned down {ratio} questions it must refuse.",
      none: "The benchmark has not run with all {checks} checks yet, so there are no results to show.",
      source: "Strata's benchmark run of {date}.",
      notes:
        "The verifier is plain code, and it runs on every answer, a press per check. For a number, it looks for the " +
        "row and never asks a model. Only one check, whether a sentence follows from its passages, uses a model as a " +
        "judge, and the answer says so on screen. A removed sentence stays in view under the answer, like any you saw" +
        " on the Kenya package. Strata would rather say less than say something it can't back.",
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
        "The assessment asks what to do when a completion report and the supervision ratings disagree. Kenya water is" +
        " still running, so this example is a closed roads project, P130164. A press per rung, then the example. " +
        "Strata keeps both reports. The card turns amber only when the disagreement changes a number or a claim in " +
        "the answer, because constant warnings get ignored. A rating that moves over time is a trajectory, not a " +
        "disagreement.",
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
        "This is the test I'd trust over any demo. Freeze Strata at a project's approval date, let it build its risk " +
        "table, and {coders} people compare it with what the completion report later blamed. The baseline is a plain " +
        "checklist of the sector's commonest risks, and every new version has to beat it before it ships.",
      notesInterval: "With {level} confidence, the share it caught lies between {low} and {high} percent.",
    },

    // ── How it grows ──
    growsOpener: {
      notes:
        "Last part, how Strata learns and grows without drifting. Let the figure play for a few seconds.",
    },
    loops: {
      title: "{loops} loops learn on their own schedules, and people decide each change",
      notes:
        "Each loop runs on its own clock, a press each. Documents arrive every night. People decide every week. " +
        "Models change at most once a quarter. A lesson needs its quote found word for word on the cited page, then a" +
        " specialist and a lead both decide. A new model has to win its backtest and spend a quarter in shadow. " +
        "Strata keeps every version, so any old answer can be replayed exactly.",
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
        "The rollout follows who carries the risk of a wrong answer, a phase per press. World Bank staff come first, " +
        "in {countries} countries, because they can judge a wrong answer. Agencies come next, once the drafts hold " +
        "up. The public comes last, and read-only. When a plan copies Strata's range, Strata marks it and reports " +
        "plan accuracy for those plans apart, so it never grades its own homework.",
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
        "Budgets only send alerts, and cost data can arrive a day late, so hard caps do the stopping. A press each: a" +
        " token limit on every model deployment, a daily page cap on document reading, and a replica limit on the " +
        "app. If asked about the bill, the number on the slide is measured, from strata.ops.azure_costs.",
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
        "This is where you test me. Each kind of change lives in one file, and I've rehearsed the likely ones. Pick " +
        "one, and I'll make it with the gate running, then show it in the app. Good ones to offer are a new " +
        "threshold, a new example question or a model swap.",
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
        "This maps the rubric to what you can open. Each link goes to the screen in Strata where that part of the " +
        "work shows. The proposal follows the assessment's modules, and every number in it links to its measured " +
        "result.",
    },
    limits: {
      title: "What is designed but not built yet",
      empty: "Everything in this deck is built and runs in the app.",
      itemAt: "{name}, labeled at {route}",
      notes:
        "Here's what I designed but didn't build, so nothing in the demo pretends otherwise. The same list is in the " +
        "proposal, and the app labels each one where it would appear. Saying so up front is part of the design.",
      notesEmpty: "Everything on these slides is built and runs in the app, and you can open any of it now.",
    },
    thanks: {
      title: "Thank you",
      figure: "Every night, new reports settle on the core as a new layer, and Strata keeps every layer.",
      ask: "What would you like to ask?",
      links: { app: "Open Strata", proposal: "Read the proposal", dashboard: "Open the dashboard", repo: "Read the code" },
      notes:
        "Thank you. Everything on these slides is built and runs in the app, and you can open any of it right now. " +
        "Ask me anything, or hand me a change to make live, here in the room.",
      notesAfterLimits:
        "Thank you. Ask me anything, or hand me a change to make live, here in the room.",
    },
  },
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
      "The tools are SQL through the Genie Agent, hybrid search over passages, a walk over the edge table, and the time estimates.",
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
  retrieval: {
    title: "What happens behind one answer",
    heading: "How I check an answer before you see it",
    steps: [
      "The viewer asks a question in the app.",
      "The app passes it to the Strata agent in Microsoft Foundry, which picks the tools to call.",
      "The app runs each tool with the viewer's own permissions: SQL on strata.gold.package, notice and contract, AI " +
        "Search over strata.gold.passage, and the claims graph in strata.gold.assertion and disagreement. It keeps every " +
        "row and passage, each with its ID.",
      "The agent writes its claims, each with the IDs of its evidence. It can go back for more, up to a fixed number of rounds.",
      "The verifier checks every sentence against the kept rows and passages.",
      "The viewer reads the answer. Under it are any sentences the verifier removed, each with the reason. Strata keeps " +
        "each run in strata.ops.agent_runs, with its tool calls and removed sentences.",
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
