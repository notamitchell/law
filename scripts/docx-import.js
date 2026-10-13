/*
 * eLiebermann: split a Word document of Liebermann's dictionary into entries.
 *
 * DocxImport.parse(documentXml) reads word/document.xml (from inside the
 * .docx) and returns one object per entry:
 *   { headword, lang, page, html, warnings: [] }
 * where html is the entry's text with <strong>, <em>, <sup> and <sub>, ready
 * for ELieb.linkAbbreviations() and ELieb.buildEntryXml().
 *
 * How the document is read (see docs/IMPORT.md):
 * - A paragraph that is only a number ("1.", "2") is a page number of the
 *   printed book; the paragraph after it is the running head ("Abetot – Accent").
 * - A paragraph that is only a capital letter ("A", "B.") is a letter heading.
 * - A paragraph starts a new entry when its first bold text comes before any
 *   other text, apart from the L or F language marker and a few unbolded
 *   words ("ut aberste", "[-abeden]").
 * - Any other paragraph continues the entry before it; a page break inside
 *   an entry is kept as a page marker.
 */
(function (root) {
    'use strict';

    const W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main';
    let DOM = typeof window !== 'undefined' ? window : null;

    function useDom(win) { DOM = win; }

    function esc(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function isOn(rPr, name) {
        if (!rPr) return false;
        const el = [...rPr.children].find(c => c.localName === name);
        if (!el) return false;
        const v = el.getAttributeNS(W, 'val') || el.getAttribute('w:val');
        return v !== '0' && v !== 'false' && v !== 'none';
    }

    function vertAlign(rPr) {
        if (!rPr) return '';
        const el = [...rPr.children].find(c => c.localName === 'vertAlign');
        return el ? (el.getAttributeNS(W, 'val') || el.getAttribute('w:val') || '') : '';
    }

    /** A paragraph as a list of runs: { text, b, i, sup, sub }. Adjacent runs with the same formatting are merged. */
    function readRuns(p) {
        const runs = [];
        const rs = p.getElementsByTagNameNS(W, 'r');
        for (let k = 0; k < rs.length; k++) {
            const r = rs[k];
            const rPr = [...r.children].find(c => c.localName === 'rPr') || null;
            let text = '';
            [...r.children].forEach(c => {
                if (c.localName === 't') text += c.textContent;
                else if (c.localName === 'tab') text += '\t';
                else if (c.localName === 'br') text += ' ';
            });
            text = text.replace(/[‎‏]/g, '');
            if (!text) continue;
            const va = vertAlign(rPr);
            let run = { text, b: isOn(rPr, 'b'), i: isOn(rPr, 'i'), sup: va === 'superscript', sub: va === 'subscript' };
            // Formatting on spaces alone means nothing; it only splits words.
            if (!text.trim()) run = { text, b: false, i: false, sup: false, sub: false, space: true };
            const prev = runs[runs.length - 1];
            if (prev && !run.space && !prev.space && prev.b === run.b && prev.i === run.i && prev.sup === run.sup && prev.sub === run.sub) {
                prev.text += run.text;
            } else if (prev && run.space && prev.space) {
                prev.text += run.text;
            } else {
                runs.push(run);
            }
        }
        return runs;
    }

    function runsToHtml(runs) {
        return runs.map(r => {
            let t = esc(r.text.replace(/\t/g, ' '));
            if (r.space) return t;
            if (r.i) t = '<em>' + t + '</em>';
            if (r.b) t = '<strong>' + t + '</strong>';
            if (r.sup) t = '<sup>' + t + '</sup>';
            if (r.sub) t = '<sub>' + t + '</sub>';
            return t;
        }).join('');
    }

    const plain = runs => runs.map(r => r.text).join('');

    /**
     * Does this paragraph start a new entry? Returns { headword, lang } or null.
     */
    function entryStart(runs) {
        let k = 0;
        let lang = 'ang';
        // Language marker: superscript L or F.
        if (runs[k] && runs[k].sup && /^\s*[LF]\s*$/.test(runs[k].text)) {
            lang = runs[k].text.trim() === 'L' ? 'la' : 'fro';
            k++;
            while (runs[k] && (runs[k].space || (runs[k].sup && !runs[k].text.trim()))) k++;
        }
        // A few unbolded words may come before the headword ("ut aberste", "[-abeden]").
        let prefix = '';
        while (runs[k] && !runs[k].b) {
            prefix += runs[k].text;
            k++;
        }
        if (!runs[k]) return null;
        // Allowed before the headword: lower-case words ("ut", "s." for sanctus), brackets and hyphens, not in italics.
        if (prefix.trim() && (prefix.trim().length > 20 || !/^[\p{Ll}\s\[\]().\-]+$/u.test(prefix))) return null;
        if (runs.slice(0, k).some(r => r.i && r.text.trim())) return null;
        // The headword: the first bold text (several bold pieces may be split
        // by spaces), widened to the whole word it sits in, so "[-abeden]",
        // "(-)æ-" and "a<b>gyten</b>" keep their brackets, hyphens and letters.
        let j = k;
        while (runs[j] && (runs[j].b || (runs[j].space && runs[j + 1] && runs[j + 1].b))) j++;
        const before = prefix;
        const bold = plain(runs.slice(k, j));
        const after = plain(runs.slice(j));
        const left = (before.match(/\S*$/) || [''])[0];
        const right = /^\S/.test(after) && !/\s$/.test(bold) ? (after.match(/^\S*/) || [''])[0] : '';
        // A bold sense number on its own ("3) gerichtlich…") continues an entry.
        if (/^\s*(\d+|[IVX]+|[a-z])\s*$/.test(bold) && after.startsWith(')')) return null;
        let headword = (left + bold + right).replace(/\s+/g, ' ').trim();
        // "bernet, berning" or "adp-, adqu-": the first form is the headword.
        headword = headword.split(/,\s/)[0];
        // "abrecan 1)": drop a sense number that follows the headword.
        headword = headword.replace(/\s+(\d+|[IVX]+|[A-Za-z])\)?$/, '');
        headword = headword.replace(/[,;:.]+$/, '').trim();
        if (!headword || /^[\d|]/.test(headword)) return null;
        if (runs[k].b && runs[k].i) lang = 'de';
        const joined = /\p{L}$/u.test(left);
        return { headword, lang, prefix: prefix.trim(), joined };
    }

    function parse(documentXml) {
        const doc = new DOM.DOMParser().parseFromString(documentXml, 'application/xml');
        const body = doc.getElementsByTagNameNS(W, 'body')[0];
        const paras = [...body.getElementsByTagNameNS(W, 'p')];
        const entries = [];
        const skipped = [];
        let page = null;
        let pageChanged = false;
        let expectRunningHead = false;

        paras.forEach((p, index) => {
            const runs = readRuns(p);
            const text = plain(runs).replace(/\s+/g, ' ').trim();
            if (!text) return;

            // Page number, sometimes with the running head in the same paragraph.
            const pm = text.match(/^(\d+)\.?(?:\s+(.+\s[–-]\s.+))?$/);
            // A running head is short; a long paragraph that only begins with a number
            // ("48. II Cn 5,1; …") is text, not a page number.
            if (pm && (!pm[2] || pm[2].length < 80) && runs.every(r => r.b || r.space || !r.text.trim() || pm[2])) {
                page = parseInt(pm[1], 10);
                pageChanged = true;
                expectRunningHead = !pm[2];
                return;
            }
            if (expectRunningHead) {
                expectRunningHead = false;
                if (/\s[–-]\s/.test(text) && text.length < 80) return;
            }
            // Letter heading.
            if (/^[A-ZÆÞ]\.?$/.test(text)) { pageChanged = false; return; }

            const start = entryStart(runs);
            if (start) {
                entries.push({
                    headword: start.headword,
                    lang: start.lang,
                    page,
                    html: '<p>' + runsToHtml(runs).trim() + '</p>',
                    warnings: start.joined ? ['Bold starts mid-word: check the headword'] : [],
                    paragraph: index
                });
                pageChanged = false;
                return;
            }

            // Continuation of the previous entry.
            const last = entries[entries.length - 1];
            if (!last) { skipped.push({ paragraph: index, text }); return; }
            const marker = pageChanged ? '<span data-page="' + page + '"></span>' : '';
            last.html = last.html.replace(/<\/p>$/, ' ' + marker + runsToHtml(runs).trim() + '</p>');
            last.continued = true;
            pageChanged = false;
        });

        // "~gatio" after "abnegare" is "abnegatio": ~ stands for the start of
        // the headword before, up to where the new ending joins it.
        entries.forEach((e, i) => {
            const prev = entries[i - 1];
            const m = e.headword.match(/^~(\p{L}+)$/u);
            if (!m || !prev) return;
            const join = prev.headword.lastIndexOf(m[1].slice(0, 2));
            if (join > 0) {
                e.warnings.push(`Headword written as ${e.headword} after ${prev.headword}: check that it is ${prev.headword.slice(0, join) + m[1]}`);
                e.headword = prev.headword.slice(0, join) + m[1];
            }
        });

        // Checks an editor should look at.
        entries.forEach(e => {
            if (e.headword.includes('~')) e.warnings.push('Headword uses ~ (shortened form of the entry before)');
            if (e.headword.length > 25) e.warnings.push('Long headword: check where it ends');
            if (e.page == null) e.warnings.push('No page number found');
        });
        return { entries, skipped };
    }

    /**
     * Gives each entry its file name and cross-references.
     * - slug: ELieb.slugify(headword); a file name that is already taken in
     *   this document gets -2, -3…, plain headwords first, then in document
     *   order.
     * - exists: true when entries/<slug>.xml is already on the site
     *   (existingSlugs), so the import can leave it alone.
     * - seeAlso: for entries that are only a pointer ("abere s. æbære"), the
     *   entry pointed to, when it is in this document or on the site.
     */
    const isPlain = e => (/[\[\]()~]|^-|-$/.test(e.headword) ? 0 : 1);

    function prepare(entries, existingSlugs, ELieb) {
        const existing = new Set(existingSlugs || []);
        const counts = {};
        // Plain headwords get the plain file name before affixes and bracketed
        // forms that fold to the same name ("a" before "-a-", "a-", "[a]").
        const plainFirst = [...entries].sort((x, y) => isPlain(y) - isPlain(x));
        plainFirst.forEach(e => {
            const base = ELieb.slugify(e.headword) || 'entry';
            counts[base] = (counts[base] || 0) + 1;
            e.slug = counts[base] > 1 ? base + '-' + counts[base] : base;
            e.exists = existing.has(e.slug);
        });
        const known = new Map();
        entries.forEach(e => { if (!known.has(e.headword)) known.set(e.headword, e.slug); });
        (existingSlugs || []).forEach(slug => { if (!known.has(slug)) known.set(slug, slug); });
        entries.forEach(e => {
            const div = DOM.document.createElement('div');
            div.innerHTML = e.html;
            const text = div.textContent.replace(/\s+/g, ' ').trim();
            const m = text.match(/^(?:[LF] )?\S.*?\ss\.\s+([^\s~,;]+?)\.?$/);
            e.seeAlso = [];
            if (m && text.length < 60 && known.has(m[1]) && known.get(m[1]) !== e.slug) e.seeAlso.push({ text: m[1], slug: known.get(m[1]) });
        });
        return entries;
    }

    const api = { useDom, parse, prepare, readRuns, entryStart };
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.DocxImport = api;
})(this);
