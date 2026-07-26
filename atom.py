import requests
import re
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#  AtomSporTV  –  Canlı Maç + TV Kanalları M3U
# ─────────────────────────────────────────────
START_URL    = "https://url24.link/AtomSporTV"
MATCHES_URL  = "https://teletv5.top/load/matches.php"
LOGO_BASE    = "https://im.mackolik.com/img/logo/buyuk"
OUTPUT_FILE  = "atom_mac.m3u"

# YENI: mac linkleri artik oncelikle bu endpoint'ten direkt cekiliyor.
# (Sayfa HTML'i statik olarak taraninca bu URL hic bulunamiyordu, cunku
# sayfaya JS ile dinamik olarak ekleniyor - requests JS calistirmiyor.)
CINEMA_URL = "https://streamsport365.com/cinema"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RESET  = "\033[0m"

headers = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'tr-TR,tr;q=0.8',
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': 'https://url24.link/'
}

TV_CHANNELS = [
    ("bein-sports-1", "BEIN SPORTS 1", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/BeIN_Sports_1_HD.svg/200px-BeIN_Sports_1_HD.svg.png"),
    ("bein-sports-2", "BEIN SPORTS 2", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/BeIN_Sports_2_HD.svg/200px-BeIN_Sports_2_HD.svg.png"),
    ("bein-sports-3", "BEIN SPORTS 3", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/BeIN_Sports_3_HD.svg/200px-BeIN_Sports_3_HD.svg.png"),
    ("bein-sports-4", "BEIN SPORTS 4", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/BeIN_Sports_4_HD.svg/200px-BeIN_Sports_4_HD.svg.png"),
    ("s-sport",       "S SPORT", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png"),
    ("s-sport-2",     "S SPORT 2", "https://upload.wikimedia.org/wikipedia/commons/thumb/2/20/S_Sport_logo.svg/200px-S_Sport_logo.svg.png"),
    ("trt-spor",      "TRT SPOR", "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/TRT_Spor_logo.svg/200px-TRT_Spor_logo.svg.png"),
    ("aspor",         "ASPOR", "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/A_Spor_logo.svg/200px-A_Spor_logo.svg.png"),
]

def get_base_domain():
    try:
        r1 = requests.get(START_URL, headers=headers, allow_redirects=False, timeout=10)
        if 'location' in r1.headers:
            r2 = requests.get(r1.headers['location'], headers=headers, allow_redirects=False, timeout=10)
            if 'location' in r2.headers:
                domain = r2.headers['location'].strip().rstrip('/')
                return domain
    except Exception:
        pass
    return "https://www.atomsportv510.top"

def normalize_logo(src):
    if not src: return ""
    if src.startswith("http"): return src
    if src.startswith("//"): return "https:" + src
    return LOGO_BASE + "/" + src.lstrip("/")

def get_matches():
    print(f"Maçlar çekiliyor → {MATCHES_URL}")
    try:
        resp = requests.get(MATCHES_URL, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')
        matches = []
        skip_words = {'futbol', 'futbol tr', 'futboi', 'günün maçı'}

        for a in soup.find_all('a', href=True):
            href = a['href']
            mid = re.search(r'matches\?id=([a-f0-9]+)', href)
            if not mid: continue
            match_id = mid.group(1)

            imgs = a.find_all('img')
            home_logo = normalize_logo(imgs[0]['src']) if len(imgs) >= 1 else ""
            away_logo = normalize_logo(imgs[1]['src']) if len(imgs) >= 2 else ""

            lines = [l.strip() for l in a.get_text('\n').splitlines() if l.strip() and l.strip().lower() not in skip_words]
            saat, lig, home_team, away_team = '', '', '', ''
            for line in lines:
                if '|' in line and not saat:
                    parts = line.split('|', 1)
                    saat, lig = parts[0].strip(), parts[1].strip()
                elif saat and not home_team: home_team = line
                elif saat and home_team and not away_team: away_team = line

            matches.append({
                'id': match_id,
                'home': home_team or "Ev Sahibi",
                'away': away_team or "Deplasman",
                'home_logo': home_logo,
                'away_logo': away_logo,
                'logo': home_logo or away_logo,
                'time': saat,
                'league': lig or "Diğer Maçlar"
            })
        return matches
    except Exception as e:
        print(f"Hata: {e}")
        return []


def _extract_url_field(text):
    """JSON metninde "URL" veya "url" alanini bulur, escape'leri temizler."""
    for pat in [r'"URL"\s*:\s*"([^"]+)"', r'"url"\s*:\s*"([^"]+)"']:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).replace('\\/', '/').replace('\\', '')
    return None


def get_m3u8_direct(resource_id, base_domain):
    """
    YENI/ONCELIKLI YONTEM: cinema endpoint'ini match id ile DOGRUDAN cagirir.
    Eskiden sayfa HTML'i taranarak bu URL bulunmaya calisiliyordu, ama
    sayfaya JS ile dinamik olarak ekleniyor - requests (JS calistirmiyor)
    bunu hicbir zaman goremiyordu, tum maclar bu yuzden basarisiz oluyordu.
    """
    try:
        h = headers.copy()
        h['Referer'] = f"{base_domain}/matches?id={resource_id}"
        h['Accept'] = 'application/json, text/plain, */*'
        r = requests.get(CINEMA_URL, params={'id': resource_id}, headers=h, timeout=10)
        if not r.ok:
            return None

        try:
            data = r.json()
            url = data.get('URL') or data.get('url')
            if url:
                return url.replace('\\/', '/')
        except ValueError:
            # Content-Type JSON olarak gelmemis olabilir, metinden regex ile dene
            url = _extract_url_field(r.text)
            if url:
                return url
    except Exception as e:
        print(f"  (direkt cinema cagrisi basarisiz: {e})")
    return None


def get_m3u8_scrape_fallback(resource_id, base_domain):
    """ESKI YONTEM - yedek olarak korunuyor (direkt yontem basarisiz olursa)."""
    try:
        h = headers.copy()
        h['Referer'] = f"{base_domain}/"
        page_url = f"{base_domain}/matches?id={resource_id}"
        resp = requests.get(page_url, headers=h, timeout=10)
        target_text = resp.text

        iframes = re.findall(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', target_text, re.IGNORECASE)
        for iframe_url in iframes:
            try:
                h['Referer'] = page_url
                r_iframe = requests.get(iframe_url, headers=h, timeout=10)
                target_text += "\n" + r_iframe.text
            except Exception:
                pass

        embed_urls = re.findall(r'["\'](https?://[^"\']+/cinema[^"\']*)["\']|["\'](https?://[^"\']+/embed[^"\']*)["\']', target_text)
        for group in embed_urls:
            for eu in group:
                if eu:
                    try:
                        h['Referer'] = page_url
                        r_emb = requests.get(eu, headers=h, timeout=5)
                        target_text += "\n" + r_emb.text
                    except Exception:
                        pass

        scripts = re.findall(r'src=["\'](https?://[^"\']+)["\']', target_text)
        for scr in scripts:
            if any(k in scr for k in ["load", "get", "stream", "player", "data"]):
                try:
                    r_scr = requests.get(scr, headers=h, timeout=5)
                    target_text += "\n" + r_scr.text
                except Exception:
                    pass

        fetch_matches = re.findall(r'fetch\s*\(\s*["\']([^"\']+)["\']', target_text)
        for fetch_url in fetch_matches:
            f_url = fetch_url.strip()
            if not f_url.startswith("http"):
                f_url = base_domain + "/" + f_url.lstrip("/")
            if resource_id not in f_url:
                f_url += resource_id
            try:
                h['Origin'] = base_domain
                r_fetch = requests.get(f_url, headers=h, timeout=5)
                target_text += "\n" + r_fetch.text
            except Exception:
                pass

        for pat in [r'"URL"\s*:\s*"([^"]+)"', r'"deismackanal":"(.*?)"', r'"stream":\s*"(.*?)"', r'"url":\s*"(.*?\.m3u8[^"]*)"', r'(https?://[^\s"\']+\.m3u8[^\s"\']*)']:
            mm = re.search(pat, target_text, re.IGNORECASE)
            if mm:
                found = mm.group(1).replace('\\/', '/').replace('\\', '')
                if found.startswith("http"):
                    return found
        return None
    except Exception:
        return None


def get_m3u8(resource_id, base_domain):
    """Once dogrudan/hizli yontemi dener, basarisiz olursa eski taramaya duser."""
    url = get_m3u8_direct(resource_id, base_domain)
    if url:
        return url
    return get_m3u8_scrape_fallback(resource_id, base_domain)


def build_m3u(working_matches, working_channels, base_domain):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n")

        for m in working_matches:
            display_name = f"{m['home']} - {m['away']} [{m['time']}]"
            group_title = f"CANLI MAÇLAR - {m['league']}"

            f.write(f'#EXTINF:-1 tvg-logo="{m["logo"]}" group-title="{group_title}",{display_name}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}\n')
            f.write(f'#EXTVLCOPT:http-referrer={base_domain}/\n')
            f.write(f"{m['url']}\n\n")

        for ch in working_channels:
            f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="TV Kanalları",{ch["name"]}\n')
            f.write(f'#EXTVLCOPT:http-user-agent={headers["User-Agent"]}\n')
            f.write(f'#EXTVLCOPT:http-referrer={base_domain}/\n')
            f.write(f"{ch['url']}\n\n")

    print(f"\n{GREEN}[✓] {OUTPUT_FILE} başarıyla oluşturuldu.{RESET}")


def main():
    print(f"\n{GREEN}AtomSporTV M3U Oluşturucu Başlatıldı...{RESET}")
    base_domain = get_base_domain()
    print(f"Ana Domain: {base_domain}")

    matches = get_matches()
    working_matches = []
    print(f"\n{YELLOW}Maçlar test ediliyor...{RESET}")
    for m in matches:
        url = get_m3u8(m['id'], base_domain)
        if url:
            m['url'] = url
            working_matches.append(m)
            print(f"  ✓ {m['home']} vs {m['away']}")
        else:
            print(f"  ✗ {m['home']} vs {m['away']}")

    tv_items = []
    print(f"\n{YELLOW}Kanallar test ediliyor...{RESET}")
    for cid, name, logo in TV_CHANNELS:
        url = get_m3u8(cid, base_domain)
        if url:
            tv_items.append({'name': name, 'logo': logo, 'url': url})
            print(f"  ✓ {name}")

    build_m3u(working_matches, tv_items, base_domain)


if __name__ == "__main__":
    main()
