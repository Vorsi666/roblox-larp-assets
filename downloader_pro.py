import requests, json, time
from pathlib import Path

CATALOG = "https://catalog.roblox.com/v1/search/items"
BATCH = "https://assetdelivery.roblox.com/v2/assets/batch"
THUMB = "https://thumbnails.roblox.com/v1/assets"
DETAILS = "https://economy.roblox.com/v2/assets/{}/details"
DB_FILE = Path("downloaded_pro.json")

def load_db():
    return set(json.loads(DB_FILE.read_text())) if DB_FILE.exists() else set()

def save_db(db):
    DB_FILE.write_text(json.dumps(list(db)))

def get_cookie():
    p = Path("cookie.txt")
    if not p.exists(): return None
    raw = p.read_text().strip()
    return raw.replace(".ROBLOSECURITY=", "") if raw.startswith(".ROBLOSECURITY=") else raw

def headers(cookie=None):
    h = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    if cookie: h["Cookie"] = f".ROBLOSECURITY={cookie}"
    return h

def get_details(aid, cookie):
    try:
        r = requests.get(DETAILS.format(aid), headers=headers(cookie), timeout=20)
        if r.status_code == 200:
            data = r.json()
            return data.get("Name", "Tanpa Nama"), data.get("Creator", {}).get("Name", "Tanpa Pembuat"), data.get("PriceInRobux") or 0
    except: pass
    return "Tanpa Nama", "Tanpa Pembuat", 0

def fetch_catalog(limit, cookie):
    print(f"[*] Mengambil katalog limited (target: {limit})...")
    items = []
    cursor = None
    filters = [{"category": "Accessories", "salesTypeFilter": 1}, {"category": "Collectibles", "salesTypeFilter": 1}]
    
    for f in filters:
        while len(items) < limit:
            params = dict(f)
            params.update({"limit": 30, "sortType": "Relevance"})
            if cursor: params["cursor"] = cursor
            try:
                r = requests.get(CATALOG, params=params, headers=headers(), timeout=30)
                if r.status_code != 200: break
                data = r.json()
                batch = data.get("data", [])
                if not batch: break
                for item in batch:
                    aid = item.get("id")
                    name, creator, price = get_details(aid, cookie)
                    if name != "Tanpa Nama":
                        items.append({"id": aid, "name": name, "creator": creator, "price": price})
                cursor = data.get("nextPageCursor")
                if not cursor: break
                print(f"  -> Terkumpul: {len(items)}", end="\r")
                time.sleep(0.5)
            except Exception as e:
                print(f"\n[-] Error: {e}")
                break
        if len(items) >= limit: break
    print(f"\n[*] Total kandidat valid: {len(items)}")
    return items[:limit]

def download_asset(aid, cookie, out_dir):
    payload = [{"assetId": int(aid), "requestId": f"req-{aid}"}]
    try:
        r = requests.post(BATCH, headers=headers(cookie), json=payload, timeout=30)
        if r.status_code == 200:
            res = r.json()
            if res and res[0].get("location"):
                loc = res[0]["location"]
                ext = ".rbxm" if ".rbxm" in loc else (".png" if ".png" in loc else ".jpg")
                target = out_dir / "assets" / f"{aid}{ext}"
                target.parent.mkdir(parents=True, exist_ok=True)
                dl = requests.get(loc, stream=True, timeout=60)
                if dl.status_code == 200:
                    with open(target, "wb") as f:
                        for chunk in dl.iter_content(8192): f.write(chunk)
                    return "success", ext
            err = res[0].get("errors", [{}])[0].get("message", "Gagal")
            return "gagal", err
        return "gagal", f"HTTP {r.status_code}"
    except Exception as e:
        return "gagal", str(e)

def download_thumb(aid, out_dir):
    target = out_dir / "thumbs" / f"{aid}.png"
    if target.exists(): return target
    try:
        r = requests.get(THUMB, params={"assetIds": aid, "size": "420x420", "format": "Png"}, headers=headers(), timeout=30)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data and data[0].get("imageUrl"):
                img = requests.get(data[0]["imageUrl"], timeout=30)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(img.content)
                return target
    except: pass
    return None

def main():
    limit = 500
    out_dir = Path("RobloxMasterData")
    out_dir.mkdir(exist_ok=True)
    cookie = get_cookie()
    if not cookie:
        print("[-] Cookie tidak ditemukan di cookie.txt!")
        return

    db = load_db()
    items = fetch_catalog(limit, cookie)
    
    processed = success = skipped = 0
    for i, item in enumerate(items, 1):
        aid = item["id"]
        if aid in db:
            skipped += 1
            continue

        print(f"[{i}/{len(items)}] ID: {aid} | {item['name'][:20]} | {item['creator'][:15]} | Rp{item['price']}")
        status, msg = download_asset(aid, cookie, out_dir)
        thumb = download_thumb(aid, out_dir)
        
        if status == "success":
            print(f"  [+] Sukses 3D ({msg}) | Thumb: {'OK' if thumb else 'Gagal'}")
            db.add(aid)
            save_db(db)
            success += 1
        else:
            print(f"  [-] Gagal: {msg} | Thumb: {'OK' if thumb else 'Gagal'}")
            if thumb:
                db.add(aid)
                save_db(db)
        processed += 1
        time.sleep(0.8)

    print(f"\n[*] SELESAI. Diproses: {processed} | Sukses 3D: {success} | Skip: {skipped}")
    print(f"[*] Folder: {out_dir.absolute()}")

if __name__ == "__main__":
    main()
