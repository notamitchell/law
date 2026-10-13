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
| `listPrefixDef` | Says what the short link targets below (`law:`, `gram:`, `entry:`) point to. The same in every file. |
| `revisionDesc/change` | One line per change, with its date: created, imported, edited. The form adds a line when a change is suggested. |

## The entry

`<entry>` has:

- `xml:lang`: the language of the headword. `ang` Old English, `la` Latin, `fro` French. Grammatical terms (Liebermann's articles on *Accusativ*, *Adjectiv* and so on) are `xml:lang="de"` with `type="grammatical"`.
- `n`, optional: the homograph number when Liebermann numbers headwords I), II).

Inside it, in this order:

| Element | Required | What it holds |
|---|---|---|
| `form type="lemma"/orth` | yes | The headword as printed, with any brackets or hyphens (`[-abeden]`, `-a-`). |
| `dictScrap type="liebermann"` | yes | Liebermann's whole entry as printed. See [Liebermann's text](#liebermanns-text). |
| `sense type="liebermann" xml:lang="de"` | no | Liebermann's definition. Either one `<def>`, or numbered `<sense n="1"><def>…</def></sense>` for numbered senses. |
| `sense type="translation" xml:lang="en"` | no | The English translation, in the same shape. |
| `xr type="see"` | no | A cross-reference to another entry: `<ref target="entry:aebaere">æbære</ref>`. |
| `xr type="bosworthToller"`, `"doe"`, `"wiktionary"` | no | Links to the Bosworth-Toller Anglo-Saxon Dictionary, the Dictionary of Old English and Wiktionary: `<ref target="https://…">boc-land</ref>`. One `xr` per link. |
| `xr type="lawCode"` | no | A law code citation. One is made for every passage cited in the entry, such as `<ref target="law:VIAs">VI As 1,1</ref>`, linked to the code on the law code list; the form and `tools/add-citations.js` remake these from the text, so don't edit them by hand. Citations added by hand have no `law:` target, or a `target` to the passage online, and are kept. |

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
