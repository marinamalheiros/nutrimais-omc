import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import os
from datetime import datetime

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
def calcular_meses_exatos(data_nasc, data_afericao):
    try:
        diff = data_afericao - data_nasc
        return round(diff.days / 30.44, 1)
    except:
        return 0

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
            # Mapeamento ajustado para sua planilha real (Coluna E = Data de Nascimento)
            mapeamento = {
                'Aluno': 'aluno', 
                'Gênero': 'genero', 
                'Data de Nascimento': 'nasc_data', 
                'Peso (kg)': 'peso_1', 
                'Altura (cm)': 'altura_1'
            }
            df = df.rename(columns=mapeamento)
            df['peso_1'] = pd.to_numeric(df['peso_1'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            df['altura_1'] = pd.to_numeric(df['altura_1'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
            df['nasc_data'] = pd.to_datetime(df['nasc_data'], errors='coerce')
            turmas_prontas[nome_aba] = df
        return df_ref, turmas_prontas
    except Exception as e:
        st.error(f"Erro: {e}")
        return None, None

def classificar_oms(valor, ref_linha, tipo_indice):
    if ref_linha.empty: return "Sem Ref.", "#808080"
    r = ref_linha.iloc[0]
