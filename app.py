import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import os

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="NutriGestão - Marina Malheiros", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F3E5F5; }
    .status-sidebar { color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .status-box { padding: 8px; border-radius: 5px; text-align: center; font-weight: bold; color: white; font-size: 0.85rem; margin-bottom: 10px; }
    .header-style { color: #4A148C; font-weight: bold; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE ---
def converter_idade_para_meses(texto_idade):
    try:
        texto = str(texto_idade).lower().strip()
        numeros = re.findall(r'\d+', texto)
        if not numeros: return 0
        valor = int(numeros[0])
        return valor * 12 if 'ano' in texto else valor
    except: return 0

@st.cache_data
def carregar_dados_sistema():
    try:
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',')
        cols_z = ['z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
        for col in cols_z:
            df_ref[col] = pd.to_numeric(df_ref[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        arquivo_excel = "DADOS - OMC.xlsx"
        if not os.path.exists(arquivo_excel): return df_ref, None
            
        dict_abas = pd.read_excel(arquivo_excel, sheet_name=None)
        turmas_prontas = {}
        for nome_aba, df in dict_abas.items():
            df.columns = [str(c).strip() for c in df.columns]
            mapeamento = {'Aluno': 'aluno', 'Gênero': 'genero', 'Idade': 'idade_str', 'Peso (kg)': 'peso_1', 'Altura (cm)': 'altura_1'}
            df = df.rename(columns=mapeamento)
            df['peso_1'] = pd.to_numeric(df['peso_1'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            df['altura_1'] = pd.to_numeric(df['altura_1'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            df['idade_meses'] = df['idade_str'].apply(converter_idade_para_meses)
            turmas_prontas[nome_aba] = df
        return df_ref, turmas_prontas
    except Exception as e:
        st.error(f"Erro: {e}")
        return None, None

def classificar_oms(valor, ref_linha, tipo_indice):
    if ref_linha.empty: return "Sem Ref.", "#808080"
    r = ref_linha.iloc[0]
    try:
        v = float(valor)
        # 1. ESTATURA POR IDADE (E/I)
        if tipo_indice == 'estatura_idade':
            if v < r['z_3neg']: return "Muito baixa estatura para a idade", "#8B0000"
            elif v < r['z_2neg']: return "Baixa estatura para a idade", "#FF4500"
            else: return "Estatura adequada para a idade", "#2E8B57"
        
        # 2. PESO POR IDADE (P/I)
        elif tipo_indice == 'peso_idade':
            if v < r['z_3neg']: return "Muito baixo peso para a idade", "#8B0000"
            elif v < r['z_2neg']: return "Baixo peso para a idade", "#FF4500"
            elif v < r['z_2pos']: return "Peso adequado para a idade", "#2E8B57"
            else: return "Peso elevado para a idade", "#FF8C00"
            
        # 3. PESO/ESTATURA (P/E) OU IMC POR IDADE (IMC/I)
        else:
            if v < r['z_3neg']: return "Magreza acentuada", "#8B0000"
            elif v < r['z_2neg']: return "Magreza", "#FF4500"
            elif v < r['z_1pos']: return "Eutrofia", "#2E8B57"
            elif v
