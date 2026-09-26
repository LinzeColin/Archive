import pandas as pd, numpy as np, json, math
from style import *
from matplotlib.ticker import FuncFormatter
from matplotlib import cm, colors
from mpl_toolkits.mplot3d import Axes3D
df=pd.read_pickle('clean.pkl'); R=json.load(open('results.json'))
FMT=FuncFormatter(inr_k)
# ---------------- FIG 3: 3D landscape + sampling uncertainty ----------------
kv=df.dropna(subset=['Kms_c']).copy(); kv['dec']=pd.qcut(kv.Kms_c,10,labels=False)
kv['ab']=((kv.Registration_Age-1)//5).astype(int)
grid=kv.groupby(['ab','dec']).Car_Price.median().unstack()   # 5 x 10
cnt=kv.groupby(['ab','dec']).size()
R['landscape']=dict(cells=int(grid.size),min_n=int(cnt.min()),max_n=int(cnt.max()),zmin=float(grid.values.min()),zmax=float(grid.values.max()))
fig=plt.figure(figsize=(7.1,3.3))
ax=fig.add_axes([-0.03,-0.05,0.60,1.08],projection='3d')
Dk,Ag=np.meshgrid(grid.columns.values+1,grid.index.values*5+3,indexing='xy'); Z=grid.values/1e3
cmap=colors.LinearSegmentedColormap.from_list('b',SEQ[1:])
norm=colors.Normalize(Z.min()-10,Z.max())
ax.plot_surface(Dk,Ag,Z,facecolors=cmap(norm(Z)),rstride=1,cstride=1,linewidth=0.5,edgecolor=(1,1,1,0.9),antialiased=True,shade=False)
ax.contourf(Dk,Ag,Z,zdir='z',offset=560,levels=10,cmap=cmap,alpha=0.3)
ax.set_zlim(560,790); ax.view_init(elev=22,azim=-62)
ax.set_xlabel('Kms_Driven decile',labelpad=1,fontsize=7.2); ax.set_ylabel('Age band (yrs)',labelpad=3,fontsize=7.2); ax.set_zlabel('Median price, INR k',labelpad=3,fontsize=7.2)
ax.tick_params(pad=0,labelsize=6.3)
for a in (ax.xaxis,ax.yaxis,ax.zaxis):
    a.pane.set_facecolor((0.985,0.985,0.98,1)); a.pane.set_edgecolor(GRID); a._axinfo['grid'].update(color=GRID,linewidth=0.4)
ax.set_xticks([1,4,7,10]); ax.set_xticklabels(['D1','D4','D7','D10'])
ax.set_yticks([3,8,13,18,23]); ax.set_yticklabels(['1–5','6–10','11–15','16–20','21–25'],fontsize=6.0)
ax.set_zticks([575,625,675,725,775])
fig.text(0.035,0.95,'A',fontsize=9.5,fontweight=700); fig.text(0.06,0.95,f"Price landscape · 50 cells, {int(cnt.min()):,}–{int(cnt.max()):,} cars each",fontsize=9.2,fontweight=600)
fig.text(0.06,0.885,f"z-axis starts at 560k · tilts along usage (decile medians {R['km_deciles'][0]['median']/1e3:,.0f}k → {R['km_deciles'][9]['median']/1e3:,.0f}k); level along age",fontsize=7,color=INK2)
# B: sampling distributions
ax2=fig.add_axes([0.665,0.17,0.32,0.66])
rng=np.random.default_rng(7)
# re-simulate for plot (same design as analysis: 1,000 draws of 5,000)
ra=[];rk=[]; kvv=kv[['Kms_c','Car_Price']].values; av=df[['Registration_Age','Car_Price']].values
for i in range(1000):
    ia=rng.integers(0,len(av),5000); ra.append(np.corrcoef(av[ia,0],av[ia,1])[0,1])
    ik=rng.integers(0,len(kvv),5000); rk.append(np.corrcoef(kvv[ik,0],kvv[ik,1])[0,1])
b=np.linspace(-0.11,0.07,55)
ax2.hist(ra,b,color='#b9b8b2',alpha=0.9,label='Price–Age',edgecolor='white',linewidth=0.3)
ax2.hist(rk,b,color=SEQ[4],alpha=0.85,label='Price–Kms',edgecolor='white',linewidth=0.3)
ax2.vlines([R['rel']['All']['age']['pearson'],R['rel']['All']['km']['pearson']],0,114,color=INK,lw=1)
ax2.text(R['rel']['All']['km']['pearson'],118,'full-data\nr = −0.051',fontsize=6.3,color=INK,va='bottom',ha='center',linespacing=1.2)
ax2.text(R['rel']['All']['age']['pearson'],118,'full-data\nr ≈ 0.000',fontsize=6.3,color=INK,va='bottom',ha='center',linespacing=1.2)
ax2.set_xlabel('Pearson r in a random 5,000-row sample'); ax2.set_ylabel('Count of 1,000 samples')
ax2.set_ylim(0,200); ax2.legend(loc='upper left',fontsize=6.6,ncol=1)
fig.text(0.615,0.95,'B',fontsize=9.5,fontweight=700); fig.text(0.64,0.95,'Why the full data decides',fontsize=9.2,fontweight=600)
sa=R['sample_r']['age']; sk=R['sample_r']['km']
ax2.text(0.99,0.995,f"95% of samples:\nage r ∈ [{sa['p2_5']:+.3f}, {sa['p97_5']:+.3f}]\nkms r ∈ [{sk['p2_5']:+.3f}, {sk['p97_5']:+.3f}]",transform=ax2.transAxes,ha='right',va='top',fontsize=6.6,color=INK2,linespacing=1.4)
fig.savefig('fig/fig3_landscape.png',bbox_inches='tight',pad_inches=0.04); plt.close(fig)
# ---------------- FIG 4: brand forest + signal scan ----------------
def med_ci(x):
    x=np.sort(np.asarray(x)); n=len(x); k=1.96*math.sqrt(n)/2
    return np.median(x), x[max(int(n/2-k),0)], x[min(int(n/2+k),n-1)]
fig,axs=plt.subplots(1,2,figsize=(7.1,3.35),gridspec_kw={'width_ratios':[1,1.08],'wspace':0.62})
ax=axs[0]; overall=df.Car_Price.median()
rows=[]
for b_,g in df.groupby('BrandC'): m,l,h=med_ci(g.Car_Price.values); rows.append((b_,m,l,h,len(g)))
rows.sort(key=lambda r:r[1]); LUXB={'Audi','BMW','Mercedes'}
for i,(b_,m,l,h,n) in enumerate(rows):
    c=LUX if b_ in LUXB else NON
    ax.plot([l/1e3,h/1e3],[i,i],color=c,lw=1.6,solid_capstyle='round'); ax.plot(m/1e3,i,'o',color=c,ms=4.2,mec='white',mew=0.8)
seg=[]
for j,(s_,c) in enumerate([('Non-luxury',NON),('Luxury',LUX)]):
    m,l,h=med_ci(df.Car_Price[df.Segment==s_].values); seg.append((s_,m,l,h))
    y=len(rows)+0.9+j; ax.plot([l/1e3,h/1e3],[y,y],color=c,lw=2.6,solid_capstyle='round'); ax.plot(m/1e3,y,'D',color=c,ms=5,mec='white',mew=0.8)
ax.axvline(overall/1e3,color=MUTE,lw=0.8)
ax.set_yticks(list(range(len(rows)))+[len(rows)+0.9,len(rows)+1.9]); ax.set_yticklabels([r[0] for r in rows]+['Non-luxury segment','Luxury segment'],fontsize=7.2)
for t in ax.get_yticklabels():
    if t.get_text() in LUXB or t.get_text()=='Luxury segment': t.set_color(LUX)
    if t.get_text()=='Non-luxury segment': t.set_color(NON)
ax.axhline(len(rows)+0.35,color=GRID,lw=0.8); ax.grid(axis='y',visible=False)
ax.set_xlabel('Median Car_Price, INR k (95% CI)'); ax.set_xlim(min(r[2] for r in rows)/1e3-1.5, max(r[3] for r in rows)/1e3+12)
ax.set_title('Brand & segment medians'); ax.text(-0.52,1.02,'A',transform=ax.transAxes,fontsize=9.5,fontweight=700,ha='left',va='bottom')
ax.text(0.985,0.985,f"brand spread {R['brand_median_range_pct']:.1f}%\nsegment gap {R['seg']['median_diff_pct']:+.2f}%\n95% CI {R['seg']['median_ratio_ci_pct'][0]:+.2f} to {R['seg']['median_ratio_ci_pct'][1]:+.2f}%",transform=ax.transAxes,ha='right',va='top',fontsize=6.5,color=INK2,linespacing=1.4,bbox=dict(fc='white',ec='none',pad=1.5))
# signal scan
ax=axs[1]; scr=R['screen_r2']
lab={'Kms_c':'Kms_Driven','Horsepower_c':'Horsepower','Engine_CC_c':'Engine_CC','Mileage_kmpl_c':'Mileage_kmpl','BrandC':'Brand','FuelC':'Fuel_Type','Segment':'Segment (lux/non)'}
items=sorted(scr.items(),key=lambda kv:kv[1])
names=[lab.get(k,k) for k,_ in items]; vals=[v*100 for _,v in items]
cols=[SEQ[4] if k in('Kms_c','Horsepower_c','Engine_CC_c') else ('#b9b8b2') for k,_ in items]
cols=[LUX if k=='Segment' else c for (k,_),c in zip(items,cols)]
ax.barh(range(len(items)),vals,color=cols,height=0.68)
ax.set_xscale('log'); ax.set_xlim(1e-6,2)
ax.set_yticks(range(len(items))); ax.set_yticklabels(names,fontsize=6.9)
ax.set_xticks([1e-5,1e-3,1e-1]); ax.set_xticklabels(['0.00001%','0.001%','0.1%'],fontsize=6.6); ax.minorticks_off()
ax.grid(axis='y',visible=False)
ax.set_xlabel('Share of log-price variance explained (log axis)')
ax.set_title('Signal scan · 19 candidate predictors'); ax.text(-0.44,1.02,'B',transform=ax.transAxes,fontsize=9.5,fontweight=700,ha='left',va='bottom')
for i,(k,v) in enumerate(items):
    if k in('Kms_c','Horsepower_c','Engine_CC_c'): ax.text(v*100*1.15,i,f'{v*100:.2f}%',va='center',fontsize=6.5,color=INK)
ax.text(0.98,0.03,"numeric: r² of log–log fit\ncategorical: η² (between-group share)\nall 16 others < 0.004%",transform=ax.transAxes,fontsize=6.4,color=INK2,linespacing=1.4,va='bottom',ha='right')
fig.savefig('fig/fig4_segment_signal.png',bbox_inches='tight'); plt.close(fig)
json.dump(R,open('results.json','w'),indent=1)
print(R['landscape'])
