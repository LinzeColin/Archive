"""Report text and tables (single source). Numbers come from results.json, which matches the Excel working file."""
import json, re
R = json.load(open('results.json'))
D = R['desc']; A = R['rel']['All']; S = R['seg']; CM = R['cat_medians']; CO = R['corr_all']
def n0(x): return f"{x:,.0f}"
def mn(t): return re.sub(r'(?<![\w\-])-(?=[\d.])', '−', str(t))
nonmean = D['Non-luxury']['Car_Price']['mean']
ci_lo, ci_hi = S['mean_diff_ci'][0] / nonmean * 100, S['mean_diff_ci'][1] / nonmean * 100
elast = A['km']['elasticity']; per10 = (1.1 ** elast - 1) * 100
kd1, kd10 = R['km_dec_iqr']['All']['0'][1], R['km_dec_iqr']['All']['9'][1]
age_lo, age_hi = R['age_median_range']
dp = R['dup_pairs']; tech = {k: v['zero'] + v['sd3'] for k, v in R['tech'].items()}
drop_first_med = (R['sens']['drop_dup15']['median'] / R['sens']['baseline']['median'] - 1) * 100
se_age = R['se_r5000']['age']
unk_share = R['rows_any_unknown'] / R['n_all'] * 100

TITLE = 'Preliminary Insight Development: Used Car Prices in India'
SUB = 'COMM5000 Data Literacy · Case Study Project · Milestone 1 · Term 3, 2026'

# ('h1'|'h2'|'p'|'table'|'fig'|'pagebreak', ...)
E = json.load(open('extra.json'))
lux_lo, lux_hi = E['age_rng']['Luxury']; MO = E['model']
cat_max = max(v['_range_pct'] for v in CM.values())
max_other = {g: max(abs(CO[k][g]['pearson']) for k in CO if k not in ('Kms_Driven (≤1m km)', 'Horsepower', 'Engine_CC')) for g in ['All', 'Luxury', 'Non-luxury']}
def up(x, d=1): import math; return math.ceil(x * 10**d - 1e-9) / 10**d

BODY = [
('h1', '1  Introduction'),
('p', "India’s used car market now outsells the new car market, yet price appraisal still relies heavily on manual valuation (UNSW Business School 2026, p. 4). Our client, an online marketplace, needs a fast and consistent price estimate at appraisal to support instant cash offers, spot mispriced listings and forecast stock turnover. It first needs to know what is linked to price and how reliable the data are."),
('p', f"This report explores the {n0(R['n_all'])} listings in the course dataset (Stable Space 2026) against the two project objectives (UNSW Business School 2026, p. 4): how Car_Price relates to the other variables, including brand segment, and how the methods could be improved. Section 2 presents the analysis and Section 3 the findings and plan."),
('h1', '2  Data Summaries and Descriptive Statistics'),
('h2', '2.1  Data preparation'),
('p', f"The analysis uses the workbook as randomised on 26 September 2026 (stamp in cell B6 of the Dataset sheet), with every number calculated by Excel formulas. Labels were corrected only where the intended category was obvious, and no listing was deleted (Table 1). ‘Unknown’ entries were kept as a category because they affect {unk_share:.1f}% of rows and cannot be recovered. No cell is blank because the macro fills gaps (Stable Space 2026) and sets negative draws to zero, so technical zeros were treated as missing."),
('p', f"The randomising macro (Franch 2026, slide 7) rewrites five numeric columns in its code, so repeated listings no longer look identical. Matching rows on the other 15 fields gives {n0(dp['obs_pairs'])} identical pairs, about {round(dp['excess'], -1):,.0f} more than the {n0(dp['exp_pairs'])} expected by chance. These possible repeats cannot be told apart from chance matches, so they were flagged but kept. Keeping one row per match moves the median by only {abs(drop_first_med):.2f}% (Table A4)."),
('p', f"The guide treats more than 1,000,000 km as implausible (UNSW Business School 2026, p. 7). These {n0(R['km_over_1m'])} listings match the {n0(R['km_lognorm']['expected_over_1m'])} expected from a log-normal fit, so they may be a genuine tail, but were left out of the usage analysis. A few isolated values, such as {E['hp_min_kept']:.1f} hp or a price of INR {n0(D['All']['Car_Price']['min'])}, are implausible for a car but too few to matter (Table 1)."),
('table', 'T1'),
('h2', '2.2  The variables'),
('p', "Table A1 describes all 20 fields. Car_Price is in Indian rupees (INR), and Year and Registration_Age carry the same information. Registration_Age is spread evenly over 1 to 25 years, and Engine_CC, Horsepower and Mileage_kmpl are almost flat across their main range, so their modes in Table 2 are not typical values."),
('h2', '2.3  Distribution of Car_Price'),
('p', f"Car_Price is strongly right-skewed (Table 2; skewness {D['All']['Car_Price']['skew']:.1f}). The long right tail lifts the mean of INR {n0(D['All']['Car_Price']['mean'])} to {R['mean_over_median_pct']:.1f}% above the median of INR {n0(D['All']['Car_Price']['median'])}, and {R['share_below_mean']*100:.1f}% of listings sit below the mean (Figure 1a). The median and interquartile range (INR {n0(D['All']['Car_Price']['q1'])} to {n0(D['All']['Car_Price']['q3'])}) therefore describe a typical car better and should be reported to the client. Log price is almost symmetric (skewness {R['logprice']['skew']:.3f}; Figure 1b), which suits later modelling."),
('table', 'T2'),
('fig', 'F1'),
('h2', '2.4  Price, vehicle age and usage'),
('p', f"Price was plotted for 5,000 randomly chosen listings, the largest sample the guide suggests (UNSW Business School 2026, p. 7), beside medians for all listings (Figure 2). Registration_Age shows no clear association with price (r = {A['age']['pearson']:.4f}). Its median stays between INR {n0(age_lo)} and {n0(age_hi)} across all 25 ages (Figure 2b)."),
('p', f"Usage has a weak negative association with price. The correlation is {A['km']['pearson']:.3f}, and the median falls from INR {n0(kd1)} in the lowest usage decile to INR {n0(kd10)} in the highest, {abs(kd10/kd1-1)*100:.0f}% lower. This compares different cars, not one car over time. Prices within each decile still vary far more than this (Figure 2d). The median surface in Figure 3a slopes along usage and stays flat along age. Figure 3b shows that chance alone moves r in a 5,000-row sample by about ±{se_age[1]:.3f} (95% of samples)."),
('fig', 'F2'),
('fig', 'F3'),
('h2', '2.5  Brand segment and other variables'),
('p', f"Luxury listings carry no price premium. Their mean price is {abs(S['mean_diff_pct']):.2f}% lower than for non-luxury cars and their median {abs(S['median_diff_pct']):.2f}% lower, trivial next to a price SD of INR {D['All']['Car_Price']['sd']/1e6:.2f} million. The 13 brand medians lie within {R['brand_median_range_pct']:.2f}% of each other with overlapping intervals (Figure 4a)."),
('p', f"Among the other numeric fields, only Horsepower (+{CO['Horsepower']['All']['pearson']:.3f}) and Engine_CC (+{CO['Engine_CC']['All']['pearson']:.3f}) exceed ±{up(max(max_other.values()), 3):.3f} in any segment (Figure 4b; Table A2). Other category medians differ by at most {cat_max:.2f}%, and the {MO['spread']:.1f}% spread across the {MO['k']} models is about what chance gives (Table A3). The conclusions hold without Unknown rows, extreme prices or possible duplicates (Table A4)."),
('fig', 'F4'),
('h1', '3  Conclusion and Development Plan'),
('h2', '3.1  Findings'),
('p', f"Price should be described by its median and modelled on a log scale. Usage has a weak negative association with price, Horsepower and Engine_CC weaker positive ones, and age, brand segment, model and the other fields none of practical size. A luxury premium in cash offers is therefore not supported. Any model must also handle Unknown fields ({unk_share:.0f}% of rows) and possible duplicates."),
('h2', '3.2  Limitations and a better approach'),
('p', f"The data are simulated for assessment (UNSW Business School 2026, p. 4), and the macro’s code regenerates Mileage_kmpl, Engine_CC, Horsepower, Kms_Driven and Car_Price without reference to brand or age. This probably explains the missing associations. Each summary also looks at one variable at a time. A straight line of log price on log kilometres (Excel SLOPE and INTERCEPT), fitted and checked on the same listings, misses the listed price by a median of {R['km_logmodel']['mdape']:.1f}%, barely better than quoting the overall median ({R['km_logmodel']['mdape_median_all']:.1f}%). On that line, 10% more kilometres means a price about {abs(per10):.1f}% lower. Offers based on kilometres alone would be unreliable. A better approach would fit a multiple regression on log price, check it on a hold-out sample and quote a price range. The client should also record inspection condition and trim level, and validate any model on its own final sale prices."),
('h2', '3.3  Development plan'),
('p', f"Milestone 2 will test the hypotheses in Table 3. The final report will then fit and validate the regression, allowing for the strong Engine_CC–Horsepower correlation (r = {R['corr_engine_hp']:.2f})."),
('table', 'T3'),
]

REFS = [
    [("Franch, F 2026, ‘Used cars: course and Milestone 1 project’, lecture slides, COMM5000 Data Literacy, University of New South Wales, Sydney, viewed 26 September 2026, <https://moodle.telt.unsw.edu.au>.", False)],
    [("Stable Space 2026, ", False), ("Used car price prediction dataset", True), (", data set, Kaggle, <https://www.kaggle.com/datasets/sharmajicoder/used-car-price-prediction-dataset> (page since removed); randomised copy COMM5000-Used_Car_Price_Prediction.xlsm, UNSW Moodle, viewed 26 September 2026, <https://moodle.telt.unsw.edu.au>.", False)],
    [("UNSW Business School 2026, ", False), ("Assessment guide COMM5000 Data Literacy: case study project, Milestone 1 information", True), (", University of New South Wales, Sydney, viewed 26 September 2026, <https://moodle.telt.unsw.edu.au>.", False)],
]

T1 = {'title': 'Table 1  Data problems and how they were treated', 'widths': [27, 19, 32, 22],
 'head': ['Problem', 'Found with', 'Size', 'Treatment'],
 'rows': [
  ['Brand labels with extra spaces (e.g. ‘\u00a0BMW\u00a0’)', 'TRIM, EXACT', f"{n0(R['brand_relabelled'])} rows ({n0(R['lux_hidden_by_spaces'])} luxury)", 'Trimmed; 13 brands'],
  ['Fuel_Type variants (PETROL, petrol, diesel with spaces, hybridd, electrik)', 'LOWER, TRIM, lookup table', f"{n0(R['fuel_relabelled'])} rows", 'Mapped to CNG, Diesel, Electric, Hybrid, Petrol; Unknown kept'],
  ['Other text fields (Model, Transmission, Owner_Type, Color, City)', 'LEN, TRIM, category lists', 'No variants found', 'None needed'],
  ['‘Unknown’ in Fuel_Type, Transmission, Color, City', 'COUNTIF', f"{n0(R['unknown']['FuelC'])}; {n0(R['unknown']['Transmission'])}; {n0(R['unknown']['Color'])}; {n0(R['unknown']['City'])}. {n0(R['rows_any_unknown'])} rows have at least one", 'Kept as a category'],
  ['Blank cells', 'COUNTBLANK', '0', 'None; the macro fills gaps'],
  ['Zero technical values (the macro sets negative draws to 0)', 'COUNTIF', f"Mileage {R['tech']['Mileage_kmpl']['zero']}; Engine {R['tech']['Engine_CC']['zero']}; Horsepower {R['tech']['Horsepower']['zero']}", 'Blank for that field only'],
  ['Technical values beyond mean ± 3 SD', 'AVERAGEIF, STDEV.S, COUNTIFS', f"Mileage {R['tech']['Mileage_kmpl']['sd3']}; Engine {R['tech']['Engine_CC']['sd3']}; Horsepower {R['tech']['Horsepower']['sd3']} (raw maxima {E['raw_max'][2]:.1f} km/l, {E['raw_max'][0]:,.0f} cc, {E['raw_max'][1]:,.0f} hp)", 'Blank for that field only; far from the main range'],
  ['Isolated values inside the ± 3 SD limits', 'MIN, COUNTIFS', f"hp: {E['hp_lt50']} < 50, {E['hp_gt190']} > 190; cc: {E['cc_lt850']} < 850, {E['cc_gt2250']} > 2,250; km/l: {E['kmpl_lt11']} < 11, {E['kmpl_gt255']} > 25.5; price: {E['p_lt20k']} < INR 20,000", 'Kept; too few to move any median'],
  ['Identical rows on all 20 fields', 'FREQUENCY on Car_Price', '0', 'None needed'],
  ['Repeated rows on the 15 non-randomised fields', 'Sorted key, run count, category shares', f"{n0(dp['obs_pairs'])} pairs in {n0(R['dup15_extra'])} repeat rows; {n0(dp['exp_pairs'])} pairs expected by chance", 'Flagged and kept'],
  ['Kms_Driven above 1,000,000 km', 'COUNTIF; NORM.DIST on LN(km)', f"{n0(R['km_over_1m'])} rows, up to {E['km_max']/1e6:.1f} million km ({n0(R['km_lognorm']['expected_over_1m'])} expected)", 'Excluded from usage analysis only'],
  ['Extreme Car_Price (3 × IQR on log scale)', 'QUARTILE, COUNTIF', f"{R['price_out_low']} low, {R['price_out_high']} high", 'Kept'],
  ['Year and Registration_Age consistency', 'SUMPRODUCT', 'Sum is 2025 in all rows', 'Age used as supplied'],
 ],
 'note': 'Source: calculated from Stable Space (2026). A group of k identical rows gives k(k − 1)/2 pairs and k − 1 repeat rows. The chance count multiplies, over 13 fields, the probability that two random rows share a category (sum of squared shares); Brand and Year are left out because Model and Registration_Age already fix them.'}

DV = [('Car_Price', 'Car_Price (INR)', 0), ('Registration_Age', 'Registration_Age (years)', 1), ('Kms_c', 'Kms_Driven (km)ᵃ', 0), ('Engine_CC_c', 'Engine_CC (cc)ᵇ', 0),
      ('Horsepower_c', 'Horsepower (hp)ᵇ', 1), ('Mileage_kmpl_c', 'Mileage_kmpl (km/l)ᵇ', 2), ('Accidents', 'Accidents (count)', 2)]
def t2rows():
    out = []
    for v, lab, dp_ in DV:
        for g, gl in [('All', 'All'), ('Luxury', 'Luxury'), ('Non-luxury', 'Non-luxury')]:
            d = D[g][v]; f = lambda x: f"{x:,.{dp_}f}"
            out.append([lab if g == 'All' else '', gl, n0(d['n']), f(d['mean']), f(d['median']), f(d['mode']), f(d['sd']), f(d['min']), f(d['max'])])
    return out
T2 = {'title': 'Table 2  Numerical summaries for all listings, luxury (Audi, BMW, Mercedes) and non-luxury listings', 'widths': [22, 10, 10, 10, 10, 9, 10, 8, 11],
 'head': ['Variable', 'Group', 'n', 'Mean', 'Median', 'Modeᶜ', 'SD', 'Min', 'Max'], 'rows': t2rows(), 'num_from': 2, 'group_every': 3,
 'note': 'Source: calculated from Stable Space (2026). ᵃ Kms_Driven ≤ 1,000,000. ᵇ Zeros and values beyond mean ± 3 SD excluded; Min and Max are isolated values (Table 1). ᶜ Exact mode for Registration_Age and Accidents; the continuous variables have no repeated value, so the midpoint of the most frequent class is shown (price 50,000; km 10,000; cc 50; hp 5; km/l 0.5). SD: sample standard deviation.'}

T3 = {'title': 'Table 3  Development plan', 'widths': [24, 11, 38, 27],
 'head': ['Question', 'Stage', 'Method', 'Output'],
 'rows': [
  ['Is vehicle age associated with price?', 'Milestone 2', 'H0: the correlation of age and log price is zero; H1: it is not. Compare age bands', 'Test result and 95% confidence interval'],
  ['How strongly is usage associated with price?', 'Milestone 2', 'H0: the slope of log price on log kilometres is zero; H1: it is not. Compare the two segments', 'Estimated slope with confidence interval'],
  ['Is brand segment associated with price?', 'Milestone 2', 'H0: mean log price is equal for the two segments; H1: it differs. Two-sample t-test', 'Test result and 95% confidence interval'],
  ['Can the fields predict price?', 'Final report', 'Multiple regression on log price; fit on 80% of rows, check on the other 20%', 'Typical error against the median benchmark; price ranges'],
  ['Which listings need a manual check now?', 'Now', 'Compare each listing’s price with the interquartile range for its usage decile (Figure 2d)', 'Listings outside the range sent for manual appraisal'],
  ['Do the choices in Table 1 matter?', 'Both', 'Repeat key results without Unknown rows, extreme values or possible duplicates', 'Conclusions kept only if unchanged'],
 ]}

SH = E['shares']
def pct(c, keys, labels=None): return ', '.join(f"{(labels or {}).get(k, k)} {SH[c][k]*100:.1f}%" for k in keys)
def rng_pct(c, excl='Unknown'):
    v = [x for k, x in SH[c].items() if k != excl]; lo, hi = f"{min(v)*100:.1f}", f"{max(v)*100:.1f}"
    return f"about {lo}% each" if lo == hi else f"{lo}% to {hi}% each"
FIELD_DESC = [
 ('Brand', 'Text', '13 brands after trimming', f"Luxury = Audi, BMW, Mercedes; {rng_pct('BrandC', None)}"), ('Model', 'Text', '39 models, each with one brand', 'About 2.6% each'),
 ('Year', 'Numeric', '2000 to 2024', 'Year + Registration_Age = 2025'), ('Mileage_kmpl', 'Numeric', 'km per litre', 'Fuel efficiency, not distance'),
 ('Engine_CC', 'Numeric', 'cc', ''), ('Horsepower', 'Numeric', 'hp', ''),
 ('Fuel_Type', 'Text', 'CNG, Diesel, Electric, Hybrid, Petrol, Unknown', pct('FuelC', ['Petrol', 'Diesel', 'CNG', 'Electric', 'Hybrid', 'Unknown'])),
 ('Transmission', 'Text', 'Automatic, Manual, Unknown', pct('Transmission', ['Manual', 'Automatic', 'Unknown'])),
 ('Owner_Type', 'Text', 'First, Second, Third, Fourth+', pct('Owner_Type', ['First', 'Second', 'Third', 'Fourth+'])),
 ('Color', 'Text', '7 colours, Unknown', f"{rng_pct('Color')}; Unknown {SH['Color']['Unknown']*100:.1f}%"),
 ('City', 'Text', '8 cities, Unknown', f"{rng_pct('City')}; Unknown {SH['City']['Unknown']*100:.1f}%"),
 ('Kms_Driven', 'Numeric', 'km', 'Usage; cap 1,000,000 for analysis'), ('Insurance_Valid', 'Binary', '1 = valid', f"{R['seg_shares']['All']['ins']*100:.1f}% valid"),
 ('Service_History', 'Binary', '1 = records available', f"{R['seg_shares']['All']['svc']*100:.1f}% available"),
 ('Accidents', 'Numeric', 'count, 0 to 5', f"0: {SH['Accidents']['0.0']*100:.1f}%, 1: {SH['Accidents']['1.0']*100:.1f}%, 2 or more: {sum(v for k, v in SH['Accidents'].items() if float(k) >= 2)*100:.1f}%"),
 ('Tax_Paid', 'Binary', '1 = paid', f"{R['seg_shares']['All']['tax']*100:.1f}% paid"),
 ('Number_of_Doors', 'Numeric', '2, 4 or 5', pct('Number_of_Doors', ['4.0', '5.0', '2.0'], {'4.0': '4:', '5.0': '5:', '2.0': '2:'})),
 ('Seats', 'Numeric', '2, 4, 5 or 7', pct('Seats', ['5.0', '7.0', '4.0', '2.0'], {'5.0': '5:', '7.0': '7:', '4.0': '4:', '2.0': '2:'})),
 ('Registration_Age', 'Numeric', 'years, 1 to 25', 'About 40,000 cars at each age'), ('Car_Price', 'Numeric', 'INR', 'Target variable'),
]
TA1 = {'title': 'Table A1  The 20 fields in the dataset, with the share of listings in each category', 'widths': [17, 9, 29, 45], 'head': ['Field', 'Type', 'Unit or values', 'Note'], 'rows': [list(x) for x in FIELD_DESC],
 'note': f"Source: calculated from Stable Space (2026). Shares are of all 1,005,000 listings; no share differs by more than {E['seg_share_maxdiff_pp']:.1f} percentage points between the luxury and non-luxury segments."}
ORD = ['Kms_Driven (≤1m km)', 'Horsepower', 'Engine_CC', 'Tax_Paid', 'Number_of_Doors', 'Mileage_kmpl', 'Registration_Age', 'Year', 'Insurance_Valid', 'Service_History', 'Accidents', 'Seats']
TA2 = {'title': 'Table A2  Pearson correlation between Car_Price and each numeric field', 'widths': [34, 22, 22, 22], 'head': ['Field', 'All', 'Luxury', 'Non-luxury'],
 'rows': [[k.replace(' (≤1m km)', ' (≤ 1,000,000 km)')] + [f"{CO[k][g]['pearson']:+.4f}" for g in ['All', 'Luxury', 'Non-luxury']] for k in ORD], 'num_from': 1,
 'note': 'Source: calculated from Stable Space (2026). Engine_CC and Horsepower are strongly correlated with each other (r = ' + f"{R['corr_engine_hp']:.2f}" + ').'}
def ta3():
    out = []
    for lab, key in [('Fuel_Type', 'Fuel_Type'), ('Transmission', 'Transmission'), ('Owner_Type', 'Owner_Type'), ('Color', 'Color'), ('City', 'City')]:
        v = {a: b for a, b in CM[key].items() if a != '_range_pct'}; lo = min(v, key=lambda a: v[a]['median']); hi = max(v, key=lambda a: v[a]['median'])
        nk = {'Fuel_Type': 'FuelC'}.get(key, key)
        out.append([lab, str(len(v)), f"{n0(E['catn'][nk][0])} to {n0(E['catn'][nk][1])}", f"{lo} ({n0(v[lo]['median'])})", f"{hi} ({n0(v[hi]['median'])})", f"{CM[key]['_range_pct']:.2f}%"])
    out.append(['Model', str(MO['k']), f"{n0(MO['nmin'])} to {n0(MO['nmax'])}", f"{MO['lo'][0]} ({n0(MO['lo'][1])})", f"{MO['hi'][0]} ({n0(MO['hi'][1])})", f"{MO['spread']:.2f}%"])
    return out
TA3 = {'title': 'Table A3  Median Car_Price across categories (INR)', 'widths': [15, 11, 19, 22, 22, 11], 'head': ['Field', 'Categories', 'Rows per category', 'Lowest median', 'Highest median', 'Spread'], 'rows': ta3(), 'num_from': 5,
 'note': f"Source: calculated from Stable Space (2026). Spread = highest median / lowest median − 1. For {MO['cover']} of the {MO['k']} models, the 95% interval of the median contains the overall median."}
def ta4():
    s = R['sens']; out = []
    for key, lab in [('baseline', 'All rows'), ('drop_any_unknown', 'Without rows containing Unknown'), ('drop_price_outliers', 'Without the 3 extreme prices'), ('drop_dup15', 'First row of each 15-field match only')]:
        v = s[key]
        out.append([lab, n0(v['n']), n0(v['median']), f"{v['r_age']:+.5f}" if key != 'drop_dup15' else '', f"{v['r_km']:+.4f}" if key != 'drop_dup15' else '', f"{v['lux_med_gap']:+.2f}%"])
    for key, lab in [('500000.0', 'Kms cap 500,000'), ('750000.0', 'Kms cap 750,000'), ('1500000.0', 'Kms cap 1,500,000'), ('None', 'No kms cap')]:
        v = R['km_caps'][key]; out.append([lab, n0(v['n']), '', '', f"{v['r']:+.4f}", ''])
    return out
TA4 = {'title': 'Table A4  Sensitivity of the main results to the cleaning choices', 'widths': [31, 12, 14, 12, 12, 19], 'head': ['Scenario', 'Rows', 'Median price', 'r (age)', 'r (km)', 'Luxury median gap'], 'rows': ta4(), 'num_from': 1,
 'note': 'Source: calculated from Stable Space (2026). The duplicate scenario uses a sorted copy holding only price and segment.'}
APPX = ['TA1', 'TA2', 'TA3', 'TA4']
TABLES = {'T1': T1, 'T2': T2, 'T3': T3, 'TA1': TA1, 'TA2': TA2, 'TA3': TA3, 'TA4': TA4}
for _t in (TA1, TA2, TA3, TA4): _t['font'] = 8

FIGS = {
 'F1': ('fig/Figure1_price_distribution.png', f"Figure 1  Distribution of Car_Price (n = {n0(R['n_all'])}). (a) Raw scale in INR 50,000 classes; the {E['share_over_5m']*100:.1f}% of listings above INR 5 million are not shown. (b) Log scale by segment. M = million, k = thousand. Source: calculated from Stable Space (2026).", 15.5),
 'F2': ('fig/Figure2_price_age_usage.png', 'Figure 2  Car_Price against Registration_Age (a, b) and Kms_Driven (c, d). (a) and (c) Random samples of 5,000 listings (orange = luxury, blue = non-luxury); ages in (a) are spread by up to 0.3 years so that points do not overlap. (b) and (d) Medians by segment with the interquartile range (IQR) for all listings; (c) and (d) use listings with Kms_Driven ≤ 1,000,000. Source: calculated from Stable Space (2026).', 14.5),
 'F3': ('fig/Figure3_surface_sampling.png', 'Figure 3  (a) Median Car_Price by five-year age band and usage decile, about 20,000 listings per cell; the vertical axis starts at INR 560,000. (b) Expected spread of the correlation in a random sample of 5,000 rows (normal approximation); vertical lines mark the full-data values and triangles the samples used in Figure 2. Source: calculated from Stable Space (2026).', 15.0),
 'F4': ('fig/Figure4_segment_correlations.png', f"Figure 4  (a) Median Car_Price by brand and segment (orange = luxury, blue = non-luxury) with 95% intervals (ranks n/2 ± 1.96√n/2 of the sorted prices); the axis does not start at zero and the dashed line is the overall median. The 95% confidence interval for the luxury minus non-luxury difference in mean price, as a percentage of the non-luxury mean, is {ci_lo:.2f}% to +{ci_hi:.2f}%. (b) Pearson correlation of each numeric field with Car_Price. Source: calculated from Stable Space (2026).", 15.5),
}

def body_word_count():
    return sum(len(re.sub(r'<[^>]+>', '', b[1]).split()) for b in BODY if b[0] in ('h1', 'h2', 'p'))

if __name__ == '__main__':
    doc = {'title': TITLE, 'sub': SUB, 'wc': body_word_count(), 'body': [], 'refs': REFS, 'tables': {k: dict(v, rows=[[mn(c) for c in r] for r in v['rows']]) for k, v in TABLES.items()},
           'figs': {k: (f, mn(c), w) for k, (f, c, w) in FIGS.items()}, 'appx': APPX}
    for b in BODY:
        doc['body'].append([b[0], mn(b[1]) if b[0] == 'p' else b[1]])
    json.dump(doc, open('doc.json', 'w'), ensure_ascii=False, indent=1)
    print('body words', doc['wc'])
