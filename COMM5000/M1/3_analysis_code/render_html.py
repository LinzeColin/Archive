import re, html, content as C

FD = '/tmp/claude-0/-home-user-Archive/25e37d8b-0c9d-504d-9ffe-c2fe61360ca7/scratchpad/fonts'
import base64
EMBED = False
def ff(fam, pkg, file, w, style='normal'):
    path = f"{FD}/{pkg}/files/{file}"
    src = (f"url(data:font/woff2;base64,{base64.b64encode(open(path,'rb').read()).decode()}) format('woff2')" if EMBED else f"url('file://{path}') format('woff2')")
    return f"@font-face{{font-family:'{fam}';src:{src};font-weight:{w};font-style:{style};}}"
I='fontsource-inter-5.3.0'; S='fontsource-source-serif-4-5.3.0'; P='fontsource-ibm-plex-sans-condensed-5.3.0'
def fonts():
    return ''.join([
    ff('SS4', S, 'source-serif-4-latin-400-normal.woff2', 400), ff('SS4', S, 'source-serif-4-latin-400-italic.woff2', 400, 'italic'),
    ff('SS4', S, 'source-serif-4-latin-600-normal.woff2', 600), ff('SS4', S, 'source-serif-4-latin-700-normal.woff2', 700),
    ff('INT', I, 'inter-latin-400-normal.woff2', 400), ff('INT', I, 'inter-latin-500-normal.woff2', 500), ff('INT', I, 'inter-latin-600-normal.woff2', 600), ff('INT', I, 'inter-latin-700-normal.woff2', 700),
    ff('PXC', P, 'ibm-plex-sans-condensed-latin-400-normal.woff2', 400), ff('PXC', P, 'ibm-plex-sans-condensed-latin-400-italic.woff2', 400, 'italic'),
    ff('PXC', P, 'ibm-plex-sans-condensed-latin-600-normal.woff2', 600)])
FONTS = fonts()
CSS = FONTS + """
@page{size:A4;margin:15mm 16mm 16mm 16mm;}
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font-family:'SS4','Source Serif 4',serif;font-size:9.7pt;line-height:1.42;color:#1f1f1d;hyphens:auto;font-kerning:normal;font-variant-numeric:lining-nums}
.mast{border-bottom:1.2px solid #1f1f1d;padding-bottom:7px;margin-bottom:9px;display:flex;justify-content:space-between;align-items:flex-end}
.mast .k{font-family:'INT',sans-serif;font-size:7.2pt;letter-spacing:.08em;text-transform:uppercase;color:#52514e}
h1{font-family:'INT',sans-serif;font-weight:700;font-size:21pt;letter-spacing:-.015em;line-height:1.08;margin:0 0 3px}
.sub{font-family:'INT',sans-serif;font-weight:400;font-size:10.6pt;color:#3d3d3a;margin:0 0 6px}
.meta{font-family:'INT',sans-serif;font-size:7.3pt;color:#6b6a66;margin-bottom:8px;display:flex;gap:14px;flex-wrap:wrap}
.meta b{font-weight:600;color:#3d3d3a}
h2{font-family:'INT',sans-serif;font-weight:650;font-size:11.2pt;margin:11px 0 3px;letter-spacing:-.005em;break-after:avoid;color:#1f1f1d}
h2 .n{color:#2a78d6;margin-right:6px;font-weight:700}
p{margin:0 0 5.5px;text-align:justify;text-justify:inter-word;orphans:3;widows:3}
b{font-weight:600}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin:8px 0 6px;break-inside:avoid}
.kpi>div{border:1px solid #e6e5e0;border-top:2.5px solid #2a78d6;border-radius:3px;padding:6px 8px 6px;background:#fbfbfa}
.kpi>div:nth-child(4){border-top-color:#eb6834}
.kpi .v{font-family:'INT',sans-serif;font-weight:700;font-size:13.2pt;letter-spacing:-.01em;line-height:1.1}
.kpi .l{font-family:'INT',sans-serif;font-weight:500;font-size:6.9pt;color:#3d3d3a;margin-top:2px}
.kpi .s{font-family:'INT',sans-serif;font-size:6.5pt;color:#6b6a66;margin-top:1px}
.tbl{margin:7px 0 9px;break-inside:avoid}
.tbl.split{break-inside:auto} .tbl.split tr{break-inside:avoid} thead{display:table-header-group}
.cap{font-family:'INT',sans-serif;font-size:7.3pt;line-height:1.35;color:#3d3d3a;margin:3px 0 0}
.cap b{font-weight:600;color:#1f1f1d}
.tcap{font-family:'INT',sans-serif;font-size:7.6pt;font-weight:600;margin:0 0 3px;color:#1f1f1d}
table{border-collapse:collapse;width:100%;font-family:'PXC',sans-serif;font-size:7.15pt;line-height:1.28;font-variant-numeric:tabular-nums}
th{font-weight:600;text-align:left;border-top:1.1px solid #1f1f1d;border-bottom:.7px solid #1f1f1d;padding:3px 4px;background:#f4f3ef;vertical-align:bottom}
td{padding:2.2px 4px;border-bottom:.4px solid #e6e5e0;vertical-align:top}
tr:last-child td{border-bottom:1.1px solid #1f1f1d}
table.num td:nth-child(n+3),table.num th:nth-child(n+3){text-align:right}
table.desc td:nth-child(n+3),table.desc th:nth-child(n+3){text-align:right}
table.desc tr.g td{border-top:.7px solid #bdbcb6}
table.desc td:first-child{font-weight:600}
td.lux{color:#c4501f;font-weight:600} td.non{color:#1c5cab}
.note{font-family:'PXC',sans-serif;font-size:6.7pt;color:#52514e;margin-top:3px;line-height:1.3}
figure{margin:6px 0 9px;break-inside:avoid}
figure img{width:100%;display:block}
.refs p{text-align:left;padding-left:14px;text-indent:-14px;font-size:8.7pt;line-height:1.35;margin-bottom:4px;word-break:break-word}
.two{display:grid;grid-template-columns:1.55fr 1fr;gap:10px}
.pb{break-before:page}
.wc{font-family:'INT',sans-serif;font-size:7pt;color:#6b6a66;border:1px solid #e6e5e0;border-radius:3px;padding:2px 6px}
"""

def esc_keep(t):  # allow <b>,<i>
    return t

def mn(t):
    return re.sub(r'(?<![\w\-])-(?=[\d.])', '\u2212', str(t))

def table(head, rows, cls='', cells_cls=None):
    h = ''.join(f'<th>{c}</th>' for c in head)
    body = ''
    for i, r in enumerate(rows):
        tr_cls = ''
        tds = ''
        for j, c in enumerate(r):
            cc = cells_cls(i, j, c) if cells_cls else ''
            tds += f'<td class="{cc}">{mn(c)}</td>'
        if cls == 'desc' and i % 3 == 0 and i > 0: tr_cls = 'g'
        body += f'<tr class="{tr_cls}">{tds}</tr>'
    return f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>'

def build(word_count):
    out = [f'<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><title>{C.TITLE}</title><style>{CSS}</style></head><body>']
    out.append(f'<div class="mast"><span class="k">{C.META}</span><span class="wc">Body text: {word_count} words (excl. tables, figures, captions, references)</span></div>')
    out.append(f'<h1>{C.TITLE}</h1><div class="sub">{C.SUBTITLE}</div>')
    out.append('<div class="meta"><span><b>Client</b> online used-car marketplace, India</span><span><b>Data</b> COMM5000-Used_Car_Price_Prediction.xlsm · 1,005,000 listings × 20 fields · full-population analysis</span></div>')
    for b in C.BODY:
        if b[0] == 'h':
            n, t = b[1].split('  ', 1)
            if n == '6': pass
            out.append(f'<h2><span class="n">{n}</span>{t}</h2>')
        elif b[0] == 'p':
            out.append(f'<p>{mn(b[1])}</p>')
        elif b[0] == 'kpi':
            out.append('<div class="kpi">' + ''.join(f'<div><div class="v">{mn(v)}</div><div class="l">{l}</div><div class="s">{mn(s)}</div></div>' for v, l, s in C.KPIS) + '</div>')
        elif b[0] == 'fig':
            path, cap = C.FIGS[b[1]]
            lab, rest = cap.split('. ', 1)
            out.append(f'<figure><img src="{path}"><div class="cap"><b>{lab}.</b> {rest}</div></figure>')
        elif b[0] == 'table':
            if b[1] == 'audit':
                out.append('<div class="tbl split"><div class="tcap">Table 1. Data-quality audit and treatment log</div>' + table(C.AUDIT_HEAD, C.AUDIT, 'audit') + '</div>')
            elif b[1] == 'desc':
                def cc(i, j, c):
                    if j == 1: return 'lux' if c == 'Luxury' else ('non' if c.startswith('Non') else '')
                    return ''
                out.append('<div class="tbl"><div class="tcap">Table 2. Numerical summaries: entire sample, luxury (Audi, BMW, Mercedes) and non-luxury segments</div>' + table(C.DESC_HEAD, C.desc_rows(), 'desc', cc) + f'<div class="note">{C.DESC_NOTE}</div></div>')
            elif b[1] == 'plan':
                out.append('<div class="tbl"><div class="tcap">Table 3. Development plan for Milestone 2 and the final report</div>' + table(C.PLAN_HEAD, C.PLAN, 'plan') + '</div>')
    out.append('<h2><span class="n">R</span>References</h2><div class="refs">' + ''.join(f'<p>{r}</p>' for r in C.REFS) + '</div>')
    out.append('<h2><span class="n">A</span>Appendix: robustness of key results</h2>')
    out.append('<div class="two"><div class="tbl"><div class="tcap">Table A1a. Sensitivity to cleaning choices</div>' + table(C.SENS_HEAD, C.sens_rows(), 'num') +
               '</div><div class="tbl"><div class="tcap">Table A1b. Usage correlation under alternative km caps</div>' + table(["Kms_Driven cap", "n", "r (raw)", "r (log–log)"], C.cap_rows(), 'num') + '</div></div>')
    out.append('<div class="note">All statistics computed on the full saved dataset (no sampling) except the random-sample panels (Figure 2B; Figure 3A, 3C). Confidence intervals for medians use order statistics; for the segment median ratio, 200 bootstrap resamples. Reproduction: the companion Excel workbook lists every aggregate, the cleaning maps and the source row numbers of plotted samples.</div>')
    out.append('</body></html>')
    return '\n'.join(out)

if __name__ == '__main__':
    wc = sum(len(re.sub(r'<[^>]+>', '', b[1]).split()) for b in C.BODY if b[0] in ('p', 'h'))
    open('report.html', 'w').write(build(wc)); print('words', wc)
