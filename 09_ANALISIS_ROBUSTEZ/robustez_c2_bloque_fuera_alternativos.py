"""C2: validación dejando un bloque de 5 km fuera (331 reportes, 55 bloques) del ancla frente a modelos no lineales y un ensamble.
Hiperparámetros fijados de antemano (sin mirar este resultado). Comparación pareada por bloque con bootstrap de bloques."""
import sys, json, numpy as np, pandas as pd, warnings, time
warnings.filterwarnings('ignore')
from scipy.optimize import minimize
from scipy.special import logsumexp as lse
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
REPO = '/Users/daniela/Desktop/PAPER INUNDACION/11_REPO_MODELO/quito-enso-exposicion-reproducible/'
sys.path.insert(0, REPO); from modelo import evaluar
z = np.load(REPO + 'DATOS_temporal__vias_fabdem.npz'); d = {k: z[k] for k in z.files}
Xe, V, Xb, blk = d['Xe'], d['valid_e'], d['Xb'], d['block']
mu, sd = Xb.mean(0), Xb.std(0) + 1e-9
Ze, Zb = (Xe - mu) / sd, (Xb - mu) / sd
def nll(b, Xp, Vp, lam):
    fe = np.where(Vp, Xp @ b, -np.inf)
    return -((lse(fe, axis=1) - np.log(Vp.sum(1))).mean() - (lse(Zb @ b) - np.log(len(Zb)))) + 0.5 * lam * np.sum(b ** 2)
def anchor(tr):
    b = minimize(nll, np.zeros(Ze.shape[2]), args=(Ze[tr], V[tr], 0.1), method='L-BFGS-B', options=dict(maxiter=1500, ftol=1e-12)).x
    return lambda X: X @ (1.25 * b)
def clf(model):
    def fit(tr):
        Xp = Ze[tr][V[tr]]; X = np.vstack([Xp, Zb]); y = np.r_[np.ones(len(Xp)), np.zeros(len(Zb))]
        w = np.r_[np.full(len(Xp), .5 / len(Xp)), np.full(len(Zb), .5 / len(Zb))] * len(X)
        model.fit(X, y, sample_weight=w)
        return lambda Z: (lambda p: np.log(np.clip(p[:, 1], 1e-6, 1 - 1e-6) / np.clip(p[:, 0], 1e-6, 1)))(model.predict_proba(Z))
    return fit
MODS = {
 'Ancla loglineal (repo)': anchor,
 'Logística': clf(LogisticRegression(C=0.01, max_iter=2000)),
 'Boosting (prof. 2)': clf(HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=100, l2_regularization=1.0, random_state=0)),
 'Bosque aleatorio': clf(RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=100, n_jobs=-1, random_state=0)),
}
blocks = np.unique(blk); per = {k: {'ld': {}, 'cap': {}} for k in list(MODS) + ['Ensamble ancla + boosting + bosque']}
t0 = time.time()
for j, bk in enumerate(blocks):
    te = blk == bk; tr = ~te
    fs = {k: (f if k.startswith('Ancla') else f) for k, f in MODS.items()}
    fit = {k: (MODS[k](tr)) for k in MODS}
    def sc(f, X): return f(X)
    S_e, S_b = {}, {}
    for k, f in fit.items():
        se = np.full((te.sum(), Ze.shape[1]), -np.inf); se[V[te]] = f(Ze[te][V[te]]); S_e[k] = se; S_b[k] = f(Zb)
    def zs(k): m, s = S_b[k].mean(), S_b[k].std() + 1e-9; return (S_e[k] - m) / s, (S_b[k] - m) / s
    parts = [zs(k) for k in ('Ancla loglineal (repo)', 'Boosting (prof. 2)', 'Bosque aleatorio')]
    S_e['Ensamble ancla + boosting + bosque'] = np.mean([p[0] for p in parts], axis=0); S_b['Ensamble ancla + boosting + bosque'] = np.mean([p[1] for p in parts], axis=0)
    for k in per:
        ev, cap = evaluar(S_e[k], S_b[k], V[te]); per[k]['ld'][bk] = (float(ev.sum()), int(te.sum())); per[k]['cap'][bk] = (float(cap.sum()), int(te.sum()))
    if (j + 1) % 5 == 0: print(j + 1, '/', len(blocks), f'{time.time() - t0:.0f}s', flush=True)
n = np.array([per['Ancla loglineal (repo)']['ld'][b][1] for b in blocks])
M = {k: {m: np.array([per[k][m][b][0] for b in blocks]) for m in ('ld', 'cap')} for k in per}
rng = np.random.default_rng(11109); draw = rng.integers(0, len(blocks), (3000, len(blocks)))
def agg(a): return a.sum() / n.sum()
rows = []
ref = 'Ancla loglineal (repo)'
for k in per:
    r = dict(modelo=k, logdens=agg(M[k]['ld']), captura=agg(M[k]['cap']))
    for m, nm in (('ld', 'logdens'), ('cap', 'captura')):
        dif = M[k][m] - M[ref][m]; sim = dif[draw].sum(1) / n[draw].sum(1)
        r[f'{nm}_dif_vs_ancla'] = agg(dif); r[f'{nm}_dif_ic_inf'], r[f'{nm}_dif_ic_sup'] = np.quantile(sim, [.025, .975])
    r['bloques_mejor_que_ancla'] = int(((M[k]['ld'] / n) > (M[ref]['ld'] / n)).sum()); rows.append(r)
o = pd.DataFrame(rows).round(3); o.to_csv('C2_bloque_fuera_alternativos.csv', index=False, encoding='utf-8-sig'); print(o.to_string(index=False))
