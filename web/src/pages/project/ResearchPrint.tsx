// The Deep research brief as the browser prints it (ticket 149): the sample's sheets
// (.notes/prism-sample/template/build5.py and its report5.html), one Letter sheet per section with the running header
// (the project and the section) and the footer (Prism, the read date, the one-line disclaimer and the sheet's number),
// the navy cover first. It sits outside the app's frame, under the body, so the print stylesheet
// (styles/research.css) can hide the app's chrome and show only these sheets; on screen it is never shown.
// "Download as PDF" calls window.print(), so the browser's own print writes the PDF and no server renders it.
//
// The developments run on as many sheets as they need, eleven to a sheet as the sample's first held, and each site
// takes its own sheet with its Sentinel-2 grids side by side. Markers are the sample's small numbered pills, each the
// number of its source on the last sheet.
import { createPortal } from "react-dom";
import type { ReactNode } from "react";
import logo from "../../assets/world-bank-logo.svg";
import { Fill } from "../../components/Fill";
import { copy } from "../../copy";
import { formatDate } from "../../lib/format";
import { briefNumbers, developmentSheets, itemFor, itemName, notReachedIn, satelliteFor, sourceName, sourceWords, tileYear, voiceTemplate, type Brief, type ResearchSentence, type Sections } from "../../lib/research";
import { fill } from "../../routes";

const words = copy.research;

function Cites({ ids, numbers }: { ids: string[]; numbers: Map<string, number> }) {
  return (
    <>
      {ids.map((id) =>
        numbers.has(id) ? (
          <span key={id} className="cite">
            {numbers.get(id)}
          </span>
        ) : null,
      )}
    </>
  );
}

function Said({ sentence, numbers }: { sentence: ResearchSentence; numbers: Map<string, number> }) {
  return (
    <>
      {sentence.text}
      <Cites ids={sentence.evidence_ids} numbers={numbers} />
    </>
  );
}

function Sentences({ sentences, numbers }: { sentences: ResearchSentence[]; numbers: Map<string, number> }) {
  return (
    <>
      {sentences.map((sentence, index) => (
        <span key={index}>
          {index > 0 && " "}
          <Said sentence={sentence} numbers={numbers} />
        </span>
      ))}
    </>
  );
}

type Sheet = { label: string; body: ReactNode };

// The sources not reached under the section they feed, one line each, as on screen.
function NotReachedNote({ brief, sectionKey }: { brief: Brief; sectionKey: keyof Sections }) {
  return (
    <>
      {notReachedIn(brief, sectionKey).map((entry) => (
        <p key={entry.source} className="note" data-not-reached={entry.source}>
          {words.notReached(capitalFirst(sourceWords(entry.source, entry.label)))}
          {entry.note && " "}
          {entry.note}
        </p>
      ))}
    </>
  );
}

const capitalFirst = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

export function ResearchPrint({ brief, pid, name, country, agencies }: { brief: Brief; pid: string; name: string; country: string | null; agencies: string[] }) {
  const { sections } = brief;
  const numbers = briefNumbers(sections);
  const read = brief.read_on ? formatDate(brief.read_on) : "";
  const closing = brief.project?.closing_date ? fill(words.cover.closing, { date: formatDate(brief.project.closing_date) }) : null;
  const sub = [pid, country, agencies.join(", "), closing].filter((part): part is string => Boolean(part));

  const sheets: Sheet[] = [];
  sheets.push({
    label: words.section.picture,
    body: (
      <>
        {sections.headline && (
          <h1>
            <Said sentence={sections.headline} numbers={numbers} />
          </h1>
        )}
        <div className="brief">
          {sections.picture.map((sentence, index) => (
            <p key={index}>
              <Said sentence={sentence} numbers={numbers} />
            </p>
          ))}
        </div>
        <NotReachedNote brief={brief} sectionKey="picture" />
        <h2>{words.section.bottomLine}</h2>
        <ol className="bottom">
          {sections.bottom_line.map((sentence, index) => (
            <li key={index}>
              <Said sentence={sentence} numbers={numbers} />
            </li>
          ))}
        </ol>
      </>
    ),
  });
  const devSheets = developmentSheets(sections.developments);
  devSheets.forEach((rows, index) => {
    const title = index === 0 ? words.section.developments : words.section.developmentsMore;
    sheets.push({
      label: title,
      body: (
        <>
          <h1>{title}</h1>
          <table className="dev">
            <tbody>
              {rows.map((row, at) => (
                <tr key={at}>
                  <td className="d">{row.date_known && row.date ? formatDate(row.date, { style: "table" }) : words.undated}</td>
                  <td>
                    <Sentences sentences={row.sentences} numbers={numbers} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {index === devSheets.length - 1 && <NotReachedNote brief={brief} sectionKey="developments" />}
        </>
      ),
    });
  });
  sections.by_site.forEach((site, index) => {
    const satellites = satelliteFor(brief, site);
    sheets.push({
      label: site.location?.name ?? words.section.bySite,
      body: (
        <>
          <h1>
            <Said sentence={site.title} numbers={numbers} />
          </h1>
          <p>
            <Sentences sentences={site.sentences} numbers={numbers} />
          </p>
          {satellites.map((item) => {
            const [first, last] = [item.image_urls[0], item.image_urls[item.image_urls.length - 1]];
            const years = [tileYear(first) ?? "", tileYear(last) ?? ""];
            return (
              <div key={item.evidence_id} className="figure">
                <div className="pairs">
                  {[first, last].map((tiles, index) => (
                    <div key={index} className="s2">
                      <div className="when">{years[index]}</div>
                      <div className="tiles">
                        {tiles.slice(0, 9).map((url) => (
                          <img key={url} src={url} alt="" />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <p className="caption">
                  <Fill template={words.satellite} slots={{ place: item.location?.name ?? item.title, first: years[0], last: years[1] }} />
                  <Cites ids={[item.evidence_id]} numbers={numbers} />
                </p>
              </div>
            );
          })}
          {index === sections.by_site.length - 1 && <NotReachedNote brief={brief} sectionKey="by_site" />}
        </>
      ),
    });
  });
  sheets.push({
    label: words.section.voices,
    body: (
      <>
        <h1>{words.section.voices}</h1>
        <div className="quotes">
          {sections.voices.map((voice, index) => (
            <blockquote key={index}>
              <p>{voice.text}</p>
              <footer>
                <Fill
                  template={voiceTemplate(voice)}
                  slots={{ who: voice.who, outlet: voice.outlet, date: voice.date ? formatDate(voice.date) : "" }}
                />
                <Cites ids={voice.evidence_ids} numbers={numbers} />
              </footer>
            </blockquote>
          ))}
        </div>
        <NotReachedNote brief={brief} sectionKey="voices" />
      </>
    ),
  });
  sheets.push({
    label: words.section.questions,
    body: (
      <>
        <h1>{words.section.questions}</h1>
        <ol className="questions">
          {sections.questions.map((question, index) => (
            <li key={index}>
              <b>{question.lead}</b> <Sentences sentences={question.sentences} numbers={numbers} />
            </li>
          ))}
        </ol>
        <NotReachedNote brief={brief} sectionKey="questions" />
        <h2>{words.section.couldNotSee}</h2>
        <p className="note">
          <Sentences sentences={sections.could_not_see} numbers={numbers} />
        </p>
      </>
    ),
  });
  sheets.push({
    label: words.section.sources,
    body: (
      <>
        <h1>{words.section.sources}</h1>
        <ol className="sources">
          {[...numbers.keys()].map((id) => {
            const item = itemFor(brief, id);
            return (
              <li key={id}>
                <span className="b">{numbers.get(id)}</span>
                <span>
                  {item ? (
                    <>
                      {itemName(item)}
                      {". "}
                      {item.title}
                      {". "}
                      <a href={item.url}>{item.url.replace(/^https?:\/\//, "")}</a>
                    </>
                  ) : (
                    sourceName(brief, id)
                  )}
                </span>
              </li>
            );
          })}
        </ol>
        {read && <p className="note">{fill(words.printNote, { date: read })}</p>}
      </>
    ),
  });

  const header = fill(words.header, { name, pid });
  const footer = fill(words.footer, { date: read });
  return createPortal(
    <div data-research-print lang="en">
      <div className="research-sheet navy" data-sheet="cover">
        <div className="body">
          <div className="cover-top">
            <img src={logo} alt={words.cover.logo} />
            <div className="brand">
              <div>
                <div className="word">{words.cover.word}</div>
                <div className="tag">{words.cover.tagline}</div>
              </div>
            </div>
          </div>
          <div className="cover-mid">
            <p className="cover-kicker">{words.cover.kicker}</p>
            <h1 className="cover-title">{fill(words.cover.title, { name })}</h1>
            <p className="cover-sub">{sub.join(" · ")}</p>
            <div className="rule" />
            <p className="cover-meta">{fill(words.cover.meta, { date: read })}</p>
          </div>
          <div className="cover-bottom">
            <p>{words.cover.about}</p>
            <p className="cover-small">{words.cover.small}</p>
          </div>
        </div>
      </div>
      {sheets.map((sheet, index) => (
        <div key={index} className="research-sheet" data-sheet={index + 1}>
          <div className="hdr" data-sheet-header>
            <span>{header}</span>
            <span data-sheet-label>{sheet.label}</span>
          </div>
          <div className="body">{sheet.body}</div>
          <div className="ftr" data-sheet-footer>
            <span>{footer}</span>
            <span data-sheet-number>{index + 1}</span>
          </div>
        </div>
      ))}
    </div>,
    document.body,
  );
}
