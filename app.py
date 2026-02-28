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
            return "Dados Insuficientes", "#808080"
        
        # Encontra a linha da OMS mais próxima da altura do aluno
        idx = (curva_ref['altura'] - altura).abs().idxmin()
        ref = curva_ref.loc[idx]
        
        # Lógica de Classificação com cores solicitadas
        if peso < float(ref['z_3neg']): 
            return "Magreza acentuada", "#8B0000" # Vermelho Escuro
        elif peso < float(ref['z_2neg']): 
            return "Magreza", "#FF4500" # Laranja Forte
        elif peso < float(ref['z_1pos']): 
            return "Eutrofia", "#2E8B57" # Verde
        elif peso <= float(ref['z_2pos']): 
            return "Risco de sobrepeso", "#FFD700" # Amarelo
        elif peso <= float(ref['z_3pos']): 
            return "Sobrepeso", "#FF8C00" # Laranja Escuro
        else: 
            return "Obesidade", "#FF0000" # Vermelho Vivo
    except:
        return "Erro de Cálculo", "#808080"

def calcular_imc(p, a):
    return round(p / ((a/100)**2), 2) if a > 0 else 0

@st.cache_data
def carregar_dados():
    try:
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Converte colunas Z para números para evitar erros de comparação
        colunas_z = ['z_3neg','z_2neg','z_1neg','z_0','z_1pos','z_2pos','z_3pos']
        for c in colunas_z:
            if c in df_ref.columns:
                df_ref[c] = pd.to_numeric(df_ref[c], errors='coerce')
        
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro no carregamento: {e}")
        return None, None

# --- 2. EXECUÇÃO ---
df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("📋 Menu de Controle")
    aba_sel = st.sidebar.selectbox("Selecione a Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    modo = st.sidebar.radio("Modo de Visão:", ["Ficha Individual", "Relatório da Turma"])

    if modo == "Ficha Individual":
        lista = sorted(df_atual['aluno'].dropna().unique())
        aluno = st.sidebar.selectbox("Selecionar Aluno:", lista)
        dados = df_atual[df_atual['aluno'] == aluno].iloc[0]
        
        st.header(f"Acompanhamento Anual: {aluno}")
        
        # --- COLUNAS TRIMESTRAIS ---
        cols = st.columns(4)
        medicoes = []
        curva_aluno = df_ref[df_ref['genero'] == str(dados.get('genero', 'M'))]
        
        for i, nome_tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
            with cols[i]:
                st.markdown(f"#### {nome_tri}")
                # Puxa dados do Excel no 1º Tri, os outros iniciam zerados
                p_init = float(dados.get('peso', 0) or 0) if i == 0 else 0.0
                a_init = float(dados.get('altura', 0) or 0) if i == 0 else 0.0
                
                p = st.number_input(f"Peso (kg)", value=p_init, key=f"p{i}", step=0.1)
                a = st.number_input(f"Altura (cm)", value=a_init, key=f"a{i}", step=0.1)
                
                imc = calcular_imc(p, a)
                classif, cor = classificar_oms(p, a, curva_aluno)
                
                st.metric("IMC", imc)
                st.markdown(f"<div style='background-color:{cor}; color:white; padding:8px; border-radius:5px; text-align:center; font-weight:bold; font-size:14px;'>{classif}</div>", unsafe_allow_html=True)
                
                if p > 0 and a > 0:
                    medicoes.append({'tri': i+1, 'p': p, 'a': a, 'classif': classif, 'cor': cor})

        # --- GRÁFICO INDIVIDUAL (ESCALA 1x1) ---
        if medicoes:
            st.markdown("---")
            st.subheader("Gráfico de Evolução (Curva OMS)")
            
            fig = go.Figure()
            # Zoom dinâmico
            alturas = [m['a'] for m in medicoes]
            curva_zoom = curva_aluno[(curva_aluno['altura'] >= min(alturas)-5) & (curva_aluno['altura'] <= max(alturas)+5)]

            # Linhas de Referência da OMS
            referencias = [
                ('z_3pos', 'Obesidade', '#FF0000'), ('z_2pos', 'Sobrepeso', '#FF8C00'),
                ('z_1pos', 'Risco Sobrep.', '#FFD700'), ('z_0', 'Ideal', '#2E8B57'),
                ('z_2neg', 'Magreza', '#FF4500'), ('z_3neg', 'Magreza Ac.', '#8B0000')
            ]
            
            for col_z, label, cor_z in referencias:
                if col_z in curva_zoom.columns:
                    fig.add_trace(go.Scatter(x=curva_zoom['altura'], y=curva_zoom[col_z], name=label, 
                                             line=dict(color=cor_z, width=1.5, dash='dot' if '0' not in col_z else 'solid')))

            # Pontos do Aluno (T1, T2, T3, T4)
            for m in medicoes:
                fig.add_trace(go.Scatter(x=[m['a']], y=[m['p']], mode='markers+text',
                                         text=[f"T{m['tri']}"], textposition="top center",
                                         marker=dict(size=14, color=m['cor'], line=dict(width=2, color='white')),
                                         name=f"Aferição {m['tri']}"))

            fig.update_layout(
                xaxis=dict(dtick=1, title="Altura (cm)", gridcolor='lightgray'),
                yaxis=dict(dtick=1, title="Peso (kg)", gridcolor='lightgray'),
                height=650, plot_bgcolor='white'
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        # --- RELATÓRIO COLETIVO ---
        st.header(f"📊 Panorama Geral: {aba_sel}")
        df_plot = df_atual.dropna(subset=['peso', 'altura']).copy()
        df_plot = df_plot[(df_plot['peso'] > 0) & (df_plot['altura'] > 0)]
        
        if not df_plot.empty:
            res_list = df_plot.apply(lambda x: classificar_oms(x['peso'], x['altura'], df_ref[df_ref['genero'] == x['genero']]), axis=1)
            df_plot['Status'] = [r[0] for r in res_list]
            
            fig_turma = px.scatter(
                df_plot, x='altura', y='peso', color='Status',
                hover_data=['aluno'], size_max=15,
                color_discrete_map={
                    "Eutrofia": "#2E8B57", "Risco de sobrepeso": "#FFD700",
                    "Sobrepeso": "#FF8C00", "Obesidade": "#FF0000",
                    "Magreza": "#FF4500", "Magreza acentuada": "#8B0000"
                }
            )
            fig_turma.update_layout(xaxis=dict(dtick=1), yaxis=dict(dtick=1), plot_bgcolor='white')
            st.plotly_chart(fig_turma, use_container_width=True)
            st.dataframe(df_plot[['aluno', 'peso', 'altura', 'Status']], hide_index=True, use_container_width=True)
else:
    st.info("💡 Aguardando carregamento dos arquivos (DADOS - OMC.xlsx e referencias_oms_completo.csv)")
