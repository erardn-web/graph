import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse Prestations Santé", layout="wide")

st.title("📊 Analyse des revenus mensuels")

# 1. Chargement du fichier
uploaded_file = st.file_uploader("Charger l'export Excel (onglet 'Prestation')", type="xlsx")

if uploaded_file:
    # Lecture de l'onglet spécifique
    df = pd.read_excel(uploaded_file, sheet_name='Prestation')

    # --- Configuration et Nettoyage ---
    col_code = "Code tarifaire"
    col_somme = "Somme" 
    col_date = "Date"
    
    # Conversion en date
    df[col_date] = pd.to_datetime(df[col_date])

    # FILTRE : Suppression des valeurs négatives ou nulles
    df = df[df[col_somme] > 0]

    # --- Logique de regroupement par profession ---
    # Ici, tu peux adapter les codes selon ta nomenclature réelle
    def assigner_profession(code):
        code_str = str(code)
        if code_str.startswith('73'): return 'Physio'
        if code_str.startswith('74'): return 'Ergo'
        if 'massage' in code_str.lower(): return 'Massage'
        return 'Autre'

    df['Profession'] = df[col_code].apply(assigner_profession)

    # 2. Barre latérale : Filtres et Options
    st.sidebar.header("Paramètres d'affichage")
    
    chart_type = st.sidebar.radio("Type de graphique :", ("Barres", "Courbes"))
    
    # Choix de la vue : par Code ou par Profession
    view_mode = st.sidebar.selectbox("Regrouper par :", ("Code tarifaire", "Profession"))
    
    # Filtres dynamiques selon le mode choisi
    options_disponibles = sorted(df[view_mode].unique().tolist())
    selection = st.sidebar.multiselect(f"Sélectionner les {view_mode}s :", options_disponibles, default=options_disponibles)

    # Filtrage final
    df_filtered = df[df[view_mode].isin(selection)].copy()

    if not df_filtered.empty:
        # 3. Préparation des données mensuelles
        df_filtered['Mois'] = df_filtered[col_date].dt.to_period('M').dt.to_timestamp()
        df_monthly = df_filtered.groupby(['Mois', view_mode])[col_somme].sum().reset_index()

        # 4. Construction du graphique
        title_graph = f"Somme mensuelle par {view_mode} (Valeurs positives uniquement)"
        
        if chart_type == "Barres":
            fig = px.bar(df_monthly, x='Mois', y=col_somme, color=view_mode, barmode='group',
                         title=title_graph, labels={col_somme: 'Total (CHF)'})
        else:
            fig = px.line(df_monthly, x='Mois', y=col_somme, color=view_mode, markers=True,
                          title=title_graph, labels={col_somme: 'Total (CHF)'})

        fig.update_xaxes(dtick="M1", tickformat="%b %Y")
        st.plotly_chart(fig, use_container_width=True)

        # 5. Tableau récapitulatif
        with st.expander("Consulter le tableau des données"):
            st.dataframe(df_monthly)
    else:
        st.warning("Aucune donnée à afficher avec les filtres actuels.")
else:
    st.info("👋 Veuillez charger votre fichier Excel pour commencer.")
