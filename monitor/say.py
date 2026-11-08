"""Put a message on the LED strip from any machine on the LAN. It scrolls over whatever is running.

    python say.py "Deploy done"
    python say.py "TESTS PASS :check:" --style rainbow --repeat 2
    python say.py "SOMETHING IS ON FIRE" --style siren --speed 8 --color 255,0,0
    python say.py "Night shift" --banner          switch to the Banner mode and loop it

Styles: plain rainbow flash wave shake fire disco siren sparkle
Icons (type them in the text): :heart: :smile: :star: :skull: :ghost: :cat: :rocket: :bolt: :check: :x:
The wall is 60 pixels wide, so about 15 letters show at once; the message scrolls. Up to 160
characters; lower case shows as capitals. --speed 1-10, --repeat 1-5 passes.
Standard library only. STRIP_URL overrides the address (default: the Pi at 10.0.0.10:8750).
"""
import argparse
import json
import os
import sys
import urllib.request

URL = os.environ.get("STRIP_URL", "http://10.0.0.10:8750/api/strip")
STYLES = ("plain", "rainbow", "flash", "wave", "shake", "fire", "disco", "siren", "sparkle")


def rgb(text):
    return [int(v) for v in text.split(",")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", help="the message")
    ap.add_argument("--color", type=rgb, help="R,G,B, e.g. 255,150,0 (default: the strip's current color)")
    ap.add_argument("--style", choices=STYLES, default="plain")
    ap.add_argument("--speed", type=int, help="1-10 (default: the strip's speed setting)")
    ap.add_argument("--repeat", type=int, default=1, help="1-5 passes")
    ap.add_argument("--banner", action="store_true", help="loop it in Banner mode instead of scrolling once")
    args = ap.parse_args()
    if args.banner:
        body = {"text": args.text, "mode": "text"}
        if args.color:
            body["color"] = args.color
    else:
        body = {"say": {"text": args.text, "style": args.style, "repeat": args.repeat}}
        if args.color:
            body["say"]["rgb"] = args.color
        if args.speed:
            body["say"]["speed"] = args.speed
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
    except OSError as e:
        sys.exit("could not reach the strip: %s" % e)


if __name__ == "__main__":
    main()
