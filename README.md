# yeah baby. sounds

The official catalog of downloadable sound packages for **yeah baby.**, the iPad groovebox. The app reads this repository directly (yb menu ▸ **Sound Packages…**), so anything merged to `main` is offered to every user within a few minutes.

## Layout

One folder per package. Each holds its samples and a `manifest.json` describing them:

```text
hand-percussion/
├── manifest.json
├── bongo-high-1.wav
├── bongo-high-2.wav
└── …
harpsichord/
├── manifest.json
└── harpsichord-C3.wav …
index.json        ← generated catalog; don't edit
tools/samplepack.py
```

## Adding or updating a package

1. Make a folder named after the package id (e.g. `lofi-kit/`) and put the samples in it. Subfolders are fine, but flat is simplest.
2. Write `manifest.json` (reference below; the two packages here are working examples).
3. Optional: run `python3 tools/samplepack.py check lofi-kit` to catch mistakes early.
4. Push to `main`. GitHub Actions checks every package and rebuilds `index.json`: each file's size and SHA-256, which the app verifies on download. A broken package fails the check with a readable error, and the catalog isn't changed.
5. To update a package, change its files and bump `version`. The app then offers **Update**.

To try a package on the iPad before publishing, copy its folder over (AirDrop, Files) and use **Sound Packages ▸ Import from Files…**.

## Audio files

- **WAV:** 16/24/32-bit PCM or 32-bit float, mono or stereo, any sample rate (44.1 or 48 kHz recommended). Works everywhere.
- **AIFF, CAF, FLAC, MP3, M4A/AAC:** also accepted on iPad and Mac. FLAC is lossless and about half the download size.
- **Trim and prepare:** remove silence before the hit or note; the app starts playback at the first sample.
- **Volume:** level the files the way you want them to play. A pad or zone `gain` can adjust them.
- **Memory:** the app keeps samples in memory while a track uses them, at about 2 bytes per sample per channel. A 10-second stereo note at 48 kHz is about 2 MB. Keep packages under about 50 MB for older iPads.

## `manifest.json`

```json
{
  "format": "yeahbaby.sample-package",
  "formatVersion": 1,
  "id": "lofi-kit",
  "name": "Lo-Fi Kit",
  "version": "1.0.0",
  "author": "Matt Larritt",
  "summary": "Dusty drums sampled from cassette.",
  "license": { "id": "CC0-1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/", "attribution": null },
  "sources": [ { "title": "Recorded at home, 2026", "url": null, "license": "CC0-1.0" } ],
  "instruments": [ ... ]
}
```

| Field | |
|---|---|
| `format`, `formatVersion` | Always `"yeahbaby.sample-package"` and `1`. A newer version number tells older apps they need updating. |
| `id` | Lowercase letters, digits and dashes. Same as the folder name. It must be unique and must never change: projects remember sounds as `package-id/instrument-id`. |
| `version` | Bump it when you change the package; the app then offers **Update**. |
| `license` | `id` is an SPDX identifier (`CC0-1.0`, `CC-BY-4.0`, …) or `LicenseRef-<name>` for your own terms. `attribution` is credit text, if the licence needs one. |
| `sources` | Optional provenance: where the recordings came from. Shown to no one; it's your record. |

### A drum kit

Each pad is one note. A pad has one `file`, or several `layers` from soft to hard.

```json
{
  "id": "kit",
  "name": "Lo-Fi Kit",
  "kind": "drumKit",
  "pads": [
    { "note": 36, "name": "Kick", "layers": [
        { "file": "kick-soft.wav", "maxVelocity": 70 },
        { "file": "kick-hard.wav" } ] },
    { "note": 38, "name": "Snare", "file": "snare.wav", "gain": 0.9 },
    { "note": 42, "name": "Closed Hat", "file": "hat-closed.wav", "choke": 1 },
    { "note": 46, "name": "Open Hat", "file": "hat-open.wav", "choke": 1 }
  ]
}
```

- **`note`:** a MIDI number or a name (middle C is `"C4"` = 60, so `"C2"` = 36; `#` and `b` work). If you leave it out, pads count up from 36 in order. Use [General MIDI drum notes](https://en.wikipedia.org/wiki/General_MIDI#Percussion) (36 kick, 38 snare, 42/46 hats, 49 crash…) so external pads and MIDI files line up.
- **Order:** pads appear in the step grid and pad grid in the order listed.
- **`layers`:** each layer plays up to its `maxVelocity`; the last one covers the rest up to 127.
- **`gain`:** linear; 1 = as recorded, 0.5 ≈ −6 dB.
- **`choke`:** pads with the same number cut each other off, e.g. a closed hat stops the open hat.

### A pitched instrument

Each zone is one recorded note. Give its `root` (the pitch it was recorded at); the app works out the key ranges halfway between neighbouring roots unless you give `low`/`high`.

```json
{
  "id": "felt-piano",
  "name": "Felt Piano",
  "kind": "instrument",
  "category": "Keys",
  "release": 0.4,
  "velocityTracking": 0.7,
  "zones": [
    { "file": "c3-soft.wav", "root": "C3", "highVelocity": 80 },
    { "file": "c3-hard.wav", "root": "C3", "lowVelocity": 81 },
    { "file": "e3.wav", "root": "E3", "tune": -6 },
    { "file": "g3-pad.wav", "root": "G3", "low": "F3", "high": "B3",
      "loopStart": 22050, "loopEnd": 88200 }
  ]
}
```

| Instrument field | Default | |
|---|---|---|
| `category` | "Instruments" | Section in the Add Track ▸ Instruments menu, e.g. Keys, Strings, Brass, Woodwinds, Synths, Vocals. |
| `attack`, `release` | 0, 0.3 | Seconds. |
| `velocityTracking` | 1 | 0 = every note equally loud, 1 = fully velocity-sensitive. |
| `gainDb` | 0 | Whole-instrument level. |
| `loopMode` | — | `"none"`, `"oneShot"` (ignores note-off), `"sustain"` (loops while held, then plays out) or `"continuous"`. By default a zone with loop points loops continuously, and one without plays once until the key is released. |

| Zone field | |
|---|---|
| `root` | Required. The note the sample sounds at. |
| `low`, `high` | Key range. Leave out to split halfway between roots. |
| `lowVelocity`, `highVelocity` | Velocity range, 1–127. Zones with the same velocity range form a layer, and key ranges are split within each layer. |
| `tune` | Cents, to correct a slightly sharp or flat recording. |
| `gainDb`, `pan` | Level, and position from −1 (left) to 1 (right). |
| `loopStart`, `loopEnd` | Sustain loop in sample frames, end exclusive. Pick zero crossings, or crossfade the loop in your editor first. |

Advanced: instead of `zones`, an instrument may give `"sfz": "file.sfz"`, a file inside the package. Only the SFZ subset in docs/decisions.md D-044 is supported.

## `index.json` (generated)

The app reads this file to show what's available. It lists each package's folder, version, licence, size, and every file with its size and SHA-256, including `manifest.json`. A download is checked against it file by file, and only installed when everything matches.

## Hosting notes

- Files are served from `https://raw.githubusercontent.com/MattLarritt/yeah-baby-sounds/main/`. GitHub caches that address for about five minutes after a push.
- Individual files must be under 100 MB, and the repository should stay well under a few GB. Git LFS can't be used: raw URLs don't serve LFS content.

## Licensing

Only add sounds that may be redistributed inside an app: your own recordings, CC0, or a licence that explicitly allows redistributing the raw samples. "Royalty-free for use in your music" usually does **not** cover redistributing the samples themselves.

- Every package declares its licence in `manifest.json`, and the app shows it before download.
- Put credit text in `license.attribution` when the licence requires it.
- Record where the recordings came from in `sources`.

## Examples

Both examples are curated from the CC0 [Versilian Community Sample Library](https://github.com/sgossner/VCSL):
- **hand-percussion:** a 13-pad drum kit (bongos, congas, cabasa, claves, woodblocks, triangle with mute choke), 1.9 MB.
- **harpsichord:** a 28-zone pitched instrument with automatic key splits, 6.5 MB.
