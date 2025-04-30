import time
import logging
import yfinance as yf
import pandas as pd
from datetime import datetime

# Configure logging to display info and error messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_stock_data(
    ticker,
    start_date=None,
    end_date=None,
    max_retries=3,
    pause_secs=2,
    throttle_secs=0.3
):
    """
    Fetch and process historical stock data for a single ticker,
    with retry/backoff on rate-limit errors and request throttling.
    """
    # Validate the date range
    if start_date and end_date:
        if pd.to_datetime(start_date) > pd.to_datetime(end_date):
            raise ValueError("start_date must be before end_date")

    # If no dates provided, fetch full history
    period = "10y" if (start_date is None and end_date is None) else None

    logger.info(
        f"Fetching data for ticker: {ticker} "
        f"from {start_date or 'the beginning'} to {end_date or 'today'}"
    )

    attempt = 0
    while attempt < max_retries:
        try:
            # Throttle to avoid bursts
            time.sleep(throttle_secs)
            data = yf.download(
                tickers=ticker,
                start=start_date,
                end=end_date,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=False  # disable parallel requests
            )
            if data.empty:
                raise ValueError(f"No data found for ticker: {ticker}")
            break
        except Exception as e:
            msg = str(e).lower()
            # Detect rate-limit by keywords
            if "rate limit" in msg or "too many requests" in msg:
                attempt += 1
                wait = pause_secs * attempt
                logger.warning(
                    f"Rate limit on '{ticker}', retry {attempt}/{max_retries} in {wait}s: {e}"
                )
                time.sleep(wait)
                continue
            # Other errors
            logger.error(f"Error fetching '{ticker}': {e}")
            raise
    else:
        raise RuntimeError(
            f"Failed to download '{ticker}' after {max_retries} retries due to rate limits."
        )

    # Reset index so that date becomes a column
    data = data.reset_index()
    logger.info(f"Fetched columns: {list(data.columns)}")

    # Flatten multi-index columns
    if isinstance(data.columns[0], tuple):
        data.columns = [col[0] for col in data.columns]
    else:
        data.columns = [
            col.split('_')[0] if isinstance(col, str) and '_' in col else col
            for col in data.columns
        ]

    # Rename date column to 'Date'
    date_cols = [c for c in data.columns if 'date' in c.lower()]
    if date_cols:
        data = data.rename(columns={date_cols[0]: 'Date'})

    # Convert 'Date' to datetime
    try:
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce', utc=True).dt.tz_localize(None)
    except Exception as e:
        logger.error(f"Error processing dates: {e}")
        raise

    invalid_dates = data['Date'].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Found {invalid_dates} invalid dates; dropping them.")
    data = data.dropna(subset=['Date']).sort_values('Date')

    # Ensure required columns
    required = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [col for col in required if col not in data.columns]
    if missing:
        logger.error(f"Available columns: {list(data.columns)}")
        raise ValueError(f"Missing required columns: {missing}")

    # Convert Volume to numeric
    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

    logger.info(f"Successfully fetched {len(data)} rows for '{ticker}'.")
    return data[required]

# Example usage
if __name__ == "__main__":
    try:
        ticker_symbol = "TSLA"
        df = fetch_stock_data(ticker_symbol)
        logger.info(f"Fetched {len(df)} rows for {ticker_symbol}.")
        print(df.head())
    except Exception as e:
        logger.error(f"An error occurred: {e}")
