#!/usr/bin/env node
/*
 * Bulk import: turns a Word document of Liebermann's dictionary into one
 * TEI file per entry in entries/. Does the same as the Bulk import page
 * (import.html), for when you'd rather run it on your own computer.
 *
 *   npm install
 *   node tools/import-docx.js "A - boc.docx"            # writes new entries only
 *   node tools/import-docx.js "A - boc.docx" --dry-run  # report only
 *   node tools/import-docx.js "A - boc.docx" --overwrite
 *
 * Entries that already exist in entries/ are left alone unless --overwrite
 * is given. A report of entries to check is written to docs/import-report.md.
 * See docs/IMPORT.md.
 */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');
const JSZip = require('jszip');

const repo = path.resolve(__dirname, '..');
const ELieb = require(path.join(repo, 'scripts/eliebermann.js'));
const DocxImport = require(path.join(repo, 'scripts/docx-import.js'));

function loadJson(file) {
    return JSON.parse(fs.readFileSync(path.join(repo, file), 'utf8'));
}

async function main() {
    const args = process.argv.slice(2);
    const docx = args.find(a => !a.startsWith('--'));
    if (!docx) {
        console.error('Usage: node tools/import-docx.js <file.docx> [--dry-run] [--overwrite]');
        process.exit(1);
    }
    const dryRun = args.includes('--dry-run');
    const overwrite = args.includes('--overwrite');

    const dom = new JSDOM('<!doctype html><body></body>');
    ELieb.useDom(dom.window);
    DocxImport.useDom(dom.window);

    const zip = await JSZip.loadAsync(fs.readFileSync(docx));
    const documentXml = await zip.file('word/document.xml').async('string');
    // Manuscript sigla are linked like law codes.
    const markLaw = loadJson('data/markLaw.json').concat(loadJson('data/manuscripts.json'));
    const markforward = loadJson('data/markforward.json');
    const bibliography = loadJson('data/bibliography.json');

    const entriesDir = path.join(repo, 'entries');
    const existing = fs.readdirSync(entriesDir).filter(f => f.endsWith('.xml')).map(f => f.replace(/\.xml$/, ''));
    const { entries, skipped } = DocxImport.parse(documentXml);
    DocxImport.prepare(entries, existing, ELieb);

    const today = new Date().toISOString().slice(0, 10);
    const source = path.basename(docx);
    let written = 0, kept = 0;
    entries.forEach(e => {
        if (e.exists && !overwrite) { kept++; return; }
        const xml = ELieb.buildEntryXml({
            headword: e.headword,
            slug: e.slug,
            lang: e.lang,
            page: e.page,
            facsimile: e.page ? `https://archive.org/details/diegesetzederang02liebuoft/page/${e.page}/mode/2up` : '',
            entryHtml: ELieb.linkAbbreviations(e.html, markLaw, markforward, bibliography),
            seeAlso: e.seeAlso,
            change: { when: today, text: `Imported from ${source}.` }
        });
        if (!dryRun) fs.writeFileSync(path.join(entriesDir, e.slug + '.xml'), xml);
        written++;
    });

    const flagged = entries.filter(e => e.warnings.length);
    const report = [
        `# Import report: ${source}`,
        '',
        `${entries.length} entries found. ${dryRun ? 'Dry run: nothing written.' : `${written} written, ${kept} left as they were because they already exist.`}`,
        '',
        `## Entries to check (${flagged.length})`,
        '',
        '| Page | Headword | File | Check |',
        '|---|---|---|---|',
        ...flagged.map(e => `| ${e.page ?? ''} | ${e.headword} | ${e.slug}.xml | ${e.warnings.join('; ')} |`),
        '',
        `## Paragraphs not read as entries (${skipped.length})`,
        '',
        ...skipped.map(s => `- ${s.text}`),
        ''
    ].join('\n');
    fs.writeFileSync(path.join(repo, 'docs', 'import-report.md'), report);
    console.log(report.split('\n').slice(0, 3).join('\n'));
    console.log('Report written to docs/import-report.md');
}

main().catch(err => { console.error(err); process.exit(1); });
