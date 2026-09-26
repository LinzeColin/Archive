import re, numpy as np, pandas as pd, time
from lxml import etree
X='../orig/x/xl/'
ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
sst=[ ''.join(si.itertext()) for si in etree.parse(X+'sharedStrings.xml').getroot()]
cols=[chr(65+i) for i in range(20)]
data={c:[] for c in cols}; rown=[]
t0=time.time()
blank_cells=0
for ev,row in etree.iterparse(X+'worksheets/sheet2.xml', tag=ns+'row'):
    r=int(row.get('r'))
    if r==1:
        hdr={}
        for c in row: hdr[re.match(r'[A-Z]+',c.get('r')).group()]=sst[int(c.find(ns+'v').text)]
        row.clear(); continue
    vals=dict.fromkeys(cols)
    for c in row:
        col=re.match(r'[A-Z]+',c.get('r')).group()
        v=c.find(ns+'v')
        if v is None: continue
        t=c.get('t')
        if t=='s': vals[col]=sst[int(v.text)]
        elif t=='str' or t=='inlineStr': vals[col]=v.text
        else: vals[col]=float(v.text)
    for col in cols: data[col].append(vals[col])
    rown.append(r)
    row.clear()
    while row.getprevious() is not None: del row.getparent()[0]
print('parsed',len(rown),time.time()-t0)
df=pd.DataFrame({hdr[c]:data[c] for c in cols})
df.insert(0,'ExcelRow',rown)
df.to_pickle('raw.pkl')
print(df.head()); print(df.dtypes)
