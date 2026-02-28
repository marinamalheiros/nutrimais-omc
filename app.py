import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. PADRONIZAÇÃO ---
def preparar_dataframe(df):
    novo_mapeamento = {}
    for col in df.columns:
        nome_min = str(col).lower().strip()
        if 'aluno' in nome_min: novo_mapeamento[col] = 'aluno'
        elif 'matri' in nome_min: novo_mapeamento[col] = 'matricula'
        elif 'idade' in nome_min: novo_mapeamento[col] = 'idade'
        elif 'genero' in nome_min or 'sexo' in nome_min: novo_mapeamento[col] = 'genero'
        elif 'peso' in nome_min: novo_mapeamento[col] = 'peso'
        elif 'altura' in nome_min or 'estatura' in nome_min: novo_mapeamento[col] = 'altura'
        elif 'z_0' in nome_min: novo_mapeamento[col] = 'z_0'
        elif 'z_2pos' in nome_min: novo_mapeamento[col] = 'z_2pos'
        elif 'z_2neg' in nome_min: novo_mapeamento[col] = 'z_2neg'
    
    df = df.rename(columns=novo_mapeamento)
    if 'genero' in df.columns:
        df['genero'] = df['genero'].astype(str).str.upper().str.strip()
    return df

# --- 2. CARREGAMENTO ---
@st.cache_data
def carregar_dados():
    try:
        # Lendo CSV da OMS (ajustado para seu arquivo com ; e ,)
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Lendo Excel dos Alunos
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas_limpas = {}
        for aba, df_aba in dict_turmas.items():
            df_p = preparar_dataframe(df_aba)
            # Converte e força erro para quem não for número virar NaN (vazio)
            df_p['peso'] = pd.to_numeric(df_p['peso'], errors='coerce')
            df_p['altura'] = pd.to_numeric(df_p['altura'], errors='coerce')
            turmas_limpas[aba] = df_p
        return df_ref, turmas_limpas
    except Exception as e:
        st.error(f"Erro nos arquivos: {e}")
        return None, None

def calcular_imc(p, a):
    try:
        return round(p / ((a/100)**2), 2) if a > 0 else 0
    except: return 0

# --- EXECUÇÃO ---
df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("Configurações")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    modo = st.sidebar.radio("Modo:", ["Ficha Individual", "Relatório da Turma"])

    if modo == "Ficha Individual":
        # Remove linhas sem nome para a lista de seleção
        lista = sorted(df_atual['aluno'].dropna().unique())
        escolha = st.sidebar.selectbox("Aluno:", lista)
        dados = df_atual[df_atual['aluno'] == escolha].iloc[0]
        
        p = st.sidebar.number_input("Peso (kg):", value=float(dados.get('peso', 0) or 0))
        a = st.sidebar.number_input("Altura (cm):", value=float(dados.get('altura', 0) or 0))
        g_det = str(dados.get('genero', 'M'))
        sexo = st.sidebar.selectbox("Gênero:", ["Masculino", "Feminino"], index=0 if 'M' in g_det else 1)
        cod_g = "M" if sexo == "Masculino" else "F"

        st.header(f"Aluno(a): {escolha}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Idade", dados.get('idade', '---'))
        c2.metric("IMC", calcular_imc(p, a))
        c3.metric("Gênero", sexo)

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
        
        # --- LIMPEZA CRÍTICA PARA EVITAR VALUEERROR ---
        # 1. Copia e remove linhas onde Peso ou Altura são vazios (NaN)
        df_plot = df_atual.dropna(subset=['peso', 'altura', 'genero']).copy()
        
        # 2. Garante que são números maiores que zero (remove erros de digitação)
        df_plot = df_plot[(df_plot['peso'] > 0) & (df_plot['altura'] > 0)]

        if not df_plot.empty:
            df_plot['imc'] = df_plot.apply(lambda x: calcular_imc(x['peso'], x['altura']), axis=1)
            
            # Criando o gráfico apenas com dados garantidos
            fig_turma = px.scatter(
                df_plot, 
                x='altura', 
                y='peso', 
                color='genero',
                hover_data=['aluno', 'imc'],
                labels={'altura': 'Altura (cm)', 'peso': 'Peso (kg)', 'genero': 'Gênero'}
            )
            st.plotly_chart(fig_turma, use_container_width=True)
            st.dataframe(df_plot[['aluno', 'peso', 'altura', 'imc']], hide_index=True)
        else:
            st.warning("Esta aba do Excel não possui dados suficientes de peso e altura para gerar o gráfico.")

