"""B2 (paso 1): días de eventos de inundación del COE con escenas Sentinel-1 RTC disponibles (Planetary Computer)."""
import pandas as pd, datetime as dt, pystac_client, planetary_computer as pc, collections
d = pd.read_csv('coe_eventos.csv'); d = d[d.tipo_de_ev.str.contains('Inund', na=False)].copy()
d['f'] = pd.to_datetime(d.fecha, unit='ms', errors='coerce'); d = d.dropna(subset=['f']); d = d[d.f >= '2021-06-01']
d['dia'] = d.f.dt.normalize()
cnt = d.groupby('dia').size(); dias = cnt[cnt >= 4].index
cat = pystac_client.Client.open('https://planetarycomputer.microsoft.com/api/stac/v1', modifier=pc.sign_inplace)
bbox = [-78.60, -0.35, -78.35, 0.05]
its = list(cat.search(collections=['sentinel-1-rtc'], bbox=bbox, datetime='2021-01-01/2024-12-31', max_items=3000).items())
print('escenas', len(its), collections.Counter(i.properties.get('sat:relative_orbit') for i in its).most_common(6))
rows = []
for D in dias:
    post = [i for i in its if D <= pd.Timestamp(i.datetime).tz_localize(None).normalize() <= D + pd.Timedelta(days=3)]
    rows.append((D.date(), int(cnt[D]), len(post), sorted({(i.properties.get('sat:relative_orbit'), i.properties.get('sat:orbit_state')) for i in post})))
for r in rows: print(r)
