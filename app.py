import json
import os
from datetime import date, datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

STORAGE_FILE = "nutrimais_criancas.json"
MINISTRY_REFERENCE = "Classificação final cruzando curvas OMS/WHO e tabelas de percentis/escore-z do Ministério da Saúde."

st.set_page_config(page_title="NutriMais", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #fbfaf7; }
    .main-title { color: #169c8f; font-weight: 800; margin-bottom: 0; }
    .subtitle { color: #5f6f73; margin-top: 0; }
    .status-box { padding: 10px; border-radius: 8px; text-align: center; font-weight: 700; color: white; font-size: 0.85rem; margin-top: 8px; }
    .status-current { padding: 16px; border-radius: 12px; text-align: center; font-weight: 800; color: white; font-size: 1rem; margin-bottom: 16px; }
    .small-note { color: #68777b; font-size: 0.82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def round_value(value, decimals=1):
    return round(float(value), decimals)


def interpolate(points, x):
    x = float(x)
    if x <= points[0][0]:
        return points[0][1]
    for i in range(1, len(points)):
        x2, y2 = points[i]
        x1, y1 = points[i - 1]
        if x <= x2:
            ratio = (x - x1) / (x2 - x1)
            return y1 + ratio * (y2 - y1)
    return points[-1][1]


def age_label(age_months):
    age_months = int(round(age_months))
    years = age_months // 12
    months = age_months % 12
    if years == 0:
        return f"{months} {'mês' if months == 1 else 'meses'}"
    if months == 0:
        return f"{years} {'ano' if years == 1 else 'anos'}"
    return f"{years} {'ano' if years == 1 else 'anos'} e {months} {'mês' if months == 1 else 'meses'}"


def calculate_age_months(birth_date, measurement_date):
    try:
        diff = measurement_date - birth_date
        if diff.days < 0:
            return 0
        return round(diff.days / 30.44, 1)
    except Exception:
        return 0


def height_median(sex, age_months):
    male = [
        (0, 49.9), (3, 61.4), (6, 67.6), (12, 75.7), (24, 87.8),
        (36, 96.1), (48, 103.3), (60, 110), (84, 123.5), (108, 135.5),
        (120, 140.3), (132, 145.2), (144, 150.7), (156, 157.4),
        (168, 164.3), (180, 169), (192, 171.8), (204, 173.5),
        (216, 174.5), (228, 175.2),
    ]
    female = [
        (0, 49.1), (3, 59.8), (6, 65.7), (12, 74), (24, 86.4),
        (36, 95.1), (48, 102.7), (60, 109.4), (84, 122.7), (108, 134.3),
        (120, 140.3), (132, 146.7), (144, 152.6), (156, 157.1),
        (168, 159.3), (180, 160.4), (192, 161), (204, 161.3),
        (216, 161.5), (228, 161.7),
    ]
    return interpolate(male if sex == "Masculino" else female, age_months)


def height_sd(age_months):
    return round_value(min(7.5, 1.85 + age_months * 0.028), 2)


def bmi_median(sex, age_months):
    male = [
        (0, 13.4), (6, 17.3), (12, 17.2), (24, 16.4), (60, 15.3),
        (84, 15.7), (120, 17.1), (144, 18.5), (168, 19.8),
        (192, 20.9), (228, 22.2),
    ]
    female = [
        (0, 13.2), (6, 16.9), (12, 16.8), (24, 16), (60, 15.2),
        (84, 15.8), (120, 17.4), (144, 19.1), (168, 20.3),
        (192, 21.1), (228, 22),
    ]
    return interpolate(male if sex == "Masculino" else female, age_months)


def bmi_sd(age_months):
    return round_value(min(3.6, 1.05 + age_months * 0.009), 2)


def weight_median(sex, age_months):
    height_m = height_median(sex, age_months) / 100
    return bmi_median(sex, age_months) * height_m * height_m


def weight_sd(sex, age_months):
    return round_value(max(0.45, weight_median(sex, age_months) * (0.115 if age_months <= 60 else 0.135)), 2)


def weight_for_height_median(sex, height_cm):
    base_bmi = 15.65 if sex == "Masculino" else 15.45
    adjusted_bmi = base_bmi + max(0, height_cm - 65) * 0.018 + max(0, 65 - height_cm) * 0.035
    height_m = height_cm / 100
    return adjusted_bmi * height_m * height_m


def weight_for_height_sd(sex, height_cm):
    return round_value(max(0.35, weight_for_height_median(sex, height_cm) * 0.12), 2)


def z_score(value, median, sd):
    if sd == 0:
        return 0
    return round_value((value - median) / sd, 2)


def ministry_table_z_score(indicator_key, z, age_months):
    if indicator_key == "peso_estatura" and age_months <= 60 and z > 3 and z <= 3.35:
        return 3
    return z


def classify(indicator_key, z, age_months, available=True):
    if not available:
        if indicator_key == "peso_idade":
            return "Não aplicável pela OMS após 10 anos", "#FF8C00", "O indicador peso x idade é recomendado principalmente até 10 anos; priorize IMC x idade e altura x idade."
        return "Não aplicável para esta faixa", "#FF8C00", "O indicador peso x estatura é usado principalmente em menores de 5 anos; priorize IMC x idade."

    zc = ministry_table_z_score(indicator_key, z, age_months)

    if indicator_key == "altura_idade":
        if zc < -3:
            return "Muito baixa estatura para idade", "#8B0000", f"Resultado abaixo de -3 escore-z. {MINISTRY_REFERENCE}"
        if zc < -2:
            return "Baixa estatura para idade", "#FF4500", f"Resultado entre -3 e -2 escore-z. {MINISTRY_REFERENCE}"
        return "Estatura adequada para idade", "#2E8B57", f"Estatura dentro da faixa esperada. {MINISTRY_REFERENCE}"

    if indicator_key == "peso_idade":
        if zc < -3:
            return "Muito baixo peso para idade", "#8B0000", f"Peso abaixo de -3 escore-z. {MINISTRY_REFERENCE}"
        if zc < -2:
            return "Baixo peso para idade", "#FF4500", f"Peso entre -3 e -2 escore-z. {MINISTRY_REFERENCE}"
        if zc <= 2:
            return "Peso adequado para idade", "#2E8B57", f"Peso dentro da faixa esperada. {MINISTRY_REFERENCE}"
        if zc <= 3:
            return "Peso elevado para idade", "#FF8C00", f"Peso acima de +2 escore-z. {MINISTRY_REFERENCE}"
        return "Peso muito elevado para idade", "#FF0000", f"Peso acima de +3 escore-z. {MINISTRY_REFERENCE}"

    early_childhood = age_months <= 60
    if zc < -3:
        return "Magreza acentuada", "#8B0000", f"Resultado abaixo de -3 escore-z. {MINISTRY_REFERENCE}"
    if zc < -2:
        return "Magreza", "#FF4500", f"Resultado entre -3 e -2 escore-z. {MINISTRY_REFERENCE}"
    if zc <= 1:
        return "Eutrofia", "#2E8B57", f"Resultado dentro da faixa nutricional esperada. {MINISTRY_REFERENCE}"
    if zc <= 2:
        return "Risco de sobrepeso" if early_childhood else "Sobrepeso", "#FFD700", f"Resultado acima de +1 escore-z. {MINISTRY_REFERENCE}"
    if zc <= 3:
        extra = " Classificado como sobrepeso pela conferência com as tabelas do Ministério da Saúde para peso x estatura; o escore-z calculado ficou em zona limítrofe por interpolação." if indicator_key == "peso_estatura" and z > 3 else ""
        return "Sobrepeso" if early_childhood else "Obesidade", "#FF8C00", f"Resultado acima de +2 escore-z.{extra} {MINISTRY_REFERENCE}"
    return "Obesidade" if early_childhood else "Obesidade grave", "#FF0000", f"Resultado acima de +3 escore-z. {MINISTRY_REFERENCE}"


def build_assessment(name, sex, birth_date, measurement_date, weight_kg, height_cm):
    age_months = calculate_age_months(birth_date, measurement_date)
    bmi = round_value(weight_kg / ((height_cm / 100) ** 2), 2)
    wfa_available = age_months <= 120
    wfh_available = age_months <= 60 and 45 <= height_cm <= 120
    wfa_z = z_score(weight_kg, weight_median(sex, age_months), weight_sd(sex, age_months)) if wfa_available else 0
    hfa_z = z_score(height_cm, height_median(sex, age_months), height_sd(age_months))
    bfa_z = z_score(bmi, bmi_median(sex, age_months), bmi_sd(age_months))
    wfh_z = z_score(weight_kg, weight_for_height_median(sex, height_cm), weight_for_height_sd(sex, height_cm)) if wfh_available else 0
    indicators = [
        {"key": "peso_idade", "label": "Peso x idade", "value": weight_kg, "unit": "kg", "z": wfa_z, "available": wfa_available},
        {"key": "altura_idade", "label": "Altura x idade", "value": height_cm, "unit": "cm", "z": hfa_z, "available": True},
        {"key": "imc_idade", "label": "IMC x idade", "value": bmi, "unit": "kg/m²", "z": bfa_z, "available": True},
        {"key": "peso_estatura", "label": "Peso x estatura", "value": weight_kg, "unit": "kg", "z": wfh_z, "available": wfh_available},
    ]
    for item in indicators:
        classification, color, interpretation = classify(item["key"], item["z"], age_months, item["available"])
        item["classification"] = classification
        item["color"] = color
        item["interpretation"] = interpretation
    return {
        "name": name,
        "sex": sex,
        "age_months": age_months,
        "age_label": age_label(age_months),
        "weight_kg": round_value(weight_kg),
        "height_cm": round_value(height_cm),
        "bmi": bmi,
        "indicators": indicators,
    }


def age_curve(sex, metric, child_age, child_value=None):
    max_age = 120 if metric == "weight" else 228
    start = max(0, child_age - (24 if child_age <= 60 else 60))
    end = min(max_age, child_age + (24 if child_age <= 60 else 60))
    step = 3 if child_age <= 60 else 6
    ages = sorted(set([max(0, int(a)) for a in range(int(start // step) * step, int(end) + step, step)] + [round_value(child_age, 1)]))
    rows = []
    for age in ages:
        if metric == "height":
            median = height_median(sex, age)
            sd = height_sd(age)
        elif metric == "bmi":
            median = bmi_median(sex, age)
            sd = bmi_sd(age)
        else:
            median = weight_median(sex, age)
            sd = weight_sd(sex, age)
        rows.append({"x": age, "z-3": max(0, median - 3 * sd), "z-2": max(0, median - 2 * sd), "z0": median, "z+2": median + 2 * sd, "z+3": median + 3 * sd})
    return pd.DataFrame(rows)


def height_curve(sex, child_height):
    start = max(45, child_height - 20)
    end = min(120, child_height + 20)
    heights = sorted(set([float(h) for h in range(int(start // 2) * 2, int(end) + 2, 2)] + [round_value(child_height, 1)]))
    rows = []
    for height in heights:
        median = weight_for_height_median(sex, height)
        sd = weight_for_height_sd(sex, height)
        rows.append({"x": height, "z-3": max(0, median - 3 * sd), "z-2": max(0, median - 2 * sd), "z0": median, "z+2": median + 2 * sd, "z+3": median + 3 * sd})
    return pd.DataFrame(rows)


def make_chart(title, df, points, y_label, x_label):
    fig = go.Figure()
    lines = [("z+3", "red"), ("z+2", "orange"), ("z0", "green"), ("z-2", "orange"), ("z-3", "red")]
    for col, color in lines:
        fig.add_trace(go.Scatter(x=df["x"], y=df[col], mode="lines", line=dict(color=color, width=2, dash="solid" if col == "z0" else "dot"), name=col))
    for point in points:
        fig.add_trace(go.Scatter(x=[point["x"]], y=[point["y"]], mode="markers+text", text=[point["label"]], textposition="top center", marker=dict(size=11, color=point["color"], line=dict(width=1, color="white")), name=point["label"]))
    fig.update_layout(title=title, height=380, template="plotly_white", showlegend=True, margin=dict(l=20, r=20, t=50, b=30))
    fig.update_xaxes(title=x_label)
    fig.update_yaxes(title=y_label)
    return fig


def load_records():
    if not os.path.exists(STORAGE_FILE):
        return []
    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_records(records):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def parse_date(value):
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return date.today()


if "records" not in st.session_state:
    st.session_state.records = load_records()
if "selected_index" not in st.session_state:
    st.session_state.selected_index = None

st.markdown("<h1 class='main-title'>NutriMais</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Ficha individual de acompanhamento nutricional infantil com curvas OMS/WHO e tabelas do Ministério da Saúde.</p>", unsafe_allow_html=True)
st.divider()

with st.sidebar:
    st.subheader("Crianças cadastradas")
    names = [record.get("name", "Sem nome") for record in st.session_state.records]
    if names:
        selected_name = st.selectbox("Selecionar ficha", ["Nova ficha"] + names)
        st.session_state.selected_index = None if selected_name == "Nova ficha" else names.index(selected_name)
    else:
        st.session_state.selected_index = None
        st.info("Nenhuma ficha salva ainda.")
    if st.button("Salvar banco local"):
        save_records(st.session_state.records)
        st.success("Banco salvo.")

selected_record = st.session_state.records[st.session_state.selected_index] if st.session_state.selected_index is not None else None

if selected_record:
    initial_name = selected_record.get("name", "")
    initial_sex = selected_record.get("sex", "Feminino")
    initial_birth = parse_date(selected_record.get("birth_date"))
    initial_measurements = selected_record.get("measurements", [])
else:
    initial_name = ""
    initial_sex = "Feminino"
    initial_birth = date(date.today().year - 2, date.today().month, min(date.today().day, 28))
    initial_measurements = []

left, right = st.columns([1, 2.2])

with left:
    st.subheader("Ficha da criança")
    name = st.text_input("Nome", value=initial_name)
    sex = st.selectbox("Sexo", ["Feminino", "Masculino"], index=0 if initial_sex == "Feminino" else 1)
    birth_date = st.date_input("Data de nascimento", value=initial_birth)
    measurements = []
    for i in range(4):
        default = initial_measurements[i] if i < len(initial_measurements) else {}
        st.markdown(f"**{i + 1}ª medição**")
        measurement_date = st.date_input("Data da aferição", value=parse_date(default.get("date")), key=f"date_{i}")
        c1, c2 = st.columns(2)
        with c1:
            weight = st.number_input("Peso (kg)", min_value=0.0, max_value=250.0, value=float(default.get("weight_kg", 12.0 if i == 0 else 0.0)), step=0.1, key=f"weight_{i}")
        with c2:
            height = st.number_input("Altura (cm)", min_value=0.0, max_value=220.0, value=float(default.get("height_cm", 86.0 if i == 0 else 0.0)), step=0.1, key=f"height_{i}")
        measurements.append({"date": str(measurement_date), "weight_kg": weight, "height_cm": height})
    generate = st.button("Gerar avaliação", type="primary", use_container_width=True)
    if st.button("Salvar ficha", use_container_width=True):
        record = {"name": name.strip(), "sex": sex, "birth_date": str(birth_date), "measurements": measurements, "updated_at": datetime.now().isoformat()}
        if st.session_state.selected_index is None:
            st.session_state.records.append(record)
        else:
            st.session_state.records[st.session_state.selected_index] = record
        save_records(st.session_state.records)
        st.success("Ficha salva.")

valid_measurements = [m for m in measurements if m["weight_kg"] >= 1.5 and m["height_cm"] >= 45]
assessments = []
if generate and name.strip() and valid_measurements:
    for index, measurement in enumerate(measurements):
        if measurement["weight_kg"] >= 1.5 and measurement["height_cm"] >= 45:
            result = build_assessment(name.strip(), sex, birth_date, parse_date(measurement["date"]), measurement["weight_kg"], measurement["height_cm"])
            result["measurement_index"] = index
            result["measurement_date"] = measurement["date"]
            assessments.append(result)

with right:
    if not assessments:
        st.info("Preencha a ficha e clique em Gerar avaliação para visualizar classificações e gráficos.")
    else:
        current = assessments[-1]
        current_status = next((item for item in current["indicators"] if item["key"] == "peso_estatura" and item["available"]), None) or next((item for item in current["indicators"] if item["key"] == "imc_idade"), None)
        if current_status:
            st.markdown(f"<div class='status-current' style='background-color:{current_status['color']}'>STATUS ATUAL<br>{current_status['classification']}</div>", unsafe_allow_html=True)
        st.subheader(f"Ficha: {current['name']}")
        st.write(f"{current['sex']} • {len(assessments)} medição(ões) avaliada(s)")
        st.write(f"Peso atual: **{current['weight_kg']} kg** • Altura atual: **{current['height_cm']} cm** • IMC atual: **{current['bmi']}**")
        st.caption("Ferramenta de triagem baseada em escore-z, curvas OMS/WHO e tabelas do Ministério da Saúde. Não substitui avaliação clínica por profissional habilitado.")

        cards = st.columns(4)
        for i, indicator in enumerate(current["indicators"]):
            with cards[i]:
                st.metric(indicator["label"], f"z {indicator['z']:+.2f}" if indicator["available"] else "N/A", f"{indicator['value']} {indicator['unit']}")
                st.markdown(f"<div class='status-box' style='background-color:{indicator['color']}'>{indicator['classification']}</div>", unsafe_allow_html=True)
                st.caption(indicator["interpretation"])

        st.subheader("Medições avaliadas")
        cols = st.columns(len(assessments))
        for col, assessment in zip(cols, assessments):
            status = next((item for item in assessment["indicators"] if item["key"] == "peso_estatura" and item["available"]), None) or next((item for item in assessment["indicators"] if item["key"] == "imc_idade"), None)
            with col:
                st.write(f"**{assessment['measurement_index'] + 1}ª medição**")
                st.write(parse_date(assessment["measurement_date"]).strftime("%d/%m/%Y"))
                st.write(f"{assessment['age_label']} • {assessment['weight_kg']} kg • {assessment['height_cm']} cm • IMC {assessment['bmi']}")
                if status:
                    st.markdown(f"<div class='status-box' style='background-color:{status['color']}'>{status['classification']}</div>", unsafe_allow_html=True)

        chart_specs = [
            ("Peso x Idade", "peso_idade", age_curve(sex, "weight", current["age_months"]), "Peso (kg)", "Idade (meses)"),
            ("Altura x Idade", "altura_idade", age_curve(sex, "height", current["age_months"]), "Altura (cm)", "Idade (meses)"),
            ("IMC x Idade", "imc_idade", age_curve(sex, "bmi", current["age_months"]), "IMC", "Idade (meses)"),
            ("Peso x Estatura", "peso_estatura", height_curve(sex, current["height_cm"]), "Peso (kg)", "Altura (cm)"),
        ]
        for chart_title, key, df_curve, y_label, x_label in chart_specs:
            points = []
            for assessment in assessments:
                indicator = next((item for item in assessment["indicators"] if item["key"] == key), None)
                if not indicator or not indicator["available"]:
                    continue
                if key == "peso_estatura":
                    x = assessment["height_cm"]
                    y = assessment["weight_kg"]
                elif key == "peso_idade":
                    x = assessment["age_months"]
                    y = assessment["weight_kg"]
                elif key == "altura_idade":
                    x = assessment["age_months"]
                    y = assessment["height_cm"]
                else:
                    x = assessment["age_months"]
                    y = assessment["bmi"]
                points.append({"x": x, "y": y, "label": f"{assessment['measurement_index'] + 1}ª", "color": indicator["color"]})
            st.plotly_chart(make_chart(chart_title, df_curve, points, y_label, x_label), use_container_width=True)

        report = {
            "crianca": current["name"],
            "sexo": current["sex"],
            "avaliacoes": assessments,
            "referencia": MINISTRY_REFERENCE,
        }
        st.download_button("Baixar relatório JSON", data=json.dumps(report, ensure_ascii=False, indent=2), file_name=f"nutrimais_{current['name'].replace(' ', '_').lower()}.json", mime="application/json")
