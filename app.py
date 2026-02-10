import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse Prestations", layout="wide")

st.title("📊 Analyse des revenus par Code Tarifaire")

uploaded_file = st.file_uploader("Charger l'export Excel (onglet 'Prestation')", type="xlsx")

if uploaded_file:
    # 1. Lecture de l'onglet 'Prestation'
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')

    # --- Identification des colonnes par position ---
    # Colonne C (index 2) = Code tarifaire
    # Colonne L (index 11) = Somme
    col_code = df.columns[2]   
    col_somme = df.columns[11] 
    
    # Recherche de la colonne Date par nom
    date_cols = [c for c in df.columns if 'Date' in c]
    col_date = date_cols[0] if date_cols else df.columns[0]

    # --- Nettoyage des données ---
    # Conversion numérique et suppression des valeurs négatives ou nulles
    df[col_somme] = pd.to_numeric(df[col_somme], errors='coerce')
    df = df[df[col_somme] > 0].dropna(subset=[col_somme])
    
    # Conversion date
    df[col_date] = pd.to_datetime(df[col_date], errors='coerce')
    df = df.dropna(subset=[col_date])

    # 2. Barre latérale : Sélection des Codes
    st.sidebar.header("Paramètres d'affichage")
    
    chart_type = st.sidebar.radio("Type de graphique :", ("Barres", "Courbes"))
    
    # On récupère tous les codes tarifaires uniques
    codes_disponibles = sorted(df[col_code].unique().astype(str).tolist())
    
    selected_codes = st.sidebar.multiselect(
        "Sélectionnez les codes tarifaires :", 
        codes_disponibles, 
        default=codes_disponibles
    )

    # Filtrage selon les codes choisis
    df_filtered = df[df[col_code].astype(str).isin(selected_codes)].copy()

    if not df_filtered.empty:
        # 3. Préparation des données mensuelles (Somme simple)
        df_filtered['Mois'] = df_filtered[col_date].dt.to_period('M').dt.to_timestamp()
        df_monthly = df_filtered.groupby(['Mois', col_code])[col_somme].sum().reset_index()

        # 4. Graphique
        if chart_type == "Barres":
            fig = px.bar(df_monthly, x='Mois', y=col_somme, color=col_code, barmode='group',
                         title="Total mensuel par code tarifaire (CHF)")
        else:
            fig = px.line(df_monthly, x='Mois', y=col_somme, color=col_code, markers=True,
                          title="Tendance mensuelle par code tarifaire (CHF)")

        fig.update_xaxes(dtick="M1", tickformat="%b %Y")
        st.plotly_chart(fig, use_container_width=True)

        # 5. Tableau récapitulatif
        with st.expander("Voir le détail des montants par mois"):
            st.dataframe(df_monthly)
    else:
        st.warning("Veuillez sélectionner au moins un code dans la barre latérale.")

else:
    st.info("👋 En attente du fichier Excel.")
