import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse Prestations", layout="wide")

st.title("📊 Analyse des Prestations (Sommes cumulées)")

# 1. Chargement du fichier
uploaded_file = st.file_uploader("Glissez votre export Excel ici", type="xlsx")

if uploaded_file:
    # Lecture de l'onglet spécifique 'Prestation'
    # On suppose que la colonne 'Date' existe pour le cumul mensuel (à adapter si le nom diffère)
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')

    # Nettoyage rapide (ex: renommer la colonne L si nécessaire ou s'assurer des types)
    # Note : Dans pandas, les colonnes sont souvent indexées par leur nom de titre.
    col_code = "Code tarifaire"
    col_somme = df.columns[11]  # La colonne L est la 12ème (index 11)
    col_date = "Date" # <--- Vérifie le nom exact de ta colonne date dans l'Excel

    # Conversion de la date et tri
    df[col_date] = pd.to_datetime(df[col_date])
    df = df.sort_values(col_date)

    # 2. Barre latérale pour le filtrage interactif
    st.sidebar.header("Options d'affichage")
    
    codes_disponibles = df[col_code].unique().tolist()
    selected_codes = st.sidebar.multiselect(
        "Sélectionnez les codes tarifaires :", 
        codes_disponibles, 
        default=codes_disponibles[:3] # Par défaut on en affiche quelques-uns
    )

    # Filtrage des données
    df_filtered = df[df[col_code].isin(selected_codes)].copy()

    if not df_filtered.empty:
        # 3. Calcul du cumul mensuel
        # On crée une colonne 'Mois' pour grouper
        df_filtered['Mois'] = df_filtered[col_date].dt.to_period('M').dt.to_timestamp()
        
        # Groupe par mois et par code, puis somme
        df_monthly = df_filtered.groupby(['Mois', col_code])[col_somme].sum().reset_index()
        
        # Calcul de la somme cumulée par code
        df_monthly['Cumul'] = df_monthly.groupby(col_code)[col_somme].cumsum()

        # 4. Affichage du graphique
        fig = px.line(
            df_monthly, 
            x='Mois', 
            y='Cumul', 
            color=col_code,
            title="Évolution du chiffre d'affaires cumulé par code",
            labels={'Cumul': 'Somme cumulée (CHF)', 'Mois': 'Temps'},
            markers=True
        )

        st.plotly_chart(fig, use_container_width=True)

        # Affichage du tableau récapitulatif
        with st.expander("Détails des données calculées"):
            st.dataframe(df_monthly)
    else:
        st.warning("Veuillez sélectionner au moins un code tarifaire.")

else:
    st.info("👋 En attente du fichier Excel pour analyse.")
