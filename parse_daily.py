import argparse
import json
import os
import re
from typing import List, Dict, Any


INLINE_FIELD_RE = re.compile(r"\s*\[[^\]]*::[^\]]*\]")
WIKI_IMAGE_RE = re.compile(r"!\[\[([^\]]+)\]\]")


def strip_inline_fields(text: str) -> str:
    return INLINE_FIELD_RE.sub("", text).strip()


def extract_images(text: str) -> List[str]:
    images = []
    for m in WIKI_IMAGE_RE.finditer(text):
        images.append(m.group(1).strip())
    # Also support inline "[diet_photo:: path]" fallback
    m2 = re.search(r"\[diet_photo::\s*([^\]]+?)\s*\]", text)
    if m2:
        p = m2.group(1).strip()
        if p and p not in images:
            images.append(p)
    return images


def strip_wiki_images(text: str) -> str:
    return WIKI_IMAGE_RE.sub("", text)


def parse_daily_markdown(md_path: str) -> Dict[str, Any]:
    with open(md_path, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    basename = os.path.basename(md_path)
    date = os.path.splitext(basename)[0]

    result: Dict[str, Any] = {
        "date": date,
        "sleep": [],
        "exercise": [],
        "diet": [],
    }

    section = None  # one of {None, 'sleep', 'exercise', 'diet'}
    in_code_block = False

    # Sleep temp holder
    cur_sleep = {"start": None, "end": None, "hours": None}

    # Exercise temp holder
    cur_ex = {"type": None, "start": None, "duration": None}

    # Diet temp holder
    cur_diet = {"time": None, "item": None, "images": []}

    def flush_sleep():
        if cur_sleep["start"] and cur_sleep["end"] and cur_sleep["hours"] is not None:
            # cast hours to float if possible
            try:
                hours_val = float(str(cur_sleep["hours"]).strip())
            except Exception:
                hours_val = None
            result["sleep"].append({
                "start": str(cur_sleep["start"]).strip(),
                "end": str(cur_sleep["end"]).strip(),
                "hours": hours_val,
            })
        cur_sleep["start"] = None
        cur_sleep["end"] = None
        cur_sleep["hours"] = None

    def flush_ex():
        if cur_ex["type"] or cur_ex["start"] or cur_ex["duration"]:
            result["exercise"].append({
                "type": (cur_ex["type"] or "").strip(),
                "start": (cur_ex["start"] or "").strip(),
                "duration": (cur_ex["duration"] or "").strip(),
            })
        cur_ex["type"] = None
        cur_ex["start"] = None
        cur_ex["duration"] = None

    def flush_diet():
        if cur_diet["time"] or cur_diet["item"] or cur_diet["images"]:
            # de-dup images, preserve order
            seen = set()
            imgs: List[str] = []
            for im in cur_diet["images"]:
                if im and im not in seen:
                    seen.add(im)
                    imgs.append(im)
            result["diet"].append({
                "time": (cur_diet["time"] or "").strip(),
                "item": (cur_diet["item"] or "").strip(),
                "images": imgs,
            })
        cur_diet["time"] = None
        cur_diet["item"] = None
        cur_diet["images"] = []

    for raw in lines:
        line = raw.strip()

        # Code block guard
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Detect sections by headings (contains specific keywords/emojis)
        if line.startswith("#### "):
            # Flushing ongoing items when leaving sections
            if section == 'sleep':
                flush_sleep()
            elif section == 'exercise':
                flush_ex()
            elif section == 'diet':
                flush_diet()

            if "睡眠" in line:
                section = 'sleep'
                continue
            if "運動" in line:
                section = 'exercise'
                continue
            if "飲食" in line:
                section = 'diet'
                continue
            section = None
            continue

        # Parse according to section
        if section == 'sleep':
            if line.startswith("睡覺時間："):
                cur_sleep["start"] = strip_inline_fields(line.split("：", 1)[1])
                continue
            if line.startswith("起床時間："):
                cur_sleep["end"] = strip_inline_fields(line.split("：", 1)[1])
                continue
            if line.startswith("持續時間(H)："):
                cur_sleep["hours"] = strip_inline_fields(line.split("：", 1)[1])
                flush_sleep()
                continue

        elif section == 'exercise':
            if line.startswith("種類："):
                # Starting a new exercise block → flush previous
                flush_ex()
                cur_ex["type"] = strip_inline_fields(line.split("：", 1)[1])
                continue
            if line.startswith("開始時間："):
                cur_ex["start"] = strip_inline_fields(line.split("：", 1)[1])
                continue
            if line.startswith("持續時間："):
                dur = strip_inline_fields(line.split("：", 1)[1])
                # Normalize duration: keep as string (minutes or HHMM)
                cur_ex["duration"] = dur
                flush_ex()
                continue

        elif section == 'diet':
            # Start of a new diet record
            if line.startswith("飲食時間(HHMM)："):
                flush_diet()
                cur_diet["time"] = strip_inline_fields(line.split("：", 1)[1])
                continue
            if line.startswith("飲食項目："):
                raw = line.split("：", 1)[1]
                # capture images from the same line
                cur_diet["images"].extend(extract_images(raw))
                # strip wiki image embeds from the text, and inline fields
                cur_diet["item"] = strip_inline_fields(strip_wiki_images(raw)).strip()
                continue
            if line.startswith("飲食照片："):
                cur_diet["images"].extend(extract_images(line))
                continue

            # Images may be on the following lines; collect any wiki images while in diet section
            imgs = extract_images(line)
            if imgs:
                cur_diet["images"].extend(imgs)
                # don't continue; also try to append any plain text in the same line (without wiki embeds)

            # Append free-form text lines (e.g., next line describing the item)
            clean = strip_inline_fields(strip_wiki_images(line)).strip()
            if clean:
                if cur_diet["item"]:
                    # separate with a space
                    cur_diet["item"] = (cur_diet["item"] + " " + clean).strip()
                else:
                    cur_diet["item"] = clean
                continue

    # Final flush at EOF
    if section == 'sleep':
        flush_sleep()
    elif section == 'exercise':
        flush_ex()
    elif section == 'diet':
        flush_diet()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse an Obsidian daily note to JSON")
    parser.add_argument("input", help="Path to the daily markdown file (e.g., 2025-10-09.md)")
    parser.add_argument("--output", "-o", default="data.json", help="Output JSON path")
    args = parser.parse_args()

    data = parse_daily_markdown(args.input)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()




