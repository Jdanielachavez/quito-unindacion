"""A1 incertidumbre del ranking (bootstrap por bloques de 5 km de los reportes de entrenamiento, ancla refitada)
   A3 validación dejando un bloque de 5 km fuera (los 331 reportes; la parroquia de cada reporte no está en las matrices).
Uso: QUITO_REPO=/ruta/al/repo NBI_CSV=...csv python robustez_a1_a3.py [salida] [réplicas]
"""
import os, sys, json, glob, time
import numpy as np, pandas as pd
REPO = os.environ.get('QUITO_REPO', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + '/'; OUT = sys.argv[1] if len(sys.argv) > 1 else '.'; NREP = int(sys.argv[2]) if len(sys.argv) > 2 else 300
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robustez_a4_a6_a7.py'), encoding='utf-8').read().split('# ---------------- A4')[0]
exec(src.replace("OUT = sys.argv[1] if len(sys.argv) > 1 else '.'", ""))
names = P['temporal__vias_fabdem']['names']; ix = {n: i for i, n in enumerate(names)}
d = load('temporal__vias_fabdem'); LAM_PUB, ALP_PUB = P['temporal__vias_fabdem']['lambda_clipped'], P['temporal__vias_fabdem']['alpha_clipped']
t0 = time.time()
# ---------------- A1 ----------------
parts = sorted(glob.glob(REPO + 'PIXELES_*.npz')); Xs, pid, wid = [], [], []
for p in parts:
    z = np.load(p, allow_pickle=False); Xs.append(z['X']); pid.append(z['pid'].astype(int)); wid.append(z['wid'].astype(int))
X = np.vstack(Xs).astype(np.float32); pid = np.concatenate(pid); wid = np.concatenate(wid)
G = json.load(open(REPO + 'GRILLA.json')); units = G['weather_units']; nc = len(units)
wea = pd.read_csv(REPO + 'DATOS_LLUVIA_ESCENARIOS.csv'); soc = pd.read_csv(REPO + 'DATOS_PARROQUIAS.csv', dtype={'parroquia': str})
nbi = pd.read_csv(os.environ.get('NBI_CSV', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "02_DATOS_NBI", "nbi_hogar_65_parroquias_microdatos.csv")), dtype={'parroquia': str}).set_index('parroquia').pct_hogares_nbi_micro
n = soc.parroquia.map(nbi).values / 100
idx = dict(zip(wea[wea.modelo == 'red_ENSO__beta_PIT'].unit, wea[wea.modelo == 'red_ENSO__beta_PIT'].p_humedo)); prob = np.array([idx[u] for u in units])
pidw = pid * nc + wid
def prioridad(beta):
    s = X @ beta.astype(np.float32); thr = np.quantile(s, 0.90); use = s >= thr
    c = np.bincount(pidw[use], minlength=66 * nc).reshape(66, nc); H = c[1:] @ prob * 0.01
    return H, H * n
# punto de referencia: el ancla publicada
H0, I0 = prioridad(np.array(P['temporal__vias_fabdem']['anchor']))
top = lambda v, k=13: set(np.argsort(-v, kind='stable')[:k])
print('ancla publicada: top13 por H y por índice', len(top(H0)), len(top(I0)), '| cambian por NBI:', sorted(soc.nombre[i] for i in top(I0) - top(H0)))
tr = d['etrain']; Xe_tr, V_tr, blk_tr = d['Xe'][tr], d['valid_e'][tr], d['block'][tr]; Xb = d['Xb'][d['btrain']]
ub = np.unique(blk_tr); rng = np.random.default_rng(11109)
mH = np.zeros(65); mI = np.zeros(65); mEnt = np.zeros(65); rkH = np.zeros((NREP, 65)); rkI = np.zeros((NREP, 65)); est = np.zeros(65)
for r in range(NREP):
    pick = rng.choice(ub, len(ub)); ids = np.concatenate([np.where(blk_tr == k)[0] for k in pick])
    b = fit(Xe_tr[ids], V_tr[ids], Xb, LAM_PUB) * ALP_PUB
    H, I = prioridad(b); tH, tI = top(H), top(I)
    for i in tH: mH[i] += 1
    for i in tI: mI[i] += 1
    for i in tI - tH: mEnt[i] += 1
    rkH[r] = (-H).argsort().argsort() + 1; rkI[r] = (-I).argsort().argsort() + 1
    if (r + 1) % 50 == 0: print('A1', r + 1, '/', NREP, f'{time.time() - t0:.0f}s', flush=True)
a1 = pd.DataFrame({'parroquia': soc.parroquia, 'nombre': soc.nombre, 'prob_top13_por_area': mH / NREP, 'prob_top13_por_indice_nbi': mI / NREP,
                   'prob_entra_por_nbi': mEnt / NREP, 'puesto_indice_mediana': np.median(rkI, 0), 'puesto_indice_p5': np.quantile(rkI, .05, 0), 'puesto_indice_p95': np.quantile(rkI, .95, 0),
                   'top13_indice_punto': [int(i in top(I0)) for i in range(65)]}).round(3)
a1.sort_values('prob_top13_por_indice_nbi', ascending=False).to_csv(f'{OUT}/A1_incertidumbre_ranking.csv', index=False, encoding='utf-8-sig')
print('\n=== A1 probabilidad de pertenecer al top 13 por índice NBI (réplicas: %d)' % NREP)
print(a1[a1.prob_top13_por_indice_nbi >= 0.05].sort_values('prob_top13_por_indice_nbi', ascending=False)[['nombre', 'prob_top13_por_area', 'prob_top13_por_indice_nbi', 'prob_entra_por_nbi', 'puesto_indice_p5', 'puesto_indice_mediana', 'puesto_indice_p95', 'top13_indice_punto']].to_string(index=False))
print('esperado de parroquias con prob ≥ 0.9:', int((a1.prob_top13_por_indice_nbi >= 0.9).sum()), '| entre 0.5 y 0.9:', int(((a1.prob_top13_por_indice_nbi >= .5) & (a1.prob_top13_por_indice_nbi < .9)).sum()))
print('Pomasqui entra por NBI con prob %.2f; Tumbaco %.2f' % (a1.set_index('nombre').loc['POMASQUI', 'prob_entra_por_nbi'], a1.set_index('nombre').loc['TUMBACO', 'prob_entra_por_nbi']))
# ---------------- A3 ----------------
allr = np.ones(len(d['Xe']), bool); blk = d['block']; XeA, VA, XbA = d['Xe'], d['valid_e'], d['Xb']
specs = {'Ancla (25), λ=0.1 α=1.25': (names, 1.25), 'Ancla (25), α=1': (names, 1.0),
         'Urbano (3)': (['construido_100m', 'construido_500m', 'log_distancia_vial'], 1.0),
         'Solo físico (16)': ([n_ for n_ in names if n_ not in ['construido_100m', 'construido_500m', 'cobertura_50', 'log_distancia_vial', 'log_construido_contribuyente_ha', 'fraccion_construida_contribuyente', 'cobertura_70', 'cobertura_95', 'cobertura_100']], 1.0),
         'Terreno + drenaje (7)': (['altitud_km', 'pendiente_grados', 'posicion_topografica_m', 'relieve_local_m', 'log_dist_rio', 'log_dist_quebrada', 'log_dist_colector'], 1.0)}
blocks = np.unique(blk); rows = []; per = {k: [] for k in specs}
for k in specs: per[k] = {'ev': np.zeros(len(blk)), 'cap': np.zeros(len(blk))}
for j, bk in enumerate(blocks):
    te = blk == bk; trn = ~te
    for lab, (vs, a) in specs.items():
        cols = [ix[v] for v in vs]; b = fit(XeA[trn][:, :, cols], VA[trn], XbA[:, cols], LAM_PUB) * a
        ev, cap = evaluar(XeA[te][:, :, cols] @ b, XbA[:, cols] @ b, VA[te]); per[lab]['ev'][te] = ev; per[lab]['cap'][te] = cap
    if (j + 1) % 20 == 0: print('A3', j + 1, '/', len(blocks), f'{time.time() - t0:.0f}s', flush=True)
rng = np.random.default_rng(11109); draw = rng.integers(0, len(blocks), (2000, len(blocks))); cnt = np.array([(blk == k).sum() for k in blocks])
def ic(v):
    s = np.array([v[blk == k].sum() for k in blocks]); sim = s[draw].sum(1) / cnt[draw].sum(1); return v.mean(), np.quantile(sim, .025), np.quantile(sim, .975)
for lab in specs:
    m, lo, hi = ic(per[lab]['ev']); mc, loc, hic = ic(per[lab]['cap'])
    rows.append(dict(modelo=lab, reportes=len(blk), bloques=len(blocks), logdens=round(m, 3), logdens_ic_inf=round(lo, 3), logdens_ic_sup=round(hi, 3),
                     captura=round(mc, 3), captura_ic_inf=round(loc, 3), captura_ic_sup=round(hic, 3)))
a3 = pd.DataFrame(rows); a3.to_csv(f'{OUT}/A3_dejando_un_bloque_fuera.csv', index=False, encoding='utf-8-sig')
print('\n=== A3 validación dejando un bloque de 5 km fuera (331 reportes, azar = 0.000 / 0.100)'); print(a3.to_string(index=False))
print(f'tiempo total {time.time() - t0:.0f}s')
