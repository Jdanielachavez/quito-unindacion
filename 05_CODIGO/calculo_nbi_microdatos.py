import os
"""NBI por hogar de Quito recalculado desde microdatos del Censo 2022 (BaseFinal) y verificado sector por sector.

Entradas
  - BaseFinal.parquet : una fila por hogar; nbi_hogar y xnbi_hogar calculados con el script R (método INEC, 5 componentes).
  - Capa municipal de sectores censales (geoquito, capa 3): Sector_DMQ (12 dígitos) y parroquia. Se descarga de forma pública.
  - Capa municipal de parroquias (capa 2): solo para comparar.
Salidas (en --salida)
  - nbi_hogar_65_parroquias_microdatos.csv
  - validacion_sector_a_sector.csv
  - sectores_divididos_A_B.csv
Uso: python calculo_nbi_microdatos.py --base BaseFinal.parquet --salida .
"""
import argparse, json, urllib.parse, urllib.request
import numpy as np
import pandas as pd

URL = 'https://geoquito.quito.gob.ec/server/rest/services/web_service/s_nbi_porcentaje_personas_con_pobreza_por_nbi_2022/MapServer/%d/query'

def descargar(capa, campos, orden):
    filas, off = [], 0
    while True:
        q = urllib.parse.urlencode(dict(where='1=1', outFields=campos, returnGeometry='false', orderByFields=orden,
                                        resultOffset=off, resultRecordCount=2000, f='json'))
        with urllib.request.urlopen(URL % capa + '?' + q, timeout=180) as r:
            d = json.load(r)
        feats = [f['attributes'] for f in d.get('features', [])]
        filas += feats
        if len(feats) < 2000: break
        off += 2000
    return pd.DataFrame(filas)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '12_BASES', 'BaseFinal.parquet')); ap.add_argument('--salida', default='.')
    a = ap.parse_args()
    sec = descargar(3, 'OBJECTID,parroquia,nom_par,Sector_DMQ,pobT,total_hog,p_nbi,h_nbi,h_xnbi', 'OBJECTID')
    par = descargar(2, 'parroquia,nom_par,total_hog,pobT,p_nbi,h_nbi,h_xnbi,pc_hnbi,pc_hxnbi,pc_pnbi', 'parroquia')
    sec['parroquia'] = sec.parroquia.astype(str); par['parroquia'] = par.parroquia.astype(str).str.zfill(6)
    d = pd.read_parquet(a.base, columns=['id_hogar', 'cod_canton', 'nbi_hogar', 'xnbi_hogar', 'total_personas'])
    q = d[d.cod_canton == '1701'].copy()
    q['sector'] = q.id_hogar.str[:12]                      # prov(2)+cantón(2)+parroquia(2)+zona(3)+sector(3)
    q['pers_nbi'] = q.total_personas * q.nbi_hogar
    q['pers_xnbi'] = q.total_personas * q.xnbi_hogar
    g = q.groupby('sector').agg(hog=('id_hogar', 'size'), nbi=('nbi_hogar', 'sum'), xnbi=('xnbi_hogar', 'sum'),
                                pers=('total_personas', 'sum'), pnbi=('pers_nbi', 'sum'), pxnbi=('pers_xnbi', 'sum')).reset_index()
    # 1) verificación sector a sector (sectores con código idéntico)
    v = g.merge(sec, left_on='sector', right_on='Sector_DMQ', how='inner')
    v = v[['sector', 'parroquia', 'nom_par', 'hog', 'total_hog', 'nbi', 'h_nbi', 'xnbi', 'h_xnbi', 'pers', 'pobT']]
    v.columns = ['sector', 'parroquia', 'nombre', 'hogares_micro', 'hogares_capa', 'nbi_micro', 'nbi_capa',
                 'nbi_extremo_micro', 'nbi_extremo_capa', 'personas_micro', 'personas_capa']
    v.to_csv(f'{a.salida}/validacion_sector_a_sector.csv', index=False, encoding='utf-8-sig')
    # 2) sectores divididos (sufijo A/B/C en la capa)
    sec['base'] = sec.Sector_DMQ.str[:12]
    div = sec[~sec.Sector_DMQ.isin(set(g.sector))].copy()
    r = div.groupby('base').agg(partes=('Sector_DMQ', 'size'), parroquias=('nom_par', lambda x: ' / '.join(sorted(set(x)))),
                                hogares_capa=('total_hog', 'sum'), nbi_capa=('h_nbi', 'sum'), personas_capa=('pobT', 'sum')).reset_index()
    r = r.merge(g, left_on='base', right_on='sector', how='left')
    r['razon_hogares'] = r.hogares_capa / r.hog
    r['n_partes_al_cubo'] = r.partes ** 3
    r = r.rename(columns={'hog': 'hogares_micro', 'nbi': 'nbi_micro', 'pers': 'personas_micro'})
    r[['base', 'partes', 'parroquias', 'hogares_capa', 'hogares_micro', 'razon_hogares', 'n_partes_al_cubo',
       'nbi_capa', 'nbi_micro', 'personas_capa', 'personas_micro']].to_csv(f'{a.salida}/sectores_divididos_A_B.csv', index=False, encoding='utf-8-sig')
    # 3) parroquias: sectores únicos 100 % + sectores divididos repartidos por población de cada parte
    sec['peso'] = sec.pobT / sec.groupby('base').pobT.transform('sum')
    sec.loc[sec.groupby('base').pobT.transform('sum') == 0, 'peso'] = 1.0 / sec.groupby('base').Sector_DMQ.transform('size')
    j = g.merge(sec[['base', 'parroquia', 'peso']], left_on='sector', right_on='base', how='inner')
    for k in ('hog', 'nbi', 'xnbi', 'pers', 'pnbi', 'pxnbi'): j[k] = j[k] * j.peso
    p = j.groupby('parroquia')[['hog', 'nbi', 'xnbi', 'pers', 'pnbi', 'pxnbi']].sum().reset_index()
    p['pct_hogares_nbi_micro'] = 100 * p.nbi / p.hog
    p['pct_hogares_nbi_extremo_micro'] = 100 * p.xnbi / p.hog
    p['pct_personas_nbi_micro'] = 100 * p.pnbi / p.pers
    out = p.merge(par.rename(columns={'total_hog': 'hogares_capa', 'pc_hnbi': 'pct_hogares_nbi_capa',
                                      'pc_hxnbi': 'pct_hogares_nbi_extremo_capa', 'pc_pnbi': 'pct_personas_nbi_capa'}), on='parroquia')
    out['dif_pct_hogares_nbi_pp'] = out.pct_hogares_nbi_micro - out.pct_hogares_nbi_capa
    out['dif_hogares'] = out.hog - out.hogares_capa
    out = out.rename(columns={'hog': 'hogares_micro', 'nom_par': 'nombre'})
    cols = ['parroquia', 'nombre', 'hogares_micro', 'hogares_capa', 'dif_hogares', 'pct_hogares_nbi_micro', 'pct_hogares_nbi_capa',
            'dif_pct_hogares_nbi_pp', 'pct_hogares_nbi_extremo_micro', 'pct_hogares_nbi_extremo_capa',
            'pct_personas_nbi_micro', 'pct_personas_nbi_capa']
    out[cols].round(4).to_csv(f'{a.salida}/nbi_hogar_65_parroquias_microdatos.csv', index=False, encoding='utf-8-sig')
    print('sectores verificados:', len(v), '| hogares iguales:', int((v.hogares_micro == v.hogares_capa).sum()),
          '| NBI igual:', int((v.nbi_micro == v.nbi_capa).sum()), '| |dif|<=1:', int(((v.nbi_micro - v.nbi_capa).abs() <= 1).sum()))
    print('sectores divididos:', len(r), '| razón hogares == partes^3:', int(np.isclose(r.razon_hogares, r.n_partes_al_cubo, atol=.01).sum()))
    print('parroquias:', len(out), '| dif media abs %.3f pp, máx %.3f pp' % (out.dif_pct_hogares_nbi_pp.abs().mean(), out.dif_pct_hogares_nbi_pp.abs().max()))

if __name__ == '__main__':
    main()
