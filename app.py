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

from data.asset_loader import B3AssetLoader
from data.market_data import MarketDataLoader
from indicators.cacas_channel import CacasChannel
from signals.convergence import ConvergenceDetector
from signals.risk_manager import RiskManager

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
    return B3AssetLoader(), MarketDataLoader()

asset_loader, market_loader = init_loaders()

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÕES")
    
    # Ativos
    st.subheader("📊 ATIVOS")
    
    # Seleção de categorias
    selected_categories = st.multiselect(
        "Categorias:",
        options=['Ação', 'FII', 'ETF', 'BDR'],
        default=['Ação'],
        help="Selecione os tipos de ativos"
    )
    
    if selected_categories:
        assets_df = asset_loader.filter_by_category(selected_categories)
        
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

if not selected_tickers:
    st.info("👈 **Selecione ativos na barra lateral**")
    
    # Stats
    st.subheader("📊 Ativos Disponíveis")
    counts = asset_loader.count_assets()
    
    cols = st.columns(5)
    cols[0].metric("📈 Ações", counts['Ação'])
    cols[1].metric("🏢 FIIs", counts['FII'])
    cols[2].metric("📊 ETFs", counts['ETF'])
    cols[3].metric("🌎 BDRs", counts['BDR'])
    cols[4].metric("📦 Total", counts['Total'])

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
    
    results = {}
    failed = []
    
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
        
        # Tabela
        st.dataframe(
            conv_results[['ticker', 'status', 'descricao']],
            use_container_width=True,
            hide_index=True
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
        
        # Detalhes
        if len(buys) > 0:
            st.markdown("---")
            st.subheader("🟢 SINAIS DE COMPRA")
            
            for _, row in buys.iterrows():
                ticker = row['ticker']
                
                with st.expander(f"📈 {ticker} - {row['status']}"):
                    st.write(f"**{row['descricao']}**")
                    
                    daily_df = results[ticker]['daily']
                    latest = daily_df.iloc[-1]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Preço", f"R$ {latest['Close']:.2f}")
                        st.metric("Sinal Diário", "Alta ✅" if latest['sinal'] == 1 else "Baixa")
                    
                    with col2:
                        plan = risk_mgr.generate_trade_plan(
                            daily_df,
                            entry_type='long',
                            target_multiplier=target_mult
                        )
                        
                        if plan:
                            st.metric("Stop", f"R$ {plan['stop_loss']['price']:.2f}")
                            st.metric("Alvo", f"R$ {plan['target']['price']:.2f}")
        
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
