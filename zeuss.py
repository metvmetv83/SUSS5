import requests
import re
from bs4 import BeautifulSoup

def get_working_tv_url():
    source_url = "https://raw.githubusercontent.com/metvmetv83/SUSS5/refs/heads/main/zeus.txt"
    try:
        response = requests.get(source_url, timeout=10)
        if response.status_code == 200:
            for line in response.text.splitlines():
                line = line.strip()
                if line.startswith("http"):
                    return line.rstrip('/')
    except Exception as e:
        print(f"Raw URL okunurken hata: {e}")
    raise Exception("Çalışan TV URL'si raw dosyasından alınamadı!")

def extract_stream_domain(tv_url):
    try:
        response = requests.get(tv_url + "/", timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Sayfa içerisindeki index.txt veya ch.html bağlantılarını tarayarak stream domain'ini bulur
            for script in soup.find_all(['script', 'iframe', 'a'], href=True):
                pass
            
            # Alternatif olarak sayfa içeriğinde geçen *.cfd uzantılı domain yapılarını yakala
            matches = re.findall(r'https?://([a-zA-Z0-9.-]+\.cfd)', response.text)
            for domain in matches:
                if "zeus" in domain and domain != tv_url.replace("https://", "").replace("http://", ""):
                    return f"https://{domain}"
                    
            # Eğer regex ile bulunamazsa ch.html linklerini incele
            for a in soup.find_all('a', href=True):
                if 'ch.html' in a['href']:
                    # Sayfa içi istek simülasyonu veya iframe kaynaklarından domain çekme
                    pass
    except Exception as e:
        print(f"Stream domain aranırken hata: {e}")
        
    # Varsayılan dinamik arama başarısız olursa sayfadaki ilk index.txt geçen URL'yi baz al
    try:
        response = requests.get(tv_url + "/", timeout=10)
        match = re.search(r'(https?://[^\s<>"]+?/b1/index\.txt)', response.text)
        if match:
            full_path = match.group(1)
            return full_path.split('/b1/')[0]
    except:
        pass

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
        
        if not channels:
            print("Dinamik kanal listesi oluşturulamadı, site yapısı kontrol edilmeli.")
            
    except Exception as e:
        print(f"Kanal verileri çekilirken hata oluştu: {e}")
    
    return channels

def create_m3u():
    tv_url = get_working_tv_url()
    print(f"Raw'dan alınan aktif TV URL: {tv_url}")
    
    stream_domain = extract_stream_domain(tv_url)
    print(f"Dinamik olarak çekilen Stream Domain: {stream_domain}")
    
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
