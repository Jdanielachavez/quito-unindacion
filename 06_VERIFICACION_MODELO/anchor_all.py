import os
import sys, json, csv, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.environ.get("QUITO_REPO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")))
from anchor_fit import load, fit, calib, P, pens
from modelo import evaluar
from scipy.special import logsumexp
pen = pens['lam/2*||b||^2']
R = os.environ.get("QUITO_REPO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + "/"
ref = {(r['protocolo'], r['variante'], r['modelo']): r for r in csv.DictReader(open(R + 'REFERENCIA_comparacion_modelos.csv'))}
LAM = (0.001, 0.01, 0.1, 1.0); ALP = (0.25, 0.5, 0.75, 1.0, 1.25)
out = {}
print(f"{'combinación':26s} {'sel.(λ,α) propia':>17s} {'publicada':>11s} {'max|Δanclaje|':>14s} | {'log-dens test':>13s} {'ref':>7s} | {'captura':>8s} {'ref':>6s}")
for key, st in P.items():
    d = load(key); proto, var = st['protocol'], st['variant']
    best = None
    betas = {lam: fit(d, lam, pen) for lam in LAM}
    for lam in LAM:
        for a in ALP:
            s = calib(d, a * betas[lam])
            if best is None or s > best[0]: best = (s, lam, a)
    s, lam, a = best; anchor_new = a * betas[lam]; anchor_pub = np.array(st['anchor'])
    e, b = d['etest'], d['btest']; valid = d['valid_e'][e]; Xb = d['Xb'][b]
    fe = d['Xe'][e] @ anchor_new; fb = Xb @ anchor_new
    ev, cap = evaluar(fe, fb, valid)
    r = ref[(proto, var, 'ancla_acotada')]
    out[key] = dict(lam=lam, alpha=a, pub_lam=st['lambda_clipped'], pub_alpha=st['alpha_clipped'], maxdiff=float(np.abs(anchor_new - anchor_pub).max()),
                    ld=float(ev.mean()), ld_ref=float(r['log_densidad_relativa']), cap=float(cap.mean()), cap_ref=float(r['captura_top10pct_soporte']), calib=s)
    o = out[key]
    print(f"{key:26s} {f'({lam},{a})':>17s} {f'({o['pub_lam']},{o['pub_alpha']})':>11s} {o['maxdiff']:14.5f} | {o['ld']:13.5f} {o['ld_ref']:7.4f} | {o['cap']:8.4f} {o['cap_ref']:6.4f}")
json.dump(out, open(os.path.dirname(os.path.abspath(__file__)) + "/anchor_refit.json", 'w'), indent=1)
print('\nselección propia == publicada en', sum(1 for o in out.values() if (o['lam'], o['alpha']) == (o['pub_lam'], o['pub_alpha'])), 'de', len(out))
print('max |Δ log-densidad test| vs referencia: %.2e | max |Δ captura|: %.2e' % (max(abs(o['ld'] - o['ld_ref']) for o in out.values()), max(abs(o['cap'] - o['cap_ref']) for o in out.values())))
