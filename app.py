import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÕES DE APOIO ---
def preparar_dataframe(df):
    df.columns = [str(c).strip() for c in df.columns]
    mapeamento = {}
    for col in df.columns:
        c_lower = col.lower()
        if 'aluno' in c_lower: mapeamento[col] = 'aluno'
        elif 'peso' in c_lower: mapeamento[col] = 'peso'
        elif 'altura' in c_lower: mapeamento[col] = 'altura'
        elif 'genero' in c_lower or 'gênero' in c_lower: mapeamento[col] = 'genero'
        elif 'z_0' in c_lower: mapeamento[col] = 'z_0'
        elif 'z_1pos' in c_lower: mapeamento[col] = 'z_1pos'
        elif 'z_2pos' in c_lower: mapeamento[col] = 'z_2pos'
        elif 'z_3pos' in c_lower: mapeamento[col] = 'z_3pos'
        elif 'z_1neg' in c_lower: mapeamento[col] = 'z_1neg'
        elif 'z_2neg' in c_lower: mapeamento[col] = 'z_2neg'
        elif 'z_3neg' in c_lower: mapeamento[col] = 'z_3neg'
    df = df.rename(columns=mapeamento)
    if 'genero' in df.columns:
        df['genero'] = df['genero'].astype(str).str.upper().str.strip()
    return df

def classificar_oms(peso, altura, curva_ref):
    try:
        if peso <= 0 or altura <= 0 or curva_ref.empty:
            return "Dados Insuficientes", "gray"
        
        # Encontra a linha da OMS mais próxima da altura do aluno
        idx = (curva_ref['altura'] - altura).abs().idxmin()
        ref = curva_ref.loc[idx]
        
        # Lógica de Classificação solicitada
        if peso < float(ref['z_3neg']): return "Magreza acentuada", "#8B0000"
        elif peso < float(ref['z_2neg']): return "Magreza", "#FF4500"
        elif peso < float(ref['z_1pos']): return "Eutrofia", "#2E8B57"
        elif peso <= float(ref['z_2pos']): return "Risco de sobrepeso", "#FFD700"
        elif peso <= float(ref['z_3pos']): return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except:
        return "Erro de Cálculo", "gray"

def calcular_imc(p, a):
    return round(p / ((a/100)**2), 2) if a > 0 else 0

@st.cache_data
def carregar_dados():
    try:
        # Carrega o CSV forçando as colunas Z a serem números
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        # Força conversão de todas as colunas Z para float
        colunas_z = ['z_3neg','z_2neg','z_1neg','z_0','z_1pos','z_2pos','z_3pos']
        for col in colunas_z:
            if col in df_ref.columns:
                df_ref[col] = pd.to_numeric(df_ref[col], errors='coerce')
        
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}"); return None, None

# --- 2. EXECUÇÃO ---
df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("Configurações")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    modo = st.sidebar.radio("Visão:", ["Ficha Individual", "Relatório da Turma"])

    if modo == "Ficha Individual":
        lista = sorted(df_atual['aluno'].dropna().unique())
        aluno = st.sidebar.selectbox("Selecionar Aluno:", lista)
        dados = df_atual[df_atual['aluno'] == aluno].iloc[0]
        
        st.header(f"Acompanhamento Anual: {aluno}")
        
        # --- SEÇÕES TRIMESTRAIS EM COLUNAS ---
        cols = st.columns(4)
        medicoes = []
        curva_aluno = df_ref[df_ref['genero'] == str(dados.get('genero', 'M'))]
        
        for i, nome_tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
            with cols[i]:
                st.markdown(f"### {nome_tri}")
                p_val = float(dados.get('peso', 0) or 0) if i == 0 else 0.0
                a_val = float(dados.get('altura', 0) or 0) if i == 0 else 0.0
                
                p = st.number_input(f"Peso (kg)", value=p_val, key=f"p{i}", step=0.1)
                a = st.number_input(f"Altura (cm)", value=a_val, key=f"a{i}", step=0.1)
                
                imc = calcular_imc(p, a)
                classif, cor = classificar_oms(p, a, curva_aluno)
                
                st.metric("IMC", imc)
                st.markdown(f"<div style='background-color:{cor}; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{classif}</div>", unsafe_allow_html=True)
                
                if p > 0 and a > 0:
                    medicoes.append({'tri': i+1, 'p': p, 'a': a, 'classif': class
