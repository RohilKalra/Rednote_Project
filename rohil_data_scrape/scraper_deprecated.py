from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import requests
import logging
from datetime import datetime


class XiaohongshuScraper:
    def __init__(self, save_dir="downloaded_images"):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_dir = os.path.join(save_dir, self.timestamp)
        self.start_time = datetime.now()
        self.setup_logging()
        self.setup_driver()

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        chrome_options = Options()

        # Use default Chrome profile
        chrome_options.add_argument(
            "--user-data-dir=/Users/rohilkalra/Library/Application Support/Google/Chrome/Profile 14"
        )
        chrome_options.add_argument("--profile-directory=Profile 14")

        # Other necessary options
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")

        self.driver = webdriver.Chrome(options=chrome_options)

    def scroll_page(self, scroll_pause_time=3):
        """Scroll the page gradually to load all dynamic content"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        for _ in range(10):  # Increased number of scroll iterations
            # Scroll in smaller increments
            self.driver.execute_script("window.scrollBy(0, window.innerHeight/2);")
            time.sleep(scroll_pause_time)  # Longer pause between scrolls

            try:
                # Wait for new images to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "img[src*='sns-webpic-qc.xhscdn.com']")
                    )
                )
            except Exception as e:
                self.logger.warning(f"Wait timeout during scroll: {e}")

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def download_image(self, img_url, index):
        """Download a single image"""
        try:
            cookies = {
                cookie["name"]: cookie["value"] for cookie in self.driver.get_cookies()
            }

            headers = {
                "User-Agent": self.driver.execute_script("return navigator.userAgent"),
                "Referer": "https://www.xiaohongshu.com",
                "Accept-Ranges": "bytes",
                "Cache-Control": "max-age=2592000",
            }

            response = requests.get(
                img_url, headers=headers, cookies=cookies, stream=True
            )
            if response.status_code == 200:
                img_path = os.path.join(self.save_dir, f"image_{index}.jpg")
                with open(img_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                self.logger.info(f"Successfully downloaded image {index}")
                return True
            else:
                self.logger.error(
                    f"Failed to download image {index}: Status code {response.status_code}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Error downloading image {index}: {e}")
            return False

    def save_metadata(self, url, total_images, successful_downloads, duration):
        metadata_path = os.path.join(self.save_dir, "metadata.txt")
        with open(metadata_path, "w") as f:
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Total images found: {total_images}\n")
            f.write(f"Successfully downloaded: {successful_downloads}\n")
            f.write(f"Duration: {duration:.2f} seconds\n")

    def scrape_images(self, url):
        try:
            os.makedirs(self.save_dir, exist_ok=True)

            self.logger.info(f"Accessing URL: {url}")
            self.driver.get(url)
            time.sleep(10)  # Longer initial wait

            # Scroll gradually
            self.scroll_page()

            # Wait for all images to be present
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "img[src*='sns-webpic-qc.xhscdn.com']")
                )
            )

            images = self.driver.find_elements(
                By.CSS_SELECTOR, "img[src*='sns-webpic-qc.xhscdn.com']"
            )
            self.logger.info(f"Found {len(images)} images")

            successful_downloads = 0
            for index, img in enumerate(images):
                try:
                    img_url = img.get_attribute("src")
                    if img_url and "sns-webpic-qc.xhscdn.com" in img_url:
                        # Wait for each image to be properly loaded
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, f"img[src='{img_url}']")
                            )
                        )
                        if self.download_image(img_url, index):
                            successful_downloads += 1
                            time.sleep(2)  # Longer delay between downloads
                except Exception as e:
                    self.logger.error(f"Error processing image {index}: {e}")

            duration = (datetime.now() - self.start_time).total_seconds()
            self.save_metadata(url, len(images), successful_downloads, duration)
            self.logger.info(f"Successfully downloaded {successful_downloads} images")

        except Exception as e:
            self.logger.error(f"Scraping error: {e}")

    def close_browser(self):
        """Optional method to close the browser when needed"""
        self.driver.quit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape images from Xiaohongshu")
    parser.add_argument("url", help="The URL to scrape")

    args = parser.parse_args()

    scraper = XiaohongshuScraper()
    scraper.scrape_images(args.url)

    # Keep the script running and browser open
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nPress Ctrl+C again to exit...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting...")
            scraper.close_browser()
