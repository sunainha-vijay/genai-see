# technical_analysis.py
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- Calculation Functions (Keep as before) ---
def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    if data.isnull().all() or len(data) < window + 1: return pd.Series(index=data.index, dtype=float)
    delta = data.diff(); gain = (delta.where(delta > 0, 0)).rolling(window=window).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, 1e-10); rsi = 100 - (100 / (1 + rs)); return rsi

def calculate_macd(data: pd.Series, fast_window: int = 12, slow_window: int = 26, signal_window: int = 9):
    if data.isnull().all() or len(data) < slow_window: empty_series = pd.Series(index=data.index, dtype=float); return empty_series, empty_series, empty_series
    ema_fast = data.ewm(span=fast_window, adjust=False).mean(); ema_slow = data.ewm(span=slow_window, adjust=False).mean(); macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_window, adjust=False).mean(); histogram = macd_line - signal_line; return macd_line, signal_line, histogram

def calculate_bollinger_bands(data: pd.Series, window: int = 20, num_std: int = 2):
    if data.isnull().all() or len(data) < window: empty_series = pd.Series(index=data.index, dtype=float); return empty_series, empty_series, empty_series
    middle_band = data.rolling(window=window).mean(); std_dev = data.rolling(window=window).std(); upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std); return upper_band, middle_band, lower_band

def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    if data.isnull().all() or len(data) < window: return pd.Series(index=data.index, dtype=float)
    return data.rolling(window=window).mean()

def calculate_volume_sma(data: pd.DataFrame, window: int) -> pd.Series: # Changed input to DataFrame
    if 'Volume' not in data.columns or data['Volume'].isnull().all() or len(data) < window: return pd.Series(index=data.index, dtype=float)
    return data['Volume'].rolling(window=window).mean()

# --- Conclusion Generation Functions (Keep as before) ---
def get_rsi_conclusion(rsi_value):
    if pd.isna(rsi_value): return "RSI data not available."
    if rsi_value > 70: return f"RSI ({rsi_value:.1f}) is above 70, suggesting potential overbought conditions. This could indicate a higher chance of a price pullback or consolidation."
    elif rsi_value < 30: return f"RSI ({rsi_value:.1f}) is below 30, suggesting potential oversold conditions. This could indicate a higher chance of a price rebound."
    else: return f"RSI ({rsi_value:.1f}) is in the neutral zone (30-70), indicating balanced momentum."

def get_macd_conclusion(macd_line_now, signal_line_now, histogram_now, histogram_prev):
    if pd.isna(macd_line_now) or pd.isna(signal_line_now) or pd.isna(histogram_now) or pd.isna(histogram_prev): return "MACD data not available or insufficient for comparison."
    conclusion = ""
    if histogram_now > 0 and histogram_prev < 0: conclusion += "A bullish MACD crossover (histogram crossing above zero) may have recently occurred, suggesting potential upward momentum. "
    elif histogram_now < 0 and histogram_prev > 0: conclusion += "A bearish MACD crossover (histogram crossing below zero) may have recently occurred, suggesting potential downward momentum. "
    if macd_line_now > signal_line_now: conclusion += f"Currently, the MACD line ({macd_line_now:.2f}) is above the signal line ({signal_line_now:.2f}), generally considered a bullish signal. "
    else: conclusion += f"Currently, the MACD line ({macd_line_now:.2f}) is below the signal line ({signal_line_now:.2f}), generally considered a bearish signal. "
    if histogram_now > 0: conclusion += f"The positive histogram ({histogram_now:.2f}) indicates strengthening bullish momentum (or weakening bearish momentum)."
    else: conclusion += f"The negative histogram ({histogram_now:.2f}) indicates strengthening bearish momentum (or weakening bullish momentum)."
    return conclusion.strip()

def get_bb_conclusion(close_price, upper_band, lower_band, middle_band):
    if pd.isna(close_price) or pd.isna(upper_band) or pd.isna(lower_band) or pd.isna(middle_band): return "Bollinger Band data not available."
    if close_price > upper_band: return f"The price (${close_price:.2f}) is currently above the upper Bollinger Band (${upper_band:.2f}), which can sometimes indicate an overbought condition or a strong breakout. Caution is advised as prices may revert towards the middle band (${middle_band:.2f})."
    elif close_price < lower_band: return f"The price (${close_price:.2f}) is currently below the lower Bollinger Band (${lower_band:.2f}), which can sometimes indicate an oversold condition or a strong breakdown. Prices may revert towards the middle band (${middle_band:.2f})."
    else: return f"The price (${close_price:.2f}) is currently trading within the Bollinger Bands (Lower: ${lower_band:.2f}, Upper: ${upper_band:.2f}), around the middle band (SMA20: ${middle_band:.2f})."

# --- Helper for common layout elements (Keep as before) ---
def _configure_indicator_layout(fig, title, height=350):
    fig.update_layout(title=dict(text=title, x=0.05, xanchor='left'), height=height, template="plotly_white",
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02), margin=dict(l=50, r=150, t=50, b=80), xaxis_rangeslider_visible=False)
    fig.update_xaxes(rangeselector=dict(buttons=list([ dict(count=1, label="1M", step="month", stepmode="backward"), dict(count=3, label="3M", step="month", stepmode="backward"),
            dict(count=6, label="6M", step="month", stepmode="backward"), dict(count=1, label="YTD", step="year", stepmode="todate"), dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=3, label="3Y", step="year", stepmode="backward"), dict(count=5, label="5Y", step="year", stepmode="backward"), dict(step="all")]), y= -0.3),
        range=[max(fig.data[0].x[0], fig.data[0].x[-1] - pd.DateOffset(years=1)), fig.data[0].x[-1]])
    return fig

# --- Separate Plotting Functions ---
def plot_price_bollinger(df, ticker):
    """Creates a plot for Price and Bollinger Bands."""
    if len(df) < 20: return None, "Insufficient data for Bollinger Bands."
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
    df_plot = df.dropna(subset=['BB_Upper'])
    if df_plot.empty: return None, "Bollinger Bands could not be calculated."
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Upper'], line=dict(color='rgba(211, 211, 211, 0.8)', width=1.5), name='Upper Band'))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Lower'], line=dict(color='rgba(211, 211, 211, 0.8)', width=1.5), fill='tonexty', fillcolor='rgba(211, 211, 211, 0.1)', name='Lower Band'))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Middle'], name='Middle Band (SMA20)', line=dict(color='#ff7f0e', width=1.5, dash='dash')))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Close'], name='Close Price', line=dict(color='#00008B', width=2)))
    fig = _configure_indicator_layout(fig, f'{ticker} Price & Bollinger Bands (20, 2)', height=450)
    fig.update_yaxes(title_text="Price")
    latest_valid_data = df_plot.iloc[-1]
    conclusion = get_bb_conclusion(latest_valid_data.get('Close'), latest_valid_data.get('BB_Upper'), latest_valid_data.get('BB_Lower'), latest_valid_data.get('BB_Middle'))
    return fig, conclusion

def plot_rsi(df, ticker):
    """Creates a plot for RSI."""
    if len(df) < 15: return None, "Insufficient data for RSI (14)."
    df['RSI'] = calculate_rsi(df['Close'])
    df_plot = df.dropna(subset=['RSI'])
    if df_plot.empty: return None, "RSI could not be calculated."
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['RSI'], name='RSI', line=dict(color='#8A2BE2', width=2))) # BlueViolet
    fig.add_hline(y=70, line_dash="dash", line_color="#DC143C", opacity=0.8, annotation_text="Overbought (70)", annotation_position="bottom right") # Crimson
    fig.add_hline(y=30, line_dash="dash", line_color="#228B22", opacity=0.8, annotation_text="Oversold (30)", annotation_position="bottom right") # ForestGreen
    fig = _configure_indicator_layout(fig, f'Relative Strength Index (RSI 14)')
    fig.update_yaxes(title_text="RSI", range=[0, 100])
    latest_valid_data = df_plot.iloc[-1]
    conclusion = get_rsi_conclusion(latest_valid_data.get('RSI'))
    return fig, conclusion

# --- NEW: Separated MACD Plots ---
def plot_macd_lines(df, ticker):
    """Creates a plot for MACD Line and Signal Line."""
    if len(df) < 35: return None, "Insufficient data for MACD (12, 26, 9)."
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])
    df_plot = df.dropna(subset=['MACD_Line', 'MACD_Signal'])
    if len(df_plot) < 2: return None, "Insufficient valid MACD Line/Signal data."

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD_Line'], name='MACD Line', line=dict(color='#191970', width=2))) # MidnightBlue
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD_Signal'], name='Signal Line', line=dict(color='#FF4500', width=2))) # OrangeRed
    fig.add_hline(y=0, line_dash="dash", line_color="grey", opacity=0.5) # Zero line

    fig = _configure_indicator_layout(fig, f'MACD Line vs Signal Line')
    fig.update_yaxes(title_text="MACD Value")

    # Get conclusion (needs histogram data as well)
    df_plot_hist = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
    if len(df_plot_hist) < 2:
        conclusion = "MACD conclusion requires more data."
    else:
        latest_valid_data = df_plot_hist.iloc[-1]
        prev_valid_data = df_plot_hist.iloc[-2]
        conclusion = get_macd_conclusion(latest_valid_data.get('MACD_Line'), latest_valid_data.get('MACD_Signal'), latest_valid_data.get('MACD_Hist'), prev_valid_data.get('MACD_Hist'))
    return fig, conclusion # Return same conclusion as histogram plot

def plot_macd_histogram(df, ticker):
    """Creates a plot for MACD Histogram."""
    if len(df) < 35: return None, "Insufficient data for MACD (12, 26, 9)."
    # Calculate MACD if not already present (might be called independently)
    if 'MACD_Hist' not in df.columns:
      df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])

    df_plot = df.dropna(subset=['MACD_Hist'])
    if len(df_plot) < 2: return None, "Insufficient valid MACD Histogram data."

    fig = go.Figure()
    colors = np.where(df_plot['MACD_Hist'] < 0, '#DC143C', '#228B22') # Crimson, ForestGreen
    fig.add_trace(go.Bar(x=df_plot['Date'], y=df_plot['MACD_Hist'], name='MACD Hist', marker_color=colors))

    fig = _configure_indicator_layout(fig, f'MACD Histogram')
    fig.update_yaxes(title_text="Histogram Value")

    # Get conclusion (needs line/signal data as well)
    df_plot_full = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
    if len(df_plot_full) < 2:
         conclusion = "MACD conclusion requires more data."
    else:
        latest_valid_data = df_plot_full.iloc[-1]
        prev_valid_data = df_plot_full.iloc[-2]
        conclusion = get_macd_conclusion(latest_valid_data.get('MACD_Line'), latest_valid_data.get('MACD_Signal'), latest_valid_data.get('MACD_Hist'), prev_valid_data.get('MACD_Hist'))
    return fig, conclusion # Return same conclusion as lines plot

# --- Historical Chart (keep previous version) ---
def plot_historical_line_chart(df, ticker):
    """Creates a Line chart with Price and Volume on secondary axis."""
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Close Price', line=dict(color='#00008B', width=2)), secondary_y=False) # Dark Blue
    if 'Volume' in df.columns and not df['Volume'].isnull().all():
        df['Volume_SMA20'] = calculate_volume_sma(df, 20)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Volume'], name='Volume', line=dict(color='#FF8C00', width=1), opacity=0.4), secondary_y=True) # Dark Orange
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Volume_SMA20'], name='Volume SMA(20)', line=dict(color='#8B4513', width=1.5, dash='dot')), secondary_y=True) # SaddleBrown
        fig.update_yaxes(title_text="Volume", secondary_y=True, showgrid=False)
    fig.update_yaxes(title_text="Price ($)", secondary_y=False)
    fig.update_layout(title=dict(text=f'{ticker} Historical Price & Volume', x=0.05, xanchor='left'), template="plotly_white", height=500,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02), margin=dict(l=50, r=150, t=50, b=80), xaxis_rangeslider_visible=False)
    fig.update_xaxes(rangeselector=dict(buttons=list([ dict(count=1, label="1M", step="month", stepmode="backward"), dict(count=3, label="3M", step="month", stepmode="backward"),
            dict(count=6, label="6M", step="month", stepmode="backward"), dict(count=1, label="YTD", step="year", stepmode="todate"), dict(count=1, label="1Y", step="year", stepmode="backward"),
            dict(count=3, label="3Y", step="year", stepmode="backward"), dict(count=5, label="5Y", step="year", stepmode="backward"), dict(step="all")]), y=-0.3),
        range=[max(df['Date'].min(), df['Date'].max() - pd.DateOffset(years=1)), df['Date'].max()])
    return fig

# --- Function to calculate additional indicators for summary (Keep as before) ---
def calculate_detailed_ta(df):
    """Calculates additional indicators for the summary report."""
    if df is None or df.empty: return {}
    ta_summary = {}; df = df.copy(); df['Date'] = pd.to_datetime(df['Date']); df = df.sort_values('Date')
    for period in [20, 50, 100, 200]:
        if len(df) >= period: sma_col = f'SMA_{period}'; df[sma_col] = calculate_sma(df['Close'], period); ta_summary[sma_col] = df[sma_col].iloc[-1] if not df[sma_col].isnull().iloc[-1] else None
        else: ta_summary[f'SMA_{period}'] = None
    if 'Volume' in df.columns:
        if len(df) >= 20:
             df['Volume_SMA20'] = calculate_volume_sma(df, 20); latest_volume = df['Volume'].iloc[-1]; latest_vol_sma = df['Volume_SMA20'].iloc[-1]
             if not pd.isna(latest_volume) and not pd.isna(latest_vol_sma) and latest_vol_sma > 0: ta_summary['Volume_vs_SMA20_Ratio'] = latest_volume / latest_vol_sma
             else: ta_summary['Volume_vs_SMA20_Ratio'] = None
             ta_summary['Volume_SMA20'] = latest_vol_sma
        else: ta_summary['Volume_vs_SMA20_Ratio'] = None; ta_summary['Volume_SMA20'] = None
        if len(df) >= 6:
            if df['Volume'].iloc[-1] > df['Volume'].iloc[-5:].mean() * 1.1: ta_summary['Volume_Trend_5D'] = "Increasing"
            elif df['Volume'].iloc[-1] < df['Volume'].iloc[-5:].mean() * 0.9: ta_summary['Volume_Trend_5D'] = "Decreasing"
            else: ta_summary['Volume_Trend_5D'] = "Mixed"
        else: ta_summary['Volume_Trend_5D'] = None
    lookback = 30
    if len(df) >= lookback: ta_summary['Support_30D'] = df['Low'].iloc[-lookback:].min(); ta_summary['Resistance_30D'] = df['High'].iloc[-lookback:].max()
    else: ta_summary['Support_30D'] = None; ta_summary['Resistance_30D'] = None
    return ta_summary