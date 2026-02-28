import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÕES DE APOIO ---
def preparar_dataframe(df):
    # Padroniza nomes de colunas removendo espaços e caracteres extras
    df.columns = [str(c).strip() for c in df.columns]
    mapeamento = {}
    for col in df.columns:
        c_lower = col.lower()
        if 'aluno' in c_lower: mapeamento[col] = 'aluno'
        elif 'peso' in c_lower: mapeamento[col] = 'peso'
        elif 'altura' in c_lower or 'estatura' in c_lower: mapeamento[col] = 'altura'
        elif 'genero' in c_lower or 'gênero' in c_lower: mapeamento[col] = 'genero'
        elif 'z_0' in c_lower: mapeamento[col] = 'z_0'
        elif 'z_1pos' in c_lower: mapeamento[col] = 'z_1pos'
        elif 'z_2pos' in c_lower: mapeamento[col] = 'z_2pos'
        elif 'z_3pos' in c_lower: mapeamento[col] = 'z_3pos'
        elif 'z_1neg' in c_lower: mapeamento[col] = 'z_1neg'
        elif 'z_2neg' in c_lower: mapeamento[col] = 'z_2neg'
        elif 'z_3neg' in c_lower: mapeamento[col] = 'z_3neg'
    
    df = df.rename(columns=mapeamento)
    
    # Converte dados para numérico garantindo que vírgulas virem pontos
    for col in ['peso', 'altura']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
    
    if 'genero' in df.columns:
        df['genero'] = df['genero'].astype(str).str.upper().str.strip().str[0] # Pega apenas 'M' ou 'F'
    return df

def classificar_oms(peso, altura, curva_ref):
    try:
        if peso <= 0 or altura <= 0 or curva_ref.empty:
            return "Dados Insuficientes", "#808080"
        
        idx = (curva_ref['altura'] - altura).abs().idxmin()
        ref = curva_ref.loc[idx]
        
        # Comparação lógica com as 6 faixas solicitadas
        if peso < float(ref['z_3neg']): return "Magreza acentuada", "#8B0000"
        elif peso < float(ref['z_2neg']): return "Magreza", "#FF4500"
        elif peso < float(ref['z_1pos']): return "Eutrofia", "#2E8B57"
        elif peso <= float(ref['z_2pos']): return "Risco de sobrepeso", "#FFD700"
        elif peso <= float(ref['z_3pos']): return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except:
        return "Erro de Cálculo", "#808080"

@st.cache_data
def carregar_dados():
    try:
        # Carregar Referência OMS
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Carregar Planilhas de Alunos (Excel)
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas_limpas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas_limpas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

# --- 2. EXECUÇÃO ---
df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    st.sidebar.header("📋 Menu NutriMais")
    aba_sel = st.sidebar.selectbox("Escolha a Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    modo = st.sidebar.radio("Navegação:", ["Ficha Individual", "Relatório Coletivo"])

    if modo == "Ficha Individual":
        # Filtra apenas alunos com nome preenchido
        lista_alunos = sorted(df_atual['aluno'].dropna().unique())
        aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", lista_alunos)
        
        # LOCALIZAÇÃO CRÍTICA: Busca os dados específicos DESTE aluno
        dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
        
        st.header(f"Ficha de Acompanhamento: {aluno_nome}")
        
        cols = st.columns(4)
        medicoes = []
        genero_aluno = "M" if "M" in str(dados_aluno.get('genero', 'M')).upper() else "F"
        curva_ref_aluno = df_ref[df_ref['genero'] == genero_aluno]

        for i, nome_tri in enumerate(["1º Trimestre", "2º Trimestre", "3º Trimestre", "4º Trimestre"]):
            with cols[i]:
                st.subheader(nome_tri)
                # O 1º Tri carrega o peso/altura reais da planilha. Os outros começam em 0.0
                if i == 0:
                    p_val = float(dados_aluno['peso'])
                    a_val = float(dados_aluno['altura'])
                else:
                    p_val, a_val = 0.0, 0.0

                p = st.number_input(f"Peso (kg)", value=p_val, key=f"p{i}_{aluno_nome}", step=0.1)
                a = st.number_input(f"Altura (cm)", value=a_val, key=f"a{i}_{aluno_nome}", step=0.1)
                
                imc = round(p / ((a/100)**2), 2) if a > 0 else 0
                status, cor = classificar_oms(p, a, curva_ref_aluno)
                
                st.metric("IMC", imc)
                st.markdown(f"<div style='background-color:{cor}; color:white; padding:10px; border-radius:5px; text-align:center; font-weight:bold;'>{status}</div>", unsafe_allow_html=True)
                
                if p > 0 and a > 0:
                    medicoes.append({'tri': i+1, 'p': p, 'a': a, 'status': status, 'cor': cor})

        # --- GRÁFICO COM ZOOM E ESCALA 1x1 ---
        if medicoes:
            st.markdown("---")
            fig = go.Figure()
            alturas = [m['a'] for m in medicoes]
            c_zoom = curva_ref_aluno[(curva_ref_aluno['altura'] >= min(alturas)-5) & (curva_ref_aluno['altura'] <= max(alturas)+5)]

            refs = [('z_3pos', 'Obesidade', 'red'), ('z_2pos', 'Sobrepeso', 'orange'), 
                    ('z_1pos', 'Risco Sobrep.', 'yellow'), ('z_0', 'Ideal', 'green'), 
                    ('z_2neg', 'Magreza', 'orange'), ('z_3neg', 'Magreza Ac.', 'red')]
            
            for col, lab, color in refs:
                fig.add_trace(go.Scatter(x=c_zoom['altura'], y=c_zoom[col], name=lab, 
                                         line=dict(color=color, width=1, dash='dot' if '0' not in col else 'solid')))

            for m in medicoes:
                fig.add_trace(go.Scatter(x=[m['a']], y=[m['p']], mode='markers+text', text=[f"T{m['tri']}"],
                                         textposition="top center", marker=dict(size=12, color=m['cor'], line=dict(width=2, color='black')),
                                         name=f"Tri {m['tri']}"))

            fig.update_layout(xaxis=dict(dtick=1, title="Altura (cm)"), yaxis=dict(dtick=1, title="Peso (kg)"), height=600)
            st.plotly_chart(fig, use_container_width=True)

    else:
        # RELATÓRIO COLETIVO
        st.header(f"📊 Relatório Coletivo - {aba_sel}")
        df_turma = df_atual[df_atual['peso'] > 0].copy()
        if not df_turma.empty:
            res = df_turma.apply(lambda x: classificar_oms(x['peso'], x['altura'], df_ref[df_ref['genero'] == x['genero']]), axis=1)
            df_turma['Status'] = [r[0] for r in res]
            
            fig_turma = px.scatter(df_turma, x='altura', y='peso', color='Status', hover_data=['aluno'],
                                   color_discrete_map={"Eutrofia": "#2E8B57", "Risco de sobrepeso": "#FFD700", "Sobrepeso": "#FF8C00", "Obesidade": "#FF0000", "Magreza": "#FF4500", "Magreza acentuada": "#8B0000"})
            fig_turma.update_layout(xaxis=dict(dtick=1), yaxis=dict(dtick=1))
            st.plotly_chart(fig_turma, use_container_width=True)
else:
    st.info("💡 Aguardando carregamento dos arquivos (DADOS - OMC.xlsx e referencias_oms_completo.csv)")

