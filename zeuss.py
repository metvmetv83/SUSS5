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

def extract_stream_domain_dynamically(tv_url):
    try:
        response = requests.get(tv_url + "/", timeout=10)
        if response.status_code == 200:
            cfd_domains = re.findall(r'https?://([a-zA-Z0-9.-]+\.cfd)', response.text)
            for domain in cfd_domains:
                full_domain = f"https://{domain}"
                if full_domain.rstrip('/') != tv_url.rstrip('/'):
                    print(f"Ana sayfadan dinamik yakalandı: {full_domain}")
                    return full_domain

            soup = BeautifulSoup(response.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'ch.html?id=' in href:
                    full_ch_url = href if href.startswith("http") else tv_url + ("/" if not href.startswith("/") else "") + href
                    try:
                        ch_resp = requests.get(full_ch_url, timeout=5)
                        match = re.search(r'(https?://[^\s<>"]+?/[a-zA-Z0-9_-]+/index\.txt)', ch_resp.text)
                        if match:
                            full_path = match.group(1)
                            domain_match = re.match(r'(https?://[^/]+)', full_path)
                            if domain_match:
                                found_domain = domain_match.group(1)
                                print(f"ch.html sayfasından dinamik yakalandı: {found_domain}")
                                return found_domain
                    except:
                        continue
    except Exception as e:
        print(f"Stream domain aranırken hata: {e}")

    try:
        resp = requests.get(tv_url + "/ch.html?id=b1", timeout=5)
        match = re.search(r'https?://([a-zA-Z0-9.-]+\.cfd)', resp.text)
        if match:
            return f"https://{match.group(1)}"
    except:
        pass

    raise Exception("Stream domain hiçbir kaynaktan dinamik olarak çözülemedi!")

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
                        ch_id = match.group(1).upper()
                        txt_link = f"{stream_domain}/{ch_id.lower()}/index.txt"
                        if (channel_name if channel_name else ch_id, txt_link) not in channels:
                            channels.append((channel_name if channel_name else ch_id, txt_link))
    except Exception as e:
        print(f"Kanal verileri çekilirken hata oluştu: {e}")
    
    # Eğer statik ayrıştırma boş dönerse, eksiksiz tam kanal listesini fallback olarak yükle
    if not channels:
        print("Dinamik kanal bulunamadı, tam liste otomatik olarak yükleniyor...")
        default_ids = [
            "b1", "b1local", "b2", "b3", "b4", "bein5", "b1max", "b2max", 
            "s1", "s2", "smart1", "smart2", "tivibu", "tivibu1", "tivibu2", 
            "tivibu3", "sifirtv", "euro1", "euro2", "tabiiyedek", "tabii1", 
            "tabii2", "tabii3", "tabii4", "tabii5", "tabii6", "xexxen", "xexxen1", "b5"
        ]
        for ch_id in default_ids:
            channels.append((ch_id.upper(), f"{stream_domain}/{ch_id}/index.txt"))
            
    return channels

def create_m3u():
    tv_url = get_working_tv_url()
    print(f"Aktif TV URL: {tv_url}")
    
    stream_domain = extract_stream_domain_dynamically(tv_url)
    print(f"Kullanılacak Dinamik Stream Domain: {stream_domain}")
    
    channels = fetch_channels(stream_domain, tv_url)
    
    m3u_content = f"#EXTM3U\n# Source: {tv_url}\n# Stream Domain: {stream_domain}\n"
    for name, link in channels:
        inf = 25 if "B1" == name.upper() else 0
        m3u_content += f"#EXTINF:{inf}, {name}\n"
        m3u_content += "#EXTVLCOPT:network-caching=1000\n"
        m3u_content += f"{link}\n"
        
    with open("zeus.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print(f"zeus.m3u başarıyla oluşturuldu ve kaydedildi. Toplam kanal: {len(channels)}")

if __name__ == "__main__":
    create_m3u()
