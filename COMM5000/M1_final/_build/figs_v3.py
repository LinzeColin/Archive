import pandas as pd, numpy as np, json, math
import matplotlib as mpl, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter
from matplotlib import colors
from mpl_toolkits.mplot3d import Axes3D  # noqa

mpl.rcParams.update({
    'font.family': ['Liberation Sans', 'DejaVu Sans'], 'font.size': 7, 'axes.labelsize': 7, 'xtick.labelsize': 6.3, 'ytick.labelsize': 6.3,
    'legend.fontsize': 6.3, 'axes.linewidth': 0.5, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'xtick.minor.width': 0.4, 'ytick.minor.width': 0.4,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'xtick.minor.size': 1.5, 'ytick.minor.size': 1.5, 'xtick.direction': 'out', 'ytick.direction': 'out',
    'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False, 'savefig.dpi': 600, 'pdf.fonttype': 42, 'svg.fonttype': 'none',
    'axes.edgecolor': '#222222', 'axes.labelcolor': '#222222', 'xtick.color': '#222222', 'ytick.color': '#222222', 'text.color': '#222222',
    'axes.unicode_minus': True, 'lines.linewidth': 1.0})
NON = '#2a6fbf'; LUX = '#e0662f'; INK = '#222222'; GREY = '#9a9a9a'; LIGHT = '#e9e9e9'
SEQ = ['#d7e6f7', '#a9c9ee', '#74a6e2', '#4787d3', '#2a6fbf', '#1d5496', '#123a6b']
W = 6.5  # inches, Word text width

df = pd.read_pickle('clean.pkl'); R = json.load(open('results.json'))
P = df.Car_Price; lux = df.Segment == 'Luxury'
def kfmt(x, pos=None):
    if x >= 1e6: return f'{x/1e6:g}M'
    if x >= 1e3: return f'{x/1e3:g}k'
    return f'{x:g}'
KF = FuncFormatter(kfmt)
def letter(ax, s, x=-0.14, y=1.02):
    ax.text(x, y, f'({s})', transform=ax.transAxes, fontsize=8.5, fontweight='bold', va='bottom', ha='left')
def save(fig, name):
    fig.savefig(f'fig/{name}.png', bbox_inches='tight', pad_inches=0.02, metadata={'Software': None})
    fig.savefig(f'fig/{name}.pdf', bbox_inches='tight', pad_inches=0.02, metadata={'Creator': None, 'Producer': None})
    plt.close(fig)

# ---------- Figure 1: distribution of Car_Price ----------
fig, axs = plt.subplots(1, 2, figsize=(W, 2.15), gridspec_kw={'wspace': 0.32, 'width_ratios': [1.1, 1]})
ax = axs[0]; bins = np.arange(0, 5.0e6 + 1, 50000)
h, _ = np.histogram(P, bins)
ax.bar(bins[:-1], h / 1000, width=50000, align='edge', color='#b9cfe9', edgecolor='white', linewidth=0.15)
mean, med = P.mean(), P.median(); mode = R['desc']['All']['Car_Price']['mode']
for v, lab, c, ls in [(mode, 'Modal class', GREY, (0, (2, 1.5))), (med, 'Median', INK, '-'), (mean, 'Mean', LUX, '-')]:
    ax.axvline(v, color=c, lw=0.9, ls=ls, label=f'{lab} ({v/1e3:,.0f}k)')
ax.set_xlim(0, 5e6); ax.xaxis.set_major_formatter(KF)
ax.set_xlabel('Car_Price (INR)'); ax.set_ylabel('Listings (thousands)')
ax.legend(loc='upper right', handlelength=1.6)
letter(ax, 'a')
ax = axs[1]; lb = np.linspace(np.log10(1e4), np.log10(3e7), 70)
for m, c, lab, ls, lw in [(~lux, NON, 'Non-luxury', '-', 1.4), (lux, LUX, 'Luxury', (0, (3, 1.6)), 1.1)]:
    hh, _ = np.histogram(np.log10(P[m]), lb, density=True)
    ax.plot(10 ** ((lb[:-1] + lb[1:]) / 2), hh, color=c, lw=lw, ls=ls, label=lab)
ax.set_xscale('log'); ax.xaxis.set_major_formatter(KF); ax.xaxis.set_minor_formatter(NullFormatter()); ax.set_xlim(2e4, 2e7); ax.set_ylim(0, None)
ax.set_xlabel('Car_Price (INR, log scale)'); ax.set_ylabel('Density of log$_{10}$ price')
ax.legend(loc='upper right', handlelength=2)
letter(ax, 'b')
save(fig, 'Figure1_price_distribution')

# ---------- Figure 2: price vs age and usage ----------
MAP = json.load(open('COMM5000_M1_Working.xlsx.map.json'))
byrow = df.set_index('ExcelRow')
sA = byrow.loc[MAP['sample_rows']].reset_index(); sK = byrow.loc[MAP['sample_rows_km']].reset_index(); kv = df.dropna(subset=['Kms_c'])
assert sK.Kms_Driven.le(1e6).all() and len(sA) == 5000 and len(sK) == 5000
rng = np.random.default_rng(26092026)
fig, axs = plt.subplots(2, 2, figsize=(W, 4.3), gridspec_kw={'hspace': 0.45, 'wspace': 0.3})
ax = axs[0, 0]; j = rng.uniform(-0.3, 0.3, len(sA))
for m, c in [(sA.Segment == 'Non-luxury', NON), (sA.Segment == 'Luxury', LUX)]:
    ax.scatter(sA.Registration_Age[m] + j[m], sA.Car_Price[m], s=1.3, color=c, alpha=0.45, lw=0, rasterized=True)
ax.set_yscale('log'); ax.yaxis.set_major_formatter(KF); ax.yaxis.set_minor_formatter(NullFormatter()); ax.set_ylim(2e4, 2e7); ax.set_xlim(0, 26)
ax.set_xlabel('Registration_Age (years)'); ax.set_ylabel('Car_Price (INR, log scale)'); letter(ax, 'a')
ax = axs[0, 1]; ages = np.arange(1, 26); aq = np.array([R['age_iqr'][str(a)] for a in ages])
ax.fill_between(ages, aq[:, 0], aq[:, 2], color=LIGHT, lw=0, label='IQR, all')
for seg, c, mk in [('Non-luxury', NON, 'o'), ('Luxury', LUX, 's')]:
    med_s = df[df.Segment == seg].groupby('Registration_Age').Car_Price.median()
    ax.plot(med_s.index, med_s.values, color=c, lw=1, marker=mk, ms=2.4, label=('Median, non-lux.' if seg == 'Non-luxury' else 'Median, lux.'))
ax.set_ylim(0, 1.75e6); ax.set_yticks(np.arange(0, 1.51e6, 2.5e5)); ax.set_xlim(0.5, 25.5); ax.yaxis.set_major_formatter(KF)
ax.set_xlabel('Registration_Age (years)'); ax.set_ylabel('Car_Price (INR)'); ax.legend(loc='upper center', ncol=3, columnspacing=1.0, handlelength=1.3, bbox_to_anchor=(0.55, 1.03), fontsize=6); letter(ax, 'b')
ax = axs[1, 0]
for m, c in [(sK.Segment == 'Non-luxury', NON), (sK.Segment == 'Luxury', LUX)]:
    ax.scatter(sK.Kms_c[m], sK.Car_Price[m], s=1.3, color=c, alpha=0.45, lw=0, rasterized=True)
ax.set_xscale('log'); ax.set_yscale('log')
for a in (ax.xaxis, ax.yaxis): a.set_major_formatter(KF); a.set_minor_formatter(NullFormatter())
ax.set_ylim(2e4, 2e7); ax.set_xlim(5e3, 1.05e6)
ax.set_xlabel('Kms_Driven (km, log scale; ≤ 1,000,000)'); ax.set_ylabel('Car_Price (INR, log scale)'); letter(ax, 'c')
ax = axs[1, 1]; dec = np.arange(1, 11); kq = np.array([R['km_dec_iqr']['All'][str(d - 1)] for d in dec])
ax.fill_between(dec, kq[:, 0], kq[:, 2], color=LIGHT, lw=0, label='IQR, all')
for seg, c, mk in [('Non-luxury', NON, 'o'), ('Luxury', LUX, 's')]:
    q = np.array([R['km_dec_iqr'][seg][str(d - 1)][1] for d in dec])
    ax.plot(dec, q, color=c, lw=1, marker=mk, ms=2.6, label=('Median, non-lux.' if seg == 'Non-luxury' else 'Median, lux.'))
ax.set_ylim(0, 1.75e6); ax.set_yticks(np.arange(0, 1.51e6, 2.5e5)); ax.set_xlim(0.5, 10.5); ax.set_xticks(dec); ax.set_xticklabels([f'D{d}' for d in dec]); ax.yaxis.set_major_formatter(KF)
ax.set_xlabel('Kms_Driven decile (D1 lowest, D10 highest)'); ax.set_ylabel('Car_Price (INR)'); ax.legend(loc='upper center', ncol=3, columnspacing=1.0, handlelength=1.3, bbox_to_anchor=(0.55, 1.03), fontsize=6); letter(ax, 'd')
save(fig, 'Figure2_price_age_usage')

# ---------- Figure 3: 3D median surface + sampling variability ----------
kv2 = kv.copy(); kv2['dec'] = pd.qcut(kv2.Kms_c, 10, labels=False); kv2['ab'] = ((kv2.Registration_Age - 1) // 5).astype(int)
grid = kv2.groupby(['ab', 'dec']).Car_Price.median().unstack(); cnt = kv2.groupby(['ab', 'dec']).size()
R['landscape'] = dict(cells=int(grid.size), min_n=int(cnt.min()), max_n=int(cnt.max()), zmin=float(grid.values.min()), zmax=float(grid.values.max()))
fig = plt.figure(figsize=(W, 2.75))
ax = fig.add_axes([-0.02, -0.04, 0.58, 1.08], projection='3d')
Dk, Ag = np.meshgrid(grid.columns.values + 1, grid.index.values * 5 + 3, indexing='xy'); Z = grid.values / 1e3
cmap = colors.LinearSegmentedColormap.from_list('b', SEQ[1:]); norm = colors.Normalize(Z.min() - 10, Z.max())
ax.plot_surface(Dk, Ag, Z, facecolors=cmap(norm(Z)), rstride=1, cstride=1, linewidth=0.4, edgecolor=(1, 1, 1, 0.9), antialiased=True, shade=False)
ax.contourf(Dk, Ag, Z, zdir='z', offset=560, levels=10, cmap=cmap, alpha=0.3)
ax.set_zlim(560, 790); ax.view_init(elev=22, azim=-62)
ax.set_xlabel('Kms_Driven decile', labelpad=-4); ax.set_ylabel('Registration_Age (years)', labelpad=-2); ax.set_zlabel('Median Car_Price (INR k)', labelpad=-3)
ax.tick_params(pad=-3, labelsize=5.8)
for a in (ax.xaxis, ax.yaxis, ax.zaxis):
    a.pane.set_facecolor((1, 1, 1, 0)); a.pane.set_edgecolor('#cccccc'); a._axinfo['grid'].update(color='#e3e3e3', linewidth=0.4)
ax.set_xticks([1, 4, 7, 10]); ax.set_xticklabels(['D1', 'D4', 'D7', 'D10'])
ax.set_yticks([3, 8, 13, 18, 23]); ax.set_yticklabels(['1–5', '6–10', '11–15', '16–20', '21–25'])
ax.set_zticks([600, 650, 700, 750])
fig.text(0.03, 0.93, '(a)', fontsize=8.5, fontweight='bold')
ax2 = fig.add_axes([0.66, 0.2, 0.32, 0.68])
from scipy import stats as st
xs = np.linspace(-0.11, 0.07, 600); n_s = 5000
for key, lab, c, sref in [('age', 'Price and age', '#8c8c8c', sA), ('km', 'Price and kilometres', NON, sK)]:
    r0 = R['rel']['All'][key]['pearson']; se = (1 - r0 ** 2) / math.sqrt(n_s - 1)
    ax2.fill_between(xs, st.norm.pdf(xs, r0, se), color=c, alpha=0.28, lw=0)
    ax2.plot(xs, st.norm.pdf(xs, r0, se), color=c, lw=1, label=lab)
    ax2.axvline(r0, color=c, lw=0.8)
    rs_ = np.corrcoef(sref.iloc[:, sref.columns.get_loc('Registration_Age' if key == 'age' else 'Kms_Driven')], sref.Car_Price)[0, 1]
    ax2.plot([rs_], [0.6], marker='v', color=INK, ms=4)
ax2.set_ylim(0, None); ax2.set_xlabel('Pearson r in a random sample of 5,000'); ax2.set_ylabel('Density')
ax2.set_ylim(0, 36); ax2.legend(loc='upper right', handlelength=1.4)
fig.text(0.6, 0.93, '(b)', fontsize=8.5, fontweight='bold')
save(fig, 'Figure3_surface_sampling')

# ---------- Figure 4: brands and correlations ----------
def med_ci(x):
    x = np.sort(np.asarray(x)); n = len(x); k = 1.96 * math.sqrt(n) / 2
    return np.median(x), x[max(int(n / 2 - k), 0)], x[min(int(n / 2 + k), n - 1)]
fig, axs = plt.subplots(1, 2, figsize=(W, 2.75), gridspec_kw={'wspace': 0.75, 'width_ratios': [1, 1.05]})
ax = axs[0]; rows = []
for b_, g in df.groupby('BrandC'):
    m, l, h_ = med_ci(g.Car_Price.values); rows.append((b_, m, l, h_))
rows.sort(key=lambda r: r[1]); LB = {'Audi', 'BMW', 'Mercedes'}
for i, (b_, m, l, h_) in enumerate(rows):
    c = LUX if b_ in LB else NON
    ax.plot([l / 1e3, h_ / 1e3], [i, i], color=c, lw=1.1); ax.plot(m / 1e3, i, 'o', color=c, ms=3)
segs = []
for j, (s_, c) in enumerate([('Non-luxury', NON), ('Luxury', LUX)]):
    m, l, h_ = med_ci(df.Car_Price[df.Segment == s_].values); y = len(rows) + 0.8 + j
    ax.plot([l / 1e3, h_ / 1e3], [y, y], color=c, lw=1.8); ax.plot(m / 1e3, y, 'D', color=c, ms=3.4)
ax.axvline(P.median() / 1e3, color=GREY, lw=0.6, ls=(0, (2, 1.5)))
ax.set_yticks(list(range(len(rows))) + [len(rows) + 0.8, len(rows) + 1.8]); ax.set_yticklabels([r[0] for r in rows] + ['Non-luxury (all)', 'Luxury (all)'])
ax.axhline(len(rows) + 0.3, color='#cccccc', lw=0.5)
ax.set_xlabel('Median Car_Price (INR thousand, 95% CI)'); letter(ax, 'a', x=-0.5)
ax = axs[1]
order = ['Kms_Driven (≤1m km)', 'Horsepower', 'Engine_CC', 'Tax_Paid', 'Number_of_Doors', 'Mileage_kmpl', 'Registration_Age', 'Year', 'Insurance_Valid', 'Service_History', 'Accidents', 'Seats']
C = R['corr_all']; y = np.arange(len(order))[::-1]
for g, c, mk, off in [('All', INK, 'o', 0), ('Luxury', LUX, 's', -0.22), ('Non-luxury', NON, '^', 0.22)]:
    ax.scatter([C[v][g]['pearson'] for v in order], y + off, s=7, color=c, marker=mk, label=g, zorder=3, lw=0)
ax.axvline(0, color=GREY, lw=0.6)
ax.set_yticks(y); ax.set_yticklabels([v.replace(' (≤1m km)', '') for v in order]); ax.set_xlim(-0.07, 0.05)
ax.set_xlabel('Pearson r with Car_Price'); ax.legend(loc='lower right', handletextpad=0.2); letter(ax, 'b', x=-0.55)
save(fig, 'Figure4_segment_correlations')
json.dump(R, open('results.json', 'w'), indent=1)
print('figs ok', R['landscape'])
