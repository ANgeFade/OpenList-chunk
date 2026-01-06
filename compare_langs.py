import json
import os

langs_dir = r"f:\code_program\OpenList-4.1.9\OpenList-Frontend-main\src\lang"
en_dir = os.path.join(langs_dir, "en")
cn_dir = os.path.join(langs_dir, "zh-CN")

files = [
    "br.json", "drivers.json", "global.json", "home.json", "index.json",
    "indexes.json", "login.json", "manage.json", "metas.json",
    "settings.json", "settings_other.json", "shares.json",
    "storages.json", "tasks.json", "users.json"
]

def get_keys(obj, prefix=""):
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full_key = f"{prefix}.{k}" if prefix else k
            keys.add(full_key)
            keys.update(get_keys(v, full_key))
    return keys

def compare_file(filename):
    en_path = os.path.join(en_dir, filename)
    cn_path = os.path.join(cn_dir, filename)
    
    if not os.path.exists(cn_path):
        print(f"MISSING FILE: {filename}")
        return

    try:
        with open(en_path, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        with open(cn_path, 'r', encoding='utf-8') as f:
            cn_data = json.load(f)
            
        en_keys = get_keys(en_data)
        cn_keys = get_keys(cn_data)
        
        missing = en_keys - cn_keys
        if missing:
            print(f"\n[{filename}] Missing {len(missing)} keys:")
            if filename == "settings.json":
                with open('missing_keys_full.txt', 'w', encoding='utf-8') as mf:
                     for k in sorted(missing):
                        print(f"  - {k}")
                        # We need to find the value too. Retrieve it from en_data.
                        # Since k is dot notation (e.g. "a.b"), we need to traverse en_data
                        val = en_data
                        parts = k.split('.')
                        try:
                            for part in parts:
                                val = val[part]
                            mf.write(f"{k} ||| {val}\n")
                        except:
                             mf.write(f"{k} ||| [VALUE NOT FOUND]\n")
            else:
                 for k in sorted(missing):
                    print(f"  - {k}")
                
    except Exception as e:
        print(f"Error processing {filename}: {e}")

print("Start Comparison...")
for f in files:
    compare_file(f)
print("End Comparison")
