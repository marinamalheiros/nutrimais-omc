import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÃO DE PADRONIZAÇÃO DE COLUNAS ---
def padronizar_colunas(df):
    """Remove acentos, espaços e coloca tudo em minúsculas para evitar erros."""
    df.columns = [
        str(c).lower().replace('ê', 'e').replace('é', 'e').strip() 
        for c in df.columns
    ]
    return df

# --- 2. CARREGAMENTO DAS REFERÊNCIAS OMS ---
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
        if peso > 0 and altura_cm > 0:
            return round(float(peso) / ((float(altura_cm)/100)**2), 2)
        return 0
    except:
        return 0

# --- INTERFACE ---
st.title("🍎 NutriGestão Escolar")

try:
    df_ref = carregar_referencias()
    
    # Sidebar: Upload
    st.sidebar.header("📁 Importação")
    uploaded_file = st.sidebar.file_uploader("Subir Planilha da Turma", type=["xlsx", "csv"])

    if uploaded_file:
        # Lê o ficheiro e já padroniza as colunas (Gênero vira genero, etc)
        if uploaded_file.name.endswith('.csv'):
            df_alunos = pd.read_csv(uploaded_file)
        else:
            df_alunos = pd.read_excel(uploaded_file)
        
        df_alunos = padronizar_colunas(df_alunos)
        
        # Seleção do Aluno
        aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", df_alunos['aluno'].unique())
        dados_originais = df_alunos[df_alunos['aluno'] == aluno_nome].iloc[0]

        # --- 3. SEÇÃO DE EDIÇÃO (SIDEBAR) ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📝 Editar Informações")
        
        # Tratamento de valores nulos
        peso_val = float(dados_originais['peso (kg)']) if pd.notnull(dados_originais['peso (kg)']) else 0.0
        alt_val = float(dados_originais['altura (cm)']) if pd.notnull(dados_originais['altura (cm)']) else 0.0
        gen_val = str(dados_originais['genero']).strip().upper()

        edit_peso = st.sidebar.number_input("Peso (kg):", value=peso_val, step=0.1)
        edit_altura = st.sidebar.number_input("Altura (cm):", value=alt_val, step=0.1)
        edit_gen = st.sidebar.selectbox("Gênero:", ["M", "F"], index=0 if gen_val == "M" else 1)
        edit_idade = st.sidebar.text_input("Idade:", value=str(dados_originais['idade']))

        # --- 4. EXIBIÇÃO ---
        st.header(f"Ficha: {aluno_nome}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matrícula", dados_originais['matricula'])
        c2.metric("Idade", edit_idade)
        c3.metric("Peso Atual", f"{edit_peso} kg")
        c4.metric("Altura Atual", f"{edit_altura} cm")

        # --- 5. GRÁFICO ---
        st.markdown("---")
        st.subheader("Gráfico de Crescimento (Peso x Estatura - OMS)")
        
        # Filtra curva por gênero editado
        df_visual = df_ref[df_ref['genero'] == edit_gen]
        
        if not df_visual.empty:
            fig = go.Figure()
            
            # Linhas de Referência
            fig.add_trace(go.Scatter(x=df_visual['estatura'], y=df_visual['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
            fig.add_trace(go.Scatter(x=df_visual['estatura'], y=df_visual['z_0'], name='Z-0 (Ideal)', line=dict(color='green', width=3)))
            fig.add_trace(go.Scatter(x=df_visual['estatura'], y=df_visual['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))

            # Ponto do Aluno
            imc = calcular_imc(edit_peso, edit_altura)
            fig.add_trace(go.Scatter(x=[edit_altura], y=[edit_peso], mode='markers+text', name='Aluno', 
                                     text=[f"IMC: {imc}"], textposition="top center",
                                     marker=dict(color='black', size=15, symbol='star')))

            fig.update_layout(xaxis_title="Estatura (cm)", yaxis_title="Peso (kg)", height=600)
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"O IMC atualizado é **{imc}**.")
        else:
            st.warning("Dados de referência não encontrados para o gênero selecionado.")

    else:
        st.info("Aguardando upload da planilha da escola...")

except Exception as e:
    st.error(f"Erro no processamento: {e}")

