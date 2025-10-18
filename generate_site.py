import argparse
import io
import json
import os
import shutil
from datetime import date

from parse_daily import parse_daily_markdown


def parse_date(s: str) -> date:
    s = s.strip()
    if len(s) == 5:  # MM-DD
        year = 2025  # default per current dataset
        mm, dd = map(int, s.split('-'))
        return date(year, mm, dd)
    # YYYY-MM-DD
    y, m, d = map(int, s.split('-'))
    return date(y, m, d)


def build_days(vault_daily_dir: str, start: date, end: date):
    ds = []
    cur = start
    while cur <= end:
        fname = cur.strftime('%Y-%m-%d.md')
        p = os.path.join(vault_daily_dir, fname)
        if os.path.isfile(p):
            ds.append(parse_daily_markdown(p))
        cur = cur.fromordinal(cur.toordinal() + 1)
    return ds


def embed_json_into_index(index_path: str, data_obj):
    with io.open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    start_tag = '<script id="data-json" type="application/json">'
    start_idx = html.find(start_tag)
    if start_idx == -1:
        raise RuntimeError('data-json script tag not found in index.html')
    end_idx = html.find('</script>', start_idx)
    if end_idx == -1:
        raise RuntimeError('closing script tag not found in index.html')
    new_json = json.dumps(data_obj, ensure_ascii=False)
    new_html = html[:start_idx + len(start_tag)] + new_json + html[end_idx:]
    with io.open(index_path, 'w', encoding='utf-8') as f:
        f.write(new_html)


def write_index_copy(index_src: str, start: date, end: date) -> str:
    base_dir = os.path.dirname(index_src) or '.'
    name = f"index-{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}.html"
    dst = os.path.join(base_dir, name)
    with io.open(index_src, 'r', encoding='utf-8') as f:
        html = f.read()
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(html)
    return dst


def find_file_recursively(root_dir: str, basename: str) -> str | None:
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        if basename in filenames:
            return os.path.join(dirpath, basename)
    return None


def copy_images_for_days(days: list, vault_assets: str, site_images: str) -> tuple[int, list[str]]:
    os.makedirs(site_images, exist_ok=True)
    vault_root = os.path.dirname(vault_assets.rstrip('/\\'))
    copied = 0
    missing: list[str] = []

    # collect basenames from all days
    need: set[str] = set()
    for day in days:
        for d in day.get('diet', []) or []:
            for src in d.get('images', []) or []:
                if not src:
                    continue
                name = os.path.basename(str(src))
                if name:
                    need.add(name)

    for name in sorted(need):
        candidate = os.path.join(vault_assets, name)
        if not os.path.isfile(candidate):
            alt = find_file_recursively(vault_root, name)
            if alt and os.path.isfile(alt):
                candidate = alt
            else:
                missing.append(name)
                continue
        dst_path = os.path.join(site_images, name)
        try:
            shutil.copy2(candidate, dst_path)
            copied += 1
        except Exception:
            missing.append(name)
            continue

    return copied, missing


def main():
    ap = argparse.ArgumentParser(description='Generate static index.html with embedded JSON from a date range')
    ap.add_argument('--start', required=True, help='start date (MM-DD or YYYY-MM-DD)')
    ap.add_argument('--end', required=True, help='end date (MM-DD or YYYY-MM-DD)')
    ap.add_argument('--vault-daily', default=r'L:\\我的雲端硬碟\\GD_ObsidianVault\\02_Daily', help='path to 02_Daily directory')
    ap.add_argument('--vault-assets', default=r'L:\\我的雲端硬碟\\GD_ObsidianVault\\1000_assets', help='path to 1000_assets directory for images')
    ap.add_argument('--site-images', default=r'images/1000_assets', help='destination images directory inside the site')
    ap.add_argument('--index', default='index.html', help='path to index.html to update')
    args = ap.parse_args()

    start = parse_date(args.start)
    end = parse_date(args.end)
    if start > end:
        start, end = end, start

    days = build_days(args.vault_daily, start, end)
    data_obj = { 'days': days }

    # Write data.json for inspection
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data_obj, f, ensure_ascii=False, indent=2)

    # Embed into index.html
    embed_json_into_index(args.index, data_obj)
    output_copy = write_index_copy(args.index, start, end)
    # Auto-copy images needed for the range (no prompts)
    copied, missing = copy_images_for_days(days, args.vault_assets, args.site_images)
    print(f'Wrote {len(days)} day(s) into data.json and embedded into {args.index}')
    print(f'Also wrote range file: {output_copy}')
    print(f'Images copied: {copied} -> {args.site_images}')
    if missing:
        print('Images not found (skipped):')
        for m in missing:
            print(f' - {m}')


if __name__ == '__main__':
    main()


