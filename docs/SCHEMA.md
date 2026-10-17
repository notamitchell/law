# The entry format (TEI)

Each dictionary entry is one TEI XML file in `entries/`, named after its headword (see [File names](#file-names)). The site reads these files in the browser; nothing else needs updating when one is added.

The files are made by the [Suggest an entry](../contribute.html) form, the bulk import (`import.html` or `tools/import-docx.js`), all of which use `ELieb.buildEntryXml()` in `scripts/eliebermann.js`. If you edit a file by hand, keep to the shape below.

## Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>abere</title>
      </titleStmt>
      <publicationStmt>
        <publisher>eLiebermann: An Online Dictionary of Pre-Conquest English Law</publisher>
        <idno type="slug">abere</idno>
      </publicationStmt>
      <sourceDesc>
        <bibl>
          <author>Felix Liebermann</author>, <title>Die Gesetze der Angelsachsen</title>, <biblScope unit="volume">2.1</biblScope> (Wörterbuch), <biblScope unit="page">1</biblScope>
            <ptr type="facsimile" target="https://archive.org/details/diegesetzederang02liebuoft/page/1/mode/2up"/>
        </bibl>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <listPrefixDef>
        <prefixDef ident="law" matchPattern="(.+)" replacementPattern="lawAbb.html#$1"/>
        <prefixDef ident="gram" matchPattern="(.+)" replacementPattern="gramAbb.html#$1"/>
        <prefixDef ident="bib" matchPattern="(.+)" replacementPattern="bibAbb.html#$1"/>
        <prefixDef ident="entry" matchPattern="(.+)" replacementPattern="entry.html?id=$1"/>
      </listPrefixDef>
    </encodingDesc>
    <revisionDesc>
      <change when="2026-10-12">Imported from A - boc.docx.</change>
    </revisionDesc>
  </teiHeader>
  <text>
    <body>
      <entry xml:lang="ang">
        <form type="lemma">
          <orth>abere</orth>
        </form>
        <dictScrap type="liebermann"><hi rend="bold">abere</hi> <hi rend="italic">s</hi>. æbære</dictScrap>
        <xr type="see"><ref target="entry:aebaere">æbære</ref></xr>
      </entry>
    </body>
  </text>
</TEI>
```

## The header

| Element | What it holds |
|---|---|
| `titleStmt/title` | The headword. |
| `idno type="slug"` | The file name without `.xml`. |
| `sourceDesc/bibl` | Where the entry is printed: `biblScope unit="page"` is the page of the *Wörterbuch* as printed (not the page of a PDF), and `ptr type="facsimile"` links to the scan of that page. |
| `listPrefixDef` | Says what the short link targets below (`law:`, `gram:`, `bib:`, `entry:`) point to. The same in every file. |
| `revisionDesc/change` | One line per change, with its date: created, imported, edited. The form adds a line when a change is suggested. |

## The entry

`<entry>` has:

- `xml:lang`: the language of the headword. `ang` Old English, `la` Latin, `fro` French. Grammatical terms (Liebermann's articles on *Accusativ*, *Adjectiv* and so on) are `xml:lang="de"` with `type="grammatical"`.
- `type="xref"`, optional: a cross-reference entry, one that only sends the reader to another headword ("abere s. æbære"). Its page shows Liebermann's line and a "See" list (not "See also"), and nothing else; it has no links to other dictionaries, since the headword it points to carries them. `tools/cross-reference-entries.py` finds these entries and marks them; the form keeps the mark when a change is suggested.
- `n`, optional: the homograph number when Liebermann numbers headwords I), II).

Inside it, in this order:

| Element | Required | What it holds |
|---|---|---|
| `form type="lemma"/orth` | yes | The headword as printed, with any brackets or hyphens (`[-abeden]`, `-a-`). |
| `usg type="dom"` | no | `spelling` for a spelling entry: a letter or letters rather than a word (ā, aa, -cgg-, þ, ł), where Liebermann notes how the scribes write it and lists the entries that show it. The page shows a "Spelling" badge and a line saying so. The list is kept in `tools/spelling-entries.py`. |
| `dictScrap type="liebermann"` | yes | Liebermann's whole entry as printed. See [Liebermann's text](#liebermanns-text). |
| `dictScrap type="senses"` | no | Liebermann's numbered meanings, taken from the full text: one `<sense n="2">` for each bold "2)", holding the text from after the ")" up to the next number, marked up as in the full text. The text before "1)" (headword and forms) stays only in the full text. The form and `tools/update-entries.js` remake this from the full text, so correct the full text rather than this. |
| `sense type="liebermann" xml:lang="de"` | no | Liebermann's definition. Either one `<def>`, or numbered `<sense n="1"><def>…</def></sense>` for numbered senses. |
| `sense type="translation" xml:lang="en"` | no | The English translation, in the same shape. |
| `note type="editorial"` | no | A note by the eLiebermann editors, shown under Liebermann's entry as "Editor's note": for example where his pointer names a headword the dictionary doesn't have (*s. aver* for *aveir*). May hold links: `<ref target="entry:aveir">aveir</ref>`. The form keeps it when a change is suggested. |
| `xr type="see"` | no | A cross-reference to another entry: `<ref target="entry:aebaere">æbære</ref>`. |
| `xr type="bosworthToller"`, `"doe"`, `"wiktionary"` | no | Links to the Bosworth-Toller Anglo-Saxon Dictionary, the Dictionary of Old English and Wiktionary: `<ref target="https://…">boc-land</ref>`. One `xr` per link. |
| `xr type="lawCode"` | no | A law code citation. One is made for every passage cited in the entry, such as `<ref target="law:VIAs">VI As 1,1</ref>`, linked to the code on the law code list; the form and `tools/update-entries.js` remake these from the text, so don't edit them by hand. Citations added by hand have no `law:` target, or a `target` to the passage online, and are kept. A citation an editor adds that the text implies but doesn't print, such as the clauses after Liebermann's "Swer 7ff.", is `<xr type="lawCode" subtype="added"><ref target="clause:Swer_8">Swer 8</ref></xr>`: the tools leave it alone, and the page lists it after the last citation of the same law code. |

## Liebermann's text

The text inside `dictScrap` keeps the formatting of the printed page, because it carries meaning:

| In print | In TEI |
|---|---|
| superscript L or F before the headword (Latin, French) | `<lbl type="language">L</lbl>` |
| bold (headwords, sense numbers) | `<hi rend="bold">` |
| italic (Liebermann's German) | `<hi rend="italic">` |
| superscript (footnote numbers, manuscript variants) | `<hi rend="superscript">` |
| a law code, text or manuscript siglum | `<ref type="lawCode" target="law:IICn">II Cn</ref>`, where `IICn` is its Anchor in `data/markLaw.json` |
| a German abbreviation | `<ref type="abbreviation" target="gram:Plural"><abbr>pl</abbr></ref>`, where `Plural` is its Anchor in `data/markforward.json` |
| an author or work Liebermann cites | `<ref type="bibl" target="bib:CitToller">Toller</ref>`, where `CitToller` is its Anchor in `data/bibliography.json`. Usually only the author's name is linked; the short title and page follow as plain text. |
| a clause number the citation tools can't attach to its law code ("Af 43; on G- ~an … 5,4", where 5,4 is Af 5,4) | `<ref type="clause" target="clause:Af_5-4">5,4</ref>`: a link to the clause, made by hand |
| an entry that runs over a page | `<pb n="4"/>` where page 4 begins |
| a line break the editor wants kept | `<lb/>` |

Law codes are only linked in roman type: in italics Liebermann is writing German, so *Abt* is "abbot", not the laws of Æthelberht (`Abt`).

## File names

The file name is the headword with accents and special letters folded to plain ones, capitals kept, and anything else turned into hyphens (`ELieb.slugify()`):

| Headword | File |
|---|---|
| abbod | `abbod.xml` |
| æbylgð | `aebylgd.xml` |
| Abkürzungen | `Abkurzungen.xml` |
| þegn | `thegn.xml` |
| [-abeden] | `abeden.xml` |

æ becomes ae, þ th, ð d, ƿ w, ȝ g, ⁊ and. When two headwords give the same name (Liebermann has an Old English *a*, a French *a*, and the affixes *a-*, *-a-*, *-a*), the plain headword gets the plain name and the others get `-2`, `-3`… in the order they appear in the document. So `a.xml` is the first plain *a*, and `a-5.xml` might be the prefix *a-*. The headword in the file is always the real one; the file name only has to be unique.

The entry page finds an entry by file name (`entry.html?id=aebaere`) or by headword (`entry.html?id=æbære`).

## Site pages

The text of the Home and About pages is in `pages/Home.xml` and `pages/About.xml`, as TEI `<div>`s with `<head>`, `<p>`, `<list>`/`<item>`, `<title>` and `<ref target="…">`. Edit those files to change the text; the first `<head>` is the page's title.

## Manuscripts (Statuta Vetera)

Manuscript descriptions in `tei/` use the TEI `msDesc` made by the [manuscript description generator](../StatutaVetera/tei-gen.html): `msIdentifier` (settlement, repository, idno), `msContents`, `physDesc` (with `dimensions type="leaf"` and `type="written"` in mm), `history/provenance` and `additional/listBibl`. The search page reads those elements, so keep their names.
