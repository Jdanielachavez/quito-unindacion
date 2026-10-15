import os
import sys, json, csv, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.environ.get("QUITO_REPO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")))
from anchor_fit import load, fit, calib, P, pens
from modelo import evaluar, ensamble, logsumexp
from scipy.special import logsumexp as lse
R = os.environ.get("QUITO_REPO", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "11_REPO_MODELO", "quito-enso-exposicion-reproducible")) + "/"
pen = pens['lam/2*||b||^2']
LAM = (0.001, 0.01, 0.1, 1.0); ALP = (0.25, 0.5, 0.75, 1.0, 1.25)
silu = lambda x: x / (1 + np.exp(-x))
def dsilu(x):
    s = 1 / (1 + np.exp(-x)); return s * (1 + x * (1 - s))
class Net:
    def __init__(s, p, rng):
        dims = [(p, 16), (16, 8), (8, 1)]; s.W, s.b = [], []
        for i, (a, o) in enumerate(dims):
            k = 1 / np.sqrt(a)
            if i < 2: s.W.append(rng.uniform(-k, k, (a, o))); s.b.append(rng.uniform(-k, k, o))
            else: s.W.append(np.zeros((a, o))); s.b.append(np.zeros(o))
    def fwd(s, X, rng=None, drop=0.10):
        h0 = X; z1 = h0 @ s.W[0] + s.b[0]; a1 = silu(z1); m1 = None
        if rng is not None: m1 = (rng.random(a1.shape) >= drop) / (1 - drop); a1 = a1 * m1
        z2 = a1 @ s.W[1] + s.b[1]; a2 = silu(z2); m2 = None
        if rng is not None: m2 = (rng.random(a2.shape) >= drop) / (1 - drop); a2 = a2 * m2
        g = (a2 @ s.W[2] + s.b[2]).reshape(-1)
        return g, (h0, z1, a1, m1, z2, a2, m2)
    def bwd(s, c, dg):
        h0, z1, a1, m1, z2, a2, m2 = c; dg = dg.reshape(-1, 1)
        gW2 = a2.T @ dg; gb2 = dg.sum(0); da2 = dg @ s.W[2].T
        if m2 is not None: da2 = da2 * m2
        dz2 = da2 * dsilu(z2); gW1 = a1.T @ dz2; gb1 = dz2.sum(0); da1 = dz2 @ s.W[1].T
        if m1 is not None: da1 = da1 * m1
        dz1 = da1 * dsilu(z1); gW0 = h0.T @ dz1; gb0 = dz1.sum(0)
        return [gW0, gW1, gW2], [gb0, gb1, gb2]
def train(d, anchor, B, seed, epochs=300):
    rng = np.random.default_rng(seed); p = d['Xb'].shape[1]; net = Net(p, rng)
    et, vt = d['Xe'][d['etrain']], d['valid_e'][d['etrain']]; bt = d['Xb'][d['btrain']]
    ec, vc, bc = d['Xe'][d['ecal']], d['valid_e'][d['ecal']], d['Xb'][d['bcal']]
    K, J = et.shape[0], et.shape[1]; Xe_flat = et.reshape(-1, p)
    params = net.W + net.b; mom = [np.zeros_like(x) for x in params]; var = [np.zeros_like(x) for x in params]; t = 0
    best, best_state, best_ep = -np.inf, None, None
    for ep in range(epochs + 1):
        idx = rng.choice(len(bt), min(16384, len(bt)), replace=False); Xb = bt[idx]
        ge, ce = net.fwd(Xe_flat, rng); gb, cb = net.fwd(Xb, rng)
        te, tb = np.tanh(ge), np.tanh(gb)
        fe = (Xe_flat @ anchor + B * te).reshape(K, J); fe = np.where(vt, fe, -np.inf)
        fb = Xb @ anchor + B * tb
        ev = lse(fe, axis=1) - np.log(vt.sum(1)); nb = len(fb)
        r = B * tb
        loss = lse(fb) - np.log(nb) - ev.mean() + 0.10 * np.mean(r ** 2)
        sb = np.exp(fb - lse(fb)); se = np.exp(fe - lse(fe, axis=1, keepdims=True)); se = np.where(vt, se, 0.0)
        dfe = (-se / K).reshape(-1); dfb = sb + 0.20 * r / nb * 1.0 * 0  # dfb sólo de L1; L3 entra por r
        dge = dfe * B * (1 - te ** 2)
        dgb = (sb * B + 0.20 * r / nb * B) * (1 - tb ** 2)
        gWe, gbe = net.bwd(ce, dge); gWb, gbb = net.bwd(cb, dgb)
        grads = [a + b for a, b in zip(gWe + gbe, gWb + gbb)]
        gn = np.sqrt(sum((g ** 2).sum() for g in grads))
        if gn > 5.0: grads = [g * (5.0 / (gn + 1e-6)) for g in grads]
        t += 1; lr, wd, b1, b2, eps = 0.002, 0.05, 0.9, 0.999, 1e-8
        for i, g in enumerate(grads):
            params[i] *= (1 - lr * wd)
            mom[i] = b1 * mom[i] + (1 - b1) * g; var[i] = b2 * var[i] + (1 - b2) * g * g
            params[i] -= lr * (mom[i] / (1 - b1 ** t)) / (np.sqrt(var[i] / (1 - b2 ** t)) + eps)
        if ep % 10 == 0:
            gce, _ = net.fwd(ec.reshape(-1, p)); fce = (ec.reshape(-1, p) @ anchor + B * np.tanh(gce)).reshape(ec.shape[0], J)
            fce = np.where(vc, fce, -np.inf); evc = lse(fce, axis=1) - np.log(vc.sum(1))
            gcb, _ = net.fwd(bc); fcb = bc @ anchor + B * np.tanh(gcb)
            score = float(evc.mean() - (lse(fcb) - np.log(len(fcb))))
            if score > best: best, best_ep = score, ep; best_state = ([w.copy() for w in net.W], [x.copy() for x in net.b])
    net.W, net.b = best_state
    return net, best, best_ep
def predict(net, X, anchor, B):
    sh = X.shape; g, _ = net.fwd(X.reshape(-1, sh[-1])); return (X.reshape(-1, sh[-1]) @ anchor + B * np.tanh(g)).reshape(sh[:-1])
if __name__ == '__main__':
    t0 = time.time(); ref = {(r['protocolo'], r['variante'], r['modelo']): r for r in csv.DictReader(open(R + 'REFERENCIA_comparacion_modelos.csv'))}
    sel_pub = json.load(open(R + 'SELECCION.json')); res = {}
    print('--- (1) selección del ancla: conjunta vs secuencial ---')
    for key, st in P.items():
        d = load(key); b = {lam: fit(d, lam, pen) for lam in LAM}
        joint = max(((calib(d, a*b[l]), l, a) for l in LAM for a in ALP))
        lam_seq = max(((calib(d, 1.0*b[l]), l) for l in LAM))[1]; a_seq = max(((calib(d, a*b[lam_seq]), a) for a in ALP))[1]
        res[key] = dict(joint=(joint[1], joint[2]), seq=(lam_seq, a_seq), pub=(st['lambda_clipped'], st['alpha_clipped']))
        print(f"{key:26s} conjunta={res[key]['joint']} secuencial={res[key]['seq']} publicada={res[key]['pub']} {'OK' if res[key]['seq']==res[key]['pub'] else 'NO'}")
    print('\n--- (2) reentrenamiento de las redes (NumPy, ancla publicada congelada, semillas 5101-5103) ---')
    rows = []
    for key, st in P.items():
        d = load(key); anchor = np.array(st['anchor'], dtype=np.float64); e, bm = d['etest'], d['btest']
        valid = d['valid_e'][e]; Xb = d['Xb'][bm]; Xe = d['Xe'][e]
        ev_a, cap_a = evaluar(Xe @ anchor, Xb @ anchor, valid)
        cal = {}
        for B in (0.25, 1.0):
            fes, fbs, cs = [], [], []
            for seed in (5101, 5102, 5103):
                net, score, ep = train(d, anchor, B, seed); cs.append(score)
                fes.append(predict(net, Xe, anchor, B)); fbs.append(predict(net, Xb, anchor, B))
            fe, fb = ensamble(fes, fbs); ev, cap = evaluar(fe, fb, valid); cal[B] = float(np.mean(cs))
            r = ref[(st['protocol'], st['variant'], f'residual_B{B}')]
            rows.append(dict(key=key, B=B, ld_new=float(ev.mean()), ld_pub=float(r['log_densidad_relativa']), cap_new=float(cap.mean()), cap_pub=float(r['captura_top10pct_soporte']),
                             ld_anchor=float(ev_a.mean()), cal=cal[B], ep=None))
            print(f"{key:26s} B={B:<4} test: nueva {ev.mean():.4f} | publicada {float(r['log_densidad_relativa']):.4f} | ancla {ev_a.mean():.4f} | captura nueva {cap.mean():.4f} pub {float(r['captura_top10pct_soporte']):.4f} | cal {cal[B]:.4f}")
        chosen = max(cal, key=cal.get)
        print(f"{'':26s} B elegida por calibración: {chosen} | publicada: {sel_pub[key]['bound_selected_by_calibration']}  ({time.time()-t0:.0f}s)", flush=True)
    json.dump(dict(sel=res, rows=rows), open(os.path.dirname(os.path.abspath(__file__)) + "/retrain_np.json", 'w'), indent=1, default=float)
