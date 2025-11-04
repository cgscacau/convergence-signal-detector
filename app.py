"""
CACAS CHANNEL SCANNER
Scanner de convergências multi-timeframe para B3
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Adiciona src ao path
sys.path.append(str(Path(__file__).parent / 'src'))

from data.asset_loader import AssetLoader
from data.market_data import MarketDataLoader
from indicators.cacas_channel import CacasChannel
from signals.convergence import ConvergenceDetector
from signals.risk_manager import RiskManager
from ui.charts import CacasChannelChart
from backtest.strategy_backtester import CacasBacktester, run_batch_backtest

# Configuração da página
st.set_page_config(
    page_title="Cacas Channel Scanner",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #FF4B4B;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🎯 CACAS CHANNEL SCANNER</h1>', unsafe_allow_html=True)
st.markdown("**Scanner de convergências multi-timeframe para o mercado brasileiro**")
st.markdown("---")

# Inicializa
@st.cache_resource
def init_loaders():
    return AssetLoader(), MarketDataLoader()

asset_loader, market_loader = init_loaders()

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÕES")
    
    # CONTADOR DE ATIVOS NO TOPO
    counts = asset_loader.count_assets()
    
    # Calcular subtotais (fallback caso não existam)
    if 'Brasil' not in counts:
        counts['Brasil'] = counts.get('Ação BR', 0) + counts.get('FII', 0) + counts.get('ETF BR', 0) + counts.get('BDR', 0)
    if 'EUA' not in counts:
        counts['EUA'] = counts.get('Ação US', 0) + counts.get('ETF US', 0) + counts.get('REIT US', 0)
    if 'Total' not in counts:
        counts['Total'] = counts['Brasil'] + counts['EUA'] + counts.get('Crypto', 0)
    
    st.info(f"""### 📊 BASE DE DADOS
    **🎯 {counts['Total']} ativos disponíveis**
    
    🇧🇷 Brasil: {counts['Brasil']} | 🇺🇸 EUA: {counts['EUA']} | ₿ Crypto: {counts.get('Crypto', 0)}
    """)
    
    st.markdown("---")
    
    # Ativos
    st.subheader("📊 SELEÇÃO DE ATIVOS")
    
    # Seleção de MERCADO primeiro
    market_groups = asset_loader.get_market_groups()
    
    selected_market = st.radio(
        "Mercado:",
        options=list(market_groups.keys()),
        index=0,
        help="Escolha o mercado"
    )
    
    # Categorias disponíveis para o mercado selecionado
    available_categories = market_groups[selected_market]
    
    selected_categories = st.multiselect(
        "Categorias:",
        options=available_categories,
        default=[available_categories[0]] if available_categories else [],
        help="Selecione os tipos de ativos"
    )
    
    if selected_categories:
        assets_df = asset_loader.filter_by_category(selected_categories)
        
        # MOSTRAR QUANTOS ATIVOS ESTÃO DISPONÍVEIS NA CATEGORIA
        st.success(f"✅ **{len(assets_df)} ativos disponíveis nas categorias selecionadas**")
        
        # MODO DE SELEÇÃO
        selection_mode = st.radio(
            "Modo de seleção:",
            options=["Selecionar Todos", "Escolher Específicos"],
            index=1,
            help="Escolha como selecionar os ativos"
        )
        
        if selection_mode == "Selecionar Todos":
            # TODOS OS ATIVOS DA CATEGORIA
            selected_tickers = assets_df['ticker'].tolist()
            st.success(f"✅ **{len(selected_tickers)} ativos selecionados**")
            
            # Mostra amostra
            with st.expander("📋 Ver lista completa"):
                st.write(assets_df[['ticker', 'nome']])
        
        else:
            # SELEÇÃO ESPECÍFICA
            with st.expander("🔍 Buscar e selecionar"):
                search = st.text_input("Buscar:", placeholder="Ex: PETR, Vale")
                
                if search:
                    filtered = asset_loader.search_assets(search, selected_categories)
                    if not filtered.empty:
                        st.success(f"✅ {len(filtered)} encontrados")
                        display_df = filtered
                    else:
                        st.warning("Nada encontrado")
                        display_df = assets_df.head(20)
                else:
                    display_df = assets_df.head(20)
                
                selected_tickers = st.multiselect(
                    "Ativos:",
                    options=assets_df['ticker'].tolist(),
                    default=display_df['ticker'].tolist()[:10],
                    help="Selecione os ativos desejados"
                )
    else:
        st.warning("⚠️ Selecione uma categoria")
        selected_tickers = []
    
    st.markdown("---")
    
    # Período
    st.subheader("📅 PERÍODO")
    period_options = {
        '6 meses': '6mo',
        '1 ano': '1y',
        '2 anos': '2y',
        '3 anos': '3y',
        '5 anos': '5y',
        '10 anos': '10y'
    }
    period_label = st.selectbox(
        "Período:",
        options=list(period_options.keys()),
        index=1
    )
    period = period_options[period_label]
    
    st.markdown("---")
    
    # Indicador
    st.subheader("⚙️ INDICADOR")
    with st.expander("Parâmetros", expanded=False):
        upper = st.number_input("Upper:", 5, 100, 20)
        under = st.number_input("Under:", 5, 100, 30)
        ema = st.number_input("EMA:", 3, 50, 9)
    
    st.markdown("---")
    
    # Risco
    st.subheader("🎯 RISCO")
    atr_mult = st.slider("Stop (ATR×):", 1.0, 3.0, 1.5, 0.5)
    target_mult = st.selectbox("Alvo (×Risco):", [1.5, 2.0, 2.5, 3.0], index=1)
    
    st.markdown("---")
    
    # Botão
    analyze_button = st.button("🚀 ANALISAR", type="primary", use_container_width=True)

# ========== MAIN ==========

# Verificar se já existe análise no session state
if 'analysis_done' in st.session_state and st.session_state['analysis_done'] and not analyze_button:
    # CARREGAR RESULTADOS DO SESSION STATE
    results = st.session_state.get('results', {})
    atr_mult = st.session_state.get('atr_mult', 1.5)
    target_mult = st.session_state.get('target_mult', 2.0)
    
    # Reinicializar objetos necessários
    detector = ConvergenceDetector()
    risk_mgr = RiskManager(atr_multiplier=atr_mult)
    chart_maker = CacasChannelChart()
    
    # Pular para a seção de resultados
    if len(results) > 0:
        st.success(f"✅ **Análise anterior: {len(results)} ativos processados**")
        
        # ========== ANÁLISE ==========
        st.markdown("---")
        st.subheader("📊 RESULTADOS")
        
        # Convergências
        conv_results = detector.scan_multiple_assets(results)
        conv_results = detector.sort_by_priority(conv_results)
        
        # Tabela COMPLETA com TODOS os dados
        st.dataframe(
            conv_results,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "status": st.column_config.TextColumn("Status", width="medium"),
                "descricao": st.column_config.TextColumn("Descrição", width="large"),
                "semanal": st.column_config.NumberColumn("Semanal", format="%d"),
                "diario": st.column_config.NumberColumn("Diário", format="%d"),
                "convergente": st.column_config.CheckboxColumn("Convergente"),
                "tipo": st.column_config.TextColumn("Tipo", width="small")
            }
        )
        
        # Stats
        st.markdown("---")
        st.subheader("📈 Resumo")
        
        buys = detector.get_buy_signals(conv_results)
        sells = detector.get_sell_signals(conv_results)
        waiting = detector.get_waiting_signals(conv_results)
        
        cols = st.columns(4)
        cols[0].metric("🟢 Compra", len(buys))
        cols[1].metric("🔴 Venda", len(sells))
        cols[2].metric("🟡 Aguardando", len(waiting))
        cols[3].metric("📊 Total", len(conv_results))
        
        # ========== VISUALIZAÇÃO OTIMIZADA (1 GRÁFICO POR VEZ) ==========
        st.markdown("---")
        st.subheader("📈 VISUALIZAÇÃO DE GRÁFICOS")
        
        # Filtrar apenas ativos com sinal de compra
        if len(buys) > 0:
            buy_tickers = buys['ticker'].tolist()
            
            st.info(f"💡 **{len(buy_tickers)} ativos com sinal de compra!** Selecione um abaixo para ver os gráficos detalhados.")
            
            # SELETOR DE ATIVO (dropdown)
            selected_ticker_for_chart = st.selectbox(
                "🎯 Selecione o ativo para visualizar:",
                options=buy_tickers,
                format_func=lambda x: f"{x} - {buys[buys['ticker']==x]['status'].values[0]}",
                help="Escolha um ativo para ver os gráficos multi-timeframe",
                key="ticker_selector"  # Key para manter seleção
            )
            
            if selected_ticker_for_chart:
                ticker = selected_ticker_for_chart
                row = buys[buys['ticker'] == ticker].iloc[0]
                
                st.markdown("---")
                st.markdown(f"### 📊 {ticker}")
                st.write(f"**Status:** {row['status']}")
                st.write(f"**{row['descricao']}**")
                
                daily_df = results[ticker]['daily']
                weekly_df = results[ticker]['weekly']
                latest = daily_df.iloc[-1]
                
                # CALCULAR STOP E ALVO
                plan = risk_mgr.generate_trade_plan(
                    daily_df,
                    entry_type='long',
                    target_multiplier=target_mult
                )
                
                # MÉTRICAS
                st.markdown("#### 💰 Informações de Trade")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Preço Atual", f"R$ {latest['Close']:.2f}")
                
                with col2:
                    if plan:
                        st.metric("Stop Loss", f"R$ {plan['stop_loss']['price']:.2f}",
                                delta=f"-{plan['stop_loss']['risk_percent']:.1f}%")
                
                with col3:
                    if plan:
                        st.metric("Alvo", f"R$ {plan['target']['price']:.2f}",
                                delta=f"+{plan['target']['gain_percent']:.1f}%")
                
                with col4:
                    if plan:
                        st.metric("R/R Ratio", f"{plan['risk_reward']:.2f}x")
                
                st.markdown("---")
                
                # GRÁFICOS LADO A LADO (DIÁRIO + SEMANAL)
                st.markdown("#### 📊 Gráficos Multi-Timeframe")
                
                col_daily, col_weekly = st.columns(2)
                
                with col_daily:
                    st.markdown("**📅 Gráfico Diário**")
                    # Gráfico DIÁRIO com STOP e ALVO
                    fig_daily = chart_maker.create_single_chart(
                        daily_df,
                        title=f"{ticker} - DIÁRIO",
                        show_stop=True if plan else False,
                        stop_price=plan['stop_loss']['price'] if plan else None,
                        show_target=True if plan else False,
                        target_price=plan['target']['price'] if plan else None,
                        height=600
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)
                
                with col_weekly:
                    st.markdown("**📅 Gráfico Semanal**")
                    # Gráfico SEMANAL (sem stop/alvo)
                    fig_weekly = chart_maker.create_single_chart(
                        weekly_df,
                        title=f"{ticker} - SEMANAL",
                        height=600
                    )
                    st.plotly_chart(fig_weekly, use_container_width=True)
                
                # TABELA DE DADOS RECENTES
                st.markdown("---")
                st.markdown("#### 📋 Dados Recentes (Diário)")
                
                # Últimas 10 barras do diário
                recent_data = daily_df[[
                    'Close', 'linha_superior', 'linha_inferior', 
                    'linha_media', 'linha_ema', 'sinal'
                ]].tail(10).copy()
                
                recent_data['sinal_texto'] = recent_data['sinal'].map({
                    1: '🟢 COMPRA',
                    -1: '🔴 VENDA',
                    0: '⚪ NEUTRO'
                })
                
                st.dataframe(
                    recent_data.round(2),
                    use_container_width=True,
                    column_config={
                        "Close": "Preço",
                        "linha_superior": "L. Superior",
                        "linha_inferior": "L. Inferior",
                        "linha_media": "L. Branca",
                        "linha_ema": "L. Laranja",
                        "sinal_texto": "Sinal"
                    }
                )
                
                # ========== BACKTESTING ==========
                st.markdown("---")
                st.markdown("#### 📈 BACKTEST DA ESTRATÉGIA")
                st.info("📊 Testando performance histórica da estratégia com os parâmetros atuais...")
                
                # Executar backtest
                backtester = CacasBacktester(
                    atr_multiplier=atr_mult,
                    target_multiplier=target_mult
                )
                
                bt_results = backtester.run_backtest(daily_df, weekly_df)
                
                if bt_results['total_trades'] > 0:
                    # Métricas principais em colunas
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Win Rate",
                            f"{bt_results['win_rate']:.1f}%",
                            delta=f"Ajustado: {bt_results['adjusted_win_rate']:.1f}%"
                        )
                    
                    with col2:
                        st.metric(
                            "Retorno Total",
                            f"{bt_results['total_return']:.2f}%",
                            delta=f"Médio: {bt_results['avg_return']:.2f}%"
                        )
                    
                    with col3:
                        st.metric(
                            "Profit Factor",
                            f"{bt_results['profit_factor']:.2f}x",
                            delta="Maior é melhor"
                        )
                    
                    with col4:
                        st.metric(
                            "Total Trades",
                            bt_results['total_trades'],
                            delta=f"Alvos: {bt_results['targets_hit']}"
                        )
                    
                    # Detalhes expandidos
                    with st.expander("🔍 Ver Detalhes Completos do Backtest"):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.markdown("**📈 Performance**")
                            st.write(f"Retorno Médio (Wins): **{bt_results['avg_win']:.2f}%**")
                            st.write(f"Retorno Médio (Losses): **{bt_results['avg_loss']:.2f}%**")
                            st.write(f"Melhor Trade: **{bt_results['best_trade']:.2f}%**")
                            st.write(f"Pior Trade: **{bt_results['worst_trade']:.2f}%**")
                            st.write(f"Expectância: **{bt_results['expectancy']:.2f}%**")
                        
                        with col_b:
                            st.markdown("**🛡️ Risco**")
                            st.write(f"Max Drawdown: **{bt_results['max_drawdown']:.2f}%**")
                            st.write(f"Sharpe Ratio: **{bt_results['sharpe_ratio']:.2f}**")
                            st.write(f"Stops Atingidos: **{bt_results['stops_hit']}** ({bt_results['stops_hit']/bt_results['total_trades']*100:.1f}%)")
                            st.write(f"Alvos Atingidos: **{bt_results['targets_hit']}** ({bt_results['targets_hit']/bt_results['total_trades']*100:.1f}%)")
                            st.write(f"Tempo Médio: **{bt_results['avg_bars_in_trade']:.0f} dias**")
                        
                        # Tabela de trades
                        if len(bt_results['trades_list']) > 0:
                            st.markdown("---")
                            st.markdown("**📋 Histórico de Trades**")
                            
                            trades_df = pd.DataFrame(bt_results['trades_list'])
                            trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date']).dt.strftime('%d/%m/%Y')
                            trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date']).dt.strftime('%d/%m/%Y')
                            
                            st.dataframe(
                                trades_df[['entry_date', 'entry_price', 'exit_date', 'exit_price', 'return_pct', 'exit_reason']].round(2),
                                use_container_width=True,
                                column_config={
                                    "entry_date": "Entrada",
                                    "entry_price": "Preço Entrada",
                                    "exit_date": "Saída",
                                    "exit_price": "Preço Saída",
                                    "return_pct": st.column_config.NumberColumn("Retorno %", format="%.2f%%"),
                                    "exit_reason": "Razão"
                                }
                            )
                    
                    # Interpretação
                    st.markdown("---")
                    st.markdown("**💡 Interpretação:**")
                    
                    if bt_results['win_rate'] >= 60:
                        st.success(f"✅ **Estratégia FORTE** - Win rate de {bt_results['win_rate']:.1f}% é excelente!")
                    elif bt_results['win_rate'] >= 50:
                        st.info(f"ℹ️ **Estratégia BOA** - Win rate de {bt_results['win_rate']:.1f}% é positivo.")
                    else:
                        st.warning(f"⚠️ **Estratégia FRACA** - Win rate de {bt_results['win_rate']:.1f}% está abaixo de 50%.")
                    
                    if bt_results['profit_factor'] >= 2.0:
                        st.success(f"✅ **Profit Factor {bt_results['profit_factor']:.2f}** - Ótimo! Cada R$ 1 perdido gera R$ {bt_results['profit_factor']:.2f} de ganho.")
                    elif bt_results['profit_factor'] >= 1.5:
                        st.info(f"ℹ️ **Profit Factor {bt_results['profit_factor']:.2f}** - Bom! Lucrativo mas pode melhorar.")
                    else:
                        st.warning(f"⚠️ **Profit Factor {bt_results['profit_factor']:.2f}** - Baixo. Revise parâmetros de stop/alvo.")
                    
                else:
                    st.warning("⚠️ Nenhum trade identificado no período histórico. A estratégia não gerou sinais suficientes.")

        else:
            st.info("ℹ️ Nenhum sinal de compra encontrado nos ativos analisados.")
        
        # Download
        st.markdown("---")
        st.subheader("💾 Exportar")
        
        csv = conv_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📅 Baixar CSV",
            csv,
            f"cacas_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            use_container_width=True
        )
        
        # Botão para limpar análise
        st.markdown("---")
        if st.button("🔄 Nova Análise", use_container_width=True):
            st.session_state.clear()
            st.rerun()

elif not selected_tickers:
    st.info("👈 **Selecione ativos na barra lateral**")
    
    # Stats - Organizado por mercado
    st.subheader("📊 Ativos Disponíveis")
    counts = asset_loader.count_assets()
    
    # Brasil
    st.markdown("**🇧🇷 Brasil (B3)**")
    cols = st.columns(4)
    cols[0].metric("📈 Ações BR", counts['Ação BR'])
    cols[1].metric("🏢 FIIs", counts['FII'])
    cols[2].metric("📊 ETFs BR", counts['ETF BR'])
    cols[3].metric("🌎 BDRs", counts['BDR'])
    
    # Estados Unidos
    st.markdown("**🇺🇸 Estados Unidos**")
    cols = st.columns(3)
    cols[0].metric("📈 Ações US", counts['Ação US'])
    cols[1].metric("📊 ETFs US", counts['ETF US'])
    cols[2].metric("🏢 REITs US", counts['REIT US'])
    
    # Criptomoedas
    st.markdown("**₿ Criptomoedas**")
    cols = st.columns(2)
    cols[0].metric("🪙 Crypto", counts['Crypto'])
    cols[1].metric("📦 TOTAL GERAL", counts['Total'])

elif analyze_button:
    # ========== PROCESSAMENTO ==========
    
    st.subheader(f"🔄 Analisando {len(selected_tickers)} ativos...")
    
    # Progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Inicia
    indicator = CacasChannel(upper=upper, under=under, ema=ema)
    detector = ConvergenceDetector()
    risk_mgr = RiskManager(atr_multiplier=atr_mult)
    chart_maker = CacasChannelChart()
    
    results = {}
    failed = []
    
    # SALVAR PARÂMETROS NO SESSION STATE
    st.session_state['atr_mult'] = atr_mult
    st.session_state['target_mult'] = target_mult
    
    total = len(selected_tickers)
    
    for i, ticker in enumerate(selected_tickers):
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"📊 {ticker} ({i+1}/{total})")
        
        try:
            # Download
            daily = market_loader.get_daily_data(ticker, period)
            weekly = market_loader.get_weekly_data(ticker, period)
            
            # Valida
            if (market_loader.validate_dataframe(daily) and 
                market_loader.validate_dataframe(weekly)):
                
                # Calcula
                daily_ind = indicator.calculate_full(daily)
                weekly_ind = indicator.calculate_full(weekly)
                
                # Cruza
                daily_ind = indicator.detect_crossover(daily_ind)
                weekly_ind = indicator.detect_crossover(weekly_ind)
                
                results[ticker] = {
                    'daily': daily_ind,
                    'weekly': weekly_ind
                }
            else:
                failed.append(ticker)
        except:
            failed.append(ticker)
    
    progress_bar.empty()
    status_text.empty()
    
    # Resultado
    success = len(results)
    fail = len(failed)
    
    if success > 0:
        # SALVAR RESULTADOS NO SESSION STATE
        st.session_state['results'] = results
        st.session_state['analysis_done'] = True
        
        st.success(f"✅ **{success}/{total} ativos processados com sucesso!**")
        
        if fail > 0:
            with st.expander(f"⚠️ {fail} ativos sem dados"):
                st.warning(", ".join(failed))
        
        # ========== ANÁLISE ==========
        st.markdown("---")
        st.subheader("📊 RESULTADOS")
        
        # Convergências
        conv_results = detector.scan_multiple_assets(results)
        conv_results = detector.sort_by_priority(conv_results)
        
        # Tabela COMPLETA com TODOS os dados
        st.dataframe(
            conv_results,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "status": st.column_config.TextColumn("Status", width="medium"),
                "descricao": st.column_config.TextColumn("Descrição", width="large"),
                "semanal": st.column_config.NumberColumn("Semanal", format="%d"),
                "diario": st.column_config.NumberColumn("Diário", format="%d"),
                "convergente": st.column_config.CheckboxColumn("Convergente"),
                "tipo": st.column_config.TextColumn("Tipo", width="small")
            }
        )
        
        # Stats
        st.markdown("---")
        st.subheader("📈 Resumo")
        
        buys = detector.get_buy_signals(conv_results)
        sells = detector.get_sell_signals(conv_results)
        waiting = detector.get_waiting_signals(conv_results)
        
        cols = st.columns(4)
        cols[0].metric("🟢 Compra", len(buys))
        cols[1].metric("🔴 Venda", len(sells))
        cols[2].metric("🟡 Aguardando", len(waiting))
        cols[3].metric("📊 Total", len(conv_results))
        
        # ========== VISUALIZAÇÃO OTIMIZADA (1 GRÁFICO POR VEZ) ==========
        st.markdown("---")
        st.subheader("📈 VISUALIZAÇÃO DE GRÁFICOS")
        
        # Filtrar apenas ativos com sinal de compra
        if len(buys) > 0:
            buy_tickers = buys['ticker'].tolist()
            
            st.info(f"💡 **{len(buy_tickers)} ativos com sinal de compra!** Selecione um abaixo para ver os gráficos detalhados.")
            
            # SELETOR DE ATIVO (dropdown)
            selected_ticker_for_chart = st.selectbox(
                "🎯 Selecione o ativo para visualizar:",
                options=buy_tickers,
                format_func=lambda x: f"{x} - {buys[buys['ticker']==x]['status'].values[0]}",
                help="Escolha um ativo para ver os gráficos multi-timeframe"
            )
            
            if selected_ticker_for_chart:
                ticker = selected_ticker_for_chart
                row = buys[buys['ticker'] == ticker].iloc[0]
                
                st.markdown("---")
                st.markdown(f"### 📊 {ticker}")
                st.write(f"**Status:** {row['status']}")
                st.write(f"**{row['descricao']}**")
                
                daily_df = results[ticker]['daily']
                weekly_df = results[ticker]['weekly']
                latest = daily_df.iloc[-1]
                
                # CALCULAR STOP E ALVO
                plan = risk_mgr.generate_trade_plan(
                    daily_df,
                    entry_type='long',
                    target_multiplier=target_mult
                )
                
                # MÉTRICAS
                st.markdown("#### 💰 Informações de Trade")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Preço Atual", f"R$ {latest['Close']:.2f}")
                
                with col2:
                    if plan:
                        st.metric("Stop Loss", f"R$ {plan['stop_loss']['price']:.2f}",
                                delta=f"-{plan['stop_loss']['risk_percent']:.1f}%")
                
                with col3:
                    if plan:
                        st.metric("Alvo", f"R$ {plan['target']['price']:.2f}",
                                delta=f"+{plan['target']['gain_percent']:.1f}%")
                
                with col4:
                    if plan:
                        st.metric("R/R Ratio", f"{plan['risk_reward']:.2f}x")
                
                st.markdown("---")
                
                # GRÁFICOS LADO A LADO (DIÁRIO + SEMANAL)
                st.markdown("#### 📊 Gráficos Multi-Timeframe")
                
                col_daily, col_weekly = st.columns(2)
                
                with col_daily:
                    st.markdown("**📅 Gráfico Diário**")
                    # Gráfico DIÁRIO com STOP e ALVO
                    fig_daily = chart_maker.create_single_chart(
                        daily_df,
                        title=f"{ticker} - DIÁRIO",
                        show_stop=True if plan else False,
                        stop_price=plan['stop_loss']['price'] if plan else None,
                        show_target=True if plan else False,
                        target_price=plan['target']['price'] if plan else None,
                        height=600
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)
                
                with col_weekly:
                    st.markdown("**📅 Gráfico Semanal**")
                    # Gráfico SEMANAL (sem stop/alvo)
                    fig_weekly = chart_maker.create_single_chart(
                        weekly_df,
                        title=f"{ticker} - SEMANAL",
                        height=600
                    )
                    st.plotly_chart(fig_weekly, use_container_width=True)
                
                # TABELA DE DADOS RECENTES
                st.markdown("---")
                st.markdown("#### 📋 Dados Recentes (Diário)")
                
                # Últimas 10 barras do diário
                recent_data = daily_df[[
                    'Close', 'linha_superior', 'linha_inferior', 
                    'linha_media', 'linha_ema', 'sinal'
                ]].tail(10).copy()
                
                recent_data['sinal_texto'] = recent_data['sinal'].map({
                    1: '🟢 COMPRA',
                    -1: '🔴 VENDA',
                    0: '⚪ NEUTRO'
                })
                
                st.dataframe(
                    recent_data.round(2),
                    use_container_width=True,
                    column_config={
                        "Close": "Preço",
                        "linha_superior": "L. Superior",
                        "linha_inferior": "L. Inferior",
                        "linha_media": "L. Branca",
                        "linha_ema": "L. Laranja",
                        "sinal_texto": "Sinal"
                    }
                )
                
                # ========== BACKTESTING ==========
                st.markdown("---")
                st.markdown("#### 📈 BACKTEST DA ESTRATÉGIA")
                st.info("📊 Testando performance histórica da estratégia com os parâmetros atuais...")
                
                # Executar backtest
                backtester = CacasBacktester(
                    atr_multiplier=atr_mult,
                    target_multiplier=target_mult
                )
                
                bt_results = backtester.run_backtest(daily_df, weekly_df)
                
                if bt_results['total_trades'] > 0:
                    # Métricas principais em colunas
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Win Rate",
                            f"{bt_results['win_rate']:.1f}%",
                            delta=f"Ajustado: {bt_results['adjusted_win_rate']:.1f}%"
                        )
                    
                    with col2:
                        st.metric(
                            "Retorno Total",
                            f"{bt_results['total_return']:.2f}%",
                            delta=f"Médio: {bt_results['avg_return']:.2f}%"
                        )
                    
                    with col3:
                        st.metric(
                            "Profit Factor",
                            f"{bt_results['profit_factor']:.2f}x",
                            delta="Maior é melhor"
                        )
                    
                    with col4:
                        st.metric(
                            "Total Trades",
                            bt_results['total_trades'],
                            delta=f"Alvos: {bt_results['targets_hit']}"
                        )
                    
                    # Detalhes expandidos
                    with st.expander("🔍 Ver Detalhes Completos do Backtest"):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.markdown("**📈 Performance**")
                            st.write(f"Retorno Médio (Wins): **{bt_results['avg_win']:.2f}%**")
                            st.write(f"Retorno Médio (Losses): **{bt_results['avg_loss']:.2f}%**")
                            st.write(f"Melhor Trade: **{bt_results['best_trade']:.2f}%**")
                            st.write(f"Pior Trade: **{bt_results['worst_trade']:.2f}%**")
                            st.write(f"Expectância: **{bt_results['expectancy']:.2f}%**")
                        
                        with col_b:
                            st.markdown("**🛡️ Risco**")
                            st.write(f"Max Drawdown: **{bt_results['max_drawdown']:.2f}%**")
                            st.write(f"Sharpe Ratio: **{bt_results['sharpe_ratio']:.2f}**")
                            st.write(f"Stops Atingidos: **{bt_results['stops_hit']}** ({bt_results['stops_hit']/bt_results['total_trades']*100:.1f}%)")
                            st.write(f"Alvos Atingidos: **{bt_results['targets_hit']}** ({bt_results['targets_hit']/bt_results['total_trades']*100:.1f}%)")
                            st.write(f"Tempo Médio: **{bt_results['avg_bars_in_trade']:.0f} dias**")
                        
                        # Tabela de trades
                        if len(bt_results['trades_list']) > 0:
                            st.markdown("---")
                            st.markdown("**📋 Histórico de Trades**")
                            
                            trades_df = pd.DataFrame(bt_results['trades_list'])
                            trades_df['entry_date'] = pd.to_datetime(trades_df['entry_date']).dt.strftime('%d/%m/%Y')
                            trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date']).dt.strftime('%d/%m/%Y')
                            
                            st.dataframe(
                                trades_df[['entry_date', 'entry_price', 'exit_date', 'exit_price', 'return_pct', 'exit_reason']].round(2),
                                use_container_width=True,
                                column_config={
                                    "entry_date": "Entrada",
                                    "entry_price": "Preço Entrada",
                                    "exit_date": "Saída",
                                    "exit_price": "Preço Saída",
                                    "return_pct": st.column_config.NumberColumn("Retorno %", format="%.2f%%"),
                                    "exit_reason": "Razão"
                                }
                            )
                    
                    # Interpretação
                    st.markdown("---")
                    st.markdown("**💡 Interpretação:**")
                    
                    if bt_results['win_rate'] >= 60:
                        st.success(f"✅ **Estratégia FORTE** - Win rate de {bt_results['win_rate']:.1f}% é excelente!")
                    elif bt_results['win_rate'] >= 50:
                        st.info(f"ℹ️ **Estratégia BOA** - Win rate de {bt_results['win_rate']:.1f}% é positivo.")
                    else:
                        st.warning(f"⚠️ **Estratégia FRACA** - Win rate de {bt_results['win_rate']:.1f}% está abaixo de 50%.")
                    
                    if bt_results['profit_factor'] >= 2.0:
                        st.success(f"✅ **Profit Factor {bt_results['profit_factor']:.2f}** - Ótimo! Cada R$ 1 perdido gera R$ {bt_results['profit_factor']:.2f} de ganho.")
                    elif bt_results['profit_factor'] >= 1.5:
                        st.info(f"ℹ️ **Profit Factor {bt_results['profit_factor']:.2f}** - Bom! Lucrativo mas pode melhorar.")
                    else:
                        st.warning(f"⚠️ **Profit Factor {bt_results['profit_factor']:.2f}** - Baixo. Revise parâmetros de stop/alvo.")
                    
                else:
                    st.warning("⚠️ Nenhum trade identificado no período histórico. A estratégia não gerou sinais suficientes.")
        else:
            st.info("ℹ️ Nenhum sinal de compra encontrado nos ativos analisados.")
        
        # Download
        st.markdown("---")
        st.subheader("💾 Exportar")
        
        csv = conv_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Baixar CSV",
            csv,
            f"cacas_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    else:
        st.error(f"❌ Nenhum ativo processado ({fail}/{total} falharam)")
        
        st.markdown("""
        ### 🔧 Soluções:
        1. Verifique os tickers
        2. Tente período menor (6 meses)
        3. Use ativos líquidos (PETR4, VALE3)
        4. Aguarde alguns minutos
        """)

else:
    st.info("👆 Clique em **🚀 ANALISAR**")
    
    if selected_tickers:
        st.success(f"✅ {len(selected_tickers)} ativos prontos")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888;'>
    <p><b>🎯 Cacas Channel Scanner v1.0.3</b></p>
    <p>⚠️ Apenas educacional - Não é recomendação de investimento</p>
</div>
""", unsafe_allow_html=True)
