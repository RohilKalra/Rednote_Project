# Xiaohongshu Image Scraper

A Python-based web scraper for downloading images from Xiaohongshu (小红书). The scraper creates timestamped folders for each scraping session and includes logging functionality.

## Features

- Downloads images from Xiaohongshu search results
- Organizes downloads in timestamped folders
- Includes logging with both file and console output
- Uses Chrome profile for authentication
- Handles scrolling and dynamic content loading
- Includes error handling and retry mechanisms

## Prerequisites

- Python 3.7 or higher
- Google Chrome browser
- Make (optional, but recommended)

## Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd xiaohongshu-scraper
```

2. Install dependencies using Make:
```bash
make setup
```

Or manually create a virtual environment and install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
pip install selenium requests
```

3. Update the Chrome profile path in `scraper.py` to match your system:
```python
chrome_options.add_argument("--user-data-dir=/path/to/your/chrome/profile")
chrome_options.add_argument("--profile-directory=Profile 14")
```

## Usage

### Using Make

Run the scraper with a specific URL:
```bash
make run URL="https://www.xiaohongshu.com/search_result?keyword=your_search_term"
```

Clean up downloaded images and virtual environment:
```bash
make clean
```

### Manual Usage

1. Activate the virtual environment:
```bash
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Run the scraper:
```bash
python scraper.py "https://www.xiaohongshu.com/search_result?keyword=your_search_term"
```

## Directory Structure

```
xiaohongshu-scraper/
├── scraper.py
├── Makefile
├── README.md
├── logs/
│   └── scraper_YYYYMMDD_HHMMSS.log
└── downloaded_images/
    └── YYYYMMDD_HHMMSS/
        ├── image_0.jpg
        ├── image_1.jpg
        └── ...
```

## Logging

- Logs are stored in the `logs` directory with timestamps
- Each scraping session creates a new log file
- Both console and file logging are enabled

## Notes

- The scraper uses your existing Chrome profile for authentication
- Press Ctrl+C twice to exit the script
- Images are saved in timestamped folders under `downloaded_images`
- Each scraping session creates a new folder

## Troubleshooting

1. If you encounter Chrome driver issues:
   - Make sure you have the latest version of Chrome installed
   - Update the Chrome profile path in the script

2. If images aren't downloading:
   - Check your internet connection
   - Verify that you're logged into Xiaohongshu in Chrome
   - Check the logs for specific error messages

## License

This project is licensed under the MIT License - see the LICENSE file for details.