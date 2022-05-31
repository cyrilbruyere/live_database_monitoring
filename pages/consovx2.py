# -*- coding: utf-8 -*-
# author: cyrilbruyere
# maj : 22.5.6

# import des packages
from config import wms2
import pandas as pd
import datetime as dt
from dash import dcc, html, Input, Output, callback, Dash
import plotly.graph_objs as go

# Définition de la requête SQL
conso_vx2 = """
    SELECT
    	   DISTINCT mt.CONTAINER_ID,
           mt.CONSIGNMENT,
           mt.WORK_GROUP,
           mt.TASK_TYPE,
           mt.FROM_LOC_ID,
           mt.WORK_ZONE,
           mt.PALLET_ID,
           mt.STATUS,
           mt.V_ORIG_WORK_ZONE
    FROM dcsdba.move_task mt
    LEFT JOIN dcsdba.location l ON mt.from_loc_id = l.location_id
    LEFT JOIN dcsdba.sku_sku_config ssc ON mt.sku_id = ssc.sku_id

    WHERE mt.site_id ='LDC'
        AND mt.CLIENT_ID ='VOLVO'
        AND mt.WORK_ZONE in ('WS-VX2-B','VX2S','VX2B','VX2 GZ+','WT-VX2-B','WT-ATTR','ATTS','ATTR','RVX2XDOCK', 'COZNE','VX2P-DOC','VX2B-DOC','VX2R','VX2P')
        AND mt.V_ORIG_WORK_ZONE in ('WS-VX2-B','VX2S','VX2B','VX2 GZ+','WT-VX2-B','WT-ATTR','ATTS','ATTR','RVX2XDOCK', 'COZNE','VX2P-DOC','VX2B-DOC','VX2R','VX2P')
        AND mt.TASK_TYPE in ('O')
        AND mt.status = 'Consol'
        AND mt.CONSIGNMENT NOT LIKE 'KTS%'
        AND mt.CONSIGNMENT NOT LIKE 'RMS%'
        AND mt.CONSIGNMENT NOT LIKE 'SCRAP'
"""

# Définition de l'affichage et intervalle de refresh
layout = html.Div([
    html.Div(id='datetime-consovx2', style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.A( id='datetime-consovx2',
            href='https://qlikview.srv.volvo.com/QvAJAXZfc/opendoc.htm?document=gto-sbi-wms2\outbound%20following%20-%20consolidation%20vx2.qvw&lang=en-US&host=QVS%40Cluster',
            target='_blank',
            style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.Hr(),
    html.Div([
            dcc.Interval(id='interval-consovx2',
                         interval=30000, # milliseconds
                         n_intervals=0
                         ),
            dcc.Graph(id='Andon-consovx2')
            ])
                        ], style={  'backgroundColor' : '#000000',
                                    'text-align' : 'center'})

# Refresh automatique date
@callback(Output('datetime-consovx2', 'children'),
              [Input('interval-consovx2', 'n_intervals')])
def update_time(n):
    refresh_time = dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return '{}'.format(refresh_time)

# Refresh écran Andon
@callback(Output('Andon-consovx2', 'figure'),
              [Input('interval-consovx2', 'n_intervals')])
def update_layout(n):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    colonnes = ['CONTAINER_ID', 'CONSIGNMENT', 'WORK_GROUP', 'TASK_TYPE', 'FROM_LOC_ID',
                'WORK_ZONE', 'PALLET_ID', 'STATUS', 'V_ORIG_WORK_ZONE']
    cursor = conn.cursor()
    cursor.execute(conso_vx2)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # Ajout de nouveaux champs
    df['DESTINATION'] = df['CONSIGNMENT'].apply(lambda x: x[7:] if x[5:6]!='P' else x[5:])
    df['TYPE'] = df['CONSIGNMENT'].apply(lambda x: x[5:6] if x[5:6]!='P' else 'D')
    df['TIME'] = df['CONSIGNMENT'].str[:4]
    df['GOULOTTE'] = df['FROM_LOC_ID'].str[8:9]
    df['Flag Pallet'] = (df['CONTAINER_ID'] == df['PALLET_ID'])
    # Définition de l'écran Andon
    df['Encours'] = df['FROM_LOC_ID'] == 'CONTAINER'
    df['G. A'] = ((df['FROM_LOC_ID'] != 'CONSO-QUAR') & (df['WORK_ZONE'] == 'WS-VX2-B') & (df['GOULOTTE'] == 'A'))
    df['G. B'] = ((df['FROM_LOC_ID'] != 'CONSO-QUAR') & (df['WORK_ZONE'] == 'WS-VX2-B') & (df['GOULOTTE'] == 'B'))
    df['Quar.'] = ((df['FROM_LOC_ID'] == 'CONSO-QUAR') & (df['WORK_ZONE'] == 'WS-VX2-B'))
    df['X-Dock.'] = ((df['V_ORIG_WORK_ZONE'] == 'RVX2XDOCK') & (df['WORK_ZONE'] == 'WT-VX2-B') & (df['Flag Pallet'] == True))
    df['Attr.'] = ((df['V_ORIG_WORK_ZONE'].isin(['ATTR', 'ATTS'])) & (df['WORK_ZONE'] == 'WT-VX2-B') & (df['Flag Pallet'] == True))
    df['C.W.'] = ((~df['V_ORIG_WORK_ZONE'].isin(['ATTR', 'ATTS', 'RVX2XDOCK'])) & (df['WORK_ZONE'] == 'WT-VX2-B') & (df['Flag Pallet'] == True))
    df['PLDC'] = ((df['PALLET_ID'].str[:4] == 'PLDC') & (df['WORK_ZONE'] == 'WT-VX2-B'))
    df.loc[df['TYPE']=='D','CUTOFF'] = df['WORK_GROUP'].str[-4:]
    df.loc[df['TYPE']!='D','CUTOFF'] = '0000'
    # Calcul du champ spécifique lié au nombre de pallet
    pallet = df[['TIME', 'DESTINATION', 'TYPE', 'WORK_ZONE', 'PALLET_ID']]
    pallet.drop_duplicates(inplace = True)
    pallet['P.W.'] = ((pallet['PALLET_ID'].str[:4] == 'PLDC') & (pallet['WORK_ZONE'] == 'WT-VX2-B'))
    pallet.drop(['WORK_ZONE', 'PALLET_ID'], axis = 1, inplace = True)
    pallet.replace(to_replace = [True, False], value = [1, 0], inplace = True)
    # Valeurs à afficher
    df.drop_duplicates(subset=['CONTAINER_ID'], inplace = True)
    andon_container = df.groupby(['TIME', 'DESTINATION', 'TYPE', 'CUTOFF']).sum()[['Encours', 'G. A', 'G. B', 'Quar.', 'X-Dock.', 'Attr.', 'C.W.', 'PLDC']]
    andon_container.reset_index(inplace = True)
    andon_pallet = pallet.groupby(['TIME', 'DESTINATION', 'TYPE']).sum()
    andon_pallet.reset_index(inplace = True)
    andon = pd.merge(andon_container, andon_pallet, how='left', left_on=['TIME', 'DESTINATION', 'TYPE'], right_on=['TIME', 'DESTINATION', 'TYPE'])
    andon[['Encours', 'G. A', 'G. B', 'Quar.', 'X-Dock.', 'Attr.', 'C.W.', 'P.W.', 'PLDC']] = andon[['Encours', 'G. A', 'G. B', 'Quar.', 'X-Dock.', 'Attr.', 'C.W.', 'P.W.', 'PLDC']].astype(int)
    andon = andon[andon.sum(axis=1)!=0]
    if dt.datetime.now().time() > dt.time(hour = 16, minute = 0):
        andon = andon[andon['TYPE']=='D']
    # Calcul du retard
    andon['TIME_dt'] = pd.to_datetime(andon['TIME'], format = '%H%M').dt.time
    andon['CUTOFF'] = pd.to_datetime(andon['CUTOFF'], format = '%H%M').dt.time
    andon['Total'] = andon[['Encours', 'G. A', 'G. B', 'Quar.', 'X-Dock.', 'Attr.', 'C.W.']].sum(axis = 1)
    # Définition fond rouge si palette en retard, orange s'il reste 15 minutes :
    present = dt.datetime.now()
    def def_color_backlog(x):
        if present.time() > x:
            return '#FF0000'
        elif (present + dt.timedelta(seconds = 15 * 60)).time() > x:
            return '#FA9D00'
        else:
            return '#000000'
    andon['RET_color'] = andon['TIME_dt'].apply(lambda x: def_color_backlog(x))
    # Définition fond bleu pour les commandes urgentes (D)
    andon['D_color'] = andon['TYPE'].apply(lambda x: '#0080FF' if x == 'D' else '#000000')
    # Définition fond vert lorsque les palettes sont prêtes et que l'heure de cutoff est passée
    andon['CUTOFF_color'] = '#000000'
    andon.loc[(andon['PLDC']>0)&(andon['Total']==0)&(andon['TYPE']=='D')&(andon['CUTOFF'] < present.time()),'CUTOFF_color'] = '#008000'
    andon = andon.replace(to_replace = [0], value = [''])
    # Listes à afficher
    time = andon['TIME'].values
    destination = andon['DESTINATION'].values
    type = andon['TYPE'].values
    encours = andon['Encours'].values
    goulotte_a = andon['G. A'].values
    goulotte_b = andon['G. B'].values
    quarantaine = andon['Quar.'].values
    crossdock = andon['X-Dock.'].values
    attractif = andon['Attr.'].values
    colis_peses = andon['C.W.'].values
    palette = andon['P.W.'].values
    colis_emballes = andon['PLDC'].values
    couleur_retard = andon['RET_color'].values
    couleur_day = andon['D_color'].values
    couleur_cutoff = andon['CUTOFF_color'].values
    # Colonnes à afficher
    shown_columns = ['TIME', 'DESTINATION', 'TYPE', 'Encours', 'G. A', 'G. B', 'Quar.', 'X-Dock.', 'Attr.', 'C.W.', 'P.W.', 'PLDC']
    # Application des couleurs définies
    fill_color = []
    n = len(andon)
    for col in shown_columns:
        if col in ['TIME', 'DESTINATION']:
            fill_color.append(couleur_retard)
        elif col in ['TYPE']:
            fill_color.append(couleur_day)
        elif col in ['PLDC']:
            fill_color.append(couleur_cutoff)
        else:
            fill_color.append(['#000000']*n)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [.8, 1.7, .75, .75, .75, .75, .75, .75, .75, .75, .75, .75],
                    header = dict(  values = ['Heure', 'Destination', 'Type', 'Encours', 'G. A', 'G. B', 'Quar.', 'X-Dock', 'Attract', 'C.W.', 'P.W.', 'PLDC'],
                                    fill = dict(color='#000000'),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 24),
                                    align = ['center'],
                                    height = 40),
                    cells = dict(   values = [time, destination, type, encours, goulotte_a, goulotte_b, quarantaine, crossdock, attractif, colis_peses, palette, colis_emballes],
                                    fill = dict(color=fill_color), # '#000000'
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 32), # [couleur_retard], 
                                    align = ['center'] * 5,
                                    height = 45)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 985,
            'margin' : dict(l=0, r=0, t=0, b=0)
        }
    }
