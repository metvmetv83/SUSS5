import os
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Eğer domaini manuel sabitlemek isterseniz buraya yazabilirsiniz (Örn: "https://mahsunsports80.xyz")
# Boş bırakırsanız otomatik arama yapar.
DOMAIN_OVERRIDE = "https://mahsunsports80.xyz"

def get_active_domain(playwright):
    if DOMAIN_OVERRIDE:
        return DOMAIN_OVERRIDE

    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    page = context.new_page()

    # Genişletilmiş aralık kontrolü
    for i in range(1, 1000):
        domain = f"https://mahsunsports{i}.xyz"
        try:
            response = page.goto(domain, timeout=3000, wait_until="domcontentloaded")
            if response and response.status == 200:
                browser.close()
                return domain
        except:
            pass

    browser.close()
    raise RuntimeError("Aktif domain bulunamadı!")

def main():
    with sync_playwright() as p:
        try:
            base_url = get_active_domain(p)
            print(f"Aktif Domain: {base_url}")
        except Exception as e:
            print(f"Hata: {e}")
            return

        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        try:
            page.goto(base_url, timeout=15000, wait_until="networkidle")
            time.sleep(3) # İçeriklerin yüklenmesi için bekleme
            html_content = page.content()
        except Exception as e:
            print(f"Sayfa yüklenirken hata oluştu: {e}")
            browser.close()
            return

        browser.close()

    soup = BeautifulSoup(html_content, 'html.parser')
    items = soup.find_all('div', class_='mac iframeYayin')

    m3u_lines = ["#EXTM3U\n"]

    for item in items:
        data_url = item.get('data-url', '')
        if not data_url or 'androstreamlivechNone' in data_url:
            continue

        if data_url.startswith('/'):
            stream_url = f"{base_url}{data_url}"
        elif not data_url.startswith('http'):
            stream_url = f"{base_url}/{data_url}"
        else:
            stream_url = data_url

        top_div = item.find('div', class_='mac-row-top')
        teams = top_div.find('span', class_='takimlar').text.strip() if top_div and top_div.find('span', class_='takimlar') else "Canlı Yayın"

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
