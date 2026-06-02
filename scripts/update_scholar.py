#!/usr/bin/env python3
import datetime as dt
import html
import json
import re
import ssl
import sys
import urllib.request

SCHOLAR_URL = "https://scholar.google.com/citations?user=3WzH5ewAAAAJ&hl=en"


def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    value = value.replace("\u2013", "-").replace("\u2026", "...")
    return re.sub(r"\s+", " ", value).strip()


def absolute_url(value):
    value = html.unescape(value or "")
    if value.startswith("/"):
        return "https://scholar.google.com" + value
    return value


def fetch_profile():
    request = urllib.request.Request(
        SCHOLAR_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GitHub Pages publication updater)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", errors="ignore")
    except urllib.error.URLError as error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(error):
            raise
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(request, timeout=30, context=context) as response:
            return response.read().decode("utf-8", errors="ignore")


def parse_publications(markup):
    publications = []
    rows = re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', markup, re.S)

    for row in rows:
        title_match = re.search(
            r'<a href="([^"]+)" class="gsc_a_at">(.*?)</a>', row, re.S
        )
        if not title_match:
            continue

        gray_rows = re.findall(r'<div class="gs_gray">(.*?)</div>', row, re.S)
        citation_match = re.search(r'<td class="gsc_a_c"[^>]*>(.*?)</td>', row, re.S)
        year_match = re.search(
            r'<span class="gsc_a_h gsc_a_hc gs_ibl">(.*?)</span>', row, re.S
        )

        publications.append(
            {
                "title": clean(title_match.group(2)),
                "authors": clean(gray_rows[0]) if gray_rows else "",
                "venue": clean(gray_rows[1]) if len(gray_rows) > 1 else "",
                "year": clean(year_match.group(1)) if year_match else "",
                "citations": clean(citation_match.group(1)) if citation_match else "",
                "url": absolute_url(title_match.group(1)),
            }
        )

    return publications


def main():
    markup = fetch_profile()
    publications = parse_publications(markup)
    if not publications:
        print("No publications parsed from Google Scholar.", file=sys.stderr)
        return 1

    payload = {
        "source": SCHOLAR_URL,
        "updated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "publications": publications,
    }

    with open("publications.json", "w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")

    print(f"Updated {len(publications)} publications.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
