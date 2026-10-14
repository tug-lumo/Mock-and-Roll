"""Rigged people for live posing: one skinned .glb per figure + a shared pose library.

    python tools/prep-rigs.py PACK_DIR [--out assets/rigs]

PACK_DIR is the rigged people pack (rig-gltf/, Animations.gltf/, TEXTURES/).

- Each figure in FIGURES is written as assets/rigs/<name>.glb: the pack's skinned mesh(es) and
  30-bone skeleton, with its animation stripped and the base-colour texture taken from the matching
  static figure in assets/people2/ (so the colours are exactly what the app already shows).
- assets/rigs/poses.json holds the pack clips the app poses from, as local bone rotations
  (quaternions, by bone name): one still frame per idle/gesture clip, and evenly spaced frames
  for the walk cycles. Bones are matched by name in the app, so any clip poses any figure.
"""
import argparse
import importlib.util
import json
import os
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bake", os.path.join(HERE, "bake-pose.py"))
bake = importlib.util.module_from_spec(spec); spec.loader.exec_module(bake)

# static figure (assets/people2/<name>.glb) -> pack rig
FIGURES = {
    "doctor": "Doctor_Male_B", "police-officer": "police_Female_A", "construction-worker": "worker_Male_constructor_B",
    "man-phone": "casual_Male_G", "man-walking": "casual_Male_K", "woman-standing": "casual_Female_G",
    "woman-walking": "casual_Female_K", "older-woman": "elder_Female_A", "girl": "ProstheticLeg_girl", "boy": "little_boy_B",
}
# clip id -> (animation file, still frame as a fraction of the clip | None = sample the cycle)
CLIPS = {
    "idle_m": ("idle_m_1_200f", 0.3), "idle_m2": ("idle_m_2_220f", 0.3),
    "idle_f": ("idle_f_1_150f", 0.3), "idle_f2": ("idle_f_2_190f", 0.3),
    "phone": ("idle_phoneTalking_180f", 0.3), "wave": ("greeting_waving_110f", 0.45),
    "walk_m": ("locom_m_basicWalk_30f", None), "walk_f": ("locom_f_basicWalk_30f", None),
}
CYCLE_FRAMES = 24


def static_texture(path):
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    if "images" not in j:
        return None
    bv = j["bufferViews"][j["images"][0]["bufferView"]]
    start = 20 + n + 8 + bv.get("byteOffset", 0)
    return b[start:start + bv["byteLength"]]


def write_rig(pack, rig, tex, out):
    doc = bake.Doc(os.path.join(pack, "rig-gltf", rig + ".gltf"))
    j = json.loads(json.dumps(doc.j))
    assert len(doc.buffers) == 1, "expected one buffer"
    j.pop("animations", None)
    binb = bytearray(doc.buffers[0])
    binb += b"\0" * ((-len(binb)) % 4)
    for m in j.get("materials", []):
        pbr = m.setdefault("pbrMetallicRoughness", {})
        pbr["metallicFactor"] = 0; pbr["roughnessFactor"] = 0.85
        for k in ("metallicRoughnessTexture",):
            pbr.pop(k, None)
        for k in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            m.pop(k, None)
    if tex:
        off = len(binb); binb += tex; binb += b"\0" * ((-len(binb)) % 4)
        j["bufferViews"].append({"buffer": 0, "byteOffset": off, "byteLength": len(tex)})
        j["images"] = [{"bufferView": len(j["bufferViews"]) - 1, "mimeType": "image/png"}]
        j["samplers"] = [{"magFilter": 9728, "minFilter": 9728}]          # palette texture: keep it crisp
        j["textures"] = [{"source": 0, "sampler": 0}]
        for m in j.get("materials", []):
            m["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0}
    else:
        for k in ("images", "samplers", "textures"):
            j.pop(k, None)
    j["buffers"] = [{"byteLength": len(binb)}]
    j["asset"] = {"version": "2.0", "generator": "lumostage prep-rigs"}
    js = json.dumps(j, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    with open(out, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js) + 8 + len(binb)))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(binb), 0x004E4942)); f.write(bytes(binb))
    return len(binb) + len(js)


def frame(doc, clip, t):
    pose = bake.sample(doc, clip, t)
    return {name: [round(float(v), 5) for v in p["rotation"]] for name, p in pose.items() if name and "rotation" in p}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack"); ap.add_argument("--out", default="assets/rigs")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, rig in FIGURES.items():
        tex = static_texture(os.path.join("assets", "people2", name + ".glb"))
        n = write_rig(a.pack, rig, tex, os.path.join(a.out, name + ".glb"))
        print(name, "<-", rig, n // 1024, "KB")
    lib = {}
    for cid, (file, at) in CLIPS.items():
        doc = bake.Doc(os.path.join(a.pack, "Animations.gltf", file + ".gltf"))
        clip = doc.j["animations"][0]
        dur = max(float(doc.acc(s["input"]).max()) for s in clip["samplers"])
        if at is None:
            lib[cid] = {"seconds": round(dur, 3), "frames": [frame(doc, clip, i / CYCLE_FRAMES) for i in range(CYCLE_FRAMES)]}
        else:
            lib[cid] = {"frames": [frame(doc, clip, at)]}
    p = os.path.join(a.out, "poses.json")
    json.dump(lib, open(p, "w"), separators=(",", ":"))
    print(p, os.path.getsize(p) // 1024, "KB")


if __name__ == "__main__":
    main()
