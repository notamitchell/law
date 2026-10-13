#!/usr/bin/env node
/*
 * Writes data/laws.json: one line per clause file in oe-laws/, for the Laws
 * page's list and search. Runs on every deploy (see
 * .github/workflows/static.yml), like tools/build-index.js. Needs no npm
 * packages.
 *
 *   node tools/build-laws-index.js
 */
const fs = require('fs');
const path = require('path');

const repo = path.resolve(__dirname, '..');
const dir = path.join(repo, 'oe-laws');

const decode = s => s
    .replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim();
const pick = (xml, re) => { const m = xml.match(re); return m ? decode(m[1]) : ''; };
const idno = (xml, type) => pick(xml, new RegExp('<idno type="' + type + '">([^<]*)</idno>'));
const ab = (xml, type, lang) => [...xml.matchAll(new RegExp('<ab type="' + type + '"([^>]*)>([\\s\\S]*?)</ab>', 'g'))]
    .filter(m => !lang || new RegExp('xml:lang="' + lang + '"').test(m[1]))
    .map(m => decode(m[2])).filter(Boolean);
// English translations, the modern editors' first and the English of Liebermann's German last.
const english = xml => {
    const all = [...xml.matchAll(/<ab type="translation"([^>]*)>([\s\S]*?)<\/ab>/g)]
        .filter(m => !/xml:lang="de"/.test(m[1]));
    return all.filter(m => !/ana="#fromGerman"/.test(m[1])).concat(all.filter(m => /ana="#fromGerman"/.test(m[1])))
        .map(m => decode(m[2])).filter(Boolean);
};
const terms = (xml, n) => {
    const k = xml.match(new RegExp('<keywords n="' + n + '">([\\s\\S]*?)</keywords>'));
    return k ? [...k[1].matchAll(/<term>([^<]*)<\/term>/g)].map(m => decode(m[1])).filter(Boolean) : [];
};

const catalogue = JSON.parse(fs.readFileSync(path.join(dir, 'index.json'), 'utf8'));
const clauses = catalogue.map(c => {
    const xml = fs.readFileSync(path.join(dir, c.file), 'utf8');
    return {
        id: c.id,
        citation: c.citation,
        code: c.code,
        anchor: c.anchor,
        clause: c.clause,
        law: c.legalText,
        page: c.page,
        date: pick(xml, /<note type="promulgation">([\s\S]*?)<\/note>/),
        offences: terms(xml, 'offence-legal-event'),
        people: terms(xml, 'people'),
        places: terms(xml, 'locations'),
        text: ab(xml, 'liebermannText').concat(ab(xml, 'editionText'), ab(xml, 'selectedText'), ab(xml, 'supplementaryText')).join(' '),
        gloss: english(xml)[0] || '',
        en: english(xml).concat(ab(xml, 'secondTranslation'), ab(xml, 'supplementaryTranslation')).join(' '),
        row: c.sheetRow
    };
});   // in the order of oe-laws/index.json, which is the order of the spreadsheets

fs.writeFileSync(path.join(repo, 'data', 'laws.json'),
    '[\n' + clauses.map(c => JSON.stringify(c)).join(',\n') + '\n]\n');
console.log(`data/laws.json: ${clauses.length} clauses`);
