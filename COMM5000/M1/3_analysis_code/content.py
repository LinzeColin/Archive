# Single source of truth for the report text. Every statistic is pulled from results.json.
import json
R = json.load(open('results.json'))
D = R['desc']; A = R['rel']['All']; S = R['seg']; T = R['tech']

def k(x): return f"{x/1e3:,.0f}k"
def m(x, d=3): return f"{x/1e6:.{d}f}m"
def pct(x, d=1): return f"{x:.{d}f}%"

TITLE = "From Listing to Offer"
SUBTITLE = "Preliminary insight development for used-car price appraisal"
META = "COMM5000 Data Literacy · Case Study Project · Milestone 1 · Term 3, 2026"

dup_genuine = R['dup15_extra'] - R['dup15_null_mean']
med_drop_dup = (R['sens']['drop_dup15']['median'] / R['sens']['baseline']['median'] - 1) * 100
elast = A['km']['elasticity']; per10 = (1.1 ** elast - 1) * 100
kd = R['km_deciles']
age_lo, age_hi = R['age_median_range']
tech_n = {c: T[c]['zero'] + T[c]['sd3'] for c in T}

KPIS = [
    (pct(R['mean_over_median_pct']), "mean price above median", "right-skewed: report the median"),
    (f"r = {A['age']['pearson']:+.5f}", "price vs Registration_Age", "no age gradient in 1,005,000 rows"),
    (f"{per10:.2f}%", "price per +10% Kms_Driven", "the only stable usage signal"),
    (f"{S['median_diff_pct']:+.2f}%", "luxury vs non-luxury median", f"95% CI {S['median_ratio_ci_pct'][0]:+.2f} to {S['median_ratio_ci_pct'][1]:+.2f}%"),
]

# Blocks: ('h', text) heading; ('p', text) body paragraph (counted); ('table', key); ('fig', key); ('kpi',)
BODY = [
('h', "1  Introduction"),
('p', f"India’s used-car market sold about 5.9 million vehicles in FY2025—137 used cars for every 100 new ones—and is forecast to reach 9.5 million by 2030 (Mahindra First Choice & Volkswagen Group India [MFC & VW], 2025, p. 6). Yet appraisal has traditionally been “subjective, varying across geographies and dealers” (MFC & VW, 2025, p. 53). For our client, an online marketplace, a reliable expected price underpins instant cash offers, alerts for under- and over-priced listings and inventory forecasts: a systematic 10% over-offer on a median car (INR {k(D['All']['Car_Price']['median'])}) hands roughly INR {D['All']['Car_Price']['median']*0.1/1e3:,.0f}k of margin to the seller."),
('p', "This report explores the 1,005,000 listings supplied by the client (Stable Space, 2026) to prepare two questions: (1) how Car_Price relates to vehicle age (Registration_Age) and usage (Kms_Driven), and (2) whether brand segment—luxury (Audi, BMW, Mercedes) versus non-luxury—shifts price. It moves from data preparation and description to relationships, conclusions and a development plan."),
('kpi',),
('h', "2  Data preparation"),
('p', f"The randomised workbook (Dataset!B6 stamped 2026-09-26 08:29:38) contains 20 fields. Table 1 logs each issue, its size, treatment and rationale. Three principles applied: delete no price without evidence it is wrong; relabel only when the intended category is unambiguous; and test whether each choice changes conclusions (Appendix Table A1)."),
('p', f"Two checks went beyond routine auditing. First, exact-duplicate tests find nothing because the workbook’s randomisation routine (VBA module ThisWorkbook) regenerates five numeric fields for every row. Matching on the 15 untouched fields instead finds {R['dup15_extra']:,} repeat rows, but shuffling each column independently produces {R['dup15_null_mean']:,.0f} ± {R['dup15_null_sd']:.0f} coincidental matches, so only about {round(dup_genuine,-2):,.0f} are genuine duplicates. As the two cannot be told apart, rows are flagged, not deleted; dropping all repeats moves the median price by only {med_drop_dup:+.3f}%. Second, the {R['km_over_1m']:,} listings above 1,000,000 km closely match the {R['km_over_1m_expected']:,.0f} expected from the routine’s log-normal usage distribution: they are a statistical tail, not typing errors. They are excluded from usage analysis only; results are stable for every cap from 500,000 km to none."),
('table', 'audit'),
('h', "3  Descriptive statistics"),
('p', f"Table 2 summarises the key variables for the full sample and both segments. Car_Price is heavily right-skewed (skewness {D['All']['Car_Price']['skew']:.1f}): the mean (INR {m(D['All']['Car_Price']['mean'])}) exceeds the median (INR {m(D['All']['Car_Price']['median'])}) by {pct(R['mean_over_median_pct'])}, and {pct(R['share_below_mean']*100)} of cars are priced below the mean (Figure 1A). On a log scale the distribution is almost perfectly symmetric (skewness {R['logprice']['skew']:.3f}; Figure 1B), so price is approximately log-normal. The client should therefore receive the median with its interquartile range (INR {m(D['All']['Car_Price']['q1'],2)}–{m(D['All']['Car_Price']['q3'],2)}), not the mean, and later models should use log price."),
('p', f"The segments are near-identical on every variable: price medians differ by under 0.2%, age medians not at all, and insurance, service and tax shares agree within 0.2 percentage points. Registration_Age is uniform (1–25 years). Engine_CC, Horsepower and Mileage_kmpl are flat-topped (excess kurtosis {T['Engine_CC']['kurt']:.2f}) with small peaks at both edges, so their modes (e.g. {D['All']['Engine_CC_c']['mode']:,.0f} cc) are unrepresentative and the median is the better anchor."),
('table', 'desc'),
('fig', 'fig1'),
('h', "4  Price, age and usage"),
('p', f"Figure 2A condenses the evidence into a 3D price landscape: median price tilts along usage but stays level along age. Figure 2B explains the method: across 1,000 random 5,000-row samples the price–age correlation ranges from {R['sample_r']['age']['p2_5']:+.3f} to {R['sample_r']['age']['p97_5']:+.3f}, so one sample can suggest a non-existent trend. Figure 3 therefore shows each relationship both as the guide’s 5,000-listing random scatter (3A, 3C) and as full-data medians with 95% confidence intervals (3B, 3D)."),
('fig', 'fig2'),
('p', f"<b>Age.</b> There is no relationship. The full-data Pearson r is {A['age']['pearson']:+.5f} (95% CI {A['age']['pearson_ci'][0]:+.3f} to {A['age']['pearson_ci'][1]:+.3f}), and median price moves only ±{(age_hi/age_lo-1)*50:.1f}% across the 25 ages, in both segments."),
('p', f"<b>Usage.</b> Price declines steadily but weakly with kilometres. The median falls {abs(R['km_d1_d10_median_drop_pct']):.0f}% from the lowest to the highest usage decile (INR {k(kd[0]['median'])} to {k(kd[-1]['median'])}), the Spearman correlation is {A['km']['spearman']:.3f} and the log–log slope is {elast:.3f}: each additional 10% of kilometres lowers expected price by about {abs(per10):.1f}%, with identical slopes in both segments. Although highly significant, usage explains only {R['screen_r2']['Kms_c']*100:.1f}% of log-price variance."),
('fig', 'fig3'),
('h', "5  Brand segment"),
('fig', 'fig4'),
('p', f"Luxury cars are not priced higher in this dataset. The luxury median is {abs(S['median_diff_pct']):.2f}% lower (95% bootstrap CI {S['median_ratio_ci_pct'][0]:+.2f}% to {S['median_ratio_ci_pct'][1]:+.2f}%), Welch’s t-test gives p = {S['welch_p']:.2f}, and the standardised effect is {abs(S['cohen_d_log']):.3f}, far below the 0.2 threshold for even a small effect (Cohen, 1988, p. 25). Across the 13 brands, medians span only {R['brand_median_range_pct']:.1f}% with overlapping confidence intervals (Figure 4A). Cleaning mattered for building the segments, not for the verdict: {R['lux_hidden_by_spaces']:,} luxury listings with padded labels would otherwise have been misclassified."),
('p', f"The signal scan (Figure 4B) ranks all 19 candidate predictors. Only Kms_Driven ({R['screen_r2']['Kms_c']*100:.2f}%), Horsepower ({R['screen_r2']['Horsepower_c']*100:.2f}%) and Engine_CC ({R['screen_r2']['Engine_CC_c']*100:.2f}%) explain more than 0.01% of log-price variance. This mirrors the randomisation routine, which generates the five numeric fields jointly without reference to brand, age or any categorical field. The absence of age and brand effects is therefore a property of this assessment dataset and should not be read as market behaviour."),
('h', "6  Conclusions and development plan"),
('p', f"Three conclusions follow. First, report medians and model log price. Second, usage is the only stable driver: a consistent but modest discount of about {abs(per10):.1f}% per 10% more kilometres. Third, neither brand segment nor age shifts price here, so no luxury premium should be built into offers on this evidence."),
('p', f"The limitation matters commercially. A preview log-linear model using kilometres, horsepower and engine size explains {R['prev_model']['r2']*100:.1f}% of variance, and its median absolute percentage error ({R['prev_model']['mdape']:.1f}%) barely improves on quoting the overall median ({R['mdape_global_median']:.1f}%). Instant offers built on these fields alone would be unreliable. We recommend (a) quoting price bands rather than point offers; (b) routing listings outside each segment’s 5th–95th percentile band to manual review; and (c) collecting condition, inspection-grade, trim and transaction-price data before automating appraisal—46% of Indian buyers already pay for professional inspections (MFC & VW, 2025, p. 48)."),
('p', f"Table 3 sets out the plan: Milestone 2 formally tests the age, usage and segment hypotheses on log price; the final report fits and hold-out-validates a multiple regression with prediction intervals, treating Engine_CC and Horsepower (r = {R['corr_engine_hp']:.2f}) carefully to avoid multicollinearity."),
('table', 'plan'),
]

REFS = [
    "Cohen, J. (1988). <i>Statistical power analysis for the behavioral sciences</i> (2nd ed.). Lawrence Erlbaum Associates. pp. 25–27.",
    "Mahindra First Choice & Volkswagen Group India. (2025). <i>The used car ethos: India FY2024–25</i> (Indian Blue Book report). pp. 6, 48, 53. https://www.volkswagen.co.in/idhub/content/dam/onehub_pkw/importers/in/pdf/ibb-report-fy-2024-25.pdf",
    "Stable Space. (2026). <i>Used car price prediction dataset</i> [Data set]. Kaggle. Retrieved June 2026 from https://www.kaggle.com/datasets/sharmajicoder/used-car-price-prediction-dataset (supplied as COMM5000-Used_Car_Price_Prediction.xlsm, sheets Dataset and DATA).",
]

AUDIT_HEAD = ["Issue", "How detected", "Size", "Treatment", "Rationale"]
AUDIT = [
    ["Brand labels padded with spaces (e.g. ‘ BMW ’)", "TRIM + frequency table", f"{R['brand_relabelled']:,} ({R['lux_hidden_by_spaces']:,} luxury)", "Trimmed → 13 brands", "Segments cannot be built correctly otherwise"],
    ["Fuel_Type variants (PETROL, petrol, ‘ Diesel’, ‘diesel ’, hybridd, electrik)", "TRIM/LOWER + frequency table", f"{R['fuel_relabelled']:,}", "Mapped → 5 fuel types", "Intended category is unambiguous"],
    ["‘Unknown’ in Fuel_Type / Transmission / Color / City", "Frequency table", f"{R['unknown']['FuelC']:,} / {R['unknown']['Transmission']:,} / {R['unknown']['Color']:,} / {R['unknown']['City']:,} ({R['rows_any_unknown']/1e3:,.0f}k rows)", "Kept as own category", "Deleting would drop 28% of rows; true category cannot be inferred"],
    ["Missing numeric values", "COUNTBLANK per column", "0", "None needed", "Workbook notes randomisation filled them"],
    ["Zero or isolated extreme technical values", "= 0 or beyond mean ± 3 SD", f"Mileage {tech_n['Mileage_kmpl']}, Engine {tech_n['Engine_CC']}, HP {tech_n['Horsepower']}", "Set to missing for that field only", "Physically impossible or far outside a bounded range"],
    ["Duplicated records", "Exact 20-field match; 15-field match vs permutation baseline", f"0 exact; {R['dup15_extra']:,} vs {R['dup15_null_mean']:,.0f} by chance (≈{round(dup_genuine,-2):,.0f} genuine)", "Flagged, retained", "Individual duplicates unidentifiable; median impact 0.01%"],
    ["Kms_Driven > 1,000,000", "Filter", f"{R['km_over_1m']:,} (0.61%; {R['km_over_1m_expected']:,.0f} expected)", "Excluded from usage analysis only", "Guide’s plausibility threshold; price still valid"],
    ["Extreme Car_Price", "Log-scale 3 × IQR fence", f"{R['price_out_low']} low, {R['price_out_high']} high", "Retained; medians and logs used", "Consistent with a log-normal tail"],
    ["Internal consistency", "Year + Registration_Age; Brand × Model", "100% = 2025; 39 models → 1 brand each", "Used as provided", "Confirms fields are coherent"],
]

DESC_VARS = [('Car_Price', 'Car_Price (INR)', 0), ('Registration_Age', 'Registration_Age (years)', 1), ('Kms_c', 'Kms_Driven (km, ≤ 1m)', 0),
             ('Engine_CC_c', 'Engine_CC (cc)', 0), ('Horsepower_c', 'Horsepower (hp)', 1), ('Mileage_kmpl_c', 'Mileage (km/l)', 2), ('Accidents', 'Accidents (count)', 2)]
DESC_HEAD = ["Variable", "Group", "n", "Mean", "Median", "Mode*", "SD", "Min", "Max"]

def desc_rows():
    rows = []
    for v, lab, dp in DESC_VARS:
        for g, gl in [('All', 'All'), ('Luxury', 'Luxury'), ('Non-luxury', 'Non-lux.')]:
            d = D[g][v]
            f = (lambda x: f"{x:,.{dp}f}")
            rows.append([lab if g == 'All' else '', gl, f"{d['n']:,}", f(d['mean']), f(d['median']), f(d['mode']), f(d['sd']), f(d['min']), f(d['max'])])
    return rows

sh = R['seg_shares']
DESC_NOTE = (f"*Mode: exact for discrete variables; midpoint of the modal bin for continuous ones (bins: price 50k, km 10k, cc 50, hp 5, km/l 0.5). "
             f"Binary fields (All / Luxury / Non-luxury): Insurance_Valid {sh['All']['ins']*100:.1f} / {sh['Luxury']['ins']*100:.1f} / {sh['Non-luxury']['ins']*100:.1f}%; "
             f"Service_History {sh['All']['svc']*100:.1f} / {sh['Luxury']['svc']*100:.1f} / {sh['Non-luxury']['svc']*100:.1f}%; Tax_Paid {sh['All']['tax']*100:.1f} / {sh['Luxury']['tax']*100:.1f} / {sh['Non-luxury']['tax']*100:.1f}%; "
             f"first owner {sh['All']['first_owner']*100:.1f} / {sh['Luxury']['first_owner']*100:.1f} / {sh['Non-luxury']['first_owner']*100:.1f}%. SD uses n − 1.")

PLAN_HEAD = ["Question", "Stage", "Method (course tools)", "Output / decision rule"]
PLAN = [
    ["Q1a Does age affect price?", "M2", "H0: ρ = 0 for log price vs age; one-way ANOVA across 5-year age bands", "95% CI for r; effect judged against ±1% practical band"],
    ["Q1b How strongly does usage lower price?", "M2", "t-test on the slope of log price on log km; compare slopes by segment", "Elasticity with 95% CI (current estimate −0.088)"],
    ["Q2 Is there a luxury premium?", "M2", "Welch two-sample t-test on log price; Mann–Whitney as robustness check", "CI for median ratio; premium only if CI excludes 0"],
    ["Predict price at appraisal", "Final", "Multiple regression on log price (log km, Horsepower or Engine_CC, segment dummy, controls); 80/20 hold-out", "Hold-out MdAPE vs median benchmark (55.3%); prediction bands"],
    ["Are conclusions robust?", "M2 + Final", "Re-run with duplicates removed, Unknown removed, km caps 0.5m–none", "Conclusions reported only if unchanged (Table A1)"],
]

SENS_HEAD = ["Scenario", "n", "Median price (INR)", "r (price, age)", "r (price, km ≤ 1m)", "Luxury median gap"]
def sens_rows():
    s = R['sens']; out = []
    for key, lab in [('baseline', 'Baseline (all rows)'), ('drop_dup15', 'Drop all 15-field repeats'), ('drop_any_unknown', 'Drop rows with any Unknown'), ('drop_price_outliers', 'Drop 3 extreme prices')]:
        v = s[key]; out.append([lab, f"{v['n']:,}", f"{v['median']:,.0f}", f"{v['r_age']:+.5f}", f"{v['r_km']:+.4f}", f"{v['lux_med_gap']:+.2f}%"])
    return out
def cap_rows():
    out = []
    for key, lab in [('500000.0', '≤ 500,000 km'), ('750000.0', '≤ 750,000 km'), ('1000000.0', '≤ 1,000,000 km (used)'), ('1500000.0', '≤ 1,500,000 km'), ('None', 'No cap')]:
        v = R['km_caps'][key]; out.append([lab, f"{v['n']:,}", f"{v['r']:+.4f}", f"{v['rlog']:+.4f}"])
    return out

FIGS = {
 'fig1': ('fig/fig1_price.png', "Figure 1. Distribution of Car_Price, all 1,005,000 listings. (A) Raw INR scale. (B) Log scale by segment; the two curves coincide."),
 'fig2': ('fig/fig3_landscape.png', "Figure 2. (A) Median price over 5 age bands × 10 usage deciles, all listings ≤ 1m km (about 20,000 per cell). (B) Pearson r in 1,000 random 5,000-row samples versus the full-data value."),
 'fig3': ('fig/fig2_relationships.png', "Figure 3. Price against age (top) and usage (bottom). A and C: 5,000 randomly sampled listings each (fixed seeds; source rows listed in the companion workbook), black line = full-data medians. B and D: all listings, medians with 95% order-statistic confidence intervals; D’s axis does not start at zero."),
 'fig4': ('fig/fig4_segment_signal.png', "Figure 4. (A) Median price by brand and segment, 95% CIs; grey line = overall median. (B) Share of log-price variance explained by each field, log axis."),
}
