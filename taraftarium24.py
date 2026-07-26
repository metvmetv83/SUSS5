import re
import sys
import time
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urljoin
from playwright.sync_api import sync_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

TARAFTARIUM_DOMAIN = "https://taraftarium24.xyz/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

OUTPUT_M3U = "taraftarium24.m3u8"
OUTPUT_JSON = "taraftarium24_yayinlar.json"

def scrape_default_channel_info(page):
    print(f"\n📡 Varsayılan kanal bilgisi {TARAFTARIUM_DOMAIN} adresinden alınıyor...")
    try:
        page.goto(TARAFTARIUM_DOMAIN, timeout=180000, wait_until='domcontentloaded')
        iframe_selector = "iframe#customIframe"
        page.wait_for_selector(iframe_selector, timeout=15000)
        iframe_element = page.query_selector(iframe_selector)
        if not iframe_element:
            print("❌ Iframe bulunamadı, fallback yapılacak.")
            return None, None
        iframe_src = iframe_element.get_attribute('src')
        event_url = urljoin(TARAFTARIUM_DOMAIN, iframe_src)
        parsed_event_url = urlparse(event_url)
        stream_id = parse_qs(parsed_event_url.query).get('id', [None])[0]
        return event_url, stream_id
    except TimeoutError:
        print("❌ Ana sayfa yüklenemedi (timeout), fallback yapılacak.")
        return None, None
    except Exception as e:
        print(f"❌ Hata: {e.__class__.__name__} - {e}")
        return None, None

def extract_base_m3u8_url(page, event_url):
    try:
        page.goto(event_url, timeout=30000, wait_until='domcontentloaded')
        content = page.content()
        base_url_match = re.search(r"['\"](https?://[^'\"]+/checklist/)['\"]", content)
        if base_url_match:
            return base_url_match.group(1)
        else:
            print("❌ Base URL bulunamadı.")
            return None
    except Exception as e:
        print(f"❌ Event sayfası işlenemedi: {e}")
        return None

def scrape_all_channels(page):
    print(f"\n📡 Tüm kanallar {TARAFTARIUM_DOMAIN} adresinden çekiliyor...")
    channels = []
    try:
        page.goto(TARAFTARIUM_DOMAIN, timeout=180000, wait_until='domcontentloaded')
        page.wait_for_timeout(5000)
        mac_item_selector = ".mac[data-url]"
        elements_exist = page.evaluate(f"() => document.querySelector('{mac_item_selector}') !== null")
        if not elements_exist:
            print("❌ Kanal elemanları bulunamadı, fallback yapılacak.")
            return []
        channel_elements = page.query_selector_all(mac_item_selector)
        for element in channel_elements:
            name_element = element.query_selector(".takimlar")
            channel_name = name_element.inner_text().strip() if name_element else "İsimsiz Kanal"
            channel_name_clean = channel_name.replace('CANLI', '').strip()
            data_url = element.get_attribute('data-url')
            stream_id = None
            if data_url:
                try:
                    parsed_data_url = urlparse(data_url)
                    stream_id = parse_qs(parsed_data_url.query).get('id', [None])[0]
                except Exception:
                    pass
            
            # Logo bilgisini al (varsa)
            logo_element = element.query_selector("img")
            logo_url = logo_element.get_attribute('src') if logo_element else ""
            if logo_url and not logo_url.startswith('http'):
                if logo_url.startswith('/'):
                    logo_url = TARAFTARIUM_DOMAIN.rstrip('/') + logo_url
                else:
                    logo_url = TARAFTARIUM_DOMAIN + logo_url
            
            if stream_id:
                channels.append({
                    'name': channel_name_clean,
                    'id': stream_id,
                    'logo': logo_url,
                    'type': 'channel'
                })
        return channels
    except Exception as e:
        print(f"❌ Kanal listesi işlenemedi: {e}")
        return []

def get_channel_group(channel_name):
    channel_name_lower = channel_name.lower()
    group_mappings = {
        'BeinSports': ['bein sports', 'beın sports', ' bs', ' bein '],
        'S Sports': ['s sport'],
        'Tivibu': ['tivibu spor', 'tivibu'],
        'Exxen': ['exxen'],
        'Ulusal Kanallar': ['a spor', 'trt spor', 'trt 1', 'tv8', 'atv', 'kanal d', 'show tv', 'star tv', 'trt yıldız', 'a2'],
        'Spor': ['smart spor', 'nba tv', 'eurosport', 'sport tv', 'premier sports', 'ht spor', 'sports tv'],
        'Yarış': ['tjk tv'],
        'Belgesel': ['national geographic', 'nat geo', 'discovery', 'dmax', 'bbc earth', 'history'],
        'Film & Dizi': ['bein series', 'bein movies', 'movie smart', 'filmbox', 'sinema tv'],
        'Haber': ['haber', 'cnn', 'ntv'],
        'Diğer': ['gs tv', 'fb tv', 'cbc sport']
    }
    for group, keywords in group_mappings.items():
        for keyword in keywords:
            if keyword in channel_name_lower:
                return group
    if re.search(r'\d{2}:\d{2}', channel_name) or ' - ' in channel_name:
        return "Maç Yayınları"
    return "Diğer Kanallar"

def create_m3u_content(channels, base_m3u8_url):
    """M3U içeriği oluşturur"""
    m3u_content = []
    m3u_header_lines = [
        "#EXTM3U",
        f"#EXT-X-USER-AGENT:{USER_AGENT}",
        f"#EXT-X-ORIGIN:{TARAFTARIUM_DOMAIN.rstrip('/')}"
    ]
    
    for channel_info in channels:
        channel_name = channel_info['name']
        stream_id = channel_info['id']
        group_name = get_channel_group(channel_name)
        logo = channel_info.get('logo', '')
        m3u8_link = f"{base_m3u8_url}{stream_id}.m3u8"
        
        m3u_content.append(f'#EXTINF:-1 tvg-logo="{logo}" tvg-name="{channel_name}" group-title="{group_name}",{channel_name}')
        m3u_content.append(f'#EXTVLCOPT:http-user-agent={USER_AGENT}')
        m3u_content.append(f'#EXTVLCOPT:http-referrer={TARAFTARIUM_DOMAIN}')
        m3u_content.append(m3u8_link)
        m3u_content.append('')  # Boş satır
    
    return m3u_header_lines, m3u_content

def create_json_output(channels, base_m3u8_url, default_stream_id):
    """JSON çıktısı oluşturur"""
    channels_with_url = []
    for channel in channels:
        channel_copy = channel.copy()
        channel_copy['url'] = f"{base_m3u8_url}{channel['id']}.m3u8"
        channel_copy['user_agent'] = USER_AGENT
        channel_copy['referrer'] = TARAFTARIUM_DOMAIN
        channel_copy['group'] = get_channel_group(channel['name'])
        channels_with_url.append(channel_copy)
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "Taraftarium24",
        "base_url": base_m3u8_url,
        "domain": TARAFTARIUM_DOMAIN,
        "user_agent": USER_AGENT,
        "default_stream_id": default_stream_id,
        "total_streams": len(channels),
        "channels": channels_with_url
    }
    
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {OUTPUT_JSON} başarıyla oluşturuldu!")

def main():
    print("🚀 Taraftarium24 M3U8 Kanal İndirici Başlatılıyor...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        default_event_url, default_stream_id = scrape_default_channel_info(page)
        
        if not default_event_url:
            print("⚠️ Fallback: Base URL ve kanal listesi manuel olarak girilecek.")
            base_m3u8_url = "https://andro.okan11gote12sokan.cfd/checklist/"
            channels = [{'name': 'Varsayılan Kanal', 'id': default_stream_id or 'androstreamlivebs1', 'logo': '', 'type': 'channel'}]
        else:
            base_m3u8_url = extract_base_m3u8_url(page, default_event_url)
            channels = scrape_all_channels(page)
            
            if not channels:
                print("⚠️ Kanal listesi boş, varsayılan kanal kullanılacak.")
                channels = [{'name': 'Varsayılan Kanal', 'id': default_stream_id or 'androstreamlivebs1', 'logo': '', 'type': 'channel'}]
        
        if base_m3u8_url and channels:
            # M3U oluştur
            m3u_header_lines, m3u_content = create_m3u_content(channels, base_m3u8_url)
            
            with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
                f.write("\n".join(m3u_header_lines) + "\n")
                f.write("\n".join(m3u_content))
            print(f"\n📂 {len(channels)} kanal '{OUTPUT_M3U}' dosyasına kaydedildi.")
            
            # JSON oluştur
            create_json_output(channels, base_m3u8_url, default_stream_id)
            
            # Özet
            print("\n📊 ÖZET:")
            print(f"   Kanal: {len(channels)}")
            print(f"   Base URL: {base_m3u8_url}")
            print(f"   M3U Dosyası: {OUTPUT_M3U}")
            print(f"   JSON Dosyası: {OUTPUT_JSON}")
        else:
            print("\n❌ Geçerli M3U8 linki oluşturulamadı.")

        browser.close()
        print("🎉 İşlem tamamlandı!")

if __name__ == "__main__":
    main()
