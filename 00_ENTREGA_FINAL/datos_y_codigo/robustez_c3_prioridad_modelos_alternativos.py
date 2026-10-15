"""C3: ¿cambia la priorización parroquial si el score territorial viene de un modelo alternativo?
Entrena con los reportes de entrenamiento (como la aplicación del repo), puntúa los 2 993 619 píxeles construidos,
toma el decil superior (q90 sobre todo el construido) y repite H e I = H x NBI por escenario de lluvia."""
import numpy as np, pandas as pd, json, glob, warnings
warnings.filterwarnings('ignore')
from scipy.optimize import minimize
from scipy.special import logsumexp as lse
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
ROOT = '/Users/daniela/Desktop/PAPER INUNDACION/'; REPO = ROOT + '11_REPO_MODELO/quito-enso-exposicion-reproducible/'
d = np.load(REPO + 'DATOS_temporal__vias_fabdem.npz'); Xe, V, Xb, tr = d['Xe'], d['valid_e'], d['Xb'], d['etrain']
parts = sorted(glob.glob(REPO + 'PIXELES_*.npz')); X = np.vstack([np.load(p)['X'] for p in parts]); pid = np.concatenate([np.load(p)['pid'] for p in parts]); wid = np.concatenate([np.load(p)['wid'] for p in parts])
G = json.load(open(REPO + 'GRILLA.json')); units = G['weather_units']; print('píxeles', len(X), 'parroquias', pid.max(), 'celdas', wid.max(), len(units))
Xtr, Vtr = Xe[tr], V[tr]
def nll(b, lam=0.1):
    fe = np.where(Vtr, Xtr @ b, -np.inf)
    return -((lse(fe, axis=1) - np.log(Vtr.sum(1))).mean() - (lse(Xb @ b) - np.log(len(Xb)))) + 0.5 * lam * np.sum(b ** 2)
b = minimize(nll, np.zeros(25), method='L-BFGS-B', options=dict(maxiter=1500, ftol=1e-12)).x * 1.25
Xp = Xtr[Vtr]; XX = np.vstack([Xp, Xb]); y = np.r_[np.ones(len(Xp)), np.zeros(len(Xb))]; w = np.r_[np.full(len(Xp), .5 / len(Xp)), np.full(len(Xb), .5 / len(Xb))] * len(XX)
def logit(m):
    m.fit(XX, y, sample_weight=w); p = m.predict_proba(X)[:, 1]; return np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
S = {'Ancla (recalculada)': X @ b, 'Logística': logit(LogisticRegression(C=0.01, max_iter=2000)),
     'Boosting (prof. 2)': logit(HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=100, l2_regularization=1.0, random_state=0)),
     'Bosque aleatorio': logit(RandomForestClassifier(n_estimators=150, max_depth=8, min_samples_leaf=100, n_jobs=-1, random_state=0))}
z = lambda s: (s - s.mean()) / s.std()
S['Ensamble (ancla + boosting + bosque)'] = (z(S['Ancla (recalculada)']) + z(S['Boosting (prof. 2)']) + z(S['Bosque aleatorio'])) / 3
wea = pd.read_csv(REPO + 'DATOS_LLUVIA_ESCENARIOS.csv'); soc = pd.read_csv(REPO + 'DATOS_PARROQUIAS.csv', dtype={'parroquia': str})
nbi = pd.read_csv(ROOT + '02_DATOS_NBI/nbi_hogar_65_parroquias_microdatos.csv', dtype={'parroquia': str}).set_index('parroquia').pct_hogares_nbi_micro
n = soc.parroquia.map(nbi).values / 100
rep = pd.read_csv(REPO + 'resultados/prioridad_integrada.csv', dtype={'parroquia': str})
top = lambda v, k=13: set(np.argsort(-v, kind='stable')[:k])
rows, H = [], {}
for name, s in S.items():
    use = s >= np.quantile(s, 0.9)
    A = np.zeros((66, len(units) + 1)); np.add.at(A, (pid[use].astype(int), wid[use].astype(int)), 0.01)
    for wm in dict.fromkeys(wea.modelo):
        idx = dict(zip(wea[wea.modelo == wm].unit, wea[wea.modelo == wm].p_humedo)); P = np.array([idx[u] for u in units])
        # wid indexa las celdas desde 0
        a = np.zeros((65, len(units)));  np.add.at(a, (pid[use].astype(int) - 1, wid[use].astype(int)), 0.01)
        h = a @ P; H[(name, wm)] = h; I = h * n
        r = rep[(rep.modelo_territorial == 'red_residual') & (rep.modelo_lluvia == wm)].set_index('parroquia').loc[soc.parroquia]
        rows.append(dict(modelo=name, escenario_lluvia=wm, top13_indice_coinciden_con_red_repo=len(top(I) & top(r.indice_NBI_ha_ponderadas.values)),
                         spearman_H_vs_red_repo=round(spearmanr(h, r.area_prioritaria_ponderada_humedad_ha)[0], 3),
                         spearman_indice_vs_red_repo=round(spearmanr(I, r.indice_NBI_ha_ponderadas)[0], 3)))
tops = []
for (name, wm), h in H.items():
    I = h * n
    for k, j in enumerate(np.argsort(-I, kind='stable')[:13]): tops.append(dict(modelo=name, escenario_lluvia=wm, puesto=k + 1, parroquia=soc.parroquia[j], nombre=soc.nombre[j]))
pd.DataFrame(tops).to_csv('C3_top13_por_modelo_y_lluvia.csv', index=False, encoding='utf-8-sig')
o = pd.DataFrame(rows); o.to_csv('C3_prioridad_modelos_alternativos.csv', index=False, encoding='utf-8-sig'); print(o.to_string(index=False))
