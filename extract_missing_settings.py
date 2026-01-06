import json
import os

langs_dir = r"f:\code_program\OpenList-4.1.9\OpenList-Frontend-main\src\lang"
en_path = os.path.join(langs_dir, "en", "settings.json")
cn_path = os.path.join(langs_dir, "zh-CN", "settings.json")

with open(en_path, 'r', encoding='utf-8') as f:
    en_data = json.load(f)
with open(cn_path, 'r', encoding='utf-8') as f:
    cn_data = json.load(f)

missing_keys = {}
for k, v in en_data.items():
    if k not in cn_data:
        missing_keys[k] = v

with open('missing_settings.txt', 'w', encoding='utf-8') as f:
    for k, v in missing_keys.items():
        f.write(f"{k} ||| {v}\n")
