"""
Carregador de ativos B3 a partir dos CSVs no repositório
"""

import pandas as pd
import streamlit as st
from pathlib import Path


class B3AssetLoader:
    """Carrega ativos B3 dos CSVs no repositório"""
    
    def __init__(self):
        # Caminho para pasta data (funciona no Streamlit Cloud)
        self.data_dir = Path(__file__).parent.parent.parent / "data"
    
    @st.cache_data(ttl=3600)  # Cache por 1 hora
    def load_acoes(_self):
        """
        Carrega lista de ações
        
        Returns:
            pd.DataFrame: DataFrame com colunas ticker, nome, setor, subsetor
        """
        try:
            df = pd.read_csv(_self.data_dir / "b3_acoes.csv")
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_acoes.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'setor', 'subsetor'])
    
    @st.cache_data(ttl=3600)
    def load_fiis(_self):
        """
        Carrega lista de FIIs
        
        Returns:
            pd.DataFrame: DataFrame com colunas ticker, nome, tipo, segmento
        """
        try:
            df = pd.read_csv(_self.data_dir / "b3_fiis.csv")
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_fiis.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'tipo', 'segmento'])
    
    @st.cache_data(ttl=3600)
    def load_etfs(_self):
        """
        Carrega lista de ETFs
        
        Returns:
            pd.DataFrame: DataFrame com colunas ticker, nome, tipo, benchmark
        """
        try:
            df = pd.read_csv(_self.data_dir / "b3_etfs.csv")
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_etfs.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'tipo', 'benchmark'])
    
    @st.cache_data(ttl=3600)
    def load_bdrs(_self):
        """
        Carrega lista de BDRs
        
        Returns:
            pd.DataFrame: DataFrame com colunas ticker, nome, empresa_original, pais, setor
        """
        try:
            df = pd.read_csv(_self.data_dir / "b3_bdrs.csv")
            return df
        except FileNotFoundError:
            st.error("❌ Arquivo b3_bdrs.csv não encontrado!")
            return pd.DataFrame(columns=['ticker', 'nome', 'empresa_original', 'pais', 'setor'])
    
    def load_all(self):
        """
        Carrega todos os ativos com categoria
        
        Returns:
            pd.DataFrame: DataFrame consolidado com todos os ativos
        """
        acoes = self.load_acoes()
        acoes['categoria'] = 'Ação'
        
        fiis = self.load_fiis()
        fiis['categoria'] = 'FII'
        
        etfs = self.load_etfs()
        etfs['categoria'] = 'ETF'
        
        bdrs = self.load_bdrs()
        bdrs['categoria'] = 'BDR'
        
        # Concatena todos (apenas colunas comuns)
        all_assets = pd.concat([
            acoes[['ticker', 'nome', 'categoria']],
            fiis[['ticker', 'nome', 'categoria']],
            etfs[['ticker', 'nome', 'categoria']],
            bdrs[['ticker', 'nome', 'categoria']]
        ], ignore_index=True)
        
        return all_assets
    
    def filter_by_category(self, categories):
        """
        Filtra ativos por categoria
        
        Args:
            categories (list): Lista com ['Ação', 'FII', 'ETF', 'BDR']
        
        Returns:
            pd.DataFrame: DataFrame filtrado
        """
        dfs = []
        
        if 'Ação' in categories:
            df = self.load_acoes()
            df['categoria'] = 'Ação'
            dfs.append(df[['ticker', 'nome', 'categoria']])
        
        if 'FII' in categories:
            df = self.load_fiis()
            df['categoria'] = 'FII'
            dfs.append(df[['ticker', 'nome', 'categoria']])
        
        if 'ETF' in categories:
            df = self.load_etfs()
            df['categoria'] = 'ETF'
            dfs.append(df[['ticker', 'nome', 'categoria']])
        
        if 'BDR' in categories:
            df = self.load_bdrs()
            df['categoria'] = 'BDR'
            dfs.append(df[['ticker', 'nome', 'categoria']])
        
        if dfs:
            result = pd.concat(dfs, ignore_index=True)
            # Remove duplicatas (caso existam)
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
        return {
            'Ação': len(self.load_acoes()),
            'FII': len(self.load_fiis()),
            'ETF': len(self.load_etfs()),
            'BDR': len(self.load_bdrs()),
            'Total': len(self.load_all())
        }
