#!/usr/bin/env python3
"""Checks yeah baby. sound packages and builds the catalog (format: README.md).

  python3 tools/samplepack.py check [<package-folder> ...]   validate packages (default: all)
  python3 tools/samplepack.py index                          validate all, then write index.json

A package is a top-level folder holding its samples and a manifest.json. You
never need to run `index` yourself: the GitHub Action does it on every push.
Standard library only.
"""
import hashlib, json, os, re, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = "manifest.json"
FORMAT = "yeahbaby.sample-package"
INDEX_FORMAT = "yeahbaby.sample-index"
AUDIO = {".wav", ".aif", ".aiff", ".caf", ".flac", ".mp3", ".m4a"}
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
NOTE = re.compile(r"^[A-Ga-g](#|b)?-?\d$")
COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
ICONS = {i["id"] for i in json.load(open(os.path.join(ROOT, "tools", "pad-icons.json"), encoding="utf-8"))["icons"]}


class Problem(Exception):
    pass


def safe(path):
    return bool(path) and not path.startswith("/") and "\\" not in path and ":" not in path \
        and all(p not in ("", ".", "..") for p in path.split("/"))


def note_ok(n):
    return (isinstance(n, int) and 0 <= n <= 127) or (isinstance(n, str) and bool(NOTE.match(n)))


def referenced(pkg):
    out = set()
    for inst in pkg["instruments"]:
        for pad in inst.get("pads", []):
            if "file" in pad: out.add(pad["file"])
            out.update(l["file"] for l in pad.get("layers", []))
        out.update(z["file"] for z in inst.get("zones", []))
        if "sfz" in inst: out.add(inst["sfz"])
    return out


def wav_check(path, name):
    with open(path, "rb") as f:
        head = f.read(12)
        if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
            raise Problem(f"{name}: not a WAV file")
        fmt = data = None
        while True:
            chunk = f.read(8)
            if len(chunk) < 8: break
            cid, size = chunk[:4], struct.unpack("<I", chunk[4:])[0]
            if cid == b"fmt ":
                fmt = struct.unpack("<HHIIHH", f.read(16)); f.seek(size - 16 + (size & 1), 1)
            else:
                if cid == b"data": data = size
                f.seek(size + (size & 1), 1)
        if not fmt or data is None: raise Problem(f"{name}: WAV without fmt/data chunk")
        tag, channels = fmt[0], fmt[1]
        if tag not in (1, 3, 0xFFFE): raise Problem(f"{name}: compressed WAV (format {tag}); use PCM or float")
        if channels > 2: raise Problem(f"{name}: {channels} channels; use mono or stereo")


def check(folder):
    """Validates one package folder; returns its manifest."""
    name = os.path.basename(os.path.normpath(folder))
    path = os.path.join(folder, MANIFEST)
    try:
        pkg = json.load(open(path, encoding="utf-8"))
    except OSError:
        raise Problem(f"{name}: no {MANIFEST}")
    except ValueError as e:
        raise Problem(f"{name}/{MANIFEST}: {e}")
    for key in ("format", "formatVersion", "id", "name", "version", "license", "instruments"):
        if key not in pkg: raise Problem(f"{name}: missing \"{key}\"")
    if pkg["format"] != FORMAT: raise Problem(f"{name}: format must be \"{FORMAT}\"")
    if not ID.match(pkg["id"]): raise Problem(f"{name}: id \"{pkg['id']}\": use lowercase letters, digits and dashes")
    if pkg["id"] != name: raise Problem(f"{name}: the folder must be named after the id (\"{pkg['id']}\")")
    if "id" not in pkg["license"]: raise Problem(f"{name}: license needs an \"id\" (e.g. \"CC0-1.0\")")
    ids = set()
    for inst in pkg["instruments"]:
        iid = inst.get("id", "")
        if not ID.match(iid): raise Problem(f"{name}: instrument id \"{iid}\": use lowercase letters, digits and dashes")
        if iid in ids: raise Problem(f"{name}: instrument id \"{iid}\" used twice")
        ids.add(iid)
        if inst.get("kind") == "drumKit":
            if not inst.get("pads"): raise Problem(f"{name}/{iid}: a drum kit needs pads")
            notes = set()
            for n, pad in enumerate(inst["pads"]):
                if "file" not in pad and not pad.get("layers"): raise Problem(f"{name}/{iid}: pad \"{pad.get('name')}\" has no file")
                note = pad.get("note", 36 + n)
                if not note_ok(note): raise Problem(f"{name}/{iid}: pad note {note!r} isn't 0-127 or a name like \"C2\"")
                if note in notes: raise Problem(f"{name}/{iid}: two pads on note {note}")
                notes.add(note)
                pname = pad.get("name")
                if "label" in pad and (not isinstance(pad["label"], str) or not 0 < len(pad["label"]) <= 16):
                    raise Problem(f"{name}/{iid}: pad \"{pname}\" label must be 1-16 characters")
                if "color" in pad and not (isinstance(pad["color"], str) and COLOR.match(pad["color"])):
                    raise Problem(f"{name}/{iid}: pad \"{pname}\" color {pad['color']!r} must be \"#RRGGBB\"")
                if "icon" in pad and pad["icon"] not in ICONS:
                    raise Problem(f"{name}/{iid}: pad \"{pname}\" icon {pad['icon']!r} isn't in tools/pad-icons.json")
        elif inst.get("kind") == "instrument":
            if not inst.get("zones") and "sfz" not in inst: raise Problem(f"{name}/{iid}: an instrument needs zones")
            for z in inst.get("zones", []):
                if "root" not in z: raise Problem(f"{name}/{iid}: {z.get('file')} needs a root note")
                for k in ("root", "low", "high"):
                    if k in z and not note_ok(z[k]): raise Problem(f"{name}/{iid}: {z['file']} {k} {z[k]!r} isn't a note")
        else:
            raise Problem(f"{name}/{iid}: kind must be \"drumKit\" or \"instrument\"")
    for f in sorted(referenced(pkg)):
        if not safe(f): raise Problem(f"{name}: unsafe path \"{f}\" (relative, no ..)")
        full = os.path.join(folder, f)
        if not os.path.isfile(full): raise Problem(f"{name}: {f} is used but missing")
        ext = os.path.splitext(f)[1].lower()
        if ext != ".sfz" and ext not in AUDIO: raise Problem(f"{name}: {f}: unsupported type {ext}")
        if ext == ".wav": wav_check(full, f"{name}/{f}")
    return pkg


def packages():
    return sorted(d for d in os.listdir(ROOT)
                  if not d.startswith(".") and os.path.isfile(os.path.join(ROOT, d, MANIFEST)))


def file_record(folder, rel):
    data = open(os.path.join(folder, rel), "rb").read()
    return {"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def index():
    listings, problems = [], []
    for d in packages():
        folder = os.path.join(ROOT, d)
        try:
            pkg = check(folder)
        except Problem as e:
            problems.append(str(e)); continue
        files = [file_record(folder, MANIFEST)] + [file_record(folder, f) for f in sorted(referenced(pkg))]
        listings.append({
            "id": pkg["id"], "name": pkg["name"], "version": pkg["version"],
            "summary": pkg.get("summary"), "author": pkg.get("author"),
            "path": d + "/", "bytes": sum(f["bytes"] for f in files),
            "license": pkg["license"]["id"],
            "instruments": [{"name": i["name"], "kind": i["kind"]} for i in pkg["instruments"]],
            "files": files,
        })
    if problems:
        sys.exit("\n".join(f"error: {p}" for p in problems))
    with open(os.path.join(ROOT, "index.json"), "w", encoding="utf-8") as out:
        json.dump({"format": INDEX_FORMAT, "formatVersion": 1, "packages": listings}, out, indent=2, ensure_ascii=False)
        out.write("\n")
    for l in listings:
        print(f"{l['id']} {l['version']}: {len(l['files']) - 1} files, {l['bytes'] / 1e6:.1f} MB")
    print(f"index.json: {len(listings)} package(s)")


def main(argv):
    if len(argv) >= 1 and argv[0] == "index" and len(argv) == 1:
        return index()
    if len(argv) >= 1 and argv[0] == "check":
        folders = argv[1:] or [os.path.join(ROOT, d) for d in packages()]
        failed = False
        for folder in folders:
            try:
                pkg = check(folder)
                print(f"{pkg['id']} {pkg['version']}: {len(pkg['instruments'])} instrument(s), "
                      f"{len(referenced(pkg))} files — OK")
            except Problem as e:
                print(f"error: {e}"); failed = True
        sys.exit(1 if failed else 0)
    sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
