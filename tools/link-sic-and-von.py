#!/usr/bin/env python3
"""
Links two of Liebermann's signs to the list of grammatical abbreviations
(data/markforward.json), in Liebermann's text of every entry:

  - "!" straight after a form in roman type (gefearam!, ~!) is his "sic":
    <ref type="abbreviation" target="gram:sic"><abbr>!</abbr></ref>.
    An "!" in his German (italic: "lasst uns!") is an ordinary exclamation
    mark and is left alone.
  - "von" in his German (italic) is linked to gram:von.

Text already inside a link is left alone, so it can be run again safely.
New entries get the same links from the Suggest a change form and the import,
which read data/markforward.json.

  python3 tools/link-sic-and-von.py [--dry-run]
"""
import glob, os, re, sys

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
TOK = re.compile(r'(<[^>]+>)')
SIC = '<ref type="abbreviation" target="gram:sic"><abbr>!</abbr></ref>'
VON = '<ref type="abbreviation" target="gram:von"><abbr>von</abbr></ref>'


def fix(inner, counts):
    parts, stack = TOK.split(inner), []
    for i, p in enumerate(parts):
        if p.startswith('<'):
            if p.startswith('</'):
                if stack: stack.pop()
            elif not p.endswith('/>'):
                stack.append((re.match(r'<(\w+)', p).group(1), p))
            continue
        italic = any(n == 'hi' and 'italic' in t for n, t in stack)
        if any(n in ('ref', 'abbr') for n, t in stack):
            continue
        if italic:
            p, k = re.subn(r'(?<![\w-])von(?![\w-])', VON, p)
            counts['von'] += k
        else:
            p, k = re.subn(r'!', SIC, p)
            counts['!'] += k
        parts[i] = p
    return ''.join(parts)


def main():
    dry = '--dry-run' in sys.argv
    counts, files = {'!': 0, 'von': 0}, 0
    for f in sorted(glob.glob('entries/*.xml')):
        s = open(f, encoding='utf-8').read()
        new = re.sub(r'(<dictScrap type="(?:liebermann|senses)">)(.*?)(</dictScrap>)',
                     lambda m: m.group(1) + fix(m.group(2), counts) + m.group(3), s, flags=re.S)
        if new != s:
            files += 1
            if not dry: open(f, 'w', encoding='utf-8').write(new)
    print(f'{files} entries; "!" linked {counts["!"]}, "von" linked {counts["von"]}' + (' (dry run)' if dry else ''))


if __name__ == '__main__':
    main()
