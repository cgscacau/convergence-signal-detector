"""
Gerenciador de risco - Cálculo de stop loss e alvos
"""

import pandas as pd
import numpy as np


class RiskManager:
    """Calcula stop loss e alvos baseados em ATR"""
    
    def __init__(self, atr_multiplier=1.5):
        """
        Inicializa gerenciador de risco
        
        Args:
            atr_multiplier (float): Multiplicador do ATR para stop loss
        """
        self.atr_multiplier = atr_multiplier
    
    @staticmethod
    def calculate_atr(df, period=14):
        """
        Calcula Average True Range (ATR)
        
        Args:
            df (pd.DataFrame): DataFrame com High, Low, Close
            period (int): Período para cálculo
        
        Returns:
            pd.Series: Série com valores do ATR
        """
        df = df.copy()
        
        # True Range components
        df['h_l'] = df['High'] - df['Low']
        df['h_pc'] = abs(df['High'] - df['Close'].shift(1))
        df['l_pc'] = abs(df['Low'] - df['Close'].shift(1))
        
        # True Range = max dos 3 componentes
        df['tr'] = df[['h_l', 'h_pc', 'l_pc']].max(axis=1)
        
        # ATR = média móvel do True Range
        atr = df['tr'].rolling(window=period).mean()
        
        return atr
    
    def calculate_stop_loss(self, df, entry_type='long'):
        """
        Calcula stop loss baseado em ATR
        
        Args:
            df (pd.DataFrame): DataFrame com dados OHLC
            entry_type (str): 'long' ou 'short'
        
        Returns:
            dict: Informações de stop loss
        """
        if df is None or df.empty:
            return None
        
        # Calcula ATR
        atr = self.calculate_atr(df)
        latest_atr = atr.iloc[-1]
        latest_close = df['Close'].iloc[-1]
        latest_low = df['Low'].iloc[-1]
        latest_high = df['High'].iloc[-1]
        
        # Stop loss
        if entry_type == 'long':
            # Para compra: stop abaixo da mínima recente
            stop_distance = latest_atr * self.atr_multiplier
            stop_loss = latest_low - stop_distance
            risk = latest_close - stop_loss
        else:
            # Para venda: stop acima da máxima recente
            stop_distance = latest_atr * self.atr_multiplier
            stop_loss = latest_high + stop_distance
            risk = stop_loss - latest_close
        
        return {
            'entry_price': latest_close,
            'atr': latest_atr,
            'stop_distance': stop_distance,
            'stop_loss': stop_loss,
            'risk': abs(risk),
            'risk_percent': (abs(risk) / latest_close) * 100
        }
    
    def calculate_targets(self, stop_info, target_multipliers=[1.5, 2.0, 2.5, 3.0]):
        """
        Calcula alvos baseados no risco (stop loss)
        
        Args:
            stop_info (dict): Informações do stop loss
            target_multipliers (list): Multiplicadores de risco para alvos
        
        Returns:
            dict: Informações de alvos
        """
        if stop_info is None:
            return None
        
        entry = stop_info['entry_price']
        risk = stop_info['risk']
        
        targets = {}
        
        for multiplier in target_multipliers:
            target_price = entry + (risk * multiplier)
            targets[f'target_{multiplier}x'] = {
                'price': target_price,
                'multiplier': multiplier,
                'gain': target_price - entry,
                'gain_percent': ((target_price - entry) / entry) * 100
            }
        
        return targets
    
    def calculate_position_size(self, capital, risk_percent, stop_info):
        """
        Calcula tamanho da posição baseado em risco
        
        Args:
            capital (float): Capital disponível
            risk_percent (float): Percentual de risco desejado (ex: 1 = 1%)
            stop_info (dict): Informações do stop loss
        
        Returns:
            dict: Informações de posicionamento
        """
        if stop_info is None:
            return None
        
        # Valor em risco
        risk_amount = capital * (risk_percent / 100)
        
        # Preço de entrada e risco por ação
        entry_price = stop_info['entry_price']
        risk_per_share = stop_info['risk']
        
        # Quantidade de ações
        shares = int(risk_amount / risk_per_share)
        
        # Valor total da operação
        position_value = shares * entry_price
        
        return {
            'capital': capital,
            'risk_percent': risk_percent,
            'risk_amount': risk_amount,
            'shares': shares,
            'position_value': position_value,
            'position_percent': (position_value / capital) * 100
        }
    
    def generate_trade_plan(self, df, entry_type='long', 
                           target_multiplier=2.0, 
                           capital=None, 
                           risk_percent=1.0):
        """
        Gera plano completo de trade
        
        Args:
            df (pd.DataFrame): DataFrame com dados
            entry_type (str): 'long' ou 'short'
            target_multiplier (float): Multiplicador de risco para alvo
            capital (float, optional): Capital disponível
            risk_percent (float): Percentual de risco
        
        Returns:
            dict: Plano completo de trade
        """
        # Calcula stop loss
        stop_info = self.calculate_stop_loss(df, entry_type)
        
        if stop_info is None:
            return None
        
        # Calcula alvos
        targets = self.calculate_targets(stop_info)
        
        # Seleciona alvo principal
        main_target = targets[f'target_{target_multiplier}x']
        
        plan = {
            'entry': {
                'price': stop_info['entry_price'],
                'type': entry_type
            },
            'stop_loss': {
                'price': stop_info['stop_loss'],
                'distance': stop_info['stop_distance'],
                'risk': stop_info['risk'],
                'risk_percent': stop_info['risk_percent']
            },
            'target': {
                'price': main_target['price'],
                'multiplier': target_multiplier,
                'gain': main_target['gain'],
                'gain_percent': main_target['gain_percent']
            },
            'all_targets': targets,
            'atr': stop_info['atr'],
            'risk_reward': target_multiplier
        }
        
        # Adiciona cálculo de posição se capital fornecido
        if capital is not None:
            position = self.calculate_position_size(capital, risk_percent, stop_info)
            plan['position'] = position
        
        return plan
    
    @staticmethod
    def format_trade_plan(plan):
        """
        Formata plano de trade para exibição
        
        Args:
            plan (dict): Plano de trade
        
        Returns:
            str: Texto formatado
        """
        if plan is None:
            return "Sem dados suficientes para gerar plano"
        
        text = f"""
📊 PLANO DE TRADE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 ENTRADA
   Preço: R$ {plan['entry']['price']:.2f}
   Tipo: {plan['entry']['type'].upper()}

🛑 STOP LOSS
   Preço: R$ {plan['stop_loss']['price']:.2f}
   Distância: R$ {plan['stop_loss']['distance']:.2f}
   Risco: R$ {plan['stop_loss']['risk']:.2f} ({plan['stop_loss']['risk_percent']:.2f}%)

🎯 ALVO PRINCIPAL ({plan['risk_reward']}x)
   Preço: R$ {plan['target']['price']:.2f}
   Ganho: R$ {plan['target']['gain']:.2f} ({plan['target']['gain_percent']:.2f}%)

📈 RISCO/RETORNO: 1:{plan['risk_reward']}

📊 ATR: {plan['atr']:.2f}
"""
        
        if 'position' in plan:
            pos = plan['position']
            text += f"""
💰 POSICIONAMENTO
   Capital: R$ {pos['capital']:.2f}
   Risco desejado: {pos['risk_percent']:.1f}%
   Valor em risco: R$ {pos['risk_amount']:.2f}
   Quantidade: {pos['shares']} ações
   Valor da posição: R$ {pos['position_value']:.2f} ({pos['position_percent']:.1f}% do capital)
"""
        
        return text
