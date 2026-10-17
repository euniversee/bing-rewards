import os
import json
import time
import random
import urllib.parse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from webdriver_manager.microsoft import EdgeChromiumDriverManager

WORDS_FILE = Path(__file__).parent / 'bing_rewards' / 'data' / 'keywords.txt'

def get_words():
    with open(WORDS_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_profiles():
    local_state_path = Path(os.environ['LOCALAPPDATA']) / 'Microsoft' / 'Edge' / 'User Data' / 'Local State'
    if not local_state_path.exists():
        return []
    
    with open(local_state_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    profiles = []
    info_cache = data.get('profile', {}).get('info_cache', {})
    for directory, info in info_cache.items():
        profiles.append({
            'directory': directory,
            'name': info.get('name', 'Unknown'),
            'email': info.get('user_name', ''),
            'status': 'Pending'
        })
    return profiles

def get_score(driver):
    try:
        time.sleep(3)
        selectors = [
            "span.points-container[data-tag='RewardsHeader.Counter']",
            "span#id_rc",
            "span.points-container"
        ]
        
        for sel in selectors:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, sel)
                text = elem.text.strip().replace(',', '').replace('.', '')
                if text.isdigit():
                    return int(text)
            except:
                continue
        return -1
    except:
        return -1

def run_profile(profile, words):
    print(f"\n---> Menjalankan profil: {profile['name']} ({profile['email']})")
    print("Menutup proses Edge di latar belakang (jika ada) agar profil bisa diakses...")
    import subprocess
    subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe', '/T'], capture_output=True)
    time.sleep(2)
    
    user_data_dir = Path(os.environ['LOCALAPPDATA']) / 'Microsoft' / 'Edge' / 'User Data'
    
    options = EdgeOptions()
    options.binary_location = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument(f"profile-directory={profile['directory']}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = EdgeService(EdgeChromiumDriverManager().install())
        driver = webdriver.Edge(service=service, options=options)
    except Exception as e:
        print(f"\nERROR: Gagal membuka Edge. Detail error:\n{e}")
        print("Pastikan tidak ada jendela Edge yang nyangkut, atau coba restart komputer.")
        return profile['status']

    try:
        print("Membuka bing.com...")
        driver.get("https://www.bing.com/")
        time.sleep(5)
        
        initial_score = get_score(driver)
        if initial_score == -1:
            print("Gagal menemukan elemen skor. Pastikan profil ini sudah login di Bing Rewards.")
            return "Login Error"
            
        print(f"Skor awal: {initial_score}")
        
        print("Melakukan pencarian pertama (TEST)...")
        first_query = random.choice(words)
        driver.get("https://www.bing.com/search?q=" + urllib.parse.quote_plus(first_query))
        time.sleep(8) # Jeda untuk memastikan skor server update
        
        new_score = get_score(driver)
        print(f"Skor setelah pencarian pertama: {new_score}")
        
        if new_score != -1 and new_score <= initial_score:
            print("Skor TIDAK BERTAMBAH. Profil ini sudah MAX atau terkena cooldown 15 menit.")
            return "MAX"
            
        print("Skor bertambah! Melanjutkan sisa 32 pencarian...")
        
        for i in range(32):
            query = random.choice(words)
            print(f"[{i+2}/33] Mencari: {query}")
            driver.get("https://www.bing.com/search?q=" + urllib.parse.quote_plus(query))
            delay = random.uniform(6.0, 8.0)
            time.sleep(delay)
            
        print("Selesai untuk Desktop! Status: Done")
        return "Done"
        
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        return "Error"
    finally:
        driver.quit()

def main():
    words = get_words()
    profiles = get_profiles()
    
    if not profiles:
        print("Tidak menemukan profil Edge.")
        return

    while True:
        print("\n" + "="*60)
        print("     MENU BING REWARDS SMART SELENIUM (AUTO-CHECK SCORE)")
        print("="*60)
        for idx, p in enumerate(profiles):
            print(f"{idx+1}. [{p['status']}] {p['name']} ({p['email']})")
        print("0. Keluar")
        print("="*60)
        
        choice = input("Pilih nomor profil untuk dijalankan (0 untuk keluar): ")
        
        if choice == '0':
            break
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(profiles):
                new_status = run_profile(profiles[idx], words)
                profiles[idx]['status'] = new_status
            else:
                print("Pilihan tidak valid.")
        except ValueError:
            print("Masukkan angka yang benar.")

if __name__ == '__main__':
    main()
