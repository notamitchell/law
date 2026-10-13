# Bulk import from Word

The team transcribes the *Wörterbuch* into Word documents, one letter range at a time (for example `A - boc.docx`). A bulk import turns a whole document into TEI entry files at once, instead of pasting entries into the form one by one.

There are two ways to run it. Both use the same code (`scripts/docx-import.js` and `scripts/eliebermann.js`), so they give the same files.

## In the browser (no setup)

The browser page, `import.html`, is not on the site for now: its front matter has `published: false`, so Jekyll leaves it out. To use it, run the site locally with `bundle exec jekyll serve --unpublished --baseurl /law` and open http://localhost:4000/law/import.html. To put it back on the site, delete that line and add it to `_data/navigation.yml`.

1. Open the Bulk import page and choose the `.docx`.
2. Check the list. Entries marked **Check** need a look (see [What gets flagged](#what-gets-flagged)); click a headword to preview it.
3. Download the zip. It holds the new entries in folders of 100, because GitHub's web upload takes 100 files at a time.
4. Upload each folder's files to [the entries folder on GitHub](https://github.com/notamitchell/law/upload/main/entries) and commit. The site rebuilds in a minute or two.

Entries already on the site are left out of the zip unless you tick **Also replace entries that are already on the site**, so translations and links people have added aren't overwritten.

## On your computer

Needs [Node.js](https://nodejs.org/) 18 or later.

```sh
npm install
node tools/import-docx.js "B - bysen.docx" --dry-run   # report only, writes nothing
node tools/import-docx.js "B - bysen.docx"             # writes new entries to entries/
node tools/import-docx.js "B - bysen.docx" --overwrite # also replaces existing entries
```

It writes the files straight into `entries/` and a report to `docs/import-report.md`. Review the changes with `git diff` before committing.

## How the document is read

The import reads `word/document.xml` inside the `.docx` paragraph by paragraph, keeping bold, italic, superscript and subscript.

- **Page numbers.** A paragraph that is only a number (`1.`, `2`) is the page number of the printed book. The paragraph after it is the running head (`Abetot – Accent`). Neither is copied into an entry; the page number is recorded on every entry that starts on that page.
- **Letter headings.** A paragraph that is only a capital letter (`A`, `B.`) is skipped.
- **A new entry** starts with a paragraph whose first bold text comes before any other text, apart from:
  - the superscript **L** or **F** that marks Latin and French headwords;
  - a few unbolded lower-case words, brackets or hyphens, as in *ut* **aberste**, *s.* **Agatha**, [**-abeden**].
- **Continuations.** Any other paragraph carries on the entry before it. This is how entries that run over a column or page are joined back together. When the page changes inside an entry, a page marker (`<pb/>`) is kept at that point.
- **The headword** is the first bold text, widened to the whole word around it, so brackets, hyphens and letters outside the bold are kept (`(-)æ-`, `æht(a)`). A sense number after it (**abrecan 1**)) is dropped, and of two forms (**bernet, berning**) the first is the headword.
- **Language.** Superscript L is Latin, F is French. A headword in bold italic is one of Liebermann's grammatical articles (*Accusativ*, *Adjectiv*). Everything else is Old English.
- **~ headwords.** A headword written as ~ plus an ending (**~gatio** after **abnegare**) is expanded from the headword before (*abnegatio*), and flagged so an editor can confirm it.
- **Links.** Law codes and manuscript sigla in `data/markLaw.js` and abbreviations in `data/markforward.js` are linked, longest match first. Law codes are only linked in roman type, since Liebermann's italics are German.
- **Cross-references.** A short entry that only points elsewhere (**abere** *s.* æbære) gets a "see also" link when the entry it points to is in the document or on the site.
- **File names** follow the rules in [SCHEMA.md](SCHEMA.md#file-names).

## What gets flagged

| Check | Why |
|---|---|
| Headword written as ~… | The expansion of ~ is a guess from the headword before. |
| Bold starts mid-word | The transcription bolded only part of the headword (a**gyten**), so the import added the letters before it. Confirm the headword. |
| Long headword | More than 25 characters: probably bold that runs past the headword. |
| No page number | The entry comes before the first page number in the document. |

## What it can't catch

The import trusts the formatting. If a headword isn't bold, its entry is joined onto the one before; if a word inside an entry is bold at the start of a paragraph, that paragraph becomes a new entry. When an entry looks wrong on the site, the fix is usually in the Word document's formatting, followed by importing that entry again (with **replace** ticked, or `--overwrite`), or editing the entry with the form.
