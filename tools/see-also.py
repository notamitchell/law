#!/usr/bin/env python3
"""
Makes the "See also" links of dictionary entries from Liebermann's own
cross-references.

    python3 tools/see-also.py --dry-run          # report only
    python3 tools/see-also.py                    # change the entries
    python3 tools/see-also.py --only a aa abbod  # just these entries

Liebermann sends the reader to another entry in two ways, and both are found
in the text of an entry (the <dictScrap type="liebermann">):

  s. WORD       "siehe": the headword, or a comma-separated list of
                headwords, straight after the italic abbreviation
                ("læde s. lad", "Genetivus ... s. asittan, aslacian").
  ... s. d.     "siehe dort": the word or words just before it, in roman
                type, between the italic German words ("ā geschrieben aa
                s. d." sends the reader to aa).

Each one found becomes <xr type="see"><ref target="entry:ID">headword</ref></xr>.
How a word is matched to an entry, in order:
  - the headword exactly, ignoring accents, or as one of the spellings a
    bracketed headword stands for (g[e]noh is genoh or gnoh);
  - a ~ is filled in from the entry's own headword(s): under [-feald], anf~ is
    anfeald; under hunteontig, hund~ is hundteontig;
  - a prefix or suffix with no entry of its own (heah-, -sceatt) goes to the
    word itself (heah, sceatt);
  - otherwise one usual spelling difference (ceapman / ceapmon, i / ie / y);
  - where several entries share the headword: the one numbered by a following
    I or II ("s. ure n. II"), else the one in the same language or with the
    same F / L mark, else all of them, told apart by Liebermann's first gloss.
Links a person has checked and found wrong are listed in SKIP. The report says
what was linked by a guess (to check) and what could not be linked, and why.
An entry is never linked to itself.

Existing "See also" links are kept, with one exception: a link to the entry d
is removed when the entry has "s. d." in it, since the programming that made
it read "s. d." as "see d". (They were all mistakes.)

The other kinds of cross-reference (s. o. "siehe oben", s. u. "siehe unten",
s. n., s. z., s. d. u., s. d. n.) are counted in the report but not linked.

With --compare it makes the "Compare" links instead, from Liebermann's
"vgl." / "Vgl." (vergleiche, compare): the headword or comma-separated
headwords straight after it ("vgl. heafod n. 3", "Vgl. soinus, sonet"),
matched in the same way, become <xr type="compare">…</xr>, listed after the
See links. A pointer to a section ("n. 3", "n. II") after the word is not
part of the headword. Report: docs/compare-report.md.

Writes docs/see-also-report.md (use --no-report to skip). Needs only Python 3.
Safe to run again.
"""
import argparse
import collections
import glob
import html
import os
import re
import sys
import unicodedata

SIEHE = {'siehe': 'after', 'sieheDort': 'before'}      # kinds that are linked, and where the target is
OTHER = ('sieheOben', 'sieheUnten', 'sieheNummer', 'sieheZu', 'sieheDN', 'sieheDortUnter')

ABBR = re.compile(r'(?P<open><hi rend="italic">)?<ref type="abbreviation" target="gram:(?P<kind>siehe\w*)"><abbr>(?P<text>[^<]*)</abbr></ref>')
XRTYPE = 'see'
COMPARE = False
ORTH = re.compile(r'<orth>(.*?)</orth>', re.S)
SCRAP = re.compile(r'(<dictScrap type="liebermann">)(.*?)(</dictScrap>)', re.S)
SEE = re.compile(r'^[ \t]*<xr type="see"><ref target="entry:([^"]*)">.*?</ref></xr>[ \t]*\n', re.M)
SEE_ANY = re.compile(r'^[ \t]*<xr type="see"><ref target="entry:[^"]*">.*?</ref></xr>[ \t]*\n', re.M)
WORD = re.compile(r"[^\s,;:|(){}\[\]*_«»⟦⟧<>=+/]+")


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def fold(s):
    s = unicodedata.normalize('NFD', s.lower()).replace('ð', 'þ')
    return ''.join(c for c in s if not unicodedata.combining(c))


# Links the tool would make that a person has checked and found wrong:
# (entry, target). The near spellings and stems are guesses, and these missed.
SKIP = {
    ('Pars', 'helm'), ('ae-4', 'helm'), ('haelm', 'helm'),        # healm is not helm
    ('Consonanten', 'l'), ('l-2', 'l'),                          # ll: the double letter
    ('maector', 'mete'),                                         # mæte is not mete
    ('fiht', 'f-re-ht'), ('fyht', 'f-re-ht'),                    # feoht is not freht
    ('Fremdwort-Declination', 'tu-sc'), ('Fremdwort-Declination', 'te'),
    ('cs', 'g-o-s'), ('gar', 'waru'),
}

ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}
SECTION = re.compile(r'^\s*(?:<lbl[^>]*>[^<]*</lbl>\s*)?<hi rend="bold">(I|II|III|IV|V)</hi>\)')


def spellings(hw):
    """The forms a headword with Liebermann's brackets stands for:
    g[e]noh -> genoh, gnoh; aw[ie]rdan -> awierdan, awrdan, awirdan, awerdan;
    mon(n)- -> monn-, mon-."""
    parts = re.split(r'(\[[^\]]*\]|\([^)]*\))', hw)
    forms = ['']
    for part in parts:
        if re.fullmatch(r'\[[^\]]*\]|\([^)]*\)', part or ''):
            inner = part[1:-1]
            opts = {inner}
            if part.startswith('('):
                opts.add('')                # heal(swa): healswa or heal
            elif len(inner) > 1 and inner.isalpha():
                opts.update(inner)          # [ie]: ie, i or e
            else:
                opts.add('')                # g[e]noh: genoh or gnoh
            forms = [f + o for f in forms for o in opts]
        else:
            forms = [f + part for f in forms]
        if len(forms) > 64:
            break
    return {f for f in forms if f}


def respellings(word):
    """Common spelling differences between Liebermann's cross-references and
    his headwords (ceapman / ceapmon, cierr / cyrr, ...): one change at a time."""
    swaps = [('an', 'on'), ('on', 'an'), ('ie', 'i'), ('ie', 'y'), ('i', 'ie'), ('y', 'ie'), ('i', 'y'), ('y', 'i'),
             ('æ', 'e'), ('e', 'æ'), ('ea', 'e'), ('eo', 'e'), ('io', 'eo'), ('eo', 'io'), ('u', 'o'), ('o', 'u'),
             ('c', 'k'), ('k', 'c'), ('nn', 'n'), ('ll', 'l'), ('n', 'nn'), ('l', 'll'), ('tt', 't'), ('t', 'tt'),
             ('mm', 'm'), ('ss', 's'), ('dd', 'd'), ('gg', 'g')]
    out = set()
    for a, b in swaps:
        for m in re.finditer(re.escape(a), word):
            out.add(word[:m.start()] + b + word[m.end():])
    out.discard(word)
    return out


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class Index:
    """Headword -> entry ids, for every file in entries/."""
    def __init__(self, directory):
        self.hw = {}
        self.exact = collections.defaultdict(list)
        self.folded = collections.defaultdict(list)
        self.variant = collections.defaultdict(list)
        self.lang = {}
        self.section = {}
        self.pointer = set()
        self.mark = {}
        self.gloss = {}
        for path in sorted(glob.glob(os.path.join(directory, '*.xml'))):
            text = read(path)
            m = ORTH.search(text)
            if not m:
                continue
            id_ = os.path.basename(path)[:-4]
            lm = re.search(r'<entry xml:lang="([^"]*)"', text)
            self.lang[id_] = lm.group(1) if lm else ''
            sm = SCRAP.search(text)
            nm = SECTION.match(sm.group(2)) if sm else None
            # Liebermann's first italic word after the headword ("vb", "Recht"),
            # to tell apart entries that share a headword
            for gm in re.finditer(r'<hi rend="italic">(.*?)</hi>', sm.group(2) if sm else ''):
                g = html.unescape(re.sub(r'<[^>]+>', '', gm.group(1))).strip(' ,;:.[]()')
                if len(re.sub(r'\W', '', g)) < 2 or g.startswith('s.') or g in ('s', 'vgl'):
                    continue
                self.gloss[id_] = g if len(g) <= 24 else g[:22].rsplit(' ', 1)[0] + '…'
                break
            # Liebermann's L / F before a headword (Latin, French)
            lb = re.match(r'\s*<lbl type="language">([^<]*)</lbl>', sm.group(2)) if sm else None
            self.mark[id_] = lb.group(1).strip() if lb else ''
            # an entry that is only a pointer elsewhere ("hwirfe s. hwier~")
            if sm:
                body = re.sub(r'<hi rend="bold">.*?</hi>', '', sm.group(2), count=1)
                body = html.unescape(re.sub(r'<[^>]+>', '', body)).strip(' ,')
                if body.startswith('s.') and len(body) < 60:
                    self.pointer.add(id_)
            # an entry joined from Liebermann's numbered sections (þæt I–IV) is
            # one entry: it is not labelled by its first section
            if nm and not re.search(r'<hi rend="bold">(?:II|III|IV|V)</hi>\)', sm.group(2)[nm.end():]):
                self.section[id_] = nm.group(1)
            hw = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
            self.hw[id_] = hw
            # Names that are not in the text of the laws are headed [Wiht]; a
            # reference to them has no brackets.
            plain = re.sub(r'^\[(.*)\]$', r'\1', hw)
            self.exact[plain].append(id_)
            self.folded[fold(plain)].append(id_)
            for form in spellings(plain):
                if form != plain and id_ not in self.variant[fold(form)]:
                    self.variant[fold(form)].append(id_)

    def lookup(self, word):
        """Every entry with this headword (exactly, then ignoring accents, then
        as one of the spellings a bracketed headword stands for)."""
        for table, key in ((self.exact, word), (self.folded, fold(word)), (self.variant, fold(word))):
            if table.get(key):
                return list(table[key])
        return []

    def label(self, id_):
        hw = re.sub(r'^\[(.*)\]$', r'\1', self.hw.get(id_, id_))
        return hw + (' ' + self.section[id_] if id_ in self.section else '')

    def find(self, word, lang='', numeral='', mark=None):
        """-> (list of ids, why not / how)"""
        ids = self.lookup(word)
        how = ''
        if not ids:
            # A prefix or suffix (heah-, -sceatt) with no entry of its own: the
            # entry for the word itself.
            bare = word.strip('-')
            if bare != word and len(bare) > 2:
                ids = self.lookup(bare)
                how = 'linked to the word without the hyphen' if ids else ''
        if not ids:
            cands = sorted({i for r in respellings(fold(word)) for i in self.lookup(r) if i not in self.pointer})
            if len(cands) == 1:
                return cands, 'linked by a near spelling: ' + self.hw[cands[0]]
            if cands:
                return [], 'no entry with this headword; near spellings: ' + ', '.join(cands)
            return [], 'no entry with this headword (yet)'
        if len(ids) == 1:
            return ids, how
        if numeral:
            pick = [i for i in ids if self.section.get(i) == numeral]
            if len(pick) == 1:
                return pick, how
        same = [i for i in ids if self.lang.get(i) == lang]
        if len(same) == 1:
            return same, how
        if same:
            ids = same
        if mark is not None:
            same = [i for i in ids if self.mark.get(i, '') == mark]
            if len(same) == 1:
                return same, how
            if same:
                ids = same
        return ids, 'several entries have this headword, all linked: ' + ', '.join(ids)


def words(text, backwards=False):
    """The list of words in a stretch of plain text, where the words are
    separated by commas: 'ea, o' -> ['ea', 'o']. Going forwards it stops at the
    first thing that is not a word or comma; going backwards, at the last."""
    out = []
    words.left = words.right = ''
    if not backwards:
        rest = text
        while True:
            m = re.match(r'\s*(' + WORD.pattern + ')', rest)
            if not m:
                break
            out.append(m.group(1))
            rest = rest[m.end():]
            if not re.match(r'\s*,\s*(?=\S)', rest) or re.match(r'\s*,\s*[(\[]', rest):
                break
            rest = re.sub(r'^\s*,', '', rest)
        words.right = rest
        return out
    rest = text.rstrip()
    m = re.search('(' + WORD.pattern + r')[\s.;:,]*$', rest)
    if m:
        out.append(m.group(1))
        rest = rest[:m.start()]
        while re.search(r',\s*$', rest):          # more words in the same comma-separated list
            m = re.search('(' + WORD.pattern + r')\s*,\s*$', rest)
            if not m:
                break
            out.append(m.group(1))
            rest = rest[:m.start()]
        words.left = rest                           # what is in front of the list
    return out[::-1]


def clean(token):
    return token.strip().rstrip('.,;:')


def headwords(scrap, index, entry_id):
    """The entry's own headword(s), for filling in a ~: the orth, and any other
    bold words before Liebermann's first abbreviation ("wys, wyssian")."""
    out = [index.hw.get(entry_id, '')]
    head = scrap.split('<ref type="abbreviation"', 1)[0]
    out += [html.unescape(re.sub(r'<[^>]+>', '', h)) for h in re.findall(r'<hi rend="bold">(.*?)</hi>', head)]
    forms = []
    for h in out:
        h = h.strip().strip('[]').strip().rstrip(',').strip('-')
        if h and not re.fullmatch(r'[IVX]+|\d+[a-z]?', h):
            for f in spellings(h) | {re.sub(r'[\[\]()]', '', h)}:
                if f not in forms:
                    forms.append(f)
    return forms


def tilde(word, h):
    """Liebermann's ~ stands for letters of the headword h: under [-feald],
    anf~ is anfeald; under Bernaba, Bar~ is Barnaba; under ciepemon, ~nna is
    ciepemonna; under hunteontig, hund~ is hundteontig. -> the possible
    spellings, the likeliest (where a letter is shared) first. The ~ always
    stands for at least one letter."""
    pre, _, post = word.partition('~')
    first, second = [], []
    if not pre and not post:
        return [], []
    if pre and post:
        return [pre + h + post], []
    for k in range(1, len(h)):
        if pre:
            stands, shared = len(h) - k, pre[-1].lower() == h[k - 1].lower()
            cand = pre + h[k:]
        else:
            stands, shared = k, post[0].lower() == h[k].lower()
            cand = h[:k] + post
        # the ~ stands for a fair part of the headword: two letters at least
        # where a letter is shared, more than half the word where none is
        if shared and stands >= min(2, len(h) - 1):
            first.append(cand)
        elif not shared and 2 * stands > len(h):
            second.append(cand)
    if pre:
        second.append(pre + h)
    return first, second


def resolve(word, index, lang, numeral, heads, entry_id=''):
    """-> (ids, why/how, shown)"""
    if '~' in word:
        picked, seen, tried = [], [], []
        for h in heads:
            got = tilde(word, h)
            # where no likely spelling is a headword, try them with the usual
            # spelling differences (ungielde -> ung[i]lde) before the less likely ones
            got = (got[0], sorted({r for c in got[0] for r in respellings(c)}), got[1])
            for n, group in enumerate(got):
                found = {}
                for cand in group:
                    tried.append(cand)
                    ids = [i for i in index.lookup(cand) if i != entry_id and not (n == 1 and i in index.pointer)]
                    if ids:
                        found.setdefault(tuple(ids), cand)
                if len(found) == 1:
                    picked.append(list(found.values())[0])
                    break
                if found:
                    seen += list(found.values())
                    break
        picked = list(dict.fromkeys(picked))
        # several headwords, several readings: keep those in the entry's own language
        same = [c for c in picked if any(index.lang.get(i) == lang for i in index.lookup(c))]
        if same:
            picked = same
        if picked and len(picked) <= 3:
            ids, whys = [], []
            for cand in picked:
                got, why = index.find(cand, lang, numeral, index.mark.get(entry_id, ''))
                got = [i for i in got if i != entry_id] or [i for i in index.lookup(cand) if i != entry_id]
                ids += [i for i in got if i not in ids]
            return ids, '~ read as ' + ', '.join(picked), ' / '.join(picked)
        if seen:
            return [], 'only the start or end of a word: ~ could be ' + ', '.join(seen), word
        return [], 'only the start or end of a word: no entry for it', word
    if re.search(r'\d', word):
        return [], 'a number, not a headword', word
    ids, why = index.find(word, lang, numeral, index.mark.get(entry_id, ''))
    return ids, why, word


def targets(scrap, entry_id, index):
    """Every cross-reference in an entry's text:
    [(kind, shown text, [ids], why not / how)]"""
    found = []
    lang = index.lang.get(entry_id, '')
    # A headword that is also a law code (Ine, Wiht ...) is linked as one in the
    # text; for finding the word, that link is only the word.
    scrap = re.sub(r'<ref type="lawCode" target="[^"]*">([^<]*)</ref>', r'\1', scrap)
    heads = headwords(scrap, index, entry_id)
    for m in ABBR.finditer(scrap):
        kind = m.group('kind')
        if kind in OTHER:
            found.append((kind, m.group('text'), [], 'not linked: ' + kind))
            continue
        if kind not in SIEHE:
            continue
        after = ''
        if SIEHE[kind] == 'after':
            tail = scrap[m.end():]
            if COMPARE and tail.startswith('.'):
                tail = tail[1:]                 # "vgl</abbr></ref>.": the full stop is outside the link
            if tail.startswith('</hi>'):
                tail = tail[5:]
            node = re.split(r'<', tail, maxsplit=1)[0]
            if not node[:1].isspace():
                found.append((kind, '', [], 'nothing follows'))
                continue
            toks = words(node)
            after = words.right + tail[len(node):]
        else:
            head = scrap[:m.start()]
            node = re.split(r'>', head[::-1], maxsplit=1)[0][::-1] if '>' in head else head
            before = head[:len(head) - len(node)]
            # "pares [s. d.]": the bracket belongs to the s. d.
            node = re.sub(r'\[\s*$', '', node)
            toks = words(html.unescape(node), backwards=True)
            if len(toks) > 1 and before.endswith('</hi>') and re.search(r'<hi rend="bold">[^<]*</hi>$', before) \
                    and node.lstrip().startswith(toks[0]):
                toks = toks[1:]     # "hereditaria terra, bocland": terra belongs to the headword
        # "s. ure n. II", "s. riht II": which of several entries
        plain_after = html.unescape(re.sub(r'<[^>]+>', '', after))
        if COMPARE:
            # "vgl. heafod n. 3", "vgl. oð (n. I C) þæt": a pointer to a section is not part of the word
            sec = re.match(r'\s*\(?n\.\s*[IVX\d][\w ,]*\)?', plain_after)
            if sec and toks:
                words.right = re.sub(r'^\s*\(?n\.\s*[IVX\d][\w ,]*\)?', '', html.unescape(re.sub(r'<[^>]+>', '', words.right)))
                nm2 = re.match(r'\s*\(?n\.\s*(I{1,3}|IV|V)\b', plain_after)
                plain_after = (' ' + nm2.group(1)) if nm2 else ''
        nm = re.match(r'\s*(?:n\.\s*)?(I{1,3}|IV|V)\b(?!\s*\))', plain_after)
        numeral = nm.group(1) if nm else ''
        if nm:
            words.right = words.right[len(words.right) - len(words.right.lstrip()):]
            words.right = re.sub(r'^\s*(?:n\.\s*)?(I{1,3}|IV|V)\b', '', words.right)
        phrase = bool(toks) and (
            (SIEHE[kind] == 'after' and not numeral and re.match(r"\s+[^\W\d_]", words.right)) or
            (SIEHE[kind] == 'before' and re.search(r"[^\W\d_][\w'’.]*\s+$", words.left)))
        if not toks:
            found.append((kind, '', [], 'no word found'))
        elif phrase:
            found.append((kind, ' '.join(toks), [], 'part of a longer phrase, not a single headword'))
            toks = []
        if COMPARE and toks:
            right = html.unescape(re.sub(r'<[^>]+>', '', words.right))
            if re.match(r'\s+\d', right) or right.startswith('('):
                # "vgl. Ine 75": a citation; "ma(a)nsceaða": the word goes on
                found.append((kind, ' '.join(toks), [], 'a citation or a longer word, not a headword'))
                toks = []
        for i, tok in enumerate(toks):
            word = clean(html.unescape(tok))
            if not word:
                continue
            if COMPARE and len(word.strip('-')) <= 1:
                found.append((kind, word, [], 'a single letter, not a headword'))
                continue
            ids, why, shown = resolve(word, index, lang, numeral if i == len(toks) - 1 else '', heads, entry_id)
            if any((entry_id, x) in SKIP for x in ids):
                ids = [x for x in ids if (entry_id, x) not in SKIP]
                why = why or 'checked and found wrong'
            if entry_id in ids:
                ids = [x for x in ids if x != entry_id]
                why = why or 'this entry itself'
            found.append((kind, shown, ids, why))
    return found


def labels(final, index):
    """The text of each link; where two would read the same, Liebermann's
    first gloss is added: aveir (vb), aveir (sbst)."""
    out = [index.label(i) for i in final]
    for n, l in enumerate(out):
        if out.count(l) > 1 or [index.label(i) for i in final].count(index.label(final[n])) > 1:
            g = index.gloss.get(final[n])
            out[n] = l + (' (' + g + ')' if g else '')
    return [esc(l) for l in out]


def block_labels_ok(text, final, index):
    shown = re.findall(r'<xr type="%s"><ref target="entry:[^"]*">(.*?)</ref></xr>' % XRTYPE, text)
    return shown == labels(final, index)


def update(path, index, write):
    """-> (changed, links added, links removed, found)"""
    text = read(path)
    entry_id = os.path.basename(path)[:-4]
    m = SCRAP.search(text)
    if not m:
        return False, [], [], []
    found = targets(m.group(2), entry_id, index)
    want = []
    for kind, shown, ids, why in found:
        for id_ in ids:
            if id_ not in want:
                want.append(id_)
    existing = SEE.findall(text)
    has_dort = any(k == 'sieheDort' for k, _, _, _ in found)
    removed = [x for x in existing if x == 'd' and has_dort and x not in want]
    kept = [x for x in existing if x not in removed]
    final = want + [x for x in kept if x not in want]
    if final == existing and block_labels_ok(text, final, index):
        return False, [], [], found
    block = ''.join('        <xr type="%s"><ref target="entry:%s">%s</ref></xr>\n' % (XRTYPE, i, l) for i, l in zip(final, labels(final, index)))
    new = SEE.sub('', text)
    if COMPARE:
        # after the See links, before the rest
        sees = list(SEE_ANY.finditer(new))
        first_xr = re.search(r'^[ \t]*<xr (?!type="see")', new[sees[-1].end():] if sees else new, re.M)
        if first_xr and sees:
            at = sees[-1].end() + first_xr.start()
            new = new[:at] + block + new[at:]
            first_xr = None
        elif sees:
            at = sees[-1].end(); new = new[:at] + block + new[at:]; first_xr = None
        elif first_xr:
            new = new[:first_xr.start()] + block + new[first_xr.start():]; first_xr = None
        else:
            end = re.search(r'^[ \t]*</entry>', new, re.M)
            if not end:
                return False, [], [], found
            new = new[:end.start()] + block + new[end.start():]
        if write:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(new)
        return True, [x for x in want if x not in existing], removed, found
    first_xr = re.search(r'^[ \t]*<xr ', new, re.M)
    if first_xr:
        new = new[:first_xr.start()] + block + new[first_xr.start():]
    else:
        end = re.search(r'^[ \t]*</entry>', new, re.M)
        if not end:
            return False, [], [], found
        new = new[:end.start()] + block + new[end.start():]
    if write:
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(new)
    return True, [x for x in want if x not in existing], removed, found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--only', nargs='*', help='entry ids; the default is every entry')
    ap.add_argument('--entries', default='entries')
    ap.add_argument('--report', default='docs/see-also-report.md')
    ap.add_argument('--no-report', action='store_true')
    ap.add_argument('--show', action='store_true', help='print what was found in each entry')
    ap.add_argument('--compare', action='store_true', help='make the Compare links from "vgl." instead of the See links')
    args = ap.parse_args()
    if args.compare:
        global SIEHE, OTHER, ABBR, SEE, XRTYPE, COMPARE
        SIEHE, OTHER, XRTYPE, COMPARE = {'vergleiche': 'after'}, (), 'compare', True
        ABBR = re.compile(r'(?P<open><hi rend="italic">)?<ref type="abbreviation" target="gram:(?P<kind>vergleiche)"><abbr>(?P<text>[^<]*)</abbr></ref>')
        SEE = re.compile(r'^[ \t]*<xr type="compare"><ref target="entry:([^"]*)">.*?</ref></xr>[ \t]*\n', re.M)
        if args.report == 'docs/see-also-report.md':
            args.report = 'docs/compare-report.md'

    index = Index(args.entries)
    paths = [os.path.join(args.entries, i + '.xml') for i in args.only] if args.only else sorted(glob.glob(os.path.join(args.entries, '*.xml')))
    tally = collections.Counter()
    problems = collections.defaultdict(list)
    changed = added = removed = 0
    for path in paths:
        ch, add, rem, found = update(path, index, not args.dry_run)
        entry_id = os.path.basename(path)[:-4]
        if args.show:
            for kind, shown, ids, why in found:
                print('  %-12s %-20s -> %s %s' % (entry_id, shown, ','.join(ids) or '-', why))
        changed += ch
        added += len(add)
        removed += len(rem)
        for kind, shown, ids, why in found:
            tally[(kind, 'linked' if ids else 'not linked')] += 1
            if kind in SIEHE and why:
                key = ('linked, ' if ids else 'not linked, ') + re.sub(r'^~ read as.*', '~ filled in from the headword', why.split(':')[0].split(';')[0])
                problems[key].append((entry_id, shown, why))

    lines = ['Entries: %d; changed: %d; links added: %d; wrong links removed: %d' % (len(paths), changed, added, removed)]
    for kind in list(SIEHE) + list(OTHER):
        l, n = tally[(kind, 'linked')], tally[(kind, 'not linked')]
        if l or n:
            lines.append('  %-15s found %5d, linked %5d' % (kind, l + n, l))
    for key, items in sorted(problems.items(), key=lambda kv: -len(kv[1])):
        lines.append('  %-57s %5d' % (key, len(items)))
    print('\n'.join(lines))
    print('(dry run: no files changed)' if args.dry_run else '(entries updated)')

    if not args.no_report and not args.only:
        with open(args.report, 'w', encoding='utf-8', newline='\n') as f:
            f.write('# %s links made from Liebermann\'s cross-references\n\n' % ('Compare' if COMPARE else 'See also'))
            f.write('Made by `tools/see-also.py`. It is replaced each time the tool runs.\n\n```\n%s\n```\n\n' % '\n'.join(lines))
            for key, items in sorted(problems.items(), key=lambda kv: -len(kv[1])):
                if 'this entry' in key:
                    continue
                f.write('## %s (%d)\n\n' % (key.capitalize(), len(items)))
                shown = items
                for entry_id, word, why in shown:
                    extra = why.split(': ', 1)[1] if ': ' in why else ''
                    f.write('- **%s**: %s %s%s\n' % (entry_id, 'vgl.' if COMPARE else 's.', word, ' (' + extra + ')' if extra else ''))
                if len(shown) < len(items):
                    f.write('- … and %d more\n' % (len(items) - len(shown)))
                f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
