import os
import json, numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
R = os.environ.get("QUITO_REPO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + "/"
P = json.load(open(R + 'PARAMETROS.json'))
def load(key):
    z = np.load(R + f'DATOS_{key}.npz', allow_pickle=False); return {k: z[k] for k in z.files}
def objective(beta, Xe, V, Xb, lam, pen):
    # log-verosimilitud de proceso puntual condicional: media_reportes[log media_pos exp(x.b)] - log media_fondo exp(x.b) - penalización
    fe = Xe @ beta                                   # (n,25)
    fe = np.where(V, fe, -np.inf)
    ev = logsumexp(fe, axis=1) - np.log(V.sum(1))
    fb = Xb @ beta
    nb = logsumexp(fb) - np.log(len(fb))
    return -(ev.mean() - nb) + pen(beta, lam)
def fit(d, lam, pen):
    Xe, V, Xb = d['Xe'][d['etrain']], d['valid_e'][d['etrain']], d['Xb'][d['btrain']]
    p = Xe.shape[2]
    r = minimize(objective, np.zeros(p), args=(Xe, V, Xb, lam, pen), method='L-BFGS-B', options=dict(maxiter=2000, ftol=1e-14, gtol=1e-9))
    return r.x
def calib(d, beta):
    Xe, V, Xb = d['Xe'][d['ecal']], d['valid_e'][d['ecal']], d['Xb'][d['bcal']]
    fe = np.where(V, Xe @ beta, -np.inf); ev = logsumexp(fe, axis=1) - np.log(V.sum(1))
    return float(ev.mean() - (logsumexp(Xb @ beta) - np.log(len(Xb))))
pens = {'lam*||b||^2': lambda b, l: l * np.sum(b**2), 'lam/2*||b||^2': lambda b, l: 0.5 * l * np.sum(b**2), 'lam*||b||^2 /p': lambda b, l: l * np.mean(b**2)}
if __name__ == '__main__':
    key = 'temporal__vias_fabdem'; d = load(key); st = P[key]
    anchor = np.array(st['anchor']); print(key, '| lambda_clipped', st['lambda_clipped'], '| alpha_clipped', st['alpha_clipped'])
    for pn, pf in pens.items():
        for lam in (0.001, 0.01, 0.1, 1.0):
            b = fit(d, lam, pf)
            # mejor escala alpha tal que alpha*b ~ anchor (mínimos cuadrados) y su error
            a = float(b @ anchor / (b @ b)); err = float(np.abs(a*b - anchor).max())
            print(f'{pn:18s} lam={lam:<6} escala_ls={a:6.3f} max|a*b-anchor|={err:.4f} corr={np.corrcoef(b, anchor)[0,1]:.5f} calib={calib(d, b):.5f}')
