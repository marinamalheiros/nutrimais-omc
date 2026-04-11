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
    .status-sidebar { color: white; padding: 15px; border-radius: 8_px; text-align: center; font-weight: bold; margin-bottom: 20px; }
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
        # Tenta carregar o arquivo atualizado ou o padrão
        nome_csv = "referencias_oms_completo ATUALIZADO.csv" if os.path.exists("referencias_oms_completo ATUALIZADO.csv") else "referencias_oms_completo.csv"
        df_ref = pd.read_csv(nome_csv, sep=';', decimal=',')
        
        cols_z = ['z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
        for col in cols_z:
            df_ref[col] = pd.to_numeric(df_ref[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        df_ref['idade_meses'] = pd.to_numeric(df_ref['idade_meses'], errors='coerce')
        df_ref['altura'] = pd.to_numeric(df_ref['altura'], errors='coerce')

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
        if tipo_indice == 'estatura_idade':
            if v < r['z_3neg']: return "Muito baixa estatura para a idade", "#8B0000"
            elif v < r['z_2neg']: return "Baixa estatura para a idade", "#FF4500"
            else: return "Estatura adequada para a idade", "#2E8B57"
        elif tipo_indice == 'peso_idade':
            if v < r['z_3neg']: return "Muito baixo peso para a idade", "#8B0000"
            elif v < r['z_2neg']: return "Baixo peso para a idade", "#FF4500"
            elif v < r['z_2pos']: return "Peso adequado para a idade", "#2E8B57"
            else: return "Peso elevado para a idade", "#FF8C00"
        else:
            if v < r['z_3neg']: return "Magreza acentuada", "#8B0000"
            elif v < r['z_2neg']: return "Magreza", "#FF4500"
            elif v < r['z_1pos']: return "Eutrofia", "#2E8B57"
            elif v < r['z_2pos']: return "Risco de sobrepeso", "#FFD700"
            elif v < r['z_3pos']: return "Sobrepeso", "#FF8C00"
            else: return "Obesidade", "#FF0000"
    except: return "Erro", "#808080"

# --- 3. EXECUÇÃO ---
df_ref, turmas = carregar_dados_sistema()

if df_ref is not None and turmas:
    st.markdown("<h1 class='header-style'>🍎 NutriGestão - O Mundo da Criança</h1>", unsafe_allow_html=True)
    st.markdown("<h3 class='header-style'>Nutricionista Marina Malheiros Mendonça - CRN 5 21456</h3>", unsafe_allow_html=True)
    st.divider()

    aba_sel = st.sidebar.selectbox("Turma:", list(turmas.keys()))
    df_atual = turmas[aba_sel]
    aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_atual['aluno'].unique()))
    modo = st.sidebar.radio("Navegação:", ["Ficha Individual", "Relatório Coletivo"])
    
    dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen = 'F' if str(dados_aluno['genero']).upper().startswith('F') else 'M'

    if modo == "Ficha Individual":
        st.header(f"Ficha: {aluno_nome}")
        cols_tri = st.columns(4)
        medicoes = []

        for i, tri in enumerate(["1º Tri (Planilha)", "2º Tri", "3º Tri", "4º Tri"]):
            with cols_tri[i]:
                st.subheader(tri)
                p = st.number_input(f"Peso (kg)", value=float(dados_aluno['peso_1']) if i == 0 else 0.0, key=f"p{i}_{aluno_nome}")
                a = st.number_input(f"Alt (cm)", value=float(dados_aluno['altura_1']) if i == 0 else 0.0, key=f"a{i}_{aluno_nome}")
                
                if p > 0 and a > 0:
                    imc = round(p / ((a/100)**2), 2)
                    ref_pa = df_ref[(df_ref['tipo'] == 'peso_altura') & (df_ref['genero'] == gen)]
                    if not ref_pa.empty:
                        idx_m = (ref_pa['altura'] - a).abs().idxmin()
                        status, cor = classificar_oms(p, ref_pa.loc[[idx_m]], 'peso_altura')
                        
                        medicoes.append({'p': p, 'a': a, 'imc': imc, 'cor': cor, 'status': status, 'meses': dados_aluno['idade_meses'] + (i*3)})
                        st.markdown(f"<div class='status-box' style='background-color:{cor}'>{status}</div>", unsafe_allow_html=True)
                        if i == len(medicoes) - 1:
                            st.sidebar.markdown(f"<div class='status-sidebar' style='background-color:{cor};'>STATUS ATUAL:<br>{status}</div>", unsafe_allow_html=True)

        st.divider()
        g_row = st.columns(2)
        params = [("peso_altura", "Peso x Altura"), ("imc_idade", "IMC x Idade"), ("peso_idade", "Peso x Idade"), ("estatura_idade", "Estatura x Idade")]
        
        for idx, (slug, nome_g) in enumerate(params):
            with g_row[idx % 2]:
                fig = go.Figure()
                
                curva = df_ref[(df_ref['tipo'] == slug) & (df_ref['genero'] == gen)].copy()
                eixo_x = 'altura' if slug == 'peso_altura' else 'idade_meses'
                
                # Definição dos limites de visualização
                if slug != "peso_altura":
                    x_min, x_max = max(0, int(dados_aluno['idade_meses']) - 3), int(dados_aluno['idade_meses']) + 15
                else:
                    x_min, x_max = float(dados_aluno['altura_1']) - 10, float(dados_aluno['altura_1']) + 25

                # Limpeza rigorosa: remove nulos e ordena
                curva = curva.dropna(subset=[eixo_x]).sort_values(by=eixo_x)

                for z_col, z_cor in [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]:
                    # SOLUÇÃO PARA O MERGULHO: Filtra apenas valores de Z maiores que zero para cada linha
                    dados_plot = curva[curva[z_col] > 0].dropna(subset=[z_col])
                    
                    if not dados_plot.empty:
                        fig.add_trace(go.Scatter(
                            x=dados_plot[eixo_x], 
                            y=dados_plot[z_col], 
                            line=dict(color=z_cor, width=2, shape='linear', dash='dot' if '0' not in z_col else 'solid'), 
                            mode='lines', 
                            connectgaps=False,
                            hoverinfo='skip'
                        ))

                for m in medicoes:
                    vy = m['p'] if 'peso' in slug else (m['a'] if 'estatura' in slug else m['imc'])
                    vx = m['a'] if slug == 'peso_altura' else m['meses']
                    fig.add_trace(go.Scatter(x=[vx], y=[vy], mode='markers+text', text=[f"<b>{vy}</b>"], textposition="top center", marker=dict(size=10, color=m['cor'], line=dict(width=1, color='white'))))

                fig.update_layout(title=f"<b>{nome_g}</b>", height=350, template="plotly_white", showlegend=False, margin=dict(l=10,r=10,t=40,b=10))
                fig.update_xaxes(range=[x_min, x_max])
                st.plotly_chart(fig, use_container_width=True)
                
                if medicoes:
                    m_atual = medicoes[-1]
                    v_aval = m_atual['p'] if 'peso' in slug else (m_atual['a'] if 'estatura' in slug else m_atual['imc'])
                    ref_esp = df_ref[(df_ref['tipo'] == slug) & (df_ref['genero'] == gen)]
                    if not ref_esp.empty:
                        idx_esp = (ref_esp[eixo_x] - (m_atual['a'] if slug == 'peso_altura' else m_atual['meses'])).abs().idxmin()
                        st_esp, cor_esp = classificar_oms(v_aval, ref_esp.loc[[idx_esp]], slug)
                        # CORREÇÃO DA SINTAXE (Adicionado aspas ao f-string)
                        st.markdown(f"<div class='status-box' style='background-color:{cor_esp}'>{nome_g}: {st_esp}</div>", unsafe_allow_html=True)
    
    else: 
        st.header(f"Panorama Coletivo - {aba_sel}")
        st.dataframe(df_atual[df_atual['peso_1'] > 0][['aluno', 'genero', 'idade_str', 'peso_1', 'altura_1']], use_container_width=True)
else:
    st.warning("Verifique os arquivos de dados na pasta do projeto.")
