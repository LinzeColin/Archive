import pandas as pd, numpy as np, json, math
from style import *
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter, FixedLocator
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
df=pd.read_pickle('clean.pkl'); R=json.load(open('results.json'))
P=df.Car_Price; lux=df.Segment=='Luxury'
FMT=FuncFormatter(inr_k)
def med_ci(x):
    x=np.sort(np.asarray(x)); n=len(x); k=1.96*math.sqrt(n)/2
    return np.median(x), x[max(int(n/2-k),0)], x[min(int(n/2+k),n-1)]
# ---------------- FIG 1: price anatomy ----------------
fig,axs=plt.subplots(1,2,figsize=(7.1,2.75),gridspec_kw={'width_ratios':[1.15,1],'wspace':0.28})
ax=axs[0]; bins=np.arange(0,5.0e6+1,50000)
h,_=np.histogram(P,bins); ax.bar(bins[:-1],h/1000,width=50000*0.86,align='edge',color='#9ec5f4',edgecolor='none')
mean,med=P.mean(),P.median(); mode=R['desc']['All']['Car_Price']['mode']
for v,lab,c,dy in [(mode,f'Mode bin ≈ {mode/1e3:.0f}k',MUTE,0.93),(med,f'Median {med/1e3:,.0f}k',INK,0.80),(mean,f'Mean {mean/1e6:.3f}m',LUX,0.67)]:
    ax.axvline(v,color=c,lw=1.1); ax.text(v+45000,h.max()/1000*dy,lab,color=c,fontsize=7.3,fontweight=600,bbox=dict(fc='white',ec='none',alpha=0.85,pad=1))
ax.set_xlim(0,5e6); ax.xaxis.set_major_formatter(FMT); ax.set_ylabel('Listings (thousands)'); ax.set_xlabel('Car_Price (INR, 50k bins; 1.3% of listings > 5m not shown)')
ax.set_title('Raw scale: strongly right-skewed'); tag(ax,'A')
ax.text(0.97,0.36,f"skewness = {R['desc']['All']['Car_Price']['skew']:.2f}\n{R['share_below_mean']*100:.1f}% of cars sit below the mean\ntop 10% of cars = {R['top10_share_value']*100:.1f}% of total value",transform=ax.transAxes,ha='right',va='top',fontsize=7.1,color=INK2,linespacing=1.5)
ax=axs[1]; lb=np.linspace(np.log10(8e3),np.log10(5.2e7),90)
for m,c,lab in [(~lux,NON,'Non-luxury (n=772,828)'),(lux,LUX,'Luxury (n=232,172)')]:
    hh,_=np.histogram(np.log10(P[m]),lb,density=True); ax.plot(10**((lb[:-1]+lb[1:])/2),hh,color=c,lw=1.6 if c==NON else 1.2,ls='-' if c==NON else (0,(4,2)),label=lab)
ax.set_xscale('log'); ax.xaxis.set_major_formatter(FMT); ax.set_xlim(2e4,2e7); ax.set_ylim(0,1.32)
ax.set_xlabel('Car_Price (INR, log scale)'); ax.set_ylabel('Density of log10(price)')
ax.set_title('Log scale: symmetric, segments overlap'); tag(ax,'B')
ax.legend(loc='lower center',handlelength=2.2,bbox_to_anchor=(0.5,-0.02),fontsize=6.8)
ax.text(0.03,0.97,f"log-price skewness = {R['logprice']['skew']:.3f}\ngeometric mean {R['logprice']['geomean']/1e3:,.0f}k ≈ median",transform=ax.transAxes,ha='left',va='top',fontsize=7.1,color=INK2,linespacing=1.5)
fig.savefig('fig/fig1_price.png',bbox_inches='tight'); plt.close(fig)
# ---------------- FIG 2: relationships ----------------
rng=np.random.default_rng(26092026)
sA=df.sample(5000,random_state=260926); kv=df.dropna(subset=['Kms_c']); sK=kv.sample(5000,random_state=260927)
sA[['ExcelRow','Segment','Registration_Age','Car_Price']].to_csv('plot_sample_age.csv',index=False); sK[['ExcelRow','Segment','Kms_c','Car_Price']].to_csv('plot_sample_km.csv',index=False)
fig,axs=plt.subplots(2,2,figsize=(7.1,5.35),gridspec_kw={'hspace':0.52,'wspace':0.26})
# A: age scatter
ax=axs[0,0]; j=rng.uniform(-0.28,0.28,len(sA))
for m,c,z in [(sA.Segment=='Non-luxury',NON,1),(sA.Segment=='Luxury',LUX,2)]:
    ax.scatter(sA.Registration_Age[m]+j[m],sA.Car_Price[m],s=2.2,color=c,alpha=0.45,lw=0,zorder=z,rasterized=True)
agm=df.groupby('Registration_Age').Car_Price.median(); ax.plot(agm.index,agm.values,color=INK,lw=1.6,zorder=3)
ax.set_yscale('log'); ax.yaxis.set_major_formatter(FMT); ax.set_ylim(3e4,1.5e7); ax.set_xlim(0,26)
ax.set_xlabel('Registration_Age (years; ±0.28 jitter for visibility)'); ax.set_ylabel('Car_Price (INR, log)')
sr=R['sample_r']['age']
ax.set_title('Age · random sample of 5,000'); tag(ax,'A')
ax.text(0.98,0.04,f"sample r = {np.corrcoef(sA.Registration_Age,sA.Car_Price)[0,1]:+.3f}   full-data r = {R['rel']['All']['age']['pearson']:+.5f}",transform=ax.transAxes,ha='right',fontsize=6.9,color=INK2,bbox=dict(fc='white',ec='none',alpha=0.85,pad=1.5))
# B: age medians full data
ax=axs[0,1]
q=df.groupby('Registration_Age').Car_Price.quantile([.25,.75]).unstack()
ax.fill_between(q.index,q[0.25],q[0.75],color='#e9e8e3',lw=0,label='All: interquartile range')
for seg,c,ls in [('Non-luxury',NON,'-'),('Luxury',LUX,'-')]:
    rows=[(a,)+med_ci(g.values) for a,g in df[df.Segment==seg].groupby('Registration_Age').Car_Price]
    a=np.array(rows); ax.fill_between(a[:,0],a[:,2],a[:,3],color=c,alpha=0.22,lw=0); ax.plot(a[:,0],a[:,1],color=c,lw=1.5,marker='o',ms=2.6,label=f'{seg} median (95% CI)')
ax.set_ylim(0,1.6e6); ax.set_xlim(0.5,25.5); ax.yaxis.set_major_formatter(FMT)
ax.set_xlabel('Registration_Age (years)'); ax.set_ylabel('Car_Price (INR)')
ax.set_title('Age · all 1,005,000 listings'); tag(ax,'B')
ax.legend(loc='lower right',ncol=1,fontsize=6.6,handlelength=1.4,bbox_to_anchor=(1.0,0.0),framealpha=0.9,frameon=True,edgecolor='none')
lo,hi=R['age_median_range']; ax.text(0.02,0.97,f"median range across ages: {lo/1e3:,.0f}k–{hi/1e3:,.0f}k (±{(hi/lo-1)*50:.1f}%)",transform=ax.transAxes,fontsize=6.9,color=INK2,va='top')
# C: km scatter log-log
ax=axs[1,0]
for m,c,z in [(sK.Segment=='Non-luxury',NON,1),(sK.Segment=='Luxury',LUX,2)]:
    ax.scatter(sK.Kms_c[m],sK.Car_Price[m],s=2.2,color=c,alpha=0.45,lw=0,zorder=z,rasterized=True)
kb=pd.qcut(kv.Kms_c,20); g=kv.groupby(kb,observed=True).agg(k=('Kms_c','median'),p=('Car_Price','median'))
ax.plot(g.k,g.p,color=INK,lw=1.6,zorder=3,label='full-data median (20 bins)')
ax.set_xscale('log'); ax.set_yscale('log'); ax.xaxis.set_major_formatter(FMT); ax.yaxis.set_major_formatter(FMT); ax.set_ylim(3e4,1.5e7); ax.set_xlim(8e3,1.05e6)
ax.set_xlabel('Kms_Driven (km, log; ≤ 1,000,000)'); ax.set_ylabel('Car_Price (INR, log)')
ax.set_title('Kms · random sample of 5,000'); tag(ax,'C')
ax.text(0.98,0.04,f"sample r = {np.corrcoef(sK.Kms_c,sK.Car_Price)[0,1]:+.3f}   full-data r = {R['rel']['All']['km']['pearson']:+.3f}",transform=ax.transAxes,ha='right',fontsize=6.9,color=INK2,bbox=dict(fc='white',ec='none',alpha=0.85,pad=1.5))
ax.legend(loc='upper right',fontsize=6.7)
# D: km deciles by segment
ax=axs[1,1]; kv2=kv.copy(); kv2['dec']=pd.qcut(kv2.Kms_c,10,labels=False)
edges=kv2.groupby('dec').Kms_c.agg(['min','max'])
for seg,c,off in [('Non-luxury',NON,-0.12),('Luxury',LUX,0.12)]:
    rows=[(d,)+med_ci(g.values) for d,g in kv2[kv2.Segment==seg].groupby('dec').Car_Price]; a=np.array(rows)
    ax.errorbar(a[:,0]+1+off,a[:,1],yerr=[a[:,1]-a[:,2],a[:,3]-a[:,1]],fmt='o',ms=3.4,color=c,lw=1,capsize=2,label=f'{seg} median ± 95% CI')
    ax.plot(a[:,0]+1+off,a[:,1],color=c,lw=0.9,alpha=0.7)
ax.set_xticks(range(1,11)); ax.set_xticklabels([f'D{i}' for i in range(1,11)])
ax.yaxis.set_major_formatter(FMT); ax.set_xlabel('Kms_Driven decile (D1 ≤ 58k km … D10 ≥ 406k km)'.replace('58k',f"{edges['max'][0]/1e3:.0f}k").replace('406k',f"{edges['min'][9]/1e3:.0f}k"))
ax.set_ylabel('Median Car_Price (INR)'); ax.set_title('Kms · all 998,866 listings by decile'); tag(ax,'D')
ax.legend(loc='upper right',fontsize=6.7)
ax.text(0.02,0.05,f"log–log elasticity = {R['rel']['All']['km']['elasticity']:.3f}\n(+10% km → {(1.1**R['rel']['All']['km']['elasticity']-1)*100:.2f}% price)",transform=ax.transAxes,fontsize=6.9,color=INK2,linespacing=1.45)
fig.savefig('fig/fig2_relationships.png',bbox_inches='tight'); plt.close(fig)
print('fig1,2 done')
