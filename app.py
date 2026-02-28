import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÃO DE PADRONIZAÇÃO (REFORÇADA) ---
def preparar_dataframe(df):
    # Remove espaços em branco dos nomes das colunas
    df.columns = [str(c).strip() for c in df.columns]
    
    mapeamento = {}
    for col in df.columns:
        c_lower = col.lower()
        # Busca por palavras-chave nos nomes das colunas
        if 'aluno' in c_lower: mapeamento[col] = 'aluno'
        elif 'peso' in c_lower: mapeamento[col] = 'peso'
        elif 'altura' in c_lower or 'estatura' in c_lower: mapeamento[col] = 'altura'
        elif 'genero' in c_lower or 'gênero' in c_lower or 'sexo' in c_lower: mapeamento[col] = 'genero'
        elif 'idade' in c_lower: mapeamento[col] = 'idade'
        elif 'matricula' in c_lower or 'matrícula' in c_lower: mapeamento[col] = 'matricula'
        # Colunas do CSV da OMS
        elif 'z_0' in c_lower: mapeamento[col] = 'z_0'
        elif 'z_2pos' in c_lower: mapeamento[col] = 'z_2pos'
        elif 'z_2neg' in c_lower: mapeamento[col] = 'z_2neg'

    df = df.rename(columns=mapeamento)
    
    # Se a coluna 'genero' existir, limpa o conteúdo dela
    if 'genero' in df.columns:
        df['genero'] = df['genero'].astype(str).str.upper().str.strip()
        
    return df

# --- 2. CARREGAMENTO ---
@st.cache_data
def carregar_dados():
    try:
        # Carrega Referência OMS
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Carrega Planilha de Alunos
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas_limpas = {}
        for nome, df_aba in dict_turmas.items():
            df_p = preparar_dataframe(df_aba)
            # Converte valores para número
            if 'peso' in df_p.columns:
                df_p['peso'] = pd.to_numeric(df_p['peso'], errors='coerce')
            if 'altura' in df_p.columns:
                df_p['altura'] = pd.to_numeric(df_p['altura'], errors='coerce')
            turmas_limpas[nome] = df_p
            
        return df_ref, turmas_limpas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

def calcular_imc(p, a):
    try:
        return round(p / ((a/100)**2), 2) if a > 0 else 0
    except: return 0

# --- INTERFACE ---
st.title("🍎 NutriGestão Escolar - Marina Mendonça")
df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("Configurações")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    modo = st.sidebar.radio("Modo:", ["Ficha Individual", "Relatório da Turma"])

    # Verificação de segurança: checar se as colunas mínimas existem na aba selecionada
    colunas_necessarias = ['aluno', 'peso', 'altura', 'genero']
    colunas_faltando = [c for c in colunas_necessarias if c not in df_atual.columns]

    if colunas_faltando:
        st.error(f"A aba '{aba_sel}' não possui as colunas necessárias ou os nomes estão diferentes. Faltando: {colunas_faltando}")
    else:
        if modo == "Ficha Individual":
            lista = sorted(df_atual['aluno'].dropna().unique())
            escolha = st.sidebar.selectbox("Aluno:", lista)
            dados = df_atual[df_atual['aluno'] == escolha].iloc[0]
            
            p = st.sidebar.number_input("Peso (kg):", value=float(dados.get('peso', 0) or 0))
            a = st.sidebar.number_input("Altura (cm):", value=float(dados.get('altura', 0) or 0))
            g_det = str(dados.get('genero', 'M'))
            sexo = st.sidebar.selectbox("Gênero:", ["Masculino", "Feminino"], index=0 if 'M' in g_det else 1)
            cod_g = "M" if sexo == "Masculino" else "F"

            st.header(f"Aluno(a): {escolha}")
            curva = df_ref[df_ref['genero'] == cod_g]
            
            if not curva.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=curva['altura'], y=curva['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
                fig.add_trace(go.Scatter(x=curva['altura'], y=curva['z_0'], name='Ideal', line=dict(color='green', width=3)))
                fig.add_trace(go.Scatter(x=curva['altura'], y=curva['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))
                fig.add_trace(go.Scatter(x=[a], y=[p], mode='markers', marker=dict(size=15, color='black', symbol='star'), name='Aluno'))
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.header(f"📊 Relatório Coletivo - {aba_sel}")
            # Limpeza focada apenas nas colunas que GARANTIMOS que existem agora
            df_plot = df_atual.dropna(subset=['peso', 'altura', 'genero']).copy()
            df_plot = df_plot[(df_plot['peso'] > 0) & (df_plot['altura'] > 0)]

            if not df_plot.empty:
                df_plot['imc'] = df_plot.apply(lambda x: calcular_imc(x['peso'], x['altura']), axis=1)
                fig_turma = px.scatter(
                    df_plot, x='altura', y='peso', color='genero',
                    hover_data=['aluno', 'imc'],
                    labels={'altura': 'Altura (cm)', 'peso': 'Peso (kg)', 'genero': 'Gênero'}
                )
                st.plotly_chart(fig_turma, use_container_width=True)
                st.dataframe(df_plot[['aluno', 'peso', 'altura', 'imc']], hide_index=True)
            else:
                st.warning("Não há dados válidos para gerar o gráfico desta turma.")
else:
    st.info("Carregando arquivos...")
