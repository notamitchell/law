#!/usr/bin/env python3
"""
Marks the entries that only send the reader to another headword as
cross-reference entries, and takes their links to other dictionaries out.

Many of Liebermann's entries hold nothing but a pointer: a spelling or a form,
"s." and the headword he treats it under ("abere s. æbære", "ā geschrieben aa
s. d."). On the website such an entry should show Liebermann's line and a
"See" list, and nothing else. This tool finds them and, in each file:

  - adds type="xref" to <entry> (TEI's value for an entry whose only job is
    to point to another one); the entry page then heads the list "See"
    instead of "See also" and leaves out everything else;
  - removes its Bosworth-Toller, DOE and Wiktionary links: the headword it
    points to carries those;
  - adds a line to the revisionDesc.

An entry counts as a pointer when it has at least one "See" link, no law code
citations, no numbered senses or definition, and Liebermann's text has nothing
in it but the headword and its other forms, "s." / "s. d." / "für" /
"geschrieben", grammatical labels (ac, dt, op 3, ptt…), numbers, and the words
it points to. Spelling notes ("-um ersetzt durch -on…") are left as they are.
Entries that come close but have something more (a gloss such as "Hufe", a
word pointed to that has no link yet) are listed in the report for checking.

  python3 tools/cross-reference-entries.py            # change the files
  python3 tools/cross-reference-entries.py --dry-run  # report only

The report is docs/cross-reference-entries-report.md.
"""
import glob, re, sys, unicodedata, difflib, os
from lxml import etree

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TODAY = '2026-10-17'
ns={'t':'http://www.tei-c.org/ns/1.0'}
ALLOWED={'s','d','für','geschrieben','geschr','dafür','auch','F','L','FL','I','II','III','IV','V','u','und','oder','vgl','ebd'}
def norm(w):
    w=unicodedata.normalize('NFD',w.lower()); w=''.join(c for c in w if not unicodedata.combining(c))
    return re.sub(r'[~\-\[\]()?]','',w)
TOK=re.compile(r'[^\s,;:.()\[\]|—–]+')
def classify(f):
    d=etree.parse(f); e=d.find('.//t:entry',ns)
    xrs=e.findall('t:xr',ns); types=[x.get('type') for x in xrs]
    if 'see' not in types: return None,'no see'
    if 'lawCode' in types: return False,'law citations'
    if e.find('t:sense',ns) is not None or e.find("t:dictScrap[@type='senses']",ns) is not None: return False,'senses'
    sc=etree.fromstring(etree.tostring(e.find("t:dictScrap[@type='liebermann']",ns)))
    for b in list(sc.iter('{%s}hi'%ns['t'],'{%s}ref'%ns['t'])):
        if (b.get('rend')=='bold' and b.tag.endswith('hi')) or (b.tag.endswith('ref') and (b.get('target') or '').startswith('gram:') and (b.get('target') or '') not in ('gram:siehe','gram:sieheDort','gram:fur')):
            tail=b.tail; b.clear(); b.tail=tail
    txt=' '.join(sc.itertext())
    targets=set()
    for x in xrs:
        if x.get('type')=='see':
            for w in ' '.join(x.itertext()).split(): targets.add(norm(w))
    orth=set(norm(w) for w in TOK.findall(e.find('.//t:orth',ns).text or ''))
    toks=TOK.findall(txt); bad=[]; prev=''; seen_s=False
    for w in toks:
        n=norm(w)
        if w=='s': seen_s=True
        if not seen_s and (w[0] in '~-' or any(difflib.SequenceMatcher(None,n,o).ratio()>=0.5 for o in orth)): pass
        elif not n or w in ALLOWED or n in targets or n in orth or prev in ('für','geschrieben','dafür','geschr'): pass
        elif re.fullmatch(r'[0-9]+[a-z]?|[a-zA-Z]|[IVX]+',w): pass
        elif any(t and (t.startswith(n[:2]) or difflib.SequenceMatcher(None,n,t).ratio()>=0.6) for t in targets): pass
        else: bad.append(w)
        prev=w
    note=re.findall(r'\b(ersetzt|eingeführt|abweichend|statt|dafür|variirt|Praefix|Suffix|ausgedr\w*|gebildet)\b',txt)
    orthtxt=e.find('.//t:orth',ns).text or ''
    if note: return False,'spelling note: '+' '.join(note)
    if re.match(r'^\(?-.*-\)?$',orthtxt.strip()) and len(orthtxt.strip())<=6: return False,'spelling note (inner letters)'
    return (not bad), ' '.join(bad)


def tidy(e):
    return re.sub(r'\s+', ' ', ' '.join(e.itertext())).strip()

def main():
    dry = '--dry-run' in sys.argv
    files = sorted(glob.glob('entries/*.xml'))
    bt_of = {}
    for f in files:
        bt_of[f[8:-4]] = set(re.findall(r'<xr type="bosworthToller"><ref target="([^"]+)"', open(f, encoding='utf-8').read()))
    done, already, review, lost = [], [], [], []
    for f in files:
        ok, why = classify(f)
        slug = f[8:-4]
        s = open(f, encoding='utf-8').read()
        text = tidy(etree.parse(f).find(".//t:dictScrap[@type='liebermann']", ns))
        if ok is None: continue
        if not ok:
            if why not in ('law citations', 'senses'): review.append((slug, text, why))
            continue
        if re.search(r'<entry [^>]*type="xref"', s):
            already.append(slug); continue
        targets = re.findall(r'<xr type="see"><ref target="entry:([^"]+)"', s)
        removed = re.findall(r'^ *<xr type="(?:bosworthToller|doe|wiktionary)">.*\n', s, re.M)
        for line in removed:
            m = re.search(r'target="([^"]+)"', line)
            if m and 'bosworthtoller' in m.group(1) and not any(m.group(1) in bt_of.get(t, ()) for t in targets):
                lost.append((slug, re.sub(r'<[^>]+>', '', line).strip(), m.group(1), targets))
        s = re.sub(r'^ *<xr type="(?:bosworthToller|doe|wiktionary)">.*\n', '', s, flags=re.M)
        s = re.sub(r'<entry xml:lang="([^"]*)"(?: type="[^"]*")?', r'<entry xml:lang="\1" type="xref"', s, count=1)
        note = 'Marked as a cross-reference entry (it only points to another headword); links to other dictionaries removed.' if removed else 'Marked as a cross-reference entry (it only points to another headword).'
        s = s.replace('    </revisionDesc>', f'      <change when="{TODAY}">{note}</change>\n    </revisionDesc>', 1)
        if not dry: open(f, 'w', encoding='utf-8').write(s)
        done.append((slug, text, len(removed)))

    out = ['# Cross-reference entries', '',
           'Made by `tools/cross-reference-entries.py`. It is replaced each time the tool runs.', '',
           f'- Marked as cross-reference entries this time: **{len(done)}** (links to other dictionaries removed from {sum(1 for d in done if d[2])} of them, {sum(d[2] for d in done)} links in all)',
           f'- Already marked: {len(already)}',
           f'- Close, but not changed (to check): {len(review)}', '',
           '## Bosworth-Toller links that the entry pointed to does not have', '',
           'These links were removed from a cross-reference entry, and the entry it points to has no link to the same Bosworth-Toller page. Usually the pointer\'s spelling matched a different Bosworth-Toller headword; if the link is wanted, it belongs on the entry pointed to.', '']
    out += [f'- **{s}** → {", ".join(t)}: [{lab}]({u})' for s, lab, u, t in lost] or ['None.']
    out += ['', '## Close, but not changed', '',
            'Entries with a "See" link and no citations or senses, but with something more in Liebermann\'s text than a pointer. The words that stopped them are after "Stopped by". A gloss or a note means the entry is not only a pointer and should stay as it is; a word pointed to that has no link yet means the "See" list is incomplete.', '']
    out += [f'- **{s}**: {t} — Stopped by: {w}' for s, t, w in review]
    out += ['', '## Marked as cross-reference entries', '']
    out += [f'- [{s}](../entry.html?id={s}): {t}' for s, t, n in done]
    open('docs/cross-reference-entries-report.md', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(f'marked {len(done)}, already {len(already)}, to check {len(review)}, BT links not on target {len(lost)}', '(dry run)' if dry else '')

if __name__ == '__main__':
    main()
