import pandas as pd, numpy as np, json, math
from scipy import stats
df=pd.read_pickle('clean.pkl'); R=json.load(open('results.json'))
G=[('All',df),('Luxury',df[df.Segment=='Luxury']),('Non-luxury',df[df.Segment=='Non-luxury'])]
NUM=[('Registration_Age','Registration_Age'),('Year','Year'),('Kms_c','Kms_Driven (≤1m km)'),('Mileage_kmpl_c','Mileage_kmpl'),('Engine_CC_c','Engine_CC'),('Horsepower_c','Horsepower'),
     ('Accidents','Accidents'),('Insurance_Valid','Insurance_Valid'),('Service_History','Service_History'),('Tax_Paid','Tax_Paid'),('Number_of_Doors','Number_of_Doors'),('Seats','Seats')]
corr={}
for v,lab in NUM:
    corr[lab]={}
    for g,sub in G:
        s=sub[[v,'Car_Price']].dropna()
        corr[lab][g]=dict(n=len(s),pearson=float(np.corrcoef(s[v],s.Car_Price)[0,1]),spearman=float(stats.spearmanr(s[v],s.Car_Price).statistic))
R['corr_all']=corr
# categorical medians
cat={}
for c,lab in [('FuelC','Fuel_Type'),('Transmission','Transmission'),('Owner_Type','Owner_Type'),('Color','Color'),('City','City')]:
    t=df.groupby(c).Car_Price.agg(['size','median','mean']); cat[lab]={str(k):dict(n=int(r['size']),median=float(r['median']),mean=float(r['mean'])) for k,r in t.iterrows()}
    rng=(t['median'].max()/t['median'].min()-1)*100; cat[lab]['_range_pct']=float(rng)
R['cat_medians']=cat
# lognormal fit from data itself (all km)
lk=np.log(df.Kms_Driven); mu,sd=lk.mean(),lk.std()
R['km_lognorm']=dict(mu=float(mu),sd=float(sd),expected_over_1m=float(len(df)*(1-stats.norm.cdf((math.log(1e6)-mu)/sd))),skew_log=float(stats.skew(lk)))
# age profile with IQR
ap=df.groupby('Registration_Age').Car_Price.quantile([.25,.5,.75]).unstack(); R['age_iqr']={int(a):[float(r[.25]),float(r[.5]),float(r[.75])] for a,r in ap.iterrows()}
kv=df.dropna(subset=['Kms_c']).copy(); kv['dec']=pd.qcut(kv.Kms_c,10,labels=False)
kd={}
for seg in ['All','Luxury','Non-luxury']:
    s=kv if seg=='All' else kv[kv.Segment==seg]
    q=s.groupby('dec').Car_Price.quantile([.25,.5,.75]).unstack(); kd[seg]={int(d):[float(r[.25]),float(r[.5]),float(r[.75])] for d,r in q.iterrows()}
R['km_dec_iqr']=kd; R['km_dec_edges']=[[float(a),float(b)] for a,b in kv.groupby('dec').Kms_c.agg(['min','max']).values]
# price shares
P=df.Car_Price; R['price_q']={str(q):float(P.quantile(q)) for q in [.05,.1,.25,.5,.75,.9,.95]}
json.dump(R,open('results.json','w'),indent=1)
for lab in corr: print(f"{lab:22s}", ' '.join(f"{corr[lab][g]['pearson']:+.4f}/{corr[lab][g]['spearman']:+.4f}" for g,_ in G))
print({k:round(v['_range_pct'],2) for k,v in cat.items()}); print(R['km_lognorm'])
