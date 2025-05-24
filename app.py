
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import io

st.title("📊 Simulateur de Tarification pour Nettoyage de Véhicules")

# --- Sidebar ---
with st.sidebar:
    st.header("Paramètres d'entrée")
    ambulifts = st.number_input("Nombre d'Ambulifts", 0, 100, 20)
    navettes = st.number_input("Nombre de Navettes PHMR", 0, 100, 30)
    salaire = st.number_input("Salaire chargé/mois (€)", 2000, 5000, 2800)
    ca_cible = st.number_input("Chiffre d'affaire cible/mois (€)", 1000, 10000, 3800)
    investissement = st.number_input("Investissement total (€)", 0, 50000, 12000)
    amortissement = st.slider("Période d'amortissement (mois)", 1, 36, 12)
    interventions = st.slider("% interventions ponctuelles", 0, 100, 10)
    st.markdown("---")
    st.subheader("Fréquences de nettoyage (par mois)")
    freq_complet = st.number_input("Nettoyages complets par véhicule/mois", 0, 10, 2)
    freq_interieur = st.number_input("Nettoyages intérieurs par véhicule/mois", 0, 10, 4)

# --- Paramètres fixes des durées par type de prestation ---
DUREES = {
    "Ambulift_Complet": 2.0,
    "Ambulift_Intérieur": 1.0,
    "Navette_Complet": 1.5,
    "Navette_Intérieur": 0.75,
    "Ponctuelle": 1.0  # Estimation générique
}

# Correction du double comptage
freq_interieur_seul = max(freq_interieur - freq_complet, 0)

# Génération des listes de véhicules
navettes_list = [f"Nav{i}" for i in range(1, navettes + 1)]
ambulifts_list = [f"Help{i}" for i in range(1, ambulifts + 1)]
vehicules = navettes_list + ambulifts_list

# --- Génération des prestations à planifier ---
def generer_prestations(navettes_list, ambulifts_list, freq_complet, freq_interieur_seul, months):
    prestations = []
    # Navettes
    for v in navettes_list:
        for _ in range(freq_complet * months):
            prestations.append({"Véhicule": v, "Type": "Complet", "Durée": DUREES["Navette_Complet"]})
        for _ in range(freq_interieur_seul * months):
            prestations.append({"Véhicule": v, "Type": "Intérieur seul", "Durée": DUREES["Navette_Intérieur"]})
    # Ambulifts
    for v in ambulifts_list:
        for _ in range(freq_complet * months):
            prestations.append({"Véhicule": v, "Type": "Complet", "Durée": DUREES["Ambulift_Complet"]})
        for _ in range(freq_interieur_seul * months):
            prestations.append({"Véhicule": v, "Type": "Intérieur seul", "Durée": DUREES["Ambulift_Intérieur"]})
    # Interventions ponctuelles
    total_vehicules = len(navettes_list) + len(ambulifts_list)
    nb_ponctuelles = int(total_vehicules * interventions / 100) * months
    for i in range(nb_ponctuelles):
        if total_vehicules > 0:
            v = vehicules[i % total_vehicules]
            prestations.append({"Véhicule": v, "Type": "Ponctuelle", "Durée": DUREES["Ponctuelle"]})
    return prestations

# --- Génération du planning réaliste pour un seul agent ---
def generer_planning_un_agent(prestations, start_date, heures_jour=7, jours_semaine=5):
    jours_ouvres = []
    current_date = start_date
    # Générer les jours ouvrés à l'infini jusqu'à ce que toutes les prestations soient placées
    while len(jours_ouvres) < 1000:  # Limite de sécurité
        if current_date.weekday() < jours_semaine:
            jours_ouvres.append(current_date)
        current_date += timedelta(days=1)
    planning = []
    jour_idx = 0
    temps_jour = 0
    for p in prestations:
        while jour_idx < len(jours_ouvres):
            if temps_jour + p["Durée"] <= heures_jour:
                planning.append({
                    "Date": jours_ouvres[jour_idx],
                    "Agent": "Agent1",
                    "Véhicule": p["Véhicule"],
                    "Type": p["Type"]
                })
                temps_jour += p["Durée"]
                break
            else:
                jour_idx += 1
                temps_jour = 0
    # Calcul de la période couverte
    if planning:
        date_debut = planning[0]["Date"]
        date_fin = planning[-1]["Date"]
        nb_jours = (date_fin - date_debut).days + 1
    else:
        date_debut = date_fin = None
        nb_jours = 0
    return planning, date_debut, date_fin, nb_jours

# --- Génération du planning et du calendrier ---
start_date = datetime(2025, 5, 26)
months = 3
prestations = generer_prestations(navettes_list, ambulifts_list, freq_complet, freq_interieur_seul, months)
planning, date_debut, date_fin, nb_jours = generer_planning_un_agent(prestations, start_date)

df_cal = pd.DataFrame(planning)
if not df_cal.empty:
    df_cal = df_cal.sort_values(["Date", "Agent", "Véhicule", "Type"])
    df_cal["Date"] = pd.to_datetime(df_cal["Date"]).dt.strftime("%d/%m/%Y")
    st.dataframe(df_cal.head(30))  # aperçu

    # --- Export Excel ---
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_cal.to_excel(writer, sheet_name="Planning", index=False)
        writer.close()
    st.download_button(
        label="📥 Télécharger le planning complet (Excel)",
        data=buffer.getvalue(),
        file_name="planning_interventions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.success(f"Période nécessaire pour réaliser toutes les prestations : du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')} ({nb_jours} jours calendaires).")
else:
    st.warning("Aucune prestation à planifier avec les paramètres actuels.")

# --- Affichage des coûts et tarifs ---
st.subheader("📈 Résultats de la simulation")
amortissement_mensuel = investissement / amortissement
cout_total = salaire + amortissement_mensuel
fig, ax = plt.subplots(figsize=(4, 2.5))
ax.pie([salaire, amortissement_mensuel],
       labels=[f'Salaire ({salaire}€)', f'Amortissement ({amortissement_mensuel:.0f}€)'],
       autopct='%1.1f%%')
st.pyplot(fig)

total_prestations = len(prestations)
tarif_base = (cout_total + ca_cible) / total_prestations if total_prestations else 0

df_tarif = pd.DataFrame({
    'Type prestation': [
        'Nettoyage complet ambulift',
        'Nettoyage intérieur ambulift',
        'Nettoyage complet navette',
        'Nettoyage intérieur navette',
        'Intervention ponctuelle'
    ],
    'Tarif (€)': [
        tarif_base * 1.2,
        tarif_base * 0.8,
        tarif_base * 1.2,
        tarif_base * 0.8,
        tarif_base * 1.5
    ]
})
st.dataframe(df_tarif.style.format({'Tarif (€)': '{:.2f} €'}))

st.write(f"**Prix moyen conseillé par prestation:** {tarif_base:.2f} €")
st.write(f"**Marge de sécurité:** {ca_cible - cout_total:.2f} €")
