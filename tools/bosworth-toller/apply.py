"""Add Bosworth-Toller links to entries: sure and likely matches, and the
editor's choices saved on the review page (which win)."""
import json, glob, os, re, html, pickle, sys
S, rows_pkl = sys.argv[1], sys.argv[2]
R = {r['id']: r for r in json.load(open(f'{S}/out.json'))}
dec = {os.path.basename(f)[:-5]: json.load(open(f)) for f in glob.glob(f'{S}/db/decisions/*.json')}
POS = {'noun': 'n.', 'verb': 'v.', 'adjective': 'adj.', 'adverb': 'adv.', 'preposition': 'prep.',
       'numeral': 'num.', 'pronoun': 'pron.', 'conjunction': 'conj.', 'interjection': 'interj.'}
bt = {}
for rid, head, body in pickle.load(open(rows_pkl, 'rb')):
    m = re.search(r'<orth>(.*?)</orth>', body, re.S)
    o = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else head
    if o.isupper(): o = o.lower()
    bt[rid] = (o, 'add="1"' in body, [POS[p] for p in re.findall(r'<pos>([^<]*)</pos>', body) if p in POS])
plan = {}
for e, r in R.items():
    if e in dec:
        ids = dec[e].get('ids') or []
    elif r['grade'] in ('sure', 'likely'):
        ids = [c['id'] for c in r['groups'][0]]
    else:
        continue
    if ids: plan[e] = ids
changed = added = 0
for e, ids in plan.items():
    p = f'entries/{e}.xml'; s = open(p, encoding='utf-8').read()
    # Cross-reference entries only point to another headword, which has the links.
    if re.search(r'<entry [^>]*type="xref"', s): continue
    have = set(re.findall(r'<xr type="bosworthToller"><ref target="https://bosworthtoller.com/(\d+)"', s))
    mains = [i for i in ids if not bt[i][1]]
    dup = {bt[i][0] for i in mains if sum(bt[j][0] == bt[i][0] for j in mains) > 1}
    new = []
    for i in ids:
        if i in have: continue
        o, add, pos = bt[i]
        label = html.escape(o, quote=False)
        if add: label += ' (Supplement)'
        elif o in dup and pos: label += f' ({", ".join(pos)})'
        new.append(f'        <xr type="bosworthToller"><ref target="https://bosworthtoller.com/{i}">{label}</ref></xr>\n')
    if not new: continue
    xrs = list(re.finditer(r'^        <xr type="bosworthToller">.*\n', s, re.M))
    if xrs: at = xrs[-1].end()
    else:
        m = re.search(r'^        <xr type="(doe|wiktionary|lawCode)">', s, re.M) or re.search(r'^      </entry>', s, re.M)
        at = m.start()
    s = s[:at] + ''.join(new) + s[at:]
    open(p, 'w', encoding='utf-8').write(s); changed += 1; added += len(new)
print('entries', changed, 'links', added, 'decisions used', sum(1 for e in plan if e in dec))
