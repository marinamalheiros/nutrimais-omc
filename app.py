import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÃO DE PADRONIZAÇÃO DE COLUNAS ---
def preparar_dataframe(df):
    # Limpeza: tudo minúsculo e sem espaços nas pontas
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    mapeamento = {}
    for col in df.columns:
        # Identifica colunas de identificação
        if 'aluno' in col: mapeamento[col] = 'aluno'
        if 'matri' in col: mapeamento[col] = 'matricula'
        if 'idade' in col: mapeamento[col] = 'idade'
        if 'genero' in col or 'sexo' in col: mapeamento[col] = 'genero'
        
        # Identifica a coluna de Eixo X (Altura/Estatura)
        if 'altura' in col or 'estatura' in col or 'height' in col or 'hgt' in col: 
            mapeamento[col] = 'eixo_x_altura' # Nome interno padronizado
            
        # Identifica a coluna de Eixo Y (Peso)
        if 'peso' in col or 'weight' in col or 'wgt' in col: 
            mapeamento[col] = 'peso'
            
        # Identifica as colunas de referência Z-Score
        if 'z_0' in col or 'median' in col: mapeamento[col] = 'z_0'
        if 'z_2pos' in col or 'z2pos' in col: mapeamento[col] = 'z_2pos'
        if 'z_2neg' in col or 'z2neg' in col: mapeamento[col] = 'z_2neg'

    df = df.rename(columns=mapeamento)
    
    # Padroniza Gênero para evitar erros de busca
    if 'genero' in df.columns:
        df['genero'] = df['genero'].astype(str).str.upper().str.strip().fillna('M')
    else:
        df['genero'] = 'M'
        
    return df

# --- 2. CARREGAMENTO DOS DADOS ---
@st.cache_data
def carregar_dados_sistema():
    try:
        # Carrega Referência OMS (Onde você mudou para 'altura')
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Carrega Planilha de Alunos
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        for aba in dict_turmas:
            dict_turmas[aba] = preparar_dataframe(dict_turmas[aba])
            # Garante que peso e altura sejam números (converte vírgula se necessário)
            dict_turmas[aba]['peso'] = pd.to_numeric(dict_turmas[aba]['peso'], errors='coerce')
            dict_turmas[aba]['eixo_x_altura'] = pd.to_numeric(dict_turmas[aba]['eixo_x_altura'], errors='coerce')
            
        return df_ref, dict_turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return pd.DataFrame(), {}

def calcular_imc(peso, altura_cm):
    try:
        alt_m = float(altura_cm) / 100
        return round(float(peso) / (alt_m ** 2), 2) if alt_m > 0 else 0
    except: return 0

# --- INTERFACE ---
st.title("🍎 NutriGestão Escolar - Marina Mendonça")

df_ref, dict_turmas = carregar_dados_sistema()

if not df_ref.empty and dict_turmas:
    st.sidebar.header("🏫 Menu Principal")
    turma_nome = st.sidebar.selectbox("Selecione a Turma:", list(dict_turmas.keys()))
    df_turma = dict_turmas[turma_nome]
    
    modo = st.sidebar.radio("Escolha a visão:", ["Individual (Aluno)", "Coletiva (Turma)"])

    if modo == "Individual (Aluno)":
        aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_turma['aluno'].unique()))
        dados = df_turma[df_turma['aluno'] == aluno_nome].iloc[0]

        # Edição lateral para simulação
        st.sidebar.markdown("---")
        p_edit = st.sidebar.number_input("Peso (kg):", value=float(dados.get('peso', 0) or 0))
        a_edit = st.sidebar.number_input("Altura (cm):", value=float(dados.get('eixo_x_altura', 0) or 0))
        g_orig = str(dados.get('genero', 'M'))
        g_label = st.sidebar.selectbox("Gênero:", ["Masculino", "Feminino"], index=0 if 'M' in g_orig else 1)
        g_cod = 'M' if g_label == "Masculino" else 'F'

        st.header(f"Ficha: {aluno_nome}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Idade", dados.get('idade', '---'))
        imc = calcular_imc(p_edit, a_edit)
        c2.metric("IMC", imc)
        c3.metric("Turma", turma_nome)

        # GRÁFICO OMS
        st.subheader("Análise de Desenvolvimento (OMS)")
        curva = df_ref[df_ref['genero'] == g_cod]

        if not curva.empty:
            fig = go.Figure()
            # Linhas de Referência (Usando o novo nome padronizado 'eixo_x_altura')
            fig.add_trace(go.Scatter(x=curva['eixo_x_altura'], y=curva['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
            fig.add_trace(go.Scatter(x=curva['eixo_x_altura'], y=curva['z_0'], name='Z-0 (Ideal)', line=dict(color='green', width=3)))
            fig.add_trace(go.Scatter(x=curva['eixo_x_altura'], y=curva['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))
            
            # Ponto do Aluno selecionado
            fig.add_trace(go.Scatter(x=[a_edit], y=[p_edit], mode='markers+text', text=["ALUNO"], 
                                     marker=dict(size=15, color='black', symbol='star'), name='Estado Atual'))
            
            fig.update_layout(xaxis_title="Altura (cm)", yaxis_title="Peso (kg)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Não foi possível encontrar as curvas para o gênero selecionado no CSV.")

    else:
        st.header(f"📊 Panorama Geral: {turma_nome}")
        df_turma['imc'] = df_turma.apply(lambda x: calcular_imc(x.get('peso', 0), x.get('eixo_x_altura', 0)), axis=1)
        
        fig_t = px.scatter(df_turma, x='eixo_x_altura', y='peso', color='genero', 
                           hover_data=['aluno', 'imc'],
                           labels={'eixo_x_altura': 'Altura (cm)', 'peso': 'Peso (kg)'})
        st.plotly_chart(fig_t, use_container_width=True)
        
        st.dataframe(df_turma[['aluno', 'peso', 'eixo_x_altura', 'imc']].rename(columns={'eixo_x_altura': 'altura'}), hide_index=True)

else:
    st.warning("Certifique-se de que 'DADOS - OMC.xlsx' e 'referencias_oms_completo.csv' estão na mesma pasta.")
