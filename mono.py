import requests
import urllib3
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
#  KAYNAKLAR
# ─────────────────────────────────────────────
DOMAIN_API_URL = "https://data-reality.com/domain.php"
MATCHES_API_URL = "https://data-reality.com/matches.php"
CHANNELS_API_URL = "https://data-reality.com/channels.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://patronsports2.cfd/"
}

OUTPUT_M3U = "mono.m3u"
OUTPUT_JSON = "mono_yayinlar.json"

def get_base_url_with_fallback():
    """Base URL'yi API'den alır, yoksa fallback kullanır"""
    try:
        r = requests.get(DOMAIN_API_URL, headers=HEADERS, timeout=10, verify=False)
        data = r.json()
        base_url = data.get("baseurl", "")
        if base_url:
            base_url = base_url.replace("\\", "").rstrip('/')
            return base_url + "/"
    except Exception as e:
        print(f"⚠️ Domain API hatası: {e}")
    
    parsed = urlparse(MATCHES_API_URL)
    return f"{parsed.scheme}://{parsed.netloc}/"

def parse_matches_from_html(html_content):
    """Maçları HTML'den ayrıştırır"""
    matches = []
    soup = BeautifulSoup(html_content, 'html.parser')
    match_links = soup.find_all('a', class_='single-match')
    
    for link in match_links:
        try:
            href = link.get('href', '')
            channel_id = href.replace('channel?id=', '') if 'channel?id=' in href else None
            
            if not channel_id:
                continue
            
            imgs = link.find_all('img')
            home_logo = imgs[0].get('src', '') if len(imgs) > 0 else ''
            away_logo = imgs[1].get('src', '') if len(imgs) > 1 else ''
            
            detail_div = link.find('div', class_='match-detail')
            if not detail_div: 
                continue
                
            date_div = detail_div.find('div', class_='date')
            sport_type = date_div.text.strip() if date_div else ''
            
            event_div = detail_div.find('div', class_='event')
            event_text = event_div.text.strip() if event_div else ''
            
            time, league = '', ''
            if '|' in event_text:
                parts = event_text.split('|')
                time, league = parts[0].strip(), parts[1].strip()
            else:
                league = event_text
            
            teams_div = detail_div.find('div', class_='teams')
            if teams_div:
                home_div = teams_div.find('div', class_='home')
                away_div = teams_div.find('div', class_='away')
                
                home = home_div.text.strip() if home_div else ''
                away = away_div.text.strip() if away_div else ''
                
                # Logo URL'lerini düzelt
                if home_logo and not home_logo.startswith('http'):
                    if home_logo.startswith('/'):
                        home_logo = 'https://data-reality.com' + home_logo
                    else:
                        home_logo = 'https://data-reality.com/' + home_logo
                
                if away_logo and not away_logo.startswith('http'):
                    if away_logo.startswith('/'):
                        away_logo = 'https://data-reality.com' + away_logo
                    else:
                        away_logo = 'https://data-reality.com/' + away_logo
                
                matches.append({
                    'id': channel_id,
                    'home': home,
                    'away': away,
                    'home_logo': home_logo,
                    'away_logo': away_logo,
                    'league': league,
                    'time': time,
                    'sport': sport_type,
                    'type': 'match'
                })
        except Exception as e:
            continue
    
    return matches

def parse_channels_from_html(html_content):
    """7/24 kanalları HTML'den ayrıştırır"""
    channels = []
    soup = BeautifulSoup(html_content, 'html.parser')
    channel_links = soup.find_all('a', class_='single-match')
    
    for link in channel_links:
        try:
            href = link.get('href', '')
            channel_id = href.replace('channel?id=', '') if 'channel?id=' in href else None
            
            if not channel_id:
                continue
                
            detail_div = link.find('div', class_='match-detail')
            if not detail_div:
                continue
            
            event_div = detail_div.find('div', class_='event')
            is_channel = event_div and '7/24' in event_div.text
            
            if is_channel:
                teams_div = detail_div.find('div', class_='teams')
                if teams_div:
                    home_div = teams_div.find('div', class_='home')
                    away_div = teams_div.find('div', class_='away')
                    
                    name = home_div.text.strip() if home_div else ''
                    
                    logo = ''
                    if away_div:
                        logo_img = away_div.find('img')
                        if logo_img:
                            logo = logo_img.get('src', '')
                            if logo and not logo.startswith('http'):
                                if logo.startswith('/'):
                                    logo = 'https://data-reality.com' + logo
                                else:
                                    logo = 'https://data-reality.com/' + logo
                    
                    if channel_id and name:
                        channels.append({
                            'id': channel_id,
                            'name': name,
                            'logo': logo,
                            'type': 'channel'
                        })
        except Exception as e:
            continue
    
    return channels

def create_m3u_with_logos(matches, channels, base_url, referrer):
    """M3U dosyası oluşturur"""
    m3u_list = ["#EXTM3U\n"]
    
    # --- CANLI MAÇLAR ---
    for m in matches:
        display_name = f"{m['home']} - {m['away']} [{m['time']}]"
        group_title = f"CANLI MAÇLAR - {m['league']}"
        main_logo = m['home_logo'] or m['away_logo']
        stream_url = f"{base_url}{m['id']}/mono.m3u8"
        
        m3u_list.append(f'#EXTINF:-1 tvg-logo="{main_logo}" group-title="{group_title}",{display_name}')
        m3u_list.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}')
        m3u_list.append(f'#EXTVLCOPT:http-referrer={referrer}/')
        m3u_list.append(stream_url)
        m3u_list.append(f'# İki logo: {m["home_logo"]} | {m["away_logo"]}\n')

    # --- 7/24 KANALLAR ---
    for c in channels:
        stream_url = f"{base_url}{c['id']}/mono.m3u8"
        m3u_list.append(f'#EXTINF:-1 tvg-logo="{c["logo"]}" group-title="7/24 KANALLAR",{c["name"]}')
        m3u_list.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}')
        m3u_list.append(f'#EXTVLCOPT:http-referrer={referrer}/')
        m3u_list.append(f'{stream_url}\n')
        
    return m3u_list

def create_json_output(matches, channels, base_url, referrer):
    """JSON çıktısı oluşturur - URL'ler dahil"""
    
    # Maçlara URL ekle
    matches_with_url = []
    for m in matches:
        match_copy = m.copy()
        match_copy['url'] = f"{base_url}{m['id']}/mono.m3u8"
        match_copy['user_agent'] = HEADERS["User-Agent"]
        match_copy['referrer'] = referrer + '/'
        matches_with_url.append(match_copy)
    
    # Kanallara URL ekle
    channels_with_url = []
    for c in channels:
        channel_copy = c.copy()
        channel_copy['url'] = f"{base_url}{c['id']}/mono.m3u8"
        channel_copy['user_agent'] = HEADERS["User-Agent"]
        channel_copy['referrer'] = referrer + '/'
        channels_with_url.append(channel_copy)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "base_url": base_url,
        "referrer": referrer + '/',
        "user_agent": HEADERS["User-Agent"],
        "total_streams": len(matches) + len(channels),
        "matches": matches_with_url,
        "channels": channels_with_url
    }
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {OUTPUT_JSON} başarıyla oluşturuldu!")

def main():
    print("🚀 Justin TV Verileri Çekiliyor...")
    
    base_url = get_base_url_with_fallback()
    referrer = "https://canlimacizlejustin.online"
    
    print(f"📡 Base URL: {base_url}")
    
    try:
        # Maçları çek
        print("📊 Maçlar çekiliyor...")
        resp_m = requests.get(MATCHES_API_URL, headers=HEADERS, timeout=15, verify=False)
        matches = parse_matches_from_html(resp_m.text)
        print(f"   {len(matches)} maç bulundu.")
        
        # Kanalları çek
        print("📺 Kanallar çekiliyor...")
        resp_c = requests.get(CHANNELS_API_URL, headers=HEADERS, timeout=15, verify=False)
        channels = parse_channels_from_html(resp_c.text)
        print(f"   {len(channels)} kanal bulundu.")
        
        if matches or channels:
            # M3U oluştur
            m3u_content = create_m3u_with_logos(matches, channels, base_url, referrer)
            with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
                f.write("\n".join(m3u_content))
            print(f"✅ {OUTPUT_M3U} başarıyla oluşturuldu! ({len(matches)} Maç, {len(channels)} Kanal)")
            
            # JSON oluştur (URL'ler dahil)
            create_json_output(matches, channels, base_url, referrer)
            
            # Özet
            print("\n📊 ÖZET:")
            print(f"   Maç: {len(matches)}")
            print(f"   Kanal: {len(channels)}")
            print(f"   Toplam: {len(matches) + len(channels)}")
        else:
            print("❌ Veri bulunamadı.")
            
    except Exception as e:
        print(f"💥 Hata oluştu: {e}")

if __name__ == "__main__":
    main()
