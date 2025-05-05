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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

# --- Constants ---

# File and Directory Settings
BASE_SAVE_DIR = "downloaded_images"  # Base folder to save post-specific subfolders
DOWNLOAD_CHUNK_SIZE = 1024  # Chunk size for downloading images (increased slightly)

# Chrome Profile Settings (Ensure these are correct for your system)
CHROME_PROFILE_DIR = (r"C:\Users\shiyi\AppData\Local\Google\Chrome\User Data\Default")# Path to User Data folder
CHROME_PROFILE = "Default" # Profile folder name (e.g., "Default", "Profile 1")

# WebDriver Wait Times and Interaction Settings
PAGE_LOAD_TIMEOUT = 20      # Max time to wait for a post page to load key elements
ELEMENT_WAIT = 10           # General wait time for elements
POST_PROCESS_WAIT = 4       # Time to wait between processing different posts (seconds)
IMAGE_DOWNLOAD_WAIT = 0.1   # Time to wait between downloading images for the SAME post (seconds)
CAROUSEL_CLICK_PAUSE = 1.5  # Time to wait after clicking carousel next button (seconds)
CAROUSEL_CHECK_PAUSE = 0.7  # Short pause before checking images/button state in carousel loop
MAX_SLIDER_CLICKS = 15      # Safety limit for carousel next button clicks

# --- CSS Selectors (Based on provided HTML - MAY NEED UPDATING) ---
# Selector for the "next" arrow button in the image carousel
NEXT_BUTTON_SELECTOR = "div.arrow-controller.right"
# Class indicating the next button is disabled (end of carousel)
DISABLED_BUTTON_CLASS = "forbidden"
# Selector for images within the carousel slides
IMAGE_SELECTOR = "div.swiper-slide img.note-slider-img"
# Fallback image selector if carousel structure isn't found (for single images)
FALLBACK_IMAGE_SELECTOR = "div.media-container img"
# Selector for a key element indicating post page has loaded
POST_PAGE_LOAD_INDICATOR = "div.slider-container, div.media-container img" # Slider or single image

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

class XiaohongshuScraper:
    def __init__(self):
        self.save_dir = BASE_SAVE_DIR # Base save directory
        os.makedirs(self.save_dir, exist_ok=True) # Ensure base directory exists
        self.setup_logging()
        self.driver = None # Initialize driver as None
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
            # Use specified Chrome profile (important for login state)
            chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
            chrome_options.add_argument(f"--profile-directory={CHROME_PROFILE}")

            # Common options for stability
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu") # Often helps stability
            chrome_options.add_argument("--log-level=3") # Suppress console logs from Chrome/Driver
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--ignore-certificate-errors")
            chrome_options.add_argument('--disable-blink-features=AutomationControlled') # Try to appear less like a bot
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Prevent detection - setting user agent (optional, might use profile's default)
            # chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

            # Note: Using remote-debugging-port might conflict if Chrome is already running with it. Remove if causing issues.
            # chrome_options.add_argument("--remote-debugging-port=9222")

            self.driver = webdriver.Chrome(options=chrome_options)
            # Mitigate Selenium detection
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            self.logger.info("WebDriver setup complete.")
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}", exc_info=True)
            raise # Reraise exception to stop script if driver fails

    def download_image(self, img_url, index, save_directory, base_filename="image"):
        """Downloads a single image to a specified directory with a base filename."""
        try:
            # Get cookies from the current browser session
            try:
                 cookies = {cookie["name"]: cookie["value"] for cookie in self.driver.get_cookies()}
            except Exception as cookie_e:
                 self.logger.warning(f"Could not get cookies: {cookie_e}. Proceeding without.")
                 cookies = {}

            headers = {
                # Use browser's user agent
                "User-Agent": self.driver.execute_script("return navigator.userAgent"),
                # Set Referer to the post page URL
                "Referer": self.driver.current_url,
            }

            self.logger.debug(f"Attempting download: {img_url[:80]}...")
            response = requests.get(
                img_url, headers=headers, cookies=cookies, stream=True, timeout=30 # Increased timeout
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Create filename and full path
            img_filename = f"{base_filename}_{index}.jpg"
            img_path = os.path.join(save_directory, img_filename)

            # Write image content to file
            with open(img_path, "wb") as f:
                for chunk in response.iter_content(DOWNLOAD_CHUNK_SIZE):
                    f.write(chunk)

            self.logger.info(f"Successfully downloaded image {index} to {img_path}")
            return True

        except requests.exceptions.RequestException as e:
             self.logger.error(f"Network/Request error downloading image {index} from {img_url[:80]}...: {e}")
             return False
        except IOError as e:
            self.logger.error(f"File system error saving image {index} to {img_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Generic error downloading image {index} from {img_url[:80]}...: {e}")
            return False

    def scrape_images_from_post(self, post_url):
        """Navigates to a post URL, extracts all images (handles carousel), and downloads them."""
        start_time = datetime.now()
        post_id = None
        post_save_dir = None

        try:
            # 1. Extract Post ID for folder naming
            try:
                # Extract ID like '678d4d360000000019015ca8' from '/explore/ID?params'
                match = re.search(r'/explore/([a-f0-9]{24})', post_url) # Assuming 24 hex chars ID
                if match:
                    post_id = match.group(1)
            except Exception as id_e:
                self.logger.warning(f"Regex error extracting Post ID from URL {post_url}: {id_e}")

            if not post_id:
                # Fallback naming if ID extraction fails
                ts = datetime.now().strftime('%H%M%S_%f')
                try:
                    url_path_part = post_url.split('/')[-1].split('?')[0][:10]
                except IndexError:
                    url_path_part = "parse_error"
                post_id = f"unknown_{url_path_part}_{ts}"
                self.logger.warning(f"Could not extract valid Post ID. Using fallback folder name: {post_id}")

            # Create post-specific save directory: BASE_SAVE_DIR / Post_ID
            post_save_dir = os.path.join(self.save_dir, post_id)
            os.makedirs(post_save_dir, exist_ok=True)
            self.logger.info(f"Saving images for post {post_id} to: {post_save_dir}")

            # 2. Navigate to the post URL
            self.logger.info(f"Navigating to post: {post_url}")
            self.driver.get(post_url)

            # Wait for a key element of the post page to load
            try:
                WebDriverWait(self.driver, PAGE_LOAD_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, POST_PAGE_LOAD_INDICATOR))
                )
                self.logger.info("Post page initial content loaded.")
                # Additional pause allows dynamic elements (like carousel JS) to potentially finish initializing
                time.sleep(3)
            except TimeoutException:
                 self.logger.error(f"Timeout waiting for post page content indicator '{POST_PAGE_LOAD_INDICATOR}' at {post_url}. Skipping post.")
                 return # Skip this post if page doesn't load essential content

            # 3. Extract Image URLs (handling carousel)
            post_image_urls = set()

            self.logger.info("Attempting to extract images from carousel/post...")
            for click_count in range(MAX_SLIDER_CLICKS + 1): # +1 to check initial state
                if click_count > 0:
                    self.logger.debug(f"Carousel loop iteration {click_count}")

                current_images_found = 0
                try:
                    # Give potential slide transitions or image loading a moment
                    time.sleep(CAROUSEL_CHECK_PAUSE)

                    # Find potentially visible image elements in the slider/container
                    current_page_elements = self.driver.find_elements(By.CSS_SELECTOR, IMAGE_SELECTOR)
                    if not current_page_elements:
                         # Fallback check if main selector yields nothing
                         current_page_elements = self.driver.find_elements(By.CSS_SELECTOR, FALLBACK_IMAGE_SELECTOR)
                         if current_page_elements:
                              self.logger.info("Using fallback image selector.")
                         else:
                              # If still no images, maybe it's a video post or failed load
                              if click_count == 0: # Only log this once
                                   self.logger.warning("No image elements found using primary or fallback selectors.")
                              # Assume end if no images found after first check
                              if click_count > 0: break


                    for img_element in current_page_elements:
                        try:
                            img_url = img_element.get_attribute("src")
                            # Validate URL, check for placeholder/tiny images if necessary
                            if img_url and img_url.startswith('http') and img_url not in post_image_urls:
                                # Add refinement here? Check img dimensions? For now, accept all http srcs.
                                post_image_urls.add(img_url)
                                current_images_found += 1
                                self.logger.debug(f"Found image URL: {img_url[:70]}...")
                        except Exception as inner_e:
                             self.logger.warning(f"Error getting src from one image element: {inner_e}")

                    self.logger.debug(f"Found {current_images_found} new image URLs in this view.")

                    # --- Carousel Navigation ---
                    # Check for the 'next' button *after* processing current view
                    next_button = None
                    try:
                        # Check if the next button exists
                        wait = WebDriverWait(self.driver, 1) # Short wait
                        next_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, NEXT_BUTTON_SELECTOR)))

                        # Check if the button is disabled using its class attribute
                        button_classes = next_button.get_attribute("class") or ""
                        if DISABLED_BUTTON_CLASS in button_classes:
                            self.logger.info("Next button is disabled/forbidden. End of carousel.")
                            break # Exit loop - reached the end

                        # If button exists and isn't disabled, click it (only if not the last iteration)
                        if click_count < MAX_SLIDER_CLICKS:
                            self.logger.info(f"Clicking next image button (Attempt {click_count + 1})...")
                            try:
                                # Try JS click first as it's often more robust against overlays
                                self.driver.execute_script("arguments[0].click();", next_button)
                            except Exception as click_e1:
                                self.logger.warning(f"JS click failed ({click_e1}), trying direct click...")
                                try:
                                    # Ensure clickable before direct click attempt
                                     WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, NEXT_BUTTON_SELECTOR))).click()
                                except Exception as click_e2:
                                     self.logger.error(f"Both JS and direct click failed for next button: {click_e2}")
                                     break # Stop if we can't click next

                            time.sleep(CAROUSEL_CLICK_PAUSE) # Wait for slide transition

                    except (TimeoutException, NoSuchElementException):
                        # If button isn't found, assume single image or end of carousel after checking first view
                        self.logger.info("Next button not found. Assuming single image post or end of carousel.")
                        break # Exit loop

                except Exception as outer_e:
                    self.logger.error(f"Error during carousel loop for post {post_id}: {outer_e}", exc_info=True)
                    break # Exit loop on major error

            self.logger.info(f"Finished image collection for post {post_id}. Found {len(post_image_urls)} unique image URLs.")

            # 4. Download the collected images for this post
            successful_downloads = 0
            if post_image_urls:
                 self.logger.info(f"Starting download for {len(post_image_urls)} images for post {post_id}...")
                 # Sort URLs for consistent download order (optional)
                 sorted_urls = sorted(list(post_image_urls))
                 for index, img_url in enumerate(sorted_urls):
                     # Pass the specific directory and use post_id in filename
                     if self.download_image(img_url, index, post_save_dir, base_filename=post_id):
                         successful_downloads += 1
                         # Short pause between downloads
                         time.sleep(IMAGE_DOWNLOAD_WAIT)
                 self.logger.info(f"Successfully downloaded {successful_downloads} / {len(post_image_urls)} images for post {post_id}.")
            else:
                 self.logger.info(f"No image URLs were collected for post {post_id}.")

        except Exception as e:
            self.logger.error(f"Failed to process post URL {post_url}: {e}", exc_info=True)

        finally:
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Post processing finished for {post_url} ({post_id}). Duration: {duration:.2f} seconds.")


    def close_browser(self):
        """Closes the Selenium WebDriver session."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed successfully.")
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
        self.driver = None

# --- Main Execution ---

if __name__ == "__main__":
    # Setup command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Scrape all images from Xiaohongshu posts listed in a file."
    )
    parser.add_argument("post_links_file", help="Path to the file containing post URLs (one per line)")
    args = parser.parse_args()

    # Read the list of post URLs from the specified file
    post_urls_to_scrape = read_post_urls(args.post_links_file)

    if not post_urls_to_scrape:
        print("No valid post URLs found in the file. Exiting.")
        exit(1)

    scraper = None # Initialize scraper variable
    try:
        # Initialize the scraper instance
        scraper = XiaohongshuScraper()

        total_posts = len(post_urls_to_scrape)
        print(f"\nStarting processing for {total_posts} posts...")

        # Loop through each post URL and scrape images
        for i, post_url in enumerate(post_urls_to_scrape):
            print("-" * 60)
            print(f"Processing post {i+1}/{total_posts}: {post_url}")
            scraper.scrape_images_from_post(post_url) # Call the scraping method
            # Wait between processing posts to avoid rate limiting
            if i < total_posts - 1: # Don't wait after the last post
                 print(f"Waiting {POST_PROCESS_WAIT} seconds before next post...")
                 time.sleep(POST_PROCESS_WAIT)

        print("-" * 60)
        print("\nAll post URLs processed.")

    except KeyboardInterrupt:
        # Handle Ctrl+C interruption gracefully
        print("\nCtrl+C detected. Shutting down...")
    except Exception as e:
        # Log any critical errors during the main loop
        print(f"\nAn critical error occurred during execution: {e}")
        logging.error("Critical error during script execution.", exc_info=True)
    finally:
        # Ensure the browser is closed even if errors occur
        if scraper:
            print("Closing browser...")
            scraper.close_browser()
        print("Script finished.")