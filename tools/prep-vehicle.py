"""Prepare a vehicle .glb for the library: real-world size, app orientation, see-through glass.

    python tools/prep-vehicle.py IN.glb OUT.glb --length-ft 19.5 [--nose +z] [--glass-uv 0,0.5,0.22,0.72]

- Turns the model so its nose points to local -X (the app's car convention, see carSpots) — give
  the axis the nose currently points along with --nose (+z, -z, +x, -x).
- Scales it uniformly so its length is --length-ft (an averaged real-world figure for that kind of
  vehicle), centres it on its footprint and puts the wheels on the floor. Units stay metres.
- Glass: low-poly packs often paint windows from a texture atlas. Faces whose UV centre falls in
  --glass-uv (u0,v0,u1,v1, glTF UV space: v down) are split into their own primitive with a
  material named "Glass" (blended, dark tint, glossy) — the app turns any "glass"/"window"
  material into see-through, reflective glass, so you can see through the car to the far side.
Prints the final size in feet for the catalog entry.
"""
import argparse
import json
import struct

import numpy as np

CT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
FT = 3.28084


def read_glb(path):
    b = open(path, "rb").read()
    off, j, binb = 12, None, b""
    while off < len(b):
        clen, ctype = struct.unpack("<II", b[off:off + 8])
        if ctype == 0x4E4F534A:
            j = json.loads(b[off + 8:off + 8 + clen])
        elif ctype == 0x004E4942:
            binb = b[off + 8:off + 8 + clen]
        off += 8 + clen
    return j, bytearray(binb)


def acc(j, binb, i):
    a = j["accessors"][i]
    bv = j["bufferViews"][a["bufferView"]]
    dt, n = CT[a["componentType"]], NC[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    isz = np.dtype(dt).itemsize
    stride = bv.get("byteStride") or isz * n
    if stride == isz * n:
        return np.frombuffer(bytes(binb), dt, a["count"] * n, start).reshape(a["count"], n)
    return np.stack([np.frombuffer(bytes(binb), dt, n, start + k * stride) for k in range(a["count"])])


def node_matrix(n):
    if "matrix" in n:
        return np.array(n["matrix"], float).reshape(4, 4).T
    t = n.get("translation", [0, 0, 0]); s = n.get("scale", [1, 1, 1]); x, y, z, w = n.get("rotation", [0, 0, 0, 1])
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4); m[:3, :3] = r * np.array(s); m[:3, 3] = t
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--length-ft", type=float, required=True)
    ap.add_argument("--nose", default="+z", choices=["+z", "-z", "+x", "-x"])
    ap.add_argument("--glass-uv", help="u0,v0,u1,v1")
    a = ap.parse_args()
    j, binb = read_glb(a.inp)

    def add_view(data, target):
        while len(binb) % 4:
            binb.append(0)
        off = len(binb); binb.extend(data)
        j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(data), "target": target})
        return len(j["bufferViews"]) - 1

    glass_faces = 0
    if a.glass_uv:
        u0, v0, u1, v1 = [float(x) for x in a.glass_uv.split(",")]
        j.setdefault("materials", []).append({"name": "Glass", "alphaMode": "BLEND", "doubleSided": True,
            "pbrMetallicRoughness": {"baseColorFactor": [0.1, 0.12, 0.14, 0.3], "metallicFactor": 0.9, "roughnessFactor": 0.06}})
        gmat = len(j["materials"]) - 1
        for m in j["meshes"]:
            extra = []
            for p in m["primitives"]:
                if "TEXCOORD_0" not in p["attributes"] or "indices" not in p:
                    continue
                uv = acc(j, binb, p["attributes"]["TEXCOORD_0"]).astype(float)
                idx = acc(j, binb, p["indices"])[:, 0].astype(np.uint32).reshape(-1, 3)
                c = uv[idx].mean(1)
                isg = (c[:, 0] >= u0) & (c[:, 0] <= u1) & (c[:, 1] >= v0) & (c[:, 1] <= v1)
                if not isg.any():
                    continue
                glass_faces += int(isg.sum())
                def idx_acc(faces):
                    data = faces.astype(np.uint32).ravel()
                    j["accessors"].append({"bufferView": add_view(data.tobytes(), 34963), "componentType": 5125, "count": int(data.size), "type": "SCALAR"})
                    return len(j["accessors"]) - 1
                p["indices"] = idx_acc(idx[~isg])
                q = {"attributes": dict(p["attributes"]), "indices": idx_acc(idx[isg]), "material": gmat}
                extra.append(q)
            m["primitives"].extend(extra)

    # World bounds through the existing node transforms.
    nodes = j["nodes"]
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    def world(i):
        m = node_matrix(nodes[i])
        while i in parent:
            i = parent[i]; m = node_matrix(nodes[i]) @ m
        return m
    rot = {"+z": -90, "-z": 90, "+x": 180, "-x": 0}[a.nose]
    r = np.radians(rot); R = np.eye(4); R[0, 0] = R[2, 2] = np.cos(r); R[0, 2] = np.sin(r); R[2, 0] = -np.sin(r)
    pts = []
    for i, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        w = R @ world(i)
        for p in j["meshes"][n["mesh"]]["primitives"]:
            ac = j["accessors"][p["attributes"]["POSITION"]]
            lo, hi = ac["min"], ac["max"]
            for x in (lo[0], hi[0]):
                for y in (lo[1], hi[1]):
                    for z in (lo[2], hi[2]):
                        pts.append((w @ np.array([x, y, z, 1.0]))[:3])
    pts = np.array(pts); lo, hi = pts.min(0), pts.max(0)
    k = (a.length_ft / FT) / (hi[0] - lo[0])
    T = np.eye(4); T[:3, 3] = [-(lo[0] + hi[0]) / 2 * k, -lo[1] * k, -(lo[2] + hi[2]) / 2 * k]
    S = np.diag([k, k, k, 1.0])
    root = T @ S @ R
    scene = j["scenes"][j.get("scene", 0)]
    nodes.append({"name": "lumostage_root", "matrix": root.T.ravel().tolist(), "children": scene["nodes"]})
    scene["nodes"] = [len(nodes) - 1]

    j["buffers"] = [{"byteLength": len(binb)}]
    js = json.dumps(j, separators=(",", ":")).encode(); js += b" " * ((-len(js)) % 4)
    while len(binb) % 4:
        binb.append(0)
    with open(a.out, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(binb)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(binb), 0x004E4942)); f.write(bytes(binb))
    size = (hi - lo) * k * FT
    print(json.dumps({"file": a.out, "lengthFt": round(size[0], 2), "heightFt": round(size[1], 2), "widthFt": round(size[2], 2), "glassFaces": glass_faces}))


if __name__ == "__main__":
    main()
