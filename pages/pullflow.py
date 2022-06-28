
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
SELECT DISTINCT
	container_id,
	from_loc_id,
	pallet_id,
	consignment,
	to_loc_id,
	MAX(dstamp) AS DSTAMP
FROM dcsdba.move_task 
WHERE site_id ='LDC'
    AND status ='Consol'
    AND from_loc_id LIKE 'WT%'
    AND consignment NOT LIKE 'KTS%'
GROUP BY container_id, from_loc_id, pallet_id, consignment, to_loc_id
"""

# Définition des colonnes à charger
colonnes = ['CONTAINER_ID', 'FROM_LOC_ID', 'PALLET_ID', 'CONSIGNMENT', 'TO_LOC_ID', 'DSTAMP']
quais = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M' ,'N' ,'O' ,'Y']

# Définition de l'affichage et intervalle de refresh
layout = html.Div([
    html.A( id='datetime-pullflow',
            href='https://qlikview.srv.volvo.com/QvAJAXZfc/opendoc.htm?document=gto-sbi-wms2%5Cpullflows.qvw&lang=en-US&host=QVS%40Cluster',
            target='_blank',
            style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.Div([
        html.Div(dcc.Graph(id='left-header-pullflow'), style={'width' : '33%', 'display' : 'inline-block'}),
        html.Div(
            dcc.RadioItems(
                    id = 'radio-pullflow',
                    options = ['All', 'VX1', 'VX2-P'],
                    value = 'All',
                    inline = True,
                    labelStyle = {'color': '#ECECEC'}), style={'width' : '33%', 'display' : 'inline-block'}),
        html.Div(dcc.Graph(id='right-header-pullflow'), style={'width' : '33%', 'display' : 'inline-block'})
            ]),
    html.Hr(),
    html.Div([
        html.Div([
                dcc.Interval(id='interval-pullflow',
                            interval=30000, # milliseconds
                            n_intervals=0
                            ),
                dcc.Store(id='memory-pullflow', data=[], storage_type='local'),
                dcc.Graph(id='Andon-pullflow')
                ]),
        html.Div([
            html.Div([dcc.Graph(id='pullflow-quai-A'), dcc.Graph(id='pullflow-quai-I')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='pullflow-quai-B'), dcc.Graph(id='pullflow-quai-J')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='pullflow-quai-C'), dcc.Graph(id='pullflow-quai-K')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='pullflow-quai-D'), dcc.Graph(id='pullflow-quai-L')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='pullflow-quai-E'), dcc.Graph(id='pullflow-quai-M')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='pullflow-quai-F'), dcc.Graph(id='pullflow-quai-N')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='pullflow-quai-G'), dcc.Graph(id='pullflow-quai-O')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='pullflow-quai-H'), dcc.Graph(id='pullflow-quai-Y')], style={'width' : '12.4%', 'display' : 'inline-block'})      
            ])
    ])
], style={'backgroundColor' : '#000000', 'text-align' : 'center'})

# Refresh automatique date
@callback(Output('datetime-pullflow', 'children'),
          [Input('interval-pullflow', 'n_intervals')])
def update_time(n):
    refresh_time = dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return '{}'.format(refresh_time)

# Refresh data
@callback([Output('memory-pullflow', 'data'),
           Input('interval-pullflow', 'n_intervals'),
           Input('radio-pullflow', 'value')])
def store_data(n, secteur):
    # Connection BD
    conn = wms2.connect()
    # Execution requête
    cursor = conn.cursor()
    cursor.execute(query)
    df = pd.DataFrame(cursor.fetchall(), columns = colonnes)
    # Fermeture connection
    conn.commit()
    conn.close()
    # Ajout colonnes supplémentaires
    df['ORDER_TYPE'] = df['CONSIGNMENT'].str[5:6]
    df['HORAIRE'] = df['CONSIGNMENT'].str[:4]
    df['DSTAMP'] = pd.to_datetime(df['DSTAMP'], yearfirst = True)
    # Définition de la couleur de ponctualité
    present = dt.datetime.now()
    def def_color_backlog(x):
        if present.time() > x:
            return '#FF0000' # RETARD
        elif (present + dt.timedelta(seconds = 15 * 60)).time() > x:
            return '#FA9D00' # A PRIORISER
        else:
            return '#00FF00' # A L'HEURE
    df['HORAIRE_dt'] = pd.to_datetime(df['HORAIRE'], format = '%H%M').dt.time
    df['RET_color'] = df['HORAIRE_dt'].apply(lambda x: def_color_backlog(x))
    df['FONT'] = '#ECECEC'
    df.loc[df['RET_color']=='#00FF00', 'FONT'] = '#000000'
    #Définition de la couleur de priorité
    df['FILL'] = '#000000'
    df.loc[df['ORDER_TYPE']=='D', 'FILL'] = '#0060BF'
    df.loc[df['ORDER_TYPE']=='P', 'FILL'] = '#0060BF'
    df.loc[df['ORDER_TYPE']=='R', 'FILL'] = '#0F9DE8'
    df.loc[df['ORDER_TYPE']=='V', 'FILL'] = '#EEB725'
    # Modification affichage des quais
    df = df.replace(to_replace = ['QUAI-----A', 'QUAI-----B', 'QUAI-----C', 'QUAI-----D', 'QUAI-----E', 'QUAI-----F', 'QUAI-----G', 'QUAI-----H',
                                  'QUAI-----I', 'QUAI-----J', 'QUAI-----K', 'QUAI-----L', 'QUAI-----M', 'QUAI-----N', 'QUAI-----O', 'QUAI-----Y',
                                  'GARE----G6', 'ZONE-DISPO', 'QUAI-G6ALG', 'QUAI---GCA'],
                     value = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                              'I', 'J', 'K', 'L', 'M', 'N', 'O', 'Y',
                              'G6', 'DISP', 'G6A', 'GCA'])
    df = df[df['TO_LOC_ID'].isin(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M' ,'N' ,'O' ,'Y'])]
    df = df.drop(['CONTAINER_ID', 'DSTAMP'], axis = 1)
    df = df.drop_duplicates()
    df['FROM_LOC_ID'] = df['FROM_LOC_ID'].apply(lambda x: x.replace('WT-', ''))
    if secteur != 'All':
        df = df[df['FROM_LOC_ID'] == secteur]
    return [df.to_dict()]

# Refresh histogramme
@callback(Output('Andon-pullflow', 'figure'),
              [Input('memory-pullflow', 'data')])
def update_histo(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Définition du visuel à afficher (figure)
    histo = df[['TO_LOC_ID', 'RET_color', 'PALLET_ID']]
    histo = histo.groupby(['TO_LOC_ID', 'RET_color']).count()
    histo.reset_index(inplace = True)
    pf_ret = go.Bar(
                    name = 'Retard',
                    x = histo['TO_LOC_ID'][histo['RET_color']=='#FF0000'],
                    y = histo['PALLET_ID'][histo['RET_color']=='#FF0000'],
                    text = histo['PALLET_ID'][histo['RET_color']=='#FF0000'],
                    # orientation = 'h',
                    marker = dict (color = '#FF0000'),
                    showlegend = False
                    )
    pf_prio = go.Bar(
                    name = 'A prioriser',
                    x = histo['TO_LOC_ID'][histo['RET_color']=='#FA9D00'],
                    y = histo['PALLET_ID'][histo['RET_color']=='#FA9D00'],
                    text = histo['PALLET_ID'][histo['RET_color']=='#FA9D00'],
                    # orientation = 'h',
                    marker = dict (color = '#FA9D00'),
                    showlegend = False
                    )
    pf_ontime = go.Bar(
                    name = "A l'heure",
                    x = histo['TO_LOC_ID'][histo['RET_color']=='#00FF00'],
                    y = histo['PALLET_ID'][histo['RET_color']=='#00FF00'],
                    text = histo['PALLET_ID'][histo['RET_color']=='#00FF00'],
                    # orientation = 'h',
                    marker = dict (color = '#00FF00'),
                    showlegend = False
                    )
    data = [pf_ret, pf_prio, pf_ontime]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       xaxis = dict(categoryorder = 'category ascending', tickangle = 0),
                       yaxis = dict(ticks='', showticklabels = False),
                       title = '',
                       titlefont_size = 32,
                       height = 200,
                       margin = dict(l=5, r=5, t=10, b=40))
    return {
        'data' : data,
        'layout' : layout
    }

# Refresh LEFT HEADER
@callback(Output('left-header-pullflow', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_left_header(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    header_l = df
    # Liste des colonnes à afficher    
    ontime =  len(header_l[header_l['RET_color']=='#00FF00'])
    prioriser = len(header_l[header_l['RET_color']=='#FA9D00'])
    retard = len(header_l[header_l['RET_color']=='#FF0000'])
    total = len(header_l)
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [25, 25, 25, 25],
                    header = dict(  values = ['', '', '', ''],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 0),
                    cells = dict(   values = [ontime, prioriser, retard, total],
                                    fill = dict(color=['#00FF00', '#FA9D00', '#FF0000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=['#000000', '#ECECEC', '#ECECEC', '#ECECEC'], size = 20), 
                                    align = ['center'] * 4,
                                    height = 33)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 35,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }

# Refresh RIGHT HEADER
@callback(Output('right-header-pullflow', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_left_header(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    header_l = df
    # Liste des colonnes à afficher    
    urgent =  len(header_l[header_l['FILL']=='#0060BF'])
    regulier = len(header_l[header_l['FILL']=='#000000'])
    refill = len(header_l[header_l['FILL']=='#0F9DE8'])
    vor = len(header_l[header_l['FILL']=='#EEB725'])
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [25, 25, 25, 25],
                    header = dict(  values = ['', '', '', ''],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 0),
                    cells = dict(   values = [urgent, regulier, refill, vor],
                                    fill = dict(color=['#0060BF', '#000000', '#0F9DE8', '#EEB725']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=['#ECECEC', '#ECECEC', '#ECECEC', '#ECECEC'], size = 20), 
                                    align = ['center'] * 4,
                                    height = 33)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 35,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }

# Refresh écran quai A ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-A', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='A']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI A', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }

# Refresh écran quai B ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-B', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='B']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI B', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai C ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-C', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='C']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI C', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai D ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-D', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='D']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI D', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai E ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-E', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='E']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI E', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai F ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-F', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='F']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI F', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai G ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-G', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='G']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI G', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai H ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-H', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='H']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI H', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai I ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-I', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='I']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI I', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai J ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-J', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='J']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI J', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai K ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-K', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='K']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI K', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai L ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-L', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='L']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI L', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai M ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-M', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='M']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI M', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai N ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-N', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='N']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI N', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai O ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-O', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='O']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI O', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai Y ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('pullflow-quai-Y', 'figure'),
         [Input('memory-pullflow', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['TO_LOC_ID']=='Y']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'RET_color', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'RET_color', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['RET_color'].values
    # Définition des colonnes à afficher
    shown_columns = ['CONSIGNMENT', 'PALLET_ID']
    fill_color = []
    font_color = []
    n = len(table)
    for col in shown_columns:
        if col in ['CONSIGNMENT']:
            fill_color.append(fill)
            font_color.append(['#ECECEC']*n)
        else:
            fill_color.append(retard)
            font_color.append(font)
    # Alternance des couleurs gris, noir sur les lignes
    for j, col in enumerate(fill_color):
        for i, row in enumerate(col):
            if row == '#000000' and i%2 == 1:
                fill_color[j][i] = '#363636'
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [80, 20],
                    header = dict(  values = ['QUAI Y', 'PAL'],
                                    fill = dict(color=['#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 30),
                    cells = dict(   values = [consignment, palettes],
                                    fill = dict(color=fill_color),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=font_color, size = 15), 
                                    align = ['left', 'center'],
                                    height = 25)
                    )
    data = [trace]
    return {
        'data' : data,
        'layout' : {
            'paper_bgcolor' : '#000000',
            'height' : 260,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }