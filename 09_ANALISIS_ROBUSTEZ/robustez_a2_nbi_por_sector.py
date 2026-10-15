"""A2 NBI por sector censal dentro de la parroquia.
Asigna cada píxel construido a su sector censal (capa municipal de sectores, geometría descargada y rasterizada a la grilla de 10 m),
calcula el índice a nivel sector (decil superior × P(húmedo) × tasa de hogares con NBI del sector) y lo compara con el índice parroquial.
Uso: QUITO_REPO=/ruta/al/repo python robustez_a2_nbi_por_sector.py [salida]
"""
import os, sys, json, glob, urllib.parse, urllib.request
import numpy as np, pandas as pd
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
REPO = os.environ.get('QUITO_REPO', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + '/'; OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
URL = 'https://geoquito.quito.gob.ec/server/rest/services/web_service/s_nbi_porcentaje_personas_con_pobreza_por_nbi_2022/MapServer/3/query'
cache = os.path.join(OUT, 'sectores_geometria_32717.json')
if os.path.exists(cache): feats = json.load(open(cache))
else:
    import time
    feats, off = [], 0
    while True:
        q = urllib.parse.urlencode(dict(where='1=1', outFields='OBJECTID,Sector_DMQ,parroquia,nom_par,total_hog,pobT,h_nbi,noh_nbi', returnGeometry='true',
                                        outSR='32717', geometryPrecision='1', maxAllowableOffset='2', orderByFields='OBJECTID', resultOffset=off, resultRecordCount=100, f='json'))
        for intento in range(6):
            try:
                with urllib.request.urlopen(URL + '?' + q, timeout=300) as r: page = json.load(r)['features']
                break
            except Exception as e:
                print('reintento', intento, off, type(e).__name__, flush=True); time.sleep(3 * (intento + 1))
        else:
            raise RuntimeError('descarga fallida en offset %d' % off)
        feats += page
        if len(page) < 100: break
        off += 100
        if off % 1000 == 0: print('descargados', off, flush=True)
json.dump(feats, open(cache, 'w'))
print('sectores con geometría:', len(feats))
G = json.load(open(REPO + 'GRILLA.json')); tr = G['transform']; W, H = G['width'], G['height']
def area_firmada(r):
    a = np.asarray(r); x, y = a[:, 0], a[:, 1]; return 0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])
# rasterización (sectores grandes primero para que los pequeños rellenen huecos)
img = Image.new('I', (W, H), 0); dr = ImageDraw.Draw(img)
items = []
for k, f in enumerate(feats):
    rings = (f.get('geometry') or {}).get('rings', [])
    ar = sum(abs(area_firmada(r)) for r in rings if len(r) > 3)
    items.append((ar, k, rings))
items.sort(key=lambda t: -t[0])
for ar, k, rings in items:
    outer = [r for r in rings if area_firmada(r) < 0]      # anillos exteriores en sentido horario (convención ESRI)
    holes = [r for r in rings if area_firmada(r) >= 0]
    for r in outer: dr.polygon([((x - tr[2]) / tr[0], (y - tr[5]) / tr[4]) for x, y in r], fill=k + 1)
    for r in holes: dr.polygon([((x - tr[2]) / tr[0], (y - tr[5]) / tr[4]) for x, y in r], fill=0)
raster = np.asarray(img).astype(np.int32); del img
print('raster', raster.shape, '| sectores presentes:', len(np.unique(raster)) - 1)
attrs = pd.DataFrame([f['attributes'] for f in feats]); attrs['id'] = np.arange(1, len(attrs) + 1)
for k in ('total_hog', 'pobT', 'h_nbi', 'noh_nbi'): attrs[k] = pd.to_numeric(attrs[k], errors='coerce')
attrs['tasa'] = attrs.h_nbi / (attrs.h_nbi + attrs.noh_nbi)
# píxeles construidos
parts = sorted(glob.glob(REPO + 'PIXELES_*.npz')); fl, sc, wd = [], [], []
for p in parts:
    z = np.load(p, allow_pickle=False); fl.append(z['flat']); sc.append(z['referencia_score'][:, 0]); wd.append(z['wid'].astype(int))
flat = np.concatenate(fl); score = np.concatenate(sc).astype(np.float64); wid = np.concatenate(wd)
sid = raster.reshape(-1)[flat]
print('píxeles construidos:', len(flat), '| sin sector:', int((sid == 0).sum()), '(%.2f%%)' % (100 * (sid == 0).mean()))
units = G['weather_units']; wea = pd.read_csv(REPO + 'DATOS_LLUVIA_ESCENARIOS.csv'); soc = pd.read_csv(REPO + 'DATOS_PARROQUIAS.csv', dtype={'parroquia': str})
res = {}
thr = np.quantile(score, 0.90); use = (score >= thr) & (sid > 0)
for wm in dict.fromkeys(wea.modelo):
    idx = dict(zip(wea[wea.modelo == wm].unit, wea[wea.modelo == wm].p_humedo)); prob = np.array([idx[u] for u in units])
    w = prob[wid]
    Hs = np.bincount(sid[use], weights=w[use] * 0.01, minlength=len(attrs) + 1)[1:]          # ha ponderadas por sector
    res[wm] = Hs
attrs['construido_ha'] = np.bincount(sid[sid > 0], minlength=len(attrs) + 1)[1:] * 0.01
attrs['prioritario_ha'] = np.bincount(sid[use], minlength=len(attrs) + 1)[1:] * 0.01
nbi_p = pd.read_csv(os.environ.get('NBI_CSV', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "02_DATOS_NBI", "nbi_hogar_65_parroquias_microdatos.csv")), dtype={'parroquia': str}).set_index('parroquia').pct_hogares_nbi_micro
top = lambda v, k=13: set(np.argsort(-v, kind='stable')[:k])
from scipy.stats import spearmanr
rows = []; tabla = {}
for wm, Hs in res.items():
    a = attrs.copy(); a['H_sector'] = Hs; a['I_sector'] = a.H_sector * a.tasa.fillna(0)
    par = a.groupby('parroquia').agg(H=('H_sector', 'sum'), I_sector=('I_sector', 'sum')).reindex(soc.parroquia)
    par['I_parroquia'] = par.H * soc.parroquia.map(nbi_p).values / 100
    tp, ts, th = top(par.I_parroquia.values), top(par.I_sector.values), top(par.H.values)
    rows.append(dict(escenario_lluvia=wm, top13_indice_parroquial_vs_sector=len(tp & ts), entran_con_sector=', '.join(sorted(soc.nombre[i] for i in ts - tp)),
                     salen=', '.join(sorted(soc.nombre[i] for i in tp - ts)), spearman_65=round(spearmanr(par.I_parroquia, par.I_sector)[0], 4),
                     cambian_por_nbi_parroquial=len(tp - th), cambian_por_nbi_sector=len(ts - th)))
    tabla[wm] = a
r = pd.DataFrame(rows); r.to_csv(f'{OUT}/A2_indice_sector_vs_parroquia.csv', index=False, encoding='utf-8-sig'); print(r.to_string(index=False))
a = tabla['red_ENSO__beta_PIT']
cols = ['Sector_DMQ', 'nom_par', 'total_hog', 'tasa', 'construido_ha', 'prioritario_ha', 'H_sector', 'I_sector']
a.sort_values('I_sector', ascending=False)[cols].head(40).round(3).to_csv(f'{OUT}/A2_sectores_prioritarios_top40.csv', index=False, encoding='utf-8-sig')
print('\nTop 15 sectores por índice (escenario principal):'); print(a.sort_values('I_sector', ascending=False)[cols].head(15).round(3).to_string(index=False))
# heterogeneidad dentro de la parroquia: ¿el área prioritaria cae en sectores con más o menos NBI que la media parroquial?
rate_par = soc.set_index('parroquia').index.map(nbi_p).values / 100
a['tasa_par'] = a.parroquia.map(dict(zip(soc.parroquia, rate_par)))
w = a.H_sector.values; ok = a.tasa.notna() & (w > 0)
print('\nNBI medio ponderado por área prioritaria: sector %.2f%% vs parroquia %.2f%%' % (100 * np.average(a.tasa[ok], weights=w[ok]), 100 * np.average(a.tasa_par[ok], weights=w[ok])))
rr = a[ok].groupby('parroquia').apply(lambda g: pd.Series({'tasa_sector_ponderada': np.average(g.tasa, weights=g.H_sector), 'tasa_parroquia': g.tasa_par.iloc[0], 'H': g.H_sector.sum()}), include_groups=False)
rr['dif_pp'] = 100 * (rr.tasa_sector_ponderada - rr.tasa_parroquia)
rr.join(soc.set_index('parroquia').nombre).sort_values('dif_pp').round(3).to_csv(f'{OUT}/A2_nbi_en_area_prioritaria_vs_parroquia.csv', encoding='utf-8-sig')
print('diferencia (sector ponderado - parroquia) en pp: media %.2f | min %.2f | max %.2f' % (rr.dif_pp.mean(), rr.dif_pp.min(), rr.dif_pp.max()))
