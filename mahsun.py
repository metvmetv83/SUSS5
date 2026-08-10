import os
import re
import requests
from bs4 import BeautifulSoup

def get_active_domain():
    # Aralık üzerinden aktif domain bulma
    for i in range(216, 1000):
        domain = f"https://mahsunsports{i}.com"
        try:
            response = requests.get(domain, timeout=5)
            if response.status_code == 200:
                return domain
        except:
            pass
            
    raise RuntimeError("Belirtilen aralıkta aktif domain bulunamadı!")

def main():
    try:
        base_url = get_active_domain()
        print(f"Aktif Domain: {base_url}")
    except Exception as e:
        print(f"Hata: {e}")
        return

    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        print(f"Sayfa yüklenirken hata oluştu: {e}")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    items = soup.find_all('div', class_='mac iframeYayin')

    m3u_lines = ["#EXTM3U\n"]

    for item in items:
        data_url = item.get('data-url', '')
        if not data_url or 'androstreamlivechNone' in data_url:
            continue

        # Göreceli linkleri tam URL'ye çevirme
        if data_url.startswith('/'):
            stream_url = f"{base_url}{data_url}"
        elif not data_url.startswith('http'):
            stream_url = f"{base_url}/{data_url}"
        else:
            stream_url = data_url

        # Takım / Kanal Adı
        top_div = item.find('div', class_='mac-row-top')
        teams = top_div.find('span', class_='takimlar').text.strip() if top_div and top_div.find('span', class_='takimlar') else "Canlı Yayın"

        # Saat ve Lig Bilgisi
        bottom_div = item.find('div', class_='mac-row-bottom')
        saat = ""
        lig = ""
        if bottom_div:
            saat_span = bottom_div.find('span', class_='saat')
            lig_span = bottom_div.find('span', class_='lig')
            if saat_span:
                saat = saat_span.text.strip()
            if lig_span:
                lig = lig_span.text.strip()

        # M3U Başlık Formatı
        title = f"{teams} ({lig})" if lig else teams
        if saat and saat != "CANLI":
            title = f"[{saat}] {title}"

        group_name = lig if lig else "Canlı Yayınlar"

        m3u_lines.append(f'#EXTINF:-1 tvg-name="{teams}" group-title="{group_name}",{title}\n')
        m3u_lines.append(f'{stream_url}\n')

    with open('mahsun.m3u', 'w', encoding='utf-8') as f:
        f.writelines(m3u_lines)

    print("mahsun.m3u başarıyla oluşturuldu!")

if __name__ == '__main__':
    main()
