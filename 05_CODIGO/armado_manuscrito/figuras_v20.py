"""Figuras 7, 8 y 9 de la V20 (calibración, incertidumbre del ranking y NBI por sector). Lee los CSV de 09_ANALISIS_ROBUSTEZ."""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': ['Helvetica', 'Arial', 'DejaVu Sans'], 'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#555', 'axes.linewidth': 0.8, 'xtick.color': '#333', 'ytick.color': '#333'})
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'); R = os.path.join(ROOT, '09_ANALISIS_ROBUSTEZ'); OUT = os.path.join(ROOT, '10_FIGURAS')
AZ, NA, GR = '#1f4e79', '#c55a11', '#8c8c8c'
# ---- Figura 7: calibración por deciles (acumulado desde el decil superior)
a7 = pd.read_csv(f'{R}/A7_calibracion_deciles.csv'); a7 = a7[a7.modelo == 'ancla']
fig, axs = plt.subplots(1, 2, figsize=(16 / 2.54, 6.2 / 2.54), dpi=300, sharey=True)
for ax, proto, col, tt in zip(axs, ('temporal', 'espacial'), (AZ, NA), ('a. Prueba temporal', 'b. Prueba espacial')):
    g = a7[a7.protocolo == proto].sort_values('decil', ascending=False)
    x = np.arange(1, 11) * 10; obs = np.cumsum(g.participacion_observada.values) * 100; esp = np.cumsum(g.participacion_esperada.values) * 100
    ax.plot(x, x, color=GR, lw=0.9, ls=':', label='Azar'); ax.plot(x, esp, color=col, lw=1.4, ls='--', label='Esperado por el modelo'); ax.plot(x, obs, color=col, lw=1.8, marker='o', ms=3, label='Observado en el test')
    ax.set_title(tt, loc='left', fontsize=8.5); ax.set_xlabel('Territorio ordenado de mayor a menor susceptibilidad (%)'); ax.set_xlim(0, 102); ax.set_ylim(0, 102)
    ax.annotate(f'{obs[0]:.0f} % observado\n{esp[0]:.0f} % esperado', xy=(10, obs[0]), xytext=(30, 52), fontsize=7.5, arrowprops=dict(arrowstyle='-', color='#777', lw=0.6))
axs[0].set_ylabel('Reportes acumulados (%)'); axs[0].legend(frameon=False, fontsize=7, loc='lower right')
fig.tight_layout(); fig.savefig(f'{OUT}/fig7_calibracion_deciles.png'); plt.close(fig)
# ---- Figura 8: probabilidad de pertenecer a las 13 prioritarias
a1 = pd.read_csv(f'{R}/A1_incertidumbre_ranking.csv'); a1 = a1[a1.prob_top13_por_indice_nbi >= 0.05].sort_values('prob_top13_por_indice_nbi')
fig, ax = plt.subplots(figsize=(16 / 2.54, 9.6 / 2.54), dpi=300)
cols = ['#1f4e79' if p >= .9 else '#5b9bd5' if p >= .5 else '#bdd7ee' for p in a1.prob_top13_por_indice_nbi]
y = np.arange(len(a1)); ax.barh(y, a1.prob_top13_por_indice_nbi, color=cols, height=0.7)
ax.scatter(a1.prob_top13_por_area, y, facecolors='none', edgecolors='#333', s=14, lw=0.8, zorder=3, label='Probabilidad con la selección por área (sin NBI)')
ax.scatter(np.where(a1.top13_indice_punto == 1, 1.03, np.nan), y, marker='s', color='#c00000', s=9, zorder=3, label='En las 13 con la estimación puntual')
ax.set_yticks(y); ax.set_yticklabels([n.title() for n in a1.nombre], fontsize=7); ax.set_xlim(0, 1.08)
for v in (0.5, 0.9): ax.axvline(v, color=GR, lw=0.7, ls=':')
ax.set_xlabel('Probabilidad de pertenecer a las 13 prioritarias por índice NBI (300 réplicas)')
ax.legend(frameon=False, fontsize=7, loc='lower right'); fig.tight_layout(); fig.savefig(f'{OUT}/fig8_incertidumbre_ranking.png'); plt.close(fig)
# ---- Figura 9: NBI medio del área prioritaria, sector frente a parroquia
b = pd.read_csv(f'{R}/A2_nbi_en_area_prioritaria_vs_parroquia.csv')
fig, ax = plt.subplots(figsize=(16 / 2.54, 8.4 / 2.54), dpi=300)
x = b.tasa_parroquia * 100; yv = b.tasa_sector_ponderada * 100
ax.plot([0, 100], [0, 100], color=GR, lw=0.9, ls=':'); ax.scatter(x, yv, s=10 + 160 * b.H / b.H.max(), color='#5b9bd5', alpha=0.75, edgecolors='#1f4e79', linewidths=0.5)
for _, r in b[b.dif_pp.abs() >= 10].iterrows(): ax.annotate(str(r.nombre).title(), (r.tasa_parroquia * 100, r.tasa_sector_ponderada * 100), xytext=(4, 3), textcoords='offset points', fontsize=6.5)
ax.set_xlim(0, 75); ax.set_ylim(0, 75); ax.set_xlabel('NBI de la parroquia, hogares (%)'); ax.set_ylabel('NBI medio ponderado por el área prioritaria,\nsegún sector censal (%)')
fig.tight_layout(); fig.savefig(f'{OUT}/fig9_nbi_sector_vs_parroquia.png'); plt.close(fig)
print('figuras 7, 8 y 9 generadas')
