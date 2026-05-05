import time
import requests as req
from playwright.sync_api import sync_playwright
from config import KEYWORDS, EXCLUDE_KEYWORDS, WTTJ_EMAIL, WTTJ_PASSWORD
from storage.db import insert_job

SESSION_FILE = "wttj_session.json"
MAX_PAGES = 5  # 5 pages x ~20 offres = 100 offres max par keyword

def is_relevant(title: str) -> bool:
    text = title.lower()
    for word in EXCLUDE_KEYWORDS:
        if word.lower() in text:
            return False
    return True

def login(playwright):
    print("  🔐 Connexion à WTTJ...")
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.goto('https://www.welcometothejungle.com/fr/authenticate/signin', wait_until='networkidle', timeout=30000)
    time.sleep(2)

    try:
        page.click('button:has-text("OK pour moi")', timeout=5000)
        time.sleep(1)
    except Exception:
        pass

    page.fill('input[name="session.email"]', WTTJ_EMAIL)
    page.fill('input[name="session.password"]', WTTJ_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_url('**/fr/**', timeout=15000)
    time.sleep(2)

    context.storage_state(path=SESSION_FILE)
    print("  ✅ Session sauvegardée")
    browser.close()

def get_cookies_from_session():
    """Charge les cookies depuis la session sauvegardée."""
    import json
    with open(SESSION_FILE) as f:
        session = json.load(f)
    return {c['name']: c['value'] for c in session.get('cookies', [])}

def fetch_jobs():
    new_count = 0
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'fr-FR,fr;q=0.9',
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        try:
            context = browser.new_context(storage_state=SESSION_FILE)
            print("  ♻️  Session WTTJ chargée")
        except Exception:
            browser.close()
            with sync_playwright() as p2:
                login(p2)
            return fetch_jobs()

        for keyword in KEYWORDS:
            print(f"  🔍 WTTJ — '{keyword}'")

            page = context.new_page()
            query_id = None
            first_page_jobs = []

            def handle_response(response):
                nonlocal query_id
                if '/api/v3/search/jobs' in response.url and 'query_id=' in response.url:
                    try:
                        query_id = response.url.split('query_id=')[-1].split('&')[0]
                        data = response.json()
                        first_page_jobs.extend(data.get('data', []))
                    except Exception:
                        pass

            page.on('response', handle_response)
            page.goto(
                f'https://www.welcometothejungle.com/fr/jobs?query={keyword.replace(" ", "+")}&contract_type=full_time',
                wait_until='networkidle',
                timeout=30000
            )
            time.sleep(4)
            page.close()

            if not query_id:
                print(f"    ↳ Aucun query_id intercepté")
                continue

            # Traite page 1
            all_jobs = list(first_page_jobs)

            # Pagine via API directe pages 2+
            cookies = get_cookies_from_session()
            for page_num in range(2, MAX_PAGES + 1):
                r = req.get(
                    'https://api.welcometothejungle.com/api/v3/search/jobs',
                    headers=headers,
                    cookies=cookies,
                    params={'page': page_num, 'query_id': query_id}
                )
                if r.status_code != 200:
                    break
                data = r.json().get('data', [])
                if not data:
                    break
                all_jobs.extend(data)
                time.sleep(0.5)

            print(f"    📦 {len(all_jobs)} offres trouvées")

            for hit in all_jobs:
                title    = hit.get('name', '')
                org      = hit.get('organization', {})
                company  = org.get('name', 'Inconnu')
                slug     = hit.get('slug', '')
                org_slug = org.get('slug', '')
                offices  = hit.get('offices', [])
                location = offices[0].get('city', '') if offices else ''
                job_url  = f"https://www.welcometothejungle.com/fr/companies/{org_slug}/jobs/{slug}" if slug and org_slug else ''

                if not title or not job_url:
                    continue
                if not is_relevant(title):
                    continue

                is_new = insert_job(
                    title=title,
                    company=company,
                    location=location,
                    contract='CDI',
                    source='wttj',
                    url=job_url,
                    description=hit.get('description', ''),
                )

                if is_new:
                    new_count += 1
                    print(f"    ✅ [{company}] {title} — {location}")

        browser.close()

    print(f"\n🎯 WTTJ : {new_count} nouvelle(s) offre(s) ajoutée(s)")
    return new_count
