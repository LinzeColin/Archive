# Independent check of the written DATA sheet: decode every stored raw value (strings via sharedStrings, numbers as text)
# and compare it with raw.pkl, cell by cell.
import zipfile, re, sys, numpy as np, pandas as pd
path = sys.argv[1]; z = zipfile.ZipFile(path); raw = pd.read_pickle('raw.pkl')
ss = [re.sub(r'<[^>]+>', '', x) for x in re.findall(r'<si>(.*?)</si>', z.read('xl/sharedStrings.xml').decode(), re.S)]
import html; ss = [html.unescape(x) for x in ss]
cols = list(raw.columns[1:21]); L = 'ABCDEFGHIJKLMNOPQRST'
vals = [raw[c].values for c in cols]; isstr = [raw[c].dtype == object for c in cols]
cell = re.compile(r'<c r="([A-Z]+)(\d+)"( t="s")?><v>([^<]*)</v></c>')
f = z.open('xl/worksheets/sheet3.xml'); carry = ''; nrow = 0; bad = []; nstr = 0; nnum = 0
while True:
    ch = f.read(1 << 24).decode('utf-8', errors='strict') if True else ''
    if not ch: break
    buf = carry + ch; cut = buf.rfind('</row>'); carry = buf[cut + 6:]; buf = buf[:cut + 6]
    for m in cell.finditer(buf):
        col, r, t, v = m.groups(); j = L.find(col)
        if len(col) > 1 or j < 0: continue
        i = int(r) - 2
        if i < 0: continue
        exp = vals[j][i]
        if t:
            nstr += 1
            if not v.isdigit() or ss[int(v)] != exp: bad.append((col, r, v, exp))
        else:
            nnum += 1
            if float(v) != float(exp): bad.append((col, r, v, exp))
        if j == 19: nrow += 1
print('rows', nrow, 'string cells', nstr, 'numeric cells', nnum, 'bad', len(bad), bad[:10])
print('expected rows', len(raw), 'expected string cells', len(raw) * sum(isstr))
