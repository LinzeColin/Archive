"""Export every report table from doc.json to CSV (UTF-8 with BOM so Excel shows symbols correctly)."""
import json, csv, os, sys
out = sys.argv[1] if len(sys.argv) > 1 else 'pkg_tables'
os.makedirs(out, exist_ok=True)
d = json.load(open('doc.json'))
names = {'T1': 'Table1_data_problems', 'T2': 'Table2_numerical_summaries', 'T3': 'Table3_development_plan', 'TA1': 'TableA1_fields',
         'TA2': 'TableA2_correlations', 'TA3': 'TableA3_category_medians', 'TA4': 'TableA4_sensitivity'}
for k, fn in names.items():
    t = d['tables'][k]
    with open(f'{out}/{fn}.csv', 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow([t['title']]); w.writerow(t['head'])
        for r in t['rows']: w.writerow([c.replace(' ', ' ') for c in r])
        if t.get('note'): w.writerow([]); w.writerow([t['note']])
print('exported', len(names))
