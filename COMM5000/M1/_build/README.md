# Build scripts (M1 final, version 3)

Order: `parse.py` (xlsm → raw.pkl) → `analysis.py`, `stats_final.py`, `stats_v2.py` (clean.pkl, results.json) → `figs_v4.py` (figures) → `content_v5.py` (doc.json) → `node build_docx.js report_raw.docx` → `finalize_docx.py report_raw.docx report.docx`.
Workbook: `python3 build_working.py all COMM5000_M1_Working.xlsx`, then
1. `python3 check_data_xml.py COMM5000_M1_Working.xlsx` — decodes every stored DATA value and compares it with raw.pkl;
2. `python3 uno_full.py COMM5000_M1_Working.xlsx <port> lite.xlsx` — LibreOffice recalculates every formula, counts error cells per sheet and writes the summary-sheet values to `lite.xlsx`;
3. `python3 verify_sub.py lite.xlsx <rows>` — compares those values with an independent pandas calculation.
Tables: `export_tables.py`.
The data file and the 200 MB workbook are not stored here (data policy; GitHub's 100 MB file limit); the source xlsm is in Release `COMM5000`.
