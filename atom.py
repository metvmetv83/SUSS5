import requests
import re
import json
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#  AtomSporTV  –  Canlı Maç + TV Kanalları M3U
# ─────────────────────────────────────────────
START_URL    = "https://url24.link/AtomSporTV"
MATCHES_URL  = "https://teletv5.top/load/matches.php"
YAYINLINK_URL = "https://teletv5.top/load/yayinlink.php"
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
    except Exception:
        pass
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

def get_m3u8_from_api(resource_id):
    """Yayınlink API'sinden m3u8 URL'sini alır"""
    try:
        api_url = f"{YAYINLINK_URL}?id={resource_id}"
        print(f"  API: {api_url}")
        
        h = headers.copy()
        h['Referer'] = 'https://teletv5.top/'
        
        resp = requests.get(api_url, headers=h, timeout=10)
        
        if resp.status_code != 200:
            print(f"  API Hata Kodu: {resp.status_code}")
            return None
        
        # JSON yanıtını parse et
        try:
            data = resp.json()
            print(f"  API Yanıt: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # deismackanal alanını kontrol et
            if 'deismackanal' in data:
                url = data['deismackanal']
                if url and url.startswith('http') and '.m3u8' in url:
                    # URL'deki kaçış karakterlerini temizle
                    url = url.replace('\\/', '/').replace('\\', '')
                    print(f"  ✓ M3U8 bulundu: {url[:100]}...")
                    return url
                elif url and url.isdigit():
                    # Eğer sayısal bir ID döndüyse, bu maç ID'si olabilir
                    print(f"  ! Sayısal ID döndü: {url} - Bu maç için yayın yok")
                    return None
                else:
                    print(f"  ✗ Geçersiz URL: {url}")
                    return None
            
            # Hata mesajı kontrol et
            if 'error' in data:
                print(f"  ✗ API Hatası: {data['error']}")
                return None
                
        except json.JSONDecodeError:
            print(f"  ✗ JSON parse hatası")
            return None
            
    except Exception as e:
        print(f"  ✗ API Hatası: {e}")
        return None
    
    return None

def get_m3u8(resource_id, base_domain):
    """Maç veya kanal için m3u8 URL'sini bulur"""
    # Önce API'den dene
    result = get_m3u8_from_api(resource_id)
    if result:
        return result
    
    # API çalışmazsa, ana sayfayı kontrol et
    try:
        page_url = f"{base_domain}/matches?id={resource_id}"
        print(f"  Ana sayfa: {page_url}")
        
        h = headers.copy()
        h['Referer'] = base_domain + '/'
        
        resp = requests.get(page_url, headers=h, timeout=10)
        content = resp.text
        
        # Sayfada m3u8 ara
        patterns = [
            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
            r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
            r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                url = match.replace('\\/', '/').replace('\\', '')
                if url.startswith('http') and '.m3u8' in url:
                    print(f"  ✓ Sayfada M3U8 bulundu")
                    return url
    except:
        pass
    
    print(f"  ✗ M3U8 bulunamadı")
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
    
    # TV kanallarını test et (önce)
    tv_items = []
    print(f"\n{YELLOW}TV Kanalları test ediliyor...{RESET}")
    for cid, name, logo in TV_CHANNELS:
        print(f"\nTest: {name} (ID: {cid})")
        url = get_m3u8(cid, base_domain)
        if url:
            tv_items.append({'name': name, 'logo': logo, 'url': url})
            print(f"  {GREEN}✓{RESET} M3U8 bulundu")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")
    
    # Maçları çek ve test et
    matches = get_matches()
    working_matches = []
    
    print(f"\n{YELLOW}Maçlar test ediliyor...{RESET}")
    for m in matches[:10]:  # İlk 10 maçı test et
        print(f"\nTest: {m['home']} vs {m['away']} (ID: {m['id']})")
        url = get_m3u8(m['id'], base_domain)
        if url:
            m['url'] = url
            working_matches.append(m)
            print(f"  {GREEN}✓{RESET} M3U8 bulundu")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")

    # M3U dosyasını oluştur
    if working_matches or tv_items:
        build_m3u(working_matches, tv_items, base_domain)
    else:
        print(f"\n{RED}Hiçbir yayın bulunamadı!{RESET}")
    
    # Özet
    print(f"\n{GREEN}Özet:{RESET}")
    print(f"  Çalışan TV kanalı: {len(tv_items)}/{len(TV_CHANNELS)}")
    print(f"  Çalışan maç: {len(working_matches)}/{len(matches[:10])}")
    print(f"  Toplam: {len(tv_items) + len(working_matches)} yayın")

if __name__ == "__main__":
    main()
