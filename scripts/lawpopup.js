/*
 * eLiebermann: abbreviation popups on entry pages.
 *
 * Every law code, manuscript siglum and grammatical abbreviation in an entry
 * is a link to its heading on a list: the law code list (lawAbb.html#Abt,
 * which also takes manuscript sigla such as lawAbb.html#H and sends them on to
 * msAbb.html), the grammatical abbreviations (gramAbb.html#Plural) or the
 * authors and works Liebermann cites (bibAbb.html#CitToller). This
 * script turns a click on one of those links into a small popup that shows
 * what it stands for, taken from data/markLaw.json, data/manuscripts.json,
 * data/markforward.json or data/bibliography.json: the German
 * expansion and the English translation, and for a grammatical abbreviation
 * its note, if it has one.
 *
 * - Click or tap opens the popup and keeps it open; Esc, the × button, or a
 *   click elsewhere closes it. Enter on a focused link does the same.
 * - On a computer, resting the pointer on a code previews the popup.
 * - Ctrl, Cmd, Shift or middle-click still follow the link as usual.
 * - If the data can't be loaded, or an abbreviation isn't in it, the link
 *   simply goes to its list as it did before.
 *
 * The text comes from the two data files and is only ever inserted as text,
 * never as HTML.
 */
(function () {
    'use strict';

    const LINK = 'a[href*="lawAbb.html#"], a[href*="msAbb.html#"], a[href*="gramAbb.html#"], a[href*="bibAbb.html#"]';
    // The two lists: where the data is, and what the popup calls things.
    const KINDS = {
        law: { file: 'data/markLaw.json', list: 'lawAbb.html', noun: 'Law code', more: 'Full list of law codes' },
        // Manuscript sigla are linked to lawAbb.html like law codes (lawAbb.html
        // sends them on to msAbb.html); their data is in a file of their own.
        ms: { file: 'data/manuscripts.json', list: 'msAbb.html', noun: 'Manuscript', more: 'Full list of manuscripts' },
        gram: { file: 'data/markforward.json', list: 'gramAbb.html', noun: 'Abbreviation', more: 'Full list of grammatical abbreviations' },
        bib: { file: 'data/bibliography.json', list: 'bibAbb.html', noun: 'Work cited', more: 'Full list of authors and works cited' }
    };
    const HOVER_DELAY = 220;   // ms of rest before a hover preview opens
    const LEAVE_DELAY = 280;   // ms before a hover preview closes

    const groups = {};         // kind -> anchor -> rows of that kind's data file
    const loading = {};
    let popup = null;
    let active = null;         // the link the popup belongs to
    let pinned = false;        // opened by click: stays until dismissed
    let showTimer = 0;
    let hideTimer = 0;

    const norm = s => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
    const root = () => window.SITE_ROOT || '';
    const canHover = () => window.matchMedia && window.matchMedia('(hover: hover)').matches;

    // 'gram', 'law' or 'ms'. A link to lawAbb.html is a manuscript if its
    // anchor is in data/manuscripts.json (known once that file has loaded).
    const kindOf = link => {
        const href = link.getAttribute('href') || '';
        if (href.indexOf('gramAbb.html#') >= 0) return 'gram';
        if (href.indexOf('bibAbb.html#') >= 0) return 'bib';
        if (href.indexOf('msAbb.html#') >= 0) return 'ms';
        return groups.ms && groups.ms[anchorOf(link)] ? 'ms' : 'law';
    };

    function load(kind) {
        if (!loading[kind]) {
            loading[kind] = fetch(root() + KINDS[kind].file)
                .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
                .then(rows => {
                    groups[kind] = {};
                    rows.forEach(row => { (groups[kind][row.Anchor] = groups[kind][row.Anchor] || []).push(row); });
                    return groups[kind];
                })
                .catch(err => { console.error('Abbreviation popups: ' + err); groups[kind] = {}; return groups[kind]; });
        }
        return loading[kind];
    }

    // Loads what a link needs: for a law code link, the manuscripts too, since
    // manuscript sigla are linked to the law code list.
    function ready(link) {
        const href = link.getAttribute('href') || '';
        if (href.indexOf('gramAbb.html#') >= 0) return load('gram');
        if (href.indexOf('bibAbb.html#') >= 0) return load('bib');
        return Promise.all([load('ms'), load('law')]);
    }

    function anchorOf(link) {
        const hash = (link.getAttribute('href') || '').split('#')[1];
        try { return decodeURIComponent(hash || ''); } catch (e) { return ''; }
    }

    /** The row for this link: the spelling printed in the entry if the group
     *  has it (Q and Quadr share an anchor), otherwise the first row. */
    function rowFor(link) {
        const kind = kindOf(link);
        const rows = groups[kind] && groups[kind][anchorOf(link)];
        if (!rows || !rows.length) return null;
        const printed = norm(link.textContent);
        return rows.find(r => norm(r['Gesetze Text']) === printed) || rows[0];
    }

    // ------------------------------------------------------------------
    // The popup
    // ------------------------------------------------------------------

    function element(tag, className, text) {
        const el = document.createElement(tag);
        if (className) el.className = className;
        if (text != null) el.textContent = text;
        return el;
    }

    // Text with <i>…</i> marking titles: the italics become <i> elements,
    // everything else stays text (never inserted as HTML).
    function withItalics(el, text) {
        String(text == null ? '' : text).split(/(<i>[\s\S]*?<\/i>)/).forEach(part => {
            const m = part.match(/^<i>([\s\S]*)<\/i>$/);
            if (m) el.appendChild(element('i', null, m[1]));
            else if (part) el.appendChild(document.createTextNode(part));
        });
        return el;
    }

    function build(link, row) {
        const printed = norm(link.textContent) || norm(row['Gesetze Text']);
        const box = element('div', 'law-popup law-popup--' + kindOf(link));
        box.setAttribute('role', 'dialog');
        const kind = KINDS[kindOf(link)];
        box.setAttribute('aria-label', kind.noun + ' ' + printed);
        box.tabIndex = -1;

        const close = element('button', 'law-popup-close', '×');
        close.type = 'button';
        close.setAttribute('aria-label', 'Close');
        close.addEventListener('click', () => hide(true));
        box.appendChild(close);

        box.appendChild(element('p', 'law-popup-code', printed));

        const list = element('dl');
        if (kindOf(link) === 'bib') {
            // A work cited: its full citation, with titles in italics.
            list.appendChild(element('dt', null, 'Full citation'));
            list.appendChild(withItalics(element('dd'), row['Full Citation']));
            const bibNote = norm(row['Notes']);
            if (bibNote) {
                list.appendChild(element('dt', null, 'Note'));
                list.appendChild(withItalics(element('dd', 'law-popup-note'), bibNote));
            }
            box.appendChild(list);
            const moreBib = element('a', 'law-popup-more', kind.more);
            moreBib.href = root() + kind.list + '#' + encodeURIComponent(anchorOf(link));
            box.appendChild(moreBib);
            box.addEventListener('mouseenter', () => clearTimeout(hideTimer));
            box.addEventListener('mouseleave', () => { if (!pinned) scheduleHide(); });
            return box;
        }
        const german = norm(row['German Expansion']);
        const english = norm(row['English Translation']);
        if (german) {
            list.appendChild(element('dt', null, 'German'));
            const dd = element('dd', null, german);
            dd.lang = 'de';
            // Liebermann's spelling first; the modern one underneath where it differs.
            const modern = norm(row['Modern German'] || '');
            if (modern) dd.appendChild(element('span', 'modern-german', 'today: ' + modern));
            list.appendChild(dd);
        }
        if (english) {
            list.appendChild(element('dt', null, 'English'));
            const dd = element('dd', null, english);
            dd.lang = 'en';
            list.appendChild(dd);
        }
        // A note belongs to the abbreviation, not to one spelling of it.
        const siblings = (groups[kindOf(link)] || {})[anchorOf(link)] || [];
        const note = norm(row['Notes: Grammatical'] || (siblings.find(r => r['Notes: Grammatical']) || {})['Notes: Grammatical']);
        if (note) {
            list.appendChild(element('dt', null, 'Note'));
            list.appendChild(element('dd', 'law-popup-note', note));
        }
        box.appendChild(list);

        const more = element('a', 'law-popup-more', kind.more);
        more.href = root() + kind.list + '#' + encodeURIComponent(anchorOf(link));
        box.appendChild(more);

        box.addEventListener('mouseenter', () => clearTimeout(hideTimer));
        box.addEventListener('mouseleave', () => { if (!pinned) scheduleHide(); });
        return box;
    }

    function place() {
        if (!popup || !active) return;
        const rects = active.getClientRects();
        const r = rects.length ? rects[0] : active.getBoundingClientRect();
        const margin = 12;
        const viewWidth = document.documentElement.clientWidth;

        popup.classList.remove('above');
        popup.style.left = '0px';
        popup.style.top = '0px';
        const w = popup.offsetWidth;
        const h = popup.offsetHeight;

        const left = Math.max(window.scrollX + margin,
            Math.min(r.left + window.scrollX, window.scrollX + viewWidth - w - margin));
        const above = window.innerHeight - r.bottom < h + 16 && r.top > h + 16;
        const top = above ? r.top + window.scrollY - h - 10 : r.bottom + window.scrollY + 10;

        popup.classList.toggle('above', above);
        popup.style.left = left + 'px';
        popup.style.top = top + 'px';
        const middle = r.left + r.width / 2 + window.scrollX - left;
        popup.style.setProperty('--caret', Math.max(16, Math.min(middle, w - 16)) + 'px');
    }

    function show(link, row, keepFocus) {
        hide(false);
        active = link;
        popup = build(link, row);
        document.body.appendChild(popup);
        link.classList.add('law-active');
        link.setAttribute('aria-expanded', 'true');
        place();
        if (keepFocus) popup.focus({ preventScroll: true });
    }

    function hide(returnFocus) {
        clearTimeout(showTimer);
        clearTimeout(hideTimer);
        if (!popup) return;
        const link = active;
        const hadFocus = popup.contains(document.activeElement);
        popup.remove();
        popup = null;
        active = null;
        pinned = false;
        if (link) {
            link.classList.remove('law-active');
            link.removeAttribute('aria-expanded');
            if (returnFocus && hadFocus) link.focus({ preventScroll: true });
        }
    }

    function scheduleHide() {
        clearTimeout(hideTimer);
        hideTimer = setTimeout(() => { if (!pinned) hide(false); }, LEAVE_DELAY);
    }

    // ------------------------------------------------------------------
    // Events (delegated, so they cover entries drawn after the page loads)
    // ------------------------------------------------------------------

    function lawLink(target) {
        const link = target && target.closest ? target.closest(LINK) : null;
        return link && !link.closest('.law-popup') ? link : null;
    }

    document.addEventListener('click', event => {
        const link = lawLink(event.target);
        if (!link) {
            if (popup && !popup.contains(event.target)) hide(false);
            return;
        }
        if (event.defaultPrevented || event.button !== 0 ||
            event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;

        event.preventDefault();
        const byKeyboard = event.detail === 0;
        if (popup && active === link && pinned) { hide(true); return; }

        ready(link).then(() => {
            const row = rowFor(link);
            if (!row) { window.location.href = link.href; return; }
            show(link, row, byKeyboard);
            pinned = true;
        });
    });

    document.addEventListener('mouseover', event => {
        if (!canHover()) return;
        const link = lawLink(event.target);
        if (!link || (popup && active === link)) { if (link) clearTimeout(hideTimer); return; }
        if (pinned) return;
        clearTimeout(hideTimer);
        clearTimeout(showTimer);
        showTimer = setTimeout(() => {
            ready(link).then(() => {
                const row = rowFor(link);
                if (row && link.matches(':hover') && !pinned) show(link, row, false);
            });
        }, HOVER_DELAY);
    });

    document.addEventListener('mouseout', event => {
        const link = lawLink(event.target);
        if (!link || link.contains(event.relatedTarget)) return;
        clearTimeout(showTimer);
        if (popup && active === link && !pinned) scheduleHide();
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && popup) hide(true);
    });

    window.addEventListener('resize', place);

    // ------------------------------------------------------------------
    // Manuscript sigla look different from law codes
    // ------------------------------------------------------------------
    // Entries link a manuscript siglum to the law code list (lawAbb.html#H).
    // Once the list of manuscripts has loaded, such links are pointed at the
    // manuscripts list instead and given the class ref-manuscript, so they
    // can have their own colour (style.css). Entries are drawn after the page
    // loads, so links added later are marked too.
    function markManuscripts(scope) {
        if (!groups.ms) return;
        (scope || document).querySelectorAll('a[href*="lawAbb.html#"]').forEach(a => {
            const anchor = anchorOf(a);
            if (!groups.ms[anchor]) return;
            a.classList.remove('ref-lawCode');
            a.classList.add('ref-manuscript');
            a.setAttribute('href', a.getAttribute('href').replace('lawAbb.html#', 'msAbb.html#'));
        });
    }
    load('ms').then(() => {
        markManuscripts();
        if (window.MutationObserver) {
            new MutationObserver(records => {
                if (records.some(r => r.addedNodes.length)) markManuscripts();
            }).observe(document.documentElement, { childList: true, subtree: true });
        }
    });
})();
