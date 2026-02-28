import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="NutriGestão Escolar", layout="wide")

# --- CARREGAMENTO DE REFERÊNCIAS ---
@st.cache_data
def carregar_referencias():
    # Carrega o CSV unificado que preparamos (referencias_oms_completo.csv)
    return pd.read_csv("referencias_oms_completo.csv")

def calcular_imc(peso, altura_cm):
    try:
        altura_m = float(altura_cm) / 100
        return round(float(peso) / (altura_m ** 2), 2)
    except:
        return 0

# --- INTERFACE PRINCIPAL ---
st.title("🍎 Dashboard Nutricional Infantil")

try:
    df_ref = carregar_referencias()
    
    # Upload da Planilha da Turma (Maternalzinho, Jardim, etc.)
    uploaded_file = st.sidebar.file_uploader("Subir Planilha da Turma", type=["xlsx", "csv"])

    if uploaded_file:
        # Verifica se o arquivo é CSV ou Excel
        if uploaded_file.name.endswith('.csv'):
            df_alunos = pd.read_csv(uploaded_file)
        else:
            df_alunos = pd.read_excel(uploaded_file)
        
        # Limpeza: remove linhas totalmente vazias
        df_alunos = df_alunos.dropna(subset=['Aluno'])

        # Seleção do Aluno por Nome
        st.sidebar.markdown("---")
        aluno_nome = st.sidebar.selectbox("Selecione o Aluno:", df_alunos['Aluno'].unique())
        
        # Localiza os dados originais do aluno selecionado
        dados_originais = df_alunos[df_alunos['Aluno'] == aluno_nome].iloc[0]

        # --- SEÇÃO DE EDIÇÃO (SIDEBAR) ---
        st.sidebar.subheader("📝 Editar Informações")
        st.sidebar.info("Ajuste os valores abaixo se precisar corrigir algo da planilha.")
        
        # Campos de edição com valores padrão vindos da planilha
        # Tratamos valores nulos (NaN) para não dar erro no componente do Streamlit
        val_peso = float(dados_originais['Peso (kg)']) if pd.notnull(dados_originais['Peso (kg)']) else 0.0
        val_altura = float(dados_originais['Altura (cm)']) if pd.notnull(dados_originais['Altura (cm)']) else 0.0
        
        edit_peso = st.sidebar.number_input("Peso (kg):", value=val_peso, step=0.1)
        edit_altura = st.sidebar.number_input("Altura (cm):", value=val_altura, step=0.1)
        edit_genero = st.sidebar.selectbox("Gênero:", ["M", "F"], 
                                          index=0 if dados_originais['Gênero'] == "M" else 1)
        edit_idade = st.sidebar.text_input("Idade:", value=str(dados_originais['Idade']))

        # Cálculo do IMC com os dados (originais ou editados)
        imc_atual = calcular_imc(edit_peso, edit_altura)

        # --- EXIBIÇÃO DO DASHBOARD ---
        st.header(f"Ficha do Aluno: {aluno_nome}")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Matrícula", dados_originais['Matrícula'])
        col_m2.metric("Idade", edit_idade)
        col_m3.metric("Peso", f"{edit_peso} kg")
        col_m4.metric("Altura", f"{edit_altura} cm")

        # --- GRÁFICO DE CRESCIMENTO (OMS) ---
        st.markdown("---")
        st.subheader("Análise Comparativa: Peso x Estatura")
        
        # Filtra a curva da OMS pelo gênero (M ou F)
        curva_ref = df_ref[df_ref['genero'] == edit_genero]

        fig = go.Figure()

        # Adicionando as linhas de Escore-Z (OMS)
        fig.add_trace(go.Scatter(x=curva_ref['estatura'], y=curva_ref['z_2pos'], 
                                 name='Z+2 (Sobrepeso)', line=dict(color='orange', dash='dot')))
        fig.add_trace(go.Scatter(x=curva_ref['estatura'], y=curva_ref['z_0'], 
                                 name='Z-0 (Mediana)', line=dict(color='green', width=3)))
        fig.add_trace(go.Scatter(x=curva_ref['estatura'], y=curva_ref['z_2neg'], 
                                 name='Z-2 (Baixo Peso)', line=dict(color='red', dash='dot')))

        # Ponto do Aluno (Estrela preta)
        fig.add_trace(go.Scatter(x=[edit_altura], y=[edit_peso],
                                 mode='markers+text', name='Aluno Atual',
                                 text=[f"IMC: {imc_atual}"], textposition="top center",
                                 marker=dict(color='black', size=16, symbol='star')))

        fig.update_layout(
            xaxis_title="Estatura (cm)",
            yaxis_title="Peso (kg)",
            height=600,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Mensagem de Feedback
        if imc_atual > 0:
            st.success(f"Análise concluída para {aluno_nome}. O IMC calculado é **{imc_atual}**.")
        else:
            st.warning("Insira Peso e Altura para visualizar o IMC e a posição no gráfico.")

    else:
        st.info("💡 Marina, selecione uma planilha de turma (ex: Maternal II A) para começar a análise.")

except Exception as e:
    st.error(f"Erro detectado: {e}")
    st.info("Dica: Verifique se o arquivo 'referencias_oms_completo.csv' está na raiz da pasta.")

st.sidebar.markdown("---")
st.sidebar.caption("Nutricionista Responsável: Marina Mendonça")
