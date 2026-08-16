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

def extract_stream_domain(tv_url):
    try:
        response = requests.get(tv_url + "/", timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Yöntem: ch.html?id=... linklerinin kaynak kodunu (iframe veya script) kontrol et
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'ch.html?id=' in href:
                    # ch.html sayfasına gidip içindeki gerçek index.txt linkini çekelim
                    full_ch_url = href if href.startswith("http") else tv_url + ("/" if not href.startswith("/") else "") + href
                    try:
                        ch_resp = requests.get(full_ch_url, timeout=5)
                        match = re.search(r'(https?://[^\s<>"]+?/index\.txt)', ch_resp.text)
                        if match:
                            full_path = match.group(1)
                            # Örnek: https://zeus324232.cfd/b1/index.txt -> https://zeus324232.cfd
                            domain_match = re.match(r'(https?://[^/]+)', full_path)
                            if domain_match:
                                return domain_match.group(1)
                    except:
                        continue
            
            # 2. Yöntem: Sayfa içinde geçen herhangi bir index.txt bağlantısını yakala
            match = re.search(r'(https?://[^\s<>"]+?/index\.txt)', response.text)
            if match:
                domain_match = re.match(r'(https?://[^/]+)', match.group(1))
                if domain_match:
                    return domain_match.group(1)

    except Exception as e:
        print(f"Stream domain aranırken hata: {e}")

    raise Exception("Stream domain dinamik olarak çözülemedi!")

def fetch_channels(stream_domain, tv_url):
    channels = []
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
                        channels.append((channel_name if channel_name else ch_id.upper(), txt_link))
    except Exception as e:
        print(f"Kanal verileri çekilirken hata oluştu: {e}")
    
    return channels

def create_m3u():
    tv_url = get_working_tv_url()
    print(f"Aktif TV URL: {tv_url}")
    
    stream_domain = extract_stream_domain(tv_url)
    print(f"Dinamik Stream Domain: {stream_domain}")
    
    channels = fetch_channels(stream_domain, tv_url)
    
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
