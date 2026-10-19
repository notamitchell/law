/*
 * eLiebermann: shared code for dictionary entries.
 *
 * - ELieb.slugify()        headword -> file name (entries/<slug>.xml)
 * - ELieb.linkAbbreviations() adds links to law codes, abbreviations and works cited
 * - ELieb.buildEntryXml()  builds an entry as TEI from the contribution form
 * - ELieb.renderTei()      turns TEI into HTML for entry pages and previews
 * - ELieb.readEntry()      reads the main fields of an entry (dictionary list)
 *
 * The entry format is documented in docs/SCHEMA.md.
 * Works in the browser (window.ELieb) and in Node (require), where a DOM
 * implementation such as jsdom is passed in with ELieb.useDom(window).
 */
(function (root) {
    'use strict';

    const TEI_NS = 'http://www.tei-c.org/ns/1.0';
    let DOM = typeof window !== 'undefined' ? window : null;

    const LANGUAGES = {
        ang: 'Old English',
        la: 'Latin',
        fro: 'French',
        de: 'Grammatical term'
    };

    /**
     * The little tag after a headword in lists: "OE" for Old English (with
     * "Old English" as its tooltip), and the full name for the others.
     */
    // Languages the reader has chosen to hide ("Hide Old English", "Hide Latin" etc. on the
    // Dictionary page). Remembered in this browser, so the entry pages' Previous
    // and Next links and the search suggestions skip them too.
    const HIDE_KEY = 'eliebermann.hiddenLanguages';
    function hiddenLanguages() {
        // ("prop", the old "Hide OE Proper Nouns" button, is no longer offered: a remembered choice is ignored)
        try { return new Set(JSON.parse(localStorage.getItem(HIDE_KEY) || '[]').filter(l => l !== 'prop')); } catch (e) { return new Set(); }
    }
    function setHiddenLanguages(set) {
        try { localStorage.setItem(HIDE_KEY, JSON.stringify([...set])); } catch (e) { /* not remembered */ }
    }
    // An Old English headword that begins with a capital letter (after any
    // bracket or hyphen) is a proper noun: Ine, Cent, [E]aldred, Æðel-.
    // Capitalised by Liebermann but not proper nouns (decided by the editor,
    // October 2026): adjectives of nationality, common nouns built from a
    // name, names of weekdays and months, and two prayers.
    const NOT_PROPER = new Set([
        // adjectives
        'Englisc', 'Denisc', 'Frencisc', 'Fræncisc', 'Wi[e]lisc', 'Wealisc', 'Wilisc', 'Norðmandiscere', 'Cristen',
        // common nouns built from a name
        'Wi[e]liscmonn', 'Wi[e]liscealoð', 'Cristendom', 'Romfeoh', 'Angolwitena',
        // weekdays and months
        'Sunnandæg', 'Sunnanæfen', 'Sunnanniht', 'Tiwesdæg', 'Wodnesdæg', 'Frigedæg', 'Sæternesdæges', 'Lunae',
        'A[u]gust', 'Agust', 'Septembri', 'Iunio', 'Mæge', 'Mai[us]', 'Martige', 'Rugernes',
        // prayers
        'Credo', 'Pater noster'
    ]);

    function isProperNoun(headword, lang) {
        if ((lang || 'ang') !== 'ang') return false;
        if (NOT_PROPER.has(String(headword || '').trim())) return false;
        const first = String(headword || '').replace(/^[\s\[\(\-~]+/, '').charAt(0);
        return first !== '' && first !== first.toLowerCase() && first === first.toUpperCase();
    }

    // "prop" in the hidden set hides proper nouns ("Hide Proper Nouns").
    const isShown = (lang, hidden, headword) => {
        const h = hidden || hiddenLanguages();
        return !h.has(lang || 'ang') && !(h.has('prop') && isProperNoun(headword, lang));
    };

    function properNounBadge() {
        return '<span class="lang-badge prop" title="Proper noun: a name of a person, place, people or day">Proper Noun</span>';
    }

    // The language tag, then "Proper Noun" for an Old English name.
    function languageBadge(lang, headword) {
        const name = LANGUAGES[lang] || lang;
        const text = lang === 'ang' ? 'OE' : name;
        return `<span class="lang-badge ${escapeXml(lang)}" title="${escapeXml(name)}">${escapeXml(text)}</span>` +
            (isProperNoun(headword, lang) ? ' ' + properNounBadge() : '');
    }

    // Language codes for the names the old entry pages used.
    const LANGUAGE_CODES = {
        'Old English': 'ang',
        'Latin': 'la',
        'French': 'fro',
        'Grammatical Term': 'de',
        'Grammatical term': 'de'
    };

    // Characters that don't fold to a plain letter with Unicode normalisation.
    const FOLD = { 'æ': 'ae', 'Æ': 'Ae', 'þ': 'th', 'Þ': 'Th', 'ð': 'd', 'Ð': 'D', 'ƿ': 'w', 'Ƿ': 'W', 'ȝ': 'g', 'Ȝ': 'G', 'ß': 'ss', 'œ': 'oe', 'Œ': 'Oe', '⁊': 'and', 'ꝥ': 'thaet', 'Ꝥ': 'Thaet' };

    /** Headword -> file name, keeping capitals: "æbylgð" -> "aebylgd", "Abkürzungen" -> "Abkurzungen". */
    function slugify(headword, n) {
        let s = String(headword || '').trim().replace(/[æÆþÞðÐƿǷȝȜßœŒ⁊ꝥꝤ]/g, c => FOLD[c]);
        s = s.normalize('NFD').replace(/[̀-ͯ]/g, '');
        s = s.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
        if (n) s += '-' + n;
        return s;
    }

    /** Sort key for headwords: folded and lower-case, so æ sorts as ae. */
    function sortKey(headword) {
        return slugify(headword).toLowerCase();
    }

    // The alphabet of the list: þ (and ð, which Liebermann files with it) is a
    // letter of its own after t, as in the printed Wörterbuch, where Þ runs
    // from p. 216. Headwords that begin with æ are a letter of their own, Æ,
    // after A.
    const ALPHABET = 'AÆBCDEFGHIJKLMNOPQRSTÞUVWXYZ'.split('');
    const THORN = /[þÞðÐ]|[ꝥꝤ]/g;

    /** True when a headword begins with æ (or æ with an accent or macron), ignoring brackets and hyphens before it. */
    function beginsWithAsh(headword) {
        const first = String(headword || '').replace(/^[^\p{L}]+/u, '').normalize('NFD').charAt(0);
        return first === 'æ' || first === 'Æ';
    }

    /** Key for listing headwords in Liebermann's order: æ as ae, þ after every t, and a word that begins with æ after every word that begins with a. */
    function alphaKey(headword) {
        // "~" sorts after every letter, so "t~" comes after "tz" and before "u", and "a~" after "az" and before "b".
        // Accents and macrons come off first, so that ǣ and ǽ are æ.
        const key = String(headword || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[ꝥꝤ]/g, 'þæt').replace(/ł/g, 'l').replace(/Ł/g, 'L').split(THORN)
            .map(part => sortKey(part).replace(/-/g, '')).join('t~');
        return beginsWithAsh(headword) ? key.replace(/^[^a-z]*ae/, 'a~') : key;
    }

    /** The letter of the alphabet a headword is listed under (A–Z, Æ and Þ). */
    function letterOf(headword) {
        const key = alphaKey(headword).replace(/[^a-z~]/g, '');
        if (key.startsWith('t~')) return 'Þ';
        if (key.startsWith('a~')) return 'Æ';
        return /[a-z]/.test(key[0] || '') ? key[0].toUpperCase() : '#';
    }

    function escapeXml(s) {
        return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // A link address from a file, kept only if it is a web or mail address or a
    // path on this site, so a file can't carry a javascript: link.
    function safeUrl(url) {
        const u = String(url || '').trim();
        if (!/^[a-z][a-z0-9+.-]*:/i.test(u.replace(/[\s\u0000-\u001f]/g, ''))) return u;
        return /^(https?|mailto):/i.test(u) ? u : '';
    }

    function useDom(win) { DOM = win; }

    function parseHtml(html) {
        const div = DOM.document.createElement('div');
        div.innerHTML = html || '';
        return div;
    }

    // ------------------------------------------------------------------
    // Linking law codes and abbreviations
    // ------------------------------------------------------------------

    /**
     * Wraps known law codes (markLaw), abbreviations (markforward) and the
     * authors and works Liebermann cites (bibliography) in links. Works on text only, so it never links inside an existing link,
     * never nests links, and leaves the superscript language marker (L, F)
     * at the start of an entry alone.
     */
    function linkAbbreviations(html, markLaw, markforward, bibliography) {
        const terms = [];
        // Sigla marked "Link automatically": "no" (single letters such as L or S, and sigla spelled like a
        // law code, e.g. Wi) are linked by hand only: in running text they are mostly something else.
        (markLaw || []).filter(t => t['Link automatically'] !== 'no')
            .forEach(t => terms.push({ text: t['Gesetze Text'].trim(), anchor: t['Anchor'], type: 'law' }));
        // "Link automatically": "roman only" (the sic mark "!") is not linked in
        // Liebermann's German, where "!" is an ordinary exclamation mark.
        (markforward || []).forEach(t => terms.push({ text: t['Gesetze Text'].trim(), anchor: t['Anchor'], type: 'gram', romanOnly: t['Link automatically'] === 'roman only' }));
        // Authors and works cited (data/bibliography.json). A bare name shared by
        // several works (Sweet, Thorpe) is marked "Link automatically": "no".
        (bibliography || []).filter(t => t['Link automatically'] !== 'no')
            .forEach(t => terms.push({ text: t['Gesetze Text'].trim(), anchor: t['Anchor'], type: 'bib' }));
        const byText = new Map();
        terms.filter(t => t.text).forEach(t => { if (!byText.has(t.text)) byText.set(t.text, t); });
        const sorted = [...byText.values()].sort((a, b) => b.text.length - a.text.length);
        if (!sorted.length) return html;

        // A term that begins and ends with a letter or digit must stand as a
        // word of its own; a sign such as "!" (sic) follows a word directly.
        const makeRegex = list => list.length ? new RegExp('(' + list
            .map(t => {
                const body = t.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+');
                const before = /^[\p{L}\p{N}]/u.test(t.text) ? '(?<![\\p{L}\\p{N}])' : '';
                const after = /[\p{L}\p{N}]$/u.test(t.text) ? '(?![\\p{L}\\p{N}])' : '';
                return before + body + after;
            })
            .join('|') + ')', 'gu') : null;
        // Law codes and manuscript sigla are printed in roman type; italic is
        // Liebermann's German, where "Abt" means abbot, not Æthelberht.
        const allTerms = makeRegex(sorted);
        // Author names are often in italic too.
        const italicTerms = makeRegex(sorted.filter(t => (t.type === 'gram' && !t.romanOnly) || t.type === 'bib'));
        const lookup = text => byText.get(text.replace(/\s+/g, ' '));

        const container = parseHtml(html);
        const languageMarker = findLanguageMarker(container);
        const walker = DOM.document.createTreeWalker(container, DOM.NodeFilter.SHOW_TEXT);
        const textNodes = [];
        while (walker.nextNode()) textNodes.push(walker.currentNode);

        textNodes.forEach(node => {
            if (node.parentElement.closest('a, strong, b, [data-page]')) return;
            if (languageMarker && languageMarker.contains(node)) return;
            const text = node.nodeValue;
            const regex = node.parentElement.closest('em, i') ? italicTerms : allTerms;
            if (!regex) return;
            regex.lastIndex = 0;
            if (!regex.test(text)) return;
            regex.lastIndex = 0;
            const frag = DOM.document.createDocumentFragment();
            let last = 0, m;
            while ((m = regex.exec(text))) {
                const term = lookup(m[1]);
                if (!term) continue;
                if (m.index > last) frag.appendChild(DOM.document.createTextNode(text.slice(last, m.index)));
                const a = DOM.document.createElement('a');
                if (term.type === 'law') {
                    a.setAttribute('href', 'lawAbb.html#' + encodeURIComponent(term.anchor));
                    a.textContent = m[1];
                } else if (term.type === 'bib') {
                    a.setAttribute('href', 'bibAbb.html#' + encodeURIComponent(term.anchor));
                    a.textContent = m[1];
                } else {
                    a.setAttribute('href', 'gramAbb.html#' + encodeURIComponent(term.anchor));
                    const abbr = DOM.document.createElement('abbr');
                    abbr.textContent = m[1];
                    a.appendChild(abbr);
                }
                frag.appendChild(a);
                last = m.index + m[1].length;
            }
            if (last < text.length) frag.appendChild(DOM.document.createTextNode(text.slice(last)));
            node.parentNode.replaceChild(frag, node);
        });
        return container.innerHTML;
    }

    /** The superscript L or F that opens Latin and French entries, if any. */
    function findLanguageMarker(container) {
        const first = container.querySelector('p') || container;
        let el = first.firstChild;
        while (el && el.nodeType === 3 && !el.nodeValue.trim()) el = el.nextSibling;
        if (el && el.nodeType === 1 && el.tagName === 'SUP' && /^\s*[LF]{1,2}\s*$/.test(el.textContent)) return el;
        return null;
    }

    // ------------------------------------------------------------------
    // Reading the form: language and headword
    // ------------------------------------------------------------------

    /** Language code from the formatting of the entry (see docs/SCHEMA.md). */
    function detectLanguage(html) {
        const container = parseHtml(html);
        const marker = findLanguageMarker(container);
        if (marker) return marker.textContent.trim()[0] === 'L' ? 'la' : 'fro';
        const first = (container.querySelector('p') || container).firstElementChild;
        if (first && first.tagName === 'STRONG' && first.firstElementChild && first.firstElementChild.tagName === 'EM') return 'de';
        return 'ang';
    }

    /** Headword and homograph number ("II) abbod ..." -> {headword: "abbod", n: 2}). */
    function detectHeadword(text) {
        let s = String(text || '').replace(/\s+/g, ' ').trim();
        let n = null;
        const hom = s.match(/^(I{1,3}|IV|V)\)\s+/);
        if (hom) {
            n = { I: 1, II: 2, III: 3, IV: 4, V: 5 }[hom[1]];
            s = s.slice(hom[0].length);
        }
        s = s.replace(/^[LF]{1,2}\s+/, '');
        const word = (s.split(' ')[0] || '').replace(/[.,;:]+$/, '');
        return { headword: word, n };
    }

    // ------------------------------------------------------------------
    // HTML (from the editor) -> TEI
    // ------------------------------------------------------------------

    /** Inline HTML -> TEI. Paragraph breaks become <lb/>. */
    function inlineToTei(container, opts) {
        opts = opts || {};
        const marker = opts.languageMarker ? findLanguageMarker(container) : null;
        let out = '';
        let firstBlock = true;

        function walk(node) {
            if (node.nodeType === 3) {
                out += escapeXml(node.nodeValue.replace(/ /g, ' ').replace(/[‎‏]/g, ''));
                return;
            }
            if (node.nodeType !== 1) return;
            if (node === marker) {
                out += '<lbl type="language">' + escapeXml(node.textContent.trim()) + '</lbl> ';
                return;
            }
            const tag = node.tagName;
            const kids = () => node.childNodes.forEach(walk);
            switch (tag) {
                case 'P': case 'DIV':
                    if (!firstBlock && out.trim()) out += '<lb/>';
                    firstBlock = false;
                    kids();
                    break;
                case 'BR':
                    // Quill marks an empty paragraph with a lone <br>.
                    if (node.parentNode.childNodes.length > 1) out += '<lb/>';
                    break;
                case 'STRONG': case 'B': wrap('<hi rend="bold">', '</hi>'); break;
                case 'EM': case 'I': wrap('<hi rend="italic">', '</hi>'); break;
                case 'SUP': wrap('<hi rend="superscript">', '</hi>'); break;
                case 'SUB': wrap('<hi rend="subscript">', '</hi>'); break;
                case 'ABBR': wrap('<abbr>', '</abbr>'); break;
                case 'A': link(); break;
                case 'SPAN':
                    if (node.getAttribute('data-page')) out += '<pb n="' + escapeXml(node.getAttribute('data-page')) + '"/>';
                    else kids();
                    break;
                default: kids();
            }

            function wrap(open, close) {
                const before = out.length;
                out += open;
                kids();
                if (out.length === before + open.length) out = out.slice(0, before); // drop empty
                else out += close;
            }

            function link() {
                const href = node.getAttribute('href') || '';
                let m;
                if ((m = href.match(/lawAbb\.html#(.+)$/))) {
                    out += '<ref type="lawCode" target="law:' + escapeXml(decodeURIComponent(m[1])) + '">';
                    flat(); out += '</ref>';
                } else if ((m = href.match(/bibAbb\.html#(.+)$/))) {
                    out += '<ref type="bibl" target="bib:' + escapeXml(decodeURIComponent(m[1])) + '">';
                    flat(); out += '</ref>';
                } else if ((m = href.match(/gramAbb\.html#(.+)$/))) {
                    out += '<ref type="abbreviation" target="gram:' + escapeXml(decodeURIComponent(m[1])) + '"><abbr>';
                    out += escapeXml(node.textContent.replace(/ /g, ' ').trim()) + '</abbr></ref>';
                } else if (/^https?:/.test(href)) {
                    out += '<ref target="' + escapeXml(href) + '">'; flat(); out += '</ref>';
                } else {
                    kids();
                }
            }

            // Inside a link, keep formatting but drop any nested links.
            function flat() {
                node.childNodes.forEach(function inner(n) {
                    if (n.nodeType === 1 && n.tagName === 'A') { n.childNodes.forEach(inner); return; }
                    walk(n);
                });
            }
        }

        container.childNodes.forEach(walk);
        return out.replace(/(<lb\/>\s*)+$/, '').replace(/\s+/g, ' ').trim();
    }

    /** True when the editor holds nothing but empty paragraphs. */
    function isEmptyHtml(html) {
        return !parseHtml(html).textContent.replace(/ /g, ' ').trim();
    }

    /** A definition: one <def>, or numbered <sense>s when it is a list. */
    function sensesToTei(html, indent) {
        if (isEmptyHtml(html)) return '';
        const container = parseHtml(html);
        const items = [...container.querySelectorAll('li')].filter(li => li.textContent.trim());
        if (items.length) {
            return items.map((li, i) => `${indent}<sense n="${i + 1}">\n${indent}  <def>${inlineToTei(li)}</def>\n${indent}</sense>`).join('\n');
        }
        return `${indent}<def>${inlineToTei(container)}</def>`;
    }

    // ------------------------------------------------------------------
    // Law code citations: "Af 41. 43 B" in Liebermann's text -> Af 41, Af 43 B
    // ------------------------------------------------------------------

    // Manuscripts and versions (Quadripartitus, Instituta Cnuti…). After a
    // passage they name the reading cited (Af 41 B); they are not codes, and
    // they are left out of the citation list.
    const SIGLA = new Set(['MsA', 'B', 'Bu', 'C', 'D', 'E', 'F', 'G', 'G2', 'H', 'Hk', 'I', 'K', 'Ld', 'O', 'Ot',
        'So', 'Vt', 'Io', 'Isp', 'Quadr', 'InCn', 'ConsCn', 'WlEdmr', 'Wb', 'LatVersion']);
    // "L" after a passage (msAbb: LatVersion) is the Latin version Liebermann prints
    // beside the text. Where the laws database has that version as a text of its
    // own, the citation goes to it: "VI Atr 2 L" is VI Atr Lat 2.
    const LATIN_VERSION = { VIAtr: { of: 'VI Atr', anchor: 'VIAtrLat', label: 'VI Atr Lat' } };
    // Parts of a code: Af El 49 (Introduction), Af Rb 41 (rubric).
    const QUALIFIERS = new Set(['El', 'Rb', 'retr']);
    // A passage: 41, 2,1, 70,21a, Insc., Prol., or a line (Zeile) of a text
    // Liebermann numbers by lines, such as Nor grið Z. 6.
    const PASSAGE = String.raw`(?:\d+[a-z]{0,2}(?:,\d+[a-z]{0,2})*|Inscr?\.?|Prol?\.?|Epil\.?|Z\.\s?\d+)`;

    /**
     * The law code passages cited in an entry's TEI text (the inside of
     * <dictScrap>), in order and without repeats: [{ text: 'Af 41 B', anchor: 'Af' }].
     * Follows Liebermann's style, where "II Cn 13,1. 77,1" is two passages of
     * II Cnut. A number that isn't straight after a code (after a word, a
     * semicolon or a bar) is left out, since it can't be told apart reliably.
     */
    function extractCitations(teiText) {
        const unescape = t => t.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
        // Law code refs become \u0001anchor\u0002label\u0003; superscripts
        // (footnotes, variants) and line or page breaks become a stop (\u0004).
        const flat = String(teiText || '')
            .replace(/<hi rend="superscript">[\s\S]*?<\/hi>/g, '\u0004')
            .replace(/<(lb|pb)\b[^>]*\/>/g, ' ')
            .replace(/<ref type="lawCode" target="law:([^"]*)">([\s\S]*?)<\/ref>/g, (m, a, l) => `\u0001${a}\u0002${l.replace(/<[^>]*>/g, '')}\u0003`)
            .replace(/<[^>]*>/g, '');
        const out = [], seen = new Set();
        let lastNew = -1;   // where the last citation went in out, if it was new there
        scanCitations(unescape(flat), (text, anchor, start, end, replaces) => {
            if (replaces && lastNew >= 0) { out[lastNew] = { text, anchor }; seen.add(text); return; }
            lastNew = -1;
            if (!seen.has(text)) { seen.add(text); lastNew = out.push({ text, anchor }) - 1; }
        });
        return out;
    }

    /**
     * The rules of extractCitations(), on text already flattened (law code
     * refs as \u0001anchor\u0002label\u0003, stops as \u0004). Calls
     * found(text, anchor, start, end) for every passage, repeats included;
     * start and end are where its number stands in the flat text.
     */
    function scanCitations(flat, found) {
        // A bracket with no number in it, such as a manuscript reading
        // ("Af 5,4 (geänd. aus noman H). 43 B"), does not end a run of
        // citations: it is read as spaces, so "43" is still Af 43. (Its
        // manuscript letter would otherwise stop the run.) The text keeps its
        // length, so the positions passed to found() stay right.
        // A bracket that cites a law code ("(mide- I Cn Pro)") is kept.
        flat = flat.replace(/\([^()\d]*\)/g, m => {
            const codes = [...m.matchAll(/\u0001([^\u0002]*)\u0002/g)].map(c => c[1]);
            return codes.every(a => SIGLA.has(a)) ? ' '.repeat(m.length) : m;
        });
        let code = null, last = null, open = false;   // open: only spaces since the last passage
        const add = (text, start, end) => {
            last = { text: text.replace(/\s+/g, ' ').trim(), anchor: code.anchor, start, end };
            found(last.text, last.anchor, start, end);
        };
        const passages = (text, pos) => {
            let rest = text, at = pos, m;
            // The passage follows after a space (Af 41) or, for Liebermann's "Cn 1020,11"
            // and "Iud Dei X,17", straight after a comma.
            if (code && (m = new RegExp(`^(\\s+|,(?=\\d))(${PASSAGE})(?![\\p{L}\\d])(?<!(?:^|[^\\d,])\\d{1,2}[a-z]?(?=\\)))`, 'u').exec(rest)) && (!last || !open || last.anchor !== code.anchor || code.fresh)) {
                const n = m[2].replace(/\.$/, ''), s = at + m[1].length;
                add(code.label + (m[1] === ',' ? ',' : ' ') + n, s, s + n.length);
                rest = rest.slice(m[0].length); at += m[0].length; code.fresh = false;
            } else if (code && code.fresh && !/^\s*$/.test(rest)) {
                code = null;   // a code with no passage after it, e.g. "VI As" in a sentence
            }
            for (;;) {
                while (code && last && (m = new RegExp(`^(?:\\s*\\([^()]*\\))?\\s*\\.?\\s+(${PASSAGE})(?![\\p{L}\\d])(?<!(?:^|[^\\d,])\\d{1,2}[a-z]?(?=\\)))`, 'u').exec(rest))) {
                    const n = m[1].replace(/\.$/, ''), s = at + m[0].length - m[1].length;
                    // after a line ("Z. 6. 9"), a bare number is another line
                    const line = /^\d+$/.test(n) && / Z\. ?\d+$/.test(last.text) ? 'Z. ' : '';
                    add(code.label + ' ' + line + n, s, s + n.length);
                    rest = rest.slice(m[0].length); at += m[0].length;
                }
                // Liebermann's "58,1; 2" is 58,1 and 58,2: after a clause with a comma, a
                // semicolon and a bare number name another subsection of the same clause.
                const sub = code && last && last.anchor === code.anchor && /^(.* )(\d+[a-z]{0,2}),\d+[a-z]{0,2}$/.exec(last.text);
                if (sub && (m = /^(\s*;\s*)(\d+[a-z]{0,2})(?![\p{L}\d,)])(?=\.?\s*(?:$|[.;|‖=(\[\u0001\u0004\d]|ff?\.))/u.exec(rest))) {
                    const n = m[2], s = at + m[1].length;
                    add(sub[1] + sub[2] + ',' + n, s, s + n.length);
                    rest = rest.slice(m[0].length); at += m[0].length;
                    continue;
                }
                break;
            }
            open = !!last && !(code && code.fresh) && /^\s*$/.test(rest);
            if (!open && !(code && code.fresh)) code = code && /^[\s.]*$/.test(rest) ? code : null;
        };
        const re = /\u0001([^\u0002]*)\u0002([^\u0003]*)\u0003/g;
        let m = re.exec(flat);
        passages(m ? flat.slice(0, m.index) : flat, 0);
        while (m) {
            const anchor = m[1];
            // A code Liebermann gives by its numeral alone ("III Atr 3,2. IV 1",
            // linked to IVAtr by tools/series-citations.py) is written out in
            // full in the list: "IV Atr", "Iud Dei VII", "VIIa Atr".
            let label = m[2].trim();
            if (/^(?:VIIa|[IVX]+)$/.test(label) && anchor !== label) {
                label = anchor.replace(/([a-z])([A-Z])/g, '$1 $2');
                // "VIAtr" -> "VI Atr"; "VIIa Atr" already has its space (not "VI Ia Atr")
                if (!/\s/.test(label)) label = label.replace(/^(VIIa|[IVX]+)(?=[A-Z][a-z])/, '$1 ');
            }
            // "Quadr Ded 11. Arg 3": a part of the Quadripartitus named alone is listed in full
            if (anchor === 'Quadr' + label) label = 'Quadr ' + label;
            const pos = m.index + m[0].length;
            const next = re.exec(flat);
            const text = flat.slice(pos, next ? next.index : flat.length);
            m = next;
            if (anchor === 'LatVersion' && code && code.fresh) {
                // "VI Atr L 3,1. 4", "Leis Wl L 21,3": L before the numbers, so they
                // are passages of the Latin version (for VI Atr, VI Atr Lat 3,1).
                const lv = LATIN_VERSION[code.anchor];
                if (lv && code.label === lv.of) code = { anchor: lv.anchor, label: lv.label, fresh: true };
                passages(text.replace(/^:/, ' '), pos);
                continue;
            }
            if (SIGLA.has(anchor)) {
                // "Af 41 B": the reading of manuscript B. The citation list names the
                // passage (Af 41), not the manuscript, so the letter is not added to it.
                const attached = open && last && !/^\s*:/.test(text);
                if (anchor === 'ConsCn' || anchor === 'Quadr' && /^\s*:/.test(text) || anchor === 'InCn' && /^\s*:/.test(text)) code = null;
                // "VI Atr 2 L": the citation just found is the Latin version's (VI Atr Lat 2);
                // found() is told it replaces the one before (fifth argument).
                const latin = anchor === 'LatVersion' && attached && LATIN_VERSION[last.anchor];
                if (latin && last.text.startsWith(latin.of + ' ')) {
                    last = { text: latin.label + last.text.slice(latin.of.length), anchor: latin.anchor, start: last.start, end: last.end };
                    found(last.text, last.anchor, last.start, last.end, true);
                }
                // keep the run going so "Af 41 B. 43" still reads as Af 43
                open = attached && /^\s*$/.test(text);
                if (code && last && /^\.\s+\d/.test(text)) { passages(text, pos); } else if (!/^\s*$/.test(text)) { code = code && /^[\s.]*$/.test(text) ? code : null; }
                continue;
            }
            if (QUALIFIERS.has(anchor)) {
                if (code && (code.fresh || open)) { code = { anchor: code.anchor, label: code.label + ' ' + label, fresh: true }; last = null; }
                passages(text, pos);
                continue;
            }
            code = { anchor, label, fresh: true };
            passages(text, pos);
        }
    }

    /**
     * Links the clause numbers in an entry as shown on its page: in "Ine 8",
     * "Ine" stays the link to the law code (with its popup) and "8" becomes a
     * link to the clause. The passages are found by the same rules as the
     * citation list under the entry, and a number is linked only when that
     * list has a clause for it: clauses is { 'Ine 8': 'law.html?id=Ine_8' }.
     */
    function linkClauseNumbers(container, clauses) {
        if (!container || !clauses || !Object.keys(clauses).length) return 0;
        const isCode = el => el.localName === 'a' && /(?:lawAbb|msAbb)\.html#/.test(el.getAttribute('href') || '');
        // The text as extractCitations() sees it, with where each character came from.
        let flat = '';
        const from = [];   // from[i] = [textNode, offset] or null
        const put = (str, node, offset) => {
            for (let i = 0; i < str.length; i++) { flat += str[i]; from.push(node ? [node, offset + i] : null); }
        };
        const walk = node => {
            node.childNodes.forEach(n => {
                if (n.nodeType === 3) return put(n.nodeValue, n, 0);
                if (n.nodeType !== 1) return;
                if (isCode(n)) {
                    let anchor = '';
                    try { anchor = decodeURIComponent(n.getAttribute('href').split('#')[1] || ''); } catch (e) { /* keep '' */ }
                    return put('\u0001' + anchor + '\u0002' + n.textContent + '\u0003', null, 0);
                }
                if (n.localName === 'a') return put(n.textContent, null, 0);
                if (n.localName === 'sup' && !n.classList.contains('lang-marker')) return put('\u0004', null, 0);
                if (n.localName === 'br' || n.classList.contains('pb')) return put(' ', null, 0);
                // A paragraph ends a citation: without the break, "II As 20,5"
                // at the end of one sense ran into the next sense's "2)" and
                // was read as 20,52.
                const block = /^(p|div|li|ol|ul)$/.test(n.localName);
                if (block) put(' ', null, 0);
                walk(n);
                if (block) put(' ', null, 0);
            });
        };
        walk(container);
        const hits = [];
        scanCitations(flat, (text, anchor, start, end, replaces) => {
            // a citation that replaces the one just found (VI Atr 2 L): drop that one's link
            if (replaces && hits.length && hits[hits.length - 1].text !== text && hits[hits.length - 1].flatStart === start) hits.pop();
            const href = clauses[text];
            // "Z. 6" (line 6): "Z." keeps its own link; the number is linked.
            if (/^Z\./.test(flat.slice(start, end))) start += flat.slice(start, end).search(/\d/);
            const a = from[start], b = from[end - 1];
            if (href && a && b && a[0] === b[0]) hits.push({ node: a[0], start: a[1], end: b[1] + 1, href, text, flatStart: start });
        });
        // Wrap from the last to the first, so earlier offsets stay right.
        hits.reverse().forEach(h => {
            const tail = h.node.splitText(h.start);
            tail.splitText(h.end - h.start);
            const link = container.ownerDocument.createElement('a');
            link.className = 'ref-clause';
            link.href = h.href;
            link.title = h.text + ' in the laws database';
            tail.parentNode.replaceChild(link, tail);
            link.appendChild(tail);
        });
        return hits.length;
    }

    /**
     * Splits markup at Liebermann's numbered meanings: a bold number followed
     * by ")", such as <hi rend="bold">2</hi>) in TEI or <strong>2</strong>)
     * in HTML. Only numbers outside any other element count. Returns
     * { head, senses: [{ n, body }] }: head is the text before the first
     * number (the headword and its forms), and each body runs from after the
     * ")" to the next number, without the marker. No numbers: senses is [].
     */
    function splitSenses(markup, html) {
        const text = String(markup || '');
        const marker = html ? /<(strong|b)>(\d+[a-z]?)<\/\1>\)/g : /<hi rend="bold">(\d+[a-z]?)<\/hi>\)/g;
        const cuts = [];
        let m;
        while ((m = marker.exec(text))) {
            const before = text.slice(0, m.index);
            const opened = (before.replace(/<(br|hr|img|wbr|input)\b[^>]*>/gi, '').match(/<[A-Za-z][^>]*[^/]>|<[A-Za-z]>/g) || []).length;
            const closed = (before.match(/<\/[^>]+>/g) || []).length;
            if (opened === closed) cuts.push({ at: m.index, end: m.index + m[0].length, n: html ? m[2] : m[1] });
        }
        if (!cuts.length) return { head: text, senses: [] };
        return {
            head: text.slice(0, cuts[0].at),
            senses: cuts.map((c, i) => ({ n: c.n, body: text.slice(c.end, i + 1 < cuts.length ? cuts[i + 1].at : text.length) }))
        };
    }

    /**
     * Splits an entry's HTML into Liebermann's outline. He divides an entry
     * with bold markers followed by ")": capital letters A), B); Roman
     * numerals I), II); numbers 1), 2); small letters a), b). Their order
     * varies from entry to entry (A) above I) in Gleitlaut, I) above A) in
     * mid), so each kind of marker takes the depth at which it first
     * appears, and returning to a kind closes the deeper ones.
     * Returns { head, parts: [{ marker, kind, depth, body }] }. Markers
     * inside another element, and a Roman numeral before the headword (it
     * numbers words spelled alike), stay in the text. I, V and X count as
     * capital letters only when they continue a run of letters (H) then I)).
     */
    function splitOutline(html) {
        const text = String(html || '');
        const marker = /<(strong|b)>([^<]{1,5})<\/\1>\)/g;
        const cuts = [];
        let lastUpper = '';
        let m;
        while ((m = marker.exec(text))) {
            const before = text.slice(0, m.index);
            const opened = (before.replace(/<(br|hr|img|wbr|input)\b[^>]*>/gi, '').match(/<[A-Za-z][^>]*[^/]>|<[A-Za-z]>/g) || []).length;
            const closed = (before.match(/<\/[^>]+>/g) || []).length;
            if (opened !== closed) continue;
            const v = m[2];
            let kind = '';
            if (/^\d+[a-z]?$/.test(v)) kind = 'number';
            else if (/^[IVX]+$/.test(v) && !(v.length === 1 && lastUpper && String.fromCharCode(lastUpper.charCodeAt(0) + 1) === v)) kind = 'roman';
            else if (/^[A-Z]$/.test(v)) kind = 'upper';
            else if (/^[a-z]$/.test(v)) kind = 'lower';
            if (!kind) continue;
            if (kind === 'upper') lastUpper = v;
            // A Roman numeral with nothing but a language label before it
            // numbers the headword (I) lac, II) lac).
            if (kind === 'roman' && !before.replace(/<[^>]+>/g, '').replace(/^\s*[LF]?\s*$/, '').trim()) continue;
            cuts.push({ at: m.index, end: m.index + m[0].length, marker: v, kind });
        }
        if (!cuts.length) return { head: text, parts: [] };
        // A coarser kind never goes below finer ones only: Wi[e]lisc lists
        // meanings a)–d) and then I) adj, II) sbst, which are not inside d).
        const rank = { upper: 0, roman: 1, number: 2, lower: 3 };
        const stack = [];
        const parts = cuts.map((c, i) => {
            let depth = stack.indexOf(c.kind);
            if (depth === -1 && stack.length && stack.every(k => rank[k] > rank[c.kind])) stack.length = 0;
            if (depth === -1) { stack.push(c.kind); depth = stack.length - 1; }
            else stack.length = depth + 1;
            return { marker: c.marker, kind: c.kind, depth, body: text.slice(c.end, i + 1 < cuts.length ? cuts[i + 1].at : text.length) };
        });
        return { head: text.slice(0, cuts[0].at), parts };
    }

    /** The numbered meanings of an entry's TEI text as a <dictScrap type="senses">, or ''. */
    function sensesXml(entryTei, indent) {
        const { senses } = splitSenses(entryTei);
        if (!senses.length) return '';
        const pad = indent || '        ';
        return `<dictScrap type="senses">\n${senses.map(s => `${pad}  <sense n="${s.n}">${s.body.trim()}</sense>`).join('\n')}\n${pad}</dictScrap>`;
    }

    /**
     * The law code citation list for an entry: every passage cited in its
     * text, linked to the code on the law code list, followed by any
     * citations added by hand ([{text, url}]) that aren't already in it.
     * Returns <xr type="lawCode"> elements, one per citation.
     */
    function citationXr(entryTei, extra) {
        const found = extractCitations(entryTei);
        const have = new Set(found.map(c => c.text));
        const xr = found.map(c => `<xr type="lawCode"><ref target="law:${escapeXml(c.anchor)}">${escapeXml(c.text)}</ref></xr>`);
        (extra || []).filter(l => l.text || l.url).forEach(l => {
            const text = (l.text || l.url).replace(/\s+/g, ' ').trim();
            if (!l.url && have.has(text)) return;
            have.add(text);
            xr.push(`<xr type="lawCode"><ref${l.url ? ` target="${escapeXml(l.url)}"` : ''}>${escapeXml(text)}</ref></xr>`);
        });
        return xr;
    }

    /**
     * Builds an entry as a TEI document.
     * data: { headword, n, lang, page, facsimile, entryHtml, definitionHtml,
     *         translationHtml, seeAlso: [{text, slug}], compare: [{text, slug}], links: {bt, doe,
     *         wiktionary, lawCode: [{text, url}]}, change: {when, text},
     *         earlierChanges: [{when, text}], xref, spelling }
     * editorNotes: editorial notes kept as they are, each a TEI string
     * '<note type="editorial">…</note>'.
     * spelling: true for a spelling entry (a letter or letters, not a word),
     * written as <usg type="dom">spelling</usg>.
     * xref: true for a cross-reference entry (one that only points to another
     * headword), written as <entry type="xref">.
     */
    function buildEntryXml(data) {
        const slug = data.slug || slugify(data.headword, data.n);
        const lang = data.lang || 'ang';
        const entryTei = inlineToTei(parseHtml(data.entryHtml), { languageMarker: true });
        const numbered = sensesXml(entryTei);
        const definition = sensesToTei(data.definitionHtml, '          ');
        const translation = sensesToTei(data.translationHtml, '          ');
        const today = new Date().toISOString().slice(0, 10);
        const changes = (data.earlierChanges || []).concat([data.change || { when: today, text: 'Created with the contribution form.' }]);

        const xr = [];
        (data.seeAlso || []).filter(s => s.text).forEach(s => {
            xr.push(`<xr type="see"><ref target="entry:${escapeXml(s.slug || slugify(s.text))}">${escapeXml(s.text)}</ref></xr>`);
        });
        // Liebermann's "vgl." (compare): the headwords named after it
        (data.compare || []).filter(s => s.text).forEach(s => {
            xr.push(`<xr type="compare"><ref target="entry:${escapeXml(s.slug || slugify(s.text))}">${escapeXml(s.text)}</ref></xr>`);
        });
        const linkTypes = [['bt', 'bosworthToller'], ['doe', 'doe'], ['wiktionary', 'wiktionary']];
        linkTypes.forEach(([key, type]) => {
            ((data.links || {})[key] || []).filter(l => l.text || l.url).forEach(l => {
                const target = l.url ? ` target="${escapeXml(l.url)}"` : '';
                xr.push(`<xr type="${type}"><ref${target}>${escapeXml(l.text || l.url)}</ref></xr>`);
            });
        });
        xr.push(...citationXr(entryTei, (data.links || {}).lawCode));

        const page = data.page ? `<biblScope unit="page">${escapeXml(data.page)}</biblScope>` : '';
        const facs = data.facsimile ? `\n            <ptr type="facsimile" target="${escapeXml(data.facsimile)}"/>` : '';
        const entryAttrs = (data.xref ? ' type="xref"' : lang === 'de' ? ' type="grammatical"' : '') + (data.n ? ` n="${data.n}"` : '');

        return `<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title>${escapeXml(data.headword)}</title>
      </titleStmt>
      <publicationStmt>
        <publisher>eLiebermann: An Online Dictionary of Pre-Conquest English Law</publisher>
        <idno type="slug">${escapeXml(slug)}</idno>
      </publicationStmt>
      <sourceDesc>
        <bibl>
          <author>Felix Liebermann</author>, <title>Die Gesetze der Angelsachsen</title>, <biblScope unit="volume">2.1</biblScope> (Wörterbuch)${page ? ', ' + page : ''}${facs}
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
${changes.map(c => `      <change when="${escapeXml(c.when)}">${escapeXml(c.text)}</change>`).join('\n')}
    </revisionDesc>
  </teiHeader>
  <text>
    <body>
      <entry xml:lang="${lang}"${entryAttrs}>
        <form type="lemma">
          <orth>${escapeXml(data.headword)}</orth>
        </form>${data.spelling ? `
        <usg type="dom">spelling</usg>` : ''}
        <dictScrap type="liebermann">${entryTei}</dictScrap>${numbered ? `
        ${numbered}` : ''}${(data.editorNotes || []).map(n => '\n        ' + n).join('')}${definition ? `
        <sense type="liebermann" xml:lang="de">
${definition}
        </sense>` : ''}${translation ? `
        <sense type="translation" xml:lang="en">
${translation}
        </sense>` : ''}${xr.map(x => '\n        ' + x).join('')}
      </entry>
    </body>
  </text>
</TEI>
`;
    }

    // ------------------------------------------------------------------
    // TEI -> HTML
    // ------------------------------------------------------------------

    /**
     * Renders a TEI element's content as HTML.
     * root: path from the current page to the site root ("" or "../").
     */
    function renderTei(el, root) {
        root = root || '';
        let out = '';
        el.childNodes.forEach(node => { out += renderNode(node, root); });
        return out;
    }

    function resolveTarget(target, root) {
        if (!target) return '';
        const m = target.match(/^(law|gram|bib|entry|clause):(.+)$/);
        if (m) {
            if (m[1] === 'law') return root + 'lawAbb.html#' + encodeURIComponent(m[2]);
            if (m[1] === 'gram') return root + 'gramAbb.html#' + encodeURIComponent(m[2]);
            if (m[1] === 'bib') return root + 'bibAbb.html#' + encodeURIComponent(m[2]);
            if (m[1] === 'clause') return root + 'law.html?id=' + encodeURIComponent(m[2]);
            return root + 'entry.html?id=' + encodeURIComponent(m[2]);
        }
        return safeUrl(target);
    }

    function renderNode(node, root) {
        if (node.nodeType === 3) return escapeXml(node.nodeValue);
        if (node.nodeType !== 1) return '';
        const name = node.localName;
        const inner = () => renderTei(node, root);
        const attr = a => node.getAttribute(a) || '';
        switch (name) {
            case 'hi': {
                const rend = attr('rend');
                if (rend === 'bold') return '<strong>' + inner() + '</strong>';
                if (rend === 'italic') return '<em>' + inner() + '</em>';
                if (rend === 'superscript') {
                    // A raised number after a citation ("Hn 29,4³⁹") is the number of
                    // Liebermann's footnote at that passage in vol. I, usually a manuscript reading.
                    const n = node.textContent.trim();
                    // But a raised number followed by "/" and a lowered one is a
                    // fraction (¹/₁₀ = one tenth), not a footnote.
                    const next = node.nextSibling;
                    const after = next && next.nextSibling;
                    if (next && next.nodeType === 3 && next.nodeValue === '/' && after && after.nodeType === 1
                        && after.localName === 'hi' && after.getAttribute('rend') === 'subscript') {
                        return `<sup class="frac" title="the fraction ${n}/${after.textContent.trim()}">` + inner() + '</sup>';
                    }
                    if (/^\d+$/.test(n)) return `<sup class="fn-ref" title="Liebermann’s footnote ${n} at this passage in vol. I, where he discusses the manuscript readings">` + inner() + '</sup>';
                    return '<sup>' + inner() + '</sup>';
                }
                if (rend === 'subscript') return '<sub>' + inner() + '</sub>';
                return '<span>' + inner() + '</span>';
            }
            case 'lbl':
                if (attr('type') === 'language') {
                    const label = { L: 'Latin', F: 'French', LF: 'Latin and French', FL: 'French and Latin' }[node.textContent.trim()] || 'French';
                    return `<sup class="lang-marker" title="${label}"><strong>${inner()}</strong></sup>`;
                }
                return '<span class="lbl">' + inner() + '</span>';
            case 'ref': {
                const target = resolveTarget(attr('target'), root);
                if (!target) return '<span class="ref">' + inner() + '</span>';
                const ext = /^https?:/.test(target) ? ' target="_blank" rel="noopener"' : '';
                const cls = attr('type') ? ` class="ref-${escapeXml(attr('type'))}"` : '';
                return `<a href="${escapeXml(target)}"${cls}${ext}>${inner()}</a>`;
            }
            case 'ptr': {
                const target = resolveTarget(attr('target'), root);
                return `<a href="${escapeXml(target)}" target="_blank" rel="noopener">${escapeXml(target)}</a>`;
            }
            case 'abbr': return '<abbr>' + inner() + '</abbr>';
            case 'lb': return '<br>';
            case 'pb': return `<span class="pb" title="Page ${escapeXml(attr('n'))} of the printed volume">[p. ${escapeXml(attr('n'))}]</span>`;
            case 'p': return '<p>' + inner() + '</p>';
            // <head rend="sub"> is a subheading within a section (site pages).
            case 'head': return attr('rend') === 'sub' ? '<h3>' + inner() + '</h3>' : '<h2>' + inner() + '</h2>';
            case 'list': {
                const tag = attr('rend') === 'numbered' ? 'ol' : 'ul';
                return `<${tag}>` + inner() + `</${tag}>`;
            }
            case 'item': return '<li>' + inner() + '</li>';
            case 'title': return '<cite>' + inner() + '</cite>';
            case 'quote': return '<q>' + inner() + '</q>';
            case 'div': return '<section>' + inner() + '</section>';
            case 'foreign': return `<i lang="${escapeXml(node.getAttribute('xml:lang') || '')}">` + inner() + '</i>';
            default: return inner();
        }
    }

    // ------------------------------------------------------------------
    // Reading entries
    // ------------------------------------------------------------------

    function first(doc, name) {
        return doc.getElementsByTagNameNS(TEI_NS, name)[0] || null;
    }

    function childrenNamed(el, name) {
        return [...el.children].filter(c => c.localName === name);
    }

    /** The main fields of an entry, for lists and entry pages. */
    function readEntry(doc) {
        const entry = first(doc, 'entry');
        if (!entry) return null;
        const orth = first(entry, 'orth');
        const lang = entry.getAttribute('xml:lang') || 'ang';
        const senses = childrenNamed(entry, 'sense');
        const definition = senses.find(s => s.getAttribute('type') === 'liebermann') || null;
        const translation = senses.find(s => s.getAttribute('type') === 'translation') || null;
        const idno = first(doc, 'idno');
        const scope = [...doc.getElementsByTagNameNS(TEI_NS, 'biblScope')].find(b => b.getAttribute('unit') === 'page');
        const facs = [...doc.getElementsByTagNameNS(TEI_NS, 'ptr')].find(p => p.getAttribute('type') === 'facsimile');
        const changes = [...doc.getElementsByTagNameNS(TEI_NS, 'change')];
        return {
            headword: orth ? orth.textContent.trim() : '',
            n: entry.getAttribute('n') || '',
            // A cross-reference entry: it only points to another headword.
            xref: entry.getAttribute('type') === 'xref',
            // A spelling entry: a letter or letters, not a word (<usg type="dom">spelling</usg>).
            spelling: childrenNamed(entry, 'usg').some(u => u.getAttribute('type') === 'dom' && u.textContent.trim() === 'spelling'),
            // Notes by the eLiebermann editors (<note type="editorial">), e.g. where Liebermann's pointer needs correcting.
            editorNotes: childrenNamed(entry, 'note').filter(n => n.getAttribute('type') === 'editorial'),
            slug: idno ? idno.textContent.trim() : '',
            lang,
            language: LANGUAGES[lang] || lang,
            entry,
            original: childrenNamed(entry, 'dictScrap').find(d => d.getAttribute('type') !== 'senses') || null,
            definition,
            translation,
            xr: childrenNamed(entry, 'xr'),
            page: scope ? scope.textContent.trim() : '',
            facsimile: facs ? facs.getAttribute('target') : '',
            changes: changes.map(c => ({ when: c.getAttribute('when') || '', text: c.textContent.trim() })),
            // (the English translation, if any, is kept in the file but not shown)
            gloss: definition ? definition.textContent.replace(/\s+/g, ' ').trim() : ''
        };
    }

    /**
     * Loads the law codes (data/markLaw.json), manuscript sigla
     * (data/manuscripts.json), abbreviations (data/markforward.json) and works
     * cited (data/bibliography.json) for linkAbbreviations(), once per page.
     * Resolves to { markLaw, markforward, bibliography }; a file that can't be read gives [].
     */
    let abbreviations = null;
    function loadAbbreviations(root) {
        const get = file => fetch((root || '') + 'data/' + file)
            .then(r => { if (!r.ok) throw new Error(file + ': ' + r.status); return r.json(); })
            .catch(err => { console.error(err); return []; });
        if (!abbreviations) {
            // Manuscript sigla (data/manuscripts.json) are linked like law codes,
            // so they are added to markLaw here.
            abbreviations = Promise.all([get('markLaw.json'), get('manuscripts.json'), get('markforward.json'), get('bibliography.json')])
                .then(([markLaw, manuscripts, markforward, bibliography]) => ({ markLaw: markLaw.concat(manuscripts), markforward, bibliography }));
        }
        return abbreviations;
    }

    const api = {
        TEI_NS, LANGUAGES, LANGUAGE_CODES, languageBadge, properNounBadge, isProperNoun, hiddenLanguages, setHiddenLanguages, isShown,
        useDom, slugify, sortKey, alphaKey, letterOf, ALPHABET, escapeXml, safeUrl,
        linkAbbreviations, loadAbbreviations, extractCitations, linkClauseNumbers, citationXr, splitSenses, splitOutline, sensesXml, detectLanguage, detectHeadword,
        inlineToTei, isEmptyHtml, buildEntryXml,
        renderTei, resolveTarget, readEntry
    };

    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.ELieb = api;
})(this);
