import time
import schedule # A library for scheduling tasks: pip install schedule
import requests
import json
import base64
import random
import os
import re # For slug generation
import pickle # For saving/loading the state (last processed index)
from dotenv import load_dotenv
from datetime import datetime, timedelta
from itertools import cycle # For cycling through writers
import logging
from logging.handlers import RotatingFileHandler

# --- Setup Logging ---
LOG_FILE = "auto_publisher.log" # Will be created in the same directory as the script
logger = logging.getLogger("AutoPublisherLogger")
logger.setLevel(logging.INFO)
# Create a rotating file handler: 5 MB per file, keep 5 backup files
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load environment variables from .env file
load_dotenv()

# --- Configuration from Environment Variables ---
WORDPRESS_URL = os.environ.get("WORDPRESS_URL")
NUM_WRITERS_STR = os.environ.get("NUM_WRITERS")
FRED_API_KEY = os.environ.get("FRED_API_KEY") # Loaded for underlying modules if needed

TICKERS_ENV_VAR = os.environ.get("TICKERS_LIST", "AAPL,GOOGL") # Default if not set
TICKERS_TO_PROCESS = [ticker.strip() for ticker in TICKERS_ENV_VAR.split(',')]

MIN_INTERVAL_MINUTES_STR = os.environ.get("MIN_INTERVAL_MINUTES", "02")
MAX_INTERVAL_MINUTES_STR = os.environ.get("MAX_INTERVAL_MINUTES", "05")

WP_CATEGORY_STOCKFORECAST_ID_STR = os.environ.get("WP_CATEGORY_STOCKFORECAST_ID")

STATE_FILE = "auto_publisher_state.pkl" # File to store the last processed ticker index

# --- Validate essential configurations ---
if not WORDPRESS_URL:
    print(f"[{datetime.now()}] Error: WORDPRESS_URL not found in environment variables. Please set it in your .env file.")
    exit(1)
WORDPRESS_URL = WORDPRESS_URL.rstrip('/')

try:
    NUM_WRITERS = int(NUM_WRITERS_STR) if NUM_WRITERS_STR else 0
except ValueError:
    print(f"[{datetime.now()}] Error: NUM_WRITERS ('{NUM_WRITERS_STR}') is not a valid number. Please check your .env file.")
    exit(1)

try:
    MIN_INTERVAL_MINUTES = int(MIN_INTERVAL_MINUTES_STR)
    MAX_INTERVAL_MINUTES = int(MAX_INTERVAL_MINUTES_STR)
    if MIN_INTERVAL_MINUTES >= MAX_INTERVAL_MINUTES:
        print(f"[{datetime.now()}] Error: MIN_INTERVAL_MINUTES ({MIN_INTERVAL_MINUTES}) must be less than MAX_INTERVAL_MINUTES ({MAX_INTERVAL_MINUTES}).")
        exit(1)
except ValueError:
    print(f"[{datetime.now()}] Error: MIN_INTERVAL_MINUTES ('{MIN_INTERVAL_MINUTES_STR}') or MAX_INTERVAL_MINUTES ('{MAX_INTERVAL_MINUTES_STR}') is not a valid number.")
    MIN_INTERVAL_MINUTES = 75
    MAX_INTERVAL_MINUTES = 100
    print(f"[{datetime.now()}] Defaulting to posting interval: {MIN_INTERVAL_MINUTES}-{MAX_INTERVAL_MINUTES} minutes.")

WP_CATEGORY_STOCKFORECAST_ID = None
if WP_CATEGORY_STOCKFORECAST_ID_STR:
    try:
        WP_CATEGORY_STOCKFORECAST_ID = int(WP_CATEGORY_STOCKFORECAST_ID_STR)
    except ValueError:
        print(f"[{datetime.now()}] Warning: WP_CATEGORY_STOCKFORECAST_ID ('{WP_CATEGORY_STOCKFORECAST_ID_STR}') is not a valid number. Category 'Stock Forecast' will not be set.")
else:
    print(f"[{datetime.now()}] Warning: WP_CATEGORY_STOCKFORECAST_ID not set in .env file. Category 'Stock Forecast' will not be set.")

WRITERS = []
if NUM_WRITERS > 0:
    for i in range(1, NUM_WRITERS + 1):
        username = os.environ.get(f'WRITER_{i}_USERNAME')
        app_password_env = os.environ.get(f'WRITER_{i}_APP_PASSWORD')
        wp_user_id_str = os.environ.get(f'WRITER_{i}_WP_USER_ID')

        if username and app_password_env and wp_user_id_str:
            try:
                wp_user_id = int(wp_user_id_str)
                app_password_cleaned = app_password_env.replace('\u00a0', '').replace(' ', '')
                WRITERS.append({"username": username, "app_password": app_password_cleaned, "wp_user_id": wp_user_id})
            except ValueError:
                print(f"[{datetime.now()}] Warning: Invalid WP_USER_ID for writer {i}: '{wp_user_id_str}'. Must be a number. This writer will be skipped.")
        else:
            print(f"[{datetime.now()}] Warning: Missing one or more environment variables for writer {i} (USERNAME, APP_PASSWORD, or WP_USER_ID). This writer will be skipped.")
else:
    print(f"[{datetime.now()}] Warning: NUM_WRITERS is not set or is 0. No writers will be configured.")

if not WRITERS:
    print(f"[{datetime.now()}] Error: No valid writers configured. Please check your .env file or environment variables.")
    exit(1)
if not TICKERS_TO_PROCESS:
    print(f"[{datetime.now()}] Error: No tickers configured in TICKERS_LIST or the default. Please check your .env file.")
    exit(1)

APP_ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

try:
    from pipeline import run_wp_pipeline
except ImportError:
    print(f"[{datetime.now()}] Error: Could not import run_wp_pipeline from pipeline.py. Ensure it's in the same directory or Python path.")
    exit(1)

# --- Headline Templates (Keeping your preferred ones) ---
HEADLINE_TEMPLATES = [
    "{ticker} Stock Price Forecast & Expert Insights for {year_range}",
    "{ticker} Stock Prediction, and Price Target ({year_range}) - What Experts Say", # Your existing title
    "{ticker} Future Stock Price & Technical Outlook {year_range}",
    "{ticker} Stock Forecast {year_range}: Expert Analysis and Predictions", # Your existing title
    "{ticker} Stock Price Targets and Technical Analysis for {year_range}",
    "Analyst View on {ticker}: Key Predictions and Price Forecast {year_range}",
    "The Future of {ticker} Stock Price Predictions and Analysis for {year_range}", # Your existing title
    "Expert Take: {ticker} Stock Forecast, Analysis, and Predictions {year_range}",
    "Is {ticker} a Buy? {year_range} Stock Analysis and Price Forecast",
    "{ticker} {year_range} Forecast: Technical Analysis & Price Predictions"
]

# --- State Management for Ticker Index ---
def load_last_processed_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'rb') as f:
                state = pickle.load(f)
                return state.get('last_ticker_original_index', -1)
        except Exception as e:
            print(f"[{datetime.now()}] Warning: Could not load state from '{STATE_FILE}': {e}")
    return -1

def save_last_processed_state(original_index):
    try:
        with open(STATE_FILE, 'wb') as f:
            pickle.dump({'last_ticker_original_index': original_index}, f)
    except Exception as e:
        print(f"[{datetime.now()}] Warning: Could not save state to '{STATE_FILE}': {e}")

# --- Global State Initialization ---
last_original_index_processed = load_last_processed_state()
if TICKERS_TO_PROCESS: # Check if the list is not empty
    start_offset = (last_original_index_processed + 1) % len(TICKERS_TO_PROCESS)
    # Create a reordered list for the cycle, starting after the last processed ticker
    reordered_tickers_for_cycle = TICKERS_TO_PROCESS[start_offset:] + TICKERS_TO_PROCESS[:start_offset]
    ticker_iterator = cycle(reordered_tickers_for_cycle)
    print(f"[{datetime.now()}] Loaded last processed original ticker index: {last_original_index_processed}.")
    if reordered_tickers_for_cycle:
        print(f"[{datetime.now()}] Iterator will start with ticker: {reordered_tickers_for_cycle[0]} (Original index: {TICKERS_TO_PROCESS.index(reordered_tickers_for_cycle[0])})")
    else:
        print(f"[{datetime.now()}] Warning: Ticker list is empty after reordering (should not happen if TICKERS_TO_PROCESS is not empty).")
else:
    ticker_iterator = cycle([]) # Should have exited if TICKERS_TO_PROCESS was empty
    print(f"[{datetime.now()}] Error: TICKERS_TO_PROCESS is empty. Cannot initialize ticker iterator. Exiting.")
    exit(1)


writer_iterator = cycle(WRITERS)
posts_published_today = 0 # Resets on each script start, for daily limit within a single run
last_publish_time = None  # Resets on each script start


# --- Helper Functions ---
def get_report_html_from_ai_app(ticker, app_root):
    print(f"[{datetime.now()}] Generating report for ticker: {ticker}")
    timestamp = str(int(time.time()))
    try:
        _model, _forecast, text_report_html, _img_urls = run_wp_pipeline(ticker, timestamp, app_root)
        if text_report_html and "Error Generating Report" not in text_report_html:
            print(f"[{datetime.now()}] Report HTML generated successfully for {ticker}.")
            return text_report_html
        else:
            error_detail = f"Error in pipeline output: {text_report_html if text_report_html else 'No HTML returned'}"
            print(f"[{datetime.now()}] Failed to generate report HTML for {ticker}. {error_detail}")
            return None
    except Exception as e:
        print(f"[{datetime.now()}] Exception during report generation for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_post_title(ticker, writer_info):
    year_range_fixed = "2025-26"
    template = random.choice(HEADLINE_TEMPLATES)
    title = template.format(ticker=ticker, year_range=year_range_fixed, writer_name=writer_info['username'])
    max_title_length = 80 # As per your previous version
    if len(title) > max_title_length:
        last_space = title.rfind(' ', 0, max_title_length - 3)
        title = title[:last_space] + "..." if last_space != -1 else title[:max_title_length - 3] + "..."
    return title

def create_slug(title, max_length=70):
    slug = title.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    if len(slug) > max_length:
        trimmed_slug = slug[:max_length]
        last_hyphen_index = trimmed_slug.rfind('-')
        slug = trimmed_slug[:last_hyphen_index] if last_hyphen_index > 0 else trimmed_slug
    return slug

def publish_to_wordpress(writer_info, ticker, report_html_content, ticker_original_idx_to_save):
    post_title = generate_post_title(ticker, writer_info)
    post_slug = create_slug(post_title, max_length=65)
    post_status = "draft"

    credentials = f"{writer_info['username']}:{writer_info['app_password']}"
    token = base64.b64encode(credentials.encode())
    headers = {
        "Authorization": f"Basic {token.decode('utf-8')}",
        "Content-Type": "application/json",
    }
    api_url = f"{WORDPRESS_URL}/wp-json/wp/v2/posts"

    payload = {
        "title": post_title,
        "content": report_html_content,
        "status": post_status,
        "author": writer_info['wp_user_id'],
        "slug": post_slug,
    }

    if WP_CATEGORY_STOCKFORECAST_ID:
        payload["categories"] = [WP_CATEGORY_STOCKFORECAST_ID]
    else:
        print(f"[{datetime.now()}] Note: 'Stock Forecast' category ID not configured. Post will not be assigned to this category.")

    print(f"[{datetime.now()}] Attempting to publish '{post_title}' (Slug: {post_slug}) as user '{writer_info['username']}' (ID: {writer_info['wp_user_id']}).")
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        print(f"[{datetime.now()}] Report successfully uploaded to WordPress for {ticker} by {writer_info['username']}!")
        print(f"    Post ID: {response.json().get('id')}")
        print(f"    View Post: {response.json().get('link')}")
        save_last_processed_state(ticker_original_idx_to_save) # Save index on successful publish
        return True
    except requests.exceptions.HTTPError as errh:
        print(f"[{datetime.now()}] HTTP Error publishing for {ticker} by {writer_info['username']}: {errh}")
        print(f"    Response status code: {errh.response.status_code}")
        try:
            print(f"    Response content: {errh.response.json()}")
        except json.JSONDecodeError:
            print(f"    Response content (non-JSON): {errh.response.text}")
    except requests.exceptions.RequestException as err:
        print(f"[{datetime.now()}] Request Exception publishing for {ticker} by {writer_info['username']}: {err}")
    return False

def job():
    global posts_published_today, last_publish_time, ticker_iterator, writer_iterator
    current_time = datetime.now()

    if last_publish_time and last_publish_time.date() != current_time.date():
        print(f"[{current_time}] New day detected. Resetting daily post count.")
        posts_published_today = 0

    if posts_published_today >= 12: # Max 12 posts per 24 hours
        print(f"[{current_time}] Daily post limit (12) reached for {current_time.date()}. Skipping this run.")
        return

    # Get the next ticker from our (potentially reordered) cycle
    selected_ticker_from_cycle = next(ticker_iterator)
    
    # Find its original index in TICKERS_TO_PROCESS to save the correct state
    try:
        original_ticker_index = TICKERS_TO_PROCESS.index(selected_ticker_from_cycle)
    except ValueError:
        # This should ideally not happen if reordered_tickers_for_cycle is derived correctly
        print(f"[{datetime.now()}] CRITICAL Error: Ticker '{selected_ticker_from_cycle}' from cycle not found in original TICKERS_TO_PROCESS. State saving will be incorrect. Re-initializing ticker iterator.")
        # Fallback: re-initialize ticker_iterator to avoid getting stuck.
        # This means it might repeat, but better than continuously failing.
        start_offset = 0 # Default to start
        reordered_tickers_for_cycle = TICKERS_TO_PROCESS[start_offset:] + TICKERS_TO_PROCESS[:start_offset]
        ticker_iterator = cycle(reordered_tickers_for_cycle)
        selected_ticker_from_cycle = next(ticker_iterator) # Get the first one again
        original_ticker_index = TICKERS_TO_PROCESS.index(selected_ticker_from_cycle)

    selected_writer = next(writer_iterator)
    print(f"--- [{current_time}] Starting new publishing job ---")
    print(f"    Selected Ticker: {selected_ticker_from_cycle} (Original Index for state saving: {original_ticker_index})")
    print(f"    Selected Writer: {selected_writer['username']}")

    report_html = get_report_html_from_ai_app(selected_ticker_from_cycle, APP_ROOT_PATH)
    if report_html:
        if publish_to_wordpress(selected_writer, selected_ticker_from_cycle, report_html, original_ticker_index): # Pass original index
            posts_published_today += 1
            last_publish_time = current_time
            print(f"    Posts published today ({current_time.date()}): {posts_published_today}")
        else:
            print(f"    Failed to publish report for {selected_ticker_from_cycle}.")
    else:
        print(f"    Failed to generate HTML for {selected_ticker_from_cycle}. Skipping WordPress upload.")
    print(f"--- [{current_time}] Publishing job finished. ---")

def schedule_next_job():
    delay_minutes = random.randint(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES)
    print(f"[{datetime.now()}] Scheduling next job in {delay_minutes} minutes.")
    schedule.clear()
    schedule.every(delay_minutes).minutes.do(run_job_and_reschedule)

def run_job_and_reschedule():
    job()
    schedule_next_job()
    return schedule.CancelJob

if __name__ == "__main__":
    print(f"[{datetime.now()}] Starting Auto Publisher Service...")
    print(f"    Publishing to: {WORDPRESS_URL}")
    print(f"    Number of writers successfully configured: {len(WRITERS)}")
    print(f"    Number of tickers in rotation: {len(TICKERS_TO_PROCESS)}")
    print(f"    FRED API Key Loaded: {'Yes' if FRED_API_KEY else 'No'}")
    print(f"    Posting interval will be random between {MIN_INTERVAL_MINUTES} and {MAX_INTERVAL_MINUTES} minutes.")
    if WP_CATEGORY_STOCKFORECAST_ID:
        print(f"    Assigning posts to 'Stock Forecast' category ID: {WP_CATEGORY_STOCKFORECAST_ID}")
    else:
        print(f"    'Stock Forecast' category ID not configured. Posts will not be assigned to this category.")

    # --- Modified Startup ---
    # Instead of running job() immediately, we schedule the first job.
    # This ensures that even on the very first run after a restart,
    # the ticker selection respects the persisted index.
    print(f"[{datetime.now()}] Initializing and scheduling the first job...")
    schedule_next_job() # Schedule the first job with a random delay

    print(f"[{datetime.now()}] Scheduler started. Waiting for first scheduled run...")
    while True:
        schedule.run_pending()
        time.sleep(30)