# bing-rewards

Otomasi pencarian Bing untuk mengumpulkan poin **Microsoft Rewards**.
Script membuka browser (Chrome/Edge), mengetik kata kunci acak dari `bing_rewards/data/keywords.txt`, lalu menutup browser kembali — bisa dijalankan untuk banyak profil sekaligus.

> Fork dari [jack-mil/bing-rewards](https://github.com/jack-mil/bing-rewards) dengan tambahan dukungan multi-profil Edge, `--list-profiles`, dan `--clean-profiles`.

## Kebutuhan

- Windows (Edge/Chrome terpasang)
- Python 3.10–3.15
- Akun Microsoft yang sudah login di profil browser yang dipakai

## Instalasi

```powershell
git clone https://github.com/euniversee/bing-rewards.git
cd bing-rewards
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

Atau kalau pakai [uv](https://docs.astral.sh/uv/):

```powershell
uv sync
```

## Cara Pakai Dasar

```powershell
# 33 desktop + 23 mobile search (default)
python -m bing_rewards

# 20 pencarian desktop saja di profil Default
python -m bing_rewards -c 20 -d

# Pakai Edge dan beberapa profil sekaligus (berurutan)
python -m bing_rewards --exe "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --profile "Default" "Profile 6" "Profile 8" "Profile 9" "Profile 16" -c 20 -d
```

Perintah `bing-rewards` juga tersedia setelah instalasi (sama dengan `python -m bing_rewards`).

## Daftar Command

| Command | Fungsi |
|---|---|
| `-c, --count N` | Jumlah search per mode (menimpa config) |
| `-d, --desktop` | Hanya desktop search |
| `-m, --mobile` | Hanya mobile search (user-agent HP) |
| `-b, --bing` | Pakai kalau search engine default browser = Bing |
| `--exe PATH` | Path lengkap browser (Chrome/Edge) |
| `--profile "Default" "Profile 6" ...` | Jalankan berurutan untuk tiap profil |
| `--list-profiles` | Tampilkan daftar profil Edge + email + ukuran folder |
| `--clean-profiles` | Hapus cache semua profil Edge kecuali Default |
| `--load-delay SEC` | Jeda tunggu browser terbuka (detik) |
| `--search-delay MIN[,MAX]` | Jeda antar search, bisa satu angka atau range acak |
| `-n, --dryrun` | Coba semua tanpa benar-benar melakukan search |
| `--open-rewards` / `--no-open-rewards` | Buka halaman rewards di akhir |
| `--window` / `--no-window` | Buka window browser atau tidak |
| `-X, --exit` / `--no-exit` | Tutup browser setelah searching selesai |
| `--ime` | Untuk pengguna IME Windows: paksa keyboard ke English (SHIFT) |
| `--version` | Cek versi |

### Hotkey saat berjalan

| Tombol | Fungsi |
|---|---|
| `ESC` | Stop semua pencarian |
| `F9` | Lewati profil yang sedang berjalan, lanjut ke profil berikutnya |

## Konfigurasi

Saat pertama dijalankan, file config dibuat otomatis di:

```
%APPDATA%\bing-rewards\config.json
```

Nilai di config dipakai sebagai default, tapi argumen command line selalu menang. Contoh isi:

```json
{
  "desktop_count": 33,
  "mobile_count": 23,
  "load_delay": 1.5,
  "search_delay": 6.0,
  "browser_path": "chrome",
  "open_rewards": false,
  "window": true,
  "exit": true,
  "profile": ["Default"]
}
```

## Tips

- Jangan set `--search-delay` terlalu cepat; search bisa tidak dihitung oleh Bing.
- Gunakan `--list-profiles` dulu untuk tahu nama direktori profil Edge yang valid.
- Kalau cache profil membengkak, jalankan `--clean-profiles` (profil `Default` tidak dihapus cachenya).
- Test dulu dengan `-n` (dryrun) kalau baru mengubah command.

## Peringatan

Penggunaan otomasi seperti ini berpotensi melanggar [Ketentuan Layanan Microsoft Rewards](https://www.microsoft.com/servicesagreement). Gunakan dengan risiko sendiri — penangguhan akun adalah tanggung jawab pengguna.

## Lisensi

MIT
