# app.py (UPDATED)
from flask import Flask, render_template, request, send_from_directory, jsonify, url_for
import os
import time
import traceback
import re # Import the 're' module for regex
# --- Import BOTH pipeline functions ---
from pipeline import run_pipeline, run_wp_pipeline
from urllib.parse import urljoin, quote # Import quote for query parameters

# --- Get the absolute path to the directory where app.py is located ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# --- Define the static folder path based on APP_ROOT ---
STATIC_FOLDER_PATH = os.path.join(APP_ROOT, 'static')
TEMPLATE_FOLDER_PATH = os.path.join(APP_ROOT, 'templates') # Define template folder path

# --- Use the absolute paths for Flask ---
app = Flask(__name__,
            static_folder=STATIC_FOLDER_PATH,
            template_folder=TEMPLATE_FOLDER_PATH) # Set template folder
app.jinja_env.globals.update(zip=zip)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 # Disable caching for static files during dev
app.secret_key = os.urandom(24) # Needed if using session, good practice anyway

# Ensure the static directory exists
os.makedirs(STATIC_FOLDER_PATH, exist_ok=True)

@app.route('/static/<path:filename>')
def serve_static(filename):
    # Serve from the absolutely defined static folder path
    return send_from_directory(
        app.static_folder,
        filename,
        cache_timeout=0
    )

# --- Original Routes (Unchanged) ---
@app.route('/', methods=['GET'])
def index():
    """Serves the main homepage."""
    return render_template('stock-analysis-homepage.html')

@app.route('/report/view')
def show_report_page():
    """Renders the report viewer page, displaying the report via iframe."""
    report_url = request.args.get('url') # Get report file URL from query param
    ticker = request.args.get('ticker', 'Unknown') # Get ticker for title
    return render_template('report_display.html', report_url=report_url, ticker=ticker)

@app.route('/generate', methods=['POST'])
def generate_report():
    """
    Handles the asynchronous request to generate the standard stock analysis report.
    Returns a JSON response with the status and the URL to the viewer page.
    """
    start_time = time.time()
    print("\n--- Received /generate request (Original Report) ---")

    if not request.is_json:
        print("Error: Request must be JSON")
        return jsonify({'status': 'error', 'message': 'Invalid request format. Expected JSON.'}), 400

    data = request.get_json()
    ticker = data.get('ticker', '').strip().upper()
    print(f"Received ticker: {ticker}")

    # Use the more flexible validation pattern
    valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
    if not ticker or not re.match(valid_ticker_pattern, ticker):
        error_message = "Invalid ticker symbol format. Please use standard symbols (e.g., AAPL, BRK-A, ^GSPC)."
        print(f"Validation Error: {error_message}")
        return jsonify({'status': 'error', 'message': error_message}), 400

    try:
        timestamp = str(int(time.time()))
        print(f"Running ORIGINAL pipeline for {ticker} with timestamp {timestamp}...")

        # Call the original pipeline function
        pipeline_result = run_pipeline(ticker, timestamp, APP_ROOT)

        report_path = None
        report_html_content = None # Initialize HTML content

        if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4:
            # Unpack results carefully
            model, forecast, report_path, report_html_content = pipeline_result

        # Check if the report was generated successfully (path exists OR html content is valid)
        if (report_path and os.path.exists(report_path)) or (report_html_content and "Error Generating Report" not in report_html_content):
            end_time = time.time(); duration = end_time - start_time
            print(f"Original pipeline completed successfully for {ticker} in {duration:.2f} seconds.")

            # Prefer path if it exists, otherwise indicate HTML only
            if report_path and os.path.exists(report_path):
                report_filename = os.path.basename(report_path)
                report_file_url = url_for('serve_static', filename=report_filename, _external=False)
                viewer_url = url_for('show_report_page', ticker=ticker, url=report_file_url, _external=False)
                print(f"Generated viewer page URL: {viewer_url}")
                status_message = 'success'
            else:
                # HTML was generated but not saved
                viewer_url = "#" # No direct view URL if file wasn't saved
                status_message = 'success_html_only' # Indicate partial success
                print("Report HTML generated but file not saved.")


            return jsonify({
                'status': status_message, 'ticker': ticker,
                'viewer_url': viewer_url, 'duration': f"{duration:.2f}"
            })
        else:
            # Handle report generation failure
            error_message = f"Report generation failed for {ticker}. Check pipeline logs."
            if report_html_content and "Error Generating Report" in report_html_content:
                 error_message = f"Report generation failed for {ticker}. Pipeline returned an error report."

            print(f"Pipeline Error/Warning: {error_message}")
            return jsonify({'status': 'error', 'message': error_message}), 500

    except Exception as e:
         print(f"An unexpected error occurred in /generate: {e}")
         traceback.print_exc()
         return jsonify({'status': 'error', 'message': f"An unexpected error occurred for {ticker}."}), 500


# --- NEW Routes for WordPress Asset Generation ---

@app.route('/wp-admin-generator') # Consider a more obscure path for privacy
def wp_generator_page():
    """Serves the private HTML page used to generate WP assets."""
    # IMPORTANT: Add authentication/authorization here if this needs to be private
    print("Serving WP Generator page")
    return render_template('wp_generator.html')

@app.route('/generate-wp-assets', methods=['POST'])
def generate_wp_assets():
    """
    Handles the asynchronous request to generate WordPress assets (text HTML + image URLs).
    Returns a JSON response with the HTML content and image URLs.
    """
    start_time = time.time()
    print("\n+++ Received /generate-wp-assets request +++")

    if not request.is_json:
        print("Error: WP Asset Request must be JSON")
        return jsonify({'status': 'error', 'message': 'Invalid request format. Expected JSON.'}), 400

    data = request.get_json()
    ticker = data.get('ticker', '').strip().upper()
    print(f"Received WP ticker: {ticker}")

    # Use the same flexible validation
    valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
    if not ticker or not re.match(valid_ticker_pattern, ticker):
        error_message = "Invalid ticker symbol format. Please use standard symbols (e.g., AAPL, BRK-A, ^GSPC)."
        print(f"WP Validation Error: {error_message}")
        return jsonify({'status': 'error', 'message': error_message}), 400

    try:
        timestamp = str(int(time.time()))
        print(f"Running WP pipeline for {ticker} with timestamp {timestamp}...")

        # --- Call the WordPress pipeline function ---
        # Expecting (model, forecast, text_html, image_urls_dict)
        pipeline_result = run_wp_pipeline(ticker, timestamp, APP_ROOT)

        if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4:
            text_report_html = pipeline_result[2]
            # --- This variable now holds the dictionary of RELATIVE URLs ---
            # --- e.g., {'forecast': '/static/ticker_forecast_ts.png', ...} ---
            chart_image_urls = pipeline_result[3]

            # Check if HTML was generated successfully
            if text_report_html is not None and "Error Generating Report" not in text_report_html:
                end_time = time.time(); duration = end_time - start_time
                print(f"WP pipeline completed successfully for {ticker} in {duration:.2f} seconds.")

                # --- FIX: Directly use the returned dictionary ---
                # No need to re-validate paths or re-build URLs here.
                # The pipeline already confirmed save success and returned relative URLs.
                print(f"Received WP Chart Image URLs from pipeline: {chart_image_urls}") # Log the received dict

                # --- Return the TEXT HTML content and the received IMAGE URLs dictionary ---
                return jsonify({
                    'status': 'success',
                    'ticker': ticker,
                    'report_html': text_report_html,      # The actual text HTML string
                    'chart_urls': chart_image_urls,       # The dict of image URLs from pipeline
                    'duration': f"{duration:.2f}"
                })
            else:
                # Handle case where WP HTML wasn't generated or contained error
                error_message = f"WP Asset generation failed for {ticker}. Pipeline did not produce valid HTML."
                print(f"WP Pipeline Error: {error_message}")
                return jsonify({'status': 'error', 'message': error_message}), 500
        else:
             # Handle case where WP pipeline failed earlier or returned invalid result
             error_message = f"WP Asset generation failed for {ticker}. Check pipeline logs for errors."
             print(f"WP Pipeline Error: {error_message}")
             return jsonify({'status': 'error', 'message': error_message}), 500

    except Exception as e:
         print(f"An unexpected error occurred in /generate-wp-assets: {e}")
         traceback.print_exc()
         error_message = f"An unexpected error occurred while generating WP assets for {ticker}."
         return jsonify({'status': 'error', 'message': error_message}), 500


# --- Main execution ---
if __name__ == "__main__":
    print(f"App Root: {APP_ROOT}")
    print(f"Static Folder: {app.static_folder}")
    print(f"Template Folder: {app.template_folder}")
    print(f"Starting Flask server on http://0.0.0.0:5000")
    # Use threaded=True if your pipeline tasks are CPU-bound and can benefit from concurrency
    # Use debug=True only for development, set to False for production
    # Set use_reloader=False if reloading causes issues with background tasks/threads
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)