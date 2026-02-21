import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Analyse Prestations Santé", layout="wide")

# --- LOGIQUE MÉTIER DES PROFESSIONS ---
def assigner_profession(code):
    c = str(code).strip().lower()
    if 'rem' in c: return "Autre"
    if any(x in c for x in ['privé', 'abo', 'thais']) or c.startswith(('73', '25', '15.30')): 
        return "Physiothérapie"
    if any(x in c for x in ['foyer']) or c.startswith(('76', '31', '32')): 
        return "Ergothérapie"
    if c.startswith('1062'): 
        return "Massage"
    return "Autre"

COULEURS_PROF = {"Physiothérapie": "#00CCFF", "Ergothérapie": "#FF9900", "Massage": "#00CC96", "Autre": "#AB63FA"}

st.title("📊 Analyse des revenus mensuels")

uploaded_file = st.file_uploader("📂 Déposer l'export Excel (onglet 'Prestation')", type="xlsx")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, sheet_name='Prestation')
        nom_col_code = df.columns[2]   # C
        nom_col_somme = df.columns[11] # L
        date_cols = [c for c in df.columns if 'Date' in str(c)]
        nom_col_date = date_cols[0] if date_cols else df.columns[0]

        df[nom_col_somme] = pd.to_numeric(df[nom_col_somme], errors='coerce')
        df[nom_col_date] = pd.to_datetime(df[nom_col_date], errors='coerce')
        df = df[df[nom_col_somme] > 0].dropna(subset=[nom_col_date, nom_col_somme])
        df['Profession'] = df[nom_col_code].apply(assigner_profession)

        # --- BARRE LATÉRALE : FILTRES AVANCÉS ---
        st.sidebar.header("⚙️ Filtres")
        
        # 1. Sélection rapide par métier
        st.sidebar.subheader("Sélection par métier")
        professions_dispo = sorted(df['Profession'].unique())
        
        # On crée des checkbox pour chaque métier (activés par défaut)
        metiers_actifs = []
        for p in professions_dispo:
            if st.sidebar.checkbox(p, value=True, key=f"check_{p}"):
                metiers_actifs.append(p)

        # 2. Sélection fine par Code Tarifaire
        st.sidebar.subheader("Codes individuels")
        # On ne propose que les codes appartenant aux métiers cochés ci-dessus
        codes_possibles = df[df['Profession'].isin(metiers_actifs)]
        liste_codes = sorted(codes_possibles[nom_col_code].unique().astype(str))
        
        selection_codes = st.sidebar.multiselect(
            "Codes à afficher :", 
            options=liste_codes, 
            default=liste_codes
        )

        # --- FILTRAGE ET AFFICHAGE ---
        view_mode = st.radio("Affichage du graphique :", ["Profession", "Code tarifaire"], horizontal=True)
        chart_type = st.radio("Style :", ["Barres", "Courbes"], horizontal=True)

        df_filtered = df[df[nom_col_code].astype(str).isin(selection_codes)].copy()

        if not df_filtered.empty:
            df_filtered['Mois'] = df_filtered[nom_col_date].dt.to_period('M').dt.to_timestamp()
            target_col = "Profession" if view_mode == "Profession" else nom_col_code
            df_plot = df_filtered.groupby(['Mois', target_col])[nom_col_somme].sum().reset_index()

            color_map = COULEURS_PROF if view_mode == "Profession" else None
            
            fig = px.bar(df_plot, x='Mois', y=nom_col_somme, color=target_col, barmode='group', 
                         color_discrete_map=color_map, text_auto='.2f') if chart_type == "Barres" \
                  else px.line(df_plot, x='Mois', y=nom_col_somme, color=target_col, markers=True, color_discrete_map=color_map)

            fig.update_xaxes(dtick="M1", tickformat="%b %Y")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📄 Détails des données"):
                st.dataframe(df_plot.sort_values(['Mois', nom_col_somme], ascending=[False, False]))
        else:
            st.warning("Veuillez sélectionner au moins un métier ou un code.")
            
    except Exception as e:
        st.error(f"Erreur d'analyse : {e}")
else:
    st.info("👋 Bonjour ! Glissez votre export Excel pour générer les graphiques.")
