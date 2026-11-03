import UnityPy, glob, os, json

base = r"E:\Users\ah_3m\Documents\gits\Dusk City\Dusk City_Data\StreamingAssets\aa\StandaloneWindows64"
out = r"E:\Users\ah_3m\Documents\gits\Dusk City\translation\research\localization_settings.json"

def load_glob(pattern):
    files = glob.glob(os.path.join(base, pattern))
    if not files:
        return None
    return UnityPy.load(files[0])

records = []
for pattern in [
    "localization-locales*",
    "localization-settings*",
    "localization-assets-shared*",
    "*localization*settings*",
]:
    env = load_glob(pattern)
    if not env:
        continue
    bundle = os.path.basename(glob.glob(os.path.join(base, pattern))[0])
    for o in env.objects:
        if o.type.name != "MonoBehaviour":
            continue
        try:
            t = o.read_typetree()
        except Exception as e:
            continue
        name = t.get("m_Name", "")
        keys = list(t.keys())
        if any(k in str(t) for k in ["Locale", "Selector", "PlayerPref", "Startup", "LocalizationSettings"]):
            records.append({"bundle": bundle, "name": name, "keys": keys, "data": t})

with open(out, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)
print("bundles scanned, records", len(records), "->", out)
