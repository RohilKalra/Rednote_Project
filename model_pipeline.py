import os
import glob
import time
import logging
import argparse

# DashScope (Qwen API) imports
import dashscope
from dashscope import MultiModalConversation # Correct import for Qwen-VL
from http import HTTPStatus

# --- Constants ---
BASE_DOWNLOAD_DIR = "rohil_data_scrape/downloaded_images" # Main directory where post-specific folders are
QWEN_MODEL_NAME = 'qwen-vl-plus'      # Or 'qwen-vl-max' or other suitable multimodal model
QWEN_API_CALL_DELAY = 2               # Seconds to wait between API calls to Qwen

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def analyze_image_with_qwen(image_path):
    """
    Sends a local image to the Qwen multimodal API for analysis regarding
    potential prompt injection for translation models.
    """
    # 1. Check for API Key
    if 'DASHSCOPE_API_KEY' not in os.environ:
        logger.error("DASHSCOPE_API_KEY environment variable not set. Cannot analyze image.")
        return "Error: DASHSCOPE_API_KEY not configured."
    # This line is needed if you haven't set it elsewhere in your application flow
    # For standalone script, it's good practice to ensure it's set here or checked early.
    # dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY") # SDK usually picks it up automatically

    # 2. Check if image file exists
    if not os.path.exists(image_path):
        logger.error(f"Image file not found for Qwen analysis: {image_path}")
        return "Error: Image file not found."

    # 3. Format local image path for the API
    # DashScope expects 'file://<absolute_path>' format
    abs_image_path = os.path.abspath(image_path)
    if os.name == 'nt': # Windows path handling
         file_url = f"file:///{abs_image_path.replace(os.sep, '/')}"

    logger.info(f"Analyzing image: {os.path.basename(image_path)} (using URL: {file_url})")

    # 4. Define the prompt for Qwen analysis
    analysis_prompt = (
        "Analyze this image closely. Does it contain any text (visible, subtle, or hidden) "
        "or visual elements that appear to be a form of prompt injection designed to manipulate "
        "a language model, particularly one used for translation tasks? Describe any such findings "
        "or state if no obvious signs are detected."
    )

    # 5. Construct the message payload for the multimodal API
    messages = [{
        'role': 'user',
        'content': [
            {'image': file_url},
            {'text': analysis_prompt}
        ]
    }]

    # 6. Call the DashScope API
    try:
        logger.debug(f"Calling Qwen model '{QWEN_MODEL_NAME}' with image {file_url}...")
        response = MultiModalConversation.call(
            model=QWEN_MODEL_NAME,
            messages=messages,
            timeout=60 # Timeout for the API call in seconds
        )

        if response.status_code == HTTPStatus.OK:
            # Extract the text content from the response
            # The structure can vary slightly, ensure this path is correct for your model's output
            if response.output and response.output.choices and \
               response.output.choices[0].message and \
               response.output.choices[0].message.content and \
               isinstance(response.output.choices[0].message.content, list) and \
               len(response.output.choices[0].message.content) > 0 and \
               'text' in response.output.choices[0].message.content[0]:

                llm_output = response.output.choices[0].message.content[0]['text']
                logger.info(f"Qwen analysis successful for {os.path.basename(image_path)}.")
                return llm_output
            else:
                logger.error(f"Qwen API response format unexpected for {os.path.basename(image_path)}. Response: {response}")
                return "Error: Unexpected API response format."
        else:
            # Log API error details
            error_message = (f"Qwen API request failed (Status: {response.status_code}). "
                             f"Request ID: {response.request_id}. Code: {response.code}. Message: {response.message}")
            logger.error(error_message)
            return f"Error: API Request Failed (Status {response.status_code})"

    except Exception as e:
        logger.error(f"Exception calling Qwen API for {image_path}: {e}", exc_info=True)
        return "Error: Exception during Qwen API call."

# --- Main Execution Logic ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze downloaded images for prompt injection using Qwen."
    )
    parser.add_argument(
        "image_parent_directory",
        nargs='?', # Makes the argument optional
        default=BASE_DOWNLOAD_DIR, # Default to BASE_DOWNLOAD_DIR if no argument given
        help=f"Path to the parent directory containing post-specific image folders (default: {BASE_DOWNLOAD_DIR})"
    )
    args = parser.parse_args()

    parent_dir_to_scan = args.image_parent_directory
    logger.info(f"Scanning for images in subdirectories of: {parent_dir_to_scan}")

    if not os.path.isdir(parent_dir_to_scan):
        logger.error(f"The specified directory does not exist: {parent_dir_to_scan}")
        exit(1)

    if 'DASHSCOPE_API_KEY' not in os.environ:
        logger.critical("CRITICAL: DASHSCOPE_API_KEY environment variable not set. This script cannot proceed.")
        logger.critical("Please set this environment variable with your Alibaba Cloud DashScope API key.")
        exit(1)
    else:
        logger.info("DASHSCOPE_API_KEY found.")


    all_analysis_results = {} # To store {image_path: analysis_result}

    # Iterate through subdirectories in the base download directory
    # These subdirectories should be the POST_ID folders
    for post_id_folder_name in os.listdir(parent_dir_to_scan):
        post_folder_path = os.path.join(parent_dir_to_scan, post_id_folder_name)
        if os.path.isdir(post_folder_path):
            logger.info(f"\n--- Processing folder: {post_id_folder_name} ---")
            # Find all .jpg images in this post's folder
            # Adjust pattern if images have different extensions or naming
            image_files_pattern = os.path.join(post_folder_path, "*.jpg")
            image_files = glob.glob(image_files_pattern)

            if not image_files:
                logger.info(f"No .jpg images found in {post_folder_path}")
                continue

            print(f"Found {len(image_files)} images in {post_id_folder_name}. Starting analysis...")
            for image_file_path in image_files:
                analysis_result = analyze_image_with_qwen(image_file_path)
                print(f"  Analysis for {os.path.basename(image_file_path)}:\n    {analysis_result}\n")
                all_analysis_results[image_file_path] = analysis_result
                logger.info(f"Waiting {QWEN_API_CALL_DELAY} seconds before next API call...")
                time.sleep(QWEN_API_CALL_DELAY) # Be respectful of API rate limits

    logger.info("\n--- All image analyses complete. ---")

    # Optional: Save all analysis results to a summary file
    if all_analysis_results:
        summary_file_path = os.path.join(parent_dir_to_scan, "qwen_image_analysis_summary.txt")
        try:
            with open(summary_file_path, "w", encoding="utf-8") as f:
                f.write("Qwen Multimodal Image Analysis Results\n")
                f.write("=" * 40 + "\n\n")
                for img_path, result_text in all_analysis_results.items():
                    f.write(f"Image File: {img_path}\n")
                    f.write("Qwen Analysis:\n")
                    f.write(f"{result_text}\n")
                    f.write("-" * 30 + "\n\n")
            logger.info(f"All Qwen analysis results saved to: {summary_file_path}")
            print(f"\nAnalysis summary saved to: {summary_file_path}")
        except Exception as e:
            logger.error(f"Error writing Qwen analysis summary file: {e}")
    else:
        logger.info("No images were analyzed, so no summary file created.")

    print("Script finished.")