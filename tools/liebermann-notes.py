#!/usr/bin/env python3
"""
Adds Liebermann's notes to the clause files in oe-laws/ from the workbook
"Liebermann_notes_<code>.xlsx" (first made for Æthelberht, October 2026).

    python3 tools/liebermann-notes.py Liebermann_notes_Abt.xlsx --dry-run
    python3 tools/liebermann-notes.py Liebermann_notes_Abt.xlsx

Needs Python 3, openpyxl and lxml (pip install openpyxl lxml).

Run it AFTER tools/laws-from-database.py: that script rebuilds the clause files
from the main spreadsheet and so takes the notes out again. Running this one
twice does no harm: it first removes the notes it added before.

Two kinds of note (see docs/OE-LAWS.md, "Liebermann's notes"):

- textual notes on his Old English (or Latin) text, printed at the foot of the
  column in Gesetze I;
- his Erklärungen, the notes to his German translation, printed in Gesetze III.

In the workbook, sheet "Texts with note markers" holds columns K and L of the
main spreadsheet with each note number in curly brackets after its word:
{4}, {*}, {+1} (a number Liebermann forgot to print and supplies in vol. III),
{2/4} (number 2, misprinted 4 in vol. I). Taking out the brackets must give
the texts now in the clause file exactly; if not, the file is left alone and
the difference reported. Sheet "Liebermann notes" holds the notes, one line per
note per clause row: German as printed, Claude's English, remarks.

In the clause file the numbers become empty pointers inside the text, which
the plain view of the clause page ignores:

    <ab type="liebermannText" …>Godes<ptr type="liebermannNote" n="4" target="#Abt_1-a.lnote.oe.4"/> feoh …</ab>

and the notes go at the end of the clause:

    <note type="liebermannNote" subtype="textual" xml:id="Abt_1-a.lnote.oe.4" n="4" source="#liebermann">
      <bibl><biblScope unit="volume">1</biblScope><biblScope unit="page">3</biblScope></bibl>
      <seg type="original" xml:lang="de">Godes feoh ⁊ ci <hi rend="italic">in Capitalschrift</hi></seg>
      <seg type="translation" xml:lang="en" source="#claude">Godes feoh ⁊ ci in capital letters</seg>
    </note>

subtype "textual" (vol. I, on the Old English), "erklaerung" (vol. III, on the
German) or "translationFootnote" (vol. I's own footnote to the German).
"""
import argparse
import os
import re
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
MARK = re.compile(r'\{(\+?)([0-9a-z*]+)(?:/([0-9*]+))?\}')

ERKL_BIBL = ('<bibl xml:id="liebermann-erkl" type="commentary"><author>Felix Liebermann</author>, '
             '<title>Die Gesetze der Angelsachsen</title>, vol. <biblScope unit="volume">3</biblScope>: '
             '<title>Einleitung zu jedem Stück; Erklärungen zu einzelnen Stellen</title> '
             '(Halle: Niemeyer, 1916)</bibl>')
CLAUDE_BIBL = ('<bibl xml:id="claude" type="translation">A semi-literal English rendering of Liebermann’s German, made for this database in 2026 with Claude, a large language model (LLM) made by Anthropic. It is a crib to help the reader with Liebermann’s German, not a separate translation</bibl>')
RESP = ('<respStmt><resp>Transcription and English translation of Liebermann’s notes</resp>'
        '<name ref="#claude">Claude</name></respStmt>')


def tags_to_tei(s):
    """The workbook's light markup -> TEI. <i> italic, <b> bold, <sp> letter-spaced, <sc> small caps."""
    s = escape(s or '')
    for tag, rend in (('i', 'italic'), ('b', 'bold'), ('sp', 'spaced'), ('sc', 'smallcaps')):
        s = s.replace('&lt;%s&gt;' % tag, '<hi rend="%s">' % rend).replace('&lt;/%s&gt;' % tag, '</hi>')
    s = s.replace('\n\n', '<lb type="paragraph"/>').replace('\n', ' ')
    return s


def note_id(slug, kind, n):
    return '%s.lnote.%s.%s' % (slug, kind, 'star' if n == '*' else n)


def read_workbook(path):
    wb = openpyxl.load_workbook(path, read_only=True)
    texts = {}
    for row in list(wb['Texts with note markers'].iter_rows(values_only=True))[1:]:
        if not row or not row[1]:
            continue
        texts[row[1]] = {'K': row[5] or '', 'L': row[6] or '', 'page': row[4]}
    notes = {}
    for row in list(wb['Liebermann notes'].iter_rows(values_only=True))[1:]:
        if not row or not row[1]:
            continue
        slug, on, where, n, printed, de, en, remark = row[1], row[4] or '', row[5] or '', str(row[6]), row[7] or '', row[8], row[9], row[10] or ''
        kind = 'oe' if on.startswith('Old English') else ('de1' if where.startswith('Gesetze I p.') else 'de')
        notes.setdefault(slug, []).append(dict(kind=kind, n=n, where=where, printed=printed, de=de, en=en,
                                               remark=remark, whole=on.endswith('whole clause')))
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


def insert_markers(ab, marked, slug, kind):
    """Put <ptr> elements into <ab> where the {n} codes stand in `marked`. Returns an error or None."""
    current = re.sub(r'\s+', ' ', ab.xpath('string()')).strip()
    plain = MARK.sub('', marked)
    if plain != current:
        return 'text differs from the clause file:\n   file:     %s\n   workbook: %s' % (current, plain)
    # offsets of the markers in the plain text
    found, offset, last = [], 0, 0
    for m in MARK.finditer(marked):
        offset += m.start() - last
        last = m.end()
        found.append((offset, m.group(1) == '+', m.group(2), m.group(3)))
    if not found:
        return None
    head = (ab.text or '')
    body = etree.tostring(ab, encoding='unicode', with_tail=False)
    start = body.index('>') + 1
    end = body.rindex('</')
    inner = body[start:end]
    # leading whitespace in the file is not in `current`
    lead = len(head) - len(head.lstrip())
    ends = char_positions(inner)
    pieces, prev = [], 0
    for off, supplied, n, printed in found:
        pos = 0 if off == 0 else ends[lead + off - 1]
        if off == 0:
            pos = lead and ends[lead - 1] or 0
        attrs = 'type="liebermannNote" n="%s" target="#%s"' % (n, note_id(slug, kind if n != '*' or kind == 'oe' else 'de1', n))
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
    return None


def strip_old(doc):
    for p in doc.xpath('//t:ptr[@type="liebermannNote"]', namespaces=NS):
        parent = p.getparent()
        prev = p.getprevious()
        if p.tail:
            if prev is not None:
                prev.tail = (prev.tail or '') + p.tail
            else:
                parent.text = (parent.text or '') + p.tail
        parent.remove(p)
    for n in doc.xpath('//t:note[@type="liebermannNote"]', namespaces=NS):
        n.getparent().remove(n)


def note_xml(slug, note):
    kind = note['kind']
    nid = note_id(slug, kind, note['n'])
    m = re.search(r'Gesetze (I+) p\. (\d+)(?:, col\. (\d))?', note['where'])
    vol = {'I': '1', 'III': '3'}[m.group(1)] if m else ''
    subtype = {'oe': 'textual', 'de': 'erklaerung', 'de1': 'translationFootnote'}[kind]
    source = '#liebermann-erkl' if kind == 'de' else '#liebermann'
    attrs = 'type="liebermannNote" subtype="%s" xml:id="%s" n="%s" source="%s"' % (subtype, nid, note['n'], source)
    if note['whole']:
        attrs += ' rend="wholeClause"'
    if note['printed'] and note['printed'] not in ('not printed', 'no number'):
        attrs += ' rend="printed-as-%s"' % note['printed']
    out = ['<note xmlns="%s" %s>' % (TEI, attrs)]
    if m:
        out.append('<bibl><biblScope unit="volume">%s</biblScope><biblScope unit="page">%s</biblScope>%s</bibl>'
                   % (vol, m.group(2), '<biblScope unit="column">%s</biblScope>' % m.group(3) if m.group(3) else ''))
    out.append('<seg type="original" xml:lang="de">%s</seg>' % tags_to_tei(note['de']))
    out.append('<seg type="translation" xml:lang="en" source="#claude">%s</seg>' % tags_to_tei(note['en']))
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


def ensure_sources(doc, has_erkl):
    lb = doc.find('.//t:listBibl[@type="sources"]', NS)
    ids = {b.get('{%s}id' % XML) for b in lb.findall('t:bibl', NS)}
    wrap = '<listBibl xmlns="%s">%s</listBibl>'
    if has_erkl and 'liebermann-erkl' not in ids:
        _append(lb, etree.fromstring(wrap % (TEI, ERKL_BIBL))[0])
    if 'claude' not in ids:
        _append(lb, etree.fromstring(wrap % (TEI, CLAUDE_BIBL))[0])
    ts = doc.find('.//t:titleStmt', NS)
    if not any('Liebermann’s notes' in (r.findtext('t:resp', namespaces=NS) or '') for r in ts.findall('t:respStmt', NS)):
        _append(ts, etree.fromstring('<titleStmt xmlns="%s">%s</titleStmt>' % (TEI, RESP))[0])


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
        parser = etree.XMLParser(remove_blank_text=False)
        doc = etree.parse(path, parser)
        strip_old(doc)
        div = doc.find('.//t:div[@type="clause"]', NS)
        t = texts.get(slug, {})
        ok = True
        for col, xp, kind in (('K', 't:ab[@type="liebermannText"]', 'oe'),
                              ('L', 't:ab[@type="translation"][@xml:lang="de"]', 'de')):
            if not t.get(col):
                continue
            ab = div.find(xp, {'t': TEI, 'xml': XML}) if col == 'K' else div.xpath(xp, namespaces={'t': TEI})
            if isinstance(ab, list):
                ab = ab[0] if ab else None
            if ab is None:
                problems.append('%s: no text for column %s' % (slug, col))
                ok = False
                continue
            err = insert_markers(ab, t[col], slug, kind)
            if err:
                problems.append('%s, column %s: %s' % (slug, col, err))
                ok = False
        if not ok:
            continue
        ns_ = notes.get(slug, [])
        # notes go after the texts and any notes already there
        for note in ns_:
            div.append(note_xml(slug, note))
        ensure_sources(doc, any(n['kind'] == 'de' for n in ns_))
        out = etree.tostring(doc, encoding='unicode')
        out = re.sub(r'\s*(<note type="liebermannNote")', r'\n        \1', out)
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
