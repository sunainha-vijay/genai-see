# app.py
from flask import Flask, render_template, request, send_from_directory, jsonify, url_for, request # Keep request
import os
import time
import traceback
import re # Import the 're' module for regex
from pipeline import run_pipeline
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

@app.route('/', methods=['GET'])
def index():
    """Serves the main homepage."""
    return render_template('stock-analysis-homepage.html')

# --- NEW ROUTE ---
@app.route('/report/view')
def show_report_page():
    """Renders the report viewer page, displaying the report via iframe."""
    report_url = request.args.get('url') # Get report file URL from query param
    ticker = request.args.get('ticker', 'Unknown') # Get ticker for title
    # Basic validation/sanitization for URL might be needed in production
    return render_template('report_display.html', report_url=report_url, ticker=ticker)
# --- END NEW ROUTE ---

@app.route('/generate', methods=['POST'])
def generate_report():
    """
    Handles the asynchronous request to generate the stock analysis report.
    Returns a JSON response with the status and the URL to the viewer page.
    """
    start_time = time.time()
    print("\n--- Received /generate request ---")

    if not request.is_json:
        print("Error: Request must be JSON")
        return jsonify({'status': 'error', 'message': 'Invalid request format. Expected JSON.'}), 400

    data = request.get_json()
    ticker = data.get('ticker', '').strip().upper()
    print(f"Received ticker: {ticker}")

    # --- UPDATED VALIDATION ---
    # Allow letters, numbers, '.', '^', '-' and remove length limit
    # Adjusted regex to be more permissive: Allows alphanumeric, caret, dot, hyphen.
    # You might want to refine this further based on exact allowed symbols.
    valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
    if not ticker or not re.match(valid_ticker_pattern, ticker):
        error_message = "Invalid ticker symbol format. Please use standard symbols (e.g., AAPL, BRK-A, ^GSPC)."
        print(f"Validation Error: {error_message}")
        return jsonify({'status': 'error', 'message': error_message}), 400
    # --- END UPDATED VALIDATION ---


    try:
        timestamp = str(int(time.time()))
        print(f"Running pipeline for {ticker} with timestamp {timestamp}...")

        pipeline_result = run_pipeline(ticker, timestamp, APP_ROOT)

        report_path = None
        # Assuming pipeline returns (model, forecast, report_path, report_html)
        # We only need report_path here
        if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4: # Check for 4 elements
            report_path = pipeline_result[2] # report_path is the 3rd element

        if report_path and os.path.exists(report_path):
            end_time = time.time()
            duration = end_time - start_time
            print(f"Pipeline completed successfully for {ticker} in {duration:.2f} seconds.")
            print(f"Report saved at: {report_path}")

            report_filename = os.path.basename(report_path)

            # --- Generate URL for the static report file itself ---
            # Use relative URL is fine as iframe src will resolve it
            report_file_url = url_for('serve_static', filename=report_filename, _external=False)
            print(f"Generated static report file URL: {report_file_url}")

            # --- Generate URL for the viewer page, passing the report file URL as query param ---
            # Make sure to URL-encode the report_file_url when adding it as a parameter
            viewer_url = url_for('show_report_page', ticker=ticker, url=report_file_url, _external=False)
            print(f"Generated viewer page URL: {viewer_url}")


            # --- Return the VIEWER URL in the JSON response ---
            return jsonify({
                'status': 'success',
                'ticker': ticker,
                'viewer_url': viewer_url, # Send URL of the page that *contains* the iframe
                'duration': f"{duration:.2f}"
            })
        else:
            # Check if pipeline_result has the 4th element (report_html) even if path saving failed
            report_html_content = None
            if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 4:
                 report_html_content = pipeline_result[3]

            if report_html_content:
                 # If HTML was generated but file saving failed or wasn't returned properly
                 error_message = f"Report generation completed for {ticker}, but failed to save or retrieve the report file path. Check file system permissions or pipeline logic."
                 print(f"Pipeline Warning: {error_message}")
                 # Still might be able to proceed if html content is available?
                 # For now, return error, but you could potentially handle this differently.
                 return jsonify({'status': 'error', 'message': error_message}), 500
            else:
                 # If pipeline truly failed to generate anything
                 error_message = f"Report generation failed for {ticker}. Pipeline did not produce a valid report. Check logs."
                 print(f"Pipeline Error: {error_message}")
                 return jsonify({'status': 'error', 'message': error_message}), 500


    # --- Exception Handling (Keep as before) ---
    except Exception as e:
         print(f"An unexpected error occurred: {e}")
         traceback.print_exc()
         error_message = f"An unexpected error occurred while generating the report for {ticker}. Please try again later or contact support."
         return jsonify({'status': 'error', 'message': error_message}), 500


if __name__ == "__main__":
    print(f"App Root: {APP_ROOT}")
    print(f"Static Folder: {app.static_folder}")
    print(f"Template Folder: {app.template_folder}")
    print(f"Starting Flask server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)