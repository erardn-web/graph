import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse par Profession", layout="wide")

st.title("📊 Analyse des prestations par Profession")

uploaded_file = st.file_uploader("Charger l'export Excel", type="xlsx")

if uploaded_file:
    # 1. Lecture
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')
    
    # Identification colonnes C (index 2) et L (index 11)
    col_code = df.columns[2]
    col_somme = df.columns[11]
    
    # Nettoyage
    date_cols = [c for c in df.columns if 'Date' in c]
    col_date = date_cols[0] if date_cols else df.columns[0]
    df[col_date] = pd.to_datetime(df[col_date], errors='coerce')
    df[col_somme] = pd.to_numeric(df[col_somme], errors='coerce')
    df = df[df[col_somme] > 0].dropna(subset=[col_date, col_somme])

    # --- 2. CLASSIFICATION DYNAMIQUE ---
    st.sidebar.header("📁 Classification des professions")
    codes_uniques = sorted(df[col_code].unique().astype(str).tolist())
    
    # Dictionnaire pour stocker les correspondances {Code: Profession}
    mapping_professions = {}
    
    with st.sidebar.expander("Assigner les codes aux professions", expanded=False):
        for code in codes_uniques:
            # Valeur par défaut intelligente
            default_val = "Autre"
            if code.startswith('73'): default_val = "Physiothérapie"
            elif code.startswith('76'): default_val = "Ergothérapie"
            elif code == '1062': default_val = "Massage"
            
            prof = st.selectbox(
                f"Code {code} :",
                options=["Physiothérapie", "Ergothérapie", "Massage", "Autre"],
                index=["Physiothérapie", "Ergothérapie", "Massage", "Autre"].index(default_val),
                key=f"code_{code}"
            )
            mapping_professions[code] = prof

    # Application du mapping au DataFrame
    df['Profession'] = df[col_code].astype(str).map(mapping_professions)

    # --- 3. AFFICHAGE ---
    mode_affichage = st.radio("Afficher par :", ["Profession", "Code tarifaire"], horizontal=True)
    chart_type = st.sidebar.radio("Type de graphique :", ("Barres", "Courbes"))

    # Préparation des données mensuelles
    df['Mois'] = df[col_date].dt.to_period('M').dt.to_timestamp()
    df_monthly = df.groupby(['Mois', mode_affichage])[col_somme].sum().reset_index()

    # Graphique
    if chart_type == "Barres":
        fig = px.bar(df_monthly, x='Mois', y=col_somme, color=mode_affichage, barmode='group')
    else:
        fig = px.line(df_monthly, x='Mois', y=col_somme, color=mode_affichage, markers=True)

    st.plotly_chart(fig, use_container_width=True)

    # 4. Résumé chiffré
    with st.expander("Détails des totaux par profession"):
        total_prof = df.groupby('Profession')[col_somme].sum().reset_index()
        st.table(total_prof.style.format({col_somme: "{:.2f} CHF"}))

else:
    st.info("Veuillez charger le fichier pour configurer les professions.")
