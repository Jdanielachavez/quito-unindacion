"""Integra C2 (validación por bloques de modelos alternativos) y C3 (priorización con modelos alternativos) en los V21 de 00_ENTREGA_FINAL."""
import copy, re, docx, pandas as pd
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
from lxml import etree
ROOT = '/Users/daniela/Desktop/PAPER INUNDACION/'; E = ROOT + '00_ENTREGA_FINAL/'; R = ROOT + '09_ANALISIS_ROBUSTEZ/'
NB = ' '
def nbs(t): return re.sub(r'(?<=\d) (?=\d{3}(?!\d))', NB, t)
c2 = pd.read_csv(R + 'C2_bloque_fuera_alternativos.csv').set_index('modelo'); c3 = pd.read_csv(R + 'C3_prioridad_modelos_alternativos.csv')
t13 = pd.read_csv(R + 'C3_top13_por_modelo_y_lluvia.csv')
cnt = t13.groupby('nombre').apply(lambda x: x[['modelo', 'escenario_lluvia']].drop_duplicates().shape[0], include_groups=False)
assert cnt['GUAMANI'] == 15 and cnt['LA ECUATORIANA'] == 15 and cnt['QUITUMBE'] == 15 and cnt['TURUBAMBA'] == 14 and cnt['CONOCOTO'] == 13 and cnt['AMAGUAÑA'] == 13
cambian = 13 - c3[c3.modelo != 'Ancla (recalculada)'].top13_indice_coinciden_con_red_repo.min()
# ---------------- suplemento ----------------
S = docx.Document(E + '2_MATERIAL_SUPLEMENTARIO_V21.docx')
P = S.paragraphs
assert not any(p.text.startswith('Tabla S11.') for p in P)
old = [p for p in P if p.text.startswith('Modelos no lineales.')][0]
cap_tpl = [p for p in P if p.text.startswith('Tabla S10.')][0]; note_tpl = [p for p in P if p.text.startswith('Fuente: Sentinel-1 RTC (Microsoft')][0]
tbl_tpl = S.tables[-1]._tbl
def cl(tpl, text):
    new = copy.deepcopy(tpl._p)
    for el in new.xpath('.//w:lastRenderedPageBreak'): el.getparent().remove(el)
    p = Paragraph(new, tpl._parent)
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = nbs(text); return new
def make_table(widths, header, rows):
    t = copy.deepcopy(tbl_tpl); trs = t.xpath('./w:tr'); hdr, dat = copy.deepcopy(trs[0]), copy.deepcopy(trs[1])
    for tr in trs: t.remove(tr)
    grid = t.find(qn('w:tblGrid'))
    for g in list(grid): grid.remove(g)
    for w in widths: etree.SubElement(grid, qn('w:gridCol')).set(qn('w:w'), str(w))
    def build(tpl_tr, vals):
        tr = copy.deepcopy(tpl_tr); tcs = tr.xpath('./w:tc'); tc0 = copy.deepcopy(tcs[0])
        for tc in tcs: tr.remove(tc)
        for w, v in zip(widths, vals):
            tc = copy.deepcopy(tc0); tc.find(qn('w:tcPr')).find(qn('w:tcW')).set(qn('w:w'), str(w))
            ps = tc.xpath('./w:p')
            for ex in ps[1:]: tc.remove(ex)
            p = Paragraph(ps[0], None)
            for rr in p.runs[1:]: rr._r.getparent().remove(rr._r)
            p.runs[0].text = nbs(str(v)); tr.append(tc)
        return tr
    t.append(build(hdr, header))
    for row in rows: t.append(build(dat, row))
    return t
a = c2.loc['Ancla loglineal (repo)']; lg, bo, rf, en = (c2.loc[k] for k in ('Logística', 'Boosting (prof. 2)', 'Bosque aleatorio', 'Ensamble ancla + boosting + bosque'))
txt = (f"Modelos alternativos. Con las mismas particiones, el mismo fondo y las mismas métricas, se compararon una regresión logística, dos modelos de boosting y un bosque aleatorio, "
       "con hiperparámetros elegidos solo con la calibración (archivo C1_modelos_alternativos.csv). En la prueba temporal ninguno supera al ancla (1.960 y 86.8 %): la logística da 1.863 y 88.6 %, "
       "el boosting entre 1.710 y 1.786 y el bosque 1.799 y 87.6 %; en la espacial, el boosting de profundidad 2 (1.357 y 65.4 %) y el bosque (1.297 y 70.1 %) superan al ancla (1.095 y 63.9 %), "
       "pero con 58 reportes en 13 bloques la diferencia no es concluyente. Para ganar potencia se repitió la comparación con los 331 reportes dejando fuera un bloque de 5 km cada vez (55 bloques; hiperparámetros fijados de antemano; tabla S11). "
       f"Los tres modelos no lineales y la logística elevan la captura del 10 % superior en unos 3 puntos porcentuales (de {100 * a.captura:.1f} % a {100 * lg.captura:.1f} % con la logística, con IC 95 % de la diferencia de {100 * lg.captura_dif_ic_inf:.1f} a {100 * lg.captura_dif_ic_sup:.1f} puntos), "
       f"pero no mejoran la log densidad de forma distinguible (logística: {lg.logdens_dif_vs_ancla:+.3f}, IC {lg.logdens_dif_ic_inf:.3f} a {lg.logdens_dif_ic_sup:.3f}; bosque y ensamble, peor). Ningún modelo domina al ancla, de modo que el límite está en la información de las covariables y de los reportes y no en la forma funcional.")
new = [cl(old, txt),
       cl(old, f"Efecto sobre la priorización. Se puntuaron los 2{NB}993{NB}619 píxeles construidos con cada modelo (entrenado con los reportes de entrenamiento, como la aplicación) y se repitió la selección de 13 parroquias con el índice H por NBI en los tres escenarios de lluvia (archivo C3_prioridad_modelos_alternativos.csv). El ancla recalculada reproduce la prioridad del repositorio (Spearman de 1.00 con la red residual en los escenarios ENSO y NMME), lo que valida la reconstrucción. Con los otros modelos, la selección cambia hasta {cambian} de las 13 parroquias. En las 15 combinaciones de modelo y lluvia, Guamaní, La Ecuatoriana y Quitumbe están siempre entre las 13, Turubamba en 14, Conocoto y Amaguaña en 13, San Antonio en 11, Calderón y Solanda en 10, Pomasqui en 8 y Tumbaco en 4; es decir, la selección es sensible a la clase de modelo, además de a la lluvia y a la muestra."),
       cl(cap_tpl, 'Tabla S11. Validación dejando un bloque de 5 km fuera: ancla frente a modelos alternativos (331 reportes, 55 bloques)')]
rows = []
for k in ['Ancla loglineal (repo)', 'Logística', 'Boosting (prof. 2)', 'Bosque aleatorio', 'Ensamble ancla + boosting + bosque']:
    r = c2.loc[k]
    rows.append([k.replace('(repo)', 'del repositorio'), f'{r.logdens:.3f}', f'{100 * r.captura:.1f}',
                 '—' if k.startswith('Ancla') else f'{100 * r.captura_dif_vs_ancla:+.1f} ({100 * r.captura_dif_ic_inf:.1f} a {100 * r.captura_dif_ic_sup:.1f})',
                 '—' if k.startswith('Ancla') else f'{int(r.bloques_mejor_que_ancla)} de 55'])
new.append(make_table([3200, 1100, 1200, 2200, 1372], ['Modelo', 'Log densidad', 'Captura (%)', 'Diferencia de captura vs ancla, pp (IC 95 %)', 'Bloques con mejor log densidad'], rows))
new.append(cl(note_tpl, 'Fuente: validación dejando un bloque de 5 km fuera con los 331 reportes. Elaboración propia. Hiperparámetros fijados de antemano. IC 95 %: bootstrap de bloques (3 000 réplicas). Azar: log densidad 0 y captura 10 %. Detalle en C2_bloque_fuera_alternativos.csv.'))
anchor_p = old._p
for el in reversed(new): anchor_p.addnext(el)
anchor_p.getparent().remove(anchor_p)
# intro S8: mencionar tabla S11 no necesario; guardar
S.save(E + '2_MATERIAL_SUPLEMENTARIO_V21.docx')
# ---------------- manuscrito ----------------
M = docx.Document(E + '1_MANUSCRITO_V21.docx')
nota = [p for p in M.paragraphs if p.text.startswith('Fuente: 300 réplicas por bloques de 5 km de los reportes de entrenamiento')][0]
assert not any(p.text.startswith('Un tercer origen de variación') for p in M.paragraphs)
tpl = [p for p in M.paragraphs if p.text.startswith('El presupuesto y el umbral modifican')][0]
par = cl(tpl, f"Un tercer origen de variación es la clase de modelo territorial. Al sustituir el ancla por una regresión logística, boosting, un bosque aleatorio o un ensamble (tabla S11), la validación dejando un bloque de 5 km fuera mejora la captura en unos 3 puntos porcentuales sin mejorar la log densidad, y la selección de 13 parroquias cambia hasta en {cambian} de ellas según el modelo y el escenario de lluvia. Guamaní, La Ecuatoriana y Quitumbe permanecen entre las 13 en las 15 combinaciones de modelo y lluvia, Turubamba en 14 y Conocoto y Amaguaña en 13, mientras que Pomasqui lo hace en 8 y Tumbaco en 4 (sección S8).")
nota._p.addnext(par)
def app(start, extra):
    p = [p for p in M.paragraphs if p.text.startswith(start)][0]; assert 'clase de modelo' not in p.text
    p.runs[-1].text = p.runs[-1].text.rstrip() + extra
app('La estabilidad debe leerse con dos criterios', ' Al variar además la clase de modelo territorial, el núcleo estable se reduce a Guamaní, La Ecuatoriana y Quitumbe, con Turubamba en 14 de 15 combinaciones y Conocoto y Amaguaña en 13.')
app('El resultado debe leerse con su incertidumbre', ' Al sustituir el ancla por otras clases de modelo, solo Guamaní, La Ecuatoriana y Quitumbe permanecen siempre entre las 13, de modo que la priorización de los márgenes depende también de la forma del modelo.')
n = [p for p in M.paragraphs if p.text.startswith('Fuente: evaluación del estudio y eventos de inundación')][0]
M.save(E + '1_MANUSCRITO_V21.docx'); print('ok', cambian)
