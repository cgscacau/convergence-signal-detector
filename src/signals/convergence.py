"""
Detector de convergências entre múltiplos timeframes
"""

import pandas as pd


class ConvergenceDetector:
    """Detecta convergências entre timeframes diário e semanal"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def get_latest_signal(df):
        """
        Retorna o sinal mais recente de um DataFrame
        
        Args:
            df (pd.DataFrame): DataFrame com coluna 'sinal'
        
        Returns:
            int: 1 (compra), -1 (venda), 0 (neutro), ou None se vazio
        """
        if df is None or df.empty:
            return None
        
        return int(df['sinal'].iloc[-1])
    
    @staticmethod
    def get_latest_crossover(df):
        """
        Retorna o cruzamento mais recente
        
        Args:
            df (pd.DataFrame): DataFrame com coluna 'crossover'
        
        Returns:
            int: 1 (bullish), -1 (bearish), 0 (sem cruzamento), ou None
        """
        if df is None or df.empty or 'crossover' not in df.columns:
            return None
        
        return int(df['crossover'].iloc[-1])
    
    def analyze_convergence(self, daily_df, weekly_df):
        """
        Analisa convergência entre timeframes
        
        Args:
            daily_df (pd.DataFrame): Dados diários com indicador calculado
            weekly_df (pd.DataFrame): Dados semanais com indicador calculado
        
        Returns:
            dict: Análise de convergência
        """
        # Sinais atuais
        daily_signal = self.get_latest_signal(daily_df)
        weekly_signal = self.get_latest_signal(weekly_df)
        
        # Cruzamentos
        daily_cross = self.get_latest_crossover(daily_df)
        weekly_cross = self.get_latest_crossover(weekly_df)
        
        # Análise de convergência
        convergence = {
            'daily_signal': daily_signal,
            'weekly_signal': weekly_signal,
            'daily_crossover': daily_cross,
            'weekly_crossover': weekly_cross,
            'is_convergent': False,
            'convergence_type': 'DIVERGENTE',
            'status': 'AGUARDANDO',
            'description': ''
        }
        
        # Se algum timeframe não tem dados
        if daily_signal is None or weekly_signal is None:
            convergence['status'] = 'SEM DADOS'
            convergence['description'] = 'Dados insuficientes para análise'
            return convergence
        
        # Verifica convergência
        if daily_signal == weekly_signal:
            convergence['is_convergent'] = True
            
            if daily_signal == 1:
                convergence['convergence_type'] = 'ALTA'
                convergence['status'] = '🟢 COMPRA CONVERGENTE'
                convergence['description'] = 'Ambos timeframes em tendência de alta'
                
                # Setup ideal: semanal já está, diário acabou de cruzar
                if weekly_signal == 1 and daily_cross == 1:
                    convergence['status'] = '🔵 SETUP COMPRA'
                    convergence['description'] = '⚡ Setup ideal de compra! Diário cruzou para cima'
            
            elif daily_signal == -1:
                convergence['convergence_type'] = 'BAIXA'
                convergence['status'] = '🔴 VENDA CONVERGENTE'
                convergence['description'] = 'Ambos timeframes em tendência de baixa'
                
                # Setup de venda: estava convergente alto, diário cruzou para baixo
                if weekly_signal == -1 and daily_cross == -1:
                    convergence['status'] = '🟣 SETUP VENDA'
                    convergence['description'] = '⚡ Sinal de saída! Diário cruzou para baixo'
            
            else:  # Ambos neutros
                convergence['convergence_type'] = 'NEUTRO'
                convergence['status'] = '⚪ NEUTRO'
                convergence['description'] = 'Ambos timeframes neutros'
        
        else:
            # Divergência
            convergence['is_convergent'] = False
            convergence['convergence_type'] = 'DIVERGENTE'
            
            if weekly_signal == 1 and daily_signal == -1:
                convergence['status'] = '🟡 AGUARDANDO ALTA'
                convergence['description'] = 'Semanal em alta, aguardando confirmação diária'
            elif weekly_signal == -1 and daily_signal == 1:
                convergence['status'] = '🟠 CONTRA-TENDÊNCIA'
                convergence['description'] = 'Diário em alta, mas semanal em baixa (atenção!)'
            else:
                convergence['status'] = '🟡 AGUARDANDO'
                convergence['description'] = 'Timeframes em direções opostas'
        
        return convergence
    
    def scan_multiple_assets(self, assets_data):
        """
        Escaneia múltiplos ativos em busca de convergências
        
        Args:
            assets_data (dict): {ticker: {'daily': df, 'weekly': df}}
        
        Returns:
            pd.DataFrame: DataFrame com resultados da análise
        """
        results = []
        
        for ticker, data in assets_data.items():
            daily_df = data.get('daily')
            weekly_df = data.get('weekly')
            
            if daily_df is None or weekly_df is None:
                continue
            
            analysis = self.analyze_convergence(daily_df, weekly_df)
            
            result = {
                'ticker': ticker,
                'semanal': analysis['weekly_signal'],
                'diario': analysis['daily_signal'],
                'convergente': analysis['is_convergent'],
                'tipo': analysis['convergence_type'],
                'status': analysis['status'],
                'descricao': analysis['description']
            }
            
            results.append(result)
        
        df_results = pd.DataFrame(results)
        
        return df_results
    
    @staticmethod
    def filter_by_status(df, status_list):
        """
        Filtra resultados por status
        
        Args:
            df (pd.DataFrame): DataFrame de resultados
            status_list (list): Lista de status para filtrar
        
        Returns:
            pd.DataFrame: DataFrame filtrado
        """
        return df[df['status'].isin(status_list)]
    
    @staticmethod
    def get_buy_signals(df):
        """
        Retorna apenas sinais de compra
        
        Args:
            df (pd.DataFrame): DataFrame de resultados
        
        Returns:
            pd.DataFrame: Apenas sinais de compra
        """
        buy_statuses = ['🟢 COMPRA CONVERGENTE', '🔵 SETUP COMPRA']
        return df[df['status'].isin(buy_statuses)]
    
    @staticmethod
    def get_sell_signals(df):
        """
        Retorna apenas sinais de venda
        
        Args:
            df (pd.DataFrame): DataFrame de resultados
        
        Returns:
            pd.DataFrame: Apenas sinais de venda
        """
        sell_statuses = ['🔴 VENDA CONVERGENTE', '🟣 SETUP VENDA']
        return df[df['status'].isin(sell_statuses)]
    
    @staticmethod
    def get_waiting_signals(df):
        """
        Retorna ativos em aguardo
        
        Args:
            df (pd.DataFrame): DataFrame de resultados
        
        Returns:
            pd.DataFrame: Ativos em aguardo
        """
        waiting_statuses = ['🟡 AGUARDANDO ALTA', '🟡 AGUARDANDO']
        return df[df['status'].isin(waiting_statuses)]
    
    @staticmethod
    def sort_by_priority(df):
        """
        Ordena resultados por prioridade
        
        Args:
            df (pd.DataFrame): DataFrame de resultados
        
        Returns:
            pd.DataFrame: DataFrame ordenado
        """
        priority_order = {
            '🔵 SETUP COMPRA': 1,
            '🟣 SETUP VENDA': 2,
            '🟢 COMPRA CONVERGENTE': 3,
            '🔴 VENDA CONVERGENTE': 4,
            '🟡 AGUARDANDO ALTA': 5,
            '🟠 CONTRA-TENDÊNCIA': 6,
            '🟡 AGUARDANDO': 7,
            '⚪ NEUTRO': 8,
            'SEM DADOS': 9
        }
        
        df['_priority'] = df['status'].map(priority_order)
        df_sorted = df.sort_values('_priority').drop('_priority', axis=1)
        
        return df_sorted
