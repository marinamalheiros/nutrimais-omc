import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from datetime import datetime

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="NutriGestão - Marina Malheiros", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F3E5F5; }
    .status-sidebar { color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    .status-box { padding: 8px; border-radius: 5px; text-align: center; font-weight: bold; color: white; font-size: 0.85rem; margin-bottom: 10px; }
    .header-style { color: #4A148C; font-weight: bold; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE ---
def calcular_meses_exatos(data_nasc, data_afericao):
    try:
        # Garante que ambos são do tipo date para subtrair
        diff = data_afericao - data_nasc
        return round(diff.days / 30.44, 1)
    except:
        return 0

@st.cache_data
def carregar_dados_sistema():
    try:
        nome_csv = "referencias_oms_completo ATUALIZADO.csv" if os.path.exists("referencias_oms_completo ATUALIZADO.csv") else "referencias_oms_completo.csv"
        df_ref = pd.read_csv(nome_csv, sep=';', decimal=',')
        for col in ['z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']:
            df_ref[col] = pd.to_numeric(df_ref[col].astype(str).str.replace(',', '.'), errors='coerce')
        
        arquivo_excel = "DADOS - OMC.xlsx"
        if not os.path.exists(arquivo_excel): return df_ref, None
            
        dict_abas = pd.read_excel(arquivo_excel, sheet_name=None)
        turmas_prontas = {}
        for nome_aba, df in dict_abas.items():
            # Limpa espaços e garante que os nomes das colunas batem com o seu arquivo
            df.columns = [str(c).strip() for c in df.columns]
            
            # MAPEAMENTO EXATO CONFORME SEU ARQUIVO ENVIADO
            mapeamento = {
                'Aluno': 'aluno', 
                'Gênero': 'genero', 
                'Data de Nascimento': 'nasc_data', 
                'Peso (kg)': 'p1', 
                'Altura (cm)': 'a1'
            }
            df = df.rename(columns=mapeamento)
            
            # Converte para data e números tratando erros
            df['nasc_data'] = pd.to_datetime(df['nasc_data'], errors='coerce')
            df['p1'] = pd.to_numeric(df['p1'], errors='coerce').fillna(0.0)
            df['a1'] = pd.to_numeric(df['a1'], errors='coerce').fillna(0.0)
            
            turmas_prontas[nome_aba] = df
        return df_ref, turmas_prontas
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return None, None

def classificar_oms(valor, ref_linha, tipo_indice):
    if ref_linha.empty: return "Sem Ref.", "#808080"
    r = ref_linha.iloc[0]
    try:
        v = float(valor)
        if tipo_indice == 'estatura_idade':
            if v < r['z_3neg']: return "Muito baixa estatura", "#8B0000"
            elif v < r['z_2neg']: return "Baixa estatura", "#FF4500"
            else: return "Estatura adequada", "#2E8B57"
        elif tipo_indice == 'peso_idade':
            if v < r['z_3neg']: return "Muito baixo peso", "#8B0000"
            elif v < r['z_2neg']: return "Baixo peso", "#FF4500"
            elif v < r['z_2pos']: return "Peso adequado", "#2E8B57"
            else: return "Peso elevado", "#FF8C00"
        else:
            if v < r['z_3neg']: return "Magreza acentuada", "#8B0000"
            elif v < r['z_2neg']: return "Magreza", "#FF4500"
            elif v < r['z_1pos']: return "Eutrofia", "#2E8B57"
            elif v < r['z_2pos']: return "Risco sobrepeso", "#FFD700"
            else: return "Sobrepeso/Obesidade", "#FF0000"
    except: return "Erro", "#808080"

# --- 3. EXECUÇÃO ---
df_ref, turmas = carregar_dados_sistema()

if df_ref is not None and turmas:
    st.markdown("<h1 class='header-style'>🍎 NutriGestão</h1>", unsafe_allow_html=True)
    
    aba_sel = st.sidebar.selectbox("Turma:", list(turmas.keys()))
    df_atual = turmas[aba_sel]
    aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_atual['aluno'].unique()))
    
    dados_aluno = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen = 'F' if str(dados_aluno['genero']).upper().startswith('F') else 'M'
    data_nasc = dados_aluno['nasc_data']

    st.header(f"Ficha: {aluno_nome}")
    
    if pd.isna(data_nasc):
        st.error(f"Data de Nascimento não detectada para {aluno_nome} na coluna 'Data de Nascimento'.")
    else:
        cols_tri = st.columns(4)
        medicoes = []

        for i in range(4):
            with cols_tri[i]:
                st.subheader(f"{i+1}ª Aferição")
                # Data da Pesagem selecionável no APP
                data_af = st.date_input(f"Data da Pesagem", value=datetime.now(), key=f"d_{i}_{aluno_nome}")
                p = st.number_input(f"Peso (kg)", value=float(dados_aluno['p1']) if i == 0 else 0.0, key=f"p{i}_{aluno_nome}")
                a = st.number_input(f"Alt (cm)", value=float(dados_aluno['a1']) if i == 0 else 0.0, key=f"a{i}_{aluno_nome}")
                
                if p > 0 and a > 0:
                    meses = calcular_meses_exatos(data_nasc.date(), data_af)
                    imc = round(p / ((a/100)**2), 2)
                    
                    # Status baseado em Peso/Altura
                    ref_pa = df_ref[(df_ref['tipo'] == 'peso_altura') & (df_ref['genero'] == gen)]
                    idx_m = (ref_pa['altura'] - a).abs().idxmin()
                    status, cor = classificar_oms(p, ref_pa.loc[[idx_m]], 'peso_altura')
                    
                    medicoes.append({'p': p, 'a': a, 'imc': imc, 'cor': cor, 'status': status, 'meses': meses})
                    st.markdown(f"<div class='status-box' style='background-color:{cor}'>{status}<br>{meses} meses</div>", unsafe_allow_html=True)

        # --- GRÁFICOS ---
        st.divider()
        g_row = st.columns(2)
        params = [("peso_altura", "Peso x Altura"), ("imc_idade", "IMC x Idade"), ("peso_idade", "Peso x Idade"), ("estatura_idade", "Estatura x Idade")]
        
        for idx, (slug, nome_g) in enumerate(params):
            with g_row[idx % 2]:
                fig = go.Figure()
                curva = df_ref[(df_ref['tipo'] == slug) & (df_ref['genero'] == gen)].copy()
                eixo_x = 'altura' if slug == 'peso_altura' else 'idade_meses'
                
                # Zoom no gráfico baseado na primeira medição
                if medicoes:
                    bx = medicoes[0]['meses']
                    x_min, x_max = (bx - 3, bx + 12) if slug != "peso_altura" else (medicoes[0]['a']-10, medicoes[0]['a']+20)
                else:
                    x_min, x_max = (0, 60) if slug != "peso_altura" else (45, 120)

                for z_col, z_cor in [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]:
                    d_plot = curva[(curva[z_col] > 0.1) & (curva[eixo_x] >= x_min) & (curva[eixo_x] <= x_max)]
                    if not d_plot.empty:
                        fig.add_trace(go.Scatter(x=d_plot[eixo_x], y=d_plot[z_col], line=dict(color=z_cor, width=1.5), mode='lines', hoverinfo='skip'))

                for m in medicoes:
                    vy = m['p'] if 'peso' in slug else (m['a'] if 'estatura' in slug else m['imc'])
                    vx = m['a'] if slug == 'peso_altura' else m['meses']
                    fig.add_trace(go.Scatter(x=[vx], y=[vy], mode='markers+text', text=[f"{vy}"], textposition="top center", marker=dict(size=10, color=m['cor'])))

                fig.update_layout(title=f"<b>{nome_g}</b>", height=300, template="plotly_white", showlegend=False, margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Certifique-se de que o arquivo 'DADOS - OMC.xlsx' está na mesma pasta.")
