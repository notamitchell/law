/* Headword suggestions as you type, for any search box with data-suggest.
 * Reads data/entries.json (written by tools/build-index.js on deploy) once,
 * the first time a box is used. Matching folds æ to ae, þ to th and so on,
 * so "aeb" finds æbære. Headwords that start with what was typed come first.
 * Needs scripts/eliebermann.js. */
(function () {
    const MAX = 8;
    let loading = null;

    const fold = s => ELieb.sortKey(s).replace(/-/g, '');

    function load(root) {
        if (!loading) {
            loading = fetch(root + 'data/entries.json')
                .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
                .then(list => list.map(e => Object.assign({ key: fold(e.hw) }, e)))
                .catch(() => []);
        }
        return loading;
    }

    function match(entries, typed) {
        const term = fold(typed);
        if (!term) return [];
        const starts = [], contains = [];
        const hidden = ELieb.hiddenLanguages();
        for (const e of entries) {
            if (!ELieb.isShown(e.lang, hidden, e.hw)) continue;
            const i = e.key.indexOf(term);
            if (i === 0) starts.push(e);
            else if (i > 0) contains.push(e);
        }
        const byKey = (a, b) => a.key.length - b.key.length || a.key.localeCompare(b.key);
        return starts.sort(byKey).concat(contains.sort(byKey)).slice(0, MAX);
    }

    function attach(input, n) {
        const root = window.SITE_ROOT || '';
        const esc = ELieb.escapeXml;
        const list = document.createElement('ul');
        list.className = 'suggestions';
        list.id = 'suggestions-' + n;
        list.setAttribute('role', 'listbox');
        list.hidden = true;

        const wrap = document.createElement('div');
        wrap.className = 'suggest-wrap';
        input.parentNode.insertBefore(wrap, input);
        wrap.appendChild(input);
        wrap.appendChild(list);

        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-controls', list.id);
        input.setAttribute('aria-expanded', 'false');
        input.setAttribute('autocomplete', 'off');

        let items = [];
        let active = -1;

        const href = e => `${root}entry.html?id=${encodeURIComponent(e.id)}`;

        function close() {
            list.hidden = true;
            active = -1;
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
        }

        function highlight(i) {
            active = i;
            [...list.children].forEach((li, j) => li.setAttribute('aria-selected', String(j === i)));
            if (i >= 0) input.setAttribute('aria-activedescendant', `${list.id}-${i}`);
            else input.removeAttribute('aria-activedescendant');
        }

        function show() {
            const typed = input.value.trim();
            if (!typed) { close(); return; }
            load(root).then(entries => {
                if (input.value.trim() !== typed) return;   // typed on since
                items = match(entries, typed);
                if (!items.length) { close(); return; }
                list.innerHTML = items.map((e, i) => `
                    <li role="option" id="${list.id}-${i}" aria-selected="false">
                        <a href="${href(e)}" tabindex="-1">
                            <span class="headword">${esc(e.hw)}</span>
                            ${ELieb.languageBadge(e.lang, e.hw)}
                            <span class="gloss">${esc(e.gloss || '')}</span>
                        </a>
                    </li>`).join('');
                list.hidden = false;
                input.setAttribute('aria-expanded', 'true');
                highlight(-1);
            });
        }

        input.addEventListener('input', show);
        input.addEventListener('focus', show);
        input.addEventListener('blur', () => setTimeout(close, 150));
        input.addEventListener('keydown', ev => {
            if (list.hidden) return;
            if (ev.key === 'ArrowDown') { ev.preventDefault(); highlight((active + 1) % items.length); }
            else if (ev.key === 'ArrowUp') { ev.preventDefault(); highlight(active <= 0 ? items.length - 1 : active - 1); }
            else if (ev.key === 'Escape') close();
            else if (ev.key === 'Enter' && active >= 0) { ev.preventDefault(); location.href = href(items[active]); }
        });
        // Follow the link before blur closes the list.
        list.addEventListener('mousedown', ev => ev.preventDefault());
    }

    function init() { document.querySelectorAll('input[data-suggest]').forEach(attach); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
