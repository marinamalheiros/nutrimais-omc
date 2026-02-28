import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="NutriGestão Escolar", layout="wide")

# --- CARREGAMENTO DE REFERÊNCIAS ---
@st.cache_data
def carregar_referencias():
    # Carrega o CSV unificado que limpamos anteriormente
    return pd.read_csv("referencias_oms_completo.csv")

def calcular_imc(peso, altura_cm):
    try:
        altura_m = float(altura_cm) / 100
        return round(float(peso) / (altura_m ** 2), 2)
    except:
        return 0

# --- INTERFACE PRINCIPAL ---
st.title("🍎 Dashboard Nutricional Infantil")

try:
    df_ref = carregar_referencias()
    
    # Upload da Planilha de Alunos (Maternal, Jardim, etc.)
    uploaded_file = st.sidebar.file_uploader("Subir Planilha da Turma", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            df_alunos = pd.read_csv(uploaded_file)
        else:
            df_alunos = pd.read_excel(uploaded_file)
        
        # Seleção do Aluno
        aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", df_alunos['Aluno'].unique())
        aluno_original = df_alunos[df_alunos['Aluno'] == aluno_nome].iloc[0]

        # --- SEÇÃO DE EDIÇÃO (SIDEBAR) ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📝 Editar Informações")
        st.sidebar.info("Ajuste os valores abaixo para atualizar o gráfico em tempo real.")
        
        # Campos de edição pré-preenchidos com os dados da planilha
        peso_edit = st.sidebar.number_input("Peso (kg):", value=float(aluno_original['Peso (kg)']), step=0.1)
        altura_edit = st.sidebar.number_input("Altura (cm):", value=float(aluno_original['Altura (cm)']), step=0.1)
        genero_edit = st.sidebar.selectbox("Gênero:", ["M", "F"], index=0 if aluno_original['Gênero'] == "M" else 1)
        idade_edit = st.sidebar.text_input("Idade:", value=str(aluno_original['Idade']))

        # Cálculo do IMC com dados editados
        imc_atual = calcular_imc(peso_edit, altura_edit)

        # --- EXIBIÇÃO DO DASHBOARD ---
        st.header(f"Ficha: {aluno_nome}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Matrícula", aluno_original['Matrícula'])
        m2.metric("Idade", idade_edit)
        m3.metric("Peso Atual", f"{peso_edit} kg")
        m4.metric("Altura Atual", f"{altura_edit} cm")

        # --- GRÁFICO DE CRESCIMENTO ---
        st.markdown("---")
        st.subheader("Posição na Curva de Referência (Peso x Estatura)")
        
        # Filtra a curva da OMS pelo gênero (M ou F)
        curva_visual = df_ref[df_ref['genero'] == genero_edit]

        fig = go.Figure()

        # Adicionando as linhas de Escore-Z
        fig.add_trace(go.Scatter(x=curva_visual['estatura'], y=curva_visual['z_2pos'], 
                                 name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
        fig.add_trace(go.Scatter(x=curva_visual['estatura'], y=curva_visual['z_0'], 
                                 name='Z-0 (Mediana)', line=dict(color='green', width=3)))
        fig.add_trace(go.Scatter(x=curva_visual['estatura'], y=curva_visual['z_2neg'], 
                                 name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))

        # Ponto do
