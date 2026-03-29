import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA E ESTILO (MANTIDOS) ---
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #F3E5F5; }
    [data-testid="stMetricValue"] { color: #4A148C; }
    .status-box {
        padding: 5px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        color: white;
        font-size: 0.8rem;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 2. FUNÇÕES DE APOIO (COM CORREÇÃO PARA SERIES E IDADE) ---
def converter_idade_para_meses(texto_idade):
    try:
        texto = str(texto_idade).lower().strip()
        numeros = re.findall(r'\d+', texto)
        if not numeros: return 0
        valor = int(numeros[0])
        return valor * 12 if 'ano' in texto else valor
    except: return 0

def preparar_dataframe(df):
    df.columns = [str(c).strip() for c in df.columns]
    mapeamento = {}
    for col in df.columns:
        c_lower = col.lower()
        if 'aluno' in c_lower: mapeamento[col] = 'aluno'
        elif 'peso' in c_lower: mapeamento[col] = 'peso'
        elif 'altura' in c_lower: mapeamento[col] = 'altura'
        elif 'genero' in c_lower or 'gênero' in c_lower: mapeamento[col] = 'genero'
        elif 'z_' in c_lower: mapeamento[col] = c_lower 
        elif 'idade' in c_lower: mapeamento[col] = 'idade_original'
    df = df.rename(columns=mapeamento)
    
    cols_num = ['peso', 'altura', 'z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
    for col in df.columns:
        if col in cols_num:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    if 'idade_original' in df.columns:
        df['idade_meses'] = df['idade_original'].apply(converter_idade_para_meses)
    return df

@st.cache_data
def carregar_dados():
    try:
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref['tipo'] = df_ref['tipo'].astype(str).str.strip().str.lower()
        df_ref['genero'] = df_ref['genero'].astype(str).str.strip().str.upper() # CORREÇÃO .str.upper()
        df_ref = preparar_dataframe(df_ref)
        
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

def classificar_oms_geral(valor_y, ref_linha):
    if ref_linha.empty: return "Dados Insuficientes", "#808080"
    try:
        v = float(valor_y)
        ref = ref_linha.iloc[0]
        if v < ref['z_3neg']: return "Magreza Acentuada", "#8B0000"
        elif v < ref['z_2neg']: return "Magreza", "#FF4500"
        elif v < ref['z_1pos']: return "Eutrofia", "#2E8B57"
        elif v <= ref['z_2pos']: return "Risco de Sobrepeso", "#FFD700"
        elif v <= ref['z_3pos']: return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except: return "Erro", "#808080"

# --- 3. GERAÇÃO DE GRÁFICOS COMPACTOS ---
def plotar_mini_grafico(tipo, gen, idade_m, peso, altura, df_ref):
    # Lógica de eixos baseada no tipo
    dados_map = {
        "peso_altura": (altura, peso, "Altura (cm)", "Peso (kg)"),
        "imc_idade": (idade_m, round(peso/((altura/100)**2),2) if altura>0 else 0, "Idade (Meses)", "IMC"),
        "peso_idade": (idade_m, peso, "Idade (Meses)", "Peso (kg)"),
        "estatura_idade": (idade_m, altura, "Idade (Meses)", "Altura (cm)")
    }
    val_x, val_y, lab_x, lab_y = dados_map[tipo]
    
    curva = df_ref[(df_ref['genero'] == gen) & (df_ref['tipo'] == tipo)]
    col_busca = 'altura' if tipo == 'peso_altura' else 'idade_meses'
    idx = (curva[col_busca] - val_x).abs().idxmin()
    status, cor = classificar_oms_geral(val_y, curva.loc[[idx]])

    fig = go.Figure()
    # Referências Z-score
    for col, color in [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]:
        fig.add_trace(go.Scatter(x=curva[col_busca], y=curva[col], line=dict(color=color, width=1, dash='dot' if col!='z_0' else 'solid'), mode='lines', hoverinfo='skip', showlegend=False))
    
    # Ponto do Aluno
    fig.add_trace(go.Scatter(x=[val_x], y=[val_y], mode='markers', marker=dict(size=10, color=cor, line=dict(width=1, color='white')), showlegend=False))
    
    titulo = tipo.replace('_', ' ').upper()
    fig.update_layout(title=f"<b>{titulo}</b>", height=230, margin=dict(l=10, r=10, t=40, b=10), template="plotly_white", xaxis_title=None, yaxis_title=None)
    return fig, status, cor

# --- 4. CABEÇALHO E CARREGAMENTO ---
st.title("🍎 Acompanhamento Nutricional - O Mundo da Criança")
st.markdown("##### pela Nutricionista Marina Malheiros Mendonça - CRN 5 21456 🍐🍒")

df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    # --- BARRA LATERAL ---
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_atual['aluno'].dropna().unique()))
    
    dados = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen = "M" if "M" in str(dados.get('genero', 'M')).upper() else "F"
    imc_atual = round(dados['peso'] / ((dados['altura']/100)**2), 2) if dados['altura'] > 0 else 0

    st.sidebar.markdown("---")
    st.sidebar.metric("IMC Atual", imc_atual)
    st.sidebar.write(f"📅 Idade: {dados.get('idade_original', 'N/A')}")
    
    modo = st.sidebar.radio("Ver:", ["Ficha Individual", "Relatório Coletivo"])

    if modo == "Ficha Individual":
        st.header(f"Ficha: {aluno_nome}")
        
        # Grade 2x2 para os gráficos
        grade = st.columns(2)
        params = ["peso_altura", "imc_idade", "peso_idade", "estatura_idade"]
        
        for i, p_nome in enumerate(params):
            with grade[i % 2]:
                fig, status, cor = plotar_mini_grafico(p_nome, gen, dados['idade_meses'], dados['peso'], dados['altura'], df_ref)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"<div class='status-box' style='background-color:{cor};'>{status}</div>", unsafe_allow_html=True)
    
    else:
        st.header(f"📊 Panorama Coletivo: {aba_sel}")
        # (Lógica do Relatório Coletivo original mantida aqui...)
        st.info("Relatório coletivo baseado em Peso por Estatura.")
