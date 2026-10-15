"""Construye MANUSCRITO_QUITO_V20.docx a partir de la V19: fórmulas, tablas 8 a 11, figuras 7 a 9, anexo A.7, citas y referencias.
Uso: python construir_v20.py   (lee 01_MANUSCRITO/MANUSCRITO_QUITO_V19.docx y los CSV de 02_DATOS_NBI y 09_ANALISIS_ROBUSTEZ)"""
import os, re, copy, unicodedata
from xml.sax.saxutils import escape
import pandas as pd
import docx
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from lxml import etree
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SRC = f'{ROOT}/01_MANUSCRITO/MANUSCRITO_QUITO_V19.docx'; DST = f'{ROOT}/01_MANUSCRITO/MANUSCRITO_QUITO_V20.docx'
R09, FIG = f'{ROOT}/09_ANALISIS_ROBUSTEZ', f'{ROOT}/10_FIGURAS'
WNS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'; MNS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
d = docx.Document(SRC)
def only(sub, exact_start=False):
    r = [p for p in d.paragraphs if (p.text.strip().startswith(sub) if exact_start else sub in p.text)]
    assert len(r) == 1, (sub[:60], len(r)); return r[0]
def replace_in(p, old, new):
    for r in p.runs:
        if old in r.text: r.text = r.text.replace(old, new); return
    full = ''.join(r.text for r in p.runs); assert old in full, old[:70]
    i = full.index(old); p.runs[0].text = full[:i] + new + full[i + len(old):]
    for r in p.runs[1:]: r.text = ''
def replace_all(old, new, expect=None):
    n = 0
    for p in d.paragraphs:
        while old in ''.join(r.text for r in p.runs):
            replace_in(p, old, new); n += 1
            if old in new: break
    assert n >= 1 and (expect is None or n == expect), (old, n); return n
# ---------- plantillas de formato ----------
cap_tpl = only('Tabla 5. Particiones de evaluación', True); note_tpl = only('Fuente: particiones congeladas de reportes.', True)
tbl_tpl = [t for t in d.tables if t.rows[0].cells[0].text.strip() == 'Protocolo'][0]._tbl
body_tpl = only('Los resultados muestran una mejora puntual de la red residual', True)
head_tpl = only('A.5 Relación con la medición satelital', True)
def clone_par(tpl, text):
    new = copy.deepcopy(tpl._p)
    for el in new.xpath('.//w:lastRenderedPageBreak'): el.getparent().remove(el)
    p = Paragraph(new, tpl._parent)
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = text; return new
class Cursor:
    def __init__(self, el): self.el = el
    def add(self, new): self.el.addnext(new); self.el = new; return new
def caption(cur, text): return cur.add(clone_par(cap_tpl, text))
def note(cur, text): return cur.add(clone_par(note_tpl, text))
def para(cur, text): return cur.add(clone_par(body_tpl, text))
def heading(cur, text): return cur.add(clone_par(head_tpl, text))
def picture(cur, path, width_cm=16):
    new = copy.deepcopy(cap_tpl._p)
    for r in new.xpath('./w:r'): new.remove(r)
    cur.add(new); Paragraph(new, cap_tpl._parent).add_run().add_picture(path, width=Cm(width_cm)); return new
def make_table(cur, widths, header, rows, aligns=None):
    t = copy.deepcopy(tbl_tpl); trs = t.xpath('./w:tr'); hdr, dat = copy.deepcopy(trs[0]), copy.deepcopy(trs[1])
    for tr in trs: t.remove(tr)
    grid = t.find(f'{{{WNS}}}tblGrid')
    for g in list(grid): grid.remove(g)
    for w in widths:
        gc = etree.SubElement(grid, f'{{{WNS}}}gridCol'); gc.set(f'{{{WNS}}}w', str(w))
    def build(tpl_tr, vals):
        tr = copy.deepcopy(tpl_tr); tcs = tr.xpath('./w:tc'); tc0 = copy.deepcopy(tcs[0])
        for tc in tcs: tr.remove(tc)
        for w, v in zip(widths, vals):
            tc = copy.deepcopy(tc0); tc.find(f'{{{WNS}}}tcPr').find(f'{{{WNS}}}tcW').set(f'{{{WNS}}}w', str(w))
            ps = tc.xpath('./w:p')
            for extra in ps[1:]: tc.remove(extra)
            p = Paragraph(ps[0], None); rs = p.runs
            for r in rs[1:]: r._r.getparent().remove(r._r)
            rs[0].text = str(v); tr.append(tc)
        return tr
    t.append(build(hdr, header))
    for r in rows: t.append(build(dat, r))
    cur.add(t); return t
# ---------- ecuaciones (OMML) ----------
RPR = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'; CT = f'<m:ctrlPr>{RPR}</m:ctrlPr>'
def r(t): return f'<m:r>{RPR}<m:t xml:space="preserve">{escape(t)}</m:t></m:r>'
def sub(b, s): return f'<m:sSub><m:sSubPr>{CT}</m:sSubPr><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>'
def sup(b, p): return f'<m:sSup><m:sSupPr>{CT}</m:sSupPr><m:e>{b}</m:e><m:sup>{p}</m:sup></m:sSup>'
def subsup(b, s, p): return f'<m:sSubSup><m:sSubSupPr>{CT}</m:sSubSupPr><m:e>{b}</m:e><m:sub>{s}</m:sub><m:sup>{p}</m:sup></m:sSubSup>'
def frac(n, dn): return f'<m:f><m:fPr>{CT}</m:fPr><m:num>{n}</m:num><m:den>{dn}</m:den></m:f>'
def summ(lower, upper, body):
    hide = '' if upper else '<m:supHide m:val="1"/>'
    return f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="subSup"/>{hide}{CT}</m:naryPr><m:sub>{lower}</m:sub><m:sup>{upper or ""}</m:sup><m:e>{body}</m:e></m:nary>'
def eq(cur, inner):
    el = etree.fromstring(f'<w:p xmlns:w="{WNS}" xmlns:m="{MNS}"><w:pPr><w:jc w:val="left"/></w:pPr><m:oMathPara><m:oMath>{inner}</m:oMath></m:oMathPara></w:p>')
    cur.add(el); return el
ind = lambda body: r('1[') + body + r(']')
# =========================================================
# 0) gramática y citas nuevas dentro del texto existente
replace_in(only('Este estudio examina cómo la pobreza por necesidades básicas insatisfechas (NBI) modifican'), '(NBI) modifican las prioridades', '(NBI) modifica las prioridades')
replace_all('(Municipio del Distrito Metropolitano de Quito, s. f.)', '(Municipio del Distrito Metropolitano de Quito, s. f.-a)')
replace_in(only('Recalculamos el NBI por hogar desde microdatos'), 'de la capa municipal de sectores. ', 'de la capa municipal de sectores (Municipio del Distrito Metropolitano de Quito, s. f.-b). ')
replace_in(only('Recalculamos el NBI por hogar desde microdatos'), 'conserva un Spearman de 0.996', 'conserva una correlación de rangos de Spearman (1904) de 0.996')
replace_in(only('Seleccionamos las primeras 13 parroquias de cada ordenamiento'), 'mediante Jaccard, definido como intersección dividida por unión', 'mediante el índice de Jaccard (1912), definido como intersección dividida por unión')
replace_in(only('Para examinar variación del contraste se calculan 3000 remuestreos'), 'se calculan 3000 remuestreos emparejados de bloques de 5 km', 'se calculan 3000 remuestreos emparejados de bloques de 5 km (Efron, 1979; Künsch, 1989)')
replace_in(only('Validación con una fuente independiente. Los eventos de inundación del COE municipal'), 'Los eventos de inundación del COE municipal (2572 entre 2005 y mayo de 2024)', 'Los eventos de inundación del COE municipal (Municipio del Distrito Metropolitano de Quito, s. f.-c; 2572 entre 2005 y mayo de 2024)')
# 1) sección 2.2: NBI explicado con fórmulas
cur = Cursor(only('Recalculamos el NBI por hogar desde microdatos')._p)
para(cur, 'Para precisar la medida, sea c la indicadora (1 si el hogar h presenta la privación k y 0 en caso contrario) de las cinco privaciones que define el INEC (dependencia económica, asistencia escolar, características físicas de la vivienda, servicios básicos y hacinamiento; tabla 10 del anexo A.7). El hogar tiene NBI si acumula al menos una privación y NBI extremo si acumula al menos dos:')
eq(cur, sub(r('NBI'), r('h')) + r(' = ') + ind(summ(r('k=1'), r('5'), sub(r('c'), r('hk'))) + r(' ≥ 1')) + r(',      ') + subsup(r('NBI'), r('h'), r('ext')) + r(' = ') + ind(summ(r('k=1'), r('5'), sub(r('c'), r('hk'))) + r(' ≥ 2')))
para(cur, 'La tasa parroquial de hogares con NBI, que es la medida n de la sección 2.3, y la de personas, que pondera cada hogar por su número de miembros m, son')
eq(cur, sub(r('n'), r('p')) + r(' = ') + frac(summ(r('h∈p'), '', sub(r('NBI'), r('h'))), sub(r('N'), r('p'))) + r(',      ') + sup(sub(r('n'), r('p')), r('pers')) + r(' = ') + frac(summ(r('h∈p'), '', sub(r('m'), r('h')) + sub(r('NBI'), r('h'))), summ(r('h∈p'), '', sub(r('m'), r('h')))))
para(cur, 'donde N es el número de hogares de la parroquia p y h recorre sus hogares. Ambas tasas se calculan sobre el universo de viviendas particulares ocupadas con personas presentes.')
# 2) anexo A.3: métricas de evaluación con fórmulas
cur = Cursor(only('La evaluación conserva separaciones temporales y espaciales')._p)
para(cur, 'Para cada reporte i, con V el conjunto de sus posiciones válidas y ρ la densidad normalizada de la sección A.2, cuya media en el fondo es uno, la log densidad relativa y la captura del 10 % superior del territorio son')
eq(cur, sub(r('S'), r('i')) + r(' = ln') + r('(') + frac(r('1'), r('|') + sub(r('V'), r('i')) + r('|')) + summ(r('v∈') + sub(r('V'), r('i')), '', sub(r('ρ'), r('θ')) + r('(') + sub(r('x'), r('iv')) + r(')')) + r(')') + r(',      ') + sub(r('C'), r('i')) + r(' = ') + frac(r('1'), r('|') + sub(r('V'), r('i')) + r('|')) + summ(r('v∈') + sub(r('V'), r('i')), '', ind(sub(r('ρ'), r('θ')) + r('(') + sub(r('x'), r('iv')) + r(') ≥ ') + sub(r('q'), r('0.9')))))
para(cur, 'donde q es el cuantil 0.9 de ρ en el fondo. Las tablas 6 y 7 reportan el promedio de S y de C sobre los reportes de evaluación.')
# 3) anexo A.6: referencias a figuras y tablas, y bloques nuevos
replace_in(only('Modelos con menos variables igualan al completo'), 'y se presentan como exploratorias.', 'y se presentan como exploratorias (tabla 8).')
p7 = only('El modelo ordena, pero su intensidad no está calibrada fuera del ajuste')
replace_in(p7, 'frente a 0.904 esperado.', 'frente a 0.904 esperado (figura 7).')
cur = Cursor(p7._p)
caption(cur, 'Figura 7. Calibración por deciles de susceptibilidad en las pruebas de evaluación'); picture(cur, f'{FIG}/fig7_calibracion_deciles.png')
note(cur, 'Fuente: reportes de evaluación del SNGR y ancla de la variante vías y FABDEM. Elaboración propia. Los puntos son la participación acumulada de reportes observada al ordenar el territorio de mayor a menor puntaje; la línea discontinua es la que implica la densidad del modelo.')
pA5 = only('Quitar las variables de exposición (construido, vías y sus derivadas)')
replace_in(pA5, 'con estratos definidos por la mediana del construido y muestras pequeñas.', 'con estratos definidos por la mediana del construido y muestras pequeñas. La tabla 8 reúne los modelos de menos variables y los modelos solo físico y solo exposición.')
a4 = pd.read_csv(f'{R09}/A4_referencias_simples.csv').set_index('modelo'); a5 = pd.read_csv(f'{R09}/A5_fisico_vs_completo.csv').set_index('modelo')
def fila(nom, v, src, k):
    x = src.loc[k]; return [nom, v, f"{x.temporal_logdens:.3f}", f"{100 * x.temporal_captura:.1f}", f"{x.espacial_logdens:.3f}", f"{100 * x.espacial_captura:.1f}"]
rows8 = [fila('Completo (ancla)', 25, a4, 'Modelo completo, ancla (25)'), fila('Solo construido y vías', 3, a4, 'Urbano (construido 100/500 m y vial)'), fila('Solo exposición', 6, a5, 'Solo exposición'),
         fila('Solo físico (sin exposición)', 16, a5, 'Solo físico (sin exposición)'), fila('Terreno y drenaje', 7, a4, 'Terreno + drenaje (7)'), fila('Solo construido a 500 m', 1, a4, 'Solo construido 500 m'),
         fila('Solo distancia a vías', 1, a4, 'Solo distancia vial'), fila('Solo distancia a colector', 1, a4, 'Solo distancia a colector'), fila('Solo pendiente', 1, a4, 'Solo pendiente')]
cur = Cursor(pA5._p)
caption(cur, 'Tabla 8. Modelos de menos variables frente al modelo completo'); make_table(cur, [2400, 1000, 1418, 1418, 1418, 1418], ['Modelo', 'Variables', 'Temporal: log densidad', 'Temporal: captura (%)', 'Espacial: log densidad', 'Espacial: captura (%)'], rows8)
note(cur, 'Fuente: evaluación emparejada del estudio con las mismas particiones, posiciones y fondo de las tablas 6 y 7. Elaboración propia. Penalización y temperado elegidos por calibración. Las especificaciones se definieron después de observar el test: son exploratorias. Azar: log densidad 0 y captura 10 %.')
pB1 = only('Validación con una fuente independiente. Los eventos de inundación del COE municipal')
replace_in(pB1, 'de modo que la independencia es parcial.', 'de modo que la independencia es parcial (tabla 9).')
b1 = pd.read_csv(f'{R09}/B1_validacion_coe.csv'); b1 = b1[b1.radio_m == 50]
ordr = ['Ancla (25 variables)', 'Ancla + red (referencia del repo)', 'Urbano (3)', 'Terreno + drenaje (7)', 'Solo físico (16)']
etq = {'Ancla (25 variables)': 'Completo (ancla)', 'Ancla + red (referencia del repo)': 'Completo (ancla + red)', 'Urbano (3)': 'Solo construido y vías', 'Terreno + drenaje (7)': 'Terreno y drenaje', 'Solo físico (16)': 'Solo físico (sin exposición)'}
rows9 = []
for sub_, lab in (('posteriores', '2022 a mayo 2024'), ('todos', '2010 a mayo 2024')):
    for m in ordr:
        x = b1[b1.subconjunto.str.startswith(sub_) & (b1.modelo == m)].iloc[0]
        rows9.append([lab, etq[m], int(x.eventos), f"{100 * x.captura_10pct:.1f} ({100 * x.captura_ic_inf:.1f} a {100 * x.captura_ic_sup:.1f})", f"{x.logdens_dentro_construido:.2f} ({x.logdens_ic_inf:.2f} a {x.logdens_ic_sup:.2f})"])
cur = Cursor(pB1._p)
caption(cur, 'Tabla 9. Validación con eventos de inundación del COE municipal dentro del construido'); make_table(cur, [1900, 2400, 700, 2050, 2022], ['Período', 'Modelo', 'N', 'Captura del 10 % (%) e IC 95 %', 'Log densidad relativa e IC 95 %'], rows9)
note(cur, 'Fuente: eventos de inundación del COE municipal asignados al píxel construido más cercano (máximo 50 m). Elaboración propia. IC 95 %: bootstrap por bloques de 5 km, 1000 réplicas. Azar: captura 10 % y log densidad 0. Los eventos de 2022 a mayo de 2024 son posteriores al período de entrenamiento (2010 a 2021).')
pA3 = only('Validación dejando un bloque fuera. Con los 331 reportes')
cur = Cursor(pA3._p)
para(cur, 'Incertidumbre del ranking. Sea T el conjunto de las 13 parroquias con mayor índice NBI en la réplica b, con b = 1,…,B y B = 300. La probabilidad de pertenencia de la parroquia p es')
eq(cur, sub(r('P'), r('p')) + r(' = ') + frac(r('1'), r('B')) + summ(r('b=1'), r('B'), ind(r('p ∈ ') + subsup(r('T'), r('13'), r('(b)')))))
para(cur, 'Cada réplica remuestrea con reemplazo los bloques de 5 km de los 143 reportes de entrenamiento, reajusta el ancla con la penalización y el temperado publicados y repite la priorización sobre los 2993619 píxeles construidos. La figura 8 muestra esa probabilidad para las 28 parroquias con valor de al menos 0.05, junto con la probabilidad que resulta de seleccionar solo por área: siete parroquias superan 0.9 y la incorporación de Pomasqui y Tumbaco por NBI ocurre en 23 % y 34 % de las réplicas.')
caption(cur, 'Figura 8. Probabilidad de pertenecer a las 13 parroquias prioritarias'); picture(cur, f'{FIG}/fig8_incertidumbre_ranking.png')
note(cur, 'Fuente: 300 réplicas por bloques de 5 km de los reportes de entrenamiento, ancla reajustada y prioridad recalculada. Elaboración propia. Azul oscuro: probabilidad de al menos 0.9; azul medio: entre 0.5 y 0.9. Cuadrado rojo: parroquias que están entre las 13 con la estimación puntual.')
para(cur, 'NBI por sector censal. Para cada sector s de la parroquia p, sean H el área prioritaria ponderada por lluvia y n su tasa de hogares con NBI. El índice a escala de sector es')
eq(cur, sup(sub(r('I'), r('p')), r('sec')) + r(' = ') + summ(r('s∈p'), '', sub(r('H'), r('s')) + sub(r('n'), r('s'))))
para(cur, 'La figura 9 compara, para cada parroquia, el NBI medio ponderado por el área prioritaria con la tasa parroquial. Las diferencias van de −33 a +31 puntos porcentuales y el área prioritaria cae, en promedio, en sectores con menos NBI que la parroquia (9.36 % frente a 10.55 %). En el escenario principal coinciden 11 de las 13 parroquias del índice (Centro Histórico y El Condado reemplazan a Pomasqui y Tumbaco).')
caption(cur, 'Figura 9. NBI del área prioritaria según sector censal y según parroquia'); picture(cur, f'{FIG}/fig9_nbi_sector_vs_parroquia.png')
note(cur, 'Fuente: capa municipal de sectores censales (7221 sectores), píxeles construidos del decil superior y tasas de hogares con NBI. Elaboración propia. Cada punto es una parroquia; el tamaño es proporcional al área prioritaria ponderada. La línea punteada marca la igualdad.')
last_A6 = cur.el
# 4) anexo A.7: definición y verificación del NBI
cur = Cursor(last_A6)
heading(cur, 'A.7 Definición y verificación del NBI')
para(cur, 'El NBI sigue la metodología del INEC (2024): un hogar es pobre por NBI si presenta al menos una de cinco privaciones, que se evalúan con las variables del censo y los umbrales de la tabla 10. Los indicadores se construyen a nivel de hogar y sus miembros comparten la condición. Se calcularon con microdatos del Censo 2022 sobre viviendas particulares ocupadas con personas presentes (5188827 hogares en el país y 873512 en el cantón Quito).')
caption(cur, 'Tabla 10. Componentes, indicadores y umbrales del NBI')
make_table(cur, [2300, 3000, 3772], ['Componente', 'Indicador', 'Umbral de privación'], [
 ['1. Dependencia económica', 'Años de escolaridad del representante y personas por persona ocupada', 'Representante con 3 o menos años de escolaridad y más de 3 personas por persona ocupada'],
 ['2. Niños en edad escolar', 'Asistencia a clases', 'Existen niños de 6 a 12 años que no asisten a clases'],
 ['3. Características físicas de la vivienda', 'Material del piso y de las paredes exteriores', 'Piso de tierra u otros materiales, o paredes de caña no revestida u otro material'],
 ['4. Servicios básicos', 'Fuente y forma de recepción del agua; eliminación de excretas', 'Sin servicio higiénico, o con inodoro conectado a pozo ciego, descarga directa o letrina; o agua de pozo, carro tanquero u otras fuentes, o por tubería fuera de la vivienda'],
 ['5. Hacinamiento', 'Personas por cuarto exclusivo para dormir', 'Más de 3 personas por cuarto (con 0 cuartos se asume 1)']])
note(cur, 'Fuente: INEC (2024), cuadro 1. Elaboración propia. Cada privación pesa igual; un hogar con dos o más privaciones se clasifica en NBI extremo.')
para(cur, 'El recálculo coincide con las cifras publicadas por el INEC (tabla 11): a nivel nacional difiere en menos de 0.01 % y en el cantón Quito en 0.008 %. En cambio, la suma de las parroquias de la capa municipal supera la cifra del INEC en 23375 personas con NBI (6.4 %).')
caption(cur, 'Tabla 11. NBI recalculado frente a las cifras del INEC y de la capa municipal')
make_table(cur, [1500, 2300, 1900, 1900, 1472], ['Ámbito', 'Medida', 'INEC', 'Recalculado', 'Capa municipal'], [
 ['País', 'Hogares con NBI', '1925141 (37.1 %)', '1925025 (37.10 %)', '—'],
 ['País', 'Personas con NBI', '6713750 (39.8 %)', '6713143 (39.76 %)', '—'],
 ['País', 'Personas con NBI extremo', '13.0 %', '13.03 %', '—'],
 ['Pichincha', 'Personas con NBI', '15.9 %', '15.87 %', '—'],
 ['Cantón Quito', 'Personas con NBI', '367089 (13.7 %)', '367058 (13.72 %)', '390464 (14.6 %)']])
note(cur, 'Fuente: INEC (2024), tabla 1, tabla 3, gráfico 4 y anexo 1; microdatos del Censo 2022 y capa municipal de parroquias. Elaboración propia.')
para(cur, 'La diferencia de la capa municipal se concentra en 83 partes de sectores censales divididos entre parroquias (41 sectores con hogares): sus hogares y hogares con NBI aparecen multiplicados por n³, donde n es el número de partes, mientras su población coincide con la de los microdatos. En los 7136 sectores restantes los hogares coinciden exactamente y los hogares con NBI coinciden en 7130 (diferencia de un hogar en los seis restantes). Para asignar un sector dividido b a sus partes s se reparte el número de hogares N del sector en los microdatos según la población de cada parte (π), y la tasa parroquial se obtiene ponderando con ese peso (w) las tasas r de las partes:')
eq(cur, sub(r('π'), r('s')) + r(' = ') + frac(sub(r('pobT'), r('s')), summ(r("s'∈b"), '', sub(r('pobT'), r("s'")))) + r(',      ') + sub(r('w'), r('s')) + r(' = ') + sub(r('N'), r('b')) + sub(r('π'), r('s')) + r(',      ') + sub(r('n'), r('p')) + r(' = ') + frac(summ(r('s∈p'), '', sub(r('w'), r('s')) + sub(r('r'), r('s'))), summ(r('s∈p'), '', sub(r('w'), r('s')))))
para(cur, 'Esta corrección afecta a 28 parroquias; la diferencia media con la capa es de 0.36 puntos porcentuales y la máxima de 5.95 (La Libertad, 24.96 % frente a 19.01 %). El reparto por población afecta a 0.7 % de los hogares y 93 hogares sin sector en la capa quedan fuera. Las 13 parroquias prioritarias no cambian con la corrección.')
# 4b) referencias cruzadas que faltaban
replace_in(only('La corrección se obtiene con dos capas ocultas de 16 y 8 neuronas'), 'una salida escalar inicializada a cero.', 'una salida escalar inicializada a cero (figura 5).')
replace_in(only('La evaluación conserva separaciones temporales y espaciales para contrastar'), 'para contrastar transferencia fuera del ajuste.', 'para contrastar transferencia fuera del ajuste (tabla 5).')
# 5) referencias nuevas y renombradas
ref_head = only('Referencias', True); refs = [p for p in d.paragraphs if p.text.strip() and p._p.getprevious() is not None]
i0 = [i for i, p in enumerate(d.paragraphs) if p.text.strip() == 'Referencias'][0]; reflist = d.paragraphs[i0 + 1:]
ref_tpl = [p for p in reflist if p.text.startswith('Elfwing')][0]
def key(t): return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
for p in reflist:
    if p.text.startswith('Municipio del Distrito Metropolitano de Quito. (s. f.).'): replace_in(p, '(s. f.).', '(s. f.-a).')
nuevas = [
 'Efron, B. (1979). Bootstrap methods: Another look at the jackknife. The Annals of Statistics, 7(1), 1-26. https://doi.org/10.1214/aos/1176344552',
 'Jaccard, P. (1912). The distribution of the flora in the alpine zone. New Phytologist, 11(2), 37-50. https://doi.org/10.1111/j.1469-8137.1912.tb05611.x',
 'Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. The Annals of Statistics, 17(3), 1217-1241. https://doi.org/10.1214/aos/1176347265',
 'Municipio del Distrito Metropolitano de Quito. (s. f.-b). Personas pobres por NBI Sectores Censales Censo 2022. https://geoquito.quito.gob.ec/server/rest/services/web_service/s_nbi_porcentaje_personas_con_pobreza_por_nbi_2022/MapServer/3',
 'Municipio del Distrito Metropolitano de Quito. (s. f.-c). Eventos COE 2005 a mayo de 2024 [Capa de datos]. https://geoquito.quito.gob.ec/server/rest/services/Hosted/Eventos_2024/FeatureServer/0',
 'Spearman, C. (1904). The proof and measurement of association between two things. The American Journal of Psychology, 15(1), 72-101. https://doi.org/10.2307/1412159']
for t in nuevas:
    reflist = d.paragraphs[[i for i, p in enumerate(d.paragraphs) if p.text.strip() == 'Referencias'][0] + 1:]
    reflist = [p for p in reflist if p.text.strip()]
    pos = None
    for p in reflist:
        if key(p.text) > key(t): pos = p; break
    new = clone_par(ref_tpl, t)
    if pos is None: reflist[-1]._p.addnext(new)
    else: pos._p.addprevious(new)
# 6) referencias a las figuras 8 y 9 desde la sección 3.5
replace_in(only('La incertidumbre de estimación limita la lectura del ranking.'), 'Pomasqui y Tumbaco ingresan por NBI en 23 % y 34 % de las réplicas.', 'Pomasqui y Tumbaco ingresan por NBI en 23 % y 34 % de las réplicas (figura 8, anexo A.6).')
replace_in(only('La escala del NBI también modifica el margen de la selección.'), 'Al asignar cada píxel construido a su sector censal (7221 sectores)', 'Al asignar cada píxel construido a su sector censal (7221 sectores; figura 9, anexo A.6)')
# 7) identificadores duplicados de párrafos clonados
W14 = 'http://schemas.microsoft.com/office/word/2010/wordml'; seen = set()
for el in d.element.body.iter():
    pid = el.get(f'{{{W14}}}paraId')
    if pid is None: continue
    if pid in seen:
        del el.attrib[f'{{{W14}}}paraId']
        if el.get(f'{{{W14}}}textId') is not None: del el.attrib[f'{{{W14}}}textId']
    else: seen.add(pid)
d.save(DST); print('guardado', DST)
