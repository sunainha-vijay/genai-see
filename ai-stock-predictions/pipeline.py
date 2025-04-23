# pipeline.py
import os
import time
import traceback

import pandas as pd
import yfinance as yf

from config import TICKERS
from data_collection import fetch_stock_data
from macro_data import fetch_macro_indicators
from data_preprocessing import preprocess_data
from prophet_model import train_prophet_model
from report_generator import create_full_report # Ensure this is imported

# --- Modify function signature to accept app_root ---
# --- Modify function to return report_html ---
def run_pipeline(ticker, ts, app_root):
    """
    Runs the full analysis pipeline for a given stock ticker.

    Args:
        ticker (str): The stock ticker symbol.
        ts (str): Timestamp string for file naming.
        app_root (str): The absolute path to the application's root directory.

    Returns:
        tuple: Contains (model, forecast, report_path, report_html) on success,
               or (None, None, None, None) on failure.
               report_html contains the full HTML content of the report.
    """
    # --- Define the target static directory using app_root ---
    static_dir_path = os.path.join(app_root, 'static')
    # --- Ensure the target static directory exists ---
    os.makedirs(static_dir_path, exist_ok=True)

    # Initialize paths and content to None
    stock_csv = macro_csv = processed_csv = report_path = report_html = None
    model = forecast = None # Initialize model and forecast

    try:
        print(f"\n----- Starting pipeline for {ticker} -----")
        if not ticker or not isinstance(ticker, str) or not ticker.isalpha() or not (1 <= len(ticker) <= 5):
             raise ValueError(f"Invalid ticker format received: {ticker}. Must be 1-5 letters.")

        # --- 1. Data Collection ---
        print("Step 1: Fetching stock data...")
        stock_data = fetch_stock_data(ticker)
        if stock_data is None or stock_data.empty:
            raise RuntimeError(f"No stock data found for ticker: {ticker}. Is it a valid symbol?")
        # --- Save CSV inside the correct static folder ---
        stock_csv = os.path.join(static_dir_path, f"{ticker}_raw_data_{ts}.csv")
        stock_data.to_csv(stock_csv, index=False)
        print(f"   Saved raw data -> {os.path.basename(stock_csv)}")

        print("Step 1b: Fetching macroeconomic data...")
        macro_data = fetch_macro_indicators()
        if macro_data is None or macro_data.empty:
            print("Warning: Failed to fetch macroeconomic data. Proceeding without it.")
            # Create an empty DataFrame with expected index to avoid downstream errors if possible
            # Or handle this gracefully in preprocess_data
            # For now, just proceed, preprocess_data might handle it.
        else:
            # --- Save CSV inside the correct static folder ---
            macro_csv = os.path.join(static_dir_path, f"macro_indicators_{ts}.csv")
            macro_data.to_csv(macro_csv, index=False)
            print(f"   Saved macro data -> {os.path.basename(macro_csv)}")

        # --- 2. Data Preprocessing ---
        print("Step 2: Preprocessing data...")
        # Pass None for macro_data if fetching failed
        processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
        if processed_data is None or processed_data.empty:
            raise RuntimeError("Preprocessing resulted in empty dataset.")
        # --- Save CSV inside the correct static folder ---
        processed_csv = os.path.join(static_dir_path, f"{ticker}_processed_{ts}.csv")
        processed_data.to_csv(processed_csv, index=False)
        print(f"   Saved processed data -> {os.path.basename(processed_csv)}")

        # --- 3. Prophet Model Training & Aggregation ---
        print("Step 3: Training Prophet model & predicting...")
        model, forecast, actual_df, forecast_df = train_prophet_model(
            processed_data,
            ticker,
            forecast_horizon='1y', # Example horizon
            timestamp=ts
            # No need to pass app_root here unless prophet_model saves files
        )
        if model is None or forecast is None or actual_df is None or forecast_df is None:
             raise RuntimeError("Prophet model training or forecasting failed.")
        print(f"   Model trained. Forecast generated for {len(forecast_df)} periods.")


        # --- 4. Fetch Fundamentals Separately ---
        print("Step 4: Fetching fundamentals via yfinance...")
        try:
            yf_ticker = yf.Ticker(ticker)
            # Access attributes safely with default values
            fundamentals = {
                'info': yf_ticker.info or {}, # Use empty dict if info is None
                'recommendations': yf_ticker.recommendations if hasattr(yf_ticker, 'recommendations') and yf_ticker.recommendations is not None else pd.DataFrame(), # Use empty DF
                'news': yf_ticker.news if hasattr(yf_ticker, 'news') and yf_ticker.news is not None else [] # Use empty list
            }
            # Basic check if info was fetched
            if not fundamentals['info'].get('symbol'):
                 print(f"Warning: Could not fetch detailed info for {ticker} via yfinance.")
                 # Proceed, but fundamental sections might be empty

        except Exception as yf_err:
             print(f"Warning: Error fetching yfinance fundamentals for {ticker}: {yf_err}. Proceeding without them.")
             fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': []} # Default empty structure

        # --- 5. Generate HTML Report (includes fundamentals) ---
        print("Step 5: Generating HTML report...")
        # --- Pass app_root to the report generator ---
        # --- Capture both path and HTML content ---
        report_path, report_html = create_full_report(
            ticker=ticker,
            actual_data=actual_df,
            forecast_data=forecast_df,
            historical_data=processed_data, # Use processed for history consistency? Or raw? Check report_generator needs
            fundamentals=fundamentals,
            ts=ts,
            aggregation='Monthly', # Assuming aggregation level if needed
            app_root=app_root # Pass app_root here
        )
        if report_html is None: # Check if HTML content was generated
            raise RuntimeError(f"Report generator failed to produce HTML content for {ticker}")
        if report_path: # Check if path was returned (file saved successfully)
            print(f"   Report saved -> {os.path.basename(report_path)}")
        else:
            print(f"   Report HTML generated, but failed to save file.")


        print(f"----- Pipeline successful for {ticker} -----")
        # Return the necessary results including the HTML content
        return model, forecast, report_path, report_html

    except ValueError as ve: # Catch specific input errors first
        print(f"----- Pipeline Input Error for {ticker} -----")
        print(f"Error: {ve}")
        traceback.print_exc()
        # Return None for all expected outputs
        return None, None, None, None
    except RuntimeError as rte: # Catch operational errors
        print(f"----- Pipeline Runtime Error for {ticker} -----")
        print(f"Error: {rte}")
        traceback.print_exc()
        return None, None, None, None
    except Exception as e: # Catch any other unexpected errors
        print(f"----- Pipeline failure for {ticker} -----")
        print(f"Unexpected Error: {e}")
        traceback.print_exc()
        # Cleanup any partial files using their absolute paths
        for path in {stock_csv, macro_csv, processed_csv, report_path}: # Only attempt remove if path was assigned
            if path and os.path.exists(path):
                try:
                    print(f"Attempting to remove partial file: {os.path.basename(path)}")
                    os.remove(path)
                except OSError as rm_err:
                     print(f"Error removing file {path}: {rm_err}")
        return None, None, None, None # Return None for all expected outputs

if __name__ == "__main__":
    print("Starting batch pipeline execution...")
    # --- For standalone execution, determine app_root differently ---
    # Assume pipeline.py is in the same directory as app.py for standalone
    APP_ROOT_STANDALONE = os.path.dirname(os.path.abspath(__file__))
    print(f"Running standalone from: {APP_ROOT_STANDALONE}")

    successful, failed = [], []

    for ticker in TICKERS:
        ts = str(int(time.time()))
        # --- Pass the determined root path for standalone execution ---
        # --- Capture all 4 return values ---
        model, forecast, report_path, report_html = run_pipeline(ticker, ts, APP_ROOT_STANDALONE)

        # --- Check if HTML content was generated for success ---
        if report_html:
            successful.append(ticker)
            print(f"[✔] {ticker} - Report HTML generated.")
            if not report_path:
                 print(f"  [!] {ticker} - Report file saving failed.")
        else:
            failed.append(ticker)
            print(f"[✖] {ticker}")

    print("\nBatch Summary:")
    print(f"  Successful (HTML Generated): {', '.join(successful) or 'None'}")
    print(f"  Failed:     {', '.join(failed) or 'None'}")
    print("Batch pipeline execution completed.")