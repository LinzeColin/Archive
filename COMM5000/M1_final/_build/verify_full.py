"""Full-size check of a recalculated workbook: stream-scan big sheets for errors, then compare summary cells on a light copy."""
import zipfile, re, sys, subprocess
src = sys.argv[1]; lite = src.replace('.xlsx', '_lite.xlsx')
z = zipfile.ZipFile(src)
wb = z.read('xl/workbook.xml').decode(); rels = z.read('xl/_rels/workbook.xml.rels').decode()
def target(name):
    rid = re.search(r'<sheet [^>]*name="%s"[^>]*r:id="([^"]+)"' % name, wb).group(1)
    t = re.search(r'Id="%s"[^>]*Target="([^"]+)"' % rid, rels) or re.search(r'Target="([^"]+)"[^>]*Id="%s"' % rid, rels)
    t = t.group(1); return t.lstrip('/') if t.startswith('/xl') else 'xl/' + t
big = {target('DATA'), target('Dup_Sorted')}
for b in big:
    n_err = 0; n_f = 0; tail = ''
    with z.open(b) as fh:
        while True:
            chunk = fh.read(1 << 24)
            if not chunk: break
            s = tail + chunk.decode('utf-8', 'ignore')
            n_err += len(re.findall(r't="e"', s[:-200] if len(chunk) == 1 << 24 else s)); n_f += (s[:-200] if len(chunk) == 1 << 24 else s).count('<f')
            tail = s[-200:] if len(chunk) == 1 << 24 else ''
    print(b, 'error cells:', n_err, 'formula tags:', n_f)
out = zipfile.ZipFile(lite, 'w', zipfile.ZIP_DEFLATED)
empty = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>'
for it in z.infolist():
    out.writestr(it.filename, empty if it.filename in big else z.read(it.filename))
out.close(); print('lite written', lite)
