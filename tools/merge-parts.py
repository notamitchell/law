#!/usr/bin/env python3
"""
One page per Liebermann clause: joins the clause files of a clause that the
spreadsheet divides with letters in square brackets (Abt 1[a], 1[b] … 1[g],
to match the numbering of later editors) into one file for the whole clause
(Abt_1.xml).

    python3 tools/merge-parts.py            # after laws-from-database.py and liebermann-notes.py
    python3 tools/merge-parts.py --dry-run

In the joined file each text keeps its parts, as
    <ab …><seg type="part" n="a">…</seg> <seg type="part" n="b">…</seg></ab>
so the clause page can mark where the later editors' divisions fall; a
<note type="concordance"> says how each edition numbers the parts. Notes,
keywords, sources and manuscripts of the parts are gathered (once each).

oe-laws/index.json gets one entry for the clause, with "parts": the old part
files' ids and clause numbers. The part files are removed; law.html sends a
link to a part (law.html?id=Abt_1-c) to the whole clause, with that part
marked. Links to a part from the dictionary and from the cross-references
that cite the whole clause ("Abt 1", without a letter) are pointed at the
whole clause.

laws-from-database.py reads the "parts" back, so the next rebuild makes the
part files under the same names again, for this script to join.
"""
import argparse
import copy
import glob
import json
import os
import re
from collections import OrderedDict

from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAWS = os.path.join(ROOT, 'oe-laws')
TEI = 'http://www.tei-c.org/ns/1.0'
XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'t': TEI}
T = lambda name: '{%s}%s' % (TEI, name)
PART = re.compile(r'^(.*?)\[([a-z])\]$')
PART_NOTES = ('editorial', 'translator', 'textual', 'passageSource')   # notes on one part: marked with its letter


def groups(catalogue):
    """[(code, base clause, [entries in order])] for clauses divided into lettered parts."""
    out = OrderedDict()
    for c in catalogue:
        if c.get('parts'):
            continue
        clause = (c.get('clause') or '').strip()
        m = PART.match(clause)
        base = m.group(1) if m else clause
        out.setdefault((c['code'], base), []).append(c)
    res = []
    for (code, base), entries in out.items():
        lettered = [e for e in entries if PART.match((e.get('clause') or '').strip())]
        if len(lettered) >= 1 and len(entries) >= 2:
            res.append((code, base, entries))
    return res


def letter(entry):
    m = PART.match((entry.get('clause') or '').strip())
    return m.group(2) if m else ''


def base_id(entries):
    """Abt_1-a -> Abt_1; if one part has no letter (clause '17'), its id is the base."""
    for e in entries:
        if not letter(e):
            return e['id']
    first = entries[0]['id']
    return re.sub(r'-[a-z]$', '', first)


def text_of(el):
    return ''.join(el.itertext())


def merge(code, base, entries, bid):
    docs = [(letter(e), etree.parse(os.path.join(LAWS, e['file']))) for e in entries]
    doc = copy.deepcopy(docs[0][1])
    root = doc.getroot()
    root.set('{%s}id' % XML, bid)
    citation = '%s %s' % (code, base)

    # --- header
    tstmt = root.find('.//t:titleStmt', NS)
    tstmt.find('t:title', NS).text = citation
    have = {etree.tostring(r) for r in tstmt.findall('t:respStmt', NS)}
    for _, d in docs[1:]:
        for r in d.findall('.//t:titleStmt/t:respStmt', NS):
            if etree.tostring(r) not in have:
                tstmt.append(copy.deepcopy(r)); have.add(etree.tostring(r))
    pub = root.find('.//t:publicationStmt', NS)
    keys = []
    for _, d in docs:
        for k in d.findall('.//t:publicationStmt/t:idno[@type="citationKey"]', NS):
            if k.text not in keys:
                keys.append(k.text)
    anchor = (pub.findtext('t:idno[@type="lawCodeAnchor"]', namespaces=NS) or code).strip()
    whole_key = '%s %s' % (anchor, base.lower())
    for k in pub.findall('t:idno[@type="citationKey"]', NS):
        pub.remove(k)
    for k in [whole_key] + [k for k in keys if k != whole_key]:
        e = etree.SubElement(pub, T('idno'), type='citationKey'); e.text = k; e.tail = '\n        '
    pub[-2].tail = '\n        '
    pub[-1].tail = '\n      '
    pub.find('t:idno[@type="slug"]', NS).text = bid
    pub.find('t:idno[@type="citation"]', NS).text = citation
    if pub.find('t:idno[@type="clause"]', NS) is not None:
        pub.find('t:idno[@type="clause"]', NS).text = base
    for list_tag, item_tag in (('listBibl', 'bibl'), ('listWit', 'witness')):
        lst = root.find('.//t:sourceDesc/t:%s' % list_tag, NS)
        for _, d in docs[1:]:
            other = d.find('.//t:sourceDesc/t:%s' % list_tag, NS)
            if other is None:
                continue
            if lst is None:
                lst = copy.deepcopy(other)
                root.find('.//t:sourceDesc', NS).append(lst)
                continue
            ids = {x.get('{%s}id' % XML) for x in lst.findall('t:%s' % item_tag, NS)}
            for x in other.findall('t:%s' % item_tag, NS):
                if x.get('{%s}id' % XML) not in ids:
                    lst.append(copy.deepcopy(x)); ids.add(x.get('{%s}id' % XML))
    tc = root.find('.//t:textClass', NS)
    for _, d in docs[1:]:
        for kw in d.findall('.//t:textClass/t:keywords', NS):
            mine = tc.find('t:keywords[@n="%s"]' % kw.get('n'), NS) if tc is not None else None
            if mine is None:
                if tc is not None:
                    tc.append(copy.deepcopy(kw))
                continue
            terms = [t.text for t in mine.findall('t:term', NS)]
            for t in kw.findall('t:term', NS):
                if t.text not in terms:
                    mine.append(copy.deepcopy(t)); terms.append(t.text)
    rev = root.find('.//t:revisionDesc', NS)
    have = {etree.tostring(c) for c in rev}
    for _, d in docs[1:]:
        for c in d.findall('.//t:revisionDesc/t:change', NS):
            if c.get('type') == 'checked' and etree.tostring(c) not in have:
                rev.append(copy.deepcopy(c)); have.add(etree.tostring(c))
    ch = etree.SubElement(rev, T('change'), when=rev[0].get('when'))
    ch.text = 'Joined from the files of its parts %s (rows of the spreadsheet), to give Liebermann’s clause on one page.' % ', '.join(e['clause'] for e in entries)
    ch.tail = '\n    '

    # --- body
    div = root.find('.//t:body/t:div', NS)
    div.set('n', base)
    head = div.find('t:head', NS)
    ref = head.find('t:ref', NS)
    if ref is not None:
        ref.tail = ' ' + base
    else:
        head.text = citation
    for child in list(div):
        if child.tag != T('head'):
            div.remove(child)

    abs_, notes, numbers = OrderedDict(), [], OrderedDict()
    # Only an editor who divides the clause numbers its parts, and only in that editor's own edited text
    # (Oliver's Old English: 22, 22.1, 22.2). Other texts are not marked.
    def number(let, ab):
        return ab.get('n') if ab.get('type') == 'editionText' and ab.get('n') else ''
    for let, d in docs:
        ddiv = d.find('.//t:body/t:div', NS)
        for ab in ddiv.findall('t:ab', NS):
            key = (ab.get('type'), ab.get('{%s}lang' % XML), ab.get('source'), ab.get('corresp'), ab.get('ana'))
            if key not in abs_:
                new = etree.Element(T('ab'))
                for k, v in ab.attrib.items():
                    if k != 'n':
                        new.set(k, v)
                abs_[key] = new
            if ab.get('n'):
                numbers.setdefault((ab.get('type'), ab.get('source')), []).append(ab.get('n'))
            prev = abs_[key][-1] if len(abs_[key]) else None
            if prev is not None and let and ' '.join(text_of(prev).split()) == ' '.join(text_of(ab).split()):
                # the same words given for two parts (one translation covering both): show them once, for both
                prev.set('corresp', prev.get('corresp') + ' #part-' + let)
                first, last = (prev.get('n') or '').split('–')[0], number(let, ab)
                prev.set('n', first + '–' + last if first and last else first or last)
                continue
            seg = etree.SubElement(abs_[key], T('seg'), type='part')
            if number(let, ab):
                seg.set('n', number(let, ab))
            if let:
                seg.set('corresp', '#part-' + let)
            seg.text = ab.text
            for c in ab:
                seg.append(copy.deepcopy(c))
            seg.tail = ' '
        for n in ddiv.findall('t:note', NS):
            n = copy.deepcopy(n)
            if n.get('type') in PART_NOTES and let:
                n.set('target', '#part-' + let)
            notes.append(n)
    for (typ, lang, src, corr, ana), ab in abs_.items():
        if typ == 'editionText':
            nums = [x for seg in ab for x in (seg.get('n') or '').split('–') if x]
            if nums:
                ab.set('n', nums[0] if nums[0] == nums[-1] else nums[0] + '–' + nums[-1])
    for ab in abs_.values():
        if len(ab):
            ab[-1].tail = None
        ab.tail = '\n        '
        div.append(ab)

    # how each edition numbers the parts
    names = {r.find('t:name', NS).get('ref', '').lstrip('#'): r.findtext('t:name', namespaces=NS)
             for r in root.findall('.//t:titleStmt/t:respStmt', NS) if r.find('t:name', NS) is not None}
    conc = etree.SubElement(div, T('note'), type='concordance')
    bits = []
    for (typ, src), ns in numbers.items():
        src = (src or '').lstrip('#')
        nums = list(OrderedDict.fromkeys(ns))
        if typ == 'liebermannText':
            continue                   # Liebermann's number is the clause's own
        label = names.get(src, src.capitalize())
        if (label, ', '.join(nums)) not in [(b[0], b[1]) for b in bits]:
            bits.append((label, ', '.join(nums)))
    for i, (label, nums) in enumerate(bits):
        s = etree.SubElement(conc, T('seg'), type='edition')
        s.text = '%s %s' % (label, nums)
        s.tail = '; ' if i < len(bits) - 1 else ''
    conc.tail = '\n        '
    if not bits:
        div.remove(conc)

    # Liebermann's cross-references: one note of each kind for the whole clause (the page shows the first)
    combined = []
    for kind in ('comparison', 'comparisonPrinted', 'comparisonIncomplete', 'comparedBy'):
        mine = [n for n in notes if n.get('type') == kind and n.get('source', '#liebermann') in ('#liebermann', None)
                and (kind != 'comparison' or n.get('source') == '#liebermann') and (kind != 'comparedBy' or n.get('source') == '#liebermann')]
        if len(mine) < 2:
            continue
        one = copy.deepcopy(mine[0])
        if kind == 'comparisonPrinted':
            one.text = ' | '.join(text_of(n) for n in mine)
        elif kind in ('comparison', 'comparedBy'):
            pages = [n.get('n') for n in mine if n.get('n')]
            if pages:
                one.set('n', ', '.join(OrderedDict.fromkeys(pages)))
            refs = OrderedDict()
            for n in mine:
                for r in n:
                    refs.setdefault(etree.tostring(r, with_tail=False), r)
                if not len(n) and (n.text or '').strip():
                    refs.setdefault(n.text, n.text)
            for c in list(one):
                one.remove(c)
            one.text = None
            prev = None
            for k, r in refs.items():
                if isinstance(r, str):
                    if prev is None: one.text = (one.text or '') + r
                    else: prev.tail = (prev.tail or '') + '; ' + r
                    continue
                r = copy.deepcopy(r); r.tail = None
                if prev is not None: prev.tail = '; '
                elif one.text: one.text += '; '
                one.append(r); prev = r
        idx = notes.index(mine[0])
        for n in mine:
            notes.remove(n)
        notes.insert(idx, one)

    seen = set()
    for n in notes:
        key = (n.get('type'), n.get('source'), n.get('subtype'), text_of(n).strip())
        if n.get('type') != 'liebermannNote' and key in seen:
            continue
        seen.add(key)
        n.tail = '\n        '
        div.append(n)
    if len(div):
        div[-1].tail = '\n      '
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--code', action='append', help='only this law code')
    args = ap.parse_args()
    index_path = os.path.join(LAWS, 'index.json')
    catalogue = json.load(open(index_path, encoding='utf-8'))
    todo = [g for g in groups(catalogue) if not args.code or g[0] in args.code]
    by_part = {}
    new_entries = {}
    for code, base, entries in todo:
        bid = base_id(entries)
        if not args.dry_run:
            doc = merge(code, base, entries, bid)
            xml = etree.tostring(doc, encoding='UTF-8', xml_declaration=True).decode('utf-8')
            xml = xml.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>')
            for e in entries:
                p = os.path.join(LAWS, e['file'])
                if e['id'] != bid and os.path.exists(p):
                    os.remove(p)
            with open(os.path.join(LAWS, bid + '.xml'), 'w', encoding='utf-8', newline='\n') as f:
                f.write(xml + ('' if xml.endswith('\n') else '\n'))
        first = entries[0]
        keys = []
        for e in entries:
            for k in e.get('citationKeys', []):
                if k not in keys:
                    keys.append(k)
        whole = '%s %s' % (first.get('anchor') or code, base.lower())
        new_entries[first['id']] = dict(first, id=bid, file=bid + '.xml', citation='%s %s' % (code, base), clause=base,
                                        citationKeys=[whole] + [k for k in keys if k != whole],
                                        parts=[{'id': e['id'], 'clause': e['clause'], 'sheetRow': e.get('sheetRow')} for e in entries])
        for e in entries:
            by_part[e['id']] = bid
        print('%s %s: %s -> %s' % (code, base, ', '.join(e['clause'] for e in entries), bid))
    if args.dry_run:
        print('%d clauses would be joined' % len(todo))
        return

    out = []
    for c in catalogue:
        if c['id'] in new_entries:
            out.append(new_entries[c['id']])
        elif c['id'] in by_part and c['id'] not in new_entries:
            continue
        else:
            out.append(c)
    with open(index_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('[\n' + ',\n'.join(json.dumps(c, ensure_ascii=False, separators=(',', ':')) for c in out) + '\n]\n')

    # codes.json: clause counts and first clause
    codes_path = os.path.join(LAWS, 'codes.json')
    if os.path.exists(codes_path):
        codes = json.load(open(codes_path, encoding='utf-8'))
        count = {}
        for c in out:
            count[c['code']] = count.get(c['code'], 0) + 1
        for c in codes:
            if c.get('code') in count:
                c['clauses'] = count[c['code']]
            if c.get('first') in by_part:
                c['first'] = by_part[c['first']]
        with open(codes_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('[\n' + ',\n'.join(json.dumps(c, ensure_ascii=False, separators=(',', ':')) for c in codes) + '\n]\n')

    # links to a part that cite the whole clause (no letter in the citation) go to the whole clause
    link = re.compile(r'<ref target="clause:([^"#]+)">([^<]*)</ref>')
    def fix(m):
        return ('<ref target="clause:%s">%s</ref>' % (by_part[m.group(1)], m.group(2))
                if m.group(1) in by_part and '[' not in m.group(2) else m.group(0))
    changed = 0
    for path in glob.glob(os.path.join(ROOT, 'entries', '*.xml')) + glob.glob(os.path.join(LAWS, '*.xml')):
        s = open(path, encoding='utf-8').read()
        t = link.sub(fix, s)
        if t != s:
            open(path, 'w', encoding='utf-8', newline='\n').write(t)
            changed += 1
    print('%d clauses joined; links pointed at the whole clause in %d files' % (len(todo), changed))


if __name__ == '__main__':
    main()
