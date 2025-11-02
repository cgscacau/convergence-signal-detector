"""
CACAS CHANNEL SCANNER
Scanner de convergências multi-timeframe para B3
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

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

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #FF4B4B;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FF4B4B;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🎯 CACAS CHANNEL SCANNER</h1>', unsafe_allow_html=True)
st.markdown("**Scanner de convergências multi-timeframe para o mercado brasileiro**")
st.markdown("---")

# Inicializa classes
@st.cache_resource
def init_loaders():
    return B3AssetLoader(), MarketDataLoader()

asset_loader, market_loader = init_loaders()

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ CONFIGURAÇÕES")
    
    # Seleção de Ativos
    st.subheader("📊 ATIVOS")
    selected_categories = st.multiselect(
        "Selecione as categorias:",
        options=['Ação', 'FII', 'ETF', 'BDR'],
        default=['Ação'],
        help="Escolha os tipos de ativos para análise"
    )
    
    # Mostra contagem
    if selected_categories:
        assets_df = asset_loader.filter_by_category(selected_categories)
        st.info(f"📈 {len(assets_df)} ativos disponíveis")
        
        # Seleção de ativos específicos (opcional)
        with st.expander("🔍 Filtrar ativos específicos"):
            search_query = st.text_input("Buscar por nome ou ticker:")
            if search_query:
                filtered = asset_loader.search_assets(search_query, selected_categories)
                st.write(f"Encontrados: {len(filtered)} ativos")
                selected_tickers = st.multiselect(
                    "Selecione ativos:",
                    options=filtered['ticker'].tolist(),
                    default=filtered['ticker'].tolist()[:5]  # Primeiros 5
                )
            else:
                # Limite para análise (performance)
                max_assets = min(20, len(assets_df))
                selected_tickers = st.multiselect(
                    f"Selecione ativos (máx. {max_assets}):",
                    options=assets_df['ticker'].tolist(),
                    default=assets_df['ticker'].tolist()[:10],  # Primeiros 10
                    max_selections=max_assets
                )
    else:
        st.warning("⚠️ Selecione pelo menos uma categoria")
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
        "Selecione o período:",
        options=list(period_options.keys()),
        index=1  # 1 ano como padrão
    )
    period = period_options[period_label]
    
    st.markdown("---")
    
    # Parâmetros do Indicador
    st.subheader("⚙️ INDICADOR")
    with st.expander("Ajustar parâmetros", expanded=False):
        upper = st.number_input("Linha Superior (Upper):", min_value=5, max_value=100, value=20)
        under = st.number_input("Linha Inferior (Under):", min_value=5, max_value=100, value=30)
        ema = st.number_input("EMA:", min_value=3, max_value=50, value=9)
    
    st.markdown("---")
    
    # Gestão de Risco
    st.subheader("🎯 GESTÃO DE RISCO")
    atr_mult = st.slider("Stop Loss (ATR × ?):", min_value=1.0, max_value=3.0, value=1.5, step=0.5)
    target_mult = st.selectbox("Alvo (× Risco):", options=[1.5, 2.0, 2.5, 3.0], index=1)
    
    st.markdown("---")
    
    # Botão de análise
    analyze_button = st.button("🚀 ANALISAR", type="primary", use_container_width=True)

# ========== ÁREA PRINCIPAL ==========

if not selected_tickers:
    st.info("👈 Selecione os ativos na barra lateral para começar")
    
    # Mostra estatísticas gerais
    st.subheader("📊 Estatísticas de Ativos Disponíveis")
    counts = asset_loader.count_assets()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📈 Ações", counts['Ação'])
    col2.metric("🏢 FIIs", counts['FII'])
    col3.metric("📊 ETFs", counts['ETF'])
    col4.metric("🌎 BDRs", counts['BDR'])
    col5.metric("📦 Total", counts['Total'])
    
    st.markdown("---")
    
    # Instruções
    st.subheader("📖 Como usar")
    st.markdown("""
    1. **Selecione as categorias** de ativos (Ações, FIIs, ETFs, BDRs)
    2. **Escolha os ativos** específicos ou use a busca
    3. **Defina o período** de análise
    4. **Ajuste os parâmetros** do indicador (opcional)
    5. **Configure o risco** (stop loss e alvo)
    6. Clique em **🚀 ANALISAR**
    
    O sistema irá:
    - Baixar dados históricos (diário e semanal)
    - Calcular o indicador Cacas Channel
    - Identificar convergências entre timeframes
    - Mostrar setups de entrada/saída
    - Calcular stop loss e alvos
    """)

elif analyze_button:
    # ========== PROCESSAMENTO ==========
    
    st.subheader("🔄 Processando análise...")
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Inicializa indicador e detectores
    indicator = CacasChannel(upper=upper, under=under, ema=ema)
    detector = ConvergenceDetector()
    risk_mgr = RiskManager(atr_multiplier=atr_mult)
    
    # Dicionário para armazenar resultados
    results = {}
    total = len(selected_tickers)
    
    for i, ticker in enumerate(selected_tickers):
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"Analisando {ticker} ({i+1}/{total})...")
        
        # Download dados
        daily_data = market_loader.get_daily_data(ticker, period=period)
        weekly_data = market_loader.get_weekly_data(ticker, period=period)
        
        if daily_data is not None and weekly_data is not None:
            # Calcula indicador
            daily_with_indicator = indicator.calculate_full(daily_data)
            weekly_with_indicator = indicator.calculate_full(weekly_data)
            
            # Detecta cruzamentos
            daily_with_indicator = indicator.detect_crossover(daily_with_indicator)
            weekly_with_indicator = indicator.detect_crossover(weekly_with_indicator)
            
            # Armazena
            results[ticker] = {
                'daily': daily_with_indicator,
                'weekly': weekly_with_indicator
            }
    
    progress_bar.empty()
    status_text.empty()
    
    if not results:
        st.error("❌ Nenhum dado foi baixado com sucesso. Tente novamente ou selecione outros ativos.")
    else:
        st.success(f"✅ Análise concluída! {len(results)} ativos processados.")
        
        # ========== ANÁLISE DE CONVERGÊNCIAS ==========
        st.markdown("---")
        st.subheader("📊 RESULTADOS DA ANÁLISE")
        
        # Escaneia convergências
        convergence_results = detector.scan_multiple_assets(results)
        
        # Ordena por prioridade
        convergence_results = detector.sort_by_priority(convergence_results)
        
        # Mostra tabela
        st.dataframe(
            convergence_results[['ticker', 'status', 'descricao']],
            use_container_width=True,
            hide_index=True
        )
        
        # ========== ESTATÍSTICAS ==========
        st.markdown("---")
        st.subheader("📈 Estatísticas")
        
        buy_signals = detector.get_buy_signals(convergence_results)
        sell_signals = detector.get_sell_signals(convergence_results)
        waiting = detector.get_waiting_signals(convergence_results)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🟢 Compra", len(buy_signals))
        col2.metric("🔴 Venda", len(sell_signals))
        col3.metric("🟡 Aguardando", len(waiting))
        col4.metric("📊 Total", len(convergence_results))
        
        # ========== DETALHES DOS SINAIS ==========
        if len(buy_signals) > 0:
            st.markdown("---")
            st.subheader("🟢 SINAIS DE COMPRA")
            
            for _, row in buy_signals.iterrows():
                ticker = row['ticker']
                
                with st.expander(f"📈 {ticker} - {row['status']}"):
                    st.write(f"**{row['descricao']}**")
                    
                    # Plano de trade
                    daily_df = results[ticker]['daily']
                    trade_plan = risk_mgr.generate_trade_plan(
                        daily_df,
                        entry_type='long',
                        target_multiplier=target_mult
                    )
                    
                    if trade_plan:
                        st.text(risk_mgr.format_trade_plan(trade_plan))
        
        # ========== DOWNLOAD ==========
        st.markdown("---")
        st.subheader("💾 Exportar Resultados")
        
        csv = convergence_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"cacas_scanner_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    st.info("👆 Clique em 🚀 ANALISAR para processar os ativos selecionados")

# ========== FOOTER ==========
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>🎯 Cacas Channel Scanner v1.0 | Feito com ❤️ para traders brasileiros</p>
    <p>⚠️ Este sistema é apenas educacional. Não é recomendação de investimento.</p>
</div>
""", unsafe_allow_html=True)
