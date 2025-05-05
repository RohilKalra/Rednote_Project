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

# Scraping Constants
MAX_SCROLLS = 50  # Number of times to scroll down the page
SCROLL_PAUSE_TIME = 3  # Time to wait between scrolls (seconds)
INITIAL_PAGE_LOAD_WAIT = 5  # Time to wait after loading the initial page
SEARCH_RESULT_LOAD_WAIT = 5  # Time to wait after entering search term
IMAGE_DOWNLOAD_WAIT = 0.1  # Time to wait between downloading images
PROMPT_SWITCH_WAIT = 5  # Time to wait between processing different prompts
SCROLL_LENGTH = 1000  # Pixels to scroll each time

# WebDriver Wait Times
SEARCH_BOX_WAIT = 10  # Time to wait for search box to appear
IMAGE_PRESENCE_WAIT = 15  # Time to wait for images to load
SINGLE_IMAGE_WAIT = 5  # Time to wait for each individual image

# File and Directory Settings
BASE_SAVE_DIR = "downloaded_images"
DOWNLOAD_CHUNK_SIZE = 1024  # Chunk size for downloading images

# Chrome Profile Settings

CHROME_PROFILE_DIR = (
    r"C:\Users\shiyi\AppData\Local\Google\Chrome\User Data\Default"
)
CHROME_PROFILE = "Default"

'''
CHROME_PROFILE_DIR = (
    "/Users/rohilkalra/Library/Application Support/Google/Chrome/Profile 14"
)
CHROME_PROFILE = "Profile 14"
'''

class XiaohongshuScraper:
    def __init__(self):
        self.save_dir = BASE_SAVE_DIR
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
        chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
        chrome_options.add_argument(f"--profile-directory={CHROME_PROFILE}")

        # Other necessary options
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")

        self.driver = webdriver.Chrome(options=chrome_options)

    def create_session_directory(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self.save_dir, self.timestamp)
        os.makedirs(session_dir, exist_ok=True)
        self.session_dir = session_dir
        self.start_time = datetime.now()
        return session_dir

    def scroll_and_collect_images(self):
        """Scroll the page gradually and collect images as we go"""
        self.logger.info("Starting scrolling and collecting images...")
        current_position = 0
        image_urls = set()  # Use a set to avoid duplicates
        no_new_images_count = 0
        min_scrolls = 30  # Minimum number of scrolls before considering stopping

        for i in range(MAX_SCROLLS):
            # Get current visible images
            current_images = self.driver.find_elements(
                By.CSS_SELECTOR, "img[src*='sns-webpic-qc.xhscdn.com']"
            )
            before_count = len(image_urls)

            # Collect new image URLs
            new_urls = set()
            for img in current_images:
                try:
                    url = img.get_attribute("src")
                    if url and url not in image_urls:
                        new_urls.add(url)
                except:
                    continue

            if new_urls:
                image_urls.update(new_urls)
                self.logger.info(
                    f"Scroll {i}: Found {len(new_urls)} new images. Total unique images: {len(image_urls)}"
                )
                no_new_images_count = 0
            else:
                no_new_images_count += 1
                self.logger.info(
                    f"Scroll {i}: No new images found. Total remains: {len(image_urls)}"
                )

            # Scroll down
            current_position += SCROLL_LENGTH
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")

            # Wait longer if we're not finding new images
            if no_new_images_count >= 3:
                time.sleep(SCROLL_PAUSE_TIME * 2)  # Wait twice as long
            else:
                time.sleep(SCROLL_PAUSE_TIME)

            # Only consider stopping if we've done minimum scrolls and haven't found new images in a while
            if i > min_scrolls and no_new_images_count >= 5:
                self.logger.info(
                    f"No new images found in last 5 scrolls after minimum {min_scrolls} scrolls. Stopping."
                )
                break

        self.logger.info(
            f"Finished collecting. Total unique images found: {len(image_urls)}"
        )
        return list(image_urls)

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
                img_path = os.path.join(self.session_dir, f"image_{index}.jpg")
                with open(img_path, "wb") as f:
                    for chunk in response.iter_content(DOWNLOAD_CHUNK_SIZE):
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

    def save_metadata(self, prompt, total_images, successful_downloads, duration):
        metadata_path = os.path.join(self.session_dir, "metadata.txt")
        with open(metadata_path, "w") as f:
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Total images found: {total_images}\n")
            f.write(f"Successfully downloaded: {successful_downloads}\n")
            f.write(f"Duration: {duration:.2f} seconds\n")

    def scrape_images(self, prompt):
        try:
            self.create_session_directory()
            self.logger.info(f"Starting scraping for prompt: {prompt}")

            # Go to xiaohongshu first
            self.logger.info(f"Accessing Xiaohongshu...")
            self.driver.get("https://www.xiaohongshu.com")
            time.sleep(INITIAL_PAGE_LOAD_WAIT)

            # Wait for and find the search box
            search_box = WebDriverWait(self.driver, SEARCH_BOX_WAIT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[placeholder*='搜索']")
                )
            )

            # Clear any existing text and type the prompt
            search_box.clear()
            search_box.send_keys(prompt)
            self.logger.info(f"Searching for: {prompt}")
            search_box.send_keys("\ue007")  # Press Enter

            time.sleep(SEARCH_RESULT_LOAD_WAIT)

            # Scroll and collect images simultaneously
            image_urls = self.scroll_and_collect_images()
            self.logger.info(f"Found total of {len(image_urls)} unique images")

            # Download all collected images
            successful_downloads = 0
            for index, img_url in enumerate(image_urls):
                try:
                    if self.download_image(img_url, index):
                        successful_downloads += 1
                        time.sleep(IMAGE_DOWNLOAD_WAIT)
                except Exception as e:
                    self.logger.error(f"Error processing image {index}: {e}")

            duration = (datetime.now() - self.start_time).total_seconds()
            self.save_metadata(prompt, len(image_urls), successful_downloads, duration)
            self.logger.info(
                f"Successfully downloaded {successful_downloads} images for prompt: {prompt}"
            )

        except Exception as e:
            self.logger.error(f"Scraping error for prompt '{prompt}': {e}")

    def close_browser(self):
        """Close the browser when done"""
        self.driver.quit()


def read_prompts(file_path):
    """Read prompts from a file, skipping empty lines and stripping whitespace"""
    with open(file_path, "r", encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape images from Xiaohongshu using multiple prompts"
    )
    parser.add_argument("prompts_file", help="Path to the file containing prompts")
    args = parser.parse_args()

    try:
        prompts = read_prompts(args.prompts_file)
        if not prompts:
            print("No valid prompts found in the file")
            exit(1)

        scraper = XiaohongshuScraper()

        for prompt in prompts:
            print(f"\nProcessing prompt: {prompt}")
            scraper.scrape_images(prompt)
            time.sleep(PROMPT_SWITCH_WAIT)  # Brief pause between prompts

        print("\nAll prompts processed. Press Ctrl+C to exit...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting...")
            scraper.close_browser()

    except Exception as e:
        print(f"An error occurred: {e}")
        try:
            scraper.close_browser()
        except:
            pass
