/*
 * eLiebermann: the lists of law codes, manuscripts, grammatical
 * abbreviations and authors and works cited (lawAbb.html, msAbb.html,
 * gramAbb.html and bibAbb.html). The pages share this code; each loads its
 * own data file, named by data-source on #content-container
 * (data/markLaw.json, data/manuscripts.json, data/markforward.json or
 * data/bibliography.json). The works cited are drawn as a bibliography
 * (data-layout="works"), one entry per work, not as tables.
 *
 * Rows with the same Anchor are variant spellings of one abbreviation and
 * share a heading, which is what entry pages link to (lawAbb.html#Ine).
 */
(function () {
    'use strict';

    // Columns shown only when a group has something in them.
    const EXTRA = [
        { field: 'Notes: Grammatical', label: 'Note' },
        { field: 'Notes: Information & Editions', label: 'Manuscripts, editions and notes' },
        { field: 'Notes: Start page in Liebermann Vol. I', label: 'Start page, Liebermann vol. I' },
        // the list of manuscripts (data/manuscripts.json), from Liebermann's Gesetze I, pp. xiv, xviii–xlii
        { field: 'Date (Liebermann)', label: 'Date (Liebermann)' },
        { field: 'Laws in it', label: 'Laws in it' },
        { field: 'Notes', label: 'Notes' },
        { field: 'Liebermann I, page', label: 'Gesetze I, p.' }
    ];
    const FIELDS = ['Gesetze Text', 'German Expansion', 'Modern German', 'English Translation', 'Short Title', 'Full Citation'].concat(EXTRA.map(c => c.field));
    let groups = {};
    // The first three column heads; a page can name them with data-heads="A|B|C" on #content-container.
    function heads() {
        const h = (document.getElementById('content-container').dataset.heads || 'As printed|German expansion|English').split('|');
        return h.map(t => `<th>${esc(t)}</th>`).join('');
    }

    // Liebermann's form, with the modern spelling underneath where it differs.
    function german(r) {
        const modern = r['Modern German'] ? `<span class="modern-german">today: ${esc(r['Modern German'])}</span>` : '';
        return esc(r['German Expansion']) + modern;
    }

    function esc(s) {
        return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // Text with <i>…</i> for titles (data/bibliography.json): escaped, then
    // only the italics let through.
    function italics(s) {
        return esc(s).replace(/&lt;i&gt;/g, '<i>').replace(/&lt;\/i&gt;/g, '</i>');
    }
    const plainText = s => String(s == null ? '' : s).replace(/<\/?i>/g, '');

    // The bibliography: one entry per work, with its full citation, the
    // forms in which the Wörterbuch cites it, and any note.
    function drawWorks(term, scope, container) {
        let html = '';
        let shown = 0;
        Object.keys(groups).forEach(anchor => {
            const rows = groups[anchor];
            if (term && !rows.some(r => matches(r, term, scope))) return;
            shown++;
            const r0 = rows[0];
            const forms = [...new Set(rows.map(r => String(r['Gesetze Text']).trim()))];
            const note = (rows.find(r => r['Notes']) || {})['Notes'];
            html += `<section class="bib-work" id="${esc(anchor)}">
                <h2>${esc(r0['Short Title'])}</h2>
                <p class="bib-full">${italics(r0['Full Citation'])}</p>
                <p class="small"><span class="muted">As printed in the Gesetze:</span> ${forms.map(f => `<span class="term">${esc(f)}</span>`).join(' · ')}</p>
                ${note ? `<p class="small bib-note"><span class="muted">Note:</span> ${italics(note)}</p>` : ''}
            </section>`;
        });
        document.getElementById('count').textContent = `${shown} of ${Object.keys(groups).length} works`;
        container.innerHTML = html || `<p>Nothing matches “${esc(term)}”.</p>`;
    }

    function load(rows) {
        groups = {};
        rows.forEach(row => { (groups[row.Anchor] = groups[row.Anchor] || []).push(row); });
        draw();
        if (location.hash) {
            const anchor = decodeURIComponent(location.hash.slice(1));
            const el = document.getElementById(anchor);
            if (el) el.scrollIntoView();
            else forward(anchor);
        }
    }

    // Dictionary entries link manuscript sigla to the law code list
    // (lawAbb.html#H). If the anchor isn't here but is on the list named by
    // data-elsewhere ("data/manuscripts.json msAbb.html"), go there.
    function forward(anchor) {
        const container = document.getElementById('content-container');
        const [file, page] = (container.dataset.elsewhere || '').split(' ');
        if (!file || !page) return;
        fetch((window.SITE_ROOT || '') + file)
            .then(r => r.json())
            .then(rows => {
                if (rows.some(r => r.Anchor === anchor)) location.replace((window.SITE_ROOT || '') + page + '#' + encodeURIComponent(anchor));
            })
            .catch(() => {});
    }

    function matches(row, term, scope) {
        const fields = scope === 'all' ? FIELDS : [scope];
        return fields.some(f => row[f] && plainText(row[f]).toLowerCase().includes(term));
    }

    function draw() {
        const term = document.getElementById('searchInput').value.trim().toLowerCase();
        const scope = document.getElementById('searchScope').value;
        const container = document.getElementById('content-container');
        if (container.dataset.layout === 'works') return drawWorks(term, scope, container);
        const oneTable = document.getElementById('oneTable');
        if (oneTable && oneTable.checked) return drawOneTable(term, scope, container);
        let html = '';
        let shown = 0;
        Object.keys(groups).forEach(anchor => {
            const rows = term ? groups[anchor].filter(r => matches(r, term, scope)) : groups[anchor];
            if (!rows.length) return;
            shown++;
            const extra = EXTRA.filter(c => rows.some(r => r[c.field] && String(r[c.field]).trim()));
            const head = c => `<th>${c.label}</th>`;
            const cell = (c, r) => `<td>${esc(r[c.field])}</td>`;
            html += `<h2 id="${esc(anchor)}">${esc(groups[anchor][0]['Gesetze Text'])}</h2>
                <div class="table-wrap"><table>
                <thead><tr>${heads()}${extra.map(head).join('')}</tr></thead>
                <tbody>${rows.map(r => `<tr>
                    <td class="term">${esc(r['Gesetze Text'])}</td>
                    <td>${german(r)}</td>
                    <td>${esc(r['English Translation'])}</td>
                    ${extra.map(c => cell(c, r)).join('')}
                </tr>`).join('')}</tbody>
                </table></div>`;
        });
        document.getElementById('count').textContent = `${shown} of ${Object.keys(groups).length} abbreviations`;
        container.innerHTML = html || `<p>Nothing matches “${esc(term)}”.</p>`;
    }

    // Every row in one table, in file order: easier for checking a row against
    // its neighbours.
    function drawOneTable(term, scope, container) {
        const all = Object.values(groups).flat();
        const rows = term ? all.filter(r => matches(r, term, scope)) : all;
        const extra = EXTRA.filter(c => all.some(r => r[c.field] && String(r[c.field]).trim()));
        document.getElementById('count').textContent = `${rows.length} of ${all.length} rows`;
        container.innerHTML = rows.length ? `<div class="table-wrap"><table>
            <thead><tr>${heads()}${extra.map(c => `<th>${c.label}</th>`).join('')}</tr></thead>
            <tbody>${rows.map(r => `<tr>
                <td class="term">${esc(r['Gesetze Text'])}</td>
                <td>${german(r)}</td>
                <td>${esc(r['English Translation'])}</td>
                ${extra.map(c => `<td>${esc(r[c.field])}</td>`).join('')}
            </tr>`).join('')}</tbody></table></div>` : `<p>Nothing matches “${esc(term)}”.</p>`;
    }

    document.addEventListener('DOMContentLoaded', () => {
        const container = document.getElementById('content-container');
        fetch((window.SITE_ROOT || '') + container.dataset.source)
            .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(load)
            .catch(() => { container.innerHTML = '<p class="notice error">The list could not be loaded.</p>'; });
        document.getElementById('searchInput').addEventListener('input', draw);
        document.getElementById('searchScope').addEventListener('change', draw);
        const oneTable = document.getElementById('oneTable');
        if (oneTable) oneTable.addEventListener('change', draw);
    });
})();
