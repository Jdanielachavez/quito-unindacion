# Hoja de ruta: de un estudio de priorización a un paper más fuerte

Estado de partida (V17): priorización reproducible, NBI verificado contra el INEC, ranking estable. No hay validación física independiente y el NBI es parroquial.

## A. Se puede hacer ya, con los datos que tenemos
| # | Mejora | Qué responde | Cómo | Esfuerzo | Riesgo |
|---|---|---|---|---|---|
| A1 | **Incertidumbre del ranking** | ¿Con qué probabilidad cada parroquia pertenece al top 13? | Bootstrap por bloques de 5 km de los reportes; reajustar el ancla (segundos) y reordenar; 200 a 500 réplicas | Medio | Bajo |
| A2 | **NBI por sector censal dentro de la parroquia** | Quita la limitación "NBI parroquial": ¿los píxeles susceptibles caen en sectores pobres? | Capa municipal de 7 221 sectores con geometría; cruzar con los 2.99 M de píxeles (`flat`, `GRILLA.json`); índice a nivel sector y agregado a parroquia | Medio | Medio (hay que descargar geometrías) |
| A3 | **Validación cruzada dejando una parroquia fuera** | ¿Cuánto se transfiere el modelo entre parroquias? | 65 folds con el ancla (rápido) | Bajo | Bajo |
| A4 | **Referencias simples** | ¿El modelo aporta algo frente a "cerca de quebrada" o "pendiente baja"? | Modelos de 1 a 3 variables en la misma evaluación | Bajo | Bajo |
| A5 | **Sesgo de reporte** | ¿El mapa refleja inundación o dónde se reporta? | Modelo sin vías ni construido, y con submuestreo por densidad; comparar rankings | Bajo | Bajo |
| A6 | **Simplificar el modelo** | La red aporta 0.003; ¿conviene presentar solo el loglineal? | Rehacer mapa y prioridad con el ancla; mostrar que el ranking no cambia | Bajo | Bajo |
| A7 | **Calibración** | ¿Los deciles altos concentran lo que dicen? | Reportes observados vs esperados por decil, en test | Bajo | Bajo |

## B. Requiere datos externos
| # | Mejora | Datos | Nota |
|---|---|---|---|
| B1 | **Validación con fuente independiente** | Eventos de emergencia municipales o ECU911 / Bomberos (la geoportal municipal tiene capas de eventos; hay que revisar su contenido) | Es lo que más fortalece el paper |
| B2 | **Validación satelital** | Sentinel-1 (Misra et al. 2025), Global Flood Database | Limitado en inundación urbana pluvial y relieve andino; declararlo |
| B3 | **Hogares en riesgo** | Viviendas / hogares por sector dentro del decil | Con A2 se puede aproximar sin salir del censo |
| B4 | **Efectos sobre bienestar** | ENEMDU u otra encuesta georreferenciada | Fuera del alcance actual; el repo la excluyó a propósito |

## C. Orden sugerido
1. **A6 + A4 + A7** (rápido): definen qué modelo se presenta y cuánto vale.
2. **A1** (incertidumbre): convierte el ranking en probabilidades.
3. **A2** (NBI por sector): resuelve la limitación más visible.
4. **A3 y A5**: robustez del modelo físico.
5. **B1**: si se consigue una fuente independiente.

## D. Cómo cambiaría el mensaje del paper
De: "la prioridad cambia al incorporar NBI" (parroquial, 13 de 65).
A: "con incertidumbre cuantificada, estas parroquias y sectores son prioritarios por exposición y privación, y el resultado no depende de la complejidad del modelo".

## E. Estado
- **Hecho:** A1, A2, A3, A4, A5, A6, A7 y B1 (`09_ANALISIS_ROBUSTEZ/`; anexo A.6 y sección 3.5 de la V19).
- **Pendiente, requiere datos que no están disponibles:** B2 (validación satelital), B3 (hogares en riesgo por sector, aproximable con A2) y B4 (efectos en bienestar con encuestas).

- [x] Pruebas posestimación (colinealidad, influencia, localización, hiperparámetros, estabilidad anual COE, ICC) → suplemento S8.

- [x] B2 validación satelital con Sentinel-1 (59 adquisiciones, 2021–2024) → suplemento S9; resultado: señal débil en la dirección esperada.
- [x] A2 NBI por sector censal (ya integrado en 3.3); pendiente solo NBI de hogares dentro de cada sector.
