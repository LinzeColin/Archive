import pandas as pd, numpy as np, json, math, os
import matplotlib as mpl, matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullFormatter, FixedLocator
from matplotlib import colors, patheffects
from mpl_toolkits.mplot3d import Axes3D  # noqa
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from scipy import stats as st

mpl.rcParams.update({
    'font.family': ['Liberation Sans', 'DejaVu Sans'], 'font.size': 7, 'axes.labelsize': 7, 'xtick.labelsize': 6.2, 'ytick.labelsize': 6.2,
    'legend.fontsize': 6.2, 'axes.linewidth': 0.5, 'xtick.major.width': 0.5, 'ytick.major.width': 0.5, 'xtick.minor.width': 0.4, 'ytick.minor.width': 0.4,
    'xtick.major.size': 2.5, 'ytick.major.size': 2.5, 'xtick.minor.size': 1.5, 'ytick.minor.size': 1.5, 'xtick.direction': 'out', 'ytick.direction': 'out',
    'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False, 'savefig.dpi': 600, 'pdf.fonttype': 42, 'svg.fonttype': 'none',
    'axes.edgecolor': '#222222', 'axes.labelcolor': '#222222', 'xtick.color': '#222222', 'ytick.color': '#222222', 'text.color': '#222222',
    'axes.unicode_minus': True, 'lines.linewidth': 1.0, 'image.interpolation': 'nearest'})
NON = '#2a6fbf'; LUX = '#e0662f'; INK = '#1c1c1c'; GREY = '#8f8f8f'; LIGHT = '#ececec'
W = 6.5
OUT = 'fig4'; os.makedirs(OUT, exist_ok=True)
# perceptual sequential map (white -> teal -> deep navy) for densities, and a warm-cool map for the surface
DENS = colors.LinearSegmentedColormap.from_list('dens', ['#ffffff', '#e4eef6', '#b7d3e8', '#79aed3', '#3f86bd', '#1f5c9a', '#0d3565', '#061a36'])
SURF = colors.LinearSegmentedColormap.from_list('surf', ['#2c1a5c', '#3b4d9a', '#2f82b0', '#35b0a4', '#8fd07a', '#f0e35c'])

df = pd.read_pickle('clean.pkl'); R = json.load(open('results.json')); E = json.load(open('extra.json'))
MAP = json.load(open('COMM5000_M1_Working.xlsx.map.json'))
P = df.Car_Price.values; lux = (df.Segment == 'Luxury').values
def kfmt(x, pos=None):
    if x >= 1e6: return f'{x/1e6:g}M'
    if x >= 1e3: return f'{x/1e3:g}k'
    return f'{x:g}'
KF = FuncFormatter(kfmt)
def letter(fig_or_ax, s, x, y, fig=False):
    t = (fig_or_ax.transFigure if fig else fig_or_ax.transAxes)
    fig_or_ax.text(x, y, s, transform=t, fontsize=8.5, fontweight='bold', va='bottom', ha='left')
def save(fig, name):
    fig.savefig(f'{OUT}/{name}.png', bbox_inches='tight', pad_inches=0.03, metadata={'Software': None})
    fig.savefig(f'{OUT}/{name}.pdf', bbox_inches='tight', pad_inches=0.03, metadata={'Creator': None, 'Producer': None})
    plt.close(fig)
def logticks(ax, axis='y', lo=1e4, hi=1e8):
    a = ax.yaxis if axis == 'y' else ax.xaxis
    a.set_major_formatter(KF); a.set_minor_formatter(NullFormatter())
halo = [patheffects.withStroke(linewidth=1.6, foreground='white')]

# ============ Figure 1: distribution of Car_Price ============
fig = plt.figure(figsize=(W, 2.45))
gs = fig.add_gridspec(2, 2, height_ratios=[0.16, 1], width_ratios=[1.08, 1], hspace=0.04, wspace=0.3)
axb = fig.add_subplot(gs[0, 0]); ax = fig.add_subplot(gs[1, 0], sharex=axb)
bins = np.arange(0, 5.0e6 + 1, 50000); h, _ = np.histogram(P, bins)
mean, med = P.mean(), np.median(P); mode = R['desc']['All']['Car_Price']['mode']
q05, q25, q75, q95 = np.percentile(P, [5, 25, 75, 95])
cm_bar = colors.LinearSegmentedColormap.from_list('bar', ['#9cc0e6', '#2a6fbf'])
bar_c = [cm_bar(0.85) if (q25 <= b < q75) else cm_bar(0.12) for b in bins[:-1]]
ax.bar(bins[:-1], h / 1000, width=50000, align='edge', color=bar_c, edgecolor='white', linewidth=0.12)
# smooth outline from the log-normal-like shape (kernel density on the raw scale, drawn on the histogram scale)
ax.step(bins, np.r_[h / 1000, 0], where='post', color='#0d3565', lw=0.55)
ym = h.max() / 1000 * 1.08
for v, lab, c, ls in [(mode, 'Modal class', GREY, (0, (2, 1.4))), (med, 'Median', INK, '-'), (mean, 'Mean', LUX, '-')]:
    ax.axvline(v, color=c, lw=0.85, ls=ls, zorder=3, label=f'{lab} ({v/1e3:,.0f}k)')
ax.annotate('', xy=(mean, ym * 0.5), xytext=(med, ym * 0.5), arrowprops=dict(arrowstyle='-|>', lw=0.7, color=LUX, shrinkA=0, shrinkB=0, mutation_scale=6), zorder=4)
ax.text(mean + 60000, ym * 0.5, f'mean {R["mean_over_median_pct"]:.1f}%\nabove median', color=LUX, ha='left', va='center', fontsize=5.8, linespacing=1.0, path_effects=halo)
ax.legend(loc='upper right', handlelength=1.6, bbox_to_anchor=(1.0, 1.0))
ax.set_xlim(0, 5e6); ax.set_ylim(0, ym); ax.xaxis.set_major_formatter(KF)
ax.set_xlabel('Car_Price (INR)'); ax.set_ylabel('Listings (thousands)')
# marginal box strip: P5-P95 whiskers, IQR box, median, mean
axb.axis('off'); y0 = 0.5
axb.plot([q05, q95], [y0, y0], color=INK, lw=0.6); axb.plot([q05, q05], [y0 - .18, y0 + .18], color=INK, lw=0.6); axb.plot([q95, q95], [y0 - .18, y0 + .18], color=INK, lw=0.6)
axb.add_patch(mpl.patches.FancyBboxPatch((q25, y0 - 0.32), q75 - q25, 0.64, boxstyle='round,pad=0,rounding_size=0.08', fc=cm_bar(0.85), ec=INK, lw=0.5, mutation_aspect=0.5))
axb.plot([med, med], [y0 - 0.32, y0 + 0.32], color='white', lw=1.1); axb.plot(mean, y0, 'D', ms=3, color=LUX, mec='white', mew=0.4)
axb.set_ylim(0, 1); axb.text(q95 + 60000, y0, 'P5–P95 whiskers, IQR box', va='center', fontsize=5.8, color='#555555')
letter(axb, 'a', -0.13, 0.35)
# (b) mirrored log-scale densities with a percentile-percentile inset
ax = fig.add_subplot(gs[:, 1])
lb = np.linspace(np.log10(1.5e4), np.log10(3e7), 90); mid = 10 ** ((lb[:-1] + lb[1:]) / 2)
hL, _ = np.histogram(np.log10(P[lux]), lb, density=True); hN, _ = np.histogram(np.log10(P[~lux]), lb, density=True)
ax.fill_between(mid, 0, hL, color=LUX, alpha=0.75, lw=0, step='mid'); ax.fill_between(mid, 0, -hN, color=NON, alpha=0.75, lw=0, step='mid')
ax.plot(mid, hN, color=NON, lw=0.7, ls=(0, (2.2, 1.2)), drawstyle='steps-mid'); ax.plot(mid, -hL, color=LUX, lw=0.7, ls=(0, (2.2, 1.2)), drawstyle='steps-mid')
ax.axhline(0, color='white', lw=0.8)
for m_, c in [(lux, LUX), (~lux, NON)]:
    ax.axvline(np.median(P[m_]), color=c, lw=0.6, ymin=0.5 if c == LUX else 0, ymax=1 if c == LUX else 0.5)
ax.set_xscale('log'); logticks(ax, 'x'); ax.set_xlim(2e4, 2e7)
yl = max(hL.max(), hN.max()) * 1.12; ax.set_ylim(-yl, yl)
ax.set_yticks([-1, -0.5, 0, 0.5, 1]); ax.set_yticklabels(['1.0', '0.5', '0', '0.5', '1.0'])
ax.set_xlabel('Car_Price (INR, log scale)'); ax.set_ylabel('Density of log$_{10}$ price')
ax.text(1.9e7, yl * 0.9, f'Luxury\nn = {lux.sum():,}', color=LUX, fontsize=6.2, fontweight='bold', ha='right', va='top', linespacing=1.05)
ax.text(1.9e7, -yl * 0.9, f'Non-luxury\nn = {(~lux).sum():,}', color=NON, fontsize=6.2, fontweight='bold', ha='right', va='bottom', linespacing=1.05)
ins = ax.inset_axes([0.15, 0.63, 0.24, 0.3])
pp = np.arange(1, 100); qL = np.percentile(P[lux], pp); qN = np.percentile(P[~lux], pp)
ins.plot([2e4, 2e7], [2e4, 2e7], color=GREY, lw=0.5, ls=(0, (2, 1.5)))
ins.scatter(qN, qL, s=2.2, c=pp, cmap=SURF, lw=0, zorder=3)
ins.set_xscale('log'); ins.set_yscale('log'); ins.set_xlim(1.2e5, 5e6); ins.set_ylim(1.2e5, 5e6)
for a in (ins.xaxis, ins.yaxis): a.set_major_locator(FixedLocator([2e5, 2e6])); a.set_major_formatter(KF); a.set_minor_formatter(NullFormatter())
ins.tick_params(labelsize=5, length=1.5, pad=1); ins.set_xlabel('Non-luxury', fontsize=5.2, labelpad=0.5, path_effects=halo); ins.set_ylabel('Luxury', fontsize=5.2, labelpad=0.5)
ins.set_title('Percentiles 1–99', fontsize=5.4, pad=1.5)
for s in ('top', 'right'): ins.spines[s].set_visible(True)
ins.set_facecolor('#fbfbfb')
letter(ax, 'b', -0.2, 1.0)
save(fig, 'Figure1_price_distribution')

# ============ Figure 2: price vs age and usage ============
byrow = df.set_index('ExcelRow')
sA = byrow.loc[MAP['sample_rows']].reset_index(); sK = byrow.loc[MAP['sample_rows_km']].reset_index(); kv = df.dropna(subset=['Kms_c'])
assert sK.Kms_Driven.le(1e6).all() and len(sA) == 5000 and len(sK) == 5000
rng = np.random.default_rng(26092026)
fig, axs = plt.subplots(2, 2, figsize=(W, 3.7), gridspec_kw={'hspace': 0.58, 'wspace': 0.34})
YL = (2e4, 3e7); ybins = np.logspace(np.log10(YL[0]), np.log10(YL[1]), 75)
ages = np.arange(1, 26); aq = np.array([R['age_iqr'][str(a)] for a in ages])
# (a) sample scatter with the full-data quartile lines
ax = axs[0, 0]; j = rng.uniform(-0.3, 0.3, len(sA))
for m, c in [(sA.Segment == 'Non-luxury', NON), (sA.Segment == 'Luxury', LUX)]:
    ax.scatter(sA.Registration_Age[m] + j[m], sA.Car_Price[m], s=1.2, color=c, alpha=0.5, lw=0, rasterized=True)
ax.plot(ages, aq[:, 1], color=INK, lw=1.1, path_effects=halo, label='Median, full data')
ax.plot(ages, aq[:, 0], color=INK, lw=0.7, ls=(0, (2.5, 1.5)), path_effects=halo, label='Q1 and Q3, full data'); ax.plot(ages, aq[:, 2], color=INK, lw=0.7, ls=(0, (2.5, 1.5)), path_effects=halo)
ax.set_yscale('log'); logticks(ax); ax.set_ylim(*YL); ax.set_xlim(0, 26)
ax.set_xlabel('Registration_Age (years)'); ax.set_ylabel('Car_Price (INR, log scale)')
ax.legend(loc='upper center', ncol=2, bbox_to_anchor=(0.5, 1.13), handlelength=1.8, columnspacing=1.0, fontsize=5.8)
ax.text(0.98, 0.03, f'r = {R["rel"]["All"]["age"]["pearson"]:+.4f} (full data)'.replace('-', '−'), transform=ax.transAxes, ha='right', fontsize=5.8, path_effects=halo)
letter(ax, 'a', -0.2, 1.04)
# (b) conditional density of price at each age (every listing), segment medians
def cond_heat(ax, xcat, y, xedges, ylab_off=False):
    H, _, _ = np.histogram2d(xcat, y, bins=[xedges, ybins]); H = H / H.sum(axis=1, keepdims=True) * 100
    im = ax.pcolormesh(xedges, ybins, H.T, cmap=DENS, shading='flat', rasterized=True, vmin=0, vmax=np.percentile(H, 99.5))
    ax.set_yscale('log'); logticks(ax); ax.set_ylim(*YL)
    return im
im = cond_heat(axs[0, 1], df.Registration_Age.values, P, np.arange(0.5, 26))
ax = axs[0, 1]
ax.plot(ages, aq[:, 0], color='white', lw=0.7, ls=(0, (2.5, 1.5))); ax.plot(ages, aq[:, 2], color='white', lw=0.7, ls=(0, (2.5, 1.5)))
for seg, c in [('Non-luxury', NON), ('Luxury', LUX)]:
    med_s = df[df.Segment == seg].groupby('Registration_Age').Car_Price.median()
    ax.plot(med_s.index, med_s.values, color=c, lw=1.1, marker='o' if seg == 'Non-luxury' else 's', ms=1.8, path_effects=halo, label=f'Median, {seg.lower()}')
ax.set_xlim(0.5, 25.5); ax.set_xlabel('Registration_Age (years)'); ax.set_ylabel('Car_Price (INR, log scale)')
ax.legend(loc='upper center', ncol=2, bbox_to_anchor=(0.5, 1.13), handlelength=1.6, columnspacing=1.0, fontsize=5.8)
cax = ax.inset_axes([1.03, 0.1, 0.03, 0.8]); cb = fig.colorbar(im, cax=cax); cb.outline.set_linewidth(0.4); cb.ax.tick_params(labelsize=5, length=1.5, pad=1)
cb.set_label('% of listings at that age', fontsize=5.6, labelpad=2)
letter(ax, 'b', -0.2, 1.04)
# (c) km sample, log-log, with the fitted log-log line from the workbook
ax = axs[1, 0]
for m, c in [(sK.Segment == 'Non-luxury', NON), (sK.Segment == 'Luxury', LUX)]:
    ax.scatter(sK.Kms_c[m], sK.Car_Price[m], s=1.2, color=c, alpha=0.5, lw=0, rasterized=True)
b_, a_ = R['km_logmodel']['slope'], R['km_logmodel']['intercept']; xk = np.logspace(np.log10(3e3), 6, 50)
ax.plot(xk, np.exp(a_ + b_ * np.log(xk)), color=INK, lw=1.1, path_effects=halo, label=f'Fitted log–log line, full data (slope {b_:.3f})'.replace('-0', '−0'))
ax.set_xscale('log'); ax.set_yscale('log'); logticks(ax); logticks(ax, 'x'); ax.set_ylim(*YL); ax.set_xlim(5e3, 1.05e6)
ax.set_xlabel('Kms_Driven (km, log scale; ≤ 1,000,000)'); ax.set_ylabel('Car_Price (INR, log scale)')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.13), handlelength=1.8, fontsize=5.8)
ax.text(0.98, 0.03, f'r = {R["rel"]["All"]["km"]["pearson"]:+.3f} (full data)'.replace('-', '−'), transform=ax.transAxes, ha='right', fontsize=5.8, path_effects=halo)
letter(ax, 'c', -0.2, 1.04)
# (d) conditional density by km decile (every listing with km <= cap)
ax = axs[1, 1]; dec = pd.qcut(kv.Kms_c, 10, labels=False).values + 1
im = cond_heat(ax, dec, kv.Car_Price.values, np.arange(0.5, 11))
kq = np.array([R['km_dec_iqr']['All'][str(d - 1)] for d in range(1, 11)])
ax.plot(range(1, 11), kq[:, 0], color='white', lw=0.7, ls=(0, (2.5, 1.5))); ax.plot(range(1, 11), kq[:, 2], color='white', lw=0.7, ls=(0, (2.5, 1.5)))
for seg, c in [('Non-luxury', NON), ('Luxury', LUX)]:
    q = np.array([R['km_dec_iqr'][seg][str(d - 1)][1] for d in range(1, 11)])
    ax.plot(range(1, 11), q, color=c, lw=1.1, marker='o' if seg == 'Non-luxury' else 's', ms=2, path_effects=halo, label=f'Median, {seg.lower()}')
ax.set_xlim(0.5, 10.5); ax.set_xticks(range(1, 11)); ax.set_xticklabels([f'D{d}' for d in range(1, 11)])
ax.set_xlabel('Kms_Driven decile (D1 lowest, D10 highest)'); ax.set_ylabel('Car_Price (INR, log scale)')
ax.legend(loc='upper center', ncol=2, bbox_to_anchor=(0.5, 1.13), handlelength=1.6, columnspacing=1.0, fontsize=5.8)
cax = ax.inset_axes([1.03, 0.1, 0.03, 0.8]); cb = fig.colorbar(im, cax=cax); cb.outline.set_linewidth(0.4); cb.ax.tick_params(labelsize=5, length=1.5, pad=1)
cb.set_label('% of listings in that decile', fontsize=5.6, labelpad=2)
letter(ax, 'd', -0.2, 1.04)
save(fig, 'Figure2_price_age_usage')

# ============ Figure 3: 3-D median surface + sampling variability ============
kv2 = kv.copy(); kv2['dec'] = pd.qcut(kv2.Kms_c, 10, labels=False); kv2['ab'] = ((kv2.Registration_Age - 1) // 5).astype(int)
grid = kv2.groupby(['ab', 'dec']).Car_Price.median().unstack(); cnt = kv2.groupby(['ab', 'dec']).size()
fig = plt.figure(figsize=(W, 2.8))
ax = fig.add_axes([-0.04, -0.09, 0.64, 1.18], projection='3d')
X, Y = np.meshgrid(grid.columns.values + 1, grid.index.values * 5 + 3, indexing='xy'); Z = grid.values / 1e3
ZF = 540; norm = colors.Normalize(Z.min(), Z.max())
ax.plot_surface(X, Y, Z, facecolors=SURF(norm(Z)), rstride=1, cstride=1, linewidth=0.35, edgecolor=(1, 1, 1, 0.85), antialiased=True, shade=False, alpha=0.97)
ax.contourf(X, Y, Z, zdir='z', offset=ZF, levels=12, cmap=SURF, norm=norm, alpha=0.55)
ax.contour(X, Y, Z, zdir='z', offset=ZF, levels=12, colors='white', linewidths=0.3, alpha=0.8)
# marginal profiles projected onto the back walls
xm = np.array([R['km_dec_iqr']['All'][str(d)][1] for d in range(10)]) / 1e3; ym_ = kv2.groupby('ab').Car_Price.median().values / 1e3
R['wall_age_band_medians'] = list(ym_ * 1e3)
ax.plot(grid.columns.values + 1, np.full(10, 25.5), xm, color='#444444', lw=0.9, zorder=10)
ax.scatter(grid.columns.values + 1, np.full(10, 25.5), xm, s=2.5, color='#444444', depthshade=False)
ax.plot(np.full(5, 0.5), grid.index.values * 5 + 3, ym_, color='#444444', lw=0.9, zorder=10)
ax.scatter(np.full(5, 0.5), grid.index.values * 5 + 3, ym_, s=2.5, color='#444444', depthshade=False)
ax.set_xlim(0.5, 10.5); ax.set_ylim(0.5, 25.5); ax.set_zlim(ZF, 790); ax.view_init(elev=24, azim=-58)
ax.set_xlabel('Kms_Driven decile', labelpad=-5); ax.set_ylabel('Registration_Age (years)', labelpad=-3); ax.set_zlabel('Median Car_Price (INR k)', labelpad=-4)
ax.tick_params(pad=-3, labelsize=5.6)
for a in (ax.xaxis, ax.yaxis, ax.zaxis):
    a.pane.set_facecolor((0.97, 0.97, 0.97, 1)); a.pane.set_edgecolor('#d0d0d0'); a._axinfo['grid'].update(color='#e0e0e0', linewidth=0.35)
ax.set_xticks([1, 4, 7, 10]); ax.set_xticklabels(['D1', 'D4', 'D7', 'D10'])
ax.set_yticks([3, 8, 13, 18, 23]); ax.set_yticklabels(['1–5', '6–10', '11–15', '16–20', '21–25'])
ax.set_zticks([550, 600, 650, 700, 750])
fig.text(0.02, 0.92, 'a', fontsize=8.5, fontweight='bold')
ax2 = fig.add_axes([0.68, 0.2, 0.3, 0.68])
xs = np.linspace(-0.11, 0.07, 800); n_s = 5000
for key, lab, c, sref, col in [('age', 'Price and age', '#7a7a7a', sA, 'Registration_Age'), ('km', 'Price and kilometres', NON, sK, 'Kms_Driven')]:
    r0 = R['rel']['All'][key]['pearson']; se = (1 - r0 ** 2) / math.sqrt(n_s - 1); pdf = st.norm.pdf(xs, r0, se)
    ax2.fill_between(xs, pdf, color=c, alpha=0.12, lw=0)
    inside = (xs >= r0 - 1.96 * se) & (xs <= r0 + 1.96 * se)
    ax2.fill_between(xs[inside], pdf[inside], color=c, alpha=0.32, lw=0)
    ax2.plot(xs, pdf, color=c, lw=1, label=lab); ax2.plot([r0, r0], [0, pdf.max()], color=c, lw=0.7)
    rs_ = np.corrcoef(sref[col], sref.Car_Price)[0, 1]
    ax2.plot([rs_], [0.9], marker='v', color=c, mec=INK, mew=0.4, ms=4.2, zorder=5)
ax2.annotate('', xy=(R['rel']['All']['km']['pearson'] - 1.96 * (1 - R['rel']['All']['km']['pearson'] ** 2) / math.sqrt(4999), 31),
             xytext=(R['rel']['All']['km']['pearson'] + 1.96 * (1 - R['rel']['All']['km']['pearson'] ** 2) / math.sqrt(4999), 31),
             arrowprops=dict(arrowstyle='<->', lw=0.6, color=NON, shrinkA=0, shrinkB=0, mutation_scale=5))
ax2.text(R['rel']['All']['km']['pearson'], 32, '95% of samples', ha='center', va='bottom', fontsize=5.4, color=NON)
ax2.set_ylim(0, 38); ax2.set_xlim(-0.11, 0.07); ax2.set_xlabel('Pearson r in a random sample of 5,000'); ax2.set_ylabel('Density')
ax2.legend(loc='upper right', handlelength=1.4, bbox_to_anchor=(1.02, 1.0))
fig.text(0.625, 0.92, 'b', fontsize=8.5, fontweight='bold')
save(fig, 'Figure3_surface_sampling')

# ============ Figure 4: brands and correlations ============
def med_ci(x):
    x = np.sort(np.asarray(x)); n = len(x); k = 1.96 * math.sqrt(n) / 2
    return np.median(x), x[int(n / 2 - k)], x[int(n / 2 + k)], n
fig, axs = plt.subplots(1, 2, figsize=(W, 2.95), gridspec_kw={'wspace': 0.78, 'width_ratios': [1, 1.08]})
ax = axs[0]; rows = []
for b_, g in df.groupby('BrandC'):
    rows.append((b_,) + med_ci(g.Car_Price.values))
rows.sort(key=lambda r: r[1]); LB = {'Audi', 'BMW', 'Mercedes'}
mA, lA, hA, _ = med_ci(P)
ax.axvspan(lA / 1e3, hA / 1e3, color='#eeeeee', lw=0, zorder=0)
ax.axvline(mA / 1e3, color=GREY, lw=0.6, ls=(0, (2, 1.5)), zorder=1)
nmax = max(r[4] for r in rows)
for i, (b_, m, l, h_, n) in enumerate(rows):
    c = LUX if b_ in LB else NON
    ax.plot([l / 1e3, h_ / 1e3], [i, i], color=c, lw=1.2, solid_capstyle='round', alpha=0.9)
    ax.scatter(m / 1e3, i, s=6 + 16 * n / nmax, color=c, edgecolor='white', lw=0.4, zorder=3)
for j, (s_, c) in enumerate([('Non-luxury', NON), ('Luxury', LUX)]):
    m, l, h_, n = med_ci(P[(df.Segment == s_).values]); y = len(rows) + 0.9 + j
    ax.plot([l / 1e3, h_ / 1e3], [y, y], color=c, lw=2.2, solid_capstyle='round'); ax.scatter(m / 1e3, y, s=20, marker='D', color=c, edgecolor='white', lw=0.5, zorder=3)
ax.set_yticks(list(range(len(rows))) + [len(rows) + 0.9, len(rows) + 1.9]); ax.set_yticklabels([r[0] for r in rows] + ['Non-luxury (all)', 'Luxury (all)'])
for tl in ax.get_yticklabels():
    if tl.get_text() in LB or tl.get_text() == 'Luxury (all)': tl.set_color(LUX)
ax.axhline(len(rows) + 0.35, color='#cccccc', lw=0.5)
ax.set_xlabel('Median Car_Price (INR thousand, 95% CI)')
ax.text(hA / 1e3 + 0.3, len(rows) + 2.55, 'overall median and its 95% CI', ha='left', va='bottom', fontsize=5.4, color='#666666', path_effects=halo)
ax.set_ylim(-0.8, len(rows) + 3.1); letter(ax, 'a', -0.5, 1.0)
ax = axs[1]
order = ['Kms_Driven (≤1m km)', 'Horsepower', 'Engine_CC', 'Tax_Paid', 'Number_of_Doors', 'Mileage_kmpl', 'Registration_Age', 'Year', 'Insurance_Valid', 'Service_History', 'Accidents', 'Seats']
Cc = R['corr_all']; y = np.arange(len(order))[::-1]
ax.axvspan(-0.1, 0.1, color='#f5f5f5', lw=0, zorder=0)
ax.text(0.0, len(order) - 0.15, '|r| < 0.1', ha='center', va='bottom', fontsize=5.4, color='#777777', path_effects=[patheffects.withStroke(linewidth=2, foreground='#f5f5f5')])
for g, c, mk, off in [('All', INK, 'o', 0), ('Luxury', LUX, 's', -0.24), ('Non-luxury', NON, '^', 0.24)]:
    for v, yy in zip(order, y):
        r_, n_ = Cc[v][g]['pearson'], Cc[v][g]['n']; z = np.arctanh(r_); se = 1 / math.sqrt(n_ - 3)
        lo_, hi_ = np.tanh(z - 1.96 * se), np.tanh(z + 1.96 * se)
        ax.plot([lo_, hi_], [yy + off, yy + off], color=c, lw=0.9, zorder=2)
    ax.scatter([Cc[v][g]['pearson'] for v in order], y + off, s=7, color=c, marker=mk, label=g, zorder=3, lw=0)
ax.axvline(0, color=GREY, lw=0.6)
ax.set_yticks(y); ax.set_yticklabels([v.replace(' (≤1m km)', '') for v in order]); ax.set_xlim(-0.12, 0.12); ax.set_ylim(-0.7, len(order) + 0.5)
ax.set_xlabel('Pearson r with Car_Price (95% CI)'); ax.legend(loc='lower right', handletextpad=0.2, bbox_to_anchor=(1.03, 0.0))
letter(ax, 'b', -0.55, 1.0)
save(fig, 'Figure4_segment_correlations')
print('figs v4 ok')
