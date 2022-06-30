
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
SELECT mt.WORK_GROUP,
       mt.STATUS,
       SUBSTR(mt.CONSIGNMENT, 0, 4) as CONSIGNMENT_TIME,
       mt.PRINT_LABEL_ID,
       mt.WORK_ZONE,
       oh.SHIP_BY_DATE,
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

# Définition des colonnes à charger
colonnes = ['WORK_GROUP', 'STATUS', 'CONSIGNMENT_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'SHIP_BY_DATE', 'UP','ORDER_TYPE']

# Définition de l'affichage et intervalle de refresh
layout = html.Div([
    html.A( id='datetime-outlines',
            href='https://qlikview.srv.volvo.com/QvAJAXZfc/opendoc.htm?document=gto-sbi-wms2%5Coutlines.qvw&lang=en-US&host=QVS%40Cluster',
            target='_blank',
            style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.Div([
        html.Div(id='Régulier', children='Régulier', style={'width' : '26%',
                                                            'display' : 'inline-block',
                                                            'color' : '#ECECEC',
                                                            'text-align' : 'center',
                                                            'font-size' : 40}),
        html.Div(
            dcc.RadioItems(
                    id = 'checklist-outlines',
                    options = ['VX1', 'DE5', 'PIGO', 'FSP', 'PB', 'AEC', 'REA', 'Secteur VX1', 'Secteur VX2', 'Autres', 'Cycle'],
                    value = 'PIGO',
                    inline = True,
                    labelStyle = {'color': '#ECECEC'}), style={'width' : '45%',
                                                               'display' : 'inline-block'}),
        html.Div(id='Urgent', children='Urgent', style={'width' : '26%',
                                                        'display' : 'inline-block',
                                                        'color' : '#ECECEC',
                                                        'text-align' : 'center',
                                                        'font-size' : 40})
            ]),
    html.Hr(),
    html.Div([
        html.Div([
                dcc.Interval(id='interval-outlines',
                            interval=30000, # milliseconds
                            n_intervals=0
                            ),
                dcc.Graph(id='Andon-outlines-reg'),
                dcc.Graph(id='Andon-outlines-reg-sum')
                ], style={'width' : '49%',
                          'display' : 'inline-block'}),
        html.Div([
                dcc.Graph(id='Andon-outlines-urg'),
                dcc.Graph(id='Andon-outlines-urg-sum'),
                dcc.Store(id='memory-outlines', data=[], storage_type='local')
                ], style={'width' : '49%',
                          'display' : 'inline-block'})        
            ])
                    ], style={  'backgroundColor' : '#000000',
                                'text-align' : 'center'
                             })

# Refresh automatique date
@callback(Output('datetime-outlines', 'children'),
              [Input('interval-outlines', 'n_intervals')])
def update_time(n):
    refresh_time = dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return '{}'.format(refresh_time)

# Refresh data
@callback([Output('memory-outlines', 'data'),
           Input('interval-outlines', 'n_intervals')])
def store_data(n):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # correction périmètre des UP
    df['UP'].replace(to_replace = ['VX1-ANNEX'], value = ['VX1'], inplace = True)
    df['UP'].replace(to_replace = ['GLPB'], value = ['VX2'], inplace = True)
    # définition des secteurs
    df['SECTEUR'] = 'Autres'
    # VX1
    df.loc[df['UP'] == 'VX1', 'SECTEUR'] = 'VX1'
    df.loc[((df['UP'] == 'VX1') & (df['WORK_ZONE'] == 'DE5')), 'SECTEUR'] = 'DE5'
    df.loc[((df['UP'] == 'VX1') & (df['WORK_ZONE'] == 'WS-DE5')), 'SECTEUR'] = 'DE5'
    df.loc[((df['UP'] == 'VX1') & (df['WORK_ZONE'] == 'DE6')), 'SECTEUR'] = 'DE5'
    df.loc[((df['UP'] == 'VX1') & (df['WORK_ZONE'] == 'WS-DE6')), 'SECTEUR'] = 'DE5'
    # VX2
    df.loc[df['UP'] == 'VX2', 'SECTEUR'] = 'PIGO'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'] == 'PBGL')), 'SECTEUR'] = 'PB'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'].str.contains('^(AEC)'))), 'SECTEUR'] = 'AEC'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_GROUP'].str.contains('^5'))), 'SECTEUR'] = 'FSP'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'] == 'VX2 GZ-')), 'SECTEUR'] = 'FSP'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'] == 'VX2B-DOC')), 'SECTEUR'] = 'FSP'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'] == 'VX2R')), 'SECTEUR'] = 'FSP'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'] == 'VX2P-DOC')), 'SECTEUR'] = 'FSP'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'] == 'VX2B')), 'SECTEUR'] = 'REA'
    df.loc[((df['UP'] == 'VX2') & (df['WORK_ZONE'] == 'VX2P')), 'SECTEUR'] = 'REA'
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
    return [df.to_dict()]

# Refresh écran Andon REGULIER
@callback(Output('Andon-outlines-reg', 'figure'),
              [Input('memory-outlines', 'data'),
              Input('checklist-outlines', 'value')
              ])
def update_graf_reg(donnees, option_outlines):
    # Cycle
    cycle = ['FSP', 'PB', 'REA']
    secteur_vx1 = ['VX1', 'DE5']
    secteur_vx2 = ['PIGO', 'FSP', 'PB', 'AEC', 'REA']
    freq = dt.datetime.now().minute % 3
    if option_outlines == 'Cycle':
        secteur = [cycle[freq]]
    elif option_outlines == 'Secteur VX1':
        secteur = secteur_vx1
    elif option_outlines == 'Secteur VX2':
        secteur = secteur_vx2
    else:
        secteur = [option_outlines]
    # Restriction aux champs utiles
    df = pd.DataFrame.from_dict(donnees)
    # Regrouper les WORK_GROUP avec l'heure mini de consignment
    df_wg_min_time = df[['WORK_GROUP', 'CONSIGNMENT_TIME']]
    df_wg_min_time = df_wg_min_time.groupby(['WORK_GROUP']).min()
    df_wg_min_time.reset_index(inplace = True)
    df_wg_min_time.rename({'CONSIGNMENT_TIME' : 'MIN_TIME'}, axis = 1, inplace = True)
    df = pd.merge(df, df_wg_min_time, how = 'left', left_on = 'WORK_GROUP', right_on = 'WORK_GROUP')
    # Ajout de l'heure de consignment au work_group 
    df['WORK_GROUP_2'] = df['WORK_GROUP'].str[:10] + '-' + df['MIN_TIME']
    df.loc[df['WORK_GROUP'].str.contains('^500'), 'WORK_GROUP_2'] = df['WORK_GROUP'].str[:5] + '-' + df['WORK_GROUP'].str[6:10]
    df = df.drop(['CONSIGNMENT_TIME', 'MIN_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'WORK_GROUP', 'SHIP_BY_DATE', 'GAP', 'STATUS', 'UP'], axis = 1)
    df.rename({'WORK_GROUP_2' : 'WORK_GROUP'}, axis = 1, inplace = True)
    # Définition des données pour les visuels
    affichage = df.groupby(['ORDER_TYPE', 'SECTEUR', 'WORK_GROUP', 'BACKLOG']).size().reset_index()
    affichage.rename({0 : 'Lines'}, axis = 1, inplace = True)
    # Définition du visuel à afficher (figure)
    reg_J0 = go.Bar(
                    name = 'J',
                    x = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J')],
                    y = affichage['WORK_GROUP'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J')],
                    text = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J')],
                    orientation = 'h',
                    marker = dict (color = '#00ff00')
                    )
    reg_J1 = go.Bar(
                    name = 'J+1',
                    x = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J+1')],
                    y = affichage['WORK_GROUP'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J+1')],
                    text = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='J+1')],
                    orientation = 'h',
                    marker = dict (color = '#bbbbbb')
                    )
    reg_Ret = go.Bar(
                    name = 'Retard',
                    x = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='Retard')],
                    y = affichage['WORK_GROUP'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='Retard')],
                    text = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier') & (affichage['BACKLOG']=='Retard')],
                    orientation = 'h',
                    marker = dict (color = '#ff0000')
                    )
    data = [reg_Ret, reg_J0, reg_J1]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       yaxis = dict(categoryorder = 'category descending',
                                    showticklabels = False if len(affichage[(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Régulier')]) == 0 else True),
                       title = cycle[freq] if option_outlines == 'Cycle' else '',
                       titlefont_size = 24,
                       height = 700,
                       margin = dict(l=150, r=40, t=35, b=0),
                       showlegend = False)
    return {
        'data' : data,
        'layout' : layout
    }

# Refresh écran Andon REGULIER SUMMARY
@callback(Output('Andon-outlines-reg-sum', 'figure'),
              [Input('memory-outlines', 'data'),
              Input('checklist-outlines', 'value')
              ])
def update_summ_reg(donnees, option_outlines):
    # Cycle
    cycle = ['FSP', 'PB', 'REA']
    secteur_vx1 = ['VX1', 'DE5']
    secteur_vx2 = ['PIGO', 'FSP', 'PB', 'AEC', 'REA']
    freq = dt.datetime.now().minute % 3
    if option_outlines == 'Cycle':
        secteur = [cycle[freq]]
    elif option_outlines == 'Secteur VX1':
        secteur = secteur_vx1
    elif option_outlines == 'Secteur VX2':
        secteur = secteur_vx2
    else:
        secteur = [option_outlines]
    # Définition des données pour les visuels
    df = pd.DataFrame.from_dict(donnees)
    retard = len(df[(df['ORDER_TYPE']=='Régulier')&(df['SECTEUR'].isin(secteur))&(df['BACKLOG']=='Retard')])
    jour = len(df[(df['ORDER_TYPE']=='Régulier')&(df['SECTEUR'].isin(secteur))&(df['BACKLOG']=='J')])
    lendemain = len(df[(df['ORDER_TYPE']=='Régulier')&(df['SECTEUR'].isin(secteur))&(df['BACKLOG']=='J+1')])
    total = len(df[(df['ORDER_TYPE']=='Régulier')&(df['SECTEUR'].isin(secteur))])
    erreur = len(df[(df['ORDER_TYPE']=='Régulier')&(df['SECTEUR'].isin(secteur))&(df['STATUS']=='Error')])
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [25, 25, 25, 25, 25],
                    header = dict(  values = ['Retard', 'J', 'J+1', 'Total', 'Erreur'],
                                    fill = dict(color=['#FF0000', '#00FF00', '#BBBBBB', '#000000', '#FDEE00']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 20),
                                    align = ['center'],
                                    height = 35),
                    cells = dict(   values = [retard, jour, lendemain, total, erreur],
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
            'margin' : dict(l=150, r=75, t=40, b=0)
        }
    }

# Refresh écran Andon URGENT
@callback(Output('Andon-outlines-urg', 'figure'),
              [Input('memory-outlines', 'data'),
              Input('checklist-outlines', 'value')
              ])
def update_graf_urg(donnees, option_outlines):
    df = pd.DataFrame.from_dict(donnees)
    # Cycle
    cycle = ['FSP', 'PB', 'REA']
    secteur_vx1 = ['VX1', 'DE5']
    secteur_vx2 = ['PIGO', 'FSP', 'PB', 'AEC', 'REA']
    freq = dt.datetime.now().minute % 3
    if option_outlines == 'Cycle':
        secteur = [cycle[freq]]
    elif option_outlines == 'Secteur VX1':
        secteur = secteur_vx1
    elif option_outlines == 'Secteur VX2':
        secteur = secteur_vx2
    else:
        secteur = [option_outlines]
    # Ajout de l'heure de consignment au work_group
    df['WORK_GROUP_2'] = df['WORK_GROUP'].str[:10] + '-' + df['CONSIGNMENT_TIME']
    df.loc[df['WORK_GROUP'].str.contains('^500'), 'WORK_GROUP_2'] = df['WORK_GROUP'].str[:10]
    # Restriction aux champs utiles
    df = df.drop(['CONSIGNMENT_TIME', 'PRINT_LABEL_ID', 'WORK_ZONE', 'WORK_GROUP', 'SHIP_BY_DATE', 'GAP', 'STATUS', 'UP'], axis = 1)
    df.rename({'WORK_GROUP_2' : 'WORK_GROUP'}, axis = 1, inplace = True)
    # Définition des données pour les visuels
    affichage = df.groupby(['ORDER_TYPE', 'SECTEUR', 'WORK_GROUP', 'BACKLOG']).size().reset_index()
    affichage.rename({0 : 'Lines'}, axis = 1, inplace = True)
    # Définition du visuel à afficher (figure)
    urg_J0 = go.Bar(
                    name = 'J',
                    x = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J')],
                    y = affichage['WORK_GROUP'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J')],
                    text = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J')],
                    orientation = 'h',
                    marker = dict (color = '#00ff00')
                    )
    urg_J1 = go.Bar(
                    name = 'J+1',
                    x = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J+1')],
                    y = affichage['WORK_GROUP'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J+1')],
                    text = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='J+1')],
                    orientation = 'h',
                    marker = dict (color = '#bbbbbb')
                    )
    urg_Ret = go.Bar(
                    name = 'Retard',
                    x = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='Retard')],
                    y = affichage['WORK_GROUP'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='Retard')],
                    text = affichage['Lines'][(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent') & (affichage['BACKLOG']=='Retard')],
                    orientation = 'h',
                    marker = dict (color = '#ff0000')
                    )
    data = [urg_Ret, urg_J0, urg_J1]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       yaxis = dict(categoryorder = 'category descending',
                                    showticklabels = False if len(affichage[(affichage['SECTEUR'].isin(secteur)) & (affichage['ORDER_TYPE']=='Urgent')]) == 0 else True),
                       title = cycle[freq] if option_outlines == 'Cycle' else '',
                       titlefont_size = 24,
                       height = 700,
                       margin = dict(l=190, r=50, t=35, b=0),
                       showlegend = False)
    return {
        'data' : data,
        'layout' : layout
    }    

# Refresh écran Andon URGENT SUMMARY
@callback(Output('Andon-outlines-urg-sum', 'figure'),
              [Input('memory-outlines', 'data'),
              Input('checklist-outlines', 'value')
              ])
def update_summ_urg(donnees, option_outlines):
    df = pd.DataFrame.from_dict(donnees)
    # Cycle
    cycle = ['FSP', 'PB', 'REA']
    secteur_vx1 = ['VX1', 'DE5']
    secteur_vx2 = ['PIGO', 'FSP', 'PB', 'AEC', 'REA']
    freq = dt.datetime.now().minute % 3
    if option_outlines == 'Cycle':
        secteur = [cycle[freq]]
    elif option_outlines == 'Secteur VX1':
        secteur = secteur_vx1
    elif option_outlines == 'Secteur VX2':
        secteur = secteur_vx2
    else:
        secteur = [option_outlines]
    # Définition des données pour les visuels
    retard = len(df[(df['ORDER_TYPE']=='Urgent')&(df['SECTEUR'].isin(secteur))&(df['BACKLOG']=='Retard')])
    jour = len(df[(df['ORDER_TYPE']=='Urgent')&(df['SECTEUR'].isin(secteur))&(df['BACKLOG']=='J')])
    lendemain = len(df[(df['ORDER_TYPE']=='Urgent')&(df['SECTEUR'].isin(secteur))&(df['BACKLOG']=='J+1')])
    total = len(df[(df['ORDER_TYPE']=='Urgent')&(df['SECTEUR'].isin(secteur))])
    erreur = len(df[(df['ORDER_TYPE']=='Urgent')&(df['SECTEUR'].isin(secteur))&(df['STATUS']=='Error')]) 
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [25, 25, 25, 25, 25],
                    header = dict(  values = ['Retard', 'J', 'J+1', 'Total', 'Erreur'],
                                    fill = dict(color=['#FF0000', '#00FF00', '#BBBBBB', '#000000', '#FDEE00']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 20),
                                    align = ['center'],
                                    height = 35),
                    cells = dict(   values = [retard, jour, lendemain, total, erreur],
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
            'margin' : dict(l=150, r=75, t=40, b=0)
        }
    }
