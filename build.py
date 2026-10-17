"""Build index.html from template.html + Portuguese item names (ao-bin-dumps items.json)."""
import json, sys, urllib.request
src = sys.argv[1] if len(sys.argv) > 1 else "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/formatted/items.json"
items = json.load(open(src, encoding="utf-8")) if not src.startswith("http") else json.load(urllib.request.urlopen(src))
names = {}
for x in items:
    u, ln = x["UniqueName"], x.get("LocalizedNames") or {}
    if u.startswith(("UNIQUE", "QUESTITEM", "TREASURE")) or not ln.get("PT-BR"):
        continue
    names[u] = ln["PT-BR"]
blob = json.dumps(names, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
html = open("template.html", encoding="utf-8").read().replace("__NAMES__", blob)
open("index.html", "w", encoding="utf-8").write(html)
print(len(names), "items")
