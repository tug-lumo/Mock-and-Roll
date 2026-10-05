"""Quick report on .glb / .gltf files: meshes, triangles, size, skins, animations, textures.

    python tools/inspect-gltf.py FILE_OR_DIR [...]

Size comes from each mesh's POSITION min/max with node transforms applied (translation, rotation,
scale and parent chains; skinning is ignored), so it is a good guide for scaling into the app.
"""
import json
import math
import os
import struct
import sys


def load(path):
    if path.lower().endswith(".glb"):
        b = open(path, "rb").read()
        off, j = 12, None
        while off < len(b):
            clen, ctype = struct.unpack("<II", b[off:off + 8])
            if ctype == 0x4E4F534A:
                j = json.loads(b[off + 8:off + 8 + clen])
            off += 8 + clen
        return j
    return json.load(open(path, encoding="utf-8"))


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def node_matrix(n):
    if "matrix" in n:
        m = n["matrix"]
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    t = n.get("translation", [0, 0, 0]); s = n.get("scale", [1, 1, 1]); x, y, z, w = n.get("rotation", [0, 0, 0, 1])
    r = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    return [[r[i][0] * s[0], r[i][1] * s[1], r[i][2] * s[2], t[i]] for i in range(3)] + [[0, 0, 0, 1]]


def report(path):
    j = load(path)
    nodes, meshes, acc = j.get("nodes", []), j.get("meshes", []), j.get("accessors", [])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i

    def world(i):
        m = node_matrix(nodes[i])
        while i in parent:
            i = parent[i]
            m = mat_mul(node_matrix(nodes[i]), m)
        return m

    lo, hi, tris, rows = [1e9] * 3, [-1e9] * 3, 0, []
    for ni, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        m, w = meshes[n["mesh"]], world(ni)
        mlo, mhi, mt = [1e9] * 3, [-1e9] * 3, 0
        for p in m.get("primitives", []):
            a = acc[p["attributes"]["POSITION"]]
            mt += (acc[p["indices"]]["count"] if "indices" in p else a["count"]) // 3
            mn, mx = a.get("min"), a.get("max")
            if not mn:
                continue
            for cx in (mn[0], mx[0]):
                for cy in (mn[1], mx[1]):
                    for cz in (mn[2], mx[2]):
                        v = [sum(w[r][k] * c for k, c in enumerate((cx, cy, cz, 1))) for r in range(3)]
                        for k in range(3):
                            mlo[k] = min(mlo[k], v[k]); mhi[k] = max(mhi[k], v[k])
        tris += mt
        for k in range(3):
            lo[k] = min(lo[k], mlo[k]); hi[k] = max(hi[k], mhi[k])
        nm = n.get("name") or m.get("name") or "mesh%d" % ni
        par = nodes[parent[ni]].get("name", "") if ni in parent else ""
        rows.append("    %-34s %-22s tris %6d  size %.2f x %.2f x %.2f" % (nm[:34], par[:22], mt, *(mhi[k] - mlo[k] for k in range(3))))
    size = [hi[k] - lo[k] for k in range(3)]
    imgs = [im.get("uri", im.get("name", "embedded")) for im in j.get("images", [])]
    print("%s\n  meshes %d  nodes %d  tris %d  skins %d  animations %d  materials %d  images %s" % (
        path, len(rows), len(nodes), tris, len(j.get("skins", [])), len(j.get("animations", [])), len(j.get("materials", [])), imgs[:6]))
    print("  overall size (x,y,z) %.2f x %.2f x %.2f  (y = height if Y-up)" % tuple(size))
    if j.get("animations"):
        print("  animations: " + ", ".join(a.get("name", "?") for a in j["animations"][:12]))
    for r in rows[:40]:
        print(r)
    if len(rows) > 40:
        print("    ... %d more" % (len(rows) - 40))


for arg in sys.argv[1:]:
    if os.path.isdir(arg):
        for f in sorted(os.listdir(arg)):
            if f.lower().endswith((".glb", ".gltf")):
                report(os.path.join(arg, f))
    else:
        report(arg)
