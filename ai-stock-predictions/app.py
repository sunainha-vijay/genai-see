# app.py
from flask import Flask, render_template, request, send_from_directory, url_for, redirect
import os
import time
import traceback
from pipeline import run_pipeline

# --- Get the absolute path to the directory where app.py is located ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
# --- Define the static folder path based on APP_ROOT ---
STATIC_FOLDER_PATH = os.path.join(APP_ROOT, 'static')

# --- Use the absolute path for Flask's static_folder ---
app = Flask(__name__, static_folder=STATIC_FOLDER_PATH)
app.jinja_env.globals.update(zip=zip)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.secret_key = os.urandom(24)

# Ensure the *correct* static directory exists
os.makedirs(STATIC_FOLDER_PATH, exist_ok=True) # Create it here based on absolute path

@app.route('/static/<path:filename>')
def serve_static(filename):
    # Serve from the absolutely defined static folder path
    return send_from_directory(
        app.static_folder, # This now holds the absolute path
        filename,
        headers={
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

@app.route('/', methods=['GET', 'POST'])
def index():
    error = None
    if request.method == 'POST':
        ticker = request.form.get('ticker', '').strip().upper()

        if not ticker or not ticker.isalpha() or not (1 <= len(ticker) <= 5):
            error = "Invalid stock ticker symbol. Please enter 1-5 letters (e.g., AAPL)."
            return render_template('stock-analysis-homepage.html', error=error)

        print(f"Received ticker: {ticker}")

        try:
            timestamp = str(int(time.time()))
            print(f"Running pipeline for {ticker} with timestamp {timestamp}...")

            # --- Pass the APP_ROOT path to the pipeline ---
            result = run_pipeline(ticker, timestamp, APP_ROOT) # Pass APP_ROOT here

            if not result or len(result) != 3:
                 print("Pipeline returned an unexpected result:", result)
                 raise RuntimeError("Analysis pipeline failed to produce a valid result.")

            _, _, report_path = result

            # report_path should now be an absolute path, but basename still works
            if not report_path or not os.path.exists(report_path):
                print(f"Report file not found at expected path: {report_path}")
                raise FileNotFoundError("Generated report file could not be found.")

            report_filename = os.path.basename(report_path)
            print(f"Report generated: {report_filename}")

            # Serve the report using the filename relative to the static folder
            return render_template('report.html',
                                   report_file=report_filename,
                                   ticker=ticker)

        except FileNotFoundError as e:
             print(f"Error - File Not Found: {e}")
             traceback.print_exc()
             error = f"Report generation process failed: Could not find a necessary file. Please check server logs."
        except ValueError as e:
             print(f"Error - Value Error (e.g., bad data): {e}")
             traceback.print_exc()
             error = f"Report generation failed for {ticker}: {str(e)}. Check if the ticker is valid or try again later."
        except RuntimeError as e:
             print(f"Error - Runtime Error in pipeline: {e}")
             traceback.print_exc()
             error = f"An internal error occurred during report generation: {str(e)}. Please check server logs."
        except Exception as e:
             print(f"An unexpected error occurred: {e}")
             traceback.print_exc()
             error = f"An unexpected error occurred while generating the report for {ticker}. Please try again later or contact support."

        return render_template('stock-analysis-homepage.html', error=error)

    return render_template('stock-analysis-homepage.html', error=error)

if __name__ == "__main__":
    # Important: Run app.py from within the ai-stock-predictions directory
    print(f"App Root: {APP_ROOT}")
    print(f"Static Folder: {app.static_folder}")
    app.run(host='0.0.0.0', port=5000, debug=True)