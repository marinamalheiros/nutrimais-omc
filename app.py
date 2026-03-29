import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re

# --- 1. CONFIGURAÇÃO DA PÁGINA E ESTILO ---
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #F3E5F5; }
    [data-testid="stMetricValue"] { color: #4A148C; }
    .status-sidebar {
        color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; margin-top: 10px;
    }
    .status-box {
        padding: 5px; border-radius: 5px; text-align: center; font-weight: bold;
        color: white; font-size: 0.85rem; margin-top: -5px; margin-bottom: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 2. FUNÇÕES DE APOIO ---
def converter_idade_para_meses(texto_idade):
    try:
        texto = str(texto_idade).lower().strip()
        numeros = re.findall(r'\d+', texto)
        if not numeros: return 0
        valor = int(numeros[0])
        return valor * 12 if 'ano' in texto else valor
    except: return 0

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
        elif 'idade' in c_lower: mapeamento[col] = 'idade_original'
    df = df.rename(columns=mapeamento)
    cols_num = ['peso', 'altura', 'z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
    for col in df.columns:
        if col in cols_num:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    if 'idade_original' in df.columns:
        df['idade_meses'] = df['idade_original'].apply(converter_idade_para_meses)
    return df

def classificar_oms_geral(valor_y, ref_linha):
    if ref_linha is None or ref_linha.empty: return "Sem Ref.", "#808080"
    try:
        v = float(valor_y)
        ref = ref_linha.iloc[0]
        if v < ref['z_3neg']: return "Muito Baixo / Magreza Ac.", "#8B0000"
        elif v < ref['z_2neg']: return "Baixo / Magreza", "#FF4500"
        elif v < ref['z_1pos']: return "Eutrofia", "#2E8B57"
        elif v <= ref['z_2pos']: return "Risco de Sobrepeso", "#FFD700"
        elif v <= ref['z_3pos']: return "Sobrepeso", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except: return "Erro", "#808080"

@st.cache_data
def carregar_dados():
    try:
        # Carrega o CSV forçando o separador correto
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        
        # --- LIMPEZA CRÍTICA DE GÊNERO E TIPO ---
        df_ref['tipo'] = df_ref['tipo'].astype(str).str.strip().str.lower()
        # Remove espaços e garante que F e M fiquem padronizados
        df_ref['genero'] = df_ref['genero'].astype(str).str.strip().str.upper()
        
        df_ref = preparar_dataframe(df_ref)
        
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return None, None

# --- AJUSTE NA GERAÇÃO DO GRÁFICO ---
def gerar_mini_grafico(tipo, gen, df_ref, medicoes):
    fig = go.Figure()
    # 1. Filtro base por gênero e tipo
    curva_base = df_ref[(df_ref['genero'] == str(gen).strip().upper()) & (df_ref['tipo'] == tipo)]
    
    col_x = 'altura' if tipo == 'peso_altura' else 'idade_meses'
    
    # 2. LIMPEZA DOS ZEROS: Remove linhas onde o eixo X é zero (evita o erro visual)
    curva_base = curva_base[curva_base[col_x] > 0]
    
    # Lógica de escala mensal (Janela de 12 meses)
    if tipo != "peso_altura" and medicoes:
        idade_atual = float(medicoes[0]['x_idade'])
        min_x = max(0, idade_atual - 1)
        max_x = idade_atual + 12
        curva = curva_base[(curva_base[col_x] >= min_x) & (curva_base[col_x] <= max_x)]
        dtick_val = 1 
    else:
        curva = curva_base
        dtick_val = None

    # Desenha as linhas de referência (apenas se houver dados válidos)
    if not curva.empty:
        for col_z, color in [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]:
            if col_z in curva.columns:
                fig.add_trace(go.Scatter(
                    x=curva[col_x], 
                    y=curva[col_z], 
                    line=dict(color=color, width=1, dash='dot' if col_z!='z_0' else 'solid'), 
                    mode='lines', 
                    hoverinfo='skip'
                ))
    
    # Plotagem das aferições (Pontos do Aluno)
    for m in medicoes:
        val_y = m['y_peso'] if 'peso' in tipo else (m['y_alt'] if 'estatura' in tipo else m['y_imc'])
        val_x = m['x_alt'] if tipo == 'peso_altura' else m['x_idade']
        
        # Só plota o ponto se o valor for maior que zero
        if val_y > 0:
            fig.add_trace(go.Scatter(
                x=[val_x], y=[val_y], mode='markers+text',
                text=[f"<b>{val_y}</b>"], textposition="top center",
                marker=dict(size=10, color=m['cor_base'], line=dict(width=1, color='white'))
            ))
    
    fig.update_layout(
        title=f"<b>{tipo.replace('_',' ').upper()}</b>", 
        height=280, margin=dict(l=10, r=10, t=40, b=10), 
        template="plotly_white", 
        showlegend=False,
        xaxis=dict(dtick=dtick_val, title="Idade (Meses)" if tipo != "peso_altura" else "Altura (cm)")
    )
    return fig

# --- 3. GERAÇÃO DE GRÁFICOS ---
def gerar_mini_grafico(tipo, gen, df_ref, medicoes):
    fig = go.Figure()
    # 1. Filtro base por gênero e tipo
    curva_raw = df_ref[(df_ref['genero'] == str(gen).strip().upper()) & (df_ref['tipo'] == tipo)]
    
    col_x = 'altura' if tipo == 'peso_altura' else 'idade_meses'
    
    # --- LIMPEZA CRÍTICA: Remove zeros e nulos das CURVAS de referência ---
    # Isso impede que o gráfico tente desenhar linhas saindo do valor 0
    curva_base = curva_raw[curva_raw[col_x] > 0].copy()
    
    # 2. Lógica de escala mensal (Janela de 12 meses)
    if tipo != "peso_altura" and medicoes:
        idade_atual = float(medicoes[0]['x_idade'])
        min_x = max(0, idade_atual - 1)
        max_x = idade_atual + 12
        curva = curva_base[(curva_base[col_x] >= min_x) & (curva_base[col_x] <= max_x)]
        dtick_val = 1 
    else:
        curva = curva_base
        dtick_val = None

    # 3. Desenha as linhas de referência (APENAS se o valor Y também for > 0)
    if not curva.empty:
        for col_z, color in [('z_3pos', 'red'), ('z_2pos', 'orange'), ('z_0', 'green'), ('z_2neg', 'orange'), ('z_3neg', 'red')]:
            if col_z in curva.columns:
                # Filtramos a sub-curva para garantir que não existam zeros no eixo Y (Peso/Altura/IMC)
                sub_curva = curva[curva[col_z] > 0]
                
                fig.add_trace(go.Scatter(
                    x=sub_curva[col_x], 
                    y=sub_curva[col_z], 
                    line=dict(color=color, width=1, dash='dot' if col_z!='z_0' else 'solid'), 
                    mode='lines', 
                    hoverinfo='skip',
                    connectgaps=False # Impede que o gráfico ligue pontos distantes se houver buracos
                ))
    
    # 4. Plotagem das aferições (Pontos do Aluno)
    for m in medicoes:
        val_y = m['y_peso'] if 'peso' in tipo else (m['y_alt'] if 'estatura' in tipo else m['y_imc'])
        val_x = m['x_alt'] if tipo == 'peso_altura' else m['x_idade']
        
        if val_y > 0:
            fig.add_trace(go.Scatter(
                x=[val_x], y=[val_y], mode='markers+text',
                text=[f"<b>{val_y}</b>"], textposition="top center",
                marker=dict(size=10, color=m['cor_base'], line=dict(width=1, color='white'))
            ))
    
    fig.update_layout(
        title=f"<b>{tipo.replace('_',' ').upper()}</b>", 
        height=280, margin=dict(l=10, r=10, t=40, b=10), 
        template="plotly_white", 
        showlegend=False,
        xaxis=dict(dtick=dtick_val, title="Idade (Meses)" if tipo != "peso_altura" else "Altura (cm)"),
        yaxis=dict(rangemode="nonnegative") # Garante que o gráfico não mostre valores negativos
    )
    return fig
# --- 4. CABEÇALHO E EXECUÇÃO ---
st.title("🍎 Acompanhamento Nutricional - O Mundo da Criança")
st.markdown(f"##### pela Nutricionista Marina Malheiros Mendonça - CRN 5 21456 🍐🍒")

df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    aluno_nome = st.sidebar.selectbox("Aluno:", sorted(df_atual['aluno'].dropna().unique()))
    modo = st.sidebar.radio("Ver:", ["Ficha Individual", "Relatório Coletivo"])

    dados_base = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen = "M" if "M" in str(dados_base.get('genero', 'M')).upper() else "F"

    if modo == "Ficha Individual":
        st.header(f"Ficha: {aluno_nome}")
        cols_tri = st.columns(4)
        lista_medicoes = []
        
        for i, nome_tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
            with cols_tri[i]:
                st.markdown(f"**{nome_tri}**")
                p = st.number_input(f"Peso (kg)", value=float(dados_base['peso']) if i==0 else 0.0, key=f"p{i}")
                a = st.number_input(f"Alt (cm)", value=float(dados_base['altura']) if i==0 else 0.0, key=f"a{i}")
                
                if p > 0 and a > 0:
                    imc = round(p / ((a/100)**2), 2)
                    curva_pa = df_ref[(df_ref['genero'] == gen) & (df_ref['tipo'] == 'peso_altura')]
                    
                    if not curva_pa.empty:
                        # Forçamos a conversão para float para evitar erro de Série
                        idx_m = (curva_pa['altura'].astype(float) - float(a)).abs().idxmin()
                        st_base, cor_base = classificar_oms_geral(p, curva_pa.loc[[idx_m]])
                    else:
                        st_base, cor_base = "Sem Dados", "#808080"
                    
                    lista_medicoes.append({'tri': i+1, 'x_alt': a, 'x_idade': dados_base['idade_meses'], 'y_peso': p, 'y_alt': a, 'y_imc': imc, 'cor_base': cor_base})
                    if i == 0:
                        st.sidebar.markdown(f"<div class='status-sidebar' style='background-color:{cor_base};'>STATUS ATUAL:<br>{st_base}</div>", unsafe_allow_html=True)

        st.markdown("---")
        grade = st.columns(2)
        params = ["peso_altura", "imc_idade", "peso_idade", "estatura_idade"]
        
        for idx, p_nome in enumerate(params):
            with grade[idx % 2]:
                fig_mini = gerar_mini_grafico(p_nome, gen, df_ref, lista_medicoes)
                st.plotly_chart(fig_mini, use_container_width=True)
                
                if lista_medicoes:
                    m = lista_medicoes[-1]
                    val_y_m = m['y_peso'] if 'peso' in p_nome else (m['y_alt'] if 'estatura' in p_nome else m['y_imc'])
                    val_x_m = float(m['x_alt'] if p_nome == 'peso_altura' else m['x_idade'])
                    
                    curva_esp = df_ref[(df_ref['genero'] == gen) & (df_ref['tipo'] == p_nome)]
                    col_x_esp = 'altura' if p_nome == 'peso_altura' else 'idade_meses'
                    
                    if not curva_esp.empty:
                        # Proteção extra: removemos NaNs e garantimos float antes do idxmin
                        temp_serie = (curva_esp[col_x_esp].astype(float) - val_x_m).abs()
                        idx_esp = temp_serie.idxmin()
                        st_esp, cor_esp = classificar_oms_geral(val_y_m, curva_esp.loc[[idx_esp]])
                    else:
                        st_esp, cor_esp = "Sem Dados", "#808080"
                    st.markdown(f"<div class='status-box' style='background-color:{cor_esp};'>{st_esp}</div>", unsafe_allow_html=True)
    else:
        st.header(f"📊 Panorama Coletivo: {aba_sel}")
        st.dataframe(df_atual[df_atual['peso'] > 0][['aluno', 'genero', 'peso', 'altura', 'idade_original']], use_container_width=True)
