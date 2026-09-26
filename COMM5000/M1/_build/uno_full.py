# Full-size check without re-saving the 200 MB workbook: LibreOffice loads it, recalculates every formula
# (calculateAll), counts error cells on every sheet, and writes the computed values of the summary sheets
# to a small .xlsx that verify_sub.py can read.
import sys, time, json, subprocess, uno, os
from com.sun.star.beans import PropertyValue
from com.sun.star.sheet.FormulaResult import ERROR as FR_ERROR

path, port, out = sys.argv[1], sys.argv[2], sys.argv[3]
import tempfile; S = tempfile.gettempdir()  # folder for the LibreOffice profile
proc = subprocess.Popen(['soffice', f'-env:UserInstallation=file://{S}/lo_uno{port}', '--headless', '--norestore', '--nologo',
                         f'--accept=socket,host=localhost,port={port};urp;'])
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
ctx = uno.getComponentContext()
res = ctx.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', ctx)
for _ in range(120):
    try:
        rc = res.resolve(f'uno:socket,host=localhost,port={port};urp;StarOffice.ComponentContext'); break
    except Exception:
        time.sleep(1)
desk = rc.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', rc)
def pv(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p
t0 = time.time()
doc = desk.loadComponentFromURL(uno.systemPathToFileUrl(os.path.abspath(path)), '_blank', 0, (pv('Hidden', True),))
log('loaded', round(time.time() - t0))
t1 = time.time(); doc.calculateAll(); log('calculateAll', round(time.time() - t1))
errs = {}; dump = {}
for sh in doc.Sheets:
    cur = sh.createCursor(); cur.gotoEndOfUsedArea(False); a = cur.RangeAddress
    rng = sh.getCellRangeByPosition(0, 0, a.EndColumn, a.EndRow)
    q = rng.queryFormulaCells(FR_ERROR)
    n_err = sum((x.EndColumn - x.StartColumn + 1) * (x.EndRow - x.StartRow + 1) for x in q.RangeAddresses)
    errs[sh.Name] = [n_err, [sh.getCellRangeByPosition(x.StartColumn, x.StartRow, x.EndColumn, x.EndRow).AbsoluteName for x in q.RangeAddresses[:10]]]
    if sh.Name not in ('DATA', 'Dup_Sorted'):
        dump[sh.Name] = [list(r) for r in rng.getDataArray()]
    log(sh.Name, 'rows', a.EndRow + 1, 'errors', n_err)
json.dump({'errors': errs}, open(out + '.errors.json', 'w'), ensure_ascii=False, indent=1)
doc.close(True); proc.terminate()
from openpyxl import Workbook
wb = Workbook(); wb.remove(wb.active)
for name, rows in dump.items():
    ws = wb.create_sheet(name)
    for r in rows: ws.append([None if v == '' else v for v in r])
wb.save(out); log('wrote', out)
