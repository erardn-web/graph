import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse Mensuelle Prestations", layout="wide")

st.title("📊 Analyse des revenus mensuels par code")

# 1. Chargement du fichier
uploaded_file = st.file_uploader("Glissez l'export Excel ici", type="xlsx")

if uploaded_file:
    # Lecture de l'onglet 'Prestation'
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')

    # Configuration des colonnes
    # On cible la colonne C (index 2) pour le code et L (index 11) pour la somme
    col_code = "Code tarifaire"
    col_somme = df.columns[11]  # Récupère le nom de la 12ème colonne (L)
    col_date = "Date"           # /!\ À vérifier selon ton fichier

    # Conversion de la date en format datetime
    df[col_date] = pd.to_datetime(df[col_date])

    # 2. Barre latérale : Filtrage par codes
    st.sidebar.header("Filtres")
    codes_disponibles = sorted(df[col_code].unique().tolist())
    selected_codes = st.sidebar.multiselect(
        "Sélectionnez les codes à afficher :", 
        codes_disponibles, 
        default=codes_disponibles
    )

    # Filtrage des données selon la sélection
    df_filtered = df[df[col_code].isin(selected_codes)].copy()

    if not df_filtered.empty:
        # 3. Groupement par mois (Somme simple, pas de cumul)
        # On crée une colonne 'Mois' (ex: 2023-01)
        df_filtered['Mois'] = df_filtered[col_date].dt.to_period('M').dt.to_timestamp()
        
        # Aggrégation : Somme des montants par mois et par code
        df_monthly = df_filtered.groupby(['Mois', col_code])[col_somme].sum().reset_index()

        # 4. Création du graphique dynamique
        # Type 'bar' pour bien visualiser les sommes mensuelles séparées
        fig = px.bar(
            df_monthly, 
            x='Mois', 
            y=col_somme, 
            color=col_code,
            title="Somme mensuelle des prestations (CHF)",
            labels={col_somme: 'Total Mensuel (CHF)', 'Mois': 'Mois de prestation'},
            barmode='group' # 'group' pour comparer les codes côte à côte ou 'relative' pour empiler
        )

        # Ajustement de l'affichage de l'axe X pour voir tous les mois
        fig.update_xaxes(dtick="M1", tickformat="%b %Y")

        st.plotly_chart(fig, use_container_width=True)

        # 5. Tableau récapitulatif
        with st.expander("Voir le tableau des sommes par mois"):
            st.dataframe(df_monthly.pivot(index='Mois', columns=col_code, values=col_somme).fillna(0))

    else:
        st.warning("Aucun code sélectionné.")

else:
    st.info("Veuillez charger un fichier Excel pour générer les graphiques.")
