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

# RoyalTV kanalları (tahmini ID'ler)
TV_CHANNELS = [
    {"id": "1", "name": "ROYAL TV 1", "logo": "", "title": "Royal TV 1"},
    {"id": "2", "name": "ROYAL TV 2", "logo": "", "title": "Royal TV 2"},
    {"id": "3", "name": "ROYAL TV 3", "logo": "", "title": "Royal TV 3"},
]

def get_base_domain():
    """Ana domain adresini bulur"""
    try:
        r1 = requests.get(START_URL, headers=HEADERS, allow_redirects=True, timeout=10)
        if r1.url:
            return r1.url.rstrip('/')
    except Exception:
        pass
    return BASE_URL

def get_matches():
    """Maç listesini RoyalTV'den çeker"""
    print(f"Maçlar çekiliyor → {BASE_URL}")
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        matches = []
        
        # Maç linklerini bul (genellikle /event/ veya /match/ içerir)
        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/event/' in href or '/match/' in href or '/canli/' in href:
                match_id = re.search(r'/(?:event|match|canli)/(\d+)', href)
                if match_id:
                    match_id = match_id.group(1)
                    # Maç başlığını al
                    title = a.get_text(strip=True)
                    if title:
                        matches.append({
                            'id': match_id,
                            'title': title,
                            'home': title.split(' vs ')[0] if ' vs ' in title else title,
                            'away': title.split(' vs ')[1] if ' vs ' in title else "",
                            'logo': "",
                            'time': "",
                            'league': "RoyalTV Maçları"
                        })
        
        # Eğer hiç maç bulunamazsa, sayfadaki tüm linkleri tara
        if not matches:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/') and len(href) > 1:
                    match_id = re.search(r'/(\d+)', href)
                    if match_id:
                        title = a.get_text(strip=True)
                        if title and len(title) > 3:
                            matches.append({
                                'id': match_id.group(1),
                                'title': title,
                                'home': title,
                                'away': "",
                                'logo': "",
                                'time': "",
                                'league': "RoyalTV Maçları"
                            })
        
        return matches[:20]  # İlk 20 maç
    except Exception as e:
        print(f"{RED}Maç çekme hatası: {e}{RESET}")
        return []

def get_m3u8_from_page(resource_id, base_domain):
    """RoyalTV sayfasından m3u8 URL'sini bulur"""
    try:
        # Sayfa URL'sini dene
        page_urls = [
            f"{base_domain}/event/{resource_id}",
            f"{base_domain}/match/{resource_id}",
            f"{base_domain}/canli/{resource_id}",
            f"{base_domain}/{resource_id}"
        ]
        
        for page_url in page_urls:
            try:
                print(f"  Kontrol: {page_url}")
                h = HEADERS.copy()
                h['Referer'] = base_domain + '/'
                
                resp = requests.get(page_url, headers=h, timeout=10)
                content = resp.text
                
                # M3U8 URL'lerini ara
                patterns = [
                    r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                    r'"URL"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"stream"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"source"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"file"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"playlist"\s*:\s*"([^"]+\.m3u8[^"]*)"',
                    r'"(?:https?://[^"]+\.m3u8[^"]*)"',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        url = match.replace('\\/', '/').replace('\\', '')
                        if url.startswith('http') and '.m3u8' in url:
                            headers_info = {
                                "h1Key": "referer",
                                "h1Val": base_domain + "/",
                                "h2Key": "user-agent",
                                "h2Val": HEADERS['User-Agent']
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
                                            "h1Val": base_domain + "/",
                                            "h2Key": "user-agent",
                                            "h2Val": HEADERS['User-Agent']
                                        }
                                        return url, headers_info
                        except:
                            pass
            except:
                continue
        
        return None, None
    except Exception as e:
        print(f"  Hata: {e}")
        return None, None

def get_m3u8(resource_id, base_domain):
    """Maç veya kanal için m3u8 URL'sini bulur"""
    url, headers_info = get_m3u8_from_page(resource_id, base_domain)
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
            
            f.write(f'#EXTINF:-1 tvg-logo="" group-title="{group_title}",{display_name}\n')
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
    
    # TV kanalları (örnek)
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
            print(f"  {GREEN}✓{RESET} M3U8 bulundu")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")
    
    # Maçlar
    matches = get_matches()
    match_items = []
    
    print(f"\n{YELLOW}Maçlar test ediliyor...{RESET}")
    for m in matches[:10]:
        print(f"\nTest: {m['home']} (ID: {m['id']})")
        url, headers_info = get_m3u8(m['id'], base_domain)
        if url:
            m['url'] = url
            m['headers'] = headers_info
            m['playlistURL'] = ""
            m['media_url'] = url
            match_items.append(m)
            print(f"  {GREEN}✓{RESET} M3U8 bulundu")
        else:
            print(f"  {RED}✗{RESET} M3U8 bulunamadı")

    if tv_items or match_items:
        build_m3u(tv_items, match_items, base_domain)
        build_json_output(tv_items, match_items, base_domain)
    else:
        print(f"\n{RED}Hiçbir yayın bulunamadı!{RESET}")
    
    print(f"\n{GREEN}Özet:{RESET}")
    print(f"  Çalışan TV kanalı: {len(tv_items)}/{len(TV_CHANNELS)}")
    print(f"  Çalışan maç: {len(match_items)}/{len(matches[:10])}")
    print(f"  Toplam: {len(tv_items) + len(match_items)} yayın")

if __name__ == "__main__":
    main()
