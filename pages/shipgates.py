
# -*- coding: utf-8 -*-
# author: cyrilbruyere
# maj : 22.5.6

# import des packages
from turtle import ontimer
from config import wms2
import numpy as np
import pandas as pd
import datetime as dt
from dash import dcc, html, Input, Output, callback
import plotly.graph_objs as go
import re

# Définition de la requête SQL
query = """
SELECT  DISTINCT
        SUBSTR(mt.consignment, 6, 99) AS CONSIGNMENT,
        mt.pallet_id,
        CASE WHEN SUBSTR(mt.from_loc_id, 1, 4) = 'QUAI' THEN SUBSTR(mt.from_loc_id, -1, 1)
             WHEN SUBSTR(mt.from_loc_id, 1, 2) = 'WT' THEN SUBSTR(mt.to_loc_id, -1, 1)
             END AS VOIE,
        CASE WHEN SUBSTR(mt.from_loc_id, 1, 4) = 'QUAI' THEN 'QUAI'
             WHEN SUBSTR(mt.from_loc_id, 1, 6) = 'WT-VX1' THEN 'VX1'
             WHEN SUBSTR(mt.from_loc_id, 1, 8) = 'WT-VX2-P' THEN 'VX2'
             END AS STATUS,
        ct.trailer_id AS TRAILER,
        ct.dock_door_id AS GATE,
        l.user_def_type_6 AS DEPART,
        l.user_def_type_6||' '||SUBSTR(ct.trailer_id, 1, 4) AS CAMION,
        mt.dstamp,
        SUBSTR(mt.consignment, 6, 1) as COLOR_TYPE
FROM dcsdba.move_task mt
LEFT JOIN dcsdba.consignment_trailer ct ON (mt.site_id = ct.site_id AND mt.final_loc_id = ct.dock_door_location_id)
LEFT JOIN dcsdba.location l ON (mt.site_id = l.site_id AND mt.final_loc_id = l.location_id)
WHERE mt.site_id = 'LDC'
    AND l.site_id = 'LDC'
    AND ct.site_id = 'LDC'
    AND l.loc_type = 'ShipDock'
    AND mt.client_id = 'VOLVO'
    AND (SUBSTR(mt.from_loc_id, 1, 4) = 'QUAI' OR mt.from_loc_id = 'WT-VX1' OR mt.from_loc_id = 'WT-VX2-P')
    AND mt.task_type ='T'
"""

# Définition des colonnes à charger
colonnes = ['CONSIGNMENT', 'PALLET_ID', 'VOIE', 'STATUS', 'TRAILER', 'GATE', 'DEPART','CAMION', 'DSTAMP', 'COLOR_TYPE']

# Définition de l'affichage et intervalle de refresh
layout = html.Div([
    html.A( id='datetime-shipgates',
            href='https://qlikview.srv.volvo.com/QvAJAXZfc/opendoc.htm?document=gto-sbi-wms2%5Coutlines.qvw&lang=en-US&host=QVS%40Cluster',
            target='_blank',
            style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.Div([
        html.Div(id='left-door', style={'width' : '33%',
                                        'display' : 'inline-block',
                                        'color' : '#ECECEC',
                                        'text-align' : 'center',
                                        'font-size' : 40}),
        html.Div(
            dcc.RadioItems(
                    id = 'radio-shipgates',
                    options = ['1-2', '3-4', '5-6', '7-8', '9-10', '11-12'],
                    value = '1-2',
                    inline = True,
                    labelStyle = {'color': '#ECECEC'}), style={'width' : '33%', 'display' : 'inline-block'}),
        html.Div(id='right-door', style={'width' : '33%',
                                         'display' : 'inline-block',
                                         'color' : '#ECECEC',
                                         'text-align' : 'center',
                                         'font-size' : 40})
            ]),
    html.Hr(),
    html.Div([
        html.Div([
                dcc.Interval(id='interval-shipgates',
                            interval=30000, # milliseconds
                            n_intervals=0
                            ),
                dcc.Graph(id='Andon-shipgates-left'),
                dcc.Graph(id='Andon-shipgates-left-sum')
                ], style={'width' : '49%',
                          'display' : 'inline-block'}),
        html.Div([
                dcc.Graph(id='Andon-shipgates-right'),
                dcc.Graph(id='Andon-shipgates-right-sum'),
                dcc.Store(id='memory-shipgates', data=[], storage_type='local')
                ], style={'width' : '49%',
                          'display' : 'inline-block'})        
            ])
                    ], style={  'backgroundColor' : '#000000',
                                'text-align' : 'center'
                             })

# Refresh automatique date
@callback(Output('datetime-shipgates', 'children'),
              [Input('interval-shipgates', 'n_intervals')])
def update_time(n):
    refresh_time = dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return '{}'.format(refresh_time)

# Refresh automatique porte gauche
@callback(Output('left-door', 'children'),
              [Input('radio-shipgates', 'value')])
def update_left_door(portes):
    left_door = 'PORTE ' + re.findall(r'\d{1,2}$', portes)[0]
    return '{}'.format(left_door)

# Refresh automatique porte droite
@callback(Output('right-door', 'children'),
              [Input('radio-shipgates', 'value')])
def update_right_door(portes):
    right_door = 'PORTE ' + re.findall(r'^\d{1,2}', portes)[0]
    return '{}'.format(right_door)

# Refresh data
@callback([Output('memory-shipgates', 'data'),
           Input('interval-shipgates', 'n_intervals')])
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
    # Ajout du délai J ou J+
    aujourdhui = dt.datetime.today().date()
    maintenant = dt.datetime.now().hour * 100 + dt.datetime.now().minute
    maintenant = str(maintenant)
    if len(maintenant)==3:
        maintenant = '0'+maintenant
    df['HORAIRE'] = df['DEPART'].str[:2] + df['DEPART'].str[-2:]
    df['DSTAMP'] = pd.to_datetime(df['DSTAMP'], yearfirst = True)
    df['DATES'] = df['DSTAMP'].apply(lambda x: x.date())
    df['DELAI'] = 'J'
    df.loc[df['DATES'] < aujourdhui, 'DELAI'] = 'J+'
    df.loc[df['HORAIRE'] < maintenant, 'DELAI'] = 'J+'
    # Calcul du nombre de palettes
    df = df.drop(['DSTAMP', 'HORAIRE', 'DATES'], axis = 1)
    df = df.groupby(['CONSIGNMENT', 'STATUS', 'VOIE', 'TRAILER', 'GATE', 'DEPART', 'CAMION', 'DELAI', 'COLOR_TYPE']).count()
    df.reset_index(inplace = True)
    df.loc[df['STATUS']=='QUAI', 'STATUS'] = df['STATUS'] + ' ' + df['DELAI']
    return [df.to_dict()]

# Refresh écran Andon PORTE GAUCHE
@callback(Output('Andon-shipgates-left', 'figure'),
              [Input('memory-shipgates', 'data'),
              Input('radio-shipgates', 'value')
              ])
def update_graf_left(donnees, portes):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Affichage des palettes sur le quai uniquement
    graf = df[['CAMION', 'PALLET_ID', 'DELAI', 'GATE']][df['STATUS'].str[:4] == 'QUAI']
    # Sélection de la porte à afficher
    graf = graf[graf['GATE']=='PORTE-' + re.findall(r'\d{1,2}$', portes)[0]]
    # Nombre de palettes
    graf = graf[['CAMION', 'DELAI', 'PALLET_ID']].groupby(['CAMION', 'DELAI']).sum()
    graf.reset_index(inplace = True)
    # Définition du visuel à afficher (figure)
    left_J = go.Bar(
                    name = 'J',
                    x = graf['PALLET_ID'][graf['DELAI']=='J'],
                    y = graf['CAMION'][graf['DELAI']=='J'],
                    text = graf['PALLET_ID'][graf['DELAI']=='J'],
                    orientation = 'h',
                    marker = dict (color = '#00FF00'),
                    showlegend = False
                    )
    left_Jplus = go.Bar(
                    name = 'J+',
                    x = graf['PALLET_ID'][graf['DELAI']=='J+'],
                    y = graf['CAMION'][graf['DELAI']=='J+'],
                    text = graf['PALLET_ID'][graf['DELAI']=='J+'],
                    orientation = 'h',
                    marker = dict (color = '#FF0000'),
                    showlegend = False
                    )
    data = [left_J, left_Jplus]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       yaxis = {'categoryorder' : 'category descending'},
                       title = '',
                       titlefont_size = 24,
                       height = 200,
                       margin = dict(l=150, r=5, t=35, b=0))
    return {
        'data' : data,
        'layout' : layout
    }

# Refresh écran Andon PORTE GAUCHE SUMMARY
@callback(Output('Andon-shipgates-left-sum', 'figure'),
              [Input('memory-shipgates', 'data'),
              Input('radio-shipgates', 'value')
              ])
def update_summ_left(donnees, portes):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection de la porte à afficher
    table = df[df['GATE']=='PORTE-' + re.findall(r'\d{1,2}$', portes)[0]]
    # Mise en forme
    table = table.drop(['DELAI'], axis = 1)
    table = pd.pivot_table(table, values='PALLET_ID',
                           index=['CONSIGNMENT', 'VOIE', 'TRAILER', 'GATE', 'DEPART', 'CAMION', 'COLOR_TYPE'],
                           columns=['STATUS'],
                           aggfunc=np.sum)
    table = table.fillna(0)
    table.reset_index(inplace = True)
    if 'VX1' not in table.columns:
        table['VX1'] = 0
    if 'VX2' not in table.columns:
        table['VX2'] = 0
    if 'QUAI J' not in table.columns:
        table['QUAI J'] = 0
    if 'QUAI J+' not in table.columns:
        table['QUAI J+'] = 0
    table = table[['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'VX1', 'VX2', 'QUAI J', 'QUAI J+', 'COLOR_TYPE']]
    table = table.groupby(['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'COLOR_TYPE']).sum()
    table.reset_index(inplace = True)
    table['TOTAL'] = table['VX1'] + table['VX2'] + table['QUAI J'] + table['QUAI J+']
    table = table[table['TOTAL']!=0]
    table = table.replace(to_replace = [0], value = [''])
    # Définition couleurs d'affichage
    table['COLOR'] = '#000000'
    table.loc[table['COLOR_TYPE']=='D', 'COLOR'] = '#0060BF'
    table.loc[table['COLOR_TYPE']=='P', 'COLOR'] = '#0060BF'
    table.loc[table['COLOR_TYPE']=='R', 'COLOR'] = '#0F9DE8'
    table.loc[table['COLOR_TYPE']=='V', 'COLOR'] = '#EEB725'
    table['ONTIME'] = '#000000'
    table.loc[table['QUAI J']!='', 'ONTIME'] = '#00FF00'
    table['FONT'] = '#ECECEC'
    table.loc[table['QUAI J']!='', 'FONT'] = '#000000'
    table['LATE'] = '#000000'
    table.loc[table['QUAI J+']!='', 'LATE'] = '#FF0000'
    # Liste des colonnes à afficher    
    depart = table['DEPART'].values
    trailer = table['TRAILER'].values
    consignment = table['CONSIGNMENT'].values
    voie = table['VOIE'].values
    vx1 = table['VX1'].values
    vx2 = table['VX2'].values
    quaij = table['QUAI J'].values
    quaijplus = table['QUAI J+'].values
    total = table['TOTAL'].values
    couleur = table['COLOR'].values
    ontime = table['ONTIME'].values
    font = table['FONT'].values
    retard = table['LATE'].values
    # Définition des colonnes à afficher
    shown_columns = ['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'VX1', 'VX2', '(J)', '(J+)', 'TOTAL']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT', 'VOIE']:
            fill_color.append(couleur)
            font_color.append(['#ECECEC']*n)
        elif col in ['(J)']:
            fill_color.append(ontime)
            font_color.append(font)
        elif col in ['(J+)']:
            fill_color.append(retard)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(['#000000']*n)
            font_color.append(['#ECECEC']*n)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [20, 35, 45, 15, 15, 15, 15, 15, 15],
                    header = dict(  values = ['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'VX1', 'VX2', '(J)', '(J+)', 'TOTAL'],
                                    fill = dict(color=['#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [depart, trailer, consignment, voie, vx1, vx2, quaij, quaijplus, total],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 16), # [couleur_retard], 
                                    align = ['center'] * 5,
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            #'height' : 110,
            'margin' : dict(l=50, r=15, t=40, b=0)
        }
    }

# PORTE DROITE ##################################### CODE A L'IDENTIQUE DE LA PORTE GAUCHE SAUF FILTRE SUR LA PORTE (paramètre re.findall)
@callback(Output('Andon-shipgates-right', 'figure'),
              [Input('memory-shipgates', 'data'),
              Input('radio-shipgates', 'value')
              ])
def update_graf_right(donnees, portes):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Affichage des palettes sur le quai uniquement
    graf = df[['CAMION', 'PALLET_ID', 'DELAI', 'GATE']][df['STATUS'].str[:4] == 'QUAI']
    # Sélection de la porte à afficher
    graf = graf[graf['GATE']=='PORTE-' + re.findall(r'^\d{1,2}', portes)[0]]
    # Nombre de palettes
    graf = graf[['CAMION', 'DELAI', 'PALLET_ID']].groupby(['CAMION', 'DELAI']).sum()
    graf.reset_index(inplace = True)
    # Définition du visuel à afficher (figure)
    right_J = go.Bar(
                    name = 'J',
                    x = graf['PALLET_ID'][graf['DELAI']=='J'],
                    y = graf['CAMION'][graf['DELAI']=='J'],
                    text = graf['PALLET_ID'][graf['DELAI']=='J'],
                    orientation = 'h',
                    marker = dict (color = '#00FF00'),
                    showlegend = False
                    )
    right_Jplus = go.Bar(
                    name = 'J+',
                    x = graf['PALLET_ID'][graf['DELAI']=='J+'],
                    y = graf['CAMION'][graf['DELAI']=='J+'],
                    text = graf['PALLET_ID'][graf['DELAI']=='J+'],
                    orientation = 'h',
                    marker = dict (color = '#FF0000'),
                    showlegend = False
                    )
    data = [right_J, right_Jplus]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       yaxis = {'categoryorder' : 'category descending'},
                       title = '',
                       titlefont_size = 24,
                       height = 200,
                       margin = dict(l=150, r=5, t=35, b=0))
    return {
        'data' : data,
        'layout' : layout
    }    

# PORTE DROITE SUMMARY ##################################### CODE A L'IDENTIQUE DE LA PORTE GAUCHE SUMMARY SAUF FILTRE SUR LA PORTE (paramètre re.findall)
@callback(Output('Andon-shipgates-right-sum', 'figure'),
              [Input('memory-shipgates', 'data'),
              Input('radio-shipgates', 'value')
              ])
def update_summ_right(donnees, portes):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Chargement des données en mémoire
    table = df[df['GATE']=='PORTE-' + re.findall(r'^\d{1,2}', portes)[0]]
    # Mise en forme
    table = table.drop(['DELAI'], axis = 1)
    table = pd.pivot_table(table, values='PALLET_ID',
                           index=['CONSIGNMENT', 'VOIE', 'TRAILER', 'GATE', 'DEPART', 'CAMION', 'COLOR_TYPE'],
                           columns=['STATUS'],
                           aggfunc=np.sum)
    table = table.fillna(0)
    table.reset_index(inplace = True)
    if 'VX1' not in table.columns:
        table['VX1'] = 0
    if 'VX2' not in table.columns:
        table['VX2'] = 0
    if 'QUAI J' not in table.columns:
        table['QUAI J'] = 0
    if 'QUAI J+' not in table.columns:
        table['QUAI J+'] = 0
    table = table[['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'VX1', 'VX2', 'QUAI J', 'QUAI J+', 'COLOR_TYPE']]
    table = table.groupby(['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'COLOR_TYPE']).sum()
    table.reset_index(inplace = True)
    table['TOTAL'] = table['VX1'] + table['VX2'] + table['QUAI J'] + table['QUAI J+']
    table = table[table['TOTAL']!=0]
    table = table.replace(to_replace = [0], value = [''])
    # Définition couleurs d'affichage
    table['COLOR'] = '#000000'
    table.loc[table['COLOR_TYPE']=='D', 'COLOR'] = '#0060BF'
    table.loc[table['COLOR_TYPE']=='P', 'COLOR'] = '#0060BF'
    table.loc[table['COLOR_TYPE']=='R', 'COLOR'] = '#0F9DE8'
    table.loc[table['COLOR_TYPE']=='V', 'COLOR'] = '#EEB725'
    table['ONTIME'] = '#000000'
    table.loc[table['QUAI J']!='', 'ONTIME'] = '#00FF00'
    table['FONT'] = '#ECECEC'
    table.loc[table['QUAI J']!='', 'FONT'] = '#000000'
    table['LATE'] = '#000000'
    table.loc[table['QUAI J+']!='', 'LATE'] = '#FF0000'
    # Liste des colonnes à afficher    
    depart = table['DEPART'].values
    trailer = table['TRAILER'].values
    consignment = table['CONSIGNMENT'].values
    voie = table['VOIE'].values
    vx1 = table['VX1'].values
    vx2 = table['VX2'].values
    quaij = table['QUAI J'].values
    quaijplus = table['QUAI J+'].values
    total = table['TOTAL'].values
    couleur = table['COLOR'].values
    ontime = table['ONTIME'].values
    font = table['FONT'].values
    retard = table['LATE'].values
    # Définition des colonnes à afficher
    shown_columns = ['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'VX1', 'VX2', '(J)', '(J+)', 'TOTAL']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT', 'VOIE']:
            fill_color.append(couleur)
            font_color.append(['#ECECEC']*n)
        elif col in ['(J)']:
            fill_color.append(ontime)
            font_color.append(font)
        elif col in ['(J+)']:
            fill_color.append(retard)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(['#000000']*n)
            font_color.append(['#ECECEC']*n)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [20, 35, 45, 15, 15, 15, 15, 15, 15],
                    header = dict(  values = ['DEPART', 'TRAILER', 'CONSIGNMENT', 'VOIE', 'VX1', 'VX2', '(J)', '(J+)', 'TOTAL'],
                                    fill = dict(color=['#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [depart, trailer, consignment, voie, vx1, vx2, quaij, quaijplus, total],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 16), # [couleur_retard], 
                                    align = ['center'] * 5,
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            #'height' : 110,
            'margin' : dict(l=50, r=15, t=40, b=0)
        }
    }
