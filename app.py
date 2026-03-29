import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F3E5F5; }
    .status-sidebar { color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 10px; }
    .status-box { padding: 5px; border-radius: 5px; text-align: center; font-weight: bold; color: white; font-size: 0.85rem; margin-top: -5px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE APOIO ---
def converter_idade_para_meses(texto_idade):
    try:
        texto = str(texto_idade).lower().strip()
        numeros = re.findall(r'\d+', texto)
        if not numeros: return 0
        valor = int(numeros[0])
        return valor * 12 if 'ano' in texto else valor
    except: return 0

@st.cache_data
def carregar_dados_completos():
    try:
        # 1. Referências OMS (CSV)
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',')
        cols_z = ['z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
        for col in cols_z:
            df_ref[col] = pd.to_numeric(df_ref[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        # 2. Dados dos Alunos (Excel) - Lendo todas as abas
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas_limpas = {}
        
        for nome_aba, df in dict_turmas.items():
            # Padronização de colunas conforme o seu arquivo enviado
            df.columns = [str(c).strip() for c in df.columns]
            mapeamento = {
                'Aluno': 'aluno', 'Gênero': 'genero', 'Idade': 'idade_str',
                'Peso (kg)': 'peso', 'Altura (cm)': 'altura'
            }
            df = df.rename(columns=mapeamento)
            
            # Conversões numéricas críticas
            df['peso'] = pd.to_numeric(df['peso'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df['altura'] = pd.to_numeric(df['altura'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            df['idade_meses'] = df['idade_str'].apply(converter_idade_para_meses)
            
            turmas_limpas[nome_aba] = df
            
        return df_ref, turmas_limpas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

def classificar_status(valor, ref_linha):
    if ref_linha.empty: return "Sem Dados", "#808080"
    r = ref_linha.iloc[0]
    try:
        v = float(valor)
        if v < r['z_2neg']: return "Baixo Peso / Magreza", "#FF4500"
        elif v < r['z_1pos']: return "Eutrofia", "#2E8B57"
        elif v <= r['z_2pos']: return "Sobrepeso", "#FFD700"
        else: return "Obesidade", "#FF0000"
    except: return "Erro", "#808080"

# --- 3. EXECUÇÃO ---
df_ref, turmas = carregar_dados_completos()

if df_ref is not None and turmas:
    st.title("🍎 NutriGestão - O Mundo da Criança")
    st.markdown(f"##### Nutricionista Marina Malheiros Mendonça - CRN 5 21456")
    
    aba_sel = st.sidebar.selectbox("Turma:", list(turmas.keys()))
    df_atual = turmas[aba_sel]
    aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_atual['aluno'].dropna().unique()))
    
    # Puxa dados da planilha
    dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen = 'F' if str(dados_aluno['genero']).upper().startswith('F') else 'M'
    
    st.header(f"Ficha: {aluno_nome}")
    cols = st.columns(4)
    medicoes = []
    
    # Preenchimento automático do 1º Trimestre com os dados da Planilha
    for i, tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
        with cols[i]:
            st.markdown(f"**{tri}**")
            p_val = float(dados_aluno['peso']) if i == 0 else 0.0
            a_val = float(dados_aluno['altura']) if i == 0 else 0.0
            
            p = st.number_input(f"Peso (kg)", value=p_val, key=f"p{i}_{aluno_sel}")
            a = st.number_input(f"Alt (cm)", value=a_val, key=f"a{i}_{aluno_sel}")
            
            if p > 0 and a > 0:
                imc = round(p / ((a/100)**2), 2)
                # Referência para status (Peso/Altura)
                ref_pa = df_ref[(df_ref['tipo'] == 'peso_altura') & (df_ref['genero'] == gen)]
                linha = ref_pa.iloc[[(ref_pa['altura'] - a).abs().idxmin()]]
                status, cor = classificar_status(p, linha)
                
                medicoes.append({'p': p, 'a': a, 'imc': imc, 'cor': cor, 'status': status, 'idade': dados_aluno['idade_meses']})
                st.markdown(f"<div class='status-box' style='background-color:{cor}'>{status}</div>", unsafe_allow_html=True)

    # --- GRÁFICOS ---
    st.divider()
    g1, g2 = st.columns(2)
    graficos = [('peso_idade', 'Peso x Idade'), ('peso_altura', 'Peso x Altura')]
    
    for idx, (tipo, titulo) in enumerate(graficos):
        with [g1, g2][idx]:
            fig = go.Figure()
            curva = df_ref[(df_ref['tipo'] == tipo) & (df_ref['genero'] == gen)]
            col_x = 'altura' if tipo == 'peso_altura' else 'idade_meses'
            
            # Limpeza de zeros e ordenação (evita inversão)
            curva = curva[curva[col_x] > 0].sort_values(by=col_x)
            
            # Janela de visualização para não achatar o gráfico
            if tipo == 'peso_idade':
                curva = curva[(curva[col_x] >= dados_aluno['idade_meses'] - 2) & (curva[col_x] <= dados_aluno['idade_meses'] + 10)]

            # Linhas de Referência (Ordem fixa para não inverter)
            z_cores = [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]
            for z_col, cor_l in z_cores:
                fig.add_trace(go.Scatter(x=curva[col_x], y=curva[z_col], line=dict(color=cor_l, width=1.2, dash='dot' if '0' not in z_col else 'solid'), mode='lines', hoverinfo='skip'))
            
            # Ponto do Aluno
            for m in medicoes:
                fig.add_trace(go.Scatter(x=[m['a'] if tipo == 'peso_altura' else m['idade']], y=[m['p']], mode='markers+text', text=[f"{m['p']}"], textposition="top center", marker=dict(size=10, color=m['cor'], line=dict(width=1, color='white'))))
            
            fig.update_layout(title=titulo, height=350, template="plotly_white", showlegend=False, margin=dict(l=10,r=10,t=40,b=10))
            st.plotly_chart(fig, use_container_width=True)
