# report_generator.py
import pandas as pd
import plotly.graph_objects as go
from plotly.io import to_html
import os
import numpy as np
from datetime import datetime, timedelta
import pytz

# Import functions from helper modules (ensure imports are correct)
from technical_analysis import (
    plot_historical_line_chart, plot_price_bollinger, plot_rsi,
    plot_macd_lines, plot_macd_histogram, calculate_detailed_ta,
    calculate_sma, calculate_rsi
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

# Helper function to determine sentiment (Keep as before)
def determine_sentiment(current_price, sma_50, sma_200, overall_pct_change, rsi=None):
    if current_price is None: return "N/A"
    score = 0
    if overall_pct_change > 5: score += 1.5
    elif overall_pct_change > 1: score += 0.5
    elif overall_pct_change < -5: score -= 1.5
    elif overall_pct_change < -1: score -= 0.5
    if sma_50 is not None and current_price > sma_50: score += 0.5
    elif sma_50 is not None and current_price < sma_50: score -= 0.5
    if sma_200 is not None and current_price > sma_200: score += 1.0
    elif sma_200 is not None and current_price < sma_200: score -= 1.0
    if sma_50 is not None and sma_200 is not None and sma_50 > sma_200: score += 0.5
    elif sma_50 is not None and sma_200 is not None and sma_50 < sma_200: score -= 0.5
    if rsi is not None and not pd.isna(rsi):
        if rsi > 65: score += 0.5
        elif rsi < 35: score -= 0.5
    if score >= 2.5: return "Strong Bullish"
    elif score >= 1.0: return "Bullish"
    elif score <= -2.5: return "Strong Bearish"
    elif score <= -1.0: return "Bearish"
    else: return "Neutral"

# --- Modify function signature to accept app_root ---
def create_full_report(
    ticker,
    actual_data,
    forecast_data,
    historical_data,
    fundamentals,
    ts,
    aggregation=None,
    app_root=None # Add app_root parameter
):
    """
    Generates a detailed HTML stock analysis report.
    Uses app_root to determine the correct static directory path.
    """
    print(f"Starting report generation for {ticker}...")

    # --- Determine the static directory path ---
    if app_root is None:
        # Fallback if app_root is not provided (e.g., running script directly)
        # This assumes the script is run from the project root where 'static' should be
        print("Warning: app_root not provided to create_full_report. Assuming current directory structure.")
        static_dir = 'static'
    else:
        # Construct the absolute path to the static directory
        static_dir = os.path.join(app_root, 'static')

    # --- Ensure the target static directory exists ---
    # This will now use the potentially absolute path based on app_root
    os.makedirs(static_dir, exist_ok=True)
    print(f"Using static directory: {static_dir}")


    # --- Data Validation and Preparation (Keep as before) ---
    # ... (rest of the validation code remains the same) ...
    required_hist_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in historical_data.columns for col in required_hist_cols):
        missing_cols_str = ', '.join([col for col in required_hist_cols if col not in historical_data.columns])
        raise ValueError(f"Historical data missing required columns: {missing_cols_str}")
    if not isinstance(historical_data['Date'].iloc[0], pd.Timestamp):
         try: historical_data['Date'] = pd.to_datetime(historical_data['Date'])
         except Exception as e: raise ValueError(f"Historical data 'Date' column error: {e}")
    historical_data = historical_data.sort_values('Date').reset_index(drop=True)
    hist_data_for_ta = historical_data.copy()
    if "YearMonth" in forecast_data.columns: forecast_time_col = "YearMonth"; actual_time_col = "YearMonth"; period_label = "Month"
    elif "Period" in forecast_data.columns: forecast_time_col = "Period"; actual_time_col = "Period"; period_label = "Period"
    else: raise ValueError("Forecast data must have a 'YearMonth' or 'Period' column.")
    if actual_time_col not in actual_data.columns: raise ValueError(f"Actual data must have a '{actual_time_col}' column.")


    # --- Calculate Key Metrics (Keep as before) ---
    # ... (metrics calculation code remains the same) ...
    print("Calculating key metrics...")
    current_price = historical_data['Close'].iloc[-1] if not historical_data.empty else None
    last_date = historical_data['Date'].iloc[-1] if not historical_data.empty else datetime.now(pytz.utc)
    volatility = None; green_days = None; total_days = 0
    if len(historical_data) > 30:
        last_30_days_df = historical_data.iloc[-30:]; daily_returns = last_30_days_df['Close'].pct_change().dropna()
        if not daily_returns.empty: volatility = daily_returns.std() * np.sqrt(252) * 100
        green_days = (last_30_days_df['Close'].diff().dropna() > 0).sum(); total_days = len(last_30_days_df) -1
    elif len(historical_data) > 1:
         daily_returns = historical_data['Close'].pct_change().dropna()
         if not daily_returns.empty: volatility = daily_returns.std() * np.sqrt(252) * 100
         green_days = (historical_data['Close'].diff().dropna() > 0).sum(); total_days = len(historical_data) -1
    sma50 = calculate_sma(historical_data['Close'], 50).iloc[-1] if len(historical_data) >= 50 else None
    sma200 = calculate_sma(historical_data['Close'], 200).iloc[-1] if len(historical_data) >= 200 else None
    latest_rsi = calculate_rsi(historical_data['Close'], 14).iloc[-1] if len(historical_data) >= 15 else None
    forecast_horizon_periods = min(len(forecast_data), 12); forecast_12m = forecast_data.head(forecast_horizon_periods)
    final_forecast_average = forecast_12m['Average'].iloc[-1] if not forecast_12m.empty else None
    overall_pct_change = ((final_forecast_average - current_price) / current_price) * 100 if current_price and final_forecast_average is not None and current_price != 0 else 0
    sentiment = determine_sentiment(current_price, sma50, sma200, overall_pct_change, latest_rsi)
    forecast_1m = forecast_data['Average'].iloc[0] if len(forecast_data) > 0 else None


    # --- Calculate Detailed TA Data (Keep as before) ---
    # ... (TA calculation code remains the same) ...
    print("Calculating detailed technical analysis data...")
    detailed_ta_data = calculate_detailed_ta(hist_data_for_ta)
    if 'RSI' not in detailed_ta_data: # Ensure RSI is available for outlook
        detailed_ta_data['RSI'] = latest_rsi

    # --- Prepare Data for Tables (Keep as before) ---
    # ... (table preparation code remains the same) ...
    print("Preparing forecast table data...")
    monthly_forecast_table_data = forecast_12m.copy()
    if not monthly_forecast_table_data.empty and current_price is not None and current_price != 0:
        monthly_forecast_table_data['Potential ROI'] = ((monthly_forecast_table_data['Average'] - current_price) / current_price) * 100
        monthly_forecast_table_data['Action'] = monthly_forecast_table_data['Potential ROI'].apply( lambda x: 'Buy' if x > 2 else ('Short' if x < -2 else 'Hold'))
    else: monthly_forecast_table_data['Potential ROI'] = 0.0; monthly_forecast_table_data['Action'] = 'N/A'


    # --- Generate Plotly Figures (Keep as before) ---
    # ... (plotting code remains the same) ...
    print("Generating plots...")
    forecast_chart_fig = go.Figure(); display_actual = actual_data.tail(6)
    combined_time_axis = pd.concat([display_actual[actual_time_col], forecast_12m[forecast_time_col]]).unique()
    forecast_chart_fig.add_trace( go.Scatter(x=display_actual[actual_time_col], y=display_actual['Average'], mode='lines+markers', name='Actual Aggregated', line=dict(color='#1f77b4', width=2.5), marker=dict(size=8), hovertemplate=f"<b>%{{x}} ({period_label})</b><br><b>Avg Price</b>: %{{y:.2f}}<extra></extra>"))
    if not forecast_12m.empty:
        colors = {'Low': '#d62728', 'Average': '#2ca02c', 'High': '#9467bd'}
        for col in ['Low', 'Average', 'High']:
            forecast_chart_fig.add_trace(go.Scatter(x=forecast_12m[forecast_time_col], y=forecast_12m[col], mode='lines+markers', name='Forecast ' + col, line=dict(color=colors[col], width=2.5), marker=dict(size=8, line=dict(width=1, color='#ffffff')), hovertemplate=f"<b>%{{x}} ({period_label})</b><br><b>{col}</b>: %{{y:.2f}}<extra></extra>"))
        # Check if 'Average' column exists and we are processing it
        if col == 'Average' and final_forecast_average is not None:
             annotation_text = (f"<b>{final_forecast_average:.2f}</b><br><span style='color:{colors[col]};'>{overall_pct_change:+.1f}% ({forecast_horizon_periods} {period_label}s)</span>")
             forecast_chart_fig.add_annotation(x=forecast_12m[forecast_time_col].iloc[-1], y=final_forecast_average, text=annotation_text, showarrow=True, arrowhead=2, ax=40, ay=-40, bgcolor='rgba(255,255,255,0.8)', font=dict(color=colors[col], size=10), bordercolor='black', borderwidth=1)

    forecast_chart_fig.update_layout( title=f"{ticker} {forecast_horizon_periods}-{period_label} Price Forecast vs Actual", xaxis=dict(title=period_label, type="category", categoryorder='array', categoryarray=combined_time_axis), yaxis_title="Price", template="plotly_white", legend_title_text='Legend', height=500)
    historical_line_fig = plot_historical_line_chart(historical_data, ticker)
    bb_fig, bb_conclusion = plot_price_bollinger(hist_data_for_ta.copy(), ticker)
    rsi_fig, rsi_conclusion = plot_rsi(hist_data_for_ta.copy(), ticker)
    macd_lines_fig, macd_conclusion = plot_macd_lines(hist_data_for_ta.copy(), ticker) # Get conclusion here
    macd_hist_fig, _ = plot_macd_histogram(hist_data_for_ta.copy(), ticker) # Ignore conclusion here

    # --- Extract Fundamental Data (Keep as before) ---
    # ... (fundamental extraction code remains the same) ...
    print("Extracting fundamental data...")
    profile = extract_company_profile(fundamentals); valuation = extract_valuation_metrics(fundamentals)
    financial_health = extract_financial_health(fundamentals); profitability = extract_profitability(fundamentals)
    dividends = extract_dividends_splits(fundamentals); analyst_info = extract_analyst_info(fundamentals)
    news_list = extract_news(fundamentals) # Renamed to avoid conflict


    # --- Generate HTML Components (Keep as before) ---
    # ... (HTML generation code remains the same) ...
    print("Generating HTML components...")
    metrics_summary_html = generate_metrics_summary_html( ticker, current_price, forecast_1m, final_forecast_average, overall_pct_change, sentiment, volatility, green_days, total_days, sma50, sma200, period_label)
    risk_items = []
    info_dict = fundamentals.get('info', {})
    if sentiment.lower().find('bearish') != -1: risk_items.append(f"Overall technical sentiment is {sentiment}.")
    if volatility is not None and volatility > 40: risk_items.append(f"High annualized volatility ({volatility:.1f}%) suggests potentially large price swings.")
    if sma50 is not None and current_price is not None and current_price < sma50: risk_items.append("Price below the 50-Day SMA (short-term weakness).")
    if sma200 is not None and current_price is not None and current_price < sma200: risk_items.append("Price below the 200-Day SMA (long-term weakness).")
    if overall_pct_change < -5: risk_items.append(f"Negative {forecast_horizon_periods}-{period_label} forecast trend ({overall_pct_change:+.1f}%).")
    if latest_rsi is not None and not pd.isna(latest_rsi) and latest_rsi > 70: risk_items.append(f"RSI ({latest_rsi:.1f}) is high (>70), potential overbought condition.")
    if latest_rsi is not None and not pd.isna(latest_rsi) and latest_rsi < 30: risk_items.append(f"RSI ({latest_rsi:.1f}) is low (<30), potential oversold condition.")
    pe_value_str = valuation.get('Trailing P/E', 'N/A')
    if pe_value_str != 'N/A' and isinstance(pe_value_str, str) and 'x' in pe_value_str:
        try: pe_val = float(pe_value_str.replace('x',''));
        except ValueError: pe_val = None
        if pe_val is not None:
            if pe_val > 50: risk_items.append(f"High Trailing P/E ratio ({pe_value_str}).")
            elif pe_val <=0: risk_items.append(f"Negative/Zero Trailing P/E ratio ({pe_value_str}).")
    debt_equity_str = financial_health.get('Debt/Equity', 'N/A')
    if debt_equity_str != 'N/A' and isinstance(debt_equity_str, str):
        try:
            debt_equity_val = float(debt_equity_str.replace('x',''))
            if debt_equity_val > 1.5 : risk_items.append(f"High Debt-to-Equity ratio ({debt_equity_str}).")
        except ValueError: pass
    risk_analysis_html = generate_risk_analysis_html(risk_items)
    monthly_forecast_table_html = generate_monthly_forecast_table_html( monthly_forecast_table_data, ticker, forecast_time_col, period_label)
    tech_analysis_summary_html = generate_tech_analysis_summary_html( ticker, sentiment, current_price, last_date, detailed_ta_data)
    overall_conclusion_html = generate_overall_conclusion_html( ticker, sentiment, overall_pct_change, final_forecast_average, current_price, risk_items, valuation, analyst_info, detailed_ta_data)
    faq_html = generate_faq_html( ticker, current_price, forecast_1m, final_forecast_average, overall_pct_change, monthly_forecast_table_data, risk_items, sentiment, volatility, valuation, analyst_info, period_label)
    final_notes_html = generate_final_notes_html(datetime.now(pytz.utc))
    profile_html = generate_profile_html(profile)
    valuation_html = generate_valuation_metrics_html(valuation)
    financial_health_html = generate_financial_health_html(financial_health)
    profitability_html = generate_profitability_html(profitability)
    dividends_splits_html = generate_dividends_splits_html(dividends)
    analyst_info_html = generate_analyst_info_html(analyst_info)
    news_html = generate_news_html(news_list) # Use the extracted list


    # Convert Plotly figures to HTML (Keep as before)
    def fig_to_html(fig): return to_html(fig, include_plotlyjs=False, full_html=False) if fig else ""
    forecast_chart_html = to_html(forecast_chart_fig, include_plotlyjs='cdn', full_html=False)
    historical_chart_html = fig_to_html(historical_line_fig)
    bb_chart_html = fig_to_html(bb_fig); rsi_chart_html = fig_to_html(rsi_fig)
    macd_lines_chart_html = fig_to_html(macd_lines_fig); macd_hist_chart_html = fig_to_html(macd_hist_fig)

    # --- Define CSS (Keep as before) ---
    # ... (CSS style block remains the same) ...
    print("Defining CSS...")
    custom_style = """
    <style>
      /* --- Base & General --- */
      body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; line-height: 1.6; }
      .report-container { max-width: 1200px; margin: 2rem auto; padding: 1.5rem 2rem; background: #ffffff; box-shadow: 0 8px 25px rgba(0,0,0,0.1); border-radius: 12px; }
      .report-title { text-align: center; color: #2c3e50; margin: 0 0 2rem 0; font-size: 2.4rem; font-weight: 700; border-bottom: 1px solid #dee2e6; padding-bottom: 1rem;}
      .section { margin-bottom: 2.5rem; padding: 0; /* Remove padding here, add to content inside */ background-color: #fff; border-radius: 8px; /* box-shadow: 0 4px 8px rgba(0,0,0,0.05); */ overflow: hidden; }
      .section h2 { color: #34495e; border-bottom: 2px solid #e9ecef; padding-bottom: 0.6rem; margin: 0 0 1.5rem 0; font-size: 1.6rem; font-weight: 600;}
      .section h3 { font-size: 1.2rem; color: #34495e; margin: 1.5rem 0 1rem 0; padding-bottom: 0.4rem; border-bottom: 1px solid #ecf0f1; }
      .section h4 { font-size: 1.1rem; color: #495057; margin: 1rem 0 0.5rem 0; }
      p { font-size: 1rem; line-height: 1.7; color: #495057; margin: 0 0 1rem 0; }
      a { color: #3498db; text-decoration: none; } a:hover { text-decoration: underline; }
      strong { font-weight: 600; color: #2c3e50; }
      .disclaimer { font-size: 0.9rem; color: #6c757d; font-style: italic; margin-top: 1.5rem; padding: 1rem; background-color: #f8f9fa; border-left: 4px solid #adb5bd; border-radius: 4px;}
      .narrative { margin-bottom: 1.5rem; padding: 1rem 1.2rem; background-color: #eef5f9; border-left: 4px solid #5dade2; border-radius: 4px; font-size: 0.95rem; }
      .narrative ul { margin-top: 0.5rem; margin-bottom: 0.5rem; padding-left: 20px;} .narrative li { margin-bottom: 0.5rem;}

      /* --- Icons --- */
      .icon { margin-right: 0.6em; font-size: 1em; display: inline-block; width: 1.2em; text-align: center; vertical-align: middle; }
      .icon-up { color: #28a745; } /* Bootstrap green */
      .icon-down { color: #dc3545; } /* Bootstrap red */
      .icon-neutral { color: #6c757d; } /* Bootstrap secondary */
      .icon-warning { color: #ffc107; } /* Bootstrap warning */
      .icon-positive { color: #28a745; }
      .icon-negative { color: #dc3545; }
      .icon-info { color: #17a2b8; } /* Bootstrap info */

      /* --- Specific Section Styling --- */

      /* Key Metrics (Reverted Box Style) */
      .metrics-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
      .metric-item { background-color: #f8f9fa; padding: 0.8rem 1rem; border-radius: 6px; text-align: center; border: 1px solid #dee2e6; /* Slightly darker border */ }
      .metric-label { display: block; font-size: 0.75rem; color: #6c757d; margin-bottom: 0.4rem; text-transform: uppercase; font-weight: 500; }
      .metric-value { display: block; font-size: 1.2rem; font-weight: 600; color: #343a40; line-height: 1.2; }
      .metric-change { font-size: 0.85rem; font-weight: normal; margin-left: 0.2rem; display: inline-block; }
      .sentiment-bullish, .action-buy, .trend-up { color: #28a745 !important; } .sentiment-strong-bullish { color: #208a38 !important; font-weight: bold; }
      .sentiment-bearish, .action-short, .trend-down { color: #dc3545 !important; } .sentiment-strong-bearish { color: #c82333 !important; font-weight: bold; }
      .sentiment-neutral, .action-hold, .trend-neutral { color: #6c757d !important; }

      /* Profile, Metrics Table, Fundamentals */
      .profile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem 1.5rem; margin-bottom: 1.5rem; }
      .profile-item span { font-weight: 600; margin-right: 0.5rem; color: #495057; } /* Darker label */
      .business-summary { margin-top: 1rem; }
      .business-summary h4 { margin-bottom: 0.5rem; color: #34495e; }
      .metrics-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
      .metrics-table td { padding: 0.9rem 0.5rem; border-bottom: 1px solid #dee2e6; font-size: 0.95rem; vertical-align: top;}
      .metrics-table tr:last-child td { border-bottom: none; } .metrics-table td:first-child { font-weight: 500; color: #495057; width: 40%;} /* Adjusted width */
      .metrics-table td:last-child { text-align: right; font-weight: 600; color: #343a40;} /* Bold value */
      .analyst-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem; }
      .analyst-item { background-color: #f8f9fa; padding: 0.8rem 1rem; border-radius: 4px; border: 1px solid #dee2e6; font-size: 0.9rem;}
      .analyst-item span { font-weight: 600; margin-right: 0.3rem; color: #495057; }

      /* Table Container */
      .table-container { overflow-x: auto; margin-top: 1rem; border: 1px solid #dee2e6; border-radius: 6px; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 0.9rem 1.1rem; text-align: left; border-bottom: 1px solid #dee2e6; font-size: 0.95rem;}
      th { background-color: #e9ecef; color: #495057; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; border-bottom-width: 2px; }
      tbody tr:nth-child(even) { background-color: #f8f9fa; } tbody tr:hover { background-color: #e9ecef; }
      td:nth-child(n+2):not(:last-child) { text-align: right; } td:last-child { text-align: center; } td[class^='action-'] { font-weight: bold; }

      /* Risk Analysis - IMPROVED */
      .risk-analysis ul { list-style: none; padding-left: 0; margin-top: 1rem; }
      .risk-analysis li { background-color: #fff3cd; /* Bootstrap warning light */ border-left: 5px solid #ffc107; /* Bootstrap warning */ color: #856404; /* Bootstrap warning dark */ padding: 0.9rem 1.2rem; margin-bottom: 0.8rem; border-radius: 4px; font-size: 0.95rem; display: flex; align-items: flex-start; }
      .risk-analysis li .icon { font-size: 1.1em; margin-right: 0.8em; margin-top: 0.1em; color: #ffc107; /* Match border color */ }

      /* Tech Analysis Summary */
      .tech-analysis h4 { margin-top: 1.5rem; margin-bottom: 0.8rem; color: #34495e; font-size: 1.1rem; padding-bottom: 0.3rem; border-bottom: 1px solid #dee2e6; }
      .sentiment-indicator { margin-bottom: 1.5rem; font-size: 1.1rem; padding: 1rem; background-color:#f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; text-align: center;}
      .sentiment-indicator span:first-child { margin-right: 0.5rem; font-weight: 500;}
      .ma-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
      .ma-item { background: #f8f9fa; padding: 0.8rem 1rem; border-radius: 6px; font-size: 0.95rem; border: 1px solid #dee2e6;}
      .ma-item .label { font-weight: 600; margin-right: 0.5rem;} .ma-item .value { font-weight: 500; } .ma-item .status { font-size: 0.85rem; margin-left: 0.4rem; font-style: italic;}

      /* Chart Containers */
      .indicator-chart-container { background-color: #ffffff; padding: 1rem 0 0 0; /* Padding top only */ margin-bottom: 1.5rem; border-radius: 8px; /* Removed shadow */ }
      .historical-chart .plotly-graph-div { /* Add wrapper? */ padding-top: 1rem; } /* Add space above hist chart */
      .indicator-conclusion { padding: 1.2rem 1.5rem; margin-top: 1rem; border-top: 1px solid #dee2e6; font-size: 0.95rem; line-height: 1.6; color: #495057; background-color: #f8f9fa; border-radius: 0 0 8px 8px; }
      .plotly-graph-div { margin: auto; }

      /* Overall Conclusion Section - IMPROVED */
      .overall-conclusion .conclusion-columns { display: flex; flex-wrap: wrap; gap: 2.5rem; margin: 1.5rem 0; padding: 1.5rem; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;}
      .overall-conclusion .conclusion-column { flex: 1; min-width: 300px; }
      .overall-conclusion h3 { font-size: 1.2rem; color: #34495e; margin: 0 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid #ced4da; }
      .overall-conclusion ul { list-style: none; padding-left: 0; margin-top: 0; }
      .overall-conclusion li { margin-bottom: 1rem; /* Increased spacing */ font-size: 0.95rem; line-height: 1.6; display: flex; align-items: flex-start; padding-left: 0; }
      .overall-conclusion li .icon { margin-right: 0.8em; margin-top: 0.15em; flex-shrink: 0; width: 1.2em; text-align: center; font-size: 1.1em; /* Slightly larger icon */ }
      .overall-conclusion li > span:last-child { flex-grow: 1; } /* Allow text to wrap */

      /* Recent News - IMPROVED */
      .news-container { margin-top: 1rem; }
      .news-item { padding: 1rem 0; border-bottom: 1px solid #e9ecef; margin-bottom: 0; background-color: transparent;}
      .news-item:last-child { border-bottom: none; }
      .news-item h4 { margin: 0 0 0.3rem 0; font-size: 1.05rem; font-weight: 600;}
      .news-item h4 a { color: #0056b3; } .news-item h4 a:hover { color: #003d7a; }
      .news-meta { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; /* Adjust spacing */ color: #6c757d; font-size: 0.85rem; margin: 0.5rem 0 0 0; }
      .news-meta span { background-color: #e9ecef; padding: 0.1rem 0.5rem; border-radius: 3px; }

      /* FAQ - IMPROVED */
      .faq details { border: 1px solid #dee2e6; border-radius: 6px; margin-bottom: 1rem; background: #fff; transition: background-color 0.2s ease;}
      .faq details[open] { background-color: #f8f9fa; }
      .faq summary { padding: 1rem 1.2rem; font-weight: 600; cursor: pointer; background-color: transparent; border-radius: 6px; outline: none; position: relative; color: #34495e; display: block; /* Ensure full width clickable */ transition: background-color 0.2s ease;}
      .faq details[open] summary { background-color: #e9ecef; border-bottom: 1px solid #dee2e6; border-radius: 6px 6px 0 0; }
      .faq summary::marker { content: ""; }
      .faq summary::after { content: '+'; position: absolute; right: 1.2rem; top: 50%; transform: translateY(-50%); font-size: 1.5rem; color: #adb5bd; transition: transform 0.2s ease-in-out, color 0.2s ease;}
      .faq details[open] summary::after { content: '−'; transform: translateY(-50%) rotate(180deg); color: #3498db;}
      .faq details p { padding: 1.5rem 1.2rem; margin: 0; border-top: 1px solid #dee2e6; border-radius: 0 0 6px 6px; background-color: #fff;}
      .faq details[open] p { border-top: none; } /* Remove top border when open */

      /* Report Information / Footer */
      .general-info { padding: 1.5rem; background-color: #f8f9fa; border-radius: 8px; border-top: 1px solid #dee2e6; margin-top: 2rem;}
      .general-info p { margin-bottom: 0.5rem; font-size: 0.9rem; color: #6c757d; }
      .general-info .disclaimer { margin-top: 1rem; padding: 1rem; background-color: #e9ecef; border-left-color: #6c757d; font-size: 0.85rem; }

    </style>
    """


    # --- Assemble Final HTML (Keep as before) ---
    # ... (HTML assembly logic remains the same) ...
    print("Assembling final HTML with distinct sections...")
    html_sections = [
        ("Key Metrics & Forecast Summary", metrics_summary_html),
        ("Price Forecast Chart", forecast_chart_html, "forecast-chart", "<div class=\"narrative\"><p>The chart below shows the aggregated historical average price vs the forecasted price range.</p></div>"),
        ("Detailed Forecast Table", monthly_forecast_table_html),
        ("Company Profile", profile_html), ("Valuation Metrics", valuation_html), ("Financial Health", financial_health_html),
        ("Profitability", profitability_html), ("Dividends & Splits", dividends_splits_html), ("Analyst Insights", analyst_info_html),
        ("Technical Analysis Summary", tech_analysis_summary_html),
        ("Bollinger Bands", bb_chart_html, "tech-chart-bb", None, bb_conclusion),
        ("Relative Strength Index (RSI)", rsi_chart_html, "tech-chart-rsi", None, rsi_conclusion),
        ("Moving Average Convergence Divergence (MACD)",
         f'<div class="indicator-chart-container">{macd_lines_chart_html}</div>' +
         f'<div class="indicator-chart-container" style="margin-top: 1.5rem;">{macd_hist_chart_html}</div>' +
         f'<div class="indicator-conclusion" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #eee;">{macd_conclusion or ""}</div>',
         "tech-chart-macd-combined"),
        ("Historical Price & Volume", historical_chart_html, "historical-chart", "<div class=\"narrative\"><p>Historical closing price and volume (with 20d avg). Use buttons below to change range.</p></div>"),
        ("Potential Risk Factors", risk_analysis_html), ("Overall Outlook Summary", overall_conclusion_html),
        ("Recent News", news_html), ("Frequently Asked Questions", faq_html), ("Report Information", final_notes_html)
    ]
    report_body_content = ""
    for item in html_sections:
        title, html_content = item[0], item[1]
        section_class = item[2] if len(item) > 2 else title.lower().replace(" ", "-").replace("&", "and")
        narrative = item[3] if len(item) > 3 else None
        conclusion = item[4] if len(item) > 4 else None
        if html_content:
            if section_class.startswith("tech-chart-") and section_class != "tech-chart-macd-combined":
                 report_body_content += f"""<div class="indicator-chart-container {section_class}"> {html_content} <div class="indicator-conclusion">{conclusion or ''}</div> </div>"""
            elif section_class == "tech-chart-macd-combined":
                 report_body_content += f"""<div class="section {section_class}"> <h2>{title}</h2> {html_content} </div>"""
            elif section_class == "historical-chart":
                 report_body_content += f"""<div class="section {section_class}"> <h2>{title}</h2> {narrative if narrative else ''} <div class="indicator-chart-container"> {html_content} </div> </div>"""
            elif section_class == "forecast-chart":
                report_body_content += f"""<div class="section {section_class}"> <h2>{title}</h2> {narrative if narrative else ''} {html_content} </div>"""
            else:
                 report_body_content += f""" <div class="section {section_class}"> <h2>{title}</h2> {narrative if narrative else ''} {html_content} </div>"""
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head> <meta charset="utf-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>{ticker} Stock Analysis Report</title> {custom_style} <script src='https://cdn.plot.ly/plotly-latest.min.js'></script> </head>
<body> <div class="report-container"> <h1 class="report-title">{ticker} Stock Forecast & Analysis</h1> {report_body_content} </div> </body>
</html>"""


    # --- Save Report using the explicit static_dir path ---
    report_filename = f"{ticker}_detailed_report_{ts}.html"
    # os.path.join will correctly handle static_dir whether it's relative or absolute
    report_path = os.path.join(static_dir, report_filename)
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"Successfully generated report: {report_path}")
    except Exception as e:
        print(f"Error writing report file to {report_path}: {e}")
        return None # Return None if saving fails

    # Return the absolute path to the report
    return report_path