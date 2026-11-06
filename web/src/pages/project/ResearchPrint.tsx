// The Deep research brief as the browser prints it (ticket 149): the sample's sheets
// (.notes/prism-sample/template/build5.py and its report5.html), one Letter sheet per section with the running header
// (the project and the section) and a footer that is the sheet's number alone, the navy cover first (ticket 156). Each
// sheet opens with its section's title over a navy rule, so every main heading starts a page; the picture reads as short
// paragraphs, and developments, sites and questions as one-sentence bullets. The one-line disclaimer sits once, on the
// last sheet. It sits outside the app's frame, under the body, so the print stylesheet
// (styles/research.css) can hide the app's chrome and show only these sheets; on screen it is never shown.
// "Download as PDF" calls window.print(), so the browser's own print writes the PDF and no server renders it.
//
// The developments run on as many sheets as they need, eleven to a sheet as the sample's first held, and each site
// takes its own sheet with its Sentinel-2 grids side by side. Markers are the sample's small numbered pills, each the
// number of its source on the last sheet.
//
// Ticket 158: no blank frame and no figure split across a page. Every picture carries its width and height, so the
// page breaks are laid out before the pixels arrive; the tiles come through Prism's route, and a tile or a photo that
// fails says why (components/ResearchImages.tsx). A site's sheet holds its title, its bullets and at most one
// satellite pair; its photos go on their own sheet after it, four to a sheet and two to a row, whenever the site has a
// pair or more than one photo. "Download as PDF" waits for the pictures before it prints (ResearchPdf.tsx).
import { createPortal } from "react-dom";
import type { ReactNode } from "react";
import logo from "../../assets/world-bank-logo.svg";
import { Fill } from "../../components/Fill";
import { PhotoFrame, Tile, tileSentences, useTileFailures } from "../../components/ResearchImages";
import { copy } from "../../copy";
import { fieldPhotosPath, type FieldPhoto, type FieldPhotoList } from "../../lib/fieldPhotos";
import { formatDate } from "../../lib/format";
import { useLoad } from "../../lib/load";
import { briefNumbers, developmentSheets, itemFor, itemName, notReachedIn, PAIR_HEIGHT, paragraphsOf, PRINT_BUDGET, satelliteFor, siteHeight, sourceName, sourceSheets, sourceWords, tileYear, voiceTemplate, type Brief, type ResearchItem, type ResearchSentence, type Sections } from "../../lib/research";
import { address } from "../../lib/router";
import { useStore } from "../../lib/store";
import { withReadParams } from "../../lib/view";
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

// One sentence to a bullet (ticket 156).
function Bullets({ sentences, numbers }: { sentences: ResearchSentence[]; numbers: Map<string, number> }) {
  return (
    <ul className="bullets">
      {sentences.map((sentence, index) => (
        <li key={index}>
          <Said sentence={sentence} numbers={numbers} />
        </li>
      ))}
    </ul>
  );
}

// A sheet's section title over the navy rule that opens the section (ticket 156).
function Title({ children }: { children: ReactNode }) {
  return <h1 className="section">{children}</h1>;
}

const photoWords = copy.research.photos;

function photoLine(photo: FieldPhoto): string {
  const when = photo.taken_on ? photoWords.taken(formatDate(photo.taken_on)) : photoWords.noDate;
  const where = photo.place ? photoWords.near(photo.place) : photoWords.noPlace;
  return fill(words.photoLine, { when, where });
}

// A field photo with its caption, the day its camera recorded and its place (ticket 156), in a 4:3 frame that shows the
// whole picture or says why it did not load (ticket 158).
function PhotoFigure({ photo }: { photo: FieldPhoto }) {
  return (
    <figure className="photo" data-print-photo={photo.photo_id}>
      <PhotoFrame src={photo.url} />
      <figcaption>
        {photo.caption} {photoLine(photo)}
      </figcaption>
    </figure>
  );
}

type Sheet = { label: string; body: ReactNode };

// A site's two Sentinel-2 grids side by side, with the caption and a sentence for any tile that did not load.
function SatellitePair({ item, numbers }: { item: ResearchItem; numbers: Map<string, number> }) {
  const [first, last] = [item.image_urls[0], item.image_urls[item.image_urls.length - 1]];
  const years = [tileYear(first) ?? "", tileYear(last) ?? ""];
  const [failures, fail] = useTileFailures();
  const failed = tileSentences([first, last], years, failures);
  return (
    <div className="figure" data-print-satellite>
      <div className="pairs">
        {[first, last].map((tiles, index) => (
          <div key={index} className="s2">
            <div className="when">{years[index]}</div>
            <div className="tiles">
              {tiles.slice(0, 9).map((url) => (
                <Tile key={url} url={url} failed={failures[url]} onFail={fail} />
              ))}
            </div>
          </div>
        ))}
      </div>
      <p className="caption">
        <Fill template={words.satellite} slots={{ place: item.location?.name ?? item.title, first: years[0], last: years[1] }} />
        {failed.map((sentence) => (
          <span key={sentence} data-tiles-failed>
            {" "}
            {sentence}
          </span>
        ))}
        <Cites ids={[item.evidence_id]} numbers={numbers} />
      </p>
    </div>
  );
}

// Photos on a sheet of their own: four to a sheet, two to a row, so a figure never runs past its page.
const PHOTOS_PER_SHEET = 4;
const inFours = <T,>(all: T[]): T[][] => Array.from({ length: Math.ceil(all.length / PHOTOS_PER_SHEET) }, (_, at) => all.slice(at * PHOTOS_PER_SHEET, (at + 1) * PHOTOS_PER_SHEET));


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
  // The team's field photos (ticket 150), which only the team reads: their own sheet, after the sites.
  const search = useStore(address).search;
  const [photoLoad] = useLoad<FieldPhotoList>(withReadParams(fieldPhotosPath(pid), search));
  const photos = photoLoad.status === "ready" && !photoLoad.data.preview ? photoLoad.data.photos : [];
  const numbers = briefNumbers(sections);
  const read = brief.read_on ? formatDate(brief.read_on) : "";
  const closing = brief.project?.closing_date ? fill(words.cover.closing, { date: formatDate(brief.project.closing_date) }) : null;
  const sub = [pid, country, agencies.join(", "), closing].filter((part): part is string => Boolean(part));

  const sheets: Sheet[] = [];
  sheets.push({
    label: words.section.picture,
    body: (
      <>
        <Title>{words.section.picture}</Title>
        {sections.headline && (
          <p className="lead">
            <Said sentence={sections.headline} numbers={numbers} />
          </p>
        )}
        <div className="brief">
          {paragraphsOf(sections.picture).map((paragraph, index) => (
            <p key={index} data-picture-paragraph>
              <Sentences sentences={paragraph} numbers={numbers} />
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
  const devSheets = developmentSheets(sections.developments, notReachedIn(brief, "developments").length);
  devSheets.forEach((rows, index) => {
    const title = index === 0 ? words.section.developments : words.section.developmentsMore;
    sheets.push({
      label: title,
      body: (
        <>
          <Title>{title}</Title>
          <table className="dev">
            <tbody>
              {rows.map((row, at) => (
                <tr key={at}>
                  <td className="d">{row.date_known && row.date ? formatDate(row.date, { style: "table" }) : words.undated}</td>
                  <td>
                    <Bullets sentences={row.sentences} numbers={numbers} />
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
  // Each photo sits under the site whose words name its place; the rest get their own sheet after the sites.
  const siteOf = (photo: FieldPhoto) =>
    photo.place ? sections.by_site.findIndex((site) => [site.title, ...site.sentences].some((said) => said.text.includes(photo.place!))) : -1;
  const unplaced = photos.filter((photo) => siteOf(photo) < 0);
  sections.by_site.forEach((site, index) => {
    const satellites = satelliteFor(brief, site);
    const here = photos.filter((photo) => siteOf(photo) === index);
    const name = site.location?.name ?? words.section.bySite;
    // The site's own sheet keeps one photo only when it has no satellite pair; otherwise its photos get their own sheet.
    const keepHere = satellites.length === 0 && here.length === 1;
    // A site whose words leave no room for its pair on the page puts the pair on the next sheet (ticket 158).
    const pairHere = siteHeight(site) + PAIR_HEIGHT <= PRINT_BUDGET;
    sheets.push({
      label: name,
      body: (
        <>
          <Title>{index === 0 ? words.section.bySite : words.section.bySiteMore}</Title>
          <h2>
            <Said sentence={site.title} numbers={numbers} />
          </h2>
          <Bullets sentences={site.sentences} numbers={numbers} />
          {pairHere &&
            satellites.slice(0, 1).map((item) => (
              <SatellitePair key={item.evidence_id} item={item} numbers={numbers} />
            ))}
          {keepHere && (
            <div className="photos near">
              {here.map((photo) => (
                <PhotoFigure key={photo.photo_id} photo={photo} />
              ))}
            </div>
          )}
        </>
      ),
    });
    // A second pair for the same site, rare, takes a sheet of its own, as does a pair with no room beside its words.
    satellites.slice(pairHere ? 1 : 0).forEach((item) => {
      sheets.push({
        label: name,
        body: (
          <>
            <Title>{words.section.bySiteMore}</Title>
            <h2>{name}</h2>
            <SatellitePair item={item} numbers={numbers} />
          </>
        ),
      });
    });
    if (!keepHere) {
      const groups = inFours(here);
      groups.forEach((group) => {
        const title = fill(words.photosNear, { site: site.location?.name ?? here[0].place ?? words.section.bySite });
        sheets.push({
          label: title,
          body: (
            <>
              <Title>{words.section.bySiteMore}</Title>
              <h2>{title}</h2>
              <div className="photos" data-print-photo-sheet>
                {group.map((photo) => (
                  <PhotoFigure key={photo.photo_id} photo={photo} />
                ))}
              </div>
            </>
          ),
        });
      });
    }
  });
  // The sites' sources not reached, under the last of the sites' sheets.
  if (sections.by_site.length > 0) {
    const end = sheets[sheets.length - 1];
    sheets[sheets.length - 1] = {
      ...end,
      body: (
        <>
          {end.body}
          <NotReachedNote brief={brief} sectionKey="by_site" />
        </>
      ),
    };
  }
  inFours(unplaced).forEach((group, at) => {
    sheets.push({
      label: words.photosSheet,
      body: (
        <>
          <Title>{words.photosSheet}</Title>
          {at === 0 && <p className="note">{words.photosSheetAbout}</p>}
          <div className="photos" data-print-photo-sheet>
            {group.map((photo) => (
              <PhotoFigure key={photo.photo_id} photo={photo} />
            ))}
          </div>
        </>
      ),
    });
  });
  sheets.push({
    label: words.section.voices,
    body: (
      <>
        <Title>{words.section.voices}</Title>
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
        <Title>{words.section.questions}</Title>
        <ol className="questions">
          {sections.questions.map((question, index) => (
            <li key={index}>
              <b>{question.lead}</b>
              <Bullets sentences={question.sentences} numbers={numbers} />
            </li>
          ))}
        </ol>
        <NotReachedNote brief={brief} sectionKey="questions" />
      </>
    ),
  });
  // What the run could not see on its own sheet, so the questions keep theirs (ticket 156).
  sheets.push({
    label: words.section.couldNotSee,
    body: (
      <>
        <Title>{words.section.couldNotSee}</Title>
        <Bullets sentences={sections.could_not_see} numbers={numbers} />
      </>
    ),
  });
  // The sources, as many to a sheet as fit its page (ticket 158), so a long list never runs past its sheet's page.
  const sheetsOfSources = sourceSheets(brief, [...numbers.keys()]);
  sheetsOfSources.forEach((ids, at) => {
    const title = at === 0 ? words.section.sources : words.section.sourcesMore;
    const last = at === sheetsOfSources.length - 1;
    sheets.push({
      label: title,
      body: (
        <>
        <Title>{title}</Title>
        <ol className="sources">
          {ids.map((id) => {
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
        {last && read && <p className="note">{fill(words.printNote, { date: read })}</p>}
        {last && (
          <p className="note" data-disclaimer>
            {words.disclaimer}
          </p>
        )}
        </>
      ),
    });
  });

  const header = fill(words.header, { name, pid });
  return createPortal(
    <div data-research-print lang="en">
      <div className="research-sheet navy" data-sheet="cover">
        <div className="body">
          <div className="cover-top">
            <img src={logo} alt={words.cover.logo} width={140} height={28} />
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
          </div>
          <div className="cover-bottom">
            <p>{words.cover.about}</p>
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
            <span data-sheet-number>{index + 1}</span>
          </div>
        </div>
      ))}
    </div>,
    document.body,
  );
}
