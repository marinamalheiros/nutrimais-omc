import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import os

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F3E5F5; }
    .status-sidebar { color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .status-box { padding: 8px; border-radius: 5px; text-align: center; font-weight: bold; color: white; font-size: 0.85rem; margin-bottom: 10px; }
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
        # 1. Referências OMS
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',')
        cols_z = ['z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
        for col in cols_z:
            df_ref[col] = pd.to_numeric(df_ref[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        # 2. Dados dos Alunos (1º Tri vindo da Planilha)
        arquivo_excel = "DADOS - OMC.xlsx"
        if not os.path.exists(arquivo_excel):
            return df_ref, None
            
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
        st.error(f"Erro Crítico: {e}")
        return None, None

def classificar_oms(valor, ref_linha):
    if ref_linha.empty: return "Sem Ref.", "#808080"
    r = ref_linha.iloc[0]
    try:
        v = float(valor)
        if v < r['z_3neg']: return "Muito Baixo / Magreza Ac.", "#8B0000"
        elif v < r['z_2neg']: return "Baixo / Magreza", "#FF4500"
        elif v < r['z_1pos']: return "Eutrofia", "#2E8B57"
        elif v <= r['z_2pos']: return "Risco de Sobrepeso", "#FFD700"
        elif v <= r['z_3pos']: return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except: return "Erro", "#808080"

# --- 3. LÓGICA PRINCIPAL ---
df_ref, turmas = carregar_dados_sistema()

if df_ref is not None and turmas:
    st.sidebar.title("Configurações")
    aba_sel = st.sidebar.selectbox("Turma:", list(turmas.keys()))
    df_atual = turmas[aba_sel]
    
    aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_atual['aluno'].unique()))
    modo = st.sidebar.radio("Navegação:", ["Ficha Individual", "Relatório Coletivo"])
    
    dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen = 'F' if str(dados_aluno['genero']).upper().startswith('F') else 'M'

    if modo == "Ficha Individual":
        st.title(f"Ficha: {aluno_nome}")
        st.markdown(f"**Turma:** {aba_sel} | **Idade:** {dados_aluno['idade_str']}")

        cols_tri = st.columns(4)
        medicoes = []

        for i, tri in enumerate(["1º Trimestre", "2º Trimestre", "3º Trimestre", "4º Trimestre"]):
            with cols_tri[i]:
                st.subheader(tri)
                # Puxa do Excel apenas para o 1º Tri
                p_init = float(dados_aluno['peso_1']) if i == 0 else 0.0
                a_init = float(dados_aluno['altura_1']) if i == 0 else 0.0
                
                p = st.number_input(f"Peso (kg)", value=p_init, key=f"p{i}_{aluno_nome}")
                a = st.number_input(f"Alt (cm)", value=a_init, key=f"a{i}_{aluno_nome}")
                
                if p > 0 and a > 0:
                    imc = round(p / ((a/100)**2), 2)
                    # Classificação padrão para o Sidebar (Peso/Altura)
                    ref_pa = df_ref[(df_ref['tipo'] == 'peso_altura') & (df_ref['genero'] == gen)]
                    idx = (ref_pa['altura'] - a).abs().idxmin()
                    st_txt, cor = classificar_oms(p, ref_pa.loc[[idx]])
                    
                    medicoes.append({'p': p, 'a': a, 'imc': imc, 'cor': cor, 'status': st_txt, 'meses': dados_aluno['idade_meses'] + (i*3)})
                    st.markdown(f"<div class='status-box' style='background-color:{cor}'>{st_txt}</div>", unsafe_allow_html=True)
                    
                    if i == len(medicoes) - 1: # Atualiza sidebar com a última medição
                        st.sidebar.markdown(f"<div class='status-sidebar' style='background-color:{cor};'>STATUS ATUAL:<br>{st_txt}</div>", unsafe_allow_html=True)

        # --- GRÁFICOS ---
        st.divider()
        g_row1 = st.columns(2)
        params = [("peso_altura", "Peso x Altura"), ("imc_idade", "IMC x Idade"), ("peso_idade", "Peso x Idade"), ("estatura_idade", "Estatura x Idade")]
        
        for idx, (p_slug, p_nome) in enumerate(params):
            with g_row1[idx % 2]:
                fig = go.Figure()
                curva = df_ref[(df_ref['tipo'] == p_slug) & (df_ref['genero'] == gen)].copy()
                col_x = 'altura' if p_slug == 'peso_altura' else 'idade_meses'
                curva = curva[curva[col_x] > 0].sort_values(by=col_x)
                
                # Foco no aluno
                if p_slug != "peso_altura":
                    curva = curva[(curva[col_x] >= dados_aluno['idade_meses'] - 2) & (curva[col_x] <= dados_aluno['idade_meses'] + 12)]

                # Curvas OMS
                for z_col, z_cor in [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]:
                    fig.add_trace(go.Scatter(x=curva[col_x], y=curva[z_col], line=dict(color=z_cor, width=1, dash='dot' if '0' not in z_col else 'solid'), mode='lines', hoverinfo='skip'))

                # Pontos do Aluno
                for m in medicoes:
                    vy = m['p'] if 'peso' in p_slug else (m['a'] if 'estatura' in p_slug else m['imc'])
                    vx = m['a'] if p_slug == 'peso_altura' else m['meses']
                    fig.add_trace(go.Scatter(x=[vx], y=[vy], mode='markers+text', text=[f"{vy}"], textposition="top center", marker=dict(size=10, color=m['cor'], line=dict(width=1, color='white'))))

                fig.update_layout(title=f"<b>{p_nome}</b>", height=350, template="plotly_white", showlegend=False, margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig, use_container_width=True)
    
    else: # RELATÓRIO COLETIVO
        st.title(f"Panorama Coletivo - {aba_sel}")
        # Filtra apenas alunos com peso registrado na planilha
        df_exibir = df_atual[df_atual['peso_1'] > 0][['aluno', 'genero', 'idade_str', 'peso_1', 'altura_1']].copy()
        st.dataframe(df_exibir, use_container_width=True)

else:
    st.error("Arquivos necessários não encontrados ou corrompidos.")
