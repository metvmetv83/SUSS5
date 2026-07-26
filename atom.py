import requests
import re
import json
from bs4 import BeautifulSoup
import time

# ─────────────────────────────────────────────
#  AtomSporTV  –  Canlı Maç + TV Kanalları M3U
# ─────────────────────────────────────────────
START_URL    = "https://url24.link/AtomSporTV"
MATCHES_URL  = "https://teletv5.top/load/matches.php"
LOGO_BASE    = "https://im.mackolik.com/img/logo/buyuk"
OUTPUT_FILE  = "atom_mac.m3u"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
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
    ("bein-sports-2", "BEIN SPORTS 2", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/BeIN_Sports_2_HD.svg/200px-BeIN_Sports_2_HD.svg.png"),
    ("bein-sports-3", "BEIN SPORTS 3", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/BeIN_Sports_3_HD.svg/200px-BeIN_Sports_3_HD.svg.png"),
    ("bein-sports-4", "BEIN SPORTS 4", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/BeIN_Sports_4_HD.svg/200px-BeIN_Sports_4_HD.svg.png"),
    ("s-sport",       "S SPORT", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png"),
    ("s-sport-2",     "S SPORT 2", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png"),
    ("trt-spor",      "TRT SPOR", "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/TRT_Spor_logo.svg/200px-TRT_Spor_logo.svg.png"),
    ("aspor",         "ASPOR", "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/A_Spor_logo.svg/200px-A_Spor_logo.svg.png"),
]

def get_base_domain():
    """Ana domain adresini bulur"""
    try:
        r1 = requests.get(START_URL, headers=headers, allow_redirects=False, timeout=10)
        if 'location' in r1.headers:
            r2 = requests.get(r1.headers['location'], headers=headers, allow_redirects=False, timeout=10)
            if 'location' in r2.headers:
                domain = r2.headers['location'].strip().rstrip('/')
                return domain
    except Exception as e:
        print(f"{RED}Domain bulma hatası: {e}{RESET}")
    return "https://www.atomsportv510.top"

def normalize_logo(src):
    """Logo URL'sini normalize eder"""
    if not src: return ""
    if src.startswith("http"): return src
    if src.startswith("//"): return "https:" + src
    return LOGO_BASE + "/" + src.lstrip("/")

def get_matches():
    """Maç listesini çeker"""
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
        return matches
    except Exception as e:
        print(f"{RED}Maç çekme hatası: {e}{RESET}")
        return []

def get_m3u8_from_cinema(resource_id, base_domain):
    """Cinema sayfasından özel olarak m3u8 URL'sini bulur"""
    try:
        # Cinema sayfasına doğrudan istek at
        cinema_url = "https://streamsport365.com/cinema"
        h = headers.copy()
        h['Referer'] = f"{base_domain}/"
        h['Origin'] = base_domain
        
        print(f"  Cinema isteği: {cinema_url}")
        resp = requests.get(cinema_url, headers=h, timeout=10)
        
        # Yanıtı göster (debug için)
        print(f"  Cinema Status: {resp.status_code}")
        print(f"  Cinema Content-Type: {resp.headers.get('Content-Type', '')}")
        
        # JSON yanıtı kontrol et
        if 'application/json' in resp.headers.get('Content-Type', ''):
            try:
                data = resp.json()
                print(f"  Cinema JSON: {json.dumps(data, indent=2)[:500]}...")
                
                # JSON içinde m3u8 ara
                json_str = json.dumps(data)
                m3u8_patterns = [
                    r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                    r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"source"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"playlist"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                ]
                
                for pattern in m3u8_patterns:
                    matches = re.findall(pattern, json_str, re.IGNORECASE)
                    for match in matches:
                        url = match.replace('\\/', '/').replace('\\', '')
                        if url.startswith('http') and '.m3u8' in url:
                            print(f"  ✓ M3U8 bulundu (JSON): {url[:100]}...")
                            return url
            except Exception as e:
                print(f"  JSON parse hatası: {e}")
        
        # HTML yanıtı
        else:
            # Sayfanın ilk 1000 karakterini göster
            print(f"  Cinema HTML (ilk 500): {resp.text[:500]}...")
            
            # HTML içinde m3u8 ara
            m3u8_patterns = [
                r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                r'"source"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            ]
            
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, resp.text, re.IGNORECASE)
                for match in matches:
                    url = match.replace('\\/', '/').replace('\\', '')
                    if url.startswith('http') and '.m3u8' in url:
                        print(f"  ✓ M3U8 bulundu (HTML): {url[:100]}...")
                        return url
            
            # iframe'leri kontrol et
            iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
            for iframe_url in iframes:
                if iframe_url.startswith('http') and '.m3u8' not in iframe_url:
                    try:
                        print(f"  iframe kontrol: {iframe_url}")
                        iframe_resp = requests.get(iframe_url, headers=h, timeout=5)
                        for pattern in m3u8_patterns:
                            matches = re.findall(pattern, iframe_resp.text, re.IGNORECASE)
                            for match in matches:
                                url = match.replace('\\/', '/').replace('\\', '')
                                if url.startswith('http') and '.m3u8' in url:
                                    print(f"  ✓ M3U8 bulundu (iframe): {url[:100]}...")
                                    return url
                    except:
                        pass
        
        return None
    except Exception as e:
        print(f"  Cinema hatası: {e}")
        return None

def get_m3u8(resource_id, base_domain):
    """Maç veya kanal için m3u8 URL'sini bulur"""
    try:
        # Önce cinema sayfasını dene
        print(f"  Cinema method deneniyor...")
        result = get_m3u8_from_cinema(resource_id, base_domain)
        if result:
            return result
        
        # Ana sayfa URL'si
        page_url = f"{base_domain}/matches?id={resource_id}"
        print(f"  Ana sayfa kontrol: {page_url}")
        
        h = headers.copy()
        h['Referer'] = base_domain + '/'
        
        resp = requests.get(page_url, headers=h, timeout=10)
        content = resp.text
        
        # Ana sayfada m3u8 ara
        m3u8_patterns = [
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"source"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"playlist"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"deismackanal"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        ]
        
        for pattern in m3u8_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match.replace('\\/', '/').replace('\\', '')
                if url.startswith('http') and '.m3u8' in url:
                    print(f"  ✓ M3U8 bulundu (ana sayfa): {url[:100]}...")
                    return url
        
        # iframe'leri kontrol et
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for iframe_url in iframes:
            if iframe_url.startswith('http') and 'cinema' in iframe_url:
                print(f"  iframe cinema: {iframe_url}")
                try:
                    h['Referer'] = page_url
                    iframe_resp = requests.get(iframe_url, headers=h, timeout=5)
                    for pattern in m3u8_patterns:
                        matches = re.findall(pattern, iframe_resp.text, re.IGNORECASE)
                        for match in matches:
                            url = match.replace('\\/', '/').replace('\\', '')
                            if url.startswith('http') and '.m3u8' in url:
                                print(f"  ✓ M3U8 bulundu (iframe): {url[:100]}...")
                                return url
                except:
                    pass
        
        return None
    except Exception as e:
        print(f"{RED}M3U8 bulma hatası ({resource_id}): {e}{RESET}")
        return None

def build_m3u(working_matches, working_channels, base_domain):
    """M3U dosyasını oluşturur"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")

        # Maçları ekle
        for m in working_matches:
            display_name = f"{m['home']} - {m['away']} [{m['time']}]"
            group_title = f"CANLI MAÇLAR - {m['league']}"
            
            f.write(f'#EXTINF:-1 tvg-logo="{m["logo"]}" group-title="{group_title}",{display_name}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}\n')
            f.write(f'#EXTVLCOPT:http-referrer={base_domain}/\n')
            f.write(f"{m['url']}\n\n")

        # TV kanallarını ekle
        for ch in working_channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="TV Kanalları",{ch["name"]}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}\n')
            f.write(f'#EXTVLCOPT:http-referrer={base_domain}/\n')
            f.write(f"{ch['url']}\n\n")

    print(f"\n{GREEN}[✓] {OUTPUT_FILE} başarıyla oluşturuldu.{RESET}")

def main():
    print(f"\n{GREEN}AtomSporTV M3U Oluşturucu Başlatıldı...{RESET}")
    
    # Ana domain'i bul
    base_domain = get_base_domain()
    print(f"Ana Domain: {base_domain}")
    
    # Maçları çek
    matches = get_matches()
    working_matches = []
    
    print(f"\n{YELLOW}Maçlar test ediliyor...{RESET}")
    for m in matches[:3]:  # Sadece ilk 3 maçı test et
        print(f"\nTest: {m['home']} vs {m['away']} (ID: {m['id']})")
        url = get_m3u8(m['id'], base_domain)
        if url:
            m['url'] = url
            working_matches.append(m)
            print(f"  {GREEN}✓{RESET} M3U8 bulundu")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")
    
    # TV kanallarını test et
    tv_items = []
    print(f"\n{YELLOW}Kanallar test ediliyor...{RESET}")
    for cid, name, logo in TV_CHANNELS[:3]:  # Sadece ilk 3 kanalı test et
        print(f"\nTest: {name} (ID: {cid})")
        url = get_m3u8(cid, base_domain)
        if url:
            tv_items.append({'name': name, 'logo': logo, 'url': url})
            print(f"  {GREEN}✓{RESET} M3U8 bulundu")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")

    # M3U dosyasını oluştur
    if working_matches or tv_items:
        build_m3u(working_matches, tv_items, base_domain)
    else:
        print(f"\n{RED}Hiçbir yayın bulunamadı!{RESET}")

if __name__ == "__main__":
    main()
