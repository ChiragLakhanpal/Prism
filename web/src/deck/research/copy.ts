// Every word of the deep research talk at /present/research (ticket 162; .notes/deck3/brief.md; cut to sixteen slides
// by ticket 166): its topics, its slides, its speaker notes and its figures' titles and text versions. The deck's chrome
// (the counter, the press lines, the notes window's labels) stays in web/src/deck/copy.ts, deckCopy, which both talks
// share. The copy lint reads this file as it reads web/src/copy.ts (COPY_FILES in web/lint/run.ts).
//
// Voice: two people present it, so slides name Prism in the third person and the notes say "we", or "I" for the
// presenter's own words. Figure text versions name no speaker. The slides carry no dates, no sources and no
// disclaimers (the user, November 6, 2026): Chirag and Surya add the context out loud, from the notes.
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
  // The talk's five topics, in order, as the tracker in the header and the openers name them. The tracker is the
  // talk's agenda, so the topics have no lines of their own.
  topics: {
    here: { name: "How we got here" },
    brief: { name: "Deep research" },
    works: { name: "How it works" },
    decisions: { name: "The decisions" },
    next: { name: "What comes next" },
  },

  slides: {
    welcome: {
      statement: "What is happening on the ground, with every sentence cited and checked",
      line: "Deep research in Prism, and how we decided to build it.",
      figure: "A plot of ground tiles with one tile lifted and a pin on it, joined by a thin line to a page.",
      notes:
        "Thank you for having us both. This round asked us to work together, so we'll tell you first how we worked, " +
        "then what we built. Prism now reads what the press, the complaints register, satellites, public posts and " +
        "the World Bank's own reports say about a project, writes a short brief for a procurement specialist, checks " +
        "every sentence, and prints it.",
    },

    // ── How we got here ──
    timeline: {
      title: "We read each other's work before we wrote a line",
      notes:
        "We didn't start by merging code. Each of us read the other's repository first: its scope, its data, how it " +
        "was built and its tests. Then we had one conversation about what each app had that the other lacked. The " +
        "reading came before the talking, and the talking came before any code.",
    },
    twoApps: {
      title: "We built on Prism for its data and its checks. ProcIntel brought the sharper designs.",
      counted:
        "Prism has {linesPrism} lines of Python and {testsPrism} tests. ProcIntel has {linesProcintel} lines and " +
        "{testsProcintel} tests. Both were counted the same way.",
      notes:
        "Prism is the deeper platform: the whole open data set in a lakehouse, a verifier on every sentence and a " +
        "gate on every commit. ProcIntel is the smaller app with designs Prism didn't have: the MCP server, the " +
        "timeline across packages, goal seeking and the editable pipeline. We built on Prism because it already " +
        "runs, with sign-in, and new work lands through the same checks.",
    },
    fiveWays: {
      title: "Five ways forward, one test: what does a specialist do differently the next morning?",
      notes:
        "The four designs make Prism's existing data easier to use or plan with. Deep research came from a gap both " +
        "apps shared: neither could see what was happening on the ground at a project. We judged every option by one " +
        "question: what does a procurement specialist do differently the next morning?",
    },

    // ── Deep research ──
    // A topic's navy opener: its hairline figure's label and the arrival line, said while the figure plays. The opener
    // shows the topic's number and name, with no line under it.
    briefOpener: {
      figure: "A report whose pages split into paragraph slabs that slide out, each to its place on a shelf.",
      notes:
        "A procurement specialist can read everything the World Bank holds on a project. They still can't see the " +
        "ground.",
    },
    gap: {
      title: "The World Bank's record moved once in a year. The ground kept moving.",
      lines: [
        "Deep research is a tab on every project page. One click reads the public sources, the last {reports} status " +
          "reports and the team's field photos, then writes a short brief, checks every sentence against its source " +
          "and prints it.",
        "On the demo project the March status report put progress at {isrProgress} percent. By June the public " +
          "record put the Wajir plant at {wajirProgress} percent, and {lateAwards} awards landed in the last " +
          "{lateDays} days before closing.",
      ],
      notes:
        "A status report is written by the project team and arrives about twice a year. In the months between, works " +
        "finish or stall, people protest and awards land weeks before closing. The brief fills those months with " +
        "sources the specialist can open and check, and its last section says what the run couldn't see, so silence " +
        "is never mistaken for a clean record.",
    },
    considered: {
      title: "Twelve ideas, and the question that sorted them",
      lines: [
        "A score per project, red to green. Nobody can check it, so nobody will defend it.",
        "A chat window over the news, or live web search by an agent. Answers that vanish, and a brief that reads " +
          "differently tomorrow.",
        "A vision model on field photos, or a reader that pretends to be a browser. A guess with no source, and a lie " +
          "to the site.",
        "A mood score for public posts. A mood is a number that bought posts can move.",
        "A daily feed of every mention. Noise a specialist would mute within a week.",
        "Kept for later, each waiting on one thing: a satellite change model, paid sources, translation shown beside " +
          "the original, and the project's own grievance log.",
      ],
      ask: "Would a specialist act on this sentence, and defend it to the agency?",
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
      title: "One click starts a run, and the brief that comes back can be checked line by line",
      box: "Deep research, {project}, {name}",
      action: "Open the Deep research tab",
      lines: [
        "The run shows its plan first, a card for each stage, and says in plain words what it is doing now.",
        "The brief opens in the tab. A small marker after each sentence opens its source.",
        "The sentences the checks removed sit under the brief, each with its reason.",
        "Download as PDF prints a page per section, once every image has loaded.",
      ],
      showRun: "Recorded run",
      showPrinted: "Printed brief",
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
      notes:
        "This is the feature working. The run shows its plan and says in plain words what it's doing. The brief opens " +
        "with a marker after every sentence, and the removed sentences sit under it with their reasons.",
    },
    pipeline: {
      title: "Every source is stored as an item before a word is written, and the writer has no tools",
      // Spoken, with its numbers bound: the research sources and the checks to their settings, the kept sentences to
      // the recorded register.
      notes:
        "Prism reads {sources} sources, each through its own reader, and every reader produces the same item shape: " +
        "the source's own words, the day it became public, a link and the place it names. The writer gets every item " +
        "as data in one call and has no tools, so it can't search, fetch or count. Then every sentence goes through " +
        "the same {checks} checks as every answer in Prism. On the five prepared projects they kept between {keptLow} " +
        "and {keptHigh} sentences, and the rest sit under each brief with their reasons.",
    },

    // ── The decisions ──
    decisionsOpener: {
      figure: "A short ladder leaning on a wall, the rung under the pointer lit.",
      notes:
        "Not every source weighs the same. We ranked them, and the rank decides what each source may do in the brief.",
    },
    ladder: {
      title: "Four rungs of evidence, each harder to fake than the one below",
      lines: [
        "Satellite sits third because of cost. The free mosaics are yearly, at {metres} metres per pixel, and show a " +
          "dam but never a pipe. Prism shows the years side by side and a person judges.",
        "A post on its own can start a question, never a finding. A claim in the picture on the ground should rest on " +
          "a higher rung, or on more than one independent source. That rule is designed, not built yet.",
      ],
      notes:
        "Field photos first: the one item nobody outside the project could have planted. Formal complaints second: a " +
        "named person and a registered case. Satellite third, because of cost. Public posts last: quoted word for " +
        "word, able to start a question, never a finding on their own.",
    },
    posts: {
      title: "A post is the cheapest thing to fake, so we filter at the account",
      line:
        "Built today: a post has to name a project place or an agency with a sector word, come from a public " +
        "timeline, and is quoted word for word. Designed, not yet built: the account's age and history, bursts " +
        "counted once, and a burst near a bid deadline shown with its dates.",
      notes:
        "A losing bidder or a contractor under pressure can buy posts for a few dollars. Old accounts with real " +
        "histories cost far more and leave traces. So the filter sits at the account, and what survives is a voice, " +
        "never a fact.",
    },

    // ── What comes next ──
    nextOpener: {
      figure: "Thin layers settling on a core, the newest one lit.",
      notes:
        "None of what follows is built. Each step keeps the rules: numbers from tools, a citation on every sentence, " +
        "private uploads kept private.",
    },
    nextSteps: {
      title: "Five next steps, none of them built yet",
      tiles: [
        {
          head: "Watch a project",
          body:
            "One cited line when a late award, a Panel case, a news item naming a site or a field photo arrives. The " +
            "run exists. The watch is a schedule and a rule.",
        },
        {
          head: "One page per supplier",
          body:
            "Every award a firm holds, across projects and countries, and whether it is on the debarred list. Each " +
            "number from the awards tool.",
        },
        {
          head: "Check a bidding document",
          body:
            "A team's private upload read against the Regulations and the plan: a missing clause, dates that do not add " +
            "up, lots that differ.",
        },
        {
          head: "Where the ground changed",
          body:
            "A change model shades what moved between the satellite years. Prism points, a person judges.",
        },
        {
          head: "The live plan inside STEP",
          body:
            "A read-only feed of the live plan and its amendments. Amendment and rebidding risk become real signals.",
        },
      ],
      closing:
        "Built today: the readers, the item store, the writer with no tools, the checks and the printed brief. " +
        "Designed, not built: the account rules for posts, and a second source for every claim.",
      notes: "Each is a change to one reader, one rule or one registry entry, which is how Prism is built to change.",
    },
    thanks: {
      title: "Two apps, one conversation, five ways forward, one choice",
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
  // technical panel may ask, each with an answer that names files, tables and reasons. What the cut slides of ticket
  // 166 said lives on here: why Prism under two-apps, what each design waits on under five-ways, the brief's sections
  // under gap, the demo's honesty under demo-research, the checks and the cost under pipeline, the other decisions
  // under ladder and posts, and what is built against what is designed under next-steps.
  speaker: {
    welcome: {
      cue:
        "Chirag. Press F for full screen and keep /present/research/notes open on a laptop. Say the arrival line, then " +
        "hand to Surya for the first topic.",
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
    timeline: {
      cue: "Surya takes over. Walk the boxes left to right. Land the last line: reading, then talking, then code.",
      figureAdds: [
        "Two apps, built apart on the same brief, neither knowing the other's work.",
        "Each of us cloned the other's repository and read its plan, its tests and its data before any call.",
        "One conversation: a list of what each app had that the other lacked.",
        "We chose Prism as the base. The merged app's name is Prism; the identifiers underneath stay Strata's.",
        "Five ways forward: four ProcIntel designs, and one gap both apps shared.",
        "Deep research was built in the night after the conversation; the four designs went into docs/proposals/ as " +
          "written proposals.",
      ],
      asked: [
        {
          q: "Why not merge the two code bases, or link the apps at run time?",
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
        "Prism's verifier runs on every sentence and shows what it removed; ProcIntel checks each citation against its passage.",
        "Prism's tools live in config/tools.toml with a benchmark question each; ProcIntel's are served over MCP.",
        "The strengths: Prism's breadth, and ProcIntel's four designs, all running.",
      ],
      adds: ["Both counted the same way on the same day: Python source lines under src, and test functions under tests."],
      asked: [
        {
          q: "Why build on Prism?",
          a:
            "The lakehouse holds every award and notice in Unity Catalog tables, bronze to gold, read every night. " +
            "src/strata/agent/verifier.py runs on every sentence of every answer. The App is already deployed with the " +
            "viewer's own token, so a new feature inherits sign-in and the views. And .githooks/pre-commit runs the " +
            "ground-truth SQL and the offline tests before every commit, so new work could land overnight safely.",
        },
        {
          q: "How were the lines and tests counted?",
          a:
            "The same way in both repositories on the same day: Python source lines under src, and test_ functions " +
            "under tests. The numbers are in docs/proposal/recorded.toml with the day and how each was counted.",
        },
        {
          q: "What did ProcIntel do better?",
          a:
            "Four designs: an MCP server so an assistant can call the tools, a timeline across a project's packages, goal " +
            "seeking for a package's set-up, and a pipeline admins can edit. All four are written up as proposals.",
        },
      ],
    },
    "five-ways": {
      cue: "Surya for the four designs, then Chirag for the fifth. Land the test at the bottom.",
      figureAdds: [
        "The MCP server waits on a decision in config/roles.toml on which views may use it; each tool already has its benchmark question.",
        "The timeline waits on the dependencies a person adds, and a tool so every date on the calendar is a column the verifier can check.",
        "Goal seeking waits on enough comparable packages per set-up, from find_comparables.",
        "The pipeline waits on an admin role, and the nightly job's tasks as rules an admin can change.",
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
            "It was built in the night after the conversation. It reused the verifier, the tool registry, the views and " +
            "the print path, so the new parts were the readers, the item store, the writer's instruction and the tab.",
        },
        {
          q: "Will goal seeking tell a team to divide a package to stay under a threshold?",
          a:
            "No. The review type follows the whole package's estimate, never a lot's, and Prism refuses to describe " +
            "dividing a package to stay under a review threshold as a way to plan.",
        },
      ],
    },
    brief: {
      cue: "Chirag takes over. Say the arrival line while the figure plays.",
    },
    gap: {
      cue: "Chirag. Top lane first, then the bottom lane, then the arrow between them. Then the two lines.",
      figureAdds: [
        "The World Bank's record: one status report in March.",
        "June: a local outlet on the Wajir sludge plant.",
        "July to October: the late awards in the notices; October: weeks without water in two Mombasa suburbs.",
        "The brief fills the gap between the lanes.",
      ],
      adds: [
        "The ISR narrative reader takes the newest status reports the lakehouse holds; how many is a setting in " +
          "config/research.toml. The writer is one call with no tools.",
        "The late awards are counted by research_evidence, never by the writer; the window is " +
          "research.late_award_days in config/thresholds.toml.",
      ],
      asked: [
        {
          q: "What is in a brief?",
          a:
            "Fixed sections, so a specialist knows where the bottom line is. The message first: the headline, the " +
            "picture on the ground and the bottom line for procurement. Then the evidence: developments, each site with " +
            "its photos and satellite years, and what people are saying. Then the questions for the agencies, and what " +
            "the run could not see, which is always there.",
        },
        {
          q: "Who can see a brief?",
          a:
            "Every viewer sees the public items. A field photo is for the uploader's team only, so a project can hold the " +
            "team's brief, which cites the photos, and everyone else's, which does not.",
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
      cue: "Chirag. Don't read all six. Pick the score, the live search and the change model, then say the question.",
      adds: [
        "Prism never rates a project, an agency or a person.",
        "A brief is stored with its run in the item store, so the same click gives the same brief.",
        "The writer sees the caption a staff member wrote, never the pixels, and every reader calls under Prism's own name.",
        "Posts are quoted word for word, with who said them and a link.",
        "The watch in the next steps sends a cited line when something new arrives, not every mention.",
        "The change model waits on a measured error rate, paid sources on a cost per project, translation on showing the original beside it, and the grievance log on access, since it is not public.",
        "The question is in the callout: would they act on it, and defend it?",
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
        "Chirag. Say it before anyone asks: the demo reads no source live. The items were gathered through Prism's own " +
        "readers and stored as a run, and the writing and the checks run live. Click Open the Deep research tab and " +
        "press Research again on P156634. If the App is down, press on to the recorded run and the printed brief.",
      adds: [
        "The plan is sent first, before any reader runs, so nothing jumps while it streams. The plain words come from " +
          "the run's progress events, one per reader.",
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
            "No, and we say so. The items were gathered through Prism's own readers and stored as a run for the prepared " +
            "projects; any other project says no brief has been prepared. Research again replays the stored reads, then " +
            "writes and checks the brief live.",
        },
        {
          q: "Are the field photos real?",
          a:
            "They are samples: openly licensed Wikimedia Commons photos near the sites, captioned as samples that stand " +
            "in for staff photos, each with its license on the caption.",
        },
        {
          q: "What did the run not reach?",
          a:
            "GDELT refused this network, and the brief's last section names it. Prism never poses as a browser: it reads " +
            "named sources under its own name and says 'not reached' when one refuses. A spoofed browser would be a lie " +
            "the panel could catch.",
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
          q: "How do you stop the model making things up?",
          a:
            "The writer only sees the items Prism stored, and it has no tools. The checker compares every number, date, " +
            "quote and citation against those same items, and a judge, a second model role in config/models.toml, " +
            "confirms each sentence says no more than its items.",
        },
        {
          q: "What does a brief cost?",
          a:
            "One writer call of about 15,000 words in and 2,000 out, plus the judge's calls. The sources are free and " +
            "paced by the registry, and there is no agent loop, so the cost does not grow with the sources.",
        },
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
        "Field photos: from signed-in staff only, with the camera's date and place, seen by the uploader's team only.",
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
            "team, and shows a photo only to that team, as it does a plan or a PPSD. The writer sees the caption, never " +
            "the pixels.",
        },
        {
          q: "Why store every item?",
          a:
            "Each item keeps the source's own words and the day it became public, so a brief can be written again " +
            "without the web, and as of a past date. A live search keeps nothing to check.",
        },
      ],
    },
    posts: {
      cue: "Chirag. The why first, then be exact about what is built and what is designed. Then hand to Surya.",
      figureAdds: [
        "The Mastodon reader reads public tag timelines for the country, the sector word and each place.",
        "matching.py keeps a post only when it names a project place or an agency with a sector word.",
        "Designed: the account's age, a value in config.",
        "Designed: identical words within hours count once, as a burst.",
        "Designed: a claim needs a second independent account, or a higher rung.",
        "What survives is quoted word for word; the counts would come from a tool.",
      ],
      adds: [
        "Items are data, never instructions: the writer's instruction says so, and every sentence is checked anyway.",
      ],
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
        {
          q: "Who does the counting?",
          a:
            "A tool, never the model. research_evidence counts, the late-award window is one value in " +
            "config/thresholds.toml with a benchmark question, and the writer only quotes the counts it is given.",
        },
        {
          q: "How does Prism identify itself to a site?",
          a:
            "By its own name on every call, from the agent string in config/research.toml, the one registry of research " +
            "sources. A bot check page is detected and named as not reached.",
        },
      ],
    },
    next: {
      cue: "Surya takes over. Say the arrival line while the figure plays.",
    },
    "next-steps": {
      cue: "Surya. One line each. Land it: each is a reader, a rule or a registry entry. Then say the split plainly.",
      adds: [
        "The watch is a schedule and a rule over the run that exists.",
        "The supplier page reads the awards and the sanctions reader Prism has.",
        "The bidding document check reuses private uploads and paragraph citations.",
        "The change model needs a measured error rate before it points anywhere.",
        "The STEP feed needs the World Bank's agreement; the checks are built.",
        "The line's first half runs on the App today; its second half is written up and not yet built. Then hand to Chirag.",
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
    thanks: {
      cue: "Chirag. Close on the title line, then open for questions.",
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
// holds no number: the number check reads it on the slide. Nor a date of the build (ticket 166); record-gap's months
// are its evidence's own. brief-sections is no slide's since ticket 166, and stays an export the figure tests compare.
export const researchFigureCopy = {
  "merge-timeline": {
    title: "Strata and ProcIntel, then one conversation",
    steps: [
      "Strata and ProcIntel were built on one brief: Strata by Chirag, ProcIntel by Surya.",
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
