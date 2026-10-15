"""Figura S6: cambio de retrodispersión Sentinel-1 en bloques con eventos del COE frente al resto del construido."""
import os, numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': ['Helvetica', 'Arial', 'DejaVu Sans'], 'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False})
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')); R = f'{ROOT}/09_ANALISIS_ROBUSTEZ'
d = pd.read_csv(f'{R}/B2_sentinel1_por_adquisicion.csv'); d['t'] = pd.to_datetime(d.fecha)
s = pd.read_csv(f'{R}/B2_sentinel1_resumen.csv')
m, lo, hi = s.iloc[0][['media', 'ic95_inf', 'ic95_sup']]
fig, ax = plt.subplots(1, 2, figsize=(16 / 2.54, 7 / 2.54), dpi=300, gridspec_kw={'width_ratios': [1.5, 1]})
a = ax[0]; c = np.where(d.diferencia > 0, '#c0504d', '#1f4e79')
a.scatter(d.t, d.diferencia, s=6 + 3 * d.bloques_evento, c=c, alpha=0.8, lw=0)
a.axhline(0, color='#555', lw=0.7); a.axhline(m, color='#c0504d', lw=1, ls='--'); a.axhspan(lo, hi, color='#c0504d', alpha=0.12)
import matplotlib.dates as mdates
a.xaxis.set_major_locator(mdates.YearLocator()); a.xaxis.set_major_formatter(mdates.DateFormatter('%Y')); a.set_ylabel('Diferencia de cambio VV (dB)'); a.set_title('a. Diferencia por adquisición (n = %d)' % len(d), loc='left', fontsize=8.5)
b = ax[1]; b.scatter(d.rho_percentil_delta, np.argsort(np.argsort(d.rho_percentil_delta.values)), s=6, c='#555', lw=0)
b.axvline(0, color='#555', lw=0.7); b.axvline(s.iloc[4].media, color='#c0504d', ls='--', lw=1)
b.set_xlabel('Spearman: susceptibilidad y cambio VV'); b.set_yticks([]); b.set_title('b. Correlación por adquisición', loc='left', fontsize=8.5)
fig.tight_layout(); fig.savefig(f'{ROOT}/10_FIGURAS/figS6_sentinel1.png'); print('ok')
