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
names_pt = dict(names)  # "names" é reutilizado mais abaixo para as zonas

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

# ---- Roads of Avalon: só para o OCR as reconhecer (as ligações mudam todos os dias, não entram nas rotas) ----
roads = sorted({z["displayName"] for z in zones if z["type"] == 6})
html = open("index.html", encoding="utf-8").read().replace("__ROADS__", json.dumps(roads, separators=(",", ":")))
open("index.html", "w", encoding="utf-8").write(html)
print(len(roads), "roads")

# ---- peso de cada item (items.json "cru" do ao-bin-dumps; os encantamentos @n pesam o mesmo que o item base) ----
raw_src = os.environ.get("ITEMS_FULL", "https://raw.githubusercontent.com/ao-data/ao-bin-dumps/master/items.json")
raw = json.load(open(raw_src, encoding="utf-8")) if not raw_src.startswith("http") else json.load(urllib.request.urlopen(raw_src))
weights = {}
for cat, v in raw["items"].items():
    for it in (v if isinstance(v, list) else [v]):
        if isinstance(it, dict) and it.get("@uniquename") and it.get("@weight"):
            weights[it["@uniquename"]] = round(float(it["@weight"]), 2)
html = open("index.html", encoding="utf-8").read().replace("__WEIGHTS__", json.dumps(weights, separators=(",", ":")))
open("index.html", "w", encoding="utf-8").write(html)
print(len(weights), "pesos")

# ---- receitas de crafting/refino (items.json cru): [id de mercado, categoria, quantidade feita, [[material, qtd, devolvível]]] ----
def as_list(x): return x if isinstance(x, list) else [x] if x else []
def mkt(uid, lvl): return uid + (f"@{lvl}" if int(lvl or 0) > 0 else "")
def cat_of(it):
    sc, sub = it.get("@shopcategory", ""), it.get("@shopsubcategory1", "")
    if sub == "refinedresources": return "refino"
    if sc == "consumables": return "consumo"
    if sc in ("melee", "ranged", "magic", "armor", "offhand", "accessories", "gatherergear", "tools") or it.get("@slottype"): return "equip"
    return "outros"
def recipe(req):
    for c in as_list(req):
        res = [[mkt(r["@uniquename"], r.get("@enchantmentlevel")), int(r["@count"]), 0 if r.get("@maxreturnamount") == "0" else 1] for r in as_list(c.get("craftresource"))]
        if res: return int(c.get("@amountcrafted", 1) or 1), res
    return None
recipes = []
for cat, v in raw["items"].items():
    for it in as_list(v):
        if not isinstance(it, dict) or not it.get("@uniquename"): continue
        uid = it["@uniquename"]; base = mkt(uid, it.get("@enchantmentlevel"))
        r = recipe(it.get("craftingrequirements"))
        if r and base in names_pt: recipes.append([base, cat_of(it), r[0], r[1]])
        for en in as_list((it.get("enchantments") or {}).get("enchantment")):
            r = recipe(en.get("craftingrequirements")); eid = f"{uid}@{en['@enchantmentlevel']}"
            if r and eid in names_pt: recipes.append([eid, cat_of(it), r[0], r[1]])
html = open("index.html", encoding="utf-8").read().replace("__RECIPES__", json.dumps(recipes, separators=(",", ":")))
open("index.html", "w", encoding="utf-8").write(html)
import collections
print(len(recipes), "receitas", dict(collections.Counter(r[1] for r in recipes)))
