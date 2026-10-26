// Every word of the deck at /present, its speaker notes and the figures it shares with How Strata works (ticket 47;
// the 47 brief, sections 5, 7, 8 and 9). The copy lint reads this file as it reads web/src/copy.ts (COPY_FILES in
// web/lint/run.ts).
//
// Voice (the 47 brief, section 15, decision 6): slides name Strata in the third person, because the presenter speaks
// as "I"; speaker notes are the presenter's "I"; How Strata works keeps Strata's own "I" (DESIGN.md section 7, rule
// 5). Figure text versions name no speaker, so the deck and the page share them.
//
// {name} slots are filled through Fill. A slot that holds a number is filled by the deck's number components, which
// bind it to its key in the measures snapshot, a setting or the rubric, so the number check can trace it. Nothing
// here is a number Strata measured: the words "one" to "nine" that count something come from a setting.

export const deckCopy = {
  title: (n: string, total: string) => `Slide ${n} of ${total} | Strata deck`,
  readingTitle: "Strata deck",
  notesTitle: (n: string, total: string) => `Speaker notes, slide ${n} of ${total} | Strata deck`,
  // The footer's counter and the reading view's line, chrome the number check leaves out (data-chrome).
  counter: (n: string, total: string) => `${n} of ${total}`,
  slideOf: (n: string, total: string) => `Slide ${n} of ${total}`,
  announce: (n: string, total: string, title: string) => `Slide ${n} of ${total}: ${title}`,
  roleSlide: "slide",
  wordmark: "Strata",
  // The artwork reads WORLD BANK GROUP, so its text alternative names the Group (DESIGN.md section 9).
  logo: "World Bank Group logo",
  module: (n: string) => `Module ${n}`,
  money: (amount: string) => `US$${amount}`,
  percent: (amount: string) => `${amount} percent`,

  bar: {
    label: "Deck",
    previous: "Previous",
    next: "Next",
    showTable: "Show the table",
    showChart: "Show the chart",
    readAsPage: "Read as a page",
    notes: "Speaker notes",
    notesName: "Speaker notes (opens in a new window)",
    fullScreen: "Full screen",
    leaveFullScreen: "Leave full screen",
  },

  states: {
    note: "Note:",
    loadError: "The deck didn't load. Check your connection, then reload the page.",
    reload: "Reload the page",
    figureFailed: "This figure didn't load, so here it is as text.",
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
    tableRegion: (title: string) => `Table: ${title}`,
  },

  notesView: {
    timerName: "Time since the notes opened",
    restart: "Restart the timer",
    next: "Next: {title}",
    last: "This is the last slide.",
    noDeck: "The deck isn't open in this browser, so these notes move on their own.",
    openDeck: "Open the deck",
    previous: "Previous",
    nextButton: "Next",
  },

  // A number's tooltip and its window (the 46 brief, section 9.2; the 16 brief, section 6): what it counts, its
  // source kind and when it was measured.
  num: {
    ratio: (n: string, d: string, noun: string, kind: string, date: string) => `${n} of ${d} ${noun}. ${kind}, measured ${date}.`,
    count: (n: string, noun: string, kind: string, date: string) => `${n} ${noun}. ${kind}, measured ${date}.`,
    setting: (name: string, where: string) => `${name}. Set in ${where}.`,
    tool: (step: string, date: string) => `Counted from the comparable packages for ${step}, run ${date}.`,
    estimate: (step: string, date: string) => `From the time estimate for ${step}, run ${date}.`,
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

  slides: {
    s1: {
      statement: "Procurement intelligence on World Bank open data, with every claim cited",
      line: "Built for the World Bank Group's procurement intelligence assessment.",
      notes:
        "Strata is a working demo built only on World Bank open data, and I built it for this assessment. Over the next " +
        "slides I'll show how it links the three strata of evidence, how it checks an answer before anyone sees it, and " +
        "what it still can't do. Every number on these slides comes from a measured run, a setting or the assessment " +
        "brief, and you can point at any of them to see which. The figure shows the idea behind the name: the three strata, one under the other.",
    },
    s2: {
      title: "A planning question needs three strata of evidence, kept apart today",
      points: [
        "Today a specialist joins them by hand: a contract award, the plan row behind it, and the report paragraph that explains what happened.",
        "Strata makes that link once, keeps it current every night, and shows where each piece came from.",
      ],
      notes:
        "The assessment describes layers of evidence, and Strata calls them the three strata. What happened sits in " +
        "records such as contract awards and notices. How it was done sits in operational documents such as Procurement " +
        "Plans and status reports. Why it worked or not sits in evaluations such as completion reports and their reviews. " +
        "Strata joins them once, on keys such as the project ID and the package's reference in Systematic Tracking of " +
        "Exchanges in Procurement (STEP), and keeps the join current every night.",
    },
    s3: {
      title: "The borrower owns the plan, and Strata helps both sides check it",
      columns: [
        {
          heading: "World Bank procurement specialists and task team leaders",
          body: "They reach for Strata when they review a borrower's draft plan or prepare a mission. They leave with review notes, suggested evidence for the borrower's procurement strategy, and a mission brief.",
        },
        {
          heading: "Implementing agency procurement officers",
          body: "They reach for Strata when they draft the Procurement Plan or check it before they submit it. They leave with a planned date for each step and risk rows with their sources.",
        },
        {
          heading: "The public, read-only",
          body: "They reach for Strata when they look into a large award, or a road or school that is late. They leave with a contract's trail from notice to completion report, in neutral words.",
        },
      ],
      across: "Nothing Strata writes is a World Bank decision. A person marks every draft as checked, and exporting sends nothing.",
      notes:
        "Strata follows who owns what. The borrower prepares the Project Procurement Strategy for Development and the " +
        "Procurement Plan, and World Bank staff support and review them. So implementing agencies draft with Strata, " +
        "World Bank staff review with it, and the public can follow a contract from its notice to its completion report. " +
        "Strata never takes part in bid evaluation, awards or complaints, and it turns those questions down.",
    },
    s4: {
      title: "Each tool runs in the app with your permissions, never a shared token",
      notes:
        "Data, search and models stay in Unity Catalog on Databricks. The agent lives in Microsoft Foundry and decides " +
        "which tools to call. The app runs each tool with the permissions of the person asking and keeps every row the " +
        "answer used. That is why the verifier can check each number against the rows themselves. If the agent called " +
        "Databricks directly, it would use one shared token, everyone would see the same data, and the verifier would " +
        "not hold the rows. The figure leaves out the models in Azure OpenAI, Foundry's evaluations and the traces in " +
        "Application Insights.",
    },
    s5: {
      title: "Every document becomes numbered paragraphs, each with its page",
      passages: "{passages} passages from {documents} documents, each with its paragraph number and page.",
      passagesNone: "Strata has not counted its passages yet.",
      pages: "{ratio} pages were read without errors.",
      pagesNone: "Strata has not measured how well its pages were read yet.",
      source: "Strata's data readiness measures, taken {date}.",
      notes:
        "A page router sends each page down one of two roads. Clean pages use the text the World Bank already " +
        "publishes, which costs nothing and keeps the exact words. Scans and tables go to the layout parser in " +
        "Databricks. Either way, the unit Strata cites is the numbered paragraph, because the Independent Evaluation " +
        "Group cites reports that way. Each passage keeps its project, document type, the date it became public, its " +
        "paragraph number and its page. Tables become typed rows, and a table's summary never backs a number. The " +
        "hardest documents, such as a scanned appraisal document with a garbled risk annex, sit on the Data readiness " +
        "page as a stress test.",
    },
    s6: {
      title: "Records and documents meet at the passage",
      note: "STEP is Systematic Tracking of Exchanges in Procurement, where Procurement Plans are kept.",
      notes:
        "This is the knowledge model. It is a set of Unity Catalog tables with declared keys and one edge table, not a " +
        "separate graph database, so search and SQL read the same rows under one set of permissions. Packages join on " +
        "their reference in Systematic Tracking of Exchanges in Procurement (STEP), and suppliers join on the STEP " +
        "supplier ID before any name. The highlighted line is the link the assessment asks for: a contract and a " +
        "completion report paragraph that appeared together, scored on project, sector, time and text. Strata shows it " +
        "as appeared together and never as a cause. Every row keeps the date it became public, so any answer can be " +
        "replayed as of its date.",
    },
    s7: {
      title: "No dataset publishes contract awards for fiscal {start} to {end}",
      titleNoGap: "Contract awards are published for every fiscal year Strata reads",
      titleNone: "Strata has not measured its contract award rows yet",
      gapNote: "Award notices fill most of the gap, in local currency, so Strata keeps them apart from awards in US dollars.",
      linked:
        "{ratio} contract award rows since fiscal 2020 share their Systematic Tracking of Exchanges in Procurement (STEP) reference with a procurement notice, the key that joins an award to its notice.",
      link: "Open Data readiness",
      source: "Strata's data readiness measures, taken {date}.",
      chartAlt: "Bars show contract award rows for each fiscal year from {first} to {last}, by the dataset or the award notices they came from.",
      chartGap: "Neither awards dataset covers fiscal {start} to {end}.",
      gapLabel: "No awards dataset",
      table: { year: "Fiscal year", rows: "Contract award rows", from: "From" },
      notes:
        "This is a gap Strata states instead of hiding. Neither contract awards dataset covers fiscal {start} to {end}. " +
        "Award notices fill most of those years, but in local currency, so Strata keeps them apart from the US dollar " +
        "awards and says so whenever an answer leans on them. Only {ratio} recent award rows share their " +
        "reference in Systematic Tracking of Exchanges in Procurement (STEP) with a procurement notice, the key that " +
        "joins an award to its notice. Every answer's coverage line says how many of its packages Strata could use.",
      notesNone:
        "This slide shows the contract award rows for each fiscal year, and the years no awards dataset covers. Strata " +
        "has not measured them yet, so I'll show the Data readiness page instead.",
    },
    s8: {
      title: "{ratio} comparable packages were signed within this plan's {months} months",
      titleFew: "Strata gave no range, because it found only {total} comparable packages",
      titleNoPlan: "Strata found {total} comparable packages, and this plan sets no signing date to count against",
      titleNone: "Strata has not recorded the demo package's comparable packages yet",
      dots: "Each dot is one comparable package. Hollow dots were still open, and the range counts them.",
      estimate: "The time estimate puts the middle half at {low} to {high} months.",
      estimateNone: "Strata gave no time estimate for this package, and the chart's lower lane says why.",
      backtest: "In {year}, {ratio} packages that Strata had not seen were signed within its 8-in-10 point.",
      few: "Under {min} comparable packages, Strata shows every package and gives no range.",
      none: "The demo package's answers are recorded on the workspace, then the deck is built again.",
      source: "comparable packages and the time estimate for {step}, run {date}.",
      sourceTwoDates: "comparable packages for {step}, run {date}, and its time estimate, run {estimateDate}.",
      notes:
        "This is the package workspace for {step}, a real package in the {agency}'s plan. The top lane is what happened. Each dot is one comparable package, chosen by method, category, market " +
        "approach, review type, size, region and period. Hollow dots were still open when the data were taken, and the " +
        "range counts them, so the slowest cases don't drop out. The lower lane is Strata's time estimate for this " +
        "package, from a survival model. The line is the plan's date. Strata doesn't say the plan is wrong. It counts " +
        "how many comparable packages were signed by that date. Under every time estimate sits its track record, from " +
        "backtests on years the model had not seen.",
    },
    s9: {
      title: "The agent picks the tools, and the app runs them as the person asking",
      notes:
        "The agent in Foundry reads the question and decides which tools to call: SQL through the Genie Agent, hybrid " +
        "search over numbered passages, or a walk over the edge table. It can go back for more, up to a fixed number of " +
        "rounds. The app runs every call with the viewer's own permissions and keeps the rows. The agent returns its " +
        "claims in a fixed format, each with the IDs of the evidence behind it. Then the verifier takes over, and " +
        "nothing reaches the screen before it does.",
    },
    s10: {
      title: "Every answer passes {checks} checks before anyone sees it",
      checks: {
        1: "Every number matches a row a tool returned.",
        2: "Every cited ID came back in this answer's tool calls.",
        3: "Every quote is on the page it cites.",
        4: "Each sentence follows from its passages.",
        5: "No advice appears without a lesson or a comparable package behind it.",
        6: "When sources disagree, both sides are shown.",
      } as Record<number, string>,
      removed: "A sentence that fails any check is removed and listed under the answer, with its reason.",
      heading: "In the latest benchmark run",
      passed: "{ratio} benchmark questions passed.",
      refused: "Strata turned down {ratio} questions it must refuse.",
      none: "The benchmark has not run with all {checks} checks yet, so there are no results to show.",
      source: "Strata's benchmark run of {date}.",
      notes:
        "The verifier is plain code, and it runs on every answer. For a number, it doesn't ask a model whether the " +
        "number is right. It looks for the row. The check that a sentence follows from its passages is the only one " +
        "that uses a model as a judge, and the answer says so in its check line. The check line is neutral on purpose. " +
        "It says what was checked and what wasn't, because a green banner reads as safe. The first removed sentence " +
        "stays in view under the answer.",
    },
    s11: {
      title: "When reports disagree, both stay on screen in the order written",
      // {project} is the showcase project (config/slice.toml [showcase]), whose disagreement the slide quotes.
      point:
        "For how a project turned out, Strata leans on the most independent report written after the project closed. " +
        "For a fact about a moment, such as a rating on a date, the record made at that moment wins.",
      example:
        "In {project}, a status report rated progress toward the objective Satisfactory in August 2016. The completion " +
        "report later said the mid-term review had found part of the objective compromised by major delays. Strata " +
        "shows both and leans on the completion report.",
      source:
        "Implementation Status and Results Report 7, {project}, August 26, 2016; Implementation Completion and Results " +
        "Report, {project}, October 10, 2019, paragraph 78, page 27.",
      notes:
        "The assessment asks what to do when a completion report contradicts the ratings made during supervision. " +
        "Strata keeps both. For a judgment of how a project went, it leans on the most independent and most " +
        "retrospective source, with the Independent Evaluation Group's reviews at the top. For a fact about a moment, " +
        "such as a rating on a date, the record made at that moment wins. The card is amber only when the disagreement " +
        "changes a number or a claim in the answer. Otherwise it is a quiet note, because constant warnings get " +
        "ignored. A rating that moves over time is a trajectory, not a disagreement.",
    },
    s12: {
      title: "{loops} loops learn on their own clocks, and people decide each change",
      notes:
        "Documents arrive every night, people decide weekly, and models change at most every quarter. A new completion " +
        "report becomes a proposed lesson only if its quote is found word for word on the cited page. Then an " +
        "accredited procurement specialist recommends and a lead procurement specialist decides. A report such as " +
        "Wrong passage becomes a label only after a person checks it, never production data. A new model must win its " +
        "backtest and a quarter in shadow. Every version is kept, so any answer can be replayed. The highlighted line " +
        "is the loop through the world: plans made with Strata's ranges change the outcomes it later learns from, so " +
        "Strata logs every time it showed one.",
    },
    s13: {
      title: "Strata showed {ratio} risks that completion reports blamed",
      titleNone: "Strata's hindsight test has not run yet",
      method:
        "For each closed project in the pilot with a completion report, Strata was frozen at the project's approval " +
        "date. It listed its top risks for each main package, and {coders} people compared them with the risks the " +
        "completion report blamed.",
      checklist:
        "That was at {top} risks per package. A checklist of the sector's {checklist} most common risks showed {ratio} " +
        "of the same blamed risks.",
      none: "The test has not run yet, so there is no result to show.",
      costHeading: "What it cost to run",
      spend: "Azure spend to {date} was {spent}, against a budget of {budget} for {period}.",
      caps:
        "Hard caps do the real work, because a budget only sends alerts: token limits on every model deployment, a " +
        "daily page cap when reading documents, and a limit on app replicas.",
      noSpend: "Azure spend has not been recorded yet.",
      source: "Strata's hindsight test of {hindsight}, and Azure cost records to {cost}.",
      sourceHindsight: "Strata's hindsight test of {hindsight}.",
      sourceCost: "Azure cost records to {cost}.",
      notes:
        "The hindsight test is the gate for every release. For each closed project in the pilot with a completion " +
        "report, Strata was frozen at the project's approval date and built the risk table for the first plan's main " +
        "packages. {coders} people compared its top risks with the risks the completion report blamed, and the " +
        "Independent Evaluation Group's review won where they differed.",
      notesInterval: "With {level} confidence, the share it caught lies between {low} and {high} percent.",
      notesEnd:
        "A plain checklist of the sector's most common risks is the baseline any new version must beat. On cost, hard " +
        "caps do the real work, because budgets only send alerts and cost data arrive up to a day late.",
    },
    s14: {
      title: "The pilot grows in {phases} phases, each measured before the next",
      columns: { phase: "Phase", who: "Who uses Strata", measured: "What is measured before the next phase" },
      caption: "The rollout",
      rows: [
        {
          phase: "First",
          who: "World Bank procurement specialists and task team leaders in {countries} countries",
          measured: "Weekly users, drafts checked and exported, and Wrong passage reports for the sources opened",
        },
        {
          phase: "Second",
          who: "Implementing agencies in the same countries",
          measured:
            "Plan accuracy for plans made with Strata's ranges against plans made without them, and the days from a new completion report to a decided lesson",
        },
        {
          phase: "Third",
          who: "The public, read-only",
          measured: "Contract trails opened for closed projects. Active projects show the public no signals, estimates or disagreements.",
        },
      ],
      notes:
        "The rollout follows who carries the risk of a wrong answer. World Bank staff come first, in {countries} " +
        "countries, because they review the plans and can judge a wrong answer. Implementing agencies come next, once " +
        "the drafts hold up. The public comes last, read-only, with no signals, estimates or disagreements on active " +
        "projects. When a plan copies Strata's range, Strata marks it as anchored, so plan accuracy is reported apart " +
        "from it.",
    },
    s15: {
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
        "This maps the rubric to what you can open. Each link goes to the screen in Strata where that part of the work " +
        "shows. The proposal follows the four modules of the assessment, with every number linked to its measured " +
        "result.",
    },
    s16: {
      title: "What is designed but not built yet, and where to find the rest",
      left: "Designed, not built",
      empty: "Everything in this deck is built and runs in the app.",
      itemAt: "{name}, labeled at {route}",
      right: "Where to look",
      links: { app: "Open Strata", proposal: "Read the proposal", dashboard: "Open the dashboard", repo: "Read the code" },
      notes:
        "Here is what I designed but didn't build, so nothing in the demo pretends otherwise. The same list is in the " +
        "proposal, and the app labels each of these where it would appear. Everything else on these slides runs in the " +
        "app, and you can open it now. Thank you. I'm glad to make a change live, here in the room.",
      notesEmpty:
        "Everything on these slides is built and runs in the app, and you can open it now. Thank you. I'm glad to make " +
        "a change live, here in the room.",
    },
  },
};

// The eight structural figures (the 47 brief, section 4), which the deck and How Strata works share. title is the
// SVG's <title> (60 characters at most), steps its text version in reading order, voice-neutral, and caption the
// first-person paragraph How Strata works sets above it. heading is the page section's h2.
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
  "one-answer": {
    title: "One question, three strata, one cited answer",
    heading: "How one question uses all three",
    steps: [
      "It starts from a question about a package.",
      "Records of what happened give comparable packages.",
      "Operational documents on how it was done give each step's planned and actual dates.",
      "Evaluations of why it worked or not give what went wrong and what helped.",
      "They meet in one answer, and every sentence in it names its source.",
    ],
    caption:
      "When you ask about a package, I look in all three at once. Records give me comparable packages. Operational " +
      "documents give me each step's planned and actual dates. Evaluations give me what went wrong and what helped. I " +
      "put them into one answer, and every sentence names its source.",
  },
  pipeline: {
    title: "Where Strata runs",
    heading: "Where I run",
    steps: [
      "World Bank open data arrive each day: contract awards, notices, projects, documents and indicators.",
      "In Databricks, pipelines load them into the knowledge model, a set of Unity Catalog tables, and into a hybrid search index.",
      "The Genie Agent answers questions over the tables.",
      "In Microsoft Foundry, the Strata agent reads the question and decides which tools to call.",
      "The Strata app runs each tool with the viewer's own permissions and keeps every row it returns.",
      "The verifier checks every sentence against those rows before the viewer sees the answer.",
    ],
    caption:
      "The data, the search index and the models stay in Databricks. The agent that decides what to look up runs in " +
      "Microsoft Foundry. I run every lookup with your own permissions, so you see only what your account may see, and " +
      "I keep every row an answer used so that I can check it.",
    caption2:
      "Each time you open a page, I record who you are, which page and view you opened, and when. When you ask a " +
      "question, I also keep the steps I took, so the people who run Strata can check my work.",
  },
  reading: {
    title: "How a document becomes numbered passages",
    heading: "How I read a document",
    steps: [
      "A document arrives: an appraisal document, a status report, a completion report or a Procurement Plan.",
      "The page router checks each page.",
      "Clean pages use the text the World Bank already publishes.",
      "Scanned pages and tables go through a layout parser, a tool that reads page layouts.",
      "Both roads end in numbered passages, each with its paragraph number and page.",
      "The passages go into the hybrid search index.",
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
      "A project has packages. Each package has its STEP reference and becomes one or more contracts.",
      "Each contract is signed by a supplier, matched on its STEP supplier ID.",
      "A project is described in documents, and each document has numbered passages.",
      "A passage can be quoted by a lesson, and it can be the source of an assertion, such as a rating on a date.",
      "Two assertions about the same thing, for the same time, that cannot both be true make a disagreement.",
      "A contract and a passage about the same work appeared together. The link says they appeared together, never that one caused the other.",
      "Every row keeps the date it became public.",
    ],
    caption:
      "A project ID links everything about a project. A package links its plan row, its notice and its contracts " +
      "through its reference in Systematic Tracking of Exchanges in Procurement (STEP). When a contract and a " +
      "paragraph of a completion report are about the same work, I say they appeared together. I never say one caused " +
      "the other. Every row keeps the date it became public, so I can answer as of a past date.",
  },
  retrieval: {
    title: "How an answer is checked",
    heading: "How I check an answer before you see it",
    steps: [
      "The viewer asks a question.",
      "The Strata agent chooses which tools to call.",
      "The Strata app runs each tool with the viewer's permissions.",
      "The data come back as rows and passages, each with its ID.",
      "The agent writes its claims, each with the IDs of its evidence. It can go back for more, up to a fixed number of rounds.",
      "The verifier checks every sentence. A sentence that fails a check is removed.",
      "The viewer reads the answer, with what was removed and why.",
    ],
    caption:
      "I decide which records and passages to look up, and I write each claim with the source behind it. Then a " +
      "separate checker, written in plain code, tests every sentence. If a number doesn't match a record, or a quote " +
      "isn't on its page, I remove the sentence and show you what I removed and why.",
  },
  ladder: {
    title: "Which report Strata leans on",
    heading: "When two reports disagree",
    steps: [
      "For how a project turned out, the highest report on this ladder that speaks to the question wins.",
      "At the top is a review by the Independent Evaluation Group (IEG), written after the project closed. A Project Performance Assessment Report (PPAR) sits at the same level.",
      "Next is the completion report, written after the project closed.",
      "Next is the last status report, written during the project.",
      "At the bottom is the appraisal document, written before the project started.",
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
      "The knowledge loop runs weekly. A new completion report gives a proposed lesson, with its exact quote found on the cited page. One specialist recommends, and a lead procurement specialist decides.",
      "The retrieval loop runs monthly. Reports from readers, such as a wrong passage, become labels only after a person checks them. Search is tuned only if it loses nothing on the held-out tests.",
      "The estimates loop runs quarterly. New signings and plan dates arrive. A new model replaces the old one only after it wins its backtest and a quarter in shadow.",
      "One dated store keeps every version, and answers and drafts cite the version they used.",
      "Plans made from the time estimates change the outcomes the models later learn from, so every time an estimate is shown, it is logged.",
    ],
    caption:
      "New reports arrive every night. When one holds a lesson, I propose it with its exact quote and page, and two " +
      "people decide whether it enters the library. When you report a wrong passage, a person checks your report " +
      "before it changes anything. My time estimates change only after a new model does better than the old one on " +
      "years it had not seen.",
  },
};

export type FigureCopyId = keyof typeof figureCopy;
