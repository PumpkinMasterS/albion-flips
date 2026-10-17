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

# ---- zonas (rotas): Albion Navigator zoneData.json + tiers de albionroads maps.json ----
import os, re
ZD = os.environ.get("ZONEDATA", "zonedata")
zones = json.load(open(os.path.join(ZD, "zoneData.json"), encoding="utf-8"))
maps = json.load(open(os.path.join(ZD, "maps.json"), encoding="utf-8"))
norm = lambda s: re.sub(r"[^a-z]", "", s.lower())
tiers = {norm(m["mapName"]): m.get("tier") for m in maps}
keep = {z["id"] for z in zones if z["type"] != 6}  # 6 = Roads of Avalon (mudam todos os dias)
idx = {zid: i for i, zid in enumerate(sorted(keep))}
out = [[z["displayName"], z["type"], round(z["position"][0], 1), round(z["position"][1], 1), tiers.get(norm(z["displayName"])),
        sorted(idx[c] for c in z["connections"] if c in keep)] for z in sorted(zones, key=lambda z: z["id"]) if z["id"] in keep]
html = open("index.html", encoding="utf-8").read().replace("__ZONES__", json.dumps(out, ensure_ascii=False, separators=(",", ":")))
open("index.html", "w", encoding="utf-8").write(html)
print(len(out), "zonas")

# ---- outros sítios do jogo (world.json do ao-bin-dumps): mercados/bancos contam como a cidade; o resto é ignorado pelo OCR ----
world = json.load(open(os.path.join(ZD, "world.json"), encoding="utf-8"))
names = {z[0] for z in out}
cities = {z[0]: i for i, z in enumerate(out) if z[1] == 1}
extra = {}
for w in world:
    n = w["UniqueName"].strip()
    if n in names or not re.fullmatch(r"[A-Za-z' .-]+", n) or len(n) < 5:
        continue
    city = next((c for c in cities if c in n and ("Market" in n or "Bank" in n)), None)
    extra[n] = cities[city] if city else -1
html = open("index.html", encoding="utf-8").read().replace("__EXTRA__", json.dumps(sorted(extra.items()), ensure_ascii=False, separators=(",", ":")))
open("index.html", "w", encoding="utf-8").write(html)
print(len(extra), "outros sitios,", sum(1 for v in extra.values() if v >= 0), "ligados a cidades")
