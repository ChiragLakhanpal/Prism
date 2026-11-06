// Every word of the deep research talk at /present/research (ticket 162; .notes/deck3/brief.md): its topics, its
// slides, its speaker notes and its figures' titles and text versions. The deck's chrome (the counter, the press lines,
// the notes window's labels) stays in web/src/deck/copy.ts, deckCopy, which both talks share. The copy lint reads this
// file as it reads web/src/copy.ts (COPY_FILES in web/lint/run.ts).
//
// Voice: two people present it, so slides name Prism in the third person and the notes say "we", or "I" for the
// presenter's own words. Figure text versions name no speaker.
//
// {name} slots are filled through Fill. A slot that holds a number is filled by the deck's number components, which
// bind it to its setting (docs/proposal/settings.toml) or its recorded entry (docs/proposal/recorded.toml), so the
// number check can trace it. A count of a fixed thing the talk names, such as "Five ways forward", is on the number
// check's allow list (docs/proposal/number_check.toml) with its reason.
import type { Speaker } from "../copy";

// A figure slide's notes: what to say at each of the figure's own presses, then at the slide's own presses. Until a
// figure's drawing lands, its slide has only its own presses, so the two lists stay apart.
export type ResearchSpeaker = Speaker & { figureAdds?: (string | null)[] };

export const researchCopy = {
  // The talk's five topics, in order: the tracker shows each name, and the agenda each name with its line.
  topics: {
    here: {
      name: "How we got here",
      line: "Two apps on one brief, one conversation, five ways forward, one choice.",
    },
    brief: {
      name: "Deep research",
      line: "What the brief is, why a specialist needs it, and what we set aside on the way.",
    },
    works: {
      name: "How it works",
      line: "{sources} sources, one item shape, one writer call, {checks} checks, a printed brief.",
    },
    decisions: {
      name: "The decisions",
      line: "The evidence ladder, the rules for public posts, and the roads not taken.",
    },
    next: {
      name: "What comes next",
      line: "Five next steps, and what is built against what is designed.",
    },
  },

  slides: {
    welcome: {
      statement: "What is happening on the ground, with every sentence cited and checked",
      line: "A deep research brief for World Bank procurement specialists, and the thinking behind it.",
      figure: "A plot of ground tiles with one tile lifted and a pin on it, joined by a thin line to a page.",
      notes:
        "Thank you for having us both. This round asked us to work together, so we'll tell you first how we worked, " +
        "then what we built. Prism now reads what the press, the complaints register, satellites, public posts and " +
        "the World Bank's own reports say about a project, writes a short brief for a procurement specialist, checks " +
        "every sentence, and prints it.",
    },
    agenda: {
      title: "How we got here, what we built, how it works, what we decided, and what comes next",
      notes:
        "The first topic is how we decided what to build together. The rest is about one feature, deep " +
        "research, and the reasoning behind it.",
    },

    // ── How we got here ──
    hereOpener: {
      line: "Two apps on one brief, then one conversation.",
      figure: "Two slabs lying apart on a board, the smaller one sliding onto the larger as one stack.",
      notes:
        "Before this round, Chirag and I had each built an app on the same brief, without knowing each other's work.",
    },
    timeline: {
      title: "We read each other's work before we wrote a line",
      source: "the round's brief of November 4, 2026; both repositories, as read on November 5; docs/proposals/ in the Prism repository.",
      notes:
        "We didn't start by merging code. Each of us read the other's repository first: its scope, its data, how it " +
        "was built and its tests. Then we had one conversation about what each app had that the other lacked. The " +
        "reading came before the talking, and the talking came before any code.",
    },
    twoApps: {
      title: "Two apps on one brief, each strong in a different place",
      counted:
        "Counted the same way on November 5, 2026, Python under src and tests: Prism had {linesPrism} source lines and " +
        "{testsPrism} tests; ProcIntel had {linesProcintel} source lines and {testsProcintel} tests.",
      source: "both repositories, on November 5, 2026.",
      notes:
        "Prism is the deeper platform: the whole open data set in a lakehouse, a verifier on every sentence and a " +
        "gate on every commit. ProcIntel is the smaller app with designs Prism didn't have: the MCP server, the " +
        "timeline across packages, goal seeking and the editable pipeline. Both repositories were counted the same " +
        "way on the same day.",
    },
    whyPrism: {
      title: "We built on Prism for its data, its checks and its gate",
      lines: [
        "Depth of data: every award and notice the World Bank publishes and the documents of a pilot slice, in a " +
          "lakehouse other tools can read.",
        "Checked answers: a verifier runs on every sentence of every answer and shows what it removed. A reviewer " +
          "asks about that first, and it would check the merged app's new work the same way.",
        "Breadth and a running workspace: three views, private uploads and a long feature list, already deployed with " +
          "sign-in on Databricks, so nothing to host again.",
        "A gate: the tests run before every commit, so new work could land through a night without breaking what the " +
          "panel had already seen.",
      ],
      ask:
        "ProcIntel's designs were the sharper ones in four places. They became the first options, each written up as " +
        "a proposal in the Prism repository under Prism's rules.",
      notes:
        "Our reasons, one line each: the data, the checks, a running workspace and a gate. Then the fair half: " +
        "ProcIntel's designs were the sharper ones in four places, which is why they became the first options.",
    },
    fiveWays: {
      title: "Five ways forward, judged by what a specialist does differently",
      source: "docs/proposals/ in the Prism repository, for the four designs; the Deep research tab on the App.",
      notes:
        "The four designs make Prism's existing data easier to use or plan with. Deep research came from a gap both " +
        "apps shared: neither could see what was happening on the ground at a project. We judged every option by one " +
        "question: what does a procurement specialist do differently the next morning?",
    },
    setAside: {
      title: "Nothing was dropped: the four designs became proposals, each waiting on one thing",
      tiles: [
        {
          head: "The MCP server",
          body:
            "Waits on a decision on which views may use it, and a benchmark question per tool, so an assistant sees " +
            "exactly what its person would see in the app.",
        },
        {
          head: "The timeline across packages",
          body:
            "Waits on the dependencies a person adds, and a tool so every date on the calendar is a column the verifier " +
            "can check. The end event is the signed contract.",
        },
        {
          head: "Goal seeking",
          body:
            "Waits on enough comparable packages per set-up, and the guard that the review type follows the whole " +
            "package's estimate, never a lot's.",
        },
        {
          head: "The editable pipeline",
          body:
            "Waits on an admin role, and the rules as job tasks on the workspace, so a run still leaves one record that " +
            "traces every table.",
        },
      ],
      closing: "Also set aside: linking the two apps at run time. One app, one verifier, one demo that stays up.",
      notes:
        "Each design is written up in the repository with how it would work under Prism's rules and its open " +
        "questions. The timeline and goal seeking wait on data rules. The MCP server and the pipeline wait on " +
        "decisions about who may use them.",
    },

    // ── Deep research ──
    briefOpener: {
      figure: "A report whose pages split into paragraph slabs that slide out, each to its place on a shelf.",
      notes:
        "A procurement specialist can read everything the World Bank holds on a project. They still can't see the " +
        "ground.",
    },
    whatItIs: {
      title: "One click, one brief: the ground, cited and checked, printed for the file",
      lines: [
        "A tab on every project page. One click reads the public sources, the World Bank's own last {reports} status " +
          "reports and the team's field photos.",
        "A writer turns the items into the brief; a checker tests every sentence against the item it cites. It opens " +
          "in the tab and prints with a page per section.",
      ],
      source: "the reader is a procurement specialist before a review meeting, a mission or a decision on a contract.",
      notes:
        "The dashboard is the scorecard. The brief is the dispatch from the field, with every line cited, checked and " +
        "dated. Its last section says what the run couldn't see, so silence is never mistaken for a clean record.",
    },
    gap: {
      title: "This year the World Bank's record moved once, and the ground kept moving",
      counted:
        "The March status report put physical progress at {isrProgress} percent. In June the public record put the " +
        "Wajir plant at {wajirProgress} percent, and the notices counted {lateAwards} awards in the last {lateDays} " +
        "days before closing.",
      source: "the P156634 sample brief of November 5, 2026 (Kenya water), each item cited to its page.",
      notes:
        "A status report is written by the project team and arrives about twice a year. In the months between, works " +
        "finish or stall, people protest and awards land weeks before closing. The brief fills those months with " +
        "sources the specialist can open and check.",
    },
    considered: {
      title: "Twelve ideas, one test: would the specialist act on it, and defend it?",
      lines: [
        "No: a score per project from red to green, and a project condition report. A number nobody can check, and " +
          "tabs the specialist already has.",
        "No: a chat window over the news, and live web search by an agent. Answers that vanish, and a brief that " +
          "differs tomorrow and cannot be checked.",
        "No: a vision model on field photos, and scraping behind a browser's name. A guess with no source, and " +
          "pretending.",
        "No: a mood score for posts. A mood is a number that bought posts can move.",
        "Later: a daily feed of every mention, and a satellite change model. Noise, and no measured error rate yet.",
        "Later: paid sources, automatic translation, and the project's own grievance log. A cost per project, a quote " +
          "no longer word for word, and a log that is not public.",
      ],
      ask: "Would the specialist open the source, act on the sentence, and defend it in a meeting with the agency?",
      notes:
        "We judged every idea by one question: what does a procurement specialist do differently after reading it? " +
        "An idea that gives a number to argue about, or a feed to mute, lost to an idea that gives a sentence to act on.",
    },

    // ── How it works ──
    worksOpener: {
      figure: "A column of filter plates with sentence slabs dropping through, one caught and slid out to the side.",
      notes: "One click starts a run. Here's what happens in the minutes that follow.",
    },
    demo: {
      title: "Watch a run: the plan, the sources, the writing, the checks, then the brief",
      box: "Deep research, {project}, {name}",
      action: "Open the Deep research tab",
      lines: [
        "The run shows its plan first: a card for each stage on one rule, and how long a run usually takes.",
        "The live card says in everyday words what Prism is doing now: checking the complaints register, looking at the " +
          "satellite pictures of each site.",
        "The brief opens in the tab. Each sentence ends in a small marker that opens its source.",
        "The sentences the checks removed sit under the brief, each with its reason.",
        "Download as PDF waits for every image, then prints a page per section.",
      ],
      showRun: "Show the recorded run",
      showPrinted: "Show the printed brief",
      run: "The recorded run on {project}: the sources card live, then the checking window with its blurred older lines.",
      runAlt: "The Deep research tab while it reads the sources: a card for each stage, the sources card live with each source's state.",
      checkingAlt: "The Deep research tab while it checks the brief: the checking window, its older lines blurred as new ones arrive.",
      printed:
        "The printed brief for {project}: the cover, the picture on the ground, and two By site pages, one with satellite " +
        "years side by side and one with field photos.",
      coverAlt: "The printed brief's cover page.",
      groundAlt: "The printed brief's page The picture on the ground, with its bottom line for procurement.",
      bySiteAlt: "The printed brief's By site page, with a site's items and its satellite years side by side.",
      bySitePhotosAlt: "The printed brief's By site page for the north-east, with its sample field photos.",
      note:
        "the demo reads no source live: the items were gathered on November 5 through Prism's own readers and stored " +
        "as a run; the writing and the checks run live.",
      notes:
        "This is the feature working. The run shows its plan and says in everyday words what it's doing. The brief " +
        "opens with a marker after every sentence, and the removed sentences sit under it with their reasons.",
    },
    pipeline: {
      title: "{sources} sources, one item shape, one writer call, {checks} checks",
      source:
        "config/research.toml, the registry with the off sources and their reasons; src/strata/research/, the run, the " +
        "readers, the writer and the brief.",
      notes:
        "Each reader produces the same item shape: the source's own words, the day it became public, a link and the " +
        "place it names. Items are stored before a word is written. The writer gets every item as data in one call and " +
        "has no tools, so it can't search, fetch or count. Prism never writes a summary into an item, so the writer " +
        "and the checker always see the original.",
    },
    checks: {
      title: "Every sentence passes the same {checks} checks as every answer, or is shown with its reason",
      kept:
        "On the five prepared projects the checks kept between {keptLow} and {keptHigh} sentences, and the rest sit " +
        "under each brief with their reasons.",
      source: "src/strata/agent/verifier.py; the briefs on the App, November 6, 2026.",
      notes:
        "These are the same checks every answer in Prism goes through. Nothing reaches the screen unchecked, and the " +
        "removed sentences are shown with their reasons.",
    },
    honest: {
      title: "What the demo shows, honestly",
      lines: [
        "No live lookups: the five prepared projects carry items gathered on November 5 through Prism's own readers and " +
          "stored as a run. Any other project says no brief has been prepared.",
        "Research again replays the stored reads, then writes and checks the brief live.",
        "The field photos are samples: openly licensed Wikimedia Commons photos near the sites, captioned as samples " +
          "that stand in for staff photos.",
        "What was not reached, the brief says: GDELT refused this network, and the sanctions check did not run because " +
          "the list needs a browser download.",
      ],
      ask:
        "Prism has no web search of its own. It reads named sources under its own name, and says 'not reached' when " +
        "one refuses.",
      notes:
        "We say this before anyone asks. The honesty is part of the design, not a caveat: a spoofed browser or a " +
        "hidden failure would be a lie the panel could catch.",
    },

    // ── The decisions ──
    decisionsOpener: {
      figure: "A short ladder leaning on a wall, the rung under the pointer lit.",
      notes:
        "Not every source weighs the same. We ranked them, and the rank decides what each source may do in the brief.",
    },
    ladder: {
      title: "Four rungs: photos, complaints, satellite, posts; the floor is the World Bank's own record",
      lines: [
        "Satellite sits third because of cost. The free mosaics are yearly at {metres} metres per pixel and show a dam, " +
          "never a pipe. Sharper imagery costs money and a trained reader, so Prism shows the years side by side and a " +
          "person judges.",
        "An item from the lowest rung alone feeds the quotes and the questions. A claim in the picture on the ground " +
          "should rest on a higher rung, or on more than one independent item. That rule is designed for the next " +
          "version.",
      ],
      source:
        "config/research.toml, each source's limitations; src/strata/agent/instructions/research_brief_writer.md, the " +
        "rule per kind.",
      notes:
        "Field photos first: the one item nobody outside the project could have planted. Formal complaints second: a " +
        "named person and a registered case. Satellite third, because of cost. Public posts last: quoted word for " +
        "word, able to start a question, never a finding on their own.",
    },
    posts: {
      title: "A post is the cheapest thing to fake, so we filter at the account",
      line:
        "Built today: a post needs a project place or an agency with a sector word, public timelines only, quoted word " +
        "for word, items are data and never instructions, no mood score. Designed for next: the account's age and " +
        "history, bursts counted once, a burst near a bid deadline shown with its dates, the counts from a tool.",
      source: "src/strata/research/sources/mastodon.py and matching.py; the writer's instruction.",
      notes:
        "A losing bidder or a contractor under pressure can buy posts for a few dollars. Old accounts with real " +
        "histories cost far more and leave traces. So the filter sits at the account, and what survives is a voice, " +
        "never a fact.",
    },
    otherDecisions: {
      title: "The other decisions, each with a road not taken",
      tiles: [
        {
          head: "Prism's own name on every call, and 'not reached' when refused",
          body:
            "Prism is honest about what it read; GDELT and several outlets refused on November 5, and the brief says " +
            "so. Not a spoofed browser agent.",
        },
        {
          head: "Every sentence cites; failures are shown",
          body: "A reader can open every source, and a hidden failure is a lie by omission. Not a confidence percentage.",
        },
        {
          head: "Numbers only from a tool",
          body:
            "The writer cannot count, add or round; the late-award window is one value in config with a benchmark " +
            "question. Not the model counting.",
        },
        {
          head: "Items stored with the day they became public",
          body: "A brief can be written again without the web, and as of a past date. Not a live search with nothing kept.",
        },
        {
          head: "One registry file for sources",
          body: "Adding an outlet is one line, and the off sources are listed with their reasons. Not readers hard-coded in the app.",
        },
        {
          head: "Field photos team-only, caption-only",
          body:
            "A staff upload is visible to the uploader's team, and the writer never sees pixels. Not public photo " +
            "sources or a vision model.",
        },
      ],
      notes:
        "Each decision has a reason a panel can test, and a road we didn't take. The ones that matter most: Prism's own " +
        "name on every call, with 'not reached' when a site refuses, and numbers only from a tool.",
    },

    // ── What comes next ──
    nextOpener: {
      figure: "Thin layers settling on a core, the newest one lit.",
      notes:
        "None of what follows is built. Each step keeps the rules: numbers from tools, a citation on every sentence, " +
        "private uploads kept private.",
    },
    nextSteps: {
      title: "Five next steps, each one a reader, a rule or a registry entry",
      tiles: [
        {
          head: "Watch a project",
          body:
            "One cited line when a signal trips: a late award, a new case at the Panel, a news item that names a site, a " +
            "field photo. The run exists; the watch is a schedule and a rule.",
        },
        {
          head: "One page per supplier",
          body:
            "Every award a firm holds across projects and countries, its share of each project, whether it is on the " +
            "debarred list. Each number from the awards tool.",
        },
        {
          head: "Check a bidding document",
          body:
            "A team's private upload read against the numbered paragraphs of the Regulations and the plan: a missing " +
            "clause, dates that do not add up, lots that differ.",
        },
        {
          head: "Point to where the ground changed",
          body:
            "A change model scores each tile between the years and shades what changed, with a stated error rate. " +
            "Prism points, a person judges, and asks for a photo.",
        },
        {
          head: "The live plan inside STEP",
          body:
            "A read-only feed gives the live plan, the prior review queue and amendments. Amendment and rebidding risk " +
            "become real signals with real counts.",
        },
      ],
      source:
        "watching a project and the supplier page need no new data; pointing to where the ground changed needs a model " +
        "with a measured error rate; checking a bidding document and the live plan need the World Bank.",
      notes: "Each is a change to one reader, one rule or one registry entry, which is how Prism is built to change.",
    },
    builtDesigned: {
      title: "What is built, and what is designed",
      tiles: [
        {
          head: "In the build",
          body:
            "The sources and the field photos. The item store with the day each item became public. The writer with no " +
            "tools. The checks, with failed sentences shown. The brief in the tab and as a PDF with a page per section. " +
            "The timeline with the plain-words now line. The registry with the off sources and their reasons. The " +
            "sanctions reader on a dated copy. The tile cache, loaded at startup.",
        },
        {
          head: "Designed, not yet built",
          body:
            "The account rules for posts: age, history, bursts, independence and the counts. The rule that a claim in " +
            "the picture on the ground needs more than one source. Translation shown beside the original. The " +
            "proposals from ProcIntel's designs, and the five next steps.",
        },
      ],
      closing: "Two apps, one conversation, five ways forward, one choice: the feature the end user would notice first.",
      notes: "The left box is in the code on the App today. The right box is designed, written up, and not yet built.",
    },
    thanks: {
      title: "Two apps, one conversation, five ways forward, one choice",
      line: "The feature the end user would notice first: what is happening on the ground, with every sentence cited and checked.",
      figure: "A plot of ground tiles with one tile lifted and a pin on it, joined by a thin line to a page.",
      links: { tab: "Open the Deep research tab", repo: "Read the code" },
      notes:
        "That's the story: how two apps became one conversation, and the feature that came of it. The Deep research " +
        "tab on the App and the proposals in the repository are open for you to read. We'd be glad to take your " +
        "questions.",
    },
  },

  // Each slide's script, by its id: the stage direction with the suggested speaker (Surya takes topics 1 and 5;
  // Chirag the open, topics 2 to 4 and the close), a line per press on what runs underneath, and the questions a
  // technical panel may ask, each with an answer that names files, tables and reasons.
  speaker: {
    welcome: {
      cue:
        "Chirag. Press F for full screen and keep /present/research/notes open on a laptop. Say the arrival line, then " +
        "hand to the agenda.",
      asked: [
        {
          q: "What is deep research, in one sentence?",
          a:
            "A tab on every project page that reads named public sources and the World Bank's own status reports, writes " +
            "a short brief on what is happening on the ground, checks every sentence against the item it cites, and " +
            "prints it.",
        },
        {
          q: "Is this a separate app?",
          a:
            "No. It is a feature of Prism: the run, the readers and the brief live in src/strata/research/, the tab is " +
            "a project page route, and the checks are the same verifier every answer uses.",
        },
      ],
    },
    agenda: {
      cue: "Chirag. Say the five topics in one breath each. Surya takes topic 1.",
      adds: [
        "How two apps became one conversation, and why we built on Prism.",
        "What the brief is, why a specialist needs it, and the ideas we set aside.",
        "How a run works, and the demo.",
        "The evidence ladder, the rules for posts, and the other decisions.",
        "Five next steps, and what is built against what is designed.",
      ],
    },
    here: {
      cue: "Surya takes over. Say the arrival line while the figure plays.",
    },
    timeline: {
      cue: "Surya. Walk the six boxes left to right. Land the last line: reading, then talking, then code.",
      figureAdds: [
        "Two apps, built in parallel in late October, on the same brief.",
        "Each of us cloned the other's repository and read its plan, its tests and its data before any call.",
        "One conversation: a list of what each app had that the other lacked.",
        "We chose Prism as the base. The merged app's name is Prism; the identifiers underneath stay Strata's.",
        "Five ways forward: four ProcIntel designs, and one gap both apps shared.",
        "Deep research was built on November 5 and 6; the four designs went into docs/proposals/ as written proposals.",
      ],
      asked: [
        {
          q: "Why not merge the two code bases?",
          a:
            "One app with one verifier gives every answer the same checks, and a demo should not depend on two services " +
            "staying up. The designs moved; the code did not need to.",
        },
        {
          q: "Where are the proposals?",
          a:
            "docs/proposals/ in the Prism repository: the MCP server, the timeline across packages, goal seeking and " +
            "the editable pipeline, each with how it would work under Prism's rules and its open questions.",
        },
      ],
    },
    "two-apps": {
      cue: "Surya. Don't read the boxes. Say the shape: Prism is the deeper platform; ProcIntel brought four designs.",
      figureAdds: [
        "Prism runs on a Databricks lakehouse with Lakebase and a Databricks App; ProcIntel on FastAPI and DuckDB.",
        "Prism holds every award and notice the World Bank publishes; ProcIntel a sample of projects across countries.",
        "Prism's verifier runs six checks on every sentence; ProcIntel checks each citation against its passage.",
        "Prism's tools live in config/tools.toml with a benchmark question each; ProcIntel's four are served over MCP.",
        "The strengths: Prism's breadth, and ProcIntel's four designs, all running.",
      ],
      adds: ["Both counted the same way on the same day: Python under src and tests, with the same commands."],
      asked: [
        {
          q: "How were the lines and tests counted?",
          a:
            "The same way in both repositories on November 5: Python source lines under src, and test_ functions under " +
            "tests. The numbers are in docs/proposal/recorded.toml with the day and how each was counted.",
        },
        {
          q: "What did ProcIntel do better?",
          a:
            "Four designs: an MCP server so an assistant can call the tools, a timeline across a project's packages, goal " +
            "seeking for a package's set-up, and a pipeline admins can edit. All four are written up as proposals.",
        },
      ],
    },
    "why-prism": {
      cue: "Surya. One line per reason, then the fair half in the callout.",
      adds: [
        "The lakehouse is Unity Catalog tables, bronze to gold, read every night by the ingestion job.",
        "src/strata/agent/verifier.py runs on every answer and every draft; the removed sentences are shown.",
        "The App is already deployed with the viewer's own token, so a new feature inherits sign-in and the views.",
        "The gate is .githooks/pre-commit: the ground-truth SQL and the offline test suite before every commit.",
        "Each proposal names its rule: numbers from tools, citations on every sentence, private uploads kept private.",
      ],
      asked: [
        {
          q: "Wasn't ProcIntel's local model setup cheaper?",
          a:
            "Yes, per call. Prism's choice was the workspace the panel would sign into, with the viewer's own " +
            "permissions on every tool call. A local model can be added as a role in config/models.toml.",
        },
        {
          q: "What does the gate run?",
          a:
            "The ground-truth SQL against the fixture database and the offline test suite, in under three minutes, so a " +
            "commit that breaks a number or a screen never lands.",
        },
      ],
    },
    "five-ways": {
      cue: "Surya for the four designs, then Chirag for the fifth. Land the test at the bottom.",
      figureAdds: [
        "The MCP server would expose config/tools.toml's tools with the same verifier contracts.",
        "The timeline would need a tool so every date on the calendar is a column the verifier can check.",
        "Goal seeking needs enough comparable packages per set-up, from find_comparables.",
        "The pipeline would turn the nightly job's tasks into rules an admin can change.",
        "Deep research adds information neither app had.",
        "It also reused the most: the verifier, the tool registry, the views and the print path.",
      ],
      asked: [
        {
          q: "Why deep research before the MCP server?",
          a:
            "The test was what a procurement specialist does differently the next morning. The MCP server helps an " +
            "assistant; deep research gives the specialist information they did not have.",
        },
        {
          q: "How long did it take to build?",
          a:
            "November 5 and 6. It reused the verifier, the tool registry, the three views and the print path, so the new " +
            "parts were the readers, the item store, the writer's instruction and the tab.",
        },
      ],
    },
    "set-aside": {
      cue: "Surya. Name what each waits on, one line each. Then hand to Chirag for topic 2.",
      adds: [
        "Which views may use it is a decision in config/roles.toml; each tool already has its benchmark question.",
        "The end event is the signed contract, as everywhere in Prism.",
        "The review type follows the whole package's estimate, never a lot's, and the answer says so beside a set-up with lots.",
        "Today the nightly chain is a Databricks job; the rules would become its tasks.",
        "One verifier, one deploy, one place for the panel to sign in.",
      ],
      asked: [
        {
          q: "Will goal seeking tell a team to divide a package to stay under a threshold?",
          a:
            "No. The review type follows the whole package's estimate, and Prism refuses to describe dividing a package " +
            "to stay under a review threshold as a way to plan.",
        },
        {
          q: "Who would use the MCP server?",
          a:
            "A staff member's own assistant, such as Copilot, calling Prism's tools with that person's own token, so it " +
            "sees exactly what they would see in the app.",
        },
      ],
    },
    brief: {
      cue: "Chirag takes over. Say the arrival line while the figure plays.",
    },
    "what-it-is": {
      cue: "Chirag. Walk the sections in three groups: the message, the evidence, what to do and what is missing.",
      figureAdds: [
        "The headline, the picture on the ground and the bottom line are the answer first.",
        "Developments, the sites and the quotes are the proof.",
        "The questions and what the run could not see close it; that last section is always there.",
      ],
      adds: [
        "The ISR narrative reader takes the newest status reports the lakehouse holds; the number is a setting in config/research.toml.",
        "The writer is one call with no tools; the checks are src/strata/agent/verifier.py.",
      ],
      asked: [
        {
          q: "Why eight fixed sections?",
          a:
            "A specialist reads it on a phone before a meeting and files it after. A fixed shape means they know where " +
            "the bottom line is, and the print path gives each section its own page.",
        },
        {
          q: "Who can see a brief?",
          a:
            "Every viewer sees the public items. A field photo is for the uploader's team only, so a project can hold the " +
            "team's brief, which cites the photos, and everyone else's, which does not.",
        },
      ],
    },
    gap: {
      cue: "Chirag. Top lane first, then the bottom lane, then the arrow between them.",
      figureAdds: [
        "The World Bank's record: one status report in March.",
        "June: a local outlet on the Wajir sludge plant.",
        "July to October: the late awards in the notices; October: weeks without water in two Mombasa suburbs.",
        "The brief fills the gap between the lanes.",
      ],
      adds: ["The late awards are counted by research_evidence, never by the writer; the window is research.late_award_days in config/thresholds.toml."],
      asked: [
        {
          q: "Where do the late awards come from?",
          a:
            "The procurement notices in the lakehouse. research_evidence counts the contracts awarded in the window " +
            "before the closing date, and the window is one value in config/thresholds.toml.",
        },
        {
          q: "Is a late award a problem?",
          a:
            "It is a reason to look, never a finding. The brief names the contracts and the notices, and the specialist " +
            "decides what to ask.",
        },
      ],
    },
    considered: {
      cue: "Chirag. Don't read all six. Pick the score, the live search and the change model, then say the test.",
      adds: [
        "Prism never rates a project, an agency or a person.",
        "A brief is stored with its run in the item store, so the same click gives the same brief.",
        "The writer sees the caption a staff member wrote, never the pixels.",
        "Posts are quoted word for word, with who said them and a link.",
        "The change model is next step 4, once it has a measured error rate.",
        "The off sources are listed in config/research.toml with their reasons.",
        "The test is in the ask: open, act, defend.",
      ],
      asked: [
        {
          q: "The World Bank uses ratings. Why no score?",
          a:
            "A score is a number nobody can check, and a specialist would have to defend it to a borrower. A cited " +
            "sentence names the contract and the source, and the specialist decides.",
        },
        {
          q: "Why not search the web live?",
          a:
            "The same click would give a different brief tomorrow, sites block bots at the worst moment, and the checker " +
            "cannot verify what it never saw. Named readers store their items first.",
        },
      ],
    },
    works: {
      cue: "Chirag. Say the arrival line while the figure plays.",
    },
    "demo-research": {
      cue:
        "Chirag. Click Open the Deep research tab and press Research again on P156634. If the App is down, press on " +
        "to the recorded run and the printed brief.",
      adds: [
        "The plan is sent first, before any reader runs, so nothing jumps while it streams.",
        "The plain words come from the run's progress events, one per reader.",
        "Each marker opens the item in the evidence drawer, with its link and the day it became public.",
        "The removed sentences come from the verifier's results, each with the check it failed.",
        "The print page waits for every satellite tile and photo before it prints.",
        "The recorded run, captured on the App: the sources card while it reads, then the checking window.",
        "The printed brief: the cover, the picture on the ground, and the By site pages with satellite years and field photos.",
      ],
      asked: [
        {
          q: "Did it read these sources live, just now?",
          a:
            "No, and we say so. The items were gathered on November 5 through Prism's own readers and stored as a run. " +
            "Research again replays the stored reads, then writes and checks the brief live.",
        },
        {
          q: "What does a brief cost?",
          a:
            "One writer call of about 15,000 words in and 2,000 out, plus the judge's calls. The sources are free and " +
            "paced by the registry, and there is no agent loop, so the cost does not grow with the sources.",
        },
      ],
    },
    pipeline: {
      cue: "Chirag. Left to right. Land the item shape: Prism never writes a summary into an item.",
      figureAdds: [
        "The project's facts come from the lakehouse: name, status, closing date and the sites.",
        "Each source has one reader, named in config/research.toml, run at once with its own pace and cache.",
        "The item shape is one table in the item store, with the day each item became public.",
        "The writer's instruction is src/strata/agent/instructions/research_brief_writer.md; it gets items as data.",
        "The checks are the verifier's, on every sentence; a failed one is stored with its reason.",
        "The brief is stored with its run, so a second visit reads it and calls no model.",
      ],
      asked: [
        {
          q: "Which sources are off, and why?",
          a:
            "Reddit, Bluesky and X refuse readers that are not browsers or need a paid key, and Google News allows " +
            "personal readers only. Each sits in config/research.toml as off, with its reason.",
        },
        {
          q: "How do you add an outlet?",
          a: "One feed entry under outlet_feeds in config/research.toml. The reader, the store and the checks need no change.",
        },
      ],
    },
    checks: {
      cue: "Chirag. The same figure as the first talk: the same checks run on every sentence of a brief.",
      figureAdds: [
        "One sentence cites an item the run stored; the other has a number no tool returned.",
        "Numbers and cited IDs first: the second sentence fails.",
        "Then the quotes, and the judge on whether the sentence says no more than its items.",
        "Then advice needs evidence, and a disagreement shows both sides.",
        "The first is shown; the second is removed and listed under the brief.",
      ],
      adds: ["The kept and removed counts are from the briefs on the App, recorded in docs/proposal/recorded.toml."],
      asked: [
        {
          q: "How do you stop the model making things up?",
          a:
            "The writer only sees the items Prism stored, and it has no tools. The checker compares every number, date, " +
            "quote and citation against those same items, and a judge confirms each sentence says no more than its items.",
        },
        {
          q: "What does the judge use?",
          a:
            "A second model role in config/models.toml, asked one question per sentence with only its cited items. Its " +
            "answer is one of the checks, never the only one.",
        },
      ],
    },
    honest: {
      cue: "Chirag. Say this before anyone asks. Then hand to topic 4.",
      adds: [
        "The stored run is in the item store; config/thresholds.toml says whether a run reads live.",
        "Research again writes and checks live on Azure OpenAI.",
        "The photos' licenses are on each caption.",
        "GDELT answered 429 all afternoon on November 5; the brief's last section names it.",
        "Prism's readers send their own name on every call, from the agent string in config/research.toml.",
      ],
      asked: [
        {
          q: "Isn't this a web search with a model on top?",
          a:
            "No. The items are stored with their dates and the source's own words, every count comes from a tool, and " +
            "every sentence is checked and cited to a page the reader can open.",
        },
        {
          q: "What can it not see?",
          a:
            "The project's own grievance log, the live plan inside STEP, anything behind a paywall or a bot check, and " +
            "any complaint that never reached the Inspection Panel. The last section says so every time.",
        },
      ],
    },
    decisions: {
      cue: "Chirag. Say the arrival line while the figure plays.",
    },
    ladder: {
      cue: "Chirag. Build it from the floor up, then the two lines beside it.",
      figureAdds: [
        "The floor: the ISR narrative and the notices, the record the ground is compared against.",
        "Posts: anyone can post, so a post can start a question and never a finding.",
        "Satellite: shown for a person to compare, never read by Prism.",
        "Complaints: the Inspection Panel's register, registered cases only.",
        "Field photos: from signed-in staff only, with the camera's date and place.",
      ],
      adds: [
        "The free mosaics are Sentinel cloudless tiles, cached by Prism and loaded at startup.",
        "Today the writer follows a rule per kind; the rule for more than one source is designed for next.",
      ],
      asked: [
        {
          q: "Where does the press sit?",
          a:
            "Beside the ladder. An outlet with an editor and a byline ranks above an anonymous post and below a " +
            "registered case; an agency's page is the agency's side, named as such.",
        },
        {
          q: "Can't photo metadata be faked?",
          a:
            "It can be edited, which is why Prism takes photos only from signed-in staff, keeps the uploader's name and " +
            "team, and shows a photo only to that team.",
        },
      ],
    },
    posts: {
      cue: "Chirag. The why first, then be exact about what is built and what is designed.",
      figureAdds: [
        "The Mastodon reader reads public tag timelines for the country, the sector word and each place.",
        "matching.py keeps a post only when it names a project place or an agency with a sector word.",
        "Designed: the account's age, a value in config.",
        "Designed: identical words within hours count once, as a burst.",
        "Designed: a claim needs a second independent account, or a higher rung.",
        "What survives is quoted word for word; the counts would come from a tool.",
      ],
      adds: ["Items are data, never instructions: the writer's instruction says so, and every sentence is checked anyway."],
      asked: [
        {
          q: "What about prompt injection in a post?",
          a:
            "A post can hold words aimed at the model. The writer is told items are data, never instructions, and every " +
            "sentence is checked against its items anyway.",
        },
        {
          q: "What about bought campaigns?",
          a:
            "Today a post needs a place or an agency with a sector word and is quoted as a voice. The account rules are " +
            "designed and are the next change to the posts reader.",
        },
      ],
    },
    "other-decisions": {
      cue: "Chirag. Don't read all six. Pick the named calls and numbers from a tool, then hand to Surya for topic 5.",
      adds: [
        "The agent string is in config/research.toml; a bot check page is detected and named as not reached.",
        "The verifier's removed sentences are stored with the brief.",
        "research_evidence counts; the writer only quotes its counts.",
        "Each item keeps the day it became public, so a brief can be written as of a past date.",
        "config/research.toml is the one registry of research sources (CLAUDE.md rule 9).",
        "Photos follow the same access rule as a plan or a PPSD: the uploader's team only.",
      ],
      asked: [
        {
          q: "Why no confidence percentage?",
          a:
            "A percentage invites a number nobody can check. A sentence either passes the checks and is shown with its " +
            "citation, or is removed and listed with its reason.",
        },
        {
          q: "Why one writer call and not an agent loop?",
          a:
            "The checker can only compare what the writer saw, and one call has a known cost. An agent loop with search " +
            "tools would write from things nobody stored.",
        },
      ],
    },
    next: {
      cue: "Surya takes over. Say the arrival line while the figure plays.",
    },
    "next-steps": {
      cue: "Surya. One line each. Land it: each is a reader, a rule or a registry entry.",
      adds: [
        "The watch is a schedule and a rule over the run that exists.",
        "The supplier page reads the awards and the sanctions reader Prism has.",
        "The bidding document check reuses private uploads and paragraph citations.",
        "The change model needs a measured error rate before it points anywhere.",
        "The STEP feed needs the World Bank's agreement; the checks are built.",
      ],
      asked: [
        {
          q: "Which would you build first?",
          a: "Watching a project. It needs no new data: the run exists, and the watch is a schedule and a rule for what counts as news.",
        },
        {
          q: "What would the STEP feed change?",
          a:
            "Amendment and rebidding risk would become real signals with real counts instead of proxies, and the plan " +
            "check would read the live plan instead of a published version.",
        },
      ],
    },
    "built-designed": {
      cue: "Surya, then Chirag to close. Say the split plainly, so nobody has to ask.",
      adds: [
        "Everything on the left runs on the App today.",
        "Everything on the right is written up and not yet built.",
        "Chirag closes on the one line.",
      ],
    },
    thanks: {
      cue: "Chirag. Close on the one line, then open for questions.",
      asked: [
        {
          q: "What would you change if you had another week?",
          a:
            "The account rules for posts, since a post is the cheapest thing to fake, and then the watch on a project, " +
            "which needs no new data.",
        },
      ],
    },
  } as Record<string, ResearchSpeaker>,
};

// The research talk's figures (.notes/deck3/brief.md, section 6), drawn by tickets 163, 164 and 165. title is the
// SVG's <title>; steps its text version in reading order, one line per press on the slide, voice-neutral. A step text
// holds no number: the number check reads it on the slide.
export const researchFigureCopy = {
  "merge-timeline": {
    title: "Strata and ProcIntel, then one conversation",
    steps: [
      "Strata and ProcIntel were built on one brief in late October: Strata by Chirag, ProcIntel by Surya.",
      "Each read the other's repository: its scope, its data, how it was built and its tests.",
      "One conversation: what each app had that the other lacked.",
      "The decision to build on Prism, the merged app's name for Strata.",
      "The ways forward: the ProcIntel designs Prism lacked, and deep research.",
      "Deep research was built, and the ProcIntel designs were written up as proposals. The reading came before the talking, and the talking before any code.",
    ],
  },
  "two-apps": {
    title: "Prism and ProcIntel on one brief",
    steps: [
      "Where each runs: Prism on a Databricks lakehouse with sign-in and a view per role; ProcIntel on one machine with local models.",
      "Data: Prism holds every record the World Bank publishes and a documented pilot slice; ProcIntel a sample of projects and their reports.",
      "Checking: Prism's verifier runs on every sentence and shows what it removed; ProcIntel checks each citation against its passage and refuses when the reports do not cover it.",
      "Tools: Prism has a registry of tools, each with a contract and a benchmark question; ProcIntel serves its tools over MCP.",
      "Strengths: Prism's breadth and its rule that every number comes from a tool; ProcIntel's designs, all running.",
    ],
  },
  "five-ways": {
    title: "The ways forward, judged by one test",
    steps: [
      "An MCP server: an assistant such as Claude or Copilot calls Prism's tools, an indirect gain for the specialist.",
      "A timeline across a project's packages: the whole plan on one calendar.",
      "Goal seeking: the set-ups that met a target in the past, with the count behind each.",
      "An editable pipeline: rules the data team can change and try; nothing the specialist sees directly.",
      "Deep research: what is happening on the ground, the information neither app had.",
      "One test for every option: what does a procurement specialist do differently the next morning? Deep research first; the ProcIntel designs written up as proposals.",
    ],
  },
  "brief-sections": {
    title: "The sections of the brief",
    steps: [
      "The message first: a one-sentence headline, the picture on the ground in short cited paragraphs, and the bottom line for procurement.",
      "Then the evidence and the voices: developments newest first, each site with its photos and satellite years side by side, and what people are saying, quoted word for word.",
      "Then what to do and what is missing: questions to take to the agencies, and what the run could not see, always present.",
    ],
  },
  "record-gap": {
    title: "The record and the ground, one year",
    steps: [
      "The World Bank's own record: one status report in March, and the next months later.",
      "The public record in June: a sludge plant well short of done, in a local outlet.",
      "From July to October: awards landing in the last months before the closing date, in the notices; in October, weeks without water in Changamwe and Jomvu, in the national news agency.",
      "The brief fills the gap between the lanes, with sources the specialist can open.",
    ],
  },
  "research-run": {
    title: "How a run works",
    steps: [
      "The run reads the project's facts: its name, status, closing date and sites.",
      "Then every source at once, each through its own reader, plus the team's field photos.",
      "Every reader produces the same item shape: the source's own words, the day it became public, a link, the place it names. Items are stored before a word is written.",
      "One writer call gets every item as data. It has no tools, so it cannot search, fetch or count; every count comes from one tool.",
      "The checks run on every sentence against the items it cites; a failed sentence is removed and shown with its reason.",
      "The brief is kept with its run, in the tab and as a PDF, and a second visit calls no model.",
    ],
  },
  "evidence-ladder": {
    title: "The evidence ladder",
    steps: [
      "The floor is the World Bank's own record: the status reports' narrative and the procurement notices, which the ground is compared against.",
      "Public posts: anyone can post, so a post is quoted word for word and can start a question, never a finding on its own.",
      "Satellite pictures: shown for a person to compare, never read by Prism; third because sharper imagery costs money and a trained reader.",
      "Formal complaints: a named person and a registered case at the Inspection Panel, slow and rare, which is why it is strong.",
      "Field photos from staff: the one item nobody outside the project could have planted, dated and placed by the camera, visible to the team only.",
    ],
  },
  "post-funnel": {
    title: "How a public post reaches the brief",
    steps: [
      "The reader takes the newest public posts for each tag: the country, the sector word and each place.",
      "A post is kept only when it names a project place or an agency together with a sector word; a tag alone brings nothing in.",
      "Designed for next: the account is over a year old, with a history beyond one agency, so an account made for the tender is set aside.",
      "Designed for next: identical words from several accounts within hours count once, as a burst.",
      "Designed for next: a second independent account, or a higher rung, for each claim.",
      "What survives is quoted word for word, with a link, and can become a question for the agency. What each step set aside is counted, so the brief can say how many posts it read and kept.",
    ],
  },
};

export type ResearchFigureId = keyof typeof researchFigureCopy;
