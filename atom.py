import requests
import re
import json
from bs4 import BeautifulSoup
import urllib.parse

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

def extract_m3u8_from_text(text):
    """Metin içinden m3u8 URL'sini çıkarır"""
    patterns = [
        r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
        r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"source"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"playlist"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"deismackanal"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"video"\s*:\s*"([^"]+\.m3u8[^"]*)"',
        r'"hls"\s*:\s*"([^"]+\.m3u8[^"]*)"',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            url = match.replace('\\/', '/').replace('\\', '')
            if url.startswith('http') and '.m3u8' in url:
                return url
    return None

def get_m3u8(resource_id, base_domain):
    """Maç veya kanal için m3u8 URL'sini bulur"""
    try:
        # Ana sayfa URL'si
        page_url = f"{base_domain}/matches?id={resource_id}"
        print(f"  Kontrol: {page_url}")
        
        h = headers.copy()
        h['Referer'] = base_domain + '/'
        
        # Ana sayfayı çek
        resp = requests.get(page_url, headers=h, timeout=10)
        content = resp.text
        
        # 1. Doğrudan m3u8 URL'lerini ara
        result = extract_m3u8_from_text(content)
        if result:
            print(f"  ✓ Doğrudan M3U8 bulundu")
            return result
        
        # 2. iframe'leri kontrol et
        iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        for iframe_url in iframes:
            if not iframe_url.startswith('http'):
                if iframe_url.startswith('//'):
                    iframe_url = 'https:' + iframe_url
                elif iframe_url.startswith('/'):
                    iframe_url = base_domain + iframe_url
                else:
                    continue
            
            print(f"  iframe: {iframe_url}")
            try:
                h['Referer'] = page_url
                iframe_resp = requests.get(iframe_url, headers=h, timeout=5)
                result = extract_m3u8_from_text(iframe_resp.text)
                if result:
                    print(f"  ✓ iframe'den M3U8 bulundu")
                    return result
            except:
                pass
        
        # 3. Script içindeki URL'leri kontrol et
        scripts = re.findall(r'<script[^>]*>([^<]+)</script>', content, re.IGNORECASE | re.DOTALL)
        for script in scripts:
            # JavaScript içindeki URL'leri bul
            js_urls = re.findall(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', script)
            for url in js_urls:
                if url.startswith('http') and '.m3u8' in url:
                    print(f"  ✓ Script'ten M3U8 bulundu")
                    return url
            
            # JavaScript içindeki fetch/axios çağrıları
            api_calls = re.findall(r'(?:fetch|axios)\s*\(\s*["\']([^"\']+)["\']', script)
            for api_url in api_calls:
                if not api_url.startswith('http'):
                    if api_url.startswith('/'):
                        api_url = base_domain + api_url
                    else:
                        continue
                
                try:
                    h['Referer'] = page_url
                    api_resp = requests.get(api_url, headers=h, timeout=5)
                    result = extract_m3u8_from_text(api_resp.text)
                    if result:
                        print(f"  ✓ API'den M3U8 bulundu")
                        return result
                except:
                    pass
        
        # 4. Cinema sayfasını dene (POST ile)
        cinema_url = "https://streamsport365.com/cinema"
        try:
            # POST isteği ile dene
            post_data = {'id': resource_id}
            h['Referer'] = page_url
            h['Origin'] = base_domain
            h['Content-Type'] = 'application/x-www-form-urlencoded'
            
            print(f"  Cinema POST: {cinema_url}")
            post_resp = requests.post(cinema_url, data=post_data, headers=h, timeout=10)
            
            if post_resp.status_code == 200:
                result = extract_m3u8_from_text(post_resp.text)
                if result:
                    print(f"  ✓ Cinema POST'ten M3U8 bulundu")
                    return result
                
                # JSON yanıtı
                try:
                    data = post_resp.json()
                    json_str = json.dumps(data)
                    result = extract_m3u8_from_text(json_str)
                    if result:
                        print(f"  ✓ Cinema JSON'dan M3U8 bulundu")
                        return result
                except:
                    pass
        except:
            pass
        
        print(f"  ✗ M3U8 bulunamadı")
        return None
        
    except Exception as e:
        print(f"{RED}Hata: {e}{RESET}")
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
    for m in matches[:5]:
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
    for cid, name, logo in TV_CHANNELS:
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
