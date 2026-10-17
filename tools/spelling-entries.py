#!/usr/bin/env python3
"""
Marks Liebermann's spelling entries.

Some headwords in the Wörterbuch are not words but spellings: a letter or
group of letters (ā, aa, -cgg-, -tt, þ, ł), with a note on how the scribes
write it and a list of the entries where that spelling appears among the
forms. "aa für ā s. a, að, ladrinc, nam, ta" means that ā is sometimes
written aa, as under the adverb a (aa II Cn 15,1), að (aaþ), ladrinc
(laadrinc-), nam (nááme) and ta (taan).

Readers expect a headword to be a word, so each of these entries gets
<usg type="dom">spelling</usg> after its form. The entry page then shows a
"Spelling" badge and a line explaining what the entry is.

The list below was made in October 2026: headwords that are short letter
groups with a hyphen at either end and a spelling note in the text ("für",
"statt", "ersetzt", "abweichend", "geschwunden", "Gleitlaut"…), plus the
single letters, double letters and abbreviation signs, checked by eye. Word
elements in brackets ([-heort-], [-stryn-]) and pointers to word stems
(Æðel-, ceap-) are left out. Add or remove slugs here and run it again:

  python3 tools/spelling-entries.py

It can be run any number of times.
"""
import os, re, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TODAY = '2026-10-17'
SPELLING = [
    'a', 'a-10', 'a-11', 'a-12', 'a-5', 'a-6', 'a-7', 'a-8', 'a-9', 'aa',
    'ae', 'ae-2', 'ae-4', 'ae-5', 'ae-6', 'ae-7', 'ae-8', 'aeg', 'aei-g', 'aet-2',
    'ai', 'ai-2', 'ain', 'ain-2', 'ais', 'an-4', 'an-5', 'an-6', 'and-2', 'and-3',
    'aun', 'b', 'b-2', 'b-3', 'be-2', 'bs', 'buri', 'c', 'c-2', 'c-3',
    'c-4', 'cc', 'cc-2', 'ccg', 'cch', 'cg', 'cgc', 'cgcg', 'cgg', 'ch',
    'ch-2', 'ch-3', 'chs', 'ci', 'cs', 'ct', 'cw', 'd', 'd-2', 'd-3',
    'd-5', 'd-6', 'dd', 'dh', 'e', 'e-3', 'e-4', 'ea', 'ea-2', 'ear',
    'ee', 'eg', 'egn', 'ei', 'ei-2', 'ein', 'eis', 'en-2', 'en-3', 'entry',
    'eo', 'eor', 'er', 'eu', 'f', 'f-2', 'ff', 'fn', 'fore-5', 'g',
    'g-2', 'g-3', 'gald', 'gc', 'ge-3', 'ge-4', 'gg', 'gh', 'gi', 'gie',
    'gn', 'gs', 'gt', 'gu', 'gw', 'h', 'h-2', 'h-3', 'hc', 'heae',
    'hg', 'hh', 'hl', 'hl-2', 'hs', 'ht', 'hw', 'i', 'i-3', 'i-4',
    'ie', 'ie-2', 'ig', 'ige', 'ii', 'ing', 'io', 'ir', 'k', 'k-2',
    'l', 'l-2', 'lef', 'll', 'll-2', 'ls', 'm', 'm-2', 'm-3', 'm-4',
    'mb', 'mb-2', 'mm', 'mm-2', 'mm-3', 'mp', 'mpt', 'n', 'n-2', 'n-3',
    'n-4', 'nb', 'nc', 'nd', 'ne-5', 'ng', 'ngc', 'nn', 'nn-2', 'o',
    'o-2', 'od-5', 'oe', 'of-2', 'on-3', 'oo', 'ou', 'p', 'p-2', 'p-3',
    'pp', 'pp-2', 'pp-3', 'pur-2', 'qu', 'r', 'r-2', 'rae', 're', 'ref',
    'rf', 'ri', 'ro', 'rode', 'rr', 'rr-2', 'rs', 'ry', 's', 's-2',
    's-4', 'sc', 'sch', 'sh', 'sio-2', 'sp', 'ss', 'ss-2', 'ss-3', 'ssc',
    'ssh', 'st', 't', 't-2', 'tg', 'th', 'th-2', 'th-3', 'th-4', 'thaet',
    'thth', 'ti', 'tn', 'to-2', 'tr', 'tt', 'u', 'um', 'un-3', 'under-2',
    'ur', 'urc', 'uu', 'v', 'v-2', 'vu', 'w', 'w-2', 'we-2', 'we-a',
    'welf', 'weo', 'wer-3', 'wh', 'wi', 'wid-3', 'wie', 'wier', 'wo', 'woe',
    'wor', 'wu', 'wy', 'x', 'y', 'y-2', 'y-3', 'y-4', 'ya', 'ye',
    'yo', 'yr', 'z', 'z-2',
]

MARK = '<usg type="dom">spelling</usg>'


def main():
    changed = 0
    for slug in SPELLING:
        p = f'entries/{slug}.xml'
        if not os.path.exists(p):
            print('no such entry:', slug); continue
        s = open(p, encoding='utf-8').read()
        if MARK in s: continue
        s = re.sub(r'(\n( *)</form>)', r'\1\n\2' + MARK, s, count=1)
        s = s.replace('    </revisionDesc>', f'      <change when="{TODAY}">Marked as a spelling entry.</change>\n    </revisionDesc>', 1)
        open(p, 'w', encoding='utf-8').write(s)
        changed += 1
    print(f'{len(SPELLING)} spelling entries; {changed} marked now')


if __name__ == '__main__':
    main()
