"""B2: validación satelital (Sentinel-1 RTC, Microsoft Planetary Computer) con eventos de inundación del COE.
Para cada adquisición posterior a días con >= 3 eventos (ventana de 0 a 2 días antes de la imagen) se calcula
el cambio de retrodispersión VV frente a la mediana de hasta 6 adquisiciones previas de la misma órbita relativa,
en bloques de 80 m dentro del construido, y se compara (i) los bloques con eventos contra el resto del construido
y (ii) la susceptibilidad (percentil del modelo) contra la caída de retrodispersión.
Uso: PYTHONPATH=<libs> python robustez_b2_sentinel1.py"""
import os, sys, json, numpy as np, pandas as pd, rasterio, warnings
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.transform import Affine
import pystac_client, planetary_computer as pc
warnings.filterwarnings('ignore')
ROOT = '/Users/daniela/Desktop/PAPER INUNDACION'
TIF = f'{ROOT}/11_REPO_MODELO/quito-enso-exposicion-reproducible/REFERENCIA_percentil_construido_red_residual_10m.tif'
CACHE = f'{ROOT}/12_BASES/sentinel1'; os.makedirs(CACHE, exist_ok=True)
OUT = f'{ROOT}/09_ANALISIS_ROBUSTEZ'
F = 8                                            # 10 m -> 80 m (nivel de overview 2 del COG)
# ---- susceptibilidad por bloque
with rasterio.open(TIF) as s:
    A = s.read(1); T0 = s.transform; H, W = s.shape; ND = s.nodata
valid = A != ND
Hb, Wb = H // F, W // F
v = valid[:Hb * F, :Wb * F].reshape(Hb, F, Wb, F)
frac = v.mean(axis=(1, 3))
val = np.where(valid, A, 0).astype('float32')[:Hb * F, :Wb * F].reshape(Hb, F, Wb, F).sum(axis=(1, 3))
perc = np.where(v.sum(axis=(1, 3)) > 0, val / np.maximum(v.sum(axis=(1, 3)), 1), np.nan)
built = frac >= 0.25
bi = np.flatnonzero(built.ravel()); print('bloques construidos', len(bi), 'de', Hb * Wb, flush=True)
perc_b = perc.ravel()[bi]
dst_tr = Affine(10 * F, 0, T0.c, 0, -10 * F, T0.f)
# ---- eventos
ev = pd.read_csv(f'{OUT}/coe_eventos.csv'); ev = ev[ev.tipo_de_ev.str.contains('Inund', na=False)].copy()
ev['f'] = pd.to_datetime(ev.fecha, unit='ms', errors='coerce'); ev = ev.dropna(subset=['f']); ev = ev[ev.f >= '2021-06-01']
ev['dia'] = ev.f.dt.normalize()
ev['col'] = ((ev.x - T0.c) // (10 * F)).astype(int); ev['row'] = ((T0.f - ev.y) // (10 * F)).astype(int)
inb = (ev.row >= 1) & (ev.row < Hb - 1) & (ev.col >= 1) & (ev.col < Wb - 1)
ev = ev[inb].copy()
def asigna(r, c):
    best = None
    for dr in (0, -1, 1):
        for dc in (0, -1, 1):
            if built[r + dr, c + dc]:
                k = abs(dr) + abs(dc)
                if best is None or k < best[0]: best = (k, r + dr, c + dc)
    return None if best is None else (best[1], best[2])
asg = [asigna(r, c) for r, c in zip(ev.row, ev.col)]
ev['bloque'] = [None if a is None else a[0] * Wb + a[1] for a in asg]
ev = ev.dropna(subset=['bloque']); ev['bloque'] = ev.bloque.astype(int)
print('eventos en bloques construidos', len(ev), flush=True)
# ---- escenas
cat = pystac_client.Client.open('https://planetarycomputer.microsoft.com/api/stac/v1', modifier=pc.sign_inplace)
its = list(cat.search(collections=['sentinel-1-rtc'], bbox=[-78.60, -0.35, -78.35, 0.05], datetime='2021-01-01/2024-12-31', max_items=3000).items())
acq = {}
for i in its:
    k = '_'.join(i.id.split('_')[-3:-1]); acq.setdefault(k, []).append(i)
info = {k: dict(t=pd.Timestamp(v[0].datetime).tz_localize(None), orb=v[0].properties.get('sat:relative_orbit')) for k, v in acq.items()}
print('adquisiciones', len(acq), flush=True)
def leer(k):
    f = f'{CACHE}/{k}.npy'
    if os.path.exists(f): return np.load(f)
    acc = np.zeros(Hb * Wb, 'float32'); n = np.zeros(Hb * Wb, 'float32')
    for it in acq[k]:
        try:
            href = it.assets['vv'].href
            with rasterio.open(href, overview_level=2) as src, WarpedVRT(src, crs='EPSG:32717', transform=dst_tr, width=Wb, height=Hb, resampling=Resampling.average, nodata=src.nodata) as vrt:
                a = vrt.read(1, masked=True).astype('float32')
            m = ~np.ma.getmaskarray(a) & (a.filled(0) > 0)
            acc += np.where(m, a.filled(0), 0).ravel(); n += m.ravel()
        except Exception as e:
            print('fallo', it.id, repr(e)[:120], flush=True)
    out = np.where(n > 0, acc / np.maximum(n, 1), np.nan)[bi].astype('float32')
    np.save(f, out); return out
# ---- adquisiciones objetivo
cnt = ev.groupby('dia').size()
def eventos_para(t):
    d0 = t.normalize()
    m = (ev.dia >= d0 - pd.Timedelta(days=2)) & (ev.dia <= d0)
    return ev[m]
objetivo = []
for k, v in info.items():
    e = eventos_para(v['t'])
    if len(e) >= 3 and v['t'] >= pd.Timestamp('2021-11-01'): objetivo.append(k)
objetivo.sort(key=lambda k: info[k]['t']); print('objetivo', len(objetivo), flush=True)
def refs(k):
    t = info[k]['t']; o = info[k]['orb']
    c = [j for j, v in info.items() if v['orb'] == o and t - pd.Timedelta(days=100) <= v['t'] <= t - pd.Timedelta(days=11) and len(eventos_para(v['t'])) < 3]
    return sorted(c, key=lambda j: info[j]['t'])[-6:]
from concurrent.futures import ThreadPoolExecutor
need = set()
for k in objetivo:
    R = refs(k)
    if len(R) >= 3: need.add(k); need.update(R)
need = sorted(need); print('adquisiciones a leer', len(need), flush=True)
def _p(k):
    leer(k); print('leida', k, flush=True)
with ThreadPoolExecutor(6) as ex: list(ex.map(_p, need))
rows, per_block = [], []
for k in objetivo:
    R = refs(k)
    if len(R) < 3: print('sin referencia', k, flush=True); continue
    post = leer(k); ref = np.nanmedian(np.vstack([leer(j) for j in R]), axis=0)
    d = 10 * np.log10(post / ref); ok = np.isfinite(d)
    e = eventos_para(info[k]['t']); pos = {b: p for p, b in enumerate(bi)}
    eb = np.array(sorted({pos[b] for b in e.bloque if b in pos}))
    eb = eb[ok[eb]] if len(eb) else eb
    if len(eb) < 3 or ok.sum() < 1000: continue
    base = d[ok]
    from scipy.stats import spearmanr
    rho = spearmanr(perc_b[ok], d[ok], nan_policy='omit')[0]
    rows.append(dict(adquisicion=k, fecha=str(info[k]['t']), orbita=info[k]['orb'], referencias=len(R), eventos=len(e), bloques_evento=len(eb),
                     delta_evento=float(np.mean(d[eb])), delta_construido=float(np.mean(base)), diferencia=float(np.mean(d[eb]) - np.mean(base)),
                     p_menor3_evento=float(np.mean(d[eb] < -3)), p_menor3_construido=float(np.mean(base < -3)),
                     p_mayor3_evento=float(np.mean(d[eb] > 3)), p_mayor3_construido=float(np.mean(base > 3)),
                     perc_evento=float(np.mean(perc_b[eb])), perc_construido=float(np.nanmean(perc_b)), rho_percentil_delta=float(rho)))
    print(rows[-1]['fecha'], 'ev', len(eb), 'dif %.2f dB' % rows[-1]['diferencia'], 'rho %.3f' % rho, flush=True)
pd.DataFrame(rows).to_csv(f'{OUT}/B2_sentinel1_por_adquisicion.csv', index=False)
print('listo', len(rows))
