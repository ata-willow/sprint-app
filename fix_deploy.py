import requests
import json

TOKEN = "b66b642b3c9225af4f5d2e12c1172edb1bdb057a"
USER = "sprintwisp"
API = f"https://www.pythonanywhere.com/api/v0/user/{USER}"
HEADERS = {"Authorization": f"Token {TOKEN}"}
DEPLOY_PATH = "/var/www/sprintwisp/sprint"
BASE = "./"

def upload_file(remote_path, content):
    url = f"{API}/files/path{remote_path}"
    resp = requests.post(url, files={"content": content}, headers=HEADERS, timeout=60)
    print(f"  {remote_path} -> {resp.status_code}")
    return resp.status_code in (200, 201, 204)

def upload_local(local_path, remote_path):
    with open(local_path, "r", encoding="utf-8") as f:
        content = f.read()
    return upload_file(remote_path, content)

# 1. Upload project files
files_to_upload = [
    ("static/style.css", "/static/style.css"),
    ("templates/index.html", "/templates/index.html"),
    ("templates/log.html", "/templates/log.html"),
    ("templates/route.html", "/templates/route.html"),
]

for local, remote in files_to_upload:
    ok = upload_local(BASE + local, DEPLOY_PATH + remote)
    print(f"  {'OK' if ok else 'FAIL'}: {local}")

# 2. Fix WSGI file
wsgi_content = f"""import sys
import os

path = '{DEPLOY_PATH}/'
if path not in sys.path:
    sys.path.insert(0, path)

from app import app as application
"""
ok = upload_file("/var/www/sprintwisp_pythonanywhere_com_wsgi.py", wsgi_content)
print(f"  WSGI fix: {'OK' if ok else 'FAIL'}")

# 3. Reload
import time
time.sleep(2)
resp = requests.post(f"{API}/webapps/3155147/reload/", headers=HEADERS, timeout=30)
print(f"  Reload: {resp.status_code}")
if resp.status_code != 200:
    print(f"  Reload response: {resp.text[:200]}")
    # Try alternative: re-upload WSGI to trigger restart
    print("  Trying WSGI re-upload to trigger restart...")
    upload_file("/var/www/sprintwisp_pythonanywhere_com_wsgi.py", wsgi_content)

print("\nDone!")
