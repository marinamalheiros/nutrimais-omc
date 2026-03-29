import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re

# Configuração da Página
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

# --- ESTILO CSS CUSTOMIZADO ---
st.markdown(
    """
    <style>
    .stApp { background-color: #F3E5F5; }
    [data-testid="stMetricValue"] { color: #4A148C; }
    .status-sidebar {
        color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 10px;
    }
    .status-box {
        padding: 8px; border-radius: 5px; text-align: center; font-weight: bold; color: white; margin-bottom: 25px; font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. FUNÇÕES DE APOIO ---
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

def classificar_oms_geral(valor_y, ref_linha):
    if ref_linha.empty: return "Dados Insuficientes", "#808080"
    try:
        v = float(valor_y)
        ref = ref_linha.iloc[0]
        if v < ref['z_3neg']: return "Muito Baixo / Magreza Ac.", "#8B0000"
        elif v < ref['z_2neg']: return "Baixo / Magreza", "#FF4500"
        elif v < ref['z_1pos']: return "Eutrofia", "#2E8B57"
        elif v <= ref['z_2pos']: return "Risco de Sobrepeso", "#FFD700"
        elif v <= ref['z_3pos']: return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except: return "Erro", "#808080"

@st.cache_data
def carregar_dados():
    try:
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        if 'tipo' in df_ref.columns:
            df_ref['tipo'] = df_ref['tipo'].astype(str).str.strip().str.lower()
        if 'genero' in df_ref.columns:
            df_ref['genero'] = df_ref['genero'].astype(str).str.strip().str.upper()
        df_ref = preparar_dataframe(df_ref)
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}"); return None, None

# --- FUNÇÃO PARA CRIAR GRÁFICOS MINI COM RÓTULOS ---
def criar_grafico_painel(tipo_nome, gen, idade_m, peso, altura, df_ref):
    map_p = {
        "peso_altura": (altura, peso, "Altura (cm)", "Peso (kg)"),
        "imc_idade": (idade_m, round(peso/((altura/100)**2),2) if altura>0 else 0, "Idade (Meses)", "IMC"),
        "peso_idade": (idade_m, peso, "Idade (Meses)", "Peso (kg)"),
        "estatura_idade": (idade_m, altura, "Idade (Meses)", "Altura (cm)")
    }
    val_x, val_y, lab_x, lab_y = map_p[tipo_nome]
    
    curva = df_ref[(df_ref['genero'] == gen) & (df_ref['tipo'] == tipo_nome)]
    col_x_ref = 'altura' if tipo_nome == 'peso_altura' else 'idade_meses'
    idx = (curva[col_x_ref] - val_x).abs().idxmin()
    status, cor = classificar_oms_geral(val_y, curva.loc[[idx]])

    fig = go.Figure()
    # Linhas de referência
    for col_z, color in [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]:
        fig.add_trace(go.Scatter(x=curva[col_x_ref], y=curva[col_z], line=dict(color=color, width=1, dash='dot' if col_z!='z_0' else 'solid'), mode='lines', hoverinfo='skip'))
    
    # Ponto do Aluno com RÓTULO DE DADOS
    fig.add_trace(go.Scatter(
        x=[val_x], y=[val_y], 
        mode='markers+text', 
        text=[f"<b>{val_y}</b>"], # Rótulo do valor
        textposition="top center",
        marker=dict(size=12, color=cor, line=dict(width=2, color='white')),
        name="Avaliação"
    ))
    
    fig.update_layout(
        title=f"<b>{tipo_nome.replace('_',' ').upper()}</b>", 
        height=280, margin=dict(l=10, r=10, t=40, b=10), 
        template="plotly_white", showlegend=False,
        xaxis=dict(title=lab_x, title_font=dict(size=10)),
        yaxis=dict(title=lab_y, title_font=dict(size=10))
    )
    return fig, status, cor

# --- 2. CABEÇALHO ---
st.title("🍎 Acompanhamento Nutricional - O Mundo da Criança")
st.markdown("##### pela Nutricionista Marina Malheiros Mendonça - CRN 5 21456 🍐🍒")

df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.markdown("### 🥗 Seleção")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_atual['aluno'].dropna().unique()))
    modo = st.sidebar.radio("Ver:", ["Ficha Individual", "Relatório Coletivo"])

    dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen_aluno = "M" if "M" in str(dados_aluno.get('genero', 'M')).upper() else "F"
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **{aluno_nome}**")
    st.sidebar.write(f"📅 Idade: **{dados_aluno.get('idade_original', 'N/A')}**")

    if modo == "Ficha Individual":
        st.header(f"Ficha: {aluno_nome}")
        
        # Grade 2x2 para visualização compacta
        grade = st.columns(2)
        params = ["peso_altura", "imc_idade", "peso_idade", "estatura_idade"]
        
        for i, p_nome in enumerate(params):
            with grade[i % 2]:
                fig, status, cor = criar_grafico_painel(p_nome, gen_aluno, dados_aluno['idade_meses'], dados_aluno['peso'], dados_aluno['altura'], df_ref)
                st.plotly_chart(fig, use_container_width=True)
                # Status fixo baseado nos dados originais abaixo do gráfico
                st.markdown(f"<div class='status-box' style='background-color:{cor};'>{status}</div>", unsafe_allow_html=True)

    else:
        st.header(f"📊 Panorama: {aba_sel}")
        # (Restante do código do Relatório Coletivo permanece igual ao seu original)
