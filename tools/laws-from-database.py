#!/usr/bin/env python3
"""
Makes the clause files in oe-laws/ from the full laws database spreadsheet
(the October 2026 layout, columns A–AO: "OE_Laws_Database - Updated by
Claude.xlsx" and its later versions).

    python3 tools/laws-from-database.py "OE_Laws_Database - Updated by Claude.xlsx" --dry-run
    python3 tools/laws-from-database.py "OE_Laws_Database - Updated by Claude.xlsx"
    python3 tools/laws-from-database.py DATABASE.xlsx --code Ine      # one law code only

Needs Python 3 and openpyxl (pip install openpyxl).

Each clause row becomes one TEI file with every text the row has:
Liebermann's text and the manuscript it comes from (K), his German
translation (L), Claude's English of the German (M), his second and third
manuscripts (N, AF), the Quadripartitus Latin (O), the modern editor's text
and translation (T, U), a second translation (W), and a translation of the
manuscript in K (AA). Every text says which manuscript it is from (columns
AJ–AO), and every translation who made it. See docs/OE-LAWS.md.

File names do not change: a row keeps the file name its clause had before,
so the links from dictionary entries still work. Rows are matched to the old
files by law code and clause number. Law codes listed in SKIP are left exactly as
they are (none at present). Cn 1018, which is not in Liebermann, takes its
clause numbers from column S (Kennedy's, which Rabin follows).
"""
import argparse
import datetime
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict
from xml.sax.saxutils import escape

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


old = _load('laws_from_xlsx', 'laws-from-xlsx.py')       # slugify, clause keys, anchors, witnesses
abt = _load('law_code_from_xlsx', 'law-code-from-xlsx.py')  # italic runs
rubrics = _load('rubric_split', 'rubric_split.py')         # J&O's E and B rubrics, apart

SKIP = set()

# Header text (start of it, case and spaces ignored) -> our name for the column.
HEADERS = [
    ("liebermann's full code abbreviation", 'citation'),
    ("liebermann's code abbreviation", 'code'),
    ("liebermann's internal clause numbering", 'clause'),
    ('full english name', 'codeName'),
    ('issuing king', 'king'),
    ('place and date of promulgation', 'promulgation'),
    ('mss', 'mss'),
    ("liebermann's ms selected", 'liebermannMS'),
    ('gesetze', 'page'),
    ('editorial cap. numbers of selected ms text, liebermann', 'liebermannNumber'),
    ("liebermann's text", 'kText'),
    ("liebermann's german translation", 'german'),
    ('semi-literal translation', 'english'),
    ("liebermann's second ms", 'nText'),
    ("liebermann's quadripartitus", 'latin'),
    ('modern edition', 'editionRef'),
    ('short name of modern editor', 'editor'),
    ('ms used by modern editor', 'editorMS'),
    ('editorial cap. numbers of selected ms text, modern editor', 'editorNumber'),
    ("modern editor's text", 'tText'),
    ("modern editor's translation", 'translation'),
    ("page number of modern editor", 'editorPage'),
    ('second translation', 'secondTranslation'),
    ("second translator's name", 'secondRef'),
    ('page number of second translator', 'secondPage'),
    ('supplementary ms', 'supplementary'),
    ('translation of supplementary ms', 'supplementaryTranslation'),
    ('offence', 'offence'),
    ('people', 'people'),
    ('locations', 'locations'),
    ("siglum of liebermann's second ms", 'nSig'),
    ("liebermann's third ms", 'afText'),
    ("siglum of liebermann's third ms", 'afSig'),
    ('source of the passage', 'passageSource'),
    ('notes on this row', 'notes'),
    ("liebermann's siglum for the manuscript in column k", 'kSig'),
    ('manuscript in column k', 'kName'),
    ("manuscript of liebermann's second ms", 'nName'),
    ("manuscript of liebermann's third ms", 'afName'),
    ('siglum of the manuscript in column t', 'tSig'),
    ('manuscript in column t', 'tName'),
    ('third translation', 'thirdTranslation'),
    ("third translator's name", 'thirdRef'),
    ('ms used by third translator', 'thirdMS'),
    ("page number of third translator", 'thirdPage'),
    ("whitelock's footnotes", 'translatorNotes'),
    ('edition 2 (rabin)', 'rabinText'),
    ('rabin’s translation', 'rabinTranslation'),
    ('rabin’s edition and base ms', 'rabinRef'),
    ('page numbers in rabin', 'rabinPage'),
    ('rabin’s textual notes', 'rabinTextNotes'),
    ('rabin’s notes to the translation', 'rabinNotes'),
]
NEEDED = ['code', 'clause', 'kText', 'german', 'english', 'nText', 'kSig', 'tSig', 'notes']

LIEBERMANN_REF = ('<author>Felix Liebermann</author>, <title>Die Gesetze der Angelsachsen</title>, '
                  'vol. <biblScope unit="volume">1</biblScope> (Halle: Niemeyer, 1903)')
CLAUDE_REF = ('Claude (an AI model made by Anthropic), semi-literal English translation of '
              'Liebermann’s German, made for this database in 2026')

# Translators named in the original spreadsheet's sub-header rows for the law
# codes that have no modern editor (column T there is Liebermann's text).
# The spreadsheet no longer has those rows, so they are recorded here.
WHITELOCK_EHD = ('Dorothy Whitelock, ed., <title>English Historical Documents, I: c. 500–1042</title> '
                 '(London: Eyre &amp; Spottiswoode, 1955; 2nd edn, London: Eyre Methuen, 1979); '
                 'page numbers are those of the Taylor &amp; Francis e-Library edition (2007)')
# Rows of Had whose translation in column U is not Whitelock's (EHD prints Had 1-2 and 9-11 only).
NOT_WHITELOCK = 'not in Whitelock’s English Historical Documents'
WHITELOCK_CS = ('D. Whitelock, M. Brett and C. N. L. Brooke, eds, <title>Councils and Synods with Other '
                'Documents Relating to the English Church, I: A.D. 871–1204</title> (Oxford: Clarendon Press, 1981)')
TRANSLATORS = {   # code -> (translator of U, translator of AA)
    'Northu': ('Whitelock', None), 'Wif': ('Whitelock', None), 'Geþyncðo': ('Whitelock', 'Rabin'),
    'Norðleoda': ('Whitelock', 'Rabin'), 'Mirce': ('Whitelock', 'Rabin'), 'Að': ('Whitelock', 'Rabin'),
    'Had': ('Whitelock', 'Rabin'), 'Wer': ('Wormald', None), 'Becwæð': ('Wormald', 'Wormald'),
    'Episc': ('Whitelock C&S', None),
}
# Rabin's edition with facing Old English text, named in the sub-header rows
# of Grið and Nor Grið (the spreadsheet's column P names his 2015 book of
# translations, which has no Old English text).
RABIN_DOML = ('Andrew Rabin, ed. and trans., <title>Old English Legal Writings: Wulfstan</title>, '
              'Dumbarton Oaks Medieval Library (Cambridge, MA: Harvard University Press, 2020)')
# Rabin's sigla that mean a different manuscript from Liebermann's letter
RABIN_SIGLA = {('Prom. Reg.', 'C'): 'Cp', ('Cn 1020', 'Y'): 'York Gospels', ('IX Atr', 'MS'): '', ('X Atr', 'MS'): '',
               ('V Atr', 'G1'): 'G', ('II Eg', 'G1'): 'G', ('III Eg', 'G1'): 'G'}   # Rabin's G1 is Liebermann's G
EDITOR_OVERRIDE = {'Grið': ('Rabin', 'rabin-doml', RABIN_DOML), 'Nor Grið': ('Rabin', 'rabin-doml', RABIN_DOML)}

# Old spellings of law codes (in oe-laws/index.json) -> the spreadsheet's.
OLD_CODES = {
    'Rubric List': 'Af Rb', 'Rubrics: AF': 'Af Rb', 'Rubrics: Af': 'Af Rb', 'Rubrics Af': 'Af Rb',
    'Rubrics: INE': 'Ine Rb', 'Rubrics: Ine': 'Ine Rb', 'VI Atr (Latin Paraphrase)': 'VI Atr Lat',
    'Ord': 'Ordal', 'Blas.': 'Blas', 'Forf.': 'Forf', 'Becw': 'Becwæð', 'Geþyn.': 'Geþyncðo',
    'Norðleod.': 'Norðleoda', 'Mirc.': 'Mirce', 'Had.': 'Had', 'Nor. Cyricgrið': 'Nor Grið',
    'Rom.': 'Romscot', 'Iud. Dei VIII': 'Iud Dei VIII',
}

MS_NAMES = {
    'H': 'Strood, Medway Archive and Local Studies Centre, MS DRc/R1 (Textus Roffensis; formerly Rochester, Cathedral Library, A.3.5), c. 1120–25',
    'E': 'Cambridge, Corpus Christi College, MS 173 (Parker Chronicle and Laws)',
    'B': 'Cambridge, Corpus Christi College, MS 383',
    'B1': 'Cambridge, Corpus Christi College, MS 383 (first copy)',
    'B2': 'Cambridge, Corpus Christi College, MS 383 (second copy)',
    'D': 'Cambridge, Corpus Christi College, MS 201',
    'G': 'London, British Library, Cotton Nero A.i',
    'G2': 'London, British Library, Cotton Nero A.i (second text)',   # the spreadsheet names it code by code
    'A': 'London, British Library, Harley 55',
    'F': 'London, British Library, Cotton Nero E.i',
    'C': 'Cambridge, Corpus Christi College, MS 265',
    'K': 'London, British Library, Cotton Claudius A.iii',
    'O': 'Cambridge, Corpus Christi College, MS 190',
    'X': 'Oxford, Bodleian Library, Junius 121',
    'Ca': 'Cambridge, Corpus Christi College, MS 422',
    'Cp': 'London, British Library, Cotton Cleopatra B.xiii',
    'Ot': 'London, British Library, Cotton Otho B.xi (damaged by fire, 1731)',
    'So': "William Somner's transcript of Cotton Otho B.xi (made before the fire)",
    'Ld': 'William Lambarde, Archaionomia (London, 1568) – printed from manuscripts now lost',
    'Q': 'Quadripartitus (Latin translation, c. 1114), as edited by Liebermann',
    'Cons. Cn.': 'Consiliatio Cnuti (Latin translation, early 12th c.)',
    'Fl': 'Florence (John) of Worcester, Chronicon (Latin)',
    'Fl, Ox': 'Florence (John) of Worcester, Chronicon, and Oxford, Corpus Christi College MS 157',
    'Wanley': 'Cotton Otho A.x (burnt 1731), known only from Wanley’s extract in Hickes, Thesaurus (1705)',
    'Vr': 'Vatican, Biblioteca Apostolica, Reg. lat. 946',
    'York Gospels': 'York, Minster Library, Add. 1 (York Gospels)',
}

esc = escape
attr = old.attr


def norm_header(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip().lower()


def columns(ws):
    found = {}
    for c in range(1, ws.max_column + 1):
        h = norm_header(ws.cell(1, c).value)
        for start, name in HEADERS:
            if h.startswith(start) and name not in found:
                found[name] = c
                break
    missing = [n for n in NEEDED if n not in found]
    if missing:
        sys.exit('These columns were not found in row 1: ' + ', '.join(missing))
    return found


def sig_key(s):
    """'G(A)', 'G (B)', 'Ot (burnt)' -> 'G', 'G', 'Ot'."""
    return re.sub(r'\s*\(.*?\)\s*', '', s or '').strip()


def same_sig(a, b):
    """'Cons.Cn.' and 'Cons. Cn.' are the same siglum."""
    return re.sub(r'[\s.]', '', a).lower() == re.sub(r'[\s.]', '', b).lower()


def ident(text):
    return old.slugify(text).lower() or 'x'


LATIN = set('et est in de ut non uel vel quod cum si qui quae quo ad per sed enim autem eius sit ab ex nec aut atque '
            'uero vero item hoc hec quodsi similiter debet omni omnis omnes deo dei regis rex'.split())
OE = set('and þæt ðæt se he man ne gif gyf ðe þe beo sy to his hit mid swa ofer þonne ðonne bete gebete '
         'scillinga is wið þam ðam'.split())


def language(text):
    if re.search('[⁊þðæÞÐÆƿ]', text):
        return 'ang'
    words = re.findall(r"[a-zę]+", text.lower())
    la = sum(w in LATIN for w in words)
    oe = sum(w in OE for w in words)
    if la == oe == 0 and words:
        # a heading such as 'Iudicia ciuitatis Lundonię': go by the endings
        la = sum(bool(re.search(r'(um|us|ae|ę|is|orum|ibus|tio|tia)$', w)) for w in words) > len(words) / 3
    return 'la' if la > oe else 'ang'


# ---------------------------------------------------------------- notes
CHECK = re.compile(r'^K: (checked against|corrected against|added from) Gesetze I p\. ?([^\s;(]+)(?: \(was: ".*?"\))?(?=;|$)')
ROB = re.compile(r'^([TU]): corrected against Robertson p\. ?([^\s;(]+) \((?:was: ".*?"|(?:"[^"]*" → "[^"]*"(?:; )?)+)\)(?=;|$)')
MINOR = re.compile(r'^(?:[RE]: was "[^"]*"|T: ‘[^’]*’ corrected to ‘[^’]*’[^;]*|C: was [^;]*?(?= \(|;|$)(?: \([^)]*\))?|I: Gesetze page added|'
                   r'K: (?:a |the )?(?:double space|doubled|stray|spacing|line break)[^.;]*?(?:removed|corrected)\.?)(?=;|$|\s)')


# Remarks about the spreadsheet itself, which mean nothing on the website.
NOTE_TIDY = [
    (r'\s*A line break inside K was removed\.', ''),
    (r'\s*Only (?:the )?(?:italic formatting|spacing)(?: and ‘[^’]*’)?(?: of K)? (?:was|were) (?:corrected|tidied)(?: in K)?\.', ''),
    (r', text in column T(?=[.)])', ''),
    (r'\(text in column T; ', '('),
    (r' \(text in column T\)', ''),
    (r'\bis in column T\b', 'is also given here'),
    (r', already in column T', ''),
    (r' \(which is also column T\)', ''),
    (r'the same MS as column T', 'the same manuscript as the modern edition'),
    (r' \(as in the original layout(?: of this (?:code|text))?\)', ''),
    (r'K here (?:is|holds) the Quadripartitus Latin', 'The Latin is the Quadripartitus'),
    (r"Liebermann's (?:OE|Old English) from", "Liebermann's Old English is from"),
    (r',? (?:is )?(?:now )?in N(?=[.;,])', ''),
]


def tidy_note(text):
    for a, b in NOTE_TIDY:
        text = re.sub(a, b, text)
    return text.strip()


def split_notes(text):
    """Column AI -> (record of checks for revisionDesc, editorial notes for readers)."""
    checks, keep = [], []
    rest = (text or '').strip()
    pieces = re.split(r'; (?=[A-Z][A-Za-z]{0,3}: )', rest) if rest else []
    for p in pieces:
        p = p.strip()
        while p:
            m = CHECK.match(p)
            if m:
                verb = {'checked against': 'checked against', 'corrected against': 'corrected against',
                        'added from': 'added from'}[m.group(1)]
                checks.append(('liebermann', verb, m.group(2)))
                p = p[m.end():].lstrip('; ').strip()
                continue
            m = ROB.match(p)
            if m:
                checks.append(('robertson-' + m.group(1), 'corrected against', m.group(2)))
                p = p[m.end():].lstrip('; ').strip()
                continue
            m = MINOR.match(p)
            if m:
                p = p[m.end():].lstrip('; ').strip()
                continue
            break
        if p:
            keep.append(p)
    return checks, tidy_note('; '.join(keep))


# ---------------------------------------------------------------- reading
def read_rows(path, only=None):
    wb = openpyxl.load_workbook(path, rich_text=True)
    ws = wb['Sheet1'] if 'Sheet1' in wb.sheetnames else wb.active
    col = columns(ws)
    rows = []
    for r in range(2, ws.max_row + 1):
        cell = lambda name: ws.cell(r, col[name]) if name in col else None
        get = lambda name: old.clean(abt.plain(cell(name).value)) if cell(name) is not None else ''
        xml = lambda name: abt.marked(cell(name).value) if cell(name) is not None else ''
        code = get('code')
        if not code or (only and code not in only):
            continue
        row = {'sheetRow': r, 'code': code, 'clause': get('clause')}
        for name in ('codeName', 'king', 'promulgation', 'liebermannMS', 'page', 'liebermannNumber', 'editor',
                     'editorMS', 'editorNumber', 'editorPage', 'secondPage', 'offence', 'people', 'locations',
                     'nSig', 'afSig', 'kSig', 'tSig', 'kName', 'nName', 'afName', 'tName', 'notes', 'passageSource',
                     'thirdRef', 'thirdMS', 'thirdPage', 'translatorNotes', 'rabinRef', 'rabinPage', 'rabinTextNotes', 'rabinNotes'):
            row[name] = get(name)
        for name in ('kText', 'german', 'english', 'nText', 'latin', 'tText', 'translation',
                     'secondTranslation', 'supplementaryTranslation', 'afText', 'thirdTranslation', 'rabinText', 'rabinTranslation'):
            row[name + 'Xml'] = xml(name)
            row[name] = get(name)
        row['passageSourceXml'] = xml('passageSource')
        row['editionRefXml'] = abt.marked(cell('editionRef').value, '<title>%s</title>') if 'editionRef' in col else ''
        row['secondRefXml'] = abt.marked(cell('secondRef').value, '<title>%s</title>') if 'secondRef' in col else ''
        row['secondRef'] = get('secondRef')
        row['witnesses'] = old.witnesses(cell('mss')) if 'mss' in col else []
        if code == 'Cn 1018':
            # not in Liebermann: Kennedy's numbering (column S), which Rabin follows
            row['clause'] = {'Prologue': 'Prol.'}.get(row['editorNumber'], row['editorNumber'])
        rows.append(row)
    return rows


# Keywords that mean the same, merged into one (the first form is kept).
SAME_KEYWORD = {'Kings': 'King'}


def keywords(terms):
    """A cell's keywords, with SAME_KEYWORD applied and nothing listed twice."""
    out = []
    for t in old.split_terms(terms):
        t = SAME_KEYWORD.get(t, t)
        if t not in out:
            out.append(t)
    return out


# ---------------------------------------------------------------- building
class Sources:
    """The editions and translations one file names, in the order first used."""
    def __init__(self):
        self.items = {}

    def add(self, sid, name, xml, kind, page=''):
        if sid not in self.items:
            self.items[sid] = (name, xml, kind, page)
        return sid


def build(row, today, source_name, refs):
    code, clause = row['code'], row['clause']
    citation = ('%s %s' % (code, clause)).strip()
    anchor = row['anchor']
    srcs = Sources()
    lie = srcs.add('liebermann', 'Liebermann', LIEBERMANN_REF, 'edition', row['page'])

    # Manuscripts: those in column G (bold = Liebermann's choice), then any
    # other manuscript a text comes from.
    wits = []      # [id, siglum shown, selected, full name]
    def witness(sig, name=''):
        if not sig:
            return ''
        k = sig_key(sig)
        for w in wits:
            if w[1] == sig or same_sig(sig_key(w[1]), k):
                if name and not w[3]:
                    w[3] = name
                return w[0]
        wid = 'wit-' + ident(sig)
        while any(w[0] == wid for w in wits):
            wid += '-2'
        wits.append([wid, sig, False, name or MS_NAMES.get(sig) or MS_NAMES.get(k, '')])
        return wid
    for text, selected in row['witnesses']:
        wid = 'wit-' + ident(text)
        if any(w[0] == wid for w in wits):
            continue
        wits.append([wid, text, selected, MS_NAMES.get(text) or MS_NAMES.get(sig_key(text), '')])

    texts, translations = [], []      # (type, lang, source, xml, n, wit)
    shown = set()
    if row['kTextXml']:
        texts.append(('liebermannText', language(row['kText']), lie, row['kTextXml'], row['liebermannNumber'],
                      witness(row['kSig'], row['kName'])))
        shown.add(sig_key(row['kSig']))
    if row['nTextXml']:
        texts.append(('liebermannText', language(row['nText']), lie, row['nTextXml'], row['liebermannNumber'],
                      witness(row['nSig'], row['nName'])))
        shown.add(sig_key(row['nSig']))
    if row['afTextXml']:
        texts.append(('liebermannText', language(row['afText']), lie, row['afTextXml'], row['liebermannNumber'],
                      witness(row['afSig'], row['afName'])))
        shown.add(sig_key(row['afSig']))
    if row['latinXml']:
        texts.append(('liebermannText', 'la', lie, row['latinXml'], row['liebermannNumber'],
                      witness('Q', MS_NAMES['Q'])))

    editor = row['editor']
    t_wit = witness(row['tSig'], row['tName']) if row['tTextXml'] else ''
    ed_src = ''
    if editor:
        name, sid, ref = EDITOR_OVERRIDE.get(code, (editor, ident(editor), row['editionRefXml']))
        ed_src = srcs.add(sid, name, ref, 'edition', row['editorPage'])
        if row['tTextXml']:
            # Jurasinski and Oliver print MS B's rubric after MS E's in the same cell.
            e_text, b_text, e_trans, b_trans = rubrics.split(code, clause, row['tTextXml'], row['translationXml'])
            lang = 'ang' if code in rubrics.RUBRIC_CODES else language(row['tText'])
            texts.append(('editionText', lang, ed_src, e_text, row['editorNumber'], t_wit))
            if b_text:
                b_wit = witness('B', MS_NAMES['B'])
                texts.append(('editionText', 'ang', ed_src, b_text, '', b_wit))
                row['translationXml'] = e_trans
                row['bTranslationXml'] = b_trans
    elif row['tTextXml'] and sig_key(row['tSig']) not in shown:
        # No modern editor: column T is Liebermann's text of another manuscript.
        texts.append(('liebermannText', language(row['tText']), lie, row['tTextXml'], row['liebermannNumber'], t_wit))

    # Liebermann's texts (in the order of his columns: K, N, AF, O, T) before the modern edition.
    texts.sort(key=lambda t: t[0] == 'editionText')

    def translator(name, page=''):
        if name == 'Rabin':
            return srcs.add('rabin-doml', 'Rabin', RABIN_DOML, 'translation', page)
        if name == 'Whitelock':
            return srcs.add('whitelock', 'Whitelock', WHITELOCK_EHD, 'translation', page)
        if name == 'Whitelock C&S':
            return srcs.add('whitelock-cs', 'Whitelock', WHITELOCK_CS, 'translation')
        if name in refs:
            return srcs.add(ident(name), name, refs[name], 'translation')
        return srcs.add('unattributed', 'Translator not recorded',
                        'Translation from the original OE Laws Database spreadsheet; the translator is not recorded', 'translation')

    rabin_translation = None
    if row['rabinTextXml'] or row['rabinTranslationXml']:
        # Rabin, Old English Legal Writings: Wulfstan (columns AU-AZ)
        m = re.search(r'Base MS: (\S+) = (.*?)(?: \(|$)', row['rabinRef'])
        sig = RABIN_SIGLA.get((code, m.group(1)), m.group(1)) if m else ''
        r_wit = witness(sig, '' if sig != (m.group(1) if m else '') else (m.group(2) if m else '')) if sig else ''
        r_src = srcs.add('rabin-doml', 'Rabin', RABIN_DOML, 'edition', row['rabinPage'].split(' / ')[0])
        if row['rabinTextXml']:
            lang = 'la' if code == 'VII Atr' else 'ang'
            texts.append(('editionText', lang, r_src, row['rabinTextXml'], '', r_wit))
        if row['rabinTranslationXml']:
            rabin_translation = ('translation', 'en', r_src, row['rabinTranslationXml'], r_wit)
    u_by, aa_by = TRANSLATORS.get(code, (None, None))
    if u_by == 'Whitelock' and NOT_WHITELOCK in row['notes']:
        u_by = None
    if row['translationXml']:
        src = ed_src or translator(u_by, row['editorPage'] if u_by == 'Whitelock' else '')
        translations.append(('translation', 'en', src, row['translationXml'], t_wit))
        if row.get('bTranslationXml'):
            translations.append(('translation', 'en', src, row['bTranslationXml'], witness('B')))
    if row['secondTranslationXml']:
        second = abt.surname(row['secondRef'])
        if second == 'Rabin' and 'Wulfstan' in row['secondRef'] and '2020' in row['secondRef']:
            src = srcs.add('rabin-doml', 'Rabin', RABIN_DOML, 'translation', row['secondPage'])
        elif second:
            src = srcs.add(ident(second), second, row['secondRefXml'], 'translation', row['secondPage'])
        else:
            src = translator(None)
        translations.append(('translation', 'en', src, row['secondTranslationXml'], t_wit))
    if rabin_translation:
        translations.append(rabin_translation)       # after the editors' own translations
    if row['thirdTranslationXml']:
        # Whitelock's English Historical Documents (columns AP-AT)
        m = re.match(r'([A-Z][A-Za-z0-9]{0,3})\s+\(', row['thirdMS'])
        translations.append(('translation', 'en', translator('Whitelock', row['thirdPage']), row['thirdTranslationXml'],
                             witness(m.group(1), MS_NAMES.get(m.group(1), '')) if m else ''))
    if row['supplementaryTranslationXml']:
        translations.append(('translation', 'en', translator(aa_by), row['supplementaryTranslationXml'],
                             witness(row['kSig'], row['kName'])))
    if row['germanXml']:
        translations.append(('translation', 'de', lie, row['germanXml'], ''))
    if row['englishXml']:
        cl = srcs.add('claude', 'Claude', CLAUDE_REF, 'translation')
        translations.append(('translation', 'en', cl, row['englishXml'], ''))

    checks, notes = split_notes(row['notes'])

    L = []
    w = L.append
    w('<?xml version="1.0" encoding="UTF-8"?>')
    w('<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="%s">' % attr(row['id']))
    w('  <teiHeader>')
    w('    <fileDesc>')
    w('      <titleStmt>')
    w('        <title>%s</title>' % esc(citation))
    seen = set()
    for kind, _, sid, *_ in texts:
        if ('e', sid) not in seen:
            seen.add(('e', sid))
            w('        <respStmt><resp>Edition of the text</resp><name ref="#%s">%s</name></respStmt>' % (sid, esc(srcs.items[sid][0])))
    for kind, lang, sid, *_ in translations:
        if ('t', sid) not in seen:
            seen.add(('t', sid))
            w('        <respStmt><resp>Translation</resp><name ref="#%s">%s</name></respStmt>' % (sid, esc(srcs.items[sid][0])))
    w('      </titleStmt>')
    w('      <publicationStmt>')
    w('        <publisher>%s</publisher>' % esc(old.PUBLISHER))
    w('        <idno type="slug">%s</idno>' % esc(row['id']))
    w('        <idno type="citation">%s</idno>' % esc(citation))
    w('        <idno type="lawCode">%s</idno>' % esc(code))
    if anchor:
        w('        <idno type="lawCodeAnchor">%s</idno>' % esc(anchor))
    if clause:
        w('        <idno type="clause">%s</idno>' % esc(clause))
        for key in old.clause_keys(clause):
            w('        <idno type="citationKey">%s</idno>' % esc((anchor or code) + ' ' + key))
    w('      </publicationStmt>')
    w('      <sourceDesc>')
    w('        <bibl type="legalText"><title>%s</title>%s</bibl>' % (
        esc(row['codeName'] or code), (' <note type="reign">%s</note>' % esc(row['king'])) if row['king'] else ''))
    w('        <listBibl type="sources">')
    for sid, (name, xml, kind, page) in srcs.items.items():
        w('          <bibl xml:id="%s" type="%s">%s%s</bibl>' % (
            sid, kind, xml, (', p. <biblScope unit="page">%s</biblScope>' % esc(page)) if page else ''))
    w('        </listBibl>')
    if wits:
        w('        <listWit>')
        for wid, sig, selected, name in wits:
            w('          <witness xml:id="%s"%s><abbr>%s</abbr>%s</witness>' % (
                wid, ' rend="bold"' if selected else '', esc(sig),
                (' <note type="manuscript">%s</note>' % esc(name)) if name else ''))
        w('        </listWit>')
    w('      </sourceDesc>')
    w('    </fileDesc>')
    w('    <encodingDesc>')
    w(old.PREFIX_DEFS)
    w('    </encodingDesc>')
    kws = [('offence-legal-event', row['offence']), ('people', row['people']), ('locations', row['locations'])]
    w('    <profileDesc>')
    if row['promulgation']:
        w('      <creation><note type="promulgation">%s</note></creation>' % esc(row['promulgation']))
    if any(t for _, t in kws):
        w('      <textClass>')
        for name, terms in kws:
            if terms:
                w('        <keywords n="%s">%s</keywords>' % (name, ''.join('<term>%s</term>' % esc(t) for t in keywords(terms))))
        w('      </textClass>')
    w('    </profileDesc>')
    w('    <revisionDesc>')
    w('      <change when="%s">Generated from row %d of %s.</change>' % (today, row['sheetRow'], esc(source_name)))
    done = set()
    for who, verb, page in checks:
        if (who, verb, page) in done:
            continue
        done.add((who, verb, page))
        if who == 'liebermann':
            what = {'checked against': 'checked against', 'corrected against': 'checked and corrected against',
                    'added from': 'added from'}[verb]
            w('      <change when="2026-10" type="checked">Liebermann’s text %s <title>Die Gesetze der Angelsachsen</title> I, p. %s.</change>' % (what, esc(page)))
        else:
            part = 'text' if who.endswith('T') else 'translation'
            w('      <change when="2026-10" type="checked">Robertson’s %s checked and corrected against her edition, p. %s.</change>' % (part, esc(page)))
    w('    </revisionDesc>')
    w('  </teiHeader>')
    w('  <text>')
    w('    <body>')
    w('      <div type="clause"%s>' % ((' n="%s"' % attr(clause)) if clause else ''))
    head_code = '<ref type="lawCode" target="law:%s">%s</ref>' % (attr(anchor), esc(code)) if anchor else esc(code)
    w('        <head>%s%s</head>' % (head_code, (' ' + esc(clause)) if clause else ''))
    for kind, lang, sid, xml, n, wid in texts:
        at = ' type="%s" xml:lang="%s" source="#%s"' % (kind, lang, sid)
        if n:
            at += ' n="%s"' % attr(n)
        if wid:
            at += ' corresp="#%s"' % wid
        w('        <ab%s>%s</ab>' % (at, xml))
    for kind, lang, sid, xml, wid in translations:
        at = ' type="%s" xml:lang="%s" source="#%s"' % (kind, lang, sid)
        if sid == 'claude':
            at += ' ana="#fromGerman"'
        if wid:
            at += ' corresp="#%s"' % wid
        w('        <ab%s>%s</ab>' % (at, xml))
    if row['passageSourceXml']:
        w('        <note type="passageSource">%s</note>' % row['passageSourceXml'])
    if notes:
        w('        <note type="editorial">%s</note>' % esc(notes))
    if row['translatorNotes'] and 'whitelock' in srcs.items:
        for n in row['translatorNotes'].split(' | '):
            w('        <note type="translator" source="#whitelock">%s</note>' % esc(n))
    if 'rabin-doml' in srcs.items:
        for n in [x for x in row['rabinTextNotes'].split(' | ') if x.strip()]:
            w('        <note type="textual" source="#rabin-doml">%s</note>' % esc(n))
        for n in [x for x in row['rabinNotes'].split(' | ') if x.strip()]:
            w('        <note type="translator" source="#rabin-doml">%s</note>' % esc(n))
    w('      </div>')
    w('    </body>')
    w('  </text>')
    w('</TEI>')
    return '\n'.join(L) + '\n'


# ---------------------------------------------------------------- file names
def assign_ids(rows, catalogue):
    """Give each row the file name its clause had before; new names only for new clauses."""
    by_code = defaultdict(list)
    for c in catalogue:
        by_code[OLD_CODES.get(c['code'].strip(), c['code'].strip())].append(c)
    used, report = set(), []
    for code in dict.fromkeys(r['code'] for r in rows):
        mine = [r for r in rows if r['code'] == code]
        olds = [c for c in by_code.get(code, []) if c['id'] not in used]
        # 1. same clause number, in order
        for r in mine:
            key = old.clause_key(r['clause'])
            for c in olds:
                if c['id'] not in used and old.clause_key(c['clause'] or '') == key:
                    r['id'] = c['id']
                    used.add(c['id'])
                    break
        # 2. what is left: the old clause that came next after the previous
        #    row's old clause, or else the first old clause left
        order = [c['id'] for c in olds]
        for i, r in enumerate(mine):
            if 'id' in r:
                continue
            c = None
            prev = next((p['id'] for p in reversed(mine[:i]) if p.get('id') in order), None)
            if prev is not None:
                j = order.index(prev) + 1
                if j < len(olds) and olds[j]['id'] not in used:
                    c = olds[j]
            if c is None:
                c = next((o for o in olds if o['id'] not in used), None)
            if c is None:
                continue
            r['id'] = c['id']
            used.add(c['id'])
            report.append('  matched by position: %s %s -> %s (was %s %s)' % (code, r['clause'], c['id'], c['code'], c['clause']))
        for r in mine:
            if 'id' not in r:
                base = r['anchor'] or old.slugify(code) or 'code'
                parts = old.clause_parts(r['clause'])
                part = old.slugify(parts[0] if len(parts) == 1 else parts[0] + ' to ' + parts[-1])[:old.MAX_SLUG].strip('-') or 'x'
                rid, n = '%s_%s' % (base, part), 2
                while rid in used or any(c['id'] == rid for c in catalogue):
                    rid, n = '%s_%s_dup%d' % (base, part, n), n + 1
                r['id'] = rid
                used.add(rid)
                report.append('  new file: %s (%s %s)' % (rid, code, r['clause']))
    return used, report


# The Laws page lists the law codes under the king who issued them (column
# E). The key is the first name in E; codes with no king go under OTHER.
GROUPS = {
    'Æthelberht': 'Æthelberht of Kent', 'Hlothhere': 'Hlothhere and Eadric of Kent', 'Wihtred': 'Wihtred of Kent',
    'Alfred': 'Alfred the Great', 'Ine': 'Ine of Wessex', 'Edward': 'Edward the Elder', 'Æthelstan': 'Æthelstan',
    'Edmund': 'Edmund I', 'Edgar': 'Edgar', 'Æthelred': 'Æthelred II', 'Cnut': 'Cnut',
}
OTHER = 'Other laws and legal texts'
# Codes listed under another king than the one who issued them: the rubrics
# to Ine's laws were written for Alfred's Domboc but belong with Ine's laws.
GROUP_OVERRIDE = {'Ine Rb': 'Ine of Wessex'}


def king_parts(king):
    """'Hlothhere, r. 673–685; Eadric, r. 685–686' -> [('Hlothhere', 'r. 673–685'), ('Eadric', 'r. 685–686')]."""
    out = []
    king = re.sub(r'^Attributed to ', '', king.strip('[] '))
    for part in re.split(r';|, and ', king):
        part = part.strip(' []')
        m = re.match(r'(.*?),\s*((?:r\.|d\.).*)$', part)
        out.append((m.group(1).strip(), m.group(2).strip()) if m else (part, ''))
    return [p for p in out if p[0]]


def write_codes(rows, catalogue, find_anchor, path):
    """oe-laws/codes.json: one line per law code, in the spreadsheet's order, for the Laws page."""
    first_ids = {}
    counts = Counter()
    for c in catalogue:
        code = OLD_CODES.get(c['code'].strip(), c['code'].strip())
        first_ids.setdefault(code, c['id'])
        counts[code] += 1
    codes = {}
    for r in rows:
        c = codes.get(r['code'])
        if c is None:
            parts = king_parts(r['king']) if r['king'] else []
            key = parts[0][0].split()[0] if parts else ''
            c = codes[r['code']] = {
                'code': r['code'], 'anchor': find_anchor(r['code'])[0], 'name': r['codeName'] or r['code'],
                'king': ' and '.join(p[0] for p in parts), 'reign': r['king'],
                'group': GROUP_OVERRIDE.get(r['code']) or (GROUPS.get(key, key) if key else OTHER),
                'date': r['promulgation'], 'clauses': counts[r['code']], 'first': first_ids.get(r['code'], ''),
                'editors': [], 'manuscripts': [],
            }
        u_by, aa_by = TRANSLATORS.get(r['code'], (None, None))
        names = [EDITOR_OVERRIDE.get(r['code'], (r['editor'],))[0] if r['editor'] else '',
                 abt.surname(r['secondRef']) if r['secondTranslation'] else '',
                 u_by if r['translation'] and not r['editor'] else '', aa_by if r['supplementaryTranslation'] else '',
                 'Whitelock' if r['thirdTranslation'] else '', 'Rabin' if r['rabinText'] or r['rabinTranslation'] else '']
        for name in names:
            name = (name or '').replace(' C&S', '')
            if name and name not in c['editors']:
                c['editors'].append(name)
        for sig in (r['kSig'], r['nSig'], r['afSig'], r['tSig']):
            for k in ([sig] if sig in MS_NAMES else [sig_key(x) for x in re.split(r'[;,]\s*', sig or '')]):
                k = k.strip()
                if k and (k in MS_NAMES or re.fullmatch(r'[A-Z][a-z]?\d?', k)) and k not in c['manuscripts']:
                    c['manuscripts'].append(k)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('[\n' + ',\n'.join(json.dumps(c, ensure_ascii=False, separators=(',', ':')) for c in codes.values()) + '\n]\n')
    print('written: %s (%d law codes)' % (path, len(codes)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('xlsx')
    ap.add_argument('--out', default='oe-laws')
    ap.add_argument('--mark-law', default='data/markLaw.json')
    ap.add_argument('--code', action='append', help='only this law code (may be given more than once)')
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--dry-run', action='store_true', help='report only; write nothing')
    args = ap.parse_args()

    only = set(args.code) if args.code else None
    all_rows = read_rows(args.xlsx, only)
    rows = [r for r in all_rows if r['code'] not in SKIP]
    find_anchor = old.anchor_finder(args.mark_law)
    for r in rows:
        r['anchor'] = find_anchor(r['code'])[0]
    index_path = os.path.join(args.out, 'index.json')
    catalogue = json.load(open(index_path, encoding='utf-8'))
    codes = {r['code'] for r in rows}
    mine = [c for c in catalogue if OLD_CODES.get(c['code'].strip(), c['code'].strip()) in codes]
    used, report = assign_ids(rows, mine)
    gone = [c for c in mine if c['id'] not in used]
    print('law codes: %d; clause rows: %d; files kept under their old names: %d; new: %d; old files with no row now: %d' % (
        len(codes), len(rows), sum(1 for r in rows if r['id'] in {c['id'] for c in mine}),
        sum(1 for r in rows if r['id'] not in {c['id'] for c in mine}), len(gone)))
    print('\n'.join(report))
    for c in gone:
        print('  no row now (file removed): %s (%s %s)' % (c['id'], c['code'], c['clause']))
    # (references from the dictionary to removed files are checked in docs, see OE-LAWS.md)

    refs = {}
    for r in rows:
        if r['secondRef']:
            refs.setdefault(abt.surname(r['secondRef']), r['secondRefXml'])
        if r['editor']:
            refs.setdefault(r['editor'], r['editionRefXml'])
    langs = Counter()
    source_name = 'the spreadsheet ' + os.path.basename(args.xlsx)
    outputs = {r['id']: build(r, args.date, source_name, refs) for r in rows}
    for x in outputs.values():
        langs.update(re.findall(r'<ab type="(\w+)" xml:lang="(\w+)"', x))
    print('texts written:', ', '.join('%s %s: %d' % (k[0], k[1], n) for k, n in sorted(langs.items())))
    if args.dry_run:
        return

    for c in gone:
        p = os.path.join(args.out, c['file'])
        if os.path.exists(p):
            os.remove(p)
    for rid, x in outputs.items():
        with open(os.path.join(args.out, rid + '.xml'), 'w', encoding='utf-8', newline='\n') as f:
            f.write(x)

    def entry(r):
        return {
            'id': r['id'], 'file': r['id'] + '.xml', 'citation': ('%s %s' % (r['code'], r['clause'])).strip(),
            'code': r['code'], 'anchor': r['anchor'], 'clause': r['clause'],
            'citationKeys': [(r['anchor'] or r['code']) + ' ' + k for k in old.clause_keys(r['clause'])],
            'legalText': r['king'].split(',')[0].strip() or r['codeName'], 'page': r['page'],
            'sheetRow': r['sheetRow'], 'source': os.path.basename(args.xlsx),
        }
    # Keep the catalogue in the spreadsheet's order: each code's clauses go
    # where that code's first clause was; codes not rebuilt stay as they are.
    by_code = defaultdict(list)
    for r in rows:
        by_code[r['code']].append(r)
    out, placed = [], set()
    for c in catalogue:
        code = OLD_CODES.get(c['code'].strip(), c['code'].strip())
        if code in codes:
            if code not in placed:
                out.extend(entry(r) for r in by_code[code])
                placed.add(code)
            continue
        out.append(c)
    for code in by_code:
        if code not in placed:
            out.extend(entry(r) for r in by_code[code])
    with open(index_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('[\n' + ',\n'.join(json.dumps(c, ensure_ascii=False, separators=(',', ':')) for c in out) + '\n]\n')
    print('written: %d files and %s (%d clauses in all)' % (len(outputs), index_path, len(out)))
    if not only:
        write_codes(all_rows, out, find_anchor, os.path.join(args.out, 'codes.json'))


if __name__ == '__main__':
    sys.exit(main())
