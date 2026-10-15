"""A5 sesgo de reporte: ¿qué pasa sin las variables de exposición (construido, vías)?
(1) modelo solo físico: métricas de test y prioridad sobre los 2.99 M de píxeles;
(2) evaluación dentro de estratos de densidad construida (fondo restringido al mismo estrato).
Uso: QUITO_REPO=/ruta/al/repo NBI_CSV=...csv python robustez_a5_sesgo_reporte.py [salida]
"""
import os, sys, json, glob
import numpy as np, pandas as pd
REPO = os.environ.get('QUITO_REPO', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + '/'; OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robustez_a4_a6_a7.py'), encoding='utf-8').read().split('# ---------------- A4')[0]
src = src.replace("OUT = sys.argv[1] if len(sys.argv) > 1 else '.'", "")
exec(src)                                    # load, fit_select, test_metrics, evaluar, P, ...
names = P['temporal__vias_fabdem']['names']; ix = {n: i for i, n in enumerate(names)}
EXPO = ['construido_100m', 'construido_500m', 'cobertura_50', 'log_distancia_vial', 'log_construido_contribuyente_ha', 'fraccion_construida_contribuyente']
CONST = ['cobertura_70', 'cobertura_95', 'cobertura_100']
FIS = [n for n in names if n not in EXPO + CONST]
specs = {'Completo (25)': names, 'Solo físico (sin exposición)': FIS, 'Solo exposición': EXPO}
# ---------- (1a) métricas de test ----------
rows = []; betas = {}
for lab, vs in specs.items():
    cols = [ix[v] for v in vs]; r = {'modelo': lab, 'n_variables': len(cols)}
    for proto in ('temporal', 'espacial'):
        d = load(f'{proto}__vias_fabdem'); b, lam, a = fit_select(d, cols); ld, cap = test_metrics(d, cols, b)
        r[f'{proto}_logdens'] = round(ld, 3); r[f'{proto}_captura'] = round(cap, 3)
        if proto == 'temporal': betas[lab] = (cols, b)
    rows.append(r)
a5a = pd.DataFrame(rows); a5a.to_csv(f'{OUT}/A5_fisico_vs_completo.csv', index=False, encoding='utf-8-sig'); print(a5a.to_string(index=False))
# ---------- (1b) prioridad con cada modelo (aplicación temporal, como el mapa) ----------
parts = sorted(glob.glob(REPO + 'PIXELES_*.npz')); Xs, pid, wid = [], [], []
for p in parts:
    z = np.load(p, allow_pickle=False); Xs.append(z['X']); pid.append(z['pid'].astype(int)); wid.append(z['wid'].astype(int))
X = np.vstack(Xs); pid = np.concatenate(pid); wid = np.concatenate(wid)
G = json.load(open(REPO + 'GRILLA.json')); units = G['weather_units']; nc = len(units)
wea = pd.read_csv(REPO + 'DATOS_LLUVIA_ESCENARIOS.csv'); soc = pd.read_csv(REPO + 'DATOS_PARROQUIAS.csv', dtype={'parroquia': str})
nbi = pd.read_csv(os.environ.get('NBI_CSV', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "02_DATOS_NBI", "nbi_hogar_65_parroquias_microdatos.csv")), dtype={'parroquia': str}).set_index('parroquia').pct_hogares_nbi_micro
n = soc.parroquia.map(nbi).values / 100
ref = np.load(REPO + 'REFERENCIA_intersecciones.npz')
def counts_q90(score):
    thr = np.quantile(score.astype(np.float64), 0.90); use = score >= thr
    return np.bincount(pid[use] * nc + wid[use], minlength=66 * nc).reshape(66, nc)
anchor_full = np.array(P['temporal__vias_fabdem']['anchor'])
c_full = counts_q90(X @ anchor_full)
print('\nvalidación: conteos del ancla completa == referencia del repo:', bool((c_full == ref['ancla_acotada_q90']).all()))
cols_f, b_f = betas['Solo físico (sin exposición)']
c_fis = counts_q90(X[:, cols_f] @ b_f)
top = lambda v, k=13: set(np.argsort(-v, kind='stable')[:k])
rows = []
for wm in dict.fromkeys(wea.modelo):
    idx = dict(zip(wea[wea.modelo == wm].unit, wea[wea.modelo == wm].p_humedo)); prob = np.array([idx[u] for u in units])
    Af, Ap = c_full[1:] @ prob * 0.01, c_fis[1:] @ prob * 0.01
    rows.append(dict(escenario_lluvia=wm, top13_area_coinciden=len(top(Af) & top(Ap)), top13_indice_coinciden=len(top(Af * n) & top(Ap * n)),
                     cambian_por_nbi_completo=len(top(Af * n) - top(Af)), cambian_por_nbi_fisico=len(top(Ap * n) - top(Ap)),
                     entran_fisico_vs_completo=', '.join(sorted(soc.nombre[i] for i in top(Ap * n) - top(Af * n))),
                     salen=', '.join(sorted(soc.nombre[i] for i in top(Af * n) - top(Ap * n)))))
a5b = pd.DataFrame(rows); a5b.to_csv(f'{OUT}/A5_prioridad_fisica_vs_completa.csv', index=False, encoding='utf-8-sig')
print('\n(1b) prioridad: modelo solo físico frente a completo'); print(a5b.to_string(index=False))
# parroquias estables con el modelo físico en las 3 lluvias
cnt = np.zeros(65, int)
for wm in dict.fromkeys(wea.modelo):
    idx = dict(zip(wea[wea.modelo == wm].unit, wea[wea.modelo == wm].p_humedo)); prob = np.array([idx[u] for u in units])
    for i in top((c_fis[1:] @ prob * 0.01) * n): cnt[i] += 1
print('estables (3/3) con modelo físico:', sorted(soc.nombre[i] for i in range(65) if cnt[i] == 3))
# ---------- (2) estratos de densidad construida ----------
rows = []; cb = ix['construido_500m']
for proto in ('temporal', 'espacial'):
    d = load(f'{proto}__vias_fabdem'); e, bm = d['etest'], d['btest']
    Xe, Xb, V = d['Xe'][e], d['Xb'][bm], d['valid_e'][e]
    be = np.array([Xe[i][V[i], cb].mean() for i in range(len(Xe))])
    # el territorio es mayormente no construido: estratos = sin construido / construido bajo / construido alto (mediana de lo construido)
    mn = Xb[:, cb].min() + 1e-6; med = np.median(Xb[Xb[:, cb] > mn, cb])
    strat = lambda x: (x > mn).astype(int) + (x > med).astype(int)
    se, sb = strat(be), strat(Xb[:, cb])
    for lab, vs in specs.items():
        cols = [ix[v] for v in vs]; dd = load(f'{proto}__vias_fabdem'); b, _, _ = fit_select(dd, cols)
        fe, fb = Xe[:, :, cols] @ b, Xb[:, cols] @ b
        for s, nm in enumerate(('sin construido cercano', 'construido bajo', 'construido alto')):
            m_e, m_b = se == s, sb == s
            if m_e.sum() < 5 or m_b.sum() < 50: continue
            ev, cap = evaluar(fe[m_e], fb[m_b], V[m_e])
            rows.append(dict(protocolo=proto, modelo=lab, estrato=nm, reportes=int(m_e.sum()), logdens_dentro_estrato=round(float(ev.mean()), 3), captura_dentro_estrato=round(float(cap.mean()), 3)))
a5c = pd.DataFrame(rows); a5c.to_csv(f'{OUT}/A5_estratos_exposicion.csv', index=False, encoding='utf-8-sig')
print('\n(2) discriminación dentro de estratos de densidad construida (azar = 0.000 / 0.100)')
print(a5c.pivot_table(index=['protocolo', 'estrato'], columns='modelo', values='logdens_dentro_estrato').round(3).to_string())
print(a5c.groupby(['protocolo', 'estrato']).reportes.first().to_string())
