"""A4 referencias simples, A6 ancla sola frente a ancla + red, A7 calibración por deciles.
Uso: QUITO_REPO=/ruta/al/repo python robustez_a4_a6_a7.py [carpeta_salida]
"""
import os, sys, json, itertools
import numpy as np, pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp as lse
REPO = os.environ.get('QUITO_REPO', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + '/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
sys.path.insert(0, REPO)
from modelo import evaluar, ensamble, inferir
P = json.load(open(REPO + 'PARAMETROS.json'))
LAM = (0.001, 0.01, 0.1, 1.0); ALP = (0.25, 0.5, 0.75, 1.0, 1.25)
def load(key):
    z = np.load(REPO + f'DATOS_{key}.npz', allow_pickle=False); return {k: z[k] for k in z.files}
def nll(b, Xe, V, Xb, lam):
    fe = np.where(V, Xe @ b, -np.inf)
    return -((lse(fe, axis=1) - np.log(V.sum(1))).mean() - (lse(Xb @ b) - np.log(len(Xb)))) + 0.5 * lam * np.sum(b ** 2)
def fit(Xe, V, Xb, lam):
    return minimize(nll, np.zeros(Xe.shape[2]), args=(Xe, V, Xb, lam), method='L-BFGS-B', options=dict(maxiter=2000, ftol=1e-14, gtol=1e-9)).x
def cal(d, cols, b):
    Xe, V, Xb = d['Xe'][d['ecal']][:, :, cols], d['valid_e'][d['ecal']], d['Xb'][d['bcal']][:, cols]
    fe = np.where(V, Xe @ b, -np.inf)
    return float((lse(fe, axis=1) - np.log(V.sum(1))).mean() - (lse(Xb @ b) - np.log(len(Xb))))
def fit_select(d, cols):
    """Selección secuencial como la publicada: primero λ con α=1, luego α."""
    Xe, V, Xb = d['Xe'][d['etrain']][:, :, cols], d['valid_e'][d['etrain']], d['Xb'][d['btrain']][:, cols]
    betas = {l: fit(Xe, V, Xb, l) for l in LAM}
    lam = max(LAM, key=lambda l: cal(d, cols, betas[l]))
    a = max(ALP, key=lambda a: cal(d, cols, a * betas[lam]))
    return a * betas[lam], lam, a
def test_metrics(d, cols, b):
    e, bm = d['etest'], d['btest']
    ev, cap = evaluar(d['Xe'][e][:, :, cols] @ b, d['Xb'][bm][:, cols] @ b, d['valid_e'][e])
    return float(ev.mean()), float(cap.mean())

# ---------------- A4: referencias simples ----------------
names = P['temporal__vias_fabdem']['names']; ix = {n: i for i, n in enumerate(names)}
specs = {
 'Solo distancia a quebrada': ['log_dist_quebrada'], 'Solo distancia a río': ['log_dist_rio'], 'Solo distancia a colector': ['log_dist_colector'],
 'Solo pendiente': ['pendiente_grados'], 'Solo altitud': ['altitud_km'], 'Solo construido 500 m': ['construido_500m'], 'Solo distancia vial': ['log_distancia_vial'],
 'Drenaje (3 distancias)': ['log_dist_rio', 'log_dist_quebrada', 'log_dist_colector'],
 'Terreno (4)': ['altitud_km', 'pendiente_grados', 'posicion_topografica_m', 'relieve_local_m'],
 'Urbano (construido 100/500 m y vial)': ['construido_100m', 'construido_500m', 'log_distancia_vial'],
 'Terreno + drenaje (7)': ['altitud_km', 'pendiente_grados', 'posicion_topografica_m', 'relieve_local_m', 'log_dist_rio', 'log_dist_quebrada', 'log_dist_colector'],
 'Modelo completo, ancla (25)': names}
rows = []
for lab, vs in specs.items():
    cols = [ix[v] for v in vs]; r = {'modelo': lab, 'n_variables': len(cols)}
    for proto in ('temporal', 'espacial'):
        d = load(f'{proto}__vias_fabdem'); b, lam, a = fit_select(d, cols); ld, cap = test_metrics(d, cols, b)
        r[f'{proto}_logdens'] = round(ld, 3); r[f'{proto}_captura'] = round(cap, 3); r[f'{proto}_lambda_alpha'] = f'{lam}/{a}'
    rows.append(r)
a4 = pd.DataFrame(rows); a4.to_csv(f'{OUT}/A4_referencias_simples.csv', index=False, encoding='utf-8-sig')
print('=== A4 referencias simples (test; azar = 0.000 y captura 0.100)'); print(a4.drop(columns=[c for c in a4 if c.endswith('lambda_alpha')]).to_string(index=False))

# ---------------- A6: ancla sola frente a ancla + red ----------------
z = np.load(REPO + 'REFERENCIA_intersecciones.npz'); G = json.load(open(REPO + 'GRILLA.json')); units = G['weather_units']
wea = pd.read_csv(REPO + 'DATOS_LLUVIA_ESCENARIOS.csv'); soc = pd.read_csv(REPO + 'DATOS_PARROQUIAS.csv', dtype={'parroquia': str})
nbi_path = os.environ.get('NBI_CSV', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "02_DATOS_NBI", "nbi_hogar_65_parroquias_microdatos.csv"))  # CSV con columnas parroquia, pct_hogares_nbi_micro
nbi = pd.read_csv(nbi_path, dtype={'parroquia': str}).set_index('parroquia').pct_hogares_nbi_micro if nbi_path else None
def area(tm, wm, q=90):
    idx = dict(zip(wea[wea.modelo == wm].unit, wea[wea.modelo == wm].p_humedo)); return z[f'{tm}_q{q}'][1:] @ np.array([idx[u] for u in units]) * 0.01
top = lambda v, k=13: set(np.argsort(-v, kind='stable')[:k])
n = soc.parroquia.map(nbi).values / 100 if nbi is not None else soc.pc_pnbi.values / 100
from scipy.stats import spearmanr
rows = []
for wm in dict.fromkeys(wea.modelo):
    Ar, Aa = area('red_residual', wm), area('ancla_acotada', wm)
    rows.append(dict(escenario_lluvia=wm,
        top13_area_coinciden=len(top(Ar) & top(Aa)), top13_indice_coinciden=len(top(Ar * n) & top(Aa * n)),
        spearman_area=round(spearmanr(Ar, Aa)[0], 4), spearman_indice=round(spearmanr(Ar * n, Aa * n)[0], 4),
        cambian_por_nbi_ancla=len(top(Aa * n) - top(Aa)), cambian_por_nbi_red=len(top(Ar * n) - top(Ar))))
a6 = pd.DataFrame(rows); a6.to_csv(f'{OUT}/A6_ancla_vs_red.csv', index=False, encoding='utf-8-sig')
print('\n=== A6 ancla sola vs ancla + red (13 parroquias)'); print(a6.to_string(index=False))
cnt = np.zeros(65, int)
for wm in dict.fromkeys(wea.modelo):
    for i in top(area('ancla_acotada', wm) * n): cnt[i] += 1
print('estables en las 3 lluvias con ancla sola:', sorted(soc.nombre[i] for i in range(65) if cnt[i] == 3))

# ---------------- A7: calibración por deciles ----------------
W = np.load(REPO + 'PESOS.npz', allow_pickle=False)
rows = []
for proto in ('temporal', 'espacial'):
    key = f'{proto}__vias_fabdem'; d = load(key); e, bm = d['etest'], d['btest']
    Xe, Xb, V = d['Xe'][e], d['Xb'][bm], d['valid_e'][e]; nrep = int(e.sum())
    sel = json.load(open(REPO + 'SELECCION.json'))[key]['bound_selected_by_calibration']; lab = str(sel).replace('.', 'p')
    fes, fbs = [], []
    for s in (5101, 5102, 5103):
        pre = f'{key}__B{lab}__s{s}'
        fe, _ = inferir(Xe.reshape(-1, Xe.shape[2]), W, pre, sel); fb, _ = inferir(Xb, W, pre, sel)
        fes.append(fe.reshape(V.shape)); fbs.append(fb)
    modelos = {'ancla': (Xe @ d['anchor'], Xb @ d['anchor']), f'ancla + red (B={sel})': ensamble(fes, fbs)}
    for mname, (fe, fb) in modelos.items():
        edges = np.quantile(fb, np.linspace(0, 1, 11)); edges[0], edges[-1] = -np.inf, np.inf
        dec_b = np.clip(np.searchsorted(edges, fb, side='right') - 1, 0, 9)
        w = np.exp(fb - lse(fb)); expected = np.array([w[dec_b == k].sum() for k in range(10)])
        dec_e = np.clip(np.searchsorted(edges, fe, side='right') - 1, 0, 9)
        obs = np.zeros(10)
        for r in range(nrep):
            v = V[r]; 
            for k in range(10): obs[k] += np.mean(dec_e[r][v] == k)
        for k in range(10):
            rows.append(dict(protocolo=proto, modelo=mname, decil=k + 1, reportes_observados=round(obs[k], 1), reportes_esperados=round(nrep * expected[k], 1),
                             participacion_observada=round(obs[k] / nrep, 3), participacion_esperada=round(expected[k], 3), azar=0.1))
a7 = pd.DataFrame(rows); a7.to_csv(f'{OUT}/A7_calibracion_deciles.csv', index=False, encoding='utf-8-sig')
print('\n=== A7 calibración por deciles (decil 10 = 10 % más alto del territorio)')
for (proto, m), g in a7.groupby(['protocolo', 'modelo']):
    print(f'{proto:9s} {m:20s} decil 10: observado {g.participacion_observada.iloc[-1]:.3f} esperado {g.participacion_esperada.iloc[-1]:.3f} | deciles 9-10: obs {g.participacion_observada.iloc[-2:].sum():.3f} esp {g.participacion_esperada.iloc[-2:].sum():.3f} | deciles 1-5: obs {g.participacion_observada.iloc[:5].sum():.3f} esp {g.participacion_esperada.iloc[:5].sum():.3f}')
