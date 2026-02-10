import streamlit as st
import pandas as pd
import plotly.express as px

# Configuration de l'interface
st.set_page_config(page_title="Analyse Prestations Santé", layout="wide")

# --- LOGIQUE MÉTIER DES PROFESSIONS ---
def assigner_profession(code):
    c = str(code).strip().lower()
    
    # Priorité REM -> Autre
    if 'rem' in c:
        return "Autre"
    
    # Physiothérapie : 73xx, 25xx, 15.30xx / contient "privé", "abo" ou "thais"
    if any(x in c for x in ['privé', 'abo', 'thais']) or c.startswith(('73', '25', '15.30')): 
        return "Physiothérapie"
    
    # Ergothérapie : 76xx, 31xx, 32xx / contient "foyer"
    if any(x in c for x in ['foyer']) or c.startswith(('76', '31', '32')): 
        return "Ergothérapie"
    
    # Massage : 1062xx
    if c.startswith('1062'): 
        return "Massage"
        
    return "Autre"

# Définition des couleurs fixes
COULEURS_PROF = {
    "Physiothérapie": "#00CCFF",
    "Ergothérapie": "#FF9900",
    "Massage": "#00CC96",
    "Autre": "#AB63FA"
}

st.title("📊 Analyse des revenus mensuels")

uploaded_file = st.file_uploader("📂 Déposer l'export Excel (onglet 'Prestation')", type="xlsx")

if uploaded_file:
    try:
        # Lecture de l'onglet spécifique
        df = pd.read_excel(uploaded_file, sheet_name='Prestation')
        
        # Identification des colonnes par index
        col_code = df.columns
        col_somme = df.columns
        
        # Détection de la colonne date
        date_cols = [c for c in df.columns if 'Date' in str(c)]
        col_date = date_cols if date_cols else df.columns

        # --- Nettoyage ---
        df[col_somme] = pd.to_numeric(df[col_somme], errors='coerce')
        df[col_date] = pd.to_datetime(df[col_date], errors='coerce')
        df = df[df[col_somme] > 0].dropna(subset=[col_date, col_somme])

        # Application des règles
        df['Profession'] = df[col_code].apply(assigner_profession)

        # --- Menu Latéral ---
        st.sidebar.header("Options d'affichage")
        chart_type = st.sidebar.radio("Style de graphique :", ["Barres", "Courbes"])
        view_mode = st.radio("Grouper par :", ["Profession", "Code tarifaire"], horizontal=True)
        
        target_col = "Profession" if view_mode == "Profession" else col_code
        
        options = sorted(df[target_col].unique().astype(str))
        selection = st.sidebar.multiselect(f"Sélectionner {view_mode}(s) :", options, default=options)

        df_filtered = df[df[target_col].astype(str).isin(selection)].copy()

        if not df_filtered.empty:
            df_filtered['Mois'] = df_filtered[col_date].dt.to_period('M').dt.to_timestamp()
            df_plot = df_filtered.groupby(['Mois', target_col])[col_somme].sum().reset_index()

            color_map = COULEURS_PROF if view_mode == "Profession" else None
            
            if chart_type == "Barres":
                fig = px.bar(df_plot, x='Mois', y=col_somme, color=target_col, barmode='group', 
                             color_discrete_map=color_map, text_auto='.2f', 
                             title=f"Revenus mensuels par {view_mode}")
            else:
                fig = px.line(df_plot, x='Mois', y=col_somme, color=target_col, markers=True,
                              color_discrete_map=color_map, title=f"Évolution mensuelle par {view_mode}")

            fig.update_xaxes(dtick="M1", tickformat="%b %Y")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📄 Voir le détail des montants par mois"):
                st.dataframe(df_plot.sort_values(['Mois', col_somme], ascending=[False, False]))
        else:
            st.warning("Aucune donnée sélectionnée.")
            
    except Exception as e:
        st.error(f"Erreur d'analyse : {e}")
else:
    st.info("👋 Bonjour ! Glissez votre export Excel pour générer les graphiques.")
