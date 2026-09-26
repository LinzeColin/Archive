# Build scripts (M1 final)

Order: `parse.py` (xlsm → raw.pkl) → `analysis.py`, `stats_final.py`, `stats_v2.py` (clean.pkl, results.json) → `figs_v3.py` (figures) → `content_v3.py` (doc.json) → `node build_docx.js report_raw.docx` → `finalize_docx.py report_raw.docx report.docx` → LibreOffice PDF export.
Workbook: `python3 build_working.py all COMM5000_M1_Working.xlsx`; check with `verify_sub.py <recalculated.xlsx> <rows>`. Tables: `export_tables.py`.
The data file and the 200 MB workbook are not stored here (data policy); the source xlsm is in Release `COMM5000`.
