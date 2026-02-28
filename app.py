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
    if peso <= 0 or altura <= 0 or curva_ref.empty:
        return "Dados Insuficientes", "gray"
    
    # Busca a linha da curva mais próxima da altura do aluno
    ref = curva_ref.iloc[(curva_ref['altura'] - altura).abs().argsort()[:1]].iloc[0]
    
    if peso < ref['z_3neg']: return "Magreza acentuada", "#8B0000" # Vermelho Escuro
    elif peso < ref['z_2neg']: return "Magreza", "#FF4500" # Laranja Forte
    elif peso < ref['z_1pos']: return "Eutrofia", "#2E8B57" # Verde Marinho
    elif peso <= ref['z_2pos']: return "Risco de sobrepeso", "#FFD700" # Amarelo/Ouro
    elif peso <= ref['z_3pos']: return "Sobrepeso", "#FF8C00" # Laranja Escuro
    else: return "Obesidade", "#FF0000" # Vermelho Vivo

def calcular_imc(p, a):
    return round(p / ((a/100)**2), 2) if a > 0 else 0

@st.cache_data
def carregar_dados():
    try:
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro: {e}"); return None, None

# --- 2. EXECUÇÃO ---
df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("Configurações")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    modo = st.sidebar.radio("Visão:", ["Ficha Individual", "Relatório da Turma"])

    if modo == "Ficha Individual":
        lista = sorted(df_atual['aluno'].dropna().unique())
        aluno = st.sidebar.selectbox("Selecionar Aluno:", lista)
        dados = df_atual[df_atual['aluno'] == aluno].iloc[0]
        
        st.header(f"Acompanhamento Anual: {aluno}")
        
        # --- SEÇÕES TRIMESTRAIS ---
        cols = st.columns(4)
        medicoes = []
        
        for i, nome_tri in enumerate(["1º Trimestre (Atual)", "2º Trimestre", "3º Trimestre", "4º Trimestre"]):
            with cols[i]:
                st.subheader(nome_tri)
                # O primeiro trimestre puxa do Excel, os outros são editáveis
                p_init = float(dados.get('peso', 0) or 0) if i == 0 else 0.0
                a_init = float(dados.get('altura', 0) or 0) if i == 0 else 0.0
                
                p = st.number_input(f"Peso (kg) T{i+1}", value=p_init, key=f"p{i}")
                a = st.number_input(f"Altura (cm) T{i+1}", value=a_init, key=f"a{i}")
                
                imc = calcular_imc(p, a)
                curva_aluno = df_ref[df_ref['genero'] == str(dados.get('genero', 'M'))]
                classif, cor = classificar_oms(p, a, curva_aluno)
                
                st.metric("IMC", imc)
                st.markdown(f"**Status:** <span style='color:{cor}'>{classif}</span>", unsafe_allow_html=True)
                if p > 0: medicoes.append({'trimestre': i+1, 'p': p, 'a': a, 'classif': classif, 'cor': cor})

        # --- GRÁFICO INDIVIDUAL REFORMULADO ---
        if medicoes:
            st.markdown("---")
            st.subheader("Evolução na Curva de Crescimento")
            
            fig = go.Figure()
            # Escala de 1 em 1 para os eixos (Tick 1)
            min_a = min([m['a'] for m in medicoes]) - 5
            max_a = max([m['a'] for m in medicoes]) + 5
            curva_zoom = curva_aluno[(curva_aluno['altura'] >= min_a) & (curva_aluno['altura'] <= max_a)]

            # Linhas de Referência
            labels = [('z_3pos', 'Obesidade', 'red'), ('z_2pos', 'Sobrepeso', 'orange'), 
                      ('z_0', 'Eutrofia', 'green'), ('z_2neg', 'Magreza', 'orange'), ('z_3neg', 'Magreza Acent.', 'red')]
            
            for col, name, color in labels:
                fig.add_trace(go.Scatter(x=curva_zoom['altura'], y=curva_zoom[col], name=name, 
                                         line=dict(color=color, width=1, dash='dash' if '0' not in col else 'solid')))

            # Pontos das 4 aferições
            for m in medicoes:
                fig.add_trace(go.Scatter(x=[m['a']], y=[m['p']], mode='markers+text',
                                         name=f"{m['trimestre']}º Tri", text=[f"T{m['trimestre']}"],
                                         marker=dict(size=12, color=m['cor'], line=dict(width=2, color='black'))))

            fig.update_layout(xaxis=dict(dtick=1), yaxis=dict(dtick=1), xaxis_title="Altura (cm)", yaxis_title="Peso (kg)")
            st.plotly_chart(fig, use_container_width=True)

    else:
        # --- RELATÓRIO COLETIVO ---
        st.header(f"📊 Relatório Coletivo - {aba_sel}")
        df_plot = df_atual.dropna(subset=['peso', 'altura']).copy()
        df_plot = df_plot[(df_plot['peso'] > 0) & (df_plot['altura'] > 0)]
        
        if not df_plot.empty:
            # Aplica a mesma classificação para todos
            df_plot['Classificação'] = df_plot.apply(lambda x: classificar_oms(x['peso'], x['altura'], df_ref[df_ref['genero'] == x['genero']])[0], axis=1)
            
            fig_turma = px.scatter(df_plot, x='altura', y='peso', color='Classificação',
                                   hover_data=['aluno'], title="Panorama da Turma (1ª Aferição)",
                                   color_discrete_map={
                                       "Eutrofia": "#2E8B57", "Risco de sobrepeso": "#FFD700",
                                       "Sobrepeso": "#FF8C00", "Obesidade": "#FF0000",
                                       "Magreza": "#FF4500", "Magreza acentuada": "#8B0000"
                                   })
            fig_turma.update_layout(xaxis=dict(dtick=1), yaxis=dict(dtick=1))
            st.plotly_chart(fig_turma, use_container_width=True)
