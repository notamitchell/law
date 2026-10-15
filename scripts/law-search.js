/*
 * Laws page: reading a search for a law code and clause.
 *
 * A reader can type the law code as Liebermann abbreviates it ("Af 5", "II Cn 30,1"), by its
 * name ("Alfred 5", "II Cnut 30.1", "2 Cnut 30", "Cnut II 30", "Aethelred", "Grately"), with
 * a or ae for æ and th for þ and ð, and with small misspellings ("Alfrd", "Ethelbert").
 * A comma, a colon or a full stop in a clause number all mean the same (Liebermann's 23,2 is 23.2).
 *
 *   const s = LawSearch.build(codes);         // codes: oe-laws/codes.json
 *   s.read('Alfred 5')  -> { codes: ['Af'], clause: '5', exact: true }  (or null: not a law code)
 *   LawSearch.clauseKeys(clauseRow)           -> ['5'], ['el49.1'], ['1a'], ['prol', 'prol1'] …
 *   LawSearch.clauseMatches(keys, '5')        -> true for 5, 5.1, 5a; not for 50
 *
 * Works in the browser (window.LawSearch) and in Node (require).
 */
(function (root) {
    'use strict';

    // Plain lower-case letters for comparing: æ and ae both as a (so Æthelred, Aethelred and
    // Athelred are the same; Ethel- too), þ and ð as th, ⁊ as and, accents and apostrophes removed.
    // In a clause number a comma or colon between digits is a full stop; other punctuation is a space.
    function loose(s) {
        s = String(s || '').toLowerCase()
            .replace(/[æǣǽ]/g, 'ae').replace(/[þð]/g, 'th').replace(/⁊/g, ' and ')
            .replace(/['’‘`]/g, '')
            .normalize('NFD').replace(/[̀-ͯ]/g, '')
            .replace(/ae/g, 'a').replace(/\bethel/g, 'athel')
            .replace(/(\d)\s*[,:]\s*(?=\d)/g, '$1.')
            .replace(/[^a-z0-9.]+/g, ' ')
            .replace(/\.(?!\d)|(^|[^0-9])\./g, '$1 ');
        return s.replace(/\s+/g, ' ').trim();
    }

    const STOP = new Set(['and', 'of', 'the', 'to', 'in', 'on', 'for', 's']);
    const tokens = s => loose(s).split(' ').filter(t => t && !STOP.has(t));
    const ROMAN = { i: 1, ii: 2, iii: 3, iv: 4, v: 5, vi: 6, vii: 7, viia: '7a', viii: 8, ix: 9, x: 10 };
    // Clause words, in the forms Liebermann and the database use.
    const WORDS = [[/^(prologue|prolog|prol|pr)$/, 'prol'], [/^(inscriptio|inscr|insc)$/, 'inscr'], [/^(epilogue|epilog|epil)$/, 'epil'],
                   [/^(rubrics|rubric|rubr|rb)$/, 'rubr'], [/^(einl|el)$/, 'el']];
    const word = t => { for (const [re, w] of WORDS) if (re.test(t)) return w; return t; };

    function lev(a, b) {
        if (Math.abs(a.length - b.length) > 2) return 3;
        let prev = Array.from({ length: b.length + 1 }, (_, i) => i);
        for (let i = 1; i <= a.length; i++) {
            const cur = [i];
            for (let j = 1; j <= b.length; j++)
                cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
            prev = cur;
        }
        return prev[b.length];
    }
    // Two words are the same if equal, or (for names of five letters or more) one or two letters apart.
    function same(a, b) {
        if (a === b) return true;
        if (/th/.test(a + b) && a.replace(/th/g, 'd') === b.replace(/th/g, 'd')) return true;   // Grið as Grid
        if (!/^[a-z]+$/.test(a) || !/^[a-z]+$/.test(b) || Math.min(a.length, b.length) < 5) return false;
        return lev(a, b) <= (Math.min(a.length, b.length) >= 8 ? 2 : 1);
    }

    // The ways a law code may be named: its abbreviation, its name, the king's name with the
    // code's number before or after it, the place in its name, other spellings of the king.
    function names(c) {
        const out = new Set();
        const add = s => { const t = tokens(s); if (t.length) out.add(t.join(' ')); };
        const withNumber = s => {          // "II Æthelstan" -> also "2 Æthelstan", "Æthelstan II"
            add(s);
            const m = loose(s).match(/^(i|ii|iii|iv|v|vi|vii|viia|viii|ix|x) (.+)$/);
            if (m) { add(ROMAN[m[1]] + ' ' + m[2]); add(m[2] + ' ' + m[1]); }
        };
        withNumber(c.code);
        if (c.anchor) add(c.anchor);
        const name = String(c.name || '');
        const main = name.replace(/\s*\(([^)]*)\)/g, '').trim();
        withNumber(main);
        main.split(/:\s*/).forEach(add);                                  // "William I: London Charter"
        add(main.replace(/[’']s\b/g, '').replace(/\b(code|laws|law|letter|ordinance)\b/gi, ''));
        add(main.replace(/^(the\s+)?(treaty|laws|code)\s+(of\s+)?/i, ''));                // "Alfred and Guthrum"
        (name.match(/\(([^)]*)\)/g) || []).forEach(p => {                  // "(Grately)", "(I Edgar)"
            p = p.slice(1, -1);
            if (!/^in /i.test(p)) withNumber(p);
        });
        const year = name.match(/\b(10\d\d)\b/);                           // "Cnut 1018"
        if (year && c.king) add(c.king + ' ' + year[1]);
        // "Alfred's Domboc", "Ine's Laws", "Hlothhere and Eadric's Code" can be called "Alfred", "Ine", "Hlothhere".
        const own = main.match(/^(.+?)[’']s (code|laws|domboc)$/i);
        if (own) { add(own[1]); add(own[1].split(/ and /)[0]); }
        // Other spellings: Canute and Knut for Cnut; William and Henry for Wl and Hn.
        [...out].forEach(n => {
            if (/\bcnut\b/.test(n)) { out.add(n.replace(/\bcnut\b/, 'canute')); out.add(n.replace(/\bcnut\b/, 'knut')); }
            if (/\bwl\b/.test(n)) out.add(n.replace(/\bwl\b/, 'william'));
            if (/\bhn\b/.test(n)) out.add(n.replace(/\bhn\b/, 'henry'));
        });
        return [...out].map(n => n.split(' '));
    }

    // Does the start of the query name this code? 'exact': all of the name's words were typed,
    // and `used` query words are the code; 'partial': the query stops part-way through the name.
    function readName(q, n) {
        for (let i = 0; i < n.length; i++) {
            if (i >= q.length) return { kind: 'partial', used: q.length };
            if (same(q[i], n[i])) continue;
            if (i === q.length - 1 && n[i].startsWith(q[i]) && /[a-z]/.test(q[i])) return { kind: 'partial', used: q.length };
            return null;
        }
        return { kind: 'exact', used: n.length };
    }

    // A clause number as the database writes it, or as a reader types it, in one form:
    // "El. 49,1" -> "el49.1", "1[a]" -> "1a", "Prolog." -> "prol", "Prologue 2" -> "prol2".
    function clauseKey(s) {
        return loose(String(s || '').replace(/\[([a-z])\]/gi, '$1').replace(/\[[^\]]*\]/g, ''))
            .split(' ').filter(Boolean).map(word).join('').replace(/\.$/, '');
    }
    const CLAUSE = /^(prol|inscr|epil|rubr|el)?(\d+[a-z]?(\.\d+[a-z]?)*)?$/;

    // The keys a clause row can be found by ("Rect 3, 3.1, 3.2" by each number).
    function clauseKeys(c) {
        let s = String(c.clause || '').trim();
        if (c.code && s.toLowerCase().startsWith(c.code.toLowerCase() + ' ')) s = s.slice(c.code.length + 1);  // "Ine Prol.", "Iudex 1"
        s = s.replace(/^(\d+(?:\.\d+)*)\s*[-–]\s*\d.*$/, '$1');                                              // "12-12.2"
        const parts = s.split(/,\s+|,(?=\s*\d)/).map(p => p.trim()).filter(Boolean);
        const keys = new Set([clauseKey(s)]);
        const lead = parts.length > 1 && /^[a-z]/i.test(parts[0]) && !/\d/.test(parts[0]) ? clauseKey(parts[0]) : '';
        parts.forEach(p => { keys.add(clauseKey(p)); if (lead && /^\d/.test(p)) keys.add(lead + clauseKey(p)); });
        keys.delete('');
        return [...keys];
    }
    // "5" finds 5, 5.1, 5a, but not 50; "prol" finds every prologue clause.
    const clauseMatches = (keys, want) => !want || keys.some(k =>
        (k.startsWith(want) && (k.length === want.length || !/\d/.test(k[want.length]))) ||
        (/^(prol|inscr|epil)$/.test(want) && k.includes(want)));        // "Alfred Prol" finds Af El. Prol.

    function build(codes) {
        const all = codes.map(c => ({ code: c.code, names: names(c) }));

        // The law code(s) and clause a query names, or null when it names none.
        function read(query) {
            const q = loose(query).split(' ').filter(t => t && !STOP.has(t));
            if (!q.length) return null;
            let best = [], bestScore = -1;
            all.forEach(c => {
                let mine = -1;
                c.names.forEach(n => {
                    const r = readName(q, n);
                    if (!r) return;
                    const rest = clauseKey(q.slice(r.used).join(' '));
                    if (!CLAUSE.test(rest)) return;
                    // exact names first, longer names before shorter ones, a clause number fully read
                    const score = (r.kind === 'exact' ? 1000 : 0) + r.used * 10;
                    if (score > mine) { mine = score; c._rest = rest; c._kind = r.kind; }
                });
                if (mine < 0) return;
                if (mine > bestScore) { best = [c]; bestScore = mine; } else if (mine === bestScore) best.push(c);
            });
            if (!best.length) return null;
            return { codes: best.map(c => c.code), clause: best[0]._kind === 'exact' ? best[0]._rest : '', exact: best[0]._kind === 'exact' };
        }
        return { read };
    }

    const api = { build, loose, clauseKey, clauseKeys, clauseMatches };
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.LawSearch = api;
})(typeof window !== 'undefined' ? window : this);
