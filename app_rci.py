import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table

# --- INICIALIZAÇÃO DO APP ---



# --- PREPARAÇÃO DOS DADOS ---
file_name = 'Controle de Processos COPP - 2025 - Página5.csv'
df = pd.read_csv(file_name)

col_cats = ['PROCESSO', 'ÁREA DO CONHECIMENTO', 'UNIDADE', 'EMPRESA/PARCEIRO', 'FUNDAÇÃO']
cols_datas = [c for c in df.columns if c not in col_cats]

for col in cols_datas:
    df[col] = df[col].astype(str).replace(r'[R\$\s\.]', '', regex=True).replace(',', '.', regex=True)
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df_long = df.melt(id_vars=col_cats, value_vars=cols_datas, var_name='Data_Str', value_name='Valor')
df_long['Data'] = pd.to_datetime(df_long['Data_Str'], format='%m/%Y')

# --- ESTILIZAÇÃO ---
COR_PRINCIPAL = "#5c079e"
COR_SUPORTE = "#8cc63f"
COR_FUNDO = "#F8F9FA"
PALETA_DISTINTA = px.colors.qualitative.Alphabet
LOGO_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSpLIQtpxxZeXqbNamdf-y-O_AZYeqwKA5FqA&s"

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# --- INICIALIZAÇÃO DO APP ---
app = Dash(__name__, update_title="Carregando...")

# Definição explícita (MUITO RECOMENDADO)
app.title = "Portal de Desembolsos COPP"

app.layout = html.Div(style={'backgroundColor': COR_FUNDO, 'fontFamily': 'Inter, sans-serif', 'padding': '25px'}, children=[
    # Cabeçalho
    html.Div([
        html.Img(src=LOGO_URL, style={'height': '55px', 'marginRight': '20px', 'borderRadius': '4px'}),
        html.Div([
            html.H2("Gestão de Desembolsos do RCI", style={'fontWeight': '300', 'color': COR_PRINCIPAL, 'margin': '0'}),
            html.P("Coordenação de Projetos e Parcerias", style={'color': '#6C757D', 'fontSize': '12px', 'marginTop': '4px'})
        ], style={'borderLeft': f'2px solid {COR_SUPORTE}', 'paddingLeft': '20px'}),
    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '30px'}),

    html.Div(id='cards-container', style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '12px', 'marginBottom': '25px'}),
    
    # Filtros
    html.Div([
        html.Div([
            html.Div([
                html.Label("PERIODICIDADE", style={'fontSize': '9px', 'fontWeight': 'bold', 'color': '#ADB5BD'}),
                dcc.Dropdown(id='periodo-filtro', value='6MS', clearable=False, style={'fontSize': '11px', 'border': 'none'},
                             options=[{'label': 'Mensal', 'value': 'MS'}, {'label': 'Trimestral', 'value': 'QS'},
                                      {'label': 'Semestral', 'value': '6MS'}, {'label': 'Anual', 'value': 'YS'}])
            ], style={'width': '120px'}),
            *[html.Div([
                html.Label(col.replace('ÁREA DO ', '').split()[-1], style={'fontSize': '9px', 'fontWeight': 'bold', 'color': '#ADB5BD'}),
                dcc.Dropdown(id=f'filtro-{col}', multi=True, placeholder="Todas", style={'fontSize': '11px', 'border': 'none'},
                             options=[{'label': i, 'value': i} for i in sorted(df[col].unique())])
            ], style={'flex': '1', 'minWidth': '150px'}) for col in ['ÁREA DO CONHECIMENTO', 'UNIDADE', 'EMPRESA/PARCEIRO', 'FUNDAÇÃO']]
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '12px', 'alignItems': 'center'})
    ], style={'backgroundColor': '#FFFFFF', 'padding': '12px 18px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.02)', 'marginBottom': '25px'}),

    # Visualização
    html.Div([
        dcc.Loading(dcc.Graph(id='grafico-financeiro', config={'displayModeBar': False}), type="dot", color=COR_PRINCIPAL),
        html.Div(id='tabela-container', style={'marginTop': '10px'})
    ], style={'backgroundColor': '#FFFFFF', 'padding': '15px', 'borderRadius': '10px', 'boxShadow': '0 4px 12px rgba(0,0,0,0.03)'})
])

@app.callback(
    [Output('grafico-financeiro', 'figure'), Output('cards-container', 'children'), Output('tabela-container', 'children')],
    [Input('periodo-filtro', 'value'), Input('filtro-ÁREA DO CONHECIMENTO', 'value'),
     Input('filtro-UNIDADE', 'value'), Input('filtro-EMPRESA/PARCEIRO', 'value'), Input('filtro-FUNDAÇÃO', 'value')]
)
def update_dashboard(periodo, area, unidade, empresa, fundacao):
    dff = df_long.copy()
    if area: dff = dff[dff['ÁREA DO CONHECIMENTO'].isin(area)]
    if unidade: dff = dff[dff['UNIDADE'].isin(unidade)]
    if empresa: dff = dff[dff['EMPRESA/PARCEIRO'].isin(empresa)]
    if fundacao: dff = dff[dff['FUNDAÇÃO'].isin(fundacao)]
    
    dff_agg = dff.groupby(['EMPRESA/PARCEIRO', pd.Grouper(key='Data', freq=periodo)]).agg(
        Valor=('Valor', 'sum'), Qtd_Projetos=('PROCESSO', 'nunique')).reset_index()

    datas_com_valor = dff_agg.groupby('Data')['Valor'].sum().reset_index()
    datas_validas = datas_com_valor[datas_com_valor['Valor'] > 0]['Data']
    
    dff_plot = dff_agg[dff_agg['Data'].isin(datas_validas)].copy()
    dff_plot['Data_Label'] = dff_plot['Data'].dt.strftime('%m/%y')
    dff_plot = dff_plot.sort_values('Data')

    # 1. Cards
    total_val = dff['Valor'].sum()
    resumo_areas = dff.groupby('ÁREA DO CONHECIMENTO')['Valor'].sum().reset_index()
    cards = [html.Div([
        html.P("TOTAL GERAL", style={'fontSize': '9px', 'fontWeight': 'bold', 'color': '#E9ECEF', 'margin': '0'}),
        html.H3(formatar_brl(total_val), style={'fontSize': '15px', 'margin': '4px 0 0 0', 'color': '#FFFFFF'})
    ], style={'backgroundColor': COR_PRINCIPAL, 'padding': '12px', 'borderRadius': '8px', 'minWidth': '150px'})]

    for _, row in resumo_areas.iterrows():
        if row['Valor'] > 0:
            cards.append(html.Div([
                html.P(row['ÁREA DO CONHECIMENTO'], style={'fontSize': '9px', 'fontWeight': 'bold', 'color': '#6C757D', 'margin': '0'}),
                html.H3(formatar_brl(row['Valor']), style={'fontSize': '14px', 'margin': '4px 0 0 0', 'color': COR_PRINCIPAL})
            ], style={'backgroundColor': '#FFFFFF', 'padding': '12px', 'borderRadius': '8px', 'boxShadow': '0 2px 6px rgba(0,0,0,0.02)', 'minWidth': '135px', 'borderLeft': f'3px solid {COR_SUPORTE}', 'flex': '1'}))

    # 2. Gráfico
    fig = px.area(
        dff_plot,
        x='Data_Label',
        y='Valor',
        color='EMPRESA/PARCEIRO',
        template='plotly_white',
        color_discrete_sequence=PALETA_DISTINTA,
        # Passamos Empresa e Qtd para serem usados no hover
        custom_data=['EMPRESA/PARCEIRO', 'Qtd_Projetos']
    )

    # CORREÇÃO DEFINITIVA: Formato BRL + Dados da Empresa
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b> | "      # Nome da Empresa
            "%{customdata[1]} proj. | "        # Qtd Projetos
            "R$ %{y:,.2f}"                     # Valor em BRL (usa o separador global)
            "<extra></extra>"
        )
    )

    fig.update_layout(
        separators=',.', # Define vírgula para decimal e ponto para milhar globalmente
        margin=dict(l=50, r=20, t=10, b=50),
        hovermode="x unified",
        height=350,
        showlegend=True,
        legend=dict(font=dict(size=10), orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        font=dict(family="Inter, sans-serif"),
        yaxis=dict(
            gridcolor='#F2F2F2', 
            tickprefix="R$ ", 
            tickfont=dict(size=11),
            tickformat=',.2f', 
            title=None
        ),
        xaxis=dict(
            type='category',
            gridcolor='#F2F2F2', 
            tickfont=dict(size=11),
            tickangle=0,
            ticklabelstandoff=15,
            title=None
        )
    )

    # 3. Tabela
    df_pivot = dff_agg.pivot(index='EMPRESA/PARCEIRO', columns='Data', values='Valor').fillna(0)
    colunas_com_valor = df_pivot.columns[df_pivot.sum() > 0]
    df_pivot = df_pivot[colunas_com_valor]
    
    df_total = df_pivot.sum().to_frame().T
    df_total.index = ['TOTAL CONSOLIDADO']
    df_final = pd.concat([df_total, df_pivot])
    
    fmt_periodo = {'MS': '%m/%y', 'QS': 'Q%q/%y', '6MS': '%m/%y', 'YS': '%Y'}
    df_final.columns = [c.strftime(fmt_periodo[periodo]) for c in df_final.columns]
    df_final = df_final.reset_index().rename(columns={'index': 'PROJETO'})

    tabela = dash_table.DataTable(
        data=df_final.to_dict('records'),
        columns=[{"name": "Projeto / Parceiro", "id": "PROJETO"}] + 
                [{"name": col, "id": col, "type": "numeric", "format": {"specifier": ",.2f"}} for col in df_final.columns if col != "PROJETO"],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '10px', 'fontSize': '10px', 'fontFamily': 'Inter, sans-serif', 'border': 'none', 'minWidth': '100px'},
        style_header={'backgroundColor': '#F1F3F5', 'fontWeight': 'bold', 'color': COR_PRINCIPAL, 'borderBottom': f'2px solid {COR_SUPORTE}'},
        style_data_conditional=[
            {'if': {'row_index': 0}, 'backgroundColor': '#F9F6FF', 'fontWeight': 'bold', 'color': COR_PRINCIPAL},
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#FFFFFF'}
        ],
        locale_format={'decimal': ',', 'group': '.'}
    )
    
    return fig, cards, tabela

if __name__ == '__main__':
    app.run(debug=True)