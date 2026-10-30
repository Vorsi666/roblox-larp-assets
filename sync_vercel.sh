#!/data/data/com.termux/files/usr/bin/bash
echo "[*] Memulai proses unduh aset..."
python downloader_pro.py
echo "[*] Menyusun folder aset..."
mkdir -p assets/items assets/thumbs
mv RobloxMasterData/assets/* assets/items/ 2>/dev/null
mv RobloxMasterData/thumbs/* assets/thumbs/ 2>/dev/null
echo "[*] Push ke GitHub..."
git add .
git commit -m "Auto-sync Roblox Assets $(date +'%Y-%m-%d %H:%M')"
git push origin main
echo "[*] Selesai! Vercel akan otomatis melakukan deploy ulang."
