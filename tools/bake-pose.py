"""Bake one frame of an animation into a rigged glTF character -> a static, posed .glb.

    python tools/bake-pose.py CHARACTER.gltf OUT.glb [--anim ANIM.gltf] [--clip NAME] [--at 0.33]
                              [--height-m 1.75] [--yaw-deg 0]

- Bones are matched BY NAME, and only rotations are taken from the animation (each character keeps
  its own bone lengths, so a male idle can pose a female rig without stretching it).
- --at is the sample point as a fraction of the clip (0..1). With no --anim, the character's own
  clip is used (or the bind pose if it has none).
- The result is linear-blend skinned on the CPU, re-centred (feet at y = 0, centred in x/z),
  scaled so its height is --height-m, optionally turned (--yaw-deg, about +Y), and written as a
  single-material static .glb with the base-colour texture embedded.
"""
import argparse
import base64
import json
import os
import struct

import numpy as np

CT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8, 5122: np.int16, 5120: np.int8}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


class Doc:
    def __init__(self, path):
        self.dir = os.path.dirname(os.path.abspath(path))
        if path.lower().endswith(".glb"):
            b = open(path, "rb").read()
            off, self.bins = 12, []
            while off < len(b):
                clen, ctype = struct.unpack("<II", b[off:off + 8])
                if ctype == 0x4E4F534A:
                    self.j = json.loads(b[off + 8:off + 8 + clen])
                elif ctype == 0x004E4942:
                    self.bins.append(b[off + 8:off + 8 + clen])
                off += 8 + clen
            self.buffers = self.bins
        else:
            self.j = json.load(open(path, encoding="utf-8"))
            self.buffers = []
            for bf in self.j.get("buffers", []):
                uri = bf["uri"]
                if uri.startswith("data:"):
                    self.buffers.append(base64.b64decode(uri.split(",", 1)[1]))
                else:
                    self.buffers.append(open(os.path.join(self.dir, uri), "rb").read())

    def acc(self, i):
        a = self.j["accessors"][i]
        bv = self.j["bufferViews"][a["bufferView"]]
        dt, n = CT[a["componentType"]], NC[a["type"]]
        buf = self.buffers[bv.get("buffer", 0)]
        start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        isz = np.dtype(dt).itemsize
        stride = bv.get("byteStride") or isz * n
        if stride == isz * n:
            arr = np.frombuffer(buf, dt, a["count"] * n, start).reshape(a["count"], n)
        else:
            arr = np.stack([np.frombuffer(buf, dt, n, start + k * stride) for k in range(a["count"])])
        arr = arr.astype(np.float64) if dt == np.float32 else arr
        if a.get("normalized") and dt != np.float32:
            arr = arr.astype(np.float64) / np.iinfo(dt).max
        return arr


def quat_mat(q):
    x, y, z, w = q / (np.linalg.norm(q) or 1)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def trs(t, r, s):
    m = np.eye(4)
    m[:3, :3] = quat_mat(np.array(r, float)) * np.array(s, float)
    m[:3, 3] = t
    return m


def sample(doc, anim, t_frac):
    """{node name: {"rotation": quat, ...}} for one clip at a fraction of its length."""
    out, dur = {}, 0.0
    for s in anim["samplers"]:
        dur = max(dur, float(doc.acc(s["input"]).max()))
    t = dur * t_frac
    for ch in anim["channels"]:
        path = ch["target"]["path"]
        if path not in ("rotation", "translation"):
            continue
        s = anim["samplers"][ch["sampler"]]
        times, vals = doc.acc(s["input"])[:, 0], doc.acc(s["output"])
        if s.get("interpolation") == "CUBICSPLINE":
            vals = vals[1::3]
        k = int(np.searchsorted(times, t))
        if k <= 0:
            v = vals[0]
        elif k >= len(times):
            v = vals[-1]
        else:
            f = (t - times[k - 1]) / max(times[k] - times[k - 1], 1e-9)
            a, b = vals[k - 1], vals[k]
            if path == "rotation" and np.dot(a, b) < 0:
                b = -b
            v = a + (b - a) * (0 if s.get("interpolation") == "STEP" else f)
        name = doc.j["nodes"][ch["target"]["node"]].get("name")
        out.setdefault(name, {})[path] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("char"); ap.add_argument("out")
    ap.add_argument("--anim"); ap.add_argument("--clip"); ap.add_argument("--at", type=float, default=0.33)
    ap.add_argument("--height-m", type=float, default=1.75); ap.add_argument("--yaw-deg", type=float, default=0)
    ap.add_argument("--texture", help="override the base-colour image (e.g. a palette swap)")
    ap.add_argument("--node", help="only bake mesh nodes whose name contains this text (split a pack)")
    a = ap.parse_args()

    ch = Doc(a.char)
    nodes = ch.j["nodes"]
    local = [trs(n.get("translation", [0, 0, 0]), n.get("rotation", [0, 0, 0, 1]), n.get("scale", [1, 1, 1]))
             if "matrix" not in n else np.array(n["matrix"]).reshape(4, 4).T for n in nodes]
    src = Doc(a.anim) if a.anim else ch
    anims = src.j.get("animations", [])
    if anims:
        clip = next((x for x in anims if x.get("name") == a.clip), anims[0])
        pose = sample(src, clip, a.at)
        for i, n in enumerate(nodes):
            p = pose.get(n.get("name"))
            if p and "rotation" in p and "matrix" not in n:
                local[i] = trs(n.get("translation", [0, 0, 0]), p["rotation"], n.get("scale", [1, 1, 1]))
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}

    def world(i):
        m = local[i]
        while i in parent:
            i = parent[i]
            m = local[i] @ m
        return m
    W = [world(i) for i in range(len(nodes))]

    P, N, UV, IDX, used_mat = [], [], [], [], None
    for ni, n in enumerate(nodes):
        if "mesh" not in n:
            continue
        if a.node and a.node not in (n.get("name") or "") + "|" + (ch.j["meshes"][n["mesh"]].get("name") or ""):
            continue
        skin = ch.j["skins"][n["skin"]] if "skin" in n else None
        if skin:
            ibm = ch.acc(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
            jm = np.stack([W[j] @ ibm[k] for k, j in enumerate(skin["joints"])])
        for prim in ch.j["meshes"][n["mesh"]]["primitives"]:
            at = prim["attributes"]
            if used_mat is None:
                used_mat = prim.get("material", 0)
            pos = ch.acc(at["POSITION"])
            nor = ch.acc(at["NORMAL"]) if "NORMAL" in at else np.zeros_like(pos)
            uv = ch.acc(at["TEXCOORD_0"]) if "TEXCOORD_0" in at else np.zeros((len(pos), 2))
            if skin and "JOINTS_0" in at:
                js = ch.acc(at["JOINTS_0"]).astype(int)
                ws = ch.acc(at["WEIGHTS_0"]).astype(np.float64)
                ws = ws / np.maximum(ws.sum(1, keepdims=True), 1e-9)
                M = np.einsum("vk,vkij->vij", ws, jm[js])
                pos = np.einsum("vij,vj->vi", M[:, :3, :3], pos) + M[:, :3, 3]
                nor = np.einsum("vij,vj->vi", M[:, :3, :3], nor)
            else:
                m = W[ni]
                pos = pos @ m[:3, :3].T + m[:3, 3]
                nor = nor @ m[:3, :3].T
            idx = ch.acc(prim["indices"])[:, 0].astype(np.uint32) if "indices" in prim else np.arange(len(pos), dtype=np.uint32)
            base = sum(len(p) for p in P)
            P.append(pos); N.append(nor); UV.append(uv); IDX.append(idx + base)
    P, N, UV, IDX = np.concatenate(P), np.concatenate(N), np.concatenate(UV), np.concatenate(IDX)
    N = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)

    if a.yaw_deg:
        r = np.radians(a.yaw_deg); c, s = np.cos(r), np.sin(r)
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        P, N = P @ R.T, N @ R.T
    lo, hi = P.min(0), P.max(0)
    P = P - np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    k = a.height_m / (hi[1] - lo[1])
    P = P * k

    # Texture (embedded so the .glb stands alone).
    img, img_mime = None, "image/png"
    if a.texture:
        img = open(a.texture, "rb").read()
    else:
        mat = (ch.j.get("materials") or [{}])[used_mat or 0]
        ti = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture", {}).get("index")
        if ti is not None:
            im = ch.j["images"][ch.j["textures"][ti]["source"]]
            if "bufferView" in im:
                bv = ch.j["bufferViews"][im["bufferView"]]
                img = bytes(ch.buffers[bv.get("buffer", 0)][bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])
                img_mime = im.get("mimeType", "image/png")
            elif "uri" in im:
                pth = os.path.join(ch.dir, im["uri"])
                if not os.path.exists(pth):
                    pth = os.path.join(ch.dir, "..", "TEXTURES", os.path.basename(im["uri"]))
                img = open(pth, "rb").read() if os.path.exists(pth) else None

    blobs, views = [], []
    def add(data, target=None):
        off = sum(len(b) for b in blobs)
        pad = (-len(data)) % 4
        blobs.append(data + b"\0" * pad)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            v["target"] = target
        views.append(v)
        return len(views) - 1
    P32, N32, UV32 = P.astype(np.float32), N.astype(np.float32), UV.astype(np.float32)
    vP, vN, vU, vI = add(P32.tobytes(), 34962), add(N32.tobytes(), 34962), add(UV32.tobytes(), 34962), add(IDX.astype(np.uint32).tobytes(), 34963)
    accessors = [
        {"bufferView": vP, "componentType": 5126, "count": len(P32), "type": "VEC3", "min": P32.min(0).tolist(), "max": P32.max(0).tolist()},
        {"bufferView": vN, "componentType": 5126, "count": len(N32), "type": "VEC3"},
        {"bufferView": vU, "componentType": 5126, "count": len(UV32), "type": "VEC2"},
        {"bufferView": vI, "componentType": 5125, "count": len(IDX), "type": "SCALAR"}]
    mat = {"name": "figure", "pbrMetallicRoughness": {"metallicFactor": 0, "roughnessFactor": 0.85}}
    gj = {"asset": {"version": "2.0", "generator": "lumostage bake-pose"}, "scene": 0, "scenes": [{"nodes": [0]}],
          "nodes": [{"name": os.path.splitext(os.path.basename(a.out))[0], "mesh": 0}],
          "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3, "material": 0}]}],
          "materials": [mat], "accessors": accessors, "bufferViews": views}
    if img:
        vImg = add(img)
        gj["images"] = [{"bufferView": vImg, "mimeType": img_mime}]
        # nearest keeps palette textures crisp; photo textures (jpeg / --node splits) filter smoothly
        gj["samplers"] = [{"magFilter": 9728, "minFilter": 9728}] if img_mime == "image/png" and not a.node else [{"magFilter": 9729, "minFilter": 9987}]
        gj["textures"] = [{"source": 0, "sampler": 0}]
        mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0}
    binb = b"".join(blobs)
    gj["buffers"] = [{"byteLength": len(binb)}]
    js = json.dumps(gj, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    with open(a.out, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(binb)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(binb), 0x004E4942)); f.write(binb)
    sz = P.max(0) - P.min(0)
    print(json.dumps({"file": a.out, "tris": int(len(IDX) // 3), "h_m": round(float(sz[1]), 3), "w_m": round(float(sz[0]), 3), "d_m": round(float(sz[2]), 3), "texture": bool(img)}))


if __name__ == "__main__":
    main()
