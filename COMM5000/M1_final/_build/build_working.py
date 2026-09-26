"""Build the formula-based working workbook (human-traceable steps).
usage: python3 build_working.py <n_rows|all> <out.xlsx> [--nocache]
"""
import sys, zipfile, shutil, os, re, math, json
import numpy as np, pandas as pd
from xml.sax.saxutils import escape
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.formula import ArrayFormula
from openpyxl.utils import get_column_letter
from openpyxl.chart import ScatterChart, BarChart, LineChart, SurfaceChart3D, Reference, Series
from openpyxl.chart.axis import ChartLines

NARG = sys.argv[1]; OUT = sys.argv[2]; NOCACHE = '--nocache' in sys.argv
raw = pd.read_pickle('raw.pkl')
if NARG != 'all': raw = raw.iloc[:int(NARG)].copy()
N = len(raw); L = N + 1                       # last data row
def rng(col): return f"DATA!${col}$2:${col}${L}"
C = {k: rng(v) for k, v in dict(Brand='A', Model='B', Year='C', Mil='D', Eng='E', HP='F', Fuel='G', Trans='H', Owner='I', Color='J', City='K',
      KM='L', Ins='M', Svc='N', Acc='O', Tax='P', Doors='Q', Seats='R', Age='S', Price='T', BrandC='U', FuelC='V', Seg='W', KMOK='X',
      MilOK='Y', EngOK='Z', HPOK='AA', Unk='AB', Key='AC').items()}

ARIAL = 'Arial'
F = Font(name=ARIAL, size=10); FB = Font(name=ARIAL, size=10, bold=True); FT = Font(name=ARIAL, size=12, bold=True)
FI = Font(name=ARIAL, size=10, color='0000FF'); FN = Font(name=ARIAL, size=9, italic=True, color='555555')
HDR = PatternFill('solid', fgColor='D9E1F2'); INP = PatternFill('solid', fgColor='FFF2CC'); thin = Side(style='thin', color='BFBFBF')
def head(ws, r, c, vals):
    for j, v in enumerate(vals):
        x = ws.cell(r, c + j, v); x.font = FB; x.fill = HDR; x.alignment = Alignment(wrap_text=True, vertical='center'); x.border = Border(bottom=thin)
def put(ws, ref, val, fmt=None, font=F, arr=False):
    ws[ref] = ArrayFormula(ref, val) if arr else val
    ws[ref].font = font
    if fmt: ws[ref].number_format = fmt
def widths(ws, d):
    for k, v in d.items(): ws.column_dimensions[k].width = v

# ------------------------------------------------------------------ cleaned values (for cached values + lists)
fuel_map = {'petrol': 'Petrol', 'diesel': 'Diesel', 'cng': 'CNG', 'electric': 'Electric', 'electrik': 'Electric', 'hybrid': 'Hybrid', 'hybridd': 'Hybrid', 'unknown': 'Unknown'}
d = raw
BrandC = d.Brand.str.strip(); FuelC = d.Fuel_Type.str.strip().str.lower().map(fuel_map)
Seg = np.where(BrandC.isin(['Audi', 'BMW', 'Mercedes']), 'Luxury', 'Non-luxury')
CAP = 1_000_000
KMOK = (d.Kms_Driven >= 0) & (d.Kms_Driven <= CAP)
def okflag(s):
    pos = s[s > 0]; m = pos.mean(); sd = pos.std(ddof=1)
    return (s > 0) & ((s - m).abs() <= 3 * sd)
MilOK, EngOK, HPOK = okflag(d.Mileage_kmpl), okflag(d.Engine_CC), okflag(d.Horsepower)
Unk = (FuelC == 'Unknown') | (d.Transmission == 'Unknown') | (d.Color == 'Unknown') | (d.City == 'Unknown')
MODELS = sorted(raw.Model.unique()) if NARG == 'all' else sorted(pd.read_pickle('raw.pkl').Model.unique())
FUELS = ['CNG', 'Diesel', 'Electric', 'Hybrid', 'Petrol', 'Unknown']; TRANS = ['Automatic', 'Manual', 'Unknown']
OWN = ['First', 'Second', 'Third', 'Fourth+']; COLS = ['Black', 'Blue', 'Brown', 'Grey', 'Red', 'Silver', 'White', 'Unknown']
CITY = ['Ahmedabad', 'Bangalore', 'Chennai', 'Delhi', 'Hyderabad', 'Kolkata', 'Mumbai', 'Pune', 'Unknown']; DOORS = [2, 4, 5]; SEATS = [2, 4, 5, 7]
BRANDS = sorted(pd.read_pickle('raw.pkl').Brand.str.strip().unique())
idx = lambda s, lst: s.map({v: i for i, v in enumerate(lst)}).astype(np.int64)
Key = idx(d.Model, MODELS)
for part, rad in [((d.Year - 2000).astype(np.int64), 25), (idx(FuelC, FUELS), 6), (idx(d.Transmission, TRANS), 3), (idx(d.Owner_Type, OWN), 4), (idx(d.Color, COLS), 8),
                  (idx(d.City, CITY), 9), (d.Insurance_Valid.astype(np.int64), 2), (d.Service_History.astype(np.int64), 2), (d.Accidents.astype(np.int64), 6),
                  (d.Tax_Paid.astype(np.int64), 2), (idx(d.Number_of_Doors.astype(int), DOORS), 3), (idx(d.Seats.astype(int), SEATS), 4)]:
    Key = Key * rad + part
# ------------------------------------------------------------------ workbook skeleton
wb = Workbook(); wsS = wb.active; wsS.title = 'Steps'
wsD = wb.create_sheet('Dataset'); wsDATA = wb.create_sheet('DATA'); wsL = wb.create_sheet('Lists'); wsN = wb.create_sheet('Notes')
wsSum = wb.create_sheet('Summary'); wsM = wb.create_sheet('Mode_Bins'); wsC = wb.create_sheet('Correlations'); wsG = wb.create_sheet('Segment_Compare'); wsCS = wb.create_sheet('Category_Shares')
wsA = wb.create_sheet('Age_Profile'); wsK = wb.create_sheet('Km_Deciles'); wsSu = wb.create_sheet('Surface'); wsDup = wb.create_sheet('Dup_Check')
wsDS = wb.create_sheet('Dup_Sorted'); wsDS['A1'] = 'placeholder'
wsP = wb.create_sheet('Plot_Sample'); wsSe = wb.create_sheet('Sensitivity'); wsCh = wb.create_sheet('Charts')
wsDATA['A1'] = 'placeholder'

# Dataset sheet (copied text, B6 unchanged)
sst = json.load(open('dataset_sheet.json'))
for ref, txt in sst.items():
    wsD[ref] = txt; wsD[ref].alignment = Alignment(wrap_text=True, vertical='top'); wsD[ref].font = FB if ref == 'B3' else F
    r = int(ref[1:]); wsD.merge_cells(f'B{r}:S{r}')
for r, h in {3: 20, 4: 82, 5: 322, 6: 32, 7: 32}.items(): wsD.row_dimensions[r].height = h

# ------------------------------------------------------------------ Lists
wsL['A1'] = 'Lookup lists used by the helper columns on DATA'; wsL['A1'].font = FT
head(wsL, 2, 1, ['Fuel label (lower case, trimmed)', 'Fuel_Clean'])
for i, (a, b) in enumerate(fuel_map.items()): wsL.cell(3 + i, 1, a).font = FI; wsL.cell(3 + i, 2, b).font = FI
LISTS = [('D', 'Model', MODELS), ('F', 'Fuel_Clean', FUELS), ('G', 'Transmission', TRANS), ('H', 'Owner_Type', OWN), ('I', 'Color', COLS), ('J', 'City', CITY),
         ('K', 'Number_of_Doors', DOORS), ('L', 'Seats', SEATS), ('N', 'Brand_Clean', BRANDS)]
LREF = {}
for col, name, vals in LISTS:
    ci = wsL[col + '1'].column; head(wsL, 2, ci, [name])
    for i, v in enumerate(vals): wsL.cell(3 + i, ci, v).font = F
    LREF[name] = f"Lists!${col}$3:${col}${2 + len(vals)}"
head(wsL, 2, 15, ['Segment']);
for i, b in enumerate(BRANDS): put(wsL, f'O{3+i}', f'=IF(OR(N{3+i}="Audi",N{3+i}="BMW",N{3+i}="Mercedes"),"Luxury","Non-luxury")')
widths(wsL, {'A': 30, 'B': 12, 'D': 12, 'F': 12, 'G': 13, 'H': 12, 'I': 10, 'J': 12, 'K': 16, 'L': 8, 'N': 13, 'O': 12})

# ------------------------------------------------------------------ Notes (parameters, thresholds, cleaning log)
wsN['A1'] = 'Parameters, thresholds and cleaning log'; wsN['A1'].font = FT
wsN['A3'] = 'Input'; wsN['A3'].font = FB
wsN['B4'] = 'Kms_Driven cap for usage analysis (km)'; put(wsN, 'C4', CAP, '#,##0', FI); wsN['C4'].fill = INP
wsN['D4'] = 'Example of implausible values in the assessment guide (p. 7): more than 1,000,000 km'; wsN['D4'].font = FN
wsN['B5'] = 'Number of records'; put(wsN, 'C5', f'=COUNT({C["Price"]})', '#,##0')
head(wsN, 7, 2, ['Technical field', 'Mean (values > 0)', 'SD (values > 0)', 'Lower limit (mean − 3 SD)', 'Upper limit (mean + 3 SD)', 'Zero values', 'Non-zero values outside limits', 'Flag column on DATA'])
for i, (lab, col, flag) in enumerate([('Mileage_kmpl', 'Mil', 'Y'), ('Engine_CC', 'Eng', 'Z'), ('Horsepower', 'HP', 'AA')]):
    r = 8 + i; wsN[f'B{r}'] = lab
    put(wsN, f'C{r}', f'=AVERAGEIF({C[col]},">0")', '#,##0.000')
    put(wsN, f'D{r}', f'=_xlfn.STDEV.S(IF({C[col]}>0,{C[col]}))', '#,##0.000', arr=True)
    put(wsN, f'E{r}', f'=C{r}-3*D{r}', '#,##0.00'); put(wsN, f'F{r}', f'=C{r}+3*D{r}', '#,##0.00')
    put(wsN, f'G{r}', f'=COUNTIF({C[col]},0)', '#,##0')
    put(wsN, f'H{r}', f'=COUNTIFS({C[col]},">0",{C[col]},"<"&E{r})+COUNTIF({C[col]},">"&F{r})', '#,##0')
    wsN[f'I{r}'] = f'{flag} ({lab}_OK)'
head(wsN, 13, 2, ['Check', 'Result', 'How it is calculated', 'Treatment'])
LOG = [
 ('Brand labels changed by TRIM', f'=SUMPRODUCT(--NOT(EXACT({C["Brand"]},{C["BrandC"]})))', 'EXACT compares raw Brand with Brand_Clean (column U)', 'Use Brand_Clean for all brand and segment work'),
 ('  of which luxury brands', f'=SUMPRODUCT(NOT(EXACT({C["Brand"]},{C["BrandC"]}))*({C["Seg"]}="Luxury"))', 'Changed labels that belong to Audi, BMW or Mercedes', 'Would be misclassified without cleaning'),
 ('Fuel_Type labels changed', f'=SUMPRODUCT(--NOT(EXACT({C["Fuel"]},{C["FuelC"]})))', 'EXACT compares raw Fuel_Type with Fuel_Clean (column V)', 'Mapped to 5 fuel types plus Unknown (Lists A:B)'),
 ('Fuel_Type = Unknown', f'=COUNTIF({C["FuelC"]},"Unknown")', 'COUNTIF', 'Kept as its own category'),
 ('Transmission = Unknown', f'=COUNTIF({C["Trans"]},"Unknown")', 'COUNTIF', 'Kept as its own category'),
 ('Color = Unknown', f'=COUNTIF({C["Color"]},"Unknown")', 'COUNTIF', 'Kept as its own category'),
 ('City = Unknown', f'=COUNTIF({C["City"]},"Unknown")', 'COUNTIF', 'Kept as its own category'),
 ('Rows with at least one Unknown', f'=COUNTIF({C["Unk"]},TRUE)', 'Column AB', 'Kept; tested in Sensitivity'),
 ('Blank cells in A:T', f'=COUNTBLANK(DATA!$A$2:$T${L})', 'COUNTBLANK', 'No action needed'),
 ('Exact duplicates (all 20 fields)', f'=Dup_Check!$J$6', 'Car_Price has no repeated value, so no two rows can match on all 20 fields', 'No action needed'),
 ('Repeat rows on the 15 non-randomised fields', f'=Dup_Check!$J$4', 'Dup_Check: sorted Dup_Key, run length', 'Flagged, not deleted; tested in Sensitivity'),
 ('Kms_Driven above cap', f'=COUNTIF({C["KM"]},">"&$C$4)', 'COUNTIF against C4', 'Left out of usage analysis only (column X)'),
 ('Expected count above cap under a log-normal fit', '=C5*(1-_xlfn.NORM.DIST(LN($C$4),C38,C39,TRUE))', 'Uses the mean and SD of LN(Kms_Driven) in C38:C39', 'Compare with the observed count above'),
 ('Zero or outside ±3 SD: Mileage_kmpl', '=G8+H8', 'Rows 8 to 10', 'Blank for that field only (flag columns Y:AA)'),
 ('Zero or outside ±3 SD: Engine_CC', '=G9+H9', 'Rows 8 to 10', 'Blank for that field only'),
 ('Zero or outside ±3 SD: Horsepower', '=G10+H10', 'Rows 8 to 10', 'Blank for that field only'),
 ('Car_Price below log-scale 3×IQR fence', f'=COUNTIF({C["Price"]},"<"&EXP(C41-3*(C42-C41)))', 'Quartiles of LN(price) in C41:C42', 'Kept; consistent with a long right tail'),
 ('Car_Price above log-scale 3×IQR fence', f'=COUNTIF({C["Price"]},">"&EXP(C42+3*(C42-C41)))', 'Quartiles of LN(price) in C41:C42', 'Kept'),
 ('Rows where Year + Registration_Age = 2025', f'=SUMPRODUCT(--({C["Year"]}+{C["Age"]}=2025))', 'SUMPRODUCT', 'Age used as supplied'),
 ('Luxury records', f'=COUNTIF({C["Seg"]},"Luxury")', 'Column W', ''),
 ('Non-luxury records', f'=COUNTIF({C["Seg"]},"Non-luxury")', 'Column W', ''),
 ('Records used for usage analysis', f'=COUNTIF({C["KMOK"]},TRUE)', 'Column X', ''),
]
for i, (a, f_, how, tr) in enumerate(LOG):
    r = 14 + i; wsN[f'B{r}'] = a; put(wsN, f'C{r}', f_, '#,##0'); wsN[f'D{r}'] = how; wsN[f'E{r}'] = tr
for c_ in 'BDE':
    for r in range(14, 14 + len(LOG)): wsN[f'{c_}{r}'].font = F
wsN['B37'] = 'Log-scale helpers'; wsN['B37'].font = FB
wsN['B38'] = 'Mean of LN(Kms_Driven)'; put(wsN, 'C38', f'=AVERAGE(LN({C["KM"]}))', '0.0000', arr=True)
wsN['B39'] = 'SD of LN(Kms_Driven)'; put(wsN, 'C39', f'=_xlfn.STDEV.S(LN({C["KM"]}))', '0.0000', arr=True)
wsN['B40'] = 'Skewness of LN(Kms_Driven)'; put(wsN, 'C40', f'=SKEW(LN({C["KM"]}))', '0.0000', arr=True)
wsN['B41'] = 'Q1 of LN(Car_Price)'; put(wsN, 'C41', f'=QUARTILE(LN({C["Price"]}),1)', '0.0000', arr=True)
wsN['B42'] = 'Q3 of LN(Car_Price)'; put(wsN, 'C42', f'=QUARTILE(LN({C["Price"]}),3)', '0.0000', arr=True)
wsN['B43'] = 'Skewness of LN(Car_Price)'; put(wsN, 'C43', f'=SKEW(LN({C["Price"]}))', '0.0000', arr=True)
wsN['B45'] = 'Further checks'; wsN['B45'].font = FB
head(wsN, 46, 2, ['Check', 'Result', 'How it is calculated', 'Treatment'])
EXTRA = [
 ('Largest Kms_Driven before the cap', f'=MAX({C["KM"]})', 'MAX', 'Above the cap; left out of usage analysis'),
 ('Model labels with extra spaces', f'=SUMPRODUCT(--(LEN({C["Model"]})<>LEN(TRIM({C["Model"]}))))', 'LEN against LEN(TRIM())', 'None found; 39 models, each with one brand (Lists)'),
 ('Transmission labels with extra spaces', f'=SUMPRODUCT(--(LEN({C["Trans"]})<>LEN(TRIM({C["Trans"]}))))', 'LEN against LEN(TRIM())', 'None found; 3 labels'),
 ('Owner_Type labels with extra spaces', f'=SUMPRODUCT(--(LEN({C["Owner"]})<>LEN(TRIM({C["Owner"]}))))', 'LEN against LEN(TRIM())', 'None found; 4 labels'),
 ('Color labels with extra spaces', f'=SUMPRODUCT(--(LEN({C["Color"]})<>LEN(TRIM({C["Color"]}))))', 'LEN against LEN(TRIM())', 'None found; 8 labels'),
 ('City labels with extra spaces', f'=SUMPRODUCT(--(LEN({C["City"]})<>LEN(TRIM({C["City"]}))))', 'LEN against LEN(TRIM())', 'None found; 9 labels'),
 ('Horsepower below 50 hp that passes the ±3 SD rule', f'=COUNTIFS({C["HPOK"]},TRUE,{C["HP"]},"<50")', 'COUNTIFS with flag AA', 'Implausible for a car; kept (too few to move any median)'),
 ('Engine_CC below 850 cc that passes the ±3 SD rule', f'=COUNTIFS({C["EngOK"]},TRUE,{C["Eng"]},"<850")', 'COUNTIFS with flag Z', 'Implausible for most cars; kept'),
 ('Car_Price below INR 20,000', f'=COUNTIF({C["Price"]},"<20000")', 'COUNTIF', 'Very low for a car; kept'),
 ('Horsepower above 190 hp that passes the ±3 SD rule', f'=COUNTIFS({C["HPOK"]},TRUE,{C["HP"]},">190")', 'COUNTIFS with flag AA', 'Isolated above the main range; kept'),
 ('Engine_CC above 2,250 cc that passes the ±3 SD rule', f'=COUNTIFS({C["EngOK"]},TRUE,{C["Eng"]},">2250")', 'COUNTIFS with flag Z', 'Isolated above the main range; kept'),
 ('Mileage_kmpl below 11 km/l that passes the ±3 SD rule', f'=COUNTIFS({C["MilOK"]},TRUE,{C["Mil"]},"<11")', 'COUNTIFS with flag Y', 'Isolated below the main range; kept'),
 ('Mileage_kmpl above 25.5 km/l that passes the ±3 SD rule', f'=COUNTIFS({C["MilOK"]},TRUE,{C["Mil"]},">25.5")', 'COUNTIFS with flag Y', 'Isolated above the main range; kept'),
 ('Largest raw Engine_CC', f'=MAX({C["Eng"]})', 'MAX', 'Beyond mean + 3 SD; blank for that field'),
 ('Largest raw Horsepower', f'=MAX({C["HP"]})', 'MAX', 'Beyond mean + 3 SD; blank for that field'),
 ('Largest raw Mileage_kmpl', f'=MAX({C["Mil"]})', 'MAX', 'Beyond mean + 3 SD; blank for that field'),
 ('Smallest Horsepower kept', f'=MIN(IF({C["HPOK"]},{C["HP"]}))', 'MIN of flagged values', ''),
]
for i, (a, f_, how, tr) in enumerate(EXTRA):
    r = 47 + i; wsN[f'B{r}'] = a; put(wsN, f'C{r}', f_, '#,##0.0' if f_.startswith(('=MIN(IF', '=MAX(')) else '#,##0', arr=f_.startswith('=MIN(IF')); wsN[f'D{r}'] = how; wsN[f'E{r}'] = tr
    for c_ in 'BDE': wsN[f'{c_}{r}'].font = F
widths(wsN, {'A': 3, 'B': 46, 'C': 16, 'D': 52, 'E': 44, 'F': 16, 'G': 12, 'H': 16, 'I': 22})

# ------------------------------------------------------------------ Mode_Bins (frequency tables -> modal class; also Figure 1 histogram)
wsM['A1'] = 'Frequency tables used for modal classes (continuous variables) and the price histogram'; wsM['A1'].font = FT
BINS = [('Car_Price', 'Price', None, 0, 50000, 100), ('Kms_Driven', 'KM', 'KMOK', 0, 10000, 60), ('Engine_CC', 'Eng', 'EngOK', 600, 50, 40),
        ('Horsepower', 'HP', 'HPOK', 40, 5, 36), ('Mileage_kmpl', 'Mil', 'MilOK', 8, 0.5, 40)]
MODEREF = {}
col0 = 1
for lab, v, flag, start, w, nb in BINS:
    c1 = get_column_letter(col0); c2 = get_column_letter(col0 + 1); c3, c4, c5 = [get_column_letter(col0 + k) for k in (2, 3, 4)]
    wsM[f'{c1}3'] = f'{lab} (bin width {w:g})'; wsM[f'{c1}3'].font = FB
    head(wsM, 4, col0, ['Bin from', 'Bin to', 'All', 'Luxury', 'Non-luxury'])
    fl = f',{C[flag]},TRUE' if flag else ''
    for i in range(nb):
        r = 5 + i
        put(wsM, f'{c1}{r}', start + i * w if i == 0 else f'={c2}{r-1}', '#,##0.##')
        put(wsM, f'{c2}{r}', f'={c1}{r}+{w}', '#,##0.##')
        put(wsM, f'{c3}{r}', f'=COUNTIFS({C[v]},">="&{c1}{r},{C[v]},"<"&{c2}{r}{fl})', '#,##0')
        put(wsM, f'{c4}{r}', f'=COUNTIFS({C[v]},">="&{c1}{r},{C[v]},"<"&{c2}{r},{C["Seg"]},"Luxury"{fl})', '#,##0')
        put(wsM, f'{c5}{r}', f'=COUNTIFS({C[v]},">="&{c1}{r},{C[v]},"<"&{c2}{r},{C["Seg"]},"Non-luxury"{fl})', '#,##0')
    re_ = 5 + nb - 1; rm = re_ + 2
    wsM[f'{c1}{rm}'] = 'Modal class midpoint'; wsM[f'{c1}{rm}'].font = FB
    for cc, g in [(c3, 'All'), (c4, 'Luxury'), (c5, 'Non-luxury')]:
        put(wsM, f'{cc}{rm}', f'=INDEX(${c1}$5:${c1}${re_},MATCH(MAX({cc}5:{cc}{re_}),{cc}5:{cc}{re_},0))+{w}/2', '#,##0.##', FB)
        MODEREF[(v, g)] = f"Mode_Bins!${cc}${rm}"
    for k in range(5): wsM.column_dimensions[get_column_letter(col0 + k)].width = 11
    col0 += 6
PRICE_HIST = ('A', 'C', 5, 104)

# ------------------------------------------------------------------ Summary (Table 2)
wsSum['A1'] = 'Numerical summaries by group (report Table 2)'; wsSum['A1'].font = FT
wsSum['A2'] = 'Every cell is a formula on sheet DATA. Arrays such as MEDIAN(IF(...)) are entered with Ctrl+Shift+Enter (Cmd+Shift+Enter on Mac).'; wsSum['A2'].font = FN
wsSum['A3'] = 'Mode: MODE.SNGL for Registration_Age and Accidents. Continuous variables have no repeated exact value (Car_Price: Dup_Check!J6 = 0), so their mode is the midpoint of the most frequent class on Mode_Bins (modal class).'; wsSum['A3'].font = FN
head(wsSum, 4, 1, ['Variable', 'Group', 'n', 'Mean', 'Median', 'Mode (exact or modal class)', 'SD', 'Min', 'Max', 'Q1', 'Q3', 'Skewness'])
SV = [('Car_Price (INR)', 'Price', None, True), ('Registration_Age (years)', 'Age', None, False), ('Kms_Driven (km, ≤ cap)', 'KM', 'KMOK', True),
      ('Engine_CC (cc)', 'Eng', 'EngOK', True), ('Horsepower (hp)', 'HP', 'HPOK', True), ('Mileage_kmpl (km/l)', 'Mil', 'MilOK', True), ('Accidents (count)', 'Acc', None, False)]
r = 5; SUMREF = {}
for lab, v, flag, cont in SV:
    for g in ['All', 'Luxury', 'Non-luxury']:
        conds = []
        if g != 'All': conds.append(f'({C["Seg"]}="{g}")')
        if flag: conds.append(f'({C[flag]}=TRUE)')
        cond = '*'.join(conds)
        x = C[v]; arr = f'IF({cond},{x})' if cond else x
        ifs = ''.join([f',{C["Seg"]},"{g}"' if g != 'All' else '', f',{C[flag]},TRUE' if flag else ''])
        wsSum[f'A{r}'] = lab if g == 'All' else ''; wsSum[f'A{r}'].font = FB; wsSum[f'B{r}'] = g
        fm = '#,##0' if v in ('Price', 'KM', 'Eng') else ('#,##0.00' if v in ('Mil', 'Acc') else '#,##0.0')
        put(wsSum, f'C{r}', f'=COUNTIFS({x},"<>"{ifs})' if ifs else f'=COUNT({x})', '#,##0')
        put(wsSum, f'D{r}', f'=AVERAGEIFS({x},{x},"<>"{ifs})' if ifs else f'=AVERAGE({x})', fm)
        put(wsSum, f'E{r}', f'=MEDIAN({arr})', fm, arr=bool(cond))
        if cont: put(wsSum, f'F{r}', f'={MODEREF[(v, g)]}', fm)
        else: put(wsSum, f'F{r}', f'=_xlfn.MODE.SNGL({arr})', fm, arr=bool(cond))
        put(wsSum, f'G{r}', f'=_xlfn.STDEV.S({arr})', fm, arr=bool(cond))
        put(wsSum, f'H{r}', f'=MIN({arr})', fm, arr=bool(cond)); put(wsSum, f'I{r}', f'=MAX({arr})', fm, arr=bool(cond))
        put(wsSum, f'J{r}', f'=_xlfn.PERCENTILE.INC({arr},0.25)', fm, arr=True); put(wsSum, f'K{r}', f'=_xlfn.PERCENTILE.INC({arr},0.75)', fm, arr=True)
        put(wsSum, f'L{r}', f'=SKEW({arr})', '0.000', arr=True)
        SUMREF[(v, g)] = r; r += 1
r += 1; wsSum[f'A{r}'] = 'Shares of binary and categorical fields (%)'; wsSum[f'A{r}'].font = FB; r += 1
head(wsSum, r, 1, ['Field', 'Value', 'All', 'Luxury', 'Non-luxury']); r += 1
for lab, v, val in [('Insurance_Valid', 'Ins', 1), ('Service_History', 'Svc', 1), ('Tax_Paid', 'Tax', 1), ('Owner_Type', 'Owner', '"First"'), ('Transmission', 'Trans', '"Automatic"')]:
    wsSum[f'A{r}'] = lab; wsSum[f'B{r}'] = str(val).strip('"')
    put(wsSum, f'C{r}', f'=COUNTIF({C[v]},{val})/COUNT({C["Price"]})', '0.0%')
    put(wsSum, f'D{r}', f'=COUNTIFS({C[v]},{val},{C["Seg"]},"Luxury")/COUNTIF({C["Seg"]},"Luxury")', '0.0%')
    put(wsSum, f'E{r}', f'=COUNTIFS({C[v]},{val},{C["Seg"]},"Non-luxury")/COUNTIF({C["Seg"]},"Non-luxury")', '0.0%'); r += 1
r += 1; wsSum[f'A{r}'] = 'Price distribution checks'; wsSum[f'A{r}'].font = FB; r += 1
PD = {}
for lab, f_ in [('Mean above median (%)', f'=D{SUMREF[("Price","All")]}/E{SUMREF[("Price","All")]}-1'),
                ('Share of listings below the mean', f'=COUNTIF({C["Price"]},"<"&D{SUMREF[("Price","All")]})/C{SUMREF[("Price","All")]}'),
                ('Skewness of LN(Car_Price)', '=Notes!C43'), ('Geometric mean (EXP of mean LN price)', f'=EXP(AVERAGE(LN({C["Price"]})))'),
                ('Share of listings above INR 5,000,000', f'=COUNTIF({C["Price"]},">5000000")/COUNT({C["Price"]})')]:
    wsSum[f'A{r}'] = lab; put(wsSum, f'C{r}', f_, '0.0%' if '%' in lab or 'Share' in lab else '#,##0.000', arr=('LN(' in f_ and 'Notes' not in f_)); PD[lab] = r; r += 1
widths(wsSum, {'A': 26, 'B': 12, 'C': 11, 'D': 13, 'E': 13, 'F': 12, 'G': 13, 'H': 11, 'I': 13, 'J': 12, 'K': 13, 'L': 10})
wsSum.freeze_panes = 'C5'

# ------------------------------------------------------------------ Correlations
wsC['A1'] = 'Correlation of Car_Price with the other numeric fields (Pearson r, same rows on both sides)'; wsC['A1'].font = FT
head(wsC, 3, 1, ['Field', 'Rows used', 'All', 'Luxury', 'Non-luxury'])
CV = [('Registration_Age', 'Age', None), ('Year', 'Year', None), ('Kms_Driven (≤ cap)', 'KM', 'KMOK'), ('Mileage_kmpl', 'Mil', 'MilOK'), ('Engine_CC', 'Eng', 'EngOK'),
      ('Horsepower', 'HP', 'HPOK'), ('Accidents', 'Acc', None), ('Insurance_Valid', 'Ins', None), ('Service_History', 'Svc', None), ('Tax_Paid', 'Tax', None),
      ('Number_of_Doors', 'Doors', None), ('Seats', 'Seats', None)]
CORRREF = {}
for i, (lab, v, flag) in enumerate(CV):
    r = 4 + i; wsC[f'A{r}'] = lab; wsC[f'B{r}'] = 'flag ' + {'KMOK': 'X', 'MilOK': 'Y', 'EngOK': 'Z', 'HPOK': 'AA'}[flag] + ' = TRUE' if flag else 'all'
    for col, g in [('C', 'All'), ('D', 'Luxury'), ('E', 'Non-luxury')]:
        conds = ([f'({C["Seg"]}="{g}")'] if g != 'All' else []) + ([f'({C[flag]}=TRUE)'] if flag else [])
        cond = '*'.join(conds)
        f_ = f'=CORREL(IF({cond},{C[v]}),IF({cond},{C["Price"]}))' if cond else f'=CORREL({C[v]},{C["Price"]})'
        put(wsC, f'{col}{r}', f_, '+0.0000;-0.0000;0.0000', arr=bool(cond)); CORRREF[(v, g)] = f'Correlations!${col}${r}'
r = 18; wsC[f'A{r}'] = 'Usage on a log scale (rows with KM_OK = TRUE)'; wsC[f'A{r}'].font = FB
K = C['KMOK']
LOGM = [('r between LN(Kms_Driven) and LN(Car_Price)', f'=CORREL(IF({K},LN({C["KM"]})),IF({K},LN({C["Price"]})))', '+0.0000;-0.0000'),
        ('Slope of LN(price) on LN(km) (elasticity)', f'=SLOPE(IF({K},LN({C["Price"]})),IF({K},LN({C["KM"]})))', '0.0000'),
        ('Intercept', f'=INTERCEPT(IF({K},LN({C["Price"]})),IF({K},LN({C["KM"]})))', '0.0000'),
        ('R squared', f'=RSQ(IF({K},LN({C["Price"]})),IF({K},LN({C["KM"]})))', '0.0000'),
        ('Price change for +10% km', '=1.1^B20-1', '0.00%'),
        ('Typical error of the km model (median absolute % error)', f'=MEDIAN(IF({K},ABS({C["Price"]}-EXP(B21+B20*LN({C["KM"]})))/{C["Price"]}))', '0.00%'),
        ('Typical error of quoting the overall median price', f'=MEDIAN(ABS({C["Price"]}-MEDIAN({C["Price"]}))/{C["Price"]})', '0.00%')]
for i, (lab, f_, fm) in enumerate(LOGM):
    rr = 19 + i; wsC[f'A{rr}'] = lab; put(wsC, f'B{rr}', f_, fm, arr=('IF(' in f_ or 'MEDIAN(ABS' in f_))
r = 28; wsC[f'A{r}'] = 'Sensitivity of the price–km correlation to the km cap'; wsC[f'A{r}'].font = FB
head(wsC, 29, 1, ['Cap (km)', 'Rows kept', 'r (raw values)', 'r (log–log)'])
for i, cap in enumerate([500000, 750000, 1000000, 1500000, None]):
    rr = 30 + i
    if cap is None:
        wsC[f'A{rr}'] = 'No cap'; put(wsC, f'B{rr}', f'=COUNT({C["KM"]})', '#,##0'); put(wsC, f'C{rr}', f'=CORREL({C["KM"]},{C["Price"]})', '+0.0000;-0.0000')
        put(wsC, f'D{rr}', f'=CORREL(LN({C["KM"]}),LN({C["Price"]}))', '+0.0000;-0.0000', arr=True)
    else:
        put(wsC, f'A{rr}', cap, '#,##0', FI); put(wsC, f'B{rr}', f'=COUNTIF({C["KM"]},"<="&A{rr})', '#,##0')
        cond = f'{C["KM"]}<=A{rr}'
        put(wsC, f'C{rr}', f'=CORREL(IF({cond},{C["KM"]}),IF({cond},{C["Price"]}))', '+0.0000;-0.0000', arr=True)
        put(wsC, f'D{rr}', f'=CORREL(IF({cond},LN({C["KM"]})),IF({cond},LN({C["Price"]})))', '+0.0000;-0.0000', arr=True)
r = 37; wsC[f'A{r}'] = 'How far a 5,000-row sample can move r (normal approximation, SE = (1 − r²)/√(n − 1))'; wsC[f'A{r}'].font = FB
head(wsC, 38, 1, ['Relationship', 'Full-data r', 'Sample size', 'SE of r', '95% low', '95% high', 'r in the plotted sample'])
for i, (lab, ref, sref) in enumerate([('Price and age', CORRREF[('Age', 'All')], 'Plot_Sample!$O$5'), ('Price and km (≤ cap)', CORRREF[('KM', 'All')], 'Plot_Sample!$O$6')]):
    rr = 39 + i; wsC[f'A{rr}'] = lab; put(wsC, f'B{rr}', f'={ref}', '+0.0000;-0.0000'); put(wsC, f'C{rr}', 5000, '#,##0', FI)
    put(wsC, f'D{rr}', f'=(1-B{rr}^2)/SQRT(C{rr}-1)', '0.0000'); put(wsC, f'E{rr}', f'=B{rr}-1.96*D{rr}', '+0.0000;-0.0000'); put(wsC, f'F{rr}', f'=B{rr}+1.96*D{rr}', '+0.0000;-0.0000')
    put(wsC, f'G{rr}', f'={sref}', '+0.0000;-0.0000')
wsC['A43'] = 'Correlation between Engine_CC and Horsepower (rows with both flags Z and AA = TRUE)'; wsC['A43'].font = FB
put(wsC, 'B43', f'=CORREL(IF(({C["EngOK"]})*({C["HPOK"]}),{C["Eng"]}),IF(({C["EngOK"]})*({C["HPOK"]}),{C["HP"]}))', '0.000', FB, arr=True)
widths(wsC, {'A': 52, 'B': 14, 'C': 14, 'D': 12, 'E': 12, 'F': 12, 'G': 20})

# ------------------------------------------------------------------ Segment_Compare
g_ = wsG; g_['A1'] = 'Luxury vs non-luxury, brands and categories'; g_['A1'].font = FT
head(g_, 3, 1, ['Measure', 'Luxury', 'Non-luxury', 'Difference', 'Difference (%)'])
pl, pn = SUMREF[('Price', 'Luxury')], SUMREF[('Price', 'Non-luxury')]
for i, (lab, cl) in enumerate([('Mean Car_Price', 'D'), ('Median Car_Price', 'E'), ('SD Car_Price', 'G'), ('Q1', 'J'), ('Q3', 'K')]):
    rr = 4 + i; g_[f'A{rr}'] = lab; put(g_, f'B{rr}', f'=Summary!{cl}{pl}', '#,##0'); put(g_, f'C{rr}', f'=Summary!{cl}{pn}', '#,##0')
    put(g_, f'D{rr}', f'=B{rr}-C{rr}', '#,##0'); put(g_, f'E{rr}', f'=B{rr}/C{rr}-1', '0.00%')
head(g_, 3, 7, ['Segment', 'n', 'Median 95% CI low', 'Median 95% CI high'])
for i, (sg, sr) in enumerate([('Luxury', pl), ('Non-luxury', pn)]):
    rr = 4 + i; g_[f'G{rr}'] = sg; put(g_, f'H{rr}', f'=Summary!C{sr}', '#,##0')
    put(g_, f'I{rr}', f'=SMALL(IF({C["Seg"]}=G{rr},{C["Price"]}),INT(H{rr}/2-1.96*SQRT(H{rr})/2)+1)', '#,##0', arr=True)
    put(g_, f'J{rr}', f'=SMALL(IF({C["Seg"]}=G{rr},{C["Price"]}),INT(H{rr}/2+1.96*SQRT(H{rr})/2)+1)', '#,##0', arr=True)
g_['G6'] = 'Order-statistic interval: ranks n/2 ± 1.96√n/2 of the sorted prices.'; g_['G6'].font = FN
g_['A10'] = '95% confidence interval for the difference in means (Welch standard error)'; g_['A10'].font = FB
put(g_, 'B11', f'=SQRT(Summary!G{pl}^2/Summary!C{pl}+Summary!G{pn}^2/Summary!C{pn})', '#,##0'); g_['A11'] = 'Standard error of the difference (INR)'
g_['A12'] = 'Lower limit (INR)'; put(g_, 'B12', '=D4-1.96*B11', '#,##0'); put(g_, 'C12', '=B12/C4', '0.00%')
g_['A13'] = 'Upper limit (INR)'; put(g_, 'B13', '=D4+1.96*B11', '#,##0'); put(g_, 'C13', '=B13/C4', '0.00%')
g_['A14'] = 'Welch t statistic'; put(g_, 'B14', '=D4/B11', '0.000')
head(g_, 16, 1, ['Brand_Clean', 'Segment', 'n', 'Mean', 'Median', 'Median vs overall median', 'Median 95% CI low', 'Median 95% CI high'])
for i, b in enumerate(BRANDS):
    rr = 17 + i; g_[f'A{rr}'] = b; put(g_, f'B{rr}', f'=INDEX(Lists!$O$3:$O$15,MATCH(A{rr},Lists!$N$3:$N$15,0))')
    put(g_, f'C{rr}', f'=COUNTIF({C["BrandC"]},A{rr})', '#,##0'); put(g_, f'D{rr}', f'=AVERAGEIF({C["BrandC"]},A{rr},{C["Price"]})', '#,##0')
    put(g_, f'E{rr}', f'=MEDIAN(IF({C["BrandC"]}=A{rr},{C["Price"]}))', '#,##0', arr=True); put(g_, f'F{rr}', f'=E{rr}/Summary!$E${SUMREF[("Price","All")]}-1', '+0.00%;-0.00%')
    put(g_, f'G{rr}', f'=SMALL(IF({C["BrandC"]}=A{rr},{C["Price"]}),INT(C{rr}/2-1.96*SQRT(C{rr})/2)+1)', '#,##0', arr=True)
    put(g_, f'H{rr}', f'=SMALL(IF({C["BrandC"]}=A{rr},{C["Price"]}),INT(C{rr}/2+1.96*SQRT(C{rr})/2)+1)', '#,##0', arr=True)
rb = 17 + len(BRANDS); g_[f'A{rb}'] = 'Spread of brand medians (max/min − 1)'; put(g_, f'E{rb}', f'=MAX(E17:E{rb-1})/MIN(E17:E{rb-1})-1', '0.00%', FB)
rr = rb + 2; g_[f'A{rr}'] = 'Median Car_Price by category'; g_[f'A{rr}'].font = FB; rr += 1
head(g_, rr, 1, ['Field', 'Category', 'n', 'Median', 'Median vs overall median']); rr += 1
CATREF = {}
for lab, v, vals in [('Fuel_Type', 'FuelC', FUELS), ('Transmission', 'Trans', TRANS), ('Owner_Type', 'Owner', OWN), ('Color', 'Color', COLS), ('City', 'City', CITY), ('Model', 'Model', MODELS)]:
    r0 = rr
    if lab == 'Model':
        head(g_, rr - 1, 6, ['Median 95% CI low', 'Median 95% CI high', 'Interval contains overall median'])
    for val in vals:
        g_[f'A{rr}'] = lab if rr == r0 else ''; g_[f'B{rr}'] = val
        put(g_, f'C{rr}', f'=COUNTIF({C[v]},B{rr})', '#,##0'); put(g_, f'D{rr}', f'=MEDIAN(IF({C[v]}=B{rr},{C["Price"]}))', '#,##0', arr=True)
        put(g_, f'E{rr}', f'=D{rr}/Summary!$E${SUMREF[("Price","All")]}-1', '+0.00%;-0.00%')
        if lab == 'Model':
            put(g_, f'F{rr}', f'=SMALL(IF({C[v]}=B{rr},{C["Price"]}),INT(C{rr}/2-1.96*SQRT(C{rr})/2)+1)', '#,##0', arr=True)
            put(g_, f'G{rr}', f'=SMALL(IF({C[v]}=B{rr},{C["Price"]}),INT(C{rr}/2+1.96*SQRT(C{rr})/2)+1)', '#,##0', arr=True)
            put(g_, f'H{rr}', f'=AND(F{rr}<=Summary!$E${SUMREF[("Price","All")]},G{rr}>=Summary!$E${SUMREF[("Price","All")]})')
        rr += 1
    g_[f'B{rr}'] = 'Spread (max/min − 1)'; put(g_, f'D{rr}', f'=MAX(D{r0}:D{rr-1})/MIN(D{r0}:D{rr-1})-1', '0.00%', FB)
    g_[f'B{rr+1}'] = 'Group size (smallest, largest)'; put(g_, f'C{rr+1}', f'=MIN(C{r0}:C{rr-1})', '#,##0'); put(g_, f'D{rr+1}', f'=MAX(C{r0}:C{rr-1})', '#,##0')
    if lab == 'Model':
        g_[f'F{rr}'] = 'Intervals containing the overall median'; put(g_, f'H{rr}', f'=COUNTIF(H{r0}:H{rr-1},TRUE)', '0', FB)
    CATREF[lab] = rr; rr += 3
widths(g_, {'A': 44, 'B': 20, 'C': 12, 'D': 13, 'E': 16, 'F': 22, 'G': 18, 'H': 18, 'I': 18, 'J': 18})

# ------------------------------------------------------------------ Category_Shares (counts and shares by segment)
cs = wsCS; cs['A1'] = 'Share of listings in each category: all, luxury and non-luxury'; cs['A1'].font = FT
cs['A2'] = 'COUNTIF / COUNTIFS on DATA. Difference = luxury share − non-luxury share, in percentage points. Brand and Model are left out of the maximum because the segments are defined by brand.'; cs['A2'].font = FN
head(cs, 4, 1, ['Field', 'Category', 'n (all)', 'Share (all)', 'n (luxury)', 'Share (luxury)', 'n (non-luxury)', 'Share (non-luxury)', 'Difference (pp)'])
rr = 5; d0 = None
for lab, v, vals in [('Fuel_Clean', 'FuelC', FUELS), ('Transmission', 'Trans', TRANS), ('Owner_Type', 'Owner', OWN), ('Color', 'Color', COLS), ('City', 'City', CITY),
                     ('Number_of_Doors', 'Doors', DOORS), ('Seats', 'Seats', SEATS), ('Accidents', 'Acc', [0, 1, 2, 3, 4, 5]), ('Insurance_Valid', 'Ins', [0, 1]),
                     ('Service_History', 'Svc', [0, 1]), ('Tax_Paid', 'Tax', [0, 1]), ('Brand_Clean', 'BrandC', BRANDS)]:
    r0 = rr
    for val in vals:
        cs[f'A{rr}'] = lab if rr == r0 else ''; cs[f'B{rr}'] = val
        put(cs, f'C{rr}', f'=COUNTIF({C[v]},B{rr})', '#,##0'); put(cs, f'D{rr}', f'=C{rr}/Notes!$C$5', '0.0%')
        put(cs, f'E{rr}', f'=COUNTIFS({C[v]},B{rr},{C["Seg"]},"Luxury")', '#,##0'); put(cs, f'F{rr}', f'=E{rr}/COUNTIF({C["Seg"]},"Luxury")', '0.0%')
        put(cs, f'G{rr}', f'=COUNTIFS({C[v]},B{rr},{C["Seg"]},"Non-luxury")', '#,##0'); put(cs, f'H{rr}', f'=G{rr}/COUNTIF({C["Seg"]},"Non-luxury")', '0.0%')
        put(cs, f'I{rr}', f'=(F{rr}-H{rr})*100', '+0.00;-0.00'); rr += 1
    if lab == 'Tax_Paid': d0 = rr - 1
    rr += 1
cs[f'A{rr}'] = 'Largest difference between segments, excluding Brand (pp)'; cs[f'A{rr}'].font = FB
put(cs, f'I{rr}', f'=MAX(ABS(MAX(I5:I{d0})),ABS(MIN(I5:I{d0})))', '0.00', FB)
widths(cs, {'A': 20, 'B': 14, 'C': 11, 'D': 11, 'E': 11, 'F': 13, 'G': 13, 'H': 16, 'I': 15})

# ------------------------------------------------------------------ Age_Profile
a_ = wsA; a_['A1'] = 'Car_Price by Registration_Age (all rows)'; a_['A1'].font = FT
head(a_, 3, 1, ['Age (years)', 'n', 'Q1 (all)', 'Median (all)', 'Q3 (all)', 'Median luxury', 'Median non-luxury', 'Mean (all)'])
for i, age in enumerate(range(1, 26)):
    rr = 4 + i; put(a_, f'A{rr}', age); cA = f'{C["Age"]}=A{rr}'
    put(a_, f'B{rr}', f'=COUNTIF({C["Age"]},A{rr})', '#,##0')
    put(a_, f'C{rr}', f'=_xlfn.PERCENTILE.INC(IF({cA},{C["Price"]}),0.25)', '#,##0', arr=True)
    put(a_, f'D{rr}', f'=MEDIAN(IF({cA},{C["Price"]}))', '#,##0', arr=True)
    put(a_, f'E{rr}', f'=_xlfn.PERCENTILE.INC(IF({cA},{C["Price"]}),0.75)', '#,##0', arr=True)
    put(a_, f'F{rr}', f'=MEDIAN(IF(({cA})*({C["Seg"]}="Luxury"),{C["Price"]}))', '#,##0', arr=True)
    put(a_, f'G{rr}', f'=MEDIAN(IF(({cA})*({C["Seg"]}="Non-luxury"),{C["Price"]}))', '#,##0', arr=True)
    put(a_, f'H{rr}', f'=AVERAGEIF({C["Age"]},A{rr},{C["Price"]})', '#,##0')
a_['A30'] = 'Range of the all-row medians (max/min − 1)'; put(a_, 'D30', '=MAX(D4:D28)/MIN(D4:D28)-1', '0.00%', FB)
a_['A31'] = 'Lowest median'; put(a_, 'D31', '=MIN(D4:D28)', '#,##0'); put(a_, 'F31', '=MIN(F4:F28)', '#,##0'); put(a_, 'G31', '=MIN(G4:G28)', '#,##0')
a_['A32'] = 'Highest median'; put(a_, 'D32', '=MAX(D4:D28)', '#,##0'); put(a_, 'F32', '=MAX(F4:F28)', '#,##0'); put(a_, 'G32', '=MAX(G4:G28)', '#,##0')
widths(a_, {'A': 12, 'B': 10, 'C': 12, 'D': 13, 'E': 12, 'F': 15, 'G': 18, 'H': 12})

# ------------------------------------------------------------------ Km_Deciles
k_ = wsK; k_['A1'] = 'Car_Price by Kms_Driven decile (rows with KM_OK = TRUE)'; k_['A1'].font = FT
head(k_, 3, 1, ['Decile', 'Km from (exclusive)', 'Km to (inclusive)', 'n', 'Q1 (all)', 'Median (all)', 'Q3 (all)', 'Median luxury', 'Median non-luxury'])
for dd in range(1, 11):
    rr = 3 + dd; k_[f'A{rr}'] = f'D{dd}'
    put(k_, f'B{rr}', 0 if dd == 1 else f'=C{rr-1}', '#,##0')
    put(k_, f'C{rr}', f'=_xlfn.PERCENTILE.INC(IF({K},{C["KM"]}),{dd/10})', '#,##0', arr=True) if dd < 10 else put(k_, f'C{rr}', '=Notes!$C$4', '#,##0')
    cd = f'({K})*({C["KM"]}>B{rr})*({C["KM"]}<=C{rr})'
    put(k_, f'D{rr}', f'=SUMPRODUCT({cd})', '#,##0')
    put(k_, f'E{rr}', f'=_xlfn.PERCENTILE.INC(IF({cd},{C["Price"]}),0.25)', '#,##0', arr=True)
    put(k_, f'F{rr}', f'=MEDIAN(IF({cd},{C["Price"]}))', '#,##0', arr=True)
    put(k_, f'G{rr}', f'=_xlfn.PERCENTILE.INC(IF({cd},{C["Price"]}),0.75)', '#,##0', arr=True)
    put(k_, f'H{rr}', f'=MEDIAN(IF({cd}*({C["Seg"]}="Luxury"),{C["Price"]}))', '#,##0', arr=True)
    put(k_, f'I{rr}', f'=MEDIAN(IF({cd}*({C["Seg"]}="Non-luxury"),{C["Price"]}))', '#,##0', arr=True)
k_['A15'] = 'Change in median from D1 to D10'; put(k_, 'F15', '=F13/F4-1', '0.0%', FB)
widths(k_, {'A': 32, 'B': 18, 'C': 16, 'D': 11, 'E': 12, 'F': 13, 'G': 12, 'H': 14, 'I': 17})

# ------------------------------------------------------------------ Surface (5 age bands x 10 deciles)
s_ = wsSu; s_['A1'] = 'Median Car_Price by age band and km decile (used for the 3-D surface)'; s_['A1'].font = FT
head(s_, 3, 1, ['Age from', 'Age to'] + [f'D{i}' for i in range(1, 11)])
for bi in range(5):
    rr = 4 + bi; put(s_, f'A{rr}', 1 + 5 * bi); put(s_, f'B{rr}', 5 + 5 * bi)
    for dd in range(1, 11):
        cl = get_column_letter(2 + dd); kr = 3 + dd
        cd = f'({K})*({C["KM"]}>Km_Deciles!$B${kr})*({C["KM"]}<=Km_Deciles!$C${kr})*({C["Age"]}>=$A{rr})*({C["Age"]}<=$B{rr})'
        put(s_, f'{cl}{rr}', f'=MEDIAN(IF({cd},{C["Price"]}))', '#,##0', arr=True)
s_['A10'] = 'Listings in each cell'; s_['A10'].font = FB
head(s_, 11, 1, ['Age from', 'Age to'] + [f'D{i}' for i in range(1, 11)])
for bi in range(5):
    rr = 12 + bi; put(s_, f'A{rr}', f'=A{4 + bi}'); put(s_, f'B{rr}', f'=B{4 + bi}')
    for dd in range(1, 11):
        cl = get_column_letter(2 + dd); kr = 3 + dd
        cd = f'({K})*({C["KM"]}>Km_Deciles!$B${kr})*({C["KM"]}<=Km_Deciles!$C${kr})*({C["Age"]}>=$A{rr})*({C["Age"]}<=$B{rr})'
        put(s_, f'{cl}{rr}', f'=SUMPRODUCT({cd})', '#,##0')
s_['A18'] = 'Smallest and largest cell'; put(s_, 'C18', '=MIN(C12:L16)', '#,##0', FB); put(s_, 'D18', '=MAX(C12:L16)', '#,##0', FB)
widths(s_, {get_column_letter(i): 11 for i in range(1, 13)})

# ------------------------------------------------------------------ Dup_Check (sorted key values pasted, run length formulas, chance baseline)
p_ = wsDup; p_['A1'] = 'Duplicate check on the 15 fields the randomisation step did not change'; p_['A1'].font = FT
p_['A2'] = 'Step: copied DATA!AC (Dup_Key) with the row number, price and segment to sheet Dup_Sorted, pasted as values and sorted by Dup_Key. Column E there counts position within each run of equal keys.'; p_['A2'].font = FN
order = np.lexsort((np.arange(N), Key.values)); rows_sorted = raw.ExcelRow.values[order]; key_sorted = Key.values[order]
price_sorted = raw.Car_Price.values[order]; seg_sorted = Seg[order]
run = np.ones(N, dtype=np.int64)
for i in range(1, N):
    if key_sorted[i] == key_sorted[i-1]: run[i] = run[i-1] + 1
DS = f"Dup_Sorted!$E$2:$E${L}"; DP = f"Dup_Sorted!$C$2:$C${L}"; DG = f"Dup_Sorted!$D$2:$D${L}"
p_['G3'] = 'Result'; p_['G3'].font = FB
DUPS = [('Repeat rows (run position > 1)', f'=COUNTIF({DS},">1")', '#,##0'),
        ('Matching pairs observed (sum of run position − 1)', f'=SUMPRODUCT({DS}-1)', '#,##0'),
        ('Car_Price values that occur more than once (so exact 20-field duplicates are impossible when 0)', f'=SUMPRODUCT(--(FREQUENCY({C["Price"]},{C["Price"]})>1))', '#,##0'),
        ('Probability two random rows match (product of Σp²)', '=PRODUCT($I$17:$I$29)', '0.000E+00'),
        ('Matching pairs expected by chance = n(n−1)/2 × probability', '=Notes!$C$5*(Notes!$C$5-1)/2*J7', '#,##0'),
        ('Excess pairs (observed − expected) ≈ genuine duplicates', '=J5-J8', '#,##0'),
        ('Median price, all rows', f'=MEDIAN({DP})', '#,##0'),
        ('Median price, first row of each key only', f'=MEDIAN(IF({DS}=1,{DP}))', '#,##0')]
for i, (lab, f_, fm) in enumerate(DUPS):
    rr = 4 + i; p_[f'G{rr}'] = lab; put(p_, f'J{rr}', f_, fm, FB, arr=('IF(' in f_))
# chance baseline: frequency tables per field
FIELDS = [('Model', 'Model', MODELS), ('Year', 'Year', list(range(2000, 2025))), ('Fuel_Clean', 'FuelC', FUELS), ('Transmission', 'Trans', TRANS), ('Owner_Type', 'Owner', OWN),
          ('Color', 'Color', COLS), ('City', 'City', CITY), ('Insurance_Valid', 'Ins', [0, 1]), ('Service_History', 'Svc', [0, 1]), ('Accidents', 'Acc', [0, 1, 2, 3, 4, 5]),
          ('Tax_Paid', 'Tax', [0, 1]), ('Number_of_Doors', 'Doors', DOORS), ('Seats', 'Seats', SEATS)]
p_['G15'] = 'Chance baseline'; p_['G15'].font = FB
head(p_, 16, 7, ['Field (independent of the others)', 'Categories', 'Σp² (sum of squared shares)'])
for j, (lab, v, vals) in enumerate(FIELDS):
    c1 = get_column_letter(13 + 2 * j); c2 = get_column_letter(14 + 2 * j)
    head(p_, 16, 13 + 2 * j, [lab, 'Share p'])
    for i, val in enumerate(vals):
        rr = 17 + i; p_[f'{c1}{rr}'] = val
        put(p_, f'{c2}{rr}', f'=COUNTIF({C[v]},{c1}{rr})/Notes!$C$5', '0.0000')
    rr = 17 + j; p_[f'G{rr}'] = lab; put(p_, f'H{rr}', len(vals)); put(p_, f'I{rr}', f'=SUMSQ({c2}17:{c2}{16+len(vals)})', '0.00000')
p_['G31'] = 'Brand and Registration_Age are left out of the product because Model fixes Brand and Year fixes Registration_Age.'; p_['G31'].font = FN
widths(p_, {'G': 70, 'J': 14})

# ------------------------------------------------------------------ Plot_Sample
rs = np.random.default_rng(20260926); keys = rs.random(len(pd.read_pickle('raw.pkl')))[:N]
take = np.argsort(keys)[:5000]; take = take[np.argsort(keys[take])]
okidx = np.where(KMOK.values)[0]; take2 = okidx[np.argsort(keys[okidx])[5000:10000]] if len(okidx) > 10000 else okidx[np.argsort(keys[okidx])[:5000]]
take2 = take2[np.argsort(keys[take2])]
q_ = wsP; q_['A1'] = 'Random samples of 5,000 rows for the two scatter plots'; q_['A1'].font = FT
q_['A2'] = 'Method: a uniform random number between 0 and 1 (seed 20260926) is stored as a value next to every DATA row number, and rows are sorted by it. Age sample: the first 5,000 rows. Km sample: the next 5,000 rows with KM_OK = TRUE. Other columns use INDEX. To draw a fresh sample in Excel: =RAND() in a helper column, Paste Special > Values, sort by it, take the first 5,000 rows.'; q_['A2'].font = FN
q_['A3'] = 'Age sample'; q_['A3'].font = FB; q_['H3'] = 'Km sample (KM_OK rows only)'; q_['H3'].font = FB
head(q_, 4, 1, ['Source row', 'Random key (value)', 'Segment', 'Registration_Age', 'Car_Price'])
head(q_, 4, 8, ['Source row', 'Random key (value)', 'Segment', 'Kms_Driven', 'Car_Price'])
for i, t in enumerate(take):
    rr = 5 + i; q_.cell(rr, 1, int(raw.ExcelRow.values[t])); q_.cell(rr, 2, float(keys[t]))
    q_.cell(rr, 3, f'=INDEX(DATA!$W$1:$W${L},$A{rr})'); q_.cell(rr, 4, f'=INDEX(DATA!$S$1:$S${L},$A{rr})'); q_.cell(rr, 5, f'=INDEX(DATA!$T$1:$T${L},$A{rr})')
for i, t in enumerate(take2):
    rr = 5 + i; q_.cell(rr, 8, int(raw.ExcelRow.values[t])); q_.cell(rr, 9, float(keys[t]))
    q_.cell(rr, 10, f'=INDEX(DATA!$W$1:$W${L},$H{rr})'); q_.cell(rr, 11, f'=INDEX(DATA!$L$1:$L${L},$H{rr})'); q_.cell(rr, 12, f'=INDEX(DATA!$T$1:$T${L},$H{rr})')
le = 4 + len(take); le2 = 4 + len(take2)
q_['N4'] = 'Check'; q_['N4'].font = FB
q_['N5'] = 'r (age, price) in the age sample'; put(q_, 'O5', f'=CORREL(D5:D{le},E5:E{le})', '+0.0000;-0.0000')
q_['N6'] = 'r (km, price) in the km sample'; put(q_, 'O6', f'=CORREL(K5:K{le2},L5:L{le2})', '+0.0000;-0.0000')
q_['N7'] = 'Luxury rows in the age sample'; put(q_, 'O7', f'=COUNTIF(C5:C{le},"Luxury")', '#,##0')
q_['N8'] = 'Luxury rows in the km sample'; put(q_, 'O8', f'=COUNTIF(J5:J{le2},"Luxury")', '#,##0')
widths(q_, {'A': 11, 'B': 18, 'C': 12, 'D': 16, 'E': 13, 'H': 11, 'I': 18, 'J': 12, 'K': 13, 'L': 13, 'N': 34, 'O': 12})

# ------------------------------------------------------------------ Sensitivity
e_ = wsSe; e_['A1'] = 'Do the main results change with the cleaning choices?'; e_['A1'].font = FT
head(e_, 3, 1, ['Scenario', 'Rows', 'Median Car_Price', 'r (price, age)', 'r (price, km ≤ cap)', 'Luxury median vs non-luxury'])
U_ = f'({C["Unk"]}=FALSE)'
lo_f, hi_f = 'EXP(Notes!$C$41-3*(Notes!$C$42-Notes!$C$41))', 'EXP(Notes!$C$42+3*(Notes!$C$42-Notes!$C$41))'
PO = f'({C["Price"]}>={lo_f})*({C["Price"]}<={hi_f})'
SC = [('Baseline (all rows)', '=Notes!C5', f'=Summary!E{SUMREF[("Price","All")]}', f'={CORRREF[("Age","All")]}', f'={CORRREF[("KM","All")]}', f'=Segment_Compare!E5'),
      ('Drop rows with any Unknown', f'=COUNTIF({C["Unk"]},FALSE)', f'=MEDIAN(IF({U_},{C["Price"]}))', f'=CORREL(IF({U_},{C["Age"]}),IF({U_},{C["Price"]}))',
       f'=CORREL(IF({U_}*({K}),{C["KM"]}),IF({U_}*({K}),{C["Price"]}))', f'=MEDIAN(IF({U_}*({C["Seg"]}="Luxury"),{C["Price"]}))/MEDIAN(IF({U_}*({C["Seg"]}="Non-luxury"),{C["Price"]}))-1'),
      ('Drop prices outside the log-scale fence', f'=SUMPRODUCT({PO})', f'=MEDIAN(IF({PO},{C["Price"]}))', f'=CORREL(IF({PO},{C["Age"]}),IF({PO},{C["Price"]}))',
       f'=CORREL(IF({PO}*({K}),{C["KM"]}),IF({PO}*({K}),{C["Price"]}))', f'=MEDIAN(IF({PO}*({C["Seg"]}="Luxury"),{C["Price"]}))/MEDIAN(IF({PO}*({C["Seg"]}="Non-luxury"),{C["Price"]}))-1'),
      ('Keep first row of each 15-field key', f'=COUNTIF({DS},1)', '=Dup_Check!J11', '', '',
       f'=MEDIAN(IF(({DS}=1)*({DG}="Luxury"),{DP}))/MEDIAN(IF(({DS}=1)*({DG}="Non-luxury"),{DP}))-1')]
for i, row in enumerate(SC):
    rr = 4 + i; e_[f'A{rr}'] = row[0]
    for j, f_ in enumerate(row[1:]):
        if not f_: continue
        col = 'BCDEF'[j]; fm = ['#,##0', '#,##0', '+0.0000;-0.0000', '+0.0000;-0.0000', '+0.00%;-0.00%'][j]
        put(e_, f'{col}{rr}', f_, fm, arr=('IF(' in f_))
e_['A9'] = 'Correlations cannot be recomputed on Dup_Sorted because it holds only price and segment; the km-cap sensitivity is on sheet Correlations rows 29–34.'; e_['A9'].font = FN
widths(e_, {'A': 40, 'B': 12, 'C': 18, 'D': 16, 'E': 20, 'F': 28})

# ------------------------------------------------------------------ Charts (native Excel)
ch = wsCh; ch['A1'] = 'Charts built from the tables in this workbook'; ch['A1'].font = FT
def place(chart, anchor, w=17, h=9): chart.width, chart.height = w, h; ch.add_chart(chart, anchor)
c1 = BarChart(); c1.type = 'col'; c1.gapWidth = 10; c1.title = 'Car_Price distribution (50k bins, 0–5m)'; c1.y_axis.title = 'Listings'; c1.x_axis.title = 'Car_Price (INR, bin start)'
c1.add_data(Reference(wsM, min_col=3, min_row=4, max_row=104), titles_from_data=True); c1.set_categories(Reference(wsM, min_col=1, min_row=5, max_row=104)); c1.legend = None
place(c1, 'A3')
c2 = ScatterChart(); c2.title = 'Car_Price vs Registration_Age (random 5,000)'; c2.style = 13; c2.x_axis.title = 'Registration_Age (years)'; c2.y_axis.title = 'Car_Price (INR, log scale)'
s2 = Series(Reference(wsP, min_col=5, min_row=5, max_row=le), Reference(wsP, min_col=4, min_row=5, max_row=le), title='Listings'); s2.marker.symbol = 'circle'; s2.marker.size = 2; s2.graphicalProperties.line.noFill = True
c2.series.append(s2); c2.y_axis.scaling.logBase = 10; c2.legend = None; place(c2, 'L3')
c3 = ScatterChart(); c3.title = 'Car_Price vs Kms_Driven (random sample, km ≤ cap)'; c3.style = 13; c3.x_axis.title = 'Kms_Driven (km, log scale)'; c3.y_axis.title = 'Car_Price (INR, log scale)'
s3 = Series(Reference(wsP, min_col=12, min_row=5, max_row=le2), Reference(wsP, min_col=11, min_row=5, max_row=le2), title='Listings'); s3.marker.symbol = 'circle'; s3.marker.size = 2; s3.graphicalProperties.line.noFill = True
c3.series.append(s3); c3.x_axis.scaling.logBase = 10; c3.y_axis.scaling.logBase = 10; c3.legend = None; place(c3, 'A22')
c4 = LineChart(); c4.title = 'Median Car_Price by Registration_Age'; c4.y_axis.title = 'Median Car_Price (INR)'; c4.x_axis.title = 'Registration_Age (years)'
c4.add_data(Reference(wsA, min_col=6, max_col=7, min_row=3, max_row=28), titles_from_data=True); c4.set_categories(Reference(wsA, min_col=1, min_row=4, max_row=28)); c4.y_axis.scaling.min = 0
place(c4, 'L22')
c5 = LineChart(); c5.title = 'Median Car_Price by Kms_Driven decile'; c5.y_axis.title = 'Median Car_Price (INR)'; c5.x_axis.title = 'Decile'
c5.add_data(Reference(wsK, min_col=8, max_col=9, min_row=3, max_row=13), titles_from_data=True); c5.set_categories(Reference(wsK, min_col=1, min_row=4, max_row=13)); c5.y_axis.scaling.min = 0
place(c5, 'A41')
c6 = BarChart(); c6.type = 'bar'; c6.title = 'Median Car_Price by brand'; c6.x_axis.title = 'Brand'; c6.y_axis.title = 'Median Car_Price (INR)'
c6.add_data(Reference(wsG, min_col=5, min_row=16, max_row=16 + len(BRANDS)), titles_from_data=True); c6.set_categories(Reference(wsG, min_col=1, min_row=17, max_row=16 + len(BRANDS))); c6.legend = None
place(c6, 'L41')
c7 = BarChart(); c7.type = 'bar'; c7.title = 'Pearson r with Car_Price'; c7.y_axis.title = 'r'
c7.add_data(Reference(wsC, min_col=3, max_col=5, min_row=3, max_row=15), titles_from_data=True); c7.set_categories(Reference(wsC, min_col=1, min_row=4, max_row=15))
place(c7, 'A60')
c8 = SurfaceChart3D(); c8.title = 'Median Car_Price by age band (series) and km decile'
c8.add_data(Reference(wsSu, min_col=3, max_col=12, min_row=4, max_row=8), from_rows=True); c8.set_categories(Reference(wsSu, min_col=3, max_col=12, min_row=3))
place(c8, 'L60')

# ------------------------------------------------------------------ Steps (process log)
st = wsS; st['A1'] = 'COMM5000 Milestone 1 – working file and order of work'; st['A1'].font = FT
STEPS = [
 ('1', 'Saved the randomised workbook once. Dataset!B6 reads "Data randomisation was applied ... on 2026-09-26 08:29:38". This copy is saved as .xlsx so the randomisation macro cannot run again; sheets Dataset and DATA are unchanged.', 'Dataset, DATA A:T'),
 ('2', 'Read the variable list on Dataset!B5. Car_Price (T) is the target; Registration_Age (S) and Kms_Driven (L) are the two required relationships. Mileage_kmpl (D) is fuel efficiency, not distance.', 'Dataset'),
 ('3', 'Made lookup lists: fuel label map and category lists for the duplicate key.', 'Lists'),
 ('4', 'Added helper columns U:AC on DATA and filled them down to the last row: U =TRIM(A2); V =VLOOKUP(LOWER(TRIM(G2)),Lists!$A$3:$B$10,2,FALSE); W segment from U; X km within the cap in Notes!C4; Y:AA technical values > 0 and within mean ± 3 SD; AB any Unknown; AC a numeric key built from 13 fields with MATCH.', 'DATA U:AC'),
 ('5', 'Counted each data problem with COUNTIF/SUMPRODUCT and wrote the treatment next to it. Further checks (rows 46 onward): extra spaces in the other text fields, the largest Kms_Driven, and very low values that pass the ±3 SD rule.', 'Notes'),
 ('6', 'Built frequency tables with COUNTIFS to find the modal class of continuous variables and to draw the price histogram.', 'Mode_Bins'),
 ('7', 'Calculated n, mean, median, mode, SD, min, max, quartiles and skewness for all rows, luxury and non-luxury. Array formulas (MEDIAN(IF(...)) etc.) entered with Ctrl+Shift+Enter.', 'Summary'),
 ('8', 'Calculated Pearson r between Car_Price and every other numeric field for the three groups, the log-scale km model, and the km-cap sensitivity.', 'Correlations'),
 ('9', 'Compared luxury and non-luxury (means, medians, 95% CI of the mean difference), each brand, each category of the other text fields, and each of the 39 models (with a 95% interval for each model median).', 'Segment_Compare'),
 ('9b', 'Counted every category of the text and count fields for all, luxury and non-luxury listings.', 'Category_Shares'),
 ('10', 'Median price by age, by km decile, and by age band × km decile.', 'Age_Profile, Km_Deciles, Surface'),
 ('11', 'Duplicate check: copied DATA!AC with row number, price and segment, pasted as values, sorted by key, counted runs. Compared matching pairs with the number expected by chance from the category shares.', 'Dup_Check'),
 ('12', 'Scatter-plot samples: a uniform random number (seed 20260926), stored as a value, next to every row number; rows sorted by it. The first 5,000 rows form the age sample; the next 5,000 rows with KM_OK = TRUE form the km sample. INDEX fetches each row. The same can be done with =RAND() and Paste Values.', 'Plot_Sample'),
 ('13', 'Re-ran the key results without Unknown rows, without extreme prices and without repeat rows.', 'Sensitivity'),
 ('14', 'Drew the charts from the tables above; the report figures use the same numbers.', 'Charts'),
 ('Note', 'The file has about 9 million helper-column formulas and several hundred array formulas over 1,005,000 rows. Excel recalculates everything when the file opens; allow a minute or two.', ''),
]
head(st, 3, 1, ['Step', 'What was done', 'Where'])
for i, (a, b, c) in enumerate(STEPS):
    rr = 4 + i; st[f'A{rr}'] = a; st[f'B{rr}'] = b; st[f'C{rr}'] = c
    for col in 'ABC': st[f'{col}{rr}'].font = F; st[f'{col}{rr}'].alignment = Alignment(wrap_text=True, vertical='top')
widths(st, {'A': 7, 'B': 110, 'C': 26})
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for c in row:
            if c.value is not None and c.font == Font(): c.font = F
wb.calculation.fullCalcOnLoad = True
wb.properties.creator = ''; wb.properties.lastModifiedBy = ''
TMP = OUT + '.tmp.xlsx'; wb.save(TMP)

# ------------------------------------------------------------------ write DATA sheet XML (values + shared formulas)
def colL(i): return get_column_letter(i)
HDRS = ['Brand', 'Model', 'Year', 'Mileage_kmpl', 'Engine_CC', 'Horsepower', 'Fuel_Type', 'Transmission', 'Owner_Type', 'Color', 'City', 'Kms_Driven', 'Insurance_Valid',
        'Service_History', 'Accidents', 'Tax_Paid', 'Number_of_Doors', 'Seats', 'Registration_Age', 'Car_Price',
        'Brand_Clean', 'Fuel_Clean', 'Segment', 'KM_OK', 'Mileage_OK', 'Engine_OK', 'HP_OK', 'Any_Unknown', 'Dup_Key']
def nest_key(r):
    parts = [(f'MATCH(B{r},{LREF["Model"]},0)-1', None), (f'C{r}-2000', 25), (f'MATCH(V{r},{LREF["Fuel_Clean"]},0)-1', 6), (f'MATCH(H{r},{LREF["Transmission"]},0)-1', 3),
             (f'MATCH(I{r},{LREF["Owner_Type"]},0)-1', 4), (f'MATCH(J{r},{LREF["Color"]},0)-1', 8), (f'MATCH(K{r},{LREF["City"]},0)-1', 9), (f'M{r}', 2), (f'N{r}', 2),
             (f'O{r}', 6), (f'P{r}', 2), (f'MATCH(Q{r},{LREF["Number_of_Doors"]},0)-1', 3), (f'MATCH(R{r},{LREF["Seats"]},0)-1', 4)]
    expr = parts[0][0]
    for p, rad in parts[1:]: expr = f'({expr})*{rad}+{p}'
    return expr
FORM = {
 'U': ('TRIM(A2)', 'str'), 'V': ('VLOOKUP(LOWER(TRIM(G2)),Lists!$A$3:$B$10,2,FALSE)', 'str'),
 'W': ('IF(OR(U2="Audi",U2="BMW",U2="Mercedes"),"Luxury","Non-luxury")', 'str'), 'X': ('AND(L2>=0,L2<=Notes!$C$4)', 'b'),
 'Y': ('AND(D2>0,ABS(D2-Notes!$C$8)<=3*Notes!$D$8)', 'b'), 'Z': ('AND(E2>0,ABS(E2-Notes!$C$9)<=3*Notes!$D$9)', 'b'),
 'AA': ('AND(F2>0,ABS(F2-Notes!$C$10)<=3*Notes!$D$10)', 'b'), 'AB': ('OR(V2="Unknown",H2="Unknown",J2="Unknown",K2="Unknown")', 'b'), 'AC': (nest_key(2), 'n')}
CACHE = {'U': BrandC.values, 'V': FuelC.values, 'W': Seg, 'X': KMOK.values, 'Y': MilOK.values, 'Z': EngOK.values, 'AA': HPOK.values, 'AB': Unk.values, 'AC': Key.values}
RAWCOLS = list(raw.columns[1:21])
def fmtnum(v):
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15: return str(int(v))
    return repr(float(v))
SSTL = []; SSTI = {}
def si(t):
    if t not in SSTI: SSTI[t] = len(SSTL); SSTL.append(t)
    return SSTI[t]
tmpxml = OUT + '.sheet.xml'
with open(tmpxml, 'w', encoding='utf-8') as fh:
    fh.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    fh.write(f'<dimension ref="A1:AC{L}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    fh.write('<sheetFormatPr defaultRowHeight="15"/><cols><col min="1" max="20" width="13" customWidth="1"/><col min="21" max="29" width="14" customWidth="1"/></cols><sheetData>')
    fh.write('<row r="1">' + ''.join(f'<c r="{colL(i+1)}1" t="inlineStr"><is><t>{h}</t></is></c>' for i, h in enumerate(HDRS)) + '</row>')
    cols_vals = [raw[c].values for c in RAWCOLS]; isstr = [raw[c].dtype == object or str(raw[c].dtype).startswith('str') for c in RAWCOLS]
    for i in range(N):
        r = i + 2; parts = [f'<row r="{r}">']
        for j in range(20):
            v = cols_vals[j][i]; ref = f'{colL(j+1)}{r}'
            if isstr[j]: parts.append(f'<c r="{ref}" t="s"><v>@@{si(v)}</v></c>')
            else: parts.append(f'<c r="{ref}"><v>{fmtnum(v)}</v></c>')
        for k, (col, (f_, typ)) in enumerate(FORM.items()):
            ref = f'{col}{r}'
            fx = f'<f t="shared" ref="{col}2:{col}{L}" si="{k}">{escape(f_)}</f>' if r == 2 else f'<f t="shared" si="{k}"/>'
            if NOCACHE: parts.append(f'<c r="{ref}">{fx}</c>'); continue
            v = CACHE[col][i]
            if typ == 'str': parts.append(f'<c r="{ref}" t="str">{fx}<v>{escape(str(v))}</v></c>')
            elif typ == 'b': parts.append(f'<c r="{ref}" t="b">{fx}<v>{1 if v else 0}</v></c>')
            else: parts.append(f'<c r="{ref}">{fx}<v>{int(v)}</v></c>')
        parts.append('</row>'); fh.write(''.join(parts))
    fh.write('</sheetData><pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')
# Dup_Sorted sheet XML
dupxml = OUT + '.dup.xml'
with open(dupxml, 'w', encoding='utf-8') as fh:
    fh.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">')
    fh.write(f'<dimension ref="A1:E{L}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    fh.write('<sheetFormatPr defaultRowHeight="15"/><cols><col min="1" max="5" width="16" customWidth="1"/></cols><sheetData>')
    fh.write('<row r="1">' + ''.join(f'<c r="{colL(i+1)}1" t="inlineStr"><is><t>{h}</t></is></c>' for i, h in enumerate(['Source row', 'Dup_Key (value)', 'Car_Price (value)', 'Segment (value)', 'Run position'])) + '</row>')
    for i in range(N):
        r = i + 2
        fx = f'<f t="shared" ref="E2:E{L}" si="0">IF(B2=B1,E1+1,1)</f>' if r == 2 else '<f t="shared" si="0"/>'
        cache = '' if NOCACHE else f'<v>{int(run[i])}</v>'
        fh.write(f'<row r="{r}"><c r="A{r}"><v>{int(rows_sorted[i])}</v></c><c r="B{r}"><v>{int(key_sorted[i])}</v></c><c r="C{r}"><v>{repr(float(price_sorted[i]))}</v></c>'
                 f'<c r="D{r}" t="s"><v>@@{si(seg_sorted[i])}</v></c><c r="E{r}">{fx}{cache}</c></row>')
    fh.write('</sheetData><pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/></worksheet>')
zin = zipfile.ZipFile(TMP); wbx = zin.read('xl/workbook.xml').decode(); rels = zin.read('xl/_rels/workbook.xml.rels').decode()
def target_of(name):
    rid = re.search(rf'<sheet[^>]*name="{name}"[^>]*r:id="(rId\d+)"', wbx).group(1)
    t = re.search(rf'<Relationship[^>]*Id="{rid}"[^>]*/>', rels).group(0)
    return 'xl/' + re.search(r'Target="/?(?:xl/)?([^"]+)"', t).group(1)
from lxml import etree as ET
ssx = zin.read('xl/sharedStrings.xml') if 'xl/sharedStrings.xml' in zin.namelist() else None
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
base = [] if ssx is None else [''.join(e.itertext()) for e in ET.fromstring(ssx).findall(f'{{{NS}}}si')]
off = len(base)
def fix(path):
    out = path + '.2'
    with open(path, encoding='utf-8') as fi, open(out, 'w', encoding='utf-8') as fo:
        for chunk in iter(lambda: fi.read(1 << 24), ''):
            fo.write(re.sub(r'@@(\d+)', lambda m: str(int(m.group(1)) + off), chunk))
    os.replace(out, path)
fix(tmpxml); fix(dupxml)
allstr = base + SSTL
ssxml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<sst xmlns="%s" count="%d" uniqueCount="%d">' % (NS, len(allstr), len(allstr)) + ''.join(f'<si><t xml:space="preserve">{escape(t)}</t></si>' for t in allstr) + '</sst>'
REPL = {target_of('DATA'): tmpxml, target_of('Dup_Sorted'): dupxml}

zout = zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
for item in zin.infolist():
    if item.filename in REPL: zout.write(REPL[item.filename], item.filename)
    elif item.filename == 'xl/sharedStrings.xml': zout.writestr(item.filename, ssxml)
    elif item.filename == '[Content_Types].xml' and ssx is None:
        ct = zin.read(item.filename).decode().replace('</Types>', '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
        zout.writestr(item, ct)
    elif item.filename == 'xl/_rels/workbook.xml.rels' and ssx is None:
        rl = zin.read(item.filename).decode().replace('</Relationships>', '<Relationship Id="rIdSST1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
        zout.writestr(item, rl)
    elif item.filename == 'docProps/app.xml':
        zout.writestr(item, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"/>')
    else: zout.writestr(item, zin.read(item.filename))
if ssx is None: zout.writestr('xl/sharedStrings.xml', ssxml)
zout.close(); zin.close(); os.remove(TMP); os.remove(tmpxml); os.remove(dupxml)
json.dump({'N': N, 'SUMREF': {f'{a}|{b}': v for (a, b), v in SUMREF.items()}, 'CORRREF': {f'{a}|{b}': v for (a, b), v in CORRREF.items()}, 'CATREF': CATREF, 'PD': PD,
           'sample_rows': [int(raw.ExcelRow.values[t]) for t in take], 'sample_rows_km': [int(raw.ExcelRow.values[t]) for t in take2]}, open(OUT + '.map.json', 'w'))
print('written', OUT, os.path.getsize(OUT))
