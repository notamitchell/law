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

    const FIELDS = ['Gesetze Text', 'German Expansion', 'English Translation', 'Notes: Grammatical'];
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
        let html = '';
        let shown = 0;
        Object.keys(groups).forEach(anchor => {
            const rows = term ? groups[anchor].filter(r => matches(r, term, scope)) : groups[anchor];
            if (!rows.length) return;
            shown++;
            const notes = rows.some(r => r['Notes: Grammatical']);
            html += `<h2 id="${esc(anchor)}">${esc(groups[anchor][0]['Gesetze Text'])}</h2>
                <div class="table-wrap"><table>
                <thead><tr><th>As printed</th><th>German expansion</th><th>English</th>${notes ? '<th>Note</th>' : ''}</tr></thead>
                <tbody>${rows.map(r => `<tr>
                    <td class="term">${esc(r['Gesetze Text'])}</td>
                    <td>${esc(r['German Expansion'])}</td>
                    <td>${esc(r['English Translation'])}</td>
                    ${notes ? `<td>${esc(r['Notes: Grammatical'])}</td>` : ''}
                </tr>`).join('')}</tbody>
                </table></div>`;
        });
        document.getElementById('count').textContent = `${shown} of ${Object.keys(groups).length} abbreviations`;
        container.innerHTML = html || `<p>Nothing matches “${esc(term)}”.</p>`;
    }

    window.markLawJSONP = load;
    window.markforwardJSONP = load;

    document.addEventListener('DOMContentLoaded', () => {
        document.getElementById('searchInput').addEventListener('input', draw);
        document.getElementById('searchScope').addEventListener('change', draw);
    });
})();
