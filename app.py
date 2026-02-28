import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

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
    
    # Conversão numérica rigorosa para evitar erros de cálculo
    cols_num = ['peso', 'altura', 'z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
    for col in df.columns:
        if col in cols_num:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    return df

def classificar_oms(peso, altura, curva_ref):
    try:
        if peso <= 0 or altura <= 0 or curva_ref.empty:
            return "Dados Insuficientes", "#808080"
        
        # Encontra a linha da OMS mais próxima da altura do aluno
        idx = (curva_ref['altura'] - altura).abs().idxmin()
        ref = curva_ref.loc[idx]
        
        p = float(peso)
        # Lógica de Classificação Solicitada
        if p < ref['z_3neg']: return "Magreza acentuada", "#8B0000"
        elif p < ref['z_2neg']: return "Magreza", "#FF4500"
        elif p < ref['z_1pos']: return "Eutrofia", "#2E8B57"
        elif p <= ref['z_2pos']: return "Risco de sobrepeso", "#FFD700"
        elif p <= ref['z_3pos']: return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except:
        return "Erro de Cálculo", "#808080"

@st.cache_data
def carregar_dados():
    try:
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

# --- 2. EXECUÇÃO ---
df_ref, dict_turmas = carregar_dados()

# Título e Subtítulo Principal
st.title("🍎 Acompanhamento Nutricional - O Mundo da Criança")
st.markdown("##### pela Nutricionista Marina Malheiros Mendonça - CRN 5 21456 🍐🍒")

if df_ref is not None and dict_turmas:
    # --- BARRA LATERAL ---
    st.sidebar.markdown("### 🥗 Configurações")
    aba_sel = st.sidebar.selectbox("Selecione a Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    
    lista_alunos = sorted(df_atual['aluno'].dropna().unique())
    aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", lista_alunos)
    
    # Busca dados do aluno para a sidebar
    dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen_aluno = "M" if "M" in str(dados_aluno.get('genero', 'M')).upper() else "F"
    curva_ref_aluno = df_ref[df_ref['genero'] == gen_aluno]
    
    # IMC e Classificação na Sidebar (Status Atual da Planilha)
    p_atual = float(dados_aluno['peso'])
    a_atual = float(dados_aluno['altura'])
    status_sidebar, cor_sidebar = classificar_oms(p_atual, a_atual, curva_ref_aluno)
    imc_sidebar = round(p_atual / ((a_atual/100)**2), 2) if a_atual > 0 else 0
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Status Atual de {aluno_nome.split()[0]}:**")
    st.sidebar.metric("IMC Atual", imc_sidebar)
    st.sidebar.markdown(f"<div style='background-color:{cor_sidebar}; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{status_sidebar}</div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    modo = st.sidebar.radio("Navegação:", ["Ficha Individual", "Relatório Coletivo"])

    if modo == "Ficha Individual":
        st.header(f"Evolução Trimestral: {aluno_nome}")
        
        cols = st.columns(4)
        medicoes = []

        for i, nome_tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
            with cols[i]:
                st.markdown(f"**{nome_tri}**")
                p_init = float(dados_aluno['peso']) if i == 0 else 0.0
                a_init = float(dados_aluno['altura']) if i == 0 else 0.0
                
                p = st.number_input(f"Peso (kg)", value=p_init, key=f"p{i}_{aluno_nome}", step=0.1)
                a = st.number_input(f"Altura (cm)", value=a_init, key=f"a{i}_{aluno_nome}", step=0.1)
                
                status, cor = classificar_oms(p, a, curva_ref_aluno)
                if p > 0 and a > 0:
                    medicoes.append({'tri': i+1, 'p': p, 'a': a, 'status': status, 'cor': cor})
                    st.markdown(f"<p style='color:{cor}; font-weight:bold;'>{status}</p>", unsafe_allow_html=True)

        # --- GRÁFICO INDIVIDUAL ---
        if medicoes:
            fig = go.Figure()
            # Ajuste de Zoom
            alturas_m = [m['a'] for m in medicoes]
            pesos_m = [m['p'] for m in medicoes]
            min_x, max_x = min(alturas_m) - 4, max(alturas_m) + 4
            min_y, max_y = min(pesos_m) - 4, max(pesos_m) + 4

            curva_zoom = curva_ref_aluno[(curva_ref_aluno['altura'] >= min_x) & (curva_ref_aluno['altura'] <= max_x)]

            # Apenas linhas de classificação
            refs = [('z_3pos', 'Obesidade', 'red'), ('z_2pos', 'Sobrepeso', 'orange'), 
                    ('z_1pos', 'Risco Sobrep.', 'yellow'), ('z_0', 'Eutrofia', 'green'), 
                    ('z_2neg', 'Magreza', 'orange'), ('z_3neg', 'Magreza Ac.', 'red')]
            
            for col, lab, color in refs:
                fig.add_trace(go.Scatter(x=curva_zoom['altura'], y=curva_zoom[col], name=lab, 
                                         line=dict(color=color, width=2, dash='dot' if '0' not in col else 'solid'),
                                         mode='lines', hoverinfo='skip'))

            # Marcador do aluno
            for m in medicoes:
                fig.add_trace(go.Scatter(x=[m['a']], y=[m['p']], mode='markers+text', text=[f"T{m['tri']}"],
                                         textposition="top center", marker=dict(size=14, color=m['cor'], line=dict(width=2, color='white')),
                                         name=f"Registro T{m['tri']}"))

            fig.update_layout(xaxis=dict(range=[min_x, max_x], dtick=1, title="Altura (cm)"),
                              yaxis=dict(range=[min_y, max_y], dtick=1, title="Peso (kg)"),
                              height=600, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    else:
        # --- RELATÓRIO COLETIVO ---
        st.header(f"📊 Panorama da Turma: {aba_sel}")
        df_turma = df_atual[df_atual['peso'] > 0].copy()
        
        if not df_turma.empty:
            # Classifica todos
            df_turma['Status'] = df_turma.apply(lambda x: classificar_oms(x['peso'], x['altura'], df_ref[df_ref['genero'] == x['genero']])[0], axis=1)
            
            fig_coletivo = go.Figure()
            # Limites para o zoom coletivo
            min_xc, max_xc = df_turma['altura'].min() - 5, df_turma['altura'].max() + 5
            min_yc, max_yc = df_turma['peso'].min() - 5, df_turma['peso'].max() + 5
            
            # Referências no coletivo (Baseado no primeiro gênero encontrado ou média)
            curva_col = df_ref[df_ref['genero'] == gen_aluno] 
            curva_col_zoom = curva_col[(curva_col['altura'] >= min_xc) & (curva_col['altura'] <= max_xc)]
            
            refs = [('z_3pos', 'Obesidade', 'red'), ('z_2pos', 'Sobrepeso', 'orange'), 
                    ('z_1pos', 'Risco Sobrep.', 'yellow'), ('z_0', 'Eutrofia', 'green'), 
                    ('z_2neg', 'Magreza', 'orange'), ('z_3neg', 'Magreza Ac.', 'red')]
            
            for col, lab, color in refs:
                fig_coletivo.add_trace(go.Scatter(x=curva_col_zoom['altura'], y=curva_col_zoom[col], name=lab, 
                                                 line=dict(color=color, width=1.5, dash='dash'), mode='lines', hoverinfo='skip'))

            # Pontos dos alunos
            for status, cor in [("Eutrofia", "#2E8B57"), ("Risco de sobrepeso", "#FFD700"), ("Sobrepeso", "#FF8C00"), 
                                ("Obesidade", "#FF0000"), ("Magreza", "#FF4500"), ("Magreza acentuada", "#8B0000")]:
                df_f = df_turma[df_turma['Status'] == status]
                if not df_f.empty:
                    fig_coletivo.add_trace(go.Scatter(x=df_f['altura'], y=df_f['peso'], mode='markers',
                                                     name=status, marker=dict(size=12, color=cor),
                                                     text=df_f['aluno'], hovertemplate="<b>%{text}</b><br>Peso: %{y}kg<br>Alt: %{x}cm"))

            fig_coletivo.update_layout(xaxis=dict(range=[min_xc, max_xc], dtick=1, title="Altura (cm)"),
                                       yaxis=dict(range=[min_yc, max_yc], dtick=1, title="Peso (kg)"),
                                       height=700, template="plotly_white")
            st.plotly_chart(fig_coletivo, use_container_width=True)
            fig_turma.update_layout(xaxis=dict(dtick=1), yaxis=dict(dtick=1), template="plotly_white")
            st.plotly_chart(fig_turma, use_container_width=True)

