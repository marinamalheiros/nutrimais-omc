import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÃO DE PADRONIZAÇÃO DE COLUNAS ---
def preparar_dataframe(df):
    colunas_originais = df.columns
    novo_mapeamento = {}
    
    for col in colunas_originais:
        nome_min = str(col).lower().strip()
        
        if 'aluno' in nome_min: novo_mapeamento[col] = 'aluno'
        elif 'matri' in nome_min: novo_mapeamento[col] = 'matricula'
        elif 'idade' in nome_min: novo_mapeamento[col] = 'idade'
        elif 'genero' in nome_min or 'sexo' in nome_min: novo_mapeamento[col] = 'genero'
        elif 'peso' in nome_min: novo_mapeamento[col] = 'peso'
        elif 'altura' in nome_min or 'estatura' in nome_min: novo_mapeamento[col] = 'altura'
        elif 'z_0' in nome_min or 'median' in nome_min: novo_mapeamento[col] = 'z_0'
        elif 'z_2pos' in nome_min or 'z2pos' in nome_min: novo_mapeamento[col] = 'z_2pos'
        elif 'z_2neg' in nome_min or 'z2neg' in nome_min: novo_mapeamento[col] = 'z_2neg'

    df = df.rename(columns=novo_mapeamento)
    
    if 'genero' in df.columns:
        df['genero'] = df['genero'].astype(str).str.upper().str.strip().fillna('M')
    else:
        df['genero'] = 'M'
        
    return df

# --- 2. CARREGAMENTO DOS DADOS COM TRATAMENTO DE ERRO DE TOKENIZAÇÃO ---
@st.cache_data
def carregar_dados():
    try:
        # SOLUÇÃO PARA O ERRO: sep=',' e on_bad_lines='skip'
        # Isso faz o Python pular a linha 3 que está com erro em vez de travar o app
        df_ref = pd.read_csv(
            "referencias_oms_completo.csv", 
            sep=',', 
            on_bad_lines='skip', 
            encoding='utf-8'
        )
        df_ref = preparar_dataframe(df_ref)
        
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        
        turmas_processadas = {}
        for nome_aba, df_aba in dict_turmas.items():
            df_limpo = preparar_dataframe(df_aba)
            df_limpo['peso'] = pd.to_numeric(df_limpo['peso'], errors='coerce')
            df_limpo['altura'] = pd.to_numeric(df_limpo['altura'], errors='coerce')
            turmas_processadas[nome_aba] = df_limpo
            
        return df_ref, turmas_processadas
    except Exception as e:
        st.error(f"Erro crítico ao ler os arquivos: {e}")
        return None, None

def calcular_imc(peso, altura_cm):
    try:
        alt_m = float(altura_cm) / 100
        return round(float(peso) / (alt_m ** 2), 2) if alt_m > 0 else 0
    except: return 0

# --- INTERFACE ---
st.title("🍎 NutriGestão Escolar - Marina Mendonça")

df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("🏫 Menu Escolar")
    aba_selecionada = st.sidebar.selectbox("Selecione a Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_selecionada]
    
    modo = st.sidebar.radio("Modo de exibição:", ["Ficha Individual", "Relatório da Turma"])

    if modo == "Ficha Individual":
        lista_alunos = sorted(df_atual['aluno'].dropna().unique())
        aluno_escolhido = st.sidebar.selectbox("Selecione o Aluno:", lista_alunos)
        
        dados_aluno = df_atual[df_atual['aluno'] == aluno_escolhido].iloc[0]
        
        st.sidebar.markdown("---")
        p_val = st.sidebar.number_input("Peso (kg):", value=float(dados_aluno.get('peso', 0) or 0), step=0.1)
        a_val = st.sidebar.number_input("Altura (cm):", value=float(dados_aluno.get('altura', 0) or 0), step=0.1)
        
        gen_orig = str(dados_aluno.get('genero', 'M')).upper()
        sexo_sel = st.sidebar.selectbox("Gênero:", ["Masculino", "Feminino"], index=0 if 'M' in gen_orig else 1)
        cod_genero = "M" if sexo_sel == "Masculino" else "F"

        st.header(f"Paciente: {aluno_escolhido}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Idade", dados_aluno.get('idade', '---'))
        c2.metric("IMC Calculado", calcular_imc(p_val, a_val))
        c3.metric("Gênero", sexo_sel)

        st.subheader("Curva de Crescimento (OMS)")
        curva_oms = df_ref[df_ref['genero'] == cod_genero]

        if not curva_oms.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=curva_oms['altura'], y=curva_oms['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
            fig.add_trace(go.Scatter(x=curva_oms['altura'], y=curva_oms['z_0'], name='Ideal (Z-0)', line=dict(color='green', width=3)))
            fig.add_trace(go.Scatter(x=curva_oms['altura'], y=curva_oms['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))
            
            fig.add_trace(go.Scatter(x=[a_val], y=[p_val], mode='markers+text', 
                                     text=["ALUNO"], textposition="top center",
                                     marker=dict(size=15, color='black', symbol='star'), name='Avaliação Atual'))
            
            fig.update_layout(xaxis_title="Altura (cm)", yaxis_title="Peso (kg)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Dados de referência da OMS não localizados para este gênero.")

    else:
        st.header(f"📊 Relatório Coletivo - {aba_selecionada}")
        df_geral = df_atual.copy()
        df_geral['imc'] = df_geral.apply(lambda x: calcular_imc(x.get('peso', 0), x.get('altura', 0)), axis=1)
        
        fig_turma = px.scatter(df_geral, x='altura', y='peso', color='genero', 
                               hover_data=['aluno', 'imc'], title="Dispersão da Turma")
        st.plotly_chart(fig_turma, use_container_width=True)
        
        st.dataframe(df_geral[['aluno', 'matricula', 'peso', 'altura', 'imc']], use_container_width=True, hide_index=True)

else:
    st.info("💡 Verifique os arquivos 'DADOS - OMC.xlsx' e 'referencias_oms_completo.csv' na pasta.")
