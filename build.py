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

# ---- saídas de cada zona (ficheiros .cluster.xml do ao-bin-dumps) ----
# Coordenadas da zona (x, z) -> minimapa: este = (x+z)/√2, norte = (z−x)/√2. Confirmado no jogo: em Willowsigh Marsh
# as 4 placas ficam NE/SE/SO/NO e a de Thetford a NO; em Thetford Portal a saída para Widemoor Shore é "Nordeste".
import itertools, math
cmap = json.load(open(os.path.join(ZD, "cluster_map.json")))
def cluster_exits(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r'<cluster [^>]*origin="(-?[\d.]+) (-?[\d.]+)"[^>]*size="([\d.]+) ([\d.]+)"', s)
    if not m: return []
    ox, oz, sx, sz = map(float, m.groups()); res = []
    for r in re.finditer(r'<templateinstance [^>]*ref="([^"]*)"[^>]*pos="(-?[\d.]+) (-?[\d.]+) (-?[\d.]+)"', s):
        if "exit" in r.group(1).lower():
            x = (float(r.group(2)) - ox) / sx * 2 - 1; zz = (float(r.group(4)) - oz) / sz * 2 - 1
            res.append(((x + zz) / math.sqrt(2), (zz - x) / math.sqrt(2)))
    return res
ang = lambda dx, dy: math.degrees(math.atan2(dy, dx)) % 360
diff = lambda a, b: min(abs(a - b) % 360, 360 - abs(a - b) % 360)
exits_out = []
for i, zz in enumerate(out):
    ex = cluster_exits(os.path.join(ZD, "clusters", os.path.basename(cmap[zz[0]]))) if zz[0] in cmap else []
    nb = zz[5]; tgt = [-1] * len(ex)
    if ex and nb and len(ex) <= 8:
        wa = [ang(out[c][2] - zz[2], -(out[c][3] - zz[3])) for c in nb]; ea = [ang(*e) for e in ex]
        k = min(len(nb), len(ex))
        # nº de vizinhas > saídas: fica a combinação de vizinhas+saídas com menor erro
        best = min(((p, q) for p in itertools.permutations(range(len(nb)), k) for q in itertools.permutations(range(len(ex)), k) if list(p) == sorted(p)),
                   key=lambda pq: sum(diff(wa[a], ea[b]) for a, b in zip(*pq)))
        for a, b in zip(*best): tgt[b] = nb[a]
    exits_out.append([[round(e[0], 2), round(e[1], 2), t] for e, t in zip(ex, tgt)])
html = open("index.html", encoding="utf-8").read().replace("__EXITS__", json.dumps(exits_out, separators=(",", ":")))
open("index.html", "w", encoding="utf-8").write(html)
print(sum(1 for e in exits_out if e), "zonas com saídas no minimapa")
