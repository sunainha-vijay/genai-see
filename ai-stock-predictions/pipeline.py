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
        # --- Validation for ticker format (Original had a stricter validation, keeping it for now) ---
        # Note: Original validation might be too strict, consider using the looser one from app.py if needed
        if not ticker or not isinstance(ticker, str) or not ticker.isalpha() or not (1 <= len(ticker) <= 5):
             raise ValueError(f"[Original Pipeline] Invalid ticker format: {ticker}. Must be 1-5 letters.")

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
        # --- Call the ORIGINAL report generator ---
        report_path, report_html = create_full_report(
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data, fundamentals=fundamentals, ts=ts,
            aggregation='Monthly', app_root=app_root
        )
        if report_html is None:
            raise RuntimeError(f"Original report generator failed for {ticker}")
        if report_path:
            print(f"   Report saved -> {os.path.basename(report_path)}")
        else:
            print(f"   Report HTML generated, but failed to save file.")

        print(f"----- ORIGINAL Pipeline successful for {ticker} -----")
        return model, forecast, report_path, report_html

    except (ValueError, RuntimeError) as err:
        print(f"----- ORIGINAL Pipeline Error for {ticker} -----")
        print(f"Error: {err}")
        traceback.print_exc()
        return None, None, None, None
    except Exception as e:
        print(f"----- ORIGINAL Pipeline failure for {ticker} -----")
        print(f"Unexpected Error: {e}")
        traceback.print_exc()
        # Cleanup logic (same as original)
        for path in {stock_csv, macro_csv, processed_csv, report_path}:
            if path and os.path.exists(path):
                try: os.remove(path)
                except OSError as rm_err: print(f"Error removing file {path}: {rm_err}")
        return None, None, None, None

# --- NEW Pipeline Function for WordPress Assets ---
def run_wp_pipeline(ticker, ts, app_root):
    """
    Runs the analysis pipeline specifically to generate WordPress assets:
    text-only HTML and static chart image paths.
    """
    static_dir_path = os.path.join(app_root, 'static')
    os.makedirs(static_dir_path, exist_ok=True)

    stock_csv = macro_csv = processed_csv = None
    text_report_html = None
    chart_image_paths = {}
    model = forecast = None

    try:
        print(f"\n>>>>> Starting WORDPRESS pipeline for {ticker} <<<<<")
        # --- Use the more flexible validation from app.py ---
        valid_ticker_pattern = r'^[A-Z0-9\^.-]+$'
        if not ticker or not re.match(valid_ticker_pattern, ticker):
             raise ValueError(f"[WP Pipeline] Invalid ticker format: {ticker}.")

        # --- Steps 1-4: Data Fetching, Preprocessing, Model Training, Fundamentals ---
        # These steps are identical to the original pipeline
        print("WP Step 1: Fetching stock data...")
        stock_data = fetch_stock_data(ticker)
        if stock_data is None or stock_data.empty: raise RuntimeError(f"No stock data found for {ticker}.")
        stock_csv = os.path.join(static_dir_path, f"{ticker}_wp_raw_data_{ts}.csv") # Use diff name? Optional
        stock_data.to_csv(stock_csv, index=False)
        print(f"   Saved WP raw data -> {os.path.basename(stock_csv)}")

        print("WP Step 1b: Fetching macroeconomic data...")
        macro_data = fetch_macro_indicators()
        if macro_data is None or macro_data.empty: print("Warning: Failed to fetch macro data.")
        else:
            macro_csv = os.path.join(static_dir_path, f"wp_macro_indicators_{ts}.csv") # Optional diff name
            macro_data.to_csv(macro_csv, index=False)
            print(f"   Saved WP macro data -> {os.path.basename(macro_csv)}")

        print("WP Step 2: Preprocessing data...")
        processed_data = preprocess_data(stock_data, macro_data if macro_data is not None else None)
        if processed_data is None or processed_data.empty: raise RuntimeError("Preprocessing empty.")
        processed_csv = os.path.join(static_dir_path, f"{ticker}_wp_processed_{ts}.csv") # Optional diff name
        processed_data.to_csv(processed_csv, index=False)
        print(f"   Saved WP processed data -> {os.path.basename(processed_csv)}")

        print("WP Step 3: Training Prophet model & predicting...")
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
        # --- Call the NEW report generator function ---
        text_report_html, chart_image_paths = create_wordpress_report_assets(
            ticker=ticker, actual_data=actual_df, forecast_data=forecast_df,
            historical_data=processed_data, fundamentals=fundamentals, ts=ts,
            aggregation='Monthly', app_root=app_root
        )
        if text_report_html is None:
            raise RuntimeError(f"WordPress asset generator failed for {ticker}")

        print(f"   Text HTML generated.")
        print(f"   Chart images saved: {len(chart_image_paths)} paths returned.")

        print(f">>>>> WORDPRESS Pipeline successful for {ticker} <<<<<")
        # Return the generated text HTML and the dictionary of image paths
        return model, forecast, text_report_html, chart_image_paths

    except (ValueError, RuntimeError) as err:
        print(f">>>>> WORDPRESS Pipeline Error for {ticker} <<<<<")
        print(f"Error: {err}")
        traceback.print_exc()
        # Return expected tuple format on failure
        return None, None, None, None
    except Exception as e:
        print(f">>>>> WORDPRESS Pipeline failure for {ticker} <<<<<")
        print(f"Unexpected Error: {e}")
        traceback.print_exc()
        # Cleanup logic (you might want separate WP temp files if names differ)
        for path in {stock_csv, macro_csv, processed_csv}: # Don't clean image files on general failure
            if path and os.path.exists(path):
                try: os.remove(path)
                except OSError as rm_err: print(f"Error removing file {path}: {rm_err}")
        return None, None, None, None


if __name__ == "__main__":
    print("Starting batch pipeline execution (Original Reports)...")
    APP_ROOT_STANDALONE = os.path.dirname(os.path.abspath(__file__))
    print(f"Running standalone from: {APP_ROOT_STANDALONE}")

    successful, failed = [], []
    for ticker in TICKERS:
        ts = str(int(time.time()))
        # --- Run the original pipeline ---
        model, forecast, report_path, report_html = run_pipeline(ticker, ts, APP_ROOT_STANDALONE)
        if report_html:
            successful.append(ticker)
            print(f"[✔ Orig] {ticker} - Report HTML generated.")
        else:
            failed.append(ticker)
            print(f"[✖ Orig] {ticker}")

    print("\nBatch Summary (Original Reports):")
    print(f"  Successful: {', '.join(successful) or 'None'}")
    print(f"  Failed:     {', '.join(failed) or 'None'}")

    # --- Example: Running the WP pipeline for one ticker ---
    if TICKERS:
        print("\n--- Example: Running WP Asset Pipeline ---")
        ticker_wp = TICKERS[0]
        ts_wp = str(int(time.time()))
        _, _, text_html, img_paths = run_wp_pipeline(ticker_wp, ts_wp, APP_ROOT_STANDALONE)
        if text_html:
            print(f"[✔ WP] {ticker_wp} - Text HTML generated.")
            print(f"[✔ WP] {ticker_wp} - Image paths generated: {img_paths}")
        else:
            print(f"[✖ WP] {ticker_wp} - Failed.")

    print("\nBatch pipeline execution completed.")