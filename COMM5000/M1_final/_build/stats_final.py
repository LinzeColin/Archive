import pandas as pd, numpy as np, json
from scipy import stats
df=pd.read_pickle('clean.pkl'); R=json.load(open('results.json'))
tech={}
for c in ['Mileage_kmpl','Engine_CC','Horsepower']:
    x=df[c].where(df[c]>0); m,s=x.mean(),x.std()
    flag=(df[c]<=0)|(df[c]<m-3*s)|(df[c]>m+3*s)
    tech[c]=dict(zero=int((df[c]==0).sum()),sd3=int(((df[c]>0)&((df[c]<m-3*s)|(df[c]>m+3*s))).sum()),lo=float(m-3*s),hi=float(m+3*s),kurt=float(stats.kurtosis(x.dropna())))
    df[c+'_c']=df[c].where(~flag)
R['tech']=tech
def mode_cont(x,width):
    b=np.floor(x/width)*width; v=b.value_counts(); return float(v.index[0]+width/2)
VARS=[('Car_Price',50000),('Registration_Age',None),('Kms_c',10000),('Engine_CC_c',50),('Horsepower_c',5),('Mileage_kmpl_c',0.5),('Accidents',None)]
desc={}
for g,sub in [('All',df),('Luxury',df[df.Segment=='Luxury']),('Non-luxury',df[df.Segment=='Non-luxury'])]:
    desc[g]={}
    for v,w in VARS:
        x=sub[v].dropna()
        desc[g][v]=dict(n=int(len(x)),mean=float(x.mean()),median=float(x.median()),mode=mode_cont(x,w) if w else float(x.value_counts().index[0]),
            sd=float(x.std(ddof=1)),min=float(x.min()),max=float(x.max()),q1=float(x.quantile(.25)),q3=float(x.quantile(.75)),skew=float(stats.skew(x)),cv=float(x.std()/x.mean()))
R['desc']=desc
# segment shares for binary / categorical
seg={}
for g,sub in [('All',df),('Luxury',df[df.Segment=='Luxury']),('Non-luxury',df[df.Segment=='Non-luxury'])]:
    seg[g]=dict(ins=float(sub.Insurance_Valid.mean()),svc=float(sub.Service_History.mean()),tax=float(sub.Tax_Paid.mean()),
        first_owner=float((sub.Owner_Type=='First').mean()),auto=float((sub.Transmission=='Automatic').mean()),unk_any=float((sub[['FuelC','Transmission','Color','City']]=='Unknown').any(axis=1).mean()))
R['seg_shares']=seg
# fixed MdAPE for simple log model preview
s=df[['Kms_c','Horsepower_c','Engine_CC_c','Car_Price']].dropna()
X=np.column_stack([np.ones(len(s)),np.log(s.Kms_c),np.log(s.Horsepower_c),np.log(s.Engine_CC_c)])
b=np.linalg.lstsq(X,np.log(s.Car_Price),rcond=None)[0]; yh=X@b; y=np.log(s.Car_Price)
R['prev_model']=dict(beta=[float(v) for v in b],r2=float(1-((y-yh)**2).sum()/((y-y.mean())**2).sum()),mdape=float(np.median(np.abs(s.Car_Price-np.exp(yh))/s.Car_Price)*100),n=len(s))
# 80% prediction band width from global quantiles (P10-P90) relative to median
P=df.Car_Price; R['p10_p90']=[float(P.quantile(.1)),float(P.quantile(.9))]
R['logcorr_final']={c:float(np.corrcoef(np.log(s[c]),y)[0,1]) for c in ['Kms_c','Horsepower_c','Engine_CC_c']}
R['corr_engine_hp']=float(np.corrcoef(s.Engine_CC_c,s.Horsepower_c)[0,1])
df.to_pickle('clean.pkl'); json.dump(R,open('results.json','w'),indent=1)
print(json.dumps(tech,indent=1)); print(R['prev_model'],R['p10_p90'],R['logcorr_final'],R['corr_engine_hp']); print(seg)
