import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re

# Configuração da Página
st.set_page_config(page_title="NutriGestão - O Mundo da Criança", layout="wide")

# --- ESTILO CSS CUSTOMIZADO (Fundo Lilás) ---
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F3E5F5; /* Lilás bem clarinho */
    }
    /* Estilização dos boxes métricos para contraste */
    [data-testid="stMetricValue"] {
        color: #4A148C;
    }
    /* Estilo para a caixa de status na sidebar */
    .status-sidebar {
        color: white; 
        padding: 10px; 
        border-radius: 5px; 
        text-align: center; 
        font-weight: bold; 
        margin-top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 1. FUNÇÕES DE APOIO ---
def converter_idade_para_meses(texto_idade):
    """Lê textos como '3 anos', '1 ano', '18 meses' e devolve o número total de meses."""
    try:
        texto = str(texto_idade).lower().strip()
        # Extrai apenas os números do texto
        numeros = re.findall(r'\d+', texto)
        if not numeros: return 0
        
        valor = int(numeros[0])
        
        # Se a palavra 'ano' estiver no texto, multiplica por 12
        if 'ano' in texto:
            return valor * 12
        return valor
    except:
        return 0

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
        elif 'idade' in c_lower: mapeamento[col] = 'idade_original' # Guarda a idade original (texto)
    
    df = df.rename(columns=mapeamento)
    
    cols_num = ['peso', 'altura', 'z_3neg', 'z_2neg', 'z_1neg', 'z_0', 'z_1pos', 'z_2pos', 'z_3pos']
    for col in df.columns:
        if col in cols_num:
            # Tratamento para garantir que vírgulas virem pontos antes da conversão numérica
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Adiciona a coluna de idade em meses se for a planilha de alunos
    if 'idade_original' in df.columns:
        df['idade_meses'] = df['idade_original'].apply(converter_idade_para_meses)
        
    return df

def classificar_oms_geral(valor_y, ref_linha, label_parametro):
    """Classificação genérica baseada nos Z-scores da linha de referência."""
    try:
        v = float(valor_y)
        # Pega a primeira linha (argsort retorna índices, idxmin retorna rótulo)
        ref = ref_linha.iloc[0]
        
        # Lógica padrão da OMS (pode ser refinada por parâmetro se necessário)
        if v < ref['z_3neg']: return "Muito Baixo / Magreza Ac.", "#8B0000"
        elif v < ref['z_2neg']: return "Baixo / Magreza", "#FF4500"
        elif v < ref['z_1pos']: return "Eutrofia", "#2E8B57"
        elif v <= ref['z_2pos']: return "Risco de Sobrepeso / Elevado", "#FFD700"
        elif v <= ref['z_3pos']: return "Sobrepeso / Muito Elevado", "#FF8C00"
        else: return "Obesidade", "#FF0000"
    except:
        return "Erro", "#808080"

@st.cache_data
def carregar_dados():
    try:
        # 1. Carregamento com separador ; e decimal , conforme seu arquivo
        df_ref = pd.read_csv("referencias_oms_completo.csv", sep=';', decimal=',', on_bad_lines='skip')
        
        # 2. CORREÇÃO: Usamos .str para aplicar em toda a coluna
        if 'tipo' in df_ref.columns:
            df_ref['tipo'] = df_ref['tipo'].astype(str).str.strip().str.lower()
        if 'genero' in df_ref.columns:
            df_ref['genero'] = df_ref['genero'].astype(str).str.strip().str.upper()
            
        # 3. Processa os nomes das colunas e converte números
        df_ref = preparar_dataframe(df_ref)
        
        # 4. Carrega a planilha de alunos (Excel)
        dict_turmas = pd.read_excel("DADOS - OMC.xlsx", sheet_name=None)
        turmas = {n: preparar_dataframe(d) for n, d in dict_turmas.items()}
        
        return df_ref, turmas
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        return None, None

# --- 2. CABEÇALHO ---
st.title("🍎 Acompanhamento Nutricional - O Mundo da Criança")
st.markdown("##### pela Nutricionista Marina Malheiros Mendonça - CRN 5 21456 🍐🍒")

df_ref, dict_turmas = carregar_dados()

if df_ref is not None and dict_turmas:
    # --- BARRA LATERAL (SideBar) ---
    st.sidebar.markdown("### 🥗 Seleção")
    aba_sel = st.sidebar.selectbox("Turma:", list(dict_turmas.keys()))
    df_atual = dict_turmas[aba_sel]
    
    lista_alunos = sorted(df_atual['aluno'].dropna().unique())
    aluno_nome = st.sidebar.selectbox("Aluno:", lista_alunos)
    
    modo = st.sidebar.radio("Ver:", ["Ficha Individual", "Relatório Coletivo"])

    # Dados base do aluno (do Excel)
    dados_aluno_excel = df_atual[df_atual['aluno'] == aluno_nome].iloc[0]
    gen_aluno = "M" if "M" in str(dados_aluno_excel.get('genero', 'M')).upper() else "F"
    idade_aluno_meses = dados_aluno_excel['idade_meses']

    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **{aluno_nome}**")
    st.sidebar.write(f"📅 Idade: **{idade_aluno_meses} meses**")
    st.sidebar.markdown("---")

    if modo == "Ficha Individual":
        st.header(f"Ficha: {aluno_nome}")
        
        # --- FILTRO DE PARÂMETRO NA FICHA INDIVIDUAL ---
        param_grafico = st.selectbox(
            "Visualizar Gráfico de:",
            ["Peso por Estatura", "IMC por Idade", "Peso por Idade", "Estatura por Idade"]
        )
        
        # Mapeamento do parâmetro selecionado para as colunas do CSV de referência
        map_params = {
            "Peso por Estatura": ("peso_altura", "altura", "peso", "Altura (cm)", "Peso (kg)"),
            "IMC por Idade": ("imc_idade", "idade_meses", "imc", "Idade (Meses)", "IMC"),
            "Peso por Idade": ("peso_idade", "idade_meses", "peso", "Idade (Meses)", "Peso (kg)"),
            "Estatura por Idade": ("estatura_idade", "idade_meses", "altura", "Idade (Meses)", "Altura (cm)")
        }
        
        tipo_ref_nome, col_eixo_x, col_valor_y, label_x, label_y = map_params[param_grafico]

        # Filtra a referência pelo gênero e tipo de indicador
        curva_ref_aluno = df_ref[(df_ref['genero'] == gen_aluno) & (df_ref['tipo'] == tipo_ref_nome)]

        # --- INPUTS DE DADOS (TRI) E CLASSIFICAÇÃO AUTOMÁTICA ---
        cols = st.columns(4)
        medicoes = []

        for i, nome_tri in enumerate(["1º Tri", "2º Tri", "3º Tri", "4º Tri"]):
            with cols[i]:
                st.markdown(f"**{nome_tri}**")
                p_v = float(dados_aluno_excel['peso']) if i == 0 else 0.0
                a_v = float(dados_aluno_excel['altura']) if i == 0 else 0.0
                
                # Inputs numéricos
                p = st.number_input(f"Peso (kg)", value=p_v, key=f"pi{i}_{aluno_nome}", step=0.1)
                a = st.number_input(f"Altura (cm)", value=a_v, key=f"ai{i}_{aluno_nome}", step=0.1)
                
                # Cálculo de variáveis derivadas
                imc_calc = round(p / ((a/100)**2), 2) if a > 0 else 0
                
                # Define qual valor será usado no eixo X (Idade ou Altura)
                valor_x_tri = a if tipo_ref_nome == "peso_altura" else idade_aluno_meses
                
                # Define qual valor será usado na comparação Y (Peso, Altura ou IMC)
                valor_y_tri = p if col_valor_y == "peso" else (imc_calc if col_valor_y == "imc" else a)
                
                # Busca a linha de referência exata
                idx_ref = (curva_ref_aluno[col_eixo_x] - valor_x_tri).abs().idxmin() if not curva_ref_aluno.empty else None
                ref_linha = curva_ref_aluno.loc[[idx_ref]] if idx_ref is not None else pd.DataFrame()

                # Classificação
                status, cor = classificar_oms_geral(valor_y_tri, ref_linha, param_grafico)
                
                if p > 0 and a > 0:
                    medicoes.append({'tri': i+1, 'x': valor_x_tri, 'y': valor_y_tri, 'status': status, 'cor': cor, 'p': p, 'a': a, 'imc': imc_calc})
                    st.markdown(f"<p style='color:{cor}; font-weight:bold;'>{status}</p>", unsafe_allow_html=True)
                
                # Atualiza o status na barra lateral baseado na medição mais recente inserida
                if i == 0: # Exemplo usando a primeira medição como 'Atual' para a sidebar
                    st.sidebar.markdown(f"<div class='status-sidebar' style='background-color:{cor};'>{param_grafico}<br>{status}</div>", unsafe_allow_html=True)

        # --- GERAÇÃO DO GRÁFICO INDIVIDUAL ---
        if medicoes:
            fig_ind = go.Figure()
            
            # Dados para zoom do gráfico
            val_x_med = [m['x'] for m in medicoes]
            val_y_med = [m['y'] for m in medicoes]
            
            # Margens de zoom (Idade em meses precisa de margem menor que altura em cm)
            margin_x_zoom = 3 if "Idade" in label_x else 10
            min_x, max_x = min(val_x_med) - margin_x_zoom, max(val_x_med) + margin_x_zoom
            min_y, max_y = min(val_y_med) - 3, max(val_y_med) + 3
            
            # Filtra a curva de referência para a área de zoom
            c_zoom = curva_ref_aluno[(curva_ref_aluno[col_eixo_x] >= min_x) & (curva_ref_aluno[col_eixo_x] <= max_x)]

            # Linhas de Z-score (Referências)
            # Adaptado para usar os labels de diagnóstico padrão da OMS
            refs = [('z_3pos', 'Muito Elevado', 'red'), ('z_2pos', 'Elevado', 'orange'), 
                    ('z_1pos', 'Risco Elevado', 'yellow'), ('z_0', 'Mediana', 'green'), 
                    ('z_2neg', 'Baixo', 'orange'), ('z_3neg', 'Muito Baixo', 'red')]
            
            for col_z, lab_z, color_z in refs:
                if col_z in c_zoom.columns:
                    # Define se a linha é pontilhada (Mediana) ou sólida (Z-scores)
                    dash_style = 'solid' if col_z == 'z_0' else 'dash'
                    
                    fig_ind.add_trace(go.Scatter(x=c_zoom[col_eixo_x], y=c_zoom[col_z], name=lab_z, 
                                             line=dict(color=color_z, width=1.5, dash=dash_style),
                                             mode='lines', hoverinfo='skip'))

            # Plota os pontos das medições dos trimestres
            for m in medicoes:
                hovertxt = f"<b>T{m['tri']}</b><br>{label_y}: {m['y']}<br>{label_x}: {m['x']}"
                if 'imc' in m: hovertxt += f"<br>IMC: {m['imc']}"

                fig_ind.add_trace(go.Scatter(x=[m['x']], y=[m['y']], mode='markers+text', text=[f"T{m['tri']}"],
                                         textposition="top center", marker=dict(size=14, color=m['cor'], line=dict(width=2, color='white')),
                                         name=f"T{m['tri']}", hovertemplate=hovertxt))

            # Configurações de layout do gráfico
            fig_ind.update_layout(xaxis=dict(range=[min_x, max_x], title=label_x, dtick=1 if "Idade" in label_x else None),
                              yaxis=dict(range=[min_y, max_y], title=label_y),
                              height=600, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white',
                              title=f"Curva de Acompanhamento: {param_grafico}")
            
            st.plotly_chart(fig_ind, use_container_width=True)

    else:
        # --- RELATÓRIO COLETIVO (MANTIDO CONFORME ORIGINAL, FOCADO EM PESO/ESTATURA) ---
        st.header(f"📊 Panorama: {aba_sel}")
        df_turma = df_atual[df_atual['peso'] > 0].copy()
        if not df_turma.empty:
            
            # Filtra apenas peso_altura para o coletivo
            df_ref_pa = df_ref[df_ref['tipo'] == 'peso_altura']
            
            # Aplica classificação linha a linha filtrando o gênero correto na referência
            df_turma['Status'] = df_turma.apply(lambda x: classificar_oms(x['peso'], x['altura'], df_ref_pa[df_ref_pa['genero'] == x['genero']])[0], axis=1)
            
            fig_col = go.Figure()
            min_xc, max_xc = df_turma['altura'].min() - 5, df_turma['altura'].max() + 5
            min_yc, max_yc = df_turma['peso'].min() - 5, df_turma['peso'].max() + 5
            
            # Para o fundo do gráfico coletivo, usamos a referência do gênero do aluno selecionado na sidebar
            curva_c = df_ref_pa[df_ref_pa['genero'] == gen_aluno] 
            c_c_zoom = curva_c[(curva_c['altura'] >= min_xc) & (curva_c['altura'] <= max_xc)]
            
            refs = [('z_3pos', 'Obesidade', 'red'), ('z_2pos', 'Sobrepeso', 'orange'), 
                    ('z_1pos', 'Risco Sobrep.', 'yellow'), ('z_0', 'Eutrofia', 'green'), 
                    ('z_2neg', 'Magreza', 'orange'), ('z_3neg', 'Magreza Ac.', 'red')]
            
            for col, lab, color in refs:
                if col in c_c_zoom.columns:
                    fig_col.add_trace(go.Scatter(x=c_c_zoom['altura'], y=c_c_zoom[col], name=lab, 
                                             line=dict(color=color, width=1.5, dash='dash'), mode='lines', hoverinfo='skip'))

            for status, cor in [("Eutrofia", "#2E8B57"), ("Risco de sobrepeso", "#FFD700"), ("Sobrepeso", "#FF8C00"), 
                                ("Obesidade", "#FF0000"), ("Magreza", "#FF4500"), ("Magreza acentuada", "#8B0000")]:
                df_f = df_turma[df_turma['Status'] == status]
                if not df_f.empty:
                    fig_col.add_trace(go.Scatter(x=df_f['altura'], y=df_f['peso'], mode='markers',
                                                 name=status, marker=dict(size=12, color=cor),
                                                 text=df_f['aluno'], hovertemplate="<b>%{text}</b><br>Peso: %{y}kg<br>Alt: %{x}cm"))

            fig_col.update_layout(xaxis=dict(range=[min_xc, max_xc], dtick=1, title="Altura (cm)"),
                                  yaxis=dict(range=[min_yc, max_yc], dtick=1, title="Peso (kg)"),
                                  height=600, template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='white')
            st.plotly_chart(fig_col, use_container_width=True)
            st.markdown("### 📋 Tabela de Dados da Turma")
            st.dataframe(df_turma[['aluno', 'genero', 'peso', 'altura', 'Status']], use_container_width=True, hide_index=True)
