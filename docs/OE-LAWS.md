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
- **Notes.** Remarks about the spreadsheet itself ("a line break inside K was removed", "text in column T") are tidied away (`NOTE_TIDY` in the script). The record of checking ("K: checked against Gesetze I p. 3", "T: corrected against Robertson p. 200 (…)") is not shown as a note: it becomes a line at the foot of the clause page, such as *Liebermann's text checked against Die Gesetze der Angelsachsen I, p. 3*. What a cell said before a correction is not on the website; it is in the spreadsheet.
- **Italic** in the spreadsheet (Liebermann's and the editors' expansions of abbreviations, italic words in translations) is kept as `<hi rend="italic">`; italic in a book reference is its `<title>`.

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

The script finds the columns by their headings in row 1, so columns can be moved but not renamed. It reads the sheet called *Sheet1* (the *Read me* and *corrections* sheets are ignored).

**File names stay the same.** Each row is matched to the file its clause had before, by law code and clause number, so dictionary entries that link to a clause keep working. Where a clause number was changed in the spreadsheet (for example *I Atr 1.10*, which the old spreadsheet had as a second *1.1*), the row keeps the old file (`IAtr_1-1_dup2.xml`), and the dry run lists every such case. A clause that is new gets a new file; a file whose clause no longer has a row is removed. In October 2026 one file was removed: `Rubrics-INE_part-001`, which was a sub-header row, not a clause. All 1,069 clause links in the dictionary still find their files.

**The rubrics to Alfred and Ine (Af Rb, Ine Rb).** Jurasinski and Oliver edit the rubric list of MS E, and also print in full the rubrics of MS B (CCCC 383), whose scribe put them above the clauses and sometimes corrected them. In the spreadsheet, B's rubric follows E's in the same cell, in both the *Modern editor's text* and *Modern editor's translation* columns. The script splits them (`tools/rubric_split.py`): B's rubric becomes its own text, labelled MS B, and gets its own translation only where it translates differently from E's. Where both translate the same, the translation is given once. A cell with only E's rubric is left as it is. B's rubric is taken to start at the second *Be* in the Old English and the second *Concerning* in the English; the few rubrics that do not fit (Af Rb 11, 37, 39; Ine Rb 14, Prol.) are listed in `SPECIAL` in that file. If the spreadsheet is later given separate columns for B, this step can go.

`tools/law-code-from-xlsx.py` (one code at a time, from a spreadsheet in Æthelberht's old column order) and `tools/laws-from-xlsx.py` (the first, old layout) are kept because the new script uses their helpers, but they are not needed any more.

## Law codes that need a decision

- **Cn 1018** (77 rows) has not been checked: Liebermann does not print it as one text. Its files are in the old layout and the script leaves them alone (`SKIP` in the script). Take it out of `SKIP` once it is decided.
- **Not on the law code list**, so their clauses are not linked to it and dictionary citations cannot find them: *Af Rb* and *Ine Rb* (the rubrics), *VI Atr Lat*, *Geþyncðo*, *Prom. Reg.*, *Cn 1018* and *Ymb Æwbricas*. Add them to `data/markLaw.json` and run the script again.
- **Translators not recorded** for Duns, Forf, Pax, Wal, Swer, Romscot, Iudex, Iud Dei VIII and VI Atr Lat (see above).
