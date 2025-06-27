import time
import os
import requests
import logging
import re
import argparse
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException

# --- Constants ---

# File and Directory Settings
COMMENTS_SAVE_FILE = "all_xiaohongshu_comments.txt" # Single file to save all comments

# Chrome Profile Settings (Ensure these are correct for your system)
CHROME_PROFILE_DIR = (r"C:\Users\shiyi\AppData\Local\Google\Chrome\User Data\Default") # Path to User Data folder
CHROME_PROFILE = "Default" # Profile folder name (e.g., "Default", "Profile 1")

# WebDriver Wait Times and Interaction Settings
PAGE_LOAD_TIMEOUT = 20      # Max time to wait for a post page to load key elements
ELEMENT_WAIT = 15           # General wait time for elements
POST_PROCESS_WAIT = 15      # Time to wait between processing different posts (seconds)
SCROLL_PAUSE_TIME = 4       # Time to wait after each scroll to load more comments (can be adjusted)
MAX_SCROLLS = 40            # Max number of times to scroll down to load more comments (increased for deeper comments)
SCROLL_INCREMENT_PIXELS = 1000 # How many pixels to scroll down each time when scrolling the whole window

# --- CSS Selectors (Based on provided HTML - MAY NEED UPDATING) ---
# Selector for a key element indicating post page has loaded
POST_PAGE_LOAD_INDICATOR = "div.slider-container, div.media-container img" # Slider or single image (still needed for page load check)

# New CSS Selectors for Comments
COMMENTS_SECTION_SELECTOR = "div.comments-el" # The main container for comments
# Selector for the specific container that holds and scrolls the comments list
COMMENTS_LIST_CONTAINER_SELECTOR = "div.comments-el div.list-container" # Using the provided HTML structure
COMMENT_ITEM_SELECTOR = "div.parent-comment div.comment-item" # Individual comment container
COMMENT_CONTENT_SELECTOR = "span.note-text" # The actual text of the comment

# --- Helper Function ---

def read_post_urls(file_path):
    """Reads post URLs from a file, skipping headers/empty lines."""
    urls = []
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Basic check: must be a URL containing '/explore/'
                if line and line.startswith('http') and '/explore/' in line:
                    urls.append(line)
        print(f"Read {len(urls)} post URLs from {file_path}")
    except FileNotFoundError:
        print(f"Error: Post links file not found at {file_path}")
        return [] # Return empty list if file doesn't exist
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return []
    return urls

# --- Scraper Class ---

class XiaohongshuCommentScraper:
    def __init__(self):
        self.output_file = COMMENTS_SAVE_FILE
        self.setup_logging()
        self.driver = None
        self.setup_driver()

    def setup_logging(self):
        """Configures basic logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logging configured.")

    def setup_driver(self):
        """Configures and initializes the Selenium WebDriver."""
        try:
            chrome_options = Options()
            chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
            chrome_options.add_argument(f"--profile-directory={CHROME_PROFILE}")
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.logger.info("WebDriver setup complete.")
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}", exc_info=True)
            raise

    def scroll_specific_element_to_load_content(self, element_selector, max_scrolls=MAX_SCROLLS):
        """
        Attempts to scroll a specific element to load content within it.
        If element not found or not scrollable, falls back to main window scroll.
        """
        self.logger.info(f"Attempting to scroll specific element '{element_selector}' (max {max_scrolls} scrolls)...")
        scrollable_element = None
        try:
            scrollable_element = WebDriverWait(self.driver, ELEMENT_WAIT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, element_selector))
            )
            self.logger.info(f"Found scrollable element: '{element_selector}'.")
        except TimeoutException:
            self.logger.warning(f"Scrollable element '{element_selector}' not found. Falling back to general window scroll.")
            self._general_window_scroll(max_scrolls) # Fallback to general window scroll
            return

        last_scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", scrollable_element)
        scroll_attempts = 0

        while scroll_attempts < max_scrolls:
            try:
                # Scroll the specific element by its own scrollHeight
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
                self.logger.debug(f"Scroll attempt {scroll_attempts + 1}: scrolled element '{element_selector}' to its scrollHeight.")
                time.sleep(SCROLL_PAUSE_TIME)

                new_scroll_height = self.driver.execute_script("return arguments[0].scrollHeight;", scrollable_element)

                if new_scroll_height == last_scroll_height:
                    self.logger.info(f"Element '{element_selector}' scroll height no longer changing after {scroll_attempts + 1} scrolls. Likely reached end of content.")
                    break

                last_scroll_height = new_scroll_height
                scroll_attempts += 1

            except StaleElementReferenceException:
                self.logger.warning(f"StaleElementReferenceException on scrollable element. Re-finding element for scrolling.")
                try:
                    scrollable_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, element_selector))
                    )
                except TimeoutException:
                    self.logger.error(f"Could not re-find scrollable element '{element_selector}' after stale exception. Stopping element-specific scrolling.")
                    break
                except Exception as e:
                    self.logger.error(f"Error re-finding scrollable element: {e}. Stopping element-specific scrolling.")
                    break
            except Exception as e:
                self.logger.error(f"Error scrolling specific element '{element_selector}': {e}", exc_info=True)
                # If specific element scrolling fails, fall back to general window scroll for remaining attempts
                self.logger.warning("Element-specific scrolling failed. Falling back to general window scroll.")
                self._general_window_scroll(max_scrolls - scroll_attempts)
                break

        self.logger.info("Finished element-specific scrolling attempts.")

    def _general_window_scroll(self, remaining_scrolls, scroll_increment=SCROLL_INCREMENT_PIXELS):
        """Helper for general window scrolling if element-specific fails."""
        self.logger.info(f"Initiating general window scroll (max {remaining_scrolls} scrolls)...")
        current_scroll_y = self.driver.execute_script("return window.pageYOffset;")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0

        while scroll_attempts < remaining_scrolls:
            try:
                self.driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                self.logger.debug(f"General scroll attempt {scroll_attempts + 1}: scrolled by {scroll_increment} pixels.")
                time.sleep(SCROLL_PAUSE_TIME)

                new_height = self.driver.execute_script("return document.body.scrollHeight")
                new_scroll_y = self.driver.execute_script("return window.pageYOffset;")

                if new_height == last_height and new_scroll_y == current_scroll_y:
                    self.logger.info(f"General window scroll height and position no longer changing after {scroll_attempts + 1} scrolls. Likely reached end.")
                    break

                last_height = new_height
                current_scroll_y = new_scroll_y
                scroll_attempts += 1
            except Exception as e:
                self.logger.warning(f"Error during general window JS scroll attempt {scroll_attempts + 1}: {e}")
                # Fallback to PAGE_DOWN key for window scroll
                try:
                    self.logger.debug(f"Attempting PAGE_DOWN as fallback for general window scroll attempt {scroll_attempts + 1}.")
                    ActionChains(self.driver).send_keys(Keys.PAGE_DOWN).perform()
                    time.sleep(SCROLL_PAUSE_TIME)

                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    new_scroll_y = self.driver.execute_script("return window.pageYOffset;")

                    if new_height == last_height and new_scroll_y == current_scroll_y:
                         self.logger.info(f"General window scroll height and position no longer changing after {scroll_attempts + 1} PAGE_DOWN scrolls.")
                         break
                    last_height = new_height
                    current_scroll_y = new_scroll_y
                    scroll_attempts += 1
                except Exception as key_e:
                    self.logger.error(f"Failed to send PAGE_DOWN key for general window scroll: {key_e}. Giving up on scrolling.")
                    break
        self.logger.info("Finished general window scrolling attempts.")

    def scrape_comments_from_post(self, post_url):
        """Navigates to a post URL, extracts all comments, and returns them."""
        start_time = datetime.now()
        post_id = None
        scraped_comments = []

        try:
            # 1. Extract Post ID (for logging/identification purposes)
            try:
                match = re.search(r'/explore/([a-f0-9]{24})', post_url)
                if match:
                    post_id = match.group(1)
            except Exception as id_e:
                self.logger.warning(f"Regex error extracting Post ID from URL {post_url}: {id_e}")

            if not post_id:
                ts = datetime.now().strftime('%H%M%S_%f')
                try:
                    url_path_part = post_url.split('/')[-1].split('?')[0][:10]
                except IndexError:
                    url_path_part = "parse_error"
                post_id = f"unknown_{url_path_part}_{ts}"
                self.logger.warning(f"Could not extract valid Post ID. Using fallback for logging: {post_id}")

            self.logger.info(f"Processing post: {post_url} (ID: {post_id})")

            # 2. Navigate to the post URL
            self.driver.get(post_url)

            # Wait for a key element of the post page to load
            try:
                WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, POST_PAGE_LOAD_INDICATOR))
                )
                self.logger.info("Post page initial content loaded.")
                time.sleep(3) # Give more time for dynamic content, like comments, to start loading
            except TimeoutException:
                self.logger.error(f"Timeout waiting for post page content indicator '{POST_PAGE_LOAD_INDICATOR}' at {post_url}. Skipping post.")
                return [] # Skip this post if page doesn't load essential content

            # 3. First, try to scroll the comments section into view, as this might activate its loading
            try:
                comments_section_el = WebDriverWait(self.driver, ELEMENT_WAIT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, COMMENTS_SECTION_SELECTOR))
                )
                self.logger.info("Comments section found. Scrolling it into view...")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comments_section_el)
                time.sleep(SCROLL_PAUSE_TIME)
            except TimeoutException:
                self.logger.warning(f"Comments section '{COMMENTS_SECTION_SELECTOR}' not found initially. Will try general page scroll.")
            except Exception as e:
                self.logger.error(f"Error scrolling comments section into view: {e}", exc_info=True)

            # 4. Perform continuous scrolling, prioritizing the specific comments list container
            self.scroll_specific_element_to_load_content(COMMENTS_LIST_CONTAINER_SELECTOR)

            # 5. Extract Comments after all scrolling attempts
            self.logger.info(f"Attempting to extract comments for post {post_id} after scrolling...")
            try:
                # Wait for at least one comment item to be visible, ensuring comments are likely loaded
                WebDriverWait(self.driver, ELEMENT_WAIT).until(
                    EC.visibility_of_all_elements_located((By.CSS_SELECTOR, COMMENT_ITEM_SELECTOR))
                )
                comment_elements = self.driver.find_elements(By.CSS_SELECTOR, COMMENT_ITEM_SELECTOR)
                self.logger.info(f"Found {len(comment_elements)} potential comment elements.")

                if comment_elements:
                    for i, comment_el in enumerate(comment_elements):
                        try:
                            # Use JavaScript to get innerText from the actual content span within the comment item
                            comment_text = self.driver.execute_script(
                                "var el = arguments[0].querySelector(arguments[1]); if (el) return el.innerText; else return null;",
                                comment_el, COMMENT_CONTENT_SELECTOR
                            )
                            if comment_text:
                                scraped_comments.append(comment_text.strip())
                                self.logger.debug(f"Found comment {i+1}: {comment_text.strip()[:50]}...")
                        except StaleElementReferenceException:
                            self.logger.warning(f"StaleElementReferenceException for comment element {i}. Skipping this comment.")
                            continue
                        except Exception as ce:
                            self.logger.warning(f"Error extracting comment text from element {i}: {ce}")
                            continue

                    self.logger.info(f"Collected {len(scraped_comments)} comments for post {post_id}.")
                else:
                    self.logger.info("No comment items found after loading comments section and scrolling.")

            except TimeoutException:
                self.logger.warning(f"Timeout waiting for comment items after scrolling. No comments extracted for this post.")
            except Exception as comment_scrape_e:
                self.logger.error(f"Error during final comment extraction for post {post_id}: {comment_scrape_e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Failed to process post URL {post_url}: {e}", exc_info=True)

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Post processing finished for {post_url} (ID: {post_id}). Duration: {duration:.2f} seconds.")
            return scraped_comments


    def close_browser(self):
        """Closes the Selenium WebDriver session."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
        self.driver = None

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape comments from Xiaohongshu posts listed in a file."
    )
    parser.add_argument("post_links_file", help="Path to the file containing post URLs (one per line)")
    args = parser.parse_args()

    post_urls_to_scrape = read_post_urls(args.post_links_file)

    if not post_urls_to_scrape:
        print("No valid post URLs found in the file. Exiting.")
        exit(1)

    scraper = None
    all_scraped_comments = []

    try:
        scraper = XiaohongshuCommentScraper()
        total_posts = len(post_urls_to_scrape)
        print(f"\nStarting processing for {total_posts} posts...")

        for i, post_url in enumerate(post_urls_to_scrape):
            print("-" * 60)
            print(f"Processing post {i+1}/{total_posts}: {post_url}")
            comments_for_this_post = scraper.scrape_comments_from_post(post_url)
            all_scraped_comments.extend(comments_for_this_post)

            if i < total_posts - 1:
                print(f"Waiting {POST_PROCESS_WAIT} seconds before next post...")
                time.sleep(POST_PROCESS_WAIT)

        print("-" * 60)
        print("\nAll post URLs processed.")

        if all_scraped_comments:
            try:
                with open(COMMENTS_SAVE_FILE, "w", encoding="utf-8") as f:
                    for comment in all_scraped_comments:
                        f.write(comment + "\n")
                print(f"Successfully saved all {len(all_scraped_comments)} comments to {COMMENTS_SAVE_FILE}")
            except IOError as e:
                print(f"Error writing comments to file {COMMENTS_SAVE_FILE}: {e}")
        else:
            print("No comments were collected from any posts.")

    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down...")
    except Exception as e:
        print(f"\nAn critical error occurred during execution: {e}")
        logging.error("Critical error during script execution.", exc_info=True)
    finally:
        if scraper:
            print("Closing browser...")
            scraper.close_browser()
        print("Script finished.")