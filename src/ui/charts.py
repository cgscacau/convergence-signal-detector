"""
Módulo de geração de gráficos para Cacas Channel
Gráficos interativos com Plotly
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


class CacasChannelChart:
    """Gerador de gráficos do Cacas Channel"""
    
    def __init__(self):
        # Cores do tema
        self.colors = {
            'red': '#FF4B4B',
            'green': '#00CC66',
            'white': '#FFFFFF',
            'orange': '#FF8C00',
            'blue': '#1E90FF',
            'gray': '#888888',
            'bg': '#0E1117',
            'grid': '#262730'
        }
    
    def create_single_chart(self, df, title="Cacas Channel", 
                           show_stop=False, stop_price=None,
                           show_target=False, target_price=None,
                           height=500):
        """
        Cria gráfico único do Cacas Channel
        
        Args:
            df (pd.DataFrame): Dados com indicador calculado
            title (str): Título do gráfico
            show_stop (bool): Mostrar linha de stop loss
            stop_price (float): Preço do stop loss
            show_target (bool): Mostrar linha de alvo
            target_price (float): Preço do alvo
            height (int): Altura do gráfico
        
        Returns:
            go.Figure: Figura Plotly
        """
        fig = go.Figure()
        
        # Candlesticks
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Preço',
            increasing_line_color=self.colors['green'],
            decreasing_line_color=self.colors['red']
        ))
        
        # Linha Superior (Vermelha)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['linha_superior'],
            mode='lines',
            name='Superior',
            line=dict(color=self.colors['red'], width=1),
            opacity=0.7
        ))
        
        # Linha Inferior (Verde)
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['linha_inferior'],
            mode='lines',
            name='Inferior',
            line=dict(color=self.colors['green'], width=1),
            opacity=0.7
        ))
        
        # Linha Média (Branca) - PRINCIPAL
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['linha_media'],
            mode='lines',
            name='Linha Branca (Média)',
            line=dict(color=self.colors['white'], width=2),
        ))
        
        # Linha EMA (Laranja) - PRINCIPAL
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['linha_ema'],
            mode='lines',
            name='Linha Laranja (EMA)',
            line=dict(color=self.colors['orange'], width=2),
        ))
        
        # Stop Loss (se fornecido)
        if show_stop and stop_price is not None:
            fig.add_hline(
                y=stop_price,
                line_dash="dash",
                line_color=self.colors['red'],
                line_width=2,
                annotation_text=f"Stop: R$ {stop_price:.2f}",
                annotation_position="right"
            )
        
        # Alvo (se fornecido)
        if show_target and target_price is not None:
            fig.add_hline(
                y=target_price,
                line_dash="dash",
                line_color=self.colors['green'],
                line_width=2,
                annotation_text=f"Alvo: R$ {target_price:.2f}",
                annotation_position="right"
            )
        
        # Sinais de cruzamento (se existir coluna crossover)
        if 'crossover' in df.columns:
            # Cruzamentos de alta (bullish)
            bullish = df[df['crossover'] == 1]
            if len(bullish) > 0:
                fig.add_trace(go.Scatter(
                    x=bullish.index,
                    y=bullish['Low'] * 0.98,  # Abaixo da mínima
                    mode='markers',
                    name='Compra',
                    marker=dict(
                        symbol='triangle-up',
                        size=12,
                        color=self.colors['green']
                    )
                ))
            
            # Cruzamentos de baixa (bearish)
            bearish = df[df['crossover'] == -1]
            if len(bearish) > 0:
                fig.add_trace(go.Scatter(
                    x=bearish.index,
                    y=bearish['High'] * 1.02,  # Acima da máxima
                    mode='markers',
                    name='Venda',
                    marker=dict(
                        symbol='triangle-down',
                        size=12,
                        color=self.colors['red']
                    )
                ))
        
        # Layout
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(size=18, color=self.colors['white']),
                x=0.5,
                xanchor='center'
            ),
            xaxis_title="Data",
            yaxis_title="Preço (R$)",
            template='plotly_dark',
            height=height,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis=dict(
                rangeslider=dict(visible=False),
                gridcolor=self.colors['grid']
            ),
            yaxis=dict(
                gridcolor=self.colors['grid']
            ),
            plot_bgcolor=self.colors['bg'],
            paper_bgcolor=self.colors['bg']
        )
        
        return fig
    
    def create_dual_chart(self, daily_df, weekly_df, ticker,
                         show_stop=False, stop_price=None,
                         show_target=False, target_price=None):
        """
        Cria gráficos lado a lado (diário + semanal)
        
        Args:
            daily_df (pd.DataFrame): Dados diários com indicador
            weekly_df (pd.DataFrame): Dados semanais com indicador
            ticker (str): Ticker do ativo
            show_stop (bool): Mostrar stop loss no gráfico diário
            stop_price (float): Preço do stop loss
            show_target (bool): Mostrar alvo no gráfico diário
            target_price (float): Preço do alvo
        
        Returns:
            tuple: (fig_daily, fig_weekly) - Duas figuras Plotly
        """
        # Gráfico Diário (com stop/alvo)
        fig_daily = self.create_single_chart(
            daily_df,
            title=f"{ticker} - DIÁRIO",
            show_stop=show_stop,
            stop_price=stop_price,
            show_target=show_target,
            target_price=target_price,
            height=600
        )
        
        # Gráfico Semanal (sem stop/alvo)
        fig_weekly = self.create_single_chart(
            weekly_df,
            title=f"{ticker} - SEMANAL",
            show_stop=False,
            show_target=False,
            height=600
        )
        
        return fig_daily, fig_weekly
    
    def create_volume_chart(self, df, title="Volume"):
        """
        Cria gráfico de volume
        
        Args:
            df (pd.DataFrame): Dados com coluna Volume
            title (str): Título
        
        Returns:
            go.Figure: Figura Plotly
        """
        colors = ['green' if row['Close'] >= row['Open'] else 'red' 
                  for _, row in df.iterrows()]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.7
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Data",
            yaxis_title="Volume",
            template='plotly_dark',
            height=200,
            showlegend=False,
            xaxis=dict(gridcolor=self.colors['grid']),
            yaxis=dict(gridcolor=self.colors['grid']),
            plot_bgcolor=self.colors['bg'],
            paper_bgcolor=self.colors['bg']
        )
        
        return fig
    
    def create_comparison_chart(self, results_dict, metric='Close'):
        """
        Cria gráfico de comparação entre múltiplos ativos
        
        Args:
            results_dict (dict): {ticker: DataFrame}
            metric (str): Métrica para comparar
        
        Returns:
            go.Figure: Figura Plotly
        """
        fig = go.Figure()
        
        for ticker, df in results_dict.items():
            if metric in df.columns:
                # Normaliza para base 100
                normalized = (df[metric] / df[metric].iloc[0]) * 100
                
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=normalized,
                    mode='lines',
                    name=ticker,
                    line=dict(width=2)
                ))
        
        fig.update_layout(
            title="Comparação de Performance (Base 100)",
            xaxis_title="Data",
            yaxis_title="Performance (%)",
            template='plotly_dark',
            height=500,
            hovermode='x unified',
            showlegend=True,
            xaxis=dict(gridcolor=self.colors['grid']),
            yaxis=dict(gridcolor=self.colors['grid']),
            plot_bgcolor=self.colors['bg'],
            paper_bgcolor=self.colors['bg']
        )
        
        return fig
