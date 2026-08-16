import requests
import re
from bs4 import BeautifulSoup

def get_working_tv_url():
    source_url = "https://raw.githubusercontent.com/metvmetv83/SUSS5/refs/heads/main/zeus.txt"
    try:
        response = requests.get(source_url, timeout=10)
        if response.status_code == 200:
            urls = []
            for line in response.text.splitlines():
                line = line.strip()
                if line.startswith("http"):
                    found = re.findall(r'https?://[^\s]+', line)
                    for u in found:
                        u_clean = u.rstrip('/')
                        if u_clean not in urls:
                            urls.append(u_clean)
            
            for tv_url in urls:
                try:
                    print(f"Test ediliyor: {tv_url}")
                    resp = requests.get(tv_url + "/", timeout=5)
                    if resp.status_code == 200 and "Plesk" not in resp.text:
                        print(f"Çalışan aktif URL bulundu: {tv_url}")
                        return tv_url
                except Exception as e:
                    print(f"{tv_url} bağlanılamadı: {e}")
                    continue
    except Exception as e:
        print(f"Raw URL okunurken hata: {e}")
        
    raise Exception("Çalışan aktif TV URL'si bulunamadı!")

def fetch_channels(tv_url):
    channels = []
    stream_domain = "https://zeus324232.cfd" # Verdiğiniz koddaki ana domain
    
    try:
        response = requests.get(tv_url + "/", timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'ch.html?id=' in href:
                    channel_name = a.get_text(strip=True)
                    match = re.search(r'id=([a-zA-Z0-9_-]+)', href)
                    if match:
                        ch_id = match.group(1).lower()
                        txt_link = f"{stream_domain}/{ch_id}/index.txt"
                        # Aynı kanalı tekrar eklememek için kontrol
                        if (channel_name if channel_name else ch_id.upper(), txt_link) not in channels:
                            channels.append((channel_name if channel_name else ch_id.upper(), txt_link))
                            
        # Eğer siteden dinamik çekilemezse varsayılan temel listeyi kullan
        if not channels:
            print("Dinamik kanal bulunamadı, varsayılan liste yükleniyor...")
            default_ids = [
                "b1", "b1local", "b2", "b3", "b4", "bein5", "b1max", "b2max", 
                "s1", "s2", "smart1", "smart2", "tivibu", "tivibu1", "tivibu2", 
                "tivibu3", "sifirtv", "euro1", "euro2", "tabiiyedek", "tabii1", 
                "tabii2", "tabii3", "tabii4", "tabii5", "tabii6", "xexxen", "xexxen1", "b5"
            ]
            for ch_id in default_ids:
                channels.append((ch_id.upper(), f"{stream_domain}/{ch_id}/index.txt"))
                
    except Exception as e:
        print(f"Kanal verileri çekilirken hata oluştu: {e}")
    
    return channels, stream_domain

def create_m3u():
    tv_url = get_working_tv_url()
    print(f"Aktif TV URL: {tv_url}")
    
    channels, stream_domain = fetch_channels(tv_url)
    
    m3u_content = f"#EXTM3U\n# Source: {tv_url}\n# Stream Domain: {stream_domain}\n"
    for name, link in channels:
        inf = 25 if "B1" == name.upper() else 0
        m3u_content += f"#EXTINF:{inf}, {name}\n"
        m3u_content += "#EXTVLCOPT:network-caching=1000\n"
        m3u_content += f"{link}\n"
        
    with open("zeus.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print("zeus.m3u başarıyla oluşturuldu ve kaydedildi.")

if __name__ == "__main__":
    create_m3u()
