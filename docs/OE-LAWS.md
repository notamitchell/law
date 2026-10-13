# The Old English laws database (`oe-laws/`)

`oe-laws/` holds the text of the laws themselves, one clause at a time. It was made from the spreadsheet *OE_Laws_Database_For_Claude.xlsx*: **each clause row of the spreadsheet is one TEI XML file** (2,294 files), plus `oe-laws/index.json`, a catalogue listing every file.

It is not a section of the website yet, but there is a first clause page, `law.html`, and the dictionary entries for the letter A link to it (see "Linking to dictionary entries"). The aim is for the laws to become their own section of the site.

## What is in a file

Take `oe-laws/Abt_1-a.xml`, the clause *Abt 1[a]*. Its header says where the clause comes from and its body holds the texts.

| In the spreadsheet | In the file |
| --- | --- |
| **A** (code and clause joined) | the title, and `<idno type="citation">` |
| **B** Liebermann's code abbreviation | `<idno type="lawCode">`; the link in the clause heading; `<idno type="lawCodeAnchor">` when the code is on the [law code list](../lawAbb.html) |
| **C** Liebermann's internal clause numbering | `<idno type="clause">`, the `n` of the clause, and `<idno type="citationKey">` (see below) |
| **D** Code/Legal text | `<idno type="legalText">` when it differs from B (for example *Af (domboc)*) |
| **E** Place and date of promulgation | `<creation><note type="promulgation">`, kept exactly as typed |
| **F** MSS (Liebermann's sigla) | `<listWit>`, one `<witness>` per manuscript. The editors' selected manuscript is in bold in the spreadsheet and is kept as `rend="bold"` |
| **G** Gesetze page number | `<biblScope unit="page">`, in a reference to Liebermann, *Die Gesetze der Angelsachsen*, vol. 1 |
| **H**, **I** Editorial numbers (Liebermann's, and the modern editor's) | `<idno type="liebermannNumber">` and `<idno type="editorNumber">` |
| **J** Selected MS | `<ab type="selectedText">` |
| **K** Translation of the selected text | `<ab type="translation" xml:lang="en">` |
| **L** Second translation (where made) | `<ab type="secondTranslation">` |
| **M** Supplementary MS (where made) | `<ab type="supplementaryText">` |
| **N** Translation of the supplementary MS | `<ab type="supplementaryTranslation">` |
| **O** Offence/Legal event | `<keywords n="offence-legal-event">`, one `<term>` for each item between semicolons |
| **P** People | `<keywords n="people">`, the same way |
| **Q** Locations | `<keywords n="locations">`, the same way |

The spreadsheet repeats a **sub-header row** before each block of clauses. Those rows are not clauses, so they do not become files. They name the law, its editor, its translator and the manuscripts used, and that information is copied into the header of every file in the block (the title, the editor and translator, `<bibl type="legalText">`, `<bibl type="selectedText">`). The 352 empty rows are skipped.

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

`laws.html` is the search page for the clauses, with its own tab in the menu. It reads `data/laws.json`, which `tools/build-laws-index.js` writes from `oe-laws/` on every deploy (as `tools/build-index.js` does for the dictionary), so a clause added to `oe-laws/` appears in the search by itself. You can search by law code and clause (*Ine 23*, *abt 1a*), pick a law, type a keyword (an offence, a kind of person or a place; the box suggests the ones that exist), and tick a box to search the Old English texts and translations too (þ and th, æ and ae are treated alike). Clicking a keyword on a result or on a clause page searches for it. `law.html` is the page for one clause.

### Manuscript letters are not in the citation lists

Liebermann sometimes follows a passage with the letter of a manuscript or version, such as *Af 41 B* or *Ine 9 Q* (Quadripartitus). The list of law code citations at the foot of an entry names the passage only (*Af 41*, *Ine 9*), and a passage cited in several manuscripts is listed once. Liebermann's own text, above, is unchanged and keeps the letters. The rule is in `scripts/eliebermann.js` (`SIGLA`, in `extractCitations`), so the *Suggest an entry* form and `tools/update-entries.js` both follow it.

### The letter A trial

`tools/link-citations.py --letter A` changes the law code citations at the foot of the entries filed under A. The entries that begin with æ are a letter of their own, Æ, so they need `--letter Æ` (the first trial was run when they were part of A). A citation that finds its clause changes from `target="law:Ine"` to `target="clause:Ine_23-2"`, and the entry gets a `clause` prefix definition. The site turns that into a link to `law.html?id=Ine_23-2`, which shows the clause, its manuscripts and keywords, the neighbouring clauses, and a button to read the whole law. The citation text is unchanged. Citations that find nothing are left as they were. The tool is safe to run again, and `--dry-run` only reports. Its latest results are in [oe-laws-link-report.md](oe-laws-link-report.md).

The citation lists no longer carry manuscript letters (see the next paragraph). A citation is matched to a clause in two ways: exactly; or, where Liebermann cites *Abt 1* but the spreadsheet has *1[a]* and *1[b]*, by going to the first part.

Results for A and Æ together: 82% of all citations are linked, and 97% of those that name a clause in a code the database has. The rest are mostly citations to codes with no clause files (see below). Run it with another letter to link other entries.

**Alfred's Introduction.** The catalogue's `citationKeys` for these clauses (*Af El. 1*) are wrong: they give the keys *Af el* and *Af 1*, so *Af 1* would also point at the Introduction. `link-citations.py` works round this by using the clause as printed; `laws-from-xlsx.py` should be fixed to give *Af el.1*.

## The new layout (Æthelberht first)

From October 2026, law codes are being improved one at a time in their own spreadsheet with more columns. **Æthelberht (*Abt*) is the first and is the model for the rest.** Its 128 clause files were made from *Aethelberht.xlsx* with `tools/law-code-from-xlsx.py`, and each now holds four texts:

| In the spreadsheet | In the file | On the clause page |
| --- | --- | --- |
| **K** Liebermann's text (MS in **H**, page in **I**, number in **J**) | `<ab type="liebermannText" source="#liebermann">` | *Old English text*, labelled **Liebermann** · Gesetze I, p. … · MS … |
| **P** Modern editor's text (editor in **M**, MS in **N**, number in **O**) | `<ab type="editionText" source="#oliver">` | *Old English text*, labelled **Oliver** · § … · MS … |
| **Q** Modern editor's translation | `<ab type="translation" source="#oliver">` | *Translations*, labelled **Oliver** |
| **R** Second translation (translator and book in **S**) | `<ab type="translation" source="#attenborough">` | *Translations*, labelled **Attenborough** |
| **L**, **S** full references | `<listBibl type="sources">`, one `<bibl xml:id="…">` each | *Editions and translations*, at the foot of the page |

- On the page the Old English texts are on the left and the translations on the right (one above the other on a phone). Each is labelled with the surname of its editor or translator, which links to the full reference at the foot of the page; hovering over it shows the reference too.
- The surname of the second translator is taken from column **S** (the name before the first comma), and of the modern editor from column **M**.
- **Italic is kept.** Italic letters in the Old English (Liebermann's and Oliver's expansions of abbreviations, such as scillingu*m*) and italic words in the translations (*mundbyrd*, *wergild*) are `<hi rend="italic">`. Italic in a book reference is its `<title>`.
- **D** (*Æthelberht's Code*) and **E** (*Æthelberht, r. ?584–616*) appear under the clause heading. The short name in the Laws list and its menu is the king's name from **E**.
- The file names are the same as before (`Abt_1-a.xml`…), so links from dictionary entries still work.
- Every other law code is still in the old layout and is shown as before. `law.html` shows a clause in the new layout whenever its file has a `liebermannText`.

### Doing the next law code

Make its spreadsheet with the same column headings as *Aethelberht.xlsx* (the script finds the columns by their headings in row 1, so their order does not matter). Then, from the repository folder:

```
python3 tools/law-code-from-xlsx.py path/to/Ine.xlsx --dry-run    # report only
python3 tools/law-code-from-xlsx.py path/to/Ine.xlsx
```

It replaces only the files of the law code(s) in that spreadsheet and their lines in `oe-laws/index.json`, and leaves everything else alone. It reports any clause that is new or that no longer has a row.

**`tools/laws-from-xlsx.py` will not undo this.** If the big spreadsheet is ever run again, it keeps every law code that is already in the new layout and does not replace it.

## Law codes that need a decision

61 of the spreadsheet's 73 law codes are linked to the law code list. Two groups are not certain:

**Matched by me, please confirm** (the spreadsheet's spelling is not quite the list's; I think they are the same):

| Spreadsheet | Law code list |
| --- | --- |
| *Becw* | *Becwæð* (`Becwaeth`) |
| *Mirc.* | *Mirce* |
| *Nor. Cyricgrið* | *Nor Grið* (`NorGrith`) |
| *Norðleod.* | *Norðleoda* (`Northleoda`) |
| *Ord* | *Ordal* |
| *Rom.* | *Romscot* |

**Not on the law code list**, so their files are not linked: *Cn 1018* (77 clauses), *Rubrics: Af* and *Rubrics Af* and *Rubrics: AF*, *Rubrics: Ine* and *Rubrics: INE*, *VI Atr (Latin Paraphrase)* (65), *Wer* (11), *Geþyn.* (9), *Prom. Reg.* (5), *Rubric List* and *Ymb Æwbricas*. Add them to `data/markLaw.json`, or tell the script which existing code they are (the list `ASSUMED_ANCHORS` in `tools/laws-from-xlsx.py`), and run it again.

## Choices made that you may want to change

- **Language.** The spreadsheet does not say which language each text is in, and some of it is Latin. The selected and supplementary texts are marked `xml:lang="und"` (undetermined); the translations are marked English. Language can be added once it is known.
- **Selected manuscript.** In the spreadsheet the editors' selection is shown in bold only where more than one manuscript is listed. The files keep that bold. Where a clause lists just one manuscript, that is the one used, and it has no bold. `<bibl type="selectedText">` always names the manuscript (from the sub-header row).
- **Spaces.** Runs of spaces, line breaks and non-breaking spaces in the spreadsheet cells are single ordinary spaces in the files. Nothing else in the text is changed.
- **Merged cells.** Where the spreadsheet merges a cell over several clauses (5 clauses in *Nor. Cyricgrið*), the merged text is copied into each of those clauses and a `<note type="source">` says so.
- **A note typed in a clause cell.** One clause cell (the first *Cn 1018* row) holds a sentence of explanation, not a clause number. It is kept as `<note type="clause">`, and the file has no clause number.
- **People and Locations** are lists of kinds of people and places (*Bishops*, *Churches*), not named individuals, so they are keywords, not `<persName>` and `<placeName>`.
- Every file says it was **generated from a row of the spreadsheet and not yet checked against the print.**

## Making the files again

If the spreadsheet is corrected, make the folder again from it. You need Python 3 and `pip install openpyxl`; then, from the repository folder:

```
python3 tools/laws-from-xlsx.py path/to/OE_Laws_Database_For_Claude.xlsx
```

The script replaces the files in `oe-laws/` (it removes the old `.xml` files and `index.json` first, and touches nothing else) and prints a short report. Row numbers in each file's `revisionDesc` refer to the spreadsheet it was made from.
