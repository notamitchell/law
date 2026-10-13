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
A target is linked only when exactly one entry has that headword. Otherwise
nothing is linked, and the report says why (no such entry yet, a headword
shared by several entries, a word ending in a hyphen or ~, ...), so that a
person can decide. An entry is never linked to itself.

Existing "See also" links are kept, with one exception: a link to the entry d
is removed when the entry has "s. d." in it, since the programming that made
it read "s. d." as "see d". (They were all mistakes.)

The other kinds of cross-reference (s. o. "siehe oben", s. u. "siehe unten",
s. n., s. z., s. d. u., s. d. n.) are counted in the report but not linked.

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
ORTH = re.compile(r'<orth>(.*?)</orth>', re.S)
SCRAP = re.compile(r'(<dictScrap type="liebermann">)(.*?)(</dictScrap>)', re.S)
SEE = re.compile(r'^[ \t]*<xr type="see"><ref target="entry:([^"]*)">.*?</ref></xr>[ \t]*\n', re.M)
WORD = re.compile(r"[^\s,;:|(){}\[\]*_«»⟦⟧<>=+/]+")


def read(path):
    with open(path, encoding='utf-8', newline='') as f:
        return f.read()


def fold(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class Index:
    """Headword -> entry ids, for every file in entries/."""
    def __init__(self, directory):
        self.hw = {}
        self.exact = collections.defaultdict(list)
        self.folded = collections.defaultdict(list)
        for path in sorted(glob.glob(os.path.join(directory, '*.xml'))):
            m = ORTH.search(read(path))
            if not m:
                continue
            id_ = os.path.basename(path)[:-4]
            hw = html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()
            self.hw[id_] = hw
            # Names that are not in the text of the laws are headed [Wiht]; a
            # reference to them has no brackets.
            plain = re.sub(r'^\[(.*)\]$', r'\1', hw)
            self.exact[plain].append(id_)
            self.folded[fold(plain)].append(id_)

    def find(self, word):
        """-> (id or None, why not)"""
        for table, key in ((self.exact, word), (self.folded, fold(word))):
            ids = table.get(key)
            if ids:
                if len(ids) == 1:
                    return ids[0], ''
                return None, 'several entries have this headword: ' + ', '.join(ids)
        return None, 'no entry with this headword (yet)'


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


def targets(scrap, entry_id, index):
    """Every cross-reference in an entry's text:
    [(kind, shown text, id or None, why not)]"""
    found = []
    # A headword that is also a law code (Ine, Wiht ...) is linked as one in the
    # text; for finding the word, that link is only the word.
    scrap = re.sub(r'<ref type="lawCode" target="[^"]*">([^<]*)</ref>', r'\1', scrap)
    for m in ABBR.finditer(scrap):
        kind = m.group('kind')
        if kind in OTHER:
            found.append((kind, m.group('text'), None, 'not linked: ' + kind))
            continue
        if kind not in SIEHE:
            continue
        if SIEHE[kind] == 'after':
            tail = scrap[m.end():]
            if tail.startswith('</hi>'):
                tail = tail[5:]
            node = re.split(r'<', tail, maxsplit=1)[0]
            if not node[:1].isspace():
                found.append((kind, '', None, 'nothing follows'))
                continue
            toks = words(node)
        else:
            head = scrap[:m.start()]
            node = re.split(r'>', head[::-1], maxsplit=1)[0][::-1] if '>' in head else head
            before = head[:len(head) - len(node)]
            toks = words(html.unescape(node), backwards=True)
            if toks and node.strip() == toks[0] and before.endswith('</hi>') and re.search(r'<hi rend="bold">[^<]*</hi>$', before):
                pass
            if len(toks) > 1 and before.endswith('</hi>') and re.search(r'<hi rend="bold">[^<]*</hi>$', before) \
                    and node.lstrip().startswith(toks[0]):
                toks = toks[1:]     # "hereditaria terra, bocland": terra belongs to the headword
        phrase = bool(toks) and (
            (SIEHE[kind] == 'after' and re.match(r"\s+[^\W\d_]", words.right)) or
            (SIEHE[kind] == 'before' and re.search(r"[^\W\d_][\w'’.]*\s+$", words.left)))
        if not toks:
            found.append((kind, '', None, 'no word found'))
        elif phrase:
            found.append((kind, ' '.join(toks), None, 'part of a longer phrase, not a single headword'))
            toks = []
        for tok in toks:
            word = clean(html.unescape(tok))
            if not word:
                continue
            id_, why = index.find(word)
            if not id_ and re.search(r'^[-~]|[-~]$|~', word) and 'several' not in why:
                why = 'only the start or end of a word'
            elif not id_ and re.search(r'\d', word) and 'several' not in why:
                why = 'a number, not a headword'
            found.append((kind, word, id_ if id_ != entry_id else None, why or ('this entry itself' if id_ == entry_id else '')))
    return found


def update(path, index, write):
    """-> (changed, links added, links removed, found)"""
    text = read(path)
    entry_id = os.path.basename(path)[:-4]
    m = SCRAP.search(text)
    if not m:
        return False, [], [], []
    found = targets(m.group(2), entry_id, index)
    want = []
    for kind, shown, id_, why in found:
        if id_ and id_ not in want:
            want.append(id_)
    existing = SEE.findall(text)
    has_dort = any(k == 'sieheDort' for k, _, _, _ in found)
    removed = [x for x in existing if x == 'd' and has_dort and x not in want]
    kept = [x for x in existing if x not in removed]
    final = want + [x for x in kept if x not in want]
    if final == existing:
        return False, [], [], found
    block = ''.join('        <xr type="see"><ref target="entry:%s">%s</ref></xr>\n' % (i, esc(index.hw.get(i, i))) for i in final)
    new = SEE.sub('', text)
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
    args = ap.parse_args()

    index = Index(args.entries)
    paths = [os.path.join(args.entries, i + '.xml') for i in args.only] if args.only else sorted(glob.glob(os.path.join(args.entries, '*.xml')))
    tally = collections.Counter()
    problems = collections.defaultdict(list)
    changed = added = removed = 0
    for path in paths:
        ch, add, rem, found = update(path, index, not args.dry_run)
        entry_id = os.path.basename(path)[:-4]
        if args.show:
            for kind, shown, id_, why in found:
                print('  %-12s %-20s -> %s %s' % (entry_id, shown, id_ or '-', why))
        changed += ch
        added += len(add)
        removed += len(rem)
        for kind, shown, id_, why in found:
            tally[(kind, 'linked' if id_ else 'not linked')] += 1
            if not id_ and kind in SIEHE and why:
                key = why.split(':')[0]
                problems[key].append((entry_id, shown, why))

    lines = ['Entries: %d; changed: %d; links added: %d; wrong links removed: %d' % (len(paths), changed, added, removed)]
    for kind in list(SIEHE) + list(OTHER):
        l, n = tally[(kind, 'linked')], tally[(kind, 'not linked')]
        if l or n:
            lines.append('  %-15s found %5d, linked %5d' % (kind, l + n, l))
    for key, items in sorted(problems.items(), key=lambda kv: -len(kv[1])):
        lines.append('  not linked, %-45s %5d' % (key, len(items)))
    print('\n'.join(lines))
    print('(dry run: no files changed)' if args.dry_run else '(entries updated)')

    if not args.no_report and not args.only:
        with open(args.report, 'w', encoding='utf-8', newline='\n') as f:
            f.write('# See also links made from Liebermann\'s cross-references\n\n')
            f.write('Made by `tools/see-also.py`. It is replaced each time the tool runs.\n\n```\n%s\n```\n\n' % '\n'.join(lines))
            for key, items in sorted(problems.items(), key=lambda kv: -len(kv[1])):
                if key.startswith('this entry'):
                    continue
                f.write('## %s (%d)\n\n' % (key.capitalize(), len(items)))
                shown = items if key.startswith('several') else items[:150]
                for entry_id, word, why in shown:
                    extra = why.split(': ', 1)[1] if ': ' in why else ''
                    f.write('- **%s**: s. %s%s\n' % (entry_id, word, ' (' + extra + ')' if extra else ''))
                if len(shown) < len(items):
                    f.write('- … and %d more\n' % (len(items) - len(shown)))
                f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
