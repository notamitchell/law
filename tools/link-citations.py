#!/usr/bin/env python3
"""
Links the law code citations at the foot of dictionary entries to the clause
files in oe-laws/ (the Old English laws database).

    python3 tools/link-citations.py --letter A --dry-run   # report only
    python3 tools/link-citations.py --letter A             # make the links
    python3 tools/link-citations.py --letter all           # every letter

Each dictionary entry ends with a list of law code citations, such as
    <xr type="lawCode"><ref target="law:Ine">Ine 23,2</ref></xr>
For a citation whose clause has a file in oe-laws/, this changes the target to
    <ref target="clause:Ine_23-2">Ine 23,2</ref>
which the site turns into a link to law.html?id=Ine_23-2. The citation text is
not changed, and citations that find no clause are left as they were (they
still link to the law code list). Running it again is safe: citations already
linked are skipped.

Only entries whose headword is filed under --letter are touched (default A;
"all" for every entry).
The citations written in the entry text itself are not touched.

A citation finds its clause in three steps, and the report says which:
  exact       the code's Anchor and clause number match a clause file ("Ine 23,2")
  ms-letter   the same, once a manuscript letter after the number is ignored ("9 Q")
  subclause   the number has no file of its own but its parts do ("Abt 1" goes
              to 1[a]); it goes to the first part
  and-following  "Swer 7ff." or "7 f." (and following): to the first clause, Swer 7

Writes docs/oe-laws-link-report.md (use --no-report to skip) and needs only
Python 3.
"""
import argparse
import glob
import html
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

FOLD = {'æ': 'ae', 'Æ': 'Ae', 'þ': 'th', 'Þ': 'Th', 'ð': 'd', 'Ð': 'D', 'ƿ': 'w', 'Ƿ': 'W',
        'ȝ': 'g', 'Ȝ': 'G', 'ß': 'ss', 'œ': 'oe', 'Œ': 'Oe', '⁊': 'and', 'ꝥ': 'thaet', 'Ꝥ': 'Thaet'}

XR = re.compile(r'<xr type="lawCode"><ref target="law:(?P<anchor>[^"]+)">(?P<text>[^<]*)</ref></xr>')
PREFIX_LAW = re.compile(r'^(?P<indent>[ \t]*)<prefixDef ident="law"[^>]*/>[ \t]*\n', re.M)
PREFIX_CLAUSE = '<prefixDef ident="clause" matchPattern="(.+)" replacementPattern="law.html?id=$1"/>'


# ---- which letter an entry is filed under (same rules as ELieb.letterOf; Æ is a letter of its own) ----

def slugify(text):
    s = ''.join(FOLD.get(c, c) for c in str(text).strip())
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-')


def begins_with_ash(headword):
    first = unicodedata.normalize('NFD', re.sub(r'^[^\W\d_]*', lambda m: m.group(0), re.sub(r'^[\W\d_]+', '', str(headword)))[:1])
    return first[:1] in ('æ', 'Æ')


def alpha_key(headword):
    s = ''.join(c for c in unicodedata.normalize('NFD', str(headword)) if not unicodedata.combining(c))
    s = re.sub('[ꝥꝤ]', 'þæt', s).replace('ł', 'l').replace('Ł', 'L')
    parts = re.split('[þÞðÐ]|[ꝥꝤ]', s)
    key = 't~'.join(slugify(p).lower().replace('-', '') for p in parts)
    return re.sub(r'^[^a-z]*ae', 'a~', key) if begins_with_ash(headword) else key


def letter_of(headword):
    key = re.sub('[^a-z~]', '', alpha_key(headword))
    if key.startswith('t~'):
        return 'Þ'
    if key.startswith('a~'):
        return 'Æ'
    return key[0].upper() if key and key[0].isalpha() else '#'


def headword_of(text):
    m = re.search(r'<orth>(.*?)</orth>', text, re.S)
    return html.unescape(m.group(1)).strip() if m else ''


# ---- clause files -----------------------------------------------------------

def norm_clause(clause):
    """Clause number as dictionary citations and clause files can both be
    compared: commas read as full stops, brackets, spaces, capitals and a
    final full stop ignored."""
    s = re.sub(r'[\s\[\]]+', '', clause.replace(',', '.')).lower().rstrip('.,')
    return re.sub(r'^([a-z]+)\.', r'\1', s)   # "El. 49" and "El 49", "Prol. 1" and "Prol 1" are one thing


class Clauses:
    def __init__(self, catalogue_path, mark_law_path):
        self.by_anchor = defaultdict(dict)       # anchor -> {clause key: clause id}
        self.order = defaultdict(list)           # anchor -> clause keys in file order
        # texts in the database that have no Anchor of their own in the catalogue
        CODE_ANCHOR = {'VI Atr Lat': 'VIAtrLat'}
        # the rubrics of Alfred and Ine: catalogued as "Af Rb" / "Ine Rb" with no
        # anchor; cited "Af Rb 44", which is Af (the code) + "Rb 44"
        RUBRICS = {'Af Rb': 'Af', 'Ine Rb': 'Ine'}
        for c in json.load(open(catalogue_path, encoding='utf-8')):
            if not c['anchor'] and c.get('code') in RUBRICS:
                c = dict(c, anchor=RUBRICS[c['code']])
                if re.match(r'^Af Einl', c['clause']):
                    # the rubric to the Introduction (Af El 49,6), cited "Af Rb El 49,6"
                    c = dict(c, clause='Rb El 49.6', citationKeys=['Af Rb El 49.6'])
            if not c['anchor'] and c.get('code') in CODE_ANCHOR:
                c = dict(c, anchor=CODE_ANCHOR[c['code']])
                c['citationKeys'] = [c['code'].replace(' ', '') + ' ' + k[len(c['code']) + 1:] if k.startswith(c['code'] + ' ') else k for k in c['citationKeys']]
            if not c['anchor']:
                continue
            keys = [k[len(c['anchor']) + 1:] for k in c['citationKeys']]
            if re.match(r'^[A-Za-z]', c['clause']) and not c['clause'].startswith('Rb '):
                # A clause numbered after a word, such as Alfred's Introduction
                # ("Af El. 49,1") or a prologue ("XAtr Prol. 1"): the catalogue
                # splits "Prol. 1" into the keys "prol" and "1", and "1" would
                # wrongly claim clause 1, so use the clause as printed instead,
                # part by part ("Prol., 1" is the prologue and clause 1).
                keys = [k for k in (k.strip() for k in c['clause'].split(',')) if k]
            for k in keys:
                key = norm_clause(k)
                if key and key not in self.by_anchor[c['anchor']]:
                    self.by_anchor[c['anchor']][key] = c['id']
                    self.order[c['anchor']].append(key)
        self.spellings = defaultdict(list)       # anchor -> its printed spellings
        self.sigla = set()
        for row in json.load(open(mark_law_path, encoding='utf-8')):
            text = ' '.join(row['Gesetze Text'].split())
            self.spellings[row['Anchor']].append(text)
            if len(text) <= 3:
                self.sigla.add(text)

    def find(self, anchor, text):
        """-> (how, clause id or None). 'how' is the way it matched, or why not."""
        files = self.by_anchor.get(anchor)
        if not files:
            return 'code not in database', None
        t = ' '.join(text.split())
        rest = None
        for spelling in sorted(self.spellings.get(anchor, []), key=len, reverse=True):
            if t == spelling:
                rest = ''
                break
            if t.startswith(spelling + ' ') or t.startswith(spelling + ','):    # Af 41 and Cn 1020,11
                rest = t[len(spelling):].strip(' ,')
                break
        if rest is None:
            return 'citation not understood', None
        if not rest:
            return 'no clause number', None
        key = norm_clause(rest)
        if key in files:
            return 'exact', files[key]
        ff = re.match(r'^(\S*?\d+[a-z]??)\s*ff?\.?$', rest)    # "Swer 7ff.", "7 f.": and following; to the first
        if ff and norm_clause(ff.group(1)) in files:
            return 'and-following', files[norm_clause(ff.group(1))]
        z = re.match(r'^Z\.?\s*(\d+)$', rest)      # "Nor grið Z. 6": line 6 of a text numbered by lines
        if z:
            for k in (z.group(1), 'line' + z.group(1)):
                if k in files:
                    return 'line', files[k]
        m = re.match(r'^(.*\S)\s+([A-Z][A-Za-z]{0,2})\.?$', rest)
        if m and m.group(2) in self.sigla:
            key = norm_clause(m.group(1))
            if key in files:
                return 'ms-letter', files[key]
        for k in self.order[anchor]:
            if k.startswith(key) and len(k) > len(key) and not k[len(key)].isdigit():
                return 'subclause', files[k]
        return 'clause not found', None


# ---- main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--letter', default='A', help='link the entries filed under this letter ("all" for every entry)')
    ap.add_argument('--dry-run', action='store_true', help='report only; change no files')
    ap.add_argument('--entries', default='entries')
    ap.add_argument('--catalogue', default='oe-laws/index.json')
    ap.add_argument('--mark-law', default='data/markLaw.json')
    ap.add_argument('--report', default='docs/oe-laws-link-report.md')
    ap.add_argument('--no-report', action='store_true')
    args = ap.parse_args()

    clauses = Clauses(args.catalogue, args.mark_law)
    outcome = Counter()
    missed = defaultdict(Counter)            # reason -> {"Anchor text": count}
    entries_seen = entries_changed = entries_with_citations = entries_fully_linked = 0
    no_prefix = []
    samples = []

    for path in sorted(glob.glob(os.path.join(args.entries, '*.xml'))):
        with open(path, encoding='utf-8', newline='') as f:
            text = f.read()
        if args.letter.lower() != 'all' and letter_of(headword_of(text)) != args.letter.upper():
            continue
        entries_seen += 1
        changed_here = 0
        results_here = []

        def link(m):
            nonlocal changed_here
            how, clause_id = clauses.find(m.group('anchor'), html.unescape(m.group('text')))
            outcome[how] += 1
            results_here.append(how)
            if clause_id is None:
                missed[how]['%s | %s' % (m.group('anchor'), html.unescape(m.group('text')))] += 1
                return m.group(0)
            changed_here += 1
            if len(samples) < 12 and how != 'exact':
                samples.append((how, m.group('text'), clause_id))
            return '<xr type="lawCode"><ref target="clause:%s">%s</ref></xr>' % (clause_id, m.group('text'))

        new = XR.sub(link, text)
        # a citation already linked (target="clause:...") is not matched by XR, so
        # count it as linked rather than leaving it out of the figures
        already = len(re.findall(r'<xr type="lawCode"><ref target="clause:', text))
        if already:
            outcome['already linked'] += already
            results_here += ['already linked'] * already
        if results_here:
            entries_with_citations += 1
            if all(r in ('exact', 'ms-letter', 'subclause', 'and-following', 'already linked') for r in results_here):
                entries_fully_linked += 1
        if changed_here:
            if 'ident="clause"' not in new:
                m = PREFIX_LAW.search(new)
                if m:
                    new = new[:m.end()] + '%s%s\n' % (m.group('indent'), PREFIX_CLAUSE) + new[m.end():]
                else:
                    no_prefix.append(path)
            entries_changed += 1
            if not args.dry_run:
                with open(path, 'w', encoding='utf-8', newline='') as f:
                    f.write(new)

    total = sum(outcome.values())
    linked = sum(outcome[k] for k in ('exact', 'ms-letter', 'subclause', 'and-following', 'already linked'))
    with_clause = linked + outcome['clause not found'] + outcome['citation not understood']
    lines = []
    out = lines.append
    scope = 'All entries' if args.letter.lower() == 'all' else 'Entries filed under %s' % args.letter.upper()
    out('%s: %d (with a law code citation list: %d)' % (scope, entries_seen, entries_with_citations))
    out('Citations in their lists: %d' % total)
    for k in ('exact', 'ms-letter', 'subclause', 'and-following', 'already linked'):
        if outcome[k]:
            out('  linked, %-14s %6d' % (k, outcome[k]))
    out('  LINKED TO A CLAUSE:      %6d  (%.0f%% of all citations; %.0f%% of those with a clause number to a code in the database)'
        % (linked, 100.0 * linked / max(total, 1), 100.0 * linked / max(with_clause, 1)))
    for k in ('clause not found', 'citation not understood', 'no clause number', 'code not in database'):
        if outcome[k]:
            out('  not linked, %-24s %6d' % (k, outcome[k]))
    out('Entries changed: %d; entries whose whole list is linked: %d' % (entries_changed, entries_fully_linked))
    if no_prefix:
        out('WARNING: no law prefixDef to add the clause prefix after in: %s' % ', '.join(no_prefix[:5]))
    print('\n'.join(lines))
    print('(dry run: no files changed)' if args.dry_run else '(entries updated)')

    if not args.no_report:
        with open(args.report, 'w', encoding='utf-8', newline='\n') as f:
            f.write('# Law code citations linked to clause files\n\n')
            f.write('Made by `tools/link-citations.py --letter %s`. It is replaced each time the tool runs.\n\n```\n%s\n```\n\n' % (args.letter.upper(), '\n'.join(lines)))
            for reason, title in (('clause not found', 'The code is in the database but no clause file has that number'),
                                  ('code not in database', 'The code has no clause files'),
                                  ('citation not understood', 'The citation text does not start with a spelling of its code'),
                                  ('no clause number', 'The citation is a code with no clause number')):
                if not missed[reason]:
                    continue
                f.write('## %s\n\n' % title)
                by_code = Counter()
                for cite, n in missed[reason].items():
                    by_code[cite.split(' | ')[0]] += n
                f.write('By code: %s\n\n' % ', '.join('%s (%d)' % (a, n) for a, n in by_code.most_common(15)))
                f.write('Citations (with how many times each occurs):\n\n')
                for cite, n in sorted(missed[reason].items(), key=lambda kv: (-kv[1], kv[0]))[:60]:
                    f.write('- %s%s\n' % (cite.split(' | ', 1)[1], ' ×%d' % n if n > 1 else ''))
                f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
