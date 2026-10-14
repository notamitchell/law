import json, sys
R = json.load(open(sys.argv[1]))
rows = []
for r in R:
    if r['grade'] == 'none':
        continue
    opts = []
    for gi, g in enumerate(r['groups']):
        for c in g:
            if not c['add'] or not opts or opts[-1]['g'] != gi:
                opts.append({'m': {k: c[k] for k in ('id', 'orth', 'pos', 'eng', 'shared')}, 's': [], 'd': gi == 0, 'g': gi})
            else:
                opts[-1]['s'].append(c['id'])
    for o in opts:
        del o['g']
    rows.append({'e': r['id'], 'hw': r['hw'], 's': r['snippet'][:150], 'g': r['grade'], 't': r['tier'], 'x': r['existing'], 'o': opts[:9]})
d = json.dumps(rows, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
t = open(sys.argv[2]).read()
open(sys.argv[3], 'w').write(t.replace('__DATA__', d))
print(len(rows), len(d) // 1000, 'KB')
