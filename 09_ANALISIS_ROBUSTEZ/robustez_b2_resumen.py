import numpy as np, pandas as pd
from scipy.stats import wilcoxon, binomtest
d = pd.read_csv('B2_sentinel1_por_adquisicion.csv'); rng = np.random.default_rng(11109); n = len(d)
def ic(x, w=None):
    b = [np.average(x[i], weights=None if w is None else w[i]) for i in (rng.integers(0, n, n) for _ in range(5000))]
    return np.percentile(b, [2.5, 97.5])
out = []
def add(nombre, x, w=None):
    x = np.asarray(x, float); m = np.average(x, weights=w); lo, hi = ic(x, w)
    out.append(dict(medida=nombre, media=m, ic95_inf=lo, ic95_sup=hi)); return m
add('Diferencia de cambio VV, eventos menos construido (dB)', d.diferencia)
add('Diferencia ponderada por bloques con evento (dB)', d.diferencia, d.bloques_evento.values.astype(float))
add('Proporción con caída > 3 dB: eventos menos construido (pp)', 100 * (d.p_menor3_evento - d.p_menor3_construido))
add('Proporción con alza > 3 dB: eventos menos construido (pp)', 100 * (d.p_mayor3_evento - d.p_mayor3_construido))
add('Spearman entre percentil de susceptibilidad y cambio VV', d.rho_percentil_delta)
add('Percentil medio de los bloques con evento menos construido', d.perc_evento - d.perc_construido)
o = pd.DataFrame(out); o.to_csv('B2_sentinel1_resumen.csv', index=False)
pos = int((d.diferencia < 0).sum()); p_sign = binomtest(pos, n).pvalue; p_w = wilcoxon(d.diferencia).pvalue
print(o.round(3).to_string(index=False)); print('adquisiciones', n, 'con diferencia<0:', pos, 'p signo %.3f' % p_sign, 'p Wilcoxon %.3f' % p_w)
print('bloques con evento (total)', int(d.bloques_evento.sum()), 'eventos', int(d.eventos.sum()))
print('rho<0 en', int((d.rho_percentil_delta < 0).sum()), 'de', n)
