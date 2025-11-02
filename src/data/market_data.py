"""
Download de dados de mercado usando yfinance
Versão robusta com múltiplas abordagens
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')


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
        Baixa dados históricos de um ativo usando Ticker API
        
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
            
            # MÉTODO 1: Usando Ticker().history() - Mais robusto
            stock = yf.Ticker(ticker_yf)
            data = stock.history(period=period, interval=interval)
            
            if data.empty:
                return None
            
            # Garante nomes de colunas em inglês padrão
            data.columns = data.columns.str.title()
            
            # Remove timezone do índice se houver
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            
            # Remove linhas com NaN
            data = data.dropna()
            
            if data.empty or len(data) < 10:  # Mínimo de 10 pontos de dados
                return None
            
            return data
            
        except Exception as e:
            # Tenta método alternativo
            try:
                return _self._download_fallback(ticker, period, interval)
            except:
                return None
    
    @staticmethod
    def _download_fallback(ticker, period, interval):
        """
        Método alternativo usando download() sem parâmetros problemáticos
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período
            interval (str): Intervalo
        
        Returns:
            pd.DataFrame: DataFrame com OHLCV ou None
        """
        try:
            ticker_yf = f"{ticker}.SA" if not ticker.endswith('.SA') else ticker
            
            # Download básico
            data = yf.download(
                tickers=ticker_yf,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                repair=True
            )
            
            if data.empty:
                return None
            
            # Remove MultiIndex se houver
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            
            # Padroniza nomes
            data.columns = data.columns.str.title()
            
            # Remove timezone
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            
            # Limpa dados
            data = data.dropna()
            
            if data.empty or len(data) < 10:
                return None
            
            return data
            
        except:
            return None
    
    def download_multiple(self, tickers, period='1y', interval='1d', show_progress=True):
        """
        Baixa dados de múltiplos ativos com retry automático
        
        Args:
            tickers (list): Lista de tickers
            period (str): Período de dados
            interval (str): Intervalo dos dados
            show_progress (bool): Mostrar barra de progresso
        
        Returns:
            dict: Dicionário {ticker: DataFrame}
        """
        data_dict = {}
        failed = []
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        total = len(tickers)
        
        for i, ticker in enumerate(tickers):
            if show_progress:
                progress = (i + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"📊 Baixando: {ticker} ({i+1}/{total})")
            
            data = self.download_data(ticker, period, interval)
            
            if data is not None and not data.empty and len(data) >= 10:
                data_dict[ticker] = data
            else:
                failed.append(ticker)
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
            
            if failed and len(failed) < len(tickers):
                st.info(f"ℹ️ {len(failed)} ativos sem dados: {', '.join(failed[:5])}{'...' if len(failed) > 5 else ''}")
        
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
        # Para semanais, primeiro baixa diários e resample
        # Mais confiável que pedir direto semanal
        daily = self.get_daily_data(ticker, period)
        
        if daily is None or daily.empty:
            # Tenta direto semanal como fallback
            return self.download_data(ticker, period=period, interval='1wk')
        
        return self.resample_to_weekly(daily)
    
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
        
        try:
            # Define aggregation correta
            agg_dict = {
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }
            
            # Adiciona Adj Close se existir
            if 'Adj Close' in daily_df.columns:
                agg_dict['Adj Close'] = 'last'
            
            # Resample para semanal (fecha na sexta-feira)
            weekly = daily_df.resample('W-FRI').agg(agg_dict)
            
            # Remove linhas com NaN
            weekly = weekly.dropna()
            
            if weekly.empty:
                return None
            
            return weekly
            
        except Exception as e:
            return None
    
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
        return data is not None and not data.empty and len(data) >= 5
    
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
                status_text.text(f"🔍 Verificando: {ticker} ({i+1}/{total})")
            
            if self.check_data_availability(ticker):
                available.append(ticker)
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return available
    
    @staticmethod
    def validate_dataframe(df):
        """
        Valida se DataFrame tem estrutura correta
        
        Args:
            df (pd.DataFrame): DataFrame para validar
        
        Returns:
            bool: True se válido, False caso contrário
        """
        if df is None or df.empty:
            return False
        
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Checa colunas necessárias
        has_required = all(col in df.columns for col in required_cols)
        
        # Checa quantidade mínima de dados
        has_min_data = len(df) >= 10
        
        # Checa se tem valores válidos
        has_valid_data = not df[required_cols].isna().all().any()
        
        return has_required and has_min_data and has_valid_data
