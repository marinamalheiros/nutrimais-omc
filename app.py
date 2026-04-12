import streamlit as st
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date
import json
import os

st.set_page_config(page_title="NutriMais - Acompanhamento Nutricional", page_icon="\U0001F34E", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #F3E5F5; }
    .status-box {
        padding: 10px; border-radius: 8px; text-align: center;
        font-weight: bold; color: white; font-size: 0.85rem;
        margin-bottom: 10px;
    }
    .status-sidebar {
        color: white; padding: 15px; border-radius: 10px;
        text-align: center; font-weight: bold; margin-bottom: 20px;
        font-size: 1rem;
    }
    .header-style { color: #4A148C; font-weight: bold; margin-bottom: 5px; }
    .info-box {
        background: white; border-radius: 8px; padding: 8px 12px;
        margin-bottom: 8px; font-size: 0.85rem; color: #333;
        border-left: 3px solid #7B1FA2;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def gerar_referencias_oms():
    def _tabela_meses(m_ref, L_ref, M_ref, S_ref, max_mes):
        eixo = np.arange(0, max_mes + 1, dtype=float)
        L = np.interp(eixo, m_ref, L_ref)
        M = np.interp(eixo, m_ref, M_ref)
        S = np.interp(eixo, m_ref, S_ref)
        dados = {"meses": eixo.tolist(), "_L": L.tolist(), "_M": M.tolist(), "_S": S.tolist()}
        for z in [-3, -2, -1, 0, 1, 2, 3]:
            vals = []
            for i in range(len(eixo)):
                if abs(L[i]) > 0.001:
                    v = M[i] * (1 + L[i] * S[i] * z) ** (1.0 / L[i])
                else:
                    v = M[i] * np.exp(S[i] * z)
                vals.append(round(max(v, 0), 2))
            dados[f"z{z}"] = vals
        return dados

    def _tabela_altura(a_ref, L_ref, M_ref, S_ref):
        eixo = np.arange(int(a_ref[0]), int(a_ref[-1]) + 1, dtype=float)
        L = np.interp(eixo, a_ref, L_ref)
        M = np.interp(eixo, a_ref, M_ref)
        S = np.interp(eixo, a_ref, S_ref)
        dados = {"altura": eixo.tolist(), "_L": L.tolist(), "_M": M.tolist(), "_S": S.tolist()}
        for z in [-3, -2, -1, 0, 1, 2, 3]:
            vals = []
            for i in range(len(eixo)):
                if abs(L[i]) > 0.001:
                    v = M[i] * (1 + L[i] * S[i] * z) ** (1.0 / L[i])
                else:
                    v = M[i] * np.exp(S[i] * z)
                vals.append(round(max(v, 0), 2))
            dados[f"z{z}"] = vals
        return dados

    refs = {}

    m = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120]
    refs[("M","peso_idade")] = _tabela_meses(
        m,
        [-0.3521,-0.1600,0.0150,-0.0700,-0.1100,-0.0400,0.2300,0.3300,0.4300,0.4600,0.4800,0.4800,0.4700,0.4100,0.3500,0.2500,0.1500,0.0400,-0.0700,-0.2800,-0.4500,-0.6000,-0.7300,-0.8400],
        [3.3464,4.4709,5.5675,6.3762,7.0023,7.5105,7.9340,8.9014,9.6500,10.3060,10.8500,11.4900,12.1515,13.3000,14.3400,15.3500,16.3290,17.3370,18.3390,20.5060,22.8880,25.6270,28.7590,32.2360],
        [0.14602,0.13395,0.12385,0.11727,0.11316,0.10984,0.10867,0.10700,0.10900,0.11000,0.11100,0.11300,0.11500,0.11600,0.11727,0.11870,0.12000,0.12100,0.12200,0.13000,0.13800,0.14800,0.16000,0.17200],
        120
    )

    m = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120,132,144,156,168,180,192,204,216,228]
    refs[("M","estatura_idade")] = _tabela_meses(
        m,
        [1.0]*len(m),
        [49.8842,54.7244,58.4249,61.4292,63.8860,65.9026,67.6236,71.8540,75.7488,79.2328,82.2515,84.9413,87.8161,92.8700,96.0980,99.7130,103.3440,106.7150,110.0040,116.0000,121.7000,127.3000,132.6000,138.0000,143.5000,149.5000,156.0000,163.2000,169.0000,173.0000,175.5000,176.5000,176.8000],
        [0.03795,0.03610,0.03480,0.03380,0.03350,0.03310,0.03290,0.03210,0.03100,0.03070,0.03050,0.03045,0.03100,0.03170,0.03230,0.03280,0.03330,0.03380,0.03420,0.03510,0.03600,0.03660,0.03700,0.03750,0.03800,0.03850,0.03800,0.03700,0.03600,0.03500,0.03400,0.03350,0.03300],
        228
    )

    m = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120,132,144,156,168,180,192,204,216,228]
    refs[("M","imc_idade")] = _tabela_meses(
        m,
        [-0.3053,-0.2300,-0.1500,-0.0700,0.0500,0.2500,0.5526,0.7200,0.8400,0.9000,0.9600,0.9800,1.0000,0.8600,0.7200,0.5000,0.2800,0.0600,-0.1600,-0.5700,-0.9300,-1.2100,-1.4400,-1.6300,-1.7800,-1.8900,-1.9600,-2.0000,-2.0100,-2.0000,-1.9700,-1.9300,-1.9000],
        [13.4069,14.9500,16.4000,16.7600,17.1000,17.3000,17.4171,17.1776,16.5500,16.1200,15.9965,15.8500,16.0189,15.8000,15.6600,15.4800,15.3200,15.2500,15.2088,15.2900,15.5400,15.9400,16.4700,17.1200,17.8800,18.7300,19.6400,20.5000,21.2300,21.8000,22.2000,22.5000,22.7000],
        [0.09295,0.08800,0.08400,0.08300,0.08200,0.08140,0.08110,0.08015,0.07920,0.07870,0.07825,0.07800,0.07802,0.07810,0.07820,0.07900,0.08000,0.08150,0.08320,0.08700,0.09300,0.09900,0.10500,0.11100,0.11600,0.12000,0.12200,0.12300,0.12200,0.12000,0.11800,0.11600,0.11400],
        228
    )

    a = [45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120]
    refs[("M","peso_estatura")] = _tabela_altura(
        a,
        [-0.3521,-0.3000,-0.2500,-0.2000,-0.1500,-0.1000,-0.0500,0.0000,0.1000,0.1500,0.2000,0.2500,0.3000,0.3000,0.2500,0.2000],
        [2.4410,3.1500,4.4000,5.6000,6.9000,8.1000,9.2000,10.3000,11.5000,12.6000,13.8000,15.1000,16.5000,17.8000,19.4000,21.1000],
        [0.09200,0.09100,0.09000,0.08900,0.08800,0.08700,0.08600,0.08500,0.08400,0.08500,0.08600,0.08700,0.08800,0.09000,0.09200,0.09400]
    )

    m = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120]
    refs[("F","peso_idade")] = _tabela_meses(
        m,
        [-0.3833,-0.1800,0.0100,-0.0900,-0.1300,-0.0600,0.1500,0.2500,0.3600,0.4000,0.4200,0.4200,0.4200,0.3600,0.3000,0.2000,0.1000,-0.0100,-0.1200,-0.3500,-0.5500,-0.7000,-0.8200,-0.9000],
        [3.2322,4.1872,5.1282,5.8458,6.4237,6.8985,7.2970,8.2000,8.9500,9.6600,10.2000,10.8700,11.5000,12.6700,13.9000,14.9800,15.9000,16.9000,17.9700,20.2200,22.8200,25.8200,29.2700,33.0000],
        [0.14171,0.13724,0.12922,0.12200,0.11800,0.11500,0.11300,0.11100,0.11200,0.11300,0.11400,0.11500,0.11700,0.11800,0.12000,0.12200,0.12500,0.12800,0.13100,0.14000,0.15000,0.16000,0.17000,0.17800],
        120
    )

    m = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120,132,144,156,168,180,192,204,216,228]
    refs[("F","estatura_idade")] = _tabela_meses(
        m,
        [1.0]*len(m),
        [49.1477,53.6872,57.0673,59.8029,62.0899,63.9890,65.7311,70.0800,74.0015,77.5000,80.7000,83.6500,86.4000,91.7400,95.1000,99.1000,102.7000,106.2000,109.4000,115.4000,121.3000,127.2000,133.0000,138.6000,145.0000,151.5000,156.8000,160.0000,162.0000,163.0000,163.4000,163.6000,163.7000],
        [0.03790,0.03600,0.03500,0.03400,0.03370,0.03340,0.03310,0.03200,0.03100,0.03080,0.03070,0.03060,0.03100,0.03180,0.03260,0.03310,0.03360,0.03400,0.03450,0.03560,0.03670,0.03740,0.03790,0.03810,0.03800,0.03750,0.03650,0.03530,0.03420,0.03360,0.03320,0.03300,0.03290],
        228
    )

    m = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120,132,144,156,168,180,192,204,216,228]
    refs[("F","imc_idade")] = _tabela_meses(
        m,
        [-0.0631,0.1000,0.2500,0.3500,0.5000,0.6500,0.7657,0.8800,0.9529,0.9800,1.0000,0.9900,0.9800,0.8700,0.7500,0.5500,0.3500,0.1500,-0.0500,-0.4500,-0.8000,-1.1000,-1.3500,-1.5500,-1.7000,-1.8000,-1.8500,-1.8800,-1.8800,-1.8600,-1.8300,-1.8000,-1.7800],
        [13.3363,14.6000,15.8000,16.1631,16.6000,16.9000,17.2400,16.9800,16.4000,16.1000,15.9116,15.8500,15.8200,15.6000,15.5000,15.3500,15.2300,15.1500,15.1244,15.1800,15.4200,15.8400,16.4400,17.2000,18.0800,18.9800,19.8600,20.6000,21.1500,21.5500,21.8000,22.0000,22.1000],
        [0.09300,0.08800,0.08500,0.08312,0.08200,0.08180,0.08160,0.08100,0.08071,0.08050,0.08037,0.08020,0.08167,0.08200,0.08230,0.08300,0.08400,0.08600,0.08800,0.09300,0.09900,0.10600,0.11200,0.11700,0.12000,0.12100,0.12000,0.11800,0.11600,0.11400,0.11200,0.11000,0.10900],
        228
    )

    a = [45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120]
    refs[("F","peso_estatura")] = _tabela_altura(
        a,
        [-0.3833,-0.3200,-0.2600,-0.2000,-0.1400,-0.0800,-0.0200,0.0400,0.1000,0.1600,0.2200,0.2600,0.2800,0.2600,0.2000,0.1400],
        [2.3600,3.0500,4.2000,5.4000,6.7000,7.9000,9.0000,10.1000,11.3000,12.4000,13.6000,14.9000,16.3000,17.7000,19.3000,21.0000],
        [0.09100,0.09000,0.08950,0.08900,0.08850,0.08800,0.08780,0.08780,0.08800,0.08900,0.09000,0.09100,0.09200,0.09400,0.09600,0.09800]
    )

    return refs


ARQUIVO_DADOS = "criancas_nutrimais.json"


def carregar_criancas():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def salvar_criancas(dados):
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, default=str)


def calcular_idade_meses(data_nasc, data_medicao):
    if isinstance(data_nasc, str):
        data_nasc = datetime.strptime(data_nasc, "%Y-%m-%d").date()
    if isinstance(data_medicao, str):
        data_medicao = datetime.strptime(data_medicao, "%Y-%m-%d").date()
    diff = data_medicao - data_nasc
    return round(diff.days / 30.44, 1)


def obter_limites(ref_data, valor_eixo, tipo_eixo="meses"):
    eixo = ref_data[tipo_eixo]
    lim = {}
    for z in [-3, -2, -1, 0, 1, 2, 3]:
        lim[z] = float(np.interp(valor_eixo, eixo, ref_data[f"z{z}"]))
    return lim


def classificar_nutricional(valor, limites, tipo_indice, idade_meses=0):
    if limites is None:
        return "Sem referencia", "#808080"
    v = float(valor)
    if tipo_indice == "peso_idade":
        if v < limites[-3]:
            return "Muito baixo peso para a idade", "#8B0000"
        elif v < limites[-2]:
            return "Baixo peso para a idade", "#FF4500"
        elif v <= limites[2]:
            return "Peso adequado para a idade", "#2E8B57"
        else:
            return "Peso elevado para a idade", "#FF8C00"
    elif tipo_indice == "estatura_idade":
        if v < limites[-3]:
            return "Muito baixa estatura para a idade", "#8B0000"
        elif v < limites[-2]:
            return "Baixa estatura para a idade", "#FF4500"
        else:
            return "Estatura adequada para a idade", "#2E8B57"
    elif tipo_indice == "imc_idade":
        if idade_meses <= 60:
            if v < limites[-3]:
                return "Magreza acentuada", "#8B0000"
            elif v < limites[-2]:
                return "Magreza", "#FF4500"
            elif v <= limites[1]:
                return "Eutrofia", "#2E8B57"
            elif v <= limites[2]:
                return "Risco de sobrepeso", "#FFD700"
            elif v <= limites[3]:
                return "Sobrepeso", "#FF8C00"
            else:
                return "Obesidade", "#FF0000"
        else:
            if v < limites[-3]:
                return "Magreza acentuada", "#8B0000"
            elif v < limites[-2]:
                return "Magreza", "#FF4500"
            elif v <= limites[1]:
                return "Eutrofia", "#2E8B57"
            elif v <= limites[2]:
                return "Sobrepeso", "#FF8C00"
            elif v <= limites[3]:
                return "Obesidade", "#FF0000"
            else:
                return "Obesidade grave", "#8B0000"
    elif tipo_indice == "peso_estatura":
        if v < limites[-3]:
            return "Magreza acentuada", "#8B0000"
        elif v < limites[-2]:
            return "Magreza", "#FF4500"
        elif v <= limites[1]:
            return "Eutrofia", "#2E8B57"
        elif v <= limites[2]:
            return "Risco de sobrepeso", "#FFD700"
        elif v <= limites[3]:
            return "Sobrepeso", "#FF8C00"
        else:
            return "Obesidade", "#FF0000"
    return "Sem classificacao", "#808080"


def gerar_grafico_curva(ref_data, medicoes_plot, titulo, eixo_x_campo, eixo_y_campo, label_x, label_y, tipo_indice, sexo, idade_meses_list=None):
    fig = go.Figure()
    tipo_eixo = "altura" if eixo_x_campo == "altura" else "meses"
    x_data = ref_data[tipo_eixo]

    z_configs = [
        ("z3", "+3", "#DC143C", "dot", 1),
        ("z2", "+2", "#FF8C00", "dash", 1.2),
        ("z1", "+1", "#4682B4", "dot", 1),
        ("z0", "Mediana", "#2E8B57", "solid", 2),
        ("z-1", "-1", "#4682B4", "dot", 1),
        ("z-2", "-2", "#FF8C00", "dash", 1.2),
        ("z-3", "-3", "#DC143C", "dot", 1),
    ]

    for z_key, z_label, z_cor, z_dash, z_width in z_configs:
        fig.add_trace(go.Scatter(
            x=x_data, y=ref_data[z_key],
            mode="lines", name=z_label,
            line=dict(color=z_cor, width=z_width, dash=z_dash),
            hoverinfo="skip", showlegend=True
        ))

    cores_marcadores = []
    for idx_m, m in enumerate(medicoes_plot):
        vx = m.get(eixo_x_campo, 0)
        vy = m.get(eixo_y_campo, 0)
        if vx <= 0 or vy <= 0:
            continue

        limites = obter_limites(ref_data, vx, tipo_eixo)
        im = idade_meses_list[idx_m] if idade_meses_list else m.get("meses", 0)
        _, cor = classificar_nutricional(vy, limites, tipo_indice, im)
        cores_marcadores.append(cor)

        num_med = idx_m + 1
        fig.add_trace(go.Scatter(
            x=[vx], y=[vy],
            mode="markers+text",
            text=[f"<b>{vy}</b>"],
            textposition="top center",
            marker=dict(size=11, color=cor, line=dict(width=1.5, color="white"), symbol="circle"),
            name=f"Med. {num_med}",
            showlegend=False,
            hovertemplate=f"Medicao {num_med}<br>{label_x}: %{{x:.1f}}<br>{label_y}: %{{y:.1f}}<extra></extra>"
        ))

    if medicoes_plot:
        vx_vals = [m.get(eixo_x_campo, 0) for m in medicoes_plot if m.get(eixo_x_campo, 0) > 0]
        if vx_vals:
            vx_min = min(vx_vals)
            vx_max = max(vx_vals)
            margem = max((vx_max - vx_min) * 0.5, 10)
            x_min = max(0, vx_min - margem)
            x_max = vx_max + margem

            vy_vals = [m.get(eixo_y_campo, 0) for m in medicoes_plot if m.get(eixo_y_campo, 0) > 0]
            all_y = []
            for zk in ["z-3", "z3"]:
                for i, xv in enumerate(x_data):
                    if x_min <= xv <= x_max:
                        all_y.append(ref_data[zk][i])
            all_y.extend(vy_vals)
            if all_y:
                y_min = min(all_y) * 0.92
                y_max = max(all_y) * 1.08
                fig.update_yaxes(range=[y_min, y_max])

            fig.update_xaxes(range=[x_min, x_max])

    cor_titulo = "#1565C0" if sexo == "M" else "#AD1457"
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b>", font=dict(color=cor_titulo, size=15)),
        xaxis_title=label_x,
        yaxis_title=label_y,
        height=420,
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=9)),
        margin=dict(l=50, r=20, t=80, b=50),
    )

    return fig, cores_marcadores


refs = gerar_referencias_oms()

if "criancas" not in st.session_state:
    st.session_state.criancas = carregar_criancas()

st.sidebar.markdown("<h2 style='color:#4A148C;'>\U0001F34E NutriMais</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color:#6A1B9A; font-size:0.85rem;'>Acompanhamento Nutricional<br>Criancas e Adolescentes</p>", unsafe_allow_html=True)
st.sidebar.divider()

with st.sidebar.expander("\u2795 Cadastrar Nova Crianca", expanded=False):
    novo_nome = st.text_input("Nome completo", key="novo_nome")
    novo_sexo = st.selectbox("Sexo", ["Masculino", "Feminino"], key="novo_sexo")
    nova_nasc = st.date_input(
        "Data de Nascimento",
        value=date(2018, 1, 1),
        min_value=date(2005, 1, 1),
        max_value=date.today(),
        key="nova_nasc"
    )
    if st.button("Cadastrar", key="btn_cadastrar"):
        if novo_nome and novo_nome.strip():
            chave = novo_nome.strip()
            if chave in st.session_state.criancas:
                st.warning("Ja existe uma crianca com esse nome!")
            else:
                st.session_state.criancas[chave] = {
                    "nome": chave,
                    "sexo": "M" if novo_sexo == "Masculino" else "F",
                    "data_nascimento": str(nova_nasc),
                    "medicoes": [
                        {"data": "", "peso": 0.0, "altura": 0.0},
                        {"data": "", "peso": 0.0, "altura": 0.0},
                        {"data": "", "peso": 0.0, "altura": 0.0},
                        {"data": "", "peso": 0.0, "altura": 0.0},
                    ]
                }
                salvar_criancas(st.session_state.criancas)
                st.success(f"{chave} cadastrado(a)!")
                st.rerun()
        else:
            st.warning("Digite o nome da crianca.")

nomes = sorted(st.session_state.criancas.keys())

if not nomes:
    st.markdown("<h1 class='header-style'>\U0001F34E NutriMais - Acompanhamento Nutricional</h1>", unsafe_allow_html=True)
    st.info("Cadastre uma crianca na barra lateral para comecar o acompanhamento nutricional.")
    st.stop()

selecionado = st.sidebar.selectbox("Selecionar Crianca", nomes, key="sel_crianca")

if st.sidebar.button("\U0001F5D1 Remover Crianca Selecionada", key="btn_remover"):
    del st.session_state.criancas[selecionado]
    salvar_criancas(st.session_state.criancas)
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown(f"**Criancas cadastradas:** {len(nomes)}")

crianca = st.session_state.criancas[selecionado]
sexo = crianca["sexo"]
data_nasc = datetime.strptime(crianca["data_nascimento"], "%Y-%m-%d").date()

sexo_label = "Masculino" if sexo == "M" else "Feminino"
st.markdown(f"<h1 class='header-style'>\U0001F4CB Ficha: {selecionado}</h1>", unsafe_allow_html=True)
st.markdown(
    f"<div class='info-box'><b>Sexo:</b> {sexo_label} &nbsp;|&nbsp; <b>Data de Nascimento:</b> {data_nasc.strftime('%d/%m/%Y')}</div>",
    unsafe_allow_html=True
)
st.divider()

cols_med = st.columns(4)
medicoes_validas = []
status_por_medicao = []

for i in range(4):
    with cols_med[i]:
        st.markdown(f"**Medicao {i+1}**")

        med_salva = crianca.get("medicoes", [{}, {}, {}, {}])
        if i >= len(med_salva):
            med_salva.append({"data": "", "peso": 0.0, "altura": 0.0})

        data_salva = med_salva[i].get("data", "")
        if data_salva:
            try:
                data_default = datetime.strptime(data_salva, "%Y-%m-%d").date()
            except Exception:
                data_default = date.today()
        else:
            data_default = date.today()

        data_med = st.date_input("Data da afericao", value=data_default, key=f"data_{i}_{selecionado}")
        peso = st.number_input("Peso (kg)", value=float(med_salva[i].get("peso", 0.0)), min_value=0.0, max_value=200.0, step=0.1, format="%.1f", key=f"peso_{i}_{selecionado}")
        altura = st.number_input("Altura (cm)", value=float(med_salva[i].get("altura", 0.0)), min_value=0.0, max_value=250.0, step=0.1, format="%.1f", key=f"alt_{i}_{selecionado}")

        if peso > 0 and altura > 0:
            meses = calcular_idade_meses(data_nasc, data_med)
            imc = round(peso / ((altura / 100) ** 2), 2)
            st.markdown(f"<div class='info-box'>\U0001F4C5 <b>Idade:</b> {meses} meses<br>\U0001F4CA <b>IMC:</b> {imc}</div>", unsafe_allow_html=True)

            ref_imc = refs.get((sexo, "imc_idade"))
            if ref_imc and 0 <= meses <= 228:
                limites_imc = obter_limites(ref_imc, meses, "meses")
                status_text, status_cor = classificar_nutricional(imc, limites_imc, "imc_idade", meses)
            else:
                ref_pe = refs.get((sexo, "peso_estatura"))
                if ref_pe:
                    eixo_alt = ref_pe["altura"]
                    if eixo_alt[0] <= altura <= eixo_alt[-1]:
                        limites_pe = obter_limites(ref_pe, altura, "altura")
                        status_text, status_cor = classificar_nutricional(peso, limites_pe, "peso_estatura")
                    else:
                        status_text, status_cor = "Fora da faixa", "#808080"
                else:
                    status_text, status_cor = "Sem referencia", "#808080"

            st.markdown(f"<div class='status-box' style='background-color:{status_cor}'>{status_text}</div>", unsafe_allow_html=True)

            medicoes_validas.append({
                "meses": meses,
                "peso": peso,
                "altura": altura,
                "imc": imc,
                "data": str(data_med),
                "status": status_text,
                "cor": status_cor
            })
            status_por_medicao.append((i, status_text, status_cor))

while len(crianca.get("medicoes", [])) < 4:
    crianca["medicoes"].append({"data": "", "peso": 0.0, "altura": 0.0})

for i in range(4):
    peso_v = st.session_state.get(f"peso_{i}_{selecionado}", 0.0)
    alt_v = st.session_state.get(f"alt_{i}_{selecionado}", 0.0)
    data_v = st.session_state.get(f"data_{i}_{selecionado}", date.today())
    crianca["medicoes"][i] = {
        "data": str(data_v),
        "peso": float(peso_v),
        "altura": float(alt_v),
    }

st.session_state.criancas[selecionado] = crianca
salvar_criancas(st.session_state.criancas)

if status_por_medicao:
    ultimo = status_por_medicao[-1]
    st.sidebar.markdown(
        f"<div class='status-sidebar' style='background-color:{ultimo[2]};'>STATUS ATUAL<br>{ultimo[1]}</div>",
        unsafe_allow_html=True
    )

if medicoes_validas:
    st.divider()
    st.markdown("<h2 class='header-style'>\U0001F4CA Curvas de Crescimento - OMS</h2>", unsafe_allow_html=True)

    graficos_config = [
        ("peso_idade", "Peso x Idade", "meses", "peso", "Idade (meses)", "Peso (kg)"),
        ("estatura_idade", "Estatura x Idade", "meses", "altura", "Idade (meses)", "Estatura (cm)"),
        ("imc_idade", "IMC x Idade", "meses", "imc", "Idade (meses)", "IMC (kg/m\u00b2)"),
        ("peso_estatura", "Peso x Estatura", "altura", "peso", "Estatura (cm)", "Peso (kg)"),
    ]

    g_row = st.columns(2)

    for idx, (slug, titulo, eixo_x, eixo_y, lbl_x, lbl_y) in enumerate(graficos_config):
        with g_row[idx % 2]:
            ref = refs.get((sexo, slug))
            if ref is None:
                st.warning(f"Referencia OMS nao disponivel para {titulo}")
                continue

            idades = [m["meses"] for m in medicoes_validas]
            fig, cores = gerar_grafico_curva(
                ref, medicoes_validas, titulo,
                eixo_x, eixo_y, lbl_x, lbl_y,
                slug, sexo, idades
            )
            st.plotly_chart(fig, use_container_width=True)

            m_atual = medicoes_validas[-1]
            tipo_eixo = "altura" if eixo_x == "altura" else "meses"
            vx = m_atual.get(eixo_x, 0)
            vy = m_atual.get(eixo_y, 0)

            eixo_ref = ref[tipo_eixo]
            if vx < eixo_ref[0] or vx > eixo_ref[-1]:
                st.markdown(
                    f"<div class='status-box' style='background-color:#808080'>{titulo}: Valor fora da faixa de referencia</div>",
                    unsafe_allow_html=True
                )
            else:
                limites = obter_limites(ref, vx, tipo_eixo)
                st_class, cor_class = classificar_nutricional(vy, limites, slug, m_atual.get("meses", 0))
                st.markdown(
                    f"<div class='status-box' style='background-color:{cor_class}'>{titulo}: {st_class}</div>",
                    unsafe_allow_html=True
                )
else:
    st.info("Preencha pelo menos uma medicao (peso e altura) para visualizar as curvas de crescimento.")
