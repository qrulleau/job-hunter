import requests
from config import (
    FRANCE_TRAVAIL_CLIENT_ID,
    FRANCE_TRAVAIL_CLIENT_SECRET,
    KEYWORDS,
    EXCLUDE_KEYWORDS,
    CONTRACT_TYPE,
)
from storage.db import insert_job

AUTH_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

def get_token():
    response = requests.post(AUTH_URL, data={
        "grant_type":    "client_credentials",
        "client_id":     FRANCE_TRAVAIL_CLIENT_ID,
        "client_secret": FRANCE_TRAVAIL_CLIENT_SECRET,
        "scope":         "api_offresdemploiv2 o2dsoffre",
    }, params={"realm": "/partenaire"})
    response.raise_for_status()
    return response.json()["access_token"]

def is_relevant(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    for word in EXCLUDE_KEYWORDS:
        if word.lower() in text:
            return False
    return True

def fetch_jobs():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    new_count = 0

    for keyword in KEYWORDS:
        params = {
            "motsCles":   keyword,
            "typeContrat": CONTRACT_TYPE,
            "range":      "0-49",  # 50 résultats max par requête
        }

        response = requests.get(SEARCH_URL, headers=headers, params=params)

        if response.status_code == 204:
            print(f"  ↳ '{keyword}' : aucun résultat")
            continue

        response.raise_for_status()
        data = response.json()
        offres = data.get("resultats", [])

        for offre in offres:
            title       = offre.get("intitule", "")
            company     = offre.get("entreprise", {}).get("nom", "Inconnu")
            location    = offre.get("lieuTravail", {}).get("libelle", "")
            contract    = offre.get("typeContratLibelle", CONTRACT_TYPE)
            url         = offre.get("origineOffre", {}).get("urlOrigine", "")
            description = offre.get("description", "")

            if not url:
                url = f"https://candidat.francetravail.fr/offres/recherche/detail/{offre.get('id', '')}"

            if not is_relevant(title, description):
                continue

            is_new = insert_job(
                title=title,
                company=company,
                location=location,
                contract=contract,
                source="france_travail",
                url=url,
                description=description,
            )

            if is_new:
                new_count += 1
                print(f"  ✅ [{company}] {title} — {location}")

    print(f"\n🎯 France Travail : {new_count} nouvelle(s) offre(s) ajoutée(s)")
    return new_count
