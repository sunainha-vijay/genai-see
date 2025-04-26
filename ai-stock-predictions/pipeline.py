# pipeline.py 
import os
import time
import traceback
import re

import pandas as pd
import yfinance as yf

from config import TICKERS
from data_collection import fetch_stock_data
from macro_data import fetch_macro_indicators
from data_preprocessing import preprocess_data
from prophet_model import train_prophet_model
# --- Import BOTH report generation functions ---
from report_generator import create_full_report, create_wordpress_report_assets

# --- Original pipeline function (Unchanged) ---
def run_pipeline(ticker, ts, app_root):
    """
    Runs the full analysis pipeline for a given stock ticker,
    generating the standard detailed HTML report with interactive charts.
    """
    # --- Define the target static directory using app_root ---
    static_dir_path = os.path.join(app_root, 'static')
    os.makedirs(static_dir_path, exist_ok=True)

    stock_csv = macro_csv = processed_csv = report_path = report_html = None
    model = forecast = None

    try:
        print(f"\n----- Starting ORIGINAL pipeline for {ticker} -----")
        # --- Validation for ticker format ---
        # Using a more flexible pattern suitable for general tickers
        valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
             raise ValueError(f"[Original Pipeline] Invalid ticker format: {ticker}.")

        # --- 1. Data Collection ---
        print("Step 1: Fetching stock data...")
        stock_data = fetch_stock_data(ticker)
        if stock_data is None or stock_data.empty:
            raise RuntimeError(f"No stock data found for ticker: {ticker}.")
        stock_csv = os.path.join(static_dir_path, f"{ticker}_raw_data_{ts}.csv")
        stock_data.to_csv(stock_csv, index=False)
        print(f"   Saved raw data -> {os.path.basename(stock_csv)}")

        print("Step 1b: Fetching macroeconomic data...")
        macro_data = fetch_macro_indicators()
        if macro_data is None or macro_data.empty:
            print("Warning: Failed to fetch macroeconomic data. Proceeding without it.")
        else:
            macro_csv = os.path.join(static_dir_path, f"macro_indicators_{ts}.csv")
            macro_data.to_csv(macro_csv, index=False)
            print(f"   Saved macro data -> {os.path.basename(macro_csv)}")

        # --- 2. Data Preprocessing ---
        print("Step 2: Preprocessing data...")
        processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
        if processed_data is None or processed_data.empty:
            raise RuntimeError("Preprocessing resulted in empty dataset.")
        processed_csv = os.path.join(static_dir_path, f"{ticker}_processed_{ts}.csv")
        processed_data.to_csv(processed_csv, index=False)
        print(f"   Saved processed data -> {os.path.basename(processed_csv)}")

        # --- 3. Prophet Model Training & Aggregation ---
        print("Step 3: Training Prophet model & predicting...")
        # Assuming train_prophet_model returns: model, forecast, actual_df, forecast_df
        model, forecast, actual_df, forecast_df = train_prophet_model(
            processed_data, ticker, forecast_horizon='1y', timestamp=ts
        )
        if model is None or forecast is None or actual_df is None or forecast_df is None:
             raise RuntimeError("Prophet model training or forecasting failed.")
        print(f"   Model trained. Forecast generated for {len(forecast_df)} periods.")

        # --- 4. Fetch Fundamentals ---
        print("Step 4: Fetching fundamentals via yfinance...")
        try:
            yf_ticker = yf.Ticker(ticker)
            fundamentals = {
                'info': yf_ticker.info or {},
                'recommendations': yf_ticker.recommendations if hasattr(yf_ticker, 'recommendations') and yf_ticker.recommendations is not None else pd.DataFrame(),
                'news': yf_ticker.news if hasattr(yf_ticker, 'news') and yf_ticker.news is not None else []
            }
            if not fundamentals['info'].get('symbol'):
                 print(f"Warning: Could not fetch detailed info for {ticker} via yfinance.")
        except Exception as yf_err:
             print(f"Warning: Error fetching yfinance fundamentals for {ticker}: {yf_err}.")
             fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': []}

        # --- 5. Generate FULL HTML Report ---
        print("Step 5: Generating FULL HTML report...")
        # --- Call the report generator ---
        report_path, report_html = create_full_report(
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data, fundamentals=fundamentals, ts=ts,
            # aggregation='Monthly', # Aggregation is handled inside report generator now
            app_root=app_root
        )
        if report_html is None or "Error Generating Report" in report_html: # Check for error HTML
            raise RuntimeError(f"Original report generator failed or returned error HTML for {ticker}")
        if report_path:
            print(f"   Report saved -> {os.path.basename(report_path)}")
        else:
            # If path is None but HTML exists, it means saving failed but generation worked
             print(f"   Report HTML generated, but failed to save file.")

        print(f"----- ORIGINAL Pipeline successful for {ticker} -----")
        return model, forecast, report_path, report_html

    except (ValueError, RuntimeError) as err:
        print(f"----- ORIGINAL Pipeline Error for {ticker} -----")
        print(f"Error: {err}")
        traceback.print_exc()
        # Return None for path and HTML on specific errors
        return None, None, None, None
    except Exception as e:
        print(f"----- ORIGINAL Pipeline failure for {ticker} -----")
        print(f"Unexpected Error: {e}")
        traceback.print_exc()
        # Cleanup logic
        for path in {stock_csv, macro_csv, processed_csv, report_path}:
            if path and os.path.exists(path):
                try: os.remove(path)
                except OSError as rm_err: print(f"Error removing file {path}: {rm_err}")
        # Return None for path and HTML on general failure
        return None, None, None, None

# --- WordPress Pipeline Function (FIXED) ---
def run_wp_pipeline(ticker, ts, app_root):
    """
    Runs the analysis pipeline specifically to generate WordPress assets:
    text-only HTML and static chart image relative URLs.
    """
    static_dir_path = os.path.join(app_root, 'static')
    os.makedirs(static_dir_path, exist_ok=True)

    stock_csv = macro_csv = processed_csv = None
    text_report_html = None
    # --- Use a clear variable name for the final URL dictionary ---
    image_urls = {}
    model = forecast = None

    try:
        print(f"\n>>>>> Starting WORDPRESS pipeline for {ticker} <<<<<")
        # --- Use the more flexible validation ---
        valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
             raise ValueError(f"[WP Pipeline] Invalid ticker format: {ticker}.")

        # --- Steps 1-4: Data Fetching, Preprocessing, Model Training, Fundamentals ---
        print("WP Step 1: Fetching stock data...")
        stock_data = fetch_stock_data(ticker)
        if stock_data is None or stock_data.empty: raise RuntimeError(f"No stock data found for {ticker}.")
        stock_csv = os.path.join(static_dir_path, f"{ticker}_wp_raw_data_{ts}.csv")
        stock_data.to_csv(stock_csv, index=False)
        print(f"   Saved WP raw data -> {os.path.basename(stock_csv)}")

        print("WP Step 1b: Fetching macroeconomic data...")
        macro_data = fetch_macro_indicators()
        if macro_data is None or macro_data.empty: print("Warning: Failed to fetch macro data.")
        else:
            macro_csv = os.path.join(static_dir_path, f"wp_macro_indicators_{ts}.csv")
            macro_data.to_csv(macro_csv, index=False)
            print(f"   Saved WP macro data -> {os.path.basename(macro_csv)}")

        print("WP Step 2: Preprocessing data...")
        processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
        if processed_data is None or processed_data.empty: raise RuntimeError("Preprocessing empty.")
        processed_csv = os.path.join(static_dir_path, f"{ticker}_wp_processed_{ts}.csv")
        processed_data.to_csv(processed_csv, index=False)
        print(f"   Saved WP processed data -> {os.path.basename(processed_csv)}")

        print("WP Step 3: Training Prophet model & predicting...")
        # Assuming train_prophet_model returns: model, forecast, actual_df, forecast_df
        model, forecast, actual_df, forecast_df = train_prophet_model(
            processed_data, ticker, forecast_horizon='1y', timestamp=ts
        )
        if model is None or forecast is None or actual_df is None or forecast_df is None:
             raise RuntimeError("Prophet model failed.")
        print(f"   WP Model trained.")

        print("WP Step 4: Fetching fundamentals...")
        try:
            yf_ticker = yf.Ticker(ticker)
            fundamentals = {
                'info': yf_ticker.info or {},
                'recommendations': yf_ticker.recommendations if hasattr(yf_ticker, 'recommendations') and yf_ticker.recommendations is not None else pd.DataFrame(),
                'news': yf_ticker.news if hasattr(yf_ticker, 'news') and yf_ticker.news is not None else []
            }
            if not fundamentals['info'].get('symbol'): print(f"Warning: Could not fetch detailed info for {ticker}.")
        except Exception as yf_err:
             print(f"Warning: Error fetching fundamentals for {ticker}: {yf_err}.")
             fundamentals = {'info': {}, 'recommendations': pd.DataFrame(), 'news': []}

        # --- Step 5: Generate WORDPRESS Assets ---
        print("WP Step 5: Generating WordPress assets (Text HTML + Images)...")
        # --- Assign return values correctly ---
        # The second value returned by create_wordpress_report_assets is the dict of RELATIVE URLs
        text_report_html, image_urls = create_wordpress_report_assets( # Assign to image_urls
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data, fundamentals=fundamentals, ts=ts,
            # aggregation='Monthly', # Aggregation handled inside report generator
            app_root=app_root
        )
        # Check if HTML generation failed
        if text_report_html is None or "Error Generating Report" in text_report_html:
            # Log the error HTML content if possible
            print(f"Error HTML from report generator: {text_report_html}")
            raise RuntimeError(f"WordPress asset generator failed or returned error HTML for {ticker}")

        print(f"   Text HTML generated.")
        # --- Log using the correct variable containing the URLs ---
        print(f"   Chart image URLs generated: {len(image_urls)} URLs returned.") # Log length of image_urls

        print(f">>>>> WORDPRESS Pipeline successful for {ticker} <<<<<")
        # --- Return the CORRECT dictionary containing RELATIVE URLs ---
        return model, forecast, text_report_html, image_urls # Return the image_urls dict

    except (ValueError, RuntimeError) as err:
        print(f">>>>> WORDPRESS Pipeline Error for {ticker} <<<<<")
        print(f"Error: {err}")
        traceback.print_exc()
        # Return None for HTML and empty dict for URLs on specific errors
        return None, None, None, {}
    except Exception as e:
        print(f">>>>> WORDPRESS Pipeline failure for {ticker} <<<<<")
        print(f"Unexpected Error: {e}")
        traceback.print_exc()
        # Cleanup logic
        for path in {stock_csv, macro_csv, processed_csv}:
            if path and os.path.exists(path):
                try: os.remove(path)
                except OSError as rm_err: print(f"Error removing file {path}: {rm_err}")
        # Return None for HTML and empty dict for URLs on general failure
        return None, None, None, {}


if __name__ == "__main__":
    print("Starting batch pipeline execution (Original Reports)...")
    # --- Determine APP_ROOT correctly for standalone execution ---
    APP_ROOT_STANDALONE = os.path.dirname(os.path.abspath(__file__))
    print(f"Running standalone from: {APP_ROOT_STANDALONE}")

    successful_orig, failed_orig = [], []
    successful_wp, failed_wp = [], []

    # --- Run Original Pipeline Batch ---
    print("\n--- Running Original Pipeline Batch ---")
    for ticker in TICKERS:
        ts = str(int(time.time()))
        model, forecast, report_path, report_html = run_pipeline(ticker, ts, APP_ROOT_STANDALONE)
        if report_path and report_html and "Error Generating Report" not in report_html:
            successful_orig.append(ticker)
            print(f"[✔ Orig] {ticker} - Report HTML generated and saved.")
        elif report_html and "Error Generating Report" not in report_html:
            successful_orig.append(f"{ticker} (HTML Only)")
            print(f"[✔ Orig] {ticker} - Report HTML generated (Save Failed).")
        else:
            failed_orig.append(ticker)
            print(f"[✖ Orig] {ticker} - Failed.")
        time.sleep(1) # Add a small delay between tickers if needed

    print("\nBatch Summary (Original Reports):")
    print(f"  Successful: {', '.join(successful_orig) or 'None'}")
    print(f"  Failed:     {', '.join(failed_orig) or 'None'}")

    # --- Run WordPress Pipeline Batch ---
    print("\n--- Running WP Asset Pipeline Batch ---")
    for ticker in TICKERS:
        ts_wp = str(int(time.time()))
        # --- Capture all return values ---
        model_wp, forecast_wp, text_html_wp, img_urls_wp = run_wp_pipeline(ticker, ts_wp, APP_ROOT_STANDALONE)
        # --- Check if BOTH HTML and URLs were generated ---
        if text_html_wp and "Error Generating Report" not in text_html_wp and isinstance(img_urls_wp, dict): # img_urls_wp should be dict
            successful_wp.append(ticker)
            print(f"[✔ WP] {ticker} - Text HTML generated.")
            # Check if URLs were actually generated (dict not empty)
            if img_urls_wp:
                 print(f"[✔ WP] {ticker} - Image URLs generated: {len(img_urls_wp)} URLs -> {list(img_urls_wp.values())}")
            else:
                 print(f"[✔ WP] {ticker} - Image URLs dictionary is empty (Check logs for save errors).")

        else:
            failed_wp.append(ticker)
            print(f"[✖ WP] {ticker} - Failed.")
        time.sleep(1) # Add a small delay

    print("\nBatch Summary (WordPress Assets):")
    print(f"  Successful: {', '.join(successful_wp) or 'None'}")
    print(f"  Failed:     {', '.join(failed_wp) or 'None'}")


    print("\nBatch pipeline execution completed.")