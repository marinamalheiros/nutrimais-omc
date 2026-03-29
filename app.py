import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re

# Configuração da Página
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

# --- ESTILO CSS CUSTOMIZADO (Fundo Lilás) ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F3E5F5; /* Lilás bem clarinho */
    }
    /* Estilização dos boxes métricos para contraste */
    [data-testid="stMetricValue"] {
        color: #4A148C;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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
        elif 'z_' in c_lower: mapeamento[col] = c_lower 
    
    df = df.rename(columns=mapeamento)
    
    cols_num = ['peso', 'altura', 'z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
    for col in df.columns:
        if col in cols_num:
            # Tratamento para garantir que vírgulas virem pontos antes da conversão numérica
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    return df

def classificar_oms(peso, altura, curva_ref):
    try:
        # Filtra apenas o tipo peso_altura para esta classificação específica
        ref_pa = curva_ref[curva_ref['tipo'] == 'peso_altura']
        
        if peso <= 0 or altura <= 0 or ref_pa.empty:
            return "Dados Insuficientes", "#808080"
            
        idx = (ref_pa['altura'] - altura).abs().idxmin()
        ref = ref_pa.loc[idx]
        p = float(peso)
        
        if p < ref['z_3neg']: return "Magreza acentuada", "#8B0000"
        elif p < ref['z_2neg']: return "Magreza", "#FF4500"
        elif p < ref['z_1pos']: return "Eutrofia", "#2E8B57"
        elif p <= ref['z_2pos']: return "Risco de sobrepeso", "#FFD700"
        elif p <= ref['z_3pos']: return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except:
        return "Erro", "#808080"

@st.cache_data
def carregar_dados():
    try:
        # 1. Carregamento com separador ; e decimal , para o seu novo arquivo
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        
        # 2. Correção do erro: Usamos .str.upper() para aplicar em toda a coluna (Series)
        if 'tipo' in df_ref.columns:
            df_ref['tipo'] = df_ref['tipo'].astype(str).str.strip().str.lower()
        if 'genero' in df_ref.columns:
            df_ref['genero'] = df_ref['genero'].astype(str).str.strip().str.upper()
            
        # 3. Processa os nomes das colunas e converte números
        df_ref = preparar_dataframe(df_ref)
        
        # 4. Carrega a planilha de alunos
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

# --- 2. CABEÇALHO ---
st.title("🍎 Acompanhamento Nutricional - O Mundo da Criança")
st.markdown("##### pela Nutricionista Marina Malheiros Mendonça - CRN 5 21456 🍐🍒")

df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    # --- BARRA LATERAL ---
    st.sidebar.markdown("### 🥗 Seleção")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    
    lista_alunos = sorted(df_atual['aluno'].dropna().unique())
    aluno_nome = st.sidebar.selectbox("Aluno:", lista_alunos)
    
    dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    # Normalização do gênero para busca na referência
    gen_aluno = "M" if "M" in str(dados_aluno.get('genero', 'M')).upper() else "F"
    
    # Filtra as referências pelo gênero do aluno selecionado
    curva_ref_aluno = df_ref[df_ref['genero'] == gen_aluno]
    
    p_side = float(dados_aluno.get('peso', 0))
    a_side = float(dados_aluno.get('altura', 0))
    status_side, cor_side = classificar_oms(p_side, a_side, curva_ref_aluno)
    imc_side = round(p_side / ((a_side/100)**2), 2) if a_side > 0 else 0
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Status Atual (Peso/Est.):**")
    st.sidebar.write(f"👤 **{aluno_nome}**")
    st.sidebar.metric("IMC Atual", imc_side)
    st.sidebar.markdown(f"<div style='background-color:{cor_side}; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{status_side}</div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    modo = st.sidebar.radio("Ver:", ["Ficha Individual", "Relatório Coletivo"])

    if modo == "Ficha Individual":
        st.header(f"{aluno_nome}")
        cols = st.columns(4)
        medicoes = []

        for i, nome_tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
            with cols[i]:
                st.markdown(f"**{nome_tri}**")
                p_v = float(dados_aluno['peso']) if i == 0 else 0.0
                a_v = float(dados_aluno['altura']) if i == 0 else 0.0
                p = st.number_input(f"Peso (kg)", value=p_v, key=f"pi{i}_{aluno_nome}", step=0.1)
                a = st.number_input(f"Altura (cm)", value=a_v, key=f"ai{i}_{aluno_nome}", step=0.1)
                status, cor = classificar_oms(p, a, curva_ref_aluno)
                if p > 0 and a > 0:
                    medicoes.append({'tri': i+1, 'p': p, 'a': a, 'status': status, 'cor': cor})
                    st.markdown(f"<p style='color:{cor}; font-weight:bold;'>{status}</p>", unsafe_allow_html=True)

        if medicoes:
            fig_ind = go.Figure()
            alt_m = [m['a'] for m in medicoes]; pes_m = [m['p'] for m in medicoes]
            min_x, max_x = min(alt_m) - 4, max(alt_m) + 4
            min_y, max_y = min(pes_m) - 4, max(pes_m) + 4
            
            # Filtra apenas os dados de peso_altura para o gráfico de dispersão
            c_ref_plot = curva_ref_aluno[curva_ref_aluno['tipo'] == 'peso_altura']
            c_zoom = c_ref_plot[(c_ref_plot['altura'] >= min_x) & (c_ref_plot['altura'] <= max_x)]

            refs = [('z_3pos', 'Obesidade', 'red'), ('z_2pos', 'Sobrepeso', 'orange'), 
                    ('z_1pos', 'Risco Sobrep.', 'yellow'), ('z_0', 'Eutrofia', 'green'), 
                    ('z_2neg', 'Magreza', 'orange'), ('z_3neg', 'Magreza Ac.', 'red')]
            
            for col, lab, color in refs:
                if col in c_zoom.columns:
                    fig_ind.add_trace(go.Scatter(x=c_zoom['altura'], y=c_zoom[col], name=lab, 
                                             line=dict(color=color, width=2, dash='dot' if '0' in col else 'solid'),
                                             mode='lines', hoverinfo='skip'))

            for m in medicoes:
                fig_ind.add_trace(go.Scatter(x=[m['a']], y=[m['p']], mode='markers+text', text=[f"T{m['tri']}"],
                                         textposition="top center", marker=dict(size=14, color=m['cor'], line=dict(width=2, color='white')),
                                         name=f"Registro T{m['tri']}"))

            fig_ind.update_layout(xaxis=dict(range=[min_x, max_x], dtick=1, title="Altura (cm)"),
                              yaxis=dict(range=[min_y, max_y], dtick=1, title="Peso (kg)"),
                              height=600, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white')
            st.plotly_chart(fig_ind, use_container_width=True)

    else:
        # --- RELATÓRIO COLETIVO ---
        st.header(f"📊 Panorama: {aba_sel}")
        df_turma = df_atual[df_atual['peso'] > 0].copy()
        if not df_turma.empty:
            # Aplica classificação linha a linha filtrando o gênero correto na referência
            df_turma['Status'] = df_turma.apply(lambda x: classificar_oms(x['peso'], x['altura'], df_ref[df_ref['genero'] == x['genero']])[0], axis=1)
            
            fig_col = go.Figure()
            min_xc, max_xc = df_turma['altura'].min() - 5, df_turma['altura'].max() + 5
            min_yc, max_yc = df_turma['peso'].min() - 5, df_turma['peso'].max() + 5
            
            # Para o fundo do gráfico coletivo, usamos a referência do gênero predominante ou do último selecionado
            curva_c = df_ref[(df_ref['genero'] == gen_aluno) & (df_ref['tipo'] == 'peso_altura')] 
            c_c_zoom = curva_c[(curva_c['altura'] >= min_xc) & (curva_c['altura'] <= max_xc)]
            
            refs = [('z_3pos', 'Obesidade', 'red'), ('z_2pos', 'Sobrepeso', 'orange'), 
                    ('z_1pos', 'Risco Sobrep.', 'yellow'), ('z_0', 'Eutrofia', 'green'), 
                    ('z_2neg', 'Magreza', 'orange'), ('z_3neg', 'Magreza Ac.', 'red')]
            
            for col, lab, color in refs:
                if col in c_c_zoom.columns:
                    fig_col.add_trace(go.Scatter(x=c_c_zoom['altura'], y=c_c_zoom[col], name=lab, 
                                             line=dict(color=color, width=1.5, dash='dash'), mode='lines', hoverinfo='skip'))

            for status, cor in [("Eutrofia", "#2E8B57"), ("Risco de sobrepeso", "#FFD700"), ("Sobrepeso", "#FF8C00"), 
                                ("Obesidade", "#FF0000"), ("Magreza", "#FF4500"), ("Magreza acentuada", "#8B0000")]:
                df_f = df_turma[df_turma['Status'] == status]
                if not df_f.empty:
                    fig_col.add_trace(go.Scatter(x=df_f['altura'], y=df_f['peso'], mode='markers',
                                                 name=status, marker=dict(size=12, color=cor),
                                                 text=df_f['aluno'], hovertemplate="<b>%{text}</b><br>Peso: %{y}kg<br>Alt: %{x}cm"))

            fig_col.update_layout(xaxis=dict(range=[min_xc, max_xc], dtick=1, title="Altura (cm)"),
                                  yaxis=dict(range=[min_yc, max_yc], dtick=1, title="Peso (kg)"),
                                  height=600, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white')
            st.plotly_chart(fig_col, use_container_width=True)
            st.markdown("### 📋 Tabela de Dados da Turma")
            st.dataframe(df_turma[['aluno', 'genero', 'peso', 'altura', 'Status']], use_container_width=True, hide_index=True)
