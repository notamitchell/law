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
        const translation = pick(xml, /<sense type="translation"[^>]*>([\s\S]*?)<\/sense>\s*(?:<xr|<\/entry)/);
        const hw = decode(pick(xml, /<orth>([\s\S]*?)<\/orth>/));
        const text = decode(scrap);
        // Short summary for the list: the English translation if there is
        // one, otherwise the start of Liebermann's text after the headword.
        const t = text.replace(/^[LF]\s+/, '');
        const at = t.indexOf(hw);
        const rest = (at >= 0 ? t.slice(at + hw.length) : t).replace(/^[\s,.;:]+/, '');
        const snippet = rest.length > 110 ? rest.slice(0, 110).replace(/\s+\S*$/, '') + '…' : rest;
        return {
            id: f.replace(/\.xml$/, ''),
            hw,
            lang: pick(xml, /<entry[^>]*xml:lang="([^"]+)"/) || 'ang',
            page: pick(xml, /<biblScope unit="page">([^<]*)<\/biblScope>/),
            gloss: decode(translation) || snippet,
            en: !!translation,
            text
        };
    })
    .sort((a, b) => a.id.localeCompare(b.id));

fs.mkdirSync(path.join(repo, 'data'), { recursive: true });
fs.writeFileSync(path.join(repo, 'data', 'entries.json'),
    '[\n' + entries.map(e => JSON.stringify(e)).join(',\n') + '\n]\n');
console.log(`data/entries.json: ${entries.length} entries`);
