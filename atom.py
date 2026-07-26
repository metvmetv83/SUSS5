import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime

# ─────────────────────────────────────────────
#  AtomSporTV  –  Canlı Maç + TV Kanalları M3U
# ─────────────────────────────────────────────
START_URL    = "https://url24.link/AtomSporTV"
MATCHES_URL  = "https://teletv5.top/load/matches.php"
YAYINLINK_URL = "https://teletv5.top/load/yayinlink.php"
LOGO_BASE    = "https://im.mackolik.com/img/logo/buyuk"
OUTPUT_FILE  = "atom_mac.m3u"
JSON_FILE    = "atom_yayinlar.json"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

# Base headers
BASE_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'tr-TR,tr;q=0.8',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://url24.link/'
}

TV_CHANNELS = [
    {
        "id": "bein-sports-1",
        "name": "BEIN SPORTS 1",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/BeIN_Sports_1_HD.svg/200px-BeIN_Sports_1_HD.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/BeIN_Sports_1_HD.svg/200px-BeIN_Sports_1_HD.svg.png",
        "title": "BeIN Sports 1"
    },
    {
        "id": "bein-sports-2",
        "name": "BEIN SPORTS 2",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/BeIN_Sports_2_HD.svg/200px-BeIN_Sports_2_HD.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/BeIN_Sports_2_HD.svg/200px-BeIN_Sports_2_HD.svg.png",
        "title": "BeIN Sports 2"
    },
    {
        "id": "bein-sports-3",
        "name": "BEIN SPORTS 3",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/BeIN_Sports_3_HD.svg/200px-BeIN_Sports_3_HD.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/BeIN_Sports_3_HD.svg/200px-BeIN_Sports_3_HD.svg.png",
        "title": "BeIN Sports 3"
    },
    {
        "id": "bein-sports-4",
        "name": "BEIN SPORTS 4",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/BeIN_Sports_4_HD.svg/200px-BeIN_Sports_4_HD.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/BeIN_Sports_4_HD.svg/200px-BeIN_Sports_4_HD.svg.png",
        "title": "BeIN Sports 4"
    },
    {
        "id": "s-sport",
        "name": "S SPORT",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png",
        "title": "S Sport"
    },
    {
        "id": "s-sport-2",
        "name": "S SPORT 2",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png",
        "title": "S Sport 2"
    },
    {
        "id": "trt-spor",
        "name": "TRT SPOR",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/TRT_Spor_logo.svg/200px-TRT_Spor_logo.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/TRT_Spor_logo.svg/200px-TRT_Spor_logo.svg.png",
        "title": "TRT Spor"
    },
    {
        "id": "aspor",
        "name": "ASPOR",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/A_Spor_logo.svg/200px-A_Spor_logo.svg.png",
        "thumb_square": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/A_Spor_logo.svg/200px-A_Spor_logo.svg.png",
        "title": "A Spor"
    },
]

def get_base_domain():
    """Ana domain adresini bulur"""
    try:
        # Önce URL24 üzerinden yönlendirmeyi takip et
        r1 = requests.get(START_URL, headers=BASE_HEADERS, allow_redirects=False, timeout=10)
        if 'location' in r1.headers:
            r2 = requests.get(r1.headers['location'], headers=BASE_HEADERS, allow_redirects=False, timeout=10)
            if 'location' in r2.headers:
                domain = r2.headers['location'].strip().rstrip('/')
                # Domain'i temizle
                if domain.startswith('https://'):
                    domain = domain.split('/')[2]  # Sadece domain adını al
                return f"https://{domain}"
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
        resp = requests.get(MATCHES_URL, headers=BASE_HEADERS, timeout=10)
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

def get_m3u8_from_api(resource_id, base_domain):
    """Yayınlink API'sinden m3u8 URL'sini alır"""
    try:
        api_url = f"{YAYINLINK_URL}?id={resource_id}"
        
        h = BASE_HEADERS.copy()
        h['Referer'] = base_domain + '/'
        h['Origin'] = base_domain
        
        resp = requests.get(api_url, headers=h, timeout=10)
        
        if resp.status_code != 200:
            return None, None
        
        try:
            data = resp.json()
            
            if 'deismackanal' in data:
                url = data['deismackanal']
                if url and url.startswith('http') and '.m3u8' in url:
                    url = url.replace('\\/', '/').replace('\\', '')
                    # Header'ları base_domain'e göre oluştur
                    headers_info = {
                        "h1Key": "accept",
                        "h1Val": "*/*",
                        "h2Key": "referer",
                        "h2Val": base_domain + "/",
                        "h3Key": "origin",
                        "h3Val": base_domain,
                        "h4Key": "accept-language",
                        "h4Val": "tr-TR,tr;q=0.8",
                        "h5Key": "user-agent",
                        "h5Val": BASE_HEADERS['User-Agent']
                    }
                    return url, headers_info
                elif url and url.isdigit():
                    return None, None
                else:
                    return None, None
            
            if 'error' in data:
                return None, None
                
        except json.JSONDecodeError:
            return None, None
            
    except Exception:
        return None, None
    
    return None, None

def get_m3u8(resource_id, base_domain):
    """Maç veya kanal için m3u8 URL'sini bulur"""
    # Önce API'den dene
    url, headers_info = get_m3u8_from_api(resource_id, base_domain)
    if url:
        return url, headers_info
    
    # API çalışmazsa, ana sayfayı kontrol et
    try:
        page_url = f"{base_domain}/matches?id={resource_id}"
        
        h = BASE_HEADERS.copy()
        h['Referer'] = base_domain + '/'
        
        resp = requests.get(page_url, headers=h, timeout=10)
        content = resp.text
        
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
                    headers_info = {
                        "h1Key": "accept",
                        "h1Val": "*/*",
                        "h2Key": "referer",
                        "h2Val": base_domain + "/",
                        "h3Key": "origin",
                        "h3Val": base_domain,
                        "h4Key": "accept-language",
                        "h4Val": "tr-TR,tr;q=0.8",
                        "h5Key": "user-agent",
                        "h5Val": BASE_HEADERS['User-Agent']
                    }
                    return url, headers_info
    except:
        pass
    
    return None, None

def build_json_output(tv_items, match_items, base_domain):
    """JSON çıktısı oluşturur"""
    output = {
        "generated_at": datetime.now().isoformat(),
        "base_domain": base_domain,
        "total_streams": len(tv_items) + len(match_items),
        "channels": tv_items,
        "matches": match_items
    }
    
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"{GREEN}[✓] {JSON_FILE} başarıyla oluşturuldu.{RESET}")

def build_m3u(tv_items, match_items, base_domain):
    """M3U dosyasını oluşturur"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")

        # TV kanallarını ekle
        for ch in tv_items:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="TV Kanalları",{ch["name"]}\n')
            # Header'ları ekle
            if ch.get("headers"):
                for key, val in ch["headers"].items():
                    if key.startswith("h") and key.endswith("Key"):
                        num = key[1]
                        val_key = f"h{num}Val"
                        if val_key in ch["headers"]:
                            header_name = ch["headers"][key].lower()
                            header_value = ch["headers"][val_key]
                            f.write(f'#EXTVLCOPT:http-{header_name}={header_value}\n')
            f.write(f"{ch['url']}\n\n")

        # Maçları ekle
        for m in match_items:
            display_name = f"{m['home']} - {m['away']} [{m['time']}]"
            group_title = f"CANLI MAÇLAR - {m['league']}"
            
            f.write(f'#EXTINF:-1 tvg-logo="{m["logo"]}" group-title="{group_title}",{display_name}\n')
            if m.get("headers"):
                for key, val in m["headers"].items():
                    if key.startswith("h") and key.endswith("Key"):
                        num = key[1]
                        val_key = f"h{num}Val"
                        if val_key in m["headers"]:
                            header_name = m["headers"][key].lower()
                            header_value = m["headers"][val_key]
                            f.write(f'#EXTVLCOPT:http-{header_name}={header_value}\n')
            f.write(f"{m['url']}\n\n")

    print(f"\n{GREEN}[✓] {OUTPUT_FILE} başarıyla oluşturuldu.{RESET}")

def main():
    print(f"\n{GREEN}AtomSporTV M3U Oluşturucu Başlatıldı...{RESET}")
    
    # Ana domain'i bul
    base_domain = get_base_domain()
    print(f"Ana Domain: {base_domain}")
    
    # TV kanallarını test et
    tv_items = []
    print(f"\n{YELLOW}TV Kanalları test ediliyor...{RESET}")
    for channel in TV_CHANNELS:
        print(f"\nTest: {channel['name']} (ID: {channel['id']})")
        url, headers_info = get_m3u8(channel['id'], base_domain)
        if url:
            channel_copy = channel.copy()
            channel_copy['url'] = url
            channel_copy['headers'] = headers_info
            channel_copy['playlistURL'] = ""
            channel_copy['media_url'] = url
            tv_items.append(channel_copy)
            print(f"  {GREEN}✓{RESET} M3U8 bulundu: {url[:80]}...")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")
    
    # Maçları çek ve test et
    matches = get_matches()
    match_items = []
    
    print(f"\n{YELLOW}Maçlar test ediliyor...{RESET}")
    for m in matches[:10]:
        print(f"\nTest: {m['home']} vs {m['away']} (ID: {m['id']})")
        url, headers_info = get_m3u8(m['id'], base_domain)
        if url:
            m['url'] = url
            m['headers'] = headers_info
            m['playlistURL'] = ""
            m['media_url'] = url
            match_items.append(m)
            print(f"  {GREEN}✓{RESET} M3U8 bulundu: {url[:80]}...")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")

    # JSON ve M3U dosyalarını oluştur
    if tv_items or match_items:
        build_m3u(tv_items, match_items, base_domain)
        build_json_output(tv_items, match_items, base_domain)
    else:
        print(f"\n{RED}Hiçbir yayın bulunamadı!{RESET}")
    
    # Özet
    print(f"\n{GREEN}Özet:{RESET}")
    print(f"  Çalışan TV kanalı: {len(tv_items)}/{len(TV_CHANNELS)}")
    print(f"  Çalışan maç: {len(match_items)}/{len(matches[:10])}")
    print(f"  Toplam: {len(tv_items) + len(match_items)} yayın")
    print(f"  JSON dosyası: {JSON_FILE}")
    print(f"  M3U dosyası: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
