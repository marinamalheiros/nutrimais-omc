import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. PADRONIZAÇÃO DE COLUNAS ---
def preparar_dataframe(df):
    df.columns = [str(c).lower().replace('ê', 'e').replace('í', 'i').strip() for c in df.columns]
    mapeamento = {
        'aluno': 'aluno', 'matri': 'matricula', 'genero': 'genero', 
        'sexo': 'genero', 'peso': 'peso', 'altura': 'altura', 'idade': 'idade'
    }
    # Renomeia se encontrar parte do nome
    for col in df.columns:
        for chave, valor in mapeamento.items():
            if chave in col:
                df = df.rename(columns={col: valor})
    return df

# --- 2. CARREGAMENTO DA BASE (EXCEL COM ABAS) ---
@st.cache_data
def carregar_dados_escola():
    caminho_referencia = "referencias_oms_completo.csv"
    caminho_alunos = "DADOS - OMC.xlsx"
    
    try:
        df_ref = pd.read_csv(caminho_referencia, sep=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Lê todas as abas do Excel de uma vez
        dict_turmas = pd.read_excel(caminho_alunos, sheet_name=None)
        # Padroniza cada aba
        for aba in dict_turmas:
            dict_turmas[aba] = preparar_dataframe(dict_turmas[aba])
            
        return df_ref, dict_turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos locais: {e}")
        return pd.DataFrame(), {}

# --- 3. LÓGICA DE CÁLCULO ---
def calcular_imc(peso, altura):
    try:
        alt_m = float(altura) / 100
        return round(float(peso) / (alt_m ** 2), 2) if alt_m > 0 else 0
    except: return 0

# --- INTERFACE ---
df_ref, dict_turmas = carregar_dados_escola()

if dict_turmas:
    st.sidebar.header("🏫 Gestão Escolar")
    turma_selecionada = st.sidebar.selectbox("Selecione a Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[turma_selecionada]

    tipo_analise = st.sidebar.radio("Tipo de Análise:", ["Individual por Aluno", "Panorama da Turma"])

    if tipo_analise == "Individual por Aluno":
        # --- FICHA INDIVIDUAL ---
        aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", sorted(df_atual['aluno'].unique()))
        dados = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]

        st.header(f"Ficha: {aluno_nome} ({turma_selecionada})")
        
        # Edição instantânea
        c1, c2, c3 = st.sidebar.columns(3)
        edit_p = st.sidebar.number_input("Peso:", value=float(dados.get('peso', 0) or 0))
        edit_a = st.sidebar.number_input("Altura:", value=float(dados.get('altura', 0) or 0))
        edit_g = st.sidebar.selectbox("Gênero:", ["M", "F"], index=0 if "M" in str(dados.get('genero', 'M')).upper() else 1)

        # Gráfico Individual
        curva = df_ref[df_ref['genero'].str.upper() == edit_g]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_0'], name='Ideal (Z-0)', line=dict(color='green', width=3)))
        fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
        fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))
        
        imc = calcular_imc(edit_p, edit_a)
        fig.add_trace(go.Scatter(x=[edit_a], y=[edit_p], mode='markers+text', text=[f"IMC {imc}"], 
                                 marker=dict(size=15, color='black', symbol='star'), name='Aluno'))
        
        st.plotly_chart(fig, use_container_width=True)

    else:
        # --- PANORAMA DA TURMA ---
        st.header(f"📊 Panorama Geral: {turma_selecionada}")
        
        # Cálculo rápido para a turma
        df_turma = df_atual.copy()
        df_turma['imc'] = df_turma.apply(lambda x: calcular_imc(x.get('peso', 0), x.get('altura', 0)), axis=1)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Distribuição de Peso x Altura")
            fig_turma = px.scatter(df_turma, x='altura', y='peso', text='aluno', color='genero',
                                   title="Alunos da Turma no Espaço Amostral")
            st.plotly_chart(fig_turma, use_container_width=True)
            
        with col2:
            st.subheader("Lista de Alunos")
            st.dataframe(df_turma[['aluno', 'peso', 'altura', 'imc']], hide_index=True)

else:
    st.warning("Garante que o arquivo 'DADOS - OMC.xlsx' está na mesma pasta que este script.")
