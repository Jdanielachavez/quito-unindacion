"""B1 validación con una fuente independiente: eventos de inundación del COE municipal (capa Eventos_COE_2005_Mayo_2024).
Cada evento se asigna al píxel construido más cercano (≤ radio) y se evalúa dentro del construido:
  captura = proporción de eventos cuyo píxel está en el 10 % superior del construido; log densidad relativa dentro del construido.
Uso: QUITO_REPO=/ruta/al/repo python robustez_b1_validacion_coe.py [salida]
"""
import os, sys, json, glob, urllib.parse, urllib.request
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
from scipy.special import logsumexp as lse
REPO = os.environ.get('QUITO_REPO', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + '/'; OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robustez_a4_a6_a7.py'), encoding='utf-8').read().split('# ---------------- A4')[0]
exec(src.replace("OUT = sys.argv[1] if len(sys.argv) > 1 else '.'", ""))
URL = 'https://geoquito.quito.gob.ec/server/rest/services/Hosted/Eventos_2024/FeatureServer/0/query'
def descargar():
    filas, off = [], 0
    while True:
        q = urllib.parse.urlencode(dict(where='1=1', outFields='fid,fecha,tipo_de_ev,subcategor,anio,parroquia,x,y', returnGeometry='false',
                                        orderByFields='fid', resultOffset=off, resultRecordCount=2000, f='json'))
        with urllib.request.urlopen(URL + '?' + q, timeout=180) as r: feats = [f['attributes'] for f in json.load(r)['features']]
        filas += feats
        if len(feats) < 2000: break
        off += 2000
    return pd.DataFrame(filas)
cache = os.path.join(OUT, 'coe_eventos.csv')
ev = pd.read_csv(cache) if os.path.exists(cache) else descargar()
ev.to_csv(cache, index=False, encoding='utf-8-sig')
ev['fecha_dt'] = pd.to_datetime(ev.fecha, unit='ms', errors='coerce')
inu = ev[ev.tipo_de_ev.astype(str).str.contains('Inundaci', case=False, na=False)].copy()
print('eventos COE:', len(ev), '| inundación:', len(inu), '| por año:', inu.anio.value_counts().sort_index().to_dict())
# ---- píxeles construidos
G = json.load(open(REPO + 'GRILLA.json')); tr = G['transform']; W = G['width']
parts = sorted(glob.glob(REPO + 'PIXELES_*.npz')); Xs, flats, ref = [], [], []
for p in parts:
    z = np.load(p, allow_pickle=False); Xs.append(z['X']); flats.append(z['flat']); ref.append(z['referencia_score'])
X = np.vstack(Xs); flat = np.concatenate(flats); ref = np.vstack(ref)
col = flat % W; row = flat // W
px = tr[2] + (col + 0.5) * tr[0]; py = tr[5] + (row + 0.5) * tr[4]
tree = cKDTree(np.column_stack([px, py]))
# ---- modelos (ancla temporal vías+FABDEM y alternativas ajustadas con los reportes de entrenamiento)
names = P['temporal__vias_fabdem']['names']; ix = {n: i for i, n in enumerate(names)}
d = load('temporal__vias_fabdem')
EXPO = ['construido_100m', 'construido_500m', 'cobertura_50', 'log_distancia_vial', 'log_construido_contribuyente_ha', 'fraccion_construida_contribuyente']
CONST = ['cobertura_70', 'cobertura_95', 'cobertura_100']
specs = {'Ancla (25 variables)': names, 'Solo físico (16)': [n for n in names if n not in EXPO + CONST],
         'Urbano (3)': ['construido_100m', 'construido_500m', 'log_distancia_vial'],
         'Terreno + drenaje (7)': ['altitud_km','pendiente_grados','posicion_topografica_m','relieve_local_m','log_dist_rio','log_dist_quebrada','log_dist_colector']}
scores = {}
for lab, vs in specs.items():
    cols = [ix[v] for v in vs]; b, _, _ = fit_select(d, cols); scores[lab] = X[:, cols] @ b
scores['Ancla + red (referencia del repo)'] = ref[:, 0].astype(np.float64)
for k in scores: assert np.isfinite(scores[k]).all()
def evaluar_eventos(sub, radio, etiqueta):
    dist, j = tree.query(np.column_stack([sub.x.values, sub.y.values]), distance_upper_bound=radio)
    ok = np.isfinite(dist); out = []
    for lab, s in scores.items():
        thr = np.quantile(s, 0.90); norm = lse(s) - np.log(len(s))
        sj = s[j[ok]]
        cap = float((sj >= thr).mean()); ld = float((sj - norm).mean())
        # IC95 por bootstrap de bloques de 5 km
        blk = (np.floor(sub.x.values[ok] / 5000) * 1000 + np.floor(sub.y.values[ok] / 5000)).astype(int); ub = np.unique(blk)
        rng = np.random.default_rng(11109); caps, lds = [], []
        for _ in range(1000):
            pick = rng.choice(ub, len(ub)); idx = np.concatenate([np.where(blk == k)[0] for k in pick])
            caps.append((sj[idx] >= thr).mean()); lds.append((sj[idx] - norm).mean())
        out.append(dict(subconjunto=etiqueta, radio_m=radio, modelo=lab, eventos=int(ok.sum()), de=len(sub), captura_10pct=round(cap, 3),
                        captura_ic_inf=round(float(np.quantile(caps, .025)), 3), captura_ic_sup=round(float(np.quantile(caps, .975)), 3),
                        logdens_dentro_construido=round(ld, 3), logdens_ic_inf=round(float(np.quantile(lds, .025)), 3), logdens_ic_sup=round(float(np.quantile(lds, .975)), 3)))
    return out
rows = []
post = inu[(inu.anio >= 2022)]; todos = inu[(inu.anio >= 2010)]
for radio in (50, 100):
    rows += evaluar_eventos(post, radio, 'posteriores al entrenamiento (2022 a mayo 2024)')
    rows += evaluar_eventos(todos, radio, 'todos 2010 a mayo 2024 (parcialmente en entrenamiento)')
r = pd.DataFrame(rows); r.to_csv(f'{OUT}/B1_validacion_coe.csv', index=False, encoding='utf-8-sig')
pd.set_option('display.width', 250)
print(r[r.radio_m == 50][['subconjunto', 'modelo', 'eventos', 'de', 'captura_10pct', 'captura_ic_inf', 'captura_ic_sup', 'logdens_dentro_construido', 'logdens_ic_inf', 'logdens_ic_sup']].to_string(index=False))
print('\nradio 100 m (captura):'); print(r[r.radio_m == 100].pivot_table(index='modelo', columns='subconjunto', values='captura_10pct').to_string())
