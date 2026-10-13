# eLiebermann: An Online Dictionary of Pre-Conquest English Law

**Live site:** https://notamitchell.github.io/law/

> ### Looking for the dictionary? You probably want the website, not this page.
>
> This page is the technical documentation for the people who build and maintain the site.
>
> - **Look up a word:** [Dictionary](https://notamitchell.github.io/law/dictionary.html)
> - **Abbreviations:** [Law codes and manuscripts](https://notamitchell.github.io/law/lawAbb.html) · [Grammatical abbreviations](https://notamitchell.github.io/law/gramAbb.html)
> - **Suggest an entry or a change:** [Suggest an entry](https://notamitchell.github.io/law/contribute.html), or *Suggest a change* at the foot of any entry

---

## Contents

- [Overview](#overview)
- [How the site works](#how-the-site-works)
- [Repository layout](#repository-layout)
- [Adding entries](#adding-entries)
- [Running the site locally](#running-the-site-locally)
- [Transcription notes to review](#transcription-notes-to-review)
- [Roadmap](#roadmap)
- [Statuta Vetera (a separate project)](#statuta-vetera-a-separate-project)
- [Source](#source)

---

## Overview

eLiebermann is a digital edition of the *Wörterbuch*, the dictionary in Felix Liebermann's *Die Gesetze der Angelsachsen* (1903–1916), the standard edition of the laws of England before the Norman Conquest. The repository also hosts [Statuta Vetera](#statuta-vetera-a-separate-project), a separate project.

It is a static website hosted on **GitHub Pages** and built with **Jekyll**, using the `jekyll-theme-cayman` theme with a custom layout. It has no server or database of its own:

- **Entries** are TEI XML files in `entries/`, one per headword. The browser fetches them and renders them on the fly. The format is in [docs/SCHEMA.md](docs/SCHEMA.md).
- **New entries and changes** are suggested in the browser with the [Suggest an entry](contribute.html) form, which makes a TEI file for an editor to add to `entries/` on GitHub. Whole Word documents are imported with `tools/import-docx.js` (the browser import page is kept in the code but is not on the site for now). Sending submissions straight to the site is on the [roadmap](#roadmap).

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

 Contributor ──▶ contribute.html (suggest an entry, or ?id= a change to one)
                   │  builds TEI with scripts/eliebermann.js, links law codes and abbreviations
                   ▼
                 TEI file(s) downloaded ──▶ editor uploads to entries/ on GitHub ──▶ site rebuilds
```

- **Entry pages** (`entry.html?id=abbod`) fetch `entries/abbod.xml` and render it with `ELieb.renderTei()`. The `id` can also be a headword (`entry.html?id=æbære`). If there is no file, the page offers to start one.
- **The Dictionary page** reads `data/entries.json`, which `tools/build-index.js` writes on every deploy from the files in `entries/`. If it's missing (for example in a local build where you didn't run the script), the page falls back to a plain list of file names.
- **Abbreviation links.** When an entry is made, `ELieb.linkAbbreviations()` links every law code, manuscript siglum and abbreviation listed in `data/markLaw.json` and `data/markforward.json`, longest match first, and stores the links in the TEI. Law codes are only linked in roman type, since Liebermann's italics are German.
- **Abbreviation popups.** On an entry page, clicking a law code, manuscript siglum or grammatical abbreviation opens a small popup with its German expansion and English translation (and, for a grammatical abbreviation, its note), read by the link's Anchor from `data/markLaw.json` or `data/markforward.json` (`scripts/lawpopup.js`). Hovering previews it on a computer. Ctrl/Cmd-click, or any failure to load the data, still goes to the list. Fix a wrong popup by fixing its row in the data file.
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
| `contribute.html` | *Suggest an entry*: makes, previews and downloads one entry's TEI file. `?id=` suggests a change to an existing entry, with the form filled in from its file. |
| `import.html` | Bulk import of a Word document in the browser. Not on the site for now (`published: false`); see [docs/IMPORT.md](docs/IMPORT.md). |
| `abbreviations.html`, `lawAbb.html`, `gramAbb.html` | The abbreviation lists (`scripts/abbreviations.js`). |
| `entries/*.xml` | **The dictionary.** One TEI file per entry. See [docs/SCHEMA.md](docs/SCHEMA.md). |
| `pages/*.xml` | Text of the site pages, as TEI. |
| `data/markLaw.json`, `data/markforward.json` | Law codes and manuscript sigla; grammatical abbreviations. Edit these to add a spelling that isn't linked. |
| `scripts/eliebermann.js` | Shared code: file names, linking, building TEI from the form, rendering TEI. |
| `scripts/docx-import.js` | Splits a Word document into entries. See [docs/IMPORT.md](docs/IMPORT.md). |
| `scripts/lawpopup.js`                               | The abbreviation popups (law codes, manuscripts, grammatical) on entry pages.                                                                                                                            |
| `scripts/site-page.js` | Shows the TEI site pages. |
| `StatutaVetera/` | Manuscript search (`index.html`), manuscript page, Statutes of the Realm viewer (`sidebyside.html`), manuscript TEI generator (`tei-gen.html`). |
| `tei/*.xml` | Statuta Vetera manuscript descriptions. |
| `oe-laws/*.xml`, `oe-laws/index.json` | The Old English laws database: one TEI file per clause (2,293 of them) and a catalogue of them. Each clause has Liebermann's text(s), his German and an English rendering of it, a modern edition and translations, each labelled with its manuscript. Shown one clause at a time by `law.html`; the letter A entries link to it. See [docs/OE-LAWS.md](docs/OE-LAWS.md). |
| `commentaryN/` | Commentary for the viewer, one HTML file per page (`12.html`), in the folder named for its volume in `_data/statutes_volumes.yml`. None yet. |
| `tools/import-docx.js` | Bulk import on your own computer. |
| `tools/laws-from-database.py` | Makes `oe-laws/` from the full laws database spreadsheet, on your own computer, keeping every clause's file name. See [docs/OE-LAWS.md](docs/OE-LAWS.md#making-the-files-again). |
| `tools/laws-from-xlsx.py`, `tools/law-code-from-xlsx.py` | The earlier scripts (the first layout, and one law code at a time). Not needed now, but `laws-from-database.py` uses their helpers. |
| `tools/link-citations.py` | Links the law code citations in entries (one letter at a time) to clause files in `oe-laws/`. See [docs/OE-LAWS.md](docs/OE-LAWS.md). |
| `tools/build-laws-index.js` | Writes `data/laws.json` (every clause with its keywords and text) for the Laws page. Runs on every deploy. |
| `tools/see-also.py` | Makes each entry's "See also" links from Liebermann's own cross-references (*s. WORD*, *s. d.*). Writes a report of what it could not link, `docs/see-also-report.md`. |
| `tools/build-index.js` | Writes `data/entries.json`. Runs on every deploy. |
| `tools/update-entries.js` | Rewrites the parts of each entry made from Liebermann's text: the numbered meanings and the law code citation list. Run it after adding or changing entries outside the form. |
| `.github/workflows/static.yml` | Builds and deploys the site on every push to `main`. |
| `docs/` | Entry format, import rules, the latest import report, the stock-take of October 2026, and the cross-checks against the team's Word transcriptions (`crosscheck-*.md`). |

## Adding entries

**One entry:** fill in [Suggest an entry](https://notamitchell.github.io/law/contribute.html), download the file, and upload it to [`entries/`](https://github.com/notamitchell/law/upload/main/entries).

**A Word document of entries:** run `node tools/import-docx.js` (see [docs/IMPORT.md](docs/IMPORT.md)). Entries already on the site are kept unless you ask to replace them.

**A change:** *Suggest a change* at the foot of an entry opens the form filled in from that entry; the file it makes has the same name, so uploading it replaces the entry. Or edit the XML on GitHub directly.

**A law code or abbreviation that isn't linked:** add its spelling to `data/markLaw.json` or `data/markforward.json` with the same Anchor as its main form. Existing entries keep their links as they were made; re-import or re-save an entry to pick up new ones.

## Running the site locally

Needs Ruby and Bundler (for Jekyll) and Node.js (for the entry list).

```sh
bundle install
node tools/build-index.js
bundle exec jekyll serve --baseurl /law
```

Then open http://localhost:4000/law/.

## Transcription notes to review

The letters Z to O were transcribed from the page scans, working backwards from Z. These are the quirks and judgement calls recorded on their pull requests ([Z](https://github.com/notamitchell/law/pull/5), [Y](https://github.com/notamitchell/law/pull/7), [W](https://github.com/notamitchell/law/pull/8), [V](https://github.com/notamitchell/law/pull/9), [U](https://github.com/notamitchell/law/pull/10), [Þ](https://github.com/notamitchell/law/pull/12), [T](https://github.com/notamitchell/law/pull/14), [S](https://github.com/notamitchell/law/pull/17), [R](https://github.com/notamitchell/law/pull/19), [Q](https://github.com/notamitchell/law/pull/21), [P](https://github.com/notamitchell/law/pull/24), [O](https://github.com/notamitchell/law/pull/26)). Tick each one once someone has checked it against the print and agrees with it, or change the entries if not.

**Source and status**

- [ ] Z–O were transcribed from the page images, not archive.org's OCR. Every entry says "Transcribed by Claude from the page scan; not yet checked against the print." (all letters)
- [ ] Only spot checks have been done so far, and all matched the scan: wis–wise (p. 245), wud[u] (p. 250), the end of Verbum to vers (p. 233), utalædan to [utaslean] (p. 231). (W, V, U)
- [ ] The whole *Wörterbuch*, A to Z (pp. 1–253), has been cross-checked against the team's Word transcriptions: see [A – boc](docs/crosscheck-A-boc.md), [bocere – collaboratio](docs/crosscheck-bocere-collaboratio.md), [collarium – d](docs/crosscheck-collarium-d.md), [d – dryhten](docs/crosscheck-d-dryhten.md), [dryhtenbeag – fadian](docs/crosscheck-dryhtenbeag-fadian.md), [façe – forisfactum](docs/crosscheck-faece-forisfactum.md), [forisfactura – geargerihta](docs/crosscheck-forisfactura-geargerihta.md), [gearian – gerefa](docs/crosscheck-gearian-gerefa.md), [gerefscipe – habban](docs/crosscheck-gerefscipe-habban.md), [habban – hume](docs/crosscheck-habban-hume.md), [hund – iustitia](docs/crosscheck-hund-iustitia.md), [iustitiabilis – mægen](docs/crosscheck-iustitiabilis-maegen.md), [mægenþrymmas – minutus](docs/crosscheck-maegenthrymmas-minutus.md), [mirc – Northamtunescire](docs/crosscheck-mirc-northamtunescire.md), [norðan – orf](docs/crosscheck-nordan-orf.md), [orfenins – propriatio](docs/crosscheck-orfenins-propriatio.md), [prosecutio – sacu](docs/crosscheck-prosecutio-sacu.md), [sadelian – singan](docs/crosscheck-sadelian-singan.md), [Singular – tǣcan](docs/crosscheck-singular-taecan.md), [tǣcing – þe](docs/crosscheck-taecing-the.md), [þǣra – understandan](docs/crosscheck-thaera-understandan.md), [underþæncan – wedd](docs/crosscheck-underthaencan-wedd.md), [weddbryce – wiðertihtlan](docs/crosscheck-weddbryce-widertihtlan.md) and [wiðerwordian – Zahlwort](docs/crosscheck-widerwordian-zahlwort.md) for what was fixed. Readings still to check in the book are collected in [To check against the print](docs/to-check-against-print.md). (all letters)
- [ ] An entry that runs over a page keeps a page marker where the page turns, e.g. ymbrenfæsten (p. 253) and vel (p. 233). The very long entry on, which runs from p. 162 to p. 165, is one entry. (Y, W, V, O)

**Language labels**

- [ ] z- carries the double marker LF, but w is marked FL. Decide on one order. (Z, W)
- [ ] A superscript F or L inside an entry is kept as a language marker, not linked as a manuscript siglum, e.g. the F before *siste* in Zahlwort. (Z, Y)
- [ ] Liebermann's German articles are tagged as grammatical terms: Zahlwort, Wortbildung, Wortschatz variirt, both Wortstellung, Verallgemeinernd, Verbum, Vocalverdoppelung, Umlaut, Unpersönliche and Urkundenstil. (Z, W, V, U)
- [ ] German articles printed twice (Personalpronomen, Possessivprn., Praeposition) are stored as two entries each, the second being the Latin or French one with a `-2` file name. (P)
- [ ] II) un has no F of its own and is tagged French, like I) un. (U)

**Homographs and file names**

- [ ] Homographs printed I), II) … are separate entries with the numeral kept in the text: yfel and yfel-2, and þa, þæt, þe, þon, þy in Þ, and I) sio / II) sio(n), I) set / II) set, scyld- and seo in S, and rad I–V, r[i]san, ryman and riht I/II in R, and the French que I–III in Q. Numbered senses inside one entry stay together, as in the long qui and quod, and so do numbered people under one name (Radulfus, Ricardus, Rodbertus). (Y, Þ, S, R, Q)
- [ ] Under Petrus, the numbered people II) and III) are separate entries, unlike Radulfus, Ricardus and Rodbertus in R, which keep theirs together. Pick one rule. (R, P)
- [ ] The two utlaga entries have no I)/II) numerals in print and are stored as utlaga and utlaga-2. (U)
- [ ] The þæt abbreviation ꝥ now gives the file name "thaet", as þ gives "th". Before that change, the headword ꝥ gave an empty file name. (Þ)
- [ ] Headwords printed under both T and Þ, such as T[h]eophania (p. 210 and p. 220), are kept as two entries, the T one taking the next free file name (T-h-eophania-2). (T)
- [ ] A T headword whose file name is already taken gets the next free one, e.g. th-2 to th-4, so nothing already on the site is overwritten. Check whether these should be merged with the earlier entries or renamed. (T)

**Headwords**

- [ ] yfelwyrcendo is the headword, with "wyrto" left in the entry text. (Y)
- [ ] Some headwords are printed after a plain word (openne **wiðercwide**, se **wodfreca**). The entry text starts with that word, as in the book. (W)
- [ ] "-unga" stays inside the -ung entry, where it follows a bar. (U)
- [ ] Wynn is written ƿ only in the w entry, where Liebermann prints the letter form, and in p 1), where the sign after "durch Ähnlichkeit mit" is read as wynn because the sense requires it. Wynn also appears in the manuscript forms sƿic (*spic*), sƿræt (*spræc*) and tƿuelfhindus (*twelfhynde*), in ƿác (*wac*) and ƿeach (*Wealh*), words that Q leaves untranslated or misreads, and in *y* 12) a) (y miswritten for wynn), all of which the scan transcription had misread as thorn; the team transcription has wynn. (W, P, S)

**Printed text: kept or corrected**

- [ ] Letters broken in the type were read as the intended letter: "mögcn" → mögen, "seincs" → seines, "1,.7" → 1,7 (U); "aufhebend" and "Orthographie" (Þ); "Untergebenen" and "doppeltes" (T); "Streitigkeiten" and "einleitend" (S); "eigenem" and "retient" (R); "ceapnnge" → ceapunge in orceapunga, assuming the "nn" is broken type (O). Checked against the print: the "!" after sacu in -ch- is an ink mark and is left out, and "dém" in chose is a printing error for dem (C).
- [ ] Likely misprints in the book are kept as printed: "derehdner" (voleir) and "-rseunessa" (v), "forhttundan" under Particip, "(þingc)" in oðer and "V G G 2" in oððon, and "As Alm 1.2" in bisceop, surely for 1,2. (V, P, O, B)
- [ ] The gap printed "hundfeo:::" in þusend is kept as printed. (Þ)
- [ ] In opprimere, the small superscript in "Rb. S. 537^73^" is read as 73 but could be another number. (O)
- [ ] Literal asterisks in references are kept, e.g. *S.* 375*. (W)
- [ ] "VIIa Atr" is written closed up, to match the law-code list. (W)

**Letter boundaries**

- [ ] Þ starts halfway down column 2 of p. 216; the T entries above it belong to T. The team's transcription agrees (*tæcing - þe.docx*: *tyrian* is the last T entry and *þ* the first Þ entry, both on p. 216). (Þ)
- [ ] The dictionary list has a section Æ for headwords that begin with æ, after A, as in other Old English dictionaries. This was added to the site's list on request. Check where the printed Wörterbuch files them (the words that begin with æ were listed within A before). (Æ)
- [ ] R starts in the lower part of column 1 on p. 180, not 194 as first noted, and ends at the S heading at the top of column 3 on p. 187. Q runs from p. 179 to p. 180, as transcribed, P from the top of p. 170 to the Q heading on p. 179, and O from p. 159 to p. 169. K and L were both noted as starting on 128, and both are: the team's transcription (*iustitiabilis - mægen.docx*) has the few K entries and the start of L on p. 128. (S, R, Q, P, O)

## Roadmap

1. **Contributions straight to the site.** As in [Common Ground](https://github.com/historicalesque/carlton): the form sends each entry to a Google Apps Script, which saves a copy to a Google Sheet in the team's shared Drive and opens a pull request on this repository. Editors pick *Accept* or *Reject* in the Sheet's Decision column, and the script merges or closes the pull request. Needs a Google account for the Sheet and script, and a GitHub token with write access to this repository. Until then, the form and import download files for an editor to add.
2. **A review page** listing submissions, with a before-and-after comparison for corrections to existing entries.
3. **Check the notes in `data/markLaw.json`.** They were one row out and were realigned in October 2026 from the corrected glossary (see the [stock-take](docs/STOCKTAKE.md#data-problems)). The law code list keeps its "Under construction" notice until they have been checked against Liebermann.
4. **Better search:** search inside entries with tolerance for spelling variants (æ/ae, þ/ð), and find every entry that cites a given law code.
5. **Cross-references.** *See also* links are made from Liebermann's *s.* and *s. d.* by `tools/see-also.py`. Since October 2026 it also fills in a ~ from the headword (*s.* anf~ under [-feald] is anfeald), links a prefix such as *s.* heah- to its word, reads Liebermann's bracketed headwords (g[e]noh), picks between entries that share a headword by a following I or II, by language or by Liebermann's F, and otherwise links them all, and tries the usual spelling differences (ceapman / ceapmon). Links found wrong on checking go in its `SKIP` list. See `docs/see-also-report.md` for what it linked by a guess (to check) and what is left: mostly words with no entry (often German grammatical terms or name stems like Ælf-). Still to do: *s. o.*, *s. u.*, *s. z.*, *s. n.*; and *S.* before Maria, Paulus etc. is marked as *siehe* but means *Sanctus*.
6. **Validation.** A TEI customisation (ODD) for the entry format, and a check on every push that each entry is valid.
7. **The *Rechts- und Sachglossar*** (volume 2, part 2) as a second dictionary, linked from the *Wörterbuch*.
8. **The Old English laws database** (`oe-laws/`, 2,293 TEI files made from the laws spreadsheet; see [docs/OE-LAWS.md](docs/OE-LAWS.md)). It has a Laws tab (search and one page per clause), and the dictionary entries for the letter A link to it. To do:
    - Link the citations in the entries for the other letters to their clauses (`tools/link-citations.py --letter B`, and so on), through each file's `citationKey`.
    - Find out why citations to *Ger*, *Hl*, *Abt*, *Af* and *Wi* so often find no clause.
    - Open questions, to answer when there is time:
        - [ ] Six law codes were matched to the law code list by judgement: *Becw*, *Mirc.*, *Nor. Cyricgrið*, *Norðleod.*, *Ord*, *Rom.* Are they right?
        - [ ] Some codes are not on the law code list, so their clauses are not linked: *Cn 1018*, the *Rubrics*, *VI Atr (Latin Paraphrase)*, *Wer*, *Geþyn.*, *Prom. Reg.*, *Rubric List*, *Ymb Æwbricas*. Should they be added to it?
        - [ ] The spreadsheet does not say which language each text is in, and some is Latin, so the texts are marked `xml:lang="und"`. How should Old English and Latin be told apart?
9. **"Norðleod 2lq" under *æðeling*** (p. 8): "Ersetzt durch eorl Norðleod 2lq". The print reads 2lq, and so does the site for now. It is probably a misprint, but not obviously for 21q, since Norðleod has only twelve clauses. It may stand for clause 2 and a manuscript siglum (such as Ld). Check Liebermann's text of Norðleod 2 in volume 1 to see which manuscript has *eorl* for *æðeling*, then correct the entry.
10. **Links to Bosworth-Toller** (and later other Old English dictionaries). The dictionary's own addresses are numbers (`bosworthtoller.com/4773`), so they cannot be worked out from a headword; they have to be matched from a list. Two separate tasks:
    - [ ] **Get a headword list.** There is a data dump, [Bosworth-Toller's Anglo-Saxon Dictionary online, version 0.1](https://lindat.mff.cuni.cz/repository/items/da2f3c19-f5a9-48d2-bb8f-eb84a415f954) (LINDAT, April 2021, 62,936 entries). Its file `bosworth_entries_export.csv` has the columns `id`, `headword` and `body`, and the `id` is the number in the website address. Check the licence when downloading (the site says its data is "free for any purpose" and asks academic users to cite the dictionary). The dump is from 2021, so also **ask Bosworth-Toller for a newer copy** through the contact form on their site, which offers database dumps to researchers.
    - [ ] **Make the links.** With the list, try the letter A first: link a headword only where exactly one Bosworth-Toller entry has that spelling; where several share it, use Liebermann's definition to suggest the right one but leave those for an editor to confirm; report what has no match (spellings differ, *æ*/*þ*/*ð*). Entries already have a place for these links (`<xr type="bosworthToller">`, shown under "Other dictionaries"). Nothing is changed in the entries until the report has been looked at.
    - The Dictionary of Old English has the same problem (its addresses are codes such as `?E03539`) and covers only part of the alphabet, so it needs its own list.

## Statuta Vetera (a separate project)

*Statuta Vetera* is a separate project: descriptions of manuscripts of the *Statuta Vetera*, the collections of early English statutes copied for lawyers' use, and a viewer for reading the *Statutes of the Realm* beside commentary. It is hosted here for now, but isn't in the eLiebermann menu or home page. It may move to its own repository later.

- [Manuscripts](https://notamitchell.github.io/law/StatutaVetera/): search and filter the manuscript descriptions
- [Statutes of the Realm viewer](https://notamitchell.github.io/law/StatutaVetera/sidebyside.html)
- [Manuscript description generator](https://notamitchell.github.io/law/StatutaVetera/tei-gen.html): turns a catalogue description into a TEI file for `tei/`

Its files are `StatutaVetera/`, `tei/` (manuscript descriptions, format in [docs/SCHEMA.md](docs/SCHEMA.md#manuscripts-statuta-vetera)) and `_data/statutes_volumes.yml` (the viewer's volumes), with its own menu under `statuta` in `_data/navigation.yml`. To move it out, take those files, the `StatutaVetera` defaults in `_config.yml`, and a copy of `_layouts/default.html` and `style.css`.

Still to do: real commentary for the viewer, scans for volumes 7–11, and links between manuscripts and the statutes they contain.

## Source

Liebermann, F. (Ed.). (2015). *Die Gesetze der Angelsachsen: Herausgegeben im Auftrage der Savigny-Stiftung* (Cambridge Library Collection - Medieval History). Cambridge: Cambridge University Press. doi:10.1017/CBO9781316225127

Scans of the original edition are on [archive.org](https://archive.org/details/diegesetzederang02liebuoft).
