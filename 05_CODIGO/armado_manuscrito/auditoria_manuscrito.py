"""Auditoría del manuscrito: cifras del texto frente a los CSV y a un recálculo desde el repo congelado; figuras, tablas y citas.
Uso: python auditoria_manuscrito.py [ruta_del_docx]"""
import os, re, sys, json, itertools, unicodedata
import numpy as np, pandas as pd, docx
from docx.table import Table
from docx.text.paragraph import Paragraph
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
F = sys.argv[1] if len(sys.argv) > 1 else f'{ROOT}/01_MANUSCRITO/MANUSCRITO_QUITO_V20.docx'
REPO = f'{ROOT}/11_REPO_MODELO/quito-enso-exposicion-reproducible/'; R09 = f'{ROOT}/09_ANALISIS_ROBUSTEZ'; D02 = f'{ROOT}/02_DATOS_NBI'
ok, bad = [], []
def check(n, c, det=''): (ok if c else bad).append(n + (f' -> {det}' if det and not c else ''))
d = docx.Document(F); lines, tabs = [], []
for el in d.element.body.iterchildren():
    tag = el.tag.split('}')[1]
    if tag == 'p': lines.append(Paragraph(el, d).text)
    elif tag == 'tbl': tabs.append([[c.text.strip() for c in r.cells] for r in Table(el, d).rows])
txt = '\n'.join(lines)
# --- recálculo
units = json.load(open(REPO + 'GRILLA.json'))['weather_units']; wea = pd.read_csv(REPO + 'DATOS_LLUVIA_ESCENARIOS.csv'); z = np.load(REPO + 'REFERENCIA_intersecciones.npz')
soc = pd.read_csv(REPO + 'DATOS_PARROQUIAS.csv', dtype={'parroquia': str})
nb = pd.read_csv(f'{D02}/nbi_hogar_65_parroquias_microdatos.csv', dtype={'parroquia': str}).set_index('parroquia')
tc = pd.read_csv(f'{D02}/tasas_corregidas_65_parroquias.csv', dtype={'parroquia': str}).set_index('parroquia')
n = soc.parroquia.map(nb.pct_hogares_nbi_micro).values / 100; names = soc.nombre.values
def area(tm, wm, q=90):
    idx = dict(zip(wea[wea.modelo == wm].unit, wea[wea.modelo == wm].p_humedo)); return z[f'{tm}_q{q}'][1:] @ np.array([idx[u] for u in units]) * 0.01
top = lambda v, k=13: set(np.argsort(-v, kind='stable')[:k])
A = area('red_residual', 'red_ENSO__beta_PIT'); I = A * n; tH, tI = top(A), top(I)
check('Pomasqui y Tumbaco entran; Iñaquito y Kennedy salen', {names[i] for i in tI - tH} == {'POMASQUI', 'TUMBACO'} and {names[i] for i in tH - tI} == {'IÑAQUITO', 'KENNEDY'})
for s_, lab in ((f'{I[list(tH)].sum():.2f}', 'índice por H'), (f'{I[list(tI)].sum():.2f}', 'índice por NBI'), (f'{100 * (I[list(tI)].sum() / I[list(tH)].sum() - 1):.2f} %', '+%'), (f'{A[list(tI)].sum():.2f}', 'H por NBI')):
    check(f'cifra {lab} ({s_}) en el texto', s_ in txt)
cnt = np.zeros(65, int)
for tm, wm in itertools.product(['red_residual', 'ancla_acotada'], dict.fromkeys(wea.modelo)):
    for i in top(area(tm, wm) * n): cnt[i] += 1
t3 = [t for t in tabs if t[0][0] == 'Parroquia' and 'Acuerdo' in t[0][-1]][0][1:]; okt3 = True
for row, i in zip(t3, sorted(tI, key=lambda i: -I[i])):
    okt3 &= row[1:] == [f'{100 * n[i]:.2f}', f'{A[i]:.2f}', f'{I[i]:.2f}', str(int((A > A[i]).sum() + 1)), f'{cnt[i]}/6']
check('Tabla 3 coincide con el recálculo', okt3 and len(t3) == 13)
t2 = [t for t in tabs if t[1][0].startswith('Construido analizado')][0]
st = lambda x: [f'{x.mean():.2f}', f'{x.std(ddof=1):.2f}', f'{x.min():.2f}', f'{x.max():.2f}']
rm = {'Hogares con NBI (%)': st(nb.pct_hogares_nbi_micro), 'Saneamiento inadecuado (%)': st(tc.pct_saneamiento_corregida), 'Agua limitada (%)': st(tc.pct_agua_corregida), 'Hacinamiento (%)': st(tc.pct_hacinamiento_corregida), 'Índice NBI (ha ponderadas)': st(pd.Series(I))}
for r in t2:
    if r[0] in rm: check(f'Tabla 2 · {r[0]}', r[2:] == rm[r[0]])
# --- tablas nuevas contra CSV
a4 = pd.read_csv(f'{R09}/A4_referencias_simples.csv').set_index('modelo'); t8 = [t for t in tabs if t[0][0] == 'Modelo' and 'Variables' in t[0][1]][0]
x = a4.loc['Modelo completo, ancla (25)']; check('Tabla 8 · completo', t8[1][2:] == [f'{x.temporal_logdens:.3f}', f'{100 * x.temporal_captura:.1f}', f'{x.espacial_logdens:.3f}', f'{100 * x.espacial_captura:.1f}'])
b1 = pd.read_csv(f'{R09}/B1_validacion_coe.csv'); b1 = b1[(b1.radio_m == 50) & b1.subconjunto.str.startswith('posteriores') & (b1.modelo == 'Ancla (25 variables)')].iloc[0]
t9 = [t for t in tabs if t[0][0] == 'Período'][0]; check('Tabla 9 · eventos y captura', t9[1][2] == str(int(b1.eventos)) and t9[1][3].startswith(f'{100 * b1.captura_10pct:.1f}'))
# --- A1, A2, A3, A5, A6, A7 en el texto
a1 = pd.read_csv(f'{R09}/A1_incertidumbre_ranking.csv').set_index('nombre')
check('A1: 7 con P ≥ 0.9 y 4 entre 0.5 y 0.9', int((a1.prob_top13_por_indice_nbi >= .9).sum()) == 7 and int(((a1.prob_top13_por_indice_nbi >= .5) & (a1.prob_top13_por_indice_nbi < .9)).sum()) == 4)
check('A1: Pomasqui 0.46 / Tumbaco 0.62 en el texto', abs(a1.loc['POMASQUI', 'prob_top13_por_indice_nbi'] - .46) < .006 and abs(a1.loc['TUMBACO', 'prob_top13_por_indice_nbi'] - .62) < .006 and '0.46 y 0.62' in txt)
check('A1: 28 parroquias con P ≥ 0.05', int((a1.prob_top13_por_indice_nbi >= .05).sum()) == 28)
muestra = set(a1[a1.prob_top13_por_indice_nbi >= .9].index); escen = {names[i] for i in range(65) if cnt[i] == 6}
check('cuatro parroquias cumplen ambos criterios', len(muestra & escen) == 4 and 'solo cuatro cumplen ambos criterios' in txt, str(sorted(muestra & escen)))
for fnm, cond, lab in ((f'{R09}/A3_dejando_un_bloque_fuera.csv', None, 'A3'),):
    a3 = pd.read_csv(fnm).set_index('modelo'); check('A3 1.73 / 0.82 en el texto', abs(a3.iloc[0].logdens - 1.73) < .006 and '1.73' in txt and '0.82' in txt)
# --- estructura
fig = [int(m.group(1)) for m in (re.match(r'^Figura (\d+)\.', l) for l in lines) if m]; tab = [int(m.group(1)) for m in (re.match(r'^Tabla (\d+)\.', l) for l in lines) if m]
check('figuras consecutivas', fig == list(range(1, len(fig) + 1)), str(fig)); check('tablas consecutivas', tab == list(range(1, len(tab) + 1)), str(tab))
check('imágenes = figuras', len(d.inline_shapes) == len(fig), f'{len(d.inline_shapes)} vs {len(fig)}')
for k, nums in (('figura', fig), ('tabla', tab)):
    for nn in nums:
        c = len(re.findall(rf'\b{k}s? (?:\d+ y )?{nn}\b|\b{k}s \d+ y {nn}\b|\b{k}s {nn} y \d+\b', txt)); check(f'{k} {nn} citada en el texto', c > 0)
heads = [l for l in lines if re.match(r'^(\d(\.\d)? |A\.\d |Anexo )', l)]
for ref in sorted(set(re.findall(r'anexo A\.\d', txt))): check(f'existe «{ref}»', any(h.startswith(ref.replace('anexo ', '')) for h in heads))
for ref in sorted(set(re.findall(r'sección (\d\.\d)', txt))): check(f'existe la sección {ref}', any(h.startswith(ref + ' ') for h in heads))
stale = [s_ for s_ in ('21.08', '22.15', '134.56', '136.19', '1035.00', '1.21 %', '3.51 %', 'sexto', 'cuatro con 20', 'El Condado y Tumbaco ingresan', 'manteniendo congelados los datos') if s_ in txt]
check('sin cifras ni frases obsoletas', not stale, str(stale))
check('sin subíndices con guion bajo en la prosa', not re.findall(r'\b[A-Za-z]_[A-Za-z0-9]+\b', re.sub(r'https?://\S+', '', txt)))
# --- citas y referencias
i0 = [i for i, l in enumerate(lines) if l.strip() == 'Referencias'][0]; refs = [l for l in lines[i0 + 1:] if l.strip()]
check('referencias en orden alfabético', [unicodedata.normalize('NFKD', r)[:20].lower() for r in refs] == sorted(unicodedata.normalize('NFKD', r)[:20].lower() for r in refs))
body = '\n'.join(lines[:i0])
for aut in ('Efron', 'Künsch', 'Jaccard', 'Spearman', 'Municipio del Distrito Metropolitano de Quito, s. f.-b', 'Municipio del Distrito Metropolitano de Quito, s. f.-c', 'Municipio del Distrito Metropolitano de Quito, s. f.-a'):
    check(f'citado en el texto: {aut}', aut in body)
for r in refs:
    m = re.match(r'^(.+?)\. \((\d{4}|s\. f\.(?:-[a-z])?)\)', r); check('referencia con formato APA: ' + r[:40], bool(m))
print(f'OK: {len(ok)} | FALLAN: {len(bad)}'); [print('  ✗', b) for b in bad]
