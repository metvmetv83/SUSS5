import concurrent.futures
import requests

def check_url(num):
    # Sayının değiştiği alan adı yapısı
    url = f"https://zeustv{num}.cfd/"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        # İstek atılıyor, zaman aşımı 3 saniye olarak ayarlandı
        response = requests.get(url, headers=headers, timeout=3, allow_redirects=True)
        
        # 200 OK veya yönlendirme alan başarılı yanıtlar kontrol edilir
        if response.status_code == 200:
            print(f"[+] Çalışan Link Bulundu: {url}")
            return url
    except requests.RequestException:
        # Bağlantı hatası, zaman aşımı vb. durumlar sessizce geçilir
        pass
    return None

def main():
    print("Zeus TV aktif link taraması başlatılıyor...")
    working_urls = []
    
    # Taranacak sayı aralığı (İhtiyacınıza göre artırabilirsiniz: örn. 1 - 300)
    start_range = 1
    end_range = 400
    
    # Hızlı tarama için çoklu iş parçacığı (ThreadPool) kullanılıyor
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(check_url, i) for i in range(start_range, end_range + 1)]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                working_urls.append(result)
    
    # Sonuçları zeus.txt dosyasına yazdır
    if working_urls:
        with open("zeus.txt", "w", encoding="utf-8") as f:
            for url in working_urls:
                f.write(url + "\n")
        print(f"\n[BAŞARILI] Toplam {len(working_urls)} çalışan link 'zeus.txt' dosyasına kaydedildi!")
    else:
        print("\n[-] Belirtilen aralıkta çalışan link bulunamadı.")

if __name__ == "__main__":
    main()
