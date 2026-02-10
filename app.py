import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse Prestations Santé", layout="wide")

st.title("📊 Analyse des revenus mensuels")

uploaded_file = st.file_uploader("Charger l'export Excel (onglet 'Prestation')", type="xlsx")

if uploaded_file:
    # 1. Lecture de l'onglet 'Prestation'
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')

    # --- Identification dynamique des colonnes par position ---
    # Colonne C (index 2) = Code tarifaire
    # Colonne L (index 11) = Somme
    # On cherche la colonne Date par son nom car sa position peut varier
    
    col_code = df.columns[2]   # Récupère le nom de la 3ème colonne
    col_somme = df.columns[11] # Récupère le nom de la 12ème colonne (L)
    
    # Sécurité pour la date (on cherche une colonne qui contient 'Date')
    date_cols = [c for c in df.columns if 'Date' in c]
    col_date = date_cols[0] if date_cols else df.columns[0]

    # --- Nettoyage ---
    # Conversion en date
    df[col_date] = pd.to_datetime(df[col_date], errors='coerce')
    df = df.dropna(subset=[col_date]) # Supprime les lignes sans date

    # FILTRE : Uniquement les valeurs strictement positives
    # On s'assure que la colonne est bien numérique
    df[col_somme] = pd.to_numeric(df[col_somme], errors='coerce')
    df = df[df[col_somme] > 0]

    # --- Regroupement par profession ---
    def assigner_profession(code):
        c = str(code)
        if c.startswith('73'): return 'Physio'
        if c.startswith('74'): return 'Ergo'
        if 'massage' in c.lower(): return 'Massage'
        return 'Autre'

    df['Profession'] = df[col_code].apply(assigner_profession)

    # 2. Barre latérale
    st.sidebar.header("Paramètres")
    chart_type = st.sidebar.radio("Type de graphique :", ("Barres", "Courbes"))
    view_mode = st.sidebar.selectbox("Regrouper par :", ("Profession", col_code))
    
    options = sorted(df[view_mode].unique().tolist())
    selection = st.sidebar.multiselect(f"Sélectionner {view_mode} :", options, default=options)

    # Filtrage
    df_filtered = df[df[view_mode].isin(selection)].copy()

    if not df_filtered.empty:
        # 3. Préparation des données mensuelles
        df_filtered['Mois'] = df_filtered[col_date].dt.to_period('M').dt.to_timestamp()
        df_monthly = df_filtered.groupby(['Mois', view_mode])[col_somme].sum().reset_index()

        # 4. Graphique
        if chart_type == "Barres":
            fig = px.bar(df_monthly, x='Mois', y=col_somme, color=view_mode, barmode='group')
        else:
            fig = px.line(df_monthly, x='Mois', y=col_somme, color=view_mode, markers=True)

        fig.update_xaxes(dtick="M1", tickformat="%b %Y")
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Données détaillées"):
            st.dataframe(df_monthly)
    else:
        st.warning("Aucune donnée à afficher.")
