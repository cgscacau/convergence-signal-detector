"""
Download de dados de mercado usando yfinance
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


class MarketDataLoader:
    """Classe para download de dados de mercado"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def format_ticker_b3(ticker):
        """
        Formata ticker para padrão Yahoo Finance B3
        
        Args:
            ticker (str): Ticker no formato B3 (ex: PETR4)
        
        Returns:
            str: Ticker formatado para Yahoo Finance (ex: PETR4.SA)
        """
        if not ticker.endswith('.SA'):
            return f"{ticker}.SA"
        return ticker
    
    @st.cache_data(ttl=1800, show_spinner=False)  # Cache 30min
    def download_data(_self, ticker, period='1y', interval='1d'):
        """
        Baixa dados históricos de um ativo
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período ('1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'max')
            interval (str): Intervalo ('1d', '1wk', '1mo')
        
        Returns:
            pd.DataFrame: DataFrame com OHLCV ou None se falhar
        """
        try:
            # Formata ticker para B3
            ticker_yf = _self.format_ticker_b3(ticker)
            
            # Download (removido show_errors que não existe)
            data = yf.download(
                ticker_yf,
                period=period,
                interval=interval,
                progress=False
            )
            
            if data.empty:
                return None
            
            # Remove MultiIndex se houver
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            
            # Garante nomes de colunas em inglês
            column_mapping = {
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume',
                'Adj Close': 'Adj Close'
            }
            
            # Renomeia apenas colunas que existem
            existing_cols = {k: v for k, v in column_mapping.items() if k in data.columns}
            if existing_cols:
                data = data.rename(columns=existing_cols)
            
            # Remove linhas com NaN
            data = data.dropna()
            
            if data.empty:
                return None
            
            return data
            
        except Exception as e:
            # Silencioso - não mostra warning aqui, será tratado no app
            return None
    
    def download_multiple(self, tickers, period='1y', interval='1d', show_progress=True):
        """
        Baixa dados de múltiplos ativos
        
        Args:
            tickers (list): Lista de tickers
            period (str): Período de dados
            interval (str): Intervalo dos dados
            show_progress (bool): Mostrar barra de progresso
        
        Returns:
            dict: Dicionário {ticker: DataFrame}
        """
        data_dict = {}
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if show_progress:
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"Baixando dados: {ticker} ({i+1}/{total})")
            
            data = self.download_data(ticker, period, interval)
            
            if data is not None and not data.empty:
                data_dict[ticker] = data
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return data_dict
    
    def get_daily_data(self, ticker, period='1y'):
        """
        Retorna dados diários
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período
        
        Returns:
            pd.DataFrame: Dados diários
        """
        return self.download_data(ticker, period=period, interval='1d')
    
    def get_weekly_data(self, ticker, period='2y'):
        """
        Retorna dados semanais
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período
        
        Returns:
            pd.DataFrame: Dados semanais
        """
        return self.download_data(ticker, period=period, interval='1wk')
    
    def get_multi_timeframe(self, ticker, period='2y'):
        """
        Retorna dados em múltiplos timeframes
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período
        
        Returns:
            dict: {'daily': DataFrame, 'weekly': DataFrame}
        """
        daily = self.get_daily_data(ticker, period)
        weekly = self.get_weekly_data(ticker, period)
        
        return {
            'daily': daily,
            'weekly': weekly
        }
    
    @staticmethod
    def resample_to_weekly(daily_df):
        """
        Converte dados diários para semanais
        
        Args:
            daily_df (pd.DataFrame): DataFrame com dados diários
        
        Returns:
            pd.DataFrame: DataFrame com dados semanais
        """
        if daily_df is None or daily_df.empty:
            return None
        
        weekly = daily_df.resample('W').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        })
        
        if 'Adj Close' in daily_df.columns:
            weekly['Adj Close'] = daily_df['Adj Close'].resample('W').last()
        
        return weekly.dropna()
    
    @staticmethod
    def get_period_dates(period_str):
        """
        Converte string de período para datas
        
        Args:
            period_str (str): Período ('6mo', '1y', '2y', etc)
        
        Returns:
            tuple: (start_date, end_date)
        """
        end_date = datetime.now()
        
        period_map = {
            '1mo': timedelta(days=30),
            '3mo': timedelta(days=90),
            '6mo': timedelta(days=180),
            '1y': timedelta(days=365),
            '2y': timedelta(days=730),
            '3y': timedelta(days=1095),
            '4y': timedelta(days=1460),
            '5y': timedelta(days=1825),
            '10y': timedelta(days=3650),
        }
        
        if period_str in period_map:
            start_date = end_date - period_map[period_str]
        else:
            start_date = end_date - timedelta(days=365)
        
        return start_date, end_date
    
    def check_data_availability(self, ticker):
        """
        Verifica se dados estão disponíveis para o ticker
        
        Args:
            ticker (str): Ticker do ativo
        
        Returns:
            bool: True se dados disponíveis, False caso contrário
        """
        data = self.download_data(ticker, period='1mo', interval='1d')
        return data is not None and not data.empty
    
    def filter_available_tickers(self, tickers, show_progress=True):
        """
        Filtra apenas tickers com dados disponíveis
        
        Args:
            tickers (list): Lista de tickers
            show_progress (bool): Mostrar progresso
        
        Returns:
            list: Lista de tickers com dados disponíveis
        """
        available = []
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if show_progress:
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"Verificando: {ticker} ({i+1}/{total})")
            
            if self.check_data_availability(ticker):
                available.append(ticker)
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return available
