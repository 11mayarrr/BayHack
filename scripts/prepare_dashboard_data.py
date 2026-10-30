import pandas as pd, sys
src=sys.argv[1]; out='data_clean/dashboard_data/'
raw=pd.read_csv(src,sep=';',encoding='utf-8-sig',dtype={'UserID_clean':str},parse_dates=['Gregorian_Date','CreationTime'])
print(len(raw), raw['Recurring_01'].value_counts().to_dict())
df=raw[raw['Recurring_01']!=1]
df=df[~df['flag_dup_extra'].astype(bool)].copy()
print(len(df), df.UserID_clean.nunique(), df.Amount_num.sum())
df['hour']=df.CreationTime.dt.hour
df['wd']=df.CreationTime.dt.dayofweek  # Mon=0
AR={6:'الأحد',0:'الاثنين',1:'الثلاثاء',2:'الأربعاء',3:'الخميس',4:'الجمعة',5:'السبت'}
ORDER={6:1,0:2,1:3,2:4,3:5,4:6,5:7}
df['weekday']=df.wd.map(AR); df['weekday_order']=df.wd.map(ORDER)
print(df.CreationTime.isna().sum(), (df.CreationTime.dt.date!=df.Gregorian_Date.dt.date).sum())
# heatmap weekday x hour
h=df.groupby(['weekday_order','weekday','hour']).agg(donations=('RowID','size'),donors=('UserID_clean','nunique'),amount=('Amount_num','sum')).reset_index()
full=pd.MultiIndex.from_product([range(1,8),range(24)],names=['weekday_order','hour']).to_frame(index=False)
full['weekday']=full.weekday_order.map({v:AR[k] for k,v in ORDER.items()})
h=full.merge(h,how='left',on=['weekday_order','weekday','hour']).fillna(0)
for c in ['donations','donors','amount']: h[c]=h[c].astype(int)
h.to_csv(out+'weekday_hour.csv',index=False)
# hourly
hr=df.groupby('hour').agg(donations=('RowID','size'),amount=('Amount_num','sum')).reindex(range(24),fill_value=0).reset_index()
hr['share']=(hr.donations/hr.donations.sum()).round(4)
hr.to_csv(out+'hourly.csv',index=False)
# donor-day & daily
dd=df.groupby(['UserID_clean','Gregorian_Date']).agg(n=('RowID','size'),amt=('Amount_num','sum')).reset_index()
daily=dd.groupby('Gregorian_Date').agg(donors=('UserID_clean','size'),donations=('n','sum'),amount=('amt','sum'))
days=pd.date_range(daily.index.min(),daily.index.max())
daily=daily.reindex(days); daily.index.name='date'
meta=df.groupby('Gregorian_Date').agg(hijri_month=('Hijri_Month','first'),hijri_month_name=('Hijri_Month_Name','first'),hijri_day=('Hijri_Day','first'))
daily=daily.join(meta).reset_index()
daily['date']=daily.date.dt.strftime('%Y-%m-%d')
daily.to_csv(out+'daily.csv',index=False)
print(daily.describe())
# weekday avg donors/day
d2=daily.dropna(subset=['donors']).copy(); d2['wd']=pd.to_datetime(d2.date).dt.dayofweek
wk=d2.groupby('wd').agg(avg_donors=('donors','mean'),avg_donations=('donations','mean'),days=('donors','size')).reset_index()
wk['weekday']=wk.wd.map(AR); wk['weekday_order']=wk.wd.map(ORDER); wk=wk.sort_values('weekday_order').drop(columns='wd')
wk[['avg_donors','avg_donations']]=wk[['avg_donors','avg_donations']].round(1)
wk[['weekday_order','weekday','avg_donors','avg_donations','days']].to_csv(out+'weekday.csv',index=False)
# hijri month avg donors/day (all days incl seasons)
hm=d2.groupby(['hijri_month','hijri_month_name']).agg(avg_donors=('donors','mean'),days=('donors','size'),donations=('donations','sum'),amount=('amount','sum')).reset_index()
hm['avg_donors']=hm.avg_donors.round(1); hm['hijri_month']=hm.hijri_month.astype(int)
hm.to_csv(out+'hijri_month.csv',index=False); print(hm)
# gregorian day of month
d2['dom']=pd.to_datetime(d2.date).dt.day
nonseason=d2[~d2.hijri_month.isin([9,12])]
dm=nonseason.groupby('dom').agg(avg_donors=('donors','mean'),days=('donors','size')).reset_index(); dm['avg_donors']=dm.avg_donors.round(1)
dm.to_csv(out+'day_of_month.csv',index=False)
# ramadan by hijri day
rm=d2[d2.hijri_month==9].groupby('hijri_day').agg(avg_donors=('donors','mean'),days=('donors','size')).reset_index(); rm['avg_donors']=rm.avg_donors.round(1); rm['hijri_day']=rm.hijri_day.astype(int)
rm.to_csv(out+'ramadan_days.csv',index=False)
# top projects
tp=df.groupby('Title_clean').agg(donations=('RowID','size'),donors=('UserID_clean','nunique'),amount=('Amount_num','sum')).sort_values('donations',ascending=False).head(10).reset_index().rename(columns={'Title_clean':'project'})
tp.to_csv(out+'top_projects.csv',index=False); print(tp)
# kpis
k=pd.DataFrame([{'donations':len(df),'donors':df.UserID_clean.nunique(),'amount':int(df.Amount_num.sum()),'days_with_data':int(daily.donors.notna().sum()),
 'avg_donors_per_day':round(daily.donors.mean(),1),'median_donors_per_day':float(daily.donors.median()),'start':daily.date.min(),'end':daily.date.max(),
 'excluded_recurring':int((raw.Recurring_01==1).sum()),'merged_duplicates':int(raw[raw.Recurring_01!=1].flag_dup_extra.astype(bool).sum())}])
k.to_csv(out+'summary.csv',index=False); print(k.T)
df['period']=(df.Hijri_Month==9).map({True:'رمضان',False:'باقي السنة'})
ndays=daily.dropna(subset=['donors']).assign(p=lambda x:(x.hijri_month==9).map({True:'رمضان',False:'باقي السنة'})).groupby('p').size()
hp=df.groupby(['period','hour']).size().unstack(0).reindex(range(24),fill_value=0)
res=pd.DataFrame({'hour':range(24)})
res['ramadan_per_day']=(hp['رمضان'].values/ndays['رمضان']).round(2)
res['other_per_day']=(hp['باقي السنة'].values/ndays['باقي السنة']).round(2)
res['ramadan_share']=(hp['رمضان']/hp['رمضان'].sum()).round(4).values
res['other_share']=(hp['باقي السنة']/hp['باقي السنة'].sum()).round(4).values
res['all_donations']=hp.sum(axis=1).values
res.to_csv(out+'hourly.csv',index=False); print(res, ndays)
