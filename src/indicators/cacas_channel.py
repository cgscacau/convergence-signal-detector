"""
Implementação do Indicador Cacas Channel
Baseado no Pine Script original do TradingView
"""

import pandas as pd
import numpy as np


class CacasChannel:
    """
    Indicador Cacas Channel com Volatilidade
    
    Componentes:
    - ind01: Linha Superior (Highest)
    - ind02: Linha Inferior (Lowest)
    - ind03: Linha Média (ind01 + ind02) / 2
    - ind04: EMA da Linha Média
    """
    
    def __init__(self, upper=20, under=30, ema=9):
        """
        Inicializa o indicador
        
        Args:
            upper (int): Período para linha superior (highest)
            under (int): Período para linha inferior (lowest)
            ema (int): Período da EMA da linha média
        """
        self.upper = upper
        self.under = under
        self.ema = ema
    
    def calculate(self, df):
        """
        Calcula o indicador Cacas Channel
        
        Args:
            df (pd.DataFrame): DataFrame com coluna 'Close'
        
        Returns:
            pd.DataFrame: DataFrame original com colunas adicionais:
                - linha_superior: Máxima do período
                - linha_inferior: Mínima do período
                - linha_media: Média das linhas superior e inferior
                - linha_ema: EMA da linha média
                - sinal: 1 (compra), -1 (venda), 0 (neutro)
        """
        df = df.copy()
        
        # Linha Superior (ind01) - Highest
        df['linha_superior'] = df['Close'].rolling(window=self.upper).max()
        
        # Linha Inferior (ind02) - Lowest
        df['linha_inferior'] = df['Close'].rolling(window=self.under).min()
        
        # Linha Média (ind03) - Média das linhas
        df['linha_media'] = (df['linha_superior'] + df['linha_inferior']) / 2
        
        # Linha EMA (ind04) - EMA da linha média
        df['linha_ema'] = df['linha_media'].ewm(span=self.ema, adjust=False).mean()
        
        # Sinal: Linha Média vs Linha EMA
        # 1: Linha Média > Linha EMA (compra)
        # -1: Linha Média < Linha EMA (venda)
        # 0: Neutro
        df['sinal'] = 0
        df.loc[df['linha_media'] > df['linha_ema'], 'sinal'] = 1
        df.loc[df['linha_media'] < df['linha_ema'], 'sinal'] = -1
        
        return df
    
    def calculate_volatility(self, df, len_mensal=21, len_trimestral=63, len_anual=252):
        """
        Calcula volatilidade histórica
        
        Args:
            df (pd.DataFrame): DataFrame com coluna 'Close'
            len_mensal (int): Período mensal (padrão 21 dias)
            len_trimestral (int): Período trimestral (padrão 63 dias)
            len_anual (int): Período anual (padrão 252 dias)
        
        Returns:
            pd.DataFrame: DataFrame com colunas de volatilidade adicionadas
        """
        df = df.copy()
        
        # Retornos logarítmicos
        df['log_ret'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # Volatilidade anualizada (%)
        df['vol_mensal'] = df['log_ret'].rolling(window=len_mensal).std() * np.sqrt(252) * 100
        df['vol_trimestral'] = df['log_ret'].rolling(window=len_trimestral).std() * np.sqrt(252) * 100
        df['vol_anual'] = df['log_ret'].rolling(window=len_anual).std() * np.sqrt(252) * 100
        
        # Remove coluna temporária
        df = df.drop('log_ret', axis=1)
        
        return df
    
    def calculate_trend(self, df, sma_curta=50, sma_longa=200):
        """
        Identifica tendência baseada em médias móveis
        
        Args:
            df (pd.DataFrame): DataFrame com coluna 'Close'
            sma_curta (int): Período da SMA curta
            sma_longa (int): Período da SMA longa
        
        Returns:
            pd.DataFrame: DataFrame com colunas de tendência
        """
        df = df.copy()
        
        df['sma_curta'] = df['Close'].rolling(window=sma_curta).mean()
        df['sma_longa'] = df['Close'].rolling(window=sma_longa).mean()
        
        # Identifica tendência
        df['tendencia'] = 'Lateral'
        df.loc[df['sma_curta'] > df['sma_longa'], 'tendencia'] = 'Alta'
        df.loc[df['sma_curta'] < df['sma_longa'], 'tendencia'] = 'Baixa'
        
        return df
    
    def calculate_full(self, df, include_volatility=True, include_trend=True):
        """
        Calcula indicador completo com todas as features
        
        Args:
            df (pd.DataFrame): DataFrame com OHLCV
            include_volatility (bool): Incluir cálculo de volatilidade
            include_trend (bool): Incluir identificação de tendência
        
        Returns:
            pd.DataFrame: DataFrame completo com todos os indicadores
        """
        # Indicador base
        df = self.calculate(df)
        
        # Volatilidade (opcional)
        if include_volatility:
            df = self.calculate_volatility(df)
        
        # Tendência (opcional)
        if include_trend:
            df = self.calculate_trend(df)
        
        return df
    
    def detect_crossover(self, df):
        """
        Detecta cruzamentos entre linha média e linha EMA
        
        Args:
            df (pd.DataFrame): DataFrame com linha_media e linha_ema
        
        Returns:
            pd.DataFrame: DataFrame com coluna 'crossover'
                1: Cruzamento para cima (bullish)
                -1: Cruzamento para baixo (bearish)
                0: Sem cruzamento
        """
        df = df.copy()
        
        # Detecta mudança de sinal
        df['crossover'] = 0
        
        # Cruzamento bullish: linha média cruza acima da EMA
        bullish = (df['sinal'] == 1) & (df['sinal'].shift(1) == -1)
        df.loc[bullish, 'crossover'] = 1
        
        # Cruzamento bearish: linha média cruza abaixo da EMA
        bearish = (df['sinal'] == -1) & (df['sinal'].shift(1) == 1)
        df.loc[bearish, 'crossover'] = -1
        
        return df
    
    def get_latest_signal(self, df):
        """
        Retorna o sinal mais recente
        
        Args:
            df (pd.DataFrame): DataFrame com indicador calculado
        
        Returns:
            dict: Dicionário com informações do sinal atual
        """
        if df.empty or len(df) == 0:
            return None
        
        latest = df.iloc[-1]
        
        signal_info = {
            'date': latest.name if isinstance(df.index, pd.DatetimeIndex) else None,
            'close': latest['Close'],
            'linha_superior': latest['linha_superior'],
            'linha_inferior': latest['linha_inferior'],
            'linha_media': latest['linha_media'],
            'linha_ema': latest['linha_ema'],
            'sinal': int(latest['sinal']),
            'sinal_text': 'COMPRA' if latest['sinal'] == 1 else 'VENDA' if latest['sinal'] == -1 else 'NEUTRO'
        }
        
        # Adiciona volatilidade se disponível
        if 'vol_mensal' in df.columns:
            signal_info['vol_mensal'] = latest['vol_mensal']
            signal_info['vol_trimestral'] = latest['vol_trimestral']
            signal_info['vol_anual'] = latest['vol_anual']
        
        # Adiciona tendência se disponível
        if 'tendencia' in df.columns:
            signal_info['tendencia'] = latest['tendencia']
        
        return signal_info


def calculate_atr(df, period=14):
    """
    Calcula Average True Range (ATR)
    
    Args:
        df (pd.DataFrame): DataFrame com colunas High, Low, Close
        period (int): Período para cálculo do ATR
    
    Returns:
        pd.Series: Série com valores do ATR
    """
    df = df.copy()
    
    # True Range
    df['h_l'] = df['High'] - df['Low']
    df['h_pc'] = abs(df['High'] - df['Close'].shift(1))
    df['l_pc'] = abs(df['Low'] - df['Close'].shift(1))
    
    df['tr'] = df[['h_l', 'h_pc', 'l_pc']].max(axis=1)
    
    # ATR
    atr = df['tr'].rolling(window=period).mean()
    
    return atr
