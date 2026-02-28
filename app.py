import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuração da Página
st.set_page_config(page_title="NutriGestão Escolar", layout="wide")

# --- FUNÇÕES TÉCNICAS ---
def calcular_imc(peso, altura_cm):
    altura_m = altura_cm / 100
    if altura_m > 0:
        return round(peso / (altura_m ** 2), 2)
    return 0

def classificar_estado_nutricional(peso, altura, sexo):
    """
    Aqui você pode expandir com a lógica exata do seu CSV da OMS.
    Vou simular uma lógica baseada em faixas comuns para 3-5 anos.
    """
    # Exemplo simplificado de Mediana (Z-0) para fins de demonstração
    # Na prática, você faria um lookup na sua tabela de referência
    imc = calcular_imc(peso, altura)
    if imc < 14:
        return "Baixo Peso", "red"
    elif imc <= 17.5:
        return "Adequado", "green"
    else:
        return "Sobrepeso/Obesidade", "orange"

# --- INTERFACE ---
st.title("🍎 Dashboard de Monitoramento Nutricional Infantil")
st.markdown("---")

# Sidebar para Upload
st.sidebar.header("Configurações")
uploaded_file = st.sidebar.file_ acorns_uploader("Subir Planilha de Alunos (.xlsx)", type=["xlsx"])

# Dados de Exemplo (caso não tenha subido arquivo ainda)
if uploaded_file is None:
    st.info("Aguardando upload da planilha. Exibindo dados de exemplo...")
    data = {
        'Nome': ['João Silva', 'Maria Oliveira', 'Pedro Santos'],
        'Idade': [4, 3, 5],
        'Sexo': ['M', 'F', 'M'],
        'Peso': [16.5, 13.2, 19.5],
        'Altura': [102, 95, 110]
    }
    df = pd.DataFrame(data)
else:
    df = pd.read_excel(uploaded_file)

# Seleção do Aluno
aluno_nome = st.sidebar.selectbox("Selecione o Aluno para análise:", df['Nome'].unique())
aluno_data = df[df['Nome'] == aluno_nome].iloc[0]

# --- CÁLCULOS ---
imc = calcular_imc(aluno_data['Peso'], aluno_data['Altura'])
status, cor = classificar_estado_nutricional(aluno_data['Peso'], aluno_data['Altura'], aluno_data['Sexo'])

# --- DISPLAY DE MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Peso Atual", f"{aluno_data['Peso']} kg")
col2.metric("Estatura", f"{aluno_data['Altura']} cm")
col3.metric("IMC", imc)
col4.markdown(f"**Diagnóstico:** <span style='color:{cor}; font-size:20px'>{status}</span>", unsafe_allow_html=True)

st.markdown("---")

# --- GRÁFICO DE CRESCIMENTO (Plotly) ---
# Simulando as curvas da OMS para o gráfico
curva_x = [80, 90, 100, 110, 120]
z_zero = [10.5, 12.8, 15.4, 18.5, 22.0]  # Mediana Peso/Estatura
z_mais_2 = [12.5, 15.0, 18.2, 21.8, 26.0] # Sobrepeso
z_menos_2 = [9.0, 10.8, 13.0, 15.8, 19.0] # Baixo Peso

fig = go.Figure()

# Adicionar as linhas de referência
fig.add_trace(go.Scatter(x=curva_x, y=z_mais_2, name="Z+2 (Sobrepeso)", line=dict(color='orange', dash='dot')))
fig.add_trace(go.Scatter(x=curva_x, y=z_zero, name="Z-0 (Ideal)", line=dict(color='green', width=3)))
fig.add_trace(go.Scatter(x=curva_x, y=z_menos_2, name="Z-2 (Baixo Peso)", line=dict(color='red', dash='dot')))

# Adicionar o ponto do aluno
fig.add_trace(go.Scatter(
    x=[aluno_data['Altura']], 
    y=[aluno_data['Peso']],
    mode='markers+text',
    name=f'Posição de {aluno_nome}',
    text=[aluno_nome],
    textposition="top center",
    marker=dict(color='black', size=15, symbol='star')
))

fig.update_layout(
    title=f"Posição de {aluno_nome} na Curva de Crescimento (Peso x Estatura)",
    xaxis_title="Estatura (cm)",
    yaxis_title="Peso (kg)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- ESPAÇO PARA RELATÓRIO TÉCNICO ---
st.subheader("📝 Observações da Nutricionista")
obs = st.text_area("Digite aqui as orientações para o relatório:", 
                   f"O aluno {aluno_nome} apresenta estado nutricional {status.lower()}. Recomenda-se...")

if st.button("Gerar Resumo para Impressão"):
    st.write("Relatório gerado com sucesso! (Função de exportar PDF pode ser adicionada aqui)")

st.sidebar.markdown("---")
st.sidebar.write(f"Nutricionista: Marina Mendonça")
st.sidebar.write(f"CRN-5 21456")