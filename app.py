import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÃO DE PADRONIZAÇÃO ROBUSTA ---
def preparar_dataframe(df):
    # Limpeza básica de nomes de colunas
    df.columns = [
        str(c).lower().replace('ê', 'e').replace('é', 'e').replace('í', 'i').strip() 
        for c in df.columns
    ]
    
    # Mapeamento inteligente para colunas em Português
    mapeamento = {}
    for col in df.columns:
        if 'aluno' in col: mapeamento[col] = 'aluno'
        if 'matri' in col: mapeamento[col] = 'matricula'
        if 'genero' in col or 'sexo' in col: mapeamento[col] = 'genero'
        if 'peso' in col: mapeamento[col] = 'peso'
        if 'altura' in col or 'estatura' in col: mapeamento[col] = 'altura'
        if 'idade' in col: mapeamento[col] = 'idade'
    
    df = df.rename(columns=mapeamento)
    
    # Garantia de dados para evitar o erro 'AttributeError'
    if 'genero' not in df.columns:
        df['genero'] = 'M'
    else:
        # Força a coluna a ser texto e preenche vazios com 'M' para não travar
        df['genero'] = df['genero'].astype(str).fillna('M').replace('nan', 'M')
        
    return df

# --- 2. CARREGAMENTO DOS DADOS ---
@st.cache_data
def carregar_dados_sistema():
    caminho_ref = "referencias_oms_completo.csv"
    caminho_dados = "DADOS - OMC.xlsx"
    
    try:
        # Carrega Referência OMS
        df_ref = pd.read_csv(caminho_ref, sep=',', on_bad_lines='skip')
        df_ref = preparar_dataframe(df_ref)
        
        # Carrega Planilha de Alunos (lendo todas as abas do Excel)
        dict_turmas = pd.read_excel(caminho_dados, sheet_name=None)
        for aba in dict_turmas:
            dict_turmas[aba] = preparar_dataframe(dict_turmas[aba])
            # Converte valores para números, tratando erros como 'vazio'
            dict_turmas[aba]['peso'] = pd.to_numeric(dict_turmas[aba]['peso'], errors='coerce')
            dict_turmas[aba]['altura'] = pd.to_numeric(dict_turmas[aba]['altura'], errors='coerce')
            
        return df_ref, dict_turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}. Verifique se os nomes dos arquivos estão corretos na pasta.")
        return pd.DataFrame(), {}

def calcular_imc(peso, altura_cm):
    try:
        alt_m = float(altura_cm) / 100
        return round(float(peso) / (alt_m ** 2), 2) if alt_m > 0 else 0
    except: return 0

# --- INTERFACE PRINCIPAL ---
st.title("🍎 NutriGestão Escolar - Marina Mendonça")

df_ref, dict_turmas = carregar_dados_sistema()

if dict_turmas:
    st.sidebar.header("🏫 Menu de Navegação")
    
    # 1. Seleção da Turma (Abas detectadas automaticamente)
    turma_nome = st.sidebar.selectbox("Escolha a Turma:", list(dict_turmas.keys()))
    df_turma = dict_turmas[turma_nome]
    
    # 2. Escolha do Modo de Visualização
    modo = st.sidebar.radio("Tipo de Visualização:", ["Ficha Individual do Aluno", "Análise Geral da Turma"])
    
    if modo == "Ficha Individual do Aluno":
        st.header(f"Ficha do Aluno - {turma_nome}")
        
        # Filtro de Alunos da turma selecionada
        aluno_lista = sorted(df_turma['aluno'].unique())
        aluno_selecionado = st.sidebar.selectbox("Selecione o Aluno:", aluno_lista)
        
        # Dados originais do aluno
        dados_aluno = df_turma[df_turma['aluno'] == aluno_selecionado].iloc[0]
        
        # Painel lateral de edição instantânea
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Ajuste de Dados")
        p_atual = st.sidebar.number_input("Peso (kg):", value=float(dados_aluno.get('peso', 0) or 0), step=0.1)
        a_atual = st.sidebar.number_input("Altura (cm):", value=float(dados_aluno.get('altura', 0) or 0), step=0.1)
        # Tenta identificar o gênero original ou assume Masculino
        g_original = str(dados_aluno.get('genero', 'M')).upper().strip()
        idx_genero = 0 if "M" in g_original else 1
        g_atual = st.sidebar.selectbox("Gênero:", ["Masculino", "Feminino"], index=idx_genero)
        
        # Tradução interna para o filtro do CSV
        g_filtro = "M" if g_atual == "Masculino" else "F"
        
        # Métricas em destaque
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matrícula", dados_aluno.get('matricula', 'Não info.'))
        c2.metric("Idade", dados_aluno.get('idade', 'Não info.'))
        imc_res = calcular_imc(p_atual, a_atual)
        c3.metric("IMC Atual", imc_res)
        c4.metric("Gênero", g_atual)

        # Gráfico de Curva de Crescimento (OMS)
        st.subheader("Curva de Desenvolvimento (Peso x Estatura)")
        # Filtro corrigido para evitar o erro de AttributeError (str.upper)
        curva = df_ref[df_ref['genero'].astype(str).str.upper() == g_filtro]
        
        if not curva.empty:
            fig = go.Figure()
            # Linhas de Referência da OMS
            fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
            fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_0'], name='Z-0 (Peso Ideal)', line=dict(color='green', width=3)))
            fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))
            
            # Ponto Estrela do Aluno
            fig.add_trace(go.Scatter(x=[a_atual], y=[p_atual], mode='markers+text', 
                                     text=[f"{aluno_selecionado}"], textposition="top center",
                                     marker=dict(color='black', size=15, symbol='star'), name='Aluno'))
            
            fig.update_layout(xaxis_title="Estatura (cm)", yaxis_title="Peso (kg)", hovermode="x")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Dados de referência da OMS não carregados corretamente para este gênero.")

    else:
        # --- MODO ANÁLISE GERAL DA TURMA ---
        st.header(f"📊 Panorama Geral - {turma_nome}")
        
        # Calcula IMC para todos os alunos da tabela atual
        df_panorama = df_turma.copy()
        df_panorama['imc'] = df_panorama.apply(lambda x: calcular_imc(x.get('peso', 0), x.get('altura', 0)), axis=1)
        
        # Gráfico de dispersão da turma
        fig_turma = px.scatter(df_panorama, x='altura', y='peso', color='genero', 
                               hover_data=['aluno', 'imc', 'idade'],
                               title=f"Distribuição de Alunos: {turma_nome}",
                               labels={'altura': 'Altura (cm)', 'peso': 'Peso (kg)', 'genero': 'Gênero'})
        
        st.plotly_chart(fig_turma, use_container_width=True)
        
        # Tabela completa para conferência rápida
        st.subheader("Lista de Medições da Turma")
        st.dataframe(df_panorama[['aluno', 'matricula', 'idade', 'peso', 'altura', 'imc']], 
                     use_container_width=True, hide_index=True)

else:
    st.info("💡 Por favor, certifique-se de que o arquivo 'DADOS - OMC.xlsx' está na mesma pasta que este aplicativo.")
