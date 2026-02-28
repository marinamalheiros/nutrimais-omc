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
        elif 'z_' in c_lower: mapeamento[col] = c_lower # Mantém z_0, z_1pos, etc.
    
    df = df.rename(columns=mapeamento)
    
    # Converte colunas para numérico (trata vírgula de arquivos brasileiros)
    for col in df.columns:
        if col in ['peso', 'altura'] or col.startswith('z_'):
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    return df

def classificar_oms(peso, altura, curva_ref):
    try:
        if peso <= 0 or altura <= 0 or curva_ref.empty:
            return "Dados Insuficientes", "#808080"
        
        # Acha a linha da altura mais próxima na tabela OMS
        idx = (curva_ref['altura'] - altura).abs().idxmin()
        ref = curva_ref.loc[idx]
        
        p = float(peso)
        # Lógica de Classificação conforme solicitado
        if p < ref['z_3neg']: return "Magreza acentuada", "#8B0000"
        elif p < ref['z_2neg']: return "Magreza", "#FF4500"
        elif p < ref['z_1pos']: return "Eutrofia", "#2E8B57"
        elif p <= ref['z_2pos']: return "Risco de sobrepeso", "#FFD700"
        elif p <= ref['z_3pos']: return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except Exception:
        return "Erro de Cálculo", "#808080"

@st.cache_data
def carregar_dados():
    try:
        # Carrega CSV da OMS
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Carrega Excel dos Alunos
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

# --- 2. EXECUÇÃO ---
df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("📋 Menu NutriMais")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    modo = st.sidebar.radio("Modo:", ["Ficha Individual", "Relatório Coletivo"])

    if modo == "Ficha Individual":
        lista_alunos = sorted(df_atual['aluno'].dropna().unique())
        aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", lista_alunos)
        
        # Busca linha específica do aluno
        dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
        
        st.header(f"Acompanhamento Anual: {aluno_nome}")
        
        cols = st.columns(4)
        medicoes = []
        gen = "M" if "M" in str(dados_aluno.get('genero', 'M')).upper() else "F"
        curva_ref_aluno = df_ref[df_ref['genero'] == gen]

        for i, nome_tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
            with cols[i]:
                st.markdown(f"**{nome_tri}**")
                p_init = float(dados_aluno['peso']) if i == 0 else 0.0
                a_init = float(dados_aluno['altura']) if i == 0 else 0.0
                
                p = st.number_input(f"Peso (kg)", value=p_init, key=f"p{i}_{aluno_nome}", step=0.1)
                a = st.number_input(f"Altura (cm)", value=a_init, key=f"a{i}_{aluno_nome}", step=0.1)
                
                status, cor = classificar_oms(p, a, curva_ref_aluno)
                imc = round(p / ((a/100)**2), 2) if a > 0 else 0
                
                st.metric("IMC", imc)
                st.markdown(f"<div style='background-color:{cor}; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{status}</div>", unsafe_allow_html=True)
                
                if p > 0 and a > 0:
                    medicoes.append({'tri': i+1, 'p': p, 'a': a, 'status': status, 'cor': cor})

        # --- GRÁFICO COM ZOOM CORRIGIDO ---
        if medicoes:
            st.markdown("---")
            fig = go.Figure()
            
            # Define limites do Zoom (5 unidades de margem)
            alturas_m = [m['a'] for m in medicoes]
            pesos_m = [m['p'] for m in medicoes]
            min_x, max_x = min(alturas_m) - 5, max(alturas_m) + 5
            min_y, max_y = min(pesos_m) - 5, max(pesos_m) + 5

            curva_zoom = curva_ref_aluno[(curva_ref_aluno['altura'] >= min_x) & (curva_ref_aluno['altura'] <= max_x)]

            # Desenha as curvas de referência
            refs = [('z_3pos', 'Obs', 'red'), ('z_2pos', 'Sob', 'orange'), ('z_1pos', 'Risco', 'yellow'), 
                    ('z_0', 'Ideal', 'green'), ('z_2neg', 'Mag', 'orange'), ('z_3neg', 'MagAc', 'red')]
            
            for col, lab, color in refs:
                if col in curva_zoom.columns:
                    fig.add_trace(go.Scatter(x=curva_zoom['altura'], y=curva_zoom[col], name=lab, 
                                             line=dict(color=color, width=1.5, dash='dot' if '0' not in col else 'solid'),
                                             hoverinfo='skip'))

            # Pontos do aluno
            for m in medicoes:
                fig.add_trace(go.Scatter(x=[m['a']], y=[m['p']], mode='markers+text', text=[f"T{m['tri']}"],
                                         textposition="top center", marker=dict(size=14, color=m['cor'], line=dict(width=2, color='white')),
                                         name=f"Tri {m['tri']}"))

            fig.update_layout(
                xaxis=dict(range=[min_x, max_x], dtick=1, title="Altura (cm)"),
                yaxis=dict(range=[min_y, max_y], dtick=1, title="Peso (kg)"),
                height=600, template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        # RELATÓRIO COLETIVO
        st.header(f"📊 Relatório Coletivo - {aba_sel}")
        df_turma = df_atual[df_atual['peso'] > 0].copy()
        if not df_turma.empty:
            # Força o cálculo correto para cada aluno da turma
            def aplicar_classif(row):
                curva = df_ref[df_ref['genero'] == row['genero']]
                return classificar_oms(row['peso'], row['altura'], curva)[0]
            
            df_turma['Status'] = df_turma.apply(aplicar_classif, axis=1)
            
            fig_turma = px.scatter(df_turma, x='altura', y='peso', color='Status', hover_data=['aluno'],
                                   color_discrete_map={
                                       "Eutrofia": "#2E8B57", "Risco de sobrepeso": "#FFD700",
                                       "Sobrepeso": "#FF8C00", "Obesidade": "#FF0000",
                                       "Magreza": "#FF4500", "Magreza acentuada": "#8B0000"
                                   })
            fig_turma.update_layout(xaxis=dict(dtick=1), yaxis=dict(dtick=1), template="plotly_white")
            st.plotly_chart(fig_turma, use_container_width=True)
