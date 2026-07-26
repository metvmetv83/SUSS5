import requests
import re
from bs4 import BeautifulSoup

START_URL    = "https://url24.link/AtomSporTV"
MATCHES_URL  = "https://teletv5.top/load/matches.php"
LOGO_BASE    = "https://im.mackolik.com/img/logo/buyuk"
OUTPUT_FILE  = "atom_mac.m3u"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RESET  = "\033[0m"

headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'tr-TR,tr;q=0.8',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://url24.link/'
}

TV_CHANNELS = [
    ("bein-sports-1", "BEIN SPORTS 1", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/BeIN_Sports_1_HD.svg/200px-BeIN_Sports_1_HD.svg.png"),
]

def get_base_domain():
    try:
        r1 = requests.get(START_URL, headers=headers, allow_redirects=False, timeout=10)
        if 'location' in r1.headers:
            r2 = requests.get(r1.headers['location'], headers=headers, allow_redirects=False, timeout=10)
            if 'location' in r2.headers:
                return r2.headers['location'].strip().rstrip('/')
    except Exception:
        pass
    return "https://www.atomsportv510.top"

def normalize_logo(src):
    if not src: return ""
    if src.startswith("http"): return src
    if src.startswith("//"): return "https:" + src
    return LOGO_BASE + "/" + src.lstrip("/")

def get_matches():
    print(f"Maçlar çekiliyor → {MATCHES_URL}")
    try:
        resp = requests.get(MATCHES_URL, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        matches = []
        skip_words = {'futbol', 'futbol tr', 'futboi', 'günün maçı'}

        for a in soup.find_all('a', href=True):
            href = a['href']
            mid = re.search(r'matches\?id=([a-f0-9]+)', href)
            if not mid: continue
            match_id = mid.group(1)

            imgs = a.find_all('img')
            home_logo = normalize_logo(imgs[0]['src']) if len(imgs) >= 1 else ""
            away_logo = normalize_logo(imgs[1]['src']) if len(imgs) >= 2 else ""
            
            lines = [l.strip() for l in a.get_text('\n').splitlines() if l.strip() and l.strip().lower() not in skip_words]
            saat, lig, home_team, away_team = '', '', '', ''
            for line in lines:
                if '|' in line and not saat:
                    parts = line.split('|', 1)
                    saat, lig = parts[0].strip(), parts[1].strip()
                elif saat and not home_team: home_team = line
                elif saat and home_team and not away_team: away_team = line

            matches.append({
                'id': match_id,
                'home': home_team or "Ev Sahibi",
                'away': away_team or "Deplasman",
                'home_logo': home_logo,
                'away_logo': away_logo,
                'logo': home_logo or away_logo,
                'time': saat,
                'league': lig or "Diğer Maçlar"
            })
        return matches[:3] # Test için sadece ilk 3 maçı alalım
    except Exception as e:
        print(f"Hata: {e}")
        return []

def get_m3u8(resource_id, base_domain):
    try:
        h = headers.copy()
        page_url = f"{base_domain}/matches?id={resource_id}"
        h['Referer'] = f"{base_domain}/"
        
        resp = requests.get(page_url, headers=h, timeout=10)
        print(f"\n--- [DEBUG] Sayfa İçeriği ({resource_id}) ---")
        print(resp.text[:500]) # Gelen HTML'in ilk 500 karakterini basar
        print("------------------------------------------\n")
        
        # .m3u8 arama
        mm = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\]*)', resp.text)
        if mm:
            return mm.group(1).replace('\\/', '/').replace('\\', '')
        return None
    except Exception as e: 
        print(f"DEBUG HATA: {e}")
        return None

def main():
    base_domain = get_base_domain()
    print(f"Ana Domain: {base_domain}")
    matches = get_matches()
    for m in matches:
        print(Test ediliyor: {m['home']} vs {m['away']})
        url = get_m3u8(m['id'], base_domain)
        print(Sonuç URL: {url})

if __name__ == "__main__":
    main()
