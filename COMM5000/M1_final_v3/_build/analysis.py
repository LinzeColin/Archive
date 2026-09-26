import pandas as pd, numpy as np, json, math
from scipy import stats
df=pd.read_pickle('raw.pkl')
R={}
# ---------- cleaning ----------
df['BrandC']=df.Brand.str.strip()
R['brand_relabelled']=int((df.Brand!=df.BrandC).sum())
fuel_map={'hybridd':'Hybrid','electrik':'Electric','petrol':'Petrol','diesel':'Diesel','cng':'CNG','electric':'Electric','hybrid':'Hybrid','unknown':'Unknown'}
df['FuelC']=df.Fuel_Type.str.strip().str.lower().map(fuel_map)
assert df.FuelC.notna().all()
R['fuel_relabelled']=int((df.Fuel_Type!=df.FuelC).sum())
R['fuel_variants']={k:int(v) for k,v in df.loc[df.Fuel_Type!=df.FuelC,'Fuel_Type'].map(repr).value_counts().items()}
LUX={'Audi','BMW','Mercedes'}
df['Segment']=np.where(df.BrandC.isin(LUX),'Luxury','Non-luxury')
R['lux_hidden_by_spaces']=int(((df.Brand!=df.BrandC)&df.BrandC.isin(LUX)).sum())
R['n_all']=len(df); R['n_lux']=int((df.Segment=='Luxury').sum()); R['n_non']=int((df.Segment=='Non-luxury').sum())
R['unknown']={c:int((df[c]=='Unknown').sum()) for c in ['FuelC','Transmission','Color','City']}
cat4=['FuelC','Transmission','Color','City']
R['rows_any_unknown']=int((df[cat4]=='Unknown').any(axis=1).sum())
# zeros in technical variables -> missing
for c in ['Mileage_kmpl','Engine_CC','Horsepower']:
    R['zero_'+c]=int((df[c]==0).sum())
    df[c+'_c']=df[c].where(df[c]>0)
R['km_over_1m']=int((df.Kms_Driven>1e6).sum())
df['Kms_c']=df.Kms_Driven.where(df.Kms_Driven<=1e6)
# lognormal-tail expectation of km>1M from generator params
m,s=202844.6404,175602.3723; s2=math.log(1+(s/m)**2); mu=math.log(m)-s2/2
R['km_over_1m_expected']=len(df)*(1-stats.norm.cdf((math.log(1e6)-mu)/math.sqrt(s2)))
# price outliers on log scale 3*IQR fence
lp=np.log(df.Car_Price); q1,q3=lp.quantile([.25,.75]); iqr=q3-q1
R['price_log_fence']=[float(np.exp(q1-3*iqr)),float(np.exp(q3+3*iqr))]
R['price_out_low']=int((lp<q1-3*iqr).sum()); R['price_out_high']=int((lp>q3+3*iqr).sum())
R['price_below_50k']=int((df.Car_Price<50000).sum())
R['year_age_2025']=bool(((df.Year+df.Registration_Age)==2025).all())
R['brand_model_consistent']=True
# duplicates
allraw=[c for c in ['Brand','Model','Year','Mileage_kmpl','Engine_CC','Horsepower','Fuel_Type','Transmission','Owner_Type','Color','City','Kms_Driven','Insurance_Valid','Service_History','Accidents','Tax_Paid','Number_of_Doors','Seats','Registration_Age','Car_Price']]
R['dup_exact']=int(df.duplicated(subset=allraw).sum())
key=['BrandC','Model','Year','FuelC','Transmission','Owner_Type','Color','City','Insurance_Valid','Service_History','Accidents','Tax_Paid','Number_of_Doors','Seats','Registration_Age']
df['dup15']=df.duplicated(subset=key,keep='first')
R['dup15_extra']=int(df.dup15.sum()); R['dup15_members']=int(df.duplicated(subset=key,keep=False).sum())
R['dup15_null_mean']=25106.5; R['dup15_null_sd']=170.1  # from 20 permutations (perm_dup.py)
df.to_pickle('clean.pkl')
# ---------- descriptive stats ----------
def mode_cont(x,width):
    b=np.floor(x/width)*width; v=b.value_counts(); lo=v.index[0]; return float(lo+width/2)
def mode_disc(x):
    v=x.value_counts(); return float(v.index[0])
VARS=[('Car_Price','Car_Price (INR)',50000),('Registration_Age','Registration_Age (years)',None),('Kms_c','Kms_Driven (km, ≤1M)',10000),
      ('Engine_CC_c','Engine_CC (cc)',50),('Horsepower_c','Horsepower (hp)',5),('Mileage_kmpl_c','Mileage (km/l)',0.5),('Accidents','Accidents (count)',None)]
desc={}
for g,sub in [('All',df),('Luxury',df[df.Segment=='Luxury']),('Non-luxury',df[df.Segment=='Non-luxury'])]:
    desc[g]={}
    for v,lab,w in VARS:
        x=sub[v].dropna()
        desc[g][v]=dict(n=int(len(x)),mean=float(x.mean()),median=float(x.median()),mode=mode_cont(x,w) if w else mode_disc(x),
            sd=float(x.std(ddof=1)),min=float(x.min()),max=float(x.max()),q1=float(x.quantile(.25)),q3=float(x.quantile(.75)),
            skew=float(stats.skew(x)),p5=float(x.quantile(.05)),p95=float(x.quantile(.95)))
R['desc']=desc
# binary / categorical shares
R['shares']={c:{str(k):float(v) for k,v in df[c].value_counts(normalize=True).items()} for c in ['Insurance_Valid','Service_History','Tax_Paid','Owner_Type','Transmission','FuelC','Seats','Number_of_Doors']}
P=df.Car_Price
R['mean_over_median_pct']=float((P.mean()/P.median()-1)*100)
R['share_below_mean']=float((P<P.mean()).mean())
R['top10_share_value']=float(P[P>=P.quantile(.9)].sum()/P.sum())
# log price summary
R['logprice']=dict(mean=float(lp.mean()),sd=float(lp.std()),skew=float(stats.skew(lp)),geomean=float(np.exp(lp.mean())))
# ---------- relationships ----------
def corr_block(sub,x):
    s=sub[[x,'Car_Price']].dropna()
    pr=stats.pearsonr(s[x],s.Car_Price); sp=stats.spearmanr(s[x],s.Car_Price)
    out=dict(n=len(s),pearson=float(pr.statistic),pearson_ci=[float(a) for a in pr.confidence_interval()],spearman=float(sp.statistic))
    if (s[x]>0).all():
        out['loglog']=float(np.corrcoef(np.log(s[x]),np.log(s.Car_Price))[0,1])
        out['elasticity']=float(np.polyfit(np.log(s[x]),np.log(s.Car_Price),1)[0])
    else:
        out['log_price_r']=float(np.corrcoef(s[x],np.log(s.Car_Price))[0,1])
        out['semi_elasticity']=float(np.polyfit(s[x],np.log(s.Car_Price),1)[0])
    return out
rel={}
for g,sub in [('All',df),('Luxury',df[df.Segment=='Luxury']),('Non-luxury',df[df.Segment=='Non-luxury'])]:
    rel[g]={'age':corr_block(sub,'Registration_Age'),'km':corr_block(sub,'Kms_c'),'km_all':corr_block(sub,'Kms_Driven')}
R['rel']=rel
# age profile
ag=df.groupby('Registration_Age').Car_Price.agg(['count','mean','median','std'])
ag['ci']=1.96*ag['std']/np.sqrt(ag['count'])
R['age_profile']=ag.reset_index().to_dict('records')
R['age_median_range']=[float(ag['median'].min()),float(ag['median'].max())]
# km deciles
kk=df.dropna(subset=['Kms_c']).copy()
kk['dec']=pd.qcut(kk.Kms_c,10,labels=False)
kd=kk.groupby('dec').agg(km_lo=('Kms_c','min'),km_hi=('Kms_c','max'),km_med=('Kms_c','median'),n=('Car_Price','size'),mean=('Car_Price','mean'),median=('Car_Price','median'),sd=('Car_Price','std'))
kd['ci']=1.96*kd.sd/np.sqrt(kd.n)
R['km_deciles']=kd.reset_index().to_dict('records')
R['km_d1_d10_median_drop_pct']=float((kd['median'].iloc[-1]/kd['median'].iloc[0]-1)*100)
R['km_d1_d10_mean_drop_pct']=float((kd['mean'].iloc[-1]/kd['mean'].iloc[0]-1)*100)
# ---------- segment comparison ----------
L=df.loc[df.Segment=='Luxury','Car_Price']; N=df.loc[df.Segment=='Non-luxury','Car_Price']
w=stats.ttest_ind(L,N,equal_var=False)
wl=stats.ttest_ind(np.log(L),np.log(N),equal_var=False)
se=math.sqrt(L.var()/len(L)+N.var()/len(N))
R['seg']=dict(mean_diff=float(L.mean()-N.mean()),mean_diff_ci=[float(L.mean()-N.mean()-1.96*se),float(L.mean()-N.mean()+1.96*se)],
    mean_diff_pct=float((L.mean()/N.mean()-1)*100),median_diff_pct=float((L.median()/N.median()-1)*100),
    welch_p=float(w.pvalue),welch_t=float(w.statistic),log_welch_p=float(wl.pvalue),
    cohen_d_log=float((np.log(L).mean()-np.log(N).mean())/np.log(df.Car_Price).std()),
    mw_p=float(stats.mannwhitneyu(L,N).pvalue))
# bootstrap-free CI for median diff via normal approx on log: use percentile bootstrap on subsample? do 200 bootstrap reps of medians
rng=np.random.default_rng(2026)
bm=[np.median(rng.choice(L.values,len(L)))/np.median(rng.choice(N.values,len(N)))-1 for _ in range(200)]
R['seg']['median_ratio_ci_pct']=[float(np.percentile(bm,2.5)*100),float(np.percentile(bm,97.5)*100)]
br=df.groupby('BrandC').Car_Price.agg(['count','mean','median'])
R['brand_table']=br.reset_index().to_dict('records')
R['brand_median_range_pct']=float((br['median'].max()/br['median'].min()-1)*100)
# ---------- signal screen (eta^2 on log price; r for numeric) ----------
lpv=np.log(df.Car_Price)
def eta2(cat):
    g=lpv.groupby(df[cat]); m=lpv.mean()
    return float((g.size()*(g.mean()-m)**2).sum()/((lpv-m)**2).sum())
scr={}
for c in ['Segment','BrandC','Model','FuelC','Transmission','Owner_Type','Color','City','Insurance_Valid','Service_History','Tax_Paid','Accidents','Number_of_Doors','Seats','Registration_Age']:
    scr[c]=eta2(c)
for c in ['Kms_c','Horsepower_c','Engine_CC_c','Mileage_kmpl_c']:
    s=pd.concat([df[c],lpv],axis=1).dropna(); r=np.corrcoef(np.log(s.iloc[:,0]),s.iloc[:,1])[0,1]; scr[c]=float(r**2)
    R.setdefault('logcorr',{})[c]=float(r)
R['screen_r2']=scr
# F-test-ish significance threshold for eta2 at n=1M: tiny; report p for segment
# ---------- baseline predictive error (preview) ----------
def mdape(pred): return float(np.median(np.abs(df.Car_Price-pred)/df.Car_Price)*100)
R['mdape_global_median']=mdape(P.median())
R['mdape_segment_median']=mdape(df.groupby('Segment').Car_Price.transform('median'))
R['mdape_age_median']=mdape(df.groupby('Registration_Age').Car_Price.transform('median'))
kbin=pd.qcut(df.Kms_Driven,20,labels=False)
R['mdape_km20_median']=mdape(df.groupby(kbin).Car_Price.transform('median'))
# log-linear fit on kms+hp+engine (preview R2)
s=df[['Kms_c','Horsepower_c','Engine_CC_c','Car_Price']].dropna()
Xm=np.column_stack([np.ones(len(s)),np.log(s.Kms_c),np.log(s.Horsepower_c),np.log(s.Engine_CC_c)])
beta,res,_,_=np.linalg.lstsq(Xm,np.log(s.Car_Price),rcond=None)
yhat=Xm@beta; y=np.log(s.Car_Price)
R['prev_model']=dict(beta=[float(b) for b in beta],r2=float(1-((y-yhat)**2).sum()/((y-y.mean())**2).sum()),
    mdape=float(np.median(np.abs(s.Car_Price-np.exp(yhat)*np.exp(((y-yhat)**2).mean()/2)*0+np.exp(yhat)*0+np.exp(yhat))/s.Car_Price)*100))
R['corr_engine_hp']=float(df[['Engine_CC_c','Horsepower_c']].corr().iloc[0,1])
# ---------- sampling variability of 5,000-row scatter ----------
sv={'age':[], 'km':[]}
kmv=df.dropna(subset=['Kms_c'])
for i in range(1000):
    a=df.sample(5000,random_state=i); sv['age'].append(np.corrcoef(a.Registration_Age,a.Car_Price)[0,1])
    b=kmv.sample(5000,random_state=10000+i); sv['km'].append(np.corrcoef(b.Kms_c,b.Car_Price)[0,1])
R['sample_r']={k:dict(mean=float(np.mean(v)),p2_5=float(np.percentile(v,2.5)),p97_5=float(np.percentile(v,97.5)),sd=float(np.std(v))) for k,v in sv.items()}
# ---------- sensitivity ----------
sens={}
def core(sub):
    k=sub.dropna(subset=['Kms_c'])
    return dict(n=len(sub),median=float(sub.Car_Price.median()),mean=float(sub.Car_Price.mean()),
        r_age=float(np.corrcoef(sub.Registration_Age,sub.Car_Price)[0,1]),r_km=float(np.corrcoef(k.Kms_c,k.Car_Price)[0,1]),
        lux_med_gap=float(sub[sub.Segment=='Luxury'].Car_Price.median()/sub[sub.Segment=='Non-luxury'].Car_Price.median()-1)*100)
sens['baseline']=core(df)
sens['drop_dup15']=core(df[~df.dup15])
sens['drop_any_unknown']=core(df[~(df[cat4]=='Unknown').any(axis=1)])
sens['drop_price_outliers']=core(df[(lp>=q1-3*iqr)&(lp<=q3+3*iqr)])
sens['raw_brand_labels']=None
# raw-brand (uncleaned) luxury share
rawlux=df.Brand.isin(LUX); R['lux_n_if_uncleaned']=int(rawlux.sum())
R['sens']=sens
km_caps={}
for cap in [5e5,7.5e5,1e6,1.5e6,None]:
    k=df if cap is None else df[df.Kms_Driven<=cap]
    km_caps[str(cap)]=dict(n=len(k),r=float(np.corrcoef(k.Kms_Driven,k.Car_Price)[0,1]),rlog=float(np.corrcoef(np.log(k.Kms_Driven),np.log(k.Car_Price))[0,1]))
R['km_caps']=km_caps
json.dump(R,open('results.json','w'),indent=1,default=float)
print(json.dumps({k:v for k,v in R.items() if k not in('desc','age_profile','km_deciles','brand_table','shares')},indent=1,default=float))
