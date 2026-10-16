# The Old English laws database (`oe-laws/`)

`oe-laws/` holds the text of the laws themselves, one clause at a time: **each clause row of the laws database spreadsheet is one TEI XML file** (2,293 files), plus `oe-laws/index.json`, a catalogue listing every file. The Laws tab (`laws.html`) searches them and `law.html` shows one clause.

Since October 2026 the files are made from the full, checked spreadsheet *OE_Laws_Database - Updated by Claude.xlsx* (columns A–AO) with `tools/laws-from-database.py`. Every law code now has the layout that Æthelberht had first, with more texts. The one exception is **Cn 1018**, which is waiting for a decision and is left as it was (see "Law codes that need a decision").

## What is in a file

Take `oe-laws/Had_10.xml`, the clause *Had 10*. Its header says where the clause comes from; its body holds the texts.

| In the spreadsheet | In the file | On the clause page |
| --- | --- | --- |
| **B** code, **C** clause | the title; `<idno type="lawCode">`, `<idno type="clause">`, `<idno type="citationKey">`; `<idno type="lawCodeAnchor">` when the code is on the [law code list](../lawAbb.html) | the heading |
| **D** name of the code, **E** king and reign, **F** date and place | `<bibl type="legalText">`, `<note type="reign">`, `<note type="promulgation">` | under the heading |
| **G** Liebermann's manuscripts (bold = chosen); **AJ–AO** the sigla and full names of the manuscripts each text comes from | `<listWit>`: one `<witness>` each, with the siglum in `<abbr>` and the full name in `<note type="manuscript">` | *Manuscripts*; each text is labelled *MS H* etc., with the full name on hover |
| **K** Liebermann's text (MS in **AJ**, page in **I**, number in **J**) | `<ab type="liebermannText" source="#liebermann" corresp="#wit-h">` | left column, labelled **Liebermann** · MS … · Gesetze I, p. … |
| **N** his second MS (siglum **AE**), **AF** his third (siglum **AG**), **O** the Quadripartitus Latin | more `<ab type="liebermannText">`, each with its own `corresp` | left column, one box each |
| **L** Liebermann's German translation | `<ab type="translation" xml:lang="de" source="#liebermann">` | right column, first: *German translation* |
| **M** Claude's English of the German | `<ab type="translation" xml:lang="en" source="#claude" ana="#fromGerman">` | right column, second: *English of Liebermann's German* |
| **P**–**S**, **V** the modern edition (reference, editor, MS, number, page) and **T** its text | `<bibl xml:id="robertson">` etc. in `<listBibl type="sources">`; `<ab type="editionText">` | left column, labelled with the editor's surname · MS … · § … · p. … |
| **U** the editor's translation | `<ab type="translation" source="#robertson">` | right column, after the German and its English |
| **W** second translation (translator and book in **X**, page in **Y**) | `<ab type="translation" source="#attenborough">` | right column |
| **AA** translation of the manuscript in K | `<ab type="translation" corresp="#wit-…">` | right column, *of MS …* |
| **AB**, **AC**, **AD** offence, people, places | `<keywords>` | *Keywords* |
| **AH** source of the passage | `<note type="passageSource">` | under the texts |
| **AI** notes | the scholarly notes in `<note type="editorial">`; the record of checking in `<revisionDesc>` (`<change type="checked">`) | *Notes* under the texts; the checking at the foot of the page |
| **AP–AT** Whitelock, *English Historical Documents* I (1979): translation, edition, manuscript, page, footnotes | `<ab type="translation" source="#whitelock">`; footnotes in `<note type="translator" source="#whitelock">` | after the other translations; her footnotes under her translation |
| **AU–AZ** Rabin, *Old English Legal Writings: Wulfstan* (DOML 66, 2020): text, translation, edition and base manuscript, pages, textual notes, notes to the translation | `<ab type="editionText" source="#rabin-doml">` and `<ab type="translation" source="#rabin-doml">`; `<note type="textual">` and `<note type="translator">` with `source="#rabin-doml"` | his text after the other editors'; his textual notes (the other manuscripts' readings) under his text, his notes under his translation |

**How a clause page is laid out.** The left column is headed *Old English text* when the clause has any Old English, or *Latin text* when it survives only in Latin. Under it come Liebermann's texts in the order of his columns (his leftmost, main text first), then the modern editors' texts. Texts from the Quadripartitus (MS Q) go under their own heading, *Quadripartitus*, below, unless the clause survives only in Latin. The right column, *Translations*, has Liebermann's German first, then Claude's English of the German, then the editors' and other translations. *Manuscripts* lists every manuscript with its full name; each text above already says which manuscript it comes from.

- **Language.** Each text is marked Old English (`ang`), Latin (`la`) or German (`de`). The script decides between Old English and Latin from the words (þ, ð, æ and ⁊ mean Old English; *et*, *est*, *quod* and Latin endings mean Latin). It looked right in every case I checked.
- **Codes with no modern editor** (Northu, Had, Duns, Wer and the other short texts): in the old spreadsheet, column T held Liebermann's text of another manuscript, not a modern edition. It is shown as Liebermann's, labelled with its manuscript, and left out where it is the same manuscript as K. Their translators are not in the spreadsheet any more (they were in the sub-header rows), so the script names them (`TRANSLATORS` in the script): Whitelock (*English Historical Documents* I) for Northu, Wif, Geþyncðo, Norðleoda, Mirce, Að and Had; Whitelock, Brett and Brooke (*Councils and Synods*) for Episc; Wormald (*The Making of English Law*) for Wer and Becwæð; Rabin for the translations of H in Geþyncðo, Norðleoda, Mirce, Að and Had. The old sheet names no translator for Duns, Forf, Pax, Wal, Swer, Romscot, Iudex, Iud Dei VIII and VI Atr Lat; their translations say *Translator not recorded*.
- **Grið and Nor Grið.** Their columns T and U are Rabin's edition, checked against it in October 2026. Their old sub-header rows name Rabin's *Old English Legal Writings: Wulfstan* (2020), which has the Old English text; the spreadsheet's column P names his 2015 book of translations. The files use the 2020 book (`EDITOR_OVERRIDE` in the script).
- **William I and Henry I** (Wl Lond, Wl lad, Wl ep, Wl art, Wl art retr, Leis Wl, CHn cor, Hn mon, Hn com, Hn Lond) come from Robertson (1925), pp. 230–293, added in October 2026: text in T, translation in U, page in V, manuscript in R/AN/AO. Liebermann's own text (K–M) is not yet in these rows. Leis Wl is in Anglo-Norman French (`xml:lang="xno"`, `FRENCH_CODES` in the script), except 25, 35.1 and 40, which Robertson supplies from the Latin version (MS L). They are listed under *William I* and *Henry I* on the Laws page. The spreadsheet spells three codes differently from the law code list, so `ASSUMED_ANCHORS` in `tools/laws-from-xlsx.py` maps them: Wl lad → WiLad, Hn com → HnComm, and Prom. Reg. → SacrCor (the dictionary cites the Promissio regis as *Sacr cor*).
- **Notes.** Remarks about the spreadsheet itself ("a line break inside K was removed", "text in column T") are tidied away (`NOTE_TIDY` in the script). The record of checking ("K: checked against Gesetze I p. 3", "T: corrected against Robertson p. 200 (…)") is not shown as a note: it becomes a line at the foot of the clause page, such as *Liebermann's text checked against Die Gesetze der Angelsachsen I, p. 3*. What a cell said before a correction is not on the website; it is in the spreadsheet.
- **Italic** in the spreadsheet (Liebermann's and the editors' expansions of abbreviations, italic words in translations) is kept as `<hi rend="italic">`; italic in a book reference is its `<title>`.

## Liebermann's cross-references ("Vgl.")

In the outer margin beside his German translation, Liebermann prints short notes comparing a clause with other laws (*Vgl. I Em. 3; II 4*, *ebd. 4, 1*). All 1,348 such notes in *Gesetze* I pp. 2–528 were transcribed from the page images in October 2026 (none occur before I Edward). In the spreadsheet:

- **BA** holds the notes exactly as printed (one note per entry, separated by " | ");
- **BB** the references written out in full ("ebd." and bare numbers expanded: *I Em 3; II Em 4*);
- **BC** the page in *Gesetze* I, and anything still to check. Notes cut off in the gutter of the archive.org scan say **TO COMPLETE**; the sheet *Vgl to complete* lists them, and the sheet *Liebermann Vgl* lists every note, including those beside texts that are not in the database.

`tools/laws-from-database.py` (`vgl_links`) resolves each reference in BB to a clause file and writes `<note type="comparison">` (the references, linked with `<ref target="clause:ID">`), `<note type="comparisonPrinted">` (BA) and, where needed, `<note type="comparisonIncomplete">`. It also collects the reverse links: a clause that other clauses compare with it gets `<note type="comparedBy">`. The clause page shows both, as *Compare (Liebermann, Gesetze I p. …)* and *Liebermann compares this clause at*.

## One page per Liebermann clause (October 2026)

Where later editors divide one of Liebermann's clauses, the spreadsheet gives each part its own row, with a letter in square brackets (Abt 1[a] … 1[g]): that is how it records which words of each text go with which words of each translation. The website shows the clause whole, as Liebermann prints it. `tools/merge-parts.py` joins the part files into one file for the clause (`Abt_1.xml`):

- each text keeps its parts as `<seg type="part" corresp="#part-b">…</seg>` (`corresp`: the spreadsheet row's letter). Only an editor who divides the clause gets numbers, and only in that editor's own edited text: there the parts carry the editor's numbers (`<seg type="part" n="22.1" …>`, shown in a small box) and the text as a whole the range (`<ab type="editionText" n="22–22.2">`, shown as “§ 22–22.2” above it). No other text is marked. A translation that gives the same words for two parts is shown once, for both (`corresp="#part-f #part-g"`);
- `<note type="concordance">` gives the editions' numbers for the parts (Oliver 22, 22.1, 22.2), shown under the heading;
- notes, keywords, sources and manuscripts of the parts are gathered; a note on one part has `target="#part-a"` and is shown with its letter;
- `oe-laws/index.json` has one entry for the clause, with `"parts"`: the part files' ids and clause numbers. A link to a part (`law.html?id=Abt_1-c`) opens the clause with that part highlighted. Links to a part that cite the whole clause ("Abt 1", without a letter), from the dictionary and from the cross-references, are pointed at the clause.

`laws-from-database.py` reads `"parts"` back, so a rebuild makes the part files under the same names. The order is therefore: `laws-from-database.py`, then `liebermann-notes.py`, then `merge-parts.py`, then `build-laws-index.js` and `link-citations.py`. So far only Æthelberht is joined (`merge-parts.py --code Abt`); without `--code` it joins every code.

## Liebermann's notes (Æthelberht, October 2026)

Liebermann's edition has two sets of notes that the plain texts leave out. Both are now in the clause files for **Æthelberht** (Abt), as a pilot; the other codes can follow in the same way.

- **Textual notes on his Old English (or Latin) text**: the footnotes at the foot of the column in *Gesetze* I (manuscript readings, erasures, other inks, editors' emendations). Numbered afresh on each page; `*` marks an editor's emendation. For Abt: *Gesetze* I pp. 3–8, 43 notes.
- **Erklärungen on his German translation**: the numbers in the German refer to notes printed separately in *Gesetze* III (1916), numbered afresh in each of Liebermann's clauses (all of Abt 1 is one clause there, though the database divides it into 1[a]–1[g]). For Abt: *Gesetze* III pp. 3–17, 288 notes, plus Liebermann's own footnote on the German at Abt Inscr (vol. I p. 3).

Each note is given in Liebermann's German exactly as printed (his spelling, italics, letter-spacing) and in a semi-literal English translation by Claude. They were transcribed from the page images (not the OCR), and each Erklärung was then proofread against the page in a second, independent pass.

**Where the data lives.** In the workbook *Liebermann_notes_Abt.xlsx* (kept with the main spreadsheet, not in this repository):

- sheet *Texts with note markers*: columns K and L of the main spreadsheet with the note numbers in curly brackets after their word: `{4}`, `{*}`, `{+1}` (a number Liebermann forgot to print and in vol. III says where to put), `{2/4}` (note 2, misprinted 4 in vol. I and corrected by Liebermann in vol. III). Take out the brackets and you have K and L exactly; the script checks this.
- sheet *Liebermann notes*: one line per note per clause row: where printed, number, German, English, remarks, readings to check.

Later these can become columns of the main spreadsheet (K and L with markers) and a sheet of it (the notes); the script would then read them from there.

**In the clause file**, the note numbers are empty pointers inside the existing texts, so the plain text is unchanged and there is no second copy of it to keep in step:

```xml
<ab type="liebermannText" …>Godes<ptr type="liebermannNote" n="4" target="#Abt_1-a.lnote.oe.4"/> feoh …</ab>
<ab type="translation" xml:lang="de" source="#liebermann">Gottes<ptr type="liebermannNote" n="1" target="#Abt_1-a.lnote.de.1"/> und …</ab>
```

`rend="supplied"` marks a number supplied from Liebermann's correction, `rend="printed-as-4"` one he corrected. The notes follow at the end of the clause, `<note type="liebermannNote">` with `subtype="textual"` (vol. I, on the Old English), `"erklaerung"` (vol. III) or `"translationFootnote"` (vol. I, on the German), each with the volume and page in `<bibl>`, the German in `<seg type="original" xml:lang="de">` and the English in `<seg type="translation" xml:lang="en" source="#claude">`. Italic is `<hi rend="italic">`, letter-spacing `<hi rend="spaced">`, small capitals `<hi rend="smallcaps">`, and a paragraph break inside a note `<lb type="paragraph"/>`. Notes with no number in the text (Abt 54.3, 64.1, whose notes are on the whole clause) have `rend="wholeClause"`.

**On the clause page**, Liebermann's text and his German translation each get a small button, *Show Liebermann's notes*. It shows the note numbers in the text as grey superscripts (each a link to its note) and lists the notes under the text: German, English, and where printed. The Erklärungen carry a line saying that much of them is superseded. The reader's choice is remembered from clause to clause (in their own browser).

**Making them again.** `tools/laws-from-database.py` rebuilds the clause files without the notes, so run the notes script after it:

```
python3 tools/liebermann-notes.py "path/to/Liebermann_notes_Abt.xlsx" --dry-run
python3 tools/liebermann-notes.py "path/to/Liebermann_notes_Abt.xlsx"
```

It needs `pip install openpyxl lxml`. It removes any notes it added before, so it can be run any number of times, and it leaves a file alone (and says so) if the text in the workbook no longer matches the file.

## Other scholars' cross-references

Places where other scholars say that one clause repeats, revises, derives from, or should be compared with another were collected in October 2026 from Whitelock's footnotes (*EHD* I), Rabin's notes to his translations (DOML 66), Wormald's *Making of English Law* I (including his tables of sources) and *Papers Preparatory*, Jurasinski and Oliver's *Laws of Alfred*, and Kennedy's edition of Cnut's code of 1018 (*ASE* 11, 1983: his table of the code's sources in VI Æthelred and its reuse in I–II Cnut, and his discussion). Only links between two law clauses were taken, not lists of clauses on the same topic. Clause numbers are Liebermann's: Jurasinski and Oliver's own numbering of Alfred, Ine and Wihtred was converted using the Liebermann numbers they print in brackets.

The spreadsheet's sheet **Cross-references** has one line per link (scholar, work, page, clause, linked clause, the relation in the scholar's terms, the scholar's words, a remark), and column **BD** of Sheet1 has the same in short. `read_cross_references` and `xr_links` in `tools/laws-from-database.py` read that sheet and write, on the clause a link starts from, `<note type="comparison" source="#wormald-mel" n="PAGE"><label>relation</label> <ref target="clause:ID">…</ref> <quote>…</quote></note>`, and on the linked clause `<note type="comparedBy" source="#…" n="PAGE">`. The scholar's work is added to the file's sources. The clause page lists them under the scholar's name: *Compare (Wormald, MEL): …* and *Compared with this clause (Wormald, MEL): …*.

## File names and identifiers

A file is named after its law code and clause number, joined by an underscore: `Abt_1-a.xml`, `Ine_23-2.xml`. The code part is the code's **Anchor** on the law code list where there is one (so `IICn` for *II Cn*), otherwise the abbreviation with plain letters. In names, þ is *th*, æ is *ae* and ð is *d*, as for dictionary entries. The same text is the file's `xml:id`.

- A clause row with no number gets `part-001`, `part-002`… in order within its code (for example `Cn-1018_part-001.xml`).
- A row with the same code and clause number as an earlier row gets `_dup2` on the end (`IVAs_6-1_dup2.xml`). There are 6 of these.
- A row that covers several numbers, such as *3, 3.1, 3.2, 3.3, 3.4*, is named `Rect_3-to-3-4.xml`, and every number in it is a citation key.

## Linking to dictionary entries

Each file has one or more `<idno type="citationKey">`, in the form `Ine 23.2`: the law code's Anchor, a space, and the clause number with a comma read as a full stop (Liebermann prints 23,2) and with brackets and capitals ignored. The same keys are listed in `index.json` as `citationKeys`. A dictionary citation such as `<ref target="law:Ine">Ine 23,2</ref>` can be turned into the same key, and so matched to its clause file.

When this was made, **83%** of the dictionary's citations with a clause number found their clause file this way, and **96%** did once a manuscript letter after the number (as in *9 Q* or *1 Ld*) was ignored. The letters have since been taken out of the citation lists. The citations that do not match are most often to *Ger*, *Hl*, *Abt*, *Af* and *Wi*. I have not looked into why yet; differences between Liebermann's numbering and the spreadsheet's are the likeliest cause.

Codes the spreadsheet has no clauses for, such as the manuscript sigla *G* and *Q*, have no files; entries citing them have nothing to link to.

### The Laws tab

`laws.html` opens with the **list of law codes**, grouped under the king who issued them (codes with no king are under *Other laws and legal texts*). It reads `oe-laws/codes.json`, which `tools/laws-from-database.py` writes: one line per law code, with its abbreviation, its full name (column D), the king and reign (E), the date (F of its first row), the number of clauses, its manuscripts and its editors and translators. The group names are in `GROUPS` in the script.

Each law code has its own page, `lawcode.html?code=Abt`, listing every clause with the opening of Liebermann's text and the first English translation, a box to find a clause or a word in that code, links to the previous and next codes, and a button that opens the first clause with the whole code shown (`law.html?id=…&all=1`). The law code in the heading of a clause page links back to that list.

Searching works as before: by law code and clause (*Ine 23*, *abt 1a*), by law code (the menu, grouped by king, shows each code's abbreviation and full name), by keyword (an offence, a kind of person or a place; the box suggests the ones that exist), and, with the box ticked, in the texts and translations too (þ and th, æ and ae are treated alike). The clauses come from `data/laws.json`, which `tools/build-laws-index.js` writes from `oe-laws/` on every deploy, so a clause added to `oe-laws/` appears by itself. Clicking a keyword on a result or on a clause page searches for it. `law.html` is the page for one clause.

### Manuscript letters are not in the citation lists

Liebermann sometimes follows a passage with the letter of a manuscript or version, such as *Af 41 B* or *Ine 9 Q* (Quadripartitus). The list of law code citations at the foot of an entry names the passage only (*Af 41*, *Ine 9*), and a passage cited in several manuscripts is listed once. Liebermann's own text, above, is unchanged and keeps the letters. The rule is in `scripts/eliebermann.js` (`SIGLA`, in `extractCitations`), so the *Suggest an entry* form and `tools/update-entries.js` both follow it.

### The letter A trial

`tools/link-citations.py --letter A` changes the law code citations at the foot of the entries filed under A. The entries that begin with æ are a letter of their own, Æ, so they need `--letter Æ` (the first trial was run when they were part of A). A citation that finds its clause changes from `target="law:Ine"` to `target="clause:Ine_23-2"`, and the entry gets a `clause` prefix definition. The site turns that into a link to `law.html?id=Ine_23-2`, which shows the clause, its manuscripts and keywords, the neighbouring clauses, and a button to read the whole law. The citation text is unchanged. Citations that find nothing are left as they were. The tool is safe to run again, and `--dry-run` only reports. Its latest results are in [oe-laws-link-report.md](oe-laws-link-report.md).

The citation lists no longer carry manuscript letters (see the next paragraph). A citation is matched to a clause in two ways: exactly; or, where Liebermann cites *Abt 1* but the spreadsheet has *1[a]* and *1[b]*, by going to the first part.

Results for A and Æ together: 82% of all citations are linked, and 97% of those that name a clause in a code the database has. The rest are mostly citations to codes with no clause files (see below). Run it with another letter to link other entries.

**Alfred's Introduction.** The catalogue's `citationKeys` for these clauses (*Af El. 1*) are wrong: they give the keys *Af el* and *Af 1*, so *Af 1* would also point at the Introduction. `link-citations.py` works round this by using the clause as printed; `laws-from-xlsx.py` should be fixed to give *Af el.1*.

## Making the files again

Correct the spreadsheet, then, from the repository folder (you need Python 3 and `pip install openpyxl`):

```
python3 tools/laws-from-database.py "path/to/OE_Laws_Database - Updated by Claude.xlsx" --dry-run   # report only
python3 tools/laws-from-database.py "path/to/OE_Laws_Database - Updated by Claude.xlsx"
python3 tools/laws-from-database.py "path/to/…xlsx" --code Ine                                      # one law code only
```

**Then run `tools/liebermann-notes.py`** (see "Liebermann's notes" above), or Liebermann's notes will be missing from the rebuilt files.

The script finds the columns by their headings in row 1, so columns can be moved but not renamed. It reads the sheet called *Sheet1* (the *Read me* and *corrections* sheets are ignored).

**File names stay the same.** Each row is matched to the file its clause had before, by law code and clause number, so dictionary entries that link to a clause keep working. Where a clause number was changed in the spreadsheet (for example *I Atr 1.10*, which the old spreadsheet had as a second *1.1*), the row keeps the old file (`IAtr_1-1_dup2.xml`), and the dry run lists every such case. A clause that is new gets a new file; a file whose clause no longer has a row is removed. In October 2026 one file was removed: `Rubrics-INE_part-001`, which was a sub-header row, not a clause. All 1,069 clause links in the dictionary still find their files.

**Rabin's texts follow Liebermann's clauses.** Rabin prints some texts as continuous prose (Cnut's Proclamation of 1020, the Promissio regis, X Atr) and elsewhere divides less finely than Liebermann (II Cn 30.3, 30.3a, 30.3b…). In October 2026 his text in every code was divided again at Liebermann's clause breaks, by matching it word for word against Liebermann's text (or Robertson's, where Liebermann's was missing); his translation was divided by hand at the corresponding place, and his notes went with the words they comment on. Each clause's Rabin page is the page of the proofs where that clause begins. The spreadsheet rows to change are listed in *Rabin_and_Liebermann_corrections.xlsx*. Liebermann's own Old English was added to Cn 1020, VIII Atr (his MS D), IX Atr and X Atr, transcribed from *Gesetze* I pp. 263–275.

**Date and place.** The spreadsheet's *Place and date of promulgation* column holds dates, places and scholars in one string, e.g. *1018 (Whitelock, Kennedy, Wormald); Oxford*. The script splits it (`tools/promulgation.py`) into `<date>` and `<placeName>` elements in `<creation>`, each with `source` pointing to the works of the scholars who propose it; the original string is kept in `<note type="promulgation">`. The clause page shows them as *Date:* and *Place:* lines, with each scholar linked to their work at the foot of the page. A scholar's work that is not already on the page as an edition or translation is added as a `type="study"` source and listed under *Studies*. Every string the spreadsheet had in October 2026 is in `TABLE` in that file, split by hand; a new or changed string is split by rule (see the file), so check the page and add it to `TABLE` if needed.

**The rubrics to Alfred and Ine (Af Rb, Ine Rb).** Jurasinski and Oliver edit the rubric list of MS E, and also print in full the rubrics of MS B (CCCC 383), whose scribe put them above the clauses and sometimes corrected them. In the spreadsheet, B's rubric follows E's in the same cell, in both the *Modern editor's text* and *Modern editor's translation* columns. The script splits them (`tools/rubric_split.py`): B's rubric becomes its own text, labelled MS B, and gets its own translation only where it translates differently from E's. Where both translate the same, the translation is given once. A cell with only E's rubric is left as it is. B's rubric is taken to start at the second *Be* in the Old English and the second *Concerning* in the English; the few rubrics that do not fit (Af Rb 11, 37, 39; Ine Rb 14, Prol.) are listed in `SPECIAL` in that file. If the spreadsheet is later given separate columns for B, this step can go.

`tools/law-code-from-xlsx.py` (one code at a time, from a spreadsheet in Æthelberht's old column order) and `tools/laws-from-xlsx.py` (the first, old layout) are kept because the new script uses their helpers, but they are not needed any more.

## Law codes that need a decision

- **Cn 1018** (77 rows) has not been checked: Liebermann does not print it as one text. Its files are in the old layout and the script leaves them alone (`SKIP` in the script). Take it out of `SKIP` once it is decided.
- **Not on the law code list**, so their clauses are not linked to it and dictionary citations cannot find them: *Af Rb* and *Ine Rb* (the rubrics), *VI Atr Lat*, *Geþyncðo*, *Prom. Reg.*, *Cn 1018* and *Ymb Æwbricas*. Add them to `data/markLaw.json` and run the script again.
- **Translators not recorded** for Duns, Forf, Pax, Wal, Swer, Romscot, Iudex, Iud Dei VIII and VI Atr Lat (see above).
