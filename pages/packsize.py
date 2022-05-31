# -*- coding: utf-8 -*-
# author: cyrilbruyere
# maj : 22.5.6

# import des packages
from config import wms2
import pandas as pd
import datetime as dt
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go

# Définition de la requête SQL
query = """
    SELECT 
       TRUNC(mt.DSTAMP) as DSTAMP,
       mt.CONSIGNMENT, 
       mt.WORK_GROUP,
       mt.TASK_TYPE,
       mt.LIST_ID,  
       mt.FROM_LOC_ID,
       l.LOC_TYPE,  
       mt.WORK_ZONE,
       mt.QTY_TO_MOVE / sc.RATIO_1_TO_2 NB_UV,
       mt.CONTAINER_ID, 
       mt.PALLET_ID,
       mt.STATUS,
       mt.V_ORIG_WORK_ZONE,
       mt.CUSTOMER_ID

       --mt.TO_LOC_ID,
       --mt.PRINT_LABEL_ID,
       --mt.SKU_ID,  
       --ssc.CONFIG_ID,
       --sc.RATIO_1_TO_2 UV,
       --mt.QTY_TO_MOVE,
       --mt.V_RFS_TIME

FROM dcsdba.move_task mt
LEFT JOIN dcsdba.location l ON mt.FROM_LOC_ID = l.LOCATION_ID
LEFT JOIN DCSDBA.SKU_sku_CONFIG ssc ON mt.SKU_ID = ssc.SKU_ID
LEFT JOIN DCSDBA.SKU_CONFIG sc ON ssc.CONFIG_ID = sc.CONFIG_ID AND mt.site_id = l.site_id

WHERE mt.site_id ='LDC'
    and mt.CLIENT_ID ='VOLVO'
    and mt.CONSIGNMENT <> '-SHP-DCLYON'
    and mt.WORK_ZONE in ('WS-PACKSIZ','VX1-RETR','VX1-PREP', 'VX1-RET+','WT-PACKSIZ', 'COZNE')
    and mt.V_ORIG_WORK_ZONE in ('WS-PACKSIZ','VX1-RETR','VX1-PREP', 'VX1-RET+','WT-PACKSIZ')
    and mt.TASK_TYPE in ('O','T')
    and mt.CONSIGNMENT NOT LIKE 'KTS%'
    and mt.CONSIGNMENT NOT LIKE 'RMS%'
    and mt.CONSIGNMENT NOT LIKE 'SCRAP'
    and mt.WORK_GROUP NOT LIKE '445%'
    and mt.WORK_GROUP NOT LIKE '443%'
    and mt.WORK_GROUP NOT LIKE '420%'
    and mt.WORK_GROUP NOT LIKE '3%'
GROUP BY TRUNC(mt.DSTAMP), mt.CONSIGNMENT, mt.WORK_GROUP, mt.TASK_TYPE, mt.LIST_ID, mt.FROM_LOC_ID, l.LOC_TYPE, mt.TO_LOC_ID, mt.WORK_ZONE, mt.PRINT_LABEL_ID, mt.SKU_ID, mt.QTY_TO_MOVE, mt.CONTAINER_ID, mt.PALLET_ID, mt.STATUS, mt.V_ORIG_WORK_ZONE, mt.CUSTOMER_ID, mt.V_RFS_TIME, ssc.CONFIG_ID, sc.RATIO_1_TO_2
"""

# Définition de l'affichage et intervalle de refresh
layout = html.Div([
    html.Div(id='datetime-packsize', style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.A( id='datetime-packsize',
            href='https://qlikview.srv.volvo.com/QvAJAXZfc/opendoc.htm?document=gto-sbi-wms2\outbound%20following%20-%20consolidation%20packsize.qvw&lang=en-US&host=QVS%40Cluster',
            target='_blank',
            style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.Hr(),
    html.Div([
            dcc.Interval(id='interval-packsize',
                         interval=30000, # milliseconds
                         n_intervals=0
                         ),
            dcc.Graph(id='Andon-packsize')
            ])
                        ], style={  'backgroundColor' : '#000000',
                                    'text-align' : 'center'})

# Refresh automatique date
@callback(Output('datetime-packsize', 'children'),
              [Input('interval-packsize', 'n_intervals')])
def update_time(n):
    refresh_time = dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return '{}'.format(refresh_time)

# Refresh écran Andon
@callback(Output('Andon-packsize', 'figure'),
              [Input('interval-packsize', 'n_intervals')])
def update_layout(n):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    colonnes = ['DSTAMP', 'CONSIGNMENT', 'WORK_GROUP', 'TASK_TYPE', 'LIST_ID', 'FROM_LOC_ID', 'LOC_TYPE',
            'WORK_ZONE', 'NB_UV', 'CONTAINER_ID', 'PALLET_ID', 'STATUS', 'V_ORIG_WORK_ZONE', 'CUSTOMER_ID']
    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # Ajout de nouveaux champs
    df['NB_UV'] = df['NB_UV'].fillna(0)
    df['DESTINATION'] = df['CONSIGNMENT'].apply(lambda x: x[7:])
    df['TYPE'] = df['CONSIGNMENT'].apply(lambda x: x[5:6])
    df['TIME'] = df['CONSIGNMENT'].str[:4]
    df['Flag Pallet'] = (df['CONTAINER_ID'] == df['PALLET_ID'])
    # Définition du champ CUTOFF
    df.loc[df['TYPE']=='D','CUTOFF'] = df['WORK_GROUP'].str[-4:]
    df.loc[df['TYPE']!='D','CUTOFF'] = '0000'
    # Calcul du champ spécifique HOLD
    # NB : lorsqu'un client a plus de 7 UV, on ne passe pas par packsize
    #     Calcul du nombre d'UV par client
    customer = df[['DESTINATION', 'CUSTOMER_ID', 'NB_UV']]
    customer = customer.groupby(['DESTINATION', 'CUSTOMER_ID']).sum()
    customer.reset_index(inplace = True)
    customer.rename({'NB_UV' : 'Cust_UV'}, axis = 1, inplace = True)
    #     Calcul de la valeur HOLD
    hold = df[['DESTINATION', 'TYPE', 'TIME', 'CUSTOMER_ID', 'STATUS', 'NB_UV']]
    hold = pd.merge(hold, customer, how = 'left', left_on =['DESTINATION', 'CUSTOMER_ID'], right_on = ['DESTINATION', 'CUSTOMER_ID'])
    hold.loc[((hold['Cust_UV'] >= 7) & (hold['STATUS']=='Hold'))|(hold['STATUS']!='Hold'), 'NB_UV'] = 0
    andon_hold = hold[['DESTINATION', 'TYPE', 'TIME', 'NB_UV']]
    andon_hold.rename({'NB_UV' : 'HOLD'}, axis = 1, inplace = True)
    andon_hold = andon_hold.groupby(['TIME', 'DESTINATION', 'TYPE']).sum()
    andon_hold.reset_index(inplace = True)
    # Calcul du champ spécifique RELEASED
    df['RELEASED'] = 0
    df.loc[((df['LOC_TYPE'].isin(['Tag-FIFO', 'Tag-Operator']))
        & (df['LIST_ID'].str.contains('PRPS') == True)
        & (df['STATUS'].isin(['Released', 'In Progress']))), 'RELEASED'] = df['NB_UV']
    andon_released = df[['DESTINATION', 'TYPE', 'TIME', 'RELEASED']]
    andon_released = andon_released.groupby(['TIME', 'DESTINATION', 'TYPE']).sum()
    andon_released.reset_index(inplace = True)
    # Calcul des champs colis
    df['ENCOURS'] = ((df['FROM_LOC_ID'] == 'CONTAINER') & ((df['PALLET_ID'].str.contains('PRPS') == True) | (df['PALLET_ID'].str.contains('RPS') == True)) & (df['V_ORIG_WORK_ZONE'].isin(['VX1-RETR', 'VX1-RET+', 'VX1-PREP'])))
    df['Colis WS'] = ((df['STATUS'] == 'Consol') & (df['WORK_ZONE'] == 'WS-PACKSIZ'))
    df['Colis WT'] = ((df['STATUS'] == 'Consol') & (df['WORK_ZONE'] == 'WT-PACKSIZ') & (df['Flag Pallet'] == True))
    df['Colis PLDC'] = ((df['STATUS'] == 'Consol') & (df['WORK_ZONE'] == 'WT-PACKSIZ') & (df['Flag Pallet'] == False))
    df.drop_duplicates(subset=['CONTAINER_ID'], inplace = True)
    andon_container = df[['DESTINATION', 'TYPE', 'TIME', 'ENCOURS', 'Colis WS', 'Colis WT', 'Colis PLDC', 'CUTOFF']]
    andon_container = andon_container.groupby(['TIME', 'DESTINATION', 'TYPE', 'CUTOFF']).sum()
    andon_container.reset_index(inplace = True)   
    # Calcul du champ spécifique : nombre de PLDC
    pallet = df[['TIME', 'DESTINATION', 'TYPE', 'WORK_ZONE', 'PALLET_ID']]
    pallet.drop_duplicates(inplace = True)
    pallet['PLDC'] = ((pallet['PALLET_ID'].str[:4] == 'PLDC') & (pallet['WORK_ZONE'] == 'WT-PACKSIZ'))
    pallet.drop(['WORK_ZONE', 'PALLET_ID'], axis = 1, inplace = True)
    pallet.replace(to_replace = [True, False], value = [1, 0], inplace = True)
    andon_pallet = pallet.groupby(['TIME', 'DESTINATION', 'TYPE']).sum()
    andon_pallet.reset_index(inplace = True)
    # Compilation des champs à afficher
    andon = pd.merge(andon_hold, andon_container, how='outer', left_on=['TIME', 'DESTINATION', 'TYPE'], right_on=['TIME', 'DESTINATION', 'TYPE'])
    andon = pd.merge(andon, andon_released, how='outer', left_on=['TIME', 'DESTINATION', 'TYPE'], right_on=['TIME', 'DESTINATION', 'TYPE'])
    andon = pd.merge(andon, andon_pallet, how='left', left_on=['TIME', 'DESTINATION', 'TYPE'], right_on=['TIME', 'DESTINATION', 'TYPE'])
    andon[['ENCOURS', 'Colis WS', 'Colis WT', 'Colis PLDC', 'PLDC']] = andon[['ENCOURS', 'Colis WS', 'Colis WT', 'Colis PLDC', 'PLDC']].fillna(0)
    andon['CUTOFF'] = andon['CUTOFF'].fillna('0000')
    andon[['HOLD', 'RELEASED', 'ENCOURS', 'Colis WS', 'Colis WT', 'Colis PLDC', 'PLDC']] = andon[['HOLD', 'RELEASED', 'ENCOURS', 'Colis WS', 'Colis WT', 'Colis PLDC', 'PLDC']].astype(int)
    andon = andon[andon.sum(axis=1)!=0]
    if dt.datetime.now().time() > dt.time(hour = 13, minute = 45):
        andon = andon[andon['TYPE']=='D']
    else:
        andon = andon[andon['TYPE']=='S']
    # Calcul du retard
    andon['TIME_dt'] = pd.to_datetime(andon['TIME'], format = '%H%M').dt.time
    andon['CUTOFF_dt'] = pd.to_datetime(andon['CUTOFF'], format = '%H%M').dt.time
    andon['Total'] = andon[['HOLD', 'RELEASED', 'ENCOURS', 'Colis WS', 'Colis WT']].sum(axis = 1)
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
    andon.loc[(andon['PLDC']>0)&(andon['Total']==0)&(andon['TYPE']=='D')&(andon['CUTOFF_dt'] < present.time()),'CUTOFF_color'] = '#008000'
    andon = andon.replace(to_replace = [0, '0000'], value = ['', ''])
    # Listes à afficher
    cutoff = andon['CUTOFF']
    destination = andon['DESTINATION'].values
    quai = andon['TIME'].values
    hold = andon['HOLD'].values
    released = andon['RELEASED'].values
    encours = andon['ENCOURS'].values
    colis_ws = andon['Colis WS'].values
    colis_wt = andon['Colis WT'].values
    palette = andon['PLDC'].values
    colis_emballes = andon['Colis PLDC'].values
    couleur_retard = andon['RET_color'].values
    couleur_day = andon['D_color'].values
    couleur_cutoff = andon['CUTOFF_color'].values
    # Colonnes à afficher
    shown_columns = ['CUTOFF', 'DESTINATION', 'TIME', 'HOLD', 'RELEASED', 'ENCOURS', 'Colis WS', 'Colis WT', 'PLDC', 'Colis PLDC']
    # Application des couleurs définies
    fill_color = []
    n = len(andon)
    for col in shown_columns:
        if col in ['DESTINATION', 'TIME']:
            fill_color.append(couleur_retard)
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
                    columnwidth = [.8, 1.7, .75, .75, .75, .75, .75, .75, .75, .75],
                    header = dict(  values = ['CutOFF', 'Destination', 'Quai', 'HOLD', 'RELEASED', 'ENCOURS', 'Colis WS', 'Colis WT', 'PLDC', 'Colis PLDC'],
                                    fill = dict(color='#000000'),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 24),
                                    align = ['center'],
                                    height = 40),
                    cells = dict(   values = [cutoff, destination, quai, hold, released, encours, colis_ws, colis_wt, palette, colis_emballes],
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
