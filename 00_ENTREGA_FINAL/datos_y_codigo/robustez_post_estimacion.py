"""Pruebas posestimación del modelo territorial (ancla loglineal de la variante temporal con vías y FABDEM).
 a) colinealidad (VIF, número de condición); b) estabilidad de los coeficientes (bootstrap por bloques) y de su signo;
 c) influencia de bloques (jackknife); d) sensibilidad a la incertidumbre de localización (posición central frente a las 25);
 e) sensibilidad a la penalización y al temperado; f) estabilidad por año con eventos del COE; g) dependencia espacial (ICC por bloques).
Uso: python robustez_post_estimacion.py [salida] [réplicas]"""
import os, sys, json, glob, time
import numpy as np, pandas as pd
REPO = os.environ.get('QUITO_REPO', os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + '/'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'; NREP = int(sys.argv[2]) if len(sys.argv) > 2 else 300
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'robustez_a4_a6_a7.py'), encoding='utf-8').read().split('# ---------------- A4')[0]
exec(src.replace("OUT = sys.argv[1] if len(sys.argv) > 1 else '.'", ""))
key = 'temporal__vias_fabdem'; st = P[key]; names = st['names']; LAMP, ALPP = st['lambda_clipped'], st['alpha_clipped']
d = load(key); anchor = np.array(st['anchor']); t0 = time.time()
tr = d['etrain']; Xe, V, blk = d['Xe'][tr], d['valid_e'][tr], d['block'][tr]; Xb = d['Xb'][d['btrain']]
const = [i for i in range(len(names)) if Xb[:, i].std() < 1e-9]
act = [i for i in range(len(names)) if i not in const]
print('covariables constantes (sin efecto):', [names[i] for i in const])
# ---- (a) colinealidad
def vif(X):
    ok = X.std(0) > 1e-9; out = np.full(X.shape[1], np.nan); c = np.corrcoef(X[:, ok].T)
    out[ok] = np.diag(np.linalg.inv(c)); return out, float(np.linalg.cond(c))
# las clases de cobertura suman 1 (colinealidad perfecta por construcción): VIF con la clase más frecuente como referencia
lc = [i for i in act if names[i].startswith('cobertura_')]; ref_lc = max(lc, key=lambda i: st['mu'][i]); act_v = [i for i in act if i != ref_lc]
rank_full = int(np.linalg.matrix_rank(np.corrcoef(Xb[:, act].T))); print('rango de la matriz de correlaciones con todas las clases: %d de %d (clase de referencia para el VIF: %s)' % (rank_full, len(act), names[ref_lc]))
v_b, cond_b = vif(Xb[:, act_v])
Xrep = d['Xe'][d['etrain'] | d['ecal'] | d['etest']]; Vrep = d['valid_e'][d['etrain'] | d['ecal'] | d['etest']]
v_r, cond_r = vif(Xrep[Vrep][:, act_v])
print('número de condición de las correlaciones sin la clase de referencia: fondo %.1f | reportes %.1f' % (cond_b, cond_r))
# ---- (b) bootstrap de coeficientes
b_hat = fit(Xe, V, Xb, LAMP) * ALPP
print('ancla reajustada vs publicada, diferencia máxima: %.5f' % np.abs(b_hat - anchor).max())
ub = np.unique(blk); rng = np.random.default_rng(11109)
prev = f'{OUT}/A8_coeficientes_vif.csv'
if os.environ.get('REUSE') == '1' and os.path.exists(prev):
    tab = pd.read_csv(prev); lo, hi = tab.ic95_inf.values, tab.ic95_sup.values; se_vec = (hi - lo) / 3.92; print('bootstrap reutilizado de', prev)
else:
    draws = np.zeros((NREP, len(names)))
    for r in range(NREP):
        pick = rng.choice(ub, len(ub)); ids = np.concatenate([np.where(blk == k)[0] for k in pick])
        draws[r] = fit(Xe[ids], V[ids], Xb, LAMP) * ALPP
        if (r + 1) % 100 == 0: print('bootstrap', r + 1, '/', NREP, f'{time.time() - t0:.0f}s', flush=True)
    lo, hi = np.quantile(draws, [0.025, 0.975], axis=0); sgn = np.maximum((draws > 0).mean(0), (draws < 0).mean(0)); se_vec = draws.std(0)
    tab = pd.DataFrame({'variable': names, 'coeficiente_publicado': anchor, 'coef_reajustado': b_hat, 'ic95_inf': lo, 'ic95_sup': hi, 'estabilidad_signo': sgn,
                        'ic_excluye_cero': (lo > 0) | (hi < 0)})
    vif_b = pd.Series(np.nan, index=names); vif_b.iloc[act_v] = v_b; vif_r = pd.Series(np.nan, index=names); vif_r.iloc[act_v] = v_r
    tab['vif_fondo'] = vif_b.values; tab['vif_reportes'] = vif_r.values; tab['constante'] = [i in const for i in range(len(names))]; tab['clase_referencia_vif'] = [i == ref_lc for i in range(len(names))]
    tab.round(4).to_csv(prev, index=False, encoding='utf-8-sig')
print('\n(a,b) coeficientes con IC que excluye 0:', int(tab.ic_excluye_cero[~tab.constante].sum()), 'de', len(act), '| VIF > 10:', int((tab.vif_fondo > 10).sum()), '| VIF > 5:', int((tab.vif_fondo > 5).sum()))
print(tab[~tab.constante].sort_values('vif_fondo', ascending=False).head(8)[['variable', 'coeficiente_publicado', 'ic95_inf', 'ic95_sup', 'estabilidad_signo', 'vif_fondo']].round(3).to_string(index=False))
# ---- (c) jackknife por bloque (coeficientes y desempeño fuera de muestra)
e_te, b_te = d['etest'], d['btest']
def test_ld(b): 
    ev, cap = evaluar(d['Xe'][e_te] @ b, d['Xb'][b_te] @ b, d['valid_e'][e_te]); return float(ev.mean()), float(cap.mean())
ld0, cap0 = test_ld(b_hat); se = se_vec.copy(); se[const] = np.nan; se[se < 1e-6] = np.nan; rows = []
for k in ub:
    keep = blk != k; b = fit(Xe[keep], V[keep], Xb, LAMP) * ALPP; z = (b - b_hat) / se; ld, cap = test_ld(b)
    j = int(np.nanargmax(np.abs(z))); rows.append(dict(bloque=int(k), reportes=int((~keep).sum()), max_dif_estandarizada=float(np.abs(z[j])), variable=names[j], dif_logdens_test=ld - ld0, dif_captura_test=cap - cap0))
inf = pd.DataFrame(rows).sort_values('max_dif_estandarizada', ascending=False); inf.round(4).to_csv(f'{OUT}/A8_influencia_bloques.csv', index=False, encoding='utf-8-sig')
print('\n(c) jackknife: %d bloques de entrenamiento | máx. diferencia estandarizada %.2f (bloque %d, %s) | rango Δ log densidad de prueba [%.3f, %.3f]' % (len(inf), inf.max_dif_estandarizada.max(), inf.iloc[0].bloque, inf.iloc[0].variable, inf.dif_logdens_test.min(), inf.dif_logdens_test.max()))
# ---- (d) incertidumbre de localización: posición más central en el espacio de covariables frente a las 25
Xall = d['Xe']; Vall = d['valid_e']
cent = np.array([np.nanmean([np.linalg.norm(Xall[i, j] - np.nanmean(Xall[i][Vall[i]], 0)) for i in range(len(Xall)) if Vall[i, j]]) for j in range(Xall.shape[1])])
jc = int(np.argmin(cent)); print('\n(d) posición más central (medoide):', jc, '| distancias medias por posición (mín/máx): %.3f / %.3f' % (cent.min(), cent.max()))
def fit_pos(cols_pos):
    m = np.zeros_like(V); m[:, cols_pos] = V[:, cols_pos]; ok = m.any(1)
    b = fit(Xe[ok], m[ok], Xb, LAMP) * ALPP
    mt = np.zeros_like(d['valid_e'][e_te]); mt[:, cols_pos] = d['valid_e'][e_te][:, cols_pos]; okt = mt.any(1)
    ev, cap = evaluar(d['Xe'][e_te][okt] @ b, d['Xb'][b_te] @ b, mt[okt]); ev_f, cap_f = evaluar(d['Xe'][e_te] @ b, d['Xb'][b_te] @ b, d['valid_e'][e_te])
    return dict(reportes_entrenamiento=int(ok.sum()), reportes_prueba=int(okt.sum()), logdens_prueba_mismas_posiciones=float(ev.mean()), captura_mismas_posiciones=float(cap.mean()),
                logdens_prueba_25_posiciones=float(ev_f.mean()), captura_25_posiciones=float(cap_f.mean()), max_dif_coef_vs_25=float(np.abs(b - b_hat).max()))
loc = pd.DataFrame([dict(posiciones='25 (publicado)', **fit_pos(list(range(25)))), dict(posiciones=f'solo la central ({jc})', **fit_pos([jc])),
                    dict(posiciones='9 más centrales', **fit_pos([int(i) for i in np.argsort(cent)[:9]]))])
loc.round(4).to_csv(f'{OUT}/A8_incertidumbre_localizacion.csv', index=False, encoding='utf-8-sig'); print(loc.round(3).to_string(index=False))
# ---- (e) hiperparámetros del ancla (temporal y espacial)
rows = []
for proto in ('temporal', 'espacial'):
    dd = load(f'{proto}__vias_fabdem'); X1, V1, B1 = dd['Xe'][dd['etrain']], dd['valid_e'][dd['etrain']], dd['Xb'][dd['btrain']]
    for lam in LAM:
        bb = fit(X1, V1, B1, lam)
        for a in ALP:
            e = dd['etest']; ev, cap = evaluar(dd['Xe'][e] @ (a * bb), dd['Xb'][dd['btest']] @ (a * bb), dd['valid_e'][e])
            rows.append(dict(protocolo=proto, penalizacion=lam, temperado=a, calibracion=cal(dd, list(range(25)), a * bb), logdens_prueba=float(ev.mean()), captura_prueba=float(cap.mean()),
                             publicado=(lam, a) == ((0.1, 1.25) if proto == 'temporal' else (0.1, 1.0))))
hp = pd.DataFrame(rows); hp.round(4).to_csv(f'{OUT}/A8_sensibilidad_hiperparametros.csv', index=False, encoding='utf-8-sig')
for proto, g in hp.groupby('protocolo'):
    print(f'\n(e) {proto}: log densidad de prueba entre {g.logdens_prueba.min():.3f} y {g.logdens_prueba.max():.3f} (publicado {g[g.publicado].logdens_prueba.iloc[0]:.3f}); '
          f'rango de la calibración {g.calibracion.min():.3f}–{g.calibracion.max():.3f}; el mejor de prueba es {g.loc[g.logdens_prueba.idxmax(), ["penalizacion", "temperado"]].tolist()}')
# ---- (f) y (g): eventos del COE por año y dependencia por bloques
from scipy.spatial import cKDTree
G = json.load(open(REPO + 'GRILLA.json')); trn = G['transform']; Wd = G['width']
fl, Xs = [], []
for p in sorted(glob.glob(REPO + 'PIXELES_*.npz')):
    z = np.load(p, allow_pickle=False); fl.append(z['flat']); Xs.append(z['X'])
flat = np.concatenate(fl); Xpx = np.vstack(Xs); score = Xpx @ anchor
tree = cKDTree(np.column_stack([trn[2] + (flat % Wd + 0.5) * trn[0], trn[5] + (flat // Wd + 0.5) * trn[4]])); thr = np.quantile(score, 0.90)
ev = pd.read_csv(f'{OUT}/coe_eventos.csv') if os.path.exists(f'{OUT}/coe_eventos.csv') else pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coe_eventos.csv'))
ev = ev[ev.tipo_de_ev.astype(str).str.contains('Inundaci', na=False) & (ev.anio >= 2010)].copy()
dist, j = tree.query(np.column_stack([ev.x.values, ev.y.values]), distance_upper_bound=50); ok = np.isfinite(dist)
ev = ev[ok].copy(); ev['top'] = (score[j[ok]] >= thr).astype(int)
def wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den; return c - h, c + h
rows = []
for y, g in ev.groupby('anio'):
    lo_, hi_ = wilson(g.top.sum(), len(g)); rows.append(dict(anio=int(y), eventos=len(g), en_decil_superior=int(g.top.sum()), captura=g.top.mean(), ic95_inf=lo_, ic95_sup=hi_))
py = pd.DataFrame(rows); py.round(4).to_csv(f'{OUT}/A8_coe_por_anio.csv', index=False, encoding='utf-8-sig')
from scipy.stats import spearmanr
rho, pv = spearmanr(py.anio, py.captura)
print('\n(f) COE por año: %d años | captura entre %.3f y %.3f | Spearman año–captura %.2f (p = %.2f) | años con IC inferior > 0.10: %d' % (len(py), py.captura.min(), py.captura.max(), rho, pv, int((py.ic95_inf > 0.10).sum())))
ev['bloque'] = (np.floor(ev.x / 5000) * 1000 + np.floor(ev.y / 5000)).astype(int)
def icc(df):
    g = df.groupby('bloque').top; k = g.ngroups; n = len(df); nj = g.size().values; m = g.mean().values; grand = df.top.mean()
    msb = (nj * (m - grand) ** 2).sum() / (k - 1); msw = ((df.top - df.bloque.map(g.mean())) ** 2).sum() / (n - k); n0 = (n - (nj ** 2).sum() / n) / (k - 1)
    return max(0.0, (msb - msw) / (msb + (n0 - 1) * msw)), n / (1 + (nj.mean() - 1) * max(0.0, (msb - msw) / (msb + (n0 - 1) * msw))), k, n
rows = []
for lab, df in (('2022 a mayo 2024', ev[ev.anio >= 2022]), ('2010 a mayo 2024', ev)):
    r_, neff, k, n = icc(df); rows.append(dict(eventos=lab, n=n, bloques=k, icc=r_, n_efectivo=neff, efecto_diseno=n / neff))
dep = pd.DataFrame(rows); dep.round(4).to_csv(f'{OUT}/A8_dependencia_bloques.csv', index=False, encoding='utf-8-sig')
print('(g) dependencia por bloques de 5 km:'); print(dep.round(3).to_string(index=False)); print(f'tiempo total {time.time() - t0:.0f}s')
