"""Figura S5: coeficientes del ancla con IC 95 % (bootstrap por bloques) y captura anual con eventos del COE."""
import os
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family': ['Helvetica', 'Arial', 'DejaVu Sans'], 'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False})
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')); R = f'{ROOT}/09_ANALISIS_ROBUSTEZ'
t = pd.read_csv(f'{R}/A8_coeficientes_vif.csv'); t = t[~t.constante].copy(); t['abs'] = t.coeficiente_publicado.abs(); t = t.sort_values('abs')
y = pd.read_csv(f'{R}/A8_coe_por_anio.csv')
fig, ax = plt.subplots(1, 2, figsize=(16 / 2.54, 8.2 / 2.54), dpi=300, gridspec_kw={'width_ratios': [1.25, 1]})
a = ax[0]; yy = np.arange(len(t)); col = ['#1f4e79' if e else '#8c8c8c' for e in t.ic_excluye_cero]
a.hlines(yy, t.ic95_inf, t.ic95_sup, color=col, lw=1.3); a.scatter(t.coeficiente_publicado, yy, color=col, s=12, zorder=3); a.axvline(0, color='#555', lw=0.7)
a.set_yticks(yy); a.set_yticklabels([n.replace('_', ' ') for n in t.variable], fontsize=6.3); a.set_xlabel('Coeficiente estandarizado e IC 95 %'); a.set_title('a. Coeficientes del ancla', loc='left', fontsize=8.5)
b = ax[1]; b.errorbar(y.anio, 100 * y.captura, yerr=[100 * (y.captura - y.ic95_inf), 100 * (y.ic95_sup - y.captura)], fmt='o', ms=3.5, color='#c55a11', ecolor='#c55a11', elinewidth=1, capsize=2)
b.axhline(10, color='#8c8c8c', ls=':', lw=1); b.text(2010, 11, 'azar', fontsize=7, color='#666'); b.set_ylim(0, 48); b.set_xlabel('Año del evento (2010 a 2024)'); b.set_ylabel('Eventos en el 10 % superior del construido (%)')
b.set_title('b. Captura anual (eventos del COE)', loc='left', fontsize=8.5); b.set_xticks(range(2010, 2025, 2)); b.set_xticklabels([f"'{str(y)[2:]}" for y in range(2010, 2025, 2)], fontsize=7)
fig.tight_layout(); fig.savefig(f'{ROOT}/10_FIGURAS/figS5_posestimacion.png'); print('figura S5 generada')
