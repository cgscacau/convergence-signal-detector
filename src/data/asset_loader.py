"""
Carregador de ativos multi-mercado (B3, US Stocks, US ETFs, US REITs, Crypto)
"""

import pandas as pd
import streamlit as st
from pathlib import Path


class AssetLoader:
    """Carrega ativos de múltiplos mercados dos CSVs no repositório"""
    
    def __init__(self):
        # Caminho para pasta data (funciona no Streamlit Cloud)
        self.data_dir = Path(__file__).parent.parent.parent / "data"
    
    # ==================== B3 BRASIL ====================
    
    @st.cache_data(ttl=3600)  # Cache por 1 hora
    def load_b3_acoes(_self):
        """Carrega ações brasileiras (B3)"""
        try:
            df = pd.read_csv(_self.data_dir / "b3_acoes.csv")
            df['categoria'] = 'Ação BR'
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_acoes.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'setor', 'categoria'])
    
    @st.cache_data(ttl=3600)
    def load_b3_fiis(_self):
        """Carrega FIIs brasileiros (B3)"""
        try:
            df = pd.read_csv(_self.data_dir / "b3_fiis.csv")
            df['categoria'] = 'FII'
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_fiis.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'tipo', 'categoria'])
    
    @st.cache_data(ttl=3600)
    def load_b3_etfs(_self):
        """Carrega ETFs brasileiros (B3)"""
        try:
            df = pd.read_csv(_self.data_dir / "b3_etfs.csv")
            df['categoria'] = 'ETF BR'
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_etfs.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'tipo', 'categoria'])
    
    @st.cache_data(ttl=3600)
    def load_b3_bdrs(_self):
        """Carrega BDRs brasileiros (B3)"""
        try:
            df = pd.read_csv(_self.data_dir / "b3_bdrs.csv")
            df['categoria'] = 'BDR'
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_bdrs.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'empresa_original', 'categoria'])
    
    # ==================== MERCADO AMERICANO ====================
    
    @st.cache_data(ttl=3600)
    def load_us_stocks(_self):
        """Carrega ações americanas (US Stock)"""
        try:
            df = pd.read_csv(_self.data_dir / "us_stocks.csv")
            df['categoria'] = 'Ação US'
            return df
        except FileNotFoundError:
            st.warning("❌ Arquivo us_stocks.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'setor', 'categoria'])
    
    @st.cache_data(ttl=3600)
    def load_us_etfs(_self):
        """Carrega ETFs americanos (US ETF)"""
        try:
            df = pd.read_csv(_self.data_dir / "us_etfs.csv")
            df['categoria'] = 'ETF US'
            return df
        except FileNotFoundError:
            st.warning("❌ Arquivo us_etfs.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'tipo', 'categoria'])
    
    @st.cache_data(ttl=3600)
    def load_us_reits(_self):
        """Carrega REITs americanos (US REIT)"""
        try:
            df = pd.read_csv(_self.data_dir / "us_reits.csv")
            df['categoria'] = 'REIT US'
            return df
        except FileNotFoundError:
            st.warning("❌ Arquivo us_reits.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'tipo', 'categoria'])
    
    # ==================== CRIPTOMOEDAS ====================
    
    @st.cache_data(ttl=3600)
    def load_crypto(_self):
        """Carrega criptomoedas (Crypto)"""
        try:
            df = pd.read_csv(_self.data_dir / "crypto.csv")
            df['categoria'] = 'Crypto'
            return df
        except FileNotFoundError:
            st.warning("❌ Arquivo crypto.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'tipo', 'categoria'])
    
    # ==================== MÉTODOS GERAIS ====================
    
    def load_all(self):
        """
        Carrega TODOS os ativos de TODOS os mercados
        
        Returns:
            pd.DataFrame: DataFrame consolidado com todos os ativos
        """
        dfs = []
        
        # Brasil (B3)
        for loader in [self.load_b3_acoes, self.load_b3_fiis, 
                       self.load_b3_etfs, self.load_b3_bdrs]:
            df = loader()
            if not df.empty:
                dfs.append(df[['ticker', 'nome', 'categoria']])
        
        # Estados Unidos
        for loader in [self.load_us_stocks, self.load_us_etfs, self.load_us_reits]:
            df = loader()
            if not df.empty:
                dfs.append(df[['ticker', 'nome', 'categoria']])
        
        # Criptomoedas
        df = self.load_crypto()
        if not df.empty:
            dfs.append(df[['ticker', 'nome', 'categoria']])
        
        if dfs:
            result = pd.concat(dfs, ignore_index=True)
            result = result.drop_duplicates(subset=['ticker'])
            return result
        else:
            return pd.DataFrame(columns=['ticker', 'nome', 'categoria'])
    
    def filter_by_category(self, categories):
        """
        Filtra ativos por categoria
        
        Args:
            categories (list): Lista com categorias desejadas
                - Brasil: 'Ação BR', 'FII', 'ETF BR', 'BDR'
                - EUA: 'Ação US', 'ETF US', 'REIT US'
                - Crypto: 'Crypto'
        
        Returns:
            pd.DataFrame: DataFrame filtrado
        """
        dfs = []
        
        # Mapeia categorias para funções de carregamento
        category_map = {
            'Ação BR': self.load_b3_acoes,
            'FII': self.load_b3_fiis,
            'ETF BR': self.load_b3_etfs,
            'BDR': self.load_b3_bdrs,
            'Ação US': self.load_us_stocks,
            'ETF US': self.load_us_etfs,
            'REIT US': self.load_us_reits,
            'Crypto': self.load_crypto
        }
        
        for category in categories:
            if category in category_map:
                df = category_map[category]()
                if not df.empty:
                    dfs.append(df[['ticker', 'nome', 'categoria']])
        
        if dfs:
            result = pd.concat(dfs, ignore_index=True)
            result = result.drop_duplicates(subset=['ticker'])
            return result
        else:
            return pd.DataFrame(columns=['ticker', 'nome', 'categoria'])
    
    def get_ticker_list(self, categories=None):
        """
        Retorna lista simples de tickers
        
        Args:
            categories (list, optional): Categorias a filtrar. Se None, retorna todos.
        
        Returns:
            list: Lista de tickers
        """
        if categories:
            df = self.filter_by_category(categories)
        else:
            df = self.load_all()
        
        return df['ticker'].tolist()
    
    def get_asset_info(self, ticker):
        """
        Retorna informações de um ativo específico
        
        Args:
            ticker (str): Ticker do ativo
        
        Returns:
            dict: Dicionário com informações do ativo ou None se não encontrado
        """
        all_assets = self.load_all()
        asset = all_assets[all_assets['ticker'] == ticker]
        
        if not asset.empty:
            return asset.iloc[0].to_dict()
        else:
            return None
    
    def search_assets(self, query, categories=None):
        """
        Busca ativos por nome ou ticker
        
        Args:
            query (str): Texto de busca
            categories (list, optional): Categorias para filtrar
        
        Returns:
            pd.DataFrame: Ativos que correspondem à busca
        """
        if categories:
            df = self.filter_by_category(categories)
        else:
            df = self.load_all()
        
        query = query.upper()
        mask = (df['ticker'].str.contains(query, case=False, na=False)) | \
               (df['nome'].str.contains(query, case=False, na=False))
        
        return df[mask]
    
    def count_assets(self):
        """
        Conta total de ativos por categoria
        
        Returns:
            dict: Dicionário com contagem por categoria
        """
        counts = {}
        
        # Brasil
        counts['Ação BR'] = len(self.load_b3_acoes())
        counts['FII'] = len(self.load_b3_fiis())
        counts['ETF BR'] = len(self.load_b3_etfs())
        counts['BDR'] = len(self.load_b3_bdrs())
        
        # EUA
        counts['Ação US'] = len(self.load_us_stocks())
        counts['ETF US'] = len(self.load_us_etfs())
        counts['REIT US'] = len(self.load_us_reits())
        
        # Crypto
        counts['Crypto'] = len(self.load_crypto())
        
        # Total
        counts['Total'] = sum(counts.values())
        
        return counts
    
    def get_market_groups(self):
        """
        Retorna grupos de mercados organizados
        
        Returns:
            dict: Dicionário com grupos de mercados
        """
        return {
            '🇧🇷 Brasil (B3)': ['Ação BR', 'FII', 'ETF BR', 'BDR'],
            '🇺🇸 Estados Unidos': ['Ação US', 'ETF US', 'REIT US'],
            '₿ Criptomoedas': ['Crypto']
        }


# Compatibilidade com código antigo (alias)
B3AssetLoader = AssetLoader
