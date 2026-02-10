import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse Prestations", layout="wide")

st.title("📊 Dashboard des Prestations Santé")

uploaded_file = st.file_uploader("Charger l'export Excel", type="xlsx")

if uploaded_file:
    # 1. Lecture de l'onglet 'Prestation'
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')
    
    # --- Identification STRICTE par position ---
    # Colonne C (index 2) : Code
    # Colonne D (index 3) : Nom Prestation
    # Colonne L (index 11) : Somme CHF
    # On cherche la colonne Date par son nom car sa position varie souvent
    
    nom_col_code = df.columns[2]
    nom_col_nom = df.columns[3]
    nom_col_somme = df.columns[11]
    
    date_cols = [c for c in df.columns if 'Date' in str(c)]
    nom_col_date = date_cols[0] if date_cols else df.columns[0]

    # --- Nettoyage des données ---
    # On force la colonne Somme en numérique
    df[nom_col_somme] = pd.to_numeric(df[nom_col_somme], errors='coerce')
    
    # On force la date
    df[nom_col_date] = pd.to_datetime(df[nom_col_date], errors='coerce')
    
    # Filtre : Valeurs > 0 et on vire les lignes vides (NaN)
    df = df[df[nom_col_somme] > 0].dropna(subset=[nom_col_date, nom_col_somme])

    # --- 2. Classification des Professions (Sidebar) ---
    st.sidebar.header("📁 Configuration")
    
    # Création du dictionnaire Code -> Nom pour l'affichage
    df_codes = df[[nom_col_code, nom_col_nom]].drop_duplicates(subset=[nom_col_code])
    mapping_professions = {}
    
    with st.sidebar.expander("Assigner les professions", expanded=True):
        for _, row in df_codes.iterrows():
            c_code = str(row[nom_col_code])
            c_nom = str(row[nom_col_nom])
            
            # Pré-sélection automatique
            default_p = "Autre"
            if c_code.startswith('73'): default_p = "Physiothérapie"
            elif c_code.startswith('76'): default_p = "Ergothérapie"
            elif '1062' in c_code: default_p = "Massage"
            
            prof = st.selectbox(
                f"{c_code} - {c_nom[:30]}...", 
                ["Physiothérapie", "Ergothérapie", "Massage", "Autre"],
                index=["Physiothérapie", "Ergothérapie", "Massage", "Autre"].index(default_p),
                key=f"p_{c_code}"
            )
            mapping_professions[c_code] = prof

    # Appliquer la profession au tableau
    df['Profession'] = df[nom_col_code].astype(str).map(mapping_professions)

    # --- 3. Graphiques ---
    chart_choice = st.sidebar.radio("Type de graphique", ["Barres", "Courbes"])
    view_choice = st.radio("Grouper par :", ["Profession", nom_col_code], horizontal=True)

    # Préparation données mensuelles
    df['Mois'] = df[nom_col_date].dt.to_period('M').dt.to_timestamp()
    df_plot = df.groupby(['Mois', view_choice])[nom_col_somme].sum().reset_index()

    if chart_choice == "Barres":
        fig = px.bar(df_plot, x='Mois', y=nom_col_somme, color=view_choice, barmode='group', text_auto='.2f')
    else:
        fig = px.line(df_plot, x='Mois', y=nom_col_somme, color=view_choice, markers=True)

    fig.update_xaxes(dtick="M1", tickformat="%b %Y")
    st.plotly_chart(fig, use_container_width=True)

    # 4. Tableau de données
    with st.expander("Voir le tableau des résultats"):
        st.dataframe(df_plot)

else:
    st.info("Prêt à analyser ! Glissez votre fichier Excel ici.")
