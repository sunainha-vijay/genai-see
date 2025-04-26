# app.py
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
        if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4:
            report_path = pipeline_result[2] # report_path is the 3rd element

        if report_path and os.path.exists(report_path):
            end_time = time.time(); duration = end_time - start_time
            print(f"Original pipeline completed successfully for {ticker} in {duration:.2f} seconds.")
            report_filename = os.path.basename(report_path)
            report_file_url = url_for('serve_static', filename=report_filename, _external=False)
            viewer_url = url_for('show_report_page', ticker=ticker, url=report_file_url, _external=False)
            print(f"Generated viewer page URL: {viewer_url}")

            return jsonify({
                'status': 'success', 'ticker': ticker,
                'viewer_url': viewer_url, 'duration': f"{duration:.2f}"
            })
        else:
            # Handle report generation failure (same logic as before)
            report_html_content = pipeline_result[3] if pipeline_result and len(pipeline_result) >= 4 else None
            if report_html_content:
                 error_message = f"Report generation completed for {ticker}, but failed to save or retrieve the report file path."
            else:
                 error_message = f"Report generation failed for {ticker}. Pipeline did not produce a valid report."
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
    # For now, it's accessible to anyone who knows the URL.
    # Example (very basic, replace with proper auth):
    # if request.remote_addr != 'YOUR_IP_ADDRESS': # Very basic IP check
    #     return "Access Denied", 403
    print("Serving WP Generator page")
    # Assumes you will create 'wp_generator.html' in the templates folder
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

        # --- Call the NEW WordPress pipeline function ---
        # Expecting (model, forecast, text_html, image_paths)
        pipeline_result = run_wp_pipeline(ticker, timestamp, APP_ROOT)

        if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4:
            text_report_html = pipeline_result[2]
            chart_image_paths = pipeline_result[3] # Dict of {'type': '/path/to/img.png'}

            if text_report_html is not None:
                end_time = time.time(); duration = end_time - start_time
                print(f"WP pipeline completed successfully for {ticker} in {duration:.2f} seconds.")

                # --- Generate URLs for the saved images ---
                chart_image_urls = {}
                if isinstance(chart_image_paths, dict):
                    for chart_type, img_path in chart_image_paths.items():
                        if img_path and os.path.exists(img_path):
                            img_filename = os.path.basename(img_path)
                            # Generate URL relative to the static folder
                            chart_image_urls[chart_type] = url_for('serve_static', filename=img_filename, _external=False)
                        else:
                            print(f"Warning: WP Image path not found/invalid for '{chart_type}': {img_path}")

                print(f"Generated WP Chart Image URLs: {chart_image_urls}")

                # --- Return the TEXT HTML content and IMAGE URLs ---
                return jsonify({
                    'status': 'success',
                    'ticker': ticker,
                    'report_html': text_report_html,   # The actual text HTML string
                    'chart_urls': chart_image_urls,    # Dict of image URLs
                    'duration': f"{duration:.2f}"
                })
            else:
                # Handle case where WP HTML wasn't generated
                error_message = f"WP Asset generation failed for {ticker}. Pipeline did not produce HTML."
                print(f"WP Pipeline Error: {error_message}")
                return jsonify({'status': 'error', 'message': error_message}), 500
        else:
             # Handle case where WP pipeline failed earlier
             error_message = f"WP Asset generation failed for {ticker}. Check logs."
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
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)