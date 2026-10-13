/*
 * eLiebermann: law code popups on entry pages.
 *
 * Every law code or manuscript siglum in an entry is a link to its heading on
 * the law code list (lawAbb.html#Abt). This script turns a click on one of
 * those links into a small popup that shows what the code stands for, taken
 * from data/markLaw.json: the German expansion and the English translation.
 *
 * - Click or tap opens the popup and keeps it open; Esc, the × button, or a
 *   click elsewhere closes it. Enter on a focused link does the same.
 * - On a computer, resting the pointer on a code previews the popup.
 * - Ctrl, Cmd, Shift or middle-click still follow the link as usual.
 * - If the data can't be loaded, or a code isn't in it, the link simply
 *   goes to the law code list as it did before.
 *
 * The text comes from markLaw.json and is only ever inserted as text, never
 * as HTML.
 */
(function () {
    'use strict';

    const LINK = 'a[href*="lawAbb.html#"]';
    const HOVER_DELAY = 220;   // ms of rest before a hover preview opens
    const LEAVE_DELAY = 280;   // ms before a hover preview closes

    let groups = null;         // anchor -> rows of data/markLaw.json
    let loading = null;
    let popup = null;
    let active = null;         // the link the popup belongs to
    let pinned = false;        // opened by click: stays until dismissed
    let showTimer = 0;
    let hideTimer = 0;

    const norm = s => String(s == null ? '' : s).replace(/\s+/g, ' ').trim();
    const root = () => window.SITE_ROOT || '';
    const canHover = () => window.matchMedia && window.matchMedia('(hover: hover)').matches;

    function load() {
        if (!loading) {
            loading = fetch(root() + 'data/markLaw.json')
                .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
                .then(rows => {
                    groups = {};
                    rows.forEach(row => { (groups[row.Anchor] = groups[row.Anchor] || []).push(row); });
                    return groups;
                })
                .catch(err => { console.error('Law code popups: ' + err); groups = {}; return groups; });
        }
        return loading;
    }

    function anchorOf(link) {
        const hash = (link.getAttribute('href') || '').split('#')[1];
        try { return decodeURIComponent(hash || ''); } catch (e) { return ''; }
    }

    /** The row for this link: the spelling printed in the entry if the group
     *  has it (Q and Quadr share an anchor), otherwise the first row. */
    function rowFor(link) {
        const rows = groups && groups[anchorOf(link)];
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

    function build(link, row) {
        const printed = norm(link.textContent) || norm(row['Gesetze Text']);
        const box = element('div', 'law-popup');
        box.setAttribute('role', 'dialog');
        box.setAttribute('aria-label', 'Law code ' + printed);
        box.tabIndex = -1;

        const close = element('button', 'law-popup-close', '×');
        close.type = 'button';
        close.setAttribute('aria-label', 'Close');
        close.addEventListener('click', () => hide(true));
        box.appendChild(close);

        box.appendChild(element('p', 'law-popup-code', printed));

        const list = element('dl');
        const german = norm(row['German Expansion']);
        const english = norm(row['English Translation']);
        if (german) {
            list.appendChild(element('dt', null, 'German'));
            const dd = element('dd', null, german);
            dd.lang = 'de';
            list.appendChild(dd);
        }
        if (english) {
            list.appendChild(element('dt', null, 'English'));
            const dd = element('dd', null, english);
            dd.lang = 'en';
            list.appendChild(dd);
        }
        box.appendChild(list);

        const more = element('a', 'law-popup-more', 'Full list of law codes');
        more.href = root() + 'lawAbb.html#' + encodeURIComponent(anchorOf(link));
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

        load().then(() => {
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
            load().then(() => {
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
})();
