#!/usr/bin/env node
/*
 * Writes data/entries.json: one line per dictionary entry, for the
 * Dictionary page's list and search. Runs on every deploy (see
 * .github/workflows/static.yml), so entries added to entries/ appear in the
 * list without anything else to update. Needs no npm packages.
 *
 *   node tools/build-index.js
 */
const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const dir = path.join(repo, 'entries');

const decode = s => s
    .replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();

const pick = (xml, re) => { const m = xml.match(re); return m ? m[1] : ''; };

const entries = fs.readdirSync(dir)
    .filter(f => f.endsWith('.xml'))
    .map(f => {
        const xml = fs.readFileSync(path.join(dir, f), 'utf8');
        const scrap = pick(xml, /<dictScrap[^>]*>([\s\S]*?)<\/dictScrap>/);
        const hw = decode(pick(xml, /<orth>([\s\S]*?)<\/orth>/));
        const text = decode(scrap);
        // Short summary for the list: the start of Liebermann's text after the
        // headword. (An English translation, if any, is not shown for now.)
        const t = text.replace(/^[LF]\s+/, '');
        const at = t.indexOf(hw);
        const rest = (at >= 0 ? t.slice(at + hw.length) : t).replace(/^[\s,.;:]+/, '');
        const snippet = rest.length > 110 ? rest.slice(0, 110).replace(/\s+\S*$/, '') + '…' : rest;
        return {
            id: f.replace(/\.xml$/, ''),
            hw,
            lang: pick(xml, /<entry[^>]*xml:lang="([^"]+)"/) || 'ang',
            page: pick(xml, /<biblScope unit="page">([^<]*)<\/biblScope>/),
            gloss: snippet,
            // a spelling, not a word (<usg type="dom">spelling</usg>): badged in the list
            spelling: /<usg type="dom">spelling<\/usg>/.test(xml),
            text
        };
    })
    .sort((a, b) => a.id.localeCompare(b.id));

fs.mkdirSync(path.join(repo, 'data'), { recursive: true });
fs.writeFileSync(path.join(repo, 'data', 'entries.json'),
    '[\n' + entries.map(e => JSON.stringify(e)).join(',\n') + '\n]\n');
console.log(`data/entries.json: ${entries.length} entries`);

// A small list of every entry's id and headword, for the previous and next
// links at the foot of each entry page (the page sorts it into Liebermann's
// order, as the Dictionary page does).
fs.writeFileSync(path.join(repo, 'data', 'entry-order.json'),
    '[\n' + entries.map(e => JSON.stringify([e.id, e.hw, e.lang])).join(',\n') + '\n]\n');
console.log(`data/entry-order.json: ${entries.length} entries`);
