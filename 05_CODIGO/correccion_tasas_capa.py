import os
"""Descomposición del exceso de la capa municipal y reponderación de tasas por parroquia.

Idea: en los sectores divididos (sufijo A/B/C) las tasas de cada parte son correctas, pero sus conteos y universos no
se reparten entre las partes. Se reponderan las partes con los hogares verdaderos del sector (microdatos) y la
participación de población de cada parte.
Entradas: BaseFinal.parquet y la capa pública de sectores censales (geoquito, capa 3).
Salidas: descomposicion_exceso_personas_nbi.csv y tasas_corregidas_65_parroquias.csv
Uso: python correccion_tasas_capa.py --base BaseFinal.parquet --inec-quito 367089 --salida .
"""
import argparse, json, urllib.parse, urllib.request
import numpy as np, pandas as pd

URL = 'https://geoquito.quito.gob.ec/server/rest/services/web_service/s_nbi_porcentaje_personas_con_pobreza_por_nbi_2022/MapServer/3/query'
CAMPOS = 'OBJECTID,Sector_DMQ,parroquia,nom_par,pobT,total_hog,SH,no_SH,FSA,no_FSA,HAC,no_HAC,p_nbi,nop_nbi,h_nbi,noh_nbi'

def descargar():
    filas, off = [], 0
    while True:
        q = urllib.parse.urlencode(dict(where='1=1', outFields=CAMPOS, returnGeometry='false', orderByFields='OBJECTID',
                                        resultOffset=off, resultRecordCount=2000, f='json'))
        with urllib.request.urlopen(URL + '?' + q, timeout=180) as r:
            feats = [f['attributes'] for f in json.load(r)['features']]
        filas += feats
        if len(feats) < 2000: break
        off += 2000
    s = pd.DataFrame(filas)
    for k in CAMPOS.split(',')[4:]: s[k] = pd.to_numeric(s[k], errors='coerce')
    s['parroquia'] = s.parroquia.astype(str)
    return s

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '12_BASES', 'BaseFinal.parquet')); ap.add_argument('--inec-quito', type=int, default=367089)
    ap.add_argument('--salida', default='.')
    a = ap.parse_args()
    s = descargar()
    d = pd.read_parquet(a.base, columns=['id_hogar', 'cod_canton', 'nbi_hogar', 'total_personas'])
    q = d[d.cod_canton == '1701'].copy(); q['sector'] = q.id_hogar.str[:12]; q['pn'] = q.total_personas * q.nbi_hogar
    g = q.groupby('sector').agg(hog=('id_hogar', 'size'), pnbi=('pn', 'sum')).reset_index()
    s['dividido'] = s.Sector_DMQ.str.len() == 13; s['base'] = s.Sector_DMQ.str[:12]
    s = s.merge(g, left_on='base', right_on='sector', how='left')
    # 1) descomposición del exceso de personas con NBI frente al INEC
    norm, div = s[~s.dividido], s[s.dividido]
    micro_div = div.groupby('base').pnbi.first().fillna(0).sum()
    filas = [('capa municipal, suma de 65 parroquias', s.p_nbi.sum()), ('INEC, cantón Quito', a.inec_quito),
             ('exceso capa - INEC', s.p_nbi.sum() - a.inec_quito),
             ('sectores sin división: capa', norm.p_nbi.sum()), ('sectores sin división: microdatos', norm.pnbi.sum()),
             ('sectores divididos: capa', div.p_nbi.sum()), ('sectores divididos: microdatos', micro_div),
             ('exceso en sectores divididos', div.p_nbi.sum() - micro_div),
             ('exceso en sectores sin división', norm.p_nbi.sum() - norm.pnbi.sum()),
             ('microdatos total', g.pnbi.sum()), ('microdatos - INEC', g.pnbi.sum() - a.inec_quito)]
    pd.DataFrame(filas, columns=['concepto', 'personas_con_nbi']).to_csv(f'{a.salida}/descomposicion_exceso_personas_nbi.csv', index=False, encoding='utf-8-sig')
    # 2) tasas por parroquia: publicada (suma de la capa) vs reponderada
    s['pobT_base'] = s.groupby('base').pobT.transform('sum'); s['n'] = s.groupby('base').Sector_DMQ.transform('size')
    s['share'] = np.where(s.pobT_base > 0, s.pobT / s.pobT_base, 1.0 / s.n)
    s['H_true'] = np.where(s.dividido, s.hog.fillna(s.SH + s.no_SH), s.total_hog)
    s['w'] = s.H_true * np.where(s.dividido, s.share, 1.0)
    def corr(num, otro):
        t = s[(s[num] + s[otro]) > 0].copy(); t['rate'] = t[num] / (t[num] + t[otro])
        return t.groupby('parroquia').apply(lambda x: 100 * np.average(x.rate, weights=x.w), include_groups=False)
    def pub(num, otro):
        return s.groupby('parroquia').apply(lambda x: 100 * x[num].sum() / (x[num].sum() + x[otro].sum()), include_groups=False)
    nom = s.groupby('parroquia').nom_par.first()
    out = pd.DataFrame({'nombre': nom})
    for k, (n, o) in {'saneamiento': ('SH', 'no_SH'), 'agua': ('FSA', 'no_FSA'), 'hacinamiento': ('HAC', 'no_HAC')}.items():
        out[f'pct_{k}_capa'] = pub(n, o); out[f'pct_{k}_corregida'] = corr(n, o)
        out[f'dif_{k}_pp'] = out[f'pct_{k}_corregida'] - out[f'pct_{k}_capa']
    out.reset_index().round(4).to_csv(f'{a.salida}/tasas_corregidas_65_parroquias.csv', index=False, encoding='utf-8-sig')
    print('exceso capa - INEC:', int(s.p_nbi.sum() - a.inec_quito), '| en sectores divididos:', int(div.p_nbi.sum() - micro_div))
    for k in ('saneamiento', 'agua', 'hacinamiento'):
        print(k, 'dif abs media %.3f pp, máx %.3f pp' % (out[f'dif_{k}_pp'].abs().mean(), out[f'dif_{k}_pp'].abs().max()))

if __name__ == '__main__':
    main()
