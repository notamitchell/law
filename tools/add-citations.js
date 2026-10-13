#!/usr/bin/env node
/*
 * Law code citations: rewrites the citation list (<xr type="lawCode">) of
 * every entry in entries/ from the law codes cited in Liebermann's text, so
 * each passage, such as "VI As 1,1", is listed and links to its code on the
 * law code list. Citations added by hand that the text doesn't give (or that
 * have a link to the passage online) are kept after the generated ones.
 *
 *   npm install
 *   node tools/add-citations.js             # every entry
 *   node tools/add-citations.js bocland ad  # just these
 *   node tools/add-citations.js --dry-run   # report only
 *
 * The Suggest an entry form makes the same list when it saves an entry.
 */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const repo = path.resolve(__dirname, '..');
const ELieb = require(path.join(repo, 'scripts/eliebermann.js'));
ELieb.useDom(new JSDOM('<!doctype html><body></body>').window);

const unescape = t => t.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
const XR = /^\s*<xr type="lawCode"><ref(?: target="([^"]*)")?>([\s\S]*?)<\/ref><\/xr>\s*$/;

function update(xml) {
    const scrap = /<dictScrap[^>]*>([\s\S]*?)<\/dictScrap>/.exec(xml);
    const lines = xml.split('\n');
    const extra = [];
    const kept = lines.filter(line => {
        const m = XR.exec(line);
        if (!m) return true;
        if (!(m[1] || '').startsWith('law:')) extra.push({ text: unescape(m[2].replace(/<[^>]*>/g, '')), url: m[1] ? unescape(m[1]) : '' });
        return false;
    });
    const end = kept.findIndex(line => /^\s*<\/entry>/.test(line));
    if (end < 0) return { xml, count: 0 };
    const indent = kept[end].match(/^\s*/)[0] + '  ';
    const xr = ELieb.citationXr(scrap ? scrap[1] : '', extra);
    kept.splice(end, 0, ...xr.map(x => indent + x));
    return { xml: kept.join('\n'), count: xr.length };
}

function main() {
    const args = process.argv.slice(2);
    const dryRun = args.includes('--dry-run');
    const only = args.filter(a => !a.startsWith('--'));
    const dir = path.join(repo, 'entries');
    const files = only.length ? only.map(id => id + '.xml') : fs.readdirSync(dir).filter(f => f.endsWith('.xml'));
    let changed = 0, withCitations = 0, citations = 0;
    for (const file of files) {
        const before = fs.readFileSync(path.join(dir, file), 'utf8');
        const { xml, count } = update(before);
        if (count) { withCitations++; citations += count; }
        if (xml !== before) {
            changed++;
            if (!dryRun) fs.writeFileSync(path.join(dir, file), xml);
        }
    }
    console.log(`${files.length} entries, ${withCitations} with citations (${citations} in all); ${changed} ${dryRun ? 'would change' : 'changed'}.`);
}

if (require.main === module) main();
module.exports = { update };
