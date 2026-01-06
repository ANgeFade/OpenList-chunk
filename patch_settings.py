import json
import os

langs_dir = r"f:\code_program\OpenList-4.1.9\OpenList-Frontend-main\src\lang"
en_path = os.path.join(langs_dir, "en", "settings.json")
cn_path = os.path.join(langs_dir, "zh-CN", "settings.json")

# Known translations for the missing keys
TRANSLATIONS = {
    "115_open_temp_dir": "打开115网盘临时目录",
    "allowed_drivers": "允许加载的存储驱动",
    "archive_preview_file_size_limit": "压缩包预览文件大小限制",
    "chunked_upload_chunk_size": "分片上传分片大小",
    "offline_download_task_threads_num": "离线下载任务并发数",
    "offline_download_transfer_task_threads_num": "离线下载传输并发数",
    "ldap_skip_tls_verify": "LDAP跳过TLS验证",
    "max_client_download_speed": "客户端最大下载速度",
    "max_client_upload_speed": "客户端最大上传速度",
    "max_server_download_speed": "服务端最大下载速度",
    "max_server_upload_speed": "服务端最大上传速度",
    "ocr_api": "OCR识别接口地址",
    "sso_auto_register": "SSO登录自动注册"
}

with open(en_path, 'r', encoding='utf-8') as f:
    en_data = json.load(f)
    
if os.path.exists(cn_path):
    with open(cn_path, 'r', encoding='utf-8') as f:
        cn_data = json.load(f)
else:
    cn_data = {}

added_count = 0

def merge_dict(en_node, cn_node):
    global added_count
    for k, v in en_node.items():
        # Check if we have a translation for this key
        trans = TRANSLATIONS.get(k, None)
        
        if k not in cn_node:
            # Case 1: Key is missing
            if isinstance(v, dict):
                cn_node[k] = {}
                merge_dict(v, cn_node[k])
            else:
                cn_node[k] = trans if trans else v
                added_count += 1
                print(f"Added [Missing]: {k}")
        else:
            # Case 2: Key exists
            if isinstance(v, dict) and isinstance(cn_node[k], dict):
                merge_dict(v, cn_node[k])
            elif trans:
                 # Force update if we have a translation!
                 if cn_node[k] != trans:
                     cn_node[k] = trans
                     added_count += 1
                     print(f"Updated [Force]: {k}")

merge_dict(en_data, cn_data)

if added_count > 0:
    print(f"Successfully patched {added_count} missing keys.")
    with open(cn_path, 'w', encoding='utf-8') as f:
        json.dump(cn_data, f, ensure_ascii=False, indent=2)
else:
    print("No missing keys found.")
