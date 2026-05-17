import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import hashlib
import math
import os
import json
import base64
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from urllib.parse import quote
from datetime import datetime, date

st.set_page_config(
    page_title="NutriMais",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* 1. IMPORTAÇÃO DA FONTE NUNITO */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700;800;900&display=swap');

    /* 2. APLICAÇÃO GLOBAL (Não altera funcionalidades) */
    html, body, [class*="st-"], .main, button, input, select, textarea {
        font-family: 'Nunito', sans-serif !important;
    }

    /* SEU CÓDIGO ORIGINAL ABAIXO (SEM ALTERAÇÕES) */
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
    .imla-header { background: white; padding: 14px 24px 16px 24px; border-radius: 12px;
        border-bottom: 3px solid #CE93D8; margin-bottom: 14px;
        box-shadow: 0 2px 12px rgba(106,27,154,0.1); text-align: center; }
    .imla-logo-space { height: 58px; margin: 0 auto 4px auto; display: flex; align-items: center; justify-content: center; }
    .imla-title { font-size: 2rem; font-weight: 900; letter-spacing: 1px; line-height: 1.2; margin: 0; }
    .imla-title-green { color: #a8cf45; }
    .imla-title-blue { color: #5cc6d0; }
    .imla-turma-buttons { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; margin: 0 0 20px 0; }
    .imla-turma-button { color: white !important; text-decoration: none !important; padding: 10px 16px;
        border-radius: 999px; font-weight: 800; font-size: 0.9rem; box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        display: inline-block; transition: transform 0.15s ease, box-shadow 0.15s ease; }
    .imla-turma-button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.18); }
    .marina-logo img { mix-blend-mode: multiply; }
</style>
""", unsafe_allow_html=True)

DB_PATH = "nutrimais.db"
IMLA_GROUP_NAME = "Instituto Mãe Lalu"
IMLA_LOGO_PATHS = ["imla_logo.png", "logo_imla.png", "instituto_mae_lalu.png", "logo_instituto_mae_lalu.png"]

IMLA_TURMA_COLORS = {
    "Turma Rosa": "#ff81ba",
    "Turma Amarela": "#ffc713",
    "Turma Laranja": "#ffa500",
    "Turma Verde": "#a8cf45",
    "Turma Azul": "#5cc6d0",
    "Turma Cirandando pelo Mundo": "#6741d9",
}
TURMAS_POR_GRUPO = {
    "OMC": [
        "Maternalzinho", "Maternal I", "Maternal II A", 
        "Maternal II B", "Jardim I A", "Jardim I B", "Jardim II"
    ],
    "Instituto Mãe Lalu": [
        "Turma Rosa", "Turma Amarela", "Turma Verde", 
        "Turma Azul", "Turma Laranja"
    ]
}

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_gsheets_client():
    """Retorna um client gspread autenticado via secrets do Streamlit."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # st.secrets retorna AttrDict; convertemos para dict Python nativo campo a campo
    s = st.secrets["connections"]["gsheets"]
    creds_info = {
        "type":                        s["type"],
        "project_id":                  s["project_id"],
        "private_key_id":              s["private_key_id"],
        "private_key":                 s["private_key"],
        "client_email":                s["client_email"],
        "client_id":                   s["client_id"],
        "auth_uri":                    s["auth_uri"],
        "token_uri":                   s["token_uri"],
        "auth_provider_x509_cert_url": s["auth_provider_x509_cert_url"],
        "client_x509_cert_url":        s["client_x509_cert_url"],
        "universe_domain":             s.get("universe_domain", "googleapis.com"),
    }

    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)

def get_spreadsheet():
    """Retorna o objeto Spreadsheet do gspread."""
    client = get_gsheets_client()
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # Remove parâmetros de URL que o gspread não aceita (ex: ?usp=sharing)
    url = url.split("?")[0].replace("/edit", "")
    return client.open_by_url(url)

def garantir_aba_turma(spreadsheet, nome_turma, incluir_comunidade=False):
    """Cria a aba da turma na planilha se ela ainda não existir. Retorna a worksheet."""
    import gspread
    try:
        ws = spreadsheet.worksheet(nome_turma)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=nome_turma, rows=200, cols=20)
        # Cabeçalho
        cols = ['Nome', 'Sexo', 'Nascimento']
        if incluir_comunidade:
            cols.append('Comunidade')
        for i in range(1, 5):
            cols.extend([f'Data {i}', f'Peso {i}', f'Alt {i}'])
        ws.append_row(cols, value_input_option='USER_ENTERED')
    return ws

def sinc_crianca_gsheets(nome_turma, nome_grupo, crianca_dict, medicoes_list):
    """
    Sincroniza os dados de uma criança (e suas medições) na aba da planilha.
    Cria a aba se não existir. Insere ou atualiza a linha da criança.
    
    crianca_dict: {'nome', 'sexo', 'data_nascimento', 'comunidade'}
    medicoes_list: lista de dicts {'data_medicao', 'peso', 'altura'} ordenada por data
    """
    try:
        spreadsheet = get_spreadsheet()
        incluir_comunidade = (nome_grupo == "Instituto Mãe Lalu")
        ws = garantir_aba_turma(spreadsheet, nome_turma, incluir_comunidade)

        # Lê todos os dados atuais
        dados = ws.get_all_values()
        if not dados:
            return
        header = dados[0]
        rows = dados[1:]

        # Monta a linha a salvar
        linha = [
            crianca_dict.get('nome', ''),
            crianca_dict.get('sexo', ''),
            crianca_dict.get('data_nascimento', ''),
        ]
        if incluir_comunidade:
            linha.append(crianca_dict.get('comunidade', '') or '')

        # Até 4 medições
        for i in range(4):
            if i < len(medicoes_list):
                m = medicoes_list[i]
                linha.extend([
                    str(m.get('data_medicao', '')),
                    str(m.get('peso', '')),
                    str(m.get('altura', '')),
                ])
            else:
                linha.extend(['', '', ''])

        # Verifica se a criança já tem linha
        nome_crianca = crianca_dict.get('nome', '').strip().lower()
        row_idx = None
        for i, row in enumerate(rows):
            if row and row[0].strip().lower() == nome_crianca:
                row_idx = i + 2  # +1 pelo header, +1 porque gspread é 1-indexed
                break

        if row_idx:
            # Atualiza linha existente
            ws.update(f'A{row_idx}', [linha], value_input_option='USER_ENTERED')
        else:
            # Adiciona nova linha
            ws.append_row(linha, value_input_option='USER_ENTERED')

    except Exception as e:
        # Registra falha no log persistente da sessão
        if "_sinc_errors" not in st.session_state:
            st.session_state["_sinc_errors"] = []
        nome_crianca = crianca_dict.get("nome", "?")
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        st.session_state["_sinc_errors"].append(
            f"[{timestamp}] {nome_turma} › {nome_crianca}: {e}"
        )
        st.warning(f"⚠️ Dados salvos localmente, mas erro ao sincronizar com Google Sheets: {e}")

def sinc_tudo_gsheets():
    """
    Sincroniza TODOS os dados do SQLite com o Google Sheets de uma vez.
    Percorre todos os grupos → turmas → crianças → medições.
    Retorna (total_ok, erros[]) onde erros é lista de strings descritivas.
    """
    conn = get_db()
    grupos = conn.execute("SELECT id, nome FROM grupos").fetchall()
    total_ok = 0
    erros = []

    try:
        spreadsheet = get_spreadsheet()
    except Exception as e:
        conn.close()
        return 0, [f"Falha ao conectar ao Google Sheets: {e}"]

    for grupo in grupos:
        turmas = conn.execute(
            "SELECT id, nome FROM turmas WHERE grupo_id = ?", (grupo["id"],)
        ).fetchall()
        incluir_comunidade = (grupo["nome"] == "Instituto Mãe Lalu")

        for turma in turmas:
            # Garante que a aba existe
            try:
                ws = garantir_aba_turma(spreadsheet, turma["nome"], incluir_comunidade)
            except Exception as e:
                erros.append(f"Aba '{turma['nome']}': {e}")
                continue

            criancas = conn.execute(
                "SELECT id, nome, sexo, data_nascimento, comunidade FROM criancas WHERE turma_id = ?",
                (turma["id"],),
            ).fetchall()

            for crianca in criancas:
                meds_raw = conn.execute(
                    "SELECT data_medicao, peso, altura FROM medicoes "
                    "WHERE crianca_id = ? AND peso > 0 AND altura > 0 "
                    "ORDER BY data_medicao ASC",
                    (crianca["id"],),
                ).fetchall()
                medicoes_list = [dict(m) for m in meds_raw]
                crianca_dict = {
                    "nome": crianca["nome"],
                    "sexo": crianca["sexo"],
                    "data_nascimento": str(crianca["data_nascimento"]),
                    "comunidade": crianca["comunidade"] or "",
                }

                try:
                    dados = ws.get_all_values()
                    if not dados:
                        continue
                    rows = dados[1:]
                    linha = [
                        crianca_dict["nome"],
                        crianca_dict["sexo"],
                        crianca_dict["data_nascimento"],
                    ]
                    if incluir_comunidade:
                        linha.append(crianca_dict["comunidade"])
                    for i in range(4):
                        if i < len(medicoes_list):
                            m = medicoes_list[i]
                            linha.extend([
                                str(m.get("data_medicao", "")),
                                str(m.get("peso", "")),
                                str(m.get("altura", "")),
                            ])
                        else:
                            linha.extend(["", "", ""])

                    nome_lower = crianca_dict["nome"].strip().lower()
                    row_idx = None
                    for i, row in enumerate(rows):
                        if row and row[0].strip().lower() == nome_lower:
                            row_idx = i + 2
                            break

                    if row_idx:
                        ws.update(f"A{row_idx}", [linha], value_input_option="USER_ENTERED")
                    else:
                        ws.append_row(linha, value_input_option="USER_ENTERED")

                    total_ok += 1
                except Exception as e:
                    erros.append(
                        f"{grupo['nome']} › {turma['nome']} › {crianca['nome']}: {e}"
                    )

    conn.close()
    return total_ok, erros


def set_success_message(message):
    st.session_state["_success_message"] = message

def show_success_message():
    message = st.session_state.pop("_success_message", None)
    if message:
        st.success(message)

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
        comunidade TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    try:
        conn.execute("ALTER TABLE criancas ADD COLUMN comunidade TEXT")
        conn.commit()
    except Exception:
        pass
    c.execute("""CREATE TABLE IF NOT EXISTS medicoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crianca_id INTEGER REFERENCES criancas(id),
        data_medicao DATE NOT NULL,
        peso REAL NOT NULL,
        altura REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    admin_hash = hash_password("Nutrim@is2026")
    visitor_hash = hash_password("visitante123")
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
              ("admin", admin_hash, "admin"))
    c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
              ("visitante", visitor_hash, "visitor"))
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256((password + "nutrimais_salt").encode()).hexdigest()

def importar_gsheets_para_sqlite():
    """
    Lê TODOS os dados do Google Sheets e popula o SQLite local.
    Executado automaticamente na inicialização do app, só se o banco estiver vazio.
    Isso garante que após um reboot/reset, os dados da planilha sejam restaurados.
    """
    conn = get_db()
    total_criancas = conn.execute("SELECT COUNT(*) FROM criancas").fetchone()[0]
    conn.close()
    if total_criancas > 0:
        return  # Banco já tem dados, não precisa importar

    try:
        client = get_gsheets_client()
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        url = url.split("?")[0].replace("/edit", "")
        spreadsheet = client.open_by_url(url)
    except Exception as e:
        st.warning(f"⚠️ Não foi possível conectar ao Google Sheets para importar dados: {e}")
        return

    conn = get_db()
    total_importadas = 0

    for grupo_nome, lista_turmas in TURMAS_POR_GRUPO.items():
        # Garante que o grupo existe
        grupo_row = conn.execute("SELECT id FROM grupos WHERE nome=?", (grupo_nome,)).fetchone()
        if not grupo_row:
            conn.execute("INSERT OR IGNORE INTO grupos (nome) VALUES (?)", (grupo_nome,))
            conn.commit()
            grupo_row = conn.execute("SELECT id FROM grupos WHERE nome=?", (grupo_nome,)).fetchone()
        grupo_id = grupo_row[0]
        incluir_comunidade = (grupo_nome == "Instituto Mãe Lalu")

        for nome_turma in lista_turmas:
            try:
                ws = spreadsheet.worksheet(nome_turma)
            except Exception:
                continue  # Aba não existe ainda

            dados = ws.get_all_values()
            if len(dados) < 2:
                continue

            header = dados[0]
            rows = dados[1:]

            # Garante que a turma existe
            turma_row = conn.execute("SELECT id FROM turmas WHERE nome=? AND grupo_id=?", (nome_turma, grupo_id)).fetchone()
            if not turma_row:
                conn.execute("INSERT INTO turmas (nome, grupo_id) VALUES (?,?)", (nome_turma, grupo_id))
                conn.commit()
                turma_row = conn.execute("SELECT id FROM turmas WHERE nome=? AND grupo_id=?", (nome_turma, grupo_id)).fetchone()
            turma_id = turma_row[0]

            for row in rows:
                if not row or not row[0].strip():
                    continue
                nome = row[0].strip()
                sexo = row[1].strip() if len(row) > 1 else "M"
                nasc = row[2].strip() if len(row) > 2 else ""

                # Normaliza data de nascimento
                if nasc:
                    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                        try:
                            from datetime import datetime as _dt
                            nasc = _dt.strptime(nasc, fmt).strftime("%Y-%m-%d")
                            break
                        except:
                            pass

                if incluir_comunidade:
                    comunidade = row[3].strip() if len(row) > 3 else ""
                    med_start = 4
                else:
                    comunidade = ""
                    med_start = 3

                # Verifica se já existe
                existe = conn.execute("SELECT id FROM criancas WHERE nome=? AND turma_id=?", (nome, turma_id)).fetchone()
                if not existe:
                    conn.execute(
                        "INSERT INTO criancas (nome, sexo, data_nascimento, grupo_id, turma_id, comunidade) VALUES (?,?,?,?,?,?)",
                        (nome, sexo, nasc, grupo_id, turma_id, comunidade if comunidade else None))
                    conn.commit()
                    total_importadas += 1

                crianca_row = conn.execute("SELECT id FROM criancas WHERE nome=? AND turma_id=?", (nome, turma_id)).fetchone()
                if not crianca_row:
                    continue
                crianca_id = crianca_row[0]

                # Importa medições (até 4 grupos de 3 colunas: Data, Peso, Alt)
                for i in range(4):
                    idx_base = med_start + i * 3
                    if idx_base + 2 >= len(row):
                        break
                    data_med = row[idx_base].strip()
                    peso_str = row[idx_base + 1].strip().replace(",", ".")
                    alt_str = row[idx_base + 2].strip().replace(",", ".")
                    if not data_med or not peso_str or not alt_str:
                        continue
                    try:
                        peso = float(peso_str)
                        alt = float(alt_str)
                        if peso <= 0 or alt <= 0:
                            continue
                        # Normaliza data da medição
                        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                            try:
                                from datetime import datetime as _dt2
                                data_med = _dt2.strptime(data_med, fmt).strftime("%Y-%m-%d")
                                break
                            except:
                                pass
                        existe_med = conn.execute(
                            "SELECT id FROM medicoes WHERE crianca_id=? AND data_medicao=?",
                            (crianca_id, data_med)).fetchone()
                        if not existe_med:
                            conn.execute(
                                "INSERT INTO medicoes (crianca_id, data_medicao, peso, altura) VALUES (?,?,?,?)",
                                (crianca_id, data_med, peso, alt))
                            conn.commit()
                    except:
                        continue

    conn.close()
    if total_importadas > 0:
        st.toast(f"✅ {total_importadas} alunos importados do Google Sheets!", icon="📥")

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

def can_view_group(user, grupo_nome=None):
    if not user:
        return False
    if user["role"] in ("admin", "visitor"):
        return True
    if user["role"] in ("group_admin", "group_visitor") and grupo_nome and user.get("group_access") == grupo_nome:
        return True
    return False

init_db()
importar_gsheets_para_sqlite()

if "user" not in st.session_state:
    st.session_state.user = None

def render_marina_logo(max_width="220px", margin_bottom="12px"):
    nomes = ["logo_marina.jpg","logo_marina.png",
             "LOGONUTRIMARINAMALHEIROS.jpg","LOGONUTRIMARINAMALHEIROS.png",
             "logo_marina_malheiros.jpg","logo_marina_malheiros.png"]
    for nome in nomes:
        if os.path.exists(nome):
            ext = os.path.splitext(nome)[1].lower().replace(".","")
            mime = "jpeg" if ext in ["jpg","jpeg"] else "png"
            with open(nome,"rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<div class="marina-logo" style="text-align:center;margin-bottom:{margin_bottom};">'
                f'<img src="data:image/{mime};base64,{b64}" style="max-width:{max_width};height:auto;display:inline-block;">'
                f'</div>', unsafe_allow_html=True)
            return

def login_page():
    render_marina_logo(max_width="200px", margin_bottom="10px")
    st.markdown("<div style='text-align:center; font-size:2.2rem; letter-spacing:6px; margin-top:10px;'>🍎 🥕 🥦 🍓 🍌 🍇 🥥 🥑</div>", unsafe_allow_html=True)
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
                            "id": user["id"], "username": user["username"],
                            "role": user["role"], "cpf": user["cpf"],
                            "group_access": user["group_access"],
                        }
                        st.rerun()
                    else:
                        st.error("Credenciais invalidas")
                else:
                    st.error("Preencha usuario e senha")
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
            with c1: new_username = st.text_input("Usuario *")
            with c2: new_password = st.text_input("Senha *", type="password")
            with c3:
                new_role = st.selectbox("Perfil", ["visitor", "group_visitor", "group_admin", "admin"],
                    format_func=lambda x: {"visitor":"Visitante Geral","group_visitor":"Visitante de Grupo","group_admin":"Admin de Grupo","admin":"Administrador Geral"}[x])
            c4, c5 = st.columns(2)
            with c4: new_cpf = st.text_input("CPF (opcional)")
            with c5:
                grupo_names = [""] + [g["nome"] for g in grupos]
                new_group = st.selectbox("Grupo (para Admin/Visitante de Grupo)", grupo_names)
            if st.form_submit_button("Criar Usuario", use_container_width=True):
                if new_username and new_password:
                    conn = get_db()
                    try:
                        conn.execute(
                            "INSERT INTO users (username, password_hash, role, cpf, group_access) VALUES (?, ?, ?, ?, ?)",
                            (new_username, hash_password(new_password), new_role,
                             new_cpf if new_cpf else None,
                             new_group if new_role in ("group_admin","group_visitor") and new_group else None))
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
        role_map = {"admin":"👑 Administrador Geral","group_admin":"🔧 Admin de Grupo","group_visitor":"👁 Visitante de Grupo","visitor":"👁 Visitante Geral"}
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            st.markdown(f"**{u['username']}**")
            info_parts = []
            if u["cpf"]: info_parts.append(f"CPF: {u['cpf']}")
            if u["group_access"]: info_parts.append(f"Grupo: {u['group_access']}")
            if info_parts: st.caption(" | ".join(info_parts))
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
    st.divider()
    st.markdown("## 🔄 Backup — Sincronização com Google Sheets")
    st.markdown(
        "Use o botão abaixo para forçar a sincronização **completa** de todos os dados "
        "do banco local com o Google Sheets. Útil após um reboot ou quando a sincronização "
        "automática falhou."
    )

    col_sinc, col_clear = st.columns([3, 1])
    with col_sinc:
        if st.button("☁️ Sincronizar TUDO com Google Sheets", use_container_width=True, type="primary"):
            with st.spinner("Sincronizando… isso pode levar alguns segundos."):
                ok, erros = sinc_tudo_gsheets()
            if not erros:
                st.success(f"✅ {ok} crianças sincronizadas com sucesso!")
                # Limpa log de erros antigos se tudo deu certo
                st.session_state["_sinc_errors"] = []
            else:
                st.warning(f"⚠️ {ok} sincronizadas, mas {len(erros)} erro(s) encontrado(s):")
                for err in erros:
                    st.error(err)

    # Painel de log de erros de sincronização acumulados na sessão
    erros_sessao = st.session_state.get("_sinc_errors", [])
    with col_clear:
        if erros_sessao:
            if st.button("🗑 Limpar log", use_container_width=True):
                st.session_state["_sinc_errors"] = []
                st.rerun()

    if erros_sessao:
        with st.expander(f"🔴 Log de falhas de sincronização ({len(erros_sessao)} erro(s))", expanded=True):
            st.caption("Estes dados foram **salvos localmente** mas não chegaram ao Google Sheets. Use o botão acima para reenviar.")
            for err in erros_sessao:
                st.markdown(f"- `{err}`")
    else:
        st.success("✅ Nenhuma falha de sincronização registrada nesta sessão.")

    st.divider()
    st.markdown("## 📥 Reimportar dados do Google Sheets")
    st.markdown(
        "Use este botão para **trazer de volta** todos os dados que estão no Google Sheets "
        "para o banco local do app. Útil se o banco foi resetado/perdido e a importação "
        "automática na inicialização não foi suficiente, ou se você quer forçar uma "
        "reimportação completa mesmo com dados já existentes."
    )
    st.warning("⚠️ Isso **não apaga** dados existentes no banco local — apenas adiciona o que estiver faltando.")
    if st.button("📥 Reimportar TUDO do Google Sheets → App", use_container_width=True):
        with st.spinner("Lendo Google Sheets e populando banco local…"):
            try:
                # Força reimportação mesmo com banco não vazio
                conn_re = get_db()
                try:
                    client_re = get_gsheets_client()
                    url_re = st.secrets["connections"]["gsheets"]["spreadsheet"]
                    url_re = url_re.split("?")[0].replace("/edit", "")
                    spreadsheet_re = client_re.open_by_url(url_re)
                except Exception as e_conn:
                    st.error(f"❌ Não foi possível conectar ao Google Sheets: {e_conn}")
                    conn_re.close()
                    spreadsheet_re = None

                if spreadsheet_re:
                    total_re = 0
                    erros_re = []
                    for grupo_nome_re, lista_turmas_re in TURMAS_POR_GRUPO.items():
                        grupo_row_re = conn_re.execute("SELECT id FROM grupos WHERE nome=?", (grupo_nome_re,)).fetchone()
                        if not grupo_row_re:
                            conn_re.execute("INSERT OR IGNORE INTO grupos (nome) VALUES (?)", (grupo_nome_re,))
                            conn_re.commit()
                            grupo_row_re = conn_re.execute("SELECT id FROM grupos WHERE nome=?", (grupo_nome_re,)).fetchone()
                        grupo_id_re = grupo_row_re[0]
                        incluir_com_re = (grupo_nome_re == "Instituto Mãe Lalu")

                        for nome_turma_re in lista_turmas_re:
                            try:
                                ws_re = spreadsheet_re.worksheet(nome_turma_re)
                            except Exception:
                                continue
                            dados_re = ws_re.get_all_values()
                            if len(dados_re) < 2:
                                continue
                            rows_re = dados_re[1:]

                            turma_row_re = conn_re.execute("SELECT id FROM turmas WHERE nome=? AND grupo_id=?", (nome_turma_re, grupo_id_re)).fetchone()
                            if not turma_row_re:
                                conn_re.execute("INSERT INTO turmas (nome, grupo_id) VALUES (?,?)", (nome_turma_re, grupo_id_re))
                                conn_re.commit()
                                turma_row_re = conn_re.execute("SELECT id FROM turmas WHERE nome=? AND grupo_id=?", (nome_turma_re, grupo_id_re)).fetchone()
                            turma_id_re = turma_row_re[0]

                            for row_re in rows_re:
                                if not row_re or not row_re[0].strip():
                                    continue
                                nome_re = row_re[0].strip()
                                sexo_re = row_re[1].strip() if len(row_re) > 1 else "M"
                                nasc_re = row_re[2].strip() if len(row_re) > 2 else ""
                                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                                    try:
                                        from datetime import datetime as _dtr
                                        nasc_re = _dtr.strptime(nasc_re, fmt).strftime("%Y-%m-%d")
                                        break
                                    except:
                                        pass
                                if incluir_com_re:
                                    com_re = row_re[3].strip() if len(row_re) > 3 else ""
                                    med_start_re = 4
                                else:
                                    com_re = ""
                                    med_start_re = 3

                                existe_re = conn_re.execute("SELECT id FROM criancas WHERE nome=? AND turma_id=?", (nome_re, turma_id_re)).fetchone()
                                if not existe_re:
                                    conn_re.execute(
                                        "INSERT INTO criancas (nome, sexo, data_nascimento, grupo_id, turma_id, comunidade) VALUES (?,?,?,?,?,?)",
                                        (nome_re, sexo_re, nasc_re, grupo_id_re, turma_id_re, com_re or None))
                                    conn_re.commit()
                                    total_re += 1

                                crianca_row_re = conn_re.execute("SELECT id FROM criancas WHERE nome=? AND turma_id=?", (nome_re, turma_id_re)).fetchone()
                                if not crianca_row_re:
                                    continue
                                crianca_id_re = crianca_row_re[0]

                                for i_m in range(4):
                                    idx_b = med_start_re + i_m * 3
                                    if idx_b + 2 >= len(row_re):
                                        break
                                    dm = row_re[idx_b].strip()
                                    pm = row_re[idx_b + 1].strip().replace(",", ".")
                                    am = row_re[idx_b + 2].strip().replace(",", ".")
                                    if not dm or not pm or not am:
                                        continue
                                    try:
                                        pf = float(pm); af = float(am)
                                        if pf <= 0 or af <= 0:
                                            continue
                                        for fmt2 in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                                            try:
                                                from datetime import datetime as _dtr2
                                                dm = _dtr2.strptime(dm, fmt2).strftime("%Y-%m-%d")
                                                break
                                            except:
                                                pass
                                        existe_med_re = conn_re.execute(
                                            "SELECT id FROM medicoes WHERE crianca_id=? AND data_medicao=?",
                                            (crianca_id_re, dm)).fetchone()
                                        if not existe_med_re:
                                            conn_re.execute(
                                                "INSERT INTO medicoes (crianca_id, data_medicao, peso, altura) VALUES (?,?,?,?)",
                                                (crianca_id_re, dm, pf, af))
                                            conn_re.commit()
                                    except:
                                        continue
                    conn_re.close()
                    st.success(f"✅ Reimportação concluída! {total_re} alunos novos adicionados ao banco local.")
                    st.rerun()
            except Exception as e_re:
                st.error(f"❌ Erro na reimportação: {e_re}")

    st.divider()
    st.info("""
    **📖 Niveis de acesso:**
    - **Visitante Geral:** Visualiza todos os grupos, sem alteracoes.
    - **Visitante de Grupo:** Visualiza apenas o grupo vinculado, sem alteracoes.
    - **Admin de Grupo:** Administra um grupo especifico.
    - **Administrador Geral:** Acesso total ao sistema.
    """)

def is_imla_group(grupo):
    return bool(grupo and grupo.get("nome") == IMLA_GROUP_NAME)

def get_imla_logo_path():
    for logo_path in IMLA_LOGO_PATHS:
        if os.path.exists(logo_path):
            return logo_path
    return None

def render_imla_header():
    logo_path = get_imla_logo_path()
    if logo_path:
        ext = os.path.splitext(logo_path)[1].lower().replace(".", "")
        mime_ext = "jpeg" if ext in ["jpg", "jpeg"] else "png"
        with open(logo_path, "rb") as logo_file:
            logo_b64 = base64.b64encode(logo_file.read()).decode()
        logo_html = f'<img src="data:image/{mime_ext};base64,{logo_b64}" style="max-width:90px;max-height:58px;display:block;">'
    else:
        logo_html = ""
    st.markdown(f"""
        <div class="imla-header">
        <div class="imla-logo-space">{logo_html}</div>
        <div class="imla-title">
            <span class="imla-title-green">INSTITUTO</span>
            <span class="imla-title-blue"> MÃE </span>
            <span class="imla-title-green">LALU</span>
        </div>
        </div>""", unsafe_allow_html=True)

# ── ALTERAÇÃO 1: botões linkam para ?imla_turma=NOME&goto_coletivo=1 ──
def render_imla_turma_buttons(turmas):
    if not turmas:
        return
    
    # Estilização para transformar os botões em "pílulas" coloridas
    st.markdown("""
        <style>
        div.stButton > button {
            border-radius: 20px !important;
            border: none !important;
            padding: 4px 16px !important;
            font-weight: bold !important;
            transition: all 0.2s ease;
            height: auto !important;
            min-height: 32px !important;
        }
        div.stButton > button:hover {
            transform: scale(1.05);
            opacity: 0.9;
        }
        /* Alinhamento dos botões lado a lado */
        div[data-testid="column"] {
            width: fit-content !important;
            flex: unset !important;
            min-width: unset !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 10px;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # Criamos colunas para os botões aparecerem na mesma linha
    cols = st.columns(len(turmas))
    
    for i, turma in enumerate(turmas):
        nome = turma["nome"]
        cor = IMLA_TURMA_COLORS.get(nome, "#6741d9")
        texto_cor = "white"
        
        # Aplicamos a cor de fundo individual de cada botão via CSS
        st.markdown(f"""
            <style>
            div[data-testid="stHorizontalBlock"] > div:nth-child({i+1}) button {{
                background-color: {cor} !important;
                color: {texto_cor} !important;
            }}
            </style>
        """, unsafe_allow_html=True)
        
        # Se o botão for clicado, atualizamos o estado e forçamos o re-processamento
        if cols[i].button(nome, key=f"btn_nav_{nome}_{i}"):
            st.session_state["_imla_turma"] = nome
            st.session_state["_imla_goto_coletivo"] = True
            # Forçamos o rerun para que o main_app leia o novo estado e mude a aba
            st.rerun()

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
    vx_min, vx_max = min(vx_vals), max(vx_vals)
    margem = max((vx_max - vx_min) * 0.5, 10)
    x_min = max(0, vx_min - margem)
    x_max = vx_max + margem
    eixo = ref.get("meses") if eixo_x_campo != "altura" else ref.get("altura")
    if not eixo:
        return
    filtered_eixo = [x for x in eixo if x >= x_min and x <= x_max]
    if not filtered_eixo:
        return
    z_keys = ["z-3","z-2","z-1","z0","z1","z2","z3"]
    z_colors = {"z3":"#DC143C","z2":"#FF8C00","z1":"#4682B4","z0":"#2E8B57","z-1":"#4682B4","z-2":"#FF8C00","z-3":"#DC143C"}
    _plotly_labels_map = {
        "peso_idade":     {"z3":"+3 DP","z2":"Peso elevado","z1":"+1 DP","z0":"Mediana","z-1":"-1 DP","z-2":"Baixo peso","z-3":"Muito baixo peso"},
        "estatura_idade": {"z3":"+3 DP","z2":"+2 DP","z1":"+1 DP","z0":"Mediana","z-1":"-1 DP","z-2":"Baixa estatura","z-3":"Muito baixa estatura"},
        "imc_idade":      {"z3":"Obesidade","z2":"Sobrepeso","z1":"Risco de sobrepeso","z0":"Mediana","z-1":"-1 DP","z-2":"Magreza","z-3":"Magreza acentuada"},
        "peso_estatura":  {"z3":"Obesidade","z2":"Sobrepeso","z1":"+1 DP","z0":"Mediana","z-1":"-1 DP","z-2":"Magreza","z-3":"Magreza acentuada"},
    }
    z_labels = _plotly_labels_map.get(tipo, {"z3":"+3","z2":"+2","z1":"+1","z0":"Mediana","z-1":"-1","z-2":"-2","z-3":"-3"})
    z_dash = {"z3":"dot","z2":"dash","z1":"dash","z0":"solid","z-1":"dash","z-2":"dash","z-3":"dot"}
    fig = go.Figure()
    for zk in z_keys:
        z_arr = ref[zk]
        y_vals = [z_arr[eixo.index(x)] if x in eixo else None for x in filtered_eixo]
        fig.add_trace(go.Scatter(x=filtered_eixo, y=y_vals, mode="lines", name=z_labels[zk],
            line=dict(color=z_colors[zk], width=2 if zk=="z0" else 1, dash=z_dash[zk])))
    fig.add_trace(go.Scatter(
        x=[p["vx"] for p in pontos], y=[p["vy"] for p in pontos],
        mode="markers+lines", name="Medicoes",
        marker=dict(size=10, color="#7B1FA2", symbol="circle"),
        line=dict(color="#7B1FA2", width=2),
        text=[f"Data: {format_date_br(p['data'])}" for p in pontos]))
    fig.update_layout(
        title=dict(text=titulo, font=dict(color="#1565C0" if sexo=="M" else "#AD1457", size=16)),
        xaxis_title=label_x, yaxis_title=label_y, height=420,
        template="plotly_white", legend=dict(font=dict(size=10)),
        margin=dict(l=60, r=20, t=50, b=60))
    st.plotly_chart(fig, use_container_width=True)
    tipo_eixo = "altura" if eixo_x_campo == "altura" else "meses"
    for i, p in enumerate(pontos):
        limites = obter_limites(ref, p["vx"], tipo_eixo)
        meses_val = p["vx"] if eixo_x_campo != "altura" else 0
        status, cor = classificar_nutricional(p["vy"], limites, tipo, meses_val)
        cor_txt = "#333" if cor == "#FFD700" else "white"
        st.markdown(
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{cor};margin-right:6px;"></span>'
            f'<span style="font-size:0.85rem;color:#555;">Medicao {i+1} ({p["vx"]:.1f} {"cm" if eixo_x_campo=="altura" else "meses"}, {p["vy"]:.1f}):</span> '
            f'<span style="background:{cor};color:{cor_txt};padding:3px 10px;border-radius:6px;font-weight:bold;font-size:0.82rem;">{status}</span>',
            unsafe_allow_html=True)
    return fig

def _render_growth_chart_png(sexo, tipo, valid_meds, titulo, eixo_x_campo, eixo_y_campo, label_x, label_y):
    """
    Gera o gráfico de curva de crescimento OMS usando matplotlib e retorna PNG em bytes.
    Não depende de kaleido — funciona em qualquer ambiente cloud.
    Retorna None se não houver dados ou referência disponível.
    """
    import io as _io
    try:
        import matplotlib
        matplotlib.use("Agg")  # backend sem janela, obrigatório em servidor
        import matplotlib.pyplot as plt
        import matplotlib.lines as mlines
    except ImportError:
        return None

    ref = get_ref(sexo, tipo)
    if not ref:
        return None

    # Coleta pontos do aluno
    pontos = []
    for m in valid_meds:
        vx = m["altura"] if eixo_x_campo == "altura" else m["meses"]
        vy = m["peso"] if eixo_y_campo == "peso" else (m["altura"] if eixo_y_campo == "altura" else m["imc"])
        if vx and vy and vx > 0 and vy > 0:
            pontos.append((vx, vy))
    if not pontos:
        return None

    vx_vals = [p[0] for p in pontos]
    vx_min, vx_max = min(vx_vals), max(vx_vals)
    margem = max((vx_max - vx_min) * 0.5, 10)
    x_min = max(0, vx_min - margem)
    x_max = vx_max + margem

    eixo = ref.get("meses") if eixo_x_campo != "altura" else ref.get("altura")
    if not eixo:
        return None
    filtered_eixo = [x for x in eixo if x_min <= x <= x_max]
    if not filtered_eixo:
        return None

    _z_labels_map2 = {
        "peso_idade":     {"-3": "Muito baixo peso", "-2": "Baixo peso", "-1": "-1 DP",
                           "0": "Mediana", "+1": "+1 DP", "+2": "Peso elevado", "+3": "+3 DP"},
        "estatura_idade": {"-3": "Muito baixa estatura", "-2": "Baixa estatura", "-1": "-1 DP",
                           "0": "Mediana", "+1": "+1 DP", "+2": "+2 DP", "+3": "+3 DP"},
        "imc_idade":      {"-3": "Magreza acentuada", "-2": "Magreza", "-1": "-1 DP",
                           "0": "Mediana", "+1": "Risco de sobrepeso", "+2": "Sobrepeso", "+3": "Obesidade"},
        "peso_estatura":  {"-3": "Magreza acentuada", "-2": "Magreza", "-1": "-1 DP",
                           "0": "Mediana", "+1": "+1 DP", "+2": "Sobrepeso", "+3": "Obesidade"},
    }
    _lbl2 = _z_labels_map2.get(tipo, {"-3": "-3", "-2": "-2", "-1": "-1", "0": "Mediana", "+1": "+1", "+2": "+2", "+3": "+3"})

    z_cfg = [
        ("z-3", "#8B0000", "--", 0.8, _lbl2["-3"]),
        ("z-2", "#FF4500", "--", 0.9, _lbl2["-2"]),
        ("z-1", "#4682B4", ":",  0.9, _lbl2["-1"]),
        ("z0",  "#2E8B57", "-",  1.5, _lbl2["0"]),
        ("z1",  "#4682B4", ":",  0.9, _lbl2["+1"]),
        ("z2",  "#FF4500", "--", 0.9, _lbl2["+2"]),
        ("z3",  "#8B0000", "--", 0.8, _lbl2["+3"]),
    ]

    fig, ax = plt.subplots(figsize=(5.2, 3.0), dpi=130)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    legend_handles = []
    for zk, cor, ls, lw, lbl in z_cfg:
        z_arr = ref[zk]
        y_vals = [z_arr[eixo.index(x)] for x in filtered_eixo if x in eixo]
        x_vals = [x for x in filtered_eixo if x in eixo]
        if y_vals:
            ax.plot(x_vals, y_vals, color=cor, linestyle=ls, linewidth=lw, alpha=0.85)
            legend_handles.append(mlines.Line2D([], [], color=cor, linestyle=ls, linewidth=lw, label=lbl))

    # Pontos do aluno
    px = [p[0] for p in pontos]
    py = [p[1] for p in pontos]
    ax.plot(px, py, color="#7B1FA2", linewidth=1.4, zorder=5)
    ax.scatter(px, py, color="#7B1FA2", s=40, zorder=6, label="Medicoes")
    legend_handles.append(mlines.Line2D([], [], color="#7B1FA2", marker="o", linestyle="-",
                                         markersize=4, linewidth=1.4, label="Medicoes"))

    ax.set_title(titulo, fontsize=8, fontweight="bold", color="#333333", pad=4)
    ax.set_xlabel(label_x, fontsize=6.5)
    ax.set_ylabel(label_y, fontsize=6.5)
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.legend(handles=legend_handles, fontsize=5, loc="upper left",
              framealpha=0.7, ncol=2, borderpad=0.4, handlelength=1.2)

    plt.tight_layout(pad=0.4)

    buf_png = _io.BytesIO()
    fig.savefig(buf_png, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf_png.seek(0)
    return buf_png.read()


def _desenhar_pagina_template(c, template_path, W, H):
    """
    Usa o template PDF como imagem de fundo na página atual do canvas.
    Se o template não existir, desenha o fundo colorido padrão.
    """
    from reportlab.lib.utils import ImageReader
    import io as _io

    if template_path and os.path.exists(template_path):
        try:
            # Rasteriza a primeira página do template como PNG usando pypdf + pillow
            from pypdf import PdfReader as _PdfReader
            import subprocess, tempfile
            # Tenta com pdftoppm (poppler) para melhor qualidade
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            result = subprocess.run(
                ["pdftoppm", "-r", "150", "-png", "-singlefile", template_path, tmp_path.replace(".png", "")],
                capture_output=True, timeout=10
            )
            final_path = tmp_path.replace(".png", "") + ".png"
            if result.returncode == 0 and os.path.exists(final_path):
                c.drawImage(ImageReader(final_path), 0, 0, width=W, height=H)
                os.unlink(final_path)
                return True
        except Exception:
            pass
        # Fallback: tenta com pdf2image/pillow
        try:
            from pdf2image import convert_from_path
            imgs = convert_from_path(template_path, dpi=150, first_page=1, last_page=1)
            if imgs:
                buf_img = _io.BytesIO()
                imgs[0].save(buf_img, format="PNG")
                buf_img.seek(0)
                c.drawImage(ImageReader(buf_img), 0, 0, width=W, height=H)
                return True
        except Exception:
            pass

    # Fallback visual: fundo amarelo + borda verde arredondada
    c.setFillColorRGB(0.98, 0.96, 0.78)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColorRGB(1.0, 0.87, 0.2)
    c.rect(0, 0, W, 130, fill=1, stroke=0)
    c.rect(0, H - 130, W, 130, fill=1, stroke=0)
    c.setStrokeColorRGB(0.47, 0.73, 0.18)
    c.setLineWidth(14)
    c.roundRect(28, 28, W - 56, H - 56, 40, fill=0, stroke=1)
    return False


def _render_growth_chart_png_large(sexo, tipo, valid_meds, titulo, eixo_x_campo, eixo_y_campo, label_x, label_y):
    """
    Versão maior do gráfico para o formato folder (painel único).
    Retorna (png_bytes, lista_de_diagnosticos) onde diagnosticos é
    lista de dicts {label, status, cor_hex}.
    """
    import io as _io
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.lines as mlines
    except ImportError:
        return None, []

    ref = get_ref(sexo, tipo)
    if not ref:
        return None, []

    pontos = []
    for m in valid_meds:
        vx = m["altura"] if eixo_x_campo == "altura" else m["meses"]
        vy = m["peso"] if eixo_y_campo == "peso" else (m["altura"] if eixo_y_campo == "altura" else m["imc"])
        if vx and vy and vx > 0 and vy > 0:
            pontos.append({"vx": vx, "vy": vy, "data": m.get("data", ""), "idx": len(pontos) + 1})
    if not pontos:
        return None, []

    vx_vals = [p["vx"] for p in pontos]
    vx_min, vx_max = min(vx_vals), max(vx_vals)
    margem = max((vx_max - vx_min) * 0.5, 10)
    x_min = max(0, vx_min - margem)
    x_max = vx_max + margem

    eixo = ref.get("meses") if eixo_x_campo != "altura" else ref.get("altura")
    if not eixo:
        return None, []
    filtered_eixo = [x for x in eixo if x_min <= x <= x_max]
    if not filtered_eixo:
        return None, []

    # Rótulos clínicos por tipo de índice
    _z_labels_map = {
        "peso_idade":     {"-3": "Muito baixo peso", "-2": "Baixo peso", "-1": "-1 DP",
                           "0": "Mediana", "+1": "+1 DP", "+2": "Peso elevado", "+3": "+3 DP"},
        "estatura_idade": {"-3": "Muito baixa estatura", "-2": "Baixa estatura", "-1": "-1 DP",
                           "0": "Mediana", "+1": "+1 DP", "+2": "+2 DP", "+3": "+3 DP"},
        "imc_idade":      {"-3": "Magreza acentuada", "-2": "Magreza", "-1": "-1 DP",
                           "0": "Mediana", "+1": "Risco de sobrepeso", "+2": "Sobrepeso", "+3": "Obesidade"},
        "peso_estatura":  {"-3": "Magreza acentuada", "-2": "Magreza", "-1": "-1 DP",
                           "0": "Mediana", "+1": "+1 DP", "+2": "Sobrepeso", "+3": "Obesidade"},
    }
    _lbl = _z_labels_map.get(tipo, {"-3": "-3", "-2": "-2", "-1": "-1", "0": "Mediana", "+1": "+1", "+2": "+2", "+3": "+3"})

    z_cfg = [
        ("z-3", "#8B0000", "--", 1.0, _lbl["-3"]),
        ("z-2", "#FF4500", "--", 1.1, _lbl["-2"]),
        ("z-1", "#4682B4", ":",  1.1, _lbl["-1"]),
        ("z0",  "#2E8B57", "-",  2.0, _lbl["0"]),
        ("z1",  "#4682B4", ":",  1.1, _lbl["+1"]),
        ("z2",  "#FF4500", "--", 1.1, _lbl["+2"]),
        ("z3",  "#8B0000", "--", 1.0, _lbl["+3"]),
    ]
    fig, ax = plt.subplots(figsize=(8.0, 5.8), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#FAFAFA")

    legend_handles = []
    for zk, cor, ls, lw, lbl in z_cfg:
        z_arr = ref[zk]
        y_vals = [z_arr[eixo.index(x)] for x in filtered_eixo if x in eixo]
        x_vals = [x for x in filtered_eixo if x in eixo]
        if y_vals:
            ax.plot(x_vals, y_vals, color=cor, linestyle=ls, linewidth=lw, alpha=0.85)
            legend_handles.append(mlines.Line2D([], [], color=cor, linestyle=ls, linewidth=lw, label=lbl))

    px = [p["vx"] for p in pontos]
    py = [p["vy"] for p in pontos]
    ax.plot(px, py, color="#7B1FA2", linewidth=1.8, zorder=5)
    ax.scatter(px, py, color="#7B1FA2", s=55, zorder=6)
    legend_handles.append(mlines.Line2D([], [], color="#7B1FA2", marker="o", linestyle="-",
                                         markersize=5, linewidth=1.8, label="Medicoes"))

    ax.set_xlabel(label_x, fontsize=9)
    ax.set_ylabel(label_y, fontsize=9)
    ax.tick_params(labelsize=8)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.legend(handles=legend_handles, fontsize=6.5, loc="upper left",
              framealpha=0.75, ncol=1, borderpad=0.5, handlelength=1.4)

    plt.tight_layout(pad=0.3)

    buf_png = _io.BytesIO()
    fig.savefig(buf_png, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf_png.seek(0)
    png_bytes = buf_png.read()

    # Calcula diagnósticos por aferição
    tipo_eixo = "altura" if eixo_x_campo == "altura" else "meses"
    diagnosticos = []
    for i, p in enumerate(pontos):
        limites = obter_limites(ref, p["vx"], tipo_eixo)
        meses_val = p["vx"] if eixo_x_campo != "altura" else 0
        status, cor_hex = classificar_nutricional(p["vy"], limites, tipo, meses_val)
        unidade = "cm" if eixo_x_campo == "altura" else "meses"
        data_fmt = p["data"]
        try:
            parts = str(data_fmt).split("-")
            if len(parts) == 3:
                data_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except:
            pass
        diagnosticos.append({
            "label": f"Aferição {p['idx']} ({p['vx']:.1f} {unidade}, {p['vy']:.1f}) — {data_fmt}",
            "status": status,
            "cor_hex": cor_hex,
        })

    return png_bytes, diagnosticos


def gerar_ficha_pdf(crianca, grupo_nome, turma_nome, medicoes, valid_meds_graficos=None):
    """
    Gera PDF no formato FOLDER IMPRESSO:
    Cada página A4 é dividida verticalmente em 2 painéis (esquerdo | direito).
    O template de fundo é desenhado em cada painel individualmente.

    Página 1 (A4 paisagem):
      Painel esq → 1.1 Dados Cadastrais (nome, turma, nasc, idade, foto)
      Painel dir → 1.2 Aferições + texto OMS + aviso importante

    Página 2 (A4 paisagem):
      Painel esq → Gráfico 1 (Peso x Idade) + diagnósticos
      Painel dir → Gráfico 2 (Estatura x Idade) + diagnósticos

    Página 3 (A4 paisagem):
      Painel esq → Gráfico 3 (IMC x Idade) + diagnósticos
      Painel dir → Gráfico 4 (Peso x Estatura) + diagnósticos
    """
    import io
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from datetime import date as _date

    TEMPLATE_PATH = "template_ficha.pdf"

    # Página em modo PAISAGEM: cada painel ocupa metade da largura
    PW, PH = landscape(A4)   # PW ≈ 841, PH ≈ 595
    PANEL_W = PW / 2          # largura de cada painel

    # Padding interno de cada painel (espelhado pelo template)
    PAD_X   = 28    # margens laterais — conteúdo dentro da área branca
    PAD_TOP = 148   # bem abaixo do arco verde superior — evita sobreposição
    PAD_BOT = 110   # bem acima do rodapé verde — texto não cai sobre as frutas

    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=landscape(A4))

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────
    def format_date_pdf(d):
        if not d:
            return "-"
        try:
            parts = str(d).split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except:
            pass
        return str(d)

    def calcular_idade_str(data_nasc):
        if not data_nasc:
            return "-"
        try:
            from datetime import date as _d2
            nasc = _d2.fromisoformat(str(data_nasc))
            hoje = _d2.today()
            anos = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
            meses_total = (hoje.year - nasc.year) * 12 + (hoje.month - nasc.month)
            if hoje.day < nasc.day:
                meses_total -= 1
            meses_rest = meses_total % 12
            if anos >= 2:
                return f"{anos} anos e {meses_rest} meses"
            return f"{meses_total} meses"
        except:
            return "-"

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    # Desenha o template escalado para cobrir exatamente um painel (PANEL_W x PH)
    def draw_panel_template(offset_x):
        """Desenha o template de fundo (ou fallback) no painel com deslocamento offset_x."""
        import io as _io_t
        if TEMPLATE_PATH and os.path.exists(TEMPLATE_PATH):
            try:
                import subprocess, tempfile
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                result = subprocess.run(
                    ["pdftoppm", "-r", "150", "-png", "-singlefile", TEMPLATE_PATH,
                     tmp_path.replace(".png", "")],
                    capture_output=True, timeout=10)
                final_path = tmp_path.replace(".png", "") + ".png"
                if result.returncode == 0 and os.path.exists(final_path):
                    c.drawImage(ImageReader(final_path), offset_x, 0,
                                width=PANEL_W, height=PH, preserveAspectRatio=False)
                    os.unlink(final_path)
                    return
            except Exception:
                pass
            try:
                from pdf2image import convert_from_path
                imgs = convert_from_path(TEMPLATE_PATH, dpi=150, first_page=1, last_page=1)
                if imgs:
                    buf_img = _io_t.BytesIO()
                    imgs[0].save(buf_img, format="PNG")
                    buf_img.seek(0)
                    c.drawImage(ImageReader(buf_img), offset_x, 0,
                                width=PANEL_W, height=PH, preserveAspectRatio=False)
                    return
            except Exception:
                pass
        # Fallback visual
        c.setFillColorRGB(0.98, 0.96, 0.78)
        c.rect(offset_x, 0, PANEL_W, PH, fill=1, stroke=0)
        c.setFillColorRGB(1.0, 0.87, 0.2)
        c.rect(offset_x, 0, PANEL_W, 90, fill=1, stroke=0)
        c.rect(offset_x, PH - 90, PANEL_W, 90, fill=1, stroke=0)
        c.setStrokeColorRGB(0.47, 0.73, 0.18)
        c.setLineWidth(10)
        c.roundRect(offset_x + 18, 18, PANEL_W - 36, PH - 36, 30, fill=0, stroke=1)

    # Conteúdo dentro de um painel
    def panel_content_bounds(offset_x):
        """Retorna (cx, cy_top, cw, cy_bot) — área útil de conteúdo dentro do painel."""
        cx = offset_x + PAD_X
        cw = PANEL_W - 2 * PAD_X
        cy_top = PH - PAD_TOP
        cy_bot = PAD_BOT
        return cx, cy_top, cw, cy_bot

    def draw_section_bar(label, y, cx, cw, size=9):
        c.setFillColorRGB(0.42, 0.68, 0.15)
        c.roundRect(cx, y - 2, cw, 18, 4, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("Helvetica-Bold", size)
        c.drawString(cx + 7, y + 3, label)
        return y - 24

    def draw_field(label, value, x, y, lbl_w=70):
        c.setFillColorRGB(0.38, 0.1, 0.58)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x, y, label)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.setFont("Helvetica", 9)
        c.drawString(x + lbl_w, y, str(value) if value else "-")

    def draw_panel_title(label, cx, cw, cy_top, size=12):
        c.setFillColorRGB(0.27, 0.55, 0.09)
        c.setFont("Helvetica-Bold", size)
        c.drawCentredString(cx + cw / 2, cy_top, label)
        cur = cy_top - 14
        c.setStrokeColorRGB(0.42, 0.68, 0.15)
        c.setLineWidth(1.2)
        c.line(cx, cur, cx + cw, cur)
        return cur - 6

    def draw_footer_panel(cx, cw, cy_bot, page_num, panel_num):
        c.setFillColorRGB(0.27, 0.55, 0.09)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(cx + cw / 2, cy_bot - 2,
            f"Gerado em {_date.today().strftime('%d/%m/%Y')}  —  Pág. {page_num}")

    # ─────────────────────────────────────────────────────────
    # DADOS COMPARTILHADOS
    # ─────────────────────────────────────────────────────────
    nome_aluno = crianca.get("nome", "-")
    sexo_label = "Masculino" if crianca.get("sexo") == "M" else "Feminino"

    diag_cores_map = {
        "Magreza acentuada":               (0.55, 0, 0),
        "Magreza":                         (1, 0.27, 0),
        "Eutrofia":                        (0.18, 0.55, 0.34),
        "Peso adequado para a idade":      (0.18, 0.55, 0.34),
        "Risco de sobrepeso":              (0.85, 0.7, 0),
        "Sobrepeso":                       (1, 0.55, 0),
        "Obesidade":                       (1, 0, 0),
        "Obesidade grave":                 (0.55, 0, 0),
        "Muito baixo peso para a idade":   (0.55, 0, 0),
        "Baixo peso para a idade":         (1, 0.27, 0),
        "Peso elevado para a idade":       (1, 0.55, 0),
        "Muito baixa estatura para a idade": (0.55, 0, 0),
        "Baixa estatura para a idade":     (1, 0.27, 0),
        "Estatura adequada para a idade":  (0.18, 0.55, 0.34),
    }

    # ═════════════════════════════════════════════════════════
    # PÁGINA 1  (paisagem):
    #   Painel esq (offset 0)      → 1.1 Dados Cadastrais
    #   Painel dir (offset PANEL_W) → 1.2 Aferições + OMS + Aviso
    # ═════════════════════════════════════════════════════════
    for panel_offset in [0, PANEL_W]:
        draw_panel_template(panel_offset)

    cx_l, cy_top, cw, cy_bot = panel_content_bounds(0)
    cx_r, _, cw_r, _ = panel_content_bounds(PANEL_W)

    # ── Painel esquerdo: 1.1 Dados Cadastrais ──
    # Calcular altura total do conteúdo para centralizar verticalmente
    n_campos = 5 + (1 if crianca.get("comunidade") else 0)
    FOTO_W = 100; FOTO_H = 126
    FIELD_H = 18
    TITLE_H = 38   # título + subtítulo + linha
    BAR_H   = 24   # barra de seção
    conteudo_esq_h = TITLE_H + BAR_H + max(n_campos * FIELD_H, FOTO_H) + 10
    area_esq_h = cy_top - cy_bot
    offset_v = max(0, (area_esq_h - conteudo_esq_h) / 2)
    start_y = cy_top - offset_v

    cur_y = draw_panel_title("FICHA DO ALUNO", cx_l, cw, start_y, size=11)
    c.setFillColorRGB(0.38, 0.1, 0.58)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(cx_l + cw / 2, cur_y, f"{nome_aluno}  |  {turma_nome}  |  {grupo_nome}")
    cur_y -= 10

    cur_y = draw_section_bar("DADOS DO ALUNO", cur_y, cx_l, cw)

    # Foto (canto direito do painel)
    foto_x = cx_l + cw - FOTO_W
    foto_y_top = cur_y

    draw_field("Nome:", nome_aluno, cx_l, cur_y, lbl_w=72)
    cur_y -= FIELD_H
    draw_field("Turma:", turma_nome, cx_l, cur_y, lbl_w=60)
    cur_y -= FIELD_H
    draw_field("Nascimento:", format_date_pdf(crianca.get("data_nascimento")), cx_l, cur_y, lbl_w=80)
    cur_y -= FIELD_H
    draw_field("Idade:", calcular_idade_str(crianca.get("data_nascimento")), cx_l, cur_y, lbl_w=60)
    cur_y -= FIELD_H
    draw_field("Sexo:", sexo_label, cx_l, cur_y, lbl_w=55)
    if crianca.get("comunidade"):
        cur_y -= FIELD_H
        draw_field("Comunidade:", crianca.get("comunidade"), cx_l, cur_y, lbl_w=80)
    cur_y -= 10

    foto_y = foto_y_top - FOTO_H
    c.setFillColorRGB(0.85, 0.93, 0.98)
    c.roundRect(foto_x - 2, foto_y - 2, FOTO_W + 4, FOTO_H + 4, 5, fill=1, stroke=0)
    c.setStrokeColorRGB(0.6, 0.6, 0.6); c.setLineWidth(0.7)
    c.roundRect(foto_x - 2, foto_y - 2, FOTO_W + 4, FOTO_H + 4, 5, fill=0, stroke=1)
    c.setFillColorRGB(0.55, 0.76, 0.29)
    c.ellipse(foto_x - 2, foto_y - 2, foto_x + FOTO_W + 2, foto_y + 22, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    cx_n = foto_x + FOTO_W / 2; cy_n = foto_y + FOTO_H - 22
    for ox, oy, r in [(-10, 0, 8), (0, 0, 12), (10, 0, 8), (-5, 5, 7), (5, 5, 7)]:
        c.circle(cx_n + ox, cy_n + oy, r, fill=1, stroke=0)
    c.setFillColorRGB(0.4, 0.4, 0.4); c.setFont("Helvetica", 7)
    c.drawCentredString(foto_x + FOTO_W / 2, foto_y + 6, "Foto do Aluno")

    draw_footer_panel(cx_l, cw, cy_bot, 1, 1)

    # ── Painel direito: 1.2 Aferições ──
    # Estimar altura do conteúdo para centralização vertical
    n_meds = len(medicoes) if medicoes else 1
    ROW_H  = 15
    av_line_h = 10
    av_lines_count = 5
    aviso_h = av_lines_count * av_line_h + 14
    oms_h   = 20
    table_h = (n_meds + 1) * (ROW_H + 1) + 4
    TITLE_H2 = 40
    BAR_H2   = 24
    conteudo_dir_h = TITLE_H2 + BAR_H2 + table_h + oms_h + aviso_h + 10
    area_dir_h = cy_top - cy_bot
    offset_v2 = max(0, (area_dir_h - conteudo_dir_h) / 2)
    start_y2 = cy_top - offset_v2

    cur_y2 = draw_panel_title("FICHA DO ALUNO", cx_r, cw_r, start_y2, size=11)
    c.setFillColorRGB(0.38, 0.1, 0.58)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(cx_r + cw_r / 2, cur_y2, f"{nome_aluno}  |  {turma_nome}  |  {grupo_nome}")
    cur_y2 -= 10

    cur_y2 = draw_section_bar("AFERICOES", cur_y2, cx_r, cw_r)

    col_labels = ["Aferição", "Data", "Peso\n(kg)", "Altura\n(cm)", "IMC\n(kg/m²)"]
    col_pcts   = [0.18, 0.20, 0.18, 0.20, 0.24]
    col_ws     = [cw_r * p for p in col_pcts]
    row_h_t    = ROW_H
    table_x    = cx_r

    c.setFillColorRGB(0.38, 0.1, 0.58)
    c.rect(table_x, cur_y2 - 2, cw_r, row_h_t, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 7)
    xi = table_x
    for lbl, cw_col in zip(col_labels, col_ws):
        c.drawCentredString(xi + cw_col / 2, cur_y2 + 3, lbl.replace("\n", " "))
        xi += cw_col
    cur_y2 -= row_h_t + 2

    RESERVA = cy_bot + 80
    if medicoes:
        for idx, med in enumerate(medicoes):
            if cur_y2 < RESERVA:
                break
            peso = med.get("peso", 0) or 0
            alt  = med.get("altura", 0) or 0
            if peso > 0 and alt > 0:
                imc = peso / pow(alt / 100, 2)
                imc_txt = f"{imc:.2f}"
                meses_m = calcular_idade_meses(crianca.get("data_nascimento","2000-01-01"), med.get("data_medicao","2000-01-01"))
                ref_imc = get_ref(crianca.get("sexo","M"), "imc_idade")
                if ref_imc and 0 <= meses_m <= 228:
                    lim = obter_limites(ref_imc, meses_m, "meses")
                    diag, _ = classificar_nutricional(imc, lim, "imc_idade", meses_m)
                else:
                    diag = "Fora da faixa"
            else:
                imc_txt = "-"; diag = "Sem medicao"

            bg = (0.95, 0.91, 1.0) if idx % 2 == 0 else (1, 1, 1)
            c.setFillColorRGB(*bg)
            c.rect(table_x, cur_y2 - 2, cw_r, row_h_t, fill=1, stroke=0)
            row_vals = [f"Afer. {idx+1}", format_date_pdf(med.get("data_medicao","")),
                        f"{peso:.1f}" if peso > 0 else "-",
                        f"{alt:.1f}" if alt > 0 else "-",
                        imc_txt]
            xi = table_x
            for ci, (val, cw_col) in enumerate(zip(row_vals, col_ws)):
                c.setFillColorRGB(0.15, 0.15, 0.15); c.setFont("Helvetica", 7)
                c.drawCentredString(xi + cw_col / 2, cur_y2 + 3, val)
                xi += cw_col
            c.setStrokeColorRGB(0.8, 0.75, 0.9); c.setLineWidth(0.3)
            c.line(table_x, cur_y2 - 2, table_x + cw_r, cur_y2 - 2)
            cur_y2 -= row_h_t + 1
    else:
        c.setFillColorRGB(0.5, 0.5, 0.5); c.setFont("Helvetica-Oblique", 8)
        c.drawString(table_x + 6, cur_y2, "Nenhuma aferição registrada.")
        cur_y2 -= 14

    # Texto OMS
    cur_y2 -= 8
    c.setFillColorRGB(0.15, 0.15, 0.15); c.setFont("Helvetica-BoldOblique", 8)
    oms_txt = "Seguem as classificações de acordo com as curvas de crescimento da OMS."
    c.drawString(cx_r, cur_y2, oms_txt)
    cur_y2 -= 12

    # Caixa aviso importante
    aviso_lines = [
        ("IMPORTANTE: Essas classificações utilizam somente dados antropométricos", True),
        ("(Peso, Altura e IMC), não levando em consideração outros parâmetros", False),
        ("necessários para diagnóstico nutricional completo (exames bioquímicos,", False),
        ("hábitos alimentares). Não substituem o diagnóstico de profissional", False),
        ("capacitado. São para fins de conhecimento e rastreamento nutricional.", False),
    ]
    av_total_h = av_lines_count * av_line_h + 14
    av_y_start = cur_y2
    av_y_base  = av_y_start - av_total_h
    c.setFillColorRGB(1.0, 0.98, 0.87)
    c.roundRect(cx_r, av_y_base - 2, cw_r, av_total_h, 4, fill=1, stroke=0)
    c.setFillColorRGB(0.94, 0.75, 0.12)
    c.rect(cx_r, av_y_base - 2, 4, av_total_h, fill=1, stroke=0)
    ty = av_y_start - 8
    for txt, bold in aviso_lines:
        c.setFillColorRGB(0.35, 0.22, 0.03)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 7.5)
        c.drawString(cx_r + 8, ty, txt)
        ty -= av_line_h

    draw_footer_panel(cx_r, cw_r, cy_bot, 1, 2)

    # ═════════════════════════════════════════════════════════
    # PÁGINAS 2 e 3 — Gráficos (cada painel = 1 gráfico)
    # ═════════════════════════════════════════════════════════
    graficos_def = [
        {"tipo": "peso_idade",    "titulo": "Grafico 1 — Peso x Idade",     "eixo_x": "meses",  "eixo_y": "peso",   "lx": "Idade (meses)", "ly": "Peso (kg)"},
        {"tipo": "estatura_idade","titulo": "Grafico 2 — Estatura x Idade", "eixo_x": "meses",  "eixo_y": "altura", "lx": "Idade (meses)", "ly": "Estatura (cm)"},
        {"tipo": "imc_idade",     "titulo": "Grafico 3 — IMC x Idade",      "eixo_x": "meses",  "eixo_y": "imc",    "lx": "Idade (meses)", "ly": "IMC (kg/m²)"},
        {"tipo": "peso_estatura", "titulo": "Grafico 4 — Peso x Estatura",  "eixo_x": "altura", "eixo_y": "peso",   "lx": "Estatura (cm)", "ly": "Peso (kg)"},
    ]

    if valid_meds_graficos and crianca.get("sexo"):
        import io as _io4

        # Renderiza pares de gráficos em páginas separadas
        for pg_idx, (g_esq, g_dir) in enumerate([(graficos_def[0], graficos_def[1]),
                                                   (graficos_def[2], graficos_def[3])]):
            c.showPage()

            for panel_offset in [0, PANEL_W]:
                draw_panel_template(panel_offset)

            page_num = pg_idx + 2
            subtitulo_g = f"{nome_aluno}  |  {turma_nome}  |  {grupo_nome}"

            for gi, (g, panel_off) in enumerate([(g_esq, 0), (g_dir, PANEL_W)]):
                cx_p, cy_top_p, cw_p, cy_bot_p = panel_content_bounds(panel_off)

                ref_check = get_ref(crianca["sexo"], g["tipo"])
                valid_for = [m for m in valid_meds_graficos
                             if (m["altura"] if g["eixo_x"] == "altura" else m["meses"]) > 0]

                if not ref_check or not valid_for:
                    mid_y = (cy_top_p + cy_bot_p) / 2
                    c.setFillColorRGB(0.5, 0.5, 0.5); c.setFont("Helvetica-Oblique", 9)
                    c.drawCentredString(cx_p + cw_p / 2, mid_y, "Dados insuficientes para este grafico.")
                    draw_footer_panel(cx_p, cw_p, cy_bot_p, page_num, gi + 1)
                    continue

                png, diagnosticos = _render_growth_chart_png_large(
                    crianca["sexo"], g["tipo"], valid_meds_graficos,
                    g["titulo"], g["eixo_x"], g["eixo_y"], g["lx"], g["ly"])

                if not png:
                    draw_footer_panel(cx_p, cw_p, cy_bot_p, page_num, gi + 1)
                    continue

                # ── Constantes de layout ──
                DIAG_FONT   = 8.5
                BADGE_H     = 15
                BADGE_GAP   = 4
                TITULO_H    = 20   # texto do título
                LINHA_H     = 6    # linha separadora + gap
                SUBTIT_H    = 16   # subtítulo em negrito
                GAP_SUB_IMG = 6    # gap entre subtítulo e gráfico
                GAP_IMG_DIAG = 8   # gap entre gráfico e diagnósticos
                DIAG_AREA_H = len(diagnosticos) * (BADGE_H + BADGE_GAP)

                header_h  = TITULO_H + LINHA_H + SUBTIT_H + GAP_SUB_IMG
                footer_h  = DIAG_AREA_H + GAP_IMG_DIAG

                # Área útil total
                area_util = cy_top_p - cy_bot_p

                # Gráfico ocupa tudo que restar
                img_h = area_util - header_h - footer_h
                img_h = max(img_h, 150)

                # Bloco completo centralizado verticalmente
                bloco_h  = header_h + img_h + footer_h
                margem_v = max(0, (area_util - bloco_h) / 2)
                bloco_top = cy_top_p - margem_v

                # ── Título ──
                titulo_y = bloco_top - TITULO_H + 4
                c.setFillColorRGB(0.27, 0.55, 0.09)
                c.setFont("Helvetica-Bold", 11)
                c.drawCentredString(cx_p + cw_p / 2, titulo_y, g["titulo"])

                # Linha separadora
                linha_y = titulo_y - LINHA_H
                c.setStrokeColorRGB(0.42, 0.68, 0.15)
                c.setLineWidth(1.2)
                c.line(cx_p, linha_y, cx_p + cw_p, linha_y)

                # ── Subtítulo em negrito e fonte maior ──
                subtit_y = linha_y - SUBTIT_H + 4
                c.setFillColorRGB(0.28, 0.07, 0.44)
                c.setFont("Helvetica-Bold", 9.5)
                c.drawCentredString(cx_p + cw_p / 2, subtit_y, subtitulo_g)

                # ── Gráfico ──
                img_y = subtit_y - GAP_SUB_IMG - img_h
                img_buf = _io4.BytesIO(png)
                c.drawImage(ImageReader(img_buf), cx_p, img_y,
                            width=cw_p, height=img_h,
                            preserveAspectRatio=False, mask="auto")

                # ── Diagnósticos abaixo do gráfico ──
                diag_y = img_y - GAP_IMG_DIAG
                for diag_item in diagnosticos:
                    if diag_y < cy_bot_p + 4:
                        break
                    cor_rgb = hex_to_rgb(diag_item["cor_hex"])
                    cor_txt = (0.1, 0.1, 0.1) if diag_item["cor_hex"].upper() in ("#FFD700", "#FFC713") else (1, 1, 1)
                    c.setFillColorRGB(*cor_rgb)
                    c.roundRect(cx_p, diag_y - 2, cw_p, BADGE_H, 4, fill=1, stroke=0)
                    label_txt = diag_item["label"]
                    status_txt = diag_item["status"]
                    c.setFillColorRGB(*cor_txt)
                    c.setFont("Helvetica", DIAG_FONT)
                    c.drawString(cx_p + 7, diag_y + 3, label_txt)
                    c.setFont("Helvetica-Bold", DIAG_FONT)
                    lbl_w_px = c.stringWidth(label_txt, "Helvetica", DIAG_FONT)
                    c.drawString(cx_p + 9 + lbl_w_px, diag_y + 3, f"→ {status_txt}")
                    diag_y -= (BADGE_H + BADGE_GAP)

                draw_footer_panel(cx_p, cw_p, cy_bot_p, page_num, gi + 1)

    c.save()
    buf.seek(0)
    return buf.read()


def main_app():
    user = st.session_state.user
    conn = get_db()

    with st.sidebar:
        render_marina_logo(max_width="150px", margin_bottom="6px")
        st.markdown(f"### 🍎 NutriMais")
        role_labels = {"admin":"👑 Admin","group_admin":"🔧 Admin Grupo","group_visitor":"👁 Visitante Grupo","visitor":"👁 Visitante"}
        st.markdown(f"**{role_labels.get(user['role'], user['role'])}** | {user['username']}")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        st.divider()

        # ── ALTERAÇÃO 2: lê query params e faz st.rerun() para aplicar ──
        try:
            imla_turma_param = st.query_params.get("imla_turma")
            goto_coletivo_param = st.query_params.get("goto_coletivo")
        except Exception:
            imla_turma_param = None
            goto_coletivo_param = None
        if isinstance(imla_turma_param, list):
            imla_turma_param = imla_turma_param[0] if imla_turma_param else None
        if imla_turma_param:
            st.session_state["_imla_turma"] = imla_turma_param
            st.session_state["_imla_goto_coletivo"] = True
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.rerun()

        if st.session_state.get("_imla_goto_coletivo"):
            pagina_idx = 1
        else:
            pagina_idx = 0
        
        pagina = st.radio("Navegacao", ["📋 Sistema", "📊 Controle Coletivo"], index=pagina_idx)

        grupos = conn.execute("SELECT id, nome FROM grupos").fetchall()

        st.markdown("##### 📂 Grupo")
        grupo_names = ["-- Selecione --"] + [g["nome"] for g in grupos]
        grupo_sel_name = st.selectbox("Grupo", grupo_names, label_visibility="collapsed", key="sel_grupo")
        grupo_sel = None
        if grupo_sel_name != "-- Selecione --":
            grupo_sel = next((dict(g) for g in grupos if g["nome"] == grupo_sel_name), None)

        if can_write(user) and grupo_sel:
            if st.button("🗑 Remover este Grupo", use_container_width=True, key="btn_remover_grupo", type="primary"):
                st.session_state["_confirmar_remover_grupo"] = grupo_sel["id"]
                st.rerun()
            if st.session_state.get("_confirmar_remover_grupo") == grupo_sel["id"]:
                st.warning(f'⚠️ Confirma remoção do grupo "{grupo_sel["nome"]}" e TODOS seus dados?')
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("✅ Sim, remover", key="btn_conf_rem_grupo", use_container_width=True):
                        gid = grupo_sel["id"]
                        turmas_g = conn.execute("SELECT id FROM turmas WHERE grupo_id=?", (gid,)).fetchall()
                        for tg in turmas_g:
                            crs = conn.execute("SELECT id FROM criancas WHERE turma_id=?", (tg["id"],)).fetchall()
                            for cr in crs:
                                conn.execute("DELETE FROM medicoes WHERE crianca_id=?", (cr["id"],))
                            conn.execute("DELETE FROM criancas WHERE turma_id=?", (tg["id"],))
                        conn.execute("DELETE FROM turmas WHERE grupo_id=?", (gid,))
                        conn.execute("DELETE FROM criancas WHERE grupo_id=?", (gid,))
                        conn.execute("DELETE FROM grupos WHERE id=?", (gid,))
                        conn.commit()
                        st.session_state["_confirmar_remover_grupo"] = None
                        st.success("Grupo removido!")
                        st.rerun()
                with cc2:
                    if st.button("❌ Cancelar", key="btn_canc_rem_grupo", use_container_width=True):
                        st.session_state["_confirmar_remover_grupo"] = None
                        st.rerun()

        if can_write(user):
            st.markdown("##### 📂 Cadastrar Grupo")
            novo_grupo = st.text_input("Nome do grupo", key="novo_grupo", label_visibility="collapsed", placeholder="Nome do grupo")
            if st.button("Criar Grupo", use_container_width=True, key="btn_criar_grupo"):
                if novo_grupo and novo_grupo.strip():
                    try:
                        conn.execute("INSERT INTO grupos (nome) VALUES (?)", (novo_grupo.strip(),))
                        conn.commit()
                        set_success_message("Grupo criado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Grupo ja existe!")

        turma_sel = None
        criancas = []
        turmas = []
        if grupo_sel:
            turmas = conn.execute("SELECT id, nome, grupo_id FROM turmas WHERE grupo_id = ?", (grupo_sel["id"],)).fetchall()

    header_parts = ["🍎 NutriMais"]
    if grupo_sel and turma_sel:
        header_parts.append(f" | {grupo_sel['nome']} — {turma_sel['nome']}")
    if user["role"] == "admin":
        header_col, users_col, home_col = st.columns([4, 1, 1])
    else:
        header_col, home_col = st.columns([5, 1])
    with header_col:
        if is_imla_group(grupo_sel):
            render_imla_header()
        else:
            st.markdown(f"<div class='nutri-header'><h2 style='color:#4A148C; margin:0;'>{''.join(header_parts)}</h2></div>", unsafe_allow_html=True)
    if user["role"] == "admin":
        with users_col:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            if st.button("⚙️ Usuarios", use_container_width=True, key="btn_usuarios_topo"):
                st.session_state.show_users_panel = True
                st.rerun()
    with home_col:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("🏠 Tela inicial", use_container_width=True, key="btn_voltar_home_topo"):
            st.session_state.screen = "home"
            st.session_state.show_users_panel = False
            st.rerun()

    show_success_message()

    if user["role"] == "admin" and st.session_state.get("show_users_panel"):
        if st.button("← Voltar ao sistema", key="btn_voltar_sistema_admin"):
            st.session_state.show_users_panel = False
            st.rerun()
        conn.close()
        admin_panel()
        return

    if is_imla_group(grupo_sel) and grupo_sel:
        render_imla_turma_buttons(turmas)

    if not grupo_sel:
        st.markdown("""
        <div style='text-align:center; padding:60px 20px; color:#7B1FA2;'>
            <div style='font-size:3rem; margin-bottom:16px;'>📂</div>
            <h2 style='color:#4A148C;'>Selecione um Grupo</h2>
            <p>Use o menu lateral para selecionar ou criar um grupo.</p>
        </div>""", unsafe_allow_html=True)
        conn.close()
        return

    if grupo_sel and turmas:
        if not is_imla_group(grupo_sel):
            turma_names_central = ["-- Selecione a Turma --"] + [t["nome"] for t in turmas]
            turma_sel_central = st.selectbox("📋 Selecione a Turma", turma_names_central, key="sel_turma_central")
            if turma_sel_central != "-- Selecione a Turma --":
                turma_sel = next((dict(t) for t in turmas if t["nome"] == turma_sel_central), None)
        else:
            imla_turma = st.session_state.get("_imla_turma")
            if imla_turma:
                turma_sel = next((dict(t) for t in turmas if t["nome"] == imla_turma), None)
    elif grupo_sel and not turmas:
        turma_sel = None

    if grupo_sel and turma_sel:
        criancas_raw = conn.execute(
            "SELECT id, nome, sexo, data_nascimento, grupo_id, turma_id, comunidade FROM criancas WHERE turma_id = ?",
            (turma_sel["id"],)).fetchall()
        criancas = [dict(c) for c in criancas_raw]

    if not turma_sel:
        if can_write(user, grupo_sel["nome"] if grupo_sel else None):
            st.markdown("---")
            col_t, col_c = st.columns(2)
            with col_t:
                st.markdown("#### ➕ Cadastrar Turma")
                nova_turma = st.text_input("Nome da turma", key="nova_turma", placeholder="Nome da turma")
                if st.button("Criar Turma", use_container_width=True, key="btn_criar_turma"):
                    if nova_turma and nova_turma.strip():
                        conn.execute("INSERT INTO turmas (nome, grupo_id) VALUES (?, ?)", (nova_turma.strip(), grupo_sel["id"]))
                        conn.commit()
                        # Cria a aba correspondente na planilha Google Sheets
                        try:
                            spreadsheet = get_spreadsheet()
                            incluir_com = (grupo_sel["nome"] == "Instituto Mãe Lalu")
                            garantir_aba_turma(spreadsheet, nova_turma.strip(), incluir_com)
                        except Exception as e:
                            st.warning(f"⚠️ Turma criada localmente, mas erro ao criar aba na planilha: {e}")
                        set_success_message("Turma criada com sucesso!")
                        st.rerun()
                st.markdown("#### 🗑 Remover Turma")
                turma_names_rem = ["-- Selecione --"] + [t["nome"] for t in turmas]
                turma_rem_nome = st.selectbox("Turma para remover", turma_names_rem, key="sel_turma_remover")
                if turma_rem_nome != "-- Selecione --":
                    turma_rem = next((dict(t) for t in turmas if t["nome"] == turma_rem_nome), None)
                    if turma_rem:
                        if st.button("🗑 Confirmar Remoção da Turma", use_container_width=True, key="btn_remover_turma", type="primary"):
                            cris = conn.execute("SELECT id FROM criancas WHERE turma_id=?", (turma_rem["id"],)).fetchall()
                            for cri in cris:
                                conn.execute("DELETE FROM medicoes WHERE crianca_id=?", (cri["id"],))
                            conn.execute("DELETE FROM criancas WHERE turma_id=?", (turma_rem["id"],))
                            conn.execute("DELETE FROM turmas WHERE id=?", (turma_rem["id"],))
                            conn.commit()
                            st.success(f'Turma "{turma_rem_nome}" removida!')
                            st.rerun()
            with col_c:
                st.markdown("#### ℹ️ Como usar")
                if is_imla_group(grupo_sel):
                    st.info("Clique no botão da turma acima para ver os dados coletivos.")
                else:
                    st.info("Selecione uma turma acima para ver os alunos e registrar medicoes.")
        else:
            if not is_imla_group(grupo_sel):
                st.markdown(f"""
                <div style='text-align:center; padding:40px 20px; color:#7B1FA2;'>
                    <div style='font-size:3rem; margin-bottom:16px;'>📋</div>
                    <h2 style='color:#4A148C;'>Selecione uma Turma</h2>
                    <p>Use o seletor acima para escolher uma turma em <strong>{grupo_sel['nome']}</strong>.</p>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style='text-align:center; padding:40px 20px; color:#7B1FA2;'>
                    <div style='font-size:3rem; margin-bottom:16px;'>📋</div>
                    <h2 style='color:#4A148C;'>Selecione uma Turma</h2>
                    <p>Clique em um dos botões de turma acima para ver os dados.</p>
                </div>""", unsafe_allow_html=True)
        conn.close()
        return

    for c in criancas:
        meds = conn.execute(
            "SELECT id, crianca_id, data_medicao, peso, altura FROM medicoes WHERE crianca_id = ?",
            (c["id"],)).fetchall()
        c["medicoes"] = [dict(m) for m in meds]

    # --- ABA: CONTROLE COLETIVO ---
    if pagina == "📊 Controle Coletivo":
        st.markdown(f"## 📋 Controle Coletivo — {turma_sel['nome']}")
        st.markdown(f"**Grupo:** {grupo_sel['nome']} | **Turma:** {turma_sel['nome']} | **Total:** {len(criancas)} crianças")
        
        legend_items = [
            ("#2E8B57","Eutrofia / Adequado","white"),("#FFD700","Risco de Sobrepeso","#333"),
            ("#FF8C00","Sobrepeso","white"),("#FF0000","Obesidade","white"),
            ("#FF4500","Baixo Peso / Magreza","white"),("#8B0000","Muito Baixo / Magreza Acentuada","white"),
            ("#808080","Sem Medicao","white"),
        ]
        legend_html = " ".join([f'<span style="background:{cor};color:{txt};padding:3px 10px;border-radius:5px;font-size:0.78rem;margin-right:4px;">{label}</span>' for cor,label,txt in legend_items])
        st.markdown(legend_html, unsafe_allow_html=True)

        if criancas:
            is_imla = is_imla_group(grupo_sel)
            comunidade_header = '<th style="padding:10px 8px;text-align:center;">Comunidade</th>' if is_imla else ""
            
            table_html = f"""
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
                * {{ font-family: 'Nunito', sans-serif; }}
            </style>
            <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;box-shadow:0 2px 12px rgba(106,27,154,0.15);border-radius:10px;overflow:hidden;font-size:0.88rem;">
            <thead><tr style="background:#6A1B9A;color:white;">
                <th style="padding:10px 8px;text-align:left;">Nome</th>
                <th style="padding:10px 8px;text-align:center;">Sexo</th>
                <th style="padding:10px 8px;text-align:center;">Nascimento</th>
                <th style="padding:10px 8px;text-align:center;">Idade Atual</th>
                {comunidade_header}
                <th style="padding:10px 8px;text-align:center;">Ultima Afericao</th>
                <th style="padding:10px 8px;text-align:center;">Peso (kg)</th>
                <th style="padding:10px 8px;text-align:center;">Altura (cm)</th>
                <th style="padding:10px 8px;text-align:center;">IMC</th>
                <th style="padding:10px 8px;text-align:center;">Diagnostico Nutricional</th>
            </tr></thead><tbody>"""
            
            for i, c in enumerate(criancas):
                bg = "#FAF0FF" if i % 2 == 0 else "white"
                meds = c["medicoes"]
                ultima = next((m for m in reversed(meds) if m["peso"] > 0 and m["altura"] > 0), None)
                
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

                peso_txt = f"{ultima['peso']:.1f}" if ultima else "-"
                altura_txt = f"{ultima['altura']:.1f}" if ultima else "-"
                imc_txt = f"{imc:.1f}" if ultima else "-"
                cor_txt = "#333" if cor == "#FFD700" else "white"
                comunidade_td = f'<td style="padding:9px 8px;text-align:center;">{c.get("comunidade") or "-"}</td>' if is_imla else ""
                
                table_html += f"""
                <tr style="background:{bg};border-bottom:1px solid #E1BEE7;">
                    <td style="padding:9px 12px;font-weight:600;color:#4A148C;">{c['nome']}</td>
                    <td style="padding:9px 8px;text-align:center;">{c['sexo']}</td>
                    <td style="padding:9px 8px;text-align:center;">{format_date_br(c['data_nascimento'])}</td>
                    <td style="padding:9px 8px;text-align:center;">{idade_meses} meses</td>
                    {comunidade_td}
                    <td style="padding:9px 8px;text-align:center;">{format_date_br(ultima['data_medicao']) if ultima else '-'}</td>
                    <td style="padding:9px 8px;text-align:center;">{peso_txt}</td>
                    <td style="padding:9px 8px;text-align:center;">{altura_txt}</td>
                    <td style="padding:9px 8px;text-align:center;">{imc_txt}</td>
                    <td style="padding:9px 14px;text-align:center;">
                        <span style="background:{cor};color:{cor_txt};padding:5px 10px;border-radius:7px;font-weight:bold;font-size:0.8rem;display:inline-block;min-width:160px;">{status}</span>
                    </td>
                </tr>"""

            table_html += "</tbody></table></div>"
            table_height = min(700, 120 + len(criancas) * 48)
            components.html(table_html, height=table_height, scrolling=True)    

        st.markdown("""
            <div class="disclaimer">
                <strong>⚠️ Importante:</strong> As classificacoes feitas pelo aplicativo utilizam somente dados antropometricos
                (Peso, Estatura e IMC), nao levando em consideracao outros parametros que sao necessarios para um diagnostico
                nutricional completo, como exames bioquimicos, avaliacao dos habitos alimentares e exames clinicos. Por isso,
                estes resultados nao substituem o diagnostico individualizado feito por um profissional capacitado e habilitado.
                Essas informacoes sao para fins de conhecimento e rastreamento do perfil nutricional da instituicao.
            </div>""", unsafe_allow_html=True)

    else:
        if not criancas:
            if can_write(user, grupo_sel["nome"]):
                st.markdown("#### ➕ Cadastrar Criança nesta Turma")
                novo_nome = st.text_input("Nome completo", key="novo_nome_crianca", placeholder="Nome completo")
                novo_sexo = st.selectbox("Sexo", ["Masculino", "Feminino"], key="novo_sexo_crianca")
                nova_nasc = st.date_input("Data de nascimento", value=date(2018, 1, 1), key="nova_nasc_crianca")
                nova_comunidade = ""
                if is_imla_group(grupo_sel):
                    nova_comunidade = st.text_input("Comunidade", key="nova_comunidade_crianca", placeholder="Comunidade")
                if st.button("Cadastrar Criança", use_container_width=True, key="btn_criar_crianca"):
                    if novo_nome and novo_nome.strip():
                        sexo_val = "M" if novo_sexo == "Masculino" else "F"
                        conn.execute(
                            "INSERT INTO criancas (nome, sexo, data_nascimento, grupo_id, turma_id, comunidade) VALUES (?, ?, ?, ?, ?, ?)",
                            (novo_nome.strip(), sexo_val, str(nova_nasc), grupo_sel["id"], turma_sel["id"],
                             nova_comunidade.strip() if nova_comunidade else None))
                        conn.commit()
                        # Sincroniza com Google Sheets
                        sinc_crianca_gsheets(
                            nome_turma=turma_sel["nome"],
                            nome_grupo=grupo_sel["nome"],
                            crianca_dict={"nome": novo_nome.strip(), "sexo": sexo_val,
                                          "data_nascimento": str(nova_nasc),
                                          "comunidade": nova_comunidade.strip() if nova_comunidade else ""},
                            medicoes_list=[])
                        set_success_message("Aluno cadastrado com sucesso!")
                        st.rerun()
            else:
                st.markdown("""
                <div style='text-align:center; padding:60px 20px; color:#7B1FA2;'>
                    <div style='font-size:3rem; margin-bottom:16px;'>👶</div>
                    <h2 style='color:#4A148C;'>Nenhuma criança cadastrada</h2>
                </div>""", unsafe_allow_html=True)
        else:  # Este else corresponde ao 'if not criancas'
            crianca_names = [c["nome"] for c in criancas]
            sel_crianca_nome = st.selectbox("👶 Selecione a crianca:", crianca_names)
            crianca_sel = next((c for c in criancas if c["nome"] == sel_crianca_nome), None)

            if crianca_sel:
                write_enabled = can_write(user, grupo_sel["nome"])

                if write_enabled:
                    btn_col1, btn_col2 = st.columns([3, 1])
                    with btn_col2:
                        if st.button("🗑 Remover Criança", key="btn_remover_crianca"):
                            conn2 = get_db()
                            conn2.execute("DELETE FROM medicoes WHERE crianca_id = ?", (crianca_sel["id"],))
                            conn2.execute("DELETE FROM criancas WHERE id = ?", (crianca_sel["id"],))
                            conn2.commit()
                            conn2.close()
                            st.rerun()
                    with btn_col1:
                        with st.expander("➕ Cadastrar Nova Criança nesta Turma"):
                            novo_nome2 = st.text_input("Nome completo", key="novo_nome_crianca2", placeholder="Nome completo")
                            novo_sexo2 = st.selectbox("Sexo", ["Masculino","Feminino"], key="novo_sexo_crianca2")
                            nova_nasc2 = st.date_input("Data de nascimento", value=date(2018,1,1), key="nova_nasc_crianca2")
                            nova_comunidade2 = ""
                            if is_imla_group(grupo_sel):
                                nova_comunidade2 = st.text_input("Comunidade", key="nova_comunidade_crianca2", placeholder="Comunidade")
                            
                            if st.button("Cadastrar", use_container_width=True, key="btn_criar_crianca2"):
                                if novo_nome2 and novo_nome2.strip():
                                    sexo_val2 = "M" if novo_sexo2 == "Masculino" else "F"
                                    conn.execute(
                                        "INSERT INTO criancas (nome, sexo, data_nascimento, grupo_id, turma_id, comunidade) VALUES (?,?,?,?,?,?)",
                                        (novo_nome2.strip(), sexo_val2, str(nova_nasc2), grupo_sel["id"], turma_sel["id"],
                                         nova_comunidade2.strip() if nova_comunidade2 else None))
                                    conn.commit()
                                    # Sincroniza com Google Sheets
                                    sinc_crianca_gsheets(
                                        nome_turma=turma_sel["nome"],
                                        nome_grupo=grupo_sel["nome"],
                                        crianca_dict={"nome": novo_nome2.strip(), "sexo": sexo_val2,
                                                      "data_nascimento": str(nova_nasc2),
                                                      "comunidade": nova_comunidade2.strip() if nova_comunidade2 else ""},
                                        medicoes_list=[])
                                    set_success_message("Aluno cadastrado com sucesso!")
                                    st.rerun()

                if write_enabled:
                    with st.expander("✏️ Editar Dados da Criança"):
                        with st.form("form_editar_crianca"):
                            edit_nome = st.text_input("Nome completo", value=crianca_sel["nome"])
                            edit_sexo = st.selectbox("Sexo", ["Masculino","Feminino"],
                                                     index=0 if crianca_sel["sexo"]=="M" else 1)
                            try:
                                edit_nasc_default = datetime.strptime(crianca_sel["data_nascimento"], "%Y-%m-%d").date()
                            except:
                                edit_nasc_default = date(2018,1,1)
                            edit_nasc = st.date_input("Data de nascimento", value=edit_nasc_default)
                            edit_comunidade = None
                            if is_imla_group(grupo_sel):
                                edit_comunidade = st.text_input("Comunidade", value=crianca_sel.get("comunidade") or "")
                            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                # 1. Preparar os dados
                                sexo_edit = "M" if edit_sexo == "Masculino" else "F"

                                dados_para_planilha = {
                                    "nome": edit_nome.strip(),
                                    "sexo": sexo_edit,
                                    "nascimento": str(edit_nasc),
                                    "comunidade": edit_comunidade.strip() if edit_comunidade else "",
                                    "turma": turma_sel['nome'],
                                    "data_1": str(st.session_state.get('med_data_0', date.today())),
                                    "peso_1": st.session_state.get('med_peso_0', 0.0),
                                    "alt_1": st.session_state.get('med_alt_0', 0.0),
                                    "data_2": str(st.session_state.get('med_data_1', date.today())),
                                    "peso_2": st.session_state.get('med_peso_1', 0.0),
                                    "alt_2": st.session_state.get('med_alt_1', 0.0),
                                    "data_3": str(st.session_state.get('med_data_2', date.today())),
                                    "peso_3": st.session_state.get('med_peso_2', 0.0),
                                    "alt_3": st.session_state.get('med_alt_2', 0.0),
                                    "data_4": str(st.session_state.get('med_data_3', date.today())),
                                    "peso_4": st.session_state.get('med_peso_3', 0.0),
                                    "alt_4": st.session_state.get('med_alt_3', 0.0),
                                }

                                # Atualiza dados da criança no SQLite
                                sexo_db = "M" if edit_sexo == "Masculino" else "F"
                                conn.execute(
                                    "UPDATE criancas SET nome=?, sexo=?, data_nascimento=?, comunidade=? WHERE id=?",
                                    (edit_nome.strip(), sexo_db, str(edit_nasc),
                                     edit_comunidade.strip() if edit_comunidade else None,
                                     crianca_sel["id"]))
                                conn.commit()
                                # Sincroniza com Google Sheets
                                meds_db = conn.execute(
                                    "SELECT data_medicao, peso, altura FROM medicoes WHERE crianca_id=? AND peso>0 AND altura>0 ORDER BY data_medicao",
                                    (crianca_sel["id"],)).fetchall()
                                sinc_crianca_gsheets(
                                    nome_turma=turma_sel["nome"],
                                    nome_grupo=grupo_sel["nome"],
                                    crianca_dict={"nome": edit_nome.strip(), "sexo": sexo_db,
                                                  "data_nascimento": str(edit_nasc),
                                                  "comunidade": edit_comunidade.strip() if edit_comunidade else ""},
                                    medicoes_list=[dict(m) for m in meds_db])
                                st.success("Alterações salvas com sucesso!")
                                st.rerun()

                # --- EXIBIÇÃO DA FICHA ---
                # Estas linhas devem estar alinhadas com o 'if write_enabled' acima
                header_ficha_col, pdf_col = st.columns([4, 1])
                with header_ficha_col:
                    st.markdown(f"## 📋 Ficha: {crianca_sel['nome']}")
                with pdf_col:
                    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                    meds_para_pdf = conn.execute(
                        "SELECT data_medicao, peso, altura FROM medicoes WHERE crianca_id=? AND peso>0 AND altura>0 ORDER BY data_medicao",
                        (crianca_sel["id"],)).fetchall()
                    meds_para_pdf_list = [dict(m) for m in meds_para_pdf]
                    # Monta valid_meds para os gráficos
                    valid_meds_pdf = []
                    for m in meds_para_pdf_list:
                        meses_v = calcular_idade_meses(crianca_sel["data_nascimento"], m["data_medicao"])
                        imc_v = round(m["peso"] / pow(m["altura"] / 100, 2) * 100) / 100
                        valid_meds_pdf.append({"meses": meses_v, "peso": m["peso"], "altura": m["altura"], "imc": imc_v, "data": m["data_medicao"]})
                    try:
                        pdf_bytes = gerar_ficha_pdf(
                            crianca=crianca_sel,
                            grupo_nome=grupo_sel["nome"],
                            turma_nome=turma_sel["nome"],
                            medicoes=meds_para_pdf_list,
                            valid_meds_graficos=valid_meds_pdf if valid_meds_pdf else None
                        )
                        nome_arquivo_pdf = f"ficha_{crianca_sel['nome'].replace(' ', '_').lower()}.pdf"
                        st.download_button(
                            label="📄 Baixar Folder PDF (3 páginas)",
                            data=pdf_bytes,
                            file_name=nome_arquivo_pdf,
                            mime="application/pdf",
                            use_container_width=True,
                            key=f"dl_ficha_pdf_{crianca_sel['id']}"
                        )
                    except Exception as e_pdf:
                        st.caption(f"Erro PDF: {e_pdf}")

                sexo_label = "Masculino" if crianca_sel["sexo"] == "M" else "Feminino"
                ficha_info = (f"**Sexo:** {sexo_label} | **Data de Nascimento:** {format_date_br(crianca_sel['data_nascimento'])} | "
                              f"**Grupo:** {grupo_sel['nome']} | **Turma:** {turma_sel['nome']}")
                
                if is_imla_group(grupo_sel) and crianca_sel.get("comunidade"):
                    ficha_info += f" | **Comunidade:** {crianca_sel['comunidade']}"
                
                st.markdown(ficha_info)
                st.markdown("### 📅 Medições")
                
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
                        updated_meds.append({"id": med_id, "data_medicao": str(data_med), "peso": peso, "altura": altura})
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
                            st.markdown(f'<div style="background:{cor};color:{cor_txt};padding:6px 10px;border-radius:6px;font-weight:bold;font-size:0.82rem;text-align:center;">{status}</div>', unsafe_allow_html=True)
                            if z_val is not None:
                                st.caption(f"Escore-Z: {'+' if z_val >= 0 else ''}{z_val:.2f} DP | Percentil: {formatar_percentil(z_val)}")

                if write_enabled:
                    if st.button("💾 Salvar Medições", use_container_width=True, type="primary"):
                        conn2 = get_db()
                        for med in updated_meds:
                            if med["peso"] > 0 and med["altura"] > 0 and med["data_medicao"]:
                                if med["id"]:
                                    conn2.execute("UPDATE medicoes SET data_medicao=?, peso=?, altura=? WHERE id=?",
                                                  (med["data_medicao"], med["peso"], med["altura"], med["id"]))
                                else:
                                    conn2.execute("INSERT INTO medicoes (crianca_id, data_medicao, peso, altura) VALUES (?,?,?,?)",
                                                  (crianca_sel["id"], med["data_medicao"], med["peso"], med["altura"]))
                        conn2.commit()
                        conn2.close()
                        # Sincroniza medições com Google Sheets
                        meds_validas = [m for m in updated_meds if m["peso"] > 0 and m["altura"] > 0]
                        sinc_crianca_gsheets(
                            nome_turma=turma_sel["nome"],
                            nome_grupo=grupo_sel["nome"],
                            crianca_dict={"nome": crianca_sel["nome"], "sexo": crianca_sel["sexo"],
                                          "data_nascimento": crianca_sel["data_nascimento"],
                                          "comunidade": crianca_sel.get("comunidade", "") or ""},
                            medicoes_list=meds_validas)
                        st.success("Medições salvas com sucesso!")
                        st.rerun()

                valid_meds = []
                all_meds = conn.execute(
                    "SELECT data_medicao, peso, altura FROM medicoes WHERE crianca_id=? AND peso>0 AND altura>0",
                    (crianca_sel["id"],)).fetchall()
                for m in all_meds:
                    meses = calcular_idade_meses(crianca_sel["data_nascimento"], m["data_medicao"])
                    imc = round(m["peso"] / pow(m["altura"] / 100, 2) * 100) / 100
                    valid_meds.append({"meses": meses, "peso": m["peso"], "altura": m["altura"], "imc": imc, "data": m["data_medicao"]})

                if valid_meds and crianca_sel["sexo"]:
                    st.markdown("### 📊 Curvas de Crescimento OMS")
                    graficos = [
                        {"tipo":"peso_idade","titulo":"Peso x Idade","eixo_x":"meses","eixo_y":"peso","label_x":"Idade (meses)","label_y":"Peso (kg)"},
                        {"tipo":"estatura_idade","titulo":"Estatura x Idade","eixo_x":"meses","eixo_y":"altura","label_x":"Idade (meses)","label_y":"Estatura (cm)"},
                        {"tipo":"imc_idade","titulo":"IMC x Idade","eixo_x":"meses","eixo_y":"imc","label_x":"Idade (meses)","label_y":"IMC (kg/m2)"},
                        {"tipo":"peso_estatura","titulo":"Peso x Estatura","eixo_x":"altura","eixo_y":"peso","label_x":"Estatura (cm)","label_y":"Peso (kg)"},
                    ]
                    chart_cols = st.columns(2)
                    pdf_graficos = []
                    for idx, g in enumerate(graficos):
                        ref_check = get_ref(crianca_sel["sexo"], g["tipo"])
                        valid_for_chart = [m for m in valid_meds if (m["altura"] if g["eixo_x"]=="altura" else m["meses"]) > 0]
                        if ref_check and valid_for_chart:
                            with chart_cols[idx % 2]:
                                fig_pdf = render_growth_chart(crianca_sel["sexo"], g["tipo"], valid_meds,
                                    g["titulo"], g["eixo_x"], g["eixo_y"], g["label_x"], g["label_y"])
                                if fig_pdf:
                                    pdf_graficos.append((g["titulo"], g["tipo"], fig_pdf))
                    if pdf_graficos:
                        with st.expander("📄 Baixar graficos em PDF"):
                            for titulo_pdf, tipo_pdf, fig_pdf in pdf_graficos:
                                try:
                                    pdf_bytes = fig_pdf.to_image(format="pdf")
                                    nome_arquivo = titulo_pdf.lower().replace(" ","_").replace("x","por")
                                    st.download_button(label=f"Baixar {titulo_pdf} em PDF", data=pdf_bytes,
                                        file_name=f"curva_{nome_arquivo}.pdf", mime="application/pdf",
                                        use_container_width=True, key=f"download_pdf_{crianca_sel['id']}_{tipo_pdf}")
                                except Exception:
                                    st.info("Para habilitar o download dos graficos em PDF, instale tambem o pacote kaleido: pip install kaleido")
                                    break
                    st.markdown("""
                    <div class="disclaimer">
                        <strong>⚠️ Importante:</strong> As classificações feitas pelo aplicativo utilizam somente dados antropométricos
                        (Peso, Estatura e IMC), não levando em consideração outros parâmetros que são necessários para um diagnóstico
                        nutricional completo, como exames bioquímicos, avaliação dos hábitos alimentares e exames clínicos. Por isso,
                        estes resultados não substituem o diagnóstico individualizado feito por um profissional capacitado e habilitado.
                        Essas informações são para fins de conhecimento e rastreamento do perfil nutricional da instituição.
                    </div>""", unsafe_allow_html=True)

    conn.close()

def home_page():
    user = st.session_state.user
    render_marina_logo(max_width="220px", margin_bottom="8px")
    st.markdown("<div style='text-align:center; font-size:2.2rem; letter-spacing:6px;'>🍎 🥕 🥦 🍓 🍌 🍇 🥥 🥑</div>", unsafe_allow_html=True)
    st.markdown("<h1 style='color:#4A148C; text-align:center; font-size:2.4rem; font-weight:900;'>🍎 NutriMais</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#7B1FA2; text-align:center; font-size:1.05rem;'>Acompanhamento Nutricional de Criancas e Adolescentes</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        role_labels = {"admin":"👑 Administrador","group_admin":"🔧 Administrador de Grupo","group_visitor":"👁 Visitante de Grupo","visitor":"👁 Visitante"}
        st.markdown(f"<div style='text-align:center;'><span style='background:#7B1FA2;color:white;padding:6px 14px;border-radius:20px;font-size:0.85rem;font-weight:bold;'>{role_labels.get(user['role'], user['role'])} | {user['username']}</span></div>", unsafe_allow_html=True)
        st.markdown("")
        st.markdown("### Bem-vinda ao NutriMais!")
        st.markdown("Sistema completo de avaliacao e acompanhamento nutricional com curvas de crescimento da OMS e Ministerio da Saude.")
        if user["role"] not in ("visitor", "group_visitor"):
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
