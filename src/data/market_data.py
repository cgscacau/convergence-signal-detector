"""
Download de dados de mercado usando yfinance
Versão ultra-robusta para Streamlit Cloud
"""

import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import warnings
import sys

# Suprime TODOS os warnings
warnings.filterwarnings('ignore')
if not sys.warnoptions:
    warnings.simplefilter("ignore")


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
            str: Ticker formatado (ex: PETR4.SA)
        """
        ticker = str(ticker).upper().strip()
        if not ticker.endswith('.SA'):
            return f"{ticker}.SA"
        return ticker
    
    @st.cache_data(ttl=1800, show_spinner=False)
    def download_data(_self, ticker, period='1y', interval='1d'):
        """
        Baixa dados usando APENAS Ticker API (método mais estável)
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período ('1mo', '3mo', '6mo', '1y', '2y', etc)
            interval (str): Intervalo ('1d', '1wk', '1mo')
        
        Returns:
            pd.DataFrame: DataFrame com OHLCV ou None se falhar
        """
        try:
            # Formata ticker
            ticker_formatted = _self.format_ticker_b3(ticker)
            
            # Cria objeto Ticker
            stock = yf.Ticker(ticker_formatted)
            
            # Baixa histórico (método mais confiável)
            # NÃO usa parâmetros problemáticos
            df = stock.history(
                period=period,
                interval=interval
            )
            
            # Valida resultado
            if df is None or df.empty or len(df) < 5:
                return None
            
            # Limpa índice (remove timezone se houver)
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            # Garante nomes de colunas padronizados
            df.columns = [col.title() for col in df.columns]
            
            # Remove linhas totalmente vazias
            df = df.dropna(how='all')
            
            # Valida colunas essenciais
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                return None
            
            # Remove linhas com valores inválidos nas colunas principais
            df = df.dropna(subset=['Close'])
            
            # Última validação
            if len(df) < 5:
                return None
            
            return df
            
        except Exception:
            # Silenciosamente retorna None em caso de erro
            return None
    
    def download_multiple(self, tickers, period='1y', interval='1d', show_progress=True):
        """
        Baixa dados de múltiplos ativos
        
        Args:
            tickers (list): Lista de tickers
            period (str): Período
            interval (str): Intervalo
            show_progress (bool): Mostrar progresso
        
        Returns:
            dict: {ticker: DataFrame}
        """
        results = {}
        
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
            
            if data is not None and not data.empty:
                results[ticker] = data
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        return results
    
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
        Retorna dados semanais (via resample de diários)
        
        Args:
            ticker (str): Ticker do ativo
            period (str): Período
        
        Returns:
            pd.DataFrame: Dados semanais
        """
        # Estratégia: baixa diários e converte (mais confiável)
        daily = self.get_daily_data(ticker, period)
        
        if daily is not None and not daily.empty:
            weekly = self.resample_to_weekly(daily)
            if weekly is not None and not weekly.empty:
                return weekly
        
        # Fallback: tenta baixar direto semanal
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
        
        try:
            # Define como agregar cada coluna
            agg_dict = {}
            
            if 'Open' in daily_df.columns:
                agg_dict['Open'] = 'first'
            if 'High' in daily_df.columns:
                agg_dict['High'] = 'max'
            if 'Low' in daily_df.columns:
                agg_dict['Low'] = 'min'
            if 'Close' in daily_df.columns:
                agg_dict['Close'] = 'last'
            if 'Volume' in daily_df.columns:
                agg_dict['Volume'] = 'sum'
            if 'Adj Close' in daily_df.columns:
                agg_dict['Adj Close'] = 'last'
            
            # Resample para semanal (fecha na sexta)
            weekly = daily_df.resample('W-FRI').agg(agg_dict)
            
            # Remove linhas vazias
            weekly = weekly.dropna(how='all')
            
            if weekly.empty:
                return None
            
            return weekly
            
        except Exception:
            return None
    
    @staticmethod
    def validate_dataframe(df):
        """
        Valida se DataFrame tem estrutura mínima necessária
        
        Args:
            df (pd.DataFrame): DataFrame para validar
        
        Returns:
            bool: True se válido, False caso contrário
        """
        if df is None or df.empty:
            return False
        
        # Verifica colunas essenciais
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        has_columns = all(col in df.columns for col in required)
        
        # Verifica quantidade mínima de dados
        has_enough_data = len(df) >= 5
        
        # Verifica se tem valores válidos
        has_valid_values = df['Close'].notna().any()
        
        return has_columns and has_enough_data and has_valid_values
    
    def check_data_availability(self, ticker):
        """
        Verifica se ticker tem dados disponíveis
        
        Args:
            ticker (str): Ticker do ativo
        
        Returns:
            bool: True se dados disponíveis
        """
        data = self.download_data(ticker, period='1mo', interval='1d')
        return self.validate_dataframe(data)
