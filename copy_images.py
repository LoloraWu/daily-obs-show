import argparse
import json
import os
import shutil


def find_file_recursively(root_dir: str, basename: str) -> str | None:
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        if basename in filenames:
            return os.path.join(dirpath, basename)
    return None


def main():
    p = argparse.ArgumentParser(description="Copy diet images to site images/1000_assets")
    p.add_argument("--data", default="data.json", help="Path to data.json")
    p.add_argument("--vault-assets", required=True, help="Path to vault 1000_assets directory (e.g., L:/我的雲端硬碟/GD_ObsidianVault/1000_assets)")
    p.add_argument("--site-images", default="images/1000_assets", help="Destination site images folder")
    args = p.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    os.makedirs(args.site_images, exist_ok=True)
    vault_root = os.path.dirname(args.vault_assets.rstrip("/\\"))

    copied = 0
    missing = []
    for d in data.get("diet", []):
        for src in d.get("images", []):
            if not src:
                continue
            name = os.path.basename(src)
            # prefer in 1000_assets, else search entire vault
            candidate = os.path.join(args.vault_assets, name)
            if not os.path.isfile(candidate):
                found = find_file_recursively(vault_root, name)
                if found and os.path.isfile(found):
                    candidate = found
                else:
                    missing.append(src)
                    continue
            dst_path = os.path.join(args.site_images, name)
            shutil.copy2(candidate, dst_path)
            copied += 1

    print(f"Copied {copied} images to {args.site_images}")
    if missing:
        print("Missing (not found in vault 1000_assets or vault root):")
        for m in missing:
            print(" -", m)


if __name__ == "__main__":
    main()


