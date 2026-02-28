import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="NutriGestão - Marina Mendonça", layout="wide")

# --- 1. FUNÇÃO DE PADRONIZAÇÃO ULTRA-ROBUSTA ---
def preparar_dataframe(df):
    # 1. Limpeza básica: minúsculas, remove espaços e acentos comuns
    df.columns = [
        str(c).lower().replace('ê', 'e').replace('é', 'e').replace('í', 'i').strip() 
        for c in df.columns
    ]
    
    # 2. Mapeamento inteligente para colunas essenciais
    mapeamento = {}
    for col in df.columns:
        if 'aluno' in col: mapeamento[col] = 'aluno'
        if 'matri' in col: mapeamento[col] = 'matricula'
        if 'genero' in col or 'sexo' in col: mapeamento[col] = 'genero'
        if 'peso' in col: mapeamento[col] = 'peso'
        if 'altura' in col or 'estatura' in col: mapeamento[col] = 'altura'
        if 'idade' in col: mapeamento[col] = 'idade'
    
    df = df.rename(columns=mapeamento)
    
    # 3. Garantia: Se a coluna 'genero' ainda não existir, cria uma vazia para não dar erro
    if 'genero' not in df.columns:
        df['genero'] = 'M' # Valor padrão preventivo
        
    return df

# --- 2. CARREGAMENTO DAS REFERÊNCIAS ---
@st.cache_data
def carregar_referencias():
    try:
        # Resolve o erro "Expected 17 fields, saw 18" ignorando linhas más
        df = pd.read_csv(
            "referencias_oms_completo.csv", 
            sep=',', 
            on_bad_lines='skip', 
            encoding='utf-8'
        )
        return preparar_dataframe(df)
    except Exception as e:
        st.error(f"Erro ao carregar ficheiro de referência: {e}")
        # Retorna uma tabela mínima para o gráfico não quebrar totalmente
        return pd.DataFrame(columns=['genero', 'estatura', 'z_0', 'z_2pos', 'z_2neg'])

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
        # Carregamento do ficheiro da escola
        df_alunos = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        df_alunos = preparar_dataframe(df_alunos)
        
        if 'aluno' in df_alunos.columns:
            aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", df_alunos['aluno'].unique())
            dados = df_alunos[df_alunos['aluno'] == aluno_nome].iloc[0]

            # --- 3. SEÇÃO DE EDIÇÃO ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("📝 Editar Dados")
            
            # Valores iniciais protegidos contra erros
            p_ini = float(dados['peso']) if 'peso' in dados and pd.notnull(dados['peso']) else 0.0
            a_ini = float(dados['altura']) if 'altura' in dados and pd.notnull(dados['altura']) else 0.0
            g_ini = str(dados['genero']).upper().strip() if 'genero' in dados else "M"

            edit_peso = st.sidebar.number_input("Peso (kg):", value=p_ini, step=0.1)
            edit_altura = st.sidebar.number_input("Altura (cm):", value=a_ini, step=0.1)
            edit_gen = st.sidebar.selectbox("Gênero:", ["M", "F"], index=0 if "M" in g_ini else 1)

            # --- 4. EXIBIÇÃO ---
            st.header(f"Ficha: {aluno_nome}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Matrícula", dados.get('matricula', 'N/A'))
            c2.metric("Idade", dados.get('idade', 'N/A'))
            c3.metric("Peso", f"{edit_peso} kg")
            c4.metric("Altura", f"{edit_altura} cm")

            # --- 5. GRÁFICO ---
            st.subheader("Análise Comparativa (OMS)")
            curva = df_ref[df_ref['genero'].str.upper() == edit_gen]
            
            if not curva.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2pos'], name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
                fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_0'], name='Z-0 (Mediana)', line=dict(color='green', width=3)))
                fig.add_trace(go.Scatter(x=curva['estatura'], y=curva['z_2neg'], name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))
                
                imc = calcular_imc(edit_peso, edit_altura)
                fig.add_trace(go.Scatter(x=[edit_altura], y=[edit_peso], mode='markers+text', name='Aluno',
                                         text=[f"IMC: {imc}"], textposition="top center",
                                         marker=dict(color='black', size=15, symbol='star')))
                
                st.plotly_chart(fig, use_container_width=True)
                st.success(f"IMC: {imc}")
            else:
                st.warning("Aguardando dados de referência válidos para gerar o gráfico.")
        else:
            st.error("Coluna 'Aluno' não encontrada. Verifique o cabeçalho da sua planilha.")
    else:
        st.info("💡 Marina, carregue uma planilha (ex: Jardim II) para começar.")

except Exception as e:
    st.error(f"Ocorreu um erro inesperado: {e}")
