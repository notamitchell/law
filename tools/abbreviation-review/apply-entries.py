"""Fixes the abbreviation links in entries/ after the October 2026 review.
Edits Liebermann's text (dictScrap type="liebermann") only; the numbered-senses
copy is remade afterwards with ELieb.sensesXml."""
import glob, json, re, collections

S = 'tools/abbreviation-review'
RENAMES = json.load(open(f'{S}/renames.json'))
REF = re.compile(r'<ref type="abbreviation" target="gram:([^"]+)"><abbr>([^<]*)</abbr></ref>')
counts = collections.Counter()
changed = set()

def plain(x):
    return re.sub(r'<[^>]+>', '', x)

# per-occurrence decisions: (anchor, entry, index) -> new anchor, or None = unlink
DECIDE = {}
for e, i in [('Eadweard', 0), ('Henricus', 0), ('Normanni', 0), ('Rol', 0), ('dux', 0), ('witan-2', 0), ('th', 0)]:
    DECIDE[('circa', e, i)] = 'capitulum'
for e, i in [('Wortstellung', 0), ('gan', 0), ('ge', 0), ('infractura', 0), ('k', 0), ('secan', 0), ('socn', 0), ('transcurrere', 0)]:
    DECIDE[('circa', e, i)] = None
for e, i in [('apostol', 0), ('apostol', 1), ('bydel', 0), ('bydel', 1), ('ceorl', 0), ('ceorl', 1), ('dael', 0), ('dael', 1),
             ('eorl', 0), ('stol', 0), ('lahslit', 0), ('lahslit', 1)]:
    DECIDE[('las', e, i)] = None
for e, i in [('beon-2', 0), ('betan', 0), ('betan', 1), ('gebetan', 0), ('mundbyrd', 0), ('on', 0), ('weord', 0), ('weord', 1), ('wer', 0)] + \
            [('wite', n) for n in range(11)]:
    DECIDE[('scilicet', e, i)] = 'Schilling'
for e, i in [('Engle', 1), ('ecclesia', 0), ('stabilita-s', 0)]:
    DECIDE[('Seite', e, i)] = 'sanctus'
DECIDE[('Partitiv', 'Particip', 0)] = 'Particip'
DECIDE[('fast', 'heordfaest', 0)] = None
DECIDE[('Zahlen', 'gan', 0)] = None
DECIDE[('durch', 'peragrare', 0)] = None
DECIDE[('vor', 'gerefa', 0)] = None

UNLINK_ALL = {'ausbessern', 'bestimmer', 'bezeichne', 'OriginalLasVielleicht', 'abhang', 'beAlsBi', 'setzGlossator',
              'unbestimmer', 'Optativ2Person', 'Optativ3Person', 'Spalte1', 'Spalte2', 'Spalte3', 'imperfectSubjonctiv3Pers',
              'GermanischeMythologie', 'GermanischesAltertum'}
VOR_DETACHED = re.compile(r'\b(lag|lagen|liegt|liegen|kommt|kommen|behält sich|sehe sich|sieht sich)\b[^;|.\]]{0,45}$')
VORIG_NEXT = re.compile(r'^\.\s+(Z\.|Wort|Sp\.|Seite|Satzes|Vocal|Negation|sbjf|adj)')

def fix_refs(slug, t):
    occ = collections.Counter()
    out, pos = [], 0
    for m in REF.finditer(t):
        a, txt = m.group(1), m.group(2)
        i = occ[a]; occ[a] += 1
        new = a
        before = plain(t[max(0, m.start() - 300):m.start()])
        after = plain(t[m.end():m.end() + 300])
        if (a, slug, i) in DECIDE:
            new = DECIDE[(a, slug, i)]
        elif a in UNLINK_ALL:
            new = None
        elif a == 'Genitiv' and txt == 'g.':
            new = None
        elif a == 'stark' and txt == 'st':
            new = None
        elif a == 'vor' and VORIG_NEXT.match(after):
            new = 'vorig'
        elif a == 'vor' and VOR_DETACHED.search(before):
            new = None
        elif a == 'Object' and txt == 'obj' and re.search(r'\bgn\s*$', before):
            new = 'objectiv'
        elif a in RENAMES:
            new = RENAMES[a]
        out.append(t[pos:m.start()])
        if new is None:
            out.append(txt); counts[f'unlinked {a}'] += 1
        elif new == 'vorig':
            out.append('<ref type="abbreviation" target="gram:vorig"><abbr>vor.</abbr></ref>'); counts['vor. -> vorig'] += 1
            pos = m.end() + 1           # the full stop moves inside the link
            continue
        else:
            out.append(f'<ref type="abbreviation" target="gram:{new}"><abbr>{txt}</abbr></ref>')
            if new != a: counts[f'{a} -> {new}'] += 1
        pos = m.end()
    out.append(t[pos:])
    t = ''.join(out)
    # s. z. B. = s. (siehe) + z. B. (zum Beispiel)
    t, n = re.subn(r'<ref type="abbreviation" target="gram:sieheZu"><abbr>s\. z\.</abbr></ref> B\.',
                   '<ref type="abbreviation" target="gram:siehe"><abbr>s.</abbr></ref> <ref type="abbreviation" target="gram:zumBeispiel"><abbr>z. B.</abbr></ref>', t)
    counts['s. z. B. split'] += n
    return t

# ---- linking phrases whose printed form was corrected (spanning text and existing links)
TOKEN = re.compile(r'(<ref type="abbreviation" target="gram:[^"]+"><abbr>[^<]*</abbr></ref>|<[^>]+>)')
def link_phrase(t, phrase, anchor):
    n_total = 0
    while True:
        toks = [x for x in TOKEN.split(t) if x != '']
        flat, owner = [], []
        for k, tok in enumerate(toks):
            m = REF.fullmatch(tok)
            if m:
                s = m.group(2)
            elif tok.startswith('<'):
                s = '\x00'
            else:
                s = tok.replace('&amp;', '&')
            for j, ch in enumerate(s):
                flat.append(ch); owner.append((k, j, len(s)))
        flat = ''.join(flat)
        body = r'\s+'.join(re.escape(w) for w in phrase.split())
        pat = ('(?<![\\w-])' if phrase[0].isalnum() else '') + body + ('(?![\\w-])' if phrase[-1].isalnum() else '')
        done = False
        for m in re.finditer(pat, flat):
            (k1, j1, l1), (k2, j2, l2) = owner[m.start()], owner[m.end() - 1]
            first, last = toks[k1], toks[k2]
            if REF.fullmatch(first) and j1 != 0: continue
            if REF.fullmatch(last) and j2 != l2 - 1: continue
            if k1 == k2 and REF.fullmatch(first) and REF.fullmatch(first).group(1) == anchor: continue
            if any(toks[k].startswith('<') and not REF.fullmatch(toks[k]) for k in range(k1, k2 + 1)): continue
            pre = first[:j1] if not REF.fullmatch(first) else ''
            post = last[j2 + 1:] if not REF.fullmatch(last) else ''
            text = re.sub(r'\s+', ' ', m.group(0))
            new = pre + f'<ref type="abbreviation" target="gram:{anchor}"><abbr>{text}</abbr></ref>' + post
            toks[k1:k2 + 1] = [new]
            t = ''.join(toks); n_total += 1; done = True
            break
        if not done:
            return t, n_total

PHRASES = [('dies sieht irrig', 'diesSiehtIrrig'), ('sonst häufig', 'sonstHaufig'), ('sbj ist Abstract', 'SubjektIsAbstract'),
           ('Verb vicar.', 'verbumVicarium'), ('unbetont in- und ausl.', 'unbetontInUndAus'), ('spl', 'superlativus'),
           ('demonst.', 'demonstrativ')]

for f in sorted(glob.glob('entries/*.xml')):
    slug = f[8:-4]
    s = open(f, encoding='utf-8').read()
    m = re.search(r'(<dictScrap type="liebermann">)(.*?)(</dictScrap>)', s, re.S)
    if not m: continue
    t = m.group(2)
    t2 = fix_refs(slug, t)
    for ph, an in PHRASES:
        t2, n = link_phrase(t2, ph, an)
        counts[f'linked "{ph}"'] += n
    if slug == 'sca-m-num':
        old = '<hi rend="italic">Erdbank, ‘hillside’; Middendorf</hi> <ref type="abbreviation" target="gram:altenglisch"><abbr>Altengl.</abbr></ref> Flurnamen 10'
        assert old in t2
        t2 = t2.replace(old, '<hi rend="italic">Erdbank, ‘hillside’;</hi> <ref type="bibl" target="bib:CitMiddendorffFN"><hi rend="italic">Middendorf</hi> Altengl. Flurnamen 10</ref>')
        counts['Middendorf citation linked'] += 1
    if t2 != t:
        s = s[:m.start(2)] + t2 + s[m.end(2):]
        s = s.replace('    </revisionDesc>', '      <change when="2026-10-17">Abbreviation links corrected after the review of the abbreviations list.</change>\n    </revisionDesc>', 1)
        open(f, 'w', encoding='utf-8').write(s)
        changed.add(slug)

# no link may point to an anchor that is no longer on the list
anchors = {r['Anchor'] for r in json.load(open('data/markforward.json', encoding='utf-8'))}
dangling = collections.Counter()
for f in glob.glob('entries/*.xml'):
    s = open(f, encoding='utf-8').read()
    m = re.search(r'<dictScrap type="liebermann">(.*?)</dictScrap>', s, re.S)
    for a in re.findall(r'target="gram:([^"]+)"', m.group(1) if m else ''):
        if a not in anchors: dangling[a] += 1
json.dump(sorted(changed), open(f'{S}/changed.json', 'w'))
for k, v in sorted(counts.items()): print(f'{v:5}  {k}')
print(len(changed), 'entries changed; dangling:', dict(dangling))
