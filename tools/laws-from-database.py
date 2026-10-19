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
promulgation = _load('promulgation', 'promulgation.py')  # date and place, with their scholars

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
    ("liebermann's fourth ms", 'bfText'),
    ("siglum of liebermann's fourth ms", 'bfSig'),
    ("manuscript of liebermann's fourth ms", 'bfName'),
    ("liebermann's fifth ms", 'biText'),
    ("siglum of liebermann's fifth ms", 'biSig'),
    ("liebermann's sixth ms", 'brText'),
    ("siglum of liebermann's sixth ms", 'brSig'),
    ("manuscript of liebermann's sixth ms", 'brName'),
    ("manuscript of liebermann's fifth ms", 'biName'),
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
    ('liebermann’s marginal cross-references', 'vglPrinted'),
    ('liebermann’s cross-references written out', 'vglRefs'),
    ('cross-references: page in gesetze', 'vglRemark'),
    ('edition 3 (attenborough)', 'attText'),
    ('page number of attenborough', 'attPage'),
    ('siglum of the manuscript attenborough prints', 'attSig'),
    ('manuscript attenborough prints', 'attName'),
    ('order of liebermann’s texts', 'liebOrder'),
    ('pages of liebermann’s texts', 'liebPages'),
]
NEEDED = ['code', 'clause', 'kText', 'german', 'english', 'nText', 'kSig', 'tSig', 'notes']

LIEBERMANN_REF = ('<author>Felix Liebermann</author>, <title>Die Gesetze der Angelsachsen</title>, '
                  'vol. <biblScope unit="volume">1</biblScope> (Halle: Niemeyer, 1903)')
CLAUDE_REF = ('A semi-literal English rendering of Liebermann’s German, made for this database in 2026 with Claude, a large language model (LLM) made by Anthropic. It is a crib to help the reader with Liebermann’s German, not a separate translation')

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
# Other scholars' clause-to-clause cross-references: the 'Cross-references' sheet of the spreadsheet.
WORMALD_MEL = ('Patrick Wormald, <title>The Making of English Law: King Alfred to the Twelfth Century, I: Legislation '
               'and its Limits</title> (Oxford: Blackwell, 1999)')
WORMALD_PPMEL = ('Patrick Wormald, <title>Papers Preparatory to The Making of English Law: King Alfred to the Twelfth '
                 'Century, II: From God’s Law to Common Law</title>, ed. Stephen Baxter and John Hudson (London: University '
                 'of London, 2014)')
JO_REF = ('Stefan Jurasinski and Lisi Oliver, <title>The Laws of Alfred: The Domboc and the Making of Anglo-Saxon Law</title> '
          '(Cambridge: Cambridge University Press, 2021)')
KENNEDY_REF = 'A. G. Kennedy, ‘Cnut’s Law Code of 1018’, <title>Anglo-Saxon England</title> 11 (1983), 57–81'
XR_WORKS = {   # 'Work' on the Cross-references sheet (start of it) -> (source id, name, reference)
    'Whitelock': ('whitelock', 'Whitelock', WHITELOCK_EHD),
    'Rabin': ('rabin-doml', 'Rabin', RABIN_DOML),
    'Wormald, The Making': ('wormald-mel', 'Wormald, MEL', WORMALD_MEL),
    'Wormald, Papers': ('wormald-ppmel', 'Wormald, Papers Preparatory', WORMALD_PPMEL),
    'Jurasinski and Oliver': ('jurasinski-and-oliver', 'Jurasinski and Oliver', JO_REF),
    'Kennedy': ('kennedy', 'Kennedy', KENNEDY_REF),
}
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
    'Otho A.x': 'London, British Library, Cotton Otho A.x (burnt 1731), known only from Wanley’s extract in Hickes, Thesaurus (1705)',
    'Vr': 'Vatican, Biblioteca Apostolica, Reg. lat. 946',
    'York Gospels': 'York, Minster Library, Add. 1 (York Gospels)',
}
# codes whose column O holds a Latin text other than Quadripartitus
LATIN_OVERRIDE = {
    'Prom. Reg.': ('Lat', 'Latin form of the coronation oath (the liturgical ordo), as printed by Liebermann'),
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
    """'Cons.Cn.' and 'Cons. Cn.' are the same siglum; so are 'Cons' and 'Cons. Cn.', 'In' and 'Inst. Cn.' (Liebermann's sigla for the
    Consiliatio and Instituta Cnuti, and the forms the spreadsheet's list of manuscripts uses)."""
    k = lambda s: {'conscn': 'cons', 'instcn': 'in'}.get(re.sub(r'[\s.]', '', s).lower(), re.sub(r'[\s.]', '', s).lower())
    return k(a) == k(b)


def pages(cell):
    """'4 / 5' -> ('4', '5'); '4' -> ('4', '4'): the page of a text and of its translation on the facing page."""
    parts = [x.strip() for x in str(cell or '').split('/')]
    return (parts[0], parts[-1]) if parts[0] else ('', '')


def lieb_pages(cell):
    """'E 16; G 16; H 17; Q 17; German 17' -> {'E': '16', …}: the page of each of Liebermann's texts and of his German."""
    out = {}
    for part in str(cell or '').split(';'):
        m = re.match(r'\s*(.+?)\s+(\d+)\s*$', part)
        if m:
            out[re.sub(r'[\s.]', '', m.group(1)).lower()] = m.group(2)
    return out


def pb(page, sid):
    """The page on which a text or translation begins, as <pb> at its start (the clause page shows it)."""
    return '<pb n="%s" ed="#%s"/>' % (attr(page), sid) if page else ''


def ident(text):
    return old.slugify(text).lower() or 'x'


LATIN = set('et est in de ut non uel vel quod cum si qui quae quo ad per sed enim autem eius sit ab ex nec aut atque '
            'uero vero item hoc hec quodsi similiter debet omni omnis omnes deo dei regis rex'.split())
OE = set('and þæt ðæt se he man ne gif gyf ðe þe beo sy to his hit mid swa ofer þonne ðonne bete gebete '
         'scillinga is wið þam ðam'.split())


FRENCH_CODES = {'Leis Wl'}


def language(text, code=''):
    if code in PHASE2B:      # Latin with Old English terms (ƿere, þegen): always Latin
        return 'la'
    # the Latin ordeal and excommunication texts (October 2026) write 'æ' (aquæ, Ysaiæ): go by the words there
    if re.search('[⁊þðÞÐƿ]' if code in OWN_MS_NAMES else '[⁊þðæÞÐÆƿ]', text):
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
# The check of October 2026 against the printed editions (spreadsheet stage lcheck_stage.py):
# 'K: corrected against Gesetze I p. 10, October 2026 (was “tithte”, now “tihte”)'
OCT = re.compile(r'^(K|L|M|N|AF|BF|BI|O|T|U|W): corrected against (Gesetze I+|Attenborough|Robertson|Oliver|Jurasinski and Oliver|Whitelock) p\. ?([^\s,;]+), October 2026 \(was “(.*?)”, now “(.*?)”\)(?=;|$)')
ADDED = re.compile(r'^(K|L|N|AF|BF|BI|O): added from (Gesetze I+) p\. ?([^\s,;]+), October 2026 \(MS ([^)]*)\)(?=;|$)')
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
            m = ADDED.match(p)
            if m:
                checks.append(('oct2026-added', m.group(1), m.groups()[1:]))
                p = p[m.end():].lstrip('; ').strip()
                continue
            m = OCT.match(p)
            if m:
                checks.append(('oct2026', m.group(1), m.groups()[1:]))
                p = p[m.end():].lstrip('; ').strip()
                continue
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
YEARS = {'attenborough': 1922, 'robertson': 1925, 'whitelock': 1955, 'whitelock-cs': 1981, 'kennedy': 1983,
         'wormald': 1999, 'oliver': 2002, 'gobbitt': 2012, 'rabin': 2015, 'rabin-doml': 2020,
         'jurasinski-and-oliver': 2021}     # first published; the sheet 'Editions and translations' overrides


def read_rows(path, only=None):
    wb = openpyxl.load_workbook(path, rich_text=True)
    if 'Editions and translations' in wb.sheetnames:
        for r_ in wb['Editions and translations'].iter_rows(min_row=2, values_only=True):
            if r_ and r_[0] and isinstance(r_[3], int):
                YEARS[r_[0]] = r_[3]
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
                     'bfSig', 'bfName', 'biSig', 'biName', 'brSig', 'brName',
                     'thirdRef', 'thirdMS', 'thirdPage', 'translatorNotes', 'rabinRef', 'rabinPage', 'rabinTextNotes', 'rabinNotes',
                     'vglPrinted', 'vglRefs', 'vglRemark', 'attPage', 'attSig', 'attName', 'liebOrder', 'liebPages'):
            row[name] = get(name)
        for name in ('kText', 'german', 'english', 'nText', 'latin', 'tText', 'translation',
                     'secondTranslation', 'supplementaryTranslation', 'afText', 'bfText', 'biText', 'brText', 'thirdTranslation', 'rabinText', 'rabinTranslation', 'attText'):
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
    return in_clause_order(rows)


def clause_order_key(clause):
    """'Inscr.' < 'Prol.' < 1 < 1.1 < 2 < 2a < 2.1 < … < 'Epil.' < 'Test.' < 'Dat.' (Liebermann's numbering)"""
    c = (clause or '').strip().rstrip('.').lower()
    head = {'inscr': -3, 'rubr': -3, 'prol': -2, 'prot': -2}
    tail = {'epil': 1e6, 'test': 1e6 + 1, 'dat': 1e6 + 2, 'add': 1e6 + 3}
    if c in head: return (head[c],)
    if c in tail: return (tail[c],)
    key = []          # 2 < 2a < 2.1 < 2.2 < 2.2a < 2.3: a letter is a step between the number and its first sub-clause
    for part in re.split(r'[.,]\s*', c.split(' ')[0]):
        m = re.match(r'(\d+)([a-z]?)', part)
        if m:
            key.append(int(m.group(1)))
            if m.group(2): key.append((ord(m.group(2)) - 96) / 100)
    return (0, key)


def in_clause_order(rows):
    """Rows added at the end of Sheet1 for a code that is already higher up (October 2026: clauses Liebermann prints
    that the edition the rows were made from leaves out) are put among that code's rows, in clause order."""
    first, by_code, seen_end = {}, {}, {}
    for i, r in enumerate(rows):
        first.setdefault(r['code'], i); by_code.setdefault(r['code'], []).append(r)
    split = {c for c, rs in by_code.items() if rows.index(rs[-1]) - first[c] + 1 != len(rs)}
    if not split: return rows
    out = []
    for r in rows:
        if r['code'] in split:
            if r['code'] in seen_end: continue
            seen_end[r['code']] = True
            out.extend(sorted(by_code[r['code']], key=lambda x: clause_order_key(x['clause'])))
        else:
            out.append(r)
    return out


ROBERTSON_REF = ('A. J. Robertson, <title>The Laws of the Kings of England from Edmund to Henry I</title> '
                 '(Cambridge: Cambridge University Press, 1925)')
ATTENBOROUGH_REF = ('F. L. Attenborough, <title>The Laws of the Earliest English Kings</title> '
                    '(Cambridge: Cambridge University Press, 1922)')
KENNEDY_REF = 'A. G. Kennedy, ‘Cnut’s Law Code of 1018’, <title>Anglo-Saxon England</title> 11 (1983), 57–81'
# A scholar named for a date or place -> (source id, name, reference). A work not
# already on the clause page as an edition or translation is listed under Studies.
DATE_SCHOLARS = {
    'Whitelock': ('whitelock', 'Whitelock', WHITELOCK_EHD),
    'Wormald': ('wormald-mel', 'Wormald, MEL', WORMALD_MEL),
    'Rabin': ('rabin-doml', 'Rabin', RABIN_DOML),
    'Robertson': ('robertson', 'Robertson', ROBERTSON_REF),
    'Attenborough': ('attenborough', 'Attenborough', ATTENBOROUGH_REF),
    'Kennedy': ('kennedy', 'Kennedy', KENNEDY_REF),
    'Liebermann': ('liebermann', 'Liebermann', LIEBERMANN_REF),
}


def date_place(text, srcs):
    """The code's dates and places as [(kind, text, [source ids])], adding the scholars' works to srcs."""
    dates, places = promulgation.parse(text)
    out = []
    for kind, items in (('date', dates), ('placeName', places)):
        for what, who in items:
            ids, pages = [], []
            for entry in who:
                name, page = promulgation.split_who(entry)
                sid, short, ref = DATE_SCHOLARS[name]
                srcs.add(sid, short, ref, 'study')
                ids.append(sid)
                pages.append(page)
            out.append((kind, what, ids, pages))
    return out


def creation_xml(dated):
    """<date> and <placeName> elements, each pointing to the works that propose it."""
    # n: the page where each of those scholars gives it, in the same order, separated by "|" (blank if none)
    return ''.join('<%s%s%s>%s</%s>' % (kind, (' source="%s"' % ' '.join('#' + i for i in ids)) if ids else '',
                                         (' n="%s"' % esc('|'.join(pages))) if any(pages) else '', esc(what), kind)
                   for kind, what, ids, pages in dated)


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


# ---------------------------------------------------------------- Liebermann's cross-references
def vgl_key(clause):
    """A clause number compared loosely: commas as full stops, no spaces, 'Prol.'/'Pr.' alike."""
    c = str(clause).replace(',', '.').replace(' ', '').lower().rstrip('.')
    c = re.sub(r'^(prolog|prol|pr)\.?', 'prol', c)
    c = re.sub(r'^(inscr|insc)\.?', 'inscr', c)
    return re.sub(r'^([a-z]+)\.', r'\1', c)


def clause_finder(rows):
    """A function that turns a written-out reference ("I Em 3", "Af El 49.3", "II Cn 30–31") into the id
    of the clause it names (the first clause of a run), or '' if it names none in the database."""
    where, order, first = {}, defaultdict(list), {}
    for r in rows:
        first.setdefault(r['code'], r.get('id', r['sheetRow']))
        clause = re.sub(r'^%s\.?\s+' % re.escape(r['code']), '', r['clause'])     # "Ine Prol.", "II Ew. 1"
        m = re.match(r'^(Prol|Inscr|El|Pr)\.?,?\s*(\d.*)$', clause)
        keys = [m.group(1) + m.group(2)] if m else ([clause] if re.match(r'^[A-Za-z]', clause) else re.split(r',\s*', clause))
        for k in keys:
            k = vgl_key(k)
            if k and (r['code'], k) not in where:
                where[(r['code'], k)] = r.get('id', r['sheetRow'])
                order[r['code']].append(k)
    codes = sorted({r['code'] for r in rows} | {'Af El'}, key=len, reverse=True)

    def find(ref, whole_code=False):
        """whole_code: a reference to a whole text ("Blas") finds its first clause."""
        for code in codes:
            if ref == code or ref.startswith(code + ' '):
                break
        else:
            return ''
        clause = ref[len(code):].strip()
        if not clause and whole_code:
            return first.get(code, '')
        if code == 'Af El':
            code, clause = 'Af', 'El ' + clause
        if code == 'Að' and vgl_key(clause) == '2':     # Liebermann's Að 2 is the sheet's "Had 2[as Að]"
            code, clause = 'Had', '2[as Að]'
        k = vgl_key(clause)
        k = re.split(r'[–—-]', re.sub(r'f+\.?$', '', k))[0]
        if not k or '[?]' in k:
            return ''
        if (code, k) in where:
            return where[(code, k)]
        for kk in order[code]:
            if kk.startswith(k) and len(kk) > len(k) and not kk[len(k)].isdigit():
                return where[(code, kk)]
        m = re.match(r'^(.+)\.\d+[a-z]?$', k) or re.match(r'^(.*\d)[a-z]$', k)
        return where.get((code, m.group(1)), '') if m else ''
    return find


def vgl_links(rows):
    """Resolve each row's written-out cross-references (column BB) to clause files, and collect the
    reverse links. Sets row['vglLinks'] = [(text, id or '')] and row['vglBack'] = [(citation, id)]."""
    find = clause_finder(rows)

    back = defaultdict(list)
    for r in rows:
        r['vglLinks'] = []
        for ref in [x.strip() for x in r.get('vglRefs', '').split(';') if x.strip()]:
            rid = find(ref)
            if rid == r['id']:
                rid = ''
            r['vglLinks'].append((ref, rid))
            if rid and r['id'] not in [b[1] for b in back[rid]]:
                back[rid].append((('%s %s' % (r['code'], r['clause'])).strip(), r['id']))
    for r in rows:
        r['vglBack'] = back.get(r['id'], [])
    return sum(1 for r in rows for _, i in r['vglLinks'] if i), sum(len(r['vglLinks']) for r in rows)


def read_cross_references(path):
    """The 'Cross-references' sheet: [{work, page, from, to, relation, said}] (empty if there is none)."""
    wb = openpyxl.load_workbook(path, read_only=True)
    if 'Cross-references' not in wb.sheetnames:
        return []
    out = []
    for v in list(wb['Cross-references'].iter_rows(min_row=2, values_only=True)):
        if not v or not v[3]:
            continue
        work = next((k for k in XR_WORKS if str(v[1] or '').startswith(k)), None)
        if work:
            out.append({'work': work, 'page': '' if v[2] is None else str(v[2]), 'from': str(v[3]).strip(),
                        'to': str(v[4] or '').strip(), 'relation': str(v[5] or '').strip(), 'said': str(v[6] or '').strip()})
    return out


def xr_links(rows, links):
    """Attach other scholars' cross-references to the clauses: row['xr'] = [(work, page, relation, text, id, said)],
    row['xrBack'] = [(work, page, relation, citation, id)]."""
    find = clause_finder(rows)
    by_id = {r['id']: r for r in rows}
    for r in rows:
        r['xr'], r['xrBack'] = [], []
    n = 0
    for l in links:
        fid = find(l['from'], True)
        if not fid:
            continue
        tid = find(l['to'], True)
        if tid == fid:
            tid = ''
        by_id[fid]['xr'].append((l['work'], l['page'], l['relation'], l['to'], tid, l['said']))
        n += 1
        if tid:
            back = by_id[tid]['xrBack']
            item = (l['work'], l['page'], l['relation'], l['from'], fid)
            if not any(b[0] == item[0] and b[4] == fid for b in back):
                back.append(item)
    return n


def build(row, today, source_name, refs):
    code, clause = row['code'], row['clause']
    citation = ('%s %s' % (code, clause)).strip()
    anchor = row['anchor']
    srcs = Sources()
    lie = srcs.add('liebermann', 'Liebermann', LIEBERMANN_REF, 'edition', row['page'])
    lp = lieb_pages(row['liebPages'])
    lpage = lambda sig: lp.get(re.sub(r'[\s.]', '', sig_key(sig or '')).lower(), '') or row['page']

    # Manuscripts: those in column G (bold = Liebermann's choice), then any
    # other manuscript a text comes from.
    wits = []      # [id, siglum shown, selected, full name]
    def witness(sig, name=''):
        if not sig:
            return ''
        k = sig_key(sig)
        exact = [w for w in wits if w[1] == sig] if '(Latin)' in sig else []   # 'C (Latin)' is its own witness, not C
        for w in exact or wits:
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
        # the full name in column AK (AL, AM …) for this row's own text comes first: a siglum can mean
        # different manuscripts in different texts (Q is the Quadripartitus, but in Excom XII a Cotton MS)
        own = next((row[t + 'Name'] for t in ('k', 'n', 'af', 'bf', 'bi', 'br') if row[t + 'Sig'] == text and row[t + 'Name']), '') if code in OWN_MS_NAMES else ''
        wits.append([wid, text, selected, own or MS_NAMES.get(text) or MS_NAMES.get(sig_key(text), '')])

    texts, translations = [], []      # (type, lang, source, xml, n, wit)
    shown = set()
    if row['kTextXml']:
        texts.append(('liebermannText', language(row['kText'], code), lie, pb(lpage(row['kSig']), lie) + row['kTextXml'], row['liebermannNumber'],
                      witness(row['kSig'], row['kName'])))
        shown.add(sig_key(row['kSig']))
    if row['nTextXml']:
        texts.append(('liebermannText', language(row['nText'], code), lie, pb(lpage(row['nSig']), lie) + row['nTextXml'], row['liebermannNumber'],
                      witness(row['nSig'], row['nName'])))
        shown.add(sig_key(row['nSig']))
    if row['afTextXml']:
        texts.append(('liebermannText', language(row['afText'], code), lie, pb(lpage(row['afSig']), lie) + row['afTextXml'], row['liebermannNumber'],
                      witness(row['afSig'], row['afName'])))
        shown.add(sig_key(row['afSig']))
    for t in ('bf', 'bi', 'br'):      # Liebermann's fourth, fifth and sixth texts (columns BF-BH, BI-BK, BR-BT; October 2026)
        if row[t + 'TextXml']:
            texts.append(('liebermannText', language(row[t + 'Text'], code), lie, pb(lpage(row[t + 'Sig']), lie) + row[t + 'TextXml'], row['liebermannNumber'],
                          witness(row[t + 'Sig'], row[t + 'Name'])))
            shown.add(sig_key(row[t + 'Sig']))
    if row['latinXml']:
        lsig, lname = LATIN_OVERRIDE.get(code, ('Q', MS_NAMES['Q']))
        texts.append(('liebermannText', 'la', lie, pb(lpage('Q'), lie) + row['latinXml'], row['liebermannNumber'],
                      witness(lsig, lname)))

    editor = row['editor']
    if editor == 'Liebermann':
        # Column T reproduces Liebermann's own text (shown already as his text), and U's translator is not recorded
        editor = ''
    t_wit = witness(row['tSig'], row['tName']) if row['tTextXml'] else ''
    ed_src = ''
    if editor:
        name, sid, ref = EDITOR_OVERRIDE.get(code, (editor, ident(editor), row['editionRefXml']))
        ed_src = srcs.add(sid, name, ref, 'edition', pages(row['editorPage'])[0])
        if row['tTextXml']:
            # Jurasinski and Oliver print MS B's rubric after MS E's in the same cell.
            e_text, b_text, e_trans, b_trans = rubrics.split(code, clause, row['tTextXml'], row['translationXml'])
            lang = 'ang' if code in rubrics.RUBRIC_CODES else language(row['tText'])
            if code in FRENCH_CODES:
                # Anglo-Norman French, except the clauses Robertson supplies from the Latin version (MS L)
                lang = 'la' if sig_key(row['tSig']) == 'L' else 'xno'
            texts.append(('editionText', lang, ed_src, pb(pages(row['editorPage'])[0], ed_src) + e_text, row['editorNumber'], t_wit))
            if b_text:
                b_wit = witness('B', MS_NAMES['B'])
                texts.append(('editionText', 'ang', ed_src, pb(pages(row['editorPage'])[0], ed_src) + b_text, '', b_wit))
                row['translationXml'] = e_trans
                row['bTranslationXml'] = b_trans
            if b_text:
                row['bTranslationXml'] = pb(pages(row['editorPage'])[1], ed_src) + row['bTranslationXml']
    elif row['tTextXml'] and sig_key(row['tSig']) not in shown:
        # No modern editor: column T is Liebermann's text of another manuscript.
        texts.append(('liebermannText', language(row['tText']), lie, pb(lpage(row['tSig']), lie) + row['tTextXml'], row['liebermannNumber'], t_wit))

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

    if row['attTextXml']:
        # Attenborough's own Old English text (columns BL-BO), where column T is another editor's
        a_src = srcs.add('attenborough', 'Attenborough', ATTENBOROUGH_REF, 'edition', pages(row['attPage'])[0])
        texts.append(('editionText', 'ang', a_src, pb(pages(row['attPage'])[0], a_src) + row['attTextXml'], '', witness(row['attSig'], row['attName'])))

    rabin_translation = None
    if row['rabinTextXml'] or row['rabinTranslationXml']:
        # Rabin, Old English Legal Writings: Wulfstan (columns AU-AZ)
        m = re.search(r'Base MS: (\S+) = (.*?)(?: \(|$)', row['rabinRef'])
        sig = RABIN_SIGLA.get((code, m.group(1)), m.group(1)) if m else ''
        r_wit = witness(sig, '' if sig != (m.group(1) if m else '') else (m.group(2) if m else '')) if sig else ''
        r_src = srcs.add('rabin-doml', 'Rabin', RABIN_DOML, 'edition', row['rabinPage'].split(' / ')[0])
        if row['rabinTextXml']:
            lang = 'la' if code == 'VII Atr' else 'ang'
            texts.append(('editionText', lang, r_src, pb(pages(row['rabinPage'])[0], r_src) + row['rabinTextXml'], '', r_wit))
        if row['rabinTranslationXml']:
            rabin_translation = ('translation', 'en', r_src, pb(pages(row['rabinPage'])[1], r_src) + row['rabinTranslationXml'], r_wit)
    u_by, aa_by = TRANSLATORS.get(code, (None, None))
    if u_by == 'Whitelock' and NOT_WHITELOCK in row['notes']:
        u_by = None
    if row['translationXml']:
        src = ed_src or translator(u_by, row['editorPage'] if u_by == 'Whitelock' else '')
        tpage = pages(row['editorPage'])[1] if ed_src or u_by == 'Whitelock' else ''
        translations.append(('translation', 'en', src, pb(tpage, src) + row['translationXml'], t_wit))
        if row.get('bTranslationXml'):
            translations.append(('translation', 'en', src, row['bTranslationXml'], witness('B')))
    if row['secondTranslationXml']:
        second = abt.surname(row['secondRef'])
        if second == 'Rabin' and 'Wulfstan' in row['secondRef'] and '2020' in row['secondRef']:
            src = srcs.add('rabin-doml', 'Rabin', RABIN_DOML, 'translation', pages(row['secondPage'])[0])
        elif second:
            src = srcs.add(ident(second), second, row['secondRefXml'], 'translation', pages(row['secondPage'])[0])
        else:
            src = translator(None)
        spage = pages(row['secondPage'])[0] or (pages(row['attPage'])[1] if src == 'attenborough' else '')
        translations.append(('translation', 'en', src, pb(spage, src) + row['secondTranslationXml'], t_wit))
    if rabin_translation:
        translations.append(rabin_translation)       # after the editors' own translations
    if row['thirdTranslationXml']:
        # Whitelock's English Historical Documents (columns AP-AT)
        m = re.match(r'([A-Z][A-Za-z0-9]{0,3})\s+\(', row['thirdMS'])
        translations.append(('translation', 'en', translator('Whitelock', row['thirdPage']), pb(row['thirdPage'], 'whitelock') + row['thirdTranslationXml'],
                             witness(m.group(1), MS_NAMES.get(m.group(1), '')) if m else ''))
    if row['supplementaryTranslationXml']:
        translations.append(('translation', 'en', translator(aa_by), row['supplementaryTranslationXml'],
                             witness(row['kSig'], row['kName'])))
    if row['germanXml']:
        translations.append(('translation', 'de', lie, pb(lpage('German'), lie) + row['germanXml'], ''))
    if row['englishXml']:
        cl = srcs.add('claude', 'Claude', CLAUDE_REF, 'translation')
        translations.append(('translation', 'en', cl, row['englishXml'], ''))

    # Order on the page: Liebermann's texts left to right as he prints them (column BP), then the modern
    # editions by the year they were first published; the translations: his German, the LLM's English of it,
    # then the others by year (sheet 'Editions and translations').
    sig_of = {w_[0]: sig_key(w_[1]) for w_ in wits}
    order = [x.strip() for x in row['liebOrder'].split('|')] if row['liebOrder'] else []
    lieb_t = [t for t in texts if t[0] == 'liebermannText']
    if order:
        lieb_t.sort(key=lambda t: order.index(sig_of.get(t[5], '')) if sig_of.get(t[5], '') in order else len(order))
    texts = lieb_t + sorted([t for t in texts if t[0] != 'liebermannText'], key=lambda t: YEARS.get(t[2], 9999))
    first = lambda t: 0 if t[2] == 'liebermann' else 1 if t[2] == 'claude' else 2
    translations.sort(key=lambda t: (first(t), YEARS.get(t[2], 9999) if first(t) == 2 else 0))

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
    for work in dict.fromkeys([x[0] for x in row.get('xr', [])] + [x[0] for x in row.get('xrBack', [])]):
        sid, name, ref = XR_WORKS[work]
        srcs.add(sid, name, ref, 'study')
        if ('e', sid) not in seen and ('t', sid) not in seen and ('x', sid) not in seen:
            seen.add(('x', sid))
            w('        <respStmt><resp>Cross-references to other clauses</resp><name ref="#%s">%s</name></respStmt>' % (sid, esc(srcs.items[sid][0])))
    dated = date_place(row['promulgation'], srcs)
    for sid in dict.fromkeys(sid for _, _, ids, _ in dated for sid in ids):
        if not any((k, sid) in seen for k in 'etx'):
            seen.add(('x', sid))
            w('        <respStmt><resp>Date and place</resp><name ref="#%s">%s</name></respStmt>' % (sid, esc(srcs.items[sid][0])))
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
        w('      <creation>%s<note type="promulgation">%s</note></creation>' % (creation_xml(dated), esc(row['promulgation'])))
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
        if who == 'oct2026-added':
            book, page, ms = page
            w('      <change when="2026-10" type="checked">Liebermann’s text of MS %s added from %s, p. %s.</change>' % (esc(ms), esc(book), esc(page)))
            continue
        if who == 'oct2026':
            col, (book, page, was, now) = verb, page
            what = {'K': 'Liebermann’s text', 'N': 'Liebermann’s text', 'AF': 'Liebermann’s text', 'BF': 'Liebermann’s text', 'BI': 'Liebermann’s text', 'O': 'Liebermann’s Latin text',
                    'L': 'Liebermann’s German translation', 'M': 'The English of Liebermann’s German',
                    'T': 'The modern editor’s text', 'U': 'The modern editor’s translation', 'W': 'The second translation'}[col]
            w('      <change when="2026-10" type="checked">%s corrected against %s, p. %s: “%s” → “%s”.</change>' % (what, esc(book), esc(page), esc(was), esc(now)))
            continue
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
    if row.get('vglLinks') or row.get('vglPrinted'):
        page = re.match(r'Gesetze I p\. ([^;]+)', row['vglRemark'])
        items = ['<ref target="clause:%s">%s</ref>' % (attr(i), esc(t)) if i else esc(t) for t, i in row['vglLinks']]
        w('        <note type="comparison" source="#liebermann"%s>%s</note>' % (
            (' n="%s"' % attr(page.group(1))) if page else '', '; '.join(items)))
        w('        <note type="comparisonPrinted" source="#liebermann">%s</note>' % esc(row['vglPrinted']))
        if 'TO COMPLETE' in row['vglRemark']:
            w('        <note type="comparisonIncomplete">Some of Liebermann’s notes here are cut off in the gutter of the scan used, and are still to be completed.</note>')
    if row.get('vglBack'):
        w('        <note type="comparedBy" source="#liebermann">%s</note>' % '; '.join(
            '<ref target="clause:%s">%s</ref>' % (attr(i), esc(t)) for t, i in row['vglBack']))
    for work, page, rel, text, tid, said in row.get('xr', []):
        sid = XR_WORKS[work][0]
        w('        <note type="comparison" source="#%s"%s>%s%s%s</note>' % (
            sid, (' n="%s"' % attr(page)) if page else '', ('<label>%s</label> ' % esc(rel)) if rel else '',
            ('<ref target="clause:%s">%s</ref>' % (attr(tid), esc(text))) if tid else esc(text),
            (' <quote>%s</quote>' % esc(said)) if said else ''))
    for work, page, rel, text, fid in row.get('xrBack', []):
        w('        <note type="comparedBy" source="#%s"%s><ref target="clause:%s">%s</ref></note>' % (
            XR_WORKS[work][0], (' n="%s"' % attr(page)) if page else '', attr(fid), esc(text)))
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
    'William': 'William I', 'Henry': 'Henry I', 'Earconberht': 'Earconberht of Kent',
}
OTHER = 'Other laws and legal texts'
# Codes listed under another king than the one who issued them: the rubrics
# to Ine's laws were written for Alfred's Domboc but belong with Ine's laws.
GROUP_OVERRIDE = {'Ine Rb': 'Ine of Wessex', 'App AGu': 'Alfred the Great', 'Duel': 'Ordeal rituals (Iudicia Dei)'}
# The ordeal liturgies and excommunication formulae Liebermann prints (Gesetze I pp. 401–441; added October 2026)
GROUP_OVERRIDE.update({'Iud Dei ' + n: 'Ordeal rituals (Iudicia Dei)' for n in 'I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI'.split()})
OWN_MS_NAMES = {'Erc', 'App AGu', 'Duel', 'Wl lad', 'Wl ep', 'Wl Lond', 'Wl art', 'Wl art Frz', 'Wl art retr', 'Leis Wl', 'Wl Edmr', 'CHn cor', 'Hn mon', 'Hn com', 'Hn Lond'} | {'Iud Dei ' + n for n in 'I II III IV V VI VII IX X XI XII XIII XIV XV XVI'.split()} | {'Excom ' + n for n in 'I II III IV V VI VII VIII IX X XI XII XIII'.split()}
GROUP_OVERRIDE.update({'Excom ' + n: 'Excommunication formulae' for n in 'I II III IV V VI VII VIII IX X XI XII XIII'.split()})
# Anglo-Latin law books (Gesetze I pp. 529–675; added 19 October 2026): Latin only, with æ and ę, so their language
# is not guessed from those letters
PHASE2B = ['Quadr Ded', 'Quadr Arg', 'Quadr I', 'Quadr Rb', 'Quadr II Praef', 'Quadr II', 'Hn', 'In Cn', 'Cons Cn', 'Ps Cn for', 'Lib Lond']
OWN_MS_NAMES |= set(PHASE2B)
GROUP_OVERRIDE.update({c: 'Anglo-Latin law books' for c in PHASE2B})


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
                # the suggested dates and places, each with the scholars who propose it (the first date is the database's)
                'dates': [[d, who] for d, who in promulgation.parse(r['promulgation'])[0]],
                'places': [[p, who] for p, who in promulgation.parse(r['promulgation'])[1]],
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
        for sig in (r['kSig'], r['nSig'], r['afSig'], r['bfSig'], r['biSig'], r['brSig'], r['tSig']):
            for k in ([sig] if sig in MS_NAMES else [sig_key(x) for x in re.split(r'[;,]\s*', sig or '')]):
                k = k.strip()
                if k and (k in MS_NAMES or re.fullmatch(r'[A-Z][a-z]?\d?', k)) and k not in c['manuscripts'] and k not in ('In', 'Cons'):
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
    # A clause joined from its lettered parts by tools/merge-parts.py: the part files' names and numbers
    # come back, so the parts are rebuilt under the same names, to be joined again.
    expanded = []
    for c in catalogue:
        if c.get('parts'):
            expanded.extend(dict(c, id=p['id'], file=p['id'] + '.xml', clause=p['clause'], parts=None) for p in c['parts'])
        else:
            expanded.append(c)
    catalogue = [{k: v for k, v in c.items() if k != 'parts'} for c in expanded]
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

    linked, total = vgl_links(rows)
    print('Liebermann’s cross-references: %d of %d linked to a clause' % (linked, total))
    print('Other scholars’ cross-references: %d placed on a clause' % xr_links(rows, read_cross_references(args.xlsx)))
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
