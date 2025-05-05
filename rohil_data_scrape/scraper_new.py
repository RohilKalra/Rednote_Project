import re
from urllib.parse import urlparse
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
MAX_SCROLLS = 12  # Number of times to scroll down the page
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

    # Renamed function - collects items based on the anchor tag
    # Renamed function - collects items based on the anchor tag
    def scroll_and_collect_items(self):
        """Scroll the page gradually and collect post links (with params) and image URLs""" # Docstring updated
        self.logger.info("Starting scrolling and collecting post links (with params) and image URLs...") # Log updated
        current_position = 0
        image_urls = set()
        post_urls = set()
        processed_item_ids = set() # Keep track of processed items

        no_new_items_count = 0
        min_scrolls = 20 # Adjust if needed

        for i in range(MAX_SCROLLS):
            # Find the specific anchor tags that contain the post link structure
            current_items = self.driver.find_elements(By.CSS_SELECTOR, "a.cover[href*='/search_result/']")

            new_images_found_this_scroll = 0
            new_posts_found_this_scroll = 0

            for item_link_element in current_items:
                post_id = None
                href = None
                try:
                    # --- Extract Post ID and Query String from href ---
                    href = item_link_element.get_attribute('href')
                    query_string = "" # Initialize query string

                    if href:
                        # Extract Post ID using Regex
                        match = re.search(r'/search_result/([a-f0-9]+)', href)
                        if match:
                            post_id = match.group(1)

                        # Extract Query String using urlparse
                        try:
                            parsed_original_href = urlparse(href)
                            if parsed_original_href.query:
                                query_string = parsed_original_href.query # Get 'xsec_token=...&xsec_source=...'
                        except Exception as parse_e:
                             self.logger.warning(f"Could not parse query string from href {href}: {parse_e}")
                    # --- ---

                    if post_id and post_id not in processed_item_ids:
                        processed_item_ids.add(post_id)

                        # --- Construct the correct post URL WITH query parameters ---
                        base_url = f"https://www.xiaohongshu.com/explore/{post_id}"
                        # Append query string if it exists
                        post_url = f"{base_url}?{query_string}" if query_string else base_url
                        # --- ---

                        if post_url not in post_urls:
                            post_urls.add(post_url)
                            new_posts_found_this_scroll += 1

                        # --- Find image URL within this specific anchor tag ---
                        try:
                            img = item_link_element.find_element(By.TAG_NAME, "img")
                            img_url = img.get_attribute("src")
                            if img_url and "sns-webpic-qc.xhscdn.com" in img_url and img_url not in image_urls:
                                image_urls.add(img_url)
                                new_images_found_this_scroll += 1
                        except Exception as img_e:
                            self.logger.warning(f"Could not find expected image within link element for post ID {post_id}: {img_e}")
                        # --- ---

                except Exception as item_e:
                    self.logger.warning(f"Error processing a link element (href: {href}): {item_e}")
                    continue

            # --- Logging and stopping logic (unchanged) ---
            if new_images_found_this_scroll > 0 or new_posts_found_this_scroll > 0:
                 self.logger.info(
                     f"Scroll {i}: Found {new_images_found_this_scroll} new images, {new_posts_found_this_scroll} new posts. "
                     f"Total unique: {len(image_urls)} images, {len(post_urls)} posts."
                 )
                 no_new_items_count = 0
            else:
                 no_new_items_count += 1
                 self.logger.info(
                     f"Scroll {i}: No new items found based on link elements. Total remains: {len(image_urls)} images, {len(post_urls)} posts."
                 )

            # --- Scroll down, wait, check stopping condition (unchanged) ---
            current_position += SCROLL_LENGTH
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            if no_new_items_count >= 3:
                 time.sleep(SCROLL_PAUSE_TIME * 2)
            else:
                 time.sleep(SCROLL_PAUSE_TIME)
            if i >= min_scrolls and no_new_items_count >= 5:
                self.logger.info(
                    f"No new items found in last {no_new_items_count} scrolls after minimum {min_scrolls} scrolls. Stopping."
                )
                break
            # --- ---

        self.logger.info(
            f"Finished collecting. Total unique images found: {len(image_urls)}, Total unique post links found: {len(post_urls)}"
        )
        return list(image_urls), list(post_urls) # Returns the list of full post URLs
    
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

    def save_metadata(self, prompt, total_images, successful_downloads, duration, post_urls): # <-- Add post_urls
        metadata_path = os.path.join(self.session_dir, "metadata.txt")
        # Ensure writing with UTF-8 for prompts and other text
        with open(metadata_path, "w", encoding='utf-8') as f:
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Prompt: {prompt}\n")
            f.write(f"Total images found: {total_images}\n")
            f.write(f"Successfully downloaded: {successful_downloads}\n")
            f.write(f"Total unique post links found: {len(post_urls)}\n") # <-- Add post link count
            f.write(f"Duration: {duration:.2f} seconds\n")
            f.write(f"Post links saved to: post_links.txt\n") # <-- Indicate where links are saved

        # --- Save post links to a separate file ---
        post_links_path = os.path.join(self.session_dir, "post_links.txt")
        with open(post_links_path, "w", encoding='utf-8') as f: # Ensure UTF-8
            if post_urls:
                f.write(f"Post links found for prompt: {prompt}\n")
                f.write("=" * 30 + "\n")
                for link in sorted(post_urls): # Sort for consistency
                    f.write(f"{link}\n")
            else:
                f.write("No post links were found for this prompt.\n")
        self.logger.info(f"Saved {len(post_urls)} post links to {post_links_path}")
        # --- End saving post links ---

    def scrape_images(self, prompt):
        """
        Performs the scraping process for a given search prompt.
        Navigates, searches, scrolls, collects image and post URLs,
        downloads images, and saves metadata.
        """
        # Initialize session_dir attribute early for potential error handling
        self.session_dir = None
        self.start_time = datetime.now() # Start time for duration calculation

        try:
            # Create a timestamped directory for this session's output
            self.create_session_directory() # Sets self.session_dir
            self.logger.info(f"Starting scraping for prompt: {prompt}")
            self.logger.info(f"Output will be saved in: {self.session_dir}")

            # 1. Go to Xiaohongshu homepage
            self.logger.info(f"Accessing Xiaohongshu...")
            self.driver.get("https://www.xiaohongshu.com")
            time.sleep(INITIAL_PAGE_LOAD_WAIT) # Allow initial page load

            # 2. Find and interact with the search box
            self.logger.info("Looking for search box...")
            search_box = WebDriverWait(self.driver, SEARCH_BOX_WAIT).until(
                EC.presence_of_element_located(
                    # Assuming placeholder contains '搜索' (Search)
                    (By.CSS_SELECTOR, "input[placeholder*='搜索']")
                )
            )
            self.logger.info("Search box found.")

            # Clear any existing text, type the prompt, and press Enter
            search_box.clear()
            search_box.send_keys(prompt)
            self.logger.info(f"Searching for: {prompt}")
            search_box.send_keys("\ue007")  # Selenium's representation of Enter key
            time.sleep(SEARCH_RESULT_LOAD_WAIT) # Allow search results to load
            self.logger.info("Search submitted. Waiting for results...")

            # 3. Scroll and collect image URLs and post URLs simultaneously
            #    Calls the updated function that parses IDs from hrefs
            image_urls, post_urls = self.scroll_and_collect_items()

            self.logger.info(f"Finished scrolling. Found {len(image_urls)} unique images and {len(post_urls)} unique post links.")

            # 4. Download all collected images
            self.logger.info(f"Starting download of {len(image_urls)} images...")
            successful_downloads = 0
            '''
            if image_urls: # Only attempt download if images were found
                 for index, img_url in enumerate(image_urls):
                    try:
                        if self.download_image(img_url, index):
                            successful_downloads += 1
                            # Optional short pause between downloads
                            time.sleep(IMAGE_DOWNLOAD_WAIT)
                    except Exception as e:
                        # Log error for specific image download but continue
                        self.logger.error(f"Error processing image {index} (URL: {img_url[:60]}...): {e}")
            else:
                 self.logger.info("No images found to download.")
            '''


            # 5. Save metadata (including post URLs)
            duration = (datetime.now() - self.start_time).total_seconds()
            # Ensure save_metadata is called even if downloads fail
            self.logger.info(f"DEBUG (try block): About to save metadata. len(post_urls) = {len(post_urls)}")
            self.save_metadata(prompt, len(image_urls), successful_downloads, duration, post_urls)

            self.logger.info(
                f"Successfully downloaded {successful_downloads} out of {len(image_urls)} images found for prompt: {prompt}"
            )
            self.logger.info(f"Scraping session for prompt '{prompt}' completed in {duration:.2f} seconds.")

        except Exception as e:
            # Log the error that occurred during the main scraping process
            self.logger.error(f"Scraping error encountered for prompt '{prompt}': {e}", exc_info=True) # Log traceback

            # Attempt to save partial metadata even if an error occurred mid-process
            try:
                # If session_dir wasn't created due to early error, try creating it now
                if not self.session_dir:
                     self.create_session_directory()

                # Try saving metadata with whatever was collected (might be zeros/empty lists)
                # Check if variables exist before accessing them
                img_count = len(image_urls) if 'image_urls' in locals() else 0
                post_count = len(post_urls) if 'post_urls' in locals() else 0
                success_count = successful_downloads if 'successful_downloads' in locals() else 0
                posts_list = post_urls if 'post_urls' in locals() else []
                current_duration = (datetime.now() - self.start_time).total_seconds()

                # Add error info to prompt for metadata
                error_prompt = f"{prompt} (encountered error)"
                self.logger.info(f"DEBUG (try block): About to save metadata. len(post_urls) = {len(post_urls)}")
                self.save_metadata(error_prompt, img_count, success_count, current_duration, posts_list)
                self.logger.info("Saved partial metadata after error.")

            except Exception as meta_e:
                 # Log error if saving metadata itself failed
                 self.logger.error(f"Could not save metadata after encountering main error: {meta_e}")
            
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
