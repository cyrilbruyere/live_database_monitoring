
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
SELECT  mt.container_id,
        mt.consignment,
        oc.pallet_id,
        oc.v_container_type,
        MAX(mt.dstamp) AS DSTAMP,
        mt.from_loc_id as QUAI,
        --mt.v_orig_location_zone as PROVENANCE,
        CASE WHEN SUBSTR(mt.from_loc_id, 6, 1) = 'D' THEN 'Urgent' ELSE 'Régulier'
        END AS TYPE,
        --l.location_id,
        --l.user_def_type_4,
        --l.user_def_type_5,
        l.user_def_type_6 AS DEPART
FROM dcsdba.move_task mt
LEFT JOIN dcsdba.order_container oc ON oc.container_id = mt.container_id
LEFT JOIN dcsdba.location l ON mt.consignment = (SUBSTR(l.user_def_type_5, 1, 2)||SUBSTR(l.user_def_type_5, 4, 2)||'-'||l.location_id)
WHERE mt.site_id = 'LDC'
    AND mt.client_id = 'VOLVO'
    AND mt.from_loc_id <> 'CLIENT-INT'
    AND mt.work_zone = 'QUAI'
    AND mt.container_id IS NOT NULL
    AND oc.client_id = 'VOLVO'
    AND oc.v_site_id = 'LDC'
    AND l.site_id = 'LDC'
    AND l.loc_type = 'ShipDock'
GROUP BY (mt.container_id, mt.consignment, mt.from_loc_id, SUBSTR(mt.from_loc_id, 1, 6), oc.pallet_id, oc.v_container_type, l.location_id, l.user_def_type_4, l.user_def_type_5, l.user_def_type_6)
"""

# Définition des colonnes à charger
colonnes = ['CONTAINER_ID', 'CONSIGNMENT', 'PALLET_ID', 'V_CONTAINER_TYPE', 'DSTAMP', 'QUAI', 'TYPE', 'DEPART']
quais = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M' ,'N' ,'O' ,'Y']

# Définition de l'affichage et intervalle de refresh
layout = html.Div([
    html.A( id='datetime-shipdocks',
            href='https://qlikview.srv.volvo.com/QvAJAXZfc/opendoc.htm?document=gto-sbi-wms2%5Cdocks.qvw&lang=en-US&host=QVS%40Cluster',
            target='_blank',
            style = {'color' : '#ECECEC', 'text-align' : 'center', 'font-size' : 28}),
    html.Div([
        html.Div(dcc.Graph(id='left-header-shipdocks'), style={'width' : '33%', 'display' : 'inline-block'}),
        html.Div(style={'width' : '33%', 'display' : 'inline-block'}),
        html.Div(dcc.Graph(id='right-header-shipdocks'), style={'width' : '33%', 'display' : 'inline-block'})
            ]),
    html.Hr(),
    html.Div([
        html.Div([
                dcc.Interval(id='interval-shipdocks',
                            interval=30000, # milliseconds
                            n_intervals=0
                            ),
                dcc.Store(id='memory-shipdocks', data=[], storage_type='local'),
                dcc.Graph(id='Andon-shipdocks')
                ]),
        html.Div([
            html.Div([dcc.Graph(id='shipdocks-quai-A'), dcc.Graph(id='shipdocks-quai-I')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='shipdocks-quai-B'), dcc.Graph(id='shipdocks-quai-J')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='shipdocks-quai-C'), dcc.Graph(id='shipdocks-quai-K')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='shipdocks-quai-D'), dcc.Graph(id='shipdocks-quai-L')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='shipdocks-quai-E'), dcc.Graph(id='shipdocks-quai-M')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='shipdocks-quai-F'), dcc.Graph(id='shipdocks-quai-N')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='shipdocks-quai-G'), dcc.Graph(id='shipdocks-quai-O')], style={'width' : '12.4%', 'display' : 'inline-block'}),
            html.Div([dcc.Graph(id='shipdocks-quai-H'), dcc.Graph(id='shipdocks-quai-Y')], style={'width' : '12.4%', 'display' : 'inline-block'})      
            ])
    ])
], style={'backgroundColor' : '#000000', 'text-align' : 'center'})

# Refresh automatique date
@callback(Output('datetime-shipdocks', 'children'),
          [Input('interval-shipdocks', 'n_intervals')])
def update_time(n):
    refresh_time = dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    return '{}'.format(refresh_time)

# Refresh data
@callback([Output('memory-shipdocks', 'data'),
           Input('interval-shipdocks', 'n_intervals')])
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
    # Ajout colonnes supplémentaires
    df['ORDER_TYPE'] = df['CONSIGNMENT'].str[5:6]
    df['DSTAMP'] = pd.to_datetime(df['DSTAMP'], yearfirst = True)
    # Ajout du délai J ou J+
    aujourdhui = dt.datetime.today().date()
    maintenant = dt.datetime.now().hour * 100 + dt.datetime.now().minute
    maintenant = str(maintenant)
    if len(maintenant)==3:
        maintenant = '0'+maintenant
    df['HORAIRE'] = df['DEPART'].str[:2] + df['DEPART'].str[-2:]
    df['DSTAMP'] = pd.to_datetime(df['DSTAMP'], yearfirst = True)
    df['DATES'] = df['DSTAMP'].apply(lambda x: x.date())
    df['DELAI'] = '#00FF00'
    df.loc[df['DATES'] < aujourdhui, 'DELAI'] = '#FF0000'
    df.loc[df['HORAIRE'] < maintenant, 'DELAI'] = '#FF0000'
    # Définition de la couleur de ponctualité
    # present = dt.datetime.now()
    # def def_color_backlog(x):
    #     if present.time() > x:
    #         return '#FF0000' # RETARD
    #     elif (present + dt.timedelta(seconds = 15 * 60)).time() > x:
    #         return '#FA9D00' # A PRIORISER
    #     else:
    #         return '#00FF00' # A L'HEURE
    # df['HORAIRE_dt'] = pd.to_datetime(df['HORAIRE'], format = '%H%M').dt.time
    # df['RET_color'] = df['HORAIRE_dt'].apply(lambda x: def_color_backlog(x))
    df['FONT'] = '#ECECEC'
    df.loc[df['DELAI']=='#00FF00', 'FONT'] = '#000000'
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
    df = df[df['QUAI'].isin(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M' ,'N' ,'O' ,'Y'])]
    df = df.drop(['CONTAINER_ID', 'DSTAMP'], axis = 1)
    df = df.drop_duplicates()
    return [df.to_dict()]

# Refresh histogramme
@callback(Output('Andon-shipdocks', 'figure'),
              [Input('memory-shipdocks', 'data')])
def update_histo(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Définition du visuel à afficher (figure)
    histo = df[['QUAI', 'DELAI', 'PALLET_ID']]
    histo = histo.groupby(['QUAI', 'DELAI']).count()
    histo.reset_index(inplace = True)
    sd_j = go.Bar(
                    name = 'Retard',
                    x = histo['QUAI'][histo['DELAI']=='#00FF00'],
                    y = histo['PALLET_ID'][histo['DELAI']=='#00FF00'],
                    text = histo['PALLET_ID'][histo['DELAI']=='#00FF00'],
                    # orientation = 'h',
                    marker = dict (color = '#00FF00'),
                    showlegend = False
                    )
    sd_jplus = go.Bar(
                    name = 'A prioriser',
                    x = histo['QUAI'][histo['DELAI']=='#FF0000'],
                    y = histo['PALLET_ID'][histo['DELAI']=='#FF0000'],
                    text = histo['PALLET_ID'][histo['DELAI']=='#FF0000'],
                    # orientation = 'h',
                    marker = dict (color = '#FF0000'),
                    showlegend = False
                    )
    data = [sd_j, sd_jplus]
    layout = go.Layout(barmode = 'stack',
                       paper_bgcolor = '#000000',
                       plot_bgcolor = '#000000',
                       font_color = '#ECECEC',
                       font_size = 18,
                       xaxis = dict(categoryorder = 'category ascending', tickangle = 0),
                       yaxis = dict(ticks='', showticklabels = False),
                       title = '',
                       titlefont_size = 24,
                       height = 280,
                       margin = dict(l=5, r=5, t=10, b=40))
    return {
        'data' : data,
        'layout' : layout
    }

# Refresh LEFT HEADER
@callback(Output('left-header-shipdocks', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_left_header(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    header_l = df
    # Liste des colonnes à afficher    
    j =  len(header_l[header_l['DELAI']=='#00FF00'])
    jplus = len(header_l[header_l['DELAI']=='#FF0000'])
    total = len(header_l)
    # Définition du visuel à afficher (figure)
    trace = go.Table(
                    columnwidth = [25, 25, 25],
                    header = dict(  values = ['', '', ''],
                                    fill = dict(color=['#000000', '#000000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color = '#ECECEC', size = 16),
                                    align = ['center'],
                                    height = 0),
                    cells = dict(   values = [j, jplus, total],
                                    fill = dict(color=['#00FF00', '#FF0000', '#000000']),
                                    line = dict(color='#777777', width=1),
                                    font = dict(color=['#000000', '#ECECEC', '#ECECEC'], size = 20), 
                                    align = ['center'] * 3,
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
@callback(Output('right-header-shipdocks', 'figure'),
         [Input('memory-shipdocks', 'data')])
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
@callback(Output('shipdocks-quai-A', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='A']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }

# Refresh écran quai B ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-B', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='B']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai C ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-C', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='C']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai D ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-D', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='D']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai E ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-E', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='E']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai F ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-F', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='F']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai G ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-G', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='G']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai H ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-H', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='H']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai I ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-I', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='I']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai J ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-J', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='J']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai K ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-K', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='K']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai L ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-L', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='L']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai M ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-M', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='M']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai N ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-N', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='N']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai O ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-O', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='O']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }
# Refresh écran quai Y ########################################## CODE IDENTIQUE SAUF OUTPUT + SELECTION + HEADER
@callback(Output('shipdocks-quai-Y', 'figure'),
         [Input('memory-shipdocks', 'data')])
def update_quai_a(donnees):
    # Chargement des données en mémoire
    df = pd.DataFrame.from_dict(donnees)
    # Sélection du quai à afficher
    table = df[df['QUAI']=='Y']
    table = table[['PALLET_ID', 'CONSIGNMENT', 'DELAI', 'FONT', 'FILL']]
    table = table.groupby(['CONSIGNMENT', 'DELAI', 'FONT', 'FILL']).count()
    table.reset_index(inplace = True)
    # Liste des colonnes à afficher    
    consignment =  table['CONSIGNMENT'].values
    palettes = table['PALLET_ID'].values
    font = table['FONT'].values
    fill = table['FILL'].values
    retard = table['DELAI'].values
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
            'height' : 350,
            'margin' : dict(l=1, r=1, t=1, b=1)
        }
    }