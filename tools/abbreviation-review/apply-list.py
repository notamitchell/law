"""Applies the approved abbreviation review (October 2026) to data/markforward.json.
Run from the repository root. Writes the file in its one-object-per-line style."""
import json, re, sys, subprocess

P = 'data/markforward.json'
rows = json.load(open(P, encoding='utf-8'))
log = []

# ---------------------------------------------------------------- helpers
def find(anchor, printed=None):
    out = [r for r in rows if r['Anchor'] == anchor and (printed is None or r['Gesetze Text'].strip() == printed)]
    if not out:
        sys.exit(f'no row {anchor} / {printed}')
    return out

def setv(anchor, printed=None, de=None, en=None, note=None, modern=None, gesetze=None):
    for r in find(anchor, printed):
        if de is not None: r['German Expansion'] = de
        if en is not None: r['English Translation'] = en
        if note is not None:
            if note == '': r.pop('Notes: Grammatical', None)
            else: r['Notes: Grammatical'] = note
        if modern is not None:
            if modern == '': r.pop('Modern German', None)
            else: r['Modern German'] = modern
        if gesetze is not None: r['Gesetze Text'] = gesetze

def delete(anchor, printed=None):
    global rows
    hit = find(anchor, printed)
    rows = [r for r in rows if r not in hit]
    log.append(f'deleted {anchor} {printed or "(all rows)"}')

def add(after_anchor, row):
    i = max(i for i, r in enumerate(rows) if r['Anchor'] == after_anchor)
    rows.insert(i + 1, row)

RENAMES = {}
def rename(old, new):
    for r in rows:
        if r['Anchor'] == old: r['Anchor'] = new
    RENAMES[old] = new

# ------------------------------------------------- 0. tidy every row (stray spaces)
for r in rows:
    for k in list(r):
        if isinstance(r[k], str): r[k] = re.sub(r'\s+', ' ', r[k]).strip()

# ------------------------------------------------- 1. layout: Liebermann's form + modern German
for r in rows:
    g = r['German Expansion']
    m = re.search(r'\(?\s*Mod\.\s*Ger(?:man|\.)?(?:/NHD)?:\s*([^()]*)\)?\s*$', g)
    if m:
        modern = m.group(1).strip()
        g = g[:m.start()].strip().rstrip(',').strip()
        if not g:  # only the modern form was given: Liebermann's is the printed form
            g = r['Gesetze Text']
        r['German Expansion'] = g
        if modern and modern != g:
            r['Modern German'] = modern

# Liebermann's own forms of the core grammatical labels (from his grammatical articles)
setv('accusativus', de='Accusativ', modern='Akkusativ')
setv('adjektiv', de='Adjectiv', modern='Adjektiv')
setv('comparativus', de='Comparativ', modern='Komparativ', en='comparative')
setv('Futurum', de='Futurum', modern='Futur')
setv('Genitiv', 'gn', de='Genetiv', modern='Genitiv')
setv('Instrumental', de='Instrumentalis', modern='Instrumental')
setv('neutrum', de='Neutrum', modern='')
setv('Particip', de='Particip', modern='Partizip')
setv('Plural', de='Pluralis', modern='Plural')
setv('Praeposition', 'prp', de='Praeposition', modern='Präposition')
setv('Optativ', de='Optativ', modern='', en='optative (= Old English subjunctive)')
setv('ablativus', de='Ablativus', modern='Ablativ')
setv('superlativus', de='Superlativ', modern='')
setv('femininum', de='Femininum', modern='')
setv('vocativus', de='vocativus', modern='Vokativ')
setv('mitGenetiv', de='mit Genetiv', modern='mit Genitiv')
setv('PraepositionMitGenitiv', de='Praeposition mit Genetiv', modern='Präposition mit Genitiv')
setv('Subjekt', de='Subject', modern='Subjekt', en='subject',
     note=find('Subjekt')[0].get('Notes: Grammatical', '').replace('has makes clear', 'makes clear'))
setv('Object', de='Object', modern='Objekt')

# explanations out of the German column
setv('attributiv', de='attributiv')
setv('Form', 'Form', de='Form')
setv('mitTo', de='mit to')
setv('sanctus', de='sanctus, sancta')
setv('sic', de='sic!', note='German: so steht es da, “so it stands”. ' + find('sic')[0]['Notes: Grammatical'])

# the subjunctive rows (Old French verbs): Liebermann's Subjonctif; modern Konjunktiv
SUBJ_NOTE = find('Subjonktiv', 'sbj')[0].get('Notes: Grammatical', '')
setv('Subjonktiv', de='Subjonctif', modern='Konjunktiv', note=SUBJ_NOTE)
setv('Subjonktiv3Person', de='Subjonctif, 3. Person', modern='Konjunktiv, 3. Person', en='3rd person subjunctive', note='')
setv('SubjonktivPlural3Person', de='Subjonctif, Plural, 3. Person', modern='Konjunktiv, 3. Person Plural', en='3rd person plural subjunctive')
setv('imperfectSubjonctiv', de='Imperfect Subjonctif', modern='Konjunktiv Imperfekt')
setv('parfaitSubjonctiv3Person', de='parfait Subjonctif, 3. Person', modern='Konjunktiv Perfekt, 3. Person',
     en='3rd person perfect (= imperfect) subjunctive')
setv('parfaitSubjonctivPlural3Person', de='parfait Subjonctif, Plural, 3. Person', modern='Konjunktiv Perfekt, 3. Person Plural')
setv('PraeteritumSubjonctiv3Person', de='Praeteritum Subjonctif, 3. Person', modern='Konjunktiv Präteritum, 3. Person')
setv('mitSubjonctiv', de='mit Subjonctif', modern='mit Konjunktiv',
     note=find('mitSubjonctiv', 'm sbj')[0].get('Notes: Grammatical', '')
        .replace('OF ENTRY ', 'Old French entries ').replace('ENTRY ', '').replace('Liebermann‘s', 'Liebermann’s'))
setv('befehlendenSbjf', de='befehlenden Subjonctif einleitend, Deutsch blosser Conjunctiv',
     modern='befehlenden Konjunktiv einleitend, im Deutschen bloßer Konjunktiv',
     en="introducing a jussive (command) subjunctive; German uses the bare subjunctive, without 'dass'")
setv('ersetztDurchFolgendeSub', de='ersetzt durch folgenden Subjonctif', modern='ersetzt durch folgenden Konjunktiv',
     en='replaced by a following subjunctive')
delete('imperfectSubjonctiv3Pers')            # never linked as a whole: ipf sbj + 3

# ------------------------------------------------- 2. definitions that looked wrong
setv('abweichendVonWestsächsischLauten', de='abweichend von westsächsischen Lauten',
     en='differing from West Saxon sounds (non-West-Saxon forms)')
setv('angelsächsischDeutsch', de='angelsächsischer Dativ', en='Anglo-Saxon (Old English) dative', note='')
setv('AnakoluthStattNominativ', de='Anakoluth statt Nominativ', en='anacoluthon: accusative instead of nominative',
     note='The only instance of this phrase. At II Cn 71,1, helm ⁊ byrnan: byrnan is accusative singular, standing by anacoluthon where the list needs nominatives; Liebermann files it under ac:.')
setv('bessere', de='bessere', en='emend to, read', note='Imperative of bessern, “emend, correct”. Once (under rihte, bessere Hss.) the adjective “better”.')
setv('bessereViell', en='perhaps emend to')
setv('bessereVielleichtWie', en='perhaps emend, as in …, (to)')
setv('bezeichnet', de='bezeichnet', en='denotes; marked, designated')
setv('confundirend', en='confusing (it) with, mixing up with')
setv('dafur', en='instead (of it), in its place')
setv('dasselbe', de='desgleichen', en='likewise, ditto')
rename('dasselbe', 'desgleichen')
setv('ebensoWie', en='just as, in the same way as')
setv('geschwunden', de='geschwunden', en='lost, dropped (of a sound or letter)')
setv('Gleitlaut', en='glide, epenthetic (svarabhakti) sound')
setv('genitivSubjekt', de='Genetiv des Subjects', modern='subjektiver Genitiv', en='subjective genitive',
     note='Latin genitivus subjectivus: the genitive names the agent (le rei, the king as doer), as against gn obj, the objective genitive.')
setv('northumbrianisch', de='northumbrisch')
rename('northumbrianisch', 'northumbrisch')
setv('oderVielMehr', de='oder vielmehr')
setv('sieheDN', de='siehe dort Nummer', en='see there (that entry), number')
setv('sieheDortUnter', de='siehe dort und', en='see that entry, and')
delete('sieheDortUnter', 's.d.u.')           # never printed
setv('soDass', en='so that, with the result that', note='')
setv('spaten', en='late')
setv('untenObenNummer', de='und oben Nummer', en='and above, number […]', note='')
setv('unbetontInUndAus', gesetze='unbetont in- und ausl.', de='unbetont in- und auslautend', en='unstressed, medially and finally')
setv('vergleicheUnten', en='cf. below')
setv('vielleichtZuVerbessernFur', en='perhaps to be read (as an emendation) in place of')
delete('zugefugen', 'zugefügen')
setv('zugefugen', de='zugefügt', modern='', en='added')
rename('zugefugen', 'zugefugt')
setv('zurDeclination', en='(used) for declension, i.e. as a case marker')
setv('uberallHaufig', en='common everywhere')
# übers. merges into übersetzt
for r in find('ubersetzen'): r['Anchor'] = 'ubersetzt'
RENAMES['ubersetzen'] = 'ubersetzt'
setv('ubersetzt', de='übersetzt', en='translates; translated')
setv('ubertragen', de='übertragen', en='figurative(ly), in a transferred sense', note='')
setv('ubertritt', de='Übertritt', en='shift, transfer (to another inflectional class)')
setv('ubringe', de='übrige [Handschriften]', en='the other manuscripts (read); the rest')
rename('ubringe', 'ubrigeHandschriften')
setv('ubersetzend', note='')
# removed at your request (gloss words, not terms to look up)
for a in ('ausbessern', 'bestimmer', 'bezeichne', 'OriginalLasVielleicht'):
    delete(a)

# ------------------------------------------------- 3. rows for the links that needed their own
setv('circa', note='')
add('circa', {'Anchor': 'capitulum', 'Gesetze Text': 'c.', 'German Expansion': 'capitulum', 'Modern German': 'Kapitel', 'English Translation': 'chapter'})
delete('Genitiv', 'g.')
setv('las', de='las', en='read (past tense)', note='Past tense of lesen.')
add('Object', {'Anchor': 'objectiv', 'Gesetze Text': 'obj', 'German Expansion': 'objectiv', 'Modern German': 'objektiv',
               'English Translation': 'objective (genitive)', 'Notes: Grammatical': 'After gn: gn obj, the objective genitive (Latin genitivus objectivus), as against gn sbj.'})
setv('Partitiv', note='')
delete('sieheZu')
add('scilicet', {'Anchor': 'Schilling', 'Gesetze Text': 'sc.', 'German Expansion': 'Schilling(e)', 'English Translation': 'shilling(s)',
                 'Notes: Grammatical': 'After a number: OE scillingas, as in mid 120 sc.'})
setv('stark', 'st', note='')
setv('unten', de='und', en='and', note='In set phrases u. means unten, “below”: see u. n. and vgl. u.')
rename('unten', 'und')
setv('Zahlen', en='numbers, numerals')

# ------------------------------------------------- 4. empty or placeholder fields
setv('zitiert', 'citirt', de='citirt', modern='zitiert')
setv('zitiert', 'zitiert', de='zitiert', modern='')
setv('flectionslos', de='flectionslos', modern='flexionslos', en='uninflected, without inflection')
delete('GermanischeMythologie'); delete('GermanischesAltertum')
add('gerichtlich', {'Anchor': 'germanisch', 'Gesetze Text': 'German.', 'German Expansion': 'germanisch', 'English Translation': 'Germanic'})
setv('mitPronom.Object', gesetze='mit pronom. Object', de='mit pronominalem Object', modern='mit pronominalem Objekt')
rename('mitPronom.Object', 'mitPronomObject')
setv('PraepositionZeitlich', de='Praeposition zeitlich', modern='Präposition zeitlich', en='preposition (of time)')
add('superlativus', {'Anchor': 'superlativus', 'Gesetze Text': 'spl', 'German Expansion': 'Superlativ', 'English Translation': 'superlative'})
setv('wohl', de='wol', modern='wohl')

# ------------------------------------------------- 5. your answers
delete('abhang'); delete('altenglisch'); delete('beAlsBi')
setv('Substantiv', 'sb', note='Rare: once, in sb m gn (under eahta, feowertyne). Be careful to tell it from sbj, “Subject”.')

# ------------------------------------------------- 6. modern forms
setv('anderesSbj', de='anderes Subject', modern='anderes Subjekt')
setv('consonantischeStamme', de='consonantische Stämme', modern='konsonantische Stämme')
setv('dasHeisst', de='das heisst', modern='das heißt')
setv('einschliesslich', de='einschliesslich', modern='einschließlich')
setv('flectiert', de='flectirt', modern='flektiert', en='inflected (i.e. declined, conjugated)')
setv('InfinitivFlektiert', de='Infinitiv flectirt', modern='flektierter Infinitiv')
setv('mitObject', de='mit Object', modern='mit Objekt', en='with object')
setv('mitObjectsaccusativ', de='mit Objectsaccusativ', modern='mit Objektsakkusativ', en='with accusative object')
setv('praefigiert', de='praefigirt', modern='präfigiert')

# ------------------------------------------------- 7. smaller improvements
S7 = [
 ('aber', None, None, 'but; however'),
 ('abkunft', None, None, 'descent, extraction, origin'),
 ('abweichendFür', None, None, 'irregularly for, as a variant spelling of'),
 ('allgemein', None, None, 'in general, in a general sense'),
 ('alsAuch', None, None, '(sowohl ..) als auch: both .. and; as well as'),
 ('anderer', None, 'ander (andere, anderer, anderem, anderen)', 'other, another'),
 ('angeglichen', None, None, 'assimilated, levelled (by analogy)'),
 ('Artikel', None, None, '(grammatical) article'),
 ('aufRasur', None, None, 'on an erasure'),
 ('ausser', None, None, 'except; besides, apart from'),
 ('Bedeutungen', None, 'Bedeutungen', 'meanings, senses'),
 ('Begriff', None, None, 'concept, notion; term'),
 ('besondere', None, 'besonders', 'especially, particularly'),
 ('bezeichnen', None, None, 'to denote, designate, mark'),
 ('dafurAbweichend', None, None, 'instead, as a deviant spelling (the forms that follow are found in its place)'),
 ('daraus', None, None, '(taken) from this, derived from this'),
 ('dassMitObjektsatz', None, 'dass mit Objectsatz', "'that', introducing an object clause"),
 ('Derivativ', None, None, 'derivatives and compounds (words formed from the headword)'),
 ('durch', None, None, 'through, by (means of); because of'),
 ('durchauss', None, None, 'entirely, completely; (with nicht) not at all'),
 ('eingesetzt', None, 'eingesetzt', 'substituted (for), put in (place of); (of a bishop) installed'),
 ('Ersatz', None, None, 'replacement, substitute (for); (legal) compensation'),
 ('falsch', None, None, 'wrong(ly), erroneous(ly), false(ly)'),
 ('folgendePl', None, 'und folgende', 'and following'),
 ('FremdworterDeclination', None, None, 'declension of foreign words (loanwords)'),
 ('fur', None, None, 'for; in place of, (written) instead of'),
 ('gefasst', None, None, 'understood, taken (as); caught (of a thief)'),
 ('gesondertNeben', None, None, 'listed separately beside, as distinct from'),
 ('Gegensatz', None, None, 'contrast, opposite (im Ggs. zu: as opposed to)'),
 ('grammatischerWechsel', None, None, "grammatical alternation (Verner's Law)"),
 ('grammatisirt', None, None, 'grammatically regularised (by a scribe)'),
 ('hinterRegiertemPronomen', None, None, 'placed after the pronoun it governs (postposed preposition)'),
 ('HssVerderbt', None, None, 'text corrupt in the MSS'),
 ('haufig', None, None, 'frequent(ly), often'),
 ('irrig', None, 'irrig', 'erroneous(ly), wrongly'),
 ('jemand', None, 'jemand (jemanden, jemandem)', 'someone, somebody'),
 ('kurzsilbig', None, None, 'short-stemmed'),
 ('langsilbig', None, None, 'long-stemmed'),
 ('lies', None, None, 'read (emend to)'),
 ('mitGegensatz', None, None, 'contrasted with, as opposed to'),
 ('mehrfach', None, None, 'several times, in several places'),
 ('mitAbhang', None, 'mit abhängigem', 'with dependent (e.g. genitive)'),
 ('mitZahlenVerbunden', None, None, 'combined with (other) numerals'),
 ('Nummer', None, None, 'no. (numbered section of an entry)'),
 ('nach', None, None, 'after; according to'),
 ('nordisch', None, None, 'Norse (Old Norse, Scandinavian)'),
 ('obIndUberallEtc', None, 'ob Indicativ? überall syntaktisch Optativ möglich, ja gewöhnlicher', 'Indicative? An optative would be possible everywhere, indeed more usual.'),
 ('obliquus', None, 'Obliquus', 'oblique case'),
 ('original', None, 'original, ursprünglich', 'original; originally'),
 ('palatalen', None, None, 'palatal'),
 ('parfait', None, None, 'perfect (= Old French preterite, passé simple); pf pc = past participle'),
 ('regelmassigIn', None, 'regelmässig in', 'regularly in'),
 ('regierend', None, None, 'governing (a case, infinitive or clause)'),
 ('regiertem', None, None, 'governed (word or case)'),
 ('saeculum', None, 'saeculo', '(in the) century'),
 ('SubstantivMitGenitiv', None, None, '(used as a) noun, with genitive'),
 ('SubjekteSindPersonenInEtc', None, 'Subjecte sind Personen in obigen Citaten ausser folgenden', None),
 ('schwachIKlasse', None, 'schwache I. Klasse', 'weak (verbs), class I'),
 ('selten', None, None, 'rare, rarely'),
 ('seltener', None, None, 'less often, more rarely'),
 ('setzt', None, None, 'puts, writes, uses; renders (as)'),
 ('setztFur', None, None, 'puts for, uses to render'),
 ('sicher', None, None, 'certain(ly); safe, secure'),
 ('silbenhaft', None, None, 'syllable by syllable, i.e. element by element (calque-like)'),
 ('spatVerbessertAus', None, None, 'corrected (by a late hand) from'),
 ('Synkope', None, 'synkopirt (?)', 'syncopated'),
 ('unterAnderen', None, 'unter anderem/anderen; und andere', 'among others; and others'),
 ('umschreibt', None, None, 'expresses periphrastically'),
 ('unorganisch', None, None, 'inorganic (unetymological, intrusive)'),
 ('unverstanden', None, None, 'not understood (by the scribe or translator)'),
 ('verbessert', None, None, 'corrected (in the MS)'),
 ('Verbindung', None, None, 'combination, collocation; connection, association'),
 ('vielleichtStatt', None, None, 'perhaps (written) for'),
 ('volksetymologisch', None, None, 'by folk etymology'),
 ('wasSeltenIn', None, None, 'which is rare in'),
 ('Wechsel', None, None, 'alternation; change'),
 ('weiter', None, None, 'further; additional; (in a) wider (sense)'),
 ('weltliche', None, 'weltlich (-e, -en, -es)', None),
 ('wofur', None, None, 'in place of which, instead of which'),
 ('ZeileVorher', None, 'Zeile(n) vorher', None),
 ('ZeileWeiter', None, 'Zeile(n) weiter', None),
 ('zunachst', None, None, 'first, primarily; nearest, next'),
 ('Zusammensetzung', None, 'Zusammensetzungen', 'compounds'),
 ('älteren', None, 'älter (ältere, älteren, älteres)', 'older, earlier'),
 ('ofter', None, None, 'frequently, repeatedly (also: more often)'),
 ('uber', None, None, 'above, over; about, concerning'),
 ('ubrig', 'übrige', 'übrige [Handschriften]', 'the other manuscripts (read)'),
 ('ubrige', None, None, '(the) other(s), remaining'),
 ('ubersetzt', 'übs', None, 'translates; translated'),
 ('Ubersetzer', None, 'Übersetzer', 'translators'),
]
for a, p, de, en in S7:
    setv(a, p, de=de, en=en)
setv('absolutus', note=find('absolutus')[0]['Notes: Grammatical'].replace('im absolutem Gebrauch', 'im absoluten Gebrauch').replace('forg(ie)meleisen', 'forg[ie]meleasian'))
setv('endungslos', note='')
delete('Gegensatz', 'Gegs.')
setv('Synkope', modern='synkopiert')
setv('SubjekteSindPersonenInEtc', modern='Subjekte sind Personen in obigen Zitaten außer folgenden')
setv('regelmassigIn', modern='regelmäßig in')
setv('dassMitObjektsatz', modern='dass mit Objektsatz')
setv('eingesetzt', 'Eingesetzt', de='eingesetzt')

# ------------------------------------------------- 8. typos, duplicates, unused rows
rename('abgekürtzt', 'abgekurzt')
setv('bessereStett', gesetze='bessere statt', de='bessere statt', en='emend to [X] instead of [Y]',
     note='See [Albericus]: (bessere statt Hubertus?) deVere, camerarius Hn Lond Test.')
rename('bessereStett', 'bessereStatt')
setv('diesSeihtIrrig', gesetze='dies sieht irrig', de='dies sieht irrig', en='(the source named) wrongly reads this as')
rename('diesSeihtIrrig', 'diesSiehtIrrig')
setv('geandertIn', gesetze='geänd. in')
setv('gescriebenFur', en='written for, i.e. used as a spelling of')
rename('gescriebenFur', 'geschriebenFur')
setv('gutturalen', en='guttural, i.e. velar')
delete('hinterRegiertemPronomen', 'hinter regiertem pro')
rename('hinzugefugtBehufsSubstivirung', 'hinzugefugtBehufsSubstantivirung')
setv('identificirt', en='identified (with)')
setv('imGegensatzZuAnderenPerEtc', de='im Gegensatz zu anderen Personen des Satzes auf syntaktische Hauptperson bezogen',
     en='referring to the syntactic subject, as opposed to other persons in the clause')
setv('mitAkkusativDerPerson', en='with accusative of the person')
rename('mitAkkusativDerPerson', 'mitAccusativDerPerson')
delete('mittelenglisch', 'mengel.')
rename('ohneVerherigeNegation', 'ohneVorherigeNegation')
setv('sonstHaufig', gesetze='sonst häufig', de='sonst häufig')
setv('SubjonktivPlural3Person', en='3rd person plural subjunctive')
setv('substantivirt', en='substantivised, nominalised')
setv('sudenglisch', en='southern English')
setv('Uberschrift', de='Überschrift', en='heading, rubric', note='')
setv('unSoWeiter', de='und so weiter')
rename('unSoWeiter', 'undSoWeiter')
setv('verlesenAls', 'Verslesen als', gesetze='Verlesen als', de='verlesen als')
setv('vorbezeichnete', 'vorbezeichnetes', de='vorbezeichnetes')
delete('latinisiert', 'latinisiert')
setv('latinisiert', de='latinisirt', modern='latinisiert')
setv('Schreibern', en='scribes (dative plural of Schreiber)')
delete('ubringens')
first_unubs = find('unubersetzt')[0]
rows.remove(first_unubs)
for a in ('Optativ2Person', 'Optativ3Person', 'Spalte1', 'Spalte2', 'Spalte3', 'setzGlossator', 'unbestimmer'):
    delete(a)
setv('ableitenden', en='deriving, derivational (inflected form of ableitend)')
setv('Anakoluth', en='anacoluthon (Gr. anakolouthon)')
setv('conjunctivusFuturus', de='conjunctivus futuri', modern='Konjunktiv Futur')
setv('dafurAbweichendSpat', en='instead, as a late deviant spelling')
setv('demonstrativ', en='demonstrative')
setv('Lauten', de='Lauten', en='sounds')
setv('spatangelsachsisch', en='late Old English')
setv('SubjektIsAbstract', gesetze='sbj ist Abstract', de='Subject ist Abstract', modern='Subjekt ist Abstraktum')
setv('umschreiben', en='paraphrase, express periphrastically')
add('verbumVicarium', {**{k: v for k, v in find('verbumVicarium')[0].items()}, 'Gesetze Text': 'Verb vicar.'})
rename('vonScheibern12JahrEtc', 'vonSchreibern12JahrEtc')
setv('vorRegirtemInfinitivZu', gesetze='vor regirtem Infinitiv ‘zu’', de='vor regirtem Infinitiv ‘zu’', modern='vor regiertem Infinitiv ‘zu’',
     en='before a governed infinitive: ‘zu’ (‘to’)')
setv('zwiemalGlossirend', en='glossing (a Latin word) twice')
setv('zunachstNoch', en='at first also, to begin with')
rename('Zeite', 'Zeile')
rename('durchauss', 'durchaus')

# every remaining Modern German equal to the German is dropped
for r in rows:
    if r.get('Modern German', '').strip() in ('', r['German Expansion']):
        r.pop('Modern German', None)

# ---------------------------------------------------------------- write
order = ['Anchor', 'Gesetze Text', 'German Expansion', 'Modern German', 'English Translation', 'Notes: Grammatical', 'Link automatically']
lines = []
for r in rows:
    o = {k: r[k] for k in order if k in r}
    o.update({k: v for k, v in r.items() if k not in o})
    lines.append(json.dumps(o, ensure_ascii=False, separators=(',', ':')))
open(P, 'w', encoding='utf-8').write('[\n' + ',\n'.join(lines) + '\n]\n')
json.dump(RENAMES, open('tools/abbreviation-review/renames.json', 'w'), indent=1)
print(len(rows), 'rows;', len({r["Anchor"] for r in rows}), 'abbreviations;', len(RENAMES), 'renamed')
print('\n'.join(log))
