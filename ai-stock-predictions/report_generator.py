# report_generator.py
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
import os
import numpy as np
from datetime import datetime, timedelta
import pytz
import json # Import json for potential future use with data attributes

# Import functions from helper modules
from technical_analysis import (
    plot_historical_line_chart, plot_price_bollinger, plot_rsi,
    plot_macd_lines, plot_macd_histogram, calculate_detailed_ta, get_macd_conclusion
)
from html_components import (
    generate_metrics_summary_html, generate_risk_analysis_html,
    generate_monthly_forecast_table_html, generate_tech_analysis_summary_html,
    generate_overall_conclusion_html, generate_faq_html, generate_final_notes_html,
    generate_profile_html, generate_valuation_metrics_html, generate_financial_health_html,
    generate_profitability_html, generate_dividends_splits_html,
    generate_analyst_info_html, generate_news_html
)
from fundamental_analysis import (
    extract_company_profile, extract_valuation_metrics, extract_financial_health,
    extract_profitability, extract_dividends_splits, extract_analyst_info,
    extract_news, safe_get
)

# --- Shared CSS (used by both report types) ---
# Define CSS within the module scope to be accessible by both functions
custom_style = """
<style>
  /* --- Base & General --- */
  html { scroll-behavior: smooth; }
  body {
     font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
     color: #333;
     line-height: 1.6;
     background-color: #ffffff;
     margin: 0;
     padding: 0;
     font-size: 15px;
     -webkit-text-size-adjust: 100%;
     text-size-adjust: 100%;
     overflow-x: hidden;
  }
  /* Report Container */
  .report-container {
      max-width: 1200px;
      margin: 1rem auto;
      padding: 1rem 2rem;
      background: #ffffff;
      overflow-x: hidden;
      padding-bottom: 3rem;
    }
  .report-title { text-align: center; color: #2c3e50; margin: 0 0 2rem 0; font-size: 2.4rem; font-weight: 700; border-bottom: 1px solid #dee2e6; padding-bottom: 1rem;}
  .section { margin-bottom: 2.5rem; padding: 0; background-color: #fff; border-radius: 8px; }
  .section h2 { color: #34495e; border-bottom: 2px solid #e9ecef; padding-bottom: 0.6rem; margin: 0 0 1.5rem 0; font-size: 1.6rem; font-weight: 600;}
  .section h3 { font-size: 1.2rem; color: #34495e; margin: 1.5rem 0 1rem 0; padding-bottom: 0.4rem; border-bottom: 1px solid #ecf0f1; }
  .section h4 { font-size: 1.1rem; color: #495057; margin: 1rem 0 0.5rem 0; }
  .report-container p { font-size: 1rem; line-height: 1.7; color: #495057; margin: 0 0 1rem 0; }
  .report-container a { color: #3498db; text-decoration: none; } .report-container a:hover { text-decoration: underline; }
  .report-container strong { font-weight: 600; color: #2c3e50; }
  .disclaimer { font-size: 0.9rem; color: #6c757d; font-style: italic; margin-top: 1.5rem; padding: 1rem; background-color: #f8f9fa; border-left: 4px solid #adb5bd; border-radius: 4px;}
  .narrative { margin-bottom: 1.5rem; padding: 1rem 1.2rem; background-color: #eef5f9; border-left: 4px solid #5dade2; border-radius: 4px; font-size: 0.95rem; }
  .narrative ul { margin-top: 0.5rem; margin-bottom: 0.5rem; padding-left: 20px;} .narrative li { margin-bottom: 0.5rem;}
  .icon { margin-right: 0.6em; font-size: 1em; display: inline-block; width: 1.2em; text-align: center; vertical-align: middle; }
  .icon-up { color: #28a745; } .icon-down { color: #dc3545; } .icon-neutral { color: #6c757d; }
  .icon-warning { color: #ffc107; } .icon-positive { color: #28a745; } .icon-negative { color: #dc3545; }
  .icon-info { color: #17a2b8; }
  .metrics-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .metric-item { background-color: #f8f9fa; padding: 0.8rem 1rem; border-radius: 6px; text-align: center; border: 1px solid #dee2e6; }
  .metric-label { display: block; font-size: 0.75rem; color: #6c757d; margin-bottom: 0.4rem; text-transform: uppercase; font-weight: 500; }
  .metric-value { display: block; font-size: 1.2rem; font-weight: 600; color: #343a40; line-height: 1.2; word-wrap: break-word; }
  .metric-change { font-size: 0.85rem; font-weight: normal; margin-left: 0.2rem; display: inline-block; }
  .sentiment-bullish, .action-buy, .trend-up { color: #28a745 !important; } .sentiment-strong-bullish { color: #208a38 !important; font-weight: bold; }
  .sentiment-bearish, .action-short, .trend-down { color: #dc3545 !important; } .sentiment-strong-bearish { color: #c82333 !important; font-weight: bold; }
  .sentiment-neutral, .action-hold, .trend-neutral { color: #6c757d !important; }
  .profile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem 1.5rem; margin-bottom: 1.5rem; }
  .profile-item { word-wrap: break-word; }
  .profile-item span { font-weight: 600; margin-right: 0.5rem; color: #495057; }
  .business-summary { margin-top: 1rem; } .business-summary h4 { margin-bottom: 0.5rem; color: #34495e; }
  .metrics-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
  .metrics-table td { padding: 0.9rem 0.5rem; border-bottom: 1px solid #dee2e6; font-size: 0.95rem; vertical-align: top;}
  .metrics-table tr:last-child td { border-bottom: none; } .metrics-table td:first-child { font-weight: 500; color: #495057; width: 40%; word-break: break-word; white-space: normal; }
  .metrics-table td:last-child { text-align: right; font-weight: 600; color: #343a40; white-space: nowrap;}
  .analyst-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; }
  .analyst-item { background-color: #f8f9fa; padding: 0.8rem 1rem; border-radius: 4px; border: 1px solid #dee2e6; font-size: 0.9rem;}
  .analyst-item span { font-weight: 600; margin-right: 0.3rem; color: #495057; }
  .table-container { overflow-x: auto; margin-top: 1rem; border: 1px solid #dee2e6; border-radius: 6px; -webkit-overflow-scrolling: touch; }
  .report-container table { width: 100%; border-collapse: collapse; }
  .report-container th, .report-container td { padding: 0.9rem 1.1rem; text-align: left; border-bottom: 1px solid #dee2e6; font-size: 0.95rem; white-space: nowrap; }
  .report-container th { background-color: #e9ecef; color: #495057; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; border-bottom-width: 2px; }
  .report-container tbody tr:nth-child(even) { background-color: #f8f9fa; } .report-container tbody tr:hover { background-color: #e9ecef; }
  .report-container td:nth-child(n+2):not(:last-child) { text-align: right; } .report-container td:last-child { text-align: center; } .report-container td[class^='action-'] { font-weight: bold; }
  .risk-analysis ul { list-style: none; padding-left: 0; margin-top: 1rem; }
  .risk-analysis li { background-color: #fff3cd; border-left: 5px solid #ffc107; color: #856404; padding: 0.9rem 1.2rem; margin-bottom: 0.8rem; border-radius: 4px; font-size: 0.95rem; display: flex; align-items: flex-start; }
  .risk-analysis li .icon { font-size: 1.1em; margin-right: 0.8em; margin-top: 0.1em; color: #ffc107; flex-shrink: 0; }
  .tech-analysis h4 { margin-top: 1.5rem; margin-bottom: 0.8rem; color: #34495e; font-size: 1.1rem; padding-bottom: 0.3rem; border-bottom: 1px solid #dee2e6; }
  .sentiment-indicator { margin-bottom: 1.5rem; font-size: 1.1rem; padding: 1rem; background-color:#f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; text-align: center;}
  .sentiment-indicator span:first-child { margin-right: 0.5rem; font-weight: 500;}
  .ma-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
  .ma-item { background: #f8f9fa; padding: 0.8rem 1rem; border-radius: 6px; font-size: 0.95rem; border: 1px solid #dee2e6;}
  .ma-item .label { font-weight: 600; margin-right: 0.5rem;} .ma-item .value { font-weight: 500; } .ma-item .status { font-size: 0.85rem; margin-left: 0.4rem; font-style: italic;}
  /* --- START: Updated Graph Container Styles (for original report) --- */
  .indicator-chart-container { background-color: #ffffff; padding: 0; margin-bottom: 0.5rem; border-radius: 8px; border: 1px solid #dee2e6; width: 100%; max-width: 100%; position: relative; overflow: hidden; }
  .indicator-conclusion { padding: 1.2rem 1.5rem; margin-top: 0; border-top: 1px solid #dee2e6; font-size: 0.95rem; line-height: 1.6; color: #495057; background-color: #f8f9fa; border-radius: 0 0 8px 8px; margin-bottom: 1.5rem; }
  .plotly-graph-div { margin: 0 auto !important; width: 100% !important; height: 100% !important; position: relative; }
  .modebar { position: absolute !important; top: 2px !important; left: 50% !important; transform: translateX(-50%) !important; width: auto !important; max-width: calc(100% - 10px) !important; display: flex !important; flex-wrap: wrap !important; justify-content: center !important; background-color: rgba(245, 245, 245, 0.9) !important; border: 1px solid #ccc !important; border-radius: 4px !important; padding: 3px 5px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important; opacity: 1 !important; z-index: 1001 !important; transition: none !important; }
  .plotly-graph-div .legend { /* Removed legend styling - handled by Plotly layout now */ }
  /* --- END: Updated Graph Container Styles --- */
  .overall-conclusion .conclusion-columns { display: flex; flex-wrap: wrap; gap: 2.5rem; margin: 1.5rem 0; padding: 1.5rem; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;}
  .overall-conclusion .conclusion-column { flex: 1; min-width: 300px; }
  .overall-conclusion h3 { font-size: 1.2rem; color: #34495e; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid #ced4da; }
  .overall-conclusion ul { list-style: none; padding-left: 0; margin-top: 0; }
  .overall-conclusion li { margin-bottom: 1rem; font-size: 0.95rem; line-height: 1.6; display: flex; align-items: flex-start; padding-left: 0; }
  .overall-conclusion li .icon { margin-right: 0.8em; margin-top: 0.15em; flex-shrink: 0; width: 1.2em; text-align: center; font-size: 1.1em; }
  .overall-conclusion li > span:last-child { flex-grow: 1; }
  .news-container { margin-top: 1rem; }
  .news-item { padding: 1rem 0; border-bottom: 1px solid #e9ecef; margin-bottom: 0; background-color: transparent;}
  .news-item:last-child { border-bottom: none; }
  .news-item h4 { margin: 0 0 0.3rem 0; font-size: 1.05rem; font-weight: 600;}
  .news-item h4 a { color: #0056b3; } .news-item h4 a:hover { color: #003d7a; }
  .news-meta { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; color: #6c757d; font-size: 0.85rem; margin: 0.5rem 0 0 0; }
  .news-meta span { background-color: #e9ecef; padding: 0.1rem 0.5rem; border-radius: 3px; }
  .faq details { border: 1px solid #dee2e6; border-radius: 6px; margin-bottom: 1rem; background: #fff; transition: background-color 0.2s ease;}
  .faq details[open] { background-color: #f8f9fa; }
  .faq summary { padding: 1rem 1.2rem; font-weight: 600; cursor: pointer; background-color: transparent; border-radius: 6px; outline: none; position: relative; color: #34495e; display: block; transition: background-color 0.2s ease;}
  .faq details[open] summary { background-color: #e9ecef; border-bottom: 1px solid #dee2e6; border-radius: 6px 6px 0 0; }
  .faq summary::marker { content: ""; } /* Hide default marker */
  .faq summary::after { content: '+'; position: absolute; right: 1.2rem; top: 50%; transform: translateY(-50%); font-size: 1.5rem; color: #adb5bd; transition: transform 0.2s ease-in-out, color 0.2s ease;}
  .faq details[open] summary::after { content: '−'; transform: translateY(-50%) rotate(180deg); color: #3498db;}
  .faq details p { padding: 1.5rem 1.2rem; margin: 0; border-top: 1px solid #dee2e6; border-radius: 0 0 6px 6px; background-color: #fff;}
  .faq details[open] p { border-top: none; }
  .general-info { padding: 1.5rem; background-color: #f8f9fa; border-radius: 8px; border-top: 1px solid #dee2e6; margin-top: 2rem;}
  .general-info p { margin-bottom: 0.5rem; font-size: 0.9rem; color: #6c757d; }
  .general-info .disclaimer { margin-top: 1rem; padding: 1rem; background-color: #e9ecef; border-left-color: #6c757d; font-size: 0.85rem; }
  /* --- Responsive Adjustments --- */
  @media (max-width: 992px) {
      body { font-size: 14px; }
      .report-container { padding: 1rem 1.5rem; padding-bottom: 2rem; }
      .report-title { font-size: 2rem; }
      .section h2 { font-size: 1.4rem; }
      .report-container p { font-size: 0.95rem; }
      .metric-item { padding: 0.7rem 0.9rem; }
      .metric-value { font-size: 1.1rem; }
      .report-container th, .report-container td { padding: 0.8rem 0.9rem; font-size: 0.9rem; }
      .overall-conclusion .conclusion-columns { gap: 1.5rem; }
      .overall-conclusion .conclusion-column { min-width: unset; }
      .plotly-graph-div { min-height: 280px; }
  }
  @media (max-width: 768px) {
      body { font-size: 14px; }
      .report-container { padding: 1rem 1rem; padding-bottom: 2rem; margin: 0.5rem auto; }
      .report-title { font-size: 1.8rem; margin-bottom: 1.5rem; }
      .section { margin-bottom: 2rem; }
      .section h2 { font-size: 1.3rem; margin-bottom: 1rem; }
      .section h3 { font-size: 1.1rem; }
      .section h4 { font-size: 1rem; }
      .report-container p { font-size: 0.9rem; line-height: 1.6; }
      .metrics-summary { grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 0.8rem; }
      .metric-item { padding: 0.6rem 0.8rem; }
      .metric-value { font-size: 1rem; }
      .metric-label { font-size: 0.7rem; }
      .profile-grid { grid-template-columns: 1fr; }
      .metrics-table td:first-child { width: 35%; }
      .table-container { margin-top: 0.8rem; }
      .report-container th, .report-container td { font-size: 0.85rem; padding: 0.7rem 0.8rem; }
      .risk-analysis li { font-size: 0.9rem; padding: 0.7rem 1rem; }
      .overall-conclusion .conclusion-columns { flex-direction: column; gap: 1.5rem; padding: 1rem; }
      .overall-conclusion h3 { font-size: 1.1rem; }
      .overall-conclusion li { font-size: 0.9rem; }
      .faq summary { padding: 0.8rem 1rem; font-size: 0.95rem; }
      .faq details p { padding: 1rem; font-size: 0.9rem; }
      .disclaimer { font-size: 0.85rem; padding: 0.8rem; }
      .narrative { font-size: 0.9rem; padding: 0.8rem 1rem; }
      .analyst-grid { grid-template-columns: 1fr; }
      .ma-summary { grid-template-columns: 1fr; }
      .plotly-graph-div { min-height: 250px; padding-bottom: 50px; /* Padding for legend */ }
      .indicator-conclusion { font-size: 0.9rem; }
      .modebar-btn { min-width: 22px; height: 22px; line-height: 18px; }
      .modebar-btn svg { width: 13px; height: 13px; }
  }
  @media (max-width: 480px) {
      body { font-size: 13px; }
      .report-container { padding: 0.5rem; padding-bottom: 1.5rem; }
      .report-title { font-size: 1.5rem; }
      .section h2 { font-size: 1.2rem; }
      .report-container p { font-size: 0.85rem; }
      .report-container th, .report-container td { font-size: 0.75rem; padding: 0.5rem 0.6rem; white-space: normal; /* Allow wrapping */ }
      .report-container td:last-child { text-align: left; }
      .metrics-summary { grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 0.4rem; }
      .metric-item { padding: 0.4rem 0.5rem; }
      .metric-value { font-size: 0.85rem; }
      .metric-label { font-size: 0.6rem; }
      .risk-analysis li { font-size: 0.85rem; padding: 0.6rem 0.9rem; }
      .overall-conclusion li { font-size: 0.85rem; }
      .faq summary { font-size: 0.9rem; }
      .faq details p { font-size: 0.85rem; }
      .disclaimer { font-size: 0.8rem; }
      .narrative { font-size: 0.85rem; }
      .modebar { padding: 2px; }
      .modebar-btn { min-width: 20px; height: 20px; line-height: 16px; }
      .modebar-btn svg { width: 11px; height: 11px; }
      .plotly-graph-div { min-height: 230px; padding-bottom: 60px; /* More padding for legend */ }
      .plotly-graph-div .legend { font-size: 0.8em; }
      .indicator-conclusion { font-size: 0.85rem; }
  }
</style>
"""

# Helper function to determine sentiment (modified to use detailed_ta_data)
def determine_sentiment(detailed_ta_data, overall_pct_change):
    """Determines sentiment based on detailed TA data and forecast trend."""
    current_price = detailed_ta_data.get('Current_Price')
    sma_50 = detailed_ta_data.get('SMA_50')
    sma_200 = detailed_ta_data.get('SMA_200')
    rsi = detailed_ta_data.get('RSI_14') # Use RSI_14 from detailed data

    if current_price is None: return "N/A"

    score = 0
    # Forecast Trend
    if overall_pct_change > 5: score += 1.5
    elif overall_pct_change > 1: score += 0.5
    elif overall_pct_change < -5: score -= 1.5
    elif overall_pct_change < -1: score -= 0.5

    # Price vs SMAs
    if sma_50 is not None and current_price > sma_50: score += 0.5
    elif sma_50 is not None and current_price < sma_50: score -= 0.5
    if sma_200 is not None and current_price > sma_200: score += 1.0
    elif sma_200 is not None and current_price < sma_200: score -= 1.0

    # SMA Crossover (Golden/Death Cross approximation)
    if sma_50 is not None and sma_200 is not None:
        if sma_50 > sma_200: score += 0.5 # 50 above 200 is bullish
        else: score -= 0.5 # 50 below 200 is bearish

    # RSI Level
    if rsi is not None and not pd.isna(rsi):
        if rsi > 65: score -= 0.25 # Slightly bearish if high RSI (potential reversal)
        elif rsi < 35: score += 0.25 # Slightly bullish if low RSI (potential reversal)

    # Determine Sentiment String
    if score >= 2.5: return "Strong Bullish"
    elif score >= 1.0: return "Bullish"
    elif score <= -2.5: return "Strong Bearish"
    elif score <= -1.0: return "Bearish"
    else: return "Neutral"
    pass

# --- Helper function to safely write images ---
def _write_plotly_image(fig, path, fallback_msg="Chart could not be generated."):
    """Writes a Plotly figure to an image file, handling errors."""
    if fig is None:
        print(f"Warning: Figure is None, cannot save image to {path}.")
        return None
    try:
        # Use scale parameter for higher resolution if needed, e.g., scale=2
        fig.write_image(path)
        print(f"Saved chart image to: {os.path.basename(path)}")
        return path
    except Exception as img_err:
        print(f"Error saving chart image to {os.path.basename(path)}: {img_err}")
        # Optionally, create a fallback placeholder image or just return None
        return None


# --- Original Report Generation Function (Unchanged) ---
def create_full_report(
    ticker,
    actual_data,
    forecast_data,
    historical_data,
    fundamentals,
    ts,
    aggregation=None,
    app_root=None,
    plot_period_years=3
):
    """
    Generates a detailed HTML stock analysis report with embedded Plotly charts.
    (Original function kept for existing functionality)
    """
    global custom_style # Access the CSS defined at module level
    print(f"[Original Report] Starting generation for {ticker}...")

    # Determine the static directory path
    if app_root is None:
        print("[Original Report] Warning: app_root not provided. Assuming relative path './static'")
        static_dir = 'static'
    else:
        static_dir = os.path.join(app_root, 'static')
    os.makedirs(static_dir, exist_ok=True)
    print(f"[Original Report] Static directory: {static_dir}")

    # --- Data Validation and Preparation (Same as original) ---
    required_hist_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    if historical_data is None or historical_data.empty:
         raise ValueError("[Original Report] Historical data is missing or empty.")
    if not all(col in historical_data.columns for col in required_hist_cols):
        missing_cols_str = ', '.join([col for col in required_hist_cols if col not in historical_data.columns])
        raise ValueError(f"[Original Report] Historical data missing required columns: {missing_cols_str}")
    if not isinstance(historical_data['Date'].iloc[0], pd.Timestamp):
         try: historical_data['Date'] = pd.to_datetime(historical_data['Date'])
         except Exception as e: raise ValueError(f"[Original Report] Historical data 'Date' column error: {e}")
    historical_data = historical_data.sort_values('Date').reset_index(drop=True)
    hist_data_for_ta = historical_data.copy()

    # --- Determine time column and label (Same as original) ---
    time_col = "Period"; period_label = "Period" # Default
    if forecast_data is not None and not forecast_data.empty and "Period" in forecast_data.columns:
        first_period = str(forecast_data['Period'].iloc[0])
        if len(first_period) == 7 and '-' in first_period: period_label = "Month"
        elif len(first_period) == 7 and '-' not in first_period : period_label = "Week"
        elif len(first_period) == 10: period_label = "Day"
    elif actual_data is not None and not actual_data.empty and "Period" in actual_data.columns:
         first_period = str(actual_data['Period'].iloc[0])
         if len(first_period) == 7 and '-' in first_period: period_label = "Month"
         elif len(first_period) == 7 and '-' not in first_period : period_label = "Week"
         elif len(first_period) == 10: period_label = "Day"

    # --- Calculate Detailed TA Data (Same as original) ---
    print("[Original Report] Calculating detailed technical analysis data...")
    detailed_ta_data = calculate_detailed_ta(hist_data_for_ta)

    # --- Calculate Key Metrics (Same as original) ---
    print("[Original Report] Calculating key metrics...")
    current_price = detailed_ta_data.get('Current_Price')
    last_date = historical_data['Date'].iloc[-1] if not historical_data.empty else datetime.now(pytz.utc)
    volatility = None; green_days = None; total_days = 0
    if len(historical_data) > 1:
        last_30_days_df = historical_data.iloc[-min(30, len(historical_data)):]
        if len(last_30_days_df) > 1:
            daily_returns = last_30_days_df['Close'].pct_change().dropna()
            if not daily_returns.empty: volatility = daily_returns.std() * np.sqrt(252) * 100
            price_diff = last_30_days_df['Close'].diff().dropna()
            green_days = (price_diff > 0).sum(); total_days = len(price_diff)
    sma50 = detailed_ta_data.get('SMA_50'); sma200 = detailed_ta_data.get('SMA_200')
    latest_rsi = detailed_ta_data.get('RSI_14')
    forecast_horizon_periods = 0; forecast_12m = pd.DataFrame(); final_forecast_average = None; forecast_1m = None
    if forecast_data is not None and not forecast_data.empty and 'Average' in forecast_data.columns:
        forecast_horizon_periods = min(len(forecast_data), 12)
        forecast_12m = forecast_data.head(forecast_horizon_periods)
        if not forecast_12m.empty:
            final_forecast_average = forecast_12m['Average'].iloc[-1]
            forecast_1m = forecast_data['Average'].iloc[0] if len(forecast_data) > 0 else None
    overall_pct_change = 0.0
    if current_price is not None and final_forecast_average is not None and current_price != 0:
        overall_pct_change = ((final_forecast_average - current_price) / current_price) * 100
    sentiment = determine_sentiment(detailed_ta_data, overall_pct_change)

    # --- Prepare Data for Tables (Same as original) ---
    print("[Original Report] Preparing forecast table data...")
    monthly_forecast_table_data = forecast_12m.copy()
    if not monthly_forecast_table_data.empty and current_price is not None and current_price != 0:
        if 'Average' in monthly_forecast_table_data.columns:
            monthly_forecast_table_data['Potential ROI'] = ((monthly_forecast_table_data['Average'] - current_price) / current_price) * 100
            monthly_forecast_table_data['Action'] = monthly_forecast_table_data['Potential ROI'].apply( lambda x: 'Buy' if x > 2 else ('Short' if x < -2 else 'Hold'))
        else:
            monthly_forecast_table_data['Potential ROI'] = 0.0; monthly_forecast_table_data['Action'] = 'N/A'
    elif not monthly_forecast_table_data.empty:
         monthly_forecast_table_data['Potential ROI'] = 0.0; monthly_forecast_table_data['Action'] = 'N/A'

    # --- Generate Plotly Figures and HTML (Same as original) ---
    print("[Original Report] Generating plots...")
    def fig_to_html(fig, include_plotlyjs=True, full_html=False, div_id=None, config=None):
        if fig is None: return ""
        default_config = {'displayModeBar': True, 'displaylogo': False, 'responsive': True}
        merged_config = default_config.copy();
        if config: merged_config.update(config)
        try:
             # include_plotlyjs='cdn' is efficient for multiple plots
             return to_html(fig, include_plotlyjs='cdn', full_html=full_html, div_id=div_id, config=merged_config)
        except Exception as e:
             print(f"[Original Report] Error converting figure to HTML: {e}")
             return f'<p style="color:red;">Error rendering plot: {e}</p>'

    # --- Forecast Chart (Same as original) ---
    forecast_chart_fig = go.Figure()
    # ... (rest of forecast chart fig generation logic is identical to original) ...
    display_actual_renamed = actual_data.tail(6).rename(columns={time_col: 'TimeColumn'}) if actual_data is not None and time_col in actual_data else pd.DataFrame()
    forecast_12m_renamed = forecast_12m.rename(columns={time_col: 'TimeColumn'}) if forecast_12m is not None and time_col in forecast_12m else pd.DataFrame()
    time_axis_parts = []
    if not display_actual_renamed.empty: time_axis_parts.append(display_actual_renamed['TimeColumn'])
    if not forecast_12m_renamed.empty: time_axis_parts.append(forecast_12m_renamed['TimeColumn'])
    try: combined_time_axis = sorted(list(pd.concat(time_axis_parts).unique())) if time_axis_parts else []
    except TypeError: combined_time_axis = list(pd.concat(time_axis_parts).unique()) if time_axis_parts else []
    if not display_actual_renamed.empty and 'Average' in display_actual_renamed.columns:
        forecast_chart_fig.add_trace( go.Scatter(x=display_actual_renamed['TimeColumn'], y=display_actual_renamed['Average'], mode='lines+markers', name='Actual', line=dict(color='#1f77b4', width=2), marker=dict(size=6), hovertemplate=f"<b>%{{x}} ({period_label})</b><br><b>Actual Avg</b>: %{{y:.2f}}<extra></extra>"))
    if not forecast_12m_renamed.empty:
        colors = {'Low': '#d62728', 'Average': '#2ca02c', 'High': '#9467bd'}
        plot_cols = ['Low', 'Average', 'High'] if all(c in forecast_12m_renamed for c in ['Low', 'Average', 'High']) else ['Average']
        for col in plot_cols:
            forecast_chart_fig.add_trace(go.Scatter(x=forecast_12m_renamed['TimeColumn'], y=forecast_12m_renamed[col], mode='lines+markers', name=f'Fcst {col}', line=dict(color=colors[col], width=2), marker=dict(size=6, line=dict(width=1, color='#ffffff')), hovertemplate=f"<b>%{{x}} ({period_label})</b><br><b>{col}</b>: %{{y:.2f}}<extra></extra>"))
        if final_forecast_average is not None and 'Average' in forecast_12m_renamed.columns:
             annotation_text = (f"<b>{final_forecast_average:.2f}</b><br><span style='color:{colors['Average']};'>{overall_pct_change:+.1f}% ({forecast_horizon_periods} {period_label}s)</span>")
             last_time_period = forecast_12m_renamed['TimeColumn'].iloc[-1]
             forecast_chart_fig.add_annotation(x=last_time_period, y=final_forecast_average, text=annotation_text, showarrow=True, arrowhead=2, ax=30, ay=-30, bgcolor='rgba(255,255,255,0.8)', font=dict(color=colors['Average'], size=10), bordercolor='black', borderwidth=1)
    forecast_chart_fig.update_layout(
        title=dict(text=f"{ticker} {forecast_horizon_periods}-{period_label} Forecast", y=0.98, x=0.5, xanchor='center', yanchor='top', font_size=14),
        legend=dict(orientation="h", yanchor="top", y=0.92, xanchor="center", x=0.5, font_size=10),
        xaxis=dict(title=period_label, type="category", categoryorder='array', categoryarray=combined_time_axis, tickangle=-45, tickformat="%b %Y", tickfont_size=10, domain=[0, 1], automargin=True),
        yaxis_title="Price ($)", yaxis=dict(domain=[0, 0.85], tickfont_size=10, automargin=True),
        margin=dict(l=35, r=25, t=80, b=40), autosize=True, template="plotly_white", showlegend=True
    )
    # --- Generate HTML FOR the chart ---
    forecast_chart_html = fig_to_html(forecast_chart_fig, div_id='forecast-chart-div')

    # --- Technical Analysis Charts HTML (Same as original) ---
    historical_line_fig = plot_historical_line_chart(historical_data.copy(), ticker)
    historical_chart_html = fig_to_html(historical_line_fig, div_id='hist-chart-div') # Use False to avoid repeating Plotly.js
    bb_fig, bb_conclusion = plot_price_bollinger(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    bb_chart_html = fig_to_html(bb_fig, div_id='bb-chart-div')
    rsi_fig, rsi_conclusion = plot_rsi(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    rsi_chart_html = fig_to_html(rsi_fig, div_id='rsi-chart-div')
    macd_conclusion = get_macd_conclusion(detailed_ta_data.get('MACD_Line'), detailed_ta_data.get('MACD_Signal'), detailed_ta_data.get('MACD_Hist'), detailed_ta_data.get('MACD_Hist_Prev')) if detailed_ta_data.get('MACD_Hist') is not None else "MACD conclusion requires more data."
    macd_lines_fig, _ = plot_macd_lines(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    macd_lines_chart_html = fig_to_html(macd_lines_fig, div_id='macd-lines-chart-div')
    macd_hist_fig, _ = plot_macd_histogram(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    macd_hist_chart_html = fig_to_html(macd_hist_fig, div_id='macd-hist-chart-div')

    # --- Extract Fundamental Data (Same as original) ---
    print("[Original Report] Extracting fundamental data...")
    profile = extract_company_profile(fundamentals); valuation = extract_valuation_metrics(fundamentals)
    financial_health = extract_financial_health(fundamentals); profitability = extract_profitability(fundamentals)
    dividends = extract_dividends_splits(fundamentals); analyst_info = extract_analyst_info(fundamentals)
    news_list = extract_news(fundamentals)

    # --- Generate HTML Components (Same as original) ---
    print("[Original Report] Generating HTML components...")
    metrics_summary_html = generate_metrics_summary_html( ticker, current_price, forecast_1m, final_forecast_average, overall_pct_change, sentiment, volatility, green_days, total_days, sma50, sma200, period_label)
    # ... (risk_items calculation is identical to original) ...
    risk_items = []
    if sentiment.lower().find('bearish') != -1: risk_items.append(f"Overall technical sentiment is {sentiment}.")
    if volatility is not None and volatility > 40: risk_items.append(f"High annualized volatility ({volatility:.1f}%) suggests potentially large price swings.")
    if sma50 is not None and current_price is not None and current_price < sma50: risk_items.append("Price below the 50-Day SMA (short-term weakness).")
    if sma200 is not None and current_price is not None and current_price < sma200: risk_items.append("Price below the 200-Day SMA (long-term weakness).")
    if overall_pct_change < -5: risk_items.append(f"Negative {forecast_horizon_periods}-{period_label} forecast trend ({overall_pct_change:+.1f}%).")
    if latest_rsi is not None and not pd.isna(latest_rsi) and latest_rsi > 70: risk_items.append(f"RSI ({latest_rsi:.1f}) is high (>70), potential overbought condition.")
    pe_value_str = valuation.get('Trailing P/E', 'N/A');
    if pe_value_str != 'N/A' and isinstance(pe_value_str, str) and 'x' in pe_value_str:
        try: pe_val = float(pe_value_str.replace('x',''));
        except ValueError: pe_val = None
        if pe_val is not None:
            if pe_val > 50: risk_items.append(f"High Trailing P/E ratio ({pe_value_str}).")
            elif pe_val <=0: risk_items.append(f"Negative/Zero Trailing P/E ratio ({pe_value_str}).")
    debt_equity_str = financial_health.get('Debt/Equity', 'N/A')
    if debt_equity_str != 'N/A' and isinstance(debt_equity_str, str) and 'x' in debt_equity_str :
        try: debt_equity_val = float(debt_equity_str.replace('x',''))
        except ValueError: debt_equity_val = None
        if debt_equity_val is not None and debt_equity_val > 1.5 : risk_items.append(f"High Debt-to-Equity ratio ({debt_equity_str}).")

    risk_analysis_html = generate_risk_analysis_html(risk_items)
    monthly_forecast_table_html = generate_monthly_forecast_table_html( monthly_forecast_table_data, ticker, time_col, period_label)
    tech_analysis_summary_html = generate_tech_analysis_summary_html( ticker, sentiment, current_price, last_date, detailed_ta_data)
    overall_conclusion_html = generate_overall_conclusion_html( ticker, sentiment, overall_pct_change, final_forecast_average, current_price, risk_items, valuation, analyst_info, detailed_ta_data)
    faq_html = generate_faq_html( ticker, current_price, forecast_1m, final_forecast_average, overall_pct_change, monthly_forecast_table_data, risk_items, sentiment, volatility, valuation, analyst_info, period_label)
    final_notes_html = generate_final_notes_html(datetime.now(pytz.utc))
    profile_html = generate_profile_html(profile); valuation_html = generate_valuation_metrics_html(valuation)
    financial_health_html = generate_financial_health_html(financial_health); profitability_html = generate_profitability_html(profitability)
    dividends_splits_html = generate_dividends_splits_html(dividends); analyst_info_html = generate_analyst_info_html(analyst_info)
    news_html = generate_news_html(news_list)

    # --- Assemble Final HTML Structure (Same as original) ---
    print("[Original Report] Assembling final HTML structure...")
    html_sections = [
        ("Key Metrics & Forecast Summary", metrics_summary_html),
        ("Price Forecast Chart", forecast_chart_html, "forecast-chart", f"<div class=\"narrative\"><p>Aggregated historical price vs. forecast range ({period_label}ly).</p></div>"),
        ("Detailed Forecast Table", monthly_forecast_table_html),
        ("Company Profile", profile_html), ("Valuation Metrics", valuation_html), ("Financial Health", financial_health_html),
        ("Profitability", profitability_html), ("Dividends & Splits", dividends_splits_html), ("Analyst Insights", analyst_info_html),
        ("Technical Analysis Summary", tech_analysis_summary_html),
        ("Bollinger Bands", bb_chart_html, "tech-chart-bb", None, bb_conclusion),
        ("Relative Strength Index (RSI)", rsi_chart_html, "tech-chart-rsi", None, rsi_conclusion),
        ("Moving Average Convergence Divergence (MACD)",
         f'<div class="indicator-chart-container">{macd_lines_chart_html or ""}</div>' +
         f'<div class="indicator-chart-container">{macd_hist_chart_html or ""}</div>' +
         (f'<div class="indicator-conclusion">{macd_conclusion}</div>' if macd_conclusion else "<div class='indicator-conclusion'>MACD data not available or insufficient.</div>"),
         "tech-chart-macd-combined"),
        ("Historical Price & Volume", historical_chart_html, "historical-chart", "<div class=\"narrative\"><p>Historical closing price and volume (with 20d avg). Use buttons below chart to change range.</p></div>"),
        ("Potential Risk Factors", risk_analysis_html), ("Overall Outlook Summary", overall_conclusion_html),
        ("Recent News", news_html), ("Frequently Asked Questions", faq_html, "faq"),
        ("Report Information", final_notes_html, "general-info")
    ]

    report_body_content = f'<h1 class="report-title">{ticker} Stock Forecast & Analysis</h1>\n'
    # --- Loop through sections to build body (Same as original) ---
    for item in html_sections:
        title, html_content = item[0], item[1]
        section_class = item[2] if len(item) > 2 else title.lower().replace(" ", "-").replace("&", "and")
        narrative = item[3] if len(item) > 3 else None
        conclusion = item[4] if len(item) > 4 else None
        has_content = bool(html_content); is_chart_section = section_class.startswith("tech-chart-") or section_class in ["historical-chart", "forecast-chart"]
        if has_content or is_chart_section:
            report_body_content += f'<div class="section {section_class}">\n  <h2>{title}</h2>\n'
            if narrative: report_body_content += f"  {narrative}\n"
            chart_fallback_message = f'<p style="text-align:center; color:red; padding: 2rem 1rem;">Chart for {title} could not be generated.</p>'
            if section_class == "tech-chart-macd-combined": report_body_content += f"  {html_content or chart_fallback_message}\n"
            elif is_chart_section:
                chart_html = html_content or chart_fallback_message
                report_body_content += f'  <div class="indicator-chart-container">{chart_html}</div>\n'
                if conclusion: report_body_content += f'  <div class="indicator-conclusion">{conclusion}</div>\n'
            elif has_content: report_body_content += f"  {html_content}\n"
            report_body_content += f'</div>\n'

    # Assemble Final HTML Document (Using the inline custom_style)
    # NOTE: includes plotly.js script tag for interactive charts
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} Stock Analysis Report</title>
    {custom_style}
    <script src='https://cdn.plot.ly/plotly-latest.min.js'></script>
</head>
<body>
    <div class="report-container">
        {report_body_content}
    </div>
    <script>
       window.addEventListener('load', function() {{
           setTimeout(function() {{
               var allPlotlyDivs = document.querySelectorAll('.plotly-graph-div');
               allPlotlyDivs.forEach(function(div) {{
                   try {{ Plotly.Plots.resize(div); }} catch(e) {{ console.warn("Plotly resize failed for div:", div, e); }}
               }});
               console.log("Attempted Plotly resize on load.");
           }}, 500);
       }});
    </script>
</body>
</html>"""

    # Save Report (Same as original)
    report_filename = f"{ticker}_detailed_report_{ts}.html"
    report_path = os.path.join(static_dir, report_filename)
    try:
        with open(report_path, 'w', encoding='utf-8') as f: f.write(full_html)
        print(f"[Original Report] Successfully generated and saved report: {report_path}")
    except Exception as e:
        print(f"[Original Report] Error writing report file to {report_path}: {e}")
        return None, full_html # Return None for path, but still return HTML content

    # Return BOTH path and HTML content
    return report_path, full_html


# --- NEW Function for WordPress Report Assets ---
def create_wordpress_report_assets(
    ticker,
    actual_data,
    forecast_data,
    historical_data,
    fundamentals,
    ts,
    aggregation=None,
    app_root=None,
    plot_period_years=3
):
    """
    Generates assets for WordPress: text-only HTML and chart images.
    Requires kaleido library to be installed.
    """
    global custom_style # Access the CSS defined at module level
    print(f"[WP Assets] Starting generation for {ticker}...")

    # Determine the static directory path
    if app_root is None:
        print("[WP Assets] Warning: app_root not provided. Assuming relative path './static'")
        static_dir = 'static'
    else:
        static_dir = os.path.join(app_root, 'static')
    os.makedirs(static_dir, exist_ok=True)
    print(f"[WP Assets] Static directory for images: {static_dir}")

    # --- Data Validation and Preparation (Same as original function) ---
    required_hist_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    if historical_data is None or historical_data.empty:
         raise ValueError("[WP Assets] Historical data is missing or empty.")
    if not all(col in historical_data.columns for col in required_hist_cols):
        missing_cols_str = ', '.join([col for col in required_hist_cols if col not in historical_data.columns])
        raise ValueError(f"[WP Assets] Historical data missing required columns: {missing_cols_str}")
    if not isinstance(historical_data['Date'].iloc[0], pd.Timestamp):
         try: historical_data['Date'] = pd.to_datetime(historical_data['Date'])
         except Exception as e: raise ValueError(f"[WP Assets] Historical data 'Date' column error: {e}")
    historical_data = historical_data.sort_values('Date').reset_index(drop=True)
    hist_data_for_ta = historical_data.copy()

    # --- Determine time column and label (Same as original function) ---
    time_col = "Period"; period_label = "Period" # Default
    if forecast_data is not None and not forecast_data.empty and "Period" in forecast_data.columns:
        first_period = str(forecast_data['Period'].iloc[0])
        if len(first_period) == 7 and '-' in first_period: period_label = "Month"
        elif len(first_period) == 7 and '-' not in first_period : period_label = "Week"
        elif len(first_period) == 10: period_label = "Day"
    elif actual_data is not None and not actual_data.empty and "Period" in actual_data.columns:
         first_period = str(actual_data['Period'].iloc[0])
         if len(first_period) == 7 and '-' in first_period: period_label = "Month"
         elif len(first_period) == 7 and '-' not in first_period : period_label = "Week"
         elif len(first_period) == 10: period_label = "Day"

    # --- Calculate Detailed TA Data (Same as original function) ---
    print("[WP Assets] Calculating detailed technical analysis data...")
    detailed_ta_data = calculate_detailed_ta(hist_data_for_ta)

    # --- Calculate Key Metrics (Same as original function) ---
    print("[WP Assets] Calculating key metrics...")
    current_price = detailed_ta_data.get('Current_Price')
    last_date = historical_data['Date'].iloc[-1] if not historical_data.empty else datetime.now(pytz.utc)
    volatility = None; green_days = None; total_days = 0
    if len(historical_data) > 1:
        last_30_days_df = historical_data.iloc[-min(30, len(historical_data)):]
        if len(last_30_days_df) > 1:
            daily_returns = last_30_days_df['Close'].pct_change().dropna()
            if not daily_returns.empty: volatility = daily_returns.std() * np.sqrt(252) * 100
            price_diff = last_30_days_df['Close'].diff().dropna()
            green_days = (price_diff > 0).sum(); total_days = len(price_diff)
    sma50 = detailed_ta_data.get('SMA_50'); sma200 = detailed_ta_data.get('SMA_200')
    latest_rsi = detailed_ta_data.get('RSI_14')
    forecast_horizon_periods = 0; forecast_12m = pd.DataFrame(); final_forecast_average = None; forecast_1m = None
    if forecast_data is not None and not forecast_data.empty and 'Average' in forecast_data.columns:
        forecast_horizon_periods = min(len(forecast_data), 12)
        forecast_12m = forecast_data.head(forecast_horizon_periods)
        if not forecast_12m.empty:
            final_forecast_average = forecast_12m['Average'].iloc[-1]
            forecast_1m = forecast_data['Average'].iloc[0] if len(forecast_data) > 0 else None
    overall_pct_change = 0.0
    if current_price is not None and final_forecast_average is not None and current_price != 0:
        overall_pct_change = ((final_forecast_average - current_price) / current_price) * 100
    sentiment = determine_sentiment(detailed_ta_data, overall_pct_change)

    # --- Prepare Data for Tables (Same as original function) ---
    print("[WP Assets] Preparing forecast table data...")
    monthly_forecast_table_data = forecast_12m.copy()
    if not monthly_forecast_table_data.empty and current_price is not None and current_price != 0:
        if 'Average' in monthly_forecast_table_data.columns:
            monthly_forecast_table_data['Potential ROI'] = ((monthly_forecast_table_data['Average'] - current_price) / current_price) * 100
            monthly_forecast_table_data['Action'] = monthly_forecast_table_data['Potential ROI'].apply( lambda x: 'Buy' if x > 2 else ('Short' if x < -2 else 'Hold'))
        else:
            monthly_forecast_table_data['Potential ROI'] = 0.0; monthly_forecast_table_data['Action'] = 'N/A'
    elif not monthly_forecast_table_data.empty:
         monthly_forecast_table_data['Potential ROI'] = 0.0; monthly_forecast_table_data['Action'] = 'N/A'

    # --- Generate Plotly Figures (but don't convert to HTML yet) ---
    print("[WP Assets] Generating Plotly figures...")
    historical_line_fig = plot_historical_line_chart(historical_data.copy(), ticker)
    bb_fig, bb_conclusion = plot_price_bollinger(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    rsi_fig, rsi_conclusion = plot_rsi(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    macd_lines_fig, _ = plot_macd_lines(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    macd_hist_fig, _ = plot_macd_histogram(hist_data_for_ta.copy(), ticker, plot_period_years=plot_period_years)
    # Recalculate MACD conclusion as it's not returned by plotting functions
    macd_conclusion = get_macd_conclusion(detailed_ta_data.get('MACD_Line'), detailed_ta_data.get('MACD_Signal'), detailed_ta_data.get('MACD_Hist'), detailed_ta_data.get('MACD_Hist_Prev')) if detailed_ta_data.get('MACD_Hist') is not None else "MACD conclusion requires more data."

    # --- Save Figures as Static Images ---
    print("[WP Assets] Saving charts as static images...")
    chart_image_paths = {} # Dictionary to store paths of successfully saved images
    # (Image saving logic remains commented out as per the provided original code block)
    # ... _write_plotly_image calls would go here if needed ...

    # --- Extract Fundamental Data (Same as original function) ---
    print("[WP Assets] Extracting fundamental data...")
    profile = extract_company_profile(fundamentals); valuation = extract_valuation_metrics(fundamentals)
    financial_health = extract_financial_health(fundamentals); profitability = extract_profitability(fundamentals)
    dividends = extract_dividends_splits(fundamentals); analyst_info = extract_analyst_info(fundamentals)
    news_list = extract_news(fundamentals)

    # --- Generate HTML Components for TEXT ONLY Sections ---
    print("[WP Assets] Generating text/table HTML components...")
    metrics_summary_html = generate_metrics_summary_html( ticker, current_price, forecast_1m, final_forecast_average, overall_pct_change, sentiment, volatility, green_days, total_days, sma50, sma200, period_label)
    # ... (risk_items calculation identical) ...
    risk_items = [] # Recalculate risk items as they are not passed around
    if sentiment.lower().find('bearish') != -1: risk_items.append(f"Overall technical sentiment is {sentiment}.")
    if volatility is not None and volatility > 40: risk_items.append(f"High annualized volatility ({volatility:.1f}%) suggests potentially large price swings.")
    if sma50 is not None and current_price is not None and current_price < sma50: risk_items.append("Price below the 50-Day SMA (short-term weakness).")
    if sma200 is not None and current_price is not None and current_price < sma200: risk_items.append("Price below the 200-Day SMA (long-term weakness).")
    if overall_pct_change < -5: risk_items.append(f"Negative {forecast_horizon_periods}-{period_label} forecast trend ({overall_pct_change:+.1f}%).")
    if latest_rsi is not None and not pd.isna(latest_rsi) and latest_rsi > 70: risk_items.append(f"RSI ({latest_rsi:.1f}) is high (>70), potential overbought condition.")
    pe_value_str = valuation.get('Trailing P/E', 'N/A');
    if pe_value_str != 'N/A' and isinstance(pe_value_str, str) and 'x' in pe_value_str:
        try: pe_val = float(pe_value_str.replace('x',''));
        except ValueError: pe_val = None
        if pe_val is not None:
            if pe_val > 50: risk_items.append(f"High Trailing P/E ratio ({pe_value_str}).")
            elif pe_val <=0: risk_items.append(f"Negative/Zero Trailing P/E ratio ({pe_value_str}).")
    debt_equity_str = financial_health.get('Debt/Equity', 'N/A')
    if debt_equity_str != 'N/A' and isinstance(debt_equity_str, str) and 'x' in debt_equity_str :
        try: debt_equity_val = float(debt_equity_str.replace('x',''))
        except ValueError: debt_equity_val = None
        if debt_equity_val is not None and debt_equity_val > 1.5 : risk_items.append(f"High Debt-to-Equity ratio ({debt_equity_str}).")

    risk_analysis_html = generate_risk_analysis_html(risk_items)
    monthly_forecast_table_html = generate_monthly_forecast_table_html( monthly_forecast_table_data, ticker, time_col, period_label)
    tech_analysis_summary_html = generate_tech_analysis_summary_html( ticker, sentiment, current_price, last_date, detailed_ta_data) # Includes text summary of TA
    overall_conclusion_html = generate_overall_conclusion_html( ticker, sentiment, overall_pct_change, final_forecast_average, current_price, risk_items, valuation, analyst_info, detailed_ta_data)
    faq_html = generate_faq_html( ticker, current_price, forecast_1m, final_forecast_average, overall_pct_change, monthly_forecast_table_data, risk_items, sentiment, volatility, valuation, analyst_info, period_label)
    final_notes_html = generate_final_notes_html(datetime.now(pytz.utc))
    profile_html = generate_profile_html(profile); valuation_html = generate_valuation_metrics_html(valuation)
    financial_health_html = generate_financial_health_html(financial_health); profitability_html = generate_profitability_html(profitability)
    dividends_splits_html = generate_dividends_splits_html(dividends); analyst_info_html = generate_analyst_info_html(analyst_info)
    news_html = generate_news_html(news_list)

    # --- Assemble TEXT-ONLY Report Body ---
    print("[WP Assets] Assembling text-only HTML...")
    # --- Start: Updated Headline and Intro ---
    report_body_content = "" # Initialize empty string

    # Extract necessary fundamental info using safe_get
    info = fundamentals.get('info', {})
    company_name = safe_get(info, 'longName', ticker) # Fallback to ticker if name is missing
    market_cap_raw = safe_get(info, 'marketCap')
    employees_raw = safe_get(info, 'fullTimeEmployees')

    # Format the values using format_value function
    formatted_current_price = f"${current_price:,.2f}" if current_price is not None else "N/A"
    def format_value(value, value_type, decimals=2):
        """Formats a value based on its type (e.g., large_number, number)."""
        if value_type == 'large_number':
            if value >= 1e12:
                return f"{value / 1e12:.{decimals}f}T"
            elif value >= 1e9:
                return f"{value / 1e9:.{decimals}f}B"
            elif value >= 1e6:
                return f"{value / 1e6:.{decimals}f}M"
            elif value >= 1e3:
                return f"{value / 1e3:.{decimals}f}K"
            else:
                return f"{value:.{decimals}f}"
        elif value_type == 'number':
            return f"{value:,.{decimals}f}"
        return str(value)
    
    formatted_market_cap = format_value(market_cap_raw, 'large_number') if market_cap_raw != "N/A" else "N/A"
    formatted_employees = format_value(employees_raw, 'number', 0) if employees_raw != "N/A" else "N/A"

    # Generate the new H2 headline
    report_body_content += f'<h2>{ticker} Stock Price Prediction, Technical Analysis, and Forecast (2025-2026)</h2>\n' # Use H2, ensure class removed if not needed

    # Generate the introduction paragraph with dynamic data
    introduction_paragraph = (
        f"<p>If you're looking to explore the {ticker} stock price prediction for the next 12 months, you're in the right place. "
        f"Whether you're a retail investor or simply tracking healthcare stocks, this report is designed to help you understand the potential price path of {company_name} ({ticker}). "
        f"We combine technical analysis tools and price history data with volatility measures and moving averages for evaluation. "
        f"It generates monthly forecast ranges alongside simplified action signals through expected ROI suggestions. "
        f"The current share price of {ticker} stands at {formatted_current_price} while the company maintains a market capitalization of about {formatted_market_cap} alongside {formatted_employees} workers.</p>\n"
    )
    report_body_content += introduction_paragraph
    # --- End: Updated Headline and Intro ---

    # --- Continue adding other sections ---
    report_body_content += f'<div class="section key-metrics"><h2>Key Metrics & Forecast Summary</h2>{metrics_summary_html}</div>\n'
    # Add forecast table if needed (it's text/table based)
    if not monthly_forecast_table_data.empty:
        report_body_content += f'<div class="section forecast-table"><h2>Detailed Forecast Table</h2>{monthly_forecast_table_html}</div>\n'
    report_body_content += f'<div class="section company-profile"><h2>Company Profile</h2>{profile_html}</div>\n'
    report_body_content += f'<div class="section valuation"><h2>Valuation Metrics</h2>{valuation_html}</div>\n'
    report_body_content += f'<div class="section financial-health"><h2>Financial Health</h2>{financial_health_html}</div>\n'
    report_body_content += f'<div class="section profitability"><h2>Profitability</h2>{profitability_html}</div>\n'
    report_body_content += f'<div class="section dividends"><h2>Dividends & Splits</h2>{dividends_splits_html}</div>\n'
    report_body_content += f'<div class="section analyst"><h2>Analyst Insights</h2>{analyst_info_html}</div>\n'
    report_body_content += f'<div class="section tech-summary"><h2>Technical Analysis Summary</h2>{tech_analysis_summary_html}</div>\n'
    # Add placeholders for charts within the HTML structure if desired
    report_body_content += f'<div class="section tech-chart-bb"><h2>Bollinger Bands</h2><p><i>[Chart Image: Bollinger Bands - See generated images]</i></p><div class="indicator-conclusion">{bb_conclusion}</div></div>\n'
    report_body_content += f'<div class="section tech-chart-rsi"><h2>Relative Strength Index (RSI)</h2><p><i>[Chart Image: RSI - See generated images]</i></p><div class="indicator-conclusion">{rsi_conclusion}</div></div>\n'
    report_body_content += f'<div class="section tech-chart-macd"><h2>Moving Average Convergence Divergence (MACD)</h2><p><i>[Chart Images: MACD Lines & Histogram - See generated images]</i></p><div class="indicator-conclusion">{macd_conclusion}</div></div>\n'
    report_body_content += f'<div class="section historical-chart"><h2>Historical Price & Volume</h2><p><i>[Chart Image: Historical Price & Volume - See generated images]</i></p></div>\n'
    report_body_content += f'<div class="section risk"><h2>Potential Risk Factors</h2>{risk_analysis_html}</div>\n'
    report_body_content += f'<div class="section conclusion"><h2>Overall Outlook Summary</h2>{overall_conclusion_html}</div>\n'
    if news_list: # Only add news section if there is news
        report_body_content += f'<div class="section news"><h2>Recent News</h2>{news_html}</div>\n'
    report_body_content += f'<div class="section faq"><h2>Frequently Asked Questions</h2>{faq_html}</div>\n'
    report_body_content += f'<div class="section info"><h2>Report Information</h2>{final_notes_html}</div>\n'

    # Assemble Final HTML Document for Text Content (no plotly.js needed)
    # Make sure the custom_style includes necessary styles for h2.report-title if they differ from h1
    text_report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ticker} Stock Analysis Report (Text)</title>
    {custom_style}
</head>
<body>
    <div class="report-container">
        {report_body_content}
    </div>
</body>
</html>"""

    print(f"[WP Assets] Generation complete for {ticker}.")
    # Return the text HTML string and the dictionary of saved image paths
    return text_report_html, chart_image_paths