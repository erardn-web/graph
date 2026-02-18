import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import altair as alt

# --- CONFIGURATION PAGE WEB ---
st.set_page_config(page_title="Analyseur de Facturation Pro", layout="wide", page_icon="🏥")

# --- LOGIQUE MÉTIER (PROFESSIONS) ---
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

# --- FONCTIONS UTILITAIRES ---
def convertir_date(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    try:
        return pd.to_datetime(str(val).strip(), format="%d.%m.%Y", errors="coerce")
    except:
        return pd.to_datetime(val, errors="coerce")

def calculer_liquidites_fournisseur(f_attente, p_hist, jours_horizons):
    liq = {h: 0.0 for h in jours_horizons}
    taux_glob = {h: 0.0 for h in jours_horizons}
    if p_hist.empty: return liq, taux_glob
    for h in jours_horizons:
        stats_croisees = p_hist.groupby(["assureur", "fournisseur"])["delai"].apply(lambda x: (x <= h).mean()).to_dict()
        stats_fourn = p_hist.groupby("fournisseur")["delai"].apply(lambda x: (x <= h).mean()).to_dict()
        taux_glob[h] = (p_hist["delai"] <= h).mean()
        total_h = 0.0
        for _, row in f_attente.iterrows():
            key = (row["assureur"], row["fournisseur"])
            prob = stats_croisees.get(key, stats_fourn.get(row["fournisseur"], taux_glob[h]))
            total_h += row["montant"] * prob
        liq[h] = total_h
    return liq, taux_glob

# --- INITIALISATION DE L'ÉTAT ---
if 'page' not in st.session_state:
    st.session_state.page = "accueil"

# ==========================================
# 🏠 PAGE D'ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    st.title("🏥 Assistant d'Analyse de Facturation")
    st.markdown("---")
    st.write("### Choisissez le module d'analyse souhaité :")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📊 **MODULE FACTURATION**")
        st.write("Liquidités, délais par assureur et retards.")
        if st.button("Accéder à l'Analyse Facturation", use_container_width=True):
            st.session_state.page = "factures"
            st.rerun()
            
    with col2:
        st.success("🩺 **MODULE MÉDECINS**")
        st.write("Analyse du CA par médecin et tendances de vitalité.")
        if st.button("Accéder à l'Analyse Médecins", use_container_width=True):
            st.session_state.page = "medecins"
            st.rerun()

    with col3:
        st.warning("🏷️ **MODULE TARIFS**")
        st.write("Revenus mensuels par métier et codes prestations.")
        if st.button("Accéder à l'Analyse Tarifs", use_container_width=True):
            st.session_state.page = "tarifs"
            st.rerun()

# ==========================================
# 🏷️ MODULE TARIFS (NOUVEAU)
# ==========================================
elif st.session_state.page == "tarifs":
    if st.sidebar.button("⬅️ Retour Accueil"):
        st.session_state.page = "accueil"
        st.rerun()

    st.title("📊 Analyse des revenus mensuels")
    uploaded_file = st.sidebar.file_uploader("📂 Déposer l'export Excel (onglet 'Prestation')", type="xlsx", key="tarif_up")

    if uploaded_file:
        try:
            # Lecture spécifique de l'onglet 'Prestation'
            df = pd.read_excel(uploaded_file, sheet_name='Prestation')
            
            # Identification des colonnes par index comme dans ton code
            nom_col_code = df.columns[2]   # Colonne C
            nom_col_somme = df.columns[11] # Colonne L
            date_cols = [c for c in df.columns if 'Date' in str(c)]
            nom_col_date = date_cols[0] if date_cols else df.columns[0]

            # Nettoyage
            df[nom_col_somme] = pd.to_numeric(df[nom_col_somme], errors='coerce')
            df[nom_col_date] = pd.to_datetime(df[nom_col_date], errors='coerce')
            df = df[df[nom_col_somme] > 0].dropna(subset=[nom_col_date, nom_col_somme])
            
            # Application de la logique métier
            df['Profession'] = df[nom_col_code].apply(assigner_profession)

            # --- SIDEBAR FILTRES ---
            st.sidebar.header("⚙️ Paramètres")
            inclure_mois_en_cours = st.sidebar.toggle("Inclure le mois en cours", value=True)
            
            if not inclure_mois_en_cours:
                debut_mois_actuel = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                df = df[df[nom_col_date] < debut_mois_actuel]

            st.sidebar.subheader("Sélection par métier")
            professions_dispo = sorted(df['Profession'].unique())
            metiers_actifs = [p for p in professions_dispo if st.sidebar.checkbox(p, value=True, key=f"p_{p}")]

            # Filtrage par métier avant de lister les codes
            df_metier = df[df['Profession'].isin(metiers_actifs)]
            liste_codes = sorted(df_metier[nom_col_code].unique().astype(str))
            selection_codes = st.sidebar.multiselect("Filtrer les codes :", options=liste_codes, default=liste_codes)

            # --- GRAPHIQUE ---
            col_g1, col_g2 = st.columns(2)
            with col_g1: view_mode = st.radio("Grouper par :", ["Profession", "Code tarifaire"], horizontal=True)
            with col_g2: chart_type = st.radio("Style :", ["Barres", "Courbes"], horizontal=True)

            df_filtered = df_metier[df_metier[nom_col_code].astype(str).isin(selection_codes)].copy()

            if not df_filtered.empty:
                df_filtered['Mois'] = df_filtered[nom_col_date].dt.to_period('M').dt.to_timestamp()
                target_col = "Profession" if view_mode == "Profession" else nom_col_code
                df_plot = df_filtered.groupby(['Mois', target_col])[nom_col_somme].sum().reset_index()

                color_map = COULEURS_PROF if view_mode == "Profession" else None
                
                if chart_type == "Barres":
                    fig = px.bar(df_plot, x='Mois', y=nom_col_somme, color=target_col, barmode='group',
                                 color_discrete_map=color_map, text_auto='.2f')
                else:
                    fig = px.line(df_plot, x='Mois', y=nom_col_somme, color=target_col, markers=True, color_discrete_map=color_map)

                fig.update_xaxes(dtick="M1", tickformat="%b %Y")
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("📄 Détails des données"):
                    st.dataframe(df_plot.sort_values(['Mois', nom_col_somme], ascending=[False, False]), use_container_width=True)
            else:
                st.warning("Aucune donnée disponible avec les filtres sélectionnés.")
                
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")

# ==========================================
# 📊 MODULE FACTURES (RESTE INCHANGÉ)
# ==========================================
elif st.session_state.page == "factures":
    # ... (Garder ton code original ici)
    pass

# ==========================================
# 👨‍⚕️ MODULE MÉDECINS (RESTE INCHANGÉ)
# ==========================================
elif st.session_state.page == "medecins":
    # ... (Garder ton code original ici)
    pass
