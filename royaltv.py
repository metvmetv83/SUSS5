import requests
import re
import json
from bs4 import BeautifulSoup
from datetime import datetime
import os

# ─────────────────────────────────────────────
#  RoyalTV  –  Canlı Maç + TV Kanalları M3U
# ─────────────────────────────────────────────
START_URL    = "https://bit.ly/canl%C4%B1tvroyal"
BASE_URL     = "https://royaltv21.com"
OUTPUT_FILE  = "royaltv.m3u"
JSON_FILE    = "royaltv_yayinlar.json"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

if os.environ.get('GITHUB_ACTIONS') == 'true':
    GREEN = YELLOW = RED = RESET = ""

HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'tr-TR,tr;q=0.8',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://royaltv21.com/'
}

def get_base_domain():
    """Ana domain adresini bulur"""
    try:
        r1 = requests.get(START_URL, headers=HEADERS, allow_redirects=True, timeout=10)
        if r1.url:
            return r1.url.rstrip('/')
    except Exception:
        pass
    return BASE_URL

def get_channels_from_page():
    """Sayfadaki kanal bilgilerini çeker"""
    print(f"Kanallar çekiliyor → {BASE_URL}")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        channels = []
        
        # data-event-type="channel" olan linkleri bul
        channel_links = soup.find_all('a', attrs={'data-event-type': 'channel'})
        
        for a in channel_links:
            stream_id = a.get('data-stream', '')
            name = a.get('data-name', '')
            logo = a.get('data-logo', '')
            slug = a.get('data-slug', '')
            
            if stream_id and name:
                # Logo URL'sini düzelt
                if logo and not logo.startswith('http'):
                    if logo.startswith('/'):
                        logo = f"{BASE_URL}{logo}"
                    else:
                        logo = f"{BASE_URL}/{logo}"
                
                channels.append({
                    'id': stream_id,
                    'name': name,
                    'logo': logo,
                    'slug': slug,
                    'title': name
                })
                print(f"  Bulundu: {name} (ID: {stream_id})")
        
        return channels
    except Exception as e:
        print(f"{RED}Kanal çekme hatası: {e}{RESET}")
        return []

def get_matches_from_page():
    """Sayfadaki maç bilgilerini çeker"""
    print(f"Maçlar çekiliyor → {BASE_URL}")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        matches = []
        
        # Maç linklerini bul (data-event-type="event" veya benzeri)
        event_links = soup.find_all('a', attrs={'data-event-type': 'event'})
        
        if not event_links:
            # Alternatif: class içeren linkleri dene
            event_links = soup.find_all('a', href=True)
            event_links = [a for a in event_links if '/event/' in a.get('href', '') or '/match/' in a.get('href', '')]
        
        for a in event_links:
            href = a.get('href', '')
            match_id = re.search(r'/(?:event|match)/(\d+)', href)
            if match_id:
                match_id = match_id.group(1)
                title = a.get_text(strip=True)
                if title and len(title) > 3:
                    # Takım isimlerini ayırmaya çalış
                    home = title
                    away = ""
                    if ' - ' in title:
                        parts = title.split(' - ', 1)
                        home, away = parts[0], parts[1]
                    elif ' vs ' in title:
                        parts = title.split(' vs ', 1)
                        home, away = parts[0], parts[1]
                    
                    matches.append({
                        'id': match_id,
                        'title': title,
                        'home': home,
                        'away': away,
                        'logo': "",
                        'time': "",
                        'league': "RoyalTV Maçları"
                    })
                    print(f"  Bulundu: {title} (ID: {match_id})")
        
        return matches[:30]  # İlk 30 maç
    except Exception as e:
        print(f"{RED}Maç çekme hatası: {e}{RESET}")
        return []

def get_m3u8_from_api(stream_id):
    """RoyalTV'nin API'sinden m3u8 URL'sini alır"""
    try:
        # RoyalTV'nin olası API endpoint'leri
        api_urls = [
            f"https://royaltv21.com/api/stream/{stream_id}",
            f"https://royaltv21.com/api/channel/{stream_id}",
            f"https://royaltv21.com/stream/{stream_id}",
            f"https://royaltv21.com/get_stream/{stream_id}",
        ]
        
        h = HEADERS.copy()
        h['Referer'] = BASE_URL + '/'
        h['X-Requested-With'] = 'XMLHttpRequest'
        
        for api_url in api_urls:
            try:
                print(f"  API Dene: {api_url}")
                resp = requests.get(api_url, headers=h, timeout=10)
                
                if resp.status_code == 200:
                    # JSON yanıtı
                    try:
                        data = resp.json()
                        json_str = json.dumps(data)
                        # M3U8 ara
                        patterns = [
                            r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                            r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                            r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                            r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                            r'"source"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                            r'"playlist"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                        ]
                        for pattern in patterns:
                            matches = re.findall(pattern, json_str, re.IGNORECASE)
                            for match in matches:
                                url = match.replace('\\/', '/').replace('\\', '')
                                if url.startswith('http') and '.m3u8' in url:
                                    headers_info = {
                                        "h1Key": "referer",
                                        "h1Val": BASE_URL + "/",
                                        "h2Key": "origin",
                                        "h2Val": BASE_URL,
                                        "h3Key": "user-agent",
                                        "h3Val": HEADERS['User-Agent']
                                    }
                                    return url, headers_info
                    except:
                        pass
                    
                    # HTML yanıtı
                    patterns = [
                        r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                        r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                        r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    ]
                    for pattern in patterns:
                        matches = re.findall(pattern, resp.text, re.IGNORECASE)
                        for match in matches:
                            url = match.replace('\\/', '/').replace('\\', '')
                            if url.startswith('http') and '.m3u8' in url:
                                headers_info = {
                                    "h1Key": "referer",
                                    "h1Val": BASE_URL + "/",
                                    "h2Key": "origin",
                                    "h2Val": BASE_URL,
                                    "h3Key": "user-agent",
                                    "h3Val": HEADERS['User-Agent']
                                }
                                return url, headers_info
            except:
                continue
        
        return None, None
    except Exception as e:
        print(f"  API Hatası: {e}")
        return None, None

def get_m3u8_from_page(stream_id):
    """Sayfadan m3u8 URL'sini bulur"""
    try:
        # Sayfa URL'lerini dene
        page_urls = [
            f"{BASE_URL}/event/{stream_id}",
            f"{BASE_URL}/match/{stream_id}",
            f"{BASE_URL}/canli/{stream_id}",
            f"{BASE_URL}/stream/{stream_id}",
            f"{BASE_URL}/channel/{stream_id}",
        ]
        
        h = HEADERS.copy()
        h['Referer'] = BASE_URL + '/'
        
        for page_url in page_urls:
            try:
                print(f"  Sayfa Dene: {page_url}")
                resp = requests.get(page_url, headers=h, timeout=10)
                content = resp.text
                
                patterns = [
                    r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                    r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"source"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"playlist"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        url = match.replace('\\/', '/').replace('\\', '')
                        if url.startswith('http') and '.m3u8' in url:
                            headers_info = {
                                "h1Key": "referer",
                                "h1Val": BASE_URL + "/",
                                "h2Key": "origin",
                                "h2Val": BASE_URL,
                                "h3Key": "user-agent",
                                "h3Val": HEADERS['User-Agent']
                            }
                            return url, headers_info
                
                # iframe kontrolü
                iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
                for iframe_url in iframes:
                    if iframe_url.startswith('http'):
                        try:
                            h['Referer'] = page_url
                            iframe_resp = requests.get(iframe_url, headers=h, timeout=5)
                            for pattern in patterns:
                                matches = re.findall(pattern, iframe_resp.text, re.IGNORECASE)
                                for match in matches:
                                    url = match.replace('\\/', '/').replace('\\', '')
                                    if url.startswith('http') and '.m3u8' in url:
                                        headers_info = {
                                            "h1Key": "referer",
                                            "h1Val": BASE_URL + "/",
                                            "h2Key": "origin",
                                            "h2Val": BASE_URL,
                                            "h3Key": "user-agent",
                                            "h3Val": HEADERS['User-Agent']
                                        }
                                        return url, headers_info
                        except:
                            pass
            except:
                continue
        
        return None, None
    except Exception as e:
        print(f"  Sayfa Hatası: {e}")
        return None, None

def get_m3u8(stream_id):
    """Maç veya kanal için m3u8 URL'sini bulur"""
    # Önce API'den dene
    url, headers_info = get_m3u8_from_api(stream_id)
    if url:
        return url, headers_info
    
    # API çalışmazsa sayfadan dene
    url, headers_info = get_m3u8_from_page(stream_id)
    if url:
        return url, headers_info
    
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

        for ch in tv_items:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="TV Kanalları",{ch["name"]}\n')
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

        for m in match_items:
            display_name = f"{m['home']} - {m['away']}" if m['away'] else m['home']
            group_title = m.get('league', "RoyalTV Maçları")
            
            f.write(f'#EXTINF:-1 tvg-logo="{m.get("logo", "")}" group-title="{group_title}",{display_name}\n')
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
    print(f"\n{GREEN}RoyalTV M3U Oluşturucu Başlatıldı...{RESET}")
    
    base_domain = get_base_domain()
    print(f"Ana Domain: {base_domain}")
    
    # Kanalları çek
    channels = get_channels_from_page()
    
    # TV kanallarını test et
    tv_items = []
    print(f"\n{YELLOW}TV Kanalları test ediliyor...{RESET}")
    for channel in channels:
        print(f"\nTest: {channel['name']} (ID: {channel['id']})")
        url, headers_info = get_m3u8(channel['id'])
        if url:
            channel['url'] = url
            channel['headers'] = headers_info
            channel['playlistURL'] = ""
            channel['media_url'] = url
            tv_items.append(channel)
            print(f"  {GREEN}✓{RESET} M3U8 bulundu: {url[:80]}...")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")
    
    # Maçları çek
    matches = get_matches_from_page()
    match_items = []
    
    print(f"\n{YELLOW}Maçlar test ediliyor...{RESET}")
    for m in matches[:15]:
        print(f"\nTest: {m['home']} (ID: {m['id']})")
        url, headers_info = get_m3u8(m['id'])
        if url:
            m['url'] = url
            m['headers'] = headers_info
            m['playlistURL'] = ""
            m['media_url'] = url
            match_items.append(m)
            print(f"  {GREEN}✓{RESET} M3U8 bulundu: {url[:80]}...")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")

    if tv_items or match_items:
        build_m3u(tv_items, match_items, base_domain)
        build_json_output(tv_items, match_items, base_domain)
    else:
        print(f"\n{RED}Hiçbir yayın bulunamadı!{RESET}")
    
    print(f"\n{GREEN}Özet:{RESET}")
    print(f"  Çalışan TV kanalı: {len(tv_items)}/{len(channels)}")
    print(f"  Çalışan maç: {len(match_items)}/{len(matches[:15])}")
    print(f"  Toplam: {len(tv_items) + len(match_items)} yayın")

if __name__ == "__main__":
    main()
