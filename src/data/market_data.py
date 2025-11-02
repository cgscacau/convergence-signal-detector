"""
Download de dados - Versão simplificada para Streamlit Cloud
"""
import yfinance as yf
import pandas as pd
import streamlit as st
import warnings
warnings.filterwarnings('ignore')

class MarketDataLoader:
    
    @staticmethod
    def format_ticker_b3(ticker):
        ticker = str(ticker).upper().strip()
        if not ticker.endswith('.SA'):
            return f"{ticker}.SA"
        return ticker
    
    @st.cache_data(ttl=1800, show_spinner=False)
    def download_data(_self, ticker, period='1y', interval='1d'):
        try:
            ticker_fmt = _self.format_ticker_b3(ticker)
            stock = yf.Ticker(ticker_fmt)
            df = stock.history(period=period, interval=interval)
            
            if df is None or df.empty or len(df) < 5:
                return None
            
            if hasattr(df.index, 'tz') and df.index.tz:
                df.index = df.index.tz_localize(None)
            
            df.columns = [c.title() for c in df.columns]
            df = df.dropna(subset=['Close'])
            
            return df if len(df) >= 5 else None
        except:
            return None
    
    def get_daily_data(self, ticker, period='1y'):
        return self.download_data(ticker, period, '1d')
    
    def get_weekly_data(self, ticker, period='2y'):
        daily = self.get_daily_data(ticker, period)
        if daily is not None and not daily.empty:
            return self.resample_to_weekly(daily)
        return self.download_data(ticker, period, '1wk')
    
    @staticmethod
    def resample_to_weekly(daily_df):
        if daily_df is None or daily_df.empty:
            return None
        try:
            agg = {'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}
            weekly = daily_df.resample('W-FRI').agg(agg)
            return weekly.dropna(how='all') if not weekly.empty else None
        except:
            return None
    
    @staticmethod
    def validate_dataframe(df):
        if df is None or df.empty:
            return False
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        return all(c in df.columns for c in required) and len(df) >= 5
