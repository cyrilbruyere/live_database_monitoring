# -*- coding: utf-8 -*-
# author: cyrilbruyere
# maj : 22.5.6

from dash import Dash, dcc, html, Input, Output, callback
# Liste des pages à afficher
from pages import consovx2, packsize, outlines, shipgates, pullflow, shipdocks, export

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = 'Andons DC Lyon'
server = app.server

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Liens entre URL et contenus à afficher
@callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/consovx2':
        return consovx2.layout
    elif pathname == '/packsize':
        return packsize.layout
    elif pathname == '/outlines':
        return outlines.layout
    elif pathname == '/shipgates':
        return shipgates.layout
    elif pathname == '/pullflow':
        return pullflow.layout
    elif pathname == '/shipdocks':
        return shipdocks.layout
    elif pathname == '/export':
        return export.layout
    else:
        return '404'

if __name__ == '__main__':
    app.run_server(debug=False)