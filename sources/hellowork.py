import time
import unicodedata
import requests
from bs4 import BeautifulSoup
from config import KEYWORDS, EXCLUDE_KEYWORDS
from storage.db import insert_job

BASE_URL = "https://www.hellowork.com"
HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept-Language': 'fr-FR,fr;q=0.9',
}

def remove_accents(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

def is_relevant(title: str) -> bool:
    text = title.lower()
    for word in EXCLUDE_KEYWORDS:
        if word.lower() in text:
            return False
    return True

def fetch_jobs():
    new_count = 0

    for keyword in KEYWORDS:
        print(f"  🔍 HelloWork — '{keyword}'")
        keyword_encoded = remove_accents(keyword).replace(' ', '+')
        url = f"{BASE_URL}/fr-fr/emploi/recherche.html?k={keyword_encoded}&c=CDI&s=relevance&p=1"

        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()

            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.select('a[href*="/fr-fr/emplois/"]')

            if not cards:
                print(f"    ↳ Aucun résultat")
                continue

            print(f"    📦 {len(cards)} offres trouvées")

            for card in cards:
                try:
                    href = card.get('href', '')
                    job_url = f"{BASE_URL}{href}" if href.startswith('/') else href

                    parent = card.find_parent('li') or card.find_parent('div') or card.parent
                    parent_text = parent.get_text(separator='\n') if parent else card.get_text()

                    lines = [l.strip() for l in parent_text.strip().split('\n') if l.strip()]
                    title    = lines[0] if len(lines) > 0 else ""
                    company  = lines[1] if len(lines) > 1 else "Inconnu"
                    location = lines[2] if len(lines) > 2 else ""

                    if not title or not job_url:
                        continue
                    if not is_relevant(title):
                        continue

                    is_new = insert_job(
                        title=title,
                        company=company,
                        location=location,
                        contract='CDI',
                        source='hellowork',
                        url=job_url,
                        description='',
                    )

                    if is_new:
                        new_count += 1
                        print(f"    ✅ [{company}] {title} — {location}")

                except Exception:
                    continue

        except Exception as e:
            print(f"    ❌ Erreur : {e}")
            continue

        time.sleep(1)

    print(f"\n🎯 HelloWork : {new_count} nouvelle(s) offre(s) ajoutée(s)")
    return new_count
