# app.py
from flask import Flask, render_template, request, send_from_directory, jsonify, url_for, request # Added request
import os
import time
import traceback
from pipeline import run_pipeline
from urllib.parse import urljoin # Import urljoin

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
app.secret_key = os.urandom(24) # For session management if needed later
# --- Optional: Set SERVER_NAME if you want to use url_for with _external=True reliably ---
# --- Replace with your actual domain/IP and port if not running locally on 5000 ---
# app.config['SERVER_NAME'] = '127.0.0.1:5000'
# app.config['APPLICATION_ROOT'] = '/' # Adjust if running under a subpath
# app.config['PREFERRED_URL_SCHEME'] = 'http' # or 'https' if applicable

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

@app.route('/generate', methods=['POST'])
def generate_report():
    """
    Handles the asynchronous request to generate the stock analysis report.
    Returns a JSON response with the status and either the *absolute* report URL or an error message.
    """
    start_time = time.time()
    print("\n--- Received /generate request ---")

    if not request.is_json:
        print("Error: Request must be JSON")
        return jsonify({'status': 'error', 'message': 'Invalid request format. Expected JSON.'}), 400

    data = request.get_json()
    ticker = data.get('ticker', '').strip().upper()
    print(f"Received ticker: {ticker}")

    if not ticker or not ticker.isalpha() or not (1 <= len(ticker) <= 5):
        error_message = "Invalid stock ticker symbol. Please enter 1-5 letters (e.g., AAPL)."
        print(f"Validation Error: {error_message}")
        return jsonify({'status': 'error', 'message': error_message}), 400

    try:
        timestamp = str(int(time.time()))
        print(f"Running pipeline for {ticker} with timestamp {timestamp}...")

        pipeline_result = run_pipeline(ticker, timestamp, APP_ROOT)

        report_path = None
        if pipeline_result and isinstance(pipeline_result, tuple) and len(pipeline_result) >= 3:
            report_path = pipeline_result[2]

        if report_path and os.path.exists(report_path):
            end_time = time.time()
            duration = end_time - start_time
            print(f"Pipeline completed successfully for {ticker} in {duration:.2f} seconds.")
            print(f"Report saved at: {report_path}")

            report_filename = os.path.basename(report_path)

            # --- Generate Absolute URL ---
            # Method 1: Using url_for with _external=True (Requires SERVER_NAME config)
            # report_url_absolute = url_for('serve_static', filename=report_filename, _external=True)

            # Method 2: Manually construct using request context (More flexible if SERVER_NAME isn't set)
            # Get the base URL (scheme, host, port) from the incoming request
            # Note: request.url_root might include subpaths if accessed via proxy, handle carefully.
            # For simplicity, let's assume direct access or proxy handles path correctly.
            base_url = request.url_root # e.g., "http://127.0.0.1:5000/" or "http://example.com/myapp/"
            relative_url = url_for('serve_static', filename=report_filename) # e.g., "/static/report.html"
            # Use urljoin to correctly combine base and relative path
            report_url_absolute = urljoin(base_url, relative_url)

            print(f"Generated absolute report URL: {report_url_absolute}")

            # --- Return the ABSOLUTE URL in the JSON response ---
            return jsonify({
                'status': 'success',
                'ticker': ticker,
                'report_url': report_url_absolute, # Send the ABSOLUTE URL for redirection
                'duration': f"{duration:.2f}"
            })
        else:
            error_message = f"Report generation failed for {ticker}. Pipeline did not produce a valid report file. Check logs."
            print(f"Pipeline Error: {error_message}")
            return jsonify({'status': 'error', 'message': error_message}), 500

    # --- Exception Handling (Keep as before) ---
    except FileNotFoundError as e:
         print(f"Error - File Not Found: {e}")
         traceback.print_exc()
         error_message = f"Report generation process failed: Could not find a necessary file. Please check server logs."
         return jsonify({'status': 'error', 'message': error_message}), 500
    except ValueError as e:
         print(f"Error - Value Error (e.g., bad data/ticker): {e}")
         traceback.print_exc()
         user_error_message = f"Report generation failed for {ticker}: {str(e)}. Check if the ticker is valid or try again later."
         return jsonify({'status': 'error', 'message': user_error_message}), 400
    except RuntimeError as e:
         print(f"Error - Runtime Error in pipeline: {e}")
         traceback.print_exc()
         error_message = f"An internal error occurred during report generation: {str(e)}. Please check server logs."
         return jsonify({'status': 'error', 'message': error_message}), 500
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
    # Make sure to access the app via http://127.0.0.1:5000 or http://<your-ip>:5000
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True) # Ensure port is 5000