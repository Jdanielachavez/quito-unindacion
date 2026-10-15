"""Construye la V21 (artículo principal estilo revista Q1) y el material suplementario a partir de la V20.
Uso: python construir_v21.py"""
import os, re, copy, unicodedata
from xml.sax.saxutils import escape
import docx
from docx.text.paragraph import Paragraph
from lxml import etree
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SRC = f'{ROOT}/01_MANUSCRITO/MANUSCRITO_QUITO_V20.docx'
OUT_MAIN = f'{ROOT}/01_MANUSCRITO/MANUSCRITO_QUITO_V21.docx'; OUT_SUP = f'{ROOT}/01_MANUSCRITO/MATERIAL_SUPLEMENTARIO_V21.docx'
WNS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'; MNS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
W = lambda t: f'{{{WNS}}}{t}'
# =====================================================================  TEXTO
TITULO = 'Privación social y preparación ante inundaciones en Quito: una priorización parroquial con incertidumbre cuantificada'
AUTOR = 'Wilson Gustavo Morales Lastra y Josseline Daniela Chávez Carpio'
JEL = 'Códigos JEL: C45; C53; I32; Q54; R14'
KEYWORDS = 'Palabras clave: inundaciones urbanas; preparación ante desastres; necesidades básicas insatisfechas; vulnerabilidad social; proceso puntual; Quito'
RESUMEN = ('Objetivo. Evaluar cómo cambia la prioridad territorial de preparación ante inundaciones en Quito cuando, además de la superficie susceptible, se considera la privación por necesidades básicas insatisfechas (NBI). '
 'Métodos. La susceptibilidad se estima con 331 reportes de inundación (2010–2025) mediante un proceso puntual con ancla loglineal y corrección neuronal acotada, se aplica a 2 993 619 píxeles construidos de 10 m y se pondera por la probabilidad de un trimestre húmedo (noviembre 2026–enero 2027) y por la tasa parroquial de hogares con NBI, recalculada desde microdatos del Censo 2022 y verificada con las cifras del INEC. Se evalúa la estabilidad frente a modelo, lluvia, umbral, presupuesto, unidad de medida y muestra de reportes (300 réplicas), y la discriminación con particiones temporal y espacial y con 2 572 eventos independientes del COE municipal. '
 'Resultados. Incorporar el NBI cambia 2 de las 13 parroquias seleccionadas (Pomasqui y Tumbaco ingresan en lugar de Iñaquito y Kennedy), aumenta 1.48 % el índice social cubierto y reduce 3.10 % el área ponderada por lluvia. Solo cuatro parroquias (Guamaní, La Ecuatoriana, Conocoto y Amaguaña) son estables frente a modelo, lluvia y muestra; Pomasqui y Tumbaco ingresan en 23 % y 34 % de las réplicas. Dentro del construido, el 19.1 % de los eventos posteriores al entrenamiento cae en el 10 % superior (azar: 10 %). '
 'Conclusiones. La regla produce un orden relativo reproducible, con una cabeza robusta y un margen incierto; no estima probabilidad de inundación ni daños.')
ABSTRACT = ('Objective. To assess how the territorial priority for flood preparedness in Quito changes when unmet basic needs (UBN) are considered in addition to susceptible area. '
 'Methods. Susceptibility is estimated from 331 flood reports (2010–2025) with a point-process model combining a log-linear anchor and a bounded neural correction, applied to 2,993,619 built-up pixels at 10 m and weighted by the probability of a wet quarter (November 2026–January 2027) and by the parish rate of households with UBN, recomputed from 2022 Census microdata and checked against INEC figures. Stability is assessed against model, rainfall, threshold, budget, unit of measurement and report sample (300 replicates), and discrimination with temporal and spatial splits and 2,572 independent events from the municipal emergency committee. '
 'Results. Including UBN changes 2 of the 13 selected parishes (Pomasqui and Tumbaco enter instead of Iñaquito and Kennedy), raises the covered social index by 1.48 % and lowers rainfall-weighted area by 3.10 %. Only four parishes (Guamaní, La Ecuatoriana, Conocoto and Amaguaña) are stable across model, rainfall and sample; Pomasqui and Tumbaco enter in 23 % and 34 % of replicates. Within the built-up area, 19.1 % of post-training events fall in the top 10 % (chance: 10 %). '
 'Conclusions. The rule yields a reproducible relative ranking with a robust head and an uncertain margin; it does not estimate flood probability or damages.')
HIGHLIGHTS = ['Priorización parroquial que combina susceptibilidad, lluvia y privación social',
 'NBI por hogar recalculado desde microdatos y verificado con las cifras del INEC',
 'Solo cuatro de 13 parroquias son estables frente a modelo, lluvia y muestra',
 'Dentro del construido el modelo discrimina poco: validación con eventos del COE',
 'Datos derivados, código y auditoría disponibles para replicar los resultados']
EOF_MARK = None
# ----------------------------- cuerpo del artículo (tipo, contenido) -----------------------------
BODY = [
('h1', '1 Introducción'),
('p', 'Las inundaciones urbanas no afectan por igual a todos los hogares. La exposición física determina dónde se acumula el agua, pero la capacidad de prepararse, responder y recuperarse depende de las condiciones sociales y de los servicios disponibles (Cutter et al., 2003). La evidencia global indica que integrar exposición y vulnerabilidad modifica tanto la magnitud del riesgo como la distribución de las medidas de preparación (Rentschler et al., 2022; Fox et al., 2024; Mester et al., 2025).'),
('p', 'Quito ilustra el problema de asignación. El relieve, la urbanización y el acceso a servicios varían entre sus 65 parroquias (Watson et al., 2022), de modo que una parroquia con amplia superficie susceptible puede encabezar una selección por extensión, mientras otra con menor superficie y mayores carencias puede adquirir prioridad si el objetivo es atender necesidades básicas. Esa elección se toma con frecuencia sin hacerla explícita y sin cuantificar cuánto depende de los supuestos.'),
('p', 'La literatura aplicada presenta tres limitaciones recurrentes. Primero, los puntajes de susceptibilidad construidos con reportes de eventos se interpretan como probabilidades de inundación, aunque estiman la concentración relativa de reportes y están afectados por el sesgo de registro. Segundo, las tasas sociales provienen de capas agregadas cuyo cálculo rara vez se verifica contra las cifras oficiales. Tercero, la estabilidad de la priorización se examina frente a pocos supuestos y casi nunca frente a la incertidumbre muestral de los reportes.'),
('p', 'Este estudio examina cómo cambia la prioridad parroquial de preparación ante inundaciones en Quito cuando, a la superficie susceptible ponderada por la lluvia estacional, se incorpora la privación por necesidades básicas insatisfechas (NBI) y otras carencias de servicios. Mantenemos separadas las escalas de cada fuente (píxel construido de 10 m, celda meteorológica y parroquia censal) y evaluamos la regla bajo distintos modelos, escenarios de lluvia, umbrales, presupuestos, unidades de medida y muestras de reportes.'),
('p', 'Hacemos cuatro contribuciones. (i) Proponemos una regla de priorización reproducible que separa la localización susceptible del criterio distributivo. (ii) Recalculamos el NBI por hogar desde microdatos del Censo 2022, lo verificamos contra las cifras del INEC y documentamos una inconsistencia de agregación en la capa municipal de sectores divididos entre parroquias, que altera las tasas de 28 parroquias. (iii) Cuantificamos la incertidumbre del ranking mediante 300 remuestreos por bloques de los reportes y la distinguimos de la sensibilidad a la especificación. (iv) Evaluamos la capacidad de discriminación del modelo dentro del área construida, donde se aplica la priorización, con particiones temporal y espacial y con 2 572 eventos de una fuente municipal independiente.'),
('p', 'Incorporar el NBI cambia dos de las 13 parroquias seleccionadas, pero solo cuatro (Guamaní, La Ecuatoriana, Conocoto y Amaguaña) permanecen entre las prioritarias frente a modelo, lluvia y muestra de reportes. La capacidad del modelo para discriminar dentro del construido es modesta: la mayor parte de su desempeño proviene de separar lo construido de lo no construido. Por ello interpretamos el resultado como un orden relativo de revisión y no como una probabilidad de inundación.'),
('p', 'El artículo se organiza así. La sección 2 describe los datos y los métodos, la sección 3 presenta los resultados, la sección 4 discute implicaciones y limitaciones y la sección 5 concluye. El material suplementario detalla el modelo, la verificación del NBI y las pruebas adicionales.'),
('h1', '2 Datos y métodos'),
('h2', '2.1 Área de estudio y datos'),
('p', 'El área de estudio es el Distrito Metropolitano de Quito, con 65 parroquias (32 urbanas y 33 rurales). La tabla 1 reúne las fuentes con su referencia temporal y su soporte, para no tratar resoluciones distintas como observaciones equivalentes.'),
('tab', 'tab1'),
('p', 'Los eventos proceden de 331 reportes de inundación del Servicio Nacional de Gestión de Riesgos (SNGR) de 2010 a septiembre de 2025, depurados por fecha, posición y duplicados (SNGR, s. f.). El construido proviene de ESA WorldCover 2021 a 10 m (Zanaga et al., 2022); el relieve, de Copernicus DEM y FABDEM a unos 30 m (Copernicus, s. f.; Hawker et al., 2022); y las vías, del Plan de uso y gestión del suelo 2024 (Municipio del Distrito Metropolitano de Quito, 2024). Todo se integra en una malla de 10 m (EPSG:32717) sin interpolar el relieve, que conserva su soporte de 30 m. El análisis cubre 2 993 619 píxeles construidos con covariables válidas (29 936.19 ha); se excluyen 28 776 píxeles (287.76 ha) por falta de covariables y 14.95 % del construido requiere acotar alguna covariable al soporte de entrenamiento. La figura 1 muestra el construido analizado y su decil superior de susceptibilidad.'),
('fig', 'fig1'),
('h2', '2.2 Susceptibilidad territorial'),
('p', 'La susceptibilidad se modela como la intensidad relativa de reportes con un proceso puntual de solo presencias, que no trata los puntos de cuadratura como sitios no inundados (Warton & Shepherd, 2010). Cada reporte se representa con 25 posiciones dentro de un radio supuesto de 100 m para incorporar su incertidumbre de localización. El score de un punto con covariables x es'),
('eq', 'eq_f', 1),
('p', 'donde el primer término es un ancla loglineal con coeficientes fijos, g es una red de dos capas ocultas (16 y 8 neuronas, activación SiLU, dropout 0.10) que corrige el ancla, B limita la amplitud de la corrección (0.25 o 1.0) y C(x) acota las covariables continuas a los cuantiles 0.005 y 0.995 del fondo de entrenamiento. La densidad relativa, normalizada con la media de la intensidad sobre 60 000 puntos de cuadratura del fondo, es'),
('eq', 'eq_rho', 2),
('p', 'de modo que su media en el fondo es uno. Esa magnitud describe la concentración relativa de reportes y no una probabilidad de inundación.'),
('p', 'El ancla se ajusta con una penalización L2 y un temperado seleccionados por calibración; la red se entrena sobre el ancla congelada con tres semillas, lo que produce 48 redes entre cuatro conjuntos de covariables, dos protocolos y dos cotas. La variante aplicada al mapa (temporal, con vías y FABDEM, B = 0.25) se fijó después de examinar versiones anteriores, por lo que la evaluación es retrospectiva y no una prueba prospectiva ciega. El material suplementario (secciones S1 a S4) detalla las 25 covariables, el entrenamiento y las particiones.'),
('h2', '2.3 Escenarios de lluvia'),
('p', 'El estado húmedo se define como un acumulado trimestral de precipitación que supera el percentil 80 histórico de la estación. Para noviembre de 2026 a enero de 2027 se combinan observaciones de lluvia CHIRPS3 (Funk et al., 2026; Climate Hazards Center, s. f.) y de temperatura superficial del mar (Climate Prediction Center, s. f.-a) hasta agosto de 2026 para estimar la probabilidad P del estado húmedo en cada una de 186 celdas meteorológicas j. Se comparan tres modelos: uno estacional con ENSO, la climatología calibrada y el conjunto multimodelo NMME con ajuste local (Kirtman et al., 2014; Becker & van den Dool, 2016; Climate Prediction Center, s. f.-b), con la emisión congelada al 9 de octubre de 2026. La relación entre ENSO y precipitación difiere entre la Costa y los Andes (Recalde-Coronel et al., 2014) y las evaluaciones de precipitación en Ecuador muestran diferencias por topografía (Iza-Wong et al., 2026; Huber Magoffin et al., 2023; Arechúa-Mazón et al., 2025); por ello la lluvia se usa como contexto de preparación y se conservan las tres alternativas. P pondera la superficie susceptible y no es una probabilidad de inundación del píxel.'),
('h2', '2.4 Privación social'),
('p', 'El NBI sigue la metodología del INEC (2024): un hogar presenta NBI si acumula al menos una de cinco privaciones (dependencia económica, asistencia escolar de niños de 6 a 12 años, características físicas de la vivienda, servicios básicos y hacinamiento), con los umbrales de la tabla S6. Sea c la indicadora de que el hogar h presenta la privación k (1 si la presenta y 0 en caso contrario). El hogar tiene NBI si acumula al menos una privación y NBI extremo si acumula al menos dos:'),
('eq', 'eq_nbi', 3),
('p', 'La tasa parroquial de hogares con NBI, que es la medida principal, y la de personas, que pondera por el tamaño m del hogar, son'),
('eq', 'eq_tasa', 4),
('p', 'donde N es el número de hogares de la parroquia p. Usamos hogares como medida principal porque es la unidad en que el INEC define el indicador y porque el área que se pondera es de construido; las personas se reportan como sensibilidad.'),
('p', 'Las tasas se recalcularon desde microdatos del Censo 2022 (5 188 827 hogares en el país y 873 512 en Quito) y se asignaron a la parroquia mediante el código de sector censal de la capa municipal de sectores (Municipio del Distrito Metropolitano de Quito, s. f.-b). La capa municipal de parroquias (s. f.-a) publica tasas ya agregadas, pero su comparación con los microdatos mostró una inconsistencia: en 41 sectores divididos entre dos o tres parroquias, la capa registra hogares y hogares con NBI multiplicados por n³, donde n es el número de partes, mientras su población coincide con la de los microdatos. En los 7 136 sectores no divididos, los hogares coinciden exactamente y los hogares con NBI coinciden en 7 130 (diferencia de un hogar en los seis restantes). Para los sectores divididos repartimos los hogares de los microdatos entre las partes según su población (0.7 % de los hogares) y excluimos 93 hogares sin sector en la capa. La corrección modifica las tasas de 28 parroquias, con una diferencia media de 0.36 puntos porcentuales y máxima de 5.95 (La Libertad, 24.96 % frente a 19.01 %), y no cambia las 13 parroquias prioritarias.'),
('p', 'El recálculo coincide con las cifras publicadas por el INEC (2024): a nivel nacional, 1 925 025 hogares (37.1 %) y 6 713 143 personas (39.8 %) con NBI frente a 1 925 141 y 6 713 750 publicados, y en el cantón Quito 367 058 personas (13.7 %) frente a 367 089. En cambio, la suma de las parroquias de la capa municipal da 390 464 personas con NBI, 23 375 más que la cifra del INEC, de las cuales 23 550 se concentran en los sectores divididos (tabla S7).'),
('p', 'Además del NBI, usamos como objetivos separados el NBI extremo y los porcentajes de acceso insuficiente a saneamiento, acceso limitado a agua segura y hogares con hacinamiento de la capa municipal, reponderados con el mismo criterio en los sectores divididos. Cada porcentaje conserva su denominador y no se suma con los demás, porque sus componentes pueden solaparse con el NBI. La tabla 2 resume las 65 parroquias y la figura 2 mapea cada dimensión.'),
('tab', 'tab2'),
('fig', 'fig2'),
('h2', '2.5 Regla de priorización'),
('p', 'Sea S el área en hectáreas del decil superior de susceptibilidad del construido en la parroquia p y la celda meteorológica j, P la probabilidad del estado húmedo y n la proporción parroquial de hogares con NBI. Definimos'),
('eq', 'eq_HI', 5),
('p', 'H expresa hectáreas susceptibles ponderadas por probabilidad húmeda e I incorpora la privación y conserva la unidad de hectáreas ponderadas. Para los objetivos de saneamiento, agua, hacinamiento y NBI extremo se sustituye n por la tasa correspondiente. Las tasas no intervienen en el entrenamiento territorial, de modo que el índice separa localización susceptible y criterio distributivo.'),
('p', 'Seleccionamos las 13 primeras parroquias de cada ordenamiento como presupuesto ilustrativo. Medimos el acuerdo entre la selección por H (A) y la selección por I (B) con el índice de Jaccard (Jaccard, 1912),'),
('eq', 'eq_jac', 6),
('p', 'y comparamos el índice social y el área ponderada que cubre cada selección. Un presupuesto real requeriría costos, población localizada y capacidad de ejecución; aquí sirve para hacer explícito el intercambio entre extensión y privación.'),
('h2', '2.6 Robustez y validación'),
('p', 'Evaluamos la estabilidad de la selección frente a seis fuentes de variación: (i) el modelo territorial (ancla y ancla con red) y el modelo de lluvia (tres alternativas), que dan seis combinaciones; (ii) el percentil que define el área prioritaria (80, 90 y 95); (iii) el presupuesto (5, 10, 13 y 20 parroquias); (iv) la unidad del NBI (hogares y personas), con la correlación de rangos de Spearman (1904); (v) la escala del NBI, ponderando por la tasa del sector censal en lugar de la parroquial; y (vi) la muestra de reportes. Para (vi) remuestreamos con reemplazo los bloques de 5 km de los 143 reportes de entrenamiento (Efron, 1979; Künsch, 1989), reajustamos el ancla con la penalización y el temperado publicados y repetimos la priorización. Con T el conjunto de las 13 parroquias con mayor índice en la réplica b, la probabilidad de pertenencia de la parroquia p es'),
('eq', 'eq_boot', 7),
('p', 'con B = 300 réplicas. La capacidad de discriminación se evalúa con las particiones temporal (143, 88 y 100 reportes para entrenamiento, calibración y prueba) y espacial (85, 48 y 58; bloques de 5 km y franja de borde de 250 m), con una validación que deja fuera un bloque de 5 km cada vez (331 reportes, 55 bloques) y con eventos de inundación del COE municipal (Municipio del Distrito Metropolitano de Quito, s. f.-c), asignados al píxel construido más cercano (máximo 50 m). Para un reporte i, con V el conjunto de sus posiciones válidas y ρ la densidad normalizada de la ecuación (2), la log densidad relativa y la captura del 10 % superior son'),
('eq', 'eq_met', 8),
('p', 'donde q es el cuantil 0.9 de ρ en el fondo. La separación responde al riesgo de dependencia entre muestras próximas (Roberts et al., 2017) y las puntuaciones se interpretan como reglas de puntuación (Gneiting & Raftery, 2007), distintas de la exactitud de agua segmentada. Como la priorización se aplica solo al construido, repetimos la evaluación dentro de estratos de densidad construida, donde el fondo se restringe al mismo estrato. Las pruebas posestimación del ancla (colinealidad, estabilidad e influencia de los coeficientes, localización, hiperparámetros, estabilidad por año y dependencia espacial) se reportan en la sección S8.'),
('h1', '3 Resultados'),
('h2', '3.1 Prioridades por área y por NBI'),
('p', 'La figura 3 compara la distribución de H con el índice social en el escenario principal (red residual y modelo estacional con ENSO). De las 13 parroquias elegidas con cada criterio, 11 son comunes (Jaccard de 0.733): Pomasqui y Tumbaco ingresan en lugar de Iñaquito y Kennedy. La selección por NBI aumenta 1.48 % el índice social cubierto (de 114.98 a 116.68) y reduce 3.10 % el área ponderada por lluvia (de 1 072.61 a 1 039.32 ha ponderadas).'),
('fig', 'fig3'),
('p', 'La privación cambia el orden entre territorios con superficies ponderadas amplias (tabla 3). Guamaní tiene H de 131.58 ha ponderadas, inferior a Calderón y Turubamba, pero su NBI de 14.34 % lleva el índice a 18.87 y lo sitúa en primer lugar; Amaguaña pasa del lugar 13 por H al quinto, con 39.72 ha ponderadas y una tasa de 24.01 %. Tumbaco ocupa el lugar 22 por H y Pomasqui el 19, pero sus tasas de 15.55 % y 12.89 % les permiten ingresar. El cambio no corresponde a una nueva estimación de superficie susceptible: surge al valorar esa superficie con otro objetivo. Estos resultados describen prioridad conjunta y no una clasificación por pobreza: una parroquia puede tener NBI elevado y poca superficie seleccionada, o NBI moderado y una base susceptible amplia.'),
('tab', 'tab3'),
('h2', '3.2 Objetivos sociales alternativos'),
('p', 'La magnitud del cambio depende de la necesidad social que se prioriza (tabla 4). El saneamiento produce la mayor redistribución: conserva ocho de las 13 parroquias e incorpora cinco (El Condado, Alangasí, Llano Chico, Pomasqui y Tumbaco; Jaccard de 0.444). El agua incorpora dos (Pomasqui y Tumbaco) y el hacinamiento dos (Centro Histórico y El Condado). El NBI extremo conserva diez e incorpora tres (Tumbaco, Centro Histórico y El Condado, en lugar de San Bartolo, Iñaquito y Kennedy; Jaccard de 0.625). Mantener los objetivos separados permite reconocer que atienden necesidades distintas y evita sumar indicadores con denominadores y componentes superpuestos.'),
('tab', 'tab4'),
('h2', '3.3 Estabilidad e incertidumbre'),
('p', 'Siete parroquias (Guamaní, La Ecuatoriana, Quitumbe, Amaguaña, Conocoto, Pomasqui y San Antonio) permanecen en la selección por NBI en las seis combinaciones de modelo territorial y lluvia; Calderón, Turubamba, Chillogallo, Solanda y Tumbaco aparecen en cuatro y San Bartolo en dos (figura 4). El ancla sola y el ancla con red producen las mismas 13 parroquias en las tres lluvias (Spearman de al menos 0.9997) y los deciles de ambos modelos tienen un Jaccard de 0.983.'),
('fig', 'fig4'),
('p', 'El presupuesto y el umbral modifican el margen. Con el decil superior, introducir NBI cambia una parroquia con presupuesto de cinco (Amaguaña reemplaza a Quitumbe) y de 10, dos con 13 y cinco con 20. Con presupuesto de 13, produce dos sustituciones con el 20 % superior del construido y cuatro con el 5 % superior. Medir el NBI en personas en lugar de hogares conserva 12 de las 13 parroquias (con personas ingresa El Condado en lugar de Pomasqui; Spearman de 0.998), y en las seis combinaciones la coincidencia es de 12 o 13 parroquias (Spearman de al menos 0.997).'),
('p', 'La escala del NBI también modifica el margen. Al asignar cada píxel construido a su sector censal (7 221 sectores; figura S4), el NBI medio ponderado por el área prioritaria es 9.36 %, frente a 10.55 % con la tasa parroquial, y las diferencias dentro de las parroquias van de −33 a +31 puntos porcentuales. En el escenario principal coinciden 11 de las 13 parroquias (Centro Histórico y El Condado reemplazan a Pomasqui y Tumbaco; Spearman de 0.988) y con la climatología coinciden las 13. La incorporación de Pomasqui y Tumbaco depende, por tanto, de medir la privación a escala parroquial.'),
('p', 'La incertidumbre muestral es mayor que la sensibilidad a la especificación (figura 5). Siete parroquias (Calderón, Guamaní, Turubamba, La Ecuatoriana, Chillogallo, Conocoto y Amaguaña) están entre las 13 primeras en más del 90 % de las réplicas y cuatro entre 50 % y 90 % (Quitumbe, San Antonio, Tumbaco y Solanda); Pomasqui aparece en 46 % y El Condado en 43 %. Pomasqui y Tumbaco ingresan por NBI en 23 % y 34 % de las réplicas. Solo cuatro parroquias (Guamaní, La Ecuatoriana, Conocoto y Amaguaña) son estables frente a modelo, lluvia y muestra.'),
('fig', 'fig8'),
('h2', '3.4 Capacidad de discriminación del modelo territorial'),
('p', 'La tabla 5 resume la evidencia. Con el fondo territorial completo, el ancla alcanza 1.960 de log densidad y 86.8 % de captura en la prueba temporal y 1.095 y 63.9 % en la espacial. La red residual no mejora de forma uniforme sobre el ancla (1.963 y 1.070 en la variante aplicada) y el resultado depende de cómo se seleccionan la penalización y el temperado: una búsqueda conjunta sobre la misma grilla elige otro ancla, con mayor calibración y menor log densidad de prueba (1.878 frente a 1.960; sección S4). Las pruebas posestimación (sección S8) indican que el desempeño descansa en tres covariables (relieve local, construido a 100 m y distancia a vías), que ningún bloque de entrenamiento lo determina y que la captura anual con eventos del COE está entre 16.3 % y 30.0 % sin tendencia significativa.'),
('p', 'Cuando la evaluación se restringe al construido, la discriminación cae. Dentro de las áreas con construido alto, donde cae la mayoría de los reportes (95 de 100 en la prueba temporal y 48 de 58 en la espacial), la log densidad baja a 0.33 y −0.10 y la captura del 10 % del estrato es 19.9 % y 14.1 %. Con los eventos del COE posteriores al período de entrenamiento (659 eventos de 2022 a mayo de 2024), el 19.1 % cae en el 10 % superior del construido (IC 95 %: 12.0 a 26.0 %), frente a 10 % por azar, y la log densidad relativa es 0.03 (de −0.18 a 0.19). Un modelo de tres variables de construido y vías iguala al completo en la prueba temporal (1.905 y 88.0 %) y uno solo físico no se distingue del azar con los eventos del COE (12.4 %). Por último, el modelo ordena pero su intensidad no está calibrada fuera del ajuste: en el decil superior se observa 86.8 % de los reportes temporales frente a 91.5 % esperado, y 63.9 % de los espaciales frente a 90.4 %.'),
('tab', 'tab5'),
('h1', '4 Discusión'),
('h2', '4.1 Implicaciones para la preparación'),
('p', 'Los resultados indican que la preparación depende del objetivo social elegido aun cuando la información física se mantenga constante, en línea con la integración de vulnerabilidad y exposición de Fox et al. (2024) y Rentschler et al. (2022). Incorporar el NBI no reemplaza el criterio de extensión: lo complementa y hace visibles los márgenes donde cambia la decisión. El saneamiento produce la mayor redistribución, lo que sugiere conservar dimensiones específicas junto con el NBI agregado, porque una preparación dirigida a servicios requiere conocer qué carencia guía la atención.'),
('p', 'La estabilidad debe leerse con dos criterios. Siete parroquias son estables frente a modelo y lluvia y otras siete frente a la muestra de reportes; solo cuatro cumplen ambos y constituyen un conjunto inicial razonable para la revisión territorial. Las incorporaciones por NBI (Pomasqui y Tumbaco) y la salida de Iñaquito y Kennedy son resultados de margen, sensibles a la muestra y a la escala del NBI, y deben comunicarse como tales.'),
('p', 'La evidencia económica ecuatoriana sugiere por qué las prioridades deben considerar condiciones de respuesta y no solo exposición: las respuestas a los choques de lluvia difieren por actividad y condición laboral (Canavire-Bacarreza et al., 2026), se acumulan con la recurrencia (Llerena Pinto et al., 2025) y pueden extenderse al capital humano (Rosales-Rueda, 2018). Nuestro cruce censal no observa ingresos ni composición laboral dentro del decil, por lo que esa vía queda como motivación para vincular observaciones de hogares en episodios nuevos y no como estimación de pérdidas.'),
('p', 'La evaluación debe distinguirse de la segmentación de agua observada por satélite (Misra et al., 2025; Tellman et al., 2021) y de la modelación física (Bentivoglio et al., 2022). Nuestro resultado concierne a la concentración relativa de reportes y no a la extensión, la profundidad o los daños; una validación física independiente en Quito requeriría referencias pre, durante y post compatibles.'),
('h2', '4.2 Limitaciones'),
('p', 'Primero, la muestra de reportes es pequeña (331, con pruebas de 100 y 58) y refleja también el acceso al registro, por lo que los intervalos son anchos y el mapa puede describir parcialmente dónde se reporta. Segundo, la evaluación es retrospectiva: la cobertura de 2021, la vialidad de 2024 y el Censo 2022 no certifican las condiciones de cada reporte, la variante aplicada se fijó después de examinar versiones anteriores y los modelos simples de la tabla S4 se definieron después de observar la prueba. Tercero, el NBI es una tasa agregada que no identifica qué hogar reside en un píxel susceptible (Robinson, 1950), y el reparto de los sectores divididos por población es una aproximación que afecta a 0.7 % de los hogares. Cuarto, el COE y el SNGR pueden compartir eventos, de modo que la validación con el COE es solo parcialmente independiente. Quinto, la lluvia se resuelve en celdas meteorológicas gruesas y el relieve conserva un soporte de 30 m dentro de una malla de 10 m. Por último, el estudio no estima extensión inundada, profundidad, daños ni personas afectadas.'),
('h1', '5 Conclusiones'),
('p', 'Este estudio evaluó cómo cambia la prioridad parroquial de preparación ante inundaciones en Quito al incorporar la privación social. Incorporar el NBI por hogar cambia dos de las 13 parroquias seleccionadas y aumenta 1.48 % el índice social cubierto a cambio de reducir 3.10 % el área ponderada por lluvia; el saneamiento produce una redistribución mayor que el NBI total.'),
('p', 'El resultado debe leerse con su incertidumbre. La cabeza del ranking es robusta (Guamaní, La Ecuatoriana, Conocoto y Amaguaña son estables frente a modelo, lluvia y muestra), mientras que las incorporaciones por NBI dependen de la muestra de reportes y de la escala con que se mide la privación. El NBI recalculado desde microdatos coincide con el INEC y corrige una inconsistencia que afectaba a 28 parroquias sin cambiar las 13 prioritarias.'),
('p', 'La capacidad del modelo para discriminar dentro del construido es modesta, de modo que la priorización es un orden relativo de revisión y no una probabilidad de inundación. Los pasos siguientes son validar con fuentes de eventos independientes y con observaciones físicas, medir la privación a escala de sector y vincular observaciones de hogares y servicios antes y después de episodios nuevos.'),
]
DECLARACIONES = [
('Disponibilidad de datos y código', 'Las tablas derivadas, los pesos del modelo, las matrices de entrenamiento y los scripts que reproducen todos los resultados (incluidos el recálculo del NBI, su verificación contra el INEC y las pruebas de robustez) se entregan con el manuscrito y una auditoría automática de sus cifras. Los derivados de FABDEM conservan la licencia CC BY-NC-SA 4.0 y las demás fuentes sus términos. Los microdatos del Censo 2022 se obtienen del INEC y no se redistribuyen registros de hogares.'),
('Financiamiento', '[Completar]'),
('Conflicto de intereses', '[Completar]'),
('Contribución de los autores (CRediT)', '[Completar]'),
('Uso de inteligencia artificial generativa', 'En la preparación del código, el recálculo y la verificación de indicadores, las pruebas de robustez y la revisión y reestructuración del manuscrito se utilizó un asistente de inteligencia artificial generativa. Los autores revisaron y editaron el contenido y asumen la responsabilidad de la publicación. [Confirmar o ajustar esta declaración.]'),
]
# =====================================================================  UTILIDADES
NB = ' '
def nbsp_numbers(t):  # separador de miles con espacio duro
    return re.sub(r'(?<=\d) (?=\d{3}(?!\d))', NB, t)
def key(t): return unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
d = docx.Document(SRC)
paras = d.paragraphs
def find(prefix): 
    r = [p for p in paras if p.text.strip().startswith(prefix)]; assert len(r) == 1, (prefix, len(r)); return r[0]
body = list(d.element.body.iterchildren()); sect = body[-1]; assert sect.tag == W('sectPr')
def eq_text(el): return ''.join(el.xpath('.//m:t/text()'))
def clone(tpl_p, text):
    new = copy.deepcopy(tpl_p._p)
    for el in new.xpath('.//w:lastRenderedPageBreak'): el.getparent().remove(el)
    p = Paragraph(new, tpl_p._parent)
    for r in p.runs[1:]: r._r.getparent().remove(r._r)
    p.runs[0].text = nbsp_numbers(text); return new
title_tpl, author_tpl, jel_tpl = paras[0], paras[1], paras[2]
h1_tpl = [p for p in paras if p.text.strip() == 'Resumen'][0]; h2_tpl = find('2.1 Datos climáticos y territoriales')
body_tpl = find('Los resultados muestran una mejora puntual de la red residual'); cap_tpl = find('Tabla 5. Particiones de evaluación'); note_tpl = find('Fuente: particiones congeladas de reportes.')
ref_tpl = find('Elfwing, S.')
tbl_tpl = [t for t in d.tables if t.rows[0].cells[0].text.strip() == 'Protocolo'][0]._tbl
def block_after(caption_prefix, n_following):
    cap = find(caption_prefix)._p; els = [cap]; cur = cap
    for _ in range(n_following): cur = cur.getnext(); els.append(cur)
    return els
KEEP = {}
for k in (1, 2, 3, 4): KEEP[f'tab{k}'] = block_after(f'Tabla {k}.', 2)           # título, tabla, nota
for k in (1, 2, 3, 4, 8): KEEP[f'fig{k}'] = block_after(f'Figura {k}.', 2)         # título, imagen, nota
EQ = {}
for el in body:
    if el.xpath('.//m:oMath'):
        t = eq_text(el)
        if t.startswith('fθ(x)'): EQ['eq_f'] = el
        elif t.startswith('ρθ(x)'): EQ['eq_rho'] = el
        elif t.startswith('Hp'): EQ['eq_HI'] = el
assert set(EQ) == {'eq_f', 'eq_rho', 'eq_HI'}, EQ.keys()
# ---------- ecuaciones nuevas ----------
RPR = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'; CT = f'<m:ctrlPr>{RPR}</m:ctrlPr>'
def r(t): return f'<m:r>{RPR}<m:t xml:space="preserve">{escape(t)}</m:t></m:r>'
def sub(b, s): return f'<m:sSub><m:sSubPr>{CT}</m:sSubPr><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>'
def sup(b, p): return f'<m:sSup><m:sSupPr>{CT}</m:sSupPr><m:e>{b}</m:e><m:sup>{p}</m:sup></m:sSup>'
def subsup(b, s, p): return f'<m:sSubSup><m:sSubSupPr>{CT}</m:sSubSupPr><m:e>{b}</m:e><m:sub>{s}</m:sub><m:sup>{p}</m:sup></m:sSubSup>'
def frac(n, dn): return f'<m:f><m:fPr>{CT}</m:fPr><m:num>{n}</m:num><m:den>{dn}</m:den></m:f>'
def summ(lower, upper, b):
    hide = '' if upper else '<m:supHide m:val="1"/>'
    return f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="subSup"/>{hide}{CT}</m:naryPr><m:sub>{lower}</m:sub><m:sup>{upper or ""}</m:sup><m:e>{b}</m:e></m:nary>'
ind = lambda b: r('1[') + b + r(']')
def omath_par(inner):
    return etree.fromstring(f'<w:p xmlns:w="{WNS}" xmlns:m="{MNS}"><w:pPr><w:jc w:val="center"/></w:pPr><m:oMathPara><m:oMath>{inner}</m:oMath></m:oMathPara></w:p>')
def numbered(par_el, n):
    t = etree.fromstring(f'<w:tbl xmlns:w="{WNS}"><w:tblPr><w:tblW w:w="9072" w:type="dxa"/><w:tblLayout w:type="fixed"/></w:tblPr><w:tblGrid><w:gridCol w:w="8172"/><w:gridCol w:w="900"/></w:tblGrid>'
        f'<w:tr><w:tc><w:tcPr><w:tcW w:w="8172" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr></w:tc><w:tc><w:tcPr><w:tcW w:w="900" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
        f'<w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:t>({n})</w:t></w:r></w:p></w:tc></w:tr></w:tbl>')
    p = copy.deepcopy(par_el)
    pPr = p.find(W('pPr'))
    if pPr is None: pPr = etree.SubElement(p, W('pPr')); p.insert(0, pPr)
    jc = pPr.find(W('jc'))
    if jc is None: jc = etree.SubElement(pPr, W('jc'))
    jc.set(W('val'), 'center')
    t.xpath('./w:tr/w:tc', namespaces={'w': WNS})[0].append(p); return t
NEW_EQ = {
 'eq_nbi': omath_par(sub(r('NBI'), r('h')) + r(' = ') + ind(summ(r('k=1'), r('5'), sub(r('c'), r('hk'))) + r(' ≥ 1')) + r(',      ') + subsup(r('NBI'), r('h'), r('ext')) + r(' = ') + ind(summ(r('k=1'), r('5'), sub(r('c'), r('hk'))) + r(' ≥ 2'))),
 'eq_tasa': omath_par(sub(r('n'), r('p')) + r(' = ') + frac(summ(r('h∈p'), '', sub(r('NBI'), r('h'))), sub(r('N'), r('p'))) + r(',      ') + sup(sub(r('n'), r('p')), r('pers')) + r(' = ') + frac(summ(r('h∈p'), '', sub(r('m'), r('h')) + sub(r('NBI'), r('h'))), summ(r('h∈p'), '', sub(r('m'), r('h'))))),
 'eq_jac': omath_par(r('J(A,B) = ') + frac(r('|A ∩ B|'), r('|A ∪ B|'))),
 'eq_boot': omath_par(sub(r('P'), r('p')) + r(' = ') + frac(r('1'), r('B')) + summ(r('b=1'), r('B'), ind(r('p ∈ ') + sup(r('T'), r('(b)'))))),
 'eq_met': omath_par(sub(r('S'), r('i')) + r(' = ln') + r('(') + frac(r('1'), r('|') + sub(r('V'), r('i')) + r('|')) + summ(r('v∈') + sub(r('V'), r('i')), '', r('ρ') + r('(') + sub(r('x'), r('iv')) + r(')')) + r(')') + r(',      ') + sub(r('C'), r('i')) + r(' = ') + frac(r('1'), r('|') + sub(r('V'), r('i')) + r('|')) + summ(r('v∈') + sub(r('V'), r('i')), '', ind(r('ρ') + r('(') + sub(r('x'), r('iv')) + r(') ≥ q')))),
}
def eq_el(k, n): return numbered(NEW_EQ[k] if k in NEW_EQ else EQ[k], n)
# ---------- tablas ----------
def make_table(widths, header, rows):
    t = copy.deepcopy(tbl_tpl); trs = t.xpath('./w:tr'); hdr, dat = copy.deepcopy(trs[0]), copy.deepcopy(trs[1])
    for tr in trs: t.remove(tr)
    grid = t.find(W('tblGrid'))
    for g in list(grid): grid.remove(g)
    for w in widths: etree.SubElement(grid, W('gridCol')).set(W('w'), str(w))
    def build(tpl_tr, vals):
        tr = copy.deepcopy(tpl_tr); tcs = tr.xpath('./w:tc'); tc0 = copy.deepcopy(tcs[0])
        for tc in tcs: tr.remove(tc)
        for w, v in zip(widths, vals):
            tc = copy.deepcopy(tc0); tc.find(W('tcPr')).find(W('tcW')).set(W('w'), str(w))
            ps = tc.xpath('./w:p')
            for ex in ps[1:]: tc.remove(ex)
            p = Paragraph(ps[0], None); rs = p.runs
            for rr in rs[1:]: rr._r.getparent().remove(rr._r)
            rs[0].text = nbsp_numbers(str(v)); tr.append(tc)
        return tr
    t.append(build(hdr, header))
    for row in rows: t.append(build(dat, row))
    return t
def tab5_block():
    cap = clone(cap_tpl, 'Tabla 5. Evidencia sobre la capacidad de discriminación del modelo territorial')
    t = make_table([3700, 1700, 1836, 1836], ['Evaluación', 'Muestra', 'Log densidad relativa', 'Captura del 10 % (%)'], [
      ['Prueba temporal, ancla, fondo territorial', '100 reportes; 36 bloques', '1.960', '86.8'],
      ['Prueba espacial, ancla, fondo territorial', '58 reportes; 13 bloques', '1.095', '63.9'],
      ['Dejando un bloque de 5 km fuera, ancla', '331 reportes; 55 bloques', '1.73 (1.36 a 2.00)', '81.6 (74.7 a 86.4)'],
      ['Prueba temporal, dentro del construido alto', '95 reportes', '0.33', '19.9'],
      ['Prueba espacial, dentro del construido alto', '48 reportes', '−0.10', '14.1'],
      ['Eventos del COE de 2022 a mayo de 2024, dentro del construido', '659 eventos', '0.03 (−0.18 a 0.19)', '19.1 (12.0 a 26.0)']])
    nt = clone(note_tpl, 'Fuente: evaluación del estudio y eventos de inundación del COE municipal. Elaboración propia. Azar: log densidad 0 y captura 10 %. Intervalos del 95 %: bootstrap por bloques de 5 km. Las pruebas dentro del construido restringen el fondo al mismo estrato de densidad construida. Detalles en las secciones S3, S4 y S6.')
    return [cap, t, nt]
# =====================================================================  ENSAMBLE DEL ARTÍCULO
def renum_caption(el, kind, n):
    p = Paragraph(el, None)
    for rr in p.runs:
        if re.match(rf'^{kind} \d+\.', rr.text): rr.text = re.sub(rf'^{kind} \d+\.', f'{kind} {n}.', rr.text, count=1); return
    raise AssertionError(kind)
FIGNUM = {'fig1': 1, 'fig2': 2, 'fig3': 3, 'fig4': 4, 'fig8': 5}
out = []
out.append(clone(title_tpl, TITULO)); out.append(clone(author_tpl, AUTOR)); out.append(clone(jel_tpl, JEL)); out.append(clone(jel_tpl, KEYWORDS))
out.append(clone(h1_tpl, 'Aspectos destacados'))
for h in HIGHLIGHTS: out.append(clone(body_tpl, '• ' + h))
def labelled(text):
    res = []
    for part in re.split(r' (?=(?:Objetivo|Métodos|Resultados|Conclusiones|Objective|Methods|Results|Conclusions)\. )', text):
        label, rest = part.split('. ', 1)
        el = clone(body_tpl, label + '. '); p = Paragraph(el, body_tpl._parent); first = p.runs[0]; first.bold = True
        r2 = p.add_run(nbsp_numbers(rest))
        if first._r.rPr is not None: r2._r.insert(0, copy.deepcopy(first._r.rPr))
        r2.bold = False; res.append(el)
    return res
out.append(clone(h1_tpl, 'Resumen')); out.extend(labelled(RESUMEN))
out.append(clone(h1_tpl, 'Abstract')); out.extend(labelled(ABSTRACT))
for kind, a, *rest in BODY:
    if kind == 'h1': out.append(clone(h1_tpl, a))
    elif kind == 'h2': out.append(clone(h2_tpl, a))
    elif kind == 'p': out.append(clone(body_tpl, a))
    elif kind == 'eq': out.append(eq_el(a, rest[0]))
    elif kind == 'fig':
        els = [copy.deepcopy(e) for e in KEEP[a]]; renum_caption(els[0], 'Figura', FIGNUM[a]); out.extend(els)
    elif kind == 'tab':
        if a == 'tab5': out.extend(tab5_block())
        else: out.extend(copy.deepcopy(e) for e in KEEP[a])
out.append(clone(h1_tpl, 'Declaraciones'))
for t, c in DECLARACIONES: out.append(clone(body_tpl, f'{t}. {c}'))
# ---------- referencias ----------
ALIAS = {'Instituto Nacional de Estadística y Censos': 'INEC', 'Servicio Nacional de Gestión de Riesgos': 'SNGR'}
def ref_key(t):
    m = re.match(r'^(.+?)\. \((\d{4}|s\. f\.(?:-[a-z])?)\)', t)
    if not m: return None
    a = m.group(1); first = a.split(',')[0].strip(); first = ALIAS.get(first, first)
    return first, m.group(2)
i_ref = [i for i, p in enumerate(paras) if p.text.strip() == 'Referencias'][0]
refs_all = [p for p in paras[i_ref + 1:] if p.text.strip()]
NEW_REF_TEXTS = [
 'Belsley, D. A., Kuh, E., & Welsch, R. E. (1980). Regression diagnostics: Identifying influential data and sources of collinearity. Wiley.',
 'Dormann, C. F., Elith, J., Bacher, S., Buchmann, C., Carl, G., Carré, G., García Marquéz, J. R., Gruber, B., Lafourcade, B., Leitão, P. J., Münkemüller, T., McClean, C., Osborne, P. E., Reineking, B., Schröder, B., Skidmore, A. K., Zurell, D., & Lautenbach, S. (2013). Collinearity: A review of methods to deal with it and a simulation study evaluating their performance. Ecography, 36(1), 27-46. https://doi.org/10.1111/j.1600-0587.2012.07348.x',
 'Kish, L. (1965). Survey sampling. Wiley.',
 "O'Brien, R. M. (2007). A caution regarding rules of thumb for variance inflation factors. Quality & Quantity, 41(5), 673-690. https://doi.org/10.1007/s11135-006-9018-6",
 'Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. Journal of the American Statistical Association, 22(158), 209-212. https://doi.org/10.1080/01621459.1927.10502953']
for _t in NEW_REF_TEXTS:
    refs_all.append(Paragraph(clone(ref_tpl, _t), ref_tpl._parent))
def select_refs(text):
    sel = []
    for p in refs_all:
        k = ref_key(p.text)
        if k and re.search(re.escape(k[0]) + r'[^;)]{0,70}?' + re.escape(k[1]), text): sel.append(p)
    return sel
def corpus(els):
    t = []
    for e in els:
        t.append(''.join((x.text or '') for x in e.iter(W('t'))))
    return '\n'.join(t)
text_main = corpus(out)
sel = select_refs(text_main)
out.append(clone(h1_tpl, 'Referencias'))
for p in sel: out.append(copy.deepcopy(p._p))
# ---------- escribir ----------
for el in body[:-1]: d.element.body.remove(el)
for el in out: sect.addprevious(el)
# quitar imágenes huérfanas
doc_xml = etree.tostring(d.element).decode()
for rid, rel in list(d.part.rels.items()):
    if 'image' in rel.reltype and f'"{rid}"' not in doc_xml: d.part.drop_rel(rid)
d.save(OUT_MAIN); print('V21 guardada:', OUT_MAIN, '| referencias:', len(sel))
# ---------- autores: sin la nota "Investigador independiente..." ----------
import zipfile, shutil
def quitar_nota_autor(path):
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/footnotes.xml':
                s = data.decode('utf-8'); s2 = re.sub(r'<w:footnote [^>]*w:id="1"[^>]*>.*?</w:footnote>', '', s, flags=re.S); data = s2.encode('utf-8')
            if item.filename == 'word/document.xml':
                s = data.decode('utf-8'); s = re.sub(r'<w:r>(?:(?!</w:r>).)*?<w:footnoteReference w:id="1"/>(?:(?!</w:r>).)*?</w:r>', '', s, flags=re.S); data = s.encode('utf-8')
            zout.writestr(item, data)
    shutil.move(tmp, path)
quitar_nota_autor(OUT_MAIN)
chk = zipfile.ZipFile(OUT_MAIN); txt = chk.read('word/document.xml').decode('utf-8') + chk.read('word/footnotes.xml').decode('utf-8')
assert 'Investigador independiente' not in txt and 'wilson.morales' not in txt and 'footnoteReference w:id="1"' not in txt
print('nota del autor eliminada de la V21')
