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
    pause_secs=2
):
    """
    Fetch and process historical stock data for a single ticker,
    with retry/backoff on rate-limit errors detected by exception text.
    """
    # Validate the date range
    if start_date and end_date:
        if pd.to_datetime(start_date) > pd.to_datetime(end_date):
            raise ValueError("start_date must be before end_date")

    # If no dates provided, fetch the full available history
    period = "10y" if (start_date is None and end_date is None) else None

    logger.info(
        f"Fetching data for ticker: {ticker} "
        f"from {start_date or 'the beginning'} to {end_date or 'today'}"
    )

    attempt = 0
    while attempt < max_retries:
        try:
            data = yf.download(
                tickers=ticker,
                start=start_date,
                end=end_date,
                period=period,
                auto_adjust=True,
                progress=False
            )
            if data.empty:
                raise ValueError(f"No data found for ticker: {ticker}")
            break
        except Exception as e:
            msg = str(e).lower()
            # Detect rate-limit by keywords in the message
            if "rate limit" in msg or "too many requests" in msg:
                attempt += 1
                wait = pause_secs * attempt
                logger.warning(
                    f"Rate limit detected on '{ticker}', retry {attempt}/{max_retries} "
                    f"in {wait}s: {e}"
                )
                time.sleep(wait)
                continue
            # For other errors, re-raise immediately
            logger.error(f"Unexpected error fetching '{ticker}': {e}")
            raise
    else:
        # Retries exhausted
        raise RuntimeError(
            f"Failed to download '{ticker}' after {max_retries} attempts due to rate limits."
        )

    # Reset index so that date becomes a column
    data = data.reset_index()
    logger.info(f"Fetched columns: {list(data.columns)}")

    # Flatten multi-index columns if present
    if isinstance(data.columns[0], tuple):
        data.columns = [col[0] for col in data.columns]
    else:
        data.columns = [
            col.split('_')[0] if isinstance(col, str) and '_' in col else col
            for col in data.columns
        ]

    # Rename the date column to 'Date' if needed
    date_cols = [col for col in data.columns if 'date' in col.lower()]
    if date_cols:
        data = data.rename(columns={date_cols[0]: 'Date'})

    # Convert the 'Date' column to datetime objects
    try:
        data['Date'] = pd.to_datetime(data['Date'], errors='coerce', utc=True).dt.tz_localize(None)
    except Exception as e:
        logger.error(f"Error processing dates: {e}")
        raise

    invalid_dates = data['Date'].isna().sum()
    if invalid_dates > 0:
        logger.warning(f"Found {invalid_dates} invalid dates; dropping those rows.")
    data = data.dropna(subset=['Date']).sort_values('Date')

    # Define required columns
    required_columns = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        logger.error(f"Data columns available: {list(data.columns)}")
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Convert 'Volume' to numeric
    data['Volume'] = pd.to_numeric(data['Volume'], errors='coerce')

    logger.info(f"Successfully fetched {len(data)} rows for '{ticker}'.")
    return data[required_columns]


# Example usage
if __name__ == "__main__":
    try:
        ticker_symbol = "TSLA"
        stock_data = fetch_stock_data(ticker_symbol)
        logger.info(f"Fetched {len(stock_data)} rows of data for {ticker_symbol}.")
        print(stock_data.head())
    except Exception as e:
        logger.error(f"An error occurred: {e}")
