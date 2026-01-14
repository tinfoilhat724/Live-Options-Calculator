import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Live Options Analyzer", layout="wide")

st.title("🦅 Live Market Options Analyzer")

# --- SIDEBAR: LOOKUP ---
st.sidebar.header("1. Stock Lookup")
ticker_input = st.sidebar.text_input("Enter Ticker (e.g., AAPL, TSLA, NVDA)", value="AAPL").upper()

if ticker_input:
    stock = yf.Ticker(ticker_input)
    
    try:
        # Get Current Stock Price
        current_price = stock.history(period="1d")['Close'].iloc[-1]
        st.sidebar.metric(f"{ticker_input} Spot Price", f"${current_price:.2f}")

        # Get Available Expiration Dates
        expirations = stock.options
        if not expirations:
            st.error("No options available for this ticker.")
            st.stop()
            
        selected_expiry = st.sidebar.selectbox("Select Expiration Date", expirations)

        # Fetch Option Chain for selected date
        chain = stock.option_chain(selected_expiry)
        calls = chain.calls

        # Filter for relevant strikes (near the current price)
        calls = calls[(calls['strike'] >= current_price * 0.7) & (calls['strike'] <= current_price * 1.3)]

        st.sidebar.header("2. Select Contract")
        selected_strike = st.sidebar.selectbox("Select Strike Price", calls['strike'].tolist())
        
        # Get live data for selected strike
        opt_data = calls[calls['strike'] == selected_strike].iloc[0]
        live_premium = (opt_data['bid'] + opt_data['ask']) / 2
        
        st.sidebar.write(f"**Live Mid Price:** ${live_premium:.2f}")
        st.sidebar.write(f"**Implied Volatility:** {opt_data['impliedVolatility']*100:.1f}%")

        # --- MAIN DISPLAY ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Trade Configuration")
            # Allow user to override live premium if they want to test a different entry
            entry_price = st.number_input("Entry Premium ($)", value=float(live_premium))
            num_contracts = st.number_input("Contracts", value=1, min_value=1)
            
            total_risk = entry_price * 100 * num_contracts
            breakeven = selected_strike + entry_price
            
            st.metric("Total Risk (Capital)", f"${total_risk:,.2f}")
            st.metric("Breakeven at Expiry", f"${breakeven:.2f}")

        with col2:
            st.subheader("Profit Scenarios")
            target = st.number_input("Target Stock Price ($)", value=round(current_price * 1.1, 2))
            
            gross_profit = (max(0, target - selected_strike) - entry_price) * 100 * num_contracts
            roi = (gross_profit / total_risk) * 100 if total_risk > 0 else 0
            
            st.metric("Projected Profit", f"${gross_profit:,.2f}", delta=f"{roi:.1f}% ROI")

        # --- VISUALIZATION ---
        st.divider()
        st.subheader(f"P/L Chart for {ticker_input} ${selected_strike} Call Expiring {selected_expiry}")
        
        prices = np.linspace(current_price * 0.8, current_price * 1.2, 100)
        pnl = [((max(0, p - selected_strike) - entry_price) * 100 * num_contracts) for p in prices]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=prices, y=pnl, fill='tozeroy', line=dict(color='gold', width=3)))
        fig.add_vline(x=breakeven, line_dash="dash", line_color="white", annotation_text="Breakeven")
        fig.add_hline(y=0, line_color="gray")
        fig.update_layout(template="plotly_dark", xaxis_title="Stock Price", yaxis_title="Profit / Loss ($)")
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching data: {e}")