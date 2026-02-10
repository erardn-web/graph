import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse par Profession", layout="wide")

st.title("📊 Analyse des prestations par Profession")

uploaded_file = st.file_uploader("Charger l'export Excel", type="xlsx")

if uploaded_file:
    # 1. Lecture de l'onglet 'Prestation'
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')
    
    # Identification des colonnes par index
    col_code = df.columns   # Colonne C
    col_nom = df.columns    # Colonne D (Le nom de la prestation)
    col_somme = df.columns # Colonne L
    
    # Recherche de la colonne Date
    date_cols = [c for c in df.columns if 'Date' in c]
    col_date = date_cols if date_cols else df.columns

    # Nettoyage global
    df[col_somme] = pd.to_numeric(df[col_somme], errors='coerce')
    df[col_date] = pd.to_datetime(df[col_date], errors='coerce')
    df = df[df[col_somme] > 0].dropna(subset=[col_date, col_somme])

    # --- 2. CRÉATION DU DICTIONNAIRE DES CODES ---
    # On crée une correspondance Code -> Nom pour l'affichage dans la sidebar
    # On prend le premier nom trouvé pour chaque code unique
    dict_noms_codes = df.groupby(col_code)[col_nom].first().to_dict()
    codes_uniques = sorted(dict_noms_codes.keys())

    # --- 3. CLASSIFICATION DYNAMIQUE DANS LA SIDEBAR ---
    st.sidebar.header("📁 Classification des professions")
    mapping_professions = {}
    
    with st.sidebar.expander("Assigner les codes aux professions", expanded=True):
        st.write("Associez chaque code à une catégorie :")
        for code in codes_uniques:
            nom_prestation = dict_noms_codes[code]
            code_str = str(code)
            
            # Aide au classement automatique
            default_val = "Autre"
            if code_str.startswith('73'): default_val = "Physiothérapie"
            elif code_str.startswith('76'): default_val = "Ergothérapie"
            elif '1062' in code_str: default_val = "Massage"
            
            # Affichage : "Code - Nom"
            label = f"**{code_str}** : {nom_prestation}"
            
            prof = st.selectbox(
                label,
                options=["Physiothérapie", "Ergothérapie", "Massage", "Autre"],
                index=["Physiothérapie", "Ergothérapie", "Massage", "Autre"].index(default_val),
                key=f"sel_{code_str}"
            )
            mapping_professions[code_str] = prof

    # Application du mapping au DataFrame
    df['Profession'] = df[col_code].astype(str).map(mapping_professions)

    # --- 4. AFFICHAGE ET GRAPHIQUES ---
    st.divider()
    c1, c2 = st.columns([2, 1])
    with c1:
        mode_affichage = st.radio("Regrouper les données par :", ["Profession", col_code], horizontal=True)
    with c2:
        chart_type = st.radio("Type de graphique :", ("Barres", "Courbes"), horizontal=True)

    # Préparation des données mensuelles
    df['Mois'] = df[col_date].dt.to_period('M').dt.to_timestamp()
    df_monthly = df.groupby(['Mois', mode_affichage])[col_somme].sum().reset_index()

    # Graphique Plotly
    if chart_type == "Barres":
        fig = px.bar(df_monthly, x='Mois', y=col_somme, color=mode_affichage, barmode='group',
                     text_auto='.2f', title=f"Revenus mensuels par {mode_affichage}")
    else:
        fig = px.line(df_monthly, x='Mois', y=col_somme, color=mode_affichage, markers=True,
                      title=f"Évolution mensuelle par {mode_affichage}")

    fig.update_xaxes(dtick="M1", tickformat="%b %Y")
    st.plotly_chart(fig, use_container_width=True)

    # 5. Résumé final
    with st.expander("Tableau récapitulatif des montants"):
        st.dataframe(df_monthly.style.format({col_somme: "{:.2f} CHF"}))

else:
    st.info("👋 Bonjour ! Veuillez charger votre export Excel (onglet 'Prestation') pour générer les graphiques.")
