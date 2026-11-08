"""Put a message on the LED strip from any machine on the LAN. It scrolls over whatever is running.

    python say.py "Deploy done"
    python say.py "TESTS PASS :check:" --style rainbow --repeat 2
    python say.py "SOMETHING IS ON FIRE" --style siren --speed 8 --color 255,0,0
    python say.py "Night shift" --banner          switch to Banner mode and loop it until changed
    python say.py "BUSY" --banner --static --color 255,0,0 --duration 600
                                                  hold short text still, in red, for 10 minutes
    python say.py --restore                       end a banner and go back to the mode it interrupted

A banner takes over the wall (the mode it replaced is remembered); a one-shot message does not.

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
    ap.add_argument("text", nargs="?", help="the message")
    ap.add_argument("--color", type=rgb, help="R,G,B, e.g. 255,150,0 (default: the strip's current color)")
    ap.add_argument("--style", choices=STYLES, default="plain")
    ap.add_argument("--speed", type=int, help="1-10 (default: the strip's speed setting)")
    ap.add_argument("--repeat", type=int, default=1, help="1-5 passes")
    ap.add_argument("--banner", action="store_true", help="loop it in Banner mode instead of scrolling once")
    ap.add_argument("--static", action="store_true", help="banner only: hold short text still, centred")
    ap.add_argument("--duration", type=int, help="banner only: seconds before the wall goes back (default: stays)")
    ap.add_argument("--restore", action="store_true", help="end the banner and go back to the previous mode")
    args = ap.parse_args()
    if args.restore:
        body = {"restore": True}
    elif not args.text:
        ap.error("give some text, or --restore")
    elif args.banner:
        body = {"text": args.text, "mode": "text", "text_style": args.style, "text_static": args.static,
                "text_duration": args.duration or 0}
        if args.color:
            body["color"] = args.color
        if args.speed:
            body["speed"] = args.speed
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
