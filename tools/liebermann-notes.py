#!/usr/bin/env python3
"""
Adds the editors' notes to the clause files in oe-laws/ from the main spreadsheet
(OE_Laws_Database - Updated by Claude.xlsx), sheets "Texts with note markers",
"Liebermann notes" and (from October 2026) "Attenborough notes", "Robertson notes", "Whitelock notes" and "Oliver notes".

    python3 tools/liebermann-notes.py "OE_Laws_Database - Updated by Claude.xlsx" --dry-run
    python3 tools/liebermann-notes.py "OE_Laws_Database - Updated by Claude.xlsx"

Needs Python 3, openpyxl and lxml (pip install openpyxl lxml).

Run it AFTER tools/laws-from-database.py: that script rebuilds the clause files
from the main spreadsheet and so takes the notes out again. Running this one
twice does no harm: it first removes the notes it added before.

The notes (see docs/OE-LAWS.md, "Liebermann's notes" and "Attenborough's notes"):

- Liebermann's textual notes on his Old English (or Latin) texts, printed at the
  foot of the page in Gesetze I (columns K, N, AF, BF, BI, O of the spreadsheet);
- his Erklärungen, the notes to his German translation, printed in Gesetze III
  (column L), and his own footnotes to the German in Gesetze I;
- Attenborough's notes (The Laws of the Earliest English Kings, 1922): the notes
  at the back of the book, keyed to numbers in his translation (column W, or U
  where he is the modern editor), and his footnotes to his Old English text
  (column T where he is the editor; otherwise his text is not in the database
  and the note gives the word it stands on).

Sheet "Texts with note markers" holds the texts with each note number in curly
brackets after its word: {4}, {*}, {+1} (a number Liebermann forgot to print and
supplies in vol. III), {2/4} (number 2, misprinted 4 in vol. I). Columns: A row,
B clause file, C code, D clause, E Gesetze I page, F column K, G column L,
H remarks, I column N, J column AF, K column O, L column T, M column U, N column W,
O column BF, P column BI (Liebermann's fourth and fifth texts).
Taking out the brackets must give the texts now in the clause file exactly; if
not, the file is left alone and the difference reported.

In the clause file the numbers become empty pointers inside the text, which the
plain view of the clause page ignores:

    <ab type="liebermannText" …>Godes<ptr type="liebermannNote" n="4" target="#Abt_1-a.lnote.oe.4"/> feoh …</ab>
    <ab type="translation" source="#attenborough" …>… a number<ptr type="editorNote" n="1" target="#Hl_5-a.anote.1"/> of …</ab>

and the notes go at the end of the clause:

    <note type="liebermannNote" subtype="textual" xml:id="Abt_1-a.lnote.oe.4" n="4" source="#liebermann">
      <bibl><biblScope unit="volume">1</biblScope><biblScope unit="page">3</biblScope></bibl>
      <seg type="original" xml:lang="de">Godes feoh ⁊ ci <hi rend="italic">in Capitalschrift</hi></seg>
      <seg type="translation" xml:lang="en" source="#claude">Godes feoh ⁊ ci in capital letters</seg>
    </note>
    <note type="editorNote" subtype="endnote" xml:id="Hl_5-a.anote.1" n="1" source="#attenborough">
      <bibl><biblScope unit="page">179</biblScope></bibl>
      <seg type="original" xml:lang="en">For the ‘number’ we may possibly compare Wiht. cap. 21.</seg>
    </note>

Liebermann's subtypes: "textual" (vol. I, on his texts), "erklaerung" (vol. III, on
the German) or "translationFootnote" (vol. I's own footnote to the German).
Attenborough's: "endnote" (at the back of the book) or "footnote" (on his Old
English text; with <label> = the word it stands on, when his text is not given).
A note on the clause as a whole, with no number in the text, has rend="wholeClause"
(and n="0" when it has no number at all).
"""
import argparse
import os
import re
import unicodedata
import sys
from xml.sax.saxutils import escape

import openpyxl
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LAWS = os.path.join(ROOT, 'oe-laws')
TEI = 'http://www.tei-c.org/ns/1.0'
XML = 'http://www.w3.org/XML/1998/namespace'
NS = {'t': TEI}
MARK = re.compile(r'\{(\+?)([0-9a-z*†‡§]+)(?:/([0-9*]+))?\}')

ERKL_BIBL = ('<bibl xml:id="liebermann-erkl" type="commentary"><author>Felix Liebermann</author>, '
             '<title>Die Gesetze der Angelsachsen</title>, vol. <biblScope unit="volume">3</biblScope>: '
             '<title>Einleitung zu jedem Stück; Erklärungen zu einzelnen Stellen</title> '
             '(Halle: Niemeyer, 1916)</bibl>')
CLAUDE_BIBL = ('<bibl xml:id="claude" type="translation">A semi-literal English rendering of Liebermann’s German, made for this database in 2026 with Claude, a large language model (LLM) made by Anthropic. It is a crib to help the reader with Liebermann’s German, not a separate translation</bibl>')
ATT_BIBL = ('<bibl xml:id="attenborough" type="translation">F. L. Attenborough, <title>The Laws of the Earliest English Kings</title> '
            '(Cambridge: Cambridge University Press, 1922)</bibl>')
RESP = ('<respStmt><resp>Transcription and English translation of Liebermann’s notes</resp>'
        '<name ref="#claude">Claude</name></respStmt>')
RESP_ATT = ('<respStmt><resp>Transcription of Attenborough’s notes</resp>'
            '<name ref="#claude">Claude</name></respStmt>')

# Sheets of editors' notes -> the source id of the editor
EDITOR_SHEETS = {'Attenborough notes': 'attenborough', 'Robertson notes': 'robertson', 'Whitelock notes': 'whitelock',
                 'Oliver notes': 'oliver'}
EDITOR_BIBL = {
    'attenborough': ATT_BIBL,
    'robertson': '<bibl xml:id="robertson" type="edition">A. J. Robertson, <title>The Laws of the Kings of England from Edmund to Henry I</title> (Cambridge: Cambridge University Press, 1925)</bibl>',
    'oliver': '<bibl xml:id="oliver" type="edition">Lisi Oliver, <title>The Beginnings of English Law</title> (Toronto: University of Toronto Press, 2002)</bibl>',
    'whitelock': '<bibl xml:id="whitelock" type="translation">Dorothy Whitelock, ed., <title>English Historical Documents, I: c. 500–1042</title> (London: Eyre &amp; Spottiswoode, 1955; 2nd edn, London: Eyre Methuen, 1979); page numbers are those of the Taylor &amp; Francis e-Library edition (2007)</bibl>',
}
EDITOR_NAME = {'attenborough': 'Attenborough', 'robertson': 'Robertson', 'whitelock': 'Whitelock', 'oliver': 'Oliver'}

# Columns of "Texts with note markers" (0-based) -> the spreadsheet column they copy
TEXT_COLS = {5: 'K', 6: 'L', 8: 'N', 9: 'AF', 10: 'O', 11: 'T', 12: 'U', 13: 'W', 14: 'BF', 15: 'BI', 16: 'BL', 17: 'AP'}
LIEB_TEXT = ('K', 'N', 'AF', 'BF', 'BI', 'O')


def tags_to_tei(s):
    """The workbook's light markup -> TEI. <i> italic, <b> bold, <sp> letter-spaced, <sc> small caps."""
    s = escape(s or '')
    for tag, rend in (('i', 'italic'), ('b', 'bold'), ('sp', 'spaced'), ('sc', 'smallcaps')):
        s = s.replace('&lt;%s&gt;' % tag, '<hi rend="%s">' % rend).replace('&lt;/%s&gt;' % tag, '</hi>')
    s = s.replace('\n\n', '<lb type="paragraph"/>').replace('\n', ' ')
    return s


def safe(n):
    return {'*': 'star', '**': 'star2', '***': 'star3', '†': 'dagger', '††': 'dagger2', '‡': 'ddagger'}.get(n, re.sub(r'[^A-Za-z0-9]', '_', n))


def read_workbook(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    texts = {}
    for row in list(wb['Texts with note markers'].iter_rows(values_only=True))[1:]:
        if not row or not row[1]:
            continue
        texts[row[1]] = {col: (row[i] or '') for i, col in TEXT_COLS.items() if i < len(row) and row[i]}
    notes = {}
    for row in list(wb['Liebermann notes'].iter_rows(values_only=True))[1:]:
        if not row or not row[1]:
            continue
        slug, on, where, n, printed, de, en, remark = row[1], row[4] or '', row[5] or '', str(row[6] if row[6] is not None else ''), row[7] or '', row[8], row[9], row[10] or ''
        kind = 'oe' if not on.startswith('German') else ('de1' if where.startswith('Gesetze I p.') else 'de')
        notes.setdefault(slug, []).append(dict(owner='liebermann', kind=kind, n=n or '0', where=where, printed=printed,
                                               de=de, en=en, remark=remark, whole=on.endswith('whole clause'),
                                               col=re.search(r'\((\w+)\)', on).group(1) if re.search(r'\((\w+)\)', on) else ''))
    for sheet, owner in EDITOR_SHEETS.items():
        if sheet not in wb.sheetnames:
            continue
        for row in list(wb[sheet].iter_rows(values_only=True))[1:]:
            if not row or not row[1]:
                continue
            slug, on, where, n, word, text, remark = row[1], row[4] or '', row[5] or '', str(row[6] if row[6] is not None else ''), row[7] or '', row[8], row[9] or ''
            kind = ('footnote' if on.startswith(('Old English', 'Latin', 'Text')) else
                    'translationFootnote' if 'footnote' in where and not on.startswith(('Old English', 'Latin', 'Text')) else 'endnote')
            notes.setdefault(slug, []).append(dict(owner=owner, kind=kind,
                                                   n=n or '0', where=where, word=word, text=text, remark=remark,
                                                   whole=on.endswith('whole clause'), col=re.search(r'\((\w+)\)', on).group(1) if re.search(r'\((\w+)\)', on) else ''))
    return texts, notes


def char_positions(xml):
    """For a serialised element body, the index in the string where each text character ends."""
    ends, i = [], 0
    while i < len(xml):
        c = xml[i]
        if c == '<':
            i = xml.index('>', i) + 1
            continue
        if c == '&':
            j = xml.index(';', i)
            ends.append(j + 1)
            i = j + 1
            continue
        ends.append(i + 1)
        i += 1
    return ends


def plain_of(ab):
    return unicodedata.normalize('NFC', re.sub(r'\s+', ' ', ab.xpath('string()')).strip())


def insert_markers(ab, marked, ptr_type, target_for):
    """Put <ptr> elements into <ab> where the {n} codes stand in `marked`.
    target_for(n) gives the note id for number n. Returns the new element."""
    found, offset, last = [], 0, 0
    for m in MARK.finditer(marked):
        offset += m.start() - last
        last = m.end()
        found.append((offset, m.group(1) == '+', m.group(2), m.group(3)))
    if not found:
        return ab
    head = (ab.text or '')
    body = etree.tostring(ab, encoding='unicode', with_tail=False)
    start = body.index('>') + 1
    end = body.rindex('</')
    inner = body[start:end]
    lead = len(head) - len(head.lstrip())     # leading whitespace in the file is not in the plain text
    ends = char_positions(inner)
    pieces, prev = [], 0
    for off, supplied, n, printed in found:
        pos = (lead and ends[lead - 1] or 0) if off == 0 else ends[lead + off - 1]
        attrs = 'type="%s" n="%s" target="#%s"' % (ptr_type, n, target_for(n))
        if supplied:
            attrs += ' rend="supplied"'
        elif printed:
            attrs += ' rend="printed-as-%s"' % printed
        pieces.append(inner[prev:pos])
        pieces.append('<ptr xmlns="%s" %s/>' % (TEI, attrs))
        prev = pos
    pieces.append(inner[prev:])
    new = etree.fromstring(body[:start] + ''.join(pieces) + body[end:])
    ab.getparent().replace(ab, new)
    new.tail = ab.tail
    return new


def strip_old(doc):
    for p in doc.xpath('//t:ptr[@type="liebermannNote" or @type="editorNote"]', namespaces=NS):
        parent = p.getparent()
        prev = p.getprevious()
        if p.tail:
            if prev is not None:
                prev.tail = (prev.tail or '') + p.tail
            else:
                parent.text = (parent.text or '') + p.tail
        parent.remove(p)
    for n in doc.xpath('//t:note[@type="liebermannNote" or @type="editorNote"]', namespaces=NS):
        n.getparent().remove(n)


def assign_ids(slug, notes):
    """Give every note an xml:id, unique in the clause (a page's footnote numbers can repeat on the next page)."""
    seen = set()
    for note in notes:
        if note['owner'] == 'liebermann':
            base = '%s.lnote.%s.%s' % (slug, note['kind'], safe(note['n']))
        else:
            base = '%s.%s.%s.%s' % (slug, note['owner'][:3] + 'note', 'fn' if note['kind'] == 'footnote' else 'n', safe(note['n']))
        nid, k = base, 2
        while nid in seen:
            nid, k = '%s-%d' % (base, k), k + 1
        seen.add(nid)
        note['id'] = nid


def note_xml(note):
    if note['owner'] == 'liebermann':
        kind = note['kind']
        m = re.search(r'Gesetze (I+) p\. (\d+)(?:, col\. (\d))?', note['where'])
        vol = {'I': '1', 'III': '3'}[m.group(1)] if m else ''
        subtype = {'oe': 'textual', 'de': 'erklaerung', 'de1': 'translationFootnote'}[kind]
        source = '#liebermann-erkl' if kind == 'de' else '#liebermann'
        attrs = 'type="liebermannNote" subtype="%s" xml:id="%s" n="%s" source="%s"' % (subtype, note['id'], note['n'], source)
        rend = []
        if note['whole']:
            rend.append('wholeClause')
        if note['printed'] and note['printed'] not in ('not printed', 'no number', 'not in the text'):
            rend.append('printed-as-%s' % note['printed'])
        if rend:
            attrs += ' rend="%s"' % ' '.join(rend)
        out = ['<note xmlns="%s" %s>' % (TEI, attrs)]
        if m:
            out.append('<bibl><biblScope unit="volume">%s</biblScope><biblScope unit="page">%s</biblScope>%s</bibl>'
                       % (vol, m.group(2), '<biblScope unit="column">%s</biblScope>' % m.group(3) if m.group(3) else ''))
        out.append('<seg type="original" xml:lang="de">%s</seg>' % tags_to_tei(note['de']))
        out.append('<seg type="translation" xml:lang="en" source="#claude">%s</seg>' % tags_to_tei(note['en']))
    else:
        attrs = 'type="editorNote" subtype="%s" xml:id="%s" n="%s" source="#%s"' % (note['kind'], note['id'], note['n'], note['owner'])
        if note['whole']:
            attrs += ' rend="wholeClause"'
        out = ['<note xmlns="%s" %s>' % (TEI, attrs)]
        m = re.search(r'p\. (\d+)', note['where'])
        if m:
            out.append('<bibl><biblScope unit="page">%s</biblScope></bibl>' % m.group(1))
        if note.get('word'):
            out.append('<label>%s</label>' % tags_to_tei(note['word']))
        out.append('<seg type="original" xml:lang="en">%s</seg>' % tags_to_tei(note['text']))
    if note['remark']:
        out.append('<note type="remark" resp="#claude">%s</note>' % tags_to_tei(note['remark']))
    out.append('</note>')
    return etree.fromstring(''.join(out))


def _append(parent, el):
    """Append `el` on its own line, indented like its last sibling."""
    kids = list(parent)
    if kids:
        el.tail = kids[-1].tail
        kids[-1].tail = parent.text if parent.text and parent.text.strip() == '' else '\n'
    parent.append(el)


def ensure_sources(doc, notes):
    lb = doc.find('.//t:listBibl[@type="sources"]', NS)
    ids = {b.get('{%s}id' % XML) for b in lb.findall('t:bibl', NS)}
    wrap = '<listBibl xmlns="%s">%s</listBibl>'
    lieb = [n for n in notes if n['owner'] == 'liebermann']
    if any(n['kind'] == 'de' for n in lieb) and 'liebermann-erkl' not in ids:
        _append(lb, etree.fromstring(wrap % (TEI, ERKL_BIBL))[0])
    if lieb and 'claude' not in ids:
        _append(lb, etree.fromstring(wrap % (TEI, CLAUDE_BIBL))[0])
    for owner in sorted({n['owner'] for n in notes} - {'liebermann'}):
        if owner not in ids:
            _append(lb, etree.fromstring(wrap % (TEI, EDITOR_BIBL[owner]))[0])
    ts = doc.find('.//t:titleStmt', NS)
    resps = [r.findtext('t:resp', namespaces=NS) or '' for r in ts.findall('t:respStmt', NS)]
    if lieb and not any('Liebermann’s notes' in r for r in resps):
        _append(ts, etree.fromstring('<titleStmt xmlns="%s">%s</titleStmt>' % (TEI, RESP))[0])
    for owner in sorted({n['owner'] for n in notes} - {'liebermann'}):
        who = EDITOR_NAME[owner]
        if not any(who + '’s notes' in r for r in resps):
            _append(ts, etree.fromstring('<titleStmt xmlns="%s"><respStmt><resp>Transcription of %s’s notes</resp><name ref="#claude">Claude</name></respStmt></titleStmt>' % (TEI, who))[0])


def candidates(div, col, used):
    """The <ab> elements a column of the spreadsheet can be, in the clause file."""
    tree = div.getroottree()
    abs_ = [a for a in div.findall('t:ab', NS) if tree.getpath(a) not in used]
    src = lambda a: (a.get('source') or '').lstrip('#')
    lang = lambda a: a.get('{%s}lang' % XML) or ''
    if col in LIEB_TEXT:
        return [a for a in abs_ if a.get('type') == 'liebermannText']
    if col == 'L':
        return [a for a in abs_ if a.get('type') == 'translation' and lang(a) == 'de']
    if col == 'T':
        return [a for a in abs_ if a.get('type') == 'editionText']
    if col == 'BL':   # Attenborough's own text, where T is another editor's
        return [a for a in abs_ if a.get('type') == 'editionText' and src(a) == 'attenborough']
    return [a for a in abs_ if a.get('type') == 'translation' and lang(a) != 'de' and src(a) != 'claude']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('workbook')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    texts, notes = read_workbook(args.workbook)
    changed, problems = 0, []
    for slug in sorted(set(texts) | set(notes)):
        path = os.path.join(LAWS, slug + '.xml')
        if not os.path.exists(path):
            problems.append('%s: no clause file' % slug)
            continue
        doc = etree.parse(path, etree.XMLParser(remove_blank_text=False))
        strip_old(doc)
        div = doc.find('.//t:div[@type="clause"]', NS)
        ns_ = notes.get(slug, [])
        assign_ids(slug, ns_)
        # number -> note ids, per group of columns, in order
        queues = {}
        for note in ns_:
            if note['whole']:
                continue
            if note['owner'] == 'liebermann':
                key = 'lieb-text' if note['kind'] == 'oe' else 'lieb-de'
            else:
                key = note['owner'] + ('-T' if note['kind'] == 'footnote' else '-tr')
            queues.setdefault((key, note['n']), []).append(note['id'])

        byid = {x['id']: x for x in ns_}
        last, taken = {}, set()

        def target(key, col=''):
            def f(n):
                q = queues.get((key, n))
                if q and col and key == 'lieb-text':
                    # Liebermann's footnotes are numbered per column: take the next note of this column; a number
                    # printed twice in a column (one footnote) points to the same note again
                    mine = [i for i in q if byid[i].get('col') == col and i not in taken]
                    if mine:
                        taken.add(mine[0]); last[(col, n)] = mine[0]
                        return mine[0]
                    if (col, n) in last:
                        return last[(col, n)]
                    rest = [i for i in q if i not in taken]
                    if rest:
                        taken.add(rest[0]); return rest[0]
                    return q[-1]
                if not q and key.endswith('-tr') and n == '1':
                    # Attenborough sometimes prints the note to a clause without its number (II As 12,
                    # III As Inscr.): the marker {1} in his translation goes to that one unnumbered note
                    whole = [x for x in ns_ if x['owner'] == key[:-3] and x['kind'] == 'endnote' and x['whole']]
                    if len(whole) == 1:
                        whole[0]['whole'] = False
                        return whole[0]['id']
                if not q:
                    problems.append('%s: no note %s for marker {%s}' % (slug, key, n))
                    return 'missing'
                return q.pop(0) if len(q) > 1 else q[0]
            return f
        ok, used = True, set()
        for col, marked in texts.get(slug, {}).items():
            if not MARK.search(marked):
                continue
            want = unicodedata.normalize('NFC', MARK.sub('', marked).strip())
            cands = [a for a in candidates(div, col, used) if plain_of(a) == want]
            if not cands:
                problems.append('%s, column %s: no text in the clause file matches:\n   workbook: %s' % (slug, col, want))
                ok = False
                continue
            if col in LIEB_TEXT:
                key, ptr = 'lieb-text', 'liebermannNote'
            elif col == 'L':
                key, ptr = 'lieb-de', 'liebermannNote'
            else:
                owners = [x['owner'] for x in ns_ if x['owner'] != 'liebermann' and x.get('col') == col]
                owner = owners[0] if owners else ('whitelock' if col == 'AP' else 'attenborough')
                key, ptr = owner + ('-T' if col in ('T', 'BL') else '-tr'), 'editorNote'
            new = insert_markers(cands[0], marked, ptr, target(key, col))
            used.add(doc.getpath(new))
        if not ok:
            continue
        if any(x['owner'] == 'whitelock' for x in ns_):
            # her footnotes, now linked to her numbers, replace the plain list from column AT
            for old in div.xpath('t:note[@type="translator" and @source="#whitelock"]', namespaces=NS):
                div.remove(old)
        for note in ns_:
            div.append(note_xml(note))
        ensure_sources(doc, ns_)
        out = etree.tostring(doc, encoding='unicode')
        out = re.sub(r'\s*(<note type="(?:liebermannNote|editorNote)")', r'\n        \1', out)
        out = re.sub(r'</note>\s*</div>', '</note>\n      </div>', out)
        out = '<?xml version="1.0" encoding="UTF-8"?>\n' + out + '\n'
        if not args.dry_run:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(out)
        changed += 1
    print('%s %d clause files' % ('Would change' if args.dry_run else 'Changed', changed))
    for p in problems:
        print('PROBLEM', p)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
