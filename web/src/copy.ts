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

// The Lessons tab's purpose, which the library and Waiting for review share under the same h1.
const LESSONS_PURPOSE =
  "Each lesson comes from a completion report or its review, quoted word for word with its page. A lead " +
  "procurement specialist decides which lessons enter the library.";

// The requests I turn down every time (ticket 24; the 24 brief, section 5.6), keyed by the refusal keys in
// src/strata/agent/refusals.py. The agent answers such a request with its key and never with words of its
// own, and the answer panel writes lead (what I don't do), then instead (what I can do). How Strata works
// lists each lead with its why ("What I don't do"). A test fails when a key lacks one of the three, or when
// this list and the Python one differ.
const REFUSALS = {
  supplier_scores: {
    lead: "I don't score or rank suppliers.",
    instead: "I can list the contracts a supplier signed on World Bank-financed projects, each with its award notice.",
    why: "The public records show which contracts a supplier signed. They don't show how well it did the work.",
  },
  fraud_and_redactions: {
    lead: "I don't judge whether fraud or corruption took place, and I don't try to work out who a redacted report is about.",
    instead: "I can show what the published reports say, word for word, with their pages.",
    why: "Only the World Bank's integrity investigators make those findings, and a wrong guess about a person could harm them.",
  },
  live_tenders: {
    lead: "I don't comment on a tender that is still open, and I don't say who is likely to win one.",
    instead: "I can show how comparable packages went once their contracts were signed.",
    why: "A comment from me could affect a process that is still running.",
  },
  review_decisions: {
    lead: "I don't comment on prior-review decisions, bid evaluation reports or procurement complaints.",
    instead: "I can show the package's published notices and contract awards, with their dates.",
    why: "The borrower and the World Bank make those decisions under the Procurement Regulations.",
  },
  estimates_for_decisions: {
    lead: "I don't give time estimates for deciding an award or a review.",
    instead: "I can give a time estimate to help you plan the package's dates.",
    why: "A time estimate comes from past packages. It says nothing about any one bidder or any one review.",
  },
  dividing_packages: {
    lead: "I don't suggest dividing a package to stay under a review threshold.",
    instead: "I can show the review type for the whole package and the threshold it comes from.",
    why: "The review thresholds are there so that large packages get prior review. Dividing a package to get under them would undo that.",
  },
  rule_breach_findings: {
    lead: "I don't say whether a contract was procured against the World Bank's rules, because only the World Bank makes that formal finding.",
    instead: "I can show the contract's records and any published report that mentions it.",
    why: "That finding needs evidence that the public records don't hold, and the World Bank reaches it through its own process.",
  },
  personal_details: {
    lead: "I don't show the names of individual consultants or the contact details in notices.",
    instead: "I can show the contract's reference, method, amount and dates, and the supplier's name when the supplier is a firm.",
    why: "These details are about private people. I remove contact details from notices when I first read them.",
  },
  wrong_edition: {
    lead: "I don't quote the Procurement Regulations from an edition that did not apply to the package.",
    // The brief's "I have the {edition_name} in my sources" would be untrue: config/editions.toml holds no
    // edition of the Regulations yet (ticket 29), so this says what I can do with the documents I hold.
    instead: "I can quote the rules a project's appraisal document says it followed, word for word, with its page.",
    why: "The rules differ between editions, so a quote from the wrong one could mislead you.",
  },
  private_uploads: {
    lead:
      "I don't show a borrower's uploaded Procurement Plan or Project Procurement Strategy for Development (PPSD) to anyone outside the team that uploaded it.",
    // Ticket 38: uploads are plan checks, which Packages lists (the 38 brief, 5.11); the lead and why stay word for word.
    instead: "If the upload belongs to your team, you can open it from Packages.",
    why: "An upload is a private draft. Only the team that uploaded it can open it.",
  },
};

// Suggested risk rows for a PPSD (ticket 36), which World Bank staff draft for the borrower; ticket 38's agency
// variant (copy.draft.kinds.ppsd_rows_agency) keeps every key and swaps the words that name who the rows are for.
const PPSD_ROWS = {
    title: "Suggested risk rows for the borrower's PPSD",
    crumb: (_date: string) => "Suggested PPSD risk rows",
    rowTitle: (title: string, _date: string) => `Suggested PPSD risk rows for ${title}`,
    pageTitle: (title: string, _date: string) => `Suggested PPSD risk rows for ${title}`,
    // Under the h1: "Rural roads. No STEP reference yet." {reference} is the STEP reference in Roboto Mono.
    subtitle: "{title}. {reference}",
    lede: (count: number) =>
      count === 1 ? "I drafted a row for the one risk you selected." : "I drafted a row for each of the {count} risks you selected.",
    ledePartial: "I drafted rows for {written} of the {count} risks you selected.",
    // PPSD is spelled out here, once on the page (the 36 brief, section 5).
    method:
      "I wrote each Risk Description and Description of mitigation from {check} and their lessons, for the " +
      "borrower's Project Procurement Strategy for Development (PPSD). Open a source number to see its evidence " +
      "beside the row.",
    methodLink: "the risks you selected",
    countLine: (count: number, countText: string) => (count === 1 ? "Showing the one row" : `Showing all ${countText} rows`),
    columns: {} as Record<string, string>,
    tableCaption: (form: string, _date: string) =>
      `Suggested risk rows for the borrower's PPSD, ${form}, one row per risk you selected`,
    // A cell of Strata's that nothing passed the checks for; Word leaves it empty for the borrower.
    abstain: "I couldn't write this cell so that it passed my checks. The sentences I removed are listed above.",
    refused: {
      out_of_scope: "I didn't write this cell, because it would need more than this risk's records show.",
    } as Record<string, string>,
    refusedOther: "I didn't write this cell.",
    metaYou: (date: string) => `I drafted these rows for you on ${date}.`,
    metaTeammate: (author: string, date: string) => `I drafted these rows for ${author} on ${date}.`,
    barLead: "A working draft of suggested rows for the borrower's PPSD.",
    barLeadTeammate: (author: string) => `A working draft of ${author}'s suggested rows for the borrower's PPSD.`,
    holdNotChecked: "Mark the rows as checked before you export them.",
    // The composed hold line's first clause, and its frame (section 4.5).
    holdClause: "mark the rows as checked",
    holdCompose: "Before you export them, {clauses}.",
    readOnly: (author: string) => `Only ${author} can set owners, mark these rows as checked or export them.`,
    markedChecked: "You marked these rows as checked.",
    discarded: "You discarded these suggested rows, so your team no longer sees them in Drafts.",
    removedReasons: {
      id_not_returned: {
        item: "It cited a source other than this risk's records.",
        joined: "it cited a source other than this risk's records",
      },
    } as Record<string, { item: string; joined: string }>,
    rowNotes: (count: number, countText: string) => (count === 1 ? "One row." : `${countText} rows.`),
    steps: {
      read: {
        running: "I'm reading the risks you selected.",
        // {count} is the selected risks' count as a word from one to nine, then numerals.
        done: (count: string) =>
          count === "one" ? "I read the one risk you selected and its lesson." : `I read the ${count} risks you selected and their lessons.`,
      },
      write: {
        running: (_count: number, _countText: string) => "I'm writing a row for each risk.",
        // notes are the rows written.
        done: (_sentences: number, _sentencesText: string, rows: number, rowsText: string) =>
          rows === 1 ? "I wrote one row." : `I wrote ${rowsText} rows.`,
      },
      save: { running: "I'm saving the draft.", done: "I saved the draft." },
    },
    ready: (count: number, countText: string) =>
      count === 1 ? "The draft is ready. I wrote one row." : `The draft is ready. I wrote ${countText} rows.`,
    writeErrors: {
      no_agent: "I can't write PPSD rows yet, because the model that writes my drafts isn't connected. I saved nothing.",
      agent_unavailable:
        "I couldn't write the PPSD rows, because the model that writes my drafts did not respond. I saved nothing.",
      content_filter: "I couldn't write the PPSD rows, because a content filter stopped the writer. I saved nothing.",
      agent_output: "I wrote PPSD rows I couldn't check, so I saved nothing.",
      data_service: "I couldn't read the package's risks, because the data service didn't answer. I saved nothing.",
      draft_store: "I couldn't save the draft, because I can't write to my drafts tables right now. I saved nothing.",
      no_package: "I couldn't find this package, so I wrote nothing and saved nothing.",
      no_selected_risks: "None of the risks you selected is in the table now, so I wrote nothing and saved nothing.",
      no_plan: "I couldn't find this package, so I wrote nothing and saved nothing.",
      nothing_marked: "None of the risks you selected is in the table now, so I wrote nothing and saved nothing.",
      permission:
        "Your account can't read this package's records in Strata's tables, so I can't write PPSD rows. Ask your " +
        "workspace admin for read access to the strata catalog.",
      internal: "Something went wrong on my side, so I couldn't write the PPSD rows. I saved nothing.",
      dropped: "The connection dropped before I finished the PPSD rows. I saved nothing.",
    } as Record<string, string>,
    nothingTitle: "I couldn't write a row that passed my checks, so I saved no draft.",
    nothingBody: "The sentences I removed are below, with the reason for each.",
    previewPiuTitle: "I don't show these suggested rows in this preview, because they are a World Bank staff draft.",
    previewPiuBody: "Leave the preview to see them. Nothing about the draft changed.",
};

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
    // The Packages tab has its own words below (the 15 brief, packagesTab); this title names the browser tab.
    packages: {
      title: "Packages",
      purpose: "The packages you are planning and the plans you checked. Check a published plan, or plan a new package from one sentence.",
    },
    // The package workspace has its own words below (the 12 brief); this title names the browser tab.
    package: {
      title: "Package {id}",
      purpose: "This page shows how comparable packages went, so you can judge whether this package's plan is realistic.",
    },
    // A package planned from a sentence (the 15 brief): while I read the sentence, and once it is saved. Each
    // names itself in the browser tab with its title once it loads, such as "Rural roads, Kenya · Packages".
    packageNew: {
      title: "New package",
      purpose: "I'm reading your sentence as the criteria of a new package.",
    },
    plannedPackage: {
      title: "Package",
      purpose: "I read your sentence as the criteria below and compared them with past packages.",
    },
    // All projects, the project page and Check a plan have their own words below (the 10 brief):
    // these titles name the browser tab, and the purposes are the pages' own.
    projects: {
      title: "Projects",
      purpose:
        "Find a World Bank-financed project by its name, project ID or country. Open a project ID to see the " +
        "project's summary, Procurement Plans and documents.",
    },
    // Following (ticket 37): the Projects tab's first sub-tab for World Bank staff, at /projects/following.
    following: {
      title: "Projects",
      documentTitle: "Following, Projects",
      purpose: "Follow the projects you work on, or find any World Bank-financed project by its name, project ID or country.",
    },
    project: {
      title: "Project {pid}",
      purpose: "This page shows what I hold about one project. Each tab shows one part of it.",
    },
    checkPlan: {
      title: "Plan check, {pid}",
      // Once the check names the plan: "Northern Water Works Development Agency, plan of Oct 9, 2026".
      windowTitle: "{agency}, plan of {date}",
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
    // The source view (ticket 21) has its own words below; this title names the browser tab until the
    // document loads.
    document: {
      title: "Document",
      purpose: "This page opens one project document at the page and paragraph a citation points to.",
    },
    lessons: {
      title: "Lessons",
      purpose: LESSONS_PURPOSE,
      emptyTitle: "There are no lessons in the library yet.",
      emptyBody:
        "A lesson appears here after I read a completion report and a lead procurement specialist decides it belongs.",
      link: "Go to Data",
    },
    // Lessons > Waiting for review and one item's review page (ticket 29): the frame keeps the Lessons h1.
    lessonsQueue: {
      title: "Lessons",
      documentTitle: "Waiting for review, Lessons",
      purpose: LESSONS_PURPOSE,
    },
    lessonReview: {
      title: "Waiting for review",
      documentTitle: "Waiting for review, Lessons",
      purpose: "One lesson waiting for review, with its evidence, its history and your part in deciding it.",
    },
    // Lessons > Passage reports and Lessons > Judging (ticket 32): the frame keeps the Lessons h1, and one group's
    // page and one query's page name themselves once they load.
    lessonsReports: {
      title: "Lessons",
      documentTitle: "Passage reports, Lessons",
      purpose: LESSONS_PURPOSE,
    },
    passageReport: {
      title: "Passage reports",
      documentTitle: "Passage reports, Lessons",
      purpose: "One passage's reports, with the paragraph, what people reported and your decision.",
    },
    lessonsJudging: {
      title: "Lessons",
      documentTitle: "Judging, Lessons",
      purpose: LESSONS_PURPOSE,
    },
    judgingQuery: {
      title: "Judging",
      documentTitle: "Judging, Lessons",
      purpose: "One query of the labeled set, with each passage to grade on its own.",
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
    // An implementing agency officer's upload (ticket 38): Check my plan, and an upload's check, which names itself in
    // the browser tab once it loads. Both have their own words under copy.upload and copy.uploadCheck.
    checkMyPlan: {
      title: "Check my plan",
      purpose: "Upload the Procurement Plan you are preparing, and I check every activity in it before you submit it.",
    },
    uploadCheck: {
      title: "Your plan",
      purpose: "I checked every activity in the Procurement Plan your team uploaded.",
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
    // What the address asks for that the server could not apply (the 40 brief, 6.3). The banners for a view and a
    // date it did apply are under view.banner.
    viewUnknown: "I don't know the view in this link, so you are seeing the World Bank staff view.",
    viewUnknownOfficer: "I don't know the view in this link, so you are seeing your own view.",
    asOfUnreadable: "I can't read the date in this link, so you are seeing today's data.",
    asOfNotPast: "I can only show past dates, so you are seeing today's data.",
  },

  // The view switch (ticket 40; the 40 brief, section 6). {agency} is view.agencyInSentence's output.
  view: {
    agencyInSentence: (name: string, short: string | null) => (short ? `the ${name} (${short})` : `the ${name}`),
    // The {view_name} of earlier briefs' preview sentences.
    name: { piu: "implementing agency", public: "public" },
    banner: {
      piu: (agency: string) => `Preview of what an implementing agency officer at ${agency} sees. You are still signed in as yourself.`,
      public: "Preview of what the public sees. You are still signed in as yourself.",
      leave: "Leave the preview",
      previewRegion: "Preview",
      asOf: (date: string) => `I'm showing this page as of ${date}. I use only what was disclosed by that date.`,
      // Added after the as-of banner's sentence on the pages that keep today's state (the 35 and 38 briefs).
      drafts: "I show drafts as they are today, whatever the as-of date.",
      uploads: "I check uploads against today's records, whatever the as-of date.",
      back: "Back to today",
      asOfRegion: "Past date",
    },
    // Read with every page's h1, so a screen reader says the mode on each page; the page title adds it too.
    mode: {
      piu: "Implementing agency preview.",
      public: "Public preview.",
      asOf: (date: string) => `As of ${date}.`,
      piuAsOf: (date: string) => `Implementing agency preview, as of ${date}.`,
      publicAsOf: (date: string) => `Public preview, as of ${date}.`,
    },
    title: {
      piu: (title: string) => `${title} (implementing agency preview) | Strata`,
      public: (title: string) => `${title} (public preview) | Strata`,
      asOf: (title: string, date: string) => `${title} (as of ${date}) | Strata`,
      piuAsOf: (title: string, date: string) => `${title} (implementing agency preview, as of ${date}) | Strata`,
      publicAsOf: (title: string, date: string) => `${title} (public preview, as of ${date}) | Strata`,
    },
    status: {
      leftPreview: "You left the preview. You are seeing the World Bank staff view.",
      leftPreviewOfficer: "You left the preview. You are seeing your own view.",
      backToToday: "You are seeing today's data again.",
    },
    // A page the applied view does not show (the 40 brief, 6.4): its section's name as the h1, then this card,
    // unless its own brief wrote one.
    hidden: {
      title: (viewName: string) => `This page isn't part of the ${viewName} view.`,
      body: "Leave the preview to see it again. Nothing on the page changed.",
      link: "Go to Projects",
      packagesBody: "Members of the public see projects, lessons and data in Strata. Leave the preview to see Packages again.",
    },
    // The reason the server gives, and the held control shows, for an act whose screen no preview shows.
    actPreview: "This is a preview, so I don't record anything you do here.",
    // Home in the public view, until ticket 41 builds each view's Home (the 40 brief, 3.9 and 6.5).
    publicHome: {
      title: "Start from a project",
      purpose: "I link each World Bank-financed project to its Procurement Plans, contracts and evaluations, and I cite every claim to its source.",
      cardTitle: "I show the public projects, lessons and data.",
      cardBody:
        "Find a project by its name, project ID or country. For a closed project, I show each contract from its notice to its signing, with the reports that discussed it.",
      link: "Go to Projects",
    },
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
      // The pill names the view the server applies (the 40 brief, 3.2): each label fits the bar at 1024 px.
      pill: {
        staff: "View: World Bank staff",
        officer: "View: Agency officer",
        previewOfficer: "Preview: Agency officer",
        previewPublic: "Preview: Public",
      },
      dialog: "Your view",
      signedIn: (email: string) => `Signed in as ${email}`,
      identityError: "I can't tell which account you signed in with.",
      signedOut: "You are not signed in.",
      // The views the popover offers, as link rows (the 40 brief, 3.3). "See Strata as" keeps the ticket's words.
      group: "See Strata as",
      rows: {
        staff: { label: "World Bank staff", desc: "Your own view, with everything I show." },
        piu: {
          label: "Implementing agency officer",
          descPreview: (agency: string) => `A preview of what an officer at ${agency} sees.`,
          descOwn: (agency: string) => `Your own view, for ${agency}.`,
        },
        public: { label: "The public", desc: "A preview of what a member of the public sees. It has projects, lessons and data only." },
      },
      date: {
        label: "See Strata as of a past date",
        hint: "I show only what was disclosed by that date.",
        submit: "Show this date",
        errorEmpty: "Choose a date first.",
        errorNotPast: "Choose a date before today.",
      },
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
      askLanguage: (language: string) => `, for an answer in ${language}`,
      lookingUp: "Looking up {id}",
      // The plan-a-package intent (the 15 brief, section 7.1). It is never the default for free text.
      plan: "Plan a package from this sentence",
      planLine: "I'll read the criteria from your sentence and open a new package. You can change any of them.",
      planPreviewOff: "Planning a package is off in a preview.",
      // Check mode, opened by the Packages tab's "Check a plan": one option per agency's latest plan.
      checkPlan: (agency: string, date: string) => `Check the ${agency} plan of ${date}`,
      checkPlanLine: "{pcode}",
      noPlan: "I found no published Procurement Plan for {pcode}.",
    },
    // The two modes the Packages tab's buttons put the box in.
    mode: {
      planPlaceholder: "Describe the package in one sentence",
      planHelp: "Say what is being bought, where, and about how much. For example: rural roads, Kenya, about US$15 million.",
      checkPlaceholder: "Type a project ID, such as P156634",
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
    // Following (ticket 37): a project on which no check could run, an abstention in the first person.
    notChecked: "Not checked",
    dataNote: "Data note",
    partial: "Partial",
    gap: "Gap",
    // A disagreement card (ticket 24; DESIGN.md section 5): warning when keeping the other side would change
    // the answer, info otherwise.
    twoReportsDisagree: "Two reports disagree",
    sourcesDiffer: "Sources differ",
    // An estimate the blueprint labels experimental (ticket 28), always followed at once by why.
    experimental: "Experimental",
  },

  // The citation marker's accessible name, such as "Source 1: Implementation Completion and
  // Results Report, June 30, 2021, paragraph 54".
  citation: {
    name: (n: number, source: string, opened: boolean) => `Source ${n}: ${source}${opened ? ", opened" : ""}`,
  },

  // The check line (DESIGN.md section 5): neutral, and it says what was not checked.
  // Its parts are templates, {part} of {whole}, one form for a whole of one and one for more, so the
  // server writes the same line into a draft's evidence pack (src/strata/drafts/copy.json).
  // Three labeled parts, each on its own line (the 24 brief, section 4.1): what I matched against
  // records and pages, what a model judged (check 4), and what nobody checked.
  checkLine: {
    checked: "Checked:",
    judged: "Judged by a model:",
    notChecked: "Not checked:",
    judgedSentences: {
      one: "{part} of {whole} sentence follows from its sources",
      many: "{part} of {whole} sentences follow from their sources",
    },
    // Judged sentences that cite a source written in another language (ticket 42; the 42 brief, section 5.5).
    crossLanguage: {
      one: "It cites a source written in another language.",
      all: "All of them cite a source written in another language.",
      some: (count: string) => `${count.charAt(0).toUpperCase()}${count.slice(1)} of them cite a source written in another language.`,
    },
    // {count} is a word from one to nine, then numerals.
    provenOthers: {
      one: "The other one needed no model, because everything it stated matched a record or a page.",
      many: "The other {count} needed no model, because everything they stated matched a record or a page.",
    },
    // When no clause below applies.
    notCheckedFallback: "whether the sources themselves are right",
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
    // Keyed by what was not checked: "sentences" where the fourth check did not run (an answer or a draft
    // saved before ticket 24, or a lesson review, which runs checks 1 to 3), then the tools
    // (config/tools.toml), so a new tool adds one line, then a draft kind's writer (config/drafts.toml's
    // not_checked). A tool's clause applies when it ran, except get_lessons's, which applies when a
    // sentence on screen cites a lesson (config/tools.toml, not_checked_when = "cited").
    notCheckedClauses: {
      sentences: "whether each sentence follows from its sources",
      find_comparables: "whether these are the right comparables",
      search_passages: "whether I found every passage that matters",
      get_lessons: "whether these lessons apply here",
      ask_genie: "whether the records I looked up are the ones you meant",
      check_plan: "whether the plan's published records are complete",
      writer_review_notes: "whether these notes are what you would tell the borrower",
      // The mission brief (ticket 37): project_records' clause, then the writer's.
      project_records: "whether the project's published records are complete",
      project_signals: "whether the project's published records are complete",
      writer_mission_brief: "whether this brief covers what your mission needs",
      // Ticket 36: suggested PPSD rows and the Project Paper summary, and the agency's track record.
      writer_ppsd_rows: "whether these rows are what the borrower should put in the PPSD",
      agency_track_record: "whether the agency's past packages are like the ones in this plan",
      writer_project_paper: "whether this summary is what you would write in the Project Paper",
      // Ticket 38: an implementing agency's planned dates, then what an upload adds.
      writer_step_rows: "whether these comparable packages fit your activities",
      upload_dates: "whether the dates in your plan are the ones you meant",
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
    // Two is "both", never "all two".
    all: (count: number, countText: string) => (count === 2 ? "I removed both sentences." : `I removed all ${countText} sentences.`),
    itSaid: (sentence: string, reason: string) => `It said ${sentence}, and ${reason}.`,
    firstSaid: (sentence: string, reason: string) => `The first said ${sentence}, and ${reason}.`,
    // A removed sentence that gave advice is quoted whole after these words, in its own quote element as a list
    // item sets it (removed.quoted), then its reason as a list item gives it: advice is often an order, which
    // does not read as reported speech ("It said base your estimates...").
    itSaidQuoted: "It said",
    firstSaidQuoted: "The first said",
    others: "The others:",
    other: "The other:",
    // The sentence's own double quotes turn single inside the outer pair, so the marks never pile up.
    item: (sentence: string, reason: string) => `"${sentence.replace(/"([^"]*)"/g, "'$1'")}" ${reason}`,
    // The same sentence alone, for the removed box's list, which sets its reason beside it in another color.
    quoted: (sentence: string) => `"${sentence.replace(/"([^"]*)"/g, "'$1'")}"`,
    // A reason code with no sentence below: it makes no claim about why.
    unknownReason: { item: "It failed a check.", joined: "it failed a check" },
    // After the lead, when a service a check needs did not answer and some sentences survived (the 24 brief,
    // section 5.4), then "Try again". Said only when other sentences were removed for other reasons: when
    // every removed sentence has the same cause, the lead already says it.
    unjudged: (count: number, countText: string) =>
      count === 1
        ? "The model that judges sentences did not respond, so I couldn't check one of them."
        : `The model that judges sentences did not respond, so I couldn't check ${countText} of them.`,
    unasked: (count: number, countText: string) =>
      count === 1
        ? "I couldn't find out whether other reports disagree, so I couldn't check one of them."
        : `I couldn't find out whether other reports disagree, so I couldn't check ${countText} of them.`,
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
      // Ticket 24, the 24 brief's section 5.3: check 4, the judge said it does not follow from its sources.
      not_supported: {
        item: "The sources it cites do not say this.",
        joined: "the sources it cited do not say that",
      },
      // Check 4, when the model that judges sentences did not respond: never shown unchecked. underAlert is
      // the item under the error alert that already names the cause (the 24 brief, section 5.5).
      judge_unavailable: {
        item: "I couldn't check it, because the model that judges sentences did not respond.",
        joined: "I couldn't check it, because the model that judges sentences did not respond",
        underAlert: "I couldn't check it.",
      },
      // Check 5: advice with no lesson and no comparable among its sources.
      advice_without_lesson_or_comparable: {
        item: "It gave advice without citing a lesson or a comparable package.",
        joined: "it gave advice without citing a lesson or a comparable package",
      },
      // Check 6, when I couldn't ask which reports disagree about its project. The brief's "I couldn't load
      // the other side" would claim a disagreement I never saw, so this says what happened.
      disagreements_unavailable: {
        item: "I couldn't find out whether another report disagrees with its sources.",
        joined: "I couldn't find out whether another report disagrees with its sources",
        underAlert: "I couldn't check it.",
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
      get_disagreements: {
        running: (scope: string | null) =>
          scope ? `I'm checking where sources disagree about ${scope}.` : "I'm checking where sources disagree.",
        done: (count: number, countText: string, scope: string | null) =>
          count === 0
            ? `I found no sources that disagree${scope ? ` about ${scope}` : ""}.`
            : `I found ${countText} ${count === 1 ? "disagreement" : "disagreements"} between sources${scope ? ` about ${scope}` : ""}.`,
      },
    },
    otherTool: { running: (tool: string) => `I'm using ${tool}.`, done: (tool: string) => `I used ${tool}.` },
    write: {
      running: "I'm writing the answer.",
      done: (count: number, countText: string) =>
        count === 0 ? "I wrote no sentences." : `I wrote ${countText} ${count === 1 ? "sentence" : "sentences"}.`,
      // A full refusal's write step: it wrote no sentence because it turned the request down (ticket 24).
      refused: "I turned the request down.",
      // A step still to come, listed in ink-muted so the block keeps its height (02's round 7 critique).
      todo: "To do: write the answer.",
    },
    // The verifier's step, with its six checks under it once it is done (the 24 brief, section 5.1). Its
    // counts are over every sentence the agent wrote.
    check: {
      running: "I'm checking each sentence against its sources.",
      done: "I checked each sentence against its sources.",
      doneSix: (written: number, writtenText: string, removed: number, removedText: string) =>
        `I ran six checks on the ${written === 1 ? "one sentence" : `${writtenText} sentences`} I wrote and removed ${
          removed === 0 ? "none" : removed === 1 ? "one" : removedText
        }.`,
      todo: "To do: check each sentence against its sources.",
      // The verifier's own steps inside it, each said once while it runs; they fold into its done line.
      judge: (count: number, countText: string) =>
        count === 1
          ? "I'm asking a model whether one sentence follows from its sources."
          : `I'm asking a model whether ${countText} sentences follow from their sources.`,
      disagreement: "I'm getting the other side of a disagreement.",
      // The six checks, in order. "N of M" pairs use numerals; a count alone is a word from one to nine.
      six: {
        numbers: (matched: number, total: number) =>
          total === 0
            ? "None of the sentences stated a number or a date."
            : total === 1
              ? `${matched} of 1 number or date matched a record or a quote.`
              : `${matched} of ${total} numbers and dates matched a record or a quote.`,
        sources: (returned: number, total: number) =>
          total === 1
            ? `${returned} of 1 source I cited came back for this question.`
            : `${returned} of ${total} sources I cited came back for this question.`,
        quotes: (found: number, total: number) =>
          total === 0
            ? "None of the sentences quoted a source."
            : total === 1
              ? `${found} of 1 quote was word for word on its page.`
              : `${found} of ${total} quotes were word for word on their pages.`,
        judged: (judged: number, judgedText: string, followed: number) =>
          judged === 1
            ? `A model judged one sentence, and ${followed} of 1 followed from its sources.`
            : `A model judged ${judgedText} sentences, and ${followed} of ${judged} followed from their sources.`,
        proven: (count: number, countText: string) =>
          count === 1
            ? "The other one needed no model, because everything it stated matched a record or a page."
            : `The other ${countText} needed no model, because everything they stated matched a record or a page.`,
        // When no model was asked: every sentence I kept was proven by checks 1 to 3, since each other sentence
        // that stood went to the judge, and a sentence the earlier checks removed is never counted here.
        notJudged: (kept: number, keptText: string) =>
          kept === 0
            ? "No sentence was left for a model to judge."
            : kept === 1
              ? "The sentence I kept needed no model, because everything it stated matched a record or a page."
              : `The ${keptText} sentences I kept needed no model, because everything they stated matched a record or a page.`,
        judgeSilent: (count: number, countText: string) =>
          count === 1
            ? "The model that judges sentences did not respond, so I removed the one sentence it had to judge."
            : `The model that judges sentences did not respond, so I removed the ${countText} sentences it had to judge.`,
        advice: (cited: number, total: number) =>
          total === 0
            ? "None of the sentences gave advice."
            : total === 1
              ? `${cited} of 1 sentence that gave advice cited a lesson or a comparable package.`
              : `${cited} of ${total} sentences that gave advice cited a lesson or a comparable package.`,
        // {Count} starts the sentence, so it is a capitalized word from one to nine.
        disputedBoth: (count: number, countText: string) =>
          count === 1
            ? "One sentence rested on a report that another report disagrees with, and my draft showed both sides."
            : `${countText} sentences rested on a report that another report disagrees with, and my draft showed both sides.`,
        disputedAdded: (count: number, countText: string) =>
          count === 1
            ? "One sentence rested on a report that another report disagrees with. My draft left out the other side, so I added it."
            : `${countText} sentences rested on a report that another report disagrees with. My draft left out the other side, so I added it.`,
        disputedNone: "No sentence rested on a report that another report disagrees with.",
      },
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
    // Ticket 24's announcements (the 24 brief, sections 5.4 and 5.8).
    readyUnjudged: (count: number, countText: string) =>
      count === 1
        ? "The answer is ready. I removed one sentence, because the model that judges it did not respond."
        : `The answer is ready. I removed ${countText} sentences, because the model that judges them did not respond.`,
    readyUnasked: (count: number, countText: string) =>
      count === 1
        ? "The answer is ready. I removed one sentence, because I couldn't find out whether another report disagrees with it."
        : `The answer is ready. I removed ${countText} sentences, because I couldn't find out whether other reports disagree with them.`,
    readyDisagree: (count: number, countText: string) =>
      count === 1
        ? "The answer is ready. Two reports disagree about one sentence, and I show both."
        : `The answer is ready. Two reports disagree about ${countText} sentences, and I show both sides of each.`,
    // Nothing survived because a service a check needs did not answer: an error, not an empty answer (section
    // 5.5). The model that judges sentences did not respond, check 6 could not ask which reports disagree, or both.
    failed: {
      judge: "I couldn't check my answer, because the model that judges sentences did not respond.",
      disagreements: "I couldn't check my answer, because I couldn't find out whether other reports disagree with its sources.",
      both: "I couldn't check my answer, because the model that judges sentences did not respond and I couldn't find out whether other reports disagree with its sources.",
    },
    // The same, when another sentence was checked and failed: the removed box gives each sentence its reason.
    failedSome: {
      judge: "I couldn't check all of my answer, because the model that judges sentences did not respond.",
      disagreements: "I couldn't check all of my answer, because I couldn't find out whether other reports disagree with its sources.",
      both: "I couldn't check all of my answer, because the model that judges sentences did not respond and I couldn't find out whether other reports disagree with its sources.",
    },
    tryAgain: "Try again",
    // The answer panel's header (the 14 brief, section 5.3). {id} shows in Roboto Mono.
    panel: "Answer",
    close: "Close the answer",
    askedWithin: "Asked within {id}",
    askedAcross: "Asked across all projects",
    askedAsOf: (date: string) => `, as of ${date}`,
    // The language the answer was written in, when it is not English or differs from your choice now (ticket 42).
    askedLanguage: (language: string) => `, for an answer in ${language}`,
    // Asks the same question again in your current choice of language.
    askAgain: (language: string) => `Ask again in ${language}`,
    // A preview the server applied names its view (ticket 40; the 40 brief, 6.6): the {view_name} of view.name.
    askedPreview: (viewName: string) => `, in a preview of the ${viewName} view`,
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
    // below, shown as plain text. The refusal list's own lines are refusals, below (ticket 24). The link
    // goes to How Strata works' "What I don't do".
    refusalNote: "{link} lists what I don't do, and why.",
    refusalLink: "How Strata works",
    // A partial refusal: after the refusal's lead, before the rest of the answer (the 24 brief, section 4.6).
    refusalPartial: "I answered the rest of your question.",
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

  refusals: REFUSALS,

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
    // What a PDF's private-use character, such as a Wingdings bullet, shows as: one character for one.
    privateGlyph: "\u2022",
    openAtPage: (page: string) => `Open at page ${page} in the World Bank's PDF`,
    // Ticket 21: the drawer's link opens the in-app source view at the page, in the same tab.
    openAtPageHere: (page: string) => `Open at page ${page}`,
    newTab: ", opens in a new tab",
    failed: "I couldn't load this source.",
    missing: "I have no source with this ID. The link may be incomplete.",
    // The server gives the same answer for a source not public by the address's as-of date.
    missingAsOf: (date: string) => `I have no source with this ID as of ${date}. It may not have been public yet, or the link may be incomplete.`,
  },

  // Languages by their ISO 639-1 codes, by their English names (ticket 18; brief 42 reuses these keys).
  language: {
    name: { en: "English", fr: "French", es: "Spanish", pt: "Portuguese" } as Record<string, string>,
    // The language of answers and drafts, in the view popover and at the foot of the Menu panel (ticket 42; the 42
    // brief, section 5.1). The screens stay in English: these name the languages the writer writes in.
    choice: {
      legend: "Language of answers and drafts",
      hint: "The screens stay in English. Quotes stay in the language their source was written in.",
      changed: (language: string) =>
        `From now on, I write answers and drafts in ${language}. Answers and drafts already written keep their language.`,
      fromLink: (link: string, saved: string) => `This link asks for ${link}, so I'm using it here. Your saved choice is ${saved}.`,
      fromTeam: (language: string) => `I started with ${language}, the working language set for your team.`,
      saveFailed: "I couldn't save your choice for next time, so I kept it in this page's link instead.",
      readFailed: (language: string) => `I couldn't read your saved choice, so I'm using ${language} for now.`,
    },
    // The page alert for a ?lang= value no working language matches (the 42 brief, section 5.2). It never repeats it.
    alertUnknown: (language: string) => `I can't write answers and drafts in the language this link asks for, so I'm using ${language}.`,
  },

  // The evidence card and the evidence drawer (the 14 brief, sections 5.11 to 5.13). Each source's
  // stratum and its document's short name come from the answer stream.
  evidence: {
    eyebrow: { What: "What · record", How: "How · operations", Why: "Why · evaluation" },
    // The heading names the source, not the claim, so a drawer opened from a link still reads.
    title: "{project}, paragraph {para}",
    titleSection: "{project}, section {section}",
    recordTitle: "{kind} {reference}",
    // A mission brief's records (ticket 37), named for what they are: the totals record by its project, an agency's
    // latest plan by the agency, and an ISR's rating by the ISR and the rating.
    totalsTitle: "Totals for {pid}",
    planVersionTitle: "Latest plan of {agency}",
    isrRatingTitle: "ISR {n}, {rating}",
    // What a record is called, by the table its evidence id names (web/src/lib/sources.ts).
    recordKinds: {
      "strata.silver.plan_rows": "Activity",
      "strata.gold.contract": "Contract",
      "strata.gold.package": "Package",
      "strata.ops.lesson_versions": "Lesson",
      // An award notice a rejected bid in section 5 cites (ticket 31).
      "strata.gold.notice": "Award notice",
    } as Record<string, string>,
    // A notice a package advertised again cites (ticket 28), by its type: an award notice or any other notice.
    noticeRecordKinds: { award: "Award notice", other: "Notice" },
    recordKindOther: "Record",
    // What a record the contract trail opens is called, by the kind its row names (ticket 22), since one table
    // holds every type of notice.
    recordKindsByKey: { notice: "Notice", award_notice: "Award notice", contract: "Contract", activity: "Activity" } as Record<string, string>,
    // "Open the activity" on a notice, award notice, contract or plan row whose activity Strata holds (ticket 22).
    openActivity: "Open the activity",
    openActivityFor: (ref: string) => ` ${ref}`,
    // The records a project's Summary cites (ticket 21), by the table their evidence id names. The
    // project ID or loan number follows in Roboto Mono.
    summaryRecordKinds: {
      "strata.gold.project": "Project record",
      "strata.gold.loan": "Loan or credit",
      "strata.gold.project_closing_date": "Loan history of",
      "strata.gold.ieg_rating": "IEG ratings of",
      "strata.gold.project_isr_rating": "ISR rating of",
      "strata.silver.isr_ratings": "ISR rating of",
      "strata.ops.plan_baselines": "Baseline for",
    } as Record<string, string>,
    // Each Summary record's source line, by its source_key. {date} is the record's date.
    summaryRecordSources: {
      projects_api: "World Bank projects API, record of {date}.",
      loans: "World Bank loans and credits data, as of {date}.",
      loan_history: "World Bank monthly loan history, reported {date}.",
      ieg_ratings: "Independent Evaluation Group (IEG) ratings data, {date}.",
      // An award notice a rejected bid in section 5 cites (ticket 31).
      award_notices: "World Bank procurement notices, award notice published {date}.",
      // A notice and a contract the contract trail opens (ticket 22), and a notice a package advertised again
      // cites (ticket 28).
      notices: "World Bank procurement notices, notice published {date}.",
      awards: "World Bank contract awards data, since fiscal 2020, contract signed {date}.",
      awards_fy2001_2016: "World Bank contract awards data, fiscal 2001 to 2016, contract signed {date}.",
      projects_api_ratings: "World Bank projects API, ratings from the ISR of {date}.",
      isr_ratings: "The overall ratings table of the ISR of {date}, as I read it.",
      plan_baseline: "Strata's baseline, saved by World Bank staff on {date}.",
      // A mission brief's records (ticket 37). Its award records use awards above.
      plans: "Procurement Plan of {date}, from the World Bank documents API.",
    } as Record<string, string>,
    // The fields of a Summary record, by their key, as the projects API and the loans data name them.
    summaryRecordFields: {
      project_name: "Project name",
      country: "Country",
      status: "Status",
      approval_date: "Approval date",
      closing_date: "Closing date",
      previous_closing_date: "Closing date before",
      reported_on: "Reported",
      region: "Region",
      implementing_agency: "Implementing agency",
      original_principal_usd: "Original principal (US$)",
      disbursed_usd: "Disbursed (US$)",
      cancelled_usd: "Canceled (US$)",
      snapshot: "As of",
      evaluation_type: "Evaluation",
      evaluation_fy: "Fiscal year",
      outcome: "Outcome",
      bank_performance: "Bank performance",
      rating_name: "Rating",
      value: "Value",
      current_rating: "Rating in this ISR",
      previous_rating: "Rating in the ISR before",
      sequence: "ISR number",
      pdf_page: "PDF page",
      isr_date: "ISR date",
      esf_risk: "Environmental and social risk",
      ea_category: "Environmental Assessment Category",
      sector_name: "Sector, as Strata groups it",
      sector_share: "Sector and share",
      total_commitment_usd: "Total commitment (US$)",
      plan_date: "Plan date",
      saved_on: "Saved on",
      // An award notice's fields, as the notice names them, for a rejected bid in section 5 (ticket 31). It
      // never lists a bidder.
      notice_type: "Notice type",
      published: "Published",
      bid_reference: "Bid/Contract Reference No",
      project_id: "Project",
      reason_for_rejection: "Reason for Rejection",
      bids_rejected: "Bids rejected for this reason",
      // The records a mission brief cites (ticket 37; project_records).
      activities: "Activities",
      needs_a_look: "Need a look",
      watch: "Worth watching",
      step_reference: "STEP reference",
      signed_on: "Signed",
      individual_consultant: "Individual consultant",
      signed_amount_usd: "Signed amount (US$)",
      signed_amount: "Signed amount",
      currency: "Currency",
      estimated_amount_usd: "Estimated Amount (US$)",
      undisbursed_usd: "Undisbursed (US$)",
      original_principal_millions: "Original principal (US$, millions)",
      disbursed_millions: "Disbursed (US$, millions)",
      undisbursed_millions: "Undisbursed (US$, millions)",
      cancelled_millions: "Canceled (US$, millions)",
      loan_number: "Loan or credit",
      activity_reference_no: "Activity",
      planned_completion_on: "Planned completion",
      days_after_closing: "Days after closing",
      // The fields a plan signal adds to its plan row (ticket 37): the date as first published, and the amounts.
      planned_completion_plan_date: "Planned completion first published in the plan of",
      actual_amount_usd: "Actual Amount (US$)",
      first_plan_date: "First listed in the plan of",
      signed_millions: "Signed amount (US$, millions)",
      estimated_millions: "Estimated Amount (US$, millions)",
      // A notice and a contract the contract trail opens (ticket 22), under their sources' names. The mission
      // brief's records (ticket 37) use supplier and contract_description too.
      procurement_method: "Procurement Method",
      submission_deadline: "Submission Deadline",
      contract_signature_date: "Contract Signature Date",
      signed_contract_price: "Signed Contract Price",
      bid_description: "Description",
      contract_reference: "Contract Reference",
      signed: "Signed",
      supplier: "Supplier",
      supplier_country: "Supplier Country",
      contract_description: "Contract Description",
      // A notice and a plan row a package advertised again cites (ticket 28): the sentence that gives a reason,
      // and STEP's own field names for the plan row.
      notice_says: "The notice says",
      description: "Description",
      method: "Method",
      market_approach: "Market Approach",
      review_type: "Review Type",
      process_status: "Process Status",
    } as Record<string, string>,
    // A lesson in Strata's library, which an answer or the lesson review writer cites by version: the
    // drawer's eyebrow, its source line and the marker's name ("Source 2: Lesson, version 1, Put forest and
    // other permits in place before awarding contracts").
    lessonEyebrow: "What · lesson",
    lessonSource: "Strata's lesson library, version {version}, decided on {date}.",
    lessonSourceUndated: "Strata's lesson library, version {version}.",
    markerLesson: (version: string, statement: string) => `Lesson, version ${version}, ${statement}`,
    switcherLesson: (version: string) => `Lesson, version ${version}`,
    // The record view's fields keep STEP's own names; the description's is STEP's "Description".
    recordDescription: "Description",
    // The record view's source line, as the plan check writes a plan's: "Source: Procurement Plan,
    // Northern Water Works Development Agency, P156634, version of October 9, 2026, page 3."
    // "page" and its number never part at a line end: a no-break space joins them (DESIGN.md section 7).
    recordSource: "{doc}, {agency}, {pid}, version of {date}, page\u00a0{page}.",
    recordSourceShort: "{doc}, {pid}, {date}.",
    // A tool's totals record, such as the mission brief's totals (ticket 37), as a footnote names it.
    toolSource: "Strata's totals of this project's records, as of {date}.",
    // Ticket 36: a passage a lesson rests on, the count of comparable completion reports, and a lesson version, as
    // the evidence pack and a Word footnote name them.
    passageSource: "{doc}, {pid}, {date}, {place}, page {page}.",
    passageParagraph: "paragraph {para}",
    passageSection: "section {section}",
    countsSource: "Strata's count of comparable completion reports, as of {date}.",
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
    // Follows the line under a passage not written in your language of answers and drafts (ticket 42). No source is
    // ever translated.
    ownLanguage: "I quote sources only in the language they were written in.",
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
    // A comparable package opened from the range chart (the 15 brief, section 7.8). Its eyebrow is the What
    // stratum's, as for any record.
    package: {
      region: (ref: string) => `Records for comparable package ${ref}`,
      eyebrow: "What · record",
      meta: "{project} ({pcode})",
      findingSigned: "This package took {months} months from its notice on {notice} to its signed contract on {signed}.",
      // A still-open package's months run to the page's as-of date ({counted}), which can be later than the
      // records' last date ({through}), so the sentence names both (design review round 2, F2).
      findingOpen:
        "I count this package as still open after {months} months, from its notice on {notice} to {counted}. The records I hold run through {through} and show no signed contract.",
      findingCanceled: "This package was canceled before a contract was signed, so I left it out of the comparables.",
      whyHeading: "Why I compared it",
      why: {
        method: "Method",
        category: "Procurement Category",
        marketApproach: "Market Approach",
        reviewType: "Review Type",
        country: "Country",
      },
      recordEyebrow: "What",
      noticeTitle: "Specific procurement notice",
      contractTitle: "Contract award",
      awardNoticeTitle: "Contract award notice",
      fields: {
        noticeType: "Notice Type",
        published: "Published Date",
        bidReference: "Bid Reference No",
        description: "Bid Description",
        method: "Procurement Method",
        deadline: "Submission Deadline Date",
        contractNumber: "WB Contract No",
        contractDescription: "Contract Description",
        reviewType: "Review Type",
        signed: "Contract Signing Date",
        amount: "Contract Amount (US$)",
        signature: "Contract Signature Date",
        price: "Signed Contract Price",
      },
      price: (amount: string, currency: string) => `${amount} ${currency}`,
      noticeSource: "Procurement notice {id}, published {date}. {dataset}",
      contractSource: "Contract award {id}, signed {date}. {dataset}",
      dataset: (name: string, origin: string, license: string) => `The World Bank: ${name}: ${origin}. License: ${license}.`,
      openNotice: "Open the notice on worldbank.org",
      noContract: "No contract award in the records through {date}.",
      projectLink: "Open the project page",
      close: "Close the records",
      error: "I couldn't load this package's records just now. Try again in a moment.",
      // A quantile dot's packages (the 15 brief, section 7.8): the drawer lists the packages the dot stands
      // for, as find_comparables names them, and each opens its records, with a way back to the list.
      dot: {
        eyebrow: "What",
        region: (count: string, k: string) => `The ${count} comparable packages dot ${k} stands for`,
        regionOne: (k: string) => `The one comparable package dot ${k} stands for`,
        title: (count: string) => `${count} comparable packages`,
        titleOne: "One comparable package",
        sentence: (count: string, total: string, low: string, high: string) =>
          `This dot stands for ${count} of ${total} comparable packages, the ones that took ${low} to ${high} months.`,
        sentenceSame: (count: string, total: string, months: string) =>
          `This dot stands for ${count} of ${total} comparable packages, the ones that took ${months} months.`,
        sentenceOpen: (count: string, total: string, low: string, high: string) =>
          `This dot stands for ${count} of ${total} comparable packages, the ones signed or still open ${low} to ${high} months after their notices.`,
        sentenceOne: (total: string, months: string) => `This dot stands for one of ${total} comparable packages, which took ${months} months.`,
        sentenceOneOpen: (total: string, months: string) =>
          `This dot stands for one of ${total} comparable packages, which was still open after ${months} months.`,
        signed: (months: string) => `${months} months`,
        open: (months: string) => `Still open after ${months} months`,
        back: (count: string) => `Back to the ${count} packages`,
        backOne: "Back to the dot's package",
        close: "Close the list",
      },
    },
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

  // The words a disagreement card writes from what get_disagreements returns (ticket 20; the 23 brief,
  // section 7.5). The tool returns ids and values, never a sentence, as check_plan returns reason codes.
  // Templates whose {slots} the card fills: {lean} and {other} are the two sides' short names.
  disagreement: {
    // One sentence per rule id in config/evidence_ladder.toml, rules and ties alike. Reordering the
    // ladder changes which id comes back, not these words. A test fails when an id lacks its sentence.
    rule: {
      // Brief 23's words, changed in ticket 20's review (round 2, P3): a tie is between two records as often
      // as two reports, the other side of an outcome judgment can itself be written after closing, and
      // GLOSSARY.md avoids "fact" for an assertion. Ticket 23's design review made it one sentence that says why the
      // other report stays: under this rule it is always the earlier one, the ICR as much as an ISR.
      outcome:
        "For a judgment of how a project went, I lean on the later, more independent report, here {lean}, and I keep {other} as the record of the earlier view.",
      moment: "For something that happened at one moment, I lean on the record made at that moment, here {lean}.",
      tieSpecific: "The two sources rank the same, so I lean on the more specific one, {lean}.",
      tieRecent: "The two sources rank the same and are equally specific, so I lean on the more recent one, {lean}.",
    },
    // The card in an answer (ticket 24; the 24 brief, section 4.4). Each side's meta line names its source
    // in full, as the first place a reader may meet ISR or ICR on the screen does (DESIGN.md section 7,
    // rule 10), then its date and when it was written, from written below. {source}, {date} and {written}.
    meta: "{source}, {date}. {written}.",
    // The source in full: "Implementation Status and Results Report (ISR) 7", "Implementation Completion
    // and Results Report (ICR), paragraph 78". The short names fill {lean} and {other} in the rule.
    sourceFull: (documentType: string, short: string | null, sequence: number | null, paragraph: string | null) =>
      `${documentType}${short ? ` (${short})` : ""}${sequence ? ` ${sequence}` : ""}${paragraph ? `, paragraph ${paragraph}` : ""}`,
    sourceShort: (short: string, sequence: number | null, paragraph: string | null) =>
      `${short}${sequence ? ` ${sequence}` : ""}${paragraph ? ` paragraph ${paragraph}` : ""}`,
    lean: "Strata leans on this",
    // A report's abbreviation by its kind (config/project_page.toml's document groups), for its short name.
    shortType: {
      pad: "PAD",
      isr: "ISR",
      icr: "ICR",
      icr_review: "ICR Review",
      ppar: "PPAR",
      record: "Record",
      other: "Report",
    } as Record<string, string>,
    // What a side said: a rating's field name as the report names it, then its value.
    rated: (field: string, value: string) => `${field}: ${value}`,
    // What you would treat as true if you kept the other side, from get_disagreements' if_you_keep.
    // The field name is quoted, as the report names it, so you can see where it ends.
    whatChanges: (other: string, field: string, value: string) => `If you keep ${other} instead, I treat "${field}" as ${value}.`,
    // The group's accessible name: "Two reports disagree: ISR 7 and ICR paragraph 78".
    groupName: (badge: string, first: string, second: string) => `${badge}: ${first} and ${second}`,
    // When a side's source was written, by its evidence tier (config/evidence_ladder.toml, [tiers]).
    written: {
      pad: "Written at appraisal",
      isr: "Written during the project",
      icr: "Written after the project closed",
      ieg: "Written by IEG after the project closed",
      record: "Recorded on this date",
    },
    // The card's full look and its keep action (ticket 23; the 23 brief, sections 5 and 7.5).
    card: {
      // What the two reports disagree about, by the evidence ladder's attribute, then the moment it is about.
      subject: {
        pdo_progress: "Progress towards the project development objective (PDO)",
        implementation_progress: "Overall implementation progress",
        overall_risk: "The overall risk rating",
        outcome: "The project's outcome",
        efficiency: "Efficiency",
        bank_performance: "The World Bank's performance",
        me_quality: "The quality of monitoring and evaluation",
        signed_on: "The date the contract was signed",
        signed_amount_usd: "The signed amount",
      } as Record<string, string>,
      subjectOther: "What the two reports rated",
      subjectAt: {
        mid_term_review: "{subject} at the mid-term review",
        appraisal: "{subject} at appraisal",
        whole_project: "{subject} over the whole project",
      } as Record<string, string>,
      meta: "{date}. {written}.",
      // A side's title on the timeline and in the drawer: "ISR 7", "ICR, paragraph 78".
      title: "{short}",
      titlePara: "{short}, paragraph {para}",
      // "Open ISR 7", "Open paragraph 78".
      open: "Open {side}",
      openPara: "paragraph {para}",
      rated: (months: number) =>
        months === 1 ? "Rated {months} month after the mid-term review of {date}." : "Rated {months} months after the mid-term review of {date}.",
      written: (months: number) =>
        months === 1 ? "Written {months} month after the mid-term review of {date}." : "Written {months} months after the mid-term review of {date}.",
      sides: "The two reports, in the order they were written",
      kept: "You kept this",
      // Appended to what changes, from the stream's changes_count.
      changesAnswer: (count: number) =>
        count === 0 ? "That changes nothing in this answer." : count === 1 ? "That changes {n} sentence in this answer." : "That changes {n} sentences in this answer.",
      changesDraft: (count: number) =>
        count === 0 ? "That changes nothing in this draft." : count === 1 ? "That changes {n} sentence in this draft." : "That changes {n} sentences in this draft.",
      keep: {
        line: "You can keep {other} instead, with a reason that goes into the evidence pack.",
        lineNoTarget: "You can keep {other} instead from an answer or draft that rests on these two reports.",
        button: "Keep {other} instead",
        label: "Why do you keep {other}?",
        // The row keeps the account's id, never a name or an email (strata.ops.disagreement_choices).
        helperAnswer: "I save your reason with your account and this answer, and it goes into the evidence pack. I don't change the answer.",
        helperDraft: "I save your reason with your account and this draft, and it goes into the evidence pack. I don't change the draft.",
        submit: "Keep {other}",
        cancel: "Cancel",
        saving: "Saving",
        empty: "Write a reason, so the evidence pack says why you kept {other}.",
        failed: "I couldn't save your reason just now. Your text is still here.",
        // Going back to Strata's choice did not save: the kept choice stands.
        backFailed: "I couldn't save that just now, so you still keep {other}.",
        retry: "Try again",
        kept: "You kept {other} on {date}. Your reason: \"{reason}\"",
        undo: "Go back to Strata's choice",
        preview: "This is a preview, so I don't record choices here.",
        saved: "Saved. You kept {other}, and your reason goes into the evidence pack.",
        // A warning card on a draft (ticket 36; the 36 brief, 5.6): the author keeps one report before export.
        lineDraft:
          "Choose which report this draft keeps before you export it. Keeping {other} needs a reason, which goes into the evidence pack.",
        lean: "Keep {lean}",
        keptLean: "You kept {lean} on {date}.",
        savedLean: "Saved. You kept {lean}.",
        wentBack: "Saved. You went back to Strata's choice. Your earlier reason stays in the record.",
      },
      loadFailed: "I couldn't load these two reports.",
    },
    // One phrase per reason code on get_disagreements' coverage line (config/tools.toml,
    // [tools.get_disagreements.result] reasons), as find_comparables words its own.
    reasons: {
      replaced_by_later_version: (count: number) =>
        count === 1
          ? "{count} disagreement rested on a document that a later version replaced"
          : "{count} disagreements rested on documents that later versions replaced",
      // These two count passages, not disagreements: the sides whose words the tool kept from the agent (ticket 64).
      prompt_shields_hit: (count: number) =>
        count === 1
          ? "{count} passage behind a side held a prompt attack that Prompt Shields found, so I left out its words"
          : "{count} passages behind the sides held a prompt attack that Prompt Shields found, so I left out their words",
      not_screened: (count: number) =>
        count === 1
          ? "{count} passage behind a side was never screened by Prompt Shields, so I left out its words"
          : "{count} passages behind the sides were never screened by Prompt Shields, so I left out their words",
    },
  },

  // Tables (DESIGN.md section 5): a title sentence, a count line and a source line.
  // The title, count and source lines show only with the rows. While the rows load, skeleton
  // lines hold their places; an empty or failed table shows only its own card or alert.
  table: {
    // A fact table's units after a stacked row's label below 768 px, where the column heads are hidden:
    // "Commitment (US$, millions)".
    stackedUnit: " ({unit})",
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
    nounOne: "project",
    loading: "Loading projects.",
    // While a search waits more than 400 ms for its answer, in the count line's place.
    searching: "Searching projects.",
    columns: { project: "Project", country: "Country", status: "Status" },
    search: { label: "Search projects", hint: "Type part of a project's name, its project ID or its country." },
    pages: "Pages of the project list",
    noMatchTitle: "I found no projects that match your search.",
    noMatchBody:
      "I search project names, project IDs and country names. Check the spelling, or search for the country by the " +
      "name the World Bank uses, such as Türkiye.",
    noMatchLink: "Show all projects",
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

  // Your agency's projects, at the top of /projects in the implementing agency view (ticket 40; the 40 brief, 6.5).
  // {agency} is view.agencyInSentence's output; the finding is copy.checkPlan.finding's, from check_plan's counts.
  projectsAgency: {
    heading: "Your agency's projects",
    lead: (agency: string) =>
      `These are the projects where ${agency} has a disclosed Procurement Plan. I checked the latest plan for each one.`,
    none: (agency: string) => `The World Bank hasn't disclosed a Procurement Plan from ${agency} yet.`,
    item: (date: string) => `Procurement Plan of ${date}`,
    caption: "{name} ({pid}).",
    source: (agency: string) => `Procurement Plans that the World Bank disclosed for ${agency}. Marks from Strata's fixed checks.`,
    sourceAsOf: (agency: string, date: string) =>
      `Procurement Plans that the World Bank disclosed for ${agency}. Records as of ${date}.`,
    loading: "Loading your agency's plans.",
    error: "I couldn't load your agency's plans because the data service didn't answer.",
  },

  // The Projects sub-tabs (ticket 37; the 37 brief, section 9.1), shown only to World Bank staff.
  projectsTabs: {
    label: "Projects pages",
    // No count, so the label is the same on both pages and never grows while the list loads.
    following: "Following",
    all: "All projects",
    announce: (name: string) => `Showing ${name}.`,
  },

  // Following (ticket 37; the 37 brief, sections 3 to 5 and 9.2 to 9.9). {braces} are filled from the route.
  following: {
    heading: "Projects you follow",
    finding: "You follow {total} projects. {parts}.",
    // The finding's parts, in this order, leaving out zero counts; joined with commas and ", and".
    parts: {
      look: (n: number, word: string) => (n === 1 ? `${word} needs a look` : `${word} need a look`),
      watch: (n: number, word: string) => (n === 1 ? `${word} is worth watching` : `${word} are worth watching`),
      none: (n: number, word: string) => (n === 1 ? `${word} has no signals` : `${word} have no signals`),
      closed: (n: number, word: string) => (n === 1 ? `${word} has closed` : `${word} have closed`),
      pipeline: (n: number, word: string) => (n === 1 ? `${word} is in the pipeline` : `${word} are in the pipeline`),
      notChecked: (_n: number, word: string) => `I couldn't check ${word}`,
    },
    partsJoin: ", ",
    partsLast: ", and ",
    partsTwo: " and ",
    allQuiet: "You follow {total} projects, and none has a signal.",
    one: {
      needs_a_look: "You follow one project, and it needs a look.",
      watch: "You follow one project, and it is worth watching.",
      no_signals: "You follow one project, and it has no signals.",
      not_checked: "You follow one project, and I couldn't check it.",
      closed: "You follow one project, and it has closed.",
      pipeline: "You follow one project, and it is in the pipeline.",
      dropped: "You follow one project, and it has closed.",
    } as Record<string, string>,
    madeBy: "I ran these {checks} checks on {checked}, on public records through {through}. No model wrote this list.",
    madeByUndated: "I ran these {checks} checks on {checked}, on public records. No model wrote this list.",
    madeByAsOf: "I ran these {checks} checks as they would have run on {date}, on records public by then. No model wrote this list.",
    coverage: "I ran every check on {k} of {n} projects. On the other {m}, I lacked some records, and each row says which.",
    // When no project I checked had every check run.
    coverageNone: "I couldn't run every check on any project I checked. Each row says which records I lacked.",
    coverageLink: "See which records I hold",
    countLine: (shown: number, total: number) => `Showing ${shown} of ${total} projects you follow`,
    tableCaption: "Projects you follow, with their status, signals and next step",
    cols: {
      status: { label: "Status", def: (word: string) => `needs a look means ${word} signals or one strong one; a signal is a reason to look, not a finding` },
      project: { label: "Project", def: "with its country, project ID and closing date" },
      signals: { label: "Signals", def: "fixed checks on public records, one line each, strong signals first" },
      next: { label: "Next", def: "the brief waits in Drafts for you to check; I send nothing", defAsOf: "I draft mission briefs only from today's records" },
    },
    // The label and its definition, joined by a visually hidden ": " in a header cell, and as one sentence above the list.
    headerJoin: ": ",
    defEnd: ".",
    statusDefinition: {
      title: "Status",
      // Each status and its rule, one line each, so the rule scans.
      rules: (look: string, checks: string): [string, string][] => [
        ["Needs a look", `${look.charAt(0).toUpperCase()}${look.slice(1)} or more signals, or one strong signal.`],
        ["Watch", `At least one signal but fewer than ${look}, and none of them strong.`],
        ["No signals", `None of the ${checks} checks found anything.`],
        ["Not checked", "I couldn't run any check, because I don't hold the records."],
      ],
      signalIs: "A signal is a fixed check on public records that gives a reason to look, never a finding.",
      // No check is strong by itself; {names} each turn strong from {n} activities (the thresholds file's strong_from).
      strongNone: (names: string, n: string) =>
        `No check is strong on its own. ${names} each become strong when they fire on ${n} activities or more.`,
      strongNoneMixed: "No check is strong on its own. The table under How I check the projects you follow says when each one becomes strong.",
      strong: (names: string) => `The strong signals are ${names}.`,
      link: "How I check the projects you follow",
    },
    badge: { needs_a_look: "Needs a look", watch: "Watch", no_signals: "No signals", not_checked: "Not checked" } as Record<string, string>,
    signalCount: (n: number) => (n === 1 ? "1 signal" : `${n} signals`),
    strongTag: "Strong signal",
    meta: {
      closes: "{country}, {pid}. It closes on {date}.",
      past_closing: "{country}, {pid}. Its closing date was {date}.",
      closed: "{country}, {pid}. It closed on {date}.",
      dropped: "{country}, {pid}. It closed on {date}.",
      pipeline: "{country}, {pid}. It is in the pipeline.",
      undated: "{country}, {pid}.",
    } as Record<string, string>,
    signalsLabel: (name: string) => `Signals for ${name}`,
    partial: "I couldn't run {k} of the {n} checks, because {reasons}.",
    missing: {
      no_plans: "I haven't read its Procurement Plans",
      no_recent_plans: "no implementing agency has published a Procurement Plan for it in the last {months} months",
      no_loan_history: "I don't hold its loan history",
      no_isr: "I haven't read an ISR for it",
      no_loans: "I don't hold its disbursement records",
    } as Record<string, string>,
    missingJoin: " and ",
    notCheckedSignals: "I couldn't run any of the {checks} checks, because I don't hold this project's plans, loan history, ISRs or disbursement records yet.",
    notCheckedNext: "I need its records before I can draft a mission brief.",
    noneSignals: "None of the {checks} checks found anything.",
    noneSignalsPartial: "None of the {ran} checks I could run found anything.",
    closedSignals: "The project closed on {date}, so I no longer run the checks on it.",
    pipelineSignals: "The project is in the pipeline, so I don't run the checks on it yet.",
    closedNext: "I draft mission briefs only for active projects.",
    status: { closed: "Closed", dropped: "Closed", pipeline: "Pipeline" } as Record<string, string>,
    fold: (n: number, word: string) => (n === 1 ? "One project has no signals." : `${word} projects have no signals.`),
    // The closed and pipeline projects in the fold, each counted: "One has closed, and one is in the pipeline." alone:
    // whether the sentence opens the fold ("Two projects have closed."). The words come capitalised as they lead.
    foldEnded: (alone: boolean, closed: number, closedWord: string, pipeline: number, pipelineWord: string) => {
      const who = (n: number, word: string) => (alone ? (n === 1 ? "One project" : `${word} projects`) : word);
      const parts: string[] = [];
      if (closed > 0) parts.push(`${who(closed, closedWord)} ${closed === 1 ? "has" : "have"} closed`);
      if (pipeline > 0) parts.push(`${parts.length ? pipelineWord : who(pipeline, pipelineWord)} ${pipeline === 1 ? "is" : "are"} in the pipeline`);
      return `${parts.join(", and ")}.`;
    },
    foldPartial: (n: number, word: string) =>
      n === 1 ? "I couldn't run every check on one of the projects with no signals." : `I couldn't run every check on ${word} of the projects with no signals.`,
    show: (n: number) => (n === 1 ? "Show it" : "Show them"),
    hide: (n: number) => (n === 1 ? "Hide it" : "Hide them"),
    add: "Add to mission brief",
    // The button's name, with its row's project after the visible label (WCAG 2.5.3).
    addLabel: (name: string) => `Add to mission brief, ${name}`,
    existing: "You started one on {date}.",
    existingLink: "Open the draft",
    source: "Procurement Plans, contract awards, loan history, ISRs and disbursement records from World Bank APIs, through {date}.",
    sourceUndated: "Procurement Plans, contract awards, loan history, ISRs and disbursement records from World Bank APIs.",
    loading: "Loading the projects you follow.",
    emptyTitle: "I have no projects to check for you yet.",
    emptyBody: "Open a project and choose Follow this project. I check the projects you follow every night and list them here with their signals.",
    emptyLink: "Go to All projects",
    error: "I couldn't load the projects you follow because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show the projects you follow. Ask your workspace admin for read access to the strata catalog.",
    notStaffTitle: "I show Following only to World Bank staff.",
    notStaffBody: "Your account is not in the World Bank staff group, so I can't show signals on projects. You can still find any project in All projects.",
    notStaffLink: "Go to All projects",
    previewPiuTitle: "I don't show Following in this preview, because it is for World Bank staff.",
    previewPiuBody: "Leave the preview to see the projects you follow. Nothing about them changed.",
    previewPublicTitle: "The public view has no Following list.",
    previewPublicBody:
      "I don't show signals on active projects in the public view, so a procurement still under way isn't prejudged. Leave the preview to see the projects you follow.",
    stopped: "I stopped writing the mission brief and saved nothing.",
  },

  // Each signal's line (the 37 brief, section 9.3), filled with the tool's values. {ref} is a STEP reference in
  // mono, and the numbers marked in the brief are Nums.
  signals: {
    line: {
      completion_passed: {
        one: "{ref} passed its planned completion ({date}) with no signed contract.",
        many: "{n} activities passed their planned completion with no signed contract.",
      },
      above_estimate: {
        one: "{ref} was signed at about {ratio} times its estimate.",
        many: "{n} contracts were signed at {min} times their estimates or more, up to about {max} times.",
      },
      late_direct: {
        one: "{ref}, a US${amount} million direct-selection {category} activity, first appears in the {date} plan.",
        many: "{n} direct-selection activities, worth US${amount} million together, first appear late in the plans.",
      },
      closing_moves: {
        one: "The closing date has moved once since {year}.",
        many: "The closing date has moved {n} times since {year}.",
      },
      restructured: {
        one: "The project was restructured on {date}.",
        many: "The project was restructured {n} times since {year}, most recently on {date}.",
      },
      isr_lowered: {
        pdo: "The ISR dated {date} rated progress towards the development objective {to}, down from {from}.",
        implementation: "The ISR dated {date} rated overall implementation progress {to}, down from {from}.",
      },
      disbursement: {
        one: "By {date}, {pct} percent of the money committed and not canceled was disbursed, with {months} months left before closing.",
      },
    },
    // A plan's section, as the late direct selection line names its category.
    category: {
      WORKS: "works",
      GOODS: "goods",
      "NON CONSULTING SERVICES": "non-consulting services",
      "CONSULTING FIRMS": "consulting services",
      "INDIVIDUAL CONSULTANTS": "consulting services",
    } as Record<string, string>,
    categoryOther: "procurement",
    // What a Num's popover says behind each derived number.
    num: {
      activities: "The activities, by STEP reference, with their planned completion:",
      activity: (ref: string, date: string) => `${ref}, planned to finish on ${date}`,
      ratio: (actual: string, estimate: string, exact: string) =>
        `Signed amount: US$${actual}. Estimated Amount: US$${estimate}. Signed amount divided by estimate: ${exact}.`,
      contracts: "The contracts, by STEP reference, with their ratio:",
      contract: (ref: string, ratio: string) => `${ref}, ${ratio} times its estimate`,
      amount: (exact: string) => `Estimated Amount (US$): ${exact}, as the plan writes it.`,
      direct: "The activities, by STEP reference, with their amount and the plan that first lists them:",
      directItem: (ref: string, amount: string, date: string) => `${ref}, US$${amount}, first listed on ${date}`,
      moves: "Each move, by the month the loan history first showed it:",
      move: (month: string, from: string, to: string) => `First recorded ${month}: from ${from} to ${to}.`,
      restructurings: "Each restructuring the ISR lists, by its date:",
      restructuring: (level: string, date: string) => `Level ${level}, ${date}`,
      percent: (disbursed: string, available: string, exact: string) =>
        `Disbursed: US$${disbursed} million. Committed and not canceled: US$${available} million. Disbursed divided by that: ${exact} percent.`,
      months: (closing: string, asOf: string) => `From ${asOf} to the closing date, ${closing}, in whole months.`,
    },
    // The marker's name for each signal's source.
    source: {
      plans: "Procurement Plan of {date}",
      loan_history: "World Bank monthly loan history, reported {date}",
      isr: "The ISR of {date}",
      loans: "World Bank loans and credits data, as of {date}",
    } as Record<string, string>,
    // Each check's name and what sets it off, filled from the thresholds file (the 37 brief, section 9.5).
    check: {
      completion_passed: {
        name: "Planned completion passed",
        trigger: "An activity estimated at US${amount} million or more passed its planned completion date, as first published, and no contract was signed.",
      },
      above_estimate: { name: "Signed far above its estimate", trigger: "A contract was signed at {ratio} times its Estimated Amount or more." },
      late_direct: {
        name: "Direct selection added late",
        trigger: "A Direct Selection activity of US${amount} million or more first appears in a plan published {months} months or less before the closing date.",
      },
      closing_moves: { name: "Closing date moved", trigger: "The closing date moved {n} times or more." },
      restructured: { name: "Restructured", trigger: "The project had a level {levels} restructuring in the last {months} months." },
      isr_lowered: {
        name: "ISR rating lowered",
        trigger: "An ISR lowered the rating for progress towards the development objective or for overall implementation progress.",
      },
      disbursement: {
        name: "Slow disbursement",
        trigger: "Less than {pct} percent of the money committed and not canceled was disbursed, with {months} months or less left before closing.",
      },
    } as Record<string, { name: string; trigger: string }>,
    // Each check's name inside a sentence, after the first word.
    checkInSentence: (name: string) => name.charAt(0).toLowerCase() + name.slice(1),
  },

  // How I check the projects you follow, and the track record (the 37 brief, section 5 and 9.5).
  track: {
    heading: "How I check the projects you follow",
    method:
      "Every night I run {checks} fixed checks on public records: Procurement Plans, contract awards, the loan history, ISRs and " +
      "disbursement records. I measure delay from the planned date as first published. I don't combine the checks into a score. " +
      "Each signal is a reason to look, not a finding.",
    statusLead:
      "When I replayed these checks on past dates, {k_look} of the {n_look} projects that needed a look later extended their closing date. " +
      "So did {k_watch} of the {n_watch} worth watching, and {k_none} of the {n_none} with no signals.",
    why: "These counts say what happened next, not why.",
    fewLook: "Only {n} projects needed a look when I replayed the checks, too few to say how much the status usually means.",
    fewWatch: "Only {n} projects were worth watching when I replayed the checks, too few to say how much the status usually means.",
    none: "I haven't replayed these checks on past dates yet, so I can't say how often projects with signals later extended their closing date.",
    scope: "I replayed the checks as of {dates} on the projects I held then, and counted the projects that extended their closing date in the {window} months after each date.",
    source: "my replay of these checks, run on {date}.",
    num: (n: string, k: string, window: string, date: string) =>
      `Projects that had this status on at least one replay date: ${n}. Of them, projects whose closing date moved later within ${window} months: ${k}. Replay run: ${date}.`,
    show: (checks: string) => `Show the ${checks} checks`,
    hide: "Hide the checks",
    tableTitle: "Each check, what sets it off, and what happened next",
    cols: {
      check: "Check",
      trigger: "What sets it off",
      strong: "Strong signal",
      record: "Later extended their closing date",
      recordDef: "of the projects that had it",
      // The same head over a block's value on a phone.
      recordBlock: "Later extended their closing date, of the projects that had it",
    },
    cell: (k: string, n: string) => `${k} of ${n}`,
    few: "Too few projects to read as a rate.",
    notReplayed: "Not replayed yet",
    // A check no project had on any replay date: no count to show.
    never: "I haven't seen this signal in my replay yet.",
    yes: "Yes",
    no: "No",
    strongFrom: (n: string) => `From ${n} activities`,
    baseline: { name: "No signals", trigger: "None of the checks found anything." },
  },

  // Follow and unfollow in the project header (the 37 brief, section 6 and 9.6).
  projectFollow: {
    label: "Follow",
    button: "Follow this project",
    state: "You follow this project.",
    unfollow: "Unfollow",
    busy: "Saving",
    announceOn: (name: string) => `You follow ${name} now. It is in Following, under Projects.`,
    announceOff: (name: string) => `You no longer follow ${name}.`,
    failedOn: "I couldn't save that just now. You don't follow this project yet.",
    // When reading whether you follow the project failed: the state is unknown, so no button claims one.
    unread: "I couldn't check whether you follow this project just now.",
    retry: "Try again",
    failedOff: "I couldn't save that just now. You still follow this project.",
  },

  // The mission brief's page (the 37 brief, sections 7 and 9.7).
  mission: {
    parts: {
      plans: "Latest Procurement Plans",
      awards: "Awards since the last ISR",
      ratings: "Rating history",
      disbursement: "Disbursement",
      closing: "Closing check",
    } as Record<string, string>,
    tables: {
      plans: "The latest plan from each implementing agency",
      awards: "Contracts signed after the ISR dated {date}",
      ratings: "Ratings in each ISR I read",
      disbursement: "Disbursement by loan or credit, as of {date}",
      closing: "Activities planned to finish after the closing date",
      history: "Closing date history",
    } as Record<string, string>,
    cols: {
      plans: ["Implementing agency", "Latest plan", "Activities", "Need a look", "Worth watching"],
      awards: ["Activity", "Signed", "Supplier", "Signed amount (US$)", "Estimated Amount (US$)"],
      ratings: ["ISR", "Dated", "Progress towards achievement of PDO", "Overall implementation progress"],
      disbursement: ["Loan or credit", "Commitment (US$, millions)", "Disbursed (US$, millions)", "Undisbursed (US$, millions)", "Canceled (US$, millions)"],
      closing: ["Activity", "Implementing agency", "Planned completion", "Days after closing"],
      history: ["First recorded", "Closing date before", "Closing date after"],
    } as Record<string, string[]>,
    pdo: "PDO is the project development objective.",
    planVersion: "Plan of {date}",
    noPlan: "No plan read",
    individual: "Individual consultant",
    isr: "ISR {n}",
    notRated: "Not rated",
    total: "Total",
    moreAwards: (n: string) => `Show all ${n} contracts`,
    lessAwards: "Show fewer contracts",
    none: {
      no_plans: "I haven't read a Procurement Plan for this project, so this part has no plans to show.",
      no_isr: "I haven't read an ISR for this project, so I can't tell which contracts were signed after the last one.",
      no_awards: "No contract was signed after the ISR dated {date}.",
      no_loans: "I don't hold this project's loan records, so I can't show its disbursement.",
      closed: "The project closed on {date}, so I have no closing check to make.",
      no_closing_date: "I don't hold this project's closing date, so I have no closing check to make.",
    } as Record<string, string>,
    ratingsNone: "I haven't read an ISR for this project.",
    noneAfter: "No activity in the latest plans is planned to finish after the closing date.",
    allRemoved: "I removed every sentence I wrote for this part. They are in the removed box above, with the reason for each.",
    citedIn: "Cited in {parts}.",
    source: "Records from World Bank APIs, as of {date}.",
    writingParts: "The five parts I'm writing",
    reloadBody: "If you reloaded this page while I was writing, I stopped and saved nothing. Start again from Following.",
    backToFollowing: "Back to Following",
    // The draft's lede and method (the 37 brief, section 9.7).
    ledePartial: (written: string) => `I drafted ${written} of the five parts of the mission brief. Each other part says what I'm missing.`,
    method:
      "I wrote each part from public records through {date} and cited the record or paragraph behind every sentence. " +
      "Open a source number to see it beside the brief.",
  },

  // List search (the 21 brief, section 10): a list that filters on the server as you type.
  listSearch: {
    empty: "Empty the search box",
  },
  // Pagination (the 21 brief, section 10; built first by ticket 29): links that move a list a page at a
  // time, because they change the address. The source view's page links shorten on screen below 360 px,
  // and their names stay whole.
  pagination: {
    label: "Pages",
    previous: "Previous page",
    next: "Next page",
    previousShort: "Previous",
    nextShort: "Next",
    page: "Page {page} of {pages}",
  },

  // A project's page (the 10 and 21 briefs): the header's one line, the agency line and the tabs.
  projectPage: {
    label: { id: "Project ID", country: "Country", status: "Status", agency: "Implementing agency", agencies: "Implementing agencies" },
    // The h1's line: "{name} · {pid} · {country} · {status}". The dot and the item after it never part.
    dot: "· ",
    // The status inside the header's line, by the projects API's value. Tables keep the API's own word.
    statusInline: { Active: "active", Closed: "closed", Pipeline: "in the pipeline", Dropped: "dropped" } as Record<string, string>,
    agencyLine: "Implementing agency: {agencies}",
    agenciesLine: "Implementing agencies: {agencies}",
    noAgency: "The project record names no implementing agency.",
    // The browser tab's title: "Rajasthan Road Sector Modernization (P130164), Summary".
    documentTitle: (name: string, pid: string, tab: string) => `${name} (${pid}), ${tab}`,
    // Said once when a tab inside the project opens and focus stays on its link.
    showing: (tab: string) => `Showing ${tab}.`,
    headerError: "I couldn't load this project because the data service didn't answer.",
    // Two agency names hold commas, so the agencies are set apart with semicolons.
    agencyJoin: "; ",
    // The agencies keep to two lines; these open and close the rest.
    allAgencies: "Show all agencies",
    fewerAgencies: "Show fewer agencies",
    sections: "Project sections",
    // Every tab a project page will have, in the order the row shows them (the 21 brief, section 1). The
    // row shows only the tabs that are built (BUILT_TABS in web/src/routes.ts), so ticket 22's Connections
    // and ticket 23's Timeline join it with no change to the frame.
    tab: { summary: "Summary", procurement: "Procurement", timeline: "Timeline", documents: "Documents", connections: "Connections" },
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
    // Source lines on a project's own pages leave its ID out (DESIGN.md section 5, ProjectId).
    source: "World Bank documents and reports API, Procurement Plans listed for this project, through {date}.",
    sourceUndated: "World Bank documents and reports API, Procurement Plans listed for this project.",
    agencyEmpty: "I don't have a Procurement Plan from this agency yet.",
    // Two or more agencies with no plan share one block after the agencies with plans.
    otherAgencies: "Other implementing agencies",
    othersEmpty: "I don't have a Procurement Plan from these agencies yet:",
    // True whether the World Bank has disclosed no plan or I haven't read the ones it has (the 21 critique, round 3).
    projectEmptyTitle: "I haven't read a Procurement Plan for this project yet.",
    projectEmptyBody:
      "I can check a plan only after the World Bank discloses it and I have read it. Data readiness shows how much of " +
      "each source I have read.",
    projectEmptyLink: "Data readiness",
    // Ticket 21: what changed in each agency's latest plan, the Baseline mark and the fold.
    changes: {
      // Two sentences with long dates, so neither is dense (DESIGN.md section 7 rule 13; unslop rule 28).
      lead: "The latest plan is the plan of {plan_date}. Compared with the plan of {prev_date}, it {change_list}.",
      same: "The latest plan is the plan of {plan_date}. It lists the same activities, dates and estimates as the plan of {prev_date}.",
      link: "See what changed",
      earliest: "The only plan I have from this agency is the plan of {plan_date}, so I can't compare it with an earlier version.",
      prevUnread: "I haven't read the plan of {prev_date}, the version before the latest, so I can't say what changed.",
    },
    baselineMark: "Baseline",
    versionsMore: (count: string) => `Show all ${count} versions`,
    versionsLess: "Show fewer versions",
    versionsShowing: (shown: string, total: string) => `Showing ${shown} of ${total} versions`,
    changesLoading: "Loading this project's Procurement Plans.",
  },

  // A project's Packages, on its Procurement tab (the 21 brief, section 4).
  packages: {
    title: "Packages",
    purpose:
      "Every activity in each implementing agency's latest Procurement Plan, with its reference from " +
      STEP_SPELLED +
      ". Open a reference to follow its activity from the plan to the signed contract.",
    searchLabel: "Search packages",
    searchHint: "Type part of a STEP reference or a description.",
    noun: "packages",
    caption: "Packages in each agency's latest Procurement Plan",
    pages: "Pages of the package list",
    columns: {
      activity: "Activity",
      agency: "Implementing agency",
      method: "Method · market approach",
      estimated: "Estimated (US$)",
      status: "Process status",
    },
    source: "the latest Procurement Plan from each implementing agency, from the World Bank documents and reports API, read {date}.",
    sourceUndated: "the latest Procurement Plan from each implementing agency, from the World Bank documents and reports API.",
    noMatchTitle: "I found no packages that match your search.",
    noMatchBody:
      "I search the STEP references and descriptions in each agency's latest plan. Check the reference, or search for a " +
      "word from the description.",
    noMatchLink: "Show all packages",
    none: "I haven't read a Procurement Plan for this project yet, so I can't list its packages.",
    error: "I couldn't load this project's packages because the data service didn't answer.",
    searching: "Searching packages.",
  },

  // What changed in a plan since the version before it (the 21 brief, sections 4.2 and 5.4). The counts are
  // the route's; changeList writes them as "added two activities and re-dated three".
  changes: {
    // One part per kind of change above zero, in this order. The first carries the noun; the rest leave it out.
    changeList: (parts: { kind: "added" | "dropped" | "redated" | "reestimated"; count: string; one: boolean }[]) => {
      const verbs = { added: "added", dropped: "dropped", redated: "re-dated", reestimated: "re-estimated" };
      const written = parts.map((part, index) =>
        index === 0 ? `${verbs[part.kind]} ${part.count} ${part.one ? "activity" : "activities"}` : `${verbs[part.kind]} ${part.count}`,
      );
      return written.length <= 1 ? written.join("") : `${written.slice(0, -1).join(", ")} and ${written.at(-1)}`;
    },
    // "No activity was dropped or re-dated." for the kinds with no change, joined as "A, B or C".
    unchanged: (kinds: ("added" | "dropped" | "redated" | "reestimated")[]) => {
      const words = { added: "added", dropped: "dropped", redated: "re-dated", reestimated: "re-estimated" };
      const named = kinds.map((kind) => words[kind]);
      const joined = named.length <= 1 ? named.join("") : `${named.slice(0, -1).join(", ")} or ${named.at(-1)}`;
      return `No activity was ${joined}.`;
    },
    title: "What changed since the plan of {prev_date}",
    // The section's heading when the comparison failed, so the version before is not known.
    titleUnknown: "What changed in this plan",
    lead: "This version {change_list}.",
    // The page spells STEP out once, in "Not visible to Strata", above this note.
    matchNote: "I match activities on their STEP reference. If an activity's reference changed, it shows here as dropped and added.",
    overlapNote: "An activity can appear in more than one table.",
    tableTitle: {
      added: (count: number, text: string) => (count === 1 ? "One activity was added." : `${text} activities were added.`),
      dropped: (count: number, text: string) => (count === 1 ? "One activity was dropped." : `${text} activities were dropped.`),
      redated: (count: number, text: string) => (count === 1 ? "One activity was re-dated." : `${text} activities were re-dated.`),
      reestimated: (count: number, text: string) => (count === 1 ? "One activity was re-estimated." : `${text} activities were re-estimated.`),
    },
    caption: {
      added: (date: string) => `Activities added in the plan of ${date}`,
      dropped: (date: string) => `Activities dropped since the plan of ${date}`,
      redated: (date: string) => `Planned dates moved since the plan of ${date}`,
      reestimated: (date: string) => `Estimates changed since the plan of ${date}`,
    },
    col: {
      step: "Step",
      was: "Was",
      now: "Now",
      moved: "Moved (days)",
      wasUsd: "Was (US$)",
      nowUsd: "Now (US$)",
      changeUsd: "Change (US$)",
      lastStatus: "Last process status",
    },
    later: "{n} later",
    earlier: "{n} earlier",
    more: "{amount} more",
    less: "{amount} less",
    noDate: "No date",
    // A card's moved step below 1024 px: "Was Mar 9, 2026, now Apr 9, 2026", or two sentences when the new
    // version gives no date.
    wasNow: "Was {was}, now {now}",
    wasNoDate: "Was {was}. Now no date.",
    // A Moved cell when either date is missing: empty on screen, and this for a screen reader.
    notMeasured: "Not measured",
    movedDays: (days: string, later: boolean) => `${days} days ${later ? "later" : "earlier"}`,
    explainMoved: "Was {was} in the plan of {prev}. Now {now} in the plan of {plan}. Days between them: {days}.",
    explainAmount: "Was US${was} in the plan of {prev}. Now US${now} in the plan of {plan}.",
    cell: {
      added: "Added in this version",
      redated: "Re-dated in this version",
      reestimated: "Re-estimated in this version",
      both: "Re-dated and re-estimated in this version",
    },
    source:
      "Procurement Plans of {agency}, versions of {prev_date} and {plan_date}, compared row by row on their STEP references.",
    error: "I couldn't load what changed in this plan because the data service didn't answer.",
  },

  // A project's Summary tab (the 21 brief, section 3): facts from precomputed records, each with its source.
  // No model writes it. Dates are "October 31, 2026" in sentences and "Oct 31, 2026" in tables; amounts arrive
  // already written by the route, in US$ millions to one decimal.
  summary: {
    heading: "Summary",
    lead: {
      closed:
        "The project closed on {closing_date}{closing_moves}. The World Bank committed US${commitment} million to it. Of " +
        "that, US${disbursed} million was disbursed and US${canceled} million was canceled.",
      closedNoCancel:
        "The project closed on {closing_date}{closing_moves}. The World Bank committed US${commitment} million to it, and " +
        "US${disbursed} million of that was disbursed. None was canceled.",
      closedNoMoney: "The project closed on {closing_date}{closing_moves}.",
      active:
        "The project is active and closes on {closing_date}{closing_moves}. By {disbursed_as_of}, US${disbursed} million of " +
        "the US${commitment} million that the World Bank committed was disbursed.",
      activeCancel: "US${canceled} million was canceled.",
      activeNoMoney: "The project is active and closes on {closing_date}{closing_moves}.",
      pipeline: "The project record lists this project as in the pipeline, so it has no closing date yet.",
      dropped: "The project record lists this project as dropped.",
    },
    closingMoves: {
      none: ", its original closing date",
      one: ", after its closing date moved once",
      many: ", after its closing date moved {n} times",
    },
    madeBy: "I built this summary from World Bank records as of {as_of_date}. No model wrote it.",
    group: { dates: "Dates", money: "Money", ratings: "Ratings", who: "Sectors and implementing agencies" },
    col: { label: "Fact", date: "Date", money: "US$, millions", rating: "Rating", detail: "Detail", source: "Source" },
    caption: {
      dates: (name: string) => `Dates for ${name}`,
      money: (name: string) => `Money for ${name}, in US$ millions`,
      ratings: (name: string) => `Ratings for ${name}`,
      who: (name: string) => `Sectors and implementing agencies for ${name}`,
      history: (name: string) => `Closing date history for ${name}`,
    },
    label: {
      approval_date: "Approval date",
      original_closing_date: "Original closing date",
      closing_date: "Closing date",
      commitment: "Commitment",
      disbursed: "Disbursed",
      canceled: "Canceled",
      pdo: "Progress towards achievement of the project development objective (PDO)",
      implementation: "Overall implementation progress",
      procurement: "Procurement",
      icr_outcome: "Outcome, in the Implementation Completion and Results Report (ICR)",
      ieg_outcome: "Outcome, in the ICR Review by the Independent Evaluation Group (IEG)",
      ieg_bank_performance: "Bank performance, in IEG's ICR Review",
      esf_rating: "Environmental and social risk",
      ea_category: "Environmental Assessment Category",
      region: "Region",
      sector: "Sector, as Strata groups it",
      sectors: "Sectors in the project record",
      agency: "Implementing agency",
      agencies: "Implementing agencies",
    } as Record<string, string>,
    // A source cell: the record's short name and date, then its citation marker.
    source: {
      projects_api: "Projects API, {date}",
      loans: "Loans and credits, {date}",
      loan_history: "Loan history, {date}",
      isr: "ISR {sequence}, {date}",
      isrUnnumbered: "ISR of {date}",
      projects_api_ratings: "Projects API, ISR of {date}",
      icr: "ICR, {date}",
      ieg_ratings: "IEG ratings, {date}",
    } as Record<string, string>,
    // A citation marker's name: "Source 1: World Bank projects API, record of August 1, 2023".
    markerSource: {
      projects_api: "World Bank projects API, record of {date}",
      loans: "World Bank loans and credits data, as of {date}",
      // One marker for each loan or credit an amount sums.
      loan: "World Bank loans and credits data for {loan}, as of {date}",
      loan_history: "World Bank monthly loan history, reported {date}",
      isr: "Implementation Status and Results Report {sequence}, {date}",
      isrUnnumbered: "Implementation Status and Results Report of {date}",
      projects_api_ratings: "World Bank projects API, ratings from the ISR of {date}",
      icr: "Implementation Completion and Results Report, {date}",
      ieg_ratings: "Independent Evaluation Group ratings, {date}",
    } as Record<string, string>,
    // Under the Money table, when the loans data reports more disbursed and canceled than committed.
    money: {
      exceeds:
        "The loans and credits data reports more disbursed and canceled than committed for this project. I show each " +
        "amount as it reports it.",
    },
    // The commitment's tooltip: each loan or credit, then the total the route summed.
    loanLine: "{loan}: US${amount} million",
    loanTotal: "Total: US${amount} million",
    movesExplain: "The monthly loan history showed a new closing date this many times after approval.",
    history: {
      title: "Closing date history",
      col: { first: "First recorded", before: "Closing date before", after: "Closing date after", source: "Source" },
      none: "The closing date did not change after approval.",
      unknown:
        "I don't have this project's monthly loan history, so I can't show how its closing date changed. I read that " +
        "history only for the projects whose documents I read.",
    },
    notInRecord: "Not in the record",
    eaNote:
      "The project record has no risk rating under the Environmental and Social Framework (ESF), so I show its " +
      "Environmental Assessment Category.",
    noRatings:
      "I haven't read an ISR, an Implementation Completion and Results Report (ICR) or an ICR Review for this project, " +
      "so I have no ratings to show.",
    loading: "Loading this summary.",
    error: "I couldn't load this summary because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show this summary.",
  },

  // A project's Documents tab (the 21 brief, section 6): one table grouped by type, in the order a project
  // produces its documents, newest first in each group.
  documents: {
    heading: "Documents",
    purpose:
      "These are the documents the World Bank published for this project, grouped by type. Open one to read it page by " +
      "page, with its paragraphs numbered as the document numbers them.",
    noun: "documents",
    // The count line: the rows the list shows, of every document listed. Both counts are the route's.
    showing: (shown: string, total: string) => `Showing ${shown} of ${total} documents`,
    caption: (name: string) => `Documents for ${name}, by type`,
    col: { document: "Document", dated: "Dated", disclosed: "Disclosed", pages: "Pages read", pdf: "PDF" },
    def: {
      dated: "The date printed on the document.",
      disclosed:
        "The date the World Bank made the document public. When you view a past date, I use only the documents disclosed " +
        "by then.",
      pages:
        "How many of the document's pages I turned into numbered paragraphs and table rows. Partial means some pages were " +
        "scans, figures or tables I couldn't read.",
    },
    group: {
      pad: "Project Appraisal Document (PAD)",
      project_paper: "Project Papers",
      isr: "Implementation Status and Results Reports (ISRs)",
      procurement_plan: "Procurement Plans",
      icr: "Implementation Completion and Results Report (ICR)",
      icr_review: "ICR Reviews by the Independent Evaluation Group (IEG)",
      ppar: "Project Performance Assessment Reports (PPARs)",
      other: "Other documents",
    } as Record<string, string>,
    groupCount: (count: number, text: string) => (count === 1 ? "1 document" : `${text} documents`),
    // A document's name in the list, by its type. {date} is the table form, such as Oct 1, 2013.
    name: {
      pad: "Project Appraisal Document",
      project_paper: "Project Paper of {date}",
      isr: "ISR {sequence}",
      isrUndated: "ISR of {date}",
      procurement_plan: "{agency}, plan of {date}",
      procurementPlanUnnamed: "Procurement Plan of {date}",
      // A listed document whose type the documents API leaves blank.
      untyped: "Document of {date}",
      untypedUndated: "Document with no type or date",
      icr: "Implementation Completion and Results Report",
      icr_review: "ICR Review",
      ppar: "Project Performance Assessment Report",
    } as Record<string, string>,
    reissueNote: "The re-issue replaces the version of {date}.",
    reissueLink: "Open the version of {date}",
    reissueDated: "Re-issued {date}",
    notRead: "Not read",
    pagesOf: "{read} of {pages}",
    notReadNote: "\"Not read\" means I list the document but haven't read its pages. {link} shows which documents I read.",
    notReadLink: "Data readiness",
    pdf: "PDF",
    // The PDF link's name says the document's date once: after a name with none, or inside one that holds it.
    pdfName: (name: string, date: string) =>
      date ? `Open the PDF of ${name}, ${date}, on the World Bank's site (opens in a new tab)` : `Open the PDF of ${name}, on the World Bank's site (opens in a new tab)`,
    pdfOf: {
      project_paper: "the Project Paper of {date}",
      isrUndated: "the ISR of {date}",
      procurement_plan: "{agency}, plan of {date}",
      procurementPlanUnnamed: "the Procurement Plan of {date}",
      untyped: "the document of {date}",
    },
    more: (count: string) => `Show all ${count}`,
    less: "Show fewer",
    source: "World Bank documents and reports API, documents listed for this project, through {date}.",
    sourceUndated: "World Bank documents and reports API, documents listed for this project.",
    emptyTitle: "I don't have any documents for this project yet.",
    emptyBody:
      "I list a project's documents once I fetch them from the World Bank's documents and reports API. Data readiness " +
      "shows which projects' documents I hold.",
    emptyLink: "Data readiness",
    // A project outside the set of projects whose documents I fetch (config/slice.toml).
    outsideTitle: "I don't list documents for this project.",
    outsideBody:
      "I fetch and read documents only for a set of projects chosen for this demo, and this project isn't one of them. " +
      "Data readiness lists that set.",
    outsideLink: "Data readiness",
    loading: "Loading this project's documents.",
    error: "I couldn't load this project's documents because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't list this project's documents.",
  },

  // The source view (the 21 brief, section 7): one page of a document's own words, at a page and paragraph.
  sourceView: {
    // The h1: the document type's full name.
    typeName: {
      pad: "Project Appraisal Document",
      project_paper: "Project Paper",
      isr: "Implementation Status and Results Report",
      procurement_plan: "Procurement Plan",
      icr: "Implementation Completion and Results Report",
      icr_review: "Implementation Completion and Results Report Review",
      ppar: "Project Performance Assessment Report",
    } as Record<string, string>,
    // The last crumb: "ICR of Oct 10, 2019".
    short: {
      pad: "PAD",
      project_paper: "Project Paper",
      isr: "ISR",
      procurement_plan: "Procurement Plan",
      icr: "ICR",
      icr_review: "ICR Review",
      ppar: "PPAR",
      other: "Document",
    } as Record<string, string>,
    crumb: "{doc} of {date}",
    documentsCrumb: "Documents",
    meta: { project: "Project", dated: "Dated", disclosed: "Disclosed", pages: "Pages", language: "Language" },
    projectValue: "{name} ({pid})",
    ownWords:
      "This page shows the document's own words, divided into the paragraphs the document numbers. I don't change or " +
      "summarize them.",
    pdf: "Open page {page} in the World Bank's PDF",
    pages: {
      label: "Pages of this document",
      position: (page: string, pages: string) => `Page ${page} of ${pages}`,
      // While the page loads, no tool has returned the document's page count yet.
      positionOnly: (page: string) => `Page ${page}`,
      goLabel: "Go to page",
      goButton: "Open page",
    },
    section: "Section {section}",
    opened: "You opened this page at paragraph {para}.",
    openedPassage: "You opened this page at the passage marked below.",
    table: "A table on page {page}, as I read it into rows.",
    tableTitled: "{title}, a table on page {page}, as I read it into rows.",
    planRows: "The activities on page {page}, as I read them from the plan's table.",
    rowField: "Column",
    rowValue: "Value",
    reissueCurrent: "This is the re-issue of {reissue_date}. It replaces the version of {original_date}.",
    reissueCurrentLink: "Open the version of {date}",
    reissueOld: "A re-issue of {reissue_date} replaced this version, and current answers cite the re-issue.",
    reissueOldLink: "Open the re-issue",
    moved: "Paragraph {para} is on page {page}, so I opened that page.",
    noPara: "I don't have a paragraph {para} in this document, so I opened page {page} without a highlight.",
    pageRange: "This document has {pages} pages, so I opened page {pages}.",
    pageUnreadTitle: "I couldn't read page {page}.",
    pageUnreadBody: "The page may be a scan, a figure or a table that I couldn't turn into text. The World Bank's PDF has it.",
    pageFrontTitle: "Page {page} is front matter that I don't read.",
    pageFrontBody: "The front matter holds the report's cover, contents and abbreviations. The World Bank's PDF has it.",
    pageEmptyTitle: "Page {page} has no text I could read.",
    docUnreadTitle: "I haven't read this document.",
    docUnreadBody: "I list it, but I haven't read its pages. The World Bank's PDF has the full text.",
    docUnreadLink: "Open the World Bank's PDF",
    notFoundTitle: "I don't have this document for this project.",
    notFoundBody: "The link may be incomplete. This project's documents are listed on its Documents tab.",
    notFoundLink: "This project's documents",
    ambiguousTitle: (count: string, plural: string) => `This project has ${count} ${plural}, so the link doesn't say which one to open.`,
    ambiguousPlural: {
      pad: "Project Appraisal Documents",
      project_paper: "Project Papers",
      isr: "ISRs",
      procurement_plan: "Procurement Plans",
      icr: "ICRs",
      icr_review: "ICR Reviews",
      ppar: "PPARs",
    } as Record<string, string>,
    ambiguousBody: "Open the one you want from the project's Documents tab.",
    asofTitle: "I can't show this document as of {date}.",
    asofBody: "The World Bank disclosed it on {date}, after that date.",
    loading: (page: string) => `Loading page ${page}.`,
    error: "I couldn't load this page because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show this document.",
    documentTitle: "{doc}, page {page}",
  },

  // The baseline panel on Check a plan (the 21 brief, section 5.2): one shared baseline per project and agency.
  baseline: {
    label: "Baseline for delay",
    none:
      "No plan from this agency is saved as the baseline yet. If this is the plan agreed at negotiations, save it as " +
      "the baseline. Later checks of this agency's plans then also measure delay from its dates.",
    save: "Save as the baseline",
    saving: "Saving the baseline",
    justSaved: "I saved the plan of {plan_date} as the baseline. The reasons below now also give delay against it.",
    undo: "Undo",
    thisPlan:
      "This plan is the baseline. {saved_by} saved it on {saved_date} as the plan agreed at negotiations. I measure delay " +
      "from its dates as well as from the first published planned dates.",
    remove: "Remove the baseline",
    removing: "Removing the baseline",
    justRemoved: "I removed the baseline. Checks of this agency's plans now measure delay only from the first published planned dates.",
    another:
      "The baseline is the plan of {baseline_date}, saved by {saved_by} on {saved_date}. I measure delay from its dates as " +
      "well as from the first published planned dates.",
    anotherLink: "Plan of {date}",
    make: "Make this plan the baseline",
    confirm: "This replaces the plan of {baseline_date} as the baseline for everyone who checks {agency}'s plans.",
    replace: "Replace the baseline",
    replacing: "Replacing the baseline",
    keep: "Keep the plan of {date}",
    justReplaced: "I made the plan of {plan_date} the baseline in place of the plan of {old_date}.",
    // Undo saves that plan again, so the saver is now the person who pressed Undo (the 21 review, round 2).
    undone: "I undid that change. The baseline is the plan of {date}, now saved by you.",
    undoneNone: "I undid that change. No plan from this agency is saved as the baseline.",
    // After a failed write the panel reads the check again, so the sentence above it says what holds now.
    failed: "I couldn't make that change because the data service didn't answer.",
    tryAgain: "Try again",
    permission:
      "Your account can't save to Strata's tables, so I can't save the baseline. Ask your workspace admin for write " +
      "access to the strata catalog.",
    piuSet: "The baseline is the plan of {baseline_date}, saved on {saved_date} as the plan agreed at negotiations. Only World Bank staff can change it.",
    piuNone: "No plan from this agency is saved as the baseline.",
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
      // The public view of a project still under way (the 10 brief, section 6; ticket 40): data notes only.
      withheld: "I don't show signals on active projects in this view, so a procurement still under way isn't prejudged",
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
    // Ticket 21: the method's second sentence when a baseline is saved for this agency's plans.
    methodBaseline:
      "I checked every activity against {checks}. I measure delay two ways: from the first published planned date, " +
      "because each plan update can move the planned dates, and from the baseline, the plan of {baseline_date}.",
    // The change line under the method sentence, and its link to the change list below.
    changes: {
      line: "Compared with the plan of {prev_date}, this version {change_list}.",
      link: "See what changed",
      // When only the comparison failed: the line says so and links the section, whose alert has Try again.
      error: "I couldn't load what changed in this plan.",
      errorLink: "Go to that section",
      same: "This version lists the same activities, dates and estimates as the plan of {prev_date}.",
      earliest: "This is the earliest plan I have from this agency, so I have no earlier version to compare it with.",
      prevUnread: "I haven't read the plan of {prev_date}, the version before this one, so I can't say what changed.",
    },
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
    // The fold in a view that holds back signals on a project still under way (ticket 40): an activity in it may still
    // have a signal I don't show, so it says only that the activity has no data notes.
    foldWithheld: {
      listed: (count: number) =>
        count === 1 ? "{count} more activity has no data notes: {refs}." : "{count} more activities have no data notes: {refs}.",
      counted: "{count} more activities have no data notes.",
    },
    noDataNotes: "No data notes.",
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
      "Those stay in " +
      STEP_SPELLED +
      ".",
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
      baselineSigning: "Planned date in the baseline, the plan of {plan}",
      baselineCompletion: "Planned completion in the baseline, the plan of {plan}",
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
      // Ticket 21: with a baseline, the signing delay names the first published planned date, and a second
      // sentence gives the delay from the baseline's date.
      signed_late_first: (days: number) =>
        (days === 1
          ? "Signed {date}, {days} day after its first published planned date, "
          : "Signed {date}, {days} days after its first published planned date, ") + "at US${actual}, about {ratio} times its estimate.",
      baseline: {
        late: (days: number) => (days === 1 ? "That was {days} day after its baseline date of {date}." : "That was {days} days after its baseline date of {date}."),
        early: (days: number) => (days === 1 ? "That was {days} day before its baseline date of {date}." : "That was {days} days before its baseline date of {date}."),
        on_date: "That was on its baseline date.",
        past: (days: number) =>
          days === 1
            ? "In the baseline, its planned completion was {date}, {days} day before {as_of}."
            : "In the baseline, its planned completion was {date}, {days} days before {as_of}.",
        ahead: "In the baseline, its planned completion is {date}, which has not passed.",
        not_in_baseline: "It was not in the baseline plan, so I measure its delay only from its first published planned date.",
        no_date: "The baseline plan gives no date for this step, so I can't measure delay against it.",
      },
      method_differs_from_reference:
        "The reference ends in {code} ({referenceMethod}), but the Method column says {method}. I use the Method column.",
      actual_amount_zero: "{status}, but Actual Amount reads {actual}.",
      no_planned_date: "The plan gives no planned date for {step}, so I couldn't check its timing.",
      no_estimate: "The plan gives no Estimated Amount, so I couldn't compare the signed amount with it.",
      // Ticket 38: the data notes on an upload's rows (the 38 brief, 5.4). The officer's own cell values are quoted on
      // their own team's page.
      unread_date: 'I couldn\'t read the date in "{column}": "{value}". I left that step undated.',
      unread_amount: 'I couldn\'t read the amount in "{column}": "{value}".',
      no_method: "The row gives no Method, so I couldn't choose its steps.",
      duplicate_ref: "Another row in your file has the same reference, {ref}. I checked both.",
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
    // The later day it was disclosed is not named: as of the page's date it had not happened (ADR 0002; ticket 40).
    notPublicBody: "The World Bank disclosed it after that date.",
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
    // "Drafts from this check" at the end of the page (ticket 36; the 36 brief, section 5.7): the Project Paper
    // summary, offered as a secondary action, saying before the click what it draws on.
    ppAction: {
      title: "Procurement summary for the Project Paper",
      // {agency} is the agency's name; {rows} is the checked PPSD rows' count, a word from one to nine.
      body: (rows: number) =>
        rows === 1
          ? "I draft it from this check, {agency}'s track record with its past packages and the one PPSD row your team checked for this project's packages."
          : "I draft it from this check, {agency}'s track record with its past packages and the {rows} PPSD rows your team checked for this project's packages.",
      bodyNoRows:
        "I draft it from this check and {agency}'s track record with its past packages. Your team has no checked PPSD rows " +
        "for this project's packages, so I leave the PPSD's risks out.",
      // Before the count of checked PPSD rows has come, or when it could not be read.
      bodyUnknown:
        "I draft it from this check, {agency}'s track record with its past packages and any PPSD rows your team checked for this project's packages.",
      button: "Draft a Project Paper summary",
      feedforward: "The draft waits in Drafts for you to check. I send nothing.",
      existingYou: (date: string) => `You started a Project Paper summary on this plan on ${date}.`,
      existingTeammate: (author: string, date: string) => `${author} started a Project Paper summary on this plan on ${date}.`,
      existingLink: "Open the draft",
      asof: "I draft a Project Paper summary only from today's check, not from a past date.",
      stopped: "I stopped writing the Project Paper summary and saved nothing.",
    },
    // Each activity's link to its package workspace (the 12 brief). Its accessible name adds the
    // reference, so a list of links tells the activities apart.
    pastRangeLink: "See the past range",
    pastRangeLabel: (ref: string) => `See the past range for ${ref}`,
    // Ticket 22: each row's link to its activity page, the contract trail, before "See the past range".
    openActivity: "Open the activity",
    openActivityLabel: (ref: string) => `Open the activity ${ref}`,
  },

  // An implementing agency officer's private upload of their Procurement Plan (ticket 38; the 38 brief, sections 5.2 to
  // 5.4 and 5.10). STEP's column names come from the server's STEP column registry, never from here.
  upload: {
    title: "Check my plan",
    crumb: "Check my plan",
    purpose:
      "Upload the Procurement Plan you are preparing, and I check every activity in it before you submit it. I can then " +
      "draft a planned date for each step, as rows you can paste into Systematic Tracking of Exchanges in Procurement (STEP).",
    heading: "Upload your plan",
    // The access label (DESIGN.md section 5): "Official Use Only · visible to your team". The middle dot is hidden
    // from screen readers, which hear a comma instead.
    access: { lead: "Official Use Only", dot: "·", comma: ",", rest: "visible to your team" },
    accessCompact: "Official Use Only",
    privacy: (agency: string) =>
      `Strata shows this upload, and every draft I make from it, only to your team at ${agency}. I keep it out of the ` +
      "search that answers other people's questions.",
    kept: "I keep the activities I read from your file, not the file itself.",
    projectLabel: "Project",
    projectOption: (name: string, pid: string) => `${name} (${pid})`,
    // STEP column names a reading missed, in straight quotes: "A", "A and B" or "A, B and C".
    missingList: (names: string[]) => {
      const quoted = names.map((name) => `"${name}"`);
      return quoted.length <= 1 ? (quoted[0] ?? "") : `${quoted.slice(0, -1).join(", ")} and ${quoted[quoted.length - 1]}`;
    },
    projectPlaceholder: "Choose a project",
    projectHint: "The project this plan belongs to.",
    projectError: "Choose the project this plan belongs to.",
    fileLabel: "Procurement Plan file",
    // Which hint shows is config/uploads.toml's format: step_export once a STEP export is confirmed, published_tables
    // while Strata reads the column names of a published plan's tables (the STEP export check, docs/PLAN.md section 18).
    format: {
      step_export: (formats: string, size: string) => `Choose the plan you exported from STEP, as ${formats}. Files up to ${size}.`,
      published_tables: (formats: string, size: string) =>
        `Choose your plan as ${formats}, with the column names of the tables in a published Procurement Plan. Files up to ${size}.`,
    },
    formats: "an Excel file (.xlsx) or a CSV file",
    // A file's size, from the browser's file object, with one decimal.
    sizeKb: (size: string) => `${size} KB`,
    sizeMb: (size: string) => `${size} MB`,
    choose: "Choose a file",
    none: "No file chosen.",
    chosen: (name: string, size: string) => `${name}, ${size}.`,
    errorNone: "Choose a file to upload.",
    errorType: (name: string, ending: string) => `I can read an Excel file (.xlsx) or a CSV file. ${name} is a ${ending} file.`,
    errorSize: (name: string, size: string, max: string) => `${name} is ${size}. I can read files up to ${max}.`,
    errorEmpty: (name: string) => `${name} is empty. Choose another file.`,
    columnsShow: "Show the columns I read",
    columnsHide: "Hide the columns I read",
    columnsIntro: "I find the header row by STEP's column names, on every sheet in the file.",
    columnsRequired: "I need these columns:",
    columnsOptional: "I also read these when your file has them, and each step's Planned and Actual dates:",
    columnsOther: "I don't use any other column.",
    columnsHeading: "The columns I read",
    submit: "Upload and check",
    feedforward: "Uploading doesn't submit your plan. I send nothing to the World Bank or to STEP.",
    holdPreview: "Uploading is off in a preview.",
    reading: "I'm reading your file. I keep nothing until I finish.",
    readingSteps: {
      upload: (name: string) => `I'm uploading ${name}.`,
      check: "I'm reading the columns and rows, then checking every activity.",
    },
    ready: "Your plan's check is ready.",
    // Each reading error ends "I kept nothing" (the 38 brief, 5.3), by the server's code.
    errors: {
      unreadable: (name: string) => `I couldn't open ${name}. It may be damaged or protected by a password. I kept nothing.`,
      no_table: (name: string) =>
        `I couldn't find a Procurement Plan table in ${name}. I look for a header row with STEP's column names. I kept nothing.`,
      missing_one: (name: string, missing: string) => `I couldn't check ${name}, because it has no ${missing} column. I kept nothing.`,
      missing_many: (name: string, missing: string) => `I couldn't check ${name}, because it has no ${missing} columns. I kept nothing.`,
      no_rows: (name: string) => `I found the columns in ${name} but no activities under them. I kept nothing.`,
      too_many_rows: (name: string, n: string, max: string) =>
        `${name} lists ${n} activities, and I check up to ${max} at a time. I kept nothing.`,
      service: (name: string) => `I read ${name} but couldn't check it, because the data service didn't answer. I kept nothing.`,
      permission: (_name: string) => "Your account can't save to Strata's tables, so I can't keep a check of your plan. I kept nothing.",
      dropped: (name: string) => `The connection dropped while I was uploading ${name}. I kept nothing.`,
      type: (name: string) => `I can read an Excel file (.xlsx) or a CSV file, and ${name} is neither. I kept nothing.`,
      empty: (name: string) => `${name} is empty. I kept nothing.`,
      size: (name: string) => `${name} is larger than the files I can read. I kept nothing.`,
    } as Record<string, (name: string, ...rest: string[]) => string>,
    permissionBody: "Ask your workspace admin for write access to the strata catalog.",
    chooseAnother: "Choose another file",
    reference: (id: string) => `If it fails again, send the data team this reference: ${id}.`,
    publishedHeading: "Or check a published plan",
    publishedIntro: (agency: string) =>
      `These are the latest Procurement Plans the World Bank disclosed for ${agency}. I check them the same way.`,
    publishedItem: (date: string) => `Procurement Plan of ${date}`,
    publishedCaption: "{name} ({pid}), disclosed {date}",
    publishedNone: (agency: string) =>
      `The World Bank hasn't disclosed a Procurement Plan from ${agency} yet. Upload your draft above to check it.`,
    earlier: (count: number, countText: string) =>
      count === 1 ? "Your team has one earlier upload. You can open it from Packages." : `Your team has ${countText} earlier uploads. You can open them from Packages.`,
    loading: "Loading your team's projects.",
    loadError: "I couldn't load your team's projects because the data service didn't answer.",
    notOfficerTitle: "I check uploads only for implementing agency teams, and your account isn't on one.",
    notOfficerBody: "You can check any published plan from its project's Procurement tab.",
    notOfficerLink: "Go to Projects",
    noProjectTitle: (agency: string) => `I can't find a project for ${agency} in the World Bank's project records.`,
    noProjectBody:
      "I need the project to check a plan against its closing date and its comparable packages. Ask the person who shared " +
      "Strata with you to add the project to your team.",
  },
  // The upload's check (the 38 brief, section 5.4): brief 10's page, with these lines added.
  uploadCheck: {
    crumb: (date: string) => `Your plan, uploaded ${date}`,
    subtitleYou: (date: string) => `Your Procurement Plan, uploaded ${date} by you`,
    subtitleTeammate: (date: string, name: string) => `Your team's Procurement Plan, uploaded ${date} by ${name}`,
    method:
      "I checked every activity against its own dates, its cost estimate and the project's closing date. Where an activity " +
      "was in a published plan, I measure delay from its first published planned date. Where it is new, I measure from your dates.",
    readLine: (count: number, countText: string, file: string, name: string, pid: string) =>
      count === 1 ? `I read one activity from ${file} for ${name} (${pid}).` : `I read ${countText} activities from ${file} for ${name} (${pid}).`,
    howShow: "Show how I read your file",
    howHide: "Hide how I read your file",
    sheets: (names: string[]) => `I read these sheets: ${names.map((name) => `"${name}"`).join(", ")}.`,
    used: "I used these columns:",
    usedAs: (header: string, name: string) => `${header}, as ${name}`,
    unused: "I didn't use these columns:",
    values: (count: number, countText: string) =>
      count === 1 ? "I couldn't read one value. It is a data note on its row." : `I couldn't read ${countText} values. Each one is a data note on its row.`,
    noRef: "No reference yet",
    newActivity: "Not in a published plan yet.",
    meta: (date: string, id: string) => `Uploaded on ${date}. Upload ID ${id}`,
    datesButton: (count: number, countText: string) =>
      count === 1 ? "Draft planned dates (1 activity)" : `Draft planned dates (${countText} activities)`,
    datesFeedforward: "The draft waits in Drafts for you to check. I send nothing.",
    datesDescription: "I date each STEP step of every activity from my delay model, and I make rows you can paste into STEP.",
    notFoundTitle: "I can't find this upload.",
    notFoundBody: "The link may be incomplete, or the upload may belong to another team.",
    notFoundLink: "Go to Packages",
    error: "I couldn't load this upload's check because the data service didn't answer.",
    asofUploads: "I check uploads against today's records, whatever the as-of date.",
    backToCheck: "Back to your plan's check",
  },

  // Drafts (the 35 brief): the writing page, a draft's page with its bar, its files and the Drafts tab.
  // Every count comes from the draft runtime or a tool; the browser counts nothing. Each kind of draft
  // (config/drafts.toml) has its words under kinds, by its key.
  draft: {
    // A draft written in a language other than English, or other than your choice now, says so under its method
    // sentence; it keeps the language it was written in (ticket 42).
    language: (language: string) => `I wrote this draft in ${language}. Quotes stay in the language of their source.`,
    // The writing page's line under its state, when the draft is written in a language other than English.
    writingLanguage: (language: string) => `I'm writing it in ${language}.`,
    // The disagreement cards check 6 attached to a draft (ticket 36; the 36 brief, 4.8), above its Sources list.
    disagreements: {
      title: "Where two reports disagree",
      lede: "A source this draft cites disagrees with another report. I kept the draft as I wrote it. Choose the report it keeps where a card asks you to.",
    },
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
        // The composed hold line's first clause, and its frame, once a disagreement can hold too (ticket 36).
        holdClause: "mark the notes as checked",
        holdCompose: "Before you export them, {clauses}.",
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
      // The mission brief (ticket 37; the 37 brief, sections 7 and 9.7 to 9.8): five parts, each with cited
      // sentences first and a table of the records they rest on second. Its keys match review_notes' so the
      // draft page, bar and Drafts tab read either kind the same way.
      mission_brief: {
        title: "Mission brief",
        crumb: (_date: string) => "Mission brief",
        rowTitle: (name: string, _date: string) => `Mission brief for ${name}`,
        pageTitle: (name: string, pid: string) => `Mission brief for ${name} (${pid})`,
        // Under the h1: "Water and Sanitation Development Project (P156634), Kenya".
        subtitle: "{name} ({pid}), {country}",
        lede: (_count: number) => "I drafted all five parts of the mission brief.",
        ledePartial: "I drafted {written} of the five parts of the mission brief. Each other part says what I'm missing.",
        method:
          "I wrote each part from public records through {date} and cited the record or paragraph behind every sentence. " +
          "Open a source number to see it beside the brief.",
        methodLink: "public records",
        countLine: (_count: number, _countText: string) => "",
        columns: {} as Record<string, string>,
        tableCaption: (name: string, _date: string) => `Mission brief for ${name}`,
        abstain: "I removed every sentence I wrote for this part. They are in the removed box above, with the reason for each.",
        refused: {
          out_of_scope: "I didn't write this part, because it would need more than the project's records show.",
        } as Record<string, string>,
        refusedOther: "I didn't write this part.",
        metaYou: (date: string) => `I drafted this brief for you on ${date}.`,
        metaTeammate: (author: string, date: string) => `I drafted this brief for ${author} on ${date}.`,
        barLead: "A working draft of your mission brief.",
        barLeadTeammate: (author: string) => `A working draft of ${author}'s mission brief.`,
        holdNotChecked: "Mark the brief as checked before you export it.",
        holdClause: "mark the brief as checked",
        holdCompose: "Before you export it, {clauses}.",
        readOnly: (author: string) => `Only ${author} can mark this brief as checked or export it.`,
        markedChecked: "You marked this brief as checked. You can export it now.",
        discarded: "I discarded this mission brief, and your team no longer sees it in Drafts.",
        removedReasons: {
          id_not_returned: {
            item: "It cited a source from another part of the brief.",
            joined: "it cited a source from another part of the brief",
          },
        } as Record<string, { item: string; joined: string }>,
        rowNotes: (count: number, countText: string) => (count === 1 ? "One part." : `${countText} parts.`),
        steps: {
          read: {
            running: "I'm reading the project's records.",
            done: (_date: string) => "I read the project's latest plans, its contracts since the last ISR, its ISRs and its loan records.",
            // The writing page's line, with the counts the read step sends: the latest plans read, the contracts
            // since the last ISR, the ISRs.
            counted: (plans: number, plansText: string, awards: number, awardsText: string, isrs: number, isrsText: string) =>
              `I read ${plans === 1 ? "one implementing agency's latest Procurement Plan" : `${plansText} implementing agencies' latest Procurement Plans`}, ` +
              `${awards === 1 ? "one contract" : `${awardsText} contracts`} signed since the last ISR, ` +
              `${isrs === 1 ? "one ISR" : `${isrsText} ISRs`} and the loan records.`,
          },
          write: {
            running: (_count: number, _countText: string) => "I'm writing the five parts.",
            done: (sentences: number, sentencesText: string, _notes: number, _notesText: string) =>
              `I wrote ${sentences === 1 ? "one sentence" : `${sentencesText} sentences`} in five parts.`,
          },
          save: { running: "I'm saving the draft.", done: "I saved the draft." },
        },
        ready: (count: number, countText: string) =>
          count === 5 ? "The draft is ready. I wrote all five parts." : `The draft is ready. I wrote ${countText} of the five parts.`,
        writeErrors: {
          no_agent: "I can't write a mission brief yet, because the model that writes my drafts isn't connected. I saved nothing.",
          agent_unavailable:
            "I couldn't write the mission brief, because the model that writes my drafts did not respond. I saved nothing.",
          content_filter: "I couldn't write the mission brief, because a content filter stopped the writer. I saved nothing.",
          agent_output: "I wrote a mission brief I couldn't check, so I saved nothing.",
          data_service: "I couldn't read the project's records, because the data service didn't answer. I saved nothing.",
          draft_store: "I couldn't save the draft, because I can't write to my drafts tables right now. I saved nothing.",
          no_project: "I don't hold a record of this project, so I wrote nothing and saved nothing.",
          not_active: "I draft mission briefs only for active projects, so I wrote nothing and saved nothing.",
          no_plan: "I don't hold a record of this project, so I wrote nothing and saved nothing.",
          nothing_marked: "I found nothing to write about, so I saved nothing.",
          permission:
            "Your account can't read this project's records in Strata's tables, so I can't write a mission brief. Ask your " +
            "workspace admin for read access to the strata catalog.",
          internal: "Something went wrong on my side, so I couldn't write the mission brief. I saved nothing.",
          dropped: "The connection dropped before I finished the mission brief. I saved nothing.",
        } as Record<string, string>,
        nothingTitle: "I couldn't write a part that passed my checks, so I saved no draft.",
        nothingBody: "The sentences I removed are below, with the reason for each.",
        previewPiuTitle: "I don't show mission briefs in this preview, because they are a World Bank staff draft.",
        previewPiuBody: "Leave the preview to see them. Nothing about the draft changed.",
      },
      // Suggested risk rows for the borrower's PPSD (ticket 36; the 36 brief, sections 5.2 to 5.5). Its keys match
      // review_notes' so the draft page, the bar and the Drafts tab read every kind the same way; copy.ppsd holds what
      // only this kind says. Ticket 38's agency variant swaps these words and keeps the column names.
      ppsd_rows: PPSD_ROWS,
      // Risk rows for an implementing agency's own PPSD (ticket 38; the 38 brief, 5.8): ticket 36's rows, with the
      // officer's words, since the officer drafts rows for their own PPSD and nothing is suggested to someone else.
      ppsd_rows_agency: {
        ...PPSD_ROWS,
        title: "Risk rows for your PPSD",
        crumb: (_date: string) => "Risk rows for your PPSD",
        rowTitle: (title: string, _date: string) => `Risk rows for your PPSD, ${title}`,
        pageTitle: (title: string, _date: string) => `Risk rows for your PPSD, ${title}`,
        method:
          "I wrote each Risk Description and Description of mitigation from {check} and their lessons, for your " +
          "Project Procurement Strategy for Development (PPSD). Open a source number to see its evidence beside the row.",
        tableCaption: (form: string, _date: string) => `Risk rows for your PPSD, ${form}, one row per risk you selected`,
        barLead: "A working draft of risk rows for your Project Procurement Strategy for Development (PPSD).",
        barLeadTeammate: (author: string) => `A working draft of ${author}'s risk rows for your team's PPSD.`,
        discarded: "I discarded these risk rows, and your team no longer sees them in Drafts.",
        previewPiuTitle: "I don't show this team's drafts in a preview.",
        previewPiuBody: "In a preview I don't show an implementing agency's drafts, because they stay with the team that made them.",
      },
      // Planned dates for an implementing agency's plan (ticket 38; the 38 brief, 5.7). Its keys match review_notes'
      // so the bar and the Drafts tab read it the same way; dates holds what only this kind says. Every count is the
      // draft runtime's or estimate_time's.
      step_rows: {
        title: "Planned dates",
        crumb: (date: string) => `Planned dates for your plan uploaded ${date}`,
        rowTitle: (_title: string, date: string) => `Planned dates for your plan uploaded ${date}`,
        pageTitle: (agency: string, date: string) => `Planned dates for ${agency}'s plan of ${date}`,
        subtitle: "{agency}, your plan uploaded {date}",
        lede: (count: number) => (count === 1 ? "I dated all {total} steps of your activity." : "I dated all {total} steps of your {count} activities."),
        ledePartial: "I dated {written} of the {total} steps of your {count} activities.",
        method:
          "I started from the dates in your plan and added how far comparable packages ran past their planned dates at " +
          "each step. Open a count of comparable packages to see them.",
        methodLink: "the dates in your plan",
        countLine: (count: number, countText: string) => (count === 1 ? "Showing the one activity" : `Showing all ${countText} activities`),
        columns: { activity: "Activity", signed: "Contract signed", dated: "Steps dated" } as Record<string, string>,
        tableCaption: (_form: string, _date: string) => "Your activities, in your file's order",
        abstain: "I removed this date, because it didn't match my delay model's results.",
        refused: {} as Record<string, string>,
        refusedOther: "I didn't date this activity.",
        metaYou: (date: string) => `I drafted these dates for you on ${date}.`,
        metaTeammate: (author: string, date: string) => `I drafted these dates for ${author} on ${date}.`,
        barLead: "A working draft of planned dates for your Procurement Plan.",
        barLeadTeammate: (author: string) => `A working draft of ${author}'s planned dates for your team's Procurement Plan.`,
        holdNotChecked: "Mark the dates as checked before you export them.",
        holdClause: "mark the dates as checked",
        holdCompose: "Before you export them, {clauses}.",
        readOnly: (author: string) => `Only ${author} can mark these dates as checked or export them.`,
        markedChecked: "You marked these dates as checked. You can export them now.",
        discarded: "I discarded these planned dates, and your team no longer sees them in Drafts.",
        removedReasons: {} as Record<string, { item: string; joined: string }>,
        rowNotes: (count: number, countText: string) => (count === 1 ? "One activity." : `${countText} activities.`),
        steps: {
          read: {
            running: "I'm reading the activities in your plan and finding comparable packages for each one.",
            done: (count: string) => (count === "one" ? "I read the one activity in your plan." : `I read the ${count} activities in your plan.`),
          },
          write: {
            running: (_count: number, _countText: string) => "I'm checking every date and count against my delay model's results.",
            done: (_sentences: number, _sentencesText: string, dated: number, datedText: string) =>
              dated === 1 ? "I dated one step and checked it." : `I dated ${datedText} steps and checked them.`,
          },
          save: { running: "I'm saving the draft.", done: "I saved the draft." },
        },
        ready: (count: number, countText: string) =>
          count === 1 ? "The draft is ready. I dated one step." : `The draft is ready. I dated ${countText} steps.`,
        writeErrors: {
          data_service: "I couldn't draft the planned dates, because my delay model didn't answer. I saved nothing.",
          draft_store: "I couldn't save the draft, because I can't write to my drafts tables right now. I saved nothing.",
          no_plan: "I couldn't find this plan, so I dated nothing and saved nothing.",
          permission:
            "Your account can't read the records I date from in Strata's tables, so I can't draft planned dates. Ask your " +
            "workspace admin for read access to the strata catalog.",
          internal: "Something went wrong on my side, so I couldn't draft the planned dates. I saved nothing.",
          dropped: "The connection dropped before I finished the planned dates. I saved nothing.",
        } as Record<string, string>,
        nothingTitle: "I couldn't date any step of your plan, so I saved no draft.",
        nothingBody:
          "Every step had fewer than {min} comparable packages that recorded it. Your plan's check still lists every activity.",
        // When my verifier removed what I worked out and no step was left dated: never "too few", which may be untrue.
        nothingRemovedBody: (count: number, countText: string) =>
          count === 1
            ? "My checks removed what I worked out for one step, because it didn't match my delay model's results, and no other step had a date. What I removed is below, with its reason."
            : `My checks removed what I worked out for ${countText} steps, because it didn't match my delay model's results, and no other step had a date. What I removed is below, with the reason for each.`,
        previewPiuTitle: "I don't show this team's drafts in a preview.",
        previewPiuBody: "In a preview I don't show an implementing agency's drafts, because they stay with the team that made them.",
        // What only this kind says (the 38 brief, 5.7), each count from the draft.
        dates: {
          fileNote: "The file I make has STEP's own columns. I fill in the planned dates and copy the other values from your plan, and I leave these empty for you and STEP:",
          choiceLegend: "Date each step with",
          choices: { middle: "Middle dates: half ran later", cautious: "Cautious dates: {in10} in 10 ran later" },
          choiceLocked: { middle: "You checked the middle dates.", cautious: "You checked the cautious dates." },
          noRef: "No reference yet. STEP assigns one.",
          signedAbstain: (count: number) =>
            count === 0
              ? "I'm not dating it: no comparable packages recorded it."
              : count === 1
                ? "I'm not dating it: only one comparable package recorded it."
                : "I'm not dating it: only {count} comparable packages recorded it.",
          undated: "Not dated yet.",
          notListed: "I don't have STEP's steps for {method} yet, so I can't date them.",
          stepsDated: "{dated} of {total}",
          opened: "You opened {opened} of {lists} lists.",
          family: "These are the steps STEP uses for {family}.",
          columns: { step: "Step", plan: "In your plan", planned: "Planned date", comparables: "Comparable packages" },
          comparables: (count: number) => (count === 1 ? "one comparable package" : "{count} comparable packages"),
          removed: "I removed this date, because it didn't match my delay model's results.",
          stepAbstain: "Fewer than {min} comparable packages recorded this step, so I'm not dating it.",
          notInPlan: "Your plan gives no date for this step, so I can't date it from your plan.",
          notReached: "Too many comparable packages have not reached this step yet, so I'm not dating it.",
          exportButton: "Export STEP rows",
          barOpened: (opened: string, total: string) => `You opened ${opened} of ${total} lists of comparable packages`,
          exportedTitle: (count: number) => (count === 1 ? "Exported. I made one STEP row and an evidence pack." : "Exported. I made {count} STEP rows and an evidence pack."),
        },
      },
      // The procurement summary for the Project Paper (ticket 36; the 36 brief, section 5.8). copy.paper holds what
      // only this kind says.
      project_paper: {
        title: "Procurement summary for the Project Paper",
        crumb: (_date: string) => "Project Paper summary",
        rowTitle: (agency: string, date: string) => `Project Paper summary for the ${agency} plan of ${date}`,
        pageTitle: (agency: string, date: string) => `Project Paper summary for the ${agency} plan of ${date}`,
        subtitle: "{agency}, Procurement Plan of {date}",
        // {count} is the checked PPSD rows it drew on, from one to nine in words.
        lede: (count: number) =>
          count === 0
            ? "I drafted the summary from my check of the plan and the agency's track record."
            : count === 1
              ? "I drafted the summary from my check of the plan, the agency's track record and one checked PPSD row."
              : "I drafted the summary from my check of the plan, the agency's track record and {count} checked PPSD rows.",
        ledePartial: "I drafted {written} of the summary's three parts. Each other part says why it is empty.",
        method:
          "I wrote every sentence from a tool's counts or a record, and I cited each one. I don't rate the agency's " +
          "procurement risk. That rating is yours.",
        methodLink: "my check of the plan",
        countLine: (_count: number, _countText: string) => "",
        columns: {} as Record<string, string>,
        tableCaption: (agency: string, _date: string) => `Procurement summary for the Project Paper, ${agency}`,
        abstain: "I couldn't write this part so that it passed my checks. The sentences I removed are listed above. It is left out of the Word file.",
        refused: {
          out_of_scope: "I didn't write this part, because it would need more than the records show. It is left out of the Word file.",
        } as Record<string, string>,
        refusedOther: "I didn't write this part. It is left out of the Word file.",
        metaYou: (date: string) => `I drafted this summary for you on ${date}.`,
        metaTeammate: (author: string, date: string) => `I drafted this summary for ${author} on ${date}.`,
        barLead: "A working draft of the procurement summary for the Project Paper.",
        barLeadTeammate: (author: string) => `A working draft of ${author}'s procurement summary for the Project Paper.`,
        holdNotChecked: "Mark the summary as checked before you export it.",
        holdClause: "mark the summary as checked",
        holdCompose: "Before you export it, {clauses}.",
        readOnly: (author: string) => `Only ${author} can mark this summary as checked or export it.`,
        markedChecked: "You marked this summary as checked.",
        discarded: "You discarded this summary, so your team no longer sees it in Drafts.",
        removedReasons: {
          id_not_returned: {
            item: "It cited a source from another part of the summary.",
            joined: "it cited a source from another part of the summary",
          },
        } as Record<string, { item: string; joined: string }>,
        rowNotes: (count: number, countText: string) => (count === 1 ? "One part." : `${countText} parts.`),
        steps: {
          read: {
            running: "I'm reading my check of the plan, the agency's track record and the PPSD rows your team checked.",
            done: (date: string) => `I read my check of the plan of ${date}, the agency's track record and the PPSD rows your team checked.`,
          },
          write: {
            running: (_count: number, _countText: string) => "I'm writing the summary.",
            done: (sentences: number, sentencesText: string, parts: number, partsText: string) =>
              `I wrote ${sentences === 1 ? "one sentence" : `${sentencesText} sentences`} in ${parts === 1 ? "one part" : `${partsText} parts`}.`,
          },
          save: { running: "I'm saving the draft.", done: "I saved the draft." },
        },
        ready: (_count: number, _countText: string) => "The draft is ready.",
        writeErrors: {
          no_agent: "I can't write a Project Paper summary yet, because the model that writes my drafts isn't connected. I saved nothing.",
          agent_unavailable:
            "I couldn't write the Project Paper summary, because the model that writes my drafts did not respond. I saved nothing.",
          content_filter: "I couldn't write the Project Paper summary, because a content filter stopped the writer. I saved nothing.",
          agent_output: "I wrote a Project Paper summary I couldn't check, so I saved nothing.",
          data_service: "I couldn't read my check of the plan, because the data service didn't answer. I saved nothing.",
          draft_store: "I couldn't save the draft, because I can't write to my drafts tables right now. I saved nothing.",
          no_plan: "I couldn't find this version of the plan, so I wrote nothing and saved nothing.",
          nothing_marked: "I found nothing to write about, so I saved nothing.",
          permission:
            "Your account can't read this plan's check in Strata's tables, so I can't write a Project Paper summary. Ask " +
            "your workspace admin for read access to the strata catalog.",
          internal: "Something went wrong on my side, so I couldn't write the Project Paper summary. I saved nothing.",
          dropped: "The connection dropped before I finished the Project Paper summary. I saved nothing.",
        } as Record<string, string>,
        nothingTitle: "I couldn't write a sentence that passed my checks, so I saved no draft.",
        nothingBody: "The sentences I removed are below, with the reason for each.",
        previewPiuTitle: "I don't show the Project Paper summary in this preview, because it is a World Bank staff draft.",
        previewPiuBody: "Leave the preview to see it. Nothing about the draft changed.",
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
        // Ticket 36: each hold's clause in the composed line "Before you export them, {clauses}." (the 36 brief, 4.5),
        // by how many items are left: {count} is a word from one to nine, then numerals. Each links to the first
        // unfinished item.
        owners: { one: "set one more risk owner", many: "set {count} more risk owners" },
        ratings: { one: "fill in the ratings for one more row", many: "fill in the ratings for {count} more rows" },
        disagreements: {
          one: "choose which report to keep in one disagreement",
          many: "choose which report to keep in {count} disagreements",
        },
      } as Record<string, string | { one: string; many: string }>,
      // Two clauses join with " and "; three or more take commas, with ", and " before the last (the 24 brief's
      // serial comma).
      holdJoin: " and ",
      holdComma: ", ",
      holdLastComma: ", and ",
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
      // A mission brief's row names its project in its title, so line 2 gives the P-code and the country (ticket 37).
      projectCountry: "{pid}, {country}.",
      projectOnly: "{pid}.",
      // Suggested PPSD rows on a package from a sentence, which has no project yet (ticket 36).
      packageNoProject: "Package from a sentence, no STEP reference yet.",
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
      // The STEP rows file's title, which the evidence pack repeats (ticket 38).
      stepRows: { title: "Planned dates for {agency}'s plan of {date}" },
      word: {
        review_notes: {
          heading: "Review notes on the {agency} plan of {date}",
          line: "{project_name} ({project_id}). Procurement Plan of {date}.",
          origin:
            "Drafted with Strata on {created} and checked by {checker} on {checked}. Strata is an independent demo " +
            "built on World Bank open data. These notes are not a World Bank review, clearance or no-objection.",
          columns: ["Activity", "Review note"],
        },
        // The mission brief's Word file (the 37 brief, section 7.4).
        mission_brief: {
          heading: "Mission brief for {project_name} ({project_id})",
          line: "{country}. Public records through {date}.",
          origin:
            "Drafted with Strata on {created} and checked by {checker} on {checked}. Strata is an independent demo " +
            "built on World Bank open data. This brief is not a World Bank review, clearance or no-objection.",
          parts: {
            plans: "Latest Procurement Plans",
            awards: "Awards since the last ISR",
            ratings: "Rating history",
            disbursement: "Disbursement",
            closing: "Closing check",
          },
          tables: {
            plans: "The latest plan from each implementing agency",
            awards: "Contracts signed after the ISR dated {date}",
            ratings: "Ratings in each ISR read",
            disbursement: "Disbursement by loan or credit, in US$ millions",
            closing: "Activities planned to finish after the closing date, and the closing date history",
          },
          columns: {
            plans: ["Implementing agency", "Latest plan", "Activities", "Need a look", "Worth watching"],
            awards: ["Activity", "Signed", "Supplier", "Signed amount (US$)", "Estimated Amount (US$)"],
            ratings: ["ISR", "Dated", "Progress towards achievement of PDO", "Overall implementation progress"],
            disbursement: ["Loan or credit", "Commitment", "Disbursed", "Undisbursed", "Canceled"],
            closing: ["Activity or change", "Implementing agency, or closing date before", "Planned completion, or closing date after", "Days after closing, or first reported"],
          },
          // Why a part has no records, by the reason project_records gave, as the draft page says it.
          none: {
            no_plans: "No Procurement Plan was read for this project.",
            no_isr: "No ISR was read for this project, so there is no date to count the contracts from.",
            no_awards: "No contract was signed after the ISR dated {date}.",
            no_loans: "No loan record is held for this project.",
            closed: "The project closed on {date}, so there is no closing check.",
            no_closing_date: "No closing date is recorded for this project, so there is no closing check.",
          },
          // The ratings part's line when no ISR was read.
          ratingsNone: "No ISR was read for this project.",
          // Under the disbursement table, when the loans data reports more disbursed and canceled than committed.
          exceeds:
            "The loans and credits data reports more disbursed and canceled than committed for this project. Each amount " +
            "is shown as it reports it.",
          planVersion: "Plan of {date}",
          noPlan: "No plan read",
          individual: "Individual consultant",
          isr: "ISR {sequence}",
          notRated: "Not rated",
          total: "Total",
          moved: "Closing date moved",
        },
        // Suggested PPSD rows' Word file (the 36 brief, section 6.6): the template's table for the form chosen, in its
        // column names from config/ppsd_templates.toml, with one footnote per marker.
        ppsd_rows: {
          heading: "Suggested risk rows for the borrower's PPSD",
          // "{package_title}. {reference}." then the project, when the package has one, then the form's name.
          line: "{package_title}. {reference}.",
          noReference: "No STEP reference yet",
          project: "{project_name} ({project_id}).",
          form: "{form_name}.",
          origin:
            "Drafted with Strata on {created} and checked by {checker} on {checked}. {author} set the {set_what}. " +
            "Strata is an independent demo built on World Bank open data. These are suggested rows for the borrower's " +
            "PPSD and are not a World Bank review, clearance or no-objection.",
          setOwners: "risk owners",
          setOwnersRatings: "risk owners and ratings",
          // A footnote's text, built once on the server and shown on the page as its "In Word:" line. A passage
          // footnote is each source's pill (copy.packageRisks.pill), joined, ending with a period.
          footnote: {
            count: "Seen in {k} of {m} comparable completion reports.",
            page: ", page {page}",
            join: "; ",
            end: ".",
          },
        },
        // The Project Paper summary's Word file: a Heading 2 and its paragraph per part with sentences.
        project_paper: {
          heading: "Procurement summary for the Project Paper",
          line: "{project_name} ({project_id}). {agency}, Procurement Plan of {date}.",
          origin:
            "Drafted with Strata on {created} and checked by {checker} on {checked}. Strata is an independent demo " +
            "built on World Bank open data. This summary is not a World Bank review, clearance or no-objection.",
          parts: {
            plan: "The Procurement Plan",
            record: "The implementing agency's track record",
            ppsd: "Procurement risks in the PPSD",
          },
        },
      },
      pack: {
        title: "Evidence pack",
        // The first line of the evidence pack from an implementing agency team's draft (the 38 brief, 6.10).
        officialUseOnly: "Official Use Only",
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
        // Suggested PPSD rows add who set each owner and rating, and when, one line per save (ticket 36).
        fieldsTitle: "Fields you set",
        fieldsColumns: ["Row", "Field", "Value", "Set by", "Set on (UTC)"],
        fieldsRemoved: "Removed",
        fieldsForm: "Risk table form",
      },
    },
  },

  // Suggested PPSD rows' own words (ticket 36; the 36 brief, sections 5.3 to 5.5). The column names are never
  // here: they come from the template registry (config/ppsd_templates.toml) through the draft, word for word.
  ppsd: {
    noReference: "No STEP reference yet.",
    // The writing page's way back, and what it says after a reload (the 36 brief, section 5.2).
    backToPackage: "Back to the package",
    reloadBody: "If you reloaded this page while I was writing, I stopped and saved nothing. Start again from the package.",
    // The form control and its captions. {amount} and {threshold} are US dollar amounts with their cents.
    formLegend: "Risk table form",
    formAvailable:
      "This package's cost estimate of US${amount} is at or above US${threshold}, the lowest Table I threshold in the " +
      "PPSD guidance for {category}, so you can use the Long Form. It adds four columns for you to fill.",
    formBelow:
      "I used the Short Form, because this package's cost estimate of US${amount} is below US${threshold}, the lowest " +
      "Table I threshold in the PPSD guidance for {category}.",
    formNoAmount:
      "I used the Short Form, because this package has no cost estimate for me to compare with the PPSD guidance's Table I thresholds.",
    // A STEP category as the captions write it.
    categories: {
      Works: "works",
      Goods: "goods",
      "Non-consulting Services": "non-consulting services",
      "Consultant Services": "consultant services",
    } as Record<string, string>,
    // The progress line: its first sentence is bold.
    progressCount: (set: string, total: string) => `${set} of ${total} risk owners set.`,
    progressRated: (rated: string, total: string) => `${rated} of ${total} rows rated.`,
    progressShort: "I wrote the descriptions and mitigations. Risk owners stay with you and the borrower.",
    progressLong: "I wrote the descriptions and mitigations. Risk owners and ratings stay with you and the borrower.",
    bandLabel: (risk: string) => `For you to fill: ${risk}`,
    // The Sources list's first line of each footnote, and where it is cited.
    inWord: "In Word: {text}",
    citedIn: (column: string, risk: string) => `Cited in the ${column} for "${risk}".`,
    // A marker that carries several sources: its accessible name lists them all (the 36 brief, 4.6).
    markerName: (n: number, sources: string, opened: boolean) => `Source ${n}: ${sources}${opened ? ", opened" : ""}`,
    markerJoin: ", and ",
    markerParagraph: "{doc} {pcode} paragraph {para}, page {page}",
    markerSection: "{doc} paragraph {section}",
    markerCount: "count of comparable completion reports",
    markerLesson: "the lesson it rests on",
    // Announced in the page's one polite region (section 5.4).
    ownerSet: (set: string, total: string) => `Owner set. ${set} of ${total} risk owners set.`,
    ownerRemoved: (set: string, total: string) => `Owner removed. ${set} of ${total} risk owners set.`,
    fieldSet: (field: string, risk: string) => `${field} set for "${risk}".`,
    allOwners: (total: string) => `All ${total} risk owners are set. Mark the rows as checked to export them.`,
    exportReady: "You can export the rows now.",
    showingLong: (rated: string, total: string) => `Showing the Long Form. ${rated} of ${total} rows rated.`,
    showingShort: "Showing the Short Form.",
    formFailed: "I couldn't change the form just now.",
  },

  // Fill-in chips and their editors (ticket 36; the 36 brief, sections 4.3 and 5.4): fields only a person fills.
  // The action keeps one name from the chip to the button to the announcement.
  fill: {
    ownerEmpty: "Set the owner",
    ratingEmpty: "Set",
    // A chip's accessible name: it holds the chip's own words (WCAG 2.5.3).
    nameEmpty: (field: string, risk: string) => `Set the ${field} for ${risk}`,
    nameOwnerEmpty: (risk: string) => `Set the owner for ${risk}`,
    nameSet: (field: string, risk: string, value: string) => `${field} for ${risk}: ${value}. Change it.`,
    editorRow: (risk: string) => `For the row on "${risk}".`,
    ownerLabel: "Risk owner",
    ownerHint: "Name the role or unit that will manage this risk, as the borrower's PPSD names it.",
    counter: (left: string) => `${left} characters left.`,
    ownerError: "Write the role or unit that will manage this risk.",
    ownerSubmit: "Set the owner",
    ownerRemove: "Remove the owner",
    scoreLabel: "Score",
    scoreHint: "The template defines it as {definition}. Type it as the borrower agrees it.",
    scoreSubmit: "Set the score",
    scoreError: (min: string, max: string) => `Type a whole number from ${min} to ${max}, as the template's score uses.`,
    scoreRemove: "Remove the score",
    ratingRemove: "Remove the rating",
    stageRemove: "Remove the stage",
    stageLabel: "Stage",
    stageSubmit: "Set the stage",
    stageError: "Write the stage of the procurement process.",
    // A rating option: "4, High".
    ratingOption: (value: number, label: string) => `${value}, ${label}`,
    readOnlyEmpty: "Not set",
    saveFailed: "I couldn't save this just now.",
    tryAgain: "Try again",
    preview: "Changes are off in a preview.",
    close: "Close",
  },

  // The Project Paper summary's own words (ticket 36; the 36 brief, section 5.8).
  paper: {
    scope: (pid: string, agencies: string, agency: string) =>
      `${pid} has ${agencies} implementing agencies with Procurement Plans. This summary covers ${agency} only.`,
    parts: { plan: "The Procurement Plan", record: "The implementing agency's track record", ppsd: "Procurement risks in the PPSD" } as Record<string, string>,
    // The PPSD part's source caption: one sentence per draft it drew on, its title a link.
    ppsdSource: "From {title}, checked by {checker} on {date}.",
    ppsdNone:
      "Your team had no checked PPSD rows for this project's packages when I drafted this, so this part is empty. It is left out of the Word file.",
    recordNone: (agency: string) =>
      `I found no past package from ${agency} with both a date in a published plan and a signed contract, so this part is empty. It is left out of the Word file.`,
    abstain: "I couldn't write this part so that it passed my checks. The sentences I removed are listed above. It is left out of the Word file.",
    sheetLabel: "Procurement summary for the Project Paper, draft text",
    writingParts: "The summary's parts, being written",
  },

  // The package workspace's frame (the 12 brief): the header, the package's facts in STEP's field
  // names, and the states of the whole page.
  packagePage: {
    breadcrumbPackages: "Packages",
    facts: {
      method: "Method",
      marketApproach: "Market Approach",
      reviewType: "Review Type",
      estimated: "Estimated Amount (US$)",
      processStatus: "Process Status",
      inPlan: "In the plan",
    },
    // The "In the plan" value, a link back to the plan check with this row in view.
    inPlan: "{agency} plan of {date}",
    missing: "Not in the plan row",
    loading: "Loading this package.",
    error: "I couldn't load this package.",
    permission: "Your account can't read Strata's tables, so I can't show this package.",
    notFoundTitle: "I can't find a package with this reference",
    // {ref} carries its own full stop, so the two move to a new line together.
    notFoundBody: "No package in Strata has the reference {ref} Check the reference in STEP, or find its project in All projects.",
    notFoundLink: "All projects",
  },

  // Section 1 of the package workspace, "How long it took": the past range of comparable packages
  // (the 12 brief). Every number is find_comparables', written by web/src/lib/format.ts; the screen
  // only counts rows for the plan line's readout. Strings with {slots} are filled with Num elements.
  pastRange: {
    eyebrow: "Planning",
    // Hidden from screen readers, so the heading reads "How long it took".
    number: "1 ·",
    heading: "How long it took",
    loading: "Loading the comparable packages.",
    error: "I couldn't load the comparable packages for this section.",
    permission: "Your account can't read Strata's tables, so I can't show the comparable packages.",
    // The finding, at the plan row's own months.
    title: {
      about: "{within} of {total} comparable packages, about {in10} in 10, were signed within the plan's {plan} months.",
      none: "None of the {total} comparable packages were signed within the plan's {plan} months.",
      all: "All {total} comparable packages were signed within the plan's {plan} months.",
      fewerThanOne: "{within} of {total} comparable packages, fewer than 1 in 10, were signed within the plan's {plan} months.",
      moreThanNine: "{within} of {total} comparable packages, more than 9 in 10, were signed within the plan's {plan} months.",
      noPlan: "The middle half of the {total} comparable packages took {q25} to {q75} months from notice to signature.",
      noPlanNoRange: "I found {total} comparable packages, but so many are still open that I can't place their middle half.",
      abstain: "I'm not giving a range: only {n} comparable packages. Here are all {n}.",
      abstainOne: "I'm not giving a range: only one comparable package. Here it is.",
    },
    subtitle: "Each dot is one package, placed by the months from its specific procurement notice to its signed contract.",
    subtitleDots:
      "Each dot is 1 in 20 of the {total} packages, placed by the months from the specific procurement notice to the signed contract.",
    summary: {
      middle: "The middle half of these packages took {q25} to {q75} months, and the middle one took {q50}.",
      // With no plan dates the title already gives the middle half, so the summary starts here.
      middleOnly: "The middle one took {q50} months.",
      in10: "8 in 10 were signed within {q80} months.",
      noIn10: "Fewer than 8 in 10 of these packages have been signed so far, so I can't say when 8 in 10 were signed.",
      noUpper: "So many of these packages are still open that I can't place the upper edge of the middle half.",
      openMany: "{open} of the {total} are still open. I kept them in the range as not signed yet, so the range does not look shorter than it was.",
      openOne: "One of the {total} is still open. I kept it in the range as not signed yet, so the range does not look shorter than it was.",
      abstain: "I give a range only from {min} or more comparable packages, because a range from fewer can mislead. Each dot is one real package, and the table lists them all.",
      abstainOpenMany: "{open} of them are still open.",
      abstainOpenOne: "One of them is still open.",
    },
    // The note on what "comparable" meant: the criteria find_comparables used.
    note: {
      label: "Note:",
      same: "I compared packages with the same {fields}.",
      they: "They {parts}.",
      field: "{field} ({value})",
      category: "Category",
      size: "had signed contracts of US${from} to US${to}",
      sizeFrom: "had signed contracts of US${from} or more",
      sizeTo: "had signed contracts of US${to} or less",
      region: "were in {region}",
      period: "had notices from {from} to {to}",
    },
    // The coverage line's noun and one phrase per reason code find_comparables returns
    // (config/tools.toml, [tools.find_comparables.result]).
    coverageNoun: "matching packages",
    // A phrase that changes with its count is a function of it.
    reasons: {
      no_step_reference: () => "{count} lacked the STEP reference that links notice to contract",
      no_notice: () => "{count} had no specific procurement notice in the records I hold",
      canceled: (count: number) => (count === 1 ? "{count} was canceled before a contract was signed" : "{count} were canceled before a contract was signed"),
      signed_before_notice: (count: number) =>
        count === 1 ? "{count} was signed before the date of its notice" : "{count} were signed before the date of their notice",
      no_review_type: () => "{count} had no review type in any record",
      no_market_approach: () => "{count} had no market approach in any record",
      no_amount: () => "{count} had no signed amount in US dollars",
    },
    reasonsEnd: ".",
    source: "{sources}. Records run through {date}.",
    sourceUndated: "{sources}.",
    // The plan control above the chart.
    control: {
      label: "Planned months",
      unit: "months",
      helper: "The plan row puts the notice on {notice} and the signed contract on {signing}.",
      helperNoPlan:
        "The plan row has no planned notice date or signing date, so there is no plan line yet. Type a number of months to compare.",
      helperTyped: "The plan row has no planned notice date or signing date, so the line shows the months you typed.",
      // A package planned from a sentence (ticket 15): the line is the person's plan, the same value as its plan chip.
      helperPlanned: "The line shows your plan, the same months as Your plan above. Moving the line changes your plan.",
      helperPlannedNone: "Type your plan's months, or add your plan in the How group, to see it as a line.",
      invalid: (max: string) => `Type months from 0.5 to ${max}.`,
      reset: (plan: string) => `Use the plan's ${plan} months`,
    },
    // The range chart's words. Numbers arrive written by web/src/lib/format.ts.
    chart: {
      lane: "What happened",
      keySigned: (count: string) => `${count} signed`,
      keyOpen: (count: string) => `${count} still open`,
      keyDots: (total: string) => `Each dot is 1 in 20 of the ${total} packages.`,
      // Open packages are not drawn one by one among quantile dots, so their count is words alone.
      keyOpenDots: (count: string) => `${count} still open.`,
      plan: "Plan",
      readout: (within: string, total: string, months: string) => `${within} of ${total} signed within ${months} months`,
      // The same readout as two lines, for a chart where one line does not fit beside a plan line in its middle.
      readoutCount: (within: string, total: string) => `${within} of ${total} signed`,
      readoutWithin: (months: string) => `within ${months} months`,
      middle: (q25: string, q75: string, q50: string) => `Middle half ${q25} to ${q75}, middle ${q50}`,
      in10: (q80: string) => `8 in 10 within ${q80}`,
      axisLast: (months: string) => `${months} months`,
      group: (total: string) => `${total} comparable packages, one dot each`,
      groupDots: (total: string) => `20 dots, each 1 in 20 of the ${total} comparable packages`,
      groupHelp: "Use the arrow keys to move between packages. Press Escape to hide the details.",
      // Where a dot opens its package's records in the evidence drawer (ticket 15).
      groupHelpOpen: "Use the arrow keys to move between packages. Press Enter to open a package's records, or Escape to hide the details.",
      openHint: "Press Enter or click to open its records.",
      openRecords: "Open its records",
      // Where a quantile dot lists the packages it stands for in the evidence drawer (ticket 15).
      groupHelpOpenDots:
        "Use the arrow keys to move between dots. Press Enter to list the packages a dot stands for, or Escape to hide the details.",
      openHintDots: "Press Enter or click to list the packages it stands for.",
      openDots: "List its packages",
      dotSigned: (ref: string, country: string, months: string, date: string, index: string, total: string) =>
        `${ref}, ${country}. Signed after ${months} months, on ${date}. Dot ${index} of ${total}.`,
      dotOpen: (ref: string, country: string, months: string, index: string, total: string) =>
        `${ref}, ${country}. Still open after ${months} months. Dot ${index} of ${total}.`,
      dotQuantile: (k: string, total: string, months: string) =>
        `Dot ${k} of 20. Each dot is 1 in 20 of the ${total} comparable packages. This one is at ${months} months.`,
      dotQuantileOpen: (k: string, total: string, months: string) =>
        `Dot ${k} of 20. Each dot is 1 in 20 of the ${total} comparable packages. Too many of these packages are still open to place this dot, so it sits past ${months} months.`,
      tipMonths: (months: string) => `${months} months`,
      tipPast: (months: string) => `Past ${months} months`,
      // The country leads, as it follows the reference in the dot's name, so the notice is not read as published there.
      tipSigned: (signed: string, notice: string, country: string) => `${country}. Signed ${signed}. Its notice was published ${notice}.`,
      tipOpen: (notice: string, country: string) => `${country}. Still open. Its notice was published ${notice}.`,
      tipQuantile: (k: string) => `Dot ${k} of 20`,
      tipQuantileLine: (total: string) => `Each dot is 1 in 20 of the ${total} comparable packages.`,
      tipQuantileOpen: "Too many of these packages are still open to place this dot.",
      slider: "Planned months",
      valueText: (months: string, within: string, total: string) =>
        `${months} months. ${within} of ${total} were signed within ${months} months.`,
      valueTextPlan: (months: string, within: string, total: string) =>
        `${months} months, the plan's own figure. ${within} of ${total} were signed within ${months} months.`,
      announce: (within: string, total: string, months: string) => `${within} of ${total} were signed within ${months} months.`,
      // The text alternative: the same numbers the chart draws.
      alt: (total: string, axisMax: string, signed: string, open: string) =>
        `Dot chart of ${total} comparable packages on a month axis from 0 to ${axisMax} months: ${signed} signed and ${open} still open.`,
      altAllSigned: (total: string, axisMax: string, signed: string) =>
        `Dot chart of ${total} comparable packages on a month axis from 0 to ${axisMax} months: ${signed} signed.`,
      altDots: (total: string, axisMax: string) =>
        `Dot chart of 20 dots, each 1 in 20 of the ${total} comparable packages, on a month axis from 0 to ${axisMax} months.`,
      altRange: (q25: string, q75: string, q50: string, q80: string) =>
        `The middle half took ${q25} to ${q75} months, the middle one took ${q50}, and 8 in 10 were signed within ${q80}.`,
      altMiddle: (q25: string, q75: string, q50: string) => `The middle half took ${q25} to ${q75} months, and the middle one took ${q50}.`,
      altNoIn10: "Fewer than 8 in 10 have been signed so far.",
      altNoUpper: "Too many are still open to place the upper edge of the middle half.",
      altAbstain: "I'm not giving a range for so few.",
      altPlan: (months: string, within: string, total: string) => `A line marks ${months} months, and ${within} of ${total} were signed within it.`,
      altCanceledLeftOut: (count: number, text: string) =>
        count === 1
          ? "I left out the one canceled package, because it was never signed and is not still open."
          : `I left out the ${text} canceled packages, because a canceled package was never signed and is not still open.`,
      altCanceledCounted: (count: number, text: string) =>
        count === 1 ? "I counted the one canceled package as still open." : `I counted the ${text} canceled packages as still open.`,
    },
    // What each checkable number counts, in its tooltip.
    explain: {
      counts: (plan: string, total: string, open: string) =>
        `Packages signed in ${plan} months or less, out of all ${total}, including the ${open} still open. Select to see the rows.`,
      quantiles: (total: string, open: string) =>
        `Worked out from all ${total} comparable packages, with the ${open} still open counted as not signed yet. This is the Kaplan-Meier method. Select to see the rows.`,
      plan: (agency: string, date: string) => `From the planned dates in the ${agency} plan of ${date}.`,
      coverage: "Counted from the records behind this section. Data readiness lists them by source.",
    },
    // The table twin under the chart.
    table: {
      show: "Show the table",
      hide: "Hide the table",
      caption: (total: string) => `All ${total} comparable packages, shortest first.`,
      captionOne: "The one comparable package.",
      noun: "packages",
      nounOne: "package",
      columns: {
        package: "Package (STEP reference)",
        country: "Country",
        notice: "Notice published",
        signed: "Contract signed",
        months: "Months",
        monthsNote: "From notice to signature, or so far if still open",
        // Cards have no column heads, so the Months definition ends the count line's row once.
        monthsCards: "Months run from notice to signature, or so far if still open.",
        within: (months: string) => `Signed within ${months} months`,
      },
      stillOpen: "Still open",
      yes: "Yes",
      no: "No",
      notYet: "Not yet",
      previous: "Previous 20",
      next: "Next 20",
      openRow: (ref: string) => `Open the records for ${ref}`,
    },
    // The states with no chart.
    empty: {
      noneTitle: "No past package matched this one, so I have nothing to compare it with.",
      noneLooked: "I looked for packages with the same {fields}.",
      noneHadTo: "They had to {parts}.",
      noneSize: "have signed contracts of US${from} to US${to}",
      noneSizeFrom: "have signed contracts of US${from} or more",
      noneSizeTo: "have signed contracts of US${to} or less",
      noneRegion: "be in {region}",
      nonePeriod: "have notices from {from} to {to}",
      noneEnd: "Data readiness shows which records I hold for this region and period.",
      noneLink: "Open Data readiness",
      unmeasuredTitle: (matched: number) =>
        matched === 1
          ? "{matched} past package matched this one, but I can't measure how long it took."
          : "{matched} past packages matched this one, but I can't measure how long any of them took.",
      notMeasurableTitle: "I can't measure procurement cycle time for this package.",
      // STEP's value in quote marks, so the field's name and its value don't run together.
      notMeasurableBody:
        'I measure it from the specific procurement notice to the signed contract. Packages with the {field} "{value}" had no public notice to start from.',
      notMeasurableLink: "Back to the plan check",
      // Packages matched, but none could be measured: what they lacked, with no "Based on 0 of".
      unmeasuredOf: "Of the {matched}, {gaps}.",
    },
  },

  // Lane 2 of section 1, the time estimate, with its track record and the plan-date choice (ticket 26; the 26
  // brief, section 7). Every number is estimate_time's, written by web/src/lib/format.ts; the screen counts
  // nothing. Strings with {slots} are filled with Num elements. "Time estimate" is never shortened to
  // "estimate" (GLOSSARY.md), and a what-if says "went with".
  timeEstimate: {
    lane: "Time estimate for this package",
    // The same label where the full one would not fit in the chart, as at 320 px with a reader's text spacing.
    laneShort: "Time estimate",
    keyDescribed: "As described",
    keyWith: (option: string) => `With ${option}`,
    // Row E's labels, as lane 1's row C writes its own.
    middle: (e25: string, e75: string, e50: string) => `Middle half ${e25} to ${e75}, middle ${e50}`,
    in10: (e80: string) => `8 in 10 within ${e80}`,
    summary: "For this package, I estimate {e25} to {e75} months for the middle half and {e80} months for 8 in 10.",
    why: {
      later: "My time estimate's middle is {diff} months later than the past range's, mainly because {reason1}.",
      earlier: "My time estimate's middle is {diff} months earlier than the past range's, mainly because {reason1}.",
      laterTwo: "My time estimate's middle is {diff} months later than the past range's, mainly because {reason1}, and also because {reason2}.",
      earlierTwo:
        "My time estimate's middle is {diff} months earlier than the past range's, mainly because {reason1}, and also because {reason2}.",
      // With no reason the model's own numbers show, the sentence gives the difference alone.
      laterOnly: "My time estimate's middle is {diff} months later than the past range's.",
      earlierOnly: "My time estimate's middle is {diff} months earlier than the past range's.",
      same: "My time estimate and the past range have about the same middle.",
    },
    // One template per reason code estimate_time can return (config/tools.toml); a new code needs its words here.
    reasons: {
      size_larger: "this package is larger than {k} of the {n} comparable packages",
      size_smaller: "this package is smaller than {k} of the {n} comparable packages",
    },
    explain: {
      estimate: (date: string) =>
        `My time estimate for this package, from the model scored on ${date}. Select to see how it did on packages it had not seen.`,
      diff: "The difference between my time estimate's middle and the past range's middle, worked out by the tool.",
      size_larger: (n: string) =>
        `Comparable packages whose signed contracts add up to less than this package's estimated amount, out of all ${n}. Select to see them.`,
      size_smaller: (n: string) =>
        `Comparable packages whose signed contracts add up to more than this package's estimated amount, out of all ${n}. Select to see them.`,
      track: (year: string) => `From my backtest for ${year}. Select to see every test year.`,
      planDate: (n: string, year: string, k: string) =>
        `In my backtest of ${n} packages from ${year} that I had not seen, ${k} ran longer than this point of their own time estimate.`,
    },
    track: {
      label: "Track record:",
      sentence: "of {n} packages from {year} that I had not seen, {m} finished inside my 8-in-10 range, where a well-sized range catches about {expected}.",
      misses: "Of the {misses} that finished outside it, {late} ran late.",
      unavailable: "I have fewer than {min} packages from {year} that I had not seen, so I can't give a track record yet.",
      none: "I have no backtest results yet, so I can't give a track record.",
      notReadable: "I couldn't read my backtest results, so I can't give a track record.",
      show: "Show each test year",
      hide: "Hide the test years",
    },
    testYears: {
      caption: "How my 8-in-10 range did on packages I had not seen, by test year.",
      noun: "test years",
      nounOne: "test year",
      count: (count: string, first: string, last: string) => `Showing ${count} test years, ${first} to ${last}.`,
      countOne: (year: string) => `Showing 1 test year, ${year}.`,
      columns: {
        year: "Test year",
        n: "Packages I had not seen",
        m: "Inside my 8-in-10 range",
        expected: "A well-sized range catches about",
        mine: "My typical error (months)",
        past: "Past range's typical error (months)",
        plans: "Plans' typical error (months)",
        note: "Half of the packages were closer than this.",
      },
      notMeasured: "Not measured",
      noModel: "No model that year",
      source: "my backtests, run {date}. Each year's model learned only from packages before that year.",
      sourceUndated: "my backtests. Each year's model learned only from packages before that year.",
      cardInside: "{m} of {n} packages I had not seen finished inside my 8-in-10 range. A well-sized range catches about {expected}.",
      cardErrors: "Typical error: mine {a} months, the past range's {b}, the plans' {c}.",
      cardNone: "I had no package from this year that I had not seen.",
    },
    planDates: {
      label: "Dates I draft for this package",
      middleHalf: "{months} months: about half ran longer",
      middle: "{months} months: about {in10} in 10 ran longer",
      eight: "{months} months: about {in10} in 10 ran longer",
      // Under 50 packages in the backtest, the count comes first (DESIGN.md section 7, rule 15).
      counted: "{months} months: {k} of {n}, about {in10} in 10, ran longer",
      countedHalf: "{months} months: {k} of {n}, about half, ran longer",
      noTrackMiddle: "{months} months: the middle of my time estimate",
      noTrackEight: "{months} months: my 8-in-10 point",
      caption: "I use the date you choose when I draft planned dates for this package. The later date is the cautious one, and I start with it.",
      preview: "Changes are off in a preview.",
      failed: "I couldn't save this choice. It still applies on this page.",
      announce: (months: string) => `I'll use ${months} months for the dates I draft.`,
    },
    // Lane 2's messages, which are HTML over the lane, so they wrap.
    abstain: {
      few: "I'm not giving a time estimate: only {n} comparable packages.",
      fewOne: "I'm not giving a time estimate: only one comparable package.",
      fewSummary: "I give a time estimate only from {min} or more comparable packages, the same rule as the past range.",
      // outside_training, by the feature and its side of what the model learned from.
      outside: {
        estimated_amount_usd: {
          high: "I'm not giving a time estimate: this package is larger than any package my model learned from.",
          low: "I'm not giving a time estimate: this package is smaller than any package my model learned from.",
        },
        planned_days: {
          high: "I'm not giving a time estimate: this package's plan allows longer than any plan my model learned from.",
          low: "I'm not giving a time estimate: this package's plan allows less time than any plan my model learned from.",
        },
      },
      outsideOther: "I'm not giving a time estimate: this package is outside what my model learned from.",
      outsideSummary: "The past range above still shows every comparable package.",
      beforeTraining: "I'm not giving a time estimate as of {date}, because my model learned from packages signed after that date.",
      noModel: "I'm not giving a time estimate yet: no model has been scored.",
      error: "I couldn't load my time estimate.",
      tryAgain: "Try again",
      code: "If it fails again, quote this code: {code}.",
    },
    // Section 1's table twin: the time estimate's four points.
    table: {
      caption: "My time estimate for this package, in months from notice to signed contract.",
      points: { q25: "Middle half starts", q50: "Middle", q75: "Middle half ends", q80: "8 in 10 within" },
      point: "Point",
      described: "As described (months)",
      with: (option: string) => `With ${option} (months)`,
    },
    // The chart's text alternative, with the past range's sentences before these.
    alt: {
      lanes: (axisMax: string) => `Two lanes on one month axis from 0 to ${axisMax} months.`,
      described: (e25: string, e75: string, e50: string, e80: string) =>
        `Time estimate for this package: middle half ${e25} to ${e75} months, middle ${e50}, 8 in 10 within ${e80}.`,
      comparing: (option: string, k: string, total: string, w25: string, w75: string, w50: string, w80: string) =>
        `Compared with ${option}: ${k} of ${total} comparable packages went with it, drawn larger in blue. Time estimate with ${option}: middle half ${w25} to ${w75} months, middle ${w50}, 8 in 10 within ${w80}.`,
      comparingFew: (option: string, k: string, total: string) =>
        `Compared with ${option}: ${k} of ${total} went with it, drawn larger in blue. Too few to give a time estimate with ${option}.`,
      comparingNone: (option: string, k: string, total: string) =>
        `Compared with ${option}: ${k} of ${total} went with it, drawn larger in blue. No time estimate with ${option}.`,
      ghost: (b25: string, b75: string, b50: string, b80: string) =>
        `A dashed outline shows the time estimate as described: middle half ${b25} to ${b75} months, middle ${b50}, 8 in 10 within ${b80}.`,
      abstainFew: "I'm not giving a time estimate for so few.",
    },
    source: "Time estimates from my model scored on {date}.",
  },

  // "Compare with" (ticket 26; the 26 brief, sections 6.2 and 7.4): one comparison at a time, by the levers the
  // tool offers. Option words come from the lever and its value, in STEP's words where STEP has them.
  whatIf: {
    label: "Compare with",
    description: "Choose one approach to see how comparable packages that went with it compare. Choose it again to stop comparing.",
    segment: (option: string) => `Show how comparable packages that went with ${option} compare.`,
    none: "I have no other approach to compare for this package.",
    // A segment's label, and the option's words inside a sentence ("with open national").
    label_market_approach: {
      "Open - National": "Open national",
      "Open - International": "Open international",
      "Limited - National": "Limited national",
      "Limited - International": "Limited international",
    } as Record<string, string>,
    inSentence_market_approach: {
      "Open - National": "open national",
      "Open - International": "open international",
      "Limited - National": "limited national",
      "Limited - International": "limited international",
    } as Record<string, string>,
    lots: (count: number) => (count === 1 ? "1 lot" : `${count} lots`),
    label_prequalification: { Y: "Prequalification", N: "Post-qualification" } as Record<string, string>,
    inSentence_prequalification: { Y: "prequalification", N: "post-qualification" } as Record<string, string>,
    lever: { market_approach: "market approach", lots: "lots", prequalification: "qualification" },
    summary:
      "{k} of the {n} comparable packages went with {option}. With {option}, I estimate {w25} to {w75} months for the middle half and {w80} months for 8 in 10, against {b25} to {b75} and {b80} months as described.",
    abstain:
      "Only {k} of the {n} comparable packages went with {option}, so I'm not giving a time estimate for it. Their dots are the larger blue ones above.",
    abstainOne:
      "Only one of the {n} comparable packages went with {option}, so I'm not giving a time estimate for it. Its dot is the larger blue one above.",
    notInModel:
      "{k} of the {n} comparable packages went with {option}. My model doesn't read the number of lots, so I'm not giving a time estimate for it. Their dots are the larger blue ones above.",
    notLearned:
      "{k} of the {n} comparable packages went with {option}. My model never learned from a package that went with {option}, so I'm not giving a time estimate for it. Their dots are the larger blue ones above.",
    lotsReview: "Review type stays {reviewType}, because I compute it from the whole package's estimated amount.",
    // Row E's line while comparing, when there is no time estimate for the option.
    short: {
      too_few_in_subgroup: (k: string, option: string) => `Only ${k} went with ${option}, too few for a time estimate.`,
      not_in_model: "My model doesn't read lots, so no time estimate.",
      value_not_learned: "My model never learned from this, so no time estimate.",
      outside_training: "Outside what my model learned from, so no time estimate.",
    },
    key: {
      match: (k: string, option: string) => `${k} went with ${option}`,
      others: (rest: string) => `${rest} others`,
      open: "still open",
    },
    // Each dot's name while comparing, after its own.
    dot: {
      went: (option: string) => `Went with ${option}.`,
      not: (option: string) => `Did not go with ${option}.`,
      unknown: (lever: string) => `No record of ${lever}.`,
    },
    explainCount: (option: string, n: string) => `Comparable packages that went with ${option}, out of all ${n}. Select to see them.`,
    announce: {
      pressed: (option: string, k: string, n: string, w25: string, w75: string, b25: string, b75: string) =>
        `Comparing with ${option}. ${k} of ${n} comparable packages went with it. Middle half ${w25} to ${w75} months, against ${b25} to ${b75} as described.`,
      pressedNone: (option: string, k: string, n: string) =>
        `Comparing with ${option}. ${k} of ${n} comparable packages went with it, and I'm not giving a time estimate for it.`,
      released: (b25: string, b75: string) => `Stopped comparing. Middle half ${b25} to ${b75} months.`,
      criteria: (option: string) => `I stopped comparing with ${option} because the criteria changed.`,
    },
    table: {
      column: (option: string) => `Went with ${option}`,
      yes: "Yes",
      no: "No",
      unknown: "Not recorded",
    },
    // The evidence drawer's list of the packages a "{k} of {n}" count names (the 26 brief, section 7.8).
    drawer: {
      region: (option: string) => `Comparable packages that went with ${option}`,
      title: (k: string) => `${k} comparable packages`,
      titleOne: "One comparable package",
      sentence: (k: string, n: string, option: string) => `These ${k} of the ${n} comparable packages went with ${option}.`,
      sentenceOne: (n: string, option: string) => `This one of the ${n} comparable packages went with ${option}.`,
    },
  },

  // Section 4 of the package workspace, "Procurement approach options" (ticket 26; the 26 brief, section 7.7). PPSD
  // is spelled out in section 3's instruction sentence, which comes first on the page.
  approachOptions: {
    eyebrow: "Planning, PPSD section 6",
    number: "4 ·",
    heading: "Procurement approach options",
    summary: "Comparable packages went with {count} approaches. The most common was {option1}, with {k1} of {n}.",
    summaryAllowed:
      "Comparable packages went with {count} approaches the thresholds allow for this package. The most common was {option1}, with {k1} of {n}.",
    summaryOne: "All {n} comparable packages went with {option1}, so I have no other approach to compare.",
    summaryOneRecorded:
      "{k1} of the {n} comparable packages went with {option1}. The rest don't record their whole approach, so I have no other approach to compare.",
    summaryOneRuledOut: (ruled: number) =>
      ruled === 1
        ? "{k1} of the {n} comparable packages went with {option1}. {ruled} went with an approach the thresholds rule out for this package, so I have no other approach to compare."
        : "{k1} of the {n} comparable packages went with {option1}. {ruled} went with approaches the thresholds rule out for this package, so I have no other approach to compare.",
    summaryNone: "None of the {n} comparable packages records its market approach, lots and qualification, so I can't list approach options.",
    summaryRuledOut: (ruled: number) =>
      ruled === 1
        ? "The one comparable package that records its market approach, lots and qualification went with an approach the thresholds rule out for this package, so I can't list approach options."
        : "The {ruled} comparable packages that record their market approach, lots and qualification went with approaches the thresholds rule out for this package, so I can't list approach options.",
    show: "Show the options",
    hide: "Hide the options",
    title: "{k1} of the {n} comparable packages went with {option1}, the most common approach.",
    // When the thresholds rule out approaches some comparable packages went with, the tool doesn't count each of
    // those, so the caption claims only the most common approach of those the thresholds allow.
    titleAllowed: "{k1} of the {n} comparable packages went with {option1}, the most common approach the thresholds allow for this package.",
    count: (count: string) => `Showing ${count} approaches, the most common first.`,
    unrecorded: (rest: number) =>
      rest === 1
        ? "{rest} of the {n} comparable packages doesn't record its market approach, lots and qualification, so I can't say which approach it went with."
        : "{rest} of the {n} comparable packages don't record their market approach, lots and qualification, so I can't say which approach they went with.",
    ruledOut: (ruled: number) =>
      ruled === 1
        ? "{ruled} of the {n} comparable packages went with an approach the thresholds rule out for this package, so I left that approach out."
        : "{ruled} of the {n} comparable packages went with approaches the thresholds rule out for this package, so I left those approaches out.",
    columns: {
      approach: "Approach",
      wentWith: "Went with it",
      wentWithNote: "Comparable packages",
      middle: "Middle half (months)",
      middleNote: "My time estimate for this package",
      in10: "8 in 10 within (months)",
    },
    approach: (market: string, lots: string, qualification: string) => `${market}, ${lots}, ${qualification}`,
    asDescribed: "As described above",
    kOfN: "{k} of {n}",
    cell: {
      too_few_in_subgroup: "No time estimate: only {k} went with it",
      not_in_model: "No time estimate: my model doesn't read lots",
      value_not_learned: "No time estimate: my model never learned from this approach",
      outside_training: "No time estimate: this package is outside what my model learned from",
    },
    note: "Review type stays {reviewType} for every approach, because I compute it from the whole package's estimated amount. The counts show what comparable packages went with. Other differences between those packages can explain their times.",
    source: "{sources}. Records run through {date}.",
    card: {
      wentWith: "{k} of {n} comparable packages went with it.",
      estimate: "My time estimate: {w25} to {w75} months for the middle half, {w80} months for 8 in 10.",
    },
    abstain: "I'm not listing approach options: only {n} comparable packages.",
    abstainOne: "I'm not listing approach options: only one comparable package.",
    // Lane 2 has no time estimate for another reason (no model scored yet, or an as-of date before the end of its
    // training data), so section 4 gives that reason and no count.
    noEstimate: "I'm not listing approach options, because I have no time estimate for this package.",
    waiting: "I'll list the options after you add your plan in section 1, or choose to see the past range without it.",
    empty: "I can't compare approaches for this package, because I have no comparable packages I can measure.",
    error: "I couldn't load the approach options.",
    tryAgain: "Try again",
  },

  // A package planned from a sentence (the 15 brief): the workspace at /packages/new and /packages/:id, its
  // "What I understood" card, its chip editors, its saved stamp and its section 1 additions. The words of each
  // field (its label, its add label and its options) are in the package form schema, config/package_form.toml,
  // which the copy lint checks too, so a field added there needs nothing here.
  packageWorkspace: {
    // "Suggest {n} PPSD risk rows" (ticket 36; the 36 brief, section 5.1): the workspace's one solid button, in the
    // sticky header from 768 px and under section 3's risks below that. {n} is your own selection's count.
    ppsdAction: {
      button: (count: number, countText: string) => (count === 1 ? "Suggest 1 PPSD risk row" : `Suggest ${countText} PPSD risk rows`),
      feedforward: "The draft waits in Drafts for you to check. I send nothing.",
      description:
        "I write a Risk Description and a Description of mitigation for each risk you selected, for the borrower's " +
        "Project Procurement Strategy for Development (PPSD).",
      heldLabel: "Suggest PPSD risk rows",
      // An implementing agency officer drafts rows for their own PPSD, so nothing is suggested to someone else (ticket 38;
      // the 38 brief, 5.6).
      agencyButton: (count: number, countText: string) => (count === 1 ? "Draft 1 PPSD risk row" : `Draft ${countText} PPSD risk rows`),
      agencyHeldLabel: "Draft PPSD risk rows",
      agencyDescription:
        "I write a Risk Description and a Description of mitigation for each risk you selected, for your Project " +
        "Procurement Strategy for Development (PPSD).",
      // "section 3" links to the risks section.
      heldNone: "Select the risks you want in {section} first.",
      heldNoneLink: "section 3",
      heldNoneInline: "Select at least one risk above first.",
      heldSaveFailed: "I couldn't save your selection, so I can't draft from it yet. Try again in section 3.",
      heldPreview: "This is a preview, so you can't start a draft.",
      asof: "I draft PPSD rows only from today's records, not from a past date.",
      existingYou: (date: string) => `You started suggested PPSD rows for this package on ${date}.`,
      existingTeammate: (author: string, date: string) => `${author} started suggested PPSD rows for this package on ${date}.`,
      existingLink: "Open the draft",
      stopped: "I stopped writing the PPSD rows and saved nothing.",
    },
    titleNew: "New package",
    title: (description: string, country: string) => `${description}, ${country}`,
    documentTitle: (title: string) => `${title} · Packages`,
    breadcrumbPackages: "Packages",
    referenceNone: "No STEP reference yet",
    purpose:
      "I read your sentence as the criteria below and compared them with past packages. A package gets its reference " +
      "when the implementing agency enters it in Systematic Tracking of Exchanges in Procurement (STEP).",
    stamp: {
      notSaved: "Not saved yet",
      saving: "Saving",
      justNow: "Saved just now",
      minutes: (minutes: number) => (minutes === 1 ? "Saved 1 minute ago" : `Saved ${minutes} minutes ago`),
      at: (time: string) => `Saved at ${time}`,
      on: (date: string) => `Saved ${date}`,
      failed: "Not saved",
      tryAgain: "Try again",
      preview: "Changes are off in a preview",
    },
    card: {
      heading: "What I understood",
      youWrote: "You wrote:",
      quoted: (sentence: string) => `"${sentence}"`,
      instruction: "Choose any part to change it.",
      guesses: (count: number, words: string) => (count === 1 ? `${words} guess to check.` : `${words} guesses to check.`),
      noGuesses: "No guesses left to check.",
    },
    // A chip's words, by the kind of its field. The suffixes say a chip's state in words (DESIGN.md section 10).
    chip: {
      computed: (label: string) => `${label} · computed`,
      guess: (label: string) => `${label} · guess`,
      amount: (amount: string) => `US$${amount}`,
      amountAbout: (amount: string) => `About US$${amount}`,
      count: (count: string, unit: string) => `${count} ${unit}`,
      // "Your plan:" is set in 600 weight.
      plan: "{yours} {months} months",
      planYours: "Your plan:",
      // The chip's description: its field, then where its value came from.
      described: (label: string, from: string) => `${label}. ${from}.`,
      from: {
        sentence: "From your sentence",
        default: "The default, since your sentence did not say",
        guess: "My guess",
        computed: "Computed from the thresholds",
        you: "You set this",
        empty: "No value yet",
      },
    },
    // The computed note under the chips, in the order its lines appear.
    note: {
      changed: (field: string, from: string, to: string, cause: string) =>
        `${field} changed from ${from} to ${to} because the ${cause} changed.`,
      intro: "I computed review type and market approach from the thresholds.",
      // {threshold} is written with its "US$", so the two never split across lines.
      review: "{category} of {threshold} or more go to prior review.",
      market: "In {country}, plans send {category} of {threshold} or more to international bidding.",
      threshold: (amount: string) => `US$${amount}`,
      // A computed value the thresholds no longer give, after the change named.
      emptied: (field: string, cause: string) => `${field} is now empty, because the thresholds give no value for the new ${cause}.`,
      assumed: (rating: string) => `I assumed the implementing agency's procurement risk is ${rating}, because I don't know it yet.`,
      youSet: (field: string, value: string, computed: string) => `You set ${field} to ${value}. The thresholds give ${computed}.`,
      // The value you set is the one the thresholds give, so the note names it once.
      youSetSame: (field: string, value: string) => `You set ${field} to ${value}, the same as the thresholds give.`,
      source: "{source}, as of {date}.",
      // A source the owner has not yet checked against a dated table.
      sourceUndated: "{source}.",
      // A threshold's tooltip names its entry in the thresholds file and its source.
      thresholdTip: (entry: string, source: string) => `From ${entry} in Strata's thresholds file. ${source}.`,
      noRule: "I can compute review type and market approach once you add the category, the estimated amount and the country.",
    },
    // Its first clause is the refusal's lead, so the two never drift apart (the 24 brief, section 5.6).
    refusal: `${REFUSALS.dividing_packages.lead.replace(/\.$/, "")}, so I computed review type from the whole package.`,
    // Each reading step, in progress, done, and still to come (listed in ink-muted, as the answer's steps are).
    steps: {
      read: { running: "Reading your sentence", done: "I read your sentence.", todo: "To do: read your sentence." },
      compute: {
        running: "Computing review type and market approach from the thresholds",
        done: "I computed review type and market approach from the thresholds.",
        todo: "To do: compute review type and market approach from the thresholds.",
      },
      save: { running: "Saving the package", done: "I saved the package.", todo: "To do: save the package." },
      compare: { running: "Finding comparable packages", done: "I found the comparable packages.", todo: "To do: find comparable packages." },
    },
    readDone: (count: string, guesses: string) => `I read ${count} criteria from your sentence. ${guesses}`.trim(),
    noPackageTitle: "I couldn't find a package in that sentence.",
    noPackageBody: "Say what is being bought, where, and about how much. For example: rural roads, Kenya, about US$15 million.",
    changeSentence: "Change the sentence",
    setYourself: "Set the criteria yourself",
    tryAgain: "Try again",
    // Why a sentence could not be read, by the workflow's error code (src/strata/packages/workflow.py).
    readErrors: {
      no_reader: "I can't read sentences here, because no model is connected. Nothing is saved yet.",
      agent_unavailable: "I couldn't read your sentence just now. Nothing is saved yet.",
      content_filter: "I couldn't read that sentence, because a content filter stopped it. Nothing is saved yet.",
      agent_output: "I couldn't read your sentence just now. Nothing is saved yet.",
      package_store: "I read your sentence, but I couldn't save the package just now. Nothing is saved yet.",
      internal: "I couldn't read your sentence just now. Nothing is saved yet.",
      dropped: "The connection dropped while I read your sentence. Nothing is saved yet.",
    } as Record<string, string>,
    saveFailed: "I couldn't save your last change.",
    loading: "Loading this package.",
    loadError: "I couldn't load this package just now. Try again in a moment.",
    notFoundTitle: "I can't find this package. It may have been removed, or it was saved by someone else.",
    notFoundBody: "Packages you plan are saved for you alone, and they are listed on the Packages tab.",
    notFoundLink: "Go to Packages",
    publicTitle: "Packages are not part of the public view.",
    publicBody: "The public view shows projects, lessons and data.",
    publicLink: "Go to Projects",
    preview: "Changes are off in a preview.",
    // The chip editor (the 15 brief, section 7.6).
    editor: {
      fromSentence: "From your sentence.",
      fromDefault: "Your sentence did not say, so I used the default.",
      fromComputed: "I computed this from the thresholds.",
      fromGuess: "This is my guess. Your sentence did not say.",
      fromYou: "You set this.",
      thresholdsGive: (value: string) => `The thresholds give ${value}.`,
      empty: "This has no value yet.",
      stepLine: (field: string, value: string) => `In STEP: ${field}, ${value}.`,
      picks: "Changing this updates the past range.",
      doesNotPick: "This doesn't change which packages I compare with.",
      amountReadBack: (amount: string) => `I read this as US$${amount}.`,
      oldName: (input: string) => `I read "${input}" as this, the name the Procurement Regulations use now.`,
      use: "Use this",
      keep: (value: string) => `Keep ${value}`,
      setYourself: "Set it yourself",
      useComputed: "Use the computed value",
      remove: "Remove this value",
      close: "Close",
      options: "Choices",
      unit: "months",
      errors: {
        amount: "I couldn't read that amount. Type a number in US dollars, such as 15 million.",
        months: (max: string) => `Type a number of months, from 0.5 to ${max}.`,
        count: (max: string) => `Type a whole number from 1 to ${max}.`,
        country: "I don't have that country in the World Bank's list. Choose one from the list.",
        text: "Type a few words about what is being bought.",
        choice: "Choose one of the options.",
      },
    },
    // What the live region says after a change (the 15 brief, section 8).
    announce: {
      setPicks: (label: string, value: string) => `${label} set to ${value}. Updating the past range.`,
      set: (label: string, value: string) => `${label} set to ${value}.`,
      removed: (label: string) => `${label} removed.`,
      recomputed: (field: string, from: string, to: string) => `${field} changed from ${from} to ${to}, computed from the thresholds.`,
      emptied: (field: string, cause: string) => `${field} is now empty, because the thresholds give no value for the new ${cause}.`,
      kept: (label: string, value: string) => `${label} kept as ${value}.`,
      // After a rerun, with section 1's title as it reads now: the finding, or the sentence that says why
      // there is no range.
      updated: (title: string) => `Updated. ${title}`,
    },
    // Section 1's additions for a planned package.
    section: {
      criteria: "Comparable packages: {list}.",
      review: (type: string) => `${type} review`,
      notices: (from: string, to: string) => `notices from ${from} to ${to}`,
      promptQuestion:
        "How many months does your plan allow from bid notice to signed contract? I ask before I show the past range, so " +
        "the range doesn't set your plan.",
      promptFound: (count: number, words: string) =>
        count === 1 ? "I found one comparable package for these criteria." : `I found ${words} comparable packages for these criteria.`,
      promptLabel: "Your plan, in months",
      showRange: "Show the past range",
      showWithout: "Show it without a plan",
      updating: "Finding comparable packages for your new criteria.",
      more: "To compare with more packages, change a criterion above.",
      noneFound: "I found no comparable packages for these criteria. To compare with more packages, change a criterion above.",
      error: "I couldn't get the past range just now. Your criteria are saved. Try again in a moment.",
      errorUnsaved: "I couldn't get the past range just now. Try again in a moment.",
      missing: "{list}, and I'll find comparable packages.",
      missingStart: "Add",
    },
  },

  // Section 3 of the package workspace, procurement risks and what helped (ticket 30; the 30 brief, section 6).
  // Every number in it is a count the risk-table builder returned (src/strata/packages/risks.py); the page
  // never counts, ranks or picks the most common risk. Risk names are the closed list's labels
  // (config/lessons.toml), in straight double quotes inside a sentence.
  packageRisks: {
    // The ticket's exact words; uppercase through CSS.
    eyebrow: "Planning · PPSD section 3",
    // Hidden from screen readers, so the heading reads "Procurement risks and what helped".
    number: "3 ·",
    heading: "Procurement risks and what helped",
    intro:
      "These risks came up again and again in the completion reports of projects with comparable packages. Each one has a lesson on what helped and the reports that say so.",
    // Where PPSD is spelled out on this screen (DESIGN.md section 7, rule 10).
    instruction:
      "Select the risks that belong in section 3 of the borrower's Project Procurement Strategy for Development (PPSD). I save your choice with this package.",
    // The finding, the table's title: Fill templates whose {k} and {m} are Num values.
    finding: '"{risk}" came up most often, in {k} of the {m} completion reports for projects with comparable packages.',
    findingTwo: '"{a}" and "{b}" came up most often, each in {k} of the {m} completion reports for projects with comparable packages.',
    findingMany: "{tied} of these risks came up most often, each in {k} of the {m} completion reports for projects with comparable packages.",
    countOne: "Showing one risk.",
    count: (shown: string) => `Showing ${shown} risks, in the order I ranked them.`,
    // The person's own count, so plain text, not a finding.
    selected: (selected: string, shown: string) => `You selected ${selected} of the ${shown} risks for the PPSD.`,
    selectedNone: "You haven't selected a risk for the PPSD yet.",
    dropped: (risk: string) => `You selected "${risk}" before, but it is no longer in the table, so I don't count it.`,
    droppedMany: (count: string, risks: string) =>
      `You selected ${count} risks before that are no longer in the table, so I don't count them: ${risks}.`,
    // A risk's name in a list of names inside a sentence.
    quoted: (risk: string) => `"${risk}"`,
    saveFailed: "I couldn't save your selection. It still applies on this page.",
    saveFailedSpoken: "I couldn't save your selection.",
    tryAgain: "Try again",
    preview: "Changes are off in a preview.",
    columns: {
      select: "Select for the PPSD",
      risk: "Risk",
      often: "How often",
      oftenNote: "In completion reports for projects with comparable packages",
      helped: "What helped",
      helpedNote: "A lesson from the library, at its current version",
      sources: "Sources",
      sourcesNote: "The reports that say so. Select one to read its paragraph beside this page.",
    },
    // The How often cell: "{k} of {m}" in Num, then this on the next line.
    reports: "completion reports",
    helpedLabel: "What helped",
    sourcesLabel: "Sources",
    checkbox: (risk: string) => `Select ${risk} for the PPSD`,
    countName: (k: string, m: string, risk: string) => `${k} of ${m} completion reports, for ${risk}`,
    // A source pill's visible name: one formatter for every pill (web/src/lib/risks.ts, pillText), which the
    // PPSD draft's footnotes reuse (the 36 brief). A later pill from the same project drops the P-code.
    pill: "{doc} {pcode} {locator}",
    pillNoProject: "{doc} {locator}",
    pillParagraph: "¶{para}",
    pillParagraphSpoken: "paragraph {para}",
    // The pill's accessible name: its visible words, ¶ heard as "paragraph" (WCAG 2.5.3), then this.
    pillNameAfter: (docType: string, date: string, opened: boolean) => `, ${docType}, ${date}${opened ? ", opened" : ""}`,
    pillsLabel: "Sources",
    numTips: {
      k: (k: string) => `Completion reports for projects with comparable packages that raised this risk. Select to see the ${k}.`,
      tie: (k: string) => `Each of these risks came up in ${k} completion reports. Select a row's count to see its reports.`,
      m: (m: string) => `Completion reports of projects with comparable packages that I read. Select to see all ${m}.`,
      counted: "Counted from the records behind this section. Data readiness lists them by source.",
    },
    removed: {
      none: "I removed no risks.",
      one: "I removed one risk.",
      several: (count: string) => `I removed ${count} risks.`,
      // Two is "both", never "all two", as the answer's removed box says it.
      all: (count: number, countText: string) => (count === 2 ? "I removed both risks." : `I removed all ${countText} risks.`),
      allOne: "I removed the one risk I found.",
      // What a removed row said, as the removed box reports it.
      saidCount: (risk: string, k: string, m: string) => `"${risk}" came up in ${k} of ${m} completion reports`,
      saidHelped: (risk: string, lesson: string) => `what helped with "${risk}" was "${lesson}"`,
      // Each removed row after the first, under "The others:".
      item: (said: string, reason: string) => `It said ${said}. ${reason}`,
      // The 24 brief's reasons, word for word, except a source not retrieved, which names the package.
      reasons: {
        id_not_returned: {
          item: "It cited a source I did not retrieve for this package.",
          joined: "it cited a source I did not retrieve for this package",
        },
      } as Record<string, { item: string; joined: string }>,
    },
    noteLabel: "Note:",
    // The ranking sentence says what the builder's ranking does (src/strata/packages/risks.py, rank); the two
    // change together (CLAUDE.md rule 4).
    note: (most: string) =>
      `I counted the completion reports of projects that had comparable packages, found with the criteria in section 1. I ranked the risks by how closely their lessons match this package and how strong their evidence is, never by how often people used a lesson. I show at most ${most}.`,
    abbr: "ICR is the Implementation Completion and Results Report. An ICR Review is the Independent Evaluation Group's (IEG's) review of it.",
    abbrPpar: "PPAR is IEG's Project Performance Assessment Report.",
    // The coverage line: Fill templates whose numbers are Num values. A reason follows "; " and the first
    // sentence, and a second reason follows ", and ".
    coverage: {
      some: "Based on the completion reports of {m} of the {p} projects with comparable packages",
      all: "Based on the completion reports of all {p} projects with comparable packages.",
      allOne: "Based on the completion report of the one project with comparable packages.",
      join: "; ",
      and: ", and ",
      end: ".",
      reasons: {
        no_report: { one: "{n} has no completion report yet", many: "{n} have no completion report yet" },
        not_read: { one: "{n} had a completion report I couldn't read", many: "{n} had a completion report I couldn't read" },
      } as Record<string, { one: string; many: string }>,
      link: "Data readiness for these sources",
    },
    sourceLine: "{names} and Strata's lesson library. Records run through {date}.",
    sourceLineAsOf: "{names} and Strata's lesson library. Records as of {date}.",
    empty: {
      missing: "Add {list} above, and I'll look for the risks that came up for comparable packages.",
      noComparables: "I found no comparable packages, so I have no completion reports to look in.",
      noComparablesPlanned: "Change a criterion above to compare with more packages.",
      noComparablesStep: "Data readiness shows which records I hold for this region and period.",
      noComparablesLink: "Open Data readiness",
      noReports: "None of the {p} projects with comparable packages has a completion report I could read.",
      noReportsOne: "The one project with comparable packages has no completion report I could read.",
      noReportsBody: "A project gets a completion report only after it closes.",
      noReportsLink: "See which completion reports I have read",
      noLessons: "I found {m} completion reports for projects with comparable packages, but no lesson in the library fits this package yet.",
      noLessonsOne: "I found one completion report for a project with comparable packages, but no lesson in the library fits this package yet.",
      noLessonsBody: "A lesson enters the library only after two people decide on it. When they add one that fits, it appears here.",
      allRemoved: "I don't have risks I can support with a source.",
      allRemovedBody: (written: string) => `I found ${written} risks, and each one failed a check.`,
      allRemovedBodyOne: "I found one risk, and it failed a check.",
    },
    loading: "Loading the risks for this package.",
    error: "I couldn't load the risks for this package.",
    errorCode: "If it fails again, quote this code: {code}.",
    // The evidence drawer's views of a row (the 30 brief, section 6.7).
    drawer: {
      fromPage: "From this page",
      helped: "What helped: {lesson}",
      version: "Lesson version {version}, decided on {date}.",
      iegRestates: "IEG's review restates this lesson",
      iegWrote: 'IEG wrote in its {doc}: "{quote}"',
      awaiting: "This lesson rests on the completion report alone. IEG has not reviewed this project's completion report yet.",
      notRestated: "This lesson rests on the completion report alone. IEG's ICR Review did not restate it.",
      switcher: "Sources for this risk",
      tab: "{doc} {locator}",
      reportsEyebrow: "Why · evaluation",
      reportsTitle: "Completion reports that raised this risk",
      reportsFinding: '{k} of the {m} completion reports for projects with comparable packages raised "{risk}".',
      reportsNote: "Newest first.",
      reportEntry: "{doc}, {date}, paragraph {para}",
      allTitle: "Completion reports I counted",
      allSentence: (m: string) => `I counted the completion reports of ${m} projects with comparable packages.`,
      allSentenceOne: "I counted the completion report of one project with comparable packages.",
      allEntry: "{doc}, {date}",
      back: (count: string) => `Back to the ${count} reports`,
      backOne: "Back to the report",
      close: "Close the list",
      region: "{title}, for {risk}",
    },
  },

  // Section 2 of the package workspace, "Planned date for each step" (ticket 27; the 27 brief, section 7). The
  // steps' labels, STEP's full names, their phrases and stages are in the step-label registry, web/src/steps.ts.
  // Templates in braces are Fill templates whose numbers and dates are Num values from the tool.
  stepDates: {
    eyebrow: "Planning",
    // Hidden from screen readers, so the heading reads "Planned date for each step".
    number: "2 ·",
    heading: "Planned date for each step",
    // {first} and {last} are the family's first and last steps' phrases; the count is the registry's, in words.
    summarySteps: (countWords: string) => `${countWords} steps, from {first} to {last}.`,
    summaryLongest: "{stage} ran longest in {nm} comparable packages.",
    summaryPartial: (abstainWords: string, countWords: string) =>
      `I have too few comparable packages to date ${abstainWords} of the ${countWords}.`,
    // When every step lacks them, as on the fixture, never "six of the six".
    summaryPartialAll: (countWords: string) => `I have too few comparable packages to date any of the ${countWords}.`,
    // When some steps have no date for another reason, as the contract's completion when too many comparable
    // packages were still open: the tool counts every step it could not date, whatever the reason.
    summaryUndated: (undatedWords: string, countWords: string) => `I can't date ${undatedWords} of the ${countWords} steps.`,
    summaryUndatedAll: (countWords: string) => `I can't date any of the ${countWords} steps.`,
    summaryAbstain: "I'm not giving planned dates, because I found only {n} comparable packages.",
    summaryAbstainOne: "I'm not giving planned dates, because I found only one comparable package.",
    summaryAbstainNone: "I'm not giving planned dates, because I found no comparable package.",
    summaryNoFamily: "Add the category and method above, and I'll list the steps STEP uses for this kind of package.",
    summaryNotListed: (method: string) => `I don't have STEP's steps for ${method} yet, so I can't date them.`,
    show: "Show the steps",
    hide: "Hide the steps",
    error: "I couldn't load the planned dates for this package.",
    errorCode: "If it fails again, quote this code: {code}.",
    tryAgain: "Try again",
    introDelay: (family: string) =>
      `These are the steps STEP uses for ${family}. I dated each step by how far comparable packages ran past their planned dates. I measured from the dates as first published, because later plans can move them.`,
    introDuration: (family: string) =>
      `These are the steps STEP uses for ${family}. I dated each step from how long it took in comparable packages, using the dates in their published Procurement Plans.`,
    // No step has a date or days in either choice, as on the fixture, so no choice of dates is offered. {min} is
    // the tool's min_comparables.
    introNoneDated: (family: string) =>
      `These are the steps STEP uses for ${family}. I date a step only when {min} or more comparable packages recorded it.`,
    // The summary above already says how few comparable packages there were, so the intro does not repeat it.
    introAbstain: (family: string) =>
      `I give a date only from {min} comparable packages or more, because a date from fewer can mislead. Here are the steps STEP uses for ${family}, with how many comparable packages recorded each.`,
    start: {
      label: (phrase: string) => `Date of ${phrase}`,
      commit: "Date the steps",
      hint: "I date every later step from this one.",
      hintNoPlan: (phrase: string) => `The plan gives no date for ${phrase}. Add one, and I'll date every later step from it.`,
      errorEmpty: (phrase: string) => `Choose a date for ${phrase}.`,
      errorRange: (from: string, to: string) => `Choose a date from ${from} to ${to}.`,
      preview: "Changes are off in a preview.",
      dating: (date: string) => `Dating the steps from ${date}.`,
      failed: "I couldn't date the steps from this date. Try again in a moment.",
    },
    choice: {
      legend: "Date each step with",
      middle: "Middle dates: half ran later",
      cautious: (in10: string) => `Cautious dates: ${in10} in 10 ran later`,
      preview: "In a preview I don't save this choice.",
      saveFailed: "I couldn't save this choice. It still applies on this page.",
      saveFailedSpoken: "I couldn't save this choice.",
    },
    // The table's title, the caption: {date} is the signed contract's date in the choice shown.
    captionSigned: { cautious: "Cautious dates put the signed contract on {date}.", middle: "Middle dates put the signed contract on {date}." },
    captionPartial: (datedWords: string, countWords: string) => `I dated ${datedWords} of the ${countWords} steps.`,
    captionNone: "I couldn't date any of these steps.",
    // A package from a sentence whose only date is the one you gave its first step.
    captionNoneAfter: (phrase: string) => `I couldn't date any step after ${phrase}.`,
    captionUndated: "How many days each step took in comparable packages.",
    captionAbstain: (family: string) => `The steps STEP uses for ${family}.`,
    count: (countWords: string) => `Showing all ${countWords} steps.`,
    columns: {
      step: "Step",
      stepNote: "Short names. Choose one to see STEP's full name.",
      plan: "In the plan, as first published",
      planNote: "Plan of {date}",
      planNoteNone: "The plan's own dates",
      cautious: "Planned date, cautious",
      cautiousNote: (in10: string) => `My suggestion. ${in10} in 10 comparable packages ran later.`,
      middle: "Planned date, middle",
      middleNote: "My suggestion. Half of comparable packages ran later.",
      comparables: "Comparable packages",
      comparablesNote: "That recorded this step",
    },
    longest: "Ran longest in {nm}",
    inStep: (name: string) => `In STEP: ${name}`,
    termBody: (name: string) => `STEP calls this step "${name}".`,
    planMoved: "Moved to {date} in the plan of {plan}",
    planNone: "Not in the plan",
    // The day captions under a planned date. {days} is a Num. "plan's date" is joined by a no-break space, so a
    // narrow column never leaves "date" alone on its last line.
    days: {
      after: "{days} days after {previous}",
      afterOne: "{days} day after {previous}",
      afterPlan: "{days} days after the plan's\u00a0date",
      afterPlanOne: "{days} day after the plan's\u00a0date",
      onPlan: "On the plan's\u00a0date",
      beforePlan: "{days} days before the plan's\u00a0date",
      beforePlanOne: "{days} day before the plan's\u00a0date",
    },
    yours: "Your date",
    undated: "Not dated yet",
    undatedStart: "Add its date above.",
    abstain: "Only {n} comparable packages recorded this step, too few for me to date it.",
    abstainOne: "Only one comparable package recorded this step, too few for me to date it.",
    abstainNone: "No comparable package recorded this step, so I can't date it.",
    // {reached} of {n} comparable packages had reached the step by {date}, the records' date; the rest were still
    // open, too many to place the date.
    notReached: "Only {reached} of {n} comparable packages had reached this step by {date}, so I can't date it yet.",
    notReachedOne: "Only one of {n} comparable packages had reached this step by {date}, so I can't date it yet.",
    notReachedNone: "None of the {n} comparable packages had reached this step by {date}, so I can't date it yet.",
    notInPlan: "The plan gives this step no date to count from, so I can't date it.",
    needsEarlier: (phrase: string) => `I can't date this step without a date for ${phrase}.`,
    comparablesNone: "None",
    comparablesStart: "None used",
    countName: (n: string, label: string) => `${n} comparable packages for ${label}`,
    // The notes under the table.
    trackLabel: "Track record:",
    track: {
      cautious: "of {total} steps in packages from {year} that I had not seen, {inside} came on or before my cautious date. A well-sized cautious date catches about {catch} in 10.",
      middle: "of {total} steps in packages from {year} that I had not seen, {inside} came on or before my middle date. A well-sized middle date catches about half.",
    },
    actuals: (count: string) => `STEP records actual dates for ${count} of these steps. I suggest planned dates only and leave actual dates to STEP.`,
    actualsOne: "STEP records an actual date for one of these steps. I suggest planned dates only and leave actual dates to STEP.",
    coverage: "Based on {used} of {total} comparable packages; {missing} had no dates for these steps in their published plans.",
    coverageAll: "Based on all {total} comparable packages.",
    coverageLink: "Data readiness for these sources",
    sourceLine: "{names}. Records run through {date}.",
    sourceLineAsOf: "{names}. Records as of {date}.",
    // The section's live region (the 27 brief, section 8.5).
    loading: "Loading the planned dates.",
    showing: { cautious: "Showing cautious dates.", middle: "Showing middle dates." },
    // How many in 10 comparable packages ran later than a date, as the tool counted them. Five in 10 reads "about
    // half", as the choice and the column header say it.
    aboutIn10: "about {in10} in 10",
    aboutHalf: "about half",
    // What hover or focus on a number says, and what selecting it opens (the 27 brief, section 7.7). {about} is
    // aboutIn10 or aboutHalf.
    tips: {
      dateDelay:
        "For {longer} of {n} comparable packages, {about}, {step} came more than {days} days after the date first planned for it. I added {days} days to the plan's date. Select to see the {n} packages.",
      dateBefore:
        "For {longer} of {n} comparable packages, {about}, {step} came less than {days} days ahead of the date first planned for it. I counted {days} days back from the plan's date. Select to see the {n} packages.",
      dateDuration:
        "For {longer} of {n} comparable packages, {about}, {step} came more than {days} days after {previous}. I added {days} days to the date of {previous}. Select to see the {n} packages.",
      dateUndated:
        "For {longer} of {n} comparable packages, {about}, {step} came more than {days} days after {previous}. Add the date of {first} above, and I'll date this step. Select to see the {n} packages.",
      // The days of a step that needs an earlier step's date.
      daysNeedsEarlier:
        "For {longer} of {n} comparable packages, {about}, {step} came more than {days} days after {previous}. I have no date for {previous} to count from. Select to see the {n} packages.",
      count: (phrase: string) => `Comparable packages whose published plans recorded ${phrase}. Select to see them.`,
      longest: "Of the {m} comparable packages whose plans recorded every step up to the signed contract, {stage} ran longest in {n}. Select to see them.",
      track:
        "From the backtest for {year}: I dated the steps that plans published before {year} had planned for {year}, using only records public before {year}. Run {run}.",
      trackNoRun:
        "From the backtest for {year}: I dated the steps that plans published before {year} had planned for {year}, using only records public before {year}.",
      counted: "Counted from the records behind this section. Data readiness lists them by source.",
    },
    // The evidence drawer's two lists (the 27 brief, section 7.6).
    drawer: {
      title: (phrase: string) => `Comparable packages for ${phrase}`,
      fullName: (name: string) => `In STEP: ${name}.`,
      // {about_c} and {about_m} are aboutIn10 or aboutHalf.
      findingDelay:
        "For {longer_c} of {n} packages, {about_c}, {step} came more than {days_c} days after the date first planned for it. For {longer_m} of {n}, {about_m}, it came more than {days_m} days after.",
      findingDuration:
        "For {longer_c} of {n} packages, {about_c}, {step} came more than {days_c} days after {previous}. For {longer_m} of {n}, {about_m}, it came more than {days_m} days after.",
      findingAbstain: "Only {n} comparable packages recorded {step}, too few for me to date it. Here are all {n}.",
      findingAbstainOne: "Only one comparable package recorded {step}, too few for me to date it. Here it is.",
      findingCounts: "{n} comparable packages recorded {step}. Here are all {n}.",
      note: "Shortest first. Still-open packages had not recorded this step by {date}.",
      // On the delay basis each entry is days against its own first planned date, early ones first.
      noteDelay: "Earliest first. Still-open packages had not recorded this step by {date}.",
      entryDays: "{days} days",
      entryDay: "{days} day",
      // A comparable that reached the step after, on or before the date first planned for it (the delay basis).
      entryLate: "{days} days late",
      entryLateOne: "{days} day late",
      entryOnPlan: "On the planned date",
      entryBefore: "{days} days early",
      entryBeforeOne: "{days} day early",
      entryOpen: "Still open after {days} days",
      // A still-open comparable whose first planned date for the step came after the records' date.
      entryNotDue: "Not due yet",
      // Heard before an entry's reference and days, so its name holds its words on screen (WCAG 2.5.3).
      entryOpens: "Open the records for",
      longestTitle: "Which stage ran longest",
      longestFinding:
        "{stage} ran longest in {n} of {m} comparable packages. I counted the stages up to the signed contract, because the contract's completion measures its work, not its procurement.",
      longestNote: "Grouped by stage, the most common first, then by days, longest first.",
      longestEntry: "{stage}, {days} days",
      close: "Close the list",
    },
  },

  // Section 1's "Advertised again" block (ticket 28; the 28 brief, section 7), at the end of section 1's card.
  // Every {name} is a value rebidding_risk returned, which Num writes. "N of M" counts stay in numerals; a lone
  // count from one to nine is spelled out. Evidence is in the past tense; my model's estimate in the present.
  // It never says "risk", "re-bid" or "re-tender", and never that an agency or a bidder failed.
  rebid: {
    heading: "Advertised again",
    why: "No field in the records says a package was advertised again, so I worked this out from notices and plan rows, and I may have missed or miscounted some.",
    count: "{n} of the {m} comparable packages were advertised again.",
    countOne: "One of the {m} comparable packages was advertised again.",
    countAll: "All {m} comparable packages were advertised again.",
    countNone: "I found no sign that any of the {m} comparable packages were advertised again.",
    // The model's natural frequency, by the band the tool returned (never a percentage).
    model: "My model estimates that about {k} in 10 packages like this one are advertised again.",
    modelBelow1: "My model estimates that fewer than 1 in 10 packages like this one are advertised again.",
    modelAbove9: "My model estimates that more than 9 in 10 packages like this one are advertised again.",
    track: "Track record: in tests on {n} packages from {year} that it had not seen, my model matched what happened better than {baseline}.",
    // Each baseline the backtest compares against, by its code.
    baselines: { comparables_rate: "the rate among their comparable packages" } as Record<string, string>,
    // Why the model is held back, by the tool's not_shown_reason.
    off: {
      too_few: "I'm not giving an estimate: I give one only from {min} or more comparable packages.",
      not_better: "I'm not giving an estimate: in tests on {n} packages from {year} that my model had not seen, it did no better than {baseline}.",
      no_results: "I'm not giving an estimate: my model has no test results yet.",
      not_scored: "I'm not giving an estimate: my model scores the packages in Procurement Plans each night, and it has no score for this one yet.",
    } as Record<string, string>,
    compareNote: "The comparison above doesn't change this count. It is for this package's own criteria.",
    denominator: "I counted {m} packages here and {total} in the past range, because {reason}.",
    denominatorReasons: {
      canceled_included: "the past range leaves out canceled packages, and a canceled package counts here",
    } as Record<string, string>,
    listShow: "Show the {n} packages and their reasons",
    listShowOne: "Show the package and its reason",
    listHide: "Hide the packages",
    listHideOne: "Hide the package",
    more: "Show {count} more",
    moreOne: "Show one more",
    groupCount: "{c} of {n}",
    groupName: (label: string, c: string, n: string) => `${label}, ${c} of the ${n} packages`,
    // Each group's heading, by the tool's reason code (config/tools.toml, rebidding_risk's reasons). A code with
    // no heading here takes other's.
    reasons: {
      all_bids_rejected: "All bids were rejected",
      process_canceled: "The process was canceled",
      again_no_reason: "Advertised again, with no reason given",
      no_award: "No award followed the notice",
      canceled_row: "Canceled in the Procurement Plan",
      other: "Another reason was given",
    } as Record<string, string>,
    // A row's second line when no notice gave a reason in words, by its row_kind; again is trail.notice.again.
    noAward: "Its notice was published on {notice}, and no award followed in the records through {through}.",
    canceledRow: 'The Procurement Plan of {plan} gave its Process Status as "{status}".',
    quoted: (text: string) => `"${text}"`,
    // A row's third line: one sentence per record, in the order of its markers.
    sources: {
      notice: "Notice {id}, published {date}.",
      award_notice: "Award notice {id}, published {date}.",
      plan_row: "Procurement Plan, {agency}, version of {date}.",
    } as Record<string, string>,
    inLanguage: {
      notice: (language: string) => `In ${language}, as the notice gives it.`,
      award_notice: (language: string) => `In ${language}, as the award notice gives it.`,
    } as Record<string, (language: string) => string>,
    // A marker's source, in its accessible name (brief 22's record form): "Source 3: Notice OP00083890, February 4, 2020".
    markers: {
      notice: (id: string, date: string) => `Notice ${id}, ${date}`,
      award_notice: (id: string, date: string) => `Award notice ${id}, ${date}`,
      plan_row: (ref: string, date: string) => `Procurement Plan row ${ref}, ${date}`,
    } as Record<string, (reference: string, date: string) => string>,
    // The drawer's tab for each record of a row with two or more (the 28 brief, section 8.3).
    tabs: {
      notice: (id: string) => `Notice ${id}`,
      award_notice: (id: string) => `Award notice ${id}`,
      plan_row: (ref: string) => `Procurement Plan row ${ref}`,
    } as Record<string, (reference: string) => string>,
    openRecords: (ref: string) => `Open the records for ${ref}`,
    noneNext: "If a notice is missing from the records, I can't see that its package was advertised again.",
    noneLink: "See how complete the notices are",
    source: "{sources}. Records run through {through}.",
    sourceAsOf: "{sources}. Records as of {asOf}.",
    error: "I couldn't load the count of packages advertised again.",
    errorCode: "If it fails again, quote this code: {code}.",
    tryAgain: "Try again",
    // What each number counts, in its tooltip (the 28 brief, section 7.5).
    tips: {
      n: "Packages I counted as advertised again. Select to see each one and its reason.",
      m: "The comparable packages in the past range above. Select to see the ones advertised again.",
      mOther: "The comparable packages I counted for this. Select to see the ones advertised again.",
      k: "From my rebidding model, scored on {date} and rounded to the nearest 1 in 10.",
      track: "From my model's saved test results of {date}.",
      min: "The smallest number of comparable packages I give an estimate from.",
    },
    // The evidence drawer opened from a row: the row's line as the claim, and its records as tabs.
    fromPage: "From this page",
    switcher: "Sources for this sentence",
  },

  // Section 5 of the package workspace, "Check your criteria" (ticket 31; the 31 brief, section 6). Every
  // {name} is a value a tool, the workflow or the verifier returned, which Num writes. Every sentence says
  // "qualification criteria" for the bidding document's requirements, so it is never read as the criteria that
  // chose the comparable packages, and "cost estimate" in full.
  criteria: {
    eyebrow: "Tender design",
    number: "5 ·",
    heading: "Check your criteria",
    // The collapsed summary's first sentence holds the ticket's words: "optional. Paste your qualification
    // criteria to compare them with N packages whose criteria are public."
    summary: "This check is optional. Paste your qualification criteria to compare them with {n} packages whose criteria are public.",
    summaryOne:
      "This check is optional. Paste your qualification criteria to compare them with one package whose criteria are public.",
    summaryCompared:
      "This check is optional. On {date}, you compared {count} items in your qualification criteria with {n} packages whose criteria are public.",
    summaryComparedOne:
      "This check is optional. On {date}, you compared one item in your qualification criteria with {n} packages whose criteria are public.",
    summaryNonePublic:
      "This check is optional. None of the {total} comparable packages published their qualification criteria, so I can't compare yours yet.",
    summaryAlso: "It also covers rejected bids, cost estimates and lessons from comparable packages.",
    summaryAlsoNonePublic: "It still covers rejected bids, cost estimates and lessons from comparable packages.",
    summaryNoComparables:
      "This check is optional, and it needs comparable packages. I have none for this package yet, so there is nothing to compare your qualification criteria with.",
    summaryError: "I couldn't count the comparable packages whose criteria are public.",
    show: "Show the check",
    hide: "Hide the check",
    tryAgain: "Try again",
    code: "If it fails again, quote this code: {code}",
    loading: "Loading the check of your qualification criteria.",
    nTooltip: "Comparable packages whose notices published their qualification criteria. Select to see them.",
    intro:
      "Paste the qualification criteria from the bidding document. I break them into items, such as similar experience and average annual turnover, and compare each item with the {n} comparable packages whose criteria are public. The rejected bids, the cost estimate and the lessons below don't need your text.",
    introOne:
      "Paste the qualification criteria from the bidding document. I break them into items, such as similar experience and average annual turnover, and compare each item with the one comparable package whose criteria are public. The rejected bids, the cost estimate and the lessons below don't need your text.",
    // The summary above already says none are public, so the open section does not say it again.
    introNonePublic: "The rejected bids, the cost estimate and the lessons below come from the same comparable packages.",
    introNonePublicLink: "See how complete the notices are",
    field: {
      label: "Your qualification criteria",
      hint: "Paste them as the bidding document writes them. When you compare them, I save the text with this package, and only you can see it.",
      count: "{used} of {max} characters",
    },
    compare: "Compare the criteria",
    status: {
      running: "Comparing your qualification criteria.",
      edited: "You changed the text after I compared it. Compare the criteria again to update the table below.",
    },
    error: {
      empty: "Paste your qualification criteria first.",
      tooLong: "Your text is longer than {max} characters. Paste only the qualification criteria.",
    },
    preview: "Changes are off in a preview.",
    // The steps of each run (the 31 brief, section 6.3): the step in progress, then once it is done.
    steps: {
      notices: { running: "Finding the award notices of comparable packages", done: "Found the award notices of comparable packages" },
      reasons: { running: "Reading why bids were rejected", done: "Read why bids were rejected" },
      cost: { running: "Comparing signed amounts with cost estimates", done: "Compared signed amounts with cost estimates" },
      lessons: {
        running: "Finding lessons on cost estimates and specifications",
        done: "Found lessons on cost estimates and specifications",
      },
      checks: { running: "Checking each sentence against its sources", done: "Checked each sentence against its sources" },
      read: { running: "Reading your qualification criteria", done: "Read your qualification criteria" },
      find: {
        running: "Finding comparable notices that published their criteria",
        done: "Found comparable notices that published their criteria",
      },
      compare: { running: "Comparing each item", done: "Compared each item" },
    } as Record<string, { running: string; done: string }>,
    // The check line over the whole section (the 31 brief, section 6.4). A quote from a notice or an award
    // notice has no page, so the line then says the quotes are in their sources.
    quotesInSources: { one: "{part} of {whole} quote is in its source", many: "{part} of {whole} quotes are in their sources" },
    notCheckedItems: "whether I found every item in your qualification criteria",
    removedInPlace: "I removed this sentence. The reason is in the box above.",
    // A quote from an award notice that is not in it: the notice is a record, with no pages (removed.reasons'
    // quote_not_on_page in this section's words).
    quoteNotInSource: { item: "The quote is not in the record it cites.", joined: "the quote is not in the record it cited" },
    // A reading of your words that check 4's judge said does not follow from them: its source is your text.
    readingNotSupported: { item: "Your words do not say this.", joined: "your words do not say that" },
    // Why a run could not finish, by its code (src/strata/criteria/workflow.py, COMPARE_ERRORS).
    // unsaved: the request never reached the server, so the text was not saved either.
    errors: {
      no_reader: "I can't read qualification criteria right now, because no model is connected. Your text is saved.",
      agent_unavailable: "I couldn't compare your qualification criteria just now. Your text is saved.",
      content_filter: "I couldn't read your text, because a content filter stopped it. Try pasting only the qualification criteria, without the rest of the bidding document.",
      agent_output: "I couldn't compare your qualification criteria just now. Your text is saved.",
      store: "I couldn't save your text. It is still in the box.",
      data_service: "I couldn't compare your qualification criteria just now. Your text is saved.",
      internal: "I couldn't compare your qualification criteria just now. Your text is saved.",
      unsaved: "I couldn't compare your qualification criteria just now. Your text is still in the box.",
    } as Record<string, string>,
    // Part 1: your criteria, item by item.
    items: {
      heading: "Your criteria, item by item",
      caption: "I compared {count} items in your qualification criteria with the {n} comparable packages whose criteria are public.",
      captionOne: "I compared one item in your qualification criteria with the {n} comparable packages whose criteria are public.",
      count: "Showing all {count} items.",
      countBoth: "Showing both items.",
      countOne: "Showing the one item.",
      columns: {
        item: "Item",
        itemDefinition: "The kinds of requirement I compare",
        words: "Your words",
        wordsDefinition: "From your text, and how I read them",
        asked: "Asked for it",
        askedDefinition: "Of the {n} whose criteria are public",
        sameOrLess: "Asked for the same or less",
        sameOrLessDefinition: "Of the notices I could compare with yours",
      },
      rejected: "{r} comparable packages had bids rejected over this",
      rejectedOne: "One comparable package had bids rejected over this",
      quoted: (words: string) => `"${words}"`,
      shortened: ", shortened",
      reading: "I read this as {reading}",
      more: "{more} asked for more",
      different: "{different} set it in other terms",
      none: "None",
      noneToCompare: "No notice to compare",
      noneCompared: "None I could compare",
      removed: "I removed this comparison. The reason is in the box above.",
      staleComparables:
        "The comparable packages changed after I compared your qualification criteria. Compare the criteria again to update this table.",
      unplaced: "I didn't compare {k} parts of your text, because they set no item I compare.",
      unplacedOne: "I didn't compare one part of your text, because it sets no item I compare.",
      showThem: "Show them",
      hideThem: "Hide them",
      showIt: "Show it",
      hideIt: "Hide it",
      order:
        "I count a notice as asking for less than you when none of its parts is higher than yours and at least one is lower or left out, and as asking for more the other way round. A notice that asked for more contracts but a smaller amount for each, for example, set it in other terms.",
      // The coverage line: one idea a sentence, each count a Num with a capital where it starts the sentence.
      coverage: "Based on {n} of {total} comparable packages.",
      coverageMissing: "{missing} of them published no qualification criteria.",
      coverageOpen: "I left out {open} that were still open, because I don't compare a tender that is still open.",
      coverageAll: "Based on all {total} comparable packages.",
      coverageLink: "Data readiness for these sources",
      // {sources} is each source's dataset name from the tool, joined as a list; {through} is the day the
      // records run through, the same in every part, and {asOf} the page's as-of date (the 31 brief, 6.5).
      source: "{sources}. Records run through {through}. Compared on {compared}.",
      sourceAsOf: "{sources}. Records as of {asOf}. Compared on {compared}.",
      noneFound:
        "I found no qualification criteria in your text. Paste the part of the bidding document that sets them, such as the experience, turnover, equipment and key staff that bidders need.",
      error: "I couldn't compare your qualification criteria just now. Your text is saved.",
      // Num hover text (the 31 brief, section 6.10).
      statedTooltip: (phrase: string) => `Comparable notices that set ${phrase}. Select to see each one and what it asked for.`,
      sameOrLessTooltip: (phrase: string) => `Notices that asked for the same as you or less on ${phrase}. Select to see them.`,
      moreTooltip: (phrase: string) => `Notices that asked for more than you on ${phrase}. Select to see them.`,
      differentTooltip: (phrase: string) =>
        `Notices that set ${phrase} in a way I can't put in order with yours, such as more contracts of a smaller size. Select to see them.`,
      // A count's accessible name: the visible count plus its meaning.
      statedName: (count: string, phrase: string) => `${count} comparable notices set ${phrase}`,
      sameOrLessName: (count: string, phrase: string) => `${count} notices asked for the same or less on ${phrase}`,
    },
    // Refusals inside the section (the 31 brief, section 6.6): the key's lead, then this section's own sentence.
    refusal: {
      instead:
        "Paste only the qualification criteria from the bidding document, and I'll compare them with comparable packages whose criteria are public.",
      partial: "I compared the qualification criteria in your text and left out the rest.",
    },
    // Part 2: rejected bids (brief 28's reasons list).
    rejected: {
      heading: "Rejected bids",
      count: "{n} of {m} comparable packages had bids rejected.",
      countOne: "One of the {m} comparable packages had bids rejected.",
      countAll: "All {m} comparable packages had bids rejected.",
      countNone: "None of the {m} comparable packages had bids rejected.",
      denominator:
        "I counted the {m} comparable packages with an award notice in the records, out of {total} in all. Award notices list the rejected bids.",
      intro: "I quoted each reason from its award notice. I grouped the reasons by what they concerned, so a package can appear in more than one group.",
      groupCount: "{c} of {n}",
      groupName: (label: string, c: string, n: string) => `${label}, ${c} of the ${n} packages`,
      yours: "Your criteria set this item.",
      notice: "Award notice {id}, published {date}.",
      sameNotice: "{b} bids were rejected over this in the same award notice.",
      inLanguage: (language: string) => `In ${language}, as the award notice gives it.`,
      showMore: "Show {count} more",
      showOneMore: "Show one more",
      noneNext: "If an award notice is missing from the records, I can't see its rejected bids.",
      noneLink: "See how complete the award notices are",
      noNotices: "I found no award notices for the comparable packages, so I can't count rejected bids.",
      source: "{sources}. Records run through {through}.",
      sourceAsOf: "{sources}. Records as of {asOf}.",
      error: "I couldn't load the rejected bids just now.",
      openRecords: (ref: string) => `Open the records for ${ref}`,
      countTooltip: "Comparable packages with an award notice in the records. Select to see the ones with rejected bids.",
      // A marker's source, in its accessible name (brief 28's record form): "Source 3: Award notice OP00125282, April 14, 2021".
      markerSource: (id: string, date: string) => `Award notice ${id}, ${date}`,
      markerSourceUndated: (id: string) => `Award notice ${id}`,
    },
    // The drawer's views of section 5's lists (the 31 brief, section 6.11 A and B).
    drawer: {
      eyebrow: "What · notice",
      publicTitle: "{n} packages whose criteria are public",
      publicTitleOne: "One package whose criteria are public",
      publicSentence: "These comparable packages published their qualification criteria in their notices.",
      notice: "Notice {id}, published {date}.",
      itemTitle: "Comparable notices on {phrase}",
      fromPage: "From this page",
      claim: "{same} of {compared} comparable notices asked for the same as you or less on {phrase}.",
      youAsked: "You asked for: {words}",
      groups: { less: "Asked for less", same: "Asked for the same", more: "Asked for more", different: "Set in other terms" } as Record<string, string>,
      groupCount: "{label} ({count})",
      openNotice: "Open notice {id}",
      notStated: "{count} of the {n} comparable packages whose criteria are public didn't set {phrase}.",
      back: "Back to the {n} notices",
      backOne: "Back to the notice",
      backPackages: "Back to the {n} packages",
      close: "Close the list",
      region: (title: string) => title,
    },
    loadingRun: "Loading the rejected bids, the cost estimate and the lessons.",
    runDone: "The rejected bids, the cost estimate and the lessons are ready.",
    compareDone: (count: number, words: string) =>
      count === 1 ? "I compared one item in your qualification criteria." : `I compared ${words} items in your qualification criteria.`,
    noneFoundDone: "I found no qualification criteria in your text.",
    runError: "I couldn't load the rejected bids, the cost estimate and the lessons just now.",
  },

  // Part 3 of section 5: the cost estimate (the 31 brief, section 6.8). A package's difference from its own cost
  // estimate is a measurement of one package, not a share of a group, so it may be a percentage under 20 cases
  // (DESIGN.md section 7, rule 11).
  cost: {
    heading: "The cost estimate",
    intro:
      "Your cost estimate is {estimate}. The comparable packages had cost estimates from {low} to {high}. Each dot below is one of them, placed by how far its signed amount was from its own cost estimate.",
    introNoEstimate:
      "The plan row gives no cost estimate for this package. The comparable packages had cost estimates from {low} to {high}. Each dot below is one of them, placed by how far its signed amount was from its own cost estimate.",
    amount: (amount: string) => `US$${amount}`,
    title: "{above} of {m} comparable packages were signed above their cost estimates.",
    titleOne: "One of the {m} comparable packages was signed above its cost estimate.",
    titleAll: "All {m} comparable packages were signed above their cost estimates.",
    titleNone: "None of the {m} comparable packages were signed above their cost estimates.",
    subtitle: "Signed amount against the package's own cost estimate, %",
    line: "At the cost estimate",
    below: "{below} signed below",
    above: "{above} signed above",
    middleLabel: "Middle half {q25} to {q75}, middle {q50}",
    middle:
      "The middle half of these {m} packages were signed between {q25} and {q75} their cost estimates. The middle package was signed {q50} its cost estimate.",
    at: "{at} were signed at exactly their cost estimates.",
    atOne: "One was signed at exactly its cost estimate.",
    abstain: "I'm not giving a range: only {m} comparable packages had both a cost estimate and a signed contract. Here are all {m}.",
    abstainOne: "I'm not giving a range: only one comparable package had both a cost estimate and a signed contract. Here it is.",
    none:
      "I can't compare the cost estimate, because none of the comparable packages had both a cost estimate in its Procurement Plan and a signed contract.",
    coverage: "Based on {m} of {total} comparable packages; {gaps}.",
    // With no package to compare, "Based on 0 of ..." says nothing the sentence above has not: only the reasons.
    coverageNone: "Of the {total} comparable packages, {gaps}.",
    coverageOpen: "{open} had no signed contract yet",
    coverageNoEstimate: "{none} had no cost estimate in their Procurement Plan",
    coverageNoUsd: "{usd} were signed only in a local currency",
    coverageAnd: ", and ",
    coverageComma: ", ",
    coverageAll: "Based on all {total} comparable packages.",
    coverageLink: "Data readiness for these sources",
    source: "{sources}. Records run through {through}.",
    sourceAsOf: "{sources}. Records as of {asOf}.",
    showTable: "Show the table",
    hideTable: "Hide the table",
    tableCount: "Showing all {m} packages.",
    tableCountOne: "Showing the one package.",
    columns: {
      package: "Package",
      country: "Country",
      estimated: "Estimated Amount (US$)",
      estimatedDefinition: "In its Procurement Plan",
      signed: "Signed amount (US$)",
      signedDefinition: "All contracts the package signed",
      diff: "Against the cost estimate (%)",
      diffDefinition: "Above the cost estimate is positive",
    },
    openRecords: (ref: string) => `Open the records for ${ref}`,
    // A dot's tooltip and accessible name.
    tooltipLine: "Signed for {signed} against a cost estimate of {estimate}, in {country}.",
    tooltipLineNoCountry: "Signed for {signed} against a cost estimate of {estimate}.",
    tooltipOpen: "Press Enter or click to open its records.",
    tooltipOpenTouch: "Open its records",
    dotName: (ref: string, diff: string) => `${ref}, signed ${diff} its cost estimate`,
    alt: "One dot for each of {m} comparable packages, placed by how far its signed amount was from its own cost estimate. {below} were signed below, {at} at, and {above} above their cost estimates.",
    altMiddle: "The middle half ran from {q25} to {q75}, and the middle package was {q50}.",
    countTooltip: "Comparable packages with both a cost estimate and a signed contract. Select to see the table.",
    error: "I couldn't load the cost comparison just now.",
    // The drawer's view of one comparable package's cost records (the 31 brief, section 6.11 E).
    drawer: {
      eyebrow: "How · operations",
      title: "Cost records of {ref}",
      finding: "Its contracts were signed for {signed}, {diff} its cost estimate of {estimate}.",
      planRow: "Procurement Plan row {ref}",
      planFrom: "Procurement Plan of {date}, PDF page {page}.",
      estimated: "Estimated Amount (US$)",
      contract: "Contract {id}",
      signedOn: "Signed {date}",
      amount: "Signed amount (US$)",
      sum: "The signed amount above adds every contract this package signed.",
      close: "Close the cost records",
      region: (ref: string) => `Cost records for comparable package ${ref}`,
    },
  },

  // Part 4 of section 5: lessons on cost estimates and specifications (the 31 brief, section 6.9).
  criteriaLessons: {
    heading: "Lessons on cost estimates and specifications",
    intro:
      "Lessons from completion reports that a lead procurement specialist added to the library. I rank them by how well they fit this package and how strong their evidence is, never by how often people open them.",
    groups: { cost_estimates: "Cost estimates", designs_and_specifications: "Specifications" } as Record<string, string>,
    eyebrow: "Why · evaluation",
    quoted: (quote: string) => `"${quote}"`,
    sourceLead: "Source:",
    // The first ICR and IEG on the screen are spelled out (DESIGN.md section 7, rule 22).
    icrSpelled: "Implementation Completion and Results Report (ICR)",
    sourceLine: "{type}, {pid}, {date}, paragraph {para}, page {page}.",
    sourceLineSection: "{type}, {pid}, {date}, section {para}, page {page}.",
    // The marker's source, in its accessible name ("Source 5: Implementation Completion and Results Report,
    // October 10, 2019, paragraph 54").
    markerParagraph: (type: string, date: string, para: string) => `${type}, ${date}, paragraph ${para}`,
    markerSection: (type: string, date: string, section: string) => `${type}, ${date}, section ${section}`,
    status: {
      restated: "Lesson version {v}. IEG's ICR Review restated it.",
      restatedSpelled: "Lesson version {v}. The Independent Evaluation Group (IEG) restated it in its ICR Review.",
      awaiting: "Lesson version {v}. Awaiting IEG review.",
      awaitingSpelled: "Lesson version {v}. Awaiting review by the Independent Evaluation Group (IEG).",
      ieg_lesson: "Lesson version {v}. IEG's lesson.",
      not_restated: "Lesson version {v}. Rests on the ICR alone.",
    } as Record<string, string>,
    none: "I have no lessons on cost estimates or specifications that fit this package yet.",
    noneLink: "See all lessons",
    error: "I couldn't load the lessons just now.",
  },

  // The Packages tab (the 15 brief, section 7.9).
  packagesTab: {
    purpose: "The packages you are planning and the plans you checked. Check a published plan, or plan a new package from one sentence.",
    checkPlan: "Check a plan",
    planPackage: "Plan a package",
    // An implementing agency officer's Packages tab (ticket 38; the 38 brief, 5.1): their uploads, and Check my plan.
    purposeAgency:
      "The plans you checked and the packages you are planning. Check your plan before you submit it, or plan a new package from one sentence.",
    checkMine: "Check my plan",
    uploadsTitle: "Your team's uploads",
    uploadName: (date: string) => `Your plan, uploaded ${date}`,
    uploadCaption: (count: number, countText: string) => (count === 1 ? "One activity checked." : `${countText} activities checked.`),
    previewOff: "Checking and planning are off in a preview.",
    // Zero is "no", never "0" (DESIGN.md section 7, rule 12).
    title: (packages: number, packageWords: string, plans: number, planWords: string) =>
      `You have ${packages === 0 ? "no" : packageWords} ${packages === 1 ? "package" : "packages"} in progress and ` +
      `${plans === 0 ? "no" : planWords} checked ${plans === 1 ? "plan" : "plans"}.`,
    noun: "packages and plans",
    nounOne: "package or plan",
    columns: {
      name: "Package or plan",
      type: "Type",
      country: "Country",
      project: "Project",
      lastWorked: "Last worked on",
      lastWorkedNote: "When you last saved the package or opened the plan check",
    },
    noReference: "No STEP reference yet.",
    planName: (agency: string, date: string) => `${agency}, plan of ${date}`,
    activities: (count: number, words: string) => (count === 1 ? "One activity checked." : `${words} activities checked.`),
    typePackage: "Package",
    typePlan: "Plan check",
    noProject: "None yet",
    // A package you are planning has no country until you set one, which is no gap in the records.
    noCountry: "None yet",
    source: "your packages and plan checks, saved in Strata.",
    emptyTitle: "You have no packages or checked plans yet.",
    emptyBody: "Use Check a plan or Plan a package above to start one.",
    error: "I couldn't load your packages and checked plans just now. Try again in a moment.",
    loading: "Loading your packages and checked plans.",
    previous: "Previous 20",
    next: "Next 20",
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
      // The link's whole name, starting with its words on screen, so five "Open at page" links are told
      // apart: "Open at page 65 of the Project Appraisal Document for P130164". Ticket 21 points it at the
      // in-app source view, in the same tab, where the World Bank's PDF is linked at the same page.
      pageLinkName: (page: string, docType: string, pid: string) => `Open at page ${page} of the ${docType} for ${pid}`,
      // Under it, the World Bank's PDF at the same page, since the source view shows the page's passages and
      // tables but not its picture (the 21 design review, round 2, F16). The name goes on with
      // pdfLinkName, then ", opens in a new tab".
      pdfLink: "Open page {page} in the World Bank's PDF",
      pdfLinkName: (docType: string, pid: string) => ` of the ${docType} for ${pid}`,
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
      // The same line with the name as a slot, for a name in another language that keeps its lang (ticket 42).
      collectionNamed: "{name}, published by {publisher}, from {origin}.",
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
      // The section the link under every refusal goes to (ticket 24; the 24 brief, section 5.7). Each
      // refusal's lead and why follow, from refusals above.
      dontDo: {
        heading: "What I don't do",
        intro:
          "I turn these requests down every time, and I say what I can do instead. Each one is also a question in my test set that I must turn down.",
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
        // Section 5 of the package workspace (ticket 31; the 31 brief, section 9).
        compare_criteria: "the comparison of qualification criteria",
        rejected_bids: "the count of rejected bids",
        // Section 1's "Advertised again" block (ticket 28; the 28 brief, section 7.4).
        rebidding_risk: "the count of packages advertised again",
        compare_cost_estimates: "the comparison of cost estimates",
        // The package workspace's section 3 (ticket 30) links with its own key, since its coverage line is not
        // the quote check's.
        package_risks: "the risks and what helped",
        // The package workspace's section 2 (ticket 27).
        estimate_time: "the planned dates for each step",
        // Following's coverage line (ticket 37).
        project_signals: "the signals on projects you follow",
        // The activity page and a project's Connections tab (ticket 22).
        contract_trail: "the contract trail",
        connections: "the Connections tab",
        // Structured questions through the Genie space (ticket 33).
        ask_genie: "the records Genie looked up",
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
      // Ticket 32's reviewer pages, each shown only to its role.
      reports: "Passage reports ({waiting})",
      judging: "Judging ({left})",
      showingLibrary: "Showing Lessons.",
      showingQueue: "Showing Waiting for review.",
      showingReports: "Showing Passage reports.",
      showingJudging: "Showing Judging.",
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
      // The count line in a table's form (copy.table): numerals and no closing period.
      countAll: "Showing all {total} lessons in the library, newest first",
      countBoth: "Showing both lessons in the library, newest first",
      countOne: "Showing 1 lesson in the library",
      countRange: "Showing {from}–{to} of {total} lessons in the library, newest first",
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
      // Cards have no column heads, so the days' definition ends the count line's row once.
      daysCards: "Days from publication run from the day the report became public to the decision.",
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
        merged: "Rested on {quotes} from {reports}.",
        mergedNow: "Rests on {quotes} from {reports}.",
        quotes: { one: "{count} quote", many: "{count} quotes" },
        reports: { one: "{count} report", many: "{count} reports" },
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
      // A refusal says what failed here; the note under it says why.
      refused: "I couldn't save your {act}.",
      acts: { recommend: "recommendation", decide: "decision", cross_check: "cross-check" } as Record<string, string>,
      tryAgain: "Try again",
      staleLead: "While you had this lesson open, {name} {act} on {date}.",
      staleActs: { recommend: "recommended it", decide: "made a decision", cross_check: "cross-checked it" } as Record<string, string>,
      staleBody: "I didn't send your reason. You can copy it from the box below.",
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

  // The activity page, its contract trail, a project's Connections tab and "Why this source" (ticket 22; the 22
  // brief, sections 2.7, 3.5 and 4.2). A link between a contract and a paragraph is always "appeared together",
  // never a cause: the copy lint bans causal words in these four blocks, "because" included (web/lint/rules.ts,
  // CAUSAL_SCOPES), so an error is written as two sentences. {name} slots are values a tool returned.
  activity: {
    docTitle: (ref: string) => `Activity ${ref}`,
    crumbProcurement: "Procurement",
    titleFallback: "Activity {stepRef}",
    label: { ref: "STEP reference", agency: "Implementing agency" },
    purpose:
      "This page traces one activity from its row in the Procurement Plan to its notice, bids and signed contract, and shows the report paragraphs that appeared together with the contract.",
    // The lead joins the parts that exist, in this order, "A and B" or "A, B and C" with no serial comma.
    lead: "This activity was {parts}.",
    leadEstimated: "estimated at {estimate} in the plan",
    leadAdvertised: "advertised on {notice_date}",
    leadSigned: "signed on {signed_date}, for {amount}",
    leadSignedNoAmount: "signed on {signed_date}",
    leadSignedMany: "signed as {count} contracts between {first_signed_date} and {last_signed_date}",
    join: { pair: " and ", list: ", ", last: " and " },
    noEstimate: "The plan gives no Estimated Amount.",
    missingNoun: { notice: "notice", contract: "signed contract", notice_and_contract: "notice or signed contract" } as Record<string, string>,
    leadMissing: "I have no {missing} for it in the records through {data_through}.",
    leadBids: (one: boolean, proposals: boolean) =>
      `The award notice listed {count} ${proposals ? (one ? "proposal" : "proposals") : one ? "bid" : "bids"}.`,
    // Two or more award notices: "The award notices listed five and four bids."
    leadBidsMany: (proposals: boolean) => `The award notices listed {counts} ${proposals ? "proposals" : "bids"}.`,
    leadParagraphs: (one: boolean, many: boolean) =>
      `In the project's reports, {count} ${one ? "paragraph" : "paragraphs"} appeared together with ${many ? "its contracts" : "the contract"}.`,
    leadNoParagraphs: "No paragraph from the project's reports appeared together with the contract.",
    leadNoParagraphsMany: "No paragraph from the project's reports appeared together with its contracts.",
    // The tooltips on the lead's numbers: where each came from.
    fromRecord: (kind: string, reference: string) => `From the ${kind} ${reference}.`,
    fromAwardNotice: (id: string) => `From award notice ${id}.`,
    fromParagraphs: "From the links I scored between the contract and the project's reports.",
    recordKind: { estimated: "Procurement Plan row", advertised: "notice", signed: "contract", award_notice: "award notice" } as Record<string, string>,
    loading: "Loading this activity.",
    stillLoading: "Still loading this activity.",
    error: "I couldn't load this activity. The data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show this activity.",
    notFoundTitle: "I have no activity {stepRef} in {pid}.",
    notFoundBody: "Check the STEP reference, or find the activity in the project's Procurement Plans.",
    notFoundLink: "Procurement Plans for {pid}",
  },
  // The contract trail's words; the rebidding block (ticket 28) shares trail.notice.again.
  trail: {
    label: "Contract trail for {stepRef}",
    // A bare section number as a card's title or a chip writes it; a named section is its own name.
    sectionNumber: "Section {section}",
    legend:
      "A solid line joins records that share a key, such as the STEP reference. A dashed line joins the contract to report paragraphs that appeared together with it.",
    plan: {
      title: "In the Procurement Plan",
      date: "Plan of {date}",
      field: {
        method: "Method",
        market_approach: "Market Approach",
        review_type: "Review Type",
        estimated_amount_usd: "Estimated Amount (US$)",
        process_status: "Process Status",
      } as Record<string, string>,
      datesTitle: "Dates in the plan",
      datesCaption: "The STEP steps the plan dates for this activity",
      col: { step: "Step", planned: "Planned, as first published", actual: "Actual" },
      notInPlan: "Not in the plan",
      noneRecorded: "None recorded",
      // The step's full STEP name after its short label, for a screen reader (the hover shows it too).
      stepHidden: (name: string) => `, in STEP ${name}`,
      datesNote: "Planned dates are as first published, in the plan of {first_plan_date}. Later plans can move them.",
      plannedLine: "Planned, as first published: {planned}. Actual: {actual}.",
      showInPlan: "Show it in its plan",
      pastRange: "See the past range",
      forRef: (ref: string) => ` for ${ref}`,
      source: "Procurement Plan, {agency}, version of {plan_date}, disclosed {disclosed}.",
    },
    notice: {
      title: "Notice",
      titleMany: "Notices",
      date: "Published {date}",
      field: {
        notice_type: "Notice Type",
        published: "Published",
        procurement_method: "Procurement Method",
        submission_deadline: "Submission Deadline",
        bid_description: "Description",
      } as Record<string, string>,
      again: "The activity was advertised again on {date}.",
      open: "Open the notice on worldbank.org",
      source: "Procurement notice {id}, published {date}. {dataset}",
    },
    bids: {
      title: "Bids",
      titleProposals: "Proposals",
      date: "Award notice published {date}",
      caption: "Bids listed in award notice {id}, in the order the notice lists them",
      col: { bidder: "Bidder", consultant: "Consultant", opening: "Bid price at opening", evaluated: "Evaluated bid price", result: "Result" },
      colCurrency: (label: string, currency: string) => `${label} (${currency})`,
      // Counts under ten in words (DESIGN.md section 7, rule 12): "Showing all three bids", "Showing the one bid".
      count: (n: number, count: string, proposals: boolean) =>
        n === 1 ? `Showing the one ${proposals ? "proposal" : "bid"}` : `Showing all ${count} ${proposals ? "proposals" : "bids"}`,
      awarded: "Awarded",
      notAwarded: "Not awarded",
      rejected: "Rejected. The award notice gives the reason \"{reason}\".",
      rejectedNoReason: "Rejected.",
      // Above each award notice's bids when an activity has two or more.
      noticeHeading: "Award notice {id}",
      noResult: "The award notice gives no result.",
      notInNotice: "Not in the notice",
      individual: "Individual consultant",
      jvUnnamed: "A joint venture of {members}",
      currency: "Prices are in {currency}, as the award notice gives them.",
      noScores: "The award notice also lists evaluation scores. I don't show scores or ranks for suppliers.",
      open: "Open the award notice on worldbank.org",
      source: "Award notice {id}, published {date}. {dataset}",
    },
    contract: {
      title: "Contract",
      titleMany: "Contracts",
      date: "Signed {date}",
      field: {
        supplier: "Supplier",
        supplier_country: "Supplier Country",
        signedAmountUsd: "Signed amount (US$)",
        signedAmount: (currency: string) => `Signed amount (${currency})`,
        contract_description: "Contract Description",
        contract_reference: "Contract Reference",
      },
      fromNotice: "The World Bank's contract awards data skip fiscal 2017 to 2019. This contract comes from its award notice, in {currency}.",
      source: "Contract award {reference}, signed {date}. {dataset}",
      sourceNotice: "Award notice {id}, published {date}. {dataset}",
    },
    together: {
      title: "Paragraphs that appeared together with the contract",
      intro:
        "I link a contract to a paragraph in the same project's reports when they are close in time and share a sector, words or names. A link means only that they appeared together.",
      // Each report is a group under its name and date, and each card names its paragraph within it.
      reportTitle: "{doc}, {date}",
      // The count starts its line, so a count word starts with a capital: "Two paragraphs", "29 paragraphs".
      reportCount: (n: number, count: string) => (n === 1 ? "One paragraph" : `${count.charAt(0).toUpperCase()}${count.slice(1)} paragraphs`),
      showAll: (count: string) => `Show all ${count} paragraphs`,
      fromReport: " from the {doc} of {date}",
      cardTitle: "Paragraph {para}",
      cardTitleIn: "{section}, paragraph {para}",
      cardTitleSectionPage: "{section}, page {page}",
      topics: "Both concern {topics}.",
      topicsWith: "With contract {ref}, both concern {topics}.",
      less: "Show fewer paragraphs",
      source: "{doc}, {date}, paragraph {para}, page {page}.",
      sourceSection: "{doc}, {date}, section {section}, page {page}.",
    },
    // Each missing stage's sentence, by the reason code the trail gives (the 22 brief, section 2.7).
    missing: {
      not_read: "I haven't read a Procurement Plan that lists this activity. The {record_noun} names it by its STEP reference.",
      notReadLink: "Procurement Plans for {pid}",
      method_no_notice: "This activity had no public notice. Its Method, {method}, does not use one.",
      approach_no_notice: "This activity had no public notice. Its Market Approach, {market_approach}, invites firms directly.",
      notice_none_found: "I found no notice with this STEP reference in the records through {data_through}.",
      noticeLink: "See how complete the notices are",
      bids_none_found: "I found no award notice for this activity in the records through {data_through}. Award notices are where bids are listed.",
      bidsLink: "See how complete the award notices are",
      direct_selection: "This activity used Direct Selection, which invites a single firm. The award notice lists no other bids.",
      individual_consultant: "This activity hired an individual consultant. I don't name individuals, and no bids were listed.",
      contract_none_found: "I found no signed contract for this activity in the records through {data_through}.",
      no_links: "No paragraph in this project's reports appeared together with the contract. I keep a link only when its score reaches {threshold}.",
      no_contract: "I link paragraphs to signed contracts, and this activity has none yet.",
      after_asof: "No {record_noun} for this activity was public as of {asof_date}.",
      paragraphs_after_asof: "I link paragraphs to signed contracts. As of {asof_date}, this activity had none.",
      recordNoun: { plan: "Procurement Plan", notice: "notice", bids: "award notice", contract: "contract" } as Record<string, string>,
      coverage: "I have read {read} of the project's {total} documents.",
    },
    blank: "Not in the record",
    pill: (n: number, kind: string, reference: string, date: string, opened: boolean) =>
      `Source ${n}: ${kind} ${reference}, ${date}${opened ? ", opened" : ""}`,
    pillKind: { plan: "Procurement Plan row", notice: "notice", award_notice: "award notice", contract: "contract" } as Record<string, string>,
    // What a pill's name says after "Source {n}:": "award notice OP00164589, Feb 2, 2022".
    pillSource: (kind: string, reference: string, date: string) => `${kind} ${reference}, ${date}`,
    paraShort: (para: string) => `¶${para}`,
    // How a currency's code reads in a sentence: "Prices are in Kenya shillings". An unknown code reads as itself.
    currencyName: { KES: "Kenya shillings", INR: "Indian rupees", USD: "US dollars", EUR: "euros" } as Record<string, string>,
    // An amount in a sentence: "US$1,245,092.76", or another currency's code, a space and the amount.
    usd: (amount: string) => `US$${amount}`,
    otherCurrency: (currency: string, amount: string) => `${currency} ${amount}`,
  },
  connections: {
    finding: (contracts: number, paragraphs: number, documents: number) =>
      `In this project, {contracts} ${contracts === 1 ? "contract" : "contracts"} appeared together with {paragraphs} ${
        paragraphs === 1 ? "paragraph" : "paragraphs"
      } from {documents} of its reports.`,
    findingOneReport: (contracts: number, paragraphs: number) =>
      `In this project, {contracts} ${contracts === 1 ? "contract" : "contracts"} appeared together with {paragraphs} ${
        paragraphs === 1 ? "paragraph" : "paragraphs"
      } from one of its reports.`,
    findingNone: "In this project, no contract appeared together with a paragraph from its reports.",
    legend:
      "Solid lines join the project to the packages in its plans and the documents about it. Dashed lines join a package to report paragraphs that appeared together with one of its contracts. A dashed line means only that they appeared together.",
    legendNone: "Solid lines join the project to the packages in its plans and the documents about it.",
    // The list draws no lines, so its legend says what its items mean.
    legendList:
      "Each package lists the report paragraphs that appeared together with one of its contracts. This means only that they appeared together.",
    linesHint: "Hover over or focus a package to see its links.",
    noPackages: "I haven't read a Procurement Plan for {pid} yet.",
    noPackagesLink: "Procurement Plans for {pid}",
    count: "Showing {shown} of {total} packages and documents",
    toList: "Show as a list",
    toDiagram: "Show as a diagram",
    showingList: "Showing the list.",
    showingDiagram: "Showing the diagram.",
    col: { packages: "Packages it plans", documents: "Documents about it" },
    // After the project node's P-code and name, which its link shows.
    projectOpen: ". Open the project summary.",
    pkgSigned: "Signed {date}",
    pkgSignedMany: (count: string) => `${count} contracts, first signed {date}`,
    pkgName: (ref: string, description: string, status: string) => `${ref}, ${description}. ${status}.`,
    pkgLinks: (items: string) => `Appeared together with ${items}.`,
    together: "Appeared together with",
    chip: "¶{para}",
    // A paragraph number the document uses again in an annex, and a section name it uses twice.
    chipIn: "{section} ¶{para}",
    chipPage: "{label}, page {page}",
    chipName: (doc: string, place: string, ref: string) => `${doc} ${place}, appeared together with ${ref}`,
    placeParagraph: (para: string, section: string | null) => (section ? `${section} paragraph ${para}` : `paragraph ${para}`),
    placeSection: (section: string) => `section ${section}`,
    placePage: (place: string, page: string) => `${place}, page ${page}`,
    chipNameMany: (doc: string, place: string, count: string) => `${doc} ${place}, appeared together with ${count} packages`,
    chipWithDoc: "{doc} {label}",
    chipWithDocSection: "{doc}, {label}",
    chipOpened: (name: string) => `${name}, opened`,
    docCaption: "{type}, {date}",
    planShort: "Procurement Plan",
    moreChips: (n: number, count: string) => (n === 1 ? "and one more paragraph" : `and ${count} more paragraphs`),
    moreChipsIn: (doc: string) => ` in the ${doc}`,
    docName: (short: string, type: string, date: string) => (short === type ? `${type}, ${date}. Open the document.` : `${short}, ${type}, ${date}. Open the document.`),
    docShort: { isr: (n: string) => `ISR ${n}` },
    more: {
      packages: (n: number, count: string) => (n === 1 ? "and one more package" : `and ${count} more packages`),
      isrs: (n: number, count: string) => (n === 1 ? "and one more ISR" : `and ${count} more ISRs`),
      plans: (n: number, count: string) => (n === 1 ? "and one more Procurement Plan" : `and ${count} more Procurement Plans`),
      documents: (n: number, count: string) => (n === 1 ? "and one more document" : `and ${count} more documents`),
    } as Record<string, (n: number, count: string) => string>,
    // After a row whose documents I haven't read, all or some of them.
    moreAllUnread: " I haven't read",
    moreSomeUnread: (n: number, count: string) => (n === 1 ? ", one of them not read yet" : `, ${count} of them not read yet`),
    noneDetail: "I keep a link only when its score reaches {threshold}.",
    coverage: "I have read {read} of the project's {total} documents.",
    source:
      "Procurement Plans, procurement notices and contract awards from the World Bank's APIs, and this project's documents, through {data_through}. The links are Strata's own, scored {scored_date}.",
    sourceUnscored:
      "Procurement Plans, procurement notices and contract awards from the World Bank's APIs, and this project's documents, through {data_through}.",
    loading: "Loading this project's connections.",
    stillLoading: "Still loading this project's connections.",
    error: "I couldn't load this project's connections. The data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show this project's connections.",
    emptyTitle: "I have no packages or documents for {pid} yet.",
    emptyBody: "Once I load this project's Procurement Plans and documents, this tab shows how they connect.",
    emptyLink: "Data readiness",
  },
  why: {
    title: "Why this source",
    link: "This paragraph appeared together with {record_noun} {ref}, signed {signed_date}.",
    recordNoun: { "award notice": "award notice", contract: "contract" } as Record<string, string>,
    topics: "Both concern {topics}, in a project that {project_state}.",
    sameProject: "Both come from {pid}, a project that {project_state}.",
    projectState: { closed: "has closed", active: "is active" } as Record<string, string>,
    timeAfter: "The {doc} is dated {doc_date}, {months} months after the signing.",
    timeBefore: "The {doc} is dated {doc_date}, {months} months before the signing.",
    timeSame: "The {doc} is dated {doc_date}, in the month of the signing.",
    timeAfterOne: "The {doc} is dated {doc_date}, one month after the signing.",
    timeBeforeOne: "The {doc} is dated {doc_date}, one month before the signing.",
    only: "A link means only that they appeared together.",
    open: "Open the activity",
    openFor: (ref: string) => ` ${ref}`,
    // Each other package once, though a package can hold several contracts.
    others: (n: number) =>
      n === 1
        ? "It also appeared together with contracts of one other package in this project."
        : "It also appeared together with contracts of {count} other packages in this project.",
    othersItem: "{ref}, signed {date}",
    othersMore: (n: number) => (n === 1 ? "and one more in Connections" : "and {count} more in Connections"),
    scoreShow: "How I scored this link",
    scoreHide: "Hide how I scored this link",
    scoreCaption: "How I scored the link between this paragraph and {ref}",
    col: { part: "Part", matched: "What matched", points: "Points" },
    part: { project: "Project", sector: "Sector", time: "Time", text: "Wording", mentions: "Mentions" } as Record<string, string>,
    matched: {
      project: "Same project, {pid}",
      sector: "{sector}",
      time: "{months} months apart",
      timeOne: "One month apart",
      timeSame: "The same month",
      timeNone: "No date to compare",
      wording: "Close wording, such as \"{terms}\"",
      wordingNone: "Close wording",
      mentions: "{mentions}, as written in both",
      mentionsNone: "No shared mention",
    },
    total: "Link score: {score}. I keep a link when it scores {threshold} or more.",
    // The phrases "Both concern" uses, by the procurement category and by the World Bank's sector code (the 22
    // brief, section 4.2). An unmapped sector reads as its name, in lower case.
    category: {
      Works: "works contracts",
      Goods: "goods contracts",
      "Consultant Services": "consulting services",
      "Non-consulting Services": "non-consulting services",
    } as Record<string, string>,
    sector: {
      TI: "roads",
      TV: "urban transport",
      TW: "ports and waterways",
      TA: "aviation",
      TF: "transport administration",
      WC: "water supply",
      WA: "sanitation",
      WB: "waste management",
      WF: "water administration",
    } as Record<string, string>,
    topicJoin: { pair: " and ", list: ", ", last: " and " },
  },

  // The evidence drawer's feedback row (ticket 32; the 32 brief, section 5.1): "Was this the right passage?"
  // with "Wrong passage" and "Not useful", for a passage a search found for your question.
  feedback: {
    question: "Was this the right passage?",
    kind: { wrong_passage: "Wrong passage", not_useful: "Not useful" } as Record<string, string>,
    formLabel: {
      wrong_passage: "What was wrong with it? (optional)",
      not_useful: "What did you need that it didn't give? (optional)",
    } as Record<string, string>,
    formHelper: "A reviewer sees your question, the sentence that cited this paragraph, the paragraph and your reason.",
    send: "Send the report",
    sending: "Sending",
    cancel: "Cancel",
    sent: {
      wrong_passage: "You marked this as the wrong passage.",
      not_useful: "You marked this as not useful.",
    } as Record<string, string>,
    later: {
      wrong_passage: "You marked this as the wrong passage on {reported}.",
      not_useful: "You marked this as not useful on {reported}.",
    } as Record<string, string>,
    nextPilot: "A person reviews every report before I rank a passage differently.",
    nextScale:
      "I rank a passage differently only after a reviewer agrees, or after several people make the same report and " +
      "nobody disagrees.",
    yourReason: "Your reason: \"{reason}\"",
    withdraw: "Withdraw the report",
    withdrawing: "Withdrawing",
    withdrawn: "I withdrew your report.",
    failed: "I couldn't send your report just now. Your text is still here.",
    withdrawFailed: "I couldn't withdraw your report just now.",
    withdrawDecided: "A reviewer decided on your report while you had it open, so it can't be withdrawn now.",
    tryAgain: "Try again",
    rankedLower:
      "A reviewer agreed on {decided}, so I now rank this paragraph lower for questions about {kind}. I still show " +
      "it when it is the only source.",
    byAgreement:
      "On {decided}, after {agreeing} people made the same report and nobody disagreed, I ranked this paragraph lower " +
      "for questions about {kind}. I still show it when it is the only source.",
    kept: "A reviewer kept its ranking on {decided}.",
    reviewerReason: "Their reason: \"{reason}\"",
    preview: "This is a preview, so I'm not recording the sources you open, and you can't report a passage.",
  },

  // The retrieval loop's words that more than one screen uses (ticket 32).
  retrieval: {
    // Each kind of question in config/retrieval.toml, as "For questions about {kind}" names it. A test checks every
    // kind has one.
    queryKinds: {
      rebidding_and_prices: "rebidding and bid prices",
      delays: "delays",
      clearances_and_land: "permits, land and safeguards",
      contract_management: "contracts and their management",
      capacity: "staff and agency capacity",
      results: "results and ratings",
      other: "other topics",
    } as Record<string, string>,
    // What a passage report's sender is called on a review page: their role, never their name (the 32 brief,
    // section 4.2), and "You" for the reviewer's own report.
    roles: {
      staff: "A World Bank staff member",
      piu: "An implementing agency officer",
      public: "A member of the public",
      you: "You",
    } as Record<string, string>,
    // The per-person sentence on Lessons (ticket 39) and the dashboard's measure (ticket 45), from the counts the
    // weekly retrieval run stores in strata.ops.retrieval_feedback_viewers. One to nine are words (Num count).
    sentence: {
      fixedAndRecited:
        "You marked {marked} passages as wrong; {fixed} {isAre} fixed, and {recited} answers now cite the right paragraph.",
      fixed: "You marked {marked} passages as wrong; {fixed} {isAre} fixed.",
      oneFixed: "You marked one passage as wrong, and it is fixed. {recited} answers now cite the right paragraph.",
      waiting: "You marked {marked} passages as wrong. A reviewer hasn't decided on {themIt} yet.",
      kept: "You marked {marked} passages as wrong. Reviewers kept their ranking, and the evidence drawer shows why.",
      isAre: { one: "is", many: "are" },
      themIt: { one: "it", many: "them" },
    },
    measureName: "Wrong-passage reports per 100 sources opened",
  },

  // Lessons > Passage reports and one passage's reports (ticket 32; the 32 brief, sections 5.3 and 5.4).
  passageReports: {
    title: "Passage reports",
    purposePilot:
      "When someone marks a passage as wrong or not useful in the evidence drawer, the report comes here. In this " +
      "pilot, a person reviews every report before I rank a passage differently, and that person is never one of the " +
      "people who sent it. Only passage reviewers can open this page.",
    purposeScale:
      "When someone marks a passage as wrong or not useful in the evidence drawer, the report comes here, unless {min} " +
      "or more people made the same report and nobody disagreed. Then I rank the passage lower myself and send one in " +
      "{every} of those decisions here for a check. Reports about the sender's own project always come here. Only " +
      "passage reviewers can open this page.",
    lead: {
      both: "Reports on {you} {passagesYou} are waiting for you, and {others} {beOthers} waiting for another reviewer.",
      youOnly: "Reports on {you} {passagesYou} are waiting for you.",
      othersOnly: "Nothing is waiting for you. Reports on {others} {passagesOthers} are waiting for another reviewer.",
      none: "Nothing is waiting for review.",
      oldest: "The oldest came in on {date}.",
      passages: { one: "passage", many: "passages" },
      be: { one: "is", many: "are" },
    },
    caption:
      "Ranking a paragraph lower changes only questions like the ones in its reports. I never hide a paragraph, and I " +
      "still show it when it is the only source.",
    groups: { you: "Waiting for you", others: "Waiting for another reviewer" } as Record<string, string>,
    order: "Oldest first.",
    kindLabel: {
      wrong_passage: "Wrong passage",
      not_useful: "Not useful",
      both: "Wrong passage and not useful",
      audit: "Audit sample",
    } as Record<string, string>,
    status: { you: "{kind} · needs your review", others: "{kind} · needs another reviewer", decided: "{kind} · decided" },
    rowTitle: "{project}, paragraph {para}",
    rowTitleSection: "{project}, section {section}",
    rowSource: "{docType}, {date}, page {page}. For questions about {kind}.",
    rowCount: "{count} reports, the first on {date}.",
    rowCountOne: "One report, on {date}.",
    rowAudit: "I ranked it lower on {date}, after {agreeing} people made the same report.",
    whyNot: { own_report: "You sent one of these reports, so another reviewer decides." } as Record<string, string>,
    badgeOwnProject: "About the sender's own project",
    badgeTheirProject: "About their own project",
    badgeAudit: "Audit sample",
    decidedTitle: "Decided in the last {days} days",
    // The count line's noun: "Showing all 3 decisions, newest first" (copy.table).
    decidedNoun: "decisions, newest first",
    decidedNounOne: "decision, newest first",
    columns: { passage: "Passage", outcome: "Outcome", decided: "Decided", reports: "Reports" },
    forQuestions: "For questions about {kind}",
    outcomes: {
      ranked_lower: "Ranked lower",
      kept: "Kept its ranking",
      ranked_lower_by_agreement: "Ranked lower by agreement",
      left_lower: "Left ranked lower",
      restored: "Ranking restored",
    } as Record<string, string>,
    source: "Strata's passage report records.",
    emptyTitle: "No one has reported a passage yet.",
    emptyBody: "When someone marks a passage as wrong or not useful in the evidence drawer, the report appears here for review.",
    loading: "Loading the passage reports.",
    error: "I couldn't load the passage reports because the data service didn't answer.",
    permission:
      "Your account can't read Strata's tables, so I can't show the passage reports. Ask your workspace admin for read " +
      "access to the strata catalog.",
    noAccessTitle: "I show this page only to passage reviewers.",
    noAccessBody:
      "Passage reviewers are named in Strata's roles file. Your account isn't one of them, so the reports stay hidden " +
      "from you.",
    noAccessLink: "Go to Lessons",
    // One passage's reports (section 5.4).
    breadcrumbBack: "Passage reports",
    pageTitle: "{project}, paragraph {para}, Passage reports",
    context: "Reported for questions about {kind}. {count} reports, the first on {date}.",
    contextOne: "Reported for questions about {kind}. One report, on {date}.",
    auditContext:
      "I ranked this paragraph lower on {date}, after {agreeing} people made the same report and nobody disagreed. I " +
      "picked it for a check.",
    passageTitle: "The passage",
    reportsTitle: "What people reported",
    reportsCaption: "Oldest first. I show each sender's role, not their name.",
    reportFirst: {
      wrong_passage: "{role} marked it as the wrong passage on {date}.",
      not_useful: "{role} marked it as not useful on {date}.",
    } as Record<string, string>,
    asked: "They asked: \"{question}\"",
    askedYou: "You asked: \"{question}\"",
    sentence: "The sentence in my answer: \"{sentence}\"",
    reason: "Their reason: \"{reason}\"",
    reasonYou: "Your reason: \"{reason}\"",
    noReason: "They gave no reason.",
    noReasonYou: "You gave no reason.",
    answerId: "Answer ID {id}",
    showMore: "Show {count} more reports",
    showFewer: "Show fewer reports",
    form: {
      title: "Your decision",
      reasonLabel: "Your reason",
      reasonHelper: "The people who sent these reports see your reason. It stays in the record with your name.",
      rankLower: "Rank it lower",
      keep: "Keep its ranking",
      leaveLower: "Leave it ranked lower",
      restore: "Restore its ranking",
      feedforward:
        "Ranking it lower changes only questions about {kind}, and I still show this paragraph when it is the only " +
        "source. Keeping its ranking changes nothing.",
      feedforwardAudit:
        "Restoring its ranking puts it back where it was for questions about {kind}. Leaving it ranked lower ends the check.",
      noReason: "Write your reason first. The people who sent these reports will see it.",
      ownReport: "You sent one of these reports, so another passage reviewer decides.",
      saving: "Saving",
      failed: "I couldn't save your decision just now. Your reason is still here.",
      tryAgain: "Try again",
      stale: "{name} decided on these reports on {date}, while you had them open.",
      staleBody: "I didn't send your reason. You can copy it from the box below.",
      staleReason: "Your reason, not sent",
      lostRole: "Your account is no longer on the list of passage reviewers, so I couldn't save this.",
    },
    saved: {
      rank_lower: { lead: "You ranked this paragraph lower for questions about {kind}.", body: "I still show it when it is the only source. The people who reported it see your decision when they open it again." },
      keep: { lead: "You kept its ranking.", body: "Nothing changed in how I rank it. The people who reported it see your reason when they open it again." },
      leave_lower: { lead: "You left this paragraph ranked lower for questions about {kind}.", body: "The check is done." },
      restore: { lead: "You restored its ranking for questions about {kind}.", body: "I rank it as I did before the reports." },
    } as Record<string, { lead: string; body: string }>,
    nextReport: "Open the next report waiting for you",
    backToReports: "Back to Passage reports",
    record: {
      ranked_lower: "Ranked lower for questions about {kind} on {date}, by {name}.",
      kept: "Kept its ranking on {date}, by {name}.",
      ranked_lower_by_agreement: "Ranked lower by agreement on {date}, after {agreeing} people made the same report.",
      left_lower: "Left ranked lower on {date}, by {name}, after a check.",
      restored: "Ranking restored on {date}, by {name}, after a check.",
    } as Record<string, string>,
    recordReason: "Reason: \"{reason}\"",
    reopen: "Reopen the report",
    reopenLabel: "Why reopen it?",
    reopenHelper:
      "Reopening puts these reports back in the queue and gives the paragraph the ranking it had before. Your reason " +
      "stays in the record with your name.",
    reopenNoReason: "Write a reason, so the next reviewer knows what to look at.",
    reopenFailed: "I couldn't reopen these reports just now. Your reason is still here.",
    reopenedLead: "You reopened these reports.",
    reopenedBody: "They are waiting for review again, and the paragraph has its earlier ranking.",
    loadingOne: "Loading these reports.",
    notFoundTitle: "I have no passage report with the ID {id}.",
    notFoundBody: "Check the link, or find it in Passage reports.",
    notFoundLink: "Go to Passage reports",
    errorOne: "I couldn't load these reports because the data service didn't answer.",
  },

  // Lessons > Judging and one query's page (ticket 32; the 32 brief, sections 5.5 and 5.6).
  judging: {
    title: "Judging",
    purpose:
      "Two judges grade the passages I find for each query, each working alone. The queries were written from award " +
      "notices, and I show only passages that were public before each notice's date. Your grades make the labeled set " +
      "I use to measure search, and feedback from the evidence drawer never goes into it. Only query judges can open " +
      "this page.",
    leadNone: "You haven't judged any queries yet, and {total} are waiting for you.",
    leadNoneOne: "You haven't judged any queries yet, and one is waiting for you.",
    leadSome: "You have judged {done} of {total} queries.",
    leadAll: "You have judged all {total} queries.",
    leadOther: "The other judge has finished {done} of {total}.",
    next: "Judge the next query",
    agree: "Where you have both finished, your grades matched on {agree} of {pairs} passages. {kappaName}: {kappa}.",
    agreeCaption:
      "{kappaName} counts how often you agreed beyond what chance alone would give. 1 means you always agreed, and 0 " +
      "means no better than chance.",
    agreeWithheld: "I'll give your agreement once you have both graded {min} passages on the same queries. So far you have {pairs}.",
    kappaName: "Cohen's kappa",
    tooltipDone: "Queries where you graded every passage.",
    tooltipPairs: "Passages you both graded, across {done} queries you both finished.",
    tooltipKappa: "From {pairs} passages you both graded. I recompute it each time a query is finished by both of you.",
    show: "Show",
    filters: {
      to_judge: "To judge ({count})",
      finished_by_you: "Finished by you ({count})",
      finished_by_both: "Finished by both ({count})",
    } as Record<string, string>,
    filterNames: { to_judge: "Queries for you to judge", finished_by_you: "Queries you finished", finished_by_both: "Queries you both finished" } as Record<string, string>,
    countNoun: "queries",
    countNounOne: "query",
    columns: { query: "Query", pool: "Passages", poolDefinition: "in pool", progress: "Progress", matched: "Grades matched", matchedDefinition: "once you both finish" },
    queryCaption: "Query {n}. From award notice {ref}, {date}.",
    progressYou: { not_started: "You: Not started", started: "You: {graded} of {pool}", finished: "You: Finished" } as Record<string, string>,
    progressOther: { not_started: "Other judge: Not started", started: "Other judge: Started", finished: "Other judge: Finished" } as Record<string, string>,
    matched: "{agree} of {pool}",
    notYet: "Not yet",
    source: "Strata's labeled set of queries, written from award notices published by the World Bank.",
    emptyToJudgeTitle: "You have judged every query.",
    emptyToJudgeBody: "The other judge has finished {done} of {total}.",
    emptyToJudgeLink: "Show the queries you both finished",
    emptyYouTitle: "You haven't finished a query yet.",
    emptyYouBody: "Choose \"Judge the next query\" to start with the first one.",
    emptyBothTitle: "You haven't both finished a query yet.",
    emptyBothBody: "I show your agreement here once you have.",
    noQueriesTitle: "I have no queries for you to judge yet.",
    noQueriesBody: "They appear here once the search owner loads the queries written from award notices.",
    loading: "Loading the queries.",
    error: "I couldn't load the queries because the data service didn't answer.",
    permission:
      "Your account can't read Strata's tables, so I can't show the queries. Ask your workspace admin for read access to " +
      "the strata catalog.",
    noAccessTitle: "I show this page only to query judges.",
    noAccessBody:
      "Query judges are named in Strata's roles file. Your account isn't one of them, so the queries stay hidden from you.",
    noAccessLink: "Go to Lessons",
    // One query (section 5.6).
    breadcrumb: "Query {n}",
    breadcrumbBack: "Judging",
    pageTitle: "Query {n}, Judging",
    header: "Query {n} of {total}. Written from award notice {ref}, published {date}.",
    meter: "{graded} of {pool} passages graded.",
    poolNote: "I show only passages that were public before {date}, in a different order for each judge.",
    mapShow: "Show all {pool} passages",
    mapHide: "Hide the passage list",
    mapLabel: "Passages for this query",
    chipGraded: "Passage {i}, graded",
    chipNotGraded: "Passage {i}, not graded yet",
    panel: "Passage {i} of {pool}",
    grades: { answers: "Answers it", partly: "Partly", not_relevant: "Not relevant" } as Record<string, string>,
    definitions: {
      answers: "The paragraph answers the query, or gives a fact that the answer needs.",
      partly: "The paragraph is on the topic and helps a little, but you would need more to answer.",
      not_relevant: "The paragraph doesn't help answer the query.",
    } as Record<string, string>,
    keys: { answers: "A", partly: "P", not_relevant: "N" } as Record<string, string>,
    guidance: "Grade each paragraph on its own, as if it were the only one you read.",
    barLabel: "Your grade for passage {i}",
    barNote: "Saves and opens the next passage.",
    barNoteNarrow: "Choosing a grade saves it and opens the next passage.",
    keysNote: "While you are in this panel, the keys A, P and N choose a grade.",
    previous: "Previous passage",
    nextPassage: "Next passage",
    savedAs: "Saved as {grade}.",
    saveFailed: "I couldn't save your grade for passage {i}. Your other grades are saved.",
    finishedLead: "You graded all {pool} passages for this query.",
    finishedBody: "The other judge hasn't finished, so I'm not showing their grades yet. You can change yours until they finish.",
    bothLead: "You both finished this query. Your grades matched on {agree} of {pool} passages.",
    bothBody: "I locked your grades for this query, because I count agreement only on grades you each gave on your own.",
    differencesShow: "Show where you differed",
    differencesHide: "Hide where you differed",
    differencesCaption: "Passages where your grades differed",
    differencesColumns: { passage: "Passage", yours: "Your grade", theirs: "The other judge's grade" },
    differencesNone: "Your grades matched on every passage.",
    passageName: "Passage {i}",
    lockedYours: "Your grade: {grade}.",
    lockedTheirs: "The other judge's grade: {grade}.",
    lockedWhileOpen: "The other judge finished this query while you had it open, so I locked your grades for it.",
    afterLast: "You have judged all {total} queries.",
    backToJudging: "Back to Judging",
    emptyPoolTitle: "I found no passages for this query that were public before {date}.",
    emptyPoolBody: "I left it out of the labeled set, so there is nothing to grade.",
    emptyPoolLink: "Go to the next query",
    notAssignedTitle: "This query already has two judges.",
    notAssignedBody: "Each query gets two judges, and you aren't one of them for this query.",
    notAssignedLink: "Go to Judging",
    notFoundTitle: "I have no query with the ID {id}.",
    notFoundBody: "Check the link, or find it in Judging.",
    notFoundLink: "Go to Judging",
    loadingOne: "Loading this query.",
    errorOne: "I couldn't load this query because the data service didn't answer.",
  },

  // A project's Timeline tab (ticket 23; the 23 brief, section 7): What, How and Why in three lanes on one time
  // axis. {slots} are filled from GET /api/projects/{pid}/timeline; the page computes no number.
  timeline: {
    title: "Timeline",
    purpose:
      "This timeline puts the project's evaluations, operations documents and records on one time axis, so you can see " +
      "what was known when.",
    // The purpose's second sentence, only while there are items to select: marks on the chart, items in the list.
    purposeSelect: "Select a mark to open its source.",
    purposeSelectList: "Select an item to open its source.",
    // The chart's subtitle, with each shape drawn before its word ({report}, {event} and {record} are the glyphs,
    // hidden from screen readers, so the words carry the meaning).
    subtitle: "Each mark is a {report} report, an {event} event or a {record} record. A dashed line joins two reports that disagree.",
    // The same where no dashed line can be drawn: get_disagreements did not answer, or the view hides disagreements.
    subtitleNoLines: "Each mark is a {report} report, an {event} event or a {record} record.",
    subtitleList: "Each item is a report, an event or a record, in date order.",
    lane: { why: "Why · evaluations", how: "How · operations", what: "What · records" } as Record<string, string>,
    // The lane's word inside an item's name and the table's Stratum column.
    laneWord: { why: "Why", how: "How", what: "What" } as Record<string, string>,
    // An item's stratum on its own line in the list below 768 px.
    laneItem: { why: "Why · evaluation", how: "How · operations", what: "What · record" } as Record<string, string>,
    // The Note line under the chart: one sentence for each abbreviation that appears, then the bands and the codes.
    noteLead: "Note:",
    abbrev: {
      pad: "PAD is the Project Appraisal Document.",
      isr: "An ISR is an Implementation Status and Results Report.",
      icr: "ICR is the Implementation Completion and Results Report.",
      icr_review: "The Independent Evaluation Group (IEG) writes the ICR Review.",
      ppar: "PPAR is IEG's Project Performance Assessment Report.",
    } as Record<string, string>,
    bands: "The grey bands show each ISR's rating of progress towards the project development objective (PDO). Darker means a lower rating.",
    // Each rating's code, which a narrow band shows, and the sentence that spells it out in the Note line.
    codes: {
      "Highly Satisfactory": "HS",
      Satisfactory: "S",
      "Moderately Satisfactory": "MS",
      "Moderately Unsatisfactory": "MU",
      Unsatisfactory: "U",
      "Highly Unsatisfactory": "HU",
    } as Record<string, string>,
    codeNote: (code: string, rating: string) => `${code} is ${rating}.`,
    // "Source: World Bank documents and reports API, procurement notices and contract awards, through October 23, 2026."
    source: "{sources}, through {date}.",
    // As of a date: the sources as they stood on that date, which the chart's label and the list's line name too.
    sourceAsOf: "{sources}, as of {date}.",
    sourceNames: {
      documents: "World Bank documents and reports API",
      notices: "procurement notices",
      awards: "contract awards",
    } as Record<string, string>,
    show: "Show the table",
    hide: "Hide the table",
    caption: (name: string) => `Everything on the timeline of ${name}, in date order.`,
    count: (n: string) => `Showing all ${n} items.`,
    itemsNoun: "items",
    columns: { date: "Date", stratum: "Stratum", item: "Item", rating: "Rating", note: "Note" },
    stratumCaption: "What: records. How: operations. Why: evaluations.",
    // A mark's label on the chart.
    label: {
      pad: "PAD",
      isr: "ISR {sequence}",
      icr: "ICR",
      icr_review: "ICR Review",
      ppar: "PPAR",
      other: "Report",
      mid_term_review: "Mid-term review",
      restructuring: "Restructuring",
      contract: "{reference} signed",
    } as Record<string, string>,
    replaced: "{label}, replaced",
    reissued: "{label}, re-issued",
    contracts: (n: string) => `${n} contracts`,
    // An item's full name, in the table and the list: abbreviations spelled out.
    full: {
      pad: "Project Appraisal Document (PAD)",
      isr: "ISR {sequence}",
      icr: "Implementation Completion and Results Report (ICR)",
      icr_review: "ICR Review",
      ppar: "Project Performance Assessment Report (PPAR)",
      other: "Report",
    } as Record<string, string>,
    // A band's label, the first form that fits: the rating with its ISRs, the rating, the code with its ISRs, the code.
    band: {
      full: "{rating}, ISRs {first}–{last}",
      fullOne: "{rating}, ISR {first}",
      rating: "{rating}",
      code: "{code}, ISRs {first}–{last}",
      codeOne: "{code}, ISR {first}",
    },
    bandItem: "ISRs {first}–{last}",
    bandItemOne: "ISR {first}",
    bandLine: "ISRs {first}–{last} rated progress {rating}",
    bandLineOne: "ISR {first} rated progress {rating}",
    range: "{start} to {end}",
    tableRange: "{start} – {end}",
    // The disagreement line's label. The ticket fixes the numeral.
    chip: "2 reports disagree",
    // A tooltip's third line.
    tip: {
      disagrees: "Disagrees with {other}.",
      replacedBy: "Replaced by the re-issue of {date}.",
      isr: "{date}. Progress towards achievement of PDO.",
      from: "From {source}.",
      contract: "Contract signed.",
      group: "Select to list them.",
      band: "{start} to {end}. Progress towards achievement of PDO.",
      leans: "I lean on {lean}.",
      written: "{written}.",
      writtenDisagrees: "{written}. Disagrees with {other}.",
    },
    // Each item's accessible name. "to" stands in for the en dash, so a screen reader does not say "dash".
    name: {
      report: "{type}, {date}. {lane} lane. Item {i} of {n}.",
      reportReplaced: "{type}, {date}, replaced by its re-issue of {replaced}. {lane} lane. Item {i} of {n}.",
      reportDisagrees: "{type}, {date}. Disagrees with {other}. {lane} lane. Item {i} of {n}.",
      isr: "ISR {sequence}, {date}, rated progress {rating}. How lane. Item {i} of {n}.",
      // An ISR whose rating get_disagreements did not give.
      isrNoRating: "ISR {sequence}, {date}. How lane. Item {i} of {n}.",
      isrDisagrees: "ISR {sequence}, {date}, rated progress {rating}. Disagrees with {other}. How lane. Item {i} of {n}.",
      event: "{label}, {date}. How lane. Item {i} of {n}.",
      record: "Contract {reference} signed, {date}. What lane. Item {i} of {n}.",
      group: "{count} contracts signed in {year}. What lane. Item {i} of {n}.",
      band: "ISRs {first} to {last} rated progress {rating}, from {start} to {end}. How lane. Item {i} of {n}.",
      bandOne: "ISR {first} rated progress {rating}, from {start} to {end}. How lane. Item {i} of {n}.",
      disagreement: "2 reports disagree: {side1}, {date1}, and {side2}, {date2}. I lean on {lean}. Item {i} of {n}.",
    },
    group: (n: string, pid: string) => `${n} items on the timeline of ${pid}`,
    help: "Use the arrow keys to move between items. Left and Right go in date order. Up and Down move between lanes. Press Enter to open an item's source.",
    asOf: "As of {date}",
    // Over the list below 768 px, where no chart draws the "As of" label.
    asOfList: "This list shows what was public on {date}.",
    // The table's Note column.
    note: {
      disagrees: "Disagrees with {other}.",
      replaced: "Replaced by the re-issue of {date}.",
      trajectory: "A trajectory: each ISR rated its own period.",
      leans: "I lean on {lean}.",
    },
    // A report's short name in a sentence: "the ICR", "ISR 7". The server's copy (server.short) is the same.
    short: {
      pad: "the PAD",
      isr: "ISR {sequence}",
      icr: "the ICR",
      icr_review: "the ICR Review",
      ppar: "the PPAR",
      // A disagreement's side that rests on a contract's record (signed_on, signed_amount_usd), in the card's rule.
      record: "the contract record",
      other: "the report",
    } as Record<string, string>,
    sides: "{side1} and {side2}",
    laneEmpty: {
      why: "I have no evaluations for this project yet.",
      how: "I have no ISRs or other operations documents for this project yet.",
      what: "I have no contract records for this project.",
    } as Record<string, string>,
    noRatings: "I have no ISR ratings for this project.",
    // The band row's caption when get_disagreements did not answer, in place of noRatings.
    ratingsFailed: "I couldn't read this project's ISR ratings just now.",
    emptyTitle: "I don't have dated reports or records for this project yet.",
    emptyBody:
      "I add a project's reports and records to its timeline once I have read them. Data readiness shows which sources and years I have read.",
    emptyLink: "Data readiness",
    // get_disagreements' count of the ratings and dates it left out (the abstention state).
    abstention: (n: number) =>
      n === 1
        ? "I left out {n} rating or date that I read from this project's documents, because I couldn't find its words on the cited page."
        : "I left out {n} ratings or dates that I read from this project's documents, because I couldn't find their words on the cited pages.",
    abstentionCheck: "Counted by the disagreement check for this project.",
    // The title's count: where it came from, and that it opens the table.
    findingCheck: "Counted by the disagreement check for this project. Select it to show the table.",
    // Under the title, which already says what failed: what is missing until then, true of the chart and the list.
    // Without the check, no ISR is a side of a disagreement, so only the newest ISR keeps its own mark.
    failed: "Until I can, the timeline shows no rating bands, no dashed lines and only the newest ISR.",
    // The same for a project with no ISRs on its timeline.
    failedNoIsr: "Until I can, the timeline shows no rating bands and no dashed lines.",
    hidden: "I don't show disagreements on active projects in the public view, so I don't prejudge a project still under way.",
    loading: "Loading the timeline.",
    stillLoading: "Still loading the timeline.",
    error: "I couldn't load this project's timeline because the data service didn't answer.",
    permission: "Your account can't read Strata's tables, so I can't show this project's timeline.",
    // The evidence drawer's views a timeline mark opens (the 23 brief, sections 6 and 7.4).
    drawer: {
      fromTimeline: "From the timeline",
      fromTimelineItem: "{label}, {date}.",
      close: "Close the source",
      disagreement: {
        eyebrow: "{strata} · disagreement",
        heading: "{side1} and {side2}",
        switcher: "Reports in this disagreement",
        both: "Both reports",
        unknown: "I have no disagreement with this ID. The link may be incomplete.",
        notAsOf: "These two reports were not both public on {date}, so they did not disagree then.",
        close: "Close the reports",
      },
      // The strata of the two sides, joined: "How and Why".
      strataJoin: "{first} and {second}",
      claimLine: "{side1} and {side2} disagree about this.",
      showBoth: "Show both reports",
      ratings: {
        eyebrow: "How · operations",
        heading: "ISRs {first}–{last}, rated {rating}",
        headingOne: "ISR {first}, rated {rating}",
        trajectory:
          "Ratings that change from one ISR to the next describe different periods. I show them as a trajectory, not a disagreement.",
        caption: "ISR ratings of progress towards achievement of PDO",
        count: (n: string) => `Showing all ${n} ISRs.`,
        columns: { isr: "ISR", date: "Date", rating: "Progress towards achievement of PDO" },
        isr: "ISR {sequence}",
        source: "World Bank documents and reports API, the ISRs of {pid}.",
        close: "Close the ratings",
      },
      contracts: {
        eyebrow: "What · record",
        heading: "Contracts signed in {year}",
        // The table under the heading, which says what each row is rather than repeating the heading.
        tableTitle: "Each contract signed in {year}, in date order.",
        count: (n: string) => `Showing all ${n} contracts.`,
        columns: { contract: "Contract (STEP reference)", signed: "Signed", amount: "Signed amount (US$)" },
        notInRecord: "Not in the record",
        source: "World Bank contract awards and procurement notices, {pid}.",
        close: "Close the contracts",
      },
      doc: {
        heading: "{label}, {date}",
        labels: { type: "Document type", number: "Report number", date: "Document date", disclosed: "Disclosed", pages: "Pages" },
        // The as-of action (ticket 40; the 40 brief, 3.6): it opens the Timeline as of the day the report was disclosed.
        asofAction: "See Strata as of this date",
        asofCaption: (date: string) => `It opens this project as it was on ${date}, the day the World Bank disclosed this report.`,
        ratings: "Ratings in this report",
        ratingsCols: { rating: "Rating", value: "Value", where: "Where" },
        wherePara: "Paragraph {para}, page {page}",
        whereSection: "Section {section}, page {page}",
        wherePage: "PDF page {page}",
        inDisagreement: "{this} and {other} disagree about {subject}.",
        replaced: "IEG re-issued this review under the same number on {date}. I use the re-issue in current answers.",
        openReissue: "Open the re-issue",
        open: "Open the document",
        source: "World Bank documents and reports API, {type}, {pid}, {date}.",
        close: "Close the document",
      },
    },
    // The words the server writes into the chart's title and alt text (src/strata/server/timeline.py), which
    // `node web/lint/server-copy.ts --write` copies into src/strata/server/timeline_copy.json. The lint lane
    // fails when that file is out of date, so the words have one home. No model writes these sentences.
    server: {
      finding: {
        disagreeRatings: "{lead}, and {ratings}.",
        ratingsOnly: "{ratings}, and I found no reports that disagree.",
        disagreeOnly: "{lead}. I have no ISR ratings for this project.",
        neither: "I found no reports that disagree, and I have no ISR ratings for this project.",
        hiddenRatings: "{ratings}.",
        hiddenNone: "I have no ISR ratings for this project.",
        failed: "I couldn't read this project's ISR ratings or check its reports for disagreements just now.",
        leadOne: "Two reports disagree",
        leadSeveral: "{count} pairs of reports disagree",
        fell: "ISR ratings of progress fell from {first} to {last}",
        rose: "ISR ratings of progress rose from {first} to {last}",
        same: "ISR ratings of progress were {rating} at the first ISR and at the last",
      },
      alt: {
        populated: "Timeline of {pid} from {first} to {last} in three lanes: {why}, {how} and {what}.",
        empty: "Timeline of {pid}, with no dated reports or records yet.",
        evaluations: { none: "no evaluations", one: "{n} evaluation", many: "{n} evaluations" },
        operations: { none: "no operations items", one: "{n} operations item", many: "{n} operations items" },
        records: { none: "no records", one: "{n} record", many: "{n} records" },
        ratings: "ISR ratings of progress went from {first} to {last} over {count} ISRs.",
        ratingsSame: "ISR ratings of progress stayed {rating} over {count} ISRs.",
        noRatings: "I have no ISR ratings for this project.",
        // When get_disagreements did not answer: Strata could not read the ratings, which is not having none.
        ratingsFailed: "I couldn't read this project's ISR ratings just now.",
        line: "A dashed line joins {side1} and {side2}, which disagree.",
        noLines: "No reports disagree.",
        // The page's as-of date, last, when the page asked for one: the drawn label is inside the image.
        asOf: "It shows what was public on {date}.",
      },
      short: {
        pad: "the PAD",
        isr: "ISR {sequence}",
        icr: "the ICR",
        icr_review: "the ICR Review",
        ppar: "the PPAR",
        other: "the report",
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
    // A package's own difference from its cost estimate (ticket 31, rule 11): "+21.4%" with a true minus sign
    // for below, and "21.4 percent above" in sentences and alt text.
    signedPercent: (sign: string, n: string) => `${sign}${n}%`,
    plus: "+",
    minus: "−",
    percentAbove: (n: string) => `${n} percent above`,
    percentBelow: (n: string) => `${n} percent below`,
    percentAtZero: "0 percent above",
  },
} as const;
