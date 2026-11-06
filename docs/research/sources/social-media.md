# Social media in deep research

By Surya Yadav, November 6, 2026

Deep research reads what people post in public about a project's places. The design comes from my ProcIntel work. Prism's reader is `src/strata/research/sources/mastodon.py`, and its entry in the registry is `[sources.mastodon]` in `config/research.toml`.

## What it reads

The reader asks Mastodon's public tag timelines on mastodon.social. Each timeline gives the newest 40 posts with that tag. The registry names three kinds of tag in `settings.tags`:

- the country's name, such as `kenya`
- the sector's first word, such as `water`
- each project location's name, written as a hashtag is written, so West Pokot becomes `westpokot`

A tag timeline holds public posts only. The reader signs in to nothing and sends Prism's named client, `prism-research/0.1`. It waits at least one second between two calls and reuses an answer for six hours.

## How a post is kept or dropped

A tag only brings a post to the reader. It never keeps the post. The reader keeps a post only when its text names a project place, an agency, or the project's own name, together with one of the sector's words from `[sector_words]` in `config/research.toml`. For a water project those words include water, sanitation, sewer, borehole and pipeline.

- An agency's short name in capitals, such as NWWDA, counts only when the post writes it in capitals as a whole word.
- A place alone is not enough. A post about Mombasa's football or its music has no sector word, so it stays out.
- A post that two tags both return is kept once.
- A post with no link is dropped, because a person must be able to open it.

For each kept post, Prism keeps the post's own words with a link to it. Contact details are stripped, and the text is cut at 4,000 characters. The author is the name the account shows, or its user name when it shows none. Prism never keeps an email address or a phone number. The post's date is the day it was posted.

When no tag timeline answers, the source is not reached. The note says why: a 403, a 429, a bot check page, or a host that did not answer. When at least one answers, the note says how many timelines Prism read and how many posts it kept.

## A post can start a check but never close one

This is the rule the brief follows for every post. A post is one person's words. It can point a procurement specialist at something to look at, such as a burst pipe or a site that went quiet. It cannot show that works are done, that a contract is fine, or that a complaint was settled.

In Prism today this rule is not a separate check in the code. What keeps it is the way every brief is written and checked. The brief writer may say only what the items it cites say, and Prism's verifier removes any sentence that does not hold against them. A sentence that rests on a post cites that post, and the citation opens the post itself.

## What the brief does with posts

The writer gets each kept post as an item of kind `social`, with its author, date, text and link. It can quote a post's words in the brief, cited to the post. When the run holds public posts and none is about the project's works, the brief says so in its section on what the run could not see (`src/strata/agent/instructions/research_brief_writer.md`).

The stored run for P156634 that the demo uses, dated November 5, 2026, holds no post.

## What it cannot show

The registry lists two limits for Mastodon:

- A tag timeline holds the newest 40 posts with the tag that reached mastodon.social, not every post.
- A post is kept only when it names a project location or an agency together with a sector word, so a tag alone never brings a post in.

So a post that uses none of the tags is never seen, and a post on another server reaches the reader only if it reached mastodon.social.

## Sources listed as not connected

Three social sources sit in the registry with `enabled = false` and the reason beside each:

- Reddit refused clients that are not browsers when probed on November 5, 2026.
- Bluesky's search refused clients that are not browsers when probed on November 5, 2026.
- X's search needs a paid key, which Prism does not hold.

Prism never pretends to be a browser to get past a refusal. Turning one of them on later is a change to `config/research.toml` and a reader module.
