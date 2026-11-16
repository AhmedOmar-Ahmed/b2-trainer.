"""Record every sentence of the trainer with natural Microsoft neural voices.

Reads the lesson text from the JSON block in index.html, writes
audio/<voice>/<topic>/<section>_<sentence>.mp3 and audio/timings.js
(word timings used for highlighting). Only new or changed sentences are recorded.

Teil 2 (discussion) is recorded in all voices; Teil 3 dialogues and the
building blocks only in Seraphina and Florian (Person B / Person A).
Records at most MAX_NEW clips per run and exits with code 3 if more remain,
so the workflow can commit in batches.
"""
import asyncio, hashlib, json, os, re, sys

import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "audio")
VOICES = {
    "seraphina": "de-DE-SeraphinaMultilingualNeural",
    "florian": "de-DE-FlorianMultilingualNeural",
    "katja": "de-DE-KatjaNeural",
    "conrad": "de-DE-ConradNeural",
}
ALL = tuple(VOICES)
DUO = ("seraphina", "florian")
RATE = "-5%"
MAX_NEW = int(os.environ.get("MAX_NEW", "400"))
TEST = "Hallo! Ich bin deine Stimme für die B2-Prüfung. Viel Erfolg beim Lernen!"


def load_items():
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="data">(.*?)</script>', html, re.S)
    data = json.loads(m.group(1).replace("<\\/", "</"))
    items = {"test": (TEST, ALL)}
    for t in data["topics"]:
        typ = t.get("type")
        voices = ALL if not typ else DUO
        for si, (head, _head_en, sents) in enumerate(t["sections"]):
            if not typ:
                items[f"{t['id']}/{si}_p"] = (f"Punkt {si + 1}: {head}. Bitte sprich jetzt.", ALL)
            elif typ == "plan" and head == "Person B":
                items[f"{t['id']}/{si}_p"] = ("Du bist Person B. Bitte antworte jetzt.", DUO)
            for k, (de, _en) in enumerate(sents):
                items[f"{t['id']}/{si}_{k}"] = (de, voices)
    return items


async def record(text, voice, path):
    try:
        com = edge_tts.Communicate(text, voice, rate=RATE, boundary="WordBoundary")
    except TypeError:  # older edge-tts versions have no boundary argument
        com = edge_tts.Communicate(text, voice, rate=RATE)
    timings, pos = [], 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word = chunk["text"]
                idx = text.find(word, pos)
                if idx >= 0:
                    timings.append([idx, round(chunk["offset"] / 10000)])
                    pos = idx + len(word)
    return timings


async def main():
    items = load_items()
    man_path = os.path.join(AUDIO, "manifest.json")
    manifest = json.load(open(man_path)) if os.path.exists(man_path) else {}
    made = remaining = failed = 0
    new_manifest, out = {}, {}
    for vname, vid in VOICES.items():
        old, new = manifest.get(vname, {}), {}
        for key, (text, voices) in items.items():
            if vname not in voices:
                continue
            h = hashlib.sha1(f"{vid}|{RATE}|{text}".encode()).hexdigest()
            path = os.path.join(AUDIO, vname, key + ".mp3")
            if key in old and old[key]["h"] == h and os.path.exists(path):
                new[key] = old[key]
                continue
            if made >= MAX_NEW:
                remaining += 1
                continue
            for attempt in range(3):
                try:
                    new[key] = {"h": h, "t": await record(text, vid, path)}
                    made += 1
                    break
                except Exception as e:  # network hiccup: retry, then leave it for the next run
                    print("retry", vname, key, e, file=sys.stderr)
                    await asyncio.sleep(3)
            else:
                failed += 1
        new_manifest[vname] = new
        out[vname] = {k: v["t"] for k, v in new.items()}
    os.makedirs(AUDIO, exist_ok=True)
    json.dump(new_manifest, open(man_path, "w"), ensure_ascii=False)
    with open(os.path.join(AUDIO, "timings.js"), "w", encoding="utf-8") as f:
        f.write("window.TIMINGS=" + json.dumps(out, separators=(",", ":")) + ";\n")
    print(f"Recorded {made} clips, {remaining} still to do, {failed} failed.")
    if remaining:
        sys.exit(3)


asyncio.run(main())
