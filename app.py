import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import altair as alt

# --- CONFIGURATION PAGE WEB ---
st.set_page_config(page_title="Analyseur de Facturation Pro", layout="wide", page_icon="🏥")

# --- CONSTANTES & LOGIQUE MÉTIER ---
MOTS_EXCLUSION = {"BERNOIS", "NEUCHATELOIS", "VALAISANS", "GENEVOIS", "VAUDOIS", "FRIBOURGEOIS"}
COULEURS_PROF = {"Physiothérapie": "#00CCFF", "Ergothérapie": "#FF9900", "Massage": "#00CC96", "Autre": "#AB63FA"}

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

def convertir_date(val):
    if pd.isna(val) or str(val).strip() == "": return pd.NaT
    if isinstance(val, pd.Timestamp): return val
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
if 'analyse_lancee' not in st.session_state:
    st.session_state.analyse_lancee = False

# ==========================================
# 🏠 PAGE D'ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    st.title("🏥 Assistant d'Analyse de Santé")
    st.markdown("---")
    st.write("### Choisissez le module d'analyse souhaité :")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("📊 **MODULE FACTURATION**")
        st.write("Analyse des liquidités, délais de paiement et retards.")
        if st.button("Accéder à la Facturation", use_container_width=True):
            st.session_state.page = "factures"
            st.rerun()
            
    with col2:
        st.success("🩺 **MODULE MÉDECINS**")
        st.write("Performance par médecin, tendances et top prescripteurs.")
        if st.button("Accéder aux Médecins", use_container_width=True):
            st.session_state.page = "medecins"
            st.rerun()

    with col3:
        st.warning("🏷️ **MODULE TARIFS**")
        st.write("Analyse mensuelle par métier (Physio, Ergo, Massage).")
        if st.button("Accéder aux Tarifs", use_container_width=True):
            st.session_state.page = "tarifs"
            st.rerun()

# ==========================================
# 📊 MODULE FACTURES
# ==========================================
elif st.session_state.page == "factures":
    if st.sidebar.button("⬅️ Retour Accueil"):
        st.session_state.page = "accueil"
        st.rerun()

    st.title("📊 Analyse de la Facturation")
    uploaded_file = st.sidebar.file_uploader("Fichier Excel (.xlsx)", type="xlsx", key="fact_file")

    if uploaded_file:
        try:
            df_brut = pd.read_excel(uploaded_file, header=0)
            st.sidebar.header("🔍 Filtres")
            fournisseurs = df_brut.iloc[:, 9].dropna().unique().tolist()
            sel_fournisseurs = st.sidebar.multiselect("Fournisseurs :", options=sorted(fournisseurs), default=fournisseurs)
            lois = df_brut.iloc[:, 4].dropna().unique().tolist()
            sel_lois = st.sidebar.multiselect("Types de Loi :", options=sorted(lois), default=lois)
            
            # Renommage et nettoyage
            df = df_brut[(df_brut.iloc[:, 9].isin(sel_fournisseurs)) & (df_brut.iloc[:, 4].isin(sel_lois))].copy()
            df = df.rename(columns={
                df.columns[2]: "date_facture", df.columns[4]: "loi", df.columns[8]: "assureur", 
                df.columns[9]: "fournisseur", df.columns[12]: "statut", df.columns[13]: "montant", df.columns[15]: "date_paiement"
            })
            
            df["date_facture"] = df["date_facture"].apply(convertir_date)
            df["date_paiement"] = df["date_paiement"].apply(convertir_date)
            df["montant"] = pd.to_numeric(df["montant"], errors="coerce").fillna(0)
            ajd = pd.Timestamp(datetime.today().date())
            
            f_att = df[df["statut"].astype(str).str.lower().str.contains("en attente") & ~df["statut"].astype(str).str.lower().str.contains("annulé")].copy()
            f_att["delai_actuel"] = (ajd - f_att["date_facture"]).dt.days
            
            st.metric("💰 TOTAL BRUT EN ATTENTE", f"{f_att['montant'].sum():,.2f} CHF")

            tab1, tab2, tab3 = st.tabs(["💰 Liquidités", "🕒 Délais Assureurs", "⚠️ Retards"])
            
            p_hist = df[df["date_paiement"].notna()].copy()
            p_hist["delai"] = (p_hist["date_paiement"] - p_hist["date_facture"]).dt.days

            with tab1:
                horizons = [10, 20, 30]
                liq, t = calculer_liquidites_fournisseur(f_att, p_hist, horizons)
                st.table(pd.DataFrame({
                    "Horizon": [f"Sous {h}j" for h in horizons],
                    "Estimation (CHF)": [f"{round(liq[h]):,}" for h in horizons],
                    "Probabilité": [f"{round(t[h]*100)}%" for h in horizons]
                }))
            
            with tab2:
                stats = p_hist.groupby("assureur")["delai"].agg(['mean', 'median', 'std']).reset_index()
                st.dataframe(stats.sort_values("mean", ascending=False), use_container_width=True)

            with tab3:
                df_att_30 = f_att[f_att["delai_actuel"] > 30]
                st.warning(f"Il y a {len(df_att_30)} factures en retard de plus de 30 jours.")
                st.dataframe(df_att_30[["date_facture", "assureur", "montant", "delai_actuel"]], use_container_width=True)

        except Exception as e: st.error(f"Erreur : {e}")

# ==========================================
# 🩺 MODULE MÉDECINS
# ==========================================
elif st.session_state.page == "medecins":
    st.sidebar.button("⬅️ Retour Accueil", on_click=lambda: st.session_state.update({"page": "accueil"}))
    st.header("👨‍⚕️ Performance Médecins")
    uploaded_file = st.sidebar.file_uploader("Fichier Excel (.xlsx)", type="xlsx", key="med_up")

    if uploaded_file:
        try:
            df_brut = pd.read_excel(uploaded_file, header=0)
            
            # Moteur de fusion
            def moteur_fusion_securise(df):
                noms_originaux = df.iloc[:, 7].dropna().unique()
                mapping = {}
                def extraire_mots(texte):
                    mots = "".join(c if c.isalnum() else " " for c in str(texte)).upper().split()
                    return {m for m in mots if len(m) > 2}
                noms_tries = sorted(noms_originaux, key=len, reverse=True)
                for i, nom_long in enumerate(noms_tries):
                    mots_long = extraire_mots(nom_long)
                    for nom_court in noms_tries[i+1:]:
                        mots_court = extraire_mots(nom_court)
                        conflit = any(m in mots_long.symmetric_difference(mots_court) for m in MOTS_EXCLUSION)
                        if len(mots_long.intersection(mots_court)) >= 2 and not conflit:
                            mapping[nom_court] = nom_long
                return mapping

            df_m = df_brut.copy()
            mapping = moteur_fusion_securise(df_m)
            df_m.iloc[:, 7] = df_m.iloc[:, 7].replace(mapping)
            
            df_m["medecin"] = df_m.iloc[:, 7]
            df_m["ca"] = pd.to_numeric(df_m.iloc[:, 14], errors="coerce").fillna(0)
            df_m["date_f"] = df_m.iloc[:, 2].apply(convertir_date)
            
            ca_total = df_m.groupby("medecin")["ca"].sum().sort_values(ascending=False).reset_index()
            
            st.subheader("Top Médecins par Chiffre d'Affaires")
            chart = alt.Chart(ca_total.head(15)).mark_bar().encode(
                x=alt.X('ca:Q', title="CA Total (CHF)"),
                y=alt.Y('medecin:N', sort='-x', title="Médecin"),
                color='ca:Q'
            ).properties(height=400)
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(ca_total, use_container_width=True)

        except Exception as e: st.error(f"Erreur technique : {e}")

# ==========================================
# 🏷️ MODULE TARIFS
# ==========================================
elif
