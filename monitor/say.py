"""Put a short message on the LED strip from any machine on the LAN.

    python say.py "Deploy done"                  scroll it once over whatever mode is running
    python say.py "Deploy done" --color 0,255,90 ... in that color (default: the strip's current color)
    python say.py "Night shift" --banner         switch to the Banner mode and loop it
Standard library only. STRIP_URL overrides the address (default: the Pi at 10.0.0.10:8750).
"""
import argparse
import json
import os
import sys
import urllib.request

URL = os.environ.get("STRIP_URL", "http://10.0.0.10:8750/api/strip")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", help="up to 160 characters; letters, digits and common punctuation")
    ap.add_argument("--color", help="R,G,B, e.g. 255,150,0")
    ap.add_argument("--banner", action="store_true", help="loop it in Banner mode instead of scrolling once")
    args = ap.parse_args()
    if args.banner:
        body = {"text": args.text, "mode": "text"}
        if args.color:
            body["color"] = [int(v) for v in args.color.split(",")]
    else:
        body = {"say": {"text": args.text}}
        if args.color:
            body["say"]["rgb"] = [int(v) for v in args.color.split(",")]
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
    except OSError as e:
        sys.exit("could not reach the strip: %s" % e)


if __name__ == "__main__":
    main()
