import streamlit as st
import sqlite3
import hashlib
import math
import os
import json
from datetime import datetime, date

st.set_page_config(
    page_title="NutriMais",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main { background-color: #F3E5F5; }
    .stApp { background-color: #F3E5F5; }
    div[data-testid="stSidebar"] { background-color: #6A1B9A; }
    div[data-testid="stSidebar"] label, div[data-testid="stSidebar"] .stMarkdown p,
    div[data-testid="stSidebar"] .stMarkdown h1, div[data-testid="stSidebar"] .stMarkdown h2,
    div[data-testid="stSidebar"] .stMarkdown h3, div[data-testid="stSidebar"] .stMarkdown h4 {
        color: #CE93D8 !important;
    }
    .nutri-header { background: white; padding: 16px 24px; border-radius: 12px;
        border-bottom: 3px solid #CE93D8; margin-bottom: 20px;
        box-shadow: 0 2px 12px rgba(106,27,154,0.1); }
    .nutri-card { background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 12px rgba(106,27,154,0.1); margin-bottom: 16px; }
    .badge-ok { background: #2E8B57; color: white; padding: 4px 12px; border-radius: 8px;
        font-weight: bold; font-size: 0.85rem; display: inline-block; }
    .badge-warn { background: #FFD700; color: #333; padding: 4px 12px; border-radius: 8px;
        font-weight: bold; font-size: 0.85rem; display: inline-block; }
    .badge-danger { background: #FF0000; color: white; padding: 4px 12px; border-radius: 8px;
        font-weight: bold; font-size: 0.85rem; display: inline-block; }
    .disclaimer { background: #FFF9C4; border: 1px solid #F0C050; border-radius: 10px;
        padding: 14px 18px; font-size: 0.85rem; color: #5D4037; line-height: 1.6;
        border-left: 4px solid #F0C050; margin-top: 16px; }
    .msg-ok { background: #E8F5E9; color: #2E7D32; padding: 10px 16px; border-radius: 8px;
        font-weight: bold; font-size: 0.9rem; margin-bottom: 12px; }
    .msg-err { background: #FFEBEE; color: #C62828; padding: 10px 16px; border-radius: 8px;
        font-weight: bold; font-size: 0.9rem; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

DB_PATH = "nutrimais.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'visitor',
        cpf TEXT UNIQUE,
        group_access TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS grupos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS turmas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        grupo_id INTEGER REFERENCES grupos(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS criancas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        sexo TEXT NOT NULL,
        data_nascimento DATE NOT NULL,
        grupo_id INTEGER REFERENCES grupos(id),
        turma_id INTEGER REFERENCES turmas(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS medicoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crianca_id INTEGER REFERENCES criancas(id),
        data_medicao DATE NOT NULL,
        peso REAL NOT NULL,
        altura REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    admin_hash = hash_password("admin123")
    visitor_hash = hash_password("visitante123")
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
              ("admin", admin_hash, "admin"))
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
              ("visitante", visitor_hash, "visitor"))
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256((password + "nutrimais_salt").encode()).hexdigest()

def lerp_val(arr, x, xi):
    for i in range(len(x) - 1):
        if xi >= x[i] and xi <= x[i + 1]:
            t = (xi - x[i]) / (x[i + 1] - x[i]) if x[i + 1] != x[i] else 0
            return arr[i] + t * (arr[i + 1] - arr[i])
    if xi <= x[0]:
        return arr[0]
    return arr[-1]

def interp_table(eixo, L_arr, M_arr, S_arr):
    z_vals = [-3, -2, -1, 0, 1, 2, 3]
    result = {"_L": L_arr, "_M": M_arr, "_S": S_arr}
    for z in z_vals:
        key = f"z{z}"
        vals = []
        for i in range(len(eixo)):
            L, M, S = L_arr[i], M_arr[i], S_arr[i]
            if abs(L) > 0.001:
                v = M * pow(1 + L * S * z, 1.0 / L)
            else:
                v = M * math.exp(S * z)
            vals.append(round(max(v, 0) * 100) / 100)
        result[key] = vals
    return result

def tab_meses(m_ref, L_ref, M_ref, S_ref, max_mes):
    eixo = list(range(max_mes + 1))
    L = [lerp_val(L_ref, m_ref, x) for x in eixo]
    M = [lerp_val(M_ref, m_ref, x) for x in eixo]
    S = [lerp_val(S_ref, m_ref, x) for x in eixo]
    t = interp_table(eixo, L, M, S)
    t["meses"] = eixo
    return t

def tab_altura(a_ref, L_ref, M_ref, S_ref):
    start = int(a_ref[0])
    end = int(a_ref[-1])
    eixo = list(range(start, end + 1))
    L = [lerp_val(L_ref, a_ref, x) for x in eixo]
    M = [lerp_val(M_ref, a_ref, x) for x in eixo]
    S = [lerp_val(S_ref, a_ref, x) for x in eixo]
    t = interp_table(eixo, L, M, S)
    t["altura"] = eixo
    return t

@st.cache_data
def init_refs():
    REFS = {}
    m24 = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120]
    m228 = [0,1,2,3,4,5,6,9,12,15,18,21,24,30,36,42,48,54,60,72,84,96,108,120,132,144,156,168,180,192,204,216,228]

    REFS["M_peso_idade"] = tab_meses(m24,
        [-0.3521,-0.1600,0.0150,-0.0700,-0.1100,-0.0400,0.2300,0.3300,0.4300,0.4600,0.4800,0.4800,0.4700,0.4100,0.3500,0.2500,0.1500,0.0400,-0.0700,-0.2800,-0.4500,-0.6000,-0.7300,-0.8400],
        [3.3464,4.4709,5.5675,6.3762,7.0023,7.5105,7.9340,8.9014,9.6500,10.3060,10.8500,11.4900,12.1515,13.3000,14.3400,15.3500,16.3290,17.3370,18.3390,20.5060,22.8880,25.6270,28.7590,32.2360],
        [0.14602,0.13395,0.12385,0.11727,0.11316,0.10984,0.10867,0.10700,0.10900,0.11000,0.11100,0.11300,0.11500,0.11600,0.11727,0.11870,0.12000,0.12100,0.12200,0.13000,0.13800,0.14800,0.16000,0.17200], 120)

    REFS["M_estatura_idade"] = tab_meses(m228, [1.0]*len(m228),
        [49.8842,54.7244,58.4249,61.4292,63.8860,65.9026,67.6236,71.8540,75.7488,79.2328,82.2515,84.9413,87.8161,92.8700,96.0980,99.7130,103.3440,106.7150,110.0040,116.0000,121.7000,127.3000,132.6000,138.0000,143.5000,149.5000,156.0000,163.2000,169.0000,173.0000,175.5000,176.5000,176.8000],
        [0.03795,0.03610,0.03480,0.03380,0.03350,0.03310,0.03290,0.03210,0.03100,0.03070,0.03050,0.03045,0.03100,0.03170,0.03230,0.03280,0.03330,0.03380,0.03420,0.03510,0.03600,0.03660,0.03700,0.03750,0.03800,0.03850,0.03800,0.03700,0.03600,0.03500,0.03400,0.03350,0.03300], 228)

    REFS["M_imc_idade"] = tab_meses(m228,
        [-0.3053,-0.2300,-0.1500,-0.0700,0.0500,0.2500,0.5526,0.7200,0.8400,0.9000,0.9600,0.9800,1.0000,0.8600,0.7200,0.5000,0.2800,0.0600,-0.1600,-0.5700,-0.9300,-1.2100,-1.4400,-1.6300,-1.7800,-1.8900,-1.9600,-2.0000,-2.0100,-2.0000,-1.9700,-1.9300,-1.9000],
        [13.4069,14.9500,16.4000,16.7600,17.1000,17.3000,17.4171,17.1776,16.5500,16.1200,15.9965,15.8500,16.0189,15.8000,15.6600,15.4800,15.3200,15.2500,15.2088,15.2900,15.5400,15.9400,16.4700,17.1200,17.8800,18.7300,19.6400,20.5000,21.2300,21.8000,22.2000,22.5000,22.7000],
        [0.09295,0.08800,0.08400,0.08300,0.08200,0.08140,0.08110,0.08015,0.07920,0.07870,0.07825,0.07800,0.07802,0.07810,0.07820,0.07900,0.08000,0.08150,0.08320,0.08700,0.09300,0.09900,0.10500,0.11100,0.11600,0.12000,0.12200,0.12300,0.12200,0.12000,0.11800,0.11600,0.11400], 228)

    a_ref = [45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120]
    REFS["M_peso_estatura"] = tab_altura(a_ref, [-0.3521]*16,
        [2.4410,3.4640,4.7520,6.0990,7.3760,8.5480,9.6180,10.5890,11.4870,12.3520,13.2330,14.1820,15.2600,16.5220,17.9980,19.7260],
        [0.09323,0.09027,0.08606,0.08366,0.08325,0.08428,0.08581,0.08750,0.08887,0.09006,0.09145,0.09357,0.09680,0.10128,0.10682,0.11334])

    REFS["F_peso_idade"] = tab_meses(m24,
        [-0.3833,-0.1800,0.0100,-0.0900,-0.1300,-0.0600,0.1500,0.2500,0.3600,0.4000,0.4200,0.4200,0.4200,0.3600,0.3000,0.2000,0.1000,-0.0100,-0.1200,-0.3500,-0.5500,-0.7000,-0.8200,-0.9000],
        [3.2322,4.1872,5.1282,5.8458,6.4237,6.8985,7.2970,8.2000,8.9500,9.6600,10.2000,10.8700,11.5000,12.6700,13.9000,14.9800,15.9000,16.9000,17.9700,20.2200,22.8200,25.8200,29.2700,33.0000],
        [0.14171,0.13724,0.12922,0.12200,0.11800,0.11500,0.11300,0.11100,0.11200,0.11300,0.11400,0.11500,0.11700,0.11800,0.12000,0.12200,0.12500,0.12800,0.13100,0.14000,0.15000,0.16000,0.17000,0.17800], 120)

    REFS["F_estatura_idade"] = tab_meses(m228, [1.0]*len(m228),
        [49.1477,53.6872,57.0673,59.8029,62.0899,63.9890,65.7311,70.0800,74.0015,77.5000,80.7000,83.6500,86.4000,91.7400,95.1000,99.1000,102.7000,106.2000,109.4000,115.4000,121.3000,127.2000,133.0000,138.6000,145.0000,151.5000,156.8000,160.0000,162.0000,163.0000,163.4000,163.6000,163.7000],
        [0.03790,0.03600,0.03500,0.03400,0.03370,0.03340,0.03310,0.03200,0.03100,0.03080,0.03070,0.03060,0.03100,0.03180,0.03260,0.03310,0.03360,0.03400,0.03450,0.03560,0.03670,0.03740,0.03790,0.03810,0.03800,0.03750,0.03650,0.03530,0.03420,0.03360,0.03320,0.03300,0.03290], 228)

    REFS["F_imc_idade"] = tab_meses(m228,
        [-0.0631,0.1000,0.2500,0.3500,0.5000,0.6500,0.7657,0.8800,0.9529,0.9800,1.0000,0.9900,0.9800,0.8700,0.7500,0.5500,0.3500,0.1500,-0.0500,-0.4500,-0.8000,-1.1000,-1.3500,-1.5500,-1.7000,-1.8000,-1.8500,-1.8800,-1.8800,-1.8600,-1.8300,-1.8000,-1.7800],
        [13.3363,14.6000,15.8000,16.1631,16.6000,16.9000,17.2400,16.9800,16.4000,16.1000,15.9116,15.8500,15.8200,15.6000,15.5000,15.3500,15.2300,15.1500,15.1244,15.1800,15.4200,15.8400,16.4400,17.2000,18.0800,18.9800,19.8600,20.6000,21.1500,21.5500,21.8000,22.0000,22.1000],
        [0.09300,0.08800,0.08500,0.08312,0.08200,0.08180,0.08160,0.08100,0.08071,0.08050,0.08037,0.08020,0.08167,0.08200,0.08230,0.08300,0.08400,0.08600,0.08800,0.09300,0.09900,0.10600,0.11200,0.11700,0.12000,0.12100,0.12000,0.11800,0.11600,0.11400,0.11200,0.11000,0.10900], 228)

    REFS["F_peso_estatura"] = tab_altura(a_ref, [-0.3833]*16,
        [2.4360,3.3950,4.6080,5.8360,7.0230,8.1010,9.0860,10.0190,10.9340,11.8760,12.8860,13.9900,15.2050,16.5540,18.0540,19.7260],
        [0.09445,0.09024,0.08620,0.08375,0.08303,0.08378,0.08502,0.08640,0.08778,0.08926,0.09129,0.09414,0.09779,0.10229,0.10748,0.11325])

    return REFS

def get_ref(sexo, tipo):
    refs = init_refs()
    return refs.get(f"{sexo}_{tipo}")

def calcular_idade_meses(data_nasc, data_medicao):
    if isinstance(data_nasc, str):
        nasc = datetime.strptime(data_nasc, "%Y-%m-%d")
    else:
        nasc = datetime.combine(data_nasc, datetime.min.time())
    if isinstance(data_medicao, str):
        med = datetime.strptime(data_medicao, "%Y-%m-%d")
    else:
        med = datetime.combine(data_medicao, datetime.min.time())
    diff = (med - nasc).days
    meses = round(diff / 30.44 * 10) / 10
    return meses

def obter_limites(ref, valor_eixo, tipo_eixo):
    eixo = ref.get("meses") if tipo_eixo == "meses" else ref.get("altura")
    if not eixo:
        return {}
    result = {}
    for z in [-3, -2, -1, 0, 1, 2, 3]:
        key = f"z{z}"
        z_arr = ref[key]
        val = 0
        for i in range(len(eixo) - 1):
            if valor_eixo >= eixo[i] and valor_eixo <= eixo[i + 1]:
                t = (valor_eixo - eixo[i]) / (eixo[i + 1] - eixo[i]) if eixo[i + 1] != eixo[i] else 0
                val = z_arr[i] + t * (z_arr[i + 1] - z_arr[i])
                break
        if valor_eixo <= eixo[0]:
            val = z_arr[0]
        elif valor_eixo >= eixo[-1]:
            val = z_arr[-1]
        result[z] = val
    return result

def calcular_zscore(ref, eixo_val, tipo_eixo, valor):
    try:
        eixo = ref.get("meses") if tipo_eixo == "meses" else ref.get("altura")
        L = lerp_val(ref["_L"], eixo, eixo_val)
        M = lerp_val(ref["_M"], eixo, eixo_val)
        S = lerp_val(ref["_S"], eixo, eixo_val)
        if M <= 0 or S <= 0:
            return None
        if abs(L) > 0.001:
            z = (pow(valor / M, L) - 1) / (L * S)
        else:
            z = math.log(valor / M) / S
        return round(z * 100) / 100
    except:
        return None

def erf_approx(x):
    t = 1.0 / (1.0 + 0.5 * abs(x))
    tau = t * math.exp(-x * x - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 + t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))))
    return 1 - tau if x >= 0 else tau - 1

def zscore_para_percentil(z):
    if z is None:
        return None
    zc = max(-8, min(8, z))
    p = 0.5 * (1 + erf_approx(zc / math.sqrt(2)))
    return round(p * 1000) / 10

def formatar_percentil(z):
    p = zscore_para_percentil(z)
    if p is None:
        return "-"
    if p < 0.1:
        return "< P0,1"
    if p < 1:
        return "< P1"
    if p > 99.9:
        return "> P99,9"
    if p > 99:
        return "> P99"
    return f"P{round(p)}"

def classificar_nutricional(valor, limites, tipo_indice, idade_meses=0):
    v = valor
    if tipo_indice == "peso_idade":
        if v < limites.get(-3, 0): return ("Muito baixo peso para a idade", "#8B0000")
        if v < limites.get(-2, 0): return ("Baixo peso para a idade", "#FF4500")
        if v <= limites.get(2, 0): return ("Peso adequado para a idade", "#2E8B57")
        return ("Peso elevado para a idade", "#FF8C00")
    if tipo_indice == "estatura_idade":
        if v < limites.get(-3, 0): return ("Muito baixa estatura para a idade", "#8B0000")
        if v < limites.get(-2, 0): return ("Baixa estatura para a idade", "#FF4500")
        return ("Estatura adequada para a idade", "#2E8B57")
    if tipo_indice == "imc_idade":
        if idade_meses <= 60:
            if v < limites.get(-3, 0): return ("Magreza acentuada", "#8B0000")
            if v < limites.get(-2, 0): return ("Magreza", "#FF4500")
            if v <= limites.get(1, 0): return ("Eutrofia", "#2E8B57")
            if v <= limites.get(2, 0): return ("Risco de sobrepeso", "#FFD700")
            if v <= limites.get(3, 0): return ("Sobrepeso", "#FF8C00")
            return ("Obesidade", "#FF0000")
        else:
            if v < limites.get(-3, 0): return ("Magreza acentuada", "#8B0000")
            if v < limites.get(-2, 0): return ("Magreza", "#FF4500")
            if v <= limites.get(1, 0): return ("Eutrofia", "#2E8B57")
            if v <= limites.get(2, 0): return ("Sobrepeso", "#FF8C00")
            if v <= limites.get(3, 0): return ("Obesidade", "#FF0000")
            return ("Obesidade grave", "#8B0000")
    if tipo_indice == "peso_estatura":
        if v < limites.get(-3, 0): return ("Magreza acentuada", "#8B0000")
        if v < limites.get(-2, 0): return ("Magreza", "#FF4500")
        if v <= limites.get(2, 0): return ("Eutrofia", "#2E8B57")
        if v <= limites.get(3, 0): return ("Sobrepeso", "#FF8C00")
        return ("Obesidade", "#FF0000")
    return ("Sem classificacao", "#808080")

def format_date_br(d):
    if not d:
        return "-"
    try:
        if isinstance(d, str):
            parts = d.split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        elif isinstance(d, date):
            return d.strftime("%d/%m/%Y")
    except:
        pass
    return str(d)

def can_write(user, grupo_nome=None):
    if not user:
        return False
    if user["role"] == "admin":
        return True
    if user["role"] == "group_admin" and grupo_nome and user.get("group_access") == grupo_nome:
        return True
    return False

init_db()

if "user" not in st.session_state:
    st.session_state.user = None

def login_page():
    st.markdown("<div style='text-align:center; font-size:2.2rem; letter-spacing:6px; margin-top:30px;'>🍎 🥕 🥦 🍓 🍌 🍇 🥥 🥑</div>", unsafe_allow_html=True)
    st.markdown("<h1 style='color:#4A148C; text-align:center; font-size:2.4rem; font-weight:900;'>🍎 NutriMais</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#7B1FA2; text-align:center; font-size:1.05rem; margin-bottom:28px;'>Acompanhamento Nutricional de Criancas e Adolescentes</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<h2 style='color:#4A148C; text-align:center;'>Entrar no sistema</h2>", unsafe_allow_html=True)
            username = st.text_input("Usuario")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar", use_container_width=True)

            if submitted:
                if username and password:
                    conn = get_db()
                    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
                    conn.close()
                    if user and user["password_hash"] == hash_password(password):
                        st.session_state.user = {
                            "id": user["id"],
                            "username": user["username"],
                            "role": user["role"],
                            "cpf": user["cpf"],
                            "group_access": user["group_access"],
                        }
                        st.rerun()
                    else:
                        st.error("Credenciais invalidas")
                else:
                    st.error("Preencha usuario e senha")

        st.info("""
        **Acesso padrao:**
        - Visitante: `visitante` / `visitante123`
        - Administrador: `admin` / `admin123`
        """)

    st.markdown("<div style='text-align:center; font-size:2.2rem; letter-spacing:6px; margin-top:20px;'>🌽 🍅 🍆 🥒 🥬 🧅 🍐 🍊</div>", unsafe_allow_html=True)

def admin_panel():
    st.markdown("## ⚙️ Gerenciamento de Usuarios")

    conn = get_db()
    users = conn.execute("SELECT id, username, role, cpf, group_access FROM users").fetchall()
    grupos = conn.execute("SELECT id, nome FROM grupos").fetchall()
    conn.close()

    with st.expander("➕ Criar Novo Usuario", expanded=True):
        with st.form("create_user_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_username = st.text_input("Usuario *")
            with c2:
                new_password = st.text_input("Senha *", type="password")
            with c3:
                new_role = st.selectbox("Perfil", ["visitor", "group_admin", "admin"],
                                        format_func=lambda x: {"visitor": "Visitante", "group_admin": "Admin de Grupo", "admin": "Administrador Geral"}[x])

            c4, c5 = st.columns(2)
            with c4:
                new_cpf = st.text_input("CPF (opcional)")
            with c5:
                grupo_names = [""] + [g["nome"] for g in grupos]
                new_group = st.selectbox("Grupo (para Admin de Grupo)", grupo_names)

            if st.form_submit_button("Criar Usuario", use_container_width=True):
                if new_username and new_password:
                    conn = get_db()
                    try:
                        conn.execute(
                            "INSERT INTO users (username, password_hash, role, cpf, group_access) VALUES (?, ?, ?, ?, ?)",
                            (new_username, hash_password(new_password), new_role,
                             new_cpf if new_cpf else None,
                             new_group if new_role == "group_admin" and new_group else None))
                        conn.commit()
                        st.success(f'Usuario "{new_username}" criado!')
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Usuario ja existe!")
                    finally:
                        conn.close()
                else:
                    st.error("Usuario e senha sao obrigatorios")

    st.markdown("### 👥 Usuarios Cadastrados")
    for u in users:
        role_map = {"admin": "👑 Administrador Geral", "group_admin": "🔧 Admin de Grupo", "visitor": "👁 Visitante"}
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{u['username']}**")
            info_parts = []
            if u["cpf"]:
                info_parts.append(f"CPF: {u['cpf']}")
            if u["group_access"]:
                info_parts.append(f"Grupo: {u['group_access']}")
            if info_parts:
                st.caption(" | ".join(info_parts))
        with col2:
            st.markdown(f"`{role_map.get(u['role'], u['role'])}`")
        with col3:
            if u["username"] != "admin":
                if st.button("🗑 Remover", key=f"del_user_{u['id']}"):
                    conn = get_db()
                    conn.execute("DELETE FROM users WHERE id = ?", (u["id"],))
                    conn.commit()
                    conn.close()
                    st.rerun()
        st.divider()

    st.info("""
    **📖 Niveis de acesso:**
    - **Visitante:** Pode apenas visualizar dados, sem fazer alteracoes.
    - **Admin de Grupo:** Pode administrar um grupo especifico.
    - **Administrador Geral:** Acesso total ao sistema.
    """)

def render_growth_chart(sexo, tipo, medicoes_data, titulo, eixo_x_campo, eixo_y_campo, label_x, label_y):
    try:
        import plotly.graph_objects as go
    except ImportError:
        st.warning("Plotly nao instalado. Execute: pip install plotly")
        return

    ref = get_ref(sexo, tipo)
    if not ref:
        st.warning(f"Referencia OMS nao disponivel para {titulo}")
        return

    pontos = []
    for m in medicoes_data:
        vx = m["altura"] if eixo_x_campo == "altura" else m["meses"]
        vy = m["peso"] if eixo_y_campo == "peso" else (m["altura"] if eixo_y_campo == "altura" else m["imc"])
        if vx and vy and vx > 0 and vy > 0:
            pontos.append({"vx": vx, "vy": vy, "data": m.get("data", "")})

    if not pontos:
        return

    vx_vals = [p["vx"] for p in pontos]
    vx_min = min(vx_vals)
    vx_max = max(vx_vals)
    margem = max((vx_max - vx_min) * 0.5, 10)
    x_min = max(0, vx_min - margem)
    x_max = vx_max + margem

    eixo = ref.get("meses") if eixo_x_campo != "altura" else ref.get("altura")
    if not eixo:
        return

    filtered_eixo = [x for x in eixo if x >= x_min and x <= x_max]
    if not filtered_eixo:
        return

    z_keys = ["z-3", "z-2", "z-1", "z0", "z1", "z2", "z3"]
    z_colors = {"z3": "#DC143C", "z2": "#FF8C00", "z1": "#4682B4", "z0": "#2E8B57",
                "z-1": "#4682B4", "z-2": "#FF8C00", "z-3": "#DC143C"}
    z_labels = {"z3": "+3", "z2": "+2", "z1": "+1", "z0": "Mediana", "z-1": "-1", "z-2": "-2", "z-3": "-3"}
    z_dash = {"z3": "dot", "z2": "dash", "z1": "dash", "z0": "solid", "z-1": "dash", "z-2": "dash", "z-3": "dot"}

    fig = go.Figure()

    for zk in z_keys:
        z_arr = ref[zk]
        y_vals = []
        for x in filtered_eixo:
            idx = eixo.index(x) if x in eixo else -1
            if idx >= 0:
                y_vals.append(z_arr[idx])
            else:
                y_vals.append(None)
        fig.add_trace(go.Scatter(
            x=filtered_eixo, y=y_vals, mode="lines",
            name=z_labels[zk],
            line=dict(color=z_colors[zk], width=2 if zk == "z0" else 1, dash=z_dash[zk]),
        ))

    fig.add_trace(go.Scatter(
        x=[p["vx"] for p in pontos],
        y=[p["vy"] for p in pontos],
        mode="markers+lines",
        name="Medicoes",
        marker=dict(size=10, color="#7B1FA2", symbol="circle"),
        line=dict(color="#7B1FA2", width=2),
        text=[f"Data: {format_date_br(p['data'])}" for p in pontos],
    ))

    fig.update_layout(
        title=dict(text=titulo, font=dict(color="#1565C0" if sexo == "M" else "#AD1457", size=16)),
        xaxis_title=label_x,
        yaxis_title=label_y,
        height=420,
        template="plotly_white",
        legend=dict(font=dict(size=10)),
        margin=dict(l=60, r=20, t=50, b=60),
    )

    st.plotly_chart(fig, use_container_width=True)

    tipo_eixo = "altura" if eixo_x_campo == "altura" else "meses"
    for i, p in enumerate(pontos):
        limites = obter_limites(ref, p["vx"], tipo_eixo)
        meses_val = p["vx"] if eixo_x_campo != "altura" else 0
        status, cor = classificar_nutricional(p["vy"], limites, tipo, meses_val)
        cor_txt = "#333" if cor == "#FFD700" else "white"
        st.markdown(
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{cor};margin-right:6px;"></span>'
            f'<span style="font-size:0.85rem;color:#555;">Medicao {i+1} ({p["vx"]:.1f} {"cm" if eixo_x_campo == "altura" else "meses"}, {p["vy"]:.1f}):</span> '
            f'<span style="background:{cor};color:{cor_txt};padding:3px 10px;border-radius:6px;font-weight:bold;font-size:0.82rem;">{status}</span>',
            unsafe_allow_html=True
        )

def main_app():
    user = st.session_state.user
    conn = get_db()

    with st.sidebar:
        st.markdown(f"### 🍎 NutriMais")
        role_labels = {"admin": "👑 Admin", "group_admin": "🔧 Admin Grupo", "visitor": "👁 Visitante"}
        st.markdown(f"**{role_labels.get(user['role'], user['role'])}** | {user['username']}")

        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.user = None
            st.rerun()

        st.divider()

        pagina = st.radio("Navegacao", ["📋 Sistema", "📊 Controle Coletivo"] + (["⚙️ Usuarios"] if user["role"] == "admin" else []),
                          label_visibility="collapsed")

        if pagina == "⚙️ Usuarios":
            conn.close()
            admin_panel()
            return

        st.divider()

        grupos = conn.execute("SELECT id, nome FROM grupos").fetchall()

        if can_write(user):
            st.markdown("##### 📂 Cadastrar Grupo")
            novo_grupo = st.text_input("Nome do grupo", key="novo_grupo", label_visibility="collapsed", placeholder="Nome do grupo")
            if st.button("Criar Grupo", use_container_width=True, key="btn_criar_grupo"):
                if novo_grupo and novo_grupo.strip():
                    try:
                        conn.execute("INSERT INTO grupos (nome) VALUES (?)", (novo_grupo.strip(),))
                        conn.commit()
                        st.success(f'Grupo "{novo_grupo.strip()}" criado!')
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Grupo ja existe!")

        st.markdown("##### 📂 Grupo")
        grupo_names = ["-- Selecione --"] + [g["nome"] for g in grupos]
        grupo_sel_name = st.selectbox("Grupo", grupo_names, label_visibility="collapsed", key="sel_grupo")
        grupo_sel = None
        if grupo_sel_name != "-- Selecione --":
            grupo_sel = next((dict(g) for g in grupos if g["nome"] == grupo_sel_name), None)

        turma_sel = None
        criancas = []
        if grupo_sel:
            turmas = conn.execute("SELECT id, nome, grupo_id FROM turmas WHERE grupo_id = ?", (grupo_sel["id"],)).fetchall()

            if can_write(user, grupo_sel["nome"]):
                st.markdown("##### ➕ Cadastrar Turma")
                nova_turma = st.text_input("Nome da turma", key="nova_turma", label_visibility="collapsed", placeholder="Nome da turma")
                if st.button("Criar Turma", use_container_width=True, key="btn_criar_turma"):
                    if nova_turma and nova_turma.strip():
                        conn.execute("INSERT INTO turmas (nome, grupo_id) VALUES (?, ?)", (nova_turma.strip(), grupo_sel["id"]))
                        conn.commit()
                        st.success(f'Turma "{nova_turma.strip()}" criada!')
                        st.rerun()

            st.markdown("##### 📋 Turma")
            turma_names = ["-- Selecione --"] + [t["nome"] for t in turmas]
            turma_sel_name = st.selectbox("Turma", turma_names, label_visibility="collapsed", key="sel_turma")
            if turma_sel_name != "-- Selecione --":
                turma_sel = next((dict(t) for t in turmas if t["nome"] == turma_sel_name), None)

        if grupo_sel and turma_sel:
            criancas_raw = conn.execute(
                "SELECT id, nome, sexo, data_nascimento, grupo_id, turma_id FROM criancas WHERE turma_id = ?",
                (turma_sel["id"],)
            ).fetchall()
            criancas = [dict(c) for c in criancas_raw]

            if can_write(user, grupo_sel["nome"]):
                st.markdown("##### ➕ Cadastrar Crianca")
                novo_nome = st.text_input("Nome completo", key="novo_nome_crianca", label_visibility="collapsed", placeholder="Nome completo")
                novo_sexo = st.selectbox("Sexo", ["Masculino", "Feminino"], key="novo_sexo_crianca")
                nova_nasc = st.date_input("Data de nascimento", value=date(2018, 1, 1), key="nova_nasc_crianca")
                if st.button("Cadastrar Crianca", use_container_width=True, key="btn_criar_crianca"):
                    if novo_nome and novo_nome.strip():
                        sexo_val = "M" if novo_sexo == "Masculino" else "F"
                        conn.execute(
                            "INSERT INTO criancas (nome, sexo, data_nascimento, grupo_id, turma_id) VALUES (?, ?, ?, ?, ?)",
                            (novo_nome.strip(), sexo_val, str(nova_nasc), grupo_sel["id"], turma_sel["id"]))
                        conn.commit()
                        st.success(f'{novo_nome.strip()} cadastrado(a)!')
                        st.rerun()

    if pagina == "⚙️ Usuarios":
        conn.close()
        return

    header_parts = ["🍎 NutriMais"]
    if grupo_sel and turma_sel:
        header_parts.append(f" | {grupo_sel['nome']} — {turma_sel['nome']}")
    st.markdown(f"<div class='nutri-header'><h2 style='color:#4A148C; margin:0;'>{''.join(header_parts)}</h2></div>", unsafe_allow_html=True)

    if not grupo_sel:
        st.markdown("""
        <div style='text-align:center; padding:60px 20px; color:#7B1FA2;'>
            <div style='font-size:3rem; margin-bottom:16px;'>📂</div>
            <h2 style='color:#4A148C;'>Selecione um Grupo</h2>
            <p>Use o menu lateral para selecionar ou criar um grupo.</p>
        </div>
        """, unsafe_allow_html=True)
        conn.close()
        return

    if not turma_sel:
        st.markdown(f"""
        <div style='text-align:center; padding:60px 20px; color:#7B1FA2;'>
            <div style='font-size:3rem; margin-bottom:16px;'>📋</div>
            <h2 style='color:#4A148C;'>Selecione uma Turma</h2>
            <p>Use o menu lateral para selecionar ou criar uma turma em <strong>{grupo_sel['nome']}</strong>.</p>
        </div>
        """, unsafe_allow_html=True)
        conn.close()
        return

    for c in criancas:
        meds = conn.execute(
            "SELECT id, crianca_id, data_medicao, peso, altura FROM medicoes WHERE crianca_id = ?",
            (c["id"],)
        ).fetchall()
        c["medicoes"] = [dict(m) for m in meds]

    if pagina == "📊 Controle Coletivo":
        st.markdown(f"## 📋 Controle Coletivo — {turma_sel['nome']}")
        st.markdown(f"**Grupo:** {grupo_sel['nome']} | **Turma:** {turma_sel['nome']} | **Total:** {len(criancas)} criancas")

        legend_items = [
            ("#2E8B57", "Eutrofia / Adequado", "white"),
            ("#FFD700", "Risco de Sobrepeso", "#333"),
            ("#FF8C00", "Sobrepeso", "white"),
            ("#FF0000", "Obesidade", "white"),
            ("#FF4500", "Baixo Peso / Magreza", "white"),
            ("#8B0000", "Muito Baixo / Magreza Acentuada", "white"),
            ("#808080", "Sem Medicao", "white"),
        ]
        legend_html = " ".join([
            f'<span style="background:{cor};color:{txt};padding:3px 10px;border-radius:5px;font-size:0.78rem;margin-right:4px;">{label}</span>'
            for cor, label, txt in legend_items
        ])
        st.markdown(legend_html, unsafe_allow_html=True)

        if criancas:
            table_html = """
            <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;box-shadow:0 2px 12px rgba(106,27,154,0.15);border-radius:10px;overflow:hidden;font-size:0.88rem;">
            <thead><tr style="background:#6A1B9A;color:white;">
                <th style="padding:10px 8px;text-align:left;">Nome</th>
                <th style="padding:10px 8px;text-align:center;">Sexo</th>
                <th style="padding:10px 8px;text-align:center;">Nascimento</th>
                <th style="padding:10px 8px;text-align:center;">Idade Atual</th>
                <th style="padding:10px 8px;text-align:center;">Ultima Afericao</th>
                <th style="padding:10px 8px;text-align:center;">Peso (kg)</th>
                <th style="padding:10px 8px;text-align:center;">Altura (cm)</th>
                <th style="padding:10px 8px;text-align:center;">IMC</th>
                <th style="padding:10px 8px;text-align:center;">Diagnostico Nutricional</th>
            </tr></thead><tbody>
            """
            for i, c in enumerate(criancas):
                bg = "#FAF0FF" if i % 2 == 0 else "white"
                meds = c["medicoes"]
                ultima = None
                for m in reversed(meds):
                    if m["peso"] > 0 and m["altura"] > 0:
                        ultima = m
                        break

                idade_meses = round(calcular_idade_meses(c["data_nascimento"], str(date.today())))

                if ultima:
                    imc = ultima["peso"] / pow(ultima["altura"] / 100, 2)
                    meses_med = calcular_idade_meses(c["data_nascimento"], ultima["data_medicao"])
                    ref = get_ref(c["sexo"], "imc_idade")
                    if ref and meses_med <= 228:
                        lim = obter_limites(ref, meses_med, "meses")
                        status, cor = classificar_nutricional(imc, lim, "imc_idade", meses_med)
                    else:
                        status, cor = "Fora da faixa", "#808080"
                else:
                    status, cor = "Sem medicao", "#808080"
                    imc = 0

                cor_txt = "#333" if cor == "#FFD700" else "white"
                table_html += f"""
                <tr style="background:{bg};border-bottom:1px solid #E1BEE7;">
                    <td style="padding:9px 12px;font-weight:600;color:#4A148C;">{c['nome']}</td>
                    <td style="padding:9px 8px;text-align:center;">{c['sexo']}</td>
                    <td style="padding:9px 8px;text-align:center;">{format_date_br(c['data_nascimento'])}</td>
                    <td style="padding:9px 8px;text-align:center;">{idade_meses} meses</td>
                    <td style="padding:9px 8px;text-align:center;">{format_date_br(ultima['data_medicao']) if ultima else '-'}</td>
                    <td style="padding:9px 8px;text-align:center;">{ultima['peso']:.1f if ultima else '-'}</td>
                    <td style="padding:9px 8px;text-align:center;">{ultima['altura']:.1f if ultima else '-'}</td>
                    <td style="padding:9px 8px;text-align:center;">{imc:.1f if ultima else '-'}</td>
                    <td style="padding:9px 14px;text-align:center;">
                        <span style="background:{cor};color:{cor_txt};padding:5px 10px;border-radius:7px;font-weight:bold;font-size:0.8rem;display:inline-block;min-width:160px;">
                            {status}
                        </span>
                    </td>
                </tr>
                """
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)

        st.markdown("""
        <div class="disclaimer">
            <strong>⚠️ Importante:</strong> As classificacoes feitas pelo aplicativo utilizam somente dados antropometricos
            (Peso, Estatura e IMC), nao levando em consideracao outros parametros que sao necessarios para um diagnostico
            nutricional completo, como exames bioquimicos, avaliacao dos habitos alimentares e exames clinicos. Por isso,
            estes resultados nao substituem o diagnostico individualizado feito por um profissional capacitado e habilitado.
            Essas informacoes sao para fins de conhecimento e rastreamento do perfil nutricional da instituicao.
        </div>
        """, unsafe_allow_html=True)

    else:
        if not criancas:
            st.markdown("""
            <div style='text-align:center; padding:60px 20px; color:#7B1FA2;'>
                <div style='font-size:3rem; margin-bottom:16px;'>👶</div>
                <h2 style='color:#4A148C;'>Nenhuma crianca cadastrada</h2>
                <p>Use o menu lateral para cadastrar criancas nesta turma.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            crianca_names = [c["nome"] for c in criancas]
            sel_crianca_nome = st.selectbox("👶 Selecione a crianca:", crianca_names)
            crianca_sel = next((c for c in criancas if c["nome"] == sel_crianca_nome), None)

            if crianca_sel:
                write_enabled = can_write(user, grupo_sel["nome"])

                if write_enabled:
                    col_del = st.columns([4, 1])
                    with col_del[1]:
                        if st.button("🗑 Remover Crianca", key="btn_remover_crianca"):
                            conn2 = get_db()
                            conn2.execute("DELETE FROM medicoes WHERE crianca_id = ?", (crianca_sel["id"],))
                            conn2.execute("DELETE FROM criancas WHERE id = ?", (crianca_sel["id"],))
                            conn2.commit()
                            conn2.close()
                            st.rerun()

                st.markdown(f"## 📋 Ficha: {crianca_sel['nome']}")
                sexo_label = "Masculino" if crianca_sel["sexo"] == "M" else "Feminino"
                st.markdown(
                    f"**Sexo:** {sexo_label} | **Data de Nascimento:** {format_date_br(crianca_sel['data_nascimento'])} | "
                    f"**Grupo:** {grupo_sel['nome']} | **Turma:** {turma_sel['nome']}"
                )

                st.markdown("### 📅 Medicoes")

                meds = crianca_sel["medicoes"]
                num_slots = max(4, len(meds))

                med_cols = st.columns(min(num_slots, 4))
                updated_meds = []

                for i in range(min(num_slots, 4)):
                    with med_cols[i]:
                        st.markdown(f"**Medicao {i + 1}**")
                        existing = meds[i] if i < len(meds) else None

                        if existing:
                            try:
                                default_date = datetime.strptime(existing["data_medicao"], "%Y-%m-%d").date()
                            except:
                                default_date = date.today()
                            default_peso = float(existing["peso"])
                            default_altura = float(existing["altura"])
                            med_id = existing["id"]
                        else:
                            default_date = date.today()
                            default_peso = 0.0
                            default_altura = 0.0
                            med_id = None

                        data_med = st.date_input("Data", value=default_date, key=f"med_data_{i}", disabled=not write_enabled)
                        peso = st.number_input("Peso (kg)", value=default_peso, min_value=0.0, max_value=200.0, step=0.1, key=f"med_peso_{i}", disabled=not write_enabled)
                        altura = st.number_input("Altura (cm)", value=default_altura, min_value=0.0, max_value=250.0, step=0.1, key=f"med_alt_{i}", disabled=not write_enabled)

                        updated_meds.append({
                            "id": med_id,
                            "data_medicao": str(data_med),
                            "peso": peso,
                            "altura": altura,
                        })

                        if peso > 0 and altura > 0:
                            meses = calcular_idade_meses(crianca_sel["data_nascimento"], str(data_med))
                            imc = round(peso / pow(altura / 100, 2) * 100) / 100

                            sexo = crianca_sel["sexo"]
                            ref = get_ref(sexo, "imc_idade")
                            if ref and meses >= 0 and meses <= 228:
                                lim = obter_limites(ref, meses, "meses")
                                status, cor = classificar_nutricional(imc, lim, "imc_idade", meses)
                                z_val = calcular_zscore(ref, meses, "meses", imc)
                            else:
                                status, cor = "Fora da faixa", "#808080"
                                z_val = None

                            st.markdown(f"📅 **Idade:** {meses:.1f} meses | 📊 **IMC:** {imc:.2f}")

                            cor_txt = "#333" if cor == "#FFD700" else "white"
                            st.markdown(
                                f'<div style="background:{cor};color:{cor_txt};padding:6px 10px;border-radius:6px;font-weight:bold;font-size:0.82rem;text-align:center;">{status}</div>',
                                unsafe_allow_html=True
                            )

                            if z_val is not None:
                                st.caption(f"Escore-Z: {'+' if z_val >= 0 else ''}{z_val:.2f} DP | Percentil: {formatar_percentil(z_val)}")

                if write_enabled:
                    if st.button("💾 Salvar Medicoes", use_container_width=True, type="primary"):
                        conn2 = get_db()
                        for med in updated_meds:
                            if med["peso"] > 0 and med["altura"] > 0 and med["data_medicao"]:
                                if med["id"]:
                                    conn2.execute(
                                        "UPDATE medicoes SET data_medicao = ?, peso = ?, altura = ? WHERE id = ?",
                                        (med["data_medicao"], med["peso"], med["altura"], med["id"]))
                                else:
                                    conn2.execute(
                                        "INSERT INTO medicoes (crianca_id, data_medicao, peso, altura) VALUES (?, ?, ?, ?)",
                                        (crianca_sel["id"], med["data_medicao"], med["peso"], med["altura"]))
                        conn2.commit()
                        conn2.close()
                        st.success("Medicoes salvas com sucesso!")
                        st.rerun()

                valid_meds = []
                all_meds = conn.execute(
                    "SELECT data_medicao, peso, altura FROM medicoes WHERE crianca_id = ? AND peso > 0 AND altura > 0",
                    (crianca_sel["id"],)
                ).fetchall()
                for m in all_meds:
                    meses = calcular_idade_meses(crianca_sel["data_nascimento"], m["data_medicao"])
                    imc = round(m["peso"] / pow(m["altura"] / 100, 2) * 100) / 100
                    valid_meds.append({
                        "meses": meses,
                        "peso": m["peso"],
                        "altura": m["altura"],
                        "imc": imc,
                        "data": m["data_medicao"],
                    })

                if valid_meds and crianca_sel["sexo"]:
                    st.markdown("### 📊 Curvas de Crescimento OMS")

                    graficos = [
                        {"tipo": "peso_idade", "titulo": "Peso x Idade", "eixo_x": "meses", "eixo_y": "peso", "label_x": "Idade (meses)", "label_y": "Peso (kg)"},
                        {"tipo": "estatura_idade", "titulo": "Estatura x Idade", "eixo_x": "meses", "eixo_y": "altura", "label_x": "Idade (meses)", "label_y": "Estatura (cm)"},
                        {"tipo": "imc_idade", "titulo": "IMC x Idade", "eixo_x": "meses", "eixo_y": "imc", "label_x": "Idade (meses)", "label_y": "IMC (kg/m2)"},
                        {"tipo": "peso_estatura", "titulo": "Peso x Estatura", "eixo_x": "altura", "eixo_y": "peso", "label_x": "Estatura (cm)", "label_y": "Peso (kg)"},
                    ]

                    chart_cols = st.columns(2)
                    for idx, g in enumerate(graficos):
                        ref_check = get_ref(crianca_sel["sexo"], g["tipo"])
                        valid_for_chart = [m for m in valid_meds if (m["altura"] if g["eixo_x"] == "altura" else m["meses"]) > 0]
                        if ref_check and valid_for_chart:
                            with chart_cols[idx % 2]:
                                render_growth_chart(
                                    crianca_sel["sexo"], g["tipo"], valid_meds,
                                    g["titulo"], g["eixo_x"], g["eixo_y"],
                                    g["label_x"], g["label_y"]
                                )

                    st.markdown("""
                    <div class="disclaimer">
                        <strong>⚠️ Importante:</strong> As classificacoes feitas pelo aplicativo utilizam somente dados antropometricos
                        (Peso, Estatura e IMC), nao levando em consideracao outros parametros que sao necessarios para um diagnostico
                        nutricional completo, como exames bioquimicos, avaliacao dos habitos alimentares e exames clinicos. Por isso,
                        estes resultados nao substituem o diagnostico individualizado feito por um profissional capacitado e habilitado.
                        Essas informacoes sao para fins de conhecimento e rastreamento do perfil nutricional da instituicao.
                    </div>
                    """, unsafe_allow_html=True)

    conn.close()

def home_page():
    user = st.session_state.user

    st.markdown("<div style='text-align:center; font-size:2.2rem; letter-spacing:6px;'>🍎 🥕 🥦 🍓 🍌 🍇 🥥 🥑</div>", unsafe_allow_html=True)
    st.markdown("<h1 style='color:#4A148C; text-align:center; font-size:2.4rem; font-weight:900;'>🍎 NutriMais</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#7B1FA2; text-align:center; font-size:1.05rem;'>Acompanhamento Nutricional de Criancas e Adolescentes</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        role_labels = {"admin": "👑 Administrador", "group_admin": "🔧 Administrador de Grupo", "visitor": "👁 Visitante"}
        st.markdown(f"<div style='text-align:center;'><span style='background:#7B1FA2;color:white;padding:6px 14px;border-radius:20px;font-size:0.85rem;font-weight:bold;'>{role_labels.get(user['role'], user['role'])} | {user['username']}</span></div>", unsafe_allow_html=True)

        st.markdown("")
        st.markdown("### Bem-vinda ao NutriMais!")
        st.markdown("Sistema completo de avaliacao e acompanhamento nutricional com curvas de crescimento da OMS e Ministerio da Saude.")

        st.info("📂 **Passo 1:** Crie um **Grupo** (ex: escola, clinica, UBS)")
        st.info("📋 **Passo 2:** Adicione **Turmas** dentro do grupo")
        st.info("👶 **Passo 3:** Cadastre as **Criancas** na turma")
        st.info("📊 **Passo 4:** Registre as **Medicoes** e acompanhe pelas curvas da OMS")

        if st.button("Acessar o Sistema →", use_container_width=True, type="primary"):
            st.session_state.screen = "app"
            st.rerun()

        c1, c2 = st.columns(2)
        with c2:
            if st.button("🚪 Sair"):
                st.session_state.user = None
                st.rerun()

    st.markdown("<div style='text-align:center; font-size:2.2rem; letter-spacing:6px; margin-top:18px;'>🌽 🍅 🍆 🥒 🥬 🧅 🍐 🍊</div>", unsafe_allow_html=True)

if "screen" not in st.session_state:
    st.session_state.screen = "home"

if st.session_state.user is None:
    login_page()
elif st.session_state.screen == "home":
    home_page()
else:
    main_app()
