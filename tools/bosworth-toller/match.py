"""Match eLiebermann Old English entries to Bosworth-Toller entries.

python3 -I match.py rows.pkl /home/claude/law/entries out.json
"""
import html, sys, re, glob, json, pickle, unicodedata, itertools, collections, os

rows_path, entries_dir, out_path = sys.argv[1:4]

# ---------- spelling ----------
def base(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace('ð', 'þ').replace('ƿ', 'w').replace('ǽ', 'æ').replace('k', 'c')
    return re.sub(r'[^a-zæþ]', '', s)

def loose(s):
    s = base(s)
    s = s.replace('ie', 'i').replace('y', 'i').replace('io', 'eo').replace('ea', 'ea')
    s = re.sub(r'(.)\1', r'\1', s)          # double consonants/vowels
    s = s.replace('cg', 'g').replace('gg', 'g').replace('sc', 'sc')
    s = re.sub(r'(nis|nys|nes)$', 'nes', s)
    s = re.sub(r'ian$', 'an', s)            # -ian / -an verbs
    s = re.sub(r'ig$', 'i', s)
    return s

def nogé(s):
    return s[2:] if s.startswith('ge') and len(s) > 4 else s

NOUN_ENDINGS = ['ena', 'um', 'an', 'ra', 're', 'ne', 'es', 'as', 'a', 'e', 'u', 'o']
def lemma_guesses(form, pos):
    """Liebermann's headword is often the form found in the laws (healle, dt;
    beate, op 3). Guess the dictionary form: heall, beatan."""
    out = set()
    f = form
    if 'v' in pos or not pos:
        for end, rep in (('ige', 'ian'), ('ie', 'ian'), ('ode', 'ian'), ('ade', 'ian'), ('ede', 'an'),
                         ('od', 'ian'), ('ad', 'ian'), ('ed', 'an'), ('en', 'an'), ('að', 'an'), ('eð', 'an'),
                         ('aþ', 'an'), ('eþ', 'an'), ('e', 'an'), ('e', 'ian')):
            if f.endswith(end) and len(f) - len(end) >= 3:
                out.add(f[:-len(end)] + rep)
    if 'v' not in pos:
        for end in NOUN_ENDINGS:
            if f.endswith(end) and len(f) - len(end) >= 3:
                st = f[:-len(end)]
                out.update({st, st + 'e', st + 'u', st + 'a'})
    out.discard(f)
    return out

def lieb_variants(hw):
    """g[e]aldorcræft -> {galdorcræft, gealdorcræft}; (ge)witnes; mæg[e]ðman[n]."""
    hw = hw.strip()
    parts = re.split(r'(\[[^\]]*\]|\([^)]*\))', hw)
    opts = []
    for p in parts:
        if (p.startswith('[') and p.endswith(']')) or (p.startswith('(') and p.endswith(')')):
            opts.append(['', p[1:-1]])
        else:
            opts.append([p])
    out = set()
    for combo in itertools.islice(itertools.product(*opts), 64):
        out.add(''.join(combo))
    return out

# ---------- law code families ----------
LIEB_FAMILY = [
    (r'^Ine', 'Ine'), (r'^(Af|El)$|^Af', 'Af'), (r'^Abt$', 'Abt'), (r'^Hl$', 'Hl'), (r'^Wi$', 'Wi'),
    (r'As$', 'As'), (r'Em$', 'Em'), (r'^(I|II|III|IV)Eg$', 'Eg'), (r'Atr$', 'Atr'), (r'^(I|II)Cn$|^Cn10', 'Cn'),
    (r'^EGu$', 'EGu'), (r'^AGu$', 'AGu'), (r'Ew$', 'Ew'), (r'^Rect$', 'Rect'), (r'^Ger$', 'Ger'),
    (r'^Northu$', 'Northu'), (r'^Duns$', 'Duns'), (r'^Wer$', 'Wer'), (r'^Hu$', 'Hu'), (r'^Wif$', 'Wif'),
    (r'^Swer$', 'Swer'), (r'^Grith$', 'Grith'), (r'^Had$', 'Had'), (r'^Ordal$', 'Ordal'), (r'^Mirce$', 'Mirce'),
    (r'^Northleoda$', 'Northleoda'), (r'^Ath$', 'Ath'), (r'^Episc$', 'Episc'), (r'^Blas$', 'Blas'), (r'^Forf$', 'Forf'),
    (r'^Becwaeth$', 'Becwaeth'), (r'^Romscot$', 'Romscot'), (r'^Pax$', 'Pax'), (r'^Wal$', 'Wal'),
]
def lieb_family(anchor):
    for pat, fam in LIEB_FAMILY:
        if re.search(pat, anchor):
            return fam
    return None

# Bosworth-Toller's citations of Thorpe's Ancient Laws: "L. In. 23", "L. C. S. 12".
BT_FAMILY = [
    (r'^In\b', 'Ine'), (r'^Alf\. ?pol', 'Af'), (r'^Alf\.?$', 'Af'), (r'^Ethb', 'Abt'), (r'^H\. ?E\.?$', 'Hl'),
    (r'^Wih', 'Wi'), (r'^Ath\.?$', 'As'), (r'^Ath\. ?[iv]', 'As'), (r'^Edm\. ?[SE]', 'Em'), (r'^Edg\. ?S', 'Eg'),
    (r'^Edg\.?$', 'Eg'), (r'^Edg\. ?H', 'Hu'), (r'^Eth\.?$', 'Atr'), (r'^C\. ?S\.?$', 'Cn'), (r'^C\. ?E\.?$', 'Cn'),
    (r'^E\. ?G\.?$', 'EGu'), (r'^A\. ?G\.?$', 'AGu'), (r'^Ed\.?$', 'Ew'), (r'^R\. ?S\.?$', 'Rect'),
    (r'^N\. ?P\. ?L', 'Northu'), (r'^O\. ?D', 'Duns'), (r'^Wg', 'Wer'), (r'^H\.?$', 'Hu'),
]
def bt_families(body):
    fams = set()
    for refs in re.findall(r'<references>(.*?)</references>', body, re.S):
        for m in re.finditer(r'\bL\. ?([A-ZÆ][A-Za-zæ\. ]{0,14}?)(?= ?[ivx0-9]| ?Th| ?;|,|$)', refs):
            ab = m.group(1).strip()
            for pat, fam in BT_FAMILY:
                if re.search(pat, ab):
                    fams.add(fam)
                    break
    return fams

# ---------- part of speech ----------
BT_POS = {'noun': 'n', 'verb': 'v', 'adjective': 'adj', 'adverb': 'adv', 'preposition': 'prp',
          'numeral': 'num', 'pronoun': 'pron', 'conjunction': 'cj', 'interjection': 'int'}

def lieb_pos(text, grams, hw):
    """A set of possible classes from Liebermann's labels in the first part of the entry."""
    g = set(grams)
    pos = set()
    if g & {'adverb'}: pos.add('adv')
    if g & {'adjektiv'}: pos.add('adj')
    if g & {'Praeposition', 'PraepositionMitDativ', 'PraepositionMitGenitiv', 'PraepositionZeitlich'}: pos.add('prp')
    if g & {'conjunctio'}: pos.add('cj')
    if g & {'Pronomen'}: pos.add('pron')
    if g & {'Substantiv', 'masculin', 'femininum', 'neutrum'}: pos.add('n')
    # A case label (dt, ac, gn ..) without a more exact one: a noun, adjective or pronoun.
    if not pos and g & {'Dativ', 'accusativus', 'Genitiv', 'Nominativ', 'Instrumental', 'Plural'}:
        pos.update({'n', 'adj', 'pron', 'num'})
    if g & {'Optativ', 'Optativ2Person', 'Optativ3Person', 'Praeteritum', 'Infinitiv', 'InfinitivFlektiert',
            'Imperativ', 'Indicativ', 'PraeteritumSubjonctiv3Person'}: pos.add('v')
    return pos

# ---------- Bosworth-Toller index ----------
rows = pickle.load(open(rows_path, 'rb'))
bt = []
for rid, head, body in rows:
    if re.search(r'delete="1"', body):
        continue
    orth = re.search(r'<orth>(.*?)</orth>', body, re.S)
    orth = re.sub(r'<[^>]+>', '', orth.group(1)).strip() if orth else head
    add = re.search(r'add="(\d)"', body).group(1) == '1'
    pos = {BT_POS[p] for p in re.findall(r'<pos>([^<]*)</pos>', body) if p in BT_POS}
    gen = re.findall(r'<gen>([^<]*)</gen>', body)
    if gen and not pos: pos.add('n')
    eq = [re.sub(r'<[^>]+>', '', e).strip() for e in re.findall(r'<equiv lang="eng">(.*?)</equiv>', body, re.S)]
    has_eq = bool(eq)
    if not eq:
        d = re.search(r'<def>(.*?)</def>', body, re.S)
        if d: eq = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', d.group(1))).strip()[:80]]
    # A stub only points elsewhere ("á-bútan v. þǽr-ábútan"): no definition of its own.
    stub = 'link="1"' in body and not re.search(r'<def>|<equiv', body)
    see = [str(int(x)) for x in re.findall(r'<see>.*?<a href="(\d+)"', body, re.S)]
    eq = [html.unescape(x) for x in eq]
    bt.append({'id': rid, 'orth': orth, 'add': add, 'pos': sorted(pos), 'gen': gen,
               'eng': '; '.join(eq[:4])[:120], 'fams': sorted(bt_families(body)),
               'b': base(orth), 'l': loose(orth), 'stub': stub, 'has_eq': has_eq, 'see': see,
               'cap': orth[:1].isupper() and not orth.isupper()})

by_id = {e['id']: e for e in bt}
# Entries with a definition of their own that point to another ("Dæne .. v. Dene"):
# Bosworth-Toller's other spellings of that word.
pointed_from = collections.defaultdict(list)
for e in bt:
    if not e['stub'] and not e['add']:
        for t in e['see']:
            pointed_from[t].append(e)
bt = [e for e in bt if not e['stub']]
by_base = collections.defaultdict(list); by_loose = collections.defaultdict(list); by_noge = collections.defaultdict(list)
for e in bt:
    by_base[e['b']].append(e); by_loose[e['l']].append(e); by_noge[nogé(e['l'])].append(e)

# ---------- Liebermann entries ----------
lieb = []
for f in sorted(glob.glob(os.path.join(entries_dir, '*.xml'))):
    s = open(f, encoding='utf-8').read()
    if 'xml:lang="ang"' not in s:
        continue
    hw = re.sub(r'<[^>]+>', '', re.search(r'<orth>(.*?)</orth>', s, re.S).group(1)).strip()
    m = re.search(r'<dictScrap type="liebermann">(.*?)</dictScrap>', s, re.S)
    scrap = m.group(1) if m else ''
    plain = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', scrap))
    grams = re.findall(r'target="gram:([^"]+)"', scrap[:900])
    fams = {lieb_family(a) for a in re.findall(r'target="law:([^"]+)"', scrap)} - {None}
    fams |= {lieb_family(re.sub(r'_.*', '', a)) for a in re.findall(r'target="clause:([^"]+)"', s)} - {None}
    existing = re.findall(r'<xr type="bosworthToller"><ref target="https://bosworthtoller.com/(\d+)"', s)
    trans = re.search(r'<sense type="translation"[^>]*>(.*?)</sense>', s, re.S)
    xref = bool(re.match(r'\s*\S+\s+s\.\s', plain)) and len(plain) < 60
    lieb.append({'id': os.path.basename(f)[:-4], 'hw': hw, 'pos': sorted(lieb_pos(plain, grams, hw)),
                 'fams': sorted(fams), 'existing': existing, 'xref': xref,
                 'snippet': plain[:160], 'trans': re.sub(r'<[^>]+>', '', trans.group(1)).strip()[:120] if trans else ''})

# ---------- matching ----------
def compatible(lpos, bpos):
    if not lpos or not bpos: return None
    return bool(set(lpos) & set(bpos))

WORD = re.compile(r'[a-z]{4,}')
def same_word(a, b):
    """Two Bosworth-Toller homographs that are one word for our purposes:
    the same word as two parts of speech (a-bútan prep. and adv.;
    Norþ-hymbre n. and adj.), or a duplicate with the same meaning
    (Cinges tún, Cynges tún: KINGSTON)."""
    ga, gb = stems(a['eng']), stems(b['eng'])
    return bool(ga & gb)

FILLER = {'with', 'from', 'that', 'which', 'this', 'have', 'into', 'upon', 'used', 'person', 'thing',
          'something', 'anyone', 'other', 'make', 'made', 'take', 'give', 'place', 'what', 'when', 'where'}
def stems(eng):
    return {w[:6] for w in WORD.findall(eng.lower()) if w not in FILLER}

def skeleton(s):
    b = base(s).replace('þ', 't').replace('æ', 'a')
    return re.sub(r'(.)\1', r'\1', re.sub(r'[aeiouy]+', 'V', b))
by_skel = collections.defaultdict(list)
for e in bt:
    if not e['add']:
        by_skel[skeleton(e['orth'])].append(e)

def pack(e, shared):
    return {'id': e['id'], 'orth': e['orth'], 'add': e['add'], 'pos': e['pos'], 'eng': e['eng'], 'shared': shared}

def primary(eng):
    return '; '.join(eng.split(';')[:2])

def supplements(main):
    """The Supplement/Addenda entries for a main entry: same spelling, same
    capitalisation (Dene the Danes, not dene a valley), and no other part of speech."""
    out = []
    for e in by_base.get(main['b'], []):
        if not e['add'] or e['cap'] != main['cap']:
            continue
        if e['pos'] and main['pos'] and not set(e['pos']) & set(main['pos']):
            continue
        # A Supplement entry with a meaning of its own belongs to another homograph (wer: a weir).
        own = re.sub(r'^\W*(add|take)\b.*', '', e['eng'], flags=re.I).strip()
        if e['has_eq'] and own and main['eng'] and not stems(own) & stems(main['eng']):
            continue
        out.append(e)
    return out

def same_word_elsewhere(main, taken):
    """Bosworth-Toller's other spellings of the same word (Dæne for Dene,
    Cynges tún for Cinges tún): same consonants, same part of speech, same meaning."""
    out = []
    for e in by_skel.get(skeleton(main['orth']), []):
        if e['id'] in taken or e['cap'] != main['cap']:
            continue
        if e['pos'] and main['pos'] and set(e['pos']) & set(main['pos']) and stems(primary(main['eng'])) & stems(primary(e['eng'])):
            out.append(e)
    return out

def match_one(L):
    vars_ = {v for v in lieb_variants(L['hw']) if base(v)}
    tier, cands = None, []
    guesses = set()
    for v in vars_:
        guesses |= lemma_guesses(base(v), L['pos'])
    for t, index, key, pool in (('spelling', by_base, base, vars_), ('variant spelling', by_loose, loose, vars_),
                                ('without ge-', by_noge, lambda v: nogé(loose(v)), vars_),
                                ('inflected form', by_loose, loose, guesses)):
        seen = {}
        for v in pool:
            for e in index.get(key(v), []):
                seen[e['id']] = e
        if seen:
            tier, cands = t, list(seen.values())
            break
    scored = []
    for e in cands:
        shared = sorted(set(L['fams']) & set(e['fams']))
        comp = compatible(L['pos'], e['pos'])
        score = (3 if shared else 0) + (1 if comp else -2 if comp is False else 0)
        scored.append((score, e, shared, comp))
    scored.sort(key=lambda x: (-x[0], x[1]['add'], int(x[1]['id'])))
    mains = [x for x in scored if not x[1]['add']]
    if not mains:
        return tier, ('unsure' if scored else 'none'), ([[pack(x[1], x[2]) for x in scored[:1]]] if scored else [])
    top = mains[0]
    tied = [x for x in mains[1:] if x[0] == top[0]]
    # Homographs that are really one word go together in the first group.
    group = [top] + [x for x in tied if same_word(top[1], x[1]) and x[3] is not False]
    rivals = [x for x in tied if x not in group]
    if tier == 'spelling' and not rivals and top[3] is not False:
        grade = 'sure' if (top[2] or len(mains) == len(group)) and len(group) == 1 else 'likely'
    elif tier == 'spelling' and not rivals:
        grade = 'unsure'
    elif not rivals and tier == 'variant spelling' and (top[2] or len(mains) == len(group)) and top[3] is not False:
        grade = 'likely'
    elif not rivals and tier == 'inflected form' and (top[2] or len(mains) == len(group)) and top[3] is True:
        grade = 'likely'
    else:
        grade = 'unsure'
    first, taken = [], set()
    def put(e, shared):
        if e['id'] not in taken:
            first.append(pack(e, shared)); taken.add(e['id'])
            for y in supplements(e):
                if y['id'] not in taken:
                    first.append(pack(y, [])); taken.add(y['id'])
    for x in group:
        put(x[1], x[2])
    for x in group:
        for e in same_word_elsewhere(x[1], taken):
            put(e, sorted(set(L['fams']) & set(e['fams'])))
    groups = [first]
    # Bosworth-Toller's other spellings of the chosen word (Dæne for Dene).
    for x in group:
        for e in pointed_from.get(x[1]['id'], []):
            if e['id'] not in taken and (set(e['pos']) & set(x[1]['pos']) or not e['pos']):
                groups.append([pack(e, [])]); taken.add(e['id'])
    for x in mains:
        if x[1]['id'] not in taken and len(groups) < 8:
            groups.append([pack(x[1], x[2])]); taken.add(x[1]['id'])
    return tier, grade, groups

results = []
by_hw = collections.defaultdict(list)
for L in lieb:
    # Prefixes, suffixes and spelling notes (Æl-, -cch, -ry-) are not words.
    if re.search(r'^\[?-|-\]?$', L['hw'].strip()):
        results.append({**L, 'tier': None, 'grade': 'none', 'groups': [], 'fragment': True})
        continue
    tier, grade, groups = match_one(L)
    r = {**L, 'tier': tier, 'grade': grade, 'groups': groups}
    results.append(r)
    by_hw[base(L['hw'])].append(r)

# Liebermann's own cross-references: "Hyne s. Ine", "Deona s. Dene, gn",
# "abutan s. onbuton". The word he points to is the one to link.
for r in results:
    if r.get('fragment'):
        continue
    m = re.match(r'\s*\S+(?:,\s*[^|]*?)?\s+s\.\s+([^\s,;.|~\]\[()]+)\b', r['snippet'])
    if not m or len(r['snippet']) > 70:
        continue
    targets = [t for t in by_hw.get(base(m.group(1)), []) if t is not r and t['groups']]
    if not targets:
        continue
    via = []
    for t in targets:
        via += [g for g in t['groups'][:1]]
    taken = {c['id'] for g in via for c in g}
    rest = [[c for c in g if c['id'] not in taken] for g in r['groups']]
    tgrade = 'likely' if len(targets) == 1 and targets[0]['grade'] in ('sure', 'likely') else 'unsure'
    # A word that also matches by its own spelling keeps that as the first choice
    # only if it is the same word (it already contains the target's entry).
    r['groups'] = via + [g for g in rest if g]
    r['tier'] = 'cross-reference to ' + m.group(1)
    r['grade'] = tgrade
    for t in targets:
        for x in t['groups'][1:2]:
            pass

json.dump(results, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False)
c = collections.Counter(r['grade'] for r in results)
print(len(results), dict(c))
print(collections.Counter((r['grade'], (r['tier'] or '').split(' to ')[0]) for r in results))
