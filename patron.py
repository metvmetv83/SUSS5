import requests
import urllib3
import json
import re
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
#  KAYNAKLAR
# ─────────────────────────────────────────────
DOMAIN_API_URL = "https://patronsports2.cfd/domain.php"
CHANNELS_API_URL = "https://patronsports2.cfd/channels.php"
MATCHES_API_URL = "https://patronsports2.cfd/matches.php"

OUTPUT_M3U = "patron.m3u"
OUTPUT_JSON = "patron_yayinlar.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://patronsports2.cfd/",
    "Accept": "application/json, text/plain, */*"
}

def get_base_url():
    """Base URL'yi API'den alır"""
    try:
        r = requests.get(DOMAIN_API_URL, headers=HEADERS, timeout=10, verify=False)
        data = r.json()
        base_url = data.get("baseurl", "")
        if base_url:
            base_url = base_url.replace("\\", "").rstrip('/')
            if not base_url.endswith('/'):
                base_url += '/'
            print(f"📡 Base URL: {base_url}")
            return base_url
    except Exception as e:
        print(f"⚠️ Domain API hatası: {e}")
    
    # Fallback
    return "https://2i4.d72577a9dd0ec71.cfd/"

def get_channels():
    """Kanalları JSON API'den çeker"""
    print("📺 Kanallar çekiliyor...")
    try:
        resp = requests.get(CHANNELS_API_URL, headers=HEADERS, timeout=15, verify=False)
        data = resp.json()
        channels = []
        
        for item in data:
            channel_id = item.get("URL", "").replace("/ch.html?id=", "")
            name = item.get("Mac", "")
            logo = item.get("Logo", "")
            
            if logo and not logo.startswith('http'):
                if logo.startswith('/'):
                    logo = "https://patronsports2.cfd" + logo
                else:
                    logo = "https://patronsports2.cfd/" + logo
            
            if channel_id and name:
                channels.append({
                    'id': channel_id,
                    'name': name,
                    'logo': logo,
                    'type': 'channel'
                })
        
        print(f"   {len(channels)} kanal bulundu.")
        return channels
    except Exception as e:
        print(f"💥 Kanal çekme hatası: {e}")
        return []

def get_matches():
    """Maçları JSON API'den çeker"""
    print("📊 Maçlar çekiliyor...")
    try:
        resp = requests.get(MATCHES_API_URL, headers=HEADERS, timeout=15, verify=False)
        data = resp.json()
        matches = []
        
        for item in data:
            channel_id = item.get("URL", "").replace("/ch.html?id=", "")
            home = item.get("HomeTeam", "")
            away = item.get("AwayTeam", "")
            home_logo = item.get("HomeLogo", "")
            away_logo = item.get("AwayLogo", "")
            time = item.get("Time", "")
            league = item.get("league", "")
            sport_type = item.get("type", "")
            
            if channel_id and home and away:
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
        
        print(f"   {len(matches)} maç bulundu.")
        return matches
    except Exception as e:
        print(f"💥 Maç çekme hatası: {e}")
        return []

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
    """JSON çıktısı oluşturur"""
    
    matches_with_url = []
    for m in matches:
        match_copy = m.copy()
        match_copy['url'] = f"{base_url}{m['id']}/mono.m3u8"
        match_copy['user_agent'] = HEADERS["User-Agent"]
        match_copy['referrer'] = referrer + '/'
        matches_with_url.append(match_copy)
    
    channels_with_url = []
    for c in channels:
        channel_copy = c.copy()
        channel_copy['url'] = f"{base_url}{c['id']}/mono.m3u8"
        channel_copy['user_agent'] = HEADERS["User-Agent"]
        channel_copy['referrer'] = referrer + '/'
        channels_with_url.append(channel_copy)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "Patron Sports",
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
    print("🚀 Patron Sports Verileri Çekiliyor...")
    
    base_url = get_base_url()
    referrer = "https://patronsports2.cfd"
    
    print(f"📡 Base URL: {base_url}")
    print(f"📡 Referrer: {referrer}")
    
    # Header'ları güncelle
    HEADERS["Referer"] = referrer + "/"
    
    # Verileri çek
    channels = get_channels()
    matches = get_matches()
    
    if matches or channels:
        # M3U oluştur
        m3u_content = create_m3u_with_logos(matches, channels, base_url, referrer)
        with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_content))
        print(f"✅ {OUTPUT_M3U} başarıyla oluşturuldu! ({len(matches)} Maç, {len(channels)} Kanal)")
        
        # JSON oluştur
        create_json_output(matches, channels, base_url, referrer)
        
        # Özet
        print("\n📊 ÖZET:")
        print(f"   Maç: {len(matches)}")
        print(f"   Kanal: {len(channels)}")
        print(f"   Toplam: {len(matches) + len(channels)}")
    else:
        print("❌ Veri bulunamadı.")

if __name__ == "__main__":
    main()
