# fundamental_analysis.py
import pandas as pd
import numpy as np

def safe_get(data_dict, key, default="N/A"):
    """Safely get a value from a dictionary."""
    if data_dict is None:
        return default
    value = data_dict.get(key, default)
    # Handle cases where yfinance might return None or NaN-like values
    if value is None or pd.isna(value) or value == 'Infinity':
        return default
    return value

def format_value(value, value_type="number", precision=2):
    """Formats values for display, handling 'N/A'."""
    if value == "N/A" or value is None:
        return "N/A"

    try:
        if value_type == "currency":
            return f"${float(value):,.{precision}f}"
        elif value_type == "percent":
            return f"{float(value) * 100:.{precision}f}%"
        elif value_type == "ratio":
             return f"{float(value):.{precision}f}x"
        elif value_type == "large_number":
            num = float(value)
            if abs(num) >= 1e12:
                return f"{num / 1e12:.{precision}f} T"
            elif abs(num) >= 1e9:
                return f"{num / 1e9:.{precision}f} B"
            elif abs(num) >= 1e6:
                return f"{num / 1e6:.{precision}f} M"
            elif abs(num) >= 1e3:
                 return f"{num / 1e3:.{precision}f} K"
            else:
                return f"{num:,.{precision}f}"
        elif value_type == "number":
            return f"{float(value):,.{precision}f}"
        elif value_type == "date":
             # Assuming value might be a timestamp or epoch seconds
             try:
                 return pd.to_datetime(value, unit='s').strftime('%Y-%m-%d')
             except:
                 return str(value) # Fallback to string
        else:
            return str(value)
    except (ValueError, TypeError):
        return str(value) # Return original string if conversion fails

def extract_company_profile(fundamentals: dict):
    """Extracts key company profile info."""
    info = fundamentals.get('info', {})
    profile = {
        "Company Name": safe_get(info, 'longName'),
        "Sector": safe_get(info, 'sector'),
        "Industry": safe_get(info, 'industry'),
        "Website": safe_get(info, 'website', 'N/A'),
        "Market Cap": format_value(safe_get(info, 'marketCap'), 'large_number'),
        "Employees": format_value(safe_get(info, 'fullTimeEmployees'), 'number', 0),
        "Summary": safe_get(info, 'longBusinessSummary', 'No summary available.')
    }
    return profile

def extract_valuation_metrics(fundamentals: dict):
    """Extracts key valuation metrics."""
    info = fundamentals.get('info', {})
    metrics = {
        "Trailing P/E": format_value(safe_get(info, 'trailingPE'), 'ratio'),
        "Forward P/E": format_value(safe_get(info, 'forwardPE'), 'ratio'),
        "Price/Sales (TTM)": format_value(safe_get(info, 'priceToSalesTrailing12Months'), 'ratio'),
        "Price/Book": format_value(safe_get(info, 'priceToBook'), 'ratio'),
        "PEG Ratio": format_value(safe_get(info, 'pegRatio'), 'ratio'),
        "Enterprise Value/Revenue": format_value(safe_get(info, 'enterpriseToRevenue'), 'ratio'),
        "Enterprise Value/EBITDA": format_value(safe_get(info, 'enterpriseToEbitda'), 'ratio'),
    }
    return metrics

def extract_financial_health(fundamentals: dict):
    """Extracts key financial health metrics."""
    info = fundamentals.get('info', {})
    metrics = {
        "Return on Equity (TTM)": format_value(safe_get(info, 'returnOnEquity'), 'percent'),
        "Return on Assets (TTM)": format_value(safe_get(info, 'returnOnAssets'), 'percent'),
        "Debt/Equity": format_value(safe_get(info, 'debtToEquity'), 'ratio'),
        "Total Cash": format_value(safe_get(info, 'totalCash'), 'large_number'),
        "Total Debt": format_value(safe_get(info, 'totalDebt'), 'large_number'),
        "Current Ratio": format_value(safe_get(info, 'currentRatio'), 'ratio'),
        "Quick Ratio": format_value(safe_get(info, 'quickRatio'), 'ratio'),
        "Operating Cash Flow": format_value(safe_get(info, 'operatingCashflow'), 'large_number'),
        "Levered Free Cash Flow": format_value(safe_get(info, 'freeCashflow'), 'large_number'), # Note: yfinance might call this 'freeCashflow'
    }
    return metrics

def extract_profitability(fundamentals: dict):
    """Extracts key profitability metrics."""
    info = fundamentals.get('info', {})
    metrics = {
        "Profit Margin": format_value(safe_get(info, 'profitMargins'), 'percent'),
        "Operating Margin (TTM)": format_value(safe_get(info, 'operatingMargins'), 'percent'),
        "Gross Margin (TTM)": format_value(safe_get(info, 'grossMargins'), 'percent'), # Needs confirmation if yfinance provides this directly in 'info'
        "EBITDA Margin (TTM)": format_value(safe_get(info, 'ebitdaMargins'), 'percent'),
        "Revenue Growth (YoY)": format_value(safe_get(info, 'revenueGrowth'), 'percent'),
        "Earnings Growth (YoY)": format_value(safe_get(info, 'earningsGrowth'), 'percent'), # Often needs calc or comes from other endpoints
    }
     # Note: Gross Margin might be in financial statements, not info dict.
     # Add placeholder if not found directly.
    if metrics["Gross Margin (TTM)"] == "N/A":
         # Look in quarterly financials if available? Requires more complex parsing.
         metrics["Gross Margin (TTM)"] = "N/A (Check Financials)"

    return metrics

def extract_dividends_splits(fundamentals: dict):
    """Extracts dividend and stock split information."""
    info = fundamentals.get('info', {})
    metrics = {
        "Dividend Rate": format_value(safe_get(info, 'dividendRate'), 'currency'),
        "Dividend Yield": format_value(safe_get(info, 'dividendYield'), 'percent'),
        "Trailing Annual Dividend Rate": format_value(safe_get(info, 'trailingAnnualDividendRate'), 'currency'),
        "Trailing Annual Dividend Yield": format_value(safe_get(info, 'trailingAnnualDividendYield'), 'percent'),
        "5 Year Average Dividend Yield": format_value(safe_get(info, 'fiveYearAvgDividendYield'), 'percent', 0), # Often integer %
        "Payout Ratio": format_value(safe_get(info, 'payoutRatio'), 'percent'),
        "Ex-Dividend Date": format_value(safe_get(info, 'exDividendDate'), 'date'),
        "Last Split Date": format_value(safe_get(info, 'lastSplitDate'), 'date'),
        "Last Split Factor": safe_get(info, 'lastSplitFactor', 'N/A'),
    }
    return metrics

def extract_analyst_info(fundamentals: dict):
    """Extracts analyst recommendation and target price info."""
    info = fundamentals.get('info', {})
    # Get recommendations - could be list, DataFrame, or None
    recommendations_data = fundamentals.get('recommendations')

    recommendation_summary = "N/A"
    strong_buy, buy, hold, sell, strong_sell = 0, 0, 0, 0, 0

    # Check if recommendations_data is a non-empty list
    # The check 'recommendations_data' ensures the list is not empty
    if isinstance(recommendations_data, list) and recommendations_data:
        grades = [rec.get('toGrade', '').lower() for rec in recommendations_data if rec.get('toGrade')]
        for grade in grades:
             # Consolidate buy/strong buy and sell/strong sell for simplicity
             if 'strong buy' in grade or 'outperform' in grade or 'buy' in grade:
                 strong_buy += 1
             elif 'hold' in grade or 'neutral' in grade or 'peer perform' in grade or 'equal-weight' in grade:
                 hold += 1
             elif 'strong sell' in grade or 'underperform' in grade or 'sell' in grade:
                 strong_sell += 1

        total_ratings = strong_buy + hold + strong_sell
        if total_ratings > 0:
             # Simplified consensus logic based on counts
             if strong_buy > (hold + strong_sell): recommendation_summary = f"Buy ({total_ratings} Ratings)"
             elif strong_sell > (hold + strong_buy): recommendation_summary = f"Sell ({total_ratings} Ratings)"
             else: recommendation_summary = f"Hold ({total_ratings} Ratings)"
        else:
             # If list exists but no valid grades found after filtering
             recommendation_summary = "N/A (No Parsable Ratings in List)"

    # Check if recommendations_data is a non-empty DataFrame
    # Use '.empty' attribute for DataFrame truthiness check
    elif isinstance(recommendations_data, pd.DataFrame) and not recommendations_data.empty:
        # --- Handle DataFrame case ---
        # yfinance DataFrame often has columns like 'Firm', 'To Grade', 'From Grade', 'Action'
        # Check if the expected column exists
        if 'To Grade' in recommendations_data.columns:
            # Convert to string, handle potential NaN, convert to lower case
            grades = recommendations_data['To Grade'].astype(str).str.lower().tolist()
            # (Reuse the grade counting logic from above)
            for grade in grades:
                 if 'strong buy' in grade or 'outperform' in grade or 'buy' in grade: strong_buy +=1
                 elif 'hold' in grade or 'neutral' in grade or 'peer perform' in grade or 'equal-weight' in grade: hold += 1
                 elif 'strong sell' in grade or 'underperform' in grade or 'sell' in grade: strong_sell += 1

            total_ratings = strong_buy + hold + strong_sell
            if total_ratings > 0:
                if strong_buy > (hold + strong_sell): recommendation_summary = f"Buy ({total_ratings} Ratings)"
                elif strong_sell > (hold + strong_buy): recommendation_summary = f"Sell ({total_ratings} Ratings)"
                else: recommendation_summary = f"Hold ({total_ratings} Ratings)"
            else:
                # If DataFrame has 'To Grade' but no parsable ratings
                recommendation_summary = "N/A (No Parsable Ratings in DataFrame)"
        else:
            # If DataFrame exists but doesn't have the 'To Grade' column
            recommendation_summary = "N/A (Unexpected DataFrame Format)"

    # Fallback to 'recommendationKey' if no recommendation was processed above AND recommendationKey exists
    elif recommendation_summary == "N/A" and 'recommendationKey' in info:
         recommendation_summary = safe_get(info, 'recommendationKey', 'N/A').replace('_', ' ').title()

    # Final check if still N/A (handles None input or empty structures)
    elif recommendation_summary == "N/A":
        recommendation_summary = "N/A (No Recommendation Data Found)"


    # --- Rest of the function remains the same ---
    metrics = {
        "Recommendation": recommendation_summary,
        "Mean Target Price": format_value(safe_get(info, 'targetMeanPrice'), 'currency'),
        "High Target Price": format_value(safe_get(info, 'targetHighPrice'), 'currency'),
        "Low Target Price": format_value(safe_get(info, 'targetLowPrice'), 'currency'),
        "Number of Analyst Opinions": format_value(safe_get(info, 'numberOfAnalystOpinions'), 'number', 0),
    }
    return metrics

def extract_news(fundamentals: dict):
    """Extracts recent news headlines."""
    news_data = fundamentals.get('news')
    headlines = []
    # Check if news_data is a non-empty list
    if isinstance(news_data, list) and news_data:
        for item in news_data[:5]: # Get top 5 headlines
             # Check if item is a dictionary before accessing keys
             if isinstance(item, dict):
                 headlines.append({
                     'title': item.get('title', 'N/A'),
                     'publisher': item.get('publisher', 'N/A'),
                     'link': item.get('link', '#'),
                     # Ensure providerPublishTime exists and is numeric before formatting
                     'published': format_value(item.get('providerPublishTime'), 'date') if isinstance(item.get('providerPublishTime'), (int, float)) else 'N/A'
                 })
    return headlines