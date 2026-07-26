import requests
import re
import sys
import urllib3
import json
from bs4 import BeautifulSoup
from datetime import datetime

# SSL uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
#  AYARLAR
# ─────────────────────────────────────────────
REDIRECT_SOURCE = "https://raw.githubusercontent.com/mehmetey03/goal/refs/heads/main/domain.txt"
BASE_URL_SOURCE = "https://patronsports2.cfd/domain.php"

OUTPUT_M3U = "karsilasmalar.m3u"
OUTPUT_JSON = "karsilasmalar_yayinlar.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

def get_active_domain():
    """GitHub üzerindeki domain.txt dosyasından güncel adresi çeker."""
    try:
        print(f"🔍 Aktif domain {REDIRECT_SOURCE} adresinden alınıyor...")
        r = requests.get(REDIRECT_SOURCE, timeout=10)
        domain = r.text.strip().rstrip('/')
        
        # domain= veya guncel_domain= formatını kontrol et
        if '=' in domain:
            domain = domain.split('=')[-1].strip()
        
        if domain.startswith("http"):
            print(f"✅ Aktif domain bulundu: {domain}")
            return domain
        else:
            match = re.search(r'(https?://[^\s"<]+)', r.text)
            if match:
                return match.group(1).rstrip('/')
    except Exception as e:
        print(f"❌ Domain çekilirken hata: {e}")
    return None

def get_dynamic_base_url():
    """Belirtilen PHP adresinden güncel baseurl değerini çeker."""
    try:
        print(f"📡 Base URL {BASE_URL_SOURCE} adresinden alınıyor...")
        r = requests.get(BASE_URL_SOURCE, headers=HEADERS, timeout=10, verify=False)
        data = r.json()
        base_url = data.get("baseurl", "").replace("\\/", "/")
        if base_url:
            print(f"✅ Dinamik Base URL bulundu: {base_url}")
            return base_url
    except Exception as e:
        print(f"⚠️ Dinamik base_url alınamadı: {e}")
    
    # Fallback
    return "https://hz8.d72577a9dd0ec62.cfd/"

def parse_matches_from_html(soup, active_domain):
    """Canlı maçları HTML'den ayrıştırır"""
    matches = []
    matches_tab = soup.find(id="matches-tab")
    
    if not matches_tab:
        # Alternatif: class ile ara
        matches_tab = soup.find("div", class_="matches-tab")
    
    if matches_tab:
        for a in matches_tab.find_all("a", href=re.compile(r'id=')):
            try:
                cid_match = re.search(r'id=([^&]+)', a["href"])
                if not cid_match:
                    continue
                
                cid = cid_match.group(1)
                name_elem = a.find(class_="channel-name")
                status_elem = a.find(class_="channel-status")
                
                name = name_elem.get_text(strip=True) if name_elem else "İsimsiz Maç"
                status = status_elem.get_text(strip=True) if status_elem else "CANLI"
                
                # Logo bilgisini al (varsa)
                logo = ""
                img = a.find("img")
                if img:
                    logo = img.get("src", "")
                    if logo and not logo.startswith("http"):
                        if logo.startswith("/"):
                            logo = active_domain + logo
                        else:
                            logo = active_domain + "/" + logo
                
                matches.append({
                    'id': cid,
                    'name': name,
                    'status': status,
                    'logo': logo,
                    'type': 'match'
                })
            except Exception as e:
                continue
    
    return matches

def parse_channels_from_fixed(fixed_channels):
    """Sabit kanalları JSON formatına dönüştürür"""
    channels = []
    for cid, name in fixed_channels.items():
        channels.append({
            'id': cid,
            'name': name,
            'logo': "",
            'type': 'channel'
        })
    return channels

def create_m3u_content(matches, channels, base_url, active_domain):
    """M3U içeriği oluşturur"""
    m3u_content = ["#EXTM3U"]
    
    # --- CANLI MAÇLAR ---
    for m in matches:
        title = f"{m['status']} | {m['name']}"
        m3u_content.append(f'#EXTINF:-1 tvg-logo="{m["logo"]}" group-title="Canlı Maçlar",{title}')
        m3u_content.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}')
        m3u_content.append(f'#EXTVLCOPT:http-referrer={active_domain}/')
        m3u_content.append(f'{base_url}{m["id"]}/mono.m3u8')
        m3u_content.append('')  # Boş satır

    # --- 7/24 KANALLAR ---
    for c in channels:
        m3u_content.append(f'#EXTINF:-1 tvg-logo="{c["logo"]}" group-title="7/24 Kanallar",{c["name"]}')
        m3u_content.append(f'#EXTVLCOPT:http-user-agent={HEADERS["User-Agent"]}')
        m3u_content.append(f'#EXTVLCOPT:http-referrer={active_domain}/')
        m3u_content.append(f'{base_url}{c["id"]}/mono.m3u8')
        m3u_content.append('')  # Boş satır
    
    return m3u_content

def create_json_output(matches, channels, base_url, active_domain):
    """JSON çıktısı oluşturur"""
    
    # Maçlara URL ekle
    matches_with_url = []
    for m in matches:
        match_copy = m.copy()
        match_copy['url'] = f"{base_url}{m['id']}/mono.m3u8"
        match_copy['user_agent'] = HEADERS["User-Agent"]
        match_copy['referrer'] = active_domain + '/'
        matches_with_url.append(match_copy)
    
    # Kanallara URL ekle
    channels_with_url = []
    for c in channels:
        channel_copy = c.copy()
        channel_copy['url'] = f"{base_url}{c['id']}/mono.m3u8"
        channel_copy['user_agent'] = HEADERS["User-Agent"]
        channel_copy['referrer'] = active_domain + '/'
        channels_with_url.append(channel_copy)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "Karsilasmalar",
        "active_domain": active_domain,
        "base_url": base_url,
        "referrer": active_domain + '/',
        "user_agent": HEADERS["User-Agent"],
        "total_streams": len(matches) + len(channels),
        "matches": matches_with_url,
        "channels": channels_with_url
    }
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {OUTPUT_JSON} başarıyla oluşturuldu!")

def main():
    print("🚀 Karşılaşmalar M3U ve JSON Oluşturucu Başlatılıyor...")
    
    active_domain = get_active_domain()
    if not active_domain:
        sys.exit("❌ Başlangıç domaini bulunamadı. GitHub linkini kontrol edin.")

    base_url = get_dynamic_base_url()
    
    print(f"📡 Active Domain: {active_domain}")
    print(f"📡 Base URL: {base_url}")

    # Sabit kanallar
    fixed_channels = {
        "zirve": "beIN Sports 1 A",
        "taraftarium": "beIN Sports 1 B",
        "patron": "beIN Sports 1 C",
        "b2": "beIN Sports 2",
        "b3": "beIN Sports 3",
        "b4": "beIN Sports 4",
        "b5": "beIN Sports 5",
        "bm1": "beIN Sports 1 Max",
        "bm2": "beIN Sports 2 Max",
        "ss1": "S Sports 1",
        "ss2": "S Sports 2",
        "smarts": "Smart Sports",
        "sms2": "Smart Sports 2",
        "t1": "Tivibu Sports 1",
        "t2": "Tivibu Sports 2",
        "t3": "Tivibu Sports 3",
        "t4": "Tivibu Sports 4",
        "as": "A Spor",
        "trtspor": "TRT Spor",
        "trtspor2": "TRT Spor Yıldız",
        "trt1": "TRT 1",
        "atv": "ATV",
        "tv85": "TV8.5",
        "nbatv": "NBA TV",
        "eu1": "Euro Sport 1",
        "eu2": "Euro Sport 2",
        "ex1": "Tâbii 1",
        "ex2": "Tâbii 2",
        "ex3": "Tâbii 3",
        "ex4": "Tâbii 4",
        "ex5": "Tâbii 5",
        "ex6": "Tâbii 6",
        "ex7": "Tâbii 7",
        "ex8": "Tâbii 8"
    }

    try:
        print("📡 Canlı maçlar taranıyor...")
        resp = requests.get(active_domain, headers=HEADERS, timeout=15, verify=False)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")

        # Maçları parse et
        matches = parse_matches_from_html(soup, active_domain)
        print(f"   {len(matches)} canlı maç bulundu.")
        
        # Kanalları parse et
        channels = parse_channels_from_fixed(fixed_channels)
        print(f"   {len(channels)} sabit kanal bulundu.")

        if matches or channels:
            # M3U oluştur
            m3u_content = create_m3u_content(matches, channels, base_url, active_domain)
            with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
                f.write("\n".join(m3u_content))
            print(f"✅ {OUTPUT_M3U} başarıyla oluşturuldu! ({len(matches)} Maç, {len(channels)} Kanal)")
            
            # JSON oluştur
            create_json_output(matches, channels, base_url, active_domain)
            
            # Özet
            print("\n📊 ÖZET:")
            print(f"   Canlı Maç: {len(matches)}")
            print(f"   7/24 Kanal: {len(channels)}")
            print(f"   Toplam: {len(matches) + len(channels)}")
            print(f"   Active Domain: {active_domain}")
            print(f"   Base URL: {base_url}")
        else:
            print("❌ Veri bulunamadı.")

    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()
