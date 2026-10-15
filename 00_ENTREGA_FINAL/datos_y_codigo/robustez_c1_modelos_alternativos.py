"""C1: ¿mejora la discriminación con modelos no lineales? Mismo protocolo (particiones, fondo y métricas) que el ancla.
Presencia-fondo con clasificadores; hiperparámetros elegidos solo con calibración; prueba una sola vez."""
import os, sys, json, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
REPO = '/Users/daniela/Desktop/PAPER INUNDACION/11_REPO_MODELO/quito-enso-exposicion-reproducible/'
sys.path.insert(0, REPO); from modelo import evaluar
from scipy.special import logsumexp as lse
def load(key):
    z = np.load(REPO + f'DATOS_{key}.npz'); return {k: z[k] for k in z.files}
def score(d, f, split):
    e, b = d[f'e{split}'], d[f'b{split}']
    Xe = d['Xe'][e]; V = d['valid_e'][e]; n, k, p = Xe.shape
    se = np.full((n, k), -np.inf); se[V] = f(Xe[V])
    sb = f(d['Xb'][b])
    ev, cap = evaluar(se, sb, V); return float(ev.mean()), float(cap.mean())
def build(d, split, rng):
    e = d[f'e{split}']; V = d['valid_e'][e]; Xp = d['Xe'][e][V]
    Xb = d['Xb'][d[f'b{split}']]
    X = np.vstack([Xp, Xb]); y = np.r_[np.ones(len(Xp)), np.zeros(len(Xb))]
    w = np.r_[np.full(len(Xp), 1.0 / len(Xp)), np.full(len(Xb), 1.0 / len(Xb))] * len(X) / 2   # clases balanceadas
    return X, y, w
MODS = {
 'Logística (referencia lineal)': [dict(C=c) for c in (0.01, 0.1, 1.0)],
 'Boosting (profundidad 2)': [dict(max_depth=2, learning_rate=lr, max_iter=it, l2_regularization=1.0) for lr in (0.03, 0.1) for it in (50, 150)],
 'Boosting (profundidad 4)': [dict(max_depth=4, learning_rate=lr, max_iter=it, l2_regularization=1.0) for lr in (0.03, 0.1) for it in (50, 150)],
 'Bosque aleatorio': [dict(max_depth=d_, min_samples_leaf=ml, n_estimators=200) for d_ in (4, 8) for ml in (20, 100)],
}
def make(name, pr):
    if name.startswith('Log'): return LogisticRegression(max_iter=2000, **pr)
    if name.startswith('Boosting'): return HistGradientBoostingClassifier(random_state=0, **pr)
    return RandomForestClassifier(random_state=0, n_jobs=-1, **pr)
rows = []
for proto in ('temporal', 'espacial'):
    d = load(f'{proto}__vias_fabdem')
    mu, sd = d['Xb'][d['btrain']].mean(0), d['Xb'][d['btrain']].std(0) + 1e-9
    Z = lambda X: (X - mu) / sd
    Xtr, ytr, wtr = build(d, 'train', None)
    for name, grid in MODS.items():
        best = None
        for pr in grid:
            m = make(name, pr); m.fit(Z(Xtr), ytr, **({'sample_weight': wtr}))
            f = lambda X, m=m: np.log(np.clip(m.predict_proba(Z(X))[:, 1], 1e-6, 1 - 1e-6) / np.clip(m.predict_proba(Z(X))[:, 0], 1e-6, 1))
            cal_ld, cal_cap = score(d, f, 'cal')
            if best is None or cal_ld > best[0]: best = (cal_ld, pr, f)
        ld, cap = score(d, best[2], 'test')
        rows.append(dict(protocolo=proto, modelo=name, hiperparametros=json.dumps(best[1]), calibracion_logdens=round(best[0], 3), prueba_logdens=round(ld, 3), prueba_captura=round(cap, 3)))
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('C1_modelos_alternativos.csv', index=False, encoding='utf-8-sig')
