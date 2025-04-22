# html_components.py
import pandas as pd

# Helper for icons (can be expanded)
def get_icon(type):
    # Adding specific icons if needed, otherwise using provided ones
    if type == 'up': return '<span class="icon icon-up">▲</span>'
    if type == 'down': return '<span class="icon icon-down">▼</span>'
    if type == 'neutral': return '<span class="icon icon-neutral">●</span>'
    if type == 'warning': return '<span class="icon icon-warning">⚠️</span>'
    if type == 'positive': return '<span class="icon icon-positive">➕</span>' # Can change if needed
    if type == 'negative': return '<span class="icon icon-negative">➖</span>' # Can change if needed
    if type == 'info': return '<span class="icon icon-info">ℹ️</span>'
    return '' # Default empty


def generate_metrics_summary_html(
    ticker, current_price, forecast_1m, forecast_1y,
    overall_pct_change, sentiment, volatility,
    green_days, total_days, sma_50, sma_200,
    period_label="Month"
):
    # Add icons to metrics
    forecast_1y_icon = get_icon('up' if overall_pct_change > 1 else ('down' if overall_pct_change < -1 else 'neutral'))
    sma50_comp_icon = get_icon('up' if current_price and sma_50 and current_price > sma_50 else ('down' if current_price and sma_50 and current_price < sma_50 else 'neutral')) # Corrected logic for down icon
    sma200_comp_icon = get_icon('up' if current_price and sma_200 and current_price > sma_200 else ('down' if current_price and sma_200 and current_price < sma_200 else 'neutral')) # Corrected logic for down icon
    sentiment_icon = get_icon('up' if 'Bullish' in sentiment else ('down' if 'Bearish' in sentiment else 'neutral'))

    # This HTML structure matches the CSS for individual boxes (.metric-item)
    return f"""
    <div class="metrics-summary">
        <div class="metric-item">
            <span class="metric-label">Current Price</span>
            <span class="metric-value">{f"${current_price:,.2f}" if current_price is not None else "N/A"}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">1-{period_label} Forecast</span>
            <span class="metric-value">{f"${forecast_1m:,.2f}" if forecast_1m is not None else "N/A"}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">1-Year Forecast</span>
            <span class="metric-value">{f"${forecast_1y:,.2f}" if forecast_1y is not None else "N/A"} <span class="metric-change {('trend-up' if overall_pct_change > 0 else 'trend-down' if overall_pct_change < 0 else 'trend-neutral')}">({overall_pct_change:+.1f}%)</span> {forecast_1y_icon}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">Overall Sentiment</span>
            <span class="metric-value sentiment-{sentiment.lower().replace(' ', '-')}">{sentiment_icon} {sentiment}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">Volatility (Ann.)</span>
            <span class="metric-value">{f"{volatility:.1f}%" if volatility is not None else "N/A"}</span>
        </div>
         <div class="metric-item">
            <span class="metric-label">vs SMA 50</span>
            <span class="metric-value">{f"${sma_50:,.2f}" if sma_50 is not None else "N/A"} {sma50_comp_icon}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">vs SMA 200</span>
            <span class="metric-value">{f"${sma_200:,.2f}" if sma_200 is not None else "N/A"} {sma200_comp_icon}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">Green Days (30d)</span>
            <span class="metric-value">{f"{green_days}/{total_days} ({green_days/total_days*100:.0f}%)" if green_days is not None and total_days > 0 else "N/A"}</span>
        </div>
    </div>
    <p class="disclaimer">Snapshot based on available data. Forecasts are estimates and not guarantees. Current sentiment is {sentiment}. Annualized volatility over the last 30 days was {f"{volatility:.1f}%" if volatility is not None else "N/A"}.</p>
    """

def generate_risk_analysis_html(risk_items):
    """Generates the HTML for the risk analysis section with icons."""
    if not risk_items:
        list_items = f"<li>{get_icon('info')} No major specific risk factors identified based on automated analysis. Standard market risks always apply.</li>"
    else:
        # Using <li> tags for the list items
        list_items = "".join([f"<li>{get_icon('warning')} {item}</li>" for item in risk_items])

    # Removed the outer section div as it's handled in report_generator
    return f"""
        <div class="narrative">
            <p>This section highlights potential risks identified through automated analysis of technical and fundamental data points. It is not exhaustive and doesn't replace professional financial advice.</p>
        </div>
        <ul>
            {list_items}
        </ul>
    """

def generate_monthly_forecast_table_html(monthly_forecast_table_data, ticker, forecast_time_col, period_label="Month"):
    table_rows = ""; min_max_summary = f"<p>No detailed forecast data available for {ticker}.</p>"; table_html = ""
    if not monthly_forecast_table_data.empty:
        for _, row in monthly_forecast_table_data.iterrows():
            action_class = row['Action'].lower(); roi_icon = get_icon('up' if row['Potential ROI'] > 1 else ('down' if row['Potential ROI'] < -1 else 'neutral'))
            table_rows += (f"<tr><td>{row[forecast_time_col]}</td><td>${row['Low']:,.2f}</td><td>${row['Average']:,.2f}</td><td>${row['High']:,.2f}</td>"
                           f"<td>{roi_icon} {row['Potential ROI']:+.1f}%</td><td class='action-{action_class}'>{row['Action']}</td></tr>\n")
        min_price_12m = monthly_forecast_table_data['Low'].min(); max_price_12m = monthly_forecast_table_data['High'].max(); avg_final_price = monthly_forecast_table_data['Average'].iloc[-1]
        min_max_summary = f"""<p>Over the forecast period, the price is projected to fluctuate between approximately <strong>${min_price_12m:,.2f}</strong> and <strong>${max_price_12m:,.2f}</strong>, with an average target of <strong>${avg_final_price:,.2f}</strong> at the end.</p>"""
        table_html = f"""<div class="table-container"><table><thead><tr><th>{period_label}</th><th>Min. Price</th><th>Avg. Price</th><th>Max. Price</th><th>Potential ROI</th><th>Action Signal</th></tr></thead><tbody>{table_rows}</tbody></table></div>"""
    # Removed the outer section div
    return f"""
        <div class="narrative"><p>The table shows the forecasted price range (Low, Average, High) for {ticker}. 'Potential ROI' compares the forecasted 'Average' price to the current price. 'Action Signal' is a simplified indicator based on ROI (Buy > +2%, Short < -2%, Hold otherwise).</p>
        <p>Wider ranges between 'Low' and 'High' suggest higher uncertainty or expected volatility for that period.</p>{min_max_summary}</div>{table_html}
        """


def generate_tech_analysis_summary_html(ticker, sentiment, current_price, last_date, detailed_ta_data):
    sma20 = detailed_ta_data.get('SMA_20'); sma50 = detailed_ta_data.get('SMA_50'); sma100 = detailed_ta_data.get('SMA_100'); sma200 = detailed_ta_data.get('SMA_200')
    vol_sma20 = detailed_ta_data.get('Volume_SMA20'); vol_ratio = detailed_ta_data.get('Volume_vs_SMA20_Ratio'); vol_trend = detailed_ta_data.get('Volume_Trend_5D')
    support = detailed_ta_data.get('Support_30D'); resistance = detailed_ta_data.get('Resistance_30D')
    def price_vs_ma(price, ma):
        if price is None or ma is None: return ('trend-neutral', '')
        if price > ma: return ('trend-up', f'{get_icon("up")} (Above)')
        if price < ma: return ('trend-down', f'{get_icon("down")} (Below)')
        return ('trend-neutral', f'{get_icon("neutral")} (At MA)')
    sma20_status, sma20_label = price_vs_ma(current_price, sma20); sma50_status, sma50_label = price_vs_ma(current_price, sma50)
    sma100_status, sma100_label = price_vs_ma(current_price, sma100); sma200_status, sma200_label = price_vs_ma(current_price, sma200)
    volume_text = "Volume data unavailable or insufficient."; sr_text = "Support/Resistance levels undetermined."
    if vol_ratio is not None and vol_sma20 is not None:
        vol_level = "average"; vol_icon = get_icon('neutral')
        if vol_ratio > 1.5: vol_level = "significantly above average"; vol_icon=get_icon('up')
        elif vol_ratio > 1.1: vol_level = "above average"; vol_icon=get_icon('up')
        elif vol_ratio < 0.7: vol_level = "significantly below average"; vol_icon=get_icon('down')
        elif vol_ratio < 0.9: vol_level = "below average"; vol_icon=get_icon('down')
        volume_text = f"Current volume vs 20d SMA: {vol_icon} {vol_level} ({vol_ratio:.2f}x). "
        if vol_trend: volume_text += f"5-day trend: {vol_trend}. "
    if support is not None and resistance is not None: sr_text = f"Short-term (30d): Support ~${support:,.2f}, Resistance ~${resistance:,.2f}."
    sentiment_icon = get_icon('up' if 'Bullish' in sentiment else ('down' if 'Bearish' in sentiment else 'neutral'))
    # Removed outer section div
    return f"""<div class="sentiment-indicator"><span>Overall Technical Sentiment:</span><span class="sentiment-{sentiment.lower().replace(' ', '-')}">{sentiment_icon} {sentiment}</span></div>
        <div class="narrative"><p>Summary based on data up to {last_date:%Y-%m-%d}. See individual charts below for RSI, MACD, and Bollinger Bands.</p></div><h4>Moving Averages (Daily)</h4>
        <div class="ma-summary"><div class="ma-item"><span class="label">SMA 20:</span> <span class="value">{f"${sma20:,.2f}" if sma20 is not None else "N/A"}</span> <span class="status {sma20_status}">{sma20_label}</span></div>
        <div class="ma-item"><span class="label">SMA 50:</span> <span class="value">{f"${sma50:,.2f}" if sma50 is not None else "N/A"}</span> <span class="status {sma50_status}">{sma50_label}</span></div>
        <div class="ma-item"><span class="label">SMA 100:</span> <span class="value">{f"${sma100:,.2f}" if sma100 is not None else "N/A"}</span> <span class="status {sma100_status}">{sma100_label}</span></div>
        <div class="ma-item"><span class="label">SMA 200:</span> <span class="value">{f"${sma200:,.2f}" if sma200 is not None else "N/A"}</span> <span class="status {sma200_status}">{sma200_label}</span></div></div>
        <div class="narrative"><ul><li><strong>Trend:</strong> Price relative to MAs indicates short/long-term trends. Price > MA = Bullish sign, Price < MA = Bearish sign.</li><li><strong>Crossovers:</strong> Shorter MA crossing above longer MA (e.g., 50 > 200) is a 'Golden Cross' (bullish). Opposite is 'Death Cross' (bearish).</li></ul></div>
        <h4>Volume Analysis</h4><div class="narrative"><p>{volume_text} High volume confirms price moves (up or down). Low volume suggests weak conviction.</p></div>
        <h4>Support & Resistance</h4><div class="narrative"><p>{sr_text} Prices often pause or reverse at these historical levels.</p></div>
        <p class="disclaimer">Technical indicators provide insights but are not predictive guarantees.</p>
        """

def generate_faq_html(ticker, current_price, forecast_1m, forecast_1y, overall_pct_change, monthly_forecast_table_data, risk_items, sentiment, volatility, valuation, analyst_info, period_label="Month"):
    faq_items = [] # Define list first
    # Safely format potentially None values
    safe_current_price = f"${current_price:,.2f}" if current_price is not None else "N/A"
    faq_1y_target = f"${forecast_1y:,.2f}" if forecast_1y is not None else "an undetermined level"
    faq_1y_end_period_value = f"the end of the {len(monthly_forecast_table_data) if not monthly_forecast_table_data.empty else 'N/A'}-{period_label} forecast period"

    faq_items.append((f"What is the {ticker} stock forecast for the next year?", f"Our analysis forecasts {ticker} stock to potentially reach an average price of approximately <strong>{faq_1y_target}</strong> by {faq_1y_end_period_value}, representing a potential <strong>{overall_pct_change:+.1f}%</strong> change from the current price ({safe_current_price}). Note that this is an estimate with inherent uncertainty."))
    up_down = "go up" if overall_pct_change > 1 else "go down" if overall_pct_change < -1 else "stay relatively flat"
    faq_items.append((f"Will {ticker} stock go up or down?", f"Based on the {len(monthly_forecast_table_data) if not monthly_forecast_table_data.empty else 'N/A'}-{period_label} average forecast trend ({overall_pct_change:+.1f}% change), the projection suggests the stock might {up_down} over this period. However, market conditions change, and the forecast includes a range of possibilities (see 'Low' and 'High' in the table)."))
    buy_lean = ('positive' if sentiment.lower().find('bullish') != -1 else ('negative' if sentiment.lower().find('bearish') != -1 else 'neutral')); is_good_buy_text = f"The current overall technical sentiment is <strong>{sentiment}</strong>, and the {len(monthly_forecast_table_data) if not monthly_forecast_table_data.empty else 'N/A'}-{period_label} forecast shows a {overall_pct_change:+.1f}% potential change. This suggests a {buy_lean} leaning based on our automated analysis. "
    if len(risk_items) > 0: is_good_buy_text += f"However, be aware of the {len(risk_items)} potential risk factor(s) highlighted. "
    is_good_buy_text += "This is <strong>not investment advice</strong>. Review all sections (fundamentals, technicals, risks) and consider consulting a financial advisor."
    faq_items.append((f"Is {ticker} a good stock to buy now?", is_good_buy_text))
    if volatility is not None:
        vol_level = "low"; vol_icon = get_icon('neutral');
        if volatility > 50: vol_level = "very high"; vol_icon=get_icon('warning')
        elif volatility > 30: vol_level = "high"; vol_icon=get_icon('warning')
        elif volatility > 15: vol_level = "moderate"; vol_icon=get_icon('neutral')
        faq_items.append((f"How volatile is {ticker} stock?", f"The recent annualized volatility is {vol_icon} {volatility:.1f}%, considered {vol_level}. This suggests the stock price has experienced {vol_level} fluctuations recently, which may continue."))
    pe_ratio = valuation.get('Trailing P/E', 'N/A')
    if pe_ratio != 'N/A' and isinstance(pe_ratio, str) and 'x' in pe_ratio :
         try: pe_val = float(pe_ratio.replace('x','')); val_desc = "relatively average"; val_icon = get_icon('neutral')
         except ValueError: pe_val = None; val_desc = "N/A"; val_icon=""
         if pe_val is not None:
             if pe_val > 50 : val_desc = "quite high (suggesting high growth expectations or potential overvaluation)"; val_icon=get_icon('warning')
             elif pe_val > 25 : val_desc = "moderately high"; val_icon=get_icon('warning')
             elif pe_val < 15 and pe_val > 0 : val_desc = "relatively low (suggesting potential undervaluation or lower growth expectations)"; val_icon=get_icon('positive')
             elif pe_val <= 0 : val_desc = "negative (company may not be profitable currently)"; val_icon=get_icon('negative')
             faq_items.append((f"Is {ticker} considered expensive based on P/E ratio?", f"The Trailing P/E ratio is {val_icon} {pe_ratio}. This is considered {val_desc} compared to general market benchmarks. A high P/E often implies investors expect higher earnings growth in the future."))
    analyst_rec = analyst_info.get('Recommendation', 'N/A'); analyst_target = analyst_info.get('Mean Target Price', 'N/A'); num_analysts = analyst_info.get('Number of Analyst Opinions', 'N/A')
    if analyst_rec != 'N/A' and not ('N/A' in str(analyst_rec)): # Check string representation
        rec_icon = get_icon('up' if 'buy' in analyst_rec.lower() else ('down' if 'sell' in analyst_rec.lower() else 'neutral'))
        faq_items.append((f"What do Wall Street analysts think of {ticker}?", f"The consensus recommendation from {num_analysts} analysts is {rec_icon} <strong>{analyst_rec}</strong>. Their average price target is {analyst_target}. Analyst opinions provide context but aren't always accurate."))
    details_html = ""
    for question, answer in faq_items: details_html += f"<details><summary>{question}</summary><p>{answer}</p></details>"
    # Removed outer section div
    return f"{details_html}"


# --- UPDATED: Overall Conclusion Function with List Formatting ---
def generate_overall_conclusion_html(ticker, sentiment, overall_pct_change, forecast_1y, current_price, risk_items, valuation, analyst_info, detailed_ta_data):
    """Generates the overall conclusion section with proper list formatting."""
    points = []

    # --- Short-Term Outlook ---
    st_sentiment_icon = get_icon('up' if 'Bullish' in sentiment else ('down' if 'Bearish' in sentiment else 'neutral'))
    points.append({
        "term": "Short-Term",
        "icon": st_sentiment_icon,
        "text": f"Current technical sentiment is <strong>{sentiment}</strong>."
    })

    sma20 = detailed_ta_data.get('SMA_20')
    sma50 = detailed_ta_data.get('SMA_50')
    st_trend = "mixed"
    st_icon = get_icon('neutral')
    trend_detail = ""
    if current_price and sma20 and sma50:
        price_vs_20 = current_price > sma20
        price_vs_50 = current_price > sma50
        cross_20_50_text = ""
        if sma20 > sma50: cross_20_50_text = "SMA20 is currently above SMA50 (typically bullish)."
        elif sma50 > sma20: cross_20_50_text = "SMA50 is currently above SMA20 (typically bearish)."

        if price_vs_20 and price_vs_50:
             st_trend = "positive"
             st_icon = get_icon('up')
             trend_detail = f"Price is above key short/medium-term moving averages (SMA20: ${sma20:,.2f}, SMA50: ${sma50:,.2f}). {cross_20_50_text}"
        elif not price_vs_20 and not price_vs_50:
             st_trend = "negative"
             st_icon = get_icon('down')
             trend_detail = f"Price is below key short/medium-term moving averages (SMA20: ${sma20:,.2f}, SMA50: ${sma50:,.2f}). {cross_20_50_text}"
        else:
            st_trend = "mixed"
            st_icon = get_icon('neutral')
            trend_detail = f"Price is {'above' if price_vs_20 else 'below'} SMA20 (${sma20:,.2f}) and {'above' if price_vs_50 else 'below'} SMA50 (${sma50:,.2f}). {cross_20_50_text}"

    points.append({
         "term": "Short-Term",
         "icon": st_icon,
         "text": f"Immediate trend appears <strong>{st_trend}</strong>. {trend_detail}"
    })

    support = detailed_ta_data.get('Support_30D')
    resistance = detailed_ta_data.get('Resistance_30D')
    if support and resistance:
         points.append({
              "term": "Short-Term",
              "icon": get_icon('info'),
              "text": f"Watch key levels: Support ~${support:,.2f}, Resistance ~${resistance:,.2f}."
         })
    latest_rsi = detailed_ta_data.get('RSI')
    if latest_rsi is not None and not pd.isna(latest_rsi):
        rsi_level = "neutral (30-70)"
        rsi_icon = get_icon('neutral')
        if latest_rsi > 70: rsi_level = "overbought (>70)"; rsi_icon = get_icon('warning')
        elif latest_rsi < 30: rsi_level = "oversold (<30)"; rsi_icon = get_icon('positive')
        points.append({
            "term": "Short-Term",
            "icon": rsi_icon,
            "text": f"Relative Strength Index (RSI) is currently {latest_rsi:.1f}, indicating {rsi_level} conditions."
        })

    # --- Long-Term Outlook ---
    lt_icon = get_icon('up' if overall_pct_change > 1 else ('down' if overall_pct_change < -1 else 'neutral'))
    safe_forecast_1y = f"${forecast_1y:,.2f}" if forecast_1y is not None else "N/A"
    points.append({
        "term": "Long-Term",
        "icon": lt_icon,
        "text": f"The 1-year average price forecast suggests a potential change of <strong>{overall_pct_change:+.1f}%</strong> to ≈{safe_forecast_1y}."
    })

    # Valuation point (Improved Logic from before)
    pe_ratio = valuation.get('Trailing P/E', 'N/A')
    forward_pe = valuation.get('Forward P/E', 'N/A')
    peg_ratio = valuation.get('PEG Ratio', 'N/A')
    ps_ratio = valuation.get('Price/Sales (TTM)', 'N/A')
    val_text = "" # Start empty, build the text
    val_icon = get_icon('neutral')
    metrics_used = []
    try:
        if peg_ratio != 'N/A' and 'x' in peg_ratio:
            peg_val = float(peg_ratio.replace('x',''))
            if peg_val < 1.0 : val_text += f"Valuation potentially attractive based on PEG ({peg_ratio})."; val_icon=get_icon('positive'); metrics_used.append("PEG")
            elif peg_val > 2.0 : val_text += f"Valuation potentially high based on PEG ({peg_ratio})."; val_icon=get_icon('warning'); metrics_used.append("PEG")
            else: val_text += f"Valuation reasonable based on PEG ({peg_ratio})."; metrics_used.append("PEG")
        if forward_pe != 'N/A' and 'x' in forward_pe and ("PEG" not in metrics_used or val_icon == get_icon('neutral')):
             fpe_val = float(forward_pe.replace('x',''))
             sep = " " if val_text else ""
             if fpe_val < 15 and fpe_val > 0: val_text += f"{sep}Forward P/E ({forward_pe}) suggests potential value."; val_icon=get_icon('positive') if val_icon == get_icon('neutral') else val_icon; metrics_used.append("Fwd PE")
             elif fpe_val > 35: val_text += f"{sep}Forward P/E ({forward_pe}) appears elevated."; val_icon=get_icon('warning') if val_icon == get_icon('neutral') else val_icon; metrics_used.append("Fwd PE")
             else: val_text += f"{sep}Forward P/E ({forward_pe}) is moderate."; metrics_used.append("Fwd PE")
        elif pe_ratio != 'N/A' and 'x' in pe_ratio and not metrics_used:
            pe_val = float(pe_ratio.replace('x',''))
            if pe_val < 15 and pe_val > 0: val_text = f"Valuation appears potentially low based on P/E ratio ({pe_ratio})."; val_icon=get_icon('positive'); metrics_used.append("Trailing PE")
            elif pe_val > 40: val_text = f"Valuation appears high based on P/E ratio ({pe_ratio})."; val_icon=get_icon('warning'); metrics_used.append("Trailing PE")
            else: val_text = f"Valuation based on P/E ratio ({pe_ratio}) is moderate."; metrics_used.append("Trailing PE")
        if ps_ratio != 'N/A' and 'x' in ps_ratio and val_icon == get_icon('neutral'):
            ps_val = float(ps_ratio.replace('x',''))
            sep = " " if val_text else ""
            if ps_val > 10 : val_text += f"{sep}Price/Sales ({ps_ratio}) is also high." ; val_icon=get_icon('warning')
            elif ps_val < 2 : val_text += f"{sep}Price/Sales ({ps_ratio}) is relatively low." ; val_icon=get_icon('positive')
    except (ValueError, TypeError):
        val_text = "Valuation metrics parsing error."
        val_icon = get_icon('warning')
    if not metrics_used:
        val_text = "Limited valuation data available."
        val_icon = get_icon('neutral')
    points.append({ "term": "Long-Term", "icon": val_icon, "text": val_text })

    # Analyst rating point
    analyst_rec = analyst_info.get('Recommendation', 'N/A')
    if analyst_rec != 'N/A' and not ('N/A' in str(analyst_rec)): # Check string representation
        rec_icon = get_icon('up' if 'buy' in analyst_rec.lower() else ('down' if 'sell' in analyst_rec.lower() else 'neutral'))
        num_analysts = analyst_info.get('Number of Analyst Opinions', 'N/A')
        analyst_text = f"Analyst consensus ({num_analysts} analysts) is <strong>{analyst_rec}</strong>."
        mean_target = analyst_info.get('Mean Target Price', 'N/A')
        if mean_target != 'N/A': analyst_text += f" Average target: {mean_target}."
        points.append({ "term": "Long-Term", "icon": rec_icon, "text": analyst_text })

    # --- Generate HTML using standard UL/LI ---
    # Use list-style: none in CSS and rely on flexbox for icon alignment
    short_term_html = "".join([f"<li><span class='icon'>{p['icon']}</span><span>{p['text']}</span></li>" for p in points if p['term'] == 'Short-Term'])
    long_term_html = "".join([f"<li><span class='icon'>{p['icon']}</span><span>{p['text']}</span></li>" for p in points if p['term'] == 'Long-Term'])

    # Removed the outer section div
    return f"""
        <div class="conclusion-columns">
            <div class="conclusion-column">
                <h3>Short-Term Outlook</h3>
                <ul>{short_term_html}</ul>
            </div>
            <div class="conclusion-column">
                <h3>Long-Term Outlook (1 Year)</h3>
                <ul>{long_term_html}</ul>
            </div>
        </div>
         <p class="disclaimer">{get_icon('warning')} This summary combines automated analysis and forecasts. It is not investment advice. Consider all report sections and consult a professional.</p>
    """


def generate_final_notes_html(generation_time):
    """Generates the final disclaimer and timestamp."""
    try:
        tz_name = generation_time.tzname()
        time_str = f"{generation_time:%Y-%m-%d %H:%M:%S %Z}"
    except:
         time_str = f"{generation_time:%Y-%m-%d %H:%M:%S}"

    # Removed the outer section div
    return f"""
             <p>This report was automatically generated on {time_str}.</p>
             <p class="disclaimer"><strong>Disclaimer:</strong> This report is for informational purposes only and does not constitute investment advice or a recommendation to buy, sell, or hold any security. Financial markets are volatile and past performance is not indicative of future results. Forecasts and analyses are based on algorithms and historical data, which may contain errors and are subject to change without notice. Always conduct your own thorough research and consult with a qualified financial advisor before making any investment decisions.</p>
    """

# --- Functions to generate *individual* fundamental sections ---
# These functions now return *only the inner content* for a section

def generate_profile_html(profile):
    website_link = profile.get('Website', '#');
    if not website_link.startswith(('http://', 'https://')) and website_link != '#': website_link = f"http://{website_link}"
    # Removed outer section div and H2
    return f"""<div class="profile-grid">
        <div class="profile-item"><span>Sector:</span>{profile.get('Sector', 'N/A')}</div><div class="profile-item"><span>Industry:</span>{profile.get('Industry', 'N/A')}</div>
        <div class="profile-item"><span>Market Cap:</span>{profile.get('Market Cap', 'N/A')}</div><div class="profile-item"><span>Employees:</span>{profile.get('Employees', 'N/A')}</div>
        <div class="profile-item"><span>Website:</span><a href="{website_link}" target="_blank" rel="noopener noreferrer">{profile.get('Website', 'N/A')}</a></div></div>
        <div class="business-summary"><h4>Business Summary</h4><p>{profile.get('Summary', 'No summary available.')}</p></div>"""

def generate_metrics_section_content(metrics):
    """Helper to generate table body content for metrics."""
    rows = "".join([f"<tr><td>{k}</td><td>{v}</td></tr>" for k,v in metrics.items() if v != 'N/A']);
    if not rows: rows = "<tr><td colspan='2'>No data available for this section.</td></tr>"
    return f"""<div class="table-container"><table class="metrics-table"><tbody>{rows}</tbody></table></div>"""

def generate_valuation_metrics_html(valuation):
    # Removed outer section div and H2
    return generate_metrics_section_content(valuation)

def generate_financial_health_html(financial_health):
    # Removed outer section div and H2
    return generate_metrics_section_content(financial_health)

def generate_profitability_html(profitability):
    # Removed outer section div and H2
    return generate_metrics_section_content(profitability)

def generate_dividends_splits_html(dividends):
    # Removed outer section div and H2
    return generate_metrics_section_content(dividends)

def generate_analyst_info_html(analyst):
    valid_data = {k:v for k,v in analyst.items() if v != 'N/A' and not ('N/A' in str(v))};
    if not valid_data: return "<p>No specific analyst data available.</p>" # Return paragraph if no data
    # Removed outer section div and H2
    html = '<div class="analyst-grid">'
    if 'Recommendation' in valid_data: html += f'<div class="analyst-item"><span>Recommendation:</span>{valid_data["Recommendation"]}</div>'
    if 'Mean Target Price' in valid_data: html += f'<div class="analyst-item"><span>Mean Target:</span>{valid_data["Mean Target Price"]}</div>'
    if 'High Target Price' in valid_data: html += f'<div class="analyst-item"><span>High Target:</span>{valid_data["High Target Price"]}</div>'
    if 'Low Target Price' in valid_data: html += f'<div class="analyst-item"><span>Low Target:</span>{valid_data["Low Target Price"]}</div>'
    if 'Number of Analyst Opinions' in valid_data: html += f'<div class="analyst-item"><span>Analysts Covering:</span>{valid_data["Number of Analyst Opinions"]}</div>'
    html += '</div>'
    return html

def generate_news_html(news):
    if not news: return """<p>No recent news headlines found.</p>""" # Return paragraph if no data
    # Removed outer section div and H2
    news_items = "";
    for item in news:
         link = item.get('link', '#');
         if not link.startswith(('http://', 'https://')) and link != '#': link = f"http://{link}"
         news_items += f"""<div class="news-item"><h4><a href="{link}" target="_blank" rel="noopener noreferrer">{item.get('title', 'N/A')}</a></h4>
             <div class="news-meta"><span>{item.get('publisher', 'N/A')}</span><span>{item.get('published', 'N/A')}</span></div></div>"""
    return f"""<div class="news-container">{news_items}</div>"""