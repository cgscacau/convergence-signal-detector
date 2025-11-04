"""
Download de dados de mercado usando yfinance
Versão otimizada para download em lote
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import warnings
import logging

# Suprime todos os warnings e logs do yfinance
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)


class MarketDataLoader:
    """Classe para download de dados de mercado"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def format_ticker_b3(ticker):
        """
        Formata ticker para padrão Yahoo Finance B3
        APENAS adiciona .SA se for ticker brasileiro (sem sufixos ou hífens)
        
        Args:
            ticker (str): Ticker (ex: PETR4, AAPL, BTC-USD)
        
        Returns:
            str: Ticker formatado para Yahoo Finance
        """
        # Se já tem sufixo (.SA, -USD, etc), não adiciona nada
        if '.' in ticker or '-' in ticker:
            return ticker
        
        # Se é ticker brasileiro puro (4 letras + número), adiciona .SA
        # Tickers americanos geralmente não seguem esse padrão
        if len(ticker) >= 5 and ticker[-1].isdigit():
            return f"{ticker}.SA"
        
        # Tickers americanos puros (AAPL, MSFT, etc) - retorna sem modificar
        return ticker
    
    @st.cache_data(ttl=1800, show_spinner=False)
    def download_single_ticker(_self, ticker, period='1y', interval='1d'):
        """
        Baixa dados de UM ticker usando Ticker API (mais confiável)
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período
            interval (str): Intervalo
        
        Returns:
            pd.DataFrame: DataFrame com OHLCV ou None
        """
        try:
            ticker_yf = _self.format_ticker_b3(ticker)
            
            # Usa Ticker().history() - método mais estável
            stock = yf.Ticker(ticker_yf)
            
            # Download direto via history (sem show_errors)
            data = stock.history(
                period=period,
                interval=interval,
                auto_adjust=False,
                actions=False
            )
            
            if data is None or data.empty:
                return None
            
            # Padroniza colunas
            if not data.columns.empty:
                data.columns = data.columns.str.title()
            
            # Remove timezone
            if hasattr(data.index, 'tz') and data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            
            # Limpa dados
            data = data.dropna(how='all')
            
            # Valida mínimo de dados
            if len(data) < 10:
                return None
            
            return data
            
        except Exception:
            return None
    
    def download_data(self, ticker, period='1y', interval='1d'):
        """
        Método público para download (compatibilidade)
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período
            interval (str): Intervalo
        
        Returns:
            pd.DataFrame: DataFrame com OHLCV
        """
        return self.download_single_ticker(ticker, period, interval)
    
    def download_multiple(self, tickers, period='1y', interval='1d', show_progress=True):
        """
        Baixa dados de múltiplos ativos de forma otimizada
        
        Args:
            tickers (list): Lista de tickers
            period (str): Período
            interval (str): Intervalo  
            show_progress (bool): Mostrar progresso
        
        Returns:
            dict: {ticker: DataFrame}
        """
        results = {}
        failed = []
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        total = len(tickers)
        
        # Processa um por um (mais estável que batch)
        for i, ticker in enumerate(tickers):
            if show_progress:
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"📊 Baixando: {ticker} ({i+1}/{total})")
            
            try:
                data = self.download_single_ticker(ticker, period, interval)
                
                if data is not None and not data.empty and len(data) >= 10:
                    results[ticker] = data
                else:
                    failed.append(ticker)
                    
            except Exception:
                failed.append(ticker)
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return results
    
    def get_daily_data(self, ticker, period='1y'):
        """Retorna dados diários"""
        return self.download_single_ticker(ticker, period=period, interval='1d')
    
    def get_weekly_data(self, ticker, period='2y'):
        """Retorna dados semanais"""
        # Baixa diários e converte (mais confiável)
        daily = self.get_daily_data(ticker, period)
        
        if daily is not None and not daily.empty:
            return self.resample_to_weekly(daily)
        
        # Fallback: tenta direto semanal
        return self.download_single_ticker(ticker, period=period, interval='1wk')
    
    def get_multi_timeframe(self, ticker, period='2y'):
        """
        Retorna dados em múltiplos timeframes
        
        Args:
            ticker (str): Ticker
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
            daily_df (pd.DataFrame): Dados diários
        
        Returns:
            pd.DataFrame: Dados semanais
        """
        if daily_df is None or daily_df.empty:
            return None
        
        try:
            # Aggregation
            agg_dict = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }
            
            if 'Adj Close' in daily_df.columns:
                agg_dict['Adj Close'] = 'last'
            
            # Resample para sexta-feira
            weekly = daily_df.resample('W-FRI').agg(agg_dict)
            
            # Limpa
            weekly = weekly.dropna(how='all')
            
            if weekly.empty:
                return None
            
            return weekly
            
        except Exception:
            return None
    
    @staticmethod
    def validate_dataframe(df):
        """
        Valida DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame para validar
        
        Returns:
            bool: True se válido
        """
        if df is None or df.empty:
            return False
        
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Checa colunas
        has_cols = all(col in df.columns for col in required)
        
        # Checa quantidade
        has_data = len(df) >= 10
        
        # Checa valores
        has_values = not df[required].isna().all().any()
        
        return has_cols and has_data and has_values
    
    @staticmethod
    def get_period_dates(period_str):
        """Converte período string para datas"""
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
        
        delta = period_map.get(period_str, timedelta(days=365))
        start_date = end_date - delta
        
        return start_date, end_date
    
    def check_data_availability(self, ticker):
        """Verifica se ticker tem dados"""
        data = self.download_single_ticker(ticker, period='1mo', interval='1d')
        return self.validate_dataframe(data)
    
    def filter_available_tickers(self, tickers, show_progress=True):
        """Filtra tickers com dados disponíveis"""
        available = []
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if show_progress:
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"🔍 Verificando: {ticker} ({i+1}/{total})")
            
            if self.check_data_availability(ticker):
                available.append(ticker)
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return available
