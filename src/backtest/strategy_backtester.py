"""
Módulo de Backtesting para Estratégia Cacas Channel
Testa performance histórica da estratégia de convergência
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class CacasBacktester:
    """
    Backtester para estratégia de convergência Cacas Channel
    
    Regras:
    - ENTRADA: Linha branca > Linha laranja em AMBOS timeframes (diário + semanal)
    - STOP LOSS: ATR × multiplicador
    - ALVO: (ATR × multiplicador) × target_multiplier
    - SAÍDA: Stop loss ou alvo atingido
    """
    
    def __init__(self, atr_multiplier: float = 1.5, target_multiplier: float = 2.0):
        """
        Args:
            atr_multiplier: Multiplicador do ATR para stop loss
            target_multiplier: Multiplicador do risco para alvo
        """
        self.atr_multiplier = atr_multiplier
        self.target_multiplier = target_multiplier
        
    def run_backtest(self, daily_df: pd.DataFrame, weekly_df: pd.DataFrame) -> Dict:
        """
        Executa backtest completo
        
        Args:
            daily_df: DataFrame com dados diários e indicadores
            weekly_df: DataFrame com dados semanais e indicadores
            
        Returns:
            Dict com resultados do backtest
        """
        trades = self._identify_trades(daily_df, weekly_df)
        
        if len(trades) == 0:
            return self._empty_results()
        
        results = self._calculate_metrics(trades, daily_df)
        
        return results
    
    def _identify_trades(self, daily_df: pd.DataFrame, weekly_df: pd.DataFrame) -> List[Dict]:
        """
        Identifica todos os trades baseado na estratégia de convergência
        """
        trades = []
        in_position = False
        entry_idx = None
        entry_price = None
        stop_loss = None
        target = None
        
        # Alinhar dados semanais com diários
        daily_df = daily_df.copy()
        daily_df['weekly_signal'] = 0
        
        for idx, row in daily_df.iterrows():
            # Pegar sinal semanal correspondente
            weekly_row = weekly_df[weekly_df.index <= row.name].iloc[-1] if len(weekly_df[weekly_df.index <= row.name]) > 0 else None
            
            if weekly_row is not None:
                daily_df.at[idx, 'weekly_signal'] = weekly_row['sinal']
        
        # Identificar trades
        for idx, row in daily_df.iterrows():
            # ENTRADA: Convergência (ambos sinais = 1)
            if not in_position:
                daily_signal = row.get('sinal', 0)
                weekly_signal = row.get('weekly_signal', 0)
                
                if daily_signal == 1 and weekly_signal == 1:
                    # Abrir posição
                    in_position = True
                    entry_idx = idx
                    entry_price = row['Close']
                    
                    # Calcular stop e alvo
                    atr = row.get('ATR', row['Close'] * 0.02)  # Fallback: 2% do preço
                    stop_distance = atr * self.atr_multiplier
                    stop_loss = entry_price - stop_distance
                    target = entry_price + (stop_distance * self.target_multiplier)
            
            # SAÍDA: Stop ou alvo atingido
            elif in_position:
                low = row['Low']
                high = row['High']
                close = row['Close']
                
                # Verificar stop loss (bateu mínima)
                if low <= stop_loss:
                    # Stop loss atingido
                    exit_price = stop_loss
                    exit_idx = idx
                    exit_reason = 'Stop Loss'
                    
                    trades.append({
                        'entry_date': entry_idx,
                        'entry_price': entry_price,
                        'exit_date': exit_idx,
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'stop_loss': stop_loss,
                        'target': target,
                        'return_pct': ((exit_price - entry_price) / entry_price) * 100,
                        'bars_in_trade': (exit_idx - entry_idx).days if hasattr(exit_idx - entry_idx, 'days') else 1
                    })
                    
                    in_position = False
                
                # Verificar alvo (bateu máxima)
                elif high >= target:
                    # Alvo atingido
                    exit_price = target
                    exit_idx = idx
                    exit_reason = 'Target'
                    
                    trades.append({
                        'entry_date': entry_idx,
                        'entry_price': entry_price,
                        'exit_date': exit_idx,
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'stop_loss': stop_loss,
                        'target': target,
                        'return_pct': ((exit_price - entry_price) / entry_price) * 100,
                        'bars_in_trade': (exit_idx - entry_idx).days if hasattr(exit_idx - entry_idx, 'days') else 1
                    })
                    
                    in_position = False
        
        # Se ainda estiver em posição ao final, fechar no último preço
        if in_position:
            last_row = daily_df.iloc[-1]
            exit_price = last_row['Close']
            exit_idx = last_row.name
            
            trades.append({
                'entry_date': entry_idx,
                'entry_price': entry_price,
                'exit_date': exit_idx,
                'exit_price': exit_price,
                'exit_reason': 'End of Data',
                'stop_loss': stop_loss,
                'target': target,
                'return_pct': ((exit_price - entry_price) / entry_price) * 100,
                'bars_in_trade': (exit_idx - entry_idx).days if hasattr(exit_idx - entry_idx, 'days') else 1
            })
        
        return trades
    
    def _calculate_metrics(self, trades: List[Dict], daily_df: pd.DataFrame) -> Dict:
        """
        Calcula métricas de performance do backtest
        """
        if len(trades) == 0:
            return self._empty_results()
        
        trades_df = pd.DataFrame(trades)
        
        # Separar wins e losses
        wins = trades_df[trades_df['return_pct'] > 0]
        losses = trades_df[trades_df['return_pct'] <= 0]
        
        # Métricas básicas
        total_trades = len(trades_df)
        winning_trades = len(wins)
        losing_trades = len(losses)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # Retornos
        total_return = trades_df['return_pct'].sum()
        avg_return = trades_df['return_pct'].mean()
        avg_win = wins['return_pct'].mean() if len(wins) > 0 else 0
        avg_loss = losses['return_pct'].mean() if len(losses) > 0 else 0
        
        # Profit Factor
        gross_profit = wins['return_pct'].sum() if len(wins) > 0 else 0
        gross_loss = abs(losses['return_pct'].sum()) if len(losses) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown
        cumulative_returns = (1 + trades_df['return_pct'] / 100).cumprod()
        running_max = cumulative_returns.cummax()
        drawdown = (cumulative_returns - running_max) / running_max * 100
        max_drawdown = drawdown.min()
        
        # Sharpe Ratio (assumindo 252 dias úteis)
        returns_std = trades_df['return_pct'].std()
        sharpe_ratio = (avg_return / returns_std) * np.sqrt(252 / trades_df['bars_in_trade'].mean()) if returns_std > 0 else 0
        
        # Melhor e pior trade
        best_trade = trades_df['return_pct'].max()
        worst_trade = trades_df['return_pct'].min()
        
        # Tempo médio em trade
        avg_bars = trades_df['bars_in_trade'].mean()
        
        # Expectativa matemática
        expectancy = (win_rate / 100) * avg_win + ((100 - win_rate) / 100) * avg_loss
        
        # Contagem por resultado
        stops_hit = len(trades_df[trades_df['exit_reason'] == 'Stop Loss'])
        targets_hit = len(trades_df[trades_df['exit_reason'] == 'Target'])
        
        # Taxa de acerto ajustada (apenas stops e alvos)
        completed_trades = stops_hit + targets_hit
        adjusted_win_rate = (targets_hit / completed_trades * 100) if completed_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'adjusted_win_rate': adjusted_win_rate,
            'total_return': total_return,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_bars_in_trade': avg_bars,
            'expectancy': expectancy,
            'targets_hit': targets_hit,
            'stops_hit': stops_hit,
            'trades_list': trades,
            'start_date': daily_df.index[0],
            'end_date': daily_df.index[-1]
        }
    
    def _empty_results(self) -> Dict:
        """Retorna resultados vazios quando não há trades"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'adjusted_win_rate': 0,
            'total_return': 0,
            'avg_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'avg_bars_in_trade': 0,
            'expectancy': 0,
            'targets_hit': 0,
            'stops_hit': 0,
            'trades_list': [],
            'start_date': None,
            'end_date': None
        }
    
    def format_results_text(self, results: Dict) -> str:
        """
        Formata resultados do backtest em texto legível
        """
        if results['total_trades'] == 0:
            return "⚠️ Nenhum trade identificado no período"
        
        text = f"""
📊 **RESULTADOS DO BACKTEST**

**Período:** {results['start_date'].strftime('%d/%m/%Y') if results['start_date'] else 'N/A'} até {results['end_date'].strftime('%d/%m/%Y') if results['end_date'] else 'N/A'}

**📈 Performance Geral:**
- Total de Trades: {results['total_trades']}
- Trades Vencedores: {results['winning_trades']} 
- Trades Perdedores: {results['losing_trades']}
- Win Rate: **{results['win_rate']:.1f}%**
- Win Rate Ajustado: **{results['adjusted_win_rate']:.1f}%** (apenas stops/alvos)

**💰 Retornos:**
- Retorno Total: **{results['total_return']:.2f}%**
- Retorno Médio por Trade: **{results['avg_return']:.2f}%**
- Retorno Médio (Wins): **{results['avg_win']:.2f}%**
- Retorno Médio (Losses): **{results['avg_loss']:.2f}%**
- Melhor Trade: **{results['best_trade']:.2f}%**
- Pior Trade: **{results['worst_trade']:.2f}%**

**📊 Métricas de Risco:**
- Profit Factor: **{results['profit_factor']:.2f}**
- Maximum Drawdown: **{results['max_drawdown']:.2f}%**
- Sharpe Ratio: **{results['sharpe_ratio']:.2f}**
- Expectância: **{results['expectancy']:.2f}%**

**🎯 Resultados dos Trades:**
- Alvos Atingidos: {results['targets_hit']} ({results['targets_hit']/results['total_trades']*100:.1f}%)
- Stops Atingidos: {results['stops_hit']} ({results['stops_hit']/results['total_trades']*100:.1f}%)
- Tempo Médio em Trade: {results['avg_bars_in_trade']:.0f} dias
"""
        return text


def run_batch_backtest(results: Dict, atr_multiplier: float, target_multiplier: float) -> pd.DataFrame:
    """
    Executa backtest em múltiplos ativos
    
    Args:
        results: Dict com resultados da análise (contém daily e weekly data)
        atr_multiplier: Multiplicador do ATR para stop
        target_multiplier: Multiplicador do risco para alvo
        
    Returns:
        DataFrame com resultados de backtest para cada ativo
    """
    backtester = CacasBacktester(atr_multiplier, target_multiplier)
    
    backtest_results = []
    
    for ticker, data in results.items():
        daily_df = data['daily']
        weekly_df = data['weekly']
        
        bt_result = backtester.run_backtest(daily_df, weekly_df)
        
        backtest_results.append({
            'ticker': ticker,
            'total_trades': bt_result['total_trades'],
            'win_rate': bt_result['win_rate'],
            'win_rate_ajustado': bt_result['adjusted_win_rate'],
            'retorno_total': bt_result['total_return'],
            'retorno_medio': bt_result['avg_return'],
            'profit_factor': bt_result['profit_factor'],
            'max_drawdown': bt_result['max_drawdown'],
            'sharpe_ratio': bt_result['sharpe_ratio'],
            'expectancia': bt_result['expectancy'],
            'alvos_atingidos': bt_result['targets_hit'],
            'stops_atingidos': bt_result['stops_hit']
        })
    
    return pd.DataFrame(backtest_results)
