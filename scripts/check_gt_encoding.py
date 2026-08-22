from pathlib import Path

path = Path("data/catalog/ground_truth/Unihack__Expected_Output_-_Delivery_Format.csv")
with open(path, "rb") as f:
    raw = f.read()

print("File length:", len(raw))

# Check with utf-8 vs cp1252 / latin-1
for enc in ["utf-8", "cp1252", "latin-1"]:
    try:
        decoded = raw.decode(enc)
        print(f"Decoded successfully with {enc}!")
        lines = decoded.splitlines()
        # Find BRAND_NAME in header
        headers = [h.strip() for h in lines[0].split(",")]
        brand_idx = headers.index("BRAND_NAME")
        mfg_idx = headers.index("MANUFACTURER_NAME")
        print(f"Header indices: BRAND_NAME={brand_idx}, MANUFACTURER_NAME={mfg_idx}")
        print(f"Line 2: Mfg={lines[1].split(',')[mfg_idx]}, Brand={lines[1].split(',')[brand_idx]}")
        print(f"Line 3: Mfg={lines[2].split(',')[mfg_idx]}, Brand={lines[2].split(',')[brand_idx]}")
    except Exception as e:
        print(f"Failed with {enc}: {e}")
