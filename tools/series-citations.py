#!/usr/bin/env python3
"""
Finds the citations where Liebermann gives only the Roman numeral of a law
code in a numbered series, because the code before it is in the same series:

    I As 3. II Eg 3,1. III Atr 3,2. IV 1        IV 1 = IV Atr 1
    Excom V 6. VI 4. VIII 3                     VI 4 = Excom VI 4
    Iud Dei II 3,2. VII 23,2                    VII 23,2 = Iud Dei VII 23,2
    VI Atr 20 = VIII 13                         VIII 13 = VIII Atr 13

    python3 tools/series-citations.py --dry-run   # report only
    python3 tools/series-citations.py             # change the entries

For each one it
  - links the numeral in the entry text to its law code, as Liebermann's own
    abbreviations are linked: <ref type="lawCode" target="law:IVAtr">IV</ref>
    (the text still reads "IV", as printed);
  - adds the citation, written out in full ("IV Atr 1"), to the law code
    citation list under the entry, after the citation before it.

A numeral counts only when
  - it comes straight after a citation of a code in a numbered series (the
    codes on the law code list written "IV Atr" or "Iud Dei IV"), with only
    clause numbers between them, and after a full stop ("3,2. IV") or an
    equals sign, Liebermann's mark for the same passage in another law
    ("VI Atr 20 = VIII 13");
  - a clause number follows it ("IV 1", or "X,17" in Liebermann's style for
    Iud Dei);
  - that code is on the law code list (data/markLaw.json): there is an
    "IV Atr", so "IV" after "III Atr" is IV Atr.
A manuscript letter between them ("Ine 42 B. 43") does not break the run.

Afterwards run tools/link-citations.py --letter all, so the new citations
link to their clauses. Running this again is safe: numerals already linked
are not found again. Writes docs/series-citations-report.md (use
--no-report to skip). Needs only Python 3.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

ROMAN = r'(?:XIII|XII|XIV|XVI|XV|XI|X|IX|VIII|VIIa|VII|VI|V|IV|III|II|I)'
PASSAGE = r'(?:\d+[a-z]{0,2}(?:,\d+[a-z]{0,2})*|Inscr?\.?|Prol?\.?|Epil\.?)'
REF = re.compile(r'<ref type="lawCode" target="law:(?P<anchor>[^"]+)">(?P<text>[^<]*)</ref>')
SCRAP = re.compile(r'(<dictScrap type="(?:liebermann|senses)">)(.*?)(</dictScrap>)', re.S)
XR_LINE = re.compile(r'^(?P<pad>[ \t]*)<xr type="lawCode"><ref(?: target="[^"]*")?>(?P<text>[^<]*)</ref></xr>[ \t]*$', re.M)


class Series:
    """The law codes in numbered series: "IV Atr" is number IV of the series
    "Atr" (numeral first); "Iud Dei IV" is number IV of "Iud Dei" (last)."""
    def __init__(self, mark_law, manuscripts):
        self.of = {}            # anchor -> (series key, numeral)
        self.member = {}        # (series key, numeral) -> (anchor, printed spelling)
        for row in json.load(open(mark_law, encoding='utf-8')):
            text = ' '.join(row['Gesetze Text'].split())
            m = re.fullmatch(r'(%s) (\S.*)' % ROMAN, text) or re.fullmatch(r'(\S.*) (%s)' % ROMAN, text)
            if not m:
                continue
            numeral_first = re.fullmatch(ROMAN, m.group(1)) is not None and not re.fullmatch(ROMAN, m.group(2))
            numeral, base = (m.group(1), m.group(2)) if numeral_first else (m.group(2), m.group(1))
            key = ('first' if numeral_first else 'last', base)
            self.of[row['Anchor']] = (key, numeral)
            self.member.setdefault((key, numeral), (row['Anchor'], text))
        self.sigla = {row['Anchor'] for row in json.load(open(manuscripts, encoding='utf-8')) if row.get('Anchor')}

    def sibling(self, anchor, numeral):
        if anchor not in self.of:
            return None
        return self.member.get((self.of[anchor][0], numeral))


def passages_after(text):
    """The clause numbers at the start of text: " 1. 3 | …" -> ['1', '3'], and
    the separator before the first (' ' or ',')."""
    m = re.match(r'(\s+|,(?=\d))(%s)(?![\w)])' % PASSAGE, text)
    if not m:
        return '', []
    sep, out, pos = (',' if m.group(1) == ',' else ' '), [m.group(2).rstrip('.')], m.end()
    while True:
        m = re.compile(r'\.?\s+(%s)(?![\w)])' % PASSAGE).match(text, pos)
        if not m or re.fullmatch(ROMAN, m.group(1)):
            return sep, out
        out.append(m.group(1).rstrip('.'))
        pos = m.end()


def fix_scrap(scrap, series, found):
    """Links the bare numerals in one dictScrap; appends (previous citation,
    [new citations], numeral, anchor) to found."""
    out, pos, cur, last_cite = [], 0, None, None
    # The run: a clause number or more, then ". IV" and a clause number.
    # The first clause number may follow a comma, in Liebermann's style for
    # Iud Dei ("Iud Dei VI,1. VII 24,1"). After a manuscript letter the run
    # needs no clause number of its own ("VII 24,1 A. VIII 2").
    run = re.compile(r'(?:(?:\.?\s+|,(?=\d))%s(?![\w)]))+(?:\.|\s=)\s+(?P<num>%s)(?=(?:\s+|,)%s(?![\w)]))' % (PASSAGE, ROMAN, PASSAGE))
    run_after_letter = re.compile(r'(?:(?:\.?\s+|,(?=\d))%s(?![\w)]))*(?:\.|\s=)\s+(?P<num>%s)(?=(?:\s+|,)%s(?![\w)]))' % (PASSAGE, ROMAN, PASSAGE))
    tokens = list(REF.finditer(scrap))
    for i, ref in enumerate(tokens):
        out.append(scrap[pos:ref.end()])
        pos = ref.end()
        anchor, label = ref.group('anchor'), ' '.join(ref.group('text').split())
        after_letter = False
        if anchor in series.of:
            cur = (anchor, label)
        elif anchor in series.sigla and cur:
            after_letter = True     # "Ine 42 B. 43": still Ine
        else:
            cur = None
        end = tokens[i + 1].start() if i + 1 < len(tokens) else len(scrap)
        chunk = scrap[pos:end]
        cpos = 0
        while cur:
            sep, nums = passages_after(chunk[cpos:])
            m = (run_after_letter if after_letter and cpos == 0 else run).match(chunk, cpos)
            if nums:
                last_cite = cur[1] + sep + nums[-1]
            if not m:
                break
            hit = series.sibling(cur[0], m.group('num'))
            if not hit:
                break
            new_anchor, new_label = hit
            out.append(chunk[cpos:m.start('num')])
            out.append('<ref type="lawCode" target="law:%s">%s</ref>' % (new_anchor, m.group('num')))
            cpos = m.end('num')
            sep, nums = passages_after(chunk[cpos:])
            found.append((last_cite, [new_label + sep + n for n in nums], m.group('num'), new_anchor))
            cur = (new_anchor, new_label)
        out.append(chunk[cpos:])
        pos = end
        # a code followed by anything but clause numbers ends the run
        if cur and not re.fullmatch(r'(?:(?:\.?\s+|,(?=\d))%s(?![\w)])|[\s.=])*' % PASSAGE, chunk[cpos:]):
            cur = None
    out.append(scrap[pos:])
    return ''.join(out)


def add_to_list(xml, after, citations):
    """Adds citations ([(anchor, text)]) to the entry's citation list after
    the one called `after`, skipping any already there. -> (xml, number added)."""
    lines = list(XR_LINE.finditer(xml))
    have = {' '.join(m.group('text').split()) for m in lines}
    new = []
    for anchor, text in citations:
        if text not in have:
            have.add(text)
            new.append((anchor, text))
    if not new:
        return xml, 0
    if lines:
        at = next((m for m in lines if ' '.join(m.group('text').split()) == after), lines[-1])
        pad = at.group('pad')
        insert = ''.join('\n%s<xr type="lawCode"><ref target="law:%s">%s</ref></xr>' % (pad, a, c) for a, c in new)
        return xml[:at.end()] + insert + xml[at.end():], len(new)
    m = re.search(r'\n([ \t]*)</entry>', xml)
    pad = m.group(1) + '  '
    insert = ''.join('\n%s<xr type="lawCode"><ref target="law:%s">%s</ref></xr>' % (pad, a, c) for a, c in new)
    return xml[:m.start()] + insert + xml[m.start():], len(new)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--entries', default='entries')
    ap.add_argument('--mark-law', default='data/markLaw.json')
    ap.add_argument('--manuscripts', default='data/manuscripts.json')
    ap.add_argument('--report', default='docs/series-citations-report.md')
    ap.add_argument('--no-report', action='store_true')
    args = ap.parse_args()
    series = Series(args.mark_law, args.manuscripts)

    numerals, added, entries_changed = Counter(), 0, 0
    examples = []
    for path in sorted(glob.glob(os.path.join(args.entries, '*.xml'))):
        xml = open(path, encoding='utf-8', newline='').read()
        found_full = []
        def fix(m, record=[True]):
            found = []
            body = fix_scrap(m.group(2), series, found)
            # the senses block repeats the text, so its citations are not counted twice
            if m.group(1) == '<dictScrap type="liebermann">':
                found_full.extend(found)
            return m.group(1) + body + m.group(3)
        new = SCRAP.sub(fix, xml)
        if new == xml:
            continue
        for after, cites, numeral, anchor in found_full:
            new, n = add_to_list(new, after, [(anchor, c) for c in cites])
            added += n
            numerals[anchor] += 1
            if len(examples) < 40:
                examples.append('%s: after %s, %s → %s' % (os.path.basename(path)[:-4], after, numeral, ', '.join(cites)))
        entries_changed += 1
        if not args.dry_run:
            open(path, 'w', encoding='utf-8', newline='').write(new)

    lines = ['Numerals linked: %d, in %d entries' % (sum(numerals.values()), entries_changed),
             'Citations added to the lists: %d' % added,
             'By code: ' + ', '.join('%s (%d)' % kv for kv in numerals.most_common())]
    print('\n'.join(lines))
    print('(dry run: no files changed)' if args.dry_run else '(entries updated)')
    if not args.no_report:
        with open(args.report, 'w', encoding='utf-8', newline='\n') as f:
            f.write('# Law code citations by Roman numeral alone\n\n')
            f.write('Made by `tools/series-citations.py`. It is replaced each time the tool runs.\n\n```\n%s\n```\n\n' % '\n'.join(lines))
            f.write('Examples:\n\n' + ''.join('- %s\n' % e for e in examples))
    return 0


if __name__ == '__main__':
    sys.exit(main())
