# Stock-take, October 2026

What was in the repository before the restructure, what happened to each part, and what still needs a decision.

## Before

The site was a set of standalone HTML pages with no shared layout, deployed as static files by `.github/workflows/static.yml`.

| Path | What it was | Notes |
|---|---|---|
| `index.html` | The home page, which was the entry editor: paste an entry into a Quill box, add links, press Process, copy the generated HTML into a file. | Readers landing on the site saw a data-entry form. |
| `entries/*.html` | 18 entry pages made with the editor (aa to bocland). | Not linked from anywhere. Generated "See also" links were often wrong (on *Accusativ* and *abiddan* they were whole sentences). The linker had nested links (`<a><abbr>Ersetzt <a>durch</a></abbr></a>`), linked "I" in "I Cn" as a law code of its own, linked the superscript F that marks French as a manuscript, and linked italic *Abt* ("abbot") to the laws of Æthelberht. |
| `lawAbb.html`, `gramAbb.html` | Searchable lists of law codes and grammatical abbreviations, read from `data/markLaw.js` and `data/markforward.js`. | Two near-copies of the same code. |
| `data/markLaw.js` | 138 law codes, texts and manuscript sigla. | See [Data problems](#data-problems). |
| `data/markforward.js` | 652 grammatical abbreviations and German terms. | 22 rows have a trailing space in the printed form. |
| `style.css` | Shared stylesheet. | Turned every link into a bordered button; named fonts it never loaded; had two conflicting sets of table styles. The Statuta Vetera pages didn't use it. |
| `StatutaVetera/index.html` | Search and filters over the manuscript descriptions in `tei/`. | Listed the files through the GitHub API, which allows 60 requests an hour per visitor, so the page could stop working for busy users. Titles linked to the raw XML. |
| `StatutaVetera/sidebyside.html` | Statutes of the Realm viewer: archive.org scan beside commentary, by volume. | Also used the GitHub API. Volumes 7 to 11 have placeholder archive.org identifiers. Only volume 5 has commentary, and its six pages are test text ("Page 3. Have you read this comment?"). |
| `StatutaVetera/tei-gen.html` | Turns a catalogue description into a manuscript TEI file. | Had a download function but no button for it. |
| `tei/*.xml` | 59 manuscript descriptions. | All well formed. 4 have no dimensions. |
| `commentary5/*.html` | Six test commentary pages for the viewer. | Test text. |
| `citations/adair.html` | "Adair citation" page with a placeholder table ("A aa a."). | Test page, not linked. |
| `markdownTest.md` | A copy of the README with a title. | Test file. |
| `images/banner.png` | The eLiebermann banner. | Kept. |

## After

The site is built with Jekyll and GitHub Pages, on the model of [Common Ground](https://github.com/historicalesque/carlton). See the [README](../README.md) for how it works.

| Before | Now |
|---|---|
| Home page was the editor | `index.html` is a home page with the menu, a search box and links to every part of the site. Its text is in `pages/Home.xml`. |
| No About page | `about.html`, text in `pages/About.xml`. |
| 18 HTML entries, not linked | 977 TEI entries in `entries/`: all 976 in *A - boc.docx* plus *bocland*. The hand-added definition on *Accusativ* and translation and links on *bocland* were carried over. |
| No way to browse entries | `dictionary.html`: A–Z list with search and a language filter. `entry.html?id=…` shows one entry. |
| Editor made HTML | `contribute.html` makes a TEI file, previews it, checks whether the entry already exists, and can open an existing entry for correction. |
| Entries pasted one at a time | `import.html` (and `tools/import-docx.js`) turns a whole Word document into TEI files. See [IMPORT.md](IMPORT.md). |
| `lawAbb.html`, `gramAbb.html` | Same addresses, so old links still work; now one shared script (`scripts/abbreviations.js`) and the site layout. |
| Test files (`markdownTest.md`, `citations/adair.html`, `commentary5/`) | Deleted. |
| Statuta Vetera pages | Same addresses, in the site layout, with no GitHub API calls: the file lists are built in when the site is built. Each manuscript has its own page (`StatutaVetera/manuscript.html?id=…`). The viewer's volumes are listed in `_data/statutes_volumes.yml`. |
| `style.css` | Rewritten as one stylesheet for every page. |
| `data/markLaw.js`, `data/markforward.js` (JSONP) | `data/markLaw.json`, `data/markforward.json`: plain JSON, one row per line. |
| Static deploy | `.github/workflows/static.yml` now lists the entries (`tools/build-index.js`) and builds with Jekyll before deploying. |

The old entry addresses (`entries/abbod.html`) no longer work. Nothing on the site linked to them.

## Data problems

- **`data/markLaw.json`: the notes are one row out.** The "Notes: Information & Editions" and "Notes: Start page in Liebermann Vol. I" columns describe the *next* law code. For example, the row for *Abt* (Æthelberht) has start page 16, which is where Alfred begins; *Af* (Alfred) has 126, the start of Alfred and Guthrum; the *CHn cor* row's note is about *Cn 1020*; the *Hn Mon* row's note is about I Edgar. Probably a spreadsheet sort that left these columns behind. The law code list now shows both columns, shaded and marked "under review", so they can be checked against the rows they belong to; tick *Show every row in one table, in file order* to see the shift. Fix them in `data/markLaw.json`, then remove `review: true` from those columns in `scripts/abbreviations.js`. **Fixed 13 October 2026** from the corrected glossary spreadsheet; the "under review" shading and ⚠ marks have been removed.
- **Trailing spaces** in `'VII Atr '`, `'Excom VII '` and 22 rows of `markforward.json`. The linker now ignores them.
- **Single-letter sigla** (A, B, D, E, F, G, H, I, K, O, Q) are linked wherever they stand alone in roman type. That is right for manuscript sigla, but will occasionally catch something else, such as the "I" of a homograph number written without its bracket.

## Needs a decision

| Item | Suggestion |
|---|---|
| Viewer volumes 7–11 | Find the archive.org scans, or drop those volumes from `_data/statutes_volumes.yml`. |
| Old entry addresses | Add redirects if anyone has bookmarked them. |
