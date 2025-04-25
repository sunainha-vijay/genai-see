# technical_analysis.py (Updated to remove fixed heights)
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- Calculation Functions (Keep as before) ---
def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    if data.isnull().all() or len(data) < window + 1: return pd.Series(index=data.index, dtype=float)
    delta = data.diff(); gain = (delta.where(delta > 0, 0)).rolling(window=window).mean(); loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    # Add small epsilon to prevent division by zero if loss is consistently zero
    loss = loss.replace(0, 1e-10)
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs));
    return rsi

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
    if histogram_now > 0 and histogram_prev <= 0: # Trigger on cross or first positive
        conclusion += "A bullish MACD crossover (histogram crossing above zero) may have recently occurred, suggesting potential upward momentum. "
    elif histogram_now < 0 and histogram_prev >= 0: # Trigger on cross or first negative
        conclusion += "A bearish MACD crossover (histogram crossing below zero) may have recently occurred, suggesting potential downward momentum. "

    if macd_line_now > signal_line_now:
        conclusion += f"Currently, the MACD line ({macd_line_now:.2f}) is above the signal line ({signal_line_now:.2f}), generally considered a bullish signal. "
    else:
        conclusion += f"Currently, the MACD line ({macd_line_now:.2f}) is below the signal line ({signal_line_now:.2f}), generally considered a bearish signal. "

    if histogram_now > 0:
        conclusion += f"The positive histogram ({histogram_now:.2f}) indicates strengthening bullish momentum (or weakening bearish momentum)."
    elif histogram_now < 0:
         conclusion += f"The negative histogram ({histogram_now:.2f}) indicates strengthening bearish momentum (or weakening bullish momentum)."
    else: # Histogram is zero
         conclusion += "The histogram is at zero, indicating the MACD and signal lines are currently equal."

    return conclusion.strip()


def get_bb_conclusion(close_price, upper_band, lower_band, middle_band):
    if pd.isna(close_price) or pd.isna(upper_band) or pd.isna(lower_band) or pd.isna(middle_band): return "Bollinger Band data not available."
    if close_price > upper_band: return f"The price (${close_price:.2f}) is currently above the upper Bollinger Band (${upper_band:.2f}), which can sometimes indicate an overbought condition or a strong breakout. Caution is advised as prices may revert towards the middle band (${middle_band:.2f})."
    elif close_price < lower_band: return f"The price (${close_price:.2f}) is currently below the lower Bollinger Band (${lower_band:.2f}), which can sometimes indicate an oversold condition or a strong breakdown. Prices may revert towards the middle band (${middle_band:.2f})."
    else: return f"The price (${close_price:.2f}) is currently trading within the Bollinger Bands (Lower: ${lower_band:.2f}, Upper: ${upper_band:.2f}), around the middle band (SMA20: ${middle_band:.2f})."

# --- Helper for common layout elements (REVISED LAYOUT STRUCTURE) ---
# REMOVED height parameter from function definition and update_layout
def _configure_indicator_layout(fig, title):
    fig.update_layout(
        # 1. Title at the top
        title=dict(
            text=title,
            y=0.98, # Position title very high
            x=0.5,
            xanchor='center',
            yanchor='top',
            font=dict(size=14)
        ),
        # 2. Legend below the title
        legend=dict(
            orientation="h",    # Horizontal layout
            yanchor="top",      # Anchor legend block from its top
            y=0.92,             # Position below the title (y=0.98)
            xanchor="center",
            x=0.5,
            font=dict(size=10) # Smaller legend font
        ),
        # 3. Range Selector positioned via update_xaxes below

        # 4. Plot Area (adjust domain and margins)
        # Make space at the top for Title, Legend, RangeSelector
        margin=dict(l=35, r=25, t=100, b=40), # Increased TOP margin significantly
        # Adjust y-axis domain to prevent overlap with elements above
        # Using slightly less than space remaining after range selector to avoid overlap
        yaxis=dict(domain=[0, 0.78]),

        # height=height, # <-- REMOVED fixed height
        template="plotly_white",
        autosize=True, # Explicitly ensure autosize is on (it's default but good practice)
        xaxis_rangeslider_visible=False, # Keep this off for indicators
        xaxis_automargin=True,
        yaxis_automargin=True
    )

    # Update X-Axis specifically for Range Selector positioning
    fig.update_xaxes(
        # Keep domain spanning full width for axis ticks/labels
        domain=[0, 1],
        # Position Range Selector below Legend
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=3, label="3Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(step="all")
            ]),
            yanchor='top',
            y=0.84, # Position below the legend (y=0.92)
            xanchor='left', # Align buttons left for consistency
            x=0.01,
            font_size=10
        ),
        tickfont=dict(size=10) # Keep tick font size adjustment
    )
    # Update Y-Axis font size
    fig.update_yaxes(tickfont=dict(size=10))

    # Set initial visible range (last 1 year) - Keep this logic
    if fig.data and len(fig.data[0].x) > 0:
         # Check if data exists before accessing [-1]
         last_date_in_data = fig.data[0].x[-1]
         first_date_in_data = fig.data[0].x[0]
         default_start = max(first_date_in_data, last_date_in_data - pd.DateOffset(years=1))
         # Ensure start date is not after end date if data is less than 1 year
         if default_start > last_date_in_data:
             default_start = first_date_in_data
         fig.update_xaxes(range=[default_start, last_date_in_data])

    return fig

# --- Plotting Functions using the REVISED layout ---

def plot_price_bollinger(df, ticker):
    if len(df) < 20: return None, "Insufficient data for Bollinger Bands."
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = calculate_bollinger_bands(df['Close'])
    df_plot = df.dropna(subset=['BB_Upper'])
    if df_plot.empty: return None, "Bollinger Bands could not be calculated."
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Upper'], line=dict(color='rgba(211, 211, 211, 0.8)', width=1.5), name='Upper Band'))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Lower'], line=dict(color='rgba(211, 211, 211, 0.8)', width=1.5), fill='tonexty', fillcolor='rgba(211, 211, 211, 0.1)', name='Lower Band'))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['BB_Middle'], name='SMA20', line=dict(color='#ff7f0e', width=1.5, dash='dash')))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['Close'], name='Close', line=dict(color='#00008B', width=2)))
    # Apply REVISED layout helper (no height passed)
    fig = _configure_indicator_layout(fig, f'{ticker} Price & Bollinger Bands')
    fig.update_yaxes(title_text="Price")
    latest_valid_data = df_plot.iloc[-1]
    conclusion = get_bb_conclusion(latest_valid_data.get('Close'), latest_valid_data.get('BB_Upper'), latest_valid_data.get('BB_Lower'), latest_valid_data.get('BB_Middle'))
    return fig, conclusion

def plot_rsi(df, ticker):
    if len(df) < 15: return None, "Insufficient data for RSI (14)."
    df['RSI'] = calculate_rsi(df['Close'])
    df_plot = df.dropna(subset=['RSI'])
    if df_plot.empty: return None, "RSI could not be calculated."
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['RSI'], name='RSI', line=dict(color='#8A2BE2', width=2)))
    fig.add_hline(y=70, line_dash="dash", line_color="#DC143C", opacity=0.8, annotation_text="Overbought (70)", annotation_position="bottom right")
    fig.add_hline(y=30, line_dash="dash", line_color="#228B22", opacity=0.8, annotation_text="Oversold (30)", annotation_position="bottom right")
    # Apply REVISED layout helper (no height passed)
    fig = _configure_indicator_layout(fig, f'Relative Strength Index (RSI 14)')
    fig.update_yaxes(title_text="RSI", range=[0, 100])
    latest_valid_data = df_plot.iloc[-1]
    conclusion = get_rsi_conclusion(latest_valid_data.get('RSI'))
    return fig, conclusion

def plot_macd_lines(df, ticker):
    if len(df) < 35: return None, "Insufficient data for MACD (12, 26, 9)."
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])
    df_plot = df.dropna(subset=['MACD_Line', 'MACD_Signal'])
    if len(df_plot) < 2: return None, "Insufficient valid MACD Line/Signal data."
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD_Line'], name='MACD Line', line=dict(color='#191970', width=2)))
    fig.add_trace(go.Scatter(x=df_plot['Date'], y=df_plot['MACD_Signal'], name='Signal Line', line=dict(color='#FF4500', width=2)))
    fig.add_hline(y=0, line_dash="dash", line_color="grey", opacity=0.5)
    # Apply REVISED layout helper (no height passed)
    fig = _configure_indicator_layout(fig, f'MACD Line vs Signal Line')
    fig.update_yaxes(title_text="MACD Value")
    # Conclusion logic remains same
    df_plot_hist = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
    if len(df_plot_hist) < 2: conclusion = "MACD conclusion requires more data."
    else:
        latest = df_plot_hist.iloc[-1]; prev = df_plot_hist.iloc[-2]
        conclusion = get_macd_conclusion(latest.get('MACD_Line'), latest.get('MACD_Signal'), latest.get('MACD_Hist'), prev.get('MACD_Hist'))
    return fig, conclusion

def plot_macd_histogram(df, ticker):
    if len(df) < 35: return None, "Insufficient data for MACD (12, 26, 9)."
    # Ensure MACD is calculated if missing
    if 'MACD_Hist' not in df.columns:
        df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = calculate_macd(df['Close'])
    df_plot = df.dropna(subset=['MACD_Hist'])
    if len(df_plot) < 2: return None, "Insufficient valid MACD Histogram data."
    fig = go.Figure()
    colors = np.where(df_plot['MACD_Hist'] < 0, '#DC143C', '#228B22')
    fig.add_trace(go.Bar(x=df_plot['Date'], y=df_plot['MACD_Hist'], name='MACD Hist', marker_color=colors))
    # Apply REVISED layout helper (no height passed)
    fig = _configure_indicator_layout(fig, f'MACD Histogram')
    fig.update_yaxes(title_text="Histogram Value")
    # Conclusion logic remains same
    df_plot_full = df.dropna(subset=['MACD_Line', 'MACD_Signal', 'MACD_Hist'])
    if len(df_plot_full) < 2: conclusion = "MACD conclusion requires more data."
    else:
        latest = df_plot_full.iloc[-1]; prev = df_plot_full.iloc[-2]
        conclusion = get_macd_conclusion(latest.get('MACD_Line'), latest.get('MACD_Signal'), latest.get('MACD_Hist'), prev.get('MACD_Hist'))
    return fig, conclusion

# --- Historical Chart (REVISED LAYOUT STRUCTURE) ---
def plot_historical_line_chart(df, ticker):
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=df['Date'], y=df['Close'], name='Close', line=dict(color='#00008B', width=2)), secondary_y=False)
    if 'Volume' in df.columns and not df['Volume'].isnull().all():
        df['Volume_SMA20'] = calculate_volume_sma(df, 20)
        fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name='Volume', marker_color='#FF8C00', opacity=0.35), secondary_y=True)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Volume_SMA20'], name='Volume SMA20', line=dict(color='#8B4513', width=1.5, dash='dot')), secondary_y=True)
        # Adjust secondary y-axis domain to match primary plot area
        fig.update_yaxes(title_text="Volume", secondary_y=True, domain=[0, 0.78], showgrid=False, title_font_size=10, tickfont_size=10, automargin=True)
    # Adjust primary y-axis domain
    fig.update_yaxes(title_text="Price ($)", secondary_y=False, domain=[0, 0.78], title_font_size=10, tickfont_size=10, automargin=True)

    # Apply REVISED layout structure
    fig.update_layout(
        # 1. Title
        title=dict(text=f'{ticker} Historical Price & Volume', y=0.98, x=0.5, xanchor='center', yanchor='top', font_size=14),
        # 2. Legend
        legend=dict(orientation="h", yanchor="top", y=0.92, xanchor="center", x=0.5, font_size=10),
        # 3. Range Selector positioned via update_xaxes below
        # 4. Plot Area
        margin=dict(l=35, r=35, t=100, b=40), # Increased top margin, ensure right margin accommodates secondary y-axis label potentially
        # height=450, # <-- REMOVED fixed height
        template="plotly_white",
        autosize=True, # Explicitly ensure autosize is on
        xaxis_rangeslider_visible=False, # Keep off
        xaxis_automargin=True,
        # Y-axis domains are set above
    )
    # Update X-Axis specifically for Range Selector positioning below legend
    fig.update_xaxes(
        domain=[0, 1], # Full width for x-axis itself
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=3, label="3Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(step="all")
            ]),
            yanchor='top',
            y=0.84, # Below legend (y=0.92)
            xanchor='left',
            x=0.01,
            font_size=10
        ),
        tickfont=dict(size=10)
    )

    # Set initial visible range (last 1 year) - Keep this logic
    if not df.empty:
        last_date_in_data = df['Date'].max()
        first_date_in_data = df['Date'].min()
        default_start = max(first_date_in_data, last_date_in_data - pd.DateOffset(years=1))
        if default_start > last_date_in_data: default_start = first_date_in_data
        fig.update_xaxes(range=[default_start, last_date_in_data])

    return fig


# --- Function to calculate additional indicators for summary (Keep as before) ---
def calculate_detailed_ta(df):
    """Calculates additional indicators for the summary report."""
    if df is None or df.empty: return {}
    ta_summary = {}; df = df.copy(); df['Date'] = pd.to_datetime(df['Date']); df = df.sort_values('Date')
    for period in [20, 50, 100, 200]:
        if len(df) >= period:
            sma_col = f'SMA_{period}';
            df[sma_col] = calculate_sma(df['Close'], period);
            # Check if the calculated value is NaN before assigning
            sma_val = df[sma_col].iloc[-1]
            ta_summary[sma_col] = sma_val if not pd.isna(sma_val) else None
        else: ta_summary[f'SMA_{period}'] = None
    if 'Volume' in df.columns:
        if len(df) >= 20:
             df['Volume_SMA20'] = calculate_volume_sma(df, 20); latest_volume = df['Volume'].iloc[-1]; latest_vol_sma = df['Volume_SMA20'].iloc[-1]
             if not pd.isna(latest_volume) and not pd.isna(latest_vol_sma) and latest_vol_sma > 0: ta_summary['Volume_vs_SMA20_Ratio'] = latest_volume / latest_vol_sma
             else: ta_summary['Volume_vs_SMA20_Ratio'] = None
             ta_summary['Volume_SMA20'] = latest_vol_sma if not pd.isna(latest_vol_sma) else None # Handle NaN
        else: ta_summary['Volume_vs_SMA20_Ratio'] = None; ta_summary['Volume_SMA20'] = None
        if len(df) >= 6: # Need at least 6 days for a 5-day lookback plus the current day
            vol_slice = df['Volume'].iloc[-5:] # Last 5 days volume
            if not vol_slice.empty and not pd.isna(df['Volume'].iloc[-1]): # Ensure current volume and slice exist
                mean_vol_5d = vol_slice.mean()
                if not pd.isna(mean_vol_5d) and mean_vol_5d > 0: # Ensure mean is valid
                    if df['Volume'].iloc[-1] > mean_vol_5d * 1.1: ta_summary['Volume_Trend_5D'] = "Increasing"
                    elif df['Volume'].iloc[-1] < mean_vol_5d * 0.9: ta_summary['Volume_Trend_5D'] = "Decreasing"
                    else: ta_summary['Volume_Trend_5D'] = "Mixed"
                else: ta_summary['Volume_Trend_5D'] = None # Cannot determine trend if mean is zero/NaN
            else: ta_summary['Volume_Trend_5D'] = None
        else: ta_summary['Volume_Trend_5D'] = None
    lookback = 30
    if len(df) >= lookback:
        support = df['Low'].iloc[-lookback:].min()
        resistance = df['High'].iloc[-lookback:].max()
        ta_summary['Support_30D'] = support if not pd.isna(support) else None
        ta_summary['Resistance_30D'] = resistance if not pd.isna(resistance) else None
    else: ta_summary['Support_30D'] = None; ta_summary['Resistance_30D'] = None
    # Add RSI explicitly if needed elsewhere, ensure it's calculated
    if len(df) >= 15:
         df['RSI_14'] = calculate_rsi(df['Close'], 14)
         rsi_val = df['RSI_14'].iloc[-1]
         ta_summary['RSI_14'] = rsi_val if not pd.isna(rsi_val) else None
    else:
         ta_summary['RSI_14'] = None

    return ta_summary