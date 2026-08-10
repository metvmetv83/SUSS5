import os
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DOMAIN_OVERRIDE = "https://mahsunsports80.xyz"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()

        m3u8_links = []

        # İstekleri yakalayarak asıl .m3u8 linklerini yakalama
        def handle_request(request):
            if ".m3u8" in request.url:
                if request.url not in m3u8_links:
                    m3u8_links.append(request.url)

        page.on("request", handle_request)

        try:
            print(f"Ana sayfa yükleniyor: {DOMAIN_OVERRIDE}")
            page.goto(DOMAIN_OVERRIDE, timeout=15000, wait_until="networkidle")
            time.sleep(3)
            html_content = page.content()
        except Exception as e:
            print(f"Ana sayfa yüklenirken hata oluştu: {e}")
            browser.close()
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
                event_url = f"{DOMAIN_OVERRIDE}{data_url}"
            elif not data_url.startswith('http'):
                event_url = f"{DOMAIN_OVERRIDE}/{data_url}"
            else:
                event_url = data_url

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

            title = f"{teams} ({lig})" if lig else teams
            if saat and saat != "CANLI":
                title = f"[{saat}] {title}"

            group_name = lig if lig else "Canlı Yayınlar"

            # Her bir yayın sayfasını arka planda ziyaret edip gerçek .m3u8 linkini yakalayalım
            stream_url = event_url
            try:
                sub_page = context.new_page()
                sub_page.goto(event_url, timeout=8000, wait_until="networkidle")
                time.sleep(2)
                
                # Sayfa içi ağ trafiğinden .m3u8 yakalama
                found_m3u8 = None
                for req in sub_page.context.requests if hasattr(sub_page.context, 'requests') else []:
                    if ".m3u8" in req.url:
                        found_m3u8 = req.url
                        break
                sub_page.close()
                
                if found_m3u8:
                    stream_url = found_m3u8
            except:
                pass

            m3u_lines.append(f'#EXTINF:-1 tvg-name="{teams}" group-title="{group_name}",{title}\n')
            m3u_lines.append(f'{stream_url}\n')

        browser.close()

    with open('mahsun2.m3u', 'w', encoding='utf-8') as f:
        f.writelines(m3u_lines)

    print("mahsun2.m3u başarıyla oluşturuldu!")

if __name__ == '__main__':
    main()
