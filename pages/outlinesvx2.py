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
SELECT mt.TASK_ID,
       mt.STATUS,
       mt.WORK_GROUP,
       mt.CONSIGNMENT,
       SUBSTR(mt.CONSIGNMENT, 0, 4) as CONSIGNMENT_TIME,
       mt.PRINT_LABEL_ID,
       mt.WORK_ZONE,
       oh.SHIP_BY_DATE,
       ol.LINE_ID,
       ol.QTY_ORDERED,
       ol.QTY_TASKED,
       ol.QTY_PICKED,
       ol.QTY_SHIPPED,
       ol.V_SHORT,
       ol.USER_DEF_TYPE_8 AS UP,
       CASE oh.ORDER_TYPE
       WHEN 'VOR' THEN 'Urgent'
       WHEN 'DAY' THEN 'Urgent'
       WHEN 'STOCK' THEN 'Régulier'
       WHEN 'TPO' THEN 'Régulier'
       WHEN 'REF_NOR' THEN 'Régulier'
       WHEN 'KTS' THEN 'Régulier'
       ELSE 'Autres' END AS ORDER_TYPE
FROM dcsdba.move_task mt
LEFT JOIN dcsdba.order_header oh ON oh.ORDER_ID = mt.TASK_ID
LEFT JOIN dcsdba.order_line ol ON ol.ORDER_ID||ol.LINE_ID = mt.TASK_ID||mt.LINE_ID
WHERE mt.SITE_ID = 'LDC'
    AND mt.TASK_TYPE = 'O' 
    AND mt.STATUS not in ('Consol',' Error')
    AND (mt.WORK_GROUP like '1%' or mt.WORK_GROUP like '2%'  or mt.WORK_GROUP like '3%'  or mt.WORK_GROUP like '4%'  or mt.WORK_GROUP like '5%' )
    AND mt.WORK_ZONE not in ('RVX2QUA') and mt.WORK_ZONE not like 'QUAI%'
    AND oh.STATUS not in ('Shipped','Cancelled')
    AND ol.CLIENT_ID = 'VOLVO'
    AND ((ol.QTY_SHIPPED IS NULL OR ol.QTY_SHIPPED = 0) OR (ol.QTY_SHIPPED < (ol.QTY_PICKED + ol.QTY_TASKED)))
    AND ol.SKU_ID like 'RT%'
    AND mt.CONSIGNMENT not in ('-SHP-DCLYON','DISP-FOURN')
"""

# Définition de l'affichage et intervalle de refresh
layout = html.Div([
    html.Div(id='datetime-outlinesvx2', style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.Hr(),
    html.Div([
        html.Div([
                dcc.Interval(id='interval-outlinesvx2',
                            interval=30000, # milliseconds
                            n_intervals=0
                            ),
                dcc.Graph(id='Andon-outlinesvx2-reg'),
                dcc.Graph(id='Andon-outlinesvx2-reg-sum')
                ], style={'width' : '49%',
                          'display' : 'inline-block'}),
        html.Div([
                dcc.Graph(id='Andon-outlinesvx2-urg'),
                dcc.Graph(id='Andon-outlinesvx2-urg-sum')
                ], style={'width' : '49%',
                          'display' : 'inline-block'})        
            ])
                    ], style={  'backgroundColor' : '#000000',
                             })
# Refresh automatique date
@callback(Output('datetime-outlinesvx2', 'children'),
              [Input('interval-outlinesvx2', 'n_intervals')])
def update_time(n):
    refresh_time = dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return '{}'.format(refresh_time)

# Refresh écran Andon REGULIER
@callback(Output('Andon-outlinesvx2-reg', 'figure'),
              [Input('interval-outlinesvx2', 'n_intervals')])
def update_layout(n):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    colonnes = ['TASK_ID', 'STATUS', 'WORK_GROUP', 'CONSIGNMENT', 'CONSIGNMENT_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'SHIP_BY_DATE',
                'LINE_ID', 'QTY_ORDERED', 'QTY_TASKED', 'QTY_PICKED', 'QTY_SHIPPED', 'V_SHORT', 'UP','ORDER_TYPE']
    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # correction périmètre des UP
    df['UP'].replace(to_replace = ['GLPB'], value = ['VX2'], inplace = True)
    # définition des secteurs
    df['SECTEUR'] = 'PIGO'
    df.loc[df['WORK_ZONE'] == 'PBGL', 'SECTEUR'] = 'PB'
    df.loc[df['WORK_ZONE'].str.contains('^(AEC)'), 'SECTEUR'] = 'AEC'
    df.loc[df['WORK_GROUP'].str.contains('^5'), 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2 GZ-', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B-DOC', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2R', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P-DOC', 'SECTEUR'] = 'FSP'
    # Calcul du retard (en jours)
    aujourdhui = dt.datetime.today().date()
    df['SHIP_BY_DATE'] = pd.to_datetime(df['SHIP_BY_DATE'], yearfirst = True)
    df['SHIP_BY_DATE'] = df['SHIP_BY_DATE'].apply(lambda x: x.date())
    df['GAP'] = df['SHIP_BY_DATE'].apply(lambda x: (x - aujourdhui).days)
    df['BACKLOG'] = 'J+1'
    df.loc[df['GAP'] < 0, 'BACKLOG'] = 'Retard'
    df.loc[df['GAP'] == 0, 'BACKLOG'] = 'J'
    # Gestion spécifique pour les KITS
    df.loc[df['CONSIGNMENT_TIME'] == 'KTS-', 'BACKLOG'] = 'J+1'
    # Calcul du retard lié à l'heure de mise à quai
    maintenant = dt.datetime.now().hour * 100 + dt.datetime.now().minute
    maintenant = str(maintenant)
    if len(maintenant) == 3:
        maintenant = '0' + maintenant
    df.loc[(df['BACKLOG'] == 'J') & (df['CONSIGNMENT_TIME'] < maintenant), 'BACKLOG'] = 'Retard'
    # Regrouper les WORK_GROUP avec l'heure mini de consignment
    df_wg_min_time = df[['WORK_GROUP', 'CONSIGNMENT_TIME']]
    df_wg_min_time = df_wg_min_time.groupby(['WORK_GROUP']).min()
    df_wg_min_time.reset_index(inplace = True)
    df_wg_min_time.rename({'CONSIGNMENT_TIME' : 'MIN_TIME'}, axis = 1, inplace = True)
    df = pd.merge(df, df_wg_min_time, how = 'left', left_on = 'WORK_GROUP', right_on = 'WORK_GROUP')
    # Ajout de l'heure de consignment au work_group 
    df['WORK_GROUP_2'] = df['WORK_GROUP'].str[:10] + '-' + df['MIN_TIME']
    df.loc[df['WORK_GROUP'].str.contains('^500'), 'WORK_GROUP_2'] = df['WORK_GROUP'].str[:5] + '-' + df['WORK_GROUP'].str[6:10]
    # Restriction aux champs utiles
    df = df.drop(['TASK_ID', 'STATUS', 'CONSIGNMENT', 'CONSIGNMENT_TIME', 'MIN_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'WORK_GROUP',
    'SHIP_BY_DATE', 'LINE_ID', 'QTY_ORDERED', 'QTY_TASKED', 'QTY_PICKED', 'QTY_SHIPPED', 'V_SHORT', 'GAP'], axis = 1)
    df.rename({'WORK_GROUP_2' : 'WORK_GROUP'}, axis = 1, inplace = True)
    # Définition des données pour les visuels
    affichage = df.groupby(['UP', 'ORDER_TYPE', 'SECTEUR', 'WORK_GROUP', 'BACKLOG']).size().reset_index()
    affichage.rename({0 : 'Lines'}, axis = 1, inplace = True)
    # Définition du visuel à afficher (figure)
    reg_J0 = go.Bar(
                    name = 'J',
                    x = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J')],
                    y = affichage['WORK_GROUP'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J')],
                    text = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J')],
                    orientation = 'h',
                    marker = dict (color = '#00ff00')
                    )
    reg_J1 = go.Bar(
                    name = 'J+1',
                    x = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J+1')],
                    y = affichage['WORK_GROUP'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J+1')],
                    text = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J+1')],
                    orientation = 'h',
                    marker = dict (color = '#bbbbbb')
                    )
    reg_Ret = go.Bar(
                    name = 'Retard',
                    x = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='Retard')],
                    y = affichage['WORK_GROUP'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='Retard')],
                    text = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='Retard')],
                    orientation = 'h',
                    marker = dict (color = '#ff0000')
                    )
    data = [reg_Ret, reg_J0, reg_J1]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       yaxis = {'categoryorder' : 'category descending'},
                       title = 'Régulier',
                       titlefont_size = 24,
                       height = 700,
                       margin = dict(l=150, r=5, t=35, b=0))
    return {
        'data' : data,
        'layout' : layout
    }

# Refresh écran Andon REGULIER SUMMARY
@callback(Output('Andon-outlinesvx2-reg-sum', 'figure'),
              [Input('interval-outlinesvx2', 'n_intervals')])
def update_layout(n):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    colonnes = ['TASK_ID', 'STATUS', 'WORK_GROUP', 'CONSIGNMENT', 'CONSIGNMENT_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'SHIP_BY_DATE',
                'LINE_ID', 'QTY_ORDERED', 'QTY_TASKED', 'QTY_PICKED', 'QTY_SHIPPED', 'V_SHORT', 'UP','ORDER_TYPE']
    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # correction périmètre des UP
    df['UP'].replace(to_replace = ['GLPB'], value = ['VX2'], inplace = True)
    # définition des secteurs
    df['SECTEUR'] = 'PIGO'
    df.loc[df['WORK_ZONE'] == 'PBGL', 'SECTEUR'] = 'PB'
    df.loc[df['WORK_ZONE'].str.contains('^(AEC)'), 'SECTEUR'] = 'AEC'
    df.loc[df['WORK_GROUP'].str.contains('^5'), 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2 GZ-', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B-DOC', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2R', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P-DOC', 'SECTEUR'] = 'FSP'
    # Calcul du retard (en jours)
    aujourdhui = dt.datetime.today().date()
    df['SHIP_BY_DATE'] = pd.to_datetime(df['SHIP_BY_DATE'], yearfirst = True)
    df['SHIP_BY_DATE'] = df['SHIP_BY_DATE'].apply(lambda x: x.date())
    df['GAP'] = df['SHIP_BY_DATE'].apply(lambda x: (x - aujourdhui).days)
    df['BACKLOG'] = 'J+1'
    df.loc[df['GAP'] < 0, 'BACKLOG'] = 'Retard'
    df.loc[df['GAP'] == 0, 'BACKLOG'] = 'J'
    # Gestion spécifique pour les KITS
    df.loc[df['CONSIGNMENT_TIME'] == 'KTS-', 'BACKLOG'] = 'J+1'
    # Calcul du retard lié à l'heure de mise à quai
    maintenant = dt.datetime.now().hour * 100 + dt.datetime.now().minute
    maintenant = str(maintenant)
    if len(maintenant) == 3:
        maintenant = '0' + maintenant
    df.loc[(df['BACKLOG'] == 'J') & (df['CONSIGNMENT_TIME'] < maintenant), 'BACKLOG'] = 'Retard'
    # Définition des données pour les visuels
    retard = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Régulier')&(df['BACKLOG']=='Retard')])
    jour = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Régulier')&(df['BACKLOG']=='J')])
    lendemain = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Régulier')&(df['BACKLOG']=='J+1')])
    total = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Régulier')])
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [25, 25, 25, 25],
                    header = dict(  values = ['Retard', 'J', 'J+1', 'Total'],
                                    fill = dict(color=['#FF0000', '#00FF00', '#bbbbbb', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 20),
                                    align = ['center'],
                                    height = 35),
                    cells = dict(   values = [retard, jour, lendemain, total],
                                    fill = dict(color='#000000'),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 20), # [couleur_retard], 
                                    align = ['center'] * 5,
                                    height = 35)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 110,
            'margin' : dict(l=150, r=100, t=40, b=0)
        }
    }

# Refresh écran Andon URGENT
@callback(Output('Andon-outlinesvx2-urg', 'figure'),
              [Input('interval-outlinesvx2', 'n_intervals')])
def update_layout(n):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    colonnes = ['TASK_ID', 'STATUS', 'WORK_GROUP', 'CONSIGNMENT', 'CONSIGNMENT_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'SHIP_BY_DATE',
                'LINE_ID', 'QTY_ORDERED', 'QTY_TASKED', 'QTY_PICKED', 'QTY_SHIPPED', 'V_SHORT', 'UP','ORDER_TYPE']
    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # correction périmètre des UP
    df['UP'].replace(to_replace = ['GLPB'], value = ['VX2'], inplace = True)
    # définition des secteurs
    df['SECTEUR'] = 'PIGO'
    df.loc[df['WORK_ZONE'] == 'PBGL', 'SECTEUR'] = 'PB'
    df.loc[df['WORK_ZONE'].str.contains('^(AEC)'), 'SECTEUR'] = 'AEC'
    df.loc[df['WORK_GROUP'].str.contains('^5'), 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2 GZ-', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B-DOC', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2R', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P-DOC', 'SECTEUR'] = 'FSP'
    # Calcul du retard (en jours)
    aujourdhui = dt.datetime.today().date()
    df['SHIP_BY_DATE'] = pd.to_datetime(df['SHIP_BY_DATE'], yearfirst = True)
    df['SHIP_BY_DATE'] = df['SHIP_BY_DATE'].apply(lambda x: x.date())
    df['GAP'] = df['SHIP_BY_DATE'].apply(lambda x: (x - aujourdhui).days)
    df['BACKLOG'] = 'J+1'
    df.loc[df['GAP'] < 0, 'BACKLOG'] = 'Retard'
    df.loc[df['GAP'] == 0, 'BACKLOG'] = 'J'
    # Calcul du retard lié à l'heure de mise à quai
    maintenant = dt.datetime.now().hour * 100 + dt.datetime.now().minute
    maintenant = str(maintenant)
    if len(maintenant) == 3:
        maintenant = '0' + maintenant
    df.loc[(df['BACKLOG'] == 'J') & (df['CONSIGNMENT_TIME'] < maintenant), 'BACKLOG'] = 'Retard'
    # Ajout de l'heure de consignment au work_group
    df['WORK_GROUP_2'] = df['WORK_GROUP'].str[:10] + '-' + df['CONSIGNMENT_TIME']
    df.loc[df['WORK_GROUP'].str.contains('^500'), 'WORK_GROUP_2'] = df['WORK_GROUP'].str[:10]
    # Restriction aux champs utiles
    df = df.drop(['TASK_ID', 'STATUS', 'CONSIGNMENT', 'CONSIGNMENT_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'WORK_GROUP',
    'SHIP_BY_DATE', 'LINE_ID', 'QTY_ORDERED', 'QTY_TASKED', 'QTY_PICKED', 'QTY_SHIPPED', 'V_SHORT', 'GAP'], axis = 1)
    df.rename({'WORK_GROUP_2' : 'WORK_GROUP'}, axis = 1, inplace = True)
    # Définition des données pour les visuels
    affichage = df.groupby(['UP', 'ORDER_TYPE', 'SECTEUR', 'WORK_GROUP', 'BACKLOG']).size().reset_index()
    affichage.rename({0 : 'Lines'}, axis = 1, inplace = True)
    # Définition du visuel à afficher (figure)
    reg_J0 = go.Bar(
                    name = 'J',
                    x = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J')],
                    y = affichage['WORK_GROUP'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J')],
                    text = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J')],
                    orientation = 'h',
                    marker = dict (color = '#00ff00')
                    )
    reg_J1 = go.Bar(
                    name = 'J+1',
                    x = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J+1')],
                    y = affichage['WORK_GROUP'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J+1')],
                    text = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J+1')],
                    orientation = 'h',
                    marker = dict (color = '#bbbbbb')
                    )
    reg_Ret = go.Bar(
                    name = 'Retard',
                    x = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='Retard')],
                    y = affichage['WORK_GROUP'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='Retard')],
                    text = affichage['Lines'][(affichage['UP']=='VX2') & (affichage['SECTEUR']=='PIGO') & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='Retard')],
                    orientation = 'h',
                    marker = dict (color = '#ff0000')
                    )
    data = [reg_Ret, reg_J0, reg_J1]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       yaxis = {'categoryorder' : 'category descending'},
                       title = 'Urgent',
                       titlefont_size = 24,
                       height = 700,
                       margin = dict(l=150, r=5, t=35, b=0))
    return {
        'data' : data,
        'layout' : layout
    }    

# Refresh écran Andon URGENT SUMMARY
@callback(Output('Andon-outlinesvx2-urg-sum', 'figure'),
              [Input('interval-outlinesvx2', 'n_intervals')])
def update_layout(n):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    colonnes = ['TASK_ID', 'STATUS', 'WORK_GROUP', 'CONSIGNMENT', 'CONSIGNMENT_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'SHIP_BY_DATE',
                'LINE_ID', 'QTY_ORDERED', 'QTY_TASKED', 'QTY_PICKED', 'QTY_SHIPPED', 'V_SHORT', 'UP','ORDER_TYPE']
    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # correction périmètre des UP
    df['UP'].replace(to_replace = ['GLPB'], value = ['VX2'], inplace = True)
    # définition des secteurs
    df['SECTEUR'] = 'PIGO'
    df.loc[df['WORK_ZONE'] == 'PBGL', 'SECTEUR'] = 'PB'
    df.loc[df['WORK_ZONE'].str.contains('^(AEC)'), 'SECTEUR'] = 'AEC'
    df.loc[df['WORK_GROUP'].str.contains('^5'), 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2 GZ-', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2B-DOC', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2R', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P', 'SECTEUR'] = 'FSP'
    df.loc[df['WORK_ZONE'] == 'VX2P-DOC', 'SECTEUR'] = 'FSP'
    # Calcul du retard (en jours)
    aujourdhui = dt.datetime.today().date()
    df['SHIP_BY_DATE'] = pd.to_datetime(df['SHIP_BY_DATE'], yearfirst = True)
    df['SHIP_BY_DATE'] = df['SHIP_BY_DATE'].apply(lambda x: x.date())
    df['GAP'] = df['SHIP_BY_DATE'].apply(lambda x: (x - aujourdhui).days)
    df['BACKLOG'] = 'J+1'
    df.loc[df['GAP'] < 0, 'BACKLOG'] = 'Retard'
    df.loc[df['GAP'] == 0, 'BACKLOG'] = 'J'
    # Gestion spécifique pour les KITS
    df.loc[df['CONSIGNMENT_TIME'] == 'KTS-', 'BACKLOG'] = 'J+1'
    # Calcul du retard lié à l'heure de mise à quai
    maintenant = dt.datetime.now().hour * 100 + dt.datetime.now().minute
    maintenant = str(maintenant)
    if len(maintenant) == 3:
        maintenant = '0' + maintenant
    df.loc[(df['BACKLOG'] == 'J') & (df['CONSIGNMENT_TIME'] < maintenant), 'BACKLOG'] = 'Retard'
    # Définition des données pour les visuels
    retard = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Urgent')&(df['BACKLOG']=='Retard')])
    jour = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Urgent')&(df['BACKLOG']=='J')])
    lendemain = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Urgent')&(df['BACKLOG']=='J+1')])
    total = len(df[(df['UP']=='VX2')&(df['ORDER_TYPE']=='Urgent')])
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [25, 25, 25, 25],
                    header = dict(  values = ['Retard', 'J', 'J+1', 'Total'],
                                    fill = dict(color=['#FF0000', '#00FF00', '#bbbbbb', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 20),
                                    align = ['center'],
                                    height = 35),
                    cells = dict(   values = [retard, jour, lendemain, total],
                                    fill = dict(color='#000000'),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 20), # [couleur_retard], 
                                    align = ['center'] * 5,
                                    height = 35)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 110,
            'margin' : dict(l=150, r=100, t=40, b=0)
        }
    }
