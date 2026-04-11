import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
        # Garante que estamos lidando com objetos de data
        diff = data_afericao - data_nasc
        return round(diff.days / 30.44, 1)
    except:
        return 0

@st.cache_data
def carregar_dados_sistema():
    try:
        nome_csv = "referencias_oms_completo ATUALIZADO.csv" if os.path.exists("referencias_oms_completo ATUALIZADO.csv") else "referencias_oms_completo.csv"
        df_ref = pd.read_csv(nome_csv, sep=';', decimal=',')
        for col in ['z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']:
            df_ref[col] = pd.to_numeric(df_ref[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        arquivo_excel = "DADOS - OMC.xlsx"
        if not os.path.exists(arquivo_excel): return df_ref, None
            
        dict_abas = pd.read_excel(arquivo_excel, sheet_name=None)
        turmas_prontas = {}
        for nome_aba, df in dict_abas.items():
            # Limpa espaços nos nomes das colunas
            df.columns = [str(c).strip() for c in df.columns]
            
            # MAPEAMENTO SEGURO: Usamos 'Idade' porque é o que está no seu Excel (Coluna E)
            # Mas internamente o sistema tratará como a data de nascimento
            mapeamento = {
                'Aluno': 'aluno', 
                'Gênero': 'genero', 
                'Idade': 'nascimento_col', 
                'Peso (kg)': 'peso_1', 
                'Altura (cm)': 'altura_1'
            }
            df = df.rename(columns=mapeamento)
            
            # Converte o conteúdo da coluna E para data
            df['nascimento_col'] = pd.to_datetime(df['nascimento_col'], errors='coerce')
            df['peso_1'] = pd.to_numeric(df['peso_1'], errors='coerce').fillna(0.0)
            df['altura_1'] = pd.to_numeric(df['altura_1'], errors='coerce').fillna(0.0)
            turmas_prontas[nome_aba] = df
        return
