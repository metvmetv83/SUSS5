import requests
import urllib3
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
#  KAYNAKLAR
# ─────────────────────────────────────────────
BASE_URL = "https://galyatv1.com"
POPULAR_VIEW_URL = f"{BASE_URL}/Live/Main/GetPopularSportView"
SPORT_VIEW_URL = f"{BASE_URL}/Live/Main/GetSportView"
CDN_BASE = "https://cdn.galyatv1.com"

OUTPUT_M3U = "galyatv.m3u"
OUTPUT_JSON = "galyatv_yayinlar.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": BASE_URL + "/",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest"
}

def get_channels_from_html(html_content):
    """Kanalları HTML'den ayrıştırır"""
    channels = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Kanalları bul - farklı formatları dene
    channel_patterns = [
        r'(TRT Spor|TRT 1|S Sport 2|A Spor|S Sport|Tivibu Spor|Bein Sports|Euro Sport|Smart Spor)\s*[-–]\s*Canlı',
        r'(TRT SPOR|TRT 1|S SPORT 2|A SPOR|S SPORT|TIVIBU SPOR|BEIN SPORTS|EURO SPORT|SMART SPOR)\s*[-–]\s*CANLI'
    ]
    
    # Sayfadaki tüm metni ara
    text = soup.get_text()
    
    for pattern in channel_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            channel_name = match.strip()
            if channel_name and channel_name not in [c['name'] for c in channels]:
                # Kanal ID'sini bul (Watch/MXXXXXX formatında)
                watch_link = soup.find('a', href=re.compile(r'/Watch/M\d+'))
                if watch_link:
                    href = watch_link.get('href', '')
                    channel_id = href.replace('/Watch/M', '')
                    if channel_id:
                        channels.append({
                            'id': channel_id,
                            'name': channel_name,
                            'logo': f"{BASE_URL}/images/channels/{channel_name.lower().replace(' ', '')}.png",
                            'type': 'channel'
                        })
    
    # Alternatif: data-channel-id veya benzeri attribute ara
    channel_elements = soup.find_all(attrs={'data-channel-id': True})
    for elem in channel_elements:
        channel_id = elem.get('data-channel-id')
        channel_name = elem.get('data-channel-name') or elem.get_text(strip=True)
        if channel_id and channel_name:
            channels.append({
                'id': channel_id,
                'name': channel_name,
                'logo': f"{BASE_URL}/images/channels/{channel_name.lower().replace(' ', '')}.png",
                'type': 'channel'
            })
    
    return channels

def get_matches_from_html(html_content):
    """Maçları HTML'den ayrıştırır"""
    matches = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Maç linklerini bul - Watch/MXXXXXX formatında
    match_links = soup.find_all('a', href=re.compile(r'/Watch/M\d+'))
    
    for link in match_links:
        try:
            href = link.get('href', '')
            match_id = href.replace('/Watch/M', '')
            
            if not match_id:
                continue
            
            # Maç bilgilerini al
            title = link.get_text(strip=True)
            if not title or len(title) < 3:
                continue
            
            # Takım isimlerini ayırmaya çalış
            home = title
            away = ""
            if ' - ' in title:
                parts = title.split(' - ', 1)
                home, away = parts[0], parts[1]
            elif ' vs ' in title:
                parts = title.split(' vs ', 1)
                home, away = parts[0], parts[1]
            elif ' - ' in title and 'Canlı' in title:
                parts = title.replace(' - Canlı', '').split(' - ', 1)
                if len(parts) == 2:
                    home, away = parts[0], parts[1]
            
            # Logo bulmaya çalış
            logo = ""
            img = link.find('img')
            if img:
                logo = img.get('src', '')
                if logo and not logo.startswith('http'):
                    if logo.startswith('/'):
                        logo = BASE_URL + logo
                    else:
                        logo = BASE_URL + '/' + logo
            
            matches.append({
                'id': match_id,
                'home': home,
                'away': away,
                'title': title,
                'logo': logo,
                'type': 'match',
                'league': "Galyatv1 Maçları",
                'time': "",
                'sport': "Futbol"
            })
        except Exception as e:
            continue
    
    return matches

def create_m3u_content(channels, matches, cdn_base):
    """M3U içeriği oluşturur"""
    m3u_content = ["#EXTM3U"]
    
    # --- KANALLAR ---
    for ch in channels:
        m3u8_url = f"{cdn_base}/M{ch['id']}/M{ch['id']}.m3u8"
        m3u_content.append(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="7/24 Kanallar",{ch["name"]}')
        m3u_content.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}')
        m3u_content.append(f'#EXTVLCOPT:http-referrer={BASE_URL}/')
        m3u_content.append(m3u8_url)
        m3u_content.append('')

    # --- MAÇLAR ---
    for m in matches:
        display_name = f"{m['home']} - {m['away']}" if m['away'] else m['title']
        m3u8_url = f"{cdn_base}/M{m['id']}/M{m['id']}.m3u8"
        m3u_content.append(f'#EXTINF:-1 tvg-logo="{m["logo"]}" group-title="Canlı Maçlar",{display_name}')
        m3u_content.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}')
        m3u_content.append(f'#EXTVLCOPT:http-referrer={BASE_URL}/')
        m3u_content.append(m3u8_url)
        m3u_content.append('')
    
    return m3u_content

def create_json_output(channels, matches, cdn_base):
    """JSON çıktısı oluşturur"""
    
    channels_with_url = []
    for ch in channels:
        channel_copy = ch.copy()
        channel_copy['url'] = f"{cdn_base}/M{ch['id']}/M{ch['id']}.m3u8"
        channel_copy['user_agent'] = HEADERS["User-Agent"]
        channel_copy['referrer'] = BASE_URL + '/'
        channels_with_url.append(channel_copy)
    
    matches_with_url = []
    for m in matches:
        match_copy = m.copy()
        match_copy['url'] = f"{cdn_base}/M{m['id']}/M{m['id']}.m3u8"
        match_copy['user_agent'] = HEADERS["User-Agent"]
        match_copy['referrer'] = BASE_URL + '/'
        matches_with_url.append(match_copy)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "Galyatv1",
        "base_url": BASE_URL,
        "cdn_base": cdn_base,
        "referrer": BASE_URL + '/',
        "user_agent": HEADERS["User-Agent"],
        "total_streams": len(channels) + len(matches),
        "channels": channels_with_url,
        "matches": matches_with_url
    }
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {OUTPUT_JSON} başarıyla oluşturuldu!")

def main():
    print("🚀 Galyatv1 M3U ve JSON Oluşturucu Başlatılıyor...")
    
    all_channels = []
    all_matches = []
    
    try:
        # 1. Popüler maçları çek
        print("📡 Popüler maçlar çekiliyor...")
        resp1 = requests.get(POPULAR_VIEW_URL, headers=HEADERS, timeout=15, verify=False)
        matches1 = get_matches_from_html(resp1.text)
        channels1 = get_channels_from_html(resp1.text)
        print(f"   Popüler maçlar: {len(matches1)}")
        print(f"   Popüler kanallar: {len(channels1)}")
        
        all_matches.extend(matches1)
        all_channels.extend(channels1)
        
        # 2. Tüm spor görünümünü çek
        print("📡 Tüm spor görünümü çekiliyor...")
        resp2 = requests.get(SPORT_VIEW_URL, headers=HEADERS, timeout=15, verify=False)
        matches2 = get_matches_from_html(resp2.text)
        channels2 = get_channels_from_html(resp2.text)
        print(f"   Tüm maçlar: {len(matches2)}")
        print(f"   Tüm kanallar: {len(channels2)}")
        
        all_matches.extend(matches2)
        all_channels.extend(channels2)
        
        # Benzersiz kanalları ve maçları filtrele
        unique_channels = []
        seen_ids = set()
        for ch in all_channels:
            if ch['id'] not in seen_ids:
                seen_ids.add(ch['id'])
                unique_channels.append(ch)
        
        unique_matches = []
        seen_match_ids = set()
        for m in all_matches:
            if m['id'] not in seen_match_ids:
                seen_match_ids.add(m['id'])
                unique_matches.append(m)
        
        print(f"\n📊 Toplam benzersiz kanal: {len(unique_channels)}")
        print(f"📊 Toplam benzersiz maç: {len(unique_matches)}")
        
        if unique_channels or unique_matches:
            # M3U oluştur
            m3u_content = create_m3u_content(unique_channels, unique_matches, CDN_BASE)
            with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
                f.write("\n".join(m3u_content))
            print(f"✅ {OUTPUT_M3U} başarıyla oluşturuldu! ({len(unique_matches)} Maç, {len(unique_channels)} Kanal)")
            
            # JSON oluştur
            create_json_output(unique_channels, unique_matches, CDN_BASE)
            
            # Özet
            print("\n📊 ÖZET:")
            print(f"   Kanal: {len(unique_channels)}")
            print(f"   Maç: {len(unique_matches)}")
            print(f"   Toplam: {len(unique_channels) + len(unique_matches)}")
            print(f"   CDN Base: {CDN_BASE}")
        else:
            print("❌ Veri bulunamadı.")
            
    except Exception as e:
        print(f"💥 Hata oluştu: {e}")

if __name__ == "__main__":
    main()
