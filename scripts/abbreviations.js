/*
 * eLiebermann: the law code and grammatical abbreviation lists
 * (lawAbb.html and gramAbb.html). Both pages share this code; each loads
 * its own data file (data/markLaw.js or data/markforward.js), which calls
 * markLawJSONP() or markforwardJSONP() with the rows.
 *
 * Rows with the same Anchor are variant spellings of one abbreviation and
 * share a heading, which is what entry pages link to (lawAbb.html#Ine).
 */
(function () {
    'use strict';

    // Columns shown only when a group has something in them. `review` marks
    // columns known to be unreliable: in data/markLaw.js the editions notes
    // and start pages are out of step with their rows (docs/STOCKTAKE.md).
    const EXTRA = [
        { field: 'Notes: Grammatical', label: 'Note' },
        { field: 'Notes: Information & Editions', label: 'Manuscripts and editions', review: true },
        { field: 'Notes: Start page in Liebermann Vol. I', label: 'Start page, vol. I', review: true }
    ];
    const FIELDS = ['Gesetze Text', 'German Expansion', 'English Translation'].concat(EXTRA.map(c => c.field));
    let groups = {};

    function esc(s) {
        return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function load(rows) {
        groups = {};
        rows.forEach(row => { (groups[row.Anchor] = groups[row.Anchor] || []).push(row); });
        draw();
        if (location.hash) {
            const el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
            if (el) el.scrollIntoView();
        }
    }

    function matches(row, term, scope) {
        const fields = scope === 'all' ? FIELDS : [scope];
        return fields.some(f => row[f] && String(row[f]).toLowerCase().includes(term));
    }

    function draw() {
        const term = document.getElementById('searchInput').value.trim().toLowerCase();
        const scope = document.getElementById('searchScope').value;
        const container = document.getElementById('content-container');
        const oneTable = document.getElementById('oneTable');
        if (oneTable && oneTable.checked) return drawOneTable(term, scope, container);
        let html = '';
        let shown = 0;
        Object.keys(groups).forEach(anchor => {
            const rows = term ? groups[anchor].filter(r => matches(r, term, scope)) : groups[anchor];
            if (!rows.length) return;
            shown++;
            const extra = EXTRA.filter(c => rows.some(r => r[c.field] && String(r[c.field]).trim()));
            const head = c => c.review ? `<th class="under-review" title="Under review: may belong to another row">${c.label} ⚠</th>` : `<th>${c.label}</th>`;
            const cell = (c, r) => `<td${c.review ? ' class="under-review"' : ''}>${esc(r[c.field])}</td>`;
            html += `<h2 id="${esc(anchor)}">${esc(groups[anchor][0]['Gesetze Text'])}</h2>
                <div class="table-wrap"><table>
                <thead><tr><th>As printed</th><th>German expansion</th><th>English</th>${extra.map(head).join('')}</tr></thead>
                <tbody>${rows.map(r => `<tr>
                    <td class="term">${esc(r['Gesetze Text'])}</td>
                    <td>${esc(r['German Expansion'])}</td>
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
            <thead><tr><th>As printed</th><th>German expansion</th><th>English</th>${extra.map(c =>
                c.review ? `<th class="under-review">${c.label} ⚠</th>` : `<th>${c.label}</th>`).join('')}</tr></thead>
            <tbody>${rows.map(r => `<tr>
                <td class="term">${esc(r['Gesetze Text'])}</td>
                <td>${esc(r['German Expansion'])}</td>
                <td>${esc(r['English Translation'])}</td>
                ${extra.map(c => `<td${c.review ? ' class="under-review"' : ''}>${esc(r[c.field])}</td>`).join('')}
            </tr>`).join('')}</tbody></table></div>` : `<p>Nothing matches “${esc(term)}”.</p>`;
    }

    window.markLawJSONP = load;
    window.markforwardJSONP = load;

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('searchInput').addEventListener('input', draw);
        document.getElementById('searchScope').addEventListener('change', draw);
        const oneTable = document.getElementById('oneTable');
        if (oneTable) oneTable.addEventListener('change', draw);
    });
})();
