# eLiebermann: An Online Dictionary of Pre-Conquest English Law

**Live site:** https://notamitchell.github.io/law/

> ### Looking for the dictionary? You probably want the website, not this page.
>
> This page is the technical documentation for the people who build and maintain the site.
>
> - **Look up a word:** [Dictionary](https://notamitchell.github.io/law/dictionary.html)
> - **Abbreviations:** [Law codes and manuscripts](https://notamitchell.github.io/law/lawAbb.html) · [Grammatical abbreviations](https://notamitchell.github.io/law/gramAbb.html)
> - **Statuta Vetera:** [Manuscripts](https://notamitchell.github.io/law/StatutaVetera/) · [Statutes of the Realm viewer](https://notamitchell.github.io/law/StatutaVetera/sidebyside.html)
> - **Add or correct an entry:** [Add an entry](https://notamitchell.github.io/law/contribute.html), or *Suggest a correction* at the foot of any entry
> - **Import a Word document of entries:** [Bulk import](https://notamitchell.github.io/law/import.html)

---

## Contents

- [Overview](#overview)
- [How the site works](#how-the-site-works)
- [Repository layout](#repository-layout)
- [Adding entries](#adding-entries)
- [Running the site locally](#running-the-site-locally)
- [Roadmap](#roadmap)
- [Source](#source)

---

## Overview

eLiebermann is a digital edition of the *Wörterbuch*, the dictionary in Felix Liebermann's *Die Gesetze der Angelsachsen* (1903–1916), the standard edition of the laws of England before the Norman Conquest. Alongside it, the site describes manuscripts of the *Statuta Vetera* and has a viewer for the *Statutes of the Realm*.

It is a static website hosted on **GitHub Pages** and built with **Jekyll**, using the `jekyll-theme-cayman` theme with a custom layout. It has no server or database of its own:

- **Entries** are TEI XML files in `entries/`, one per headword. The browser fetches them and renders them on the fly. The format is in [docs/SCHEMA.md](docs/SCHEMA.md).
- **New entries** are made in the browser, by the [contribution form](contribute.html) for one entry or the [bulk import](import.html) for a whole Word document. Both produce TEI files, which an editor adds to `entries/` on GitHub. Sending submissions straight to the site is on the [roadmap](#roadmap).

The project is deliberately a **perpetual work in progress**. Entries that don't exist yet are invitations to contribute, not defects.

Nothing is published until it is committed to `main`. GitHub Pages rebuilds the site automatically after each commit, usually within a minute or two.

## How the site works

```
 Visitor ──▶ index / dictionary / entry.html?id=… / lawAbb / gramAbb / StatutaVetera/…
                 │                     │                  │
                 ▼                     ▼                  ▼
          data/entries.json     entries/<id>.xml    data/markLaw.json, data/markforward.json
          (list for search,     (fetched and        (law codes and abbreviations)
           built on deploy)      rendered in the
                                 browser)

 Contributor ──▶ contribute.html (one entry) or import.html (a Word document)
                   │  builds TEI with scripts/eliebermann.js, links law codes and abbreviations
                   ▼
                 TEI file(s) downloaded ──▶ editor uploads to entries/ on GitHub ──▶ site rebuilds
```

- **Entry pages** (`entry.html?id=abbod`) fetch `entries/abbod.xml` and render it with `ELieb.renderTei()`. The `id` can also be a headword (`entry.html?id=æbære`). If there is no file, the page offers to start one.
- **The Dictionary page** reads `data/entries.json`, which `tools/build-index.js` writes on every deploy from the files in `entries/`. If it's missing (for example in a local build where you didn't run the script), the page falls back to a plain list of file names.
- **Abbreviation links.** When an entry is made, `ELieb.linkAbbreviations()` links every law code, manuscript siglum and abbreviation listed in `data/markLaw.json` and `data/markforward.json`, longest match first, and stores the links in the TEI. Law codes are only linked in roman type, since Liebermann's italics are German.
- **Site pages are TEI too.** The text of Home and About is in `pages/Home.xml` and `pages/About.xml`, so it can be edited like an entry.
- **Statuta Vetera.** The manuscript search reads every file in `tei/`; the list of files is written into the page when the site is built, so it makes no GitHub API calls. The viewer's volumes and their commentary folders are in `_data/statutes_volumes.yml`.

## Repository layout

| Path | What it is |
|---|---|
| `_config.yml` | Jekyll config: theme, folders, the page-scan address, per-folder defaults. |
| `_layouts/default.html` | Site shell: banner, menu, section menu, work-in-progress notice, footer. Pages list the scripts they need in their front matter. |
| `_data/navigation.yml` | The main menu and the second-row menus for each section. |
| `_data/statutes_volumes.yml` | Volumes of the Statutes of the Realm for the viewer. |
| `style.css` | The one stylesheet. Colours and fonts are variables at the top. |
| `index.html`, `about.html` | Home and About. Their text is in `pages/`. |
| `dictionary.html` | A–Z list and search. |
| `entry.html` | Shows one entry. |
| `contribute.html` | Form for one entry: makes, previews and downloads its TEI file; `?id=` opens an existing entry for correction. |
| `import.html` | Bulk import of a Word document. |
| `abbreviations.html`, `lawAbb.html`, `gramAbb.html` | The abbreviation lists (`scripts/abbreviations.js`). |
| `entries/*.xml` | **The dictionary.** One TEI file per entry. See [docs/SCHEMA.md](docs/SCHEMA.md). |
| `pages/*.xml` | Text of the site pages, as TEI. |
| `data/markLaw.json`, `data/markforward.json` | Law codes and manuscript sigla; grammatical abbreviations. Edit these to add a spelling that isn't linked. |
| `scripts/eliebermann.js` | Shared code: file names, linking, building TEI from the form, rendering TEI. |
| `scripts/docx-import.js` | Splits a Word document into entries. See [docs/IMPORT.md](docs/IMPORT.md). |
| `scripts/site-page.js` | Shows the TEI site pages. |
| `StatutaVetera/` | Manuscript search (`index.html`), manuscript page, Statutes of the Realm viewer (`sidebyside.html`), manuscript TEI generator (`tei-gen.html`). |
| `tei/*.xml` | Statuta Vetera manuscript descriptions. |
| `commentaryN/` | Commentary for the viewer, one HTML file per page (`12.html`), in the folder named for its volume in `_data/statutes_volumes.yml`. None yet. |
| `tools/import-docx.js` | Bulk import on your own computer. |
| `tools/build-index.js` | Writes `data/entries.json`. Runs on every deploy. |
| `.github/workflows/static.yml` | Builds and deploys the site on every push to `main`. |
| `docs/` | Entry format, import rules, the latest import report and the stock-take of October 2026. |

## Adding entries

**One entry:** fill in [Add an entry](https://notamitchell.github.io/law/contribute.html), download the file, and upload it to [`entries/`](https://github.com/notamitchell/law/upload/main/entries).

**A Word document of entries:** use [Bulk import](https://notamitchell.github.io/law/import.html) and upload the files from the zip, or run `node tools/import-docx.js` (see [docs/IMPORT.md](docs/IMPORT.md)). Entries already on the site are kept unless you ask to replace them.

**A correction:** *Suggest a correction* at the foot of an entry opens it in the form; download the new file and upload it over the old one. Or edit the XML on GitHub directly.

**A law code or abbreviation that isn't linked:** add its spelling to `data/markLaw.json` or `data/markforward.json` with the same Anchor as its main form. Existing entries keep their links as they were made; re-import or re-save an entry to pick up new ones.

## Running the site locally

Needs Ruby and Bundler (for Jekyll) and Node.js (for the entry list).

```sh
bundle install
node tools/build-index.js
bundle exec jekyll serve --baseurl /law
```

Then open http://localhost:4000/law/.

## Roadmap

1. **Contributions straight to the site.** As in [Common Ground](https://github.com/historicalesque/carlton): the form sends each entry to a Google Apps Script, which saves a copy to a Google Sheet in the team's shared Drive and opens a pull request on this repository. Editors pick *Accept* or *Reject* in the Sheet's Decision column, and the script merges or closes the pull request. Needs a Google account for the Sheet and script, and a GitHub token with write access to this repository. Until then, the form and import download files for an editor to add.
2. **A review page** listing submissions, with a before-and-after comparison for corrections to existing entries.
3. **Fix the notes in `data/markLaw.json`** (they are one row out; see the [stock-take](docs/STOCKTAKE.md#data-problems)). The law code list shows them marked "under review" until then.
4. **Better search:** search inside entries with tolerance for spelling variants (æ/ae, þ/ð), and find every entry that cites a given law code.
5. **Cross-references with ~.** Resolve pointers like *s.* abb~ to the entry they mean.
6. **Validation.** A TEI customisation (ODD) for the entry format, and a check on every push that each entry is valid.
7. **The *Rechts- und Sachglossar*** (volume 2, part 2) as a second dictionary, linked from the *Wörterbuch*.
8. **Statuta Vetera:** real commentary for the viewer, scans for volumes 7–11, and links between manuscripts and the statutes they contain.

## Source

Liebermann, F. (Ed.). (2015). *Die Gesetze der Angelsachsen: Herausgegeben im Auftrage der Savigny-Stiftung* (Cambridge Library Collection - Medieval History). Cambridge: Cambridge University Press. doi:10.1017/CBO9781316225127

Scans of the original edition are on [archive.org](https://archive.org/details/diegesetzederang02liebuoft).
