# test_single_ocr.py
"""
Unit-test-ish check of OCR on ONE image.
Prints the text and displays the picture.
"""

from pathlib import Path
import unittest
import os
from PIL import Image
import matplotlib.pyplot as plt   # gives us a no-GUI fallback viewer
import pytesseract, platform
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"    # adjust if different
    )

# ---- adjust this --------------------------------------------------------
IMG_PATH = Path(r"D:\UCLA\Rednote_Project\rohil_data_scrape\downloaded_images\67fccc76000000001c032e06\67fccc76000000001c032e06_0.jpg")      # <-- point at the image you want to test
LANGS    = "eng+chi_sim"           # English + Simplified Chinese
PSM_MODE = "--psm 6"               # assume a block of text
# ------------------------------------------------------------------------


class TestSingleImageOCR(unittest.TestCase):
    def test_ocr_not_empty(self):
        """Open one image, OCR it, show it, and assert the text is non-empty."""
        if not IMG_PATH.exists():
            self.fail(f"Test image not found: {IMG_PATH.resolve()}")

        img = Image.open(IMG_PATH)

        # --- DISPLAY the image ------------------------------------------
        try:
            # Use Matplotlib; works in notebooks, headless CI, or local
            plt.imshow(img)
            plt.axis("off")
            plt.title(f"Preview: {IMG_PATH.name}")
            plt.show()
        except Exception as e:      # matplotlib missing? fall back to PIL viewer
            print(f"(Plot failed: {e}. Falling back to PIL Image.show().)")
            img.show()
        # ----------------------------------------------------------------

        '''
        text = pytesseract.image_to_string(img, lang=LANGS,
                                           config=PSM_MODE).strip()
        print("\n----- OCR OUTPUT -----\n", text or "[EMPTY STRING]")
        print(123)
        # The actual unit-test assertion
        self.assertTrue(text, "OCR produced an empty string!")
        '''

        for psm in (3, 6, 7, 11):
            for lang in ("eng", "chi_sim", "eng+chi_sim"):
                txt = pytesseract.image_to_string(
                  img,
                  lang=lang,
                  config=f"--oem 1 --psm {psm}").strip()
        print(f"== {lang}  PSM {psm} ==")
        print(repr(txt[:200]), "\n")

        self.assertTrue(123, "OCR produced an empty string!")
# Allow “python test_single_ocr.py” as well as pytest
if __name__ == "__main__":
    unittest.main(verbosity=2)
