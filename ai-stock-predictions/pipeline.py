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
from report_generator import create_full_report

# --- Modify function signature to accept app_root ---
def run_pipeline(ticker, ts, app_root):
    # --- Define the target static directory using app_root ---
    static_dir_path = os.path.join(app_root, 'static')
    # --- Ensure the target static directory exists ---
    os.makedirs(static_dir_path, exist_ok=True)

    # Initialize paths to None
    stock_csv = macro_csv = processed_csv = report_path = None

    try:
        print(f"\n----- Starting pipeline for {ticker} -----")
        if not ticker.isalpha() or len(ticker) > 5:
            raise ValueError(f"Invalid ticker format: {ticker}")

        # --- 1. Data Collection ---
        print("Fetching stock data...")
        stock_data = fetch_stock_data(ticker)
        if stock_data.empty:
            raise RuntimeError(f"No data found for {ticker}")
        # --- Save CSV inside the correct static folder ---
        stock_csv = os.path.join(static_dir_path, f"{ticker}_raw_data_{ts}.csv")
        stock_data.to_csv(stock_csv, index=False)
        print(f"Saved raw data → {stock_csv}")

        print("Fetching macroeconomic data...")
        macro_data = fetch_macro_indicators()
        if macro_data is None or macro_data.empty:
            raise RuntimeError("Failed to fetch macroeconomic data")
        # --- Save CSV inside the correct static folder ---
        macro_csv = os.path.join(static_dir_path, f"macro_indicators_{ts}.csv")
        macro_data.to_csv(macro_csv, index=False)
        print(f"Saved macro data → {macro_csv}")

        # --- 2. Data Preprocessing ---
        print("Preprocessing data...")
        processed_data = preprocess_data(stock_data, macro_data)
        if processed_data.empty:
            raise RuntimeError("Preprocessing resulted in empty dataset")
        # --- Save CSV inside the correct static folder ---
        processed_csv = os.path.join(static_dir_path, f"{ticker}_processed_{ts}.csv")
        processed_data.to_csv(processed_csv, index=False)
        print(f"Saved processed data → {processed_csv}")

        # --- 3. Prophet Model Training & Aggregation ---
        print("Training Prophet model...")
        model, forecast, actual_df, forecast_df = train_prophet_model(
            processed_data,
            ticker,
            forecast_horizon='1y',
            timestamp=ts
            # No need to pass app_root here unless prophet_model saves files
        )

        # --- 4. Fetch Fundamentals Separately ---
        print("Fetching fundamentals via yfinance...")
        yf_ticker = yf.Ticker(ticker)
        fundamentals = {
            'info': yf_ticker.info,
            'recommendations': getattr(yf_ticker, 'recommendations', []),
            'news': getattr(yf_ticker, 'news', [])
        }
        # Handle potential None for recommendations/news before passing
        if fundamentals['recommendations'] is None: fundamentals['recommendations'] = []
        if fundamentals['news'] is None: fundamentals['news'] = []


        # --- 5. Generate HTML Report (includes fundamentals) ---
        print("Generating HTML report...")
        # --- Pass app_root to the report generator ---
        report_path = create_full_report(
            ticker=ticker,
            actual_data=actual_df,
            forecast_data=forecast_df,
            historical_data=processed_data,
            fundamentals=fundamentals,
            ts=ts,
            aggregation='Monthly',
            app_root=app_root # Pass app_root here
        )
        if not report_path or not os.path.exists(report_path):
            raise RuntimeError(f"Report generator failed or report not found at {report_path}")
        print(f"Report saved → {report_path}")

        print(f"----- Pipeline successful for {ticker} -----")
        # Return the absolute report path
        return model, forecast, report_path

    except Exception as e: # Catch specific error 'e'
        print(f"----- Pipeline failure for {ticker} -----")
        print(f"Error: {e}") # Print the specific error message
        traceback.print_exc()
        # Cleanup any partial files using their absolute paths
        for path in {stock_csv, macro_csv, processed_csv, report_path}:
            if path and os.path.exists(path):
                try:
                    print(f"Attempting to remove partial file: {path}")
                    os.remove(path)
                except OSError as rm_err:
                     print(f"Error removing file {path}: {rm_err}")
        return None, None, None

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
        model, forecast, report = run_pipeline(ticker, ts, APP_ROOT_STANDALONE)
        if report:
            successful.append(ticker)
            print(f"[✔] {ticker}")
        else:
            failed.append(ticker)
            print(f"[✖] {ticker}")

    print("\nBatch Summary:")
    print(f"  Successful: {', '.join(successful) or 'None'}")
    print(f"  Failed:     {', '.join(failed) or 'None'}")
    print("Batch pipeline execution completed.")