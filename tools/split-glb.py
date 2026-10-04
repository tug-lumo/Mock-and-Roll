"""Split a multi-object .glb (e.g. a "pack" of people/props) into one .glb per mesh.

    python tools/split-glb.py PACK.glb OUT_DIR [--prefix person] [--ref-height-m 1.80]

For each mesh in the pack:
  - geometry is re-centred: feet on the floor (min Y = 0), centred in X/Z;
  - all meshes get ONE common scale so the tallest-standing reference ("--ref-height-m", default
    1.80 m for the 90th-percentile height in the pack) keeps their relative sizes — seated or
    child figures stay proportionally shorter;
  - the single material is copied; everything else (pack transforms, other meshes) is dropped.
Prints a JSON summary (file, name, height/width/depth in metres and feet) for the app catalog.

Handles float VEC3 POSITION/NORMAL (interleaved or not), optional TEXCOORD_0 (VEC2) and
uint16/uint32 indices — the common case for low-poly packs. Not for skinned/animated models.
"""
import argparse
import json
import os
import struct

COMP = {5126: ("f", 4), 5123: ("H", 2), 5125: ("I", 4), 5121: ("B", 1)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    b = open(path, "rb").read()
    magic, ver, length = struct.unpack("<4sII", b[:12])
    assert magic == b"glTF", "not a .glb"
    off, j, bin_ = 12, None, b""
    while off < length:
        clen, ctype = struct.unpack("<II", b[off:off + 8])
        chunk = b[off + 8:off + 8 + clen]
        if ctype == 0x4E4F534A:
            j = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_ = chunk
        off += 8 + clen
    return j, bin_


def read_accessor(j, bin_, ai):
    a = j["accessors"][ai]
    bv = j["bufferViews"][a["bufferView"]]
    fmt, size = COMP[a["componentType"]]
    n = NCOMP[a["type"]]
    stride = bv.get("byteStride") or size * n
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    out = []
    for i in range(a["count"]):
        o = base + i * stride
        out.append(struct.unpack("<" + fmt * n, bin_[o:o + size * n]))
    return a, out


def pad4(b, fill=b"\x00"):
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path, gltf, bin_):
    js = pad4(json.dumps(gltf, separators=(",", ":")).encode(), b" ")
    bn = pad4(bin_)
    total = 12 + 8 + len(js) + 8 + len(bn)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(bn), 0x004E4942)); f.write(bn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack"); ap.add_argument("out")
    ap.add_argument("--prefix", default="person")
    ap.add_argument("--ref-height-m", type=float, default=1.80)
    args = ap.parse_args()
    j, bin_ = read_glb(args.pack)
    os.makedirs(args.out, exist_ok=True)

    # Name each mesh after the node that uses it (strip the converter's "_Material_0" tails).
    # Prefer the parent node's name when the mesh node is just "<parent>_<material>_N" (FBX exports).
    nodes = j.get("nodes", [])
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    names = {}
    for i, n in enumerate(nodes):
        if "mesh" in n:
            nm = n.get("name", "")
            p = parent.get(i)
            pn = nodes[p].get("name", "") if p is not None else ""
            names[n["mesh"]] = pn if pn and nm.startswith(pn) else nm
    items = []
    for mi, mesh in enumerate(j["meshes"]):
        prims = []
        lo = [1e30] * 3; hi = [-1e30] * 3
        for p in mesh["primitives"]:
            _, pos = read_accessor(j, bin_, p["attributes"]["POSITION"])
            for v in pos:
                for k in range(3):
                    lo[k] = min(lo[k], v[k]); hi[k] = max(hi[k], v[k])
            prims.append(p)
        items.append({"mi": mi, "lo": lo, "hi": hi, "h": hi[1] - lo[1]})

    heights = sorted(it["h"] for it in items)
    ref = heights[int(round(0.9 * (len(heights) - 1)))]
    scale = args.ref_height_m / ref

    summary = []
    for it in items:
        mi, lo, hi = it["mi"], it["lo"], it["hi"]
        cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
        out_bin = b""; accessors = []; views = []; prims_out = []

        def add_view(data, target=None):
            nonlocal out_bin
            out_bin = pad4(out_bin)
            v = {"buffer": 0, "byteOffset": len(out_bin), "byteLength": len(data)}
            if target: v["target"] = target
            views.append(v); out_bin += data
            return len(views) - 1

        for p in j["meshes"][mi]["primitives"]:
            attrs = {}
            for key, ai in p["attributes"].items():
                a, vals = read_accessor(j, bin_, ai)
                if a["componentType"] != 5126:
                    continue                                   # keep float attributes only
                if key == "POSITION":
                    vals = [((v[0] - cx) * scale, (v[1] - lo[1]) * scale, (v[2] - cz) * scale) for v in vals]
                n = NCOMP[a["type"]]
                data = b"".join(struct.pack("<" + "f" * n, *v) for v in vals)
                acc = {"bufferView": add_view(data, 34962), "componentType": 5126, "count": len(vals), "type": a["type"]}
                if key == "POSITION":
                    acc["min"] = [min(v[k] for v in vals) for k in range(3)]
                    acc["max"] = [max(v[k] for v in vals) for k in range(3)]
                accessors.append(acc); attrs[key] = len(accessors) - 1
            prim = {"attributes": attrs, "mode": p.get("mode", 4)}
            if "indices" in p:
                a, idx = read_accessor(j, bin_, p["indices"])
                flat = [i[0] for i in idx]
                big = max(flat) > 65535
                data = struct.pack("<" + ("I" if big else "H") * len(flat), *flat)
                accessors.append({"bufferView": add_view(data, 34963), "componentType": 5125 if big else 5123, "count": len(flat), "type": "SCALAR"})
                prim["indices"] = len(accessors) - 1
            if "material" in p:
                prim["material"] = 0
            prims_out.append(prim)

        raw = names.get(mi) or j["meshes"][mi].get("name") or f"mesh_{mi}"
        base = raw
        num = "".join(ch for ch in base if ch.isdigit())[-2:] or str(mi + 1).zfill(2)
        fname = f"{args.prefix}-{num}.glb"
        mats = [j["materials"][j["meshes"][mi]["primitives"][0].get("material", 0)]] if j.get("materials") else []
        gltf = {
            "asset": {"version": "2.0", "generator": "mock-and-roll split-glb.py", "extras": {"source": os.path.basename(args.pack), "sourceMesh": raw}},
            "scene": 0, "scenes": [{"nodes": [0]}],
            "nodes": [{"name": base, "mesh": 0}],
            "meshes": [{"name": base, "primitives": prims_out}],
            "accessors": accessors, "bufferViews": views,
            "buffers": [{"byteLength": len(pad4(out_bin))}],
        }
        if mats:
            gltf["materials"] = mats
        write_glb(os.path.join(args.out, fname), gltf, out_bin)
        h, w, d = (hi[1] - lo[1]) * scale, (hi[0] - lo[0]) * scale, (hi[2] - lo[2]) * scale
        summary.append({"file": fname, "source": base, "heightM": round(h, 3), "widthM": round(w, 3), "depthM": round(d, 3),
                        "heightFt": round(h * 3.28084, 2), "widthFt": round(w * 3.28084, 2), "depthFt": round(d * 3.28084, 2)})
    summary.sort(key=lambda s: s["file"])
    print(json.dumps({"scale": scale, "refUnits": ref, "items": summary}, indent=1))


if __name__ == "__main__":
    main()
