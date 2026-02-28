import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÃO DE PADRONIZAÇÃO ROBUSTA ---
def preparar_dataframe(df):
    # Converte nomes de colunas para minúsculas, remove acentos e espaços
    df.columns = [
        str(c).lower().replace('í', 'i').replace('ê', 'e').replace('â', 'a').strip() 
        for c in df.columns
    ]
    
    # Mapeamento inteligente para garantir que as colunas essenciais sejam encontradas
    mapeamento = {}
    for col in df.columns:
        if 'aluno' in col: mapeamento[col] = 'aluno'
        if 'matri' in col: mapeamento[col] = 'matricula'
        if 'genero' in col or 'sexo' in col: mapeamento[col] = 'genero'
        if 'peso' in col: mapeamento[col] = 'peso'
        if 'altura' in col or 'estatura' in col: mapeamento[col] = 'altura'
        if 'idade' in col: mapeamento[col] = 'idade'
    
    return df.rename(columns=mapeamento)

# --- 2. CARREGAMENTO DAS REFERÊNCIAS ---
@st.cache_data
def carregar_referencias():
    try:
        # on_bad_lines='skip' ignora linhas com erro de colunas (como a linha 3 do seu erro)
        df = pd.read_csv(
            "referencias_oms_completo.csv", 
            sep=',', 
            on_bad_lines='skip', 
            encoding='utf-8'
        )
        return padronizar_colunas(df)
    except Exception as e:
        st.error(f"Erro crítico ao ler o arquivo de referências: {e}")
        return pd.DataFrame()

def calcular_imc(peso, altura_cm):
    try:
        alt_m = float(altura_cm) / 100
        return round(float(peso) / (alt_m ** 2), 2) if alt_m > 0 else 0
    except: return 0

# --- INTERFACE ---
st.title("🍎 NutriGestão Escolar")

try:
    df_ref = carregar_referencias()
    uploaded_file = st.sidebar.file_uploader("Subir Planilha da Turma", type=["xlsx", "csv"])

    if uploaded_file:
        # Carregamento do arquivo do usuário
        if uploaded_file.name.endswith('.csv'):
            df_alunos = pd.read_csv(uploaded_file)
        else:
            df_alunos = pd.read_excel(uploaded_file)
        
        df_alunos = preparar_dataframe(df_alunos)
        
        # Seleção do Aluno
        if 'aluno' in df_alunos.columns:
            aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", df_alunos['aluno'].unique())
            dados = df_alunos[df_alunos['aluno'] == aluno_nome].iloc[0]

            # --- 3. SEÇÃO DE EDIÇÃO ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("📝 Editar Informações")
            
            # Garantindo valores numéricos para os inputs
            p_ini = float(dados['peso']) if 'peso' in dados and pd.notnull(dados['peso']) else 0.0
            a_ini = float(dados['altura']) if 'altura' in dados and pd.notnull(dados['altura']) else 0.0
            g_ini = str(dados['genero']).upper().strip() if 'genero' in dados else "F"
            i_ini = str(dados['idade']) if 'idade' in dados else "N/A"
            m_ini = str(dados['matricula']) if 'matricula' in dados else "---"

            edit_peso = st.sidebar.number_input("Peso (kg):", value=p_ini, step=0.1)
            edit_altura = st.sidebar.number_input("Altura (cm):", value=a_ini, step=0.1)
            edit_gen = st.sidebar.selectbox("Gênero:", ["M", "F"], index=0 if "M" in g_ini else 1)

            # --- 4. DASHBOARD ---
            st.header(f"Ficha: {aluno_nome}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Matrícula", m_ini)
            c2.metric("Idade", i_ini)
            c3.metric("Peso Atual", f"{edit_peso} kg")
            c4.metric("Altura Atual", f"{edit_altura} cm")

            # --- 5. GRÁFICO ---
            st.subheader("Posição na Curva de Crescimento (OMS)")
            curva = df_ref[df_ref['genero'] == edit_gen]
            
            if not curva.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
                fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_0'], name='Z-0 (Ideal)', line=dict(color='green', width=3)))
                fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))
                
                imc = calcular_imc(edit_peso, edit_altura)
                fig.add_trace(go.Scatter(x=[edit_altura], y=[edit_peso], mode='markers+text', name='Aluno',
                                         text=[f"IMC: {imc}"], textposition="top center",
                                         marker=dict(color='black', size=15, symbol='star')))
                
                fig.update_layout(xaxis_title="Estatura (cm)", yaxis_title="Peso (kg)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Curva de referência não encontrada. Verifique o arquivo 'referencias_oms_completo.csv'.")
        else:
            st.error("A coluna 'Aluno' não foi encontrada na planilha.")
    else:
        st.info("Aguardando upload da planilha...")

except Exception as e:
    st.error(f"Erro inesperado: {e}")
