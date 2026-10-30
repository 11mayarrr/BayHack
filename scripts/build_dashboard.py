import csv, json, sys, os
d = sys.argv[1]; tpl = sys.argv[2]; out = sys.argv[3]
names = ['summary','weekday_hour','hourly','weekday','daily','hijri_month','day_of_month','ramadan_days','top_projects','model_results']
data = {n: list(csv.DictReader(open(os.path.join(d, n + '.csv'), encoding='utf-8'))) for n in names}
html = open(tpl, encoding='utf-8').read().replace('/*__DATA__*/null', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
open(out, 'w', encoding='utf-8').write(html)
print(out, len(html.encode()))
