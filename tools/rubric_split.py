"""Split Jurasinski and Oliver's two rubrics (MS E, then MS B) apart.

For the rubrics to Alfred's and Ine's laws (Af Rb, Ine Rb), Jurasinski and
Oliver, *The Laws of Alfred* (2021), edit the rubric list of MS E (CCCC 173)
and also print, in full, the rubrics of MS B (CCCC 383), whose scribe put
them above the clauses they head and sometimes corrected them. In the
spreadsheet both rubrics sit in one cell ("modern editor's text"), E's
first, and both translations sit in the next ("modern editor's
translation"). This module separates them so the site can show B's rubric
as its own text, labelled MS B.

Rules:
  * B's rubric begins at the second "Be" (capital B) in the Old English, and
    at the second "Concerning" in the English. The exceptions are listed in
    SPECIAL below.
  * Where E and B translate the same (ignoring italics and a leading
    "Concerning"), only one
    translation is kept, so the same English is not shown twice.
  * A cell with only one rubric (B has none of its own) is left alone.
See docs/OE-LAWS.md.
"""
import re

RUBRIC_CODES = {'Af Rb', 'Ine Rb'}

# clause: (where B begins in the Old English, where it begins in the English)
SPECIAL = {
    ('Af Rb', '11'): (' Eft', ' Further'),
    ('Af Rb', '37'): (None, ' About'),
    ('Af Rb', '39'): (' Eft', ' Following'),
    ('Ine Rb', '14'): (' hloðe', ' a band'),
    ('Ine Rb', 'Ine Prol.'): (' Ines lage', None),
}


def _cut(xml, marker, first_word):
    """Split xml before the second occurrence of first_word (or before marker)."""
    if marker:
        i = xml.rfind(marker) if marker in (' hloðe', ' a band') else xml.find(marker)
    else:
        start = xml.find(first_word)
        i = xml.find(' ' + first_word, start + 1) if start >= 0 else -1
    if i <= 0:
        return xml, ''
    return xml[:i].strip(), xml[i:].strip()


def plain(xml):
    s = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', xml)).strip().rstrip('.').lower()
    return re.sub(r'^(concerning|about) ', '', s)


def split(code, clause, text_xml, trans_xml):
    """Return (e_text, b_text, e_trans, b_trans); b_* are '' when not needed."""
    if code not in RUBRIC_CODES or not text_xml:
        return text_xml, '', trans_xml, ''
    oe_mark, en_mark = SPECIAL.get((code, clause), (None, None))
    e_text, b_text = _cut(text_xml, oe_mark, 'Be')
    if not b_text:
        return text_xml, '', trans_xml, ''
    e_trans, b_trans = _cut(trans_xml or '', en_mark, 'Concerning')
    if b_trans and plain(e_trans) == plain(b_trans):
        b_trans = ''
    if not b_trans:
        e_trans = e_trans if e_trans else trans_xml
    return e_text, b_text, e_trans, b_trans
