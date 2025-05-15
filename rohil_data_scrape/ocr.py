#!/usr/bin/env python3
"""
Batch-OCR for a tree of image folders.
Each CSV row = one sub-directory of images.
"""

import os
import csv
from pathlib import Path

from PIL import Image       # pip install pillow
#import pytesseract          # pip install pytesseract
import pytesseract, platform
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# Make sure the Tesseract engine itself is installed and on PATH
# macOS:   brew install tesseract
# Ubuntu:  sudo apt-get install tesseract-ocr
LANGS = "eng+chi_sim"
# ---- core --------------------------------------------------------------
def clean(img):
    """Simple Pillow pipeline: grayscale → autocontrast → denoise."""
    from PIL import ImageOps, ImageFilter
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    return img.filter(ImageFilter.MedianFilter())


def ocr_images_in_tree(root_dir: str,
                       output_csv: str = "ocr_output.csv",
                       img_exts = (".png", ".jpg", ".jpeg",
                                   ".tif", ".tiff", ".bmp", ".gif")
                      ) -> None:
    """
    Run OCR on every image inside each *immediate* sub-directory of `root_dir`
    and write results to `output_csv`.
    """
    root = Path(root_dir).expanduser().resolve()

    rows = []
    for subdir in [d for d in root.iterdir() if d.is_dir()]:
        texts = []

        for img_path in subdir.rglob("*.[jJ][pP][gG]"):   # catches .jpg .JPG
            try:
                img = clean(Image.open(img_path))
                txt = pytesseract.image_to_string(
                        img, lang=LANGS, config="--psm 6").strip()
                if txt: texts.append(txt)
            except Exception as e:
                print(f"⚠️  {img_path} failed: {e}")

        if texts:
            rows.append({"directory": subdir.name,
                         "text": "\n".join(texts)})
        else:
            print(f"⚠️  No text found in {subdir}")


        rows.append({
            "directory": subdir.name,
            "text": "\n".join(texts)
        })

    # write CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["directory", "text"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Saved OCR for {len(rows)} sub-directories → {output_csv}")

# ---- CLI wrapper -------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Extract text from images in sub-directories and write to CSV."
    )
    parser.add_argument("root_dir",
                        help="Folder whose sub-directories contain images.")
    parser.add_argument("-o", "--out", default="ocr_output.csv",
                        help="Output CSV filename (default: ocr_output.csv).")
    args = parser.parse_args()

    ocr_images_in_tree(args.root_dir, args.out)
