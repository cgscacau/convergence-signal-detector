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
    .success-box {
        padding: 1rem;
        background-color: #1e4d2b;
        border-radius: 0.5rem;
        border-left: 4px solid #2ecc71;
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
        
        # Seleção de ativos específicos
        with st.expander("🔍 Selecionar ativos específicos"):
            search_query = st.text_input("🔎 Buscar:", placeholder="Ex: PETR, Petrobras")
            
            if search_query:
                filtered = asset_loader.search_assets(search_query, selected_categories)
                if not filtered.empty:
                    st.success(f"✅ {len(filtered)} encontrado(s)")
                    selected_tickers = st.multiselect(
                        "Escolha os ativos:",
                        options=filtered['ticker'].tolist(),
                        default=filtered['ticker'].tolist()[:5]
                    )
                else:
                    st.warning("Nenhum ativo encontrado")
                    selected_tickers = []
            else:
                # Lista padrão - top ativos
                default_list = assets_df['ticker'].tolist()[:10]
                selected_tickers = st.multiselect(
                    "Ativos selecionados:",
                    options=assets_df['ticker'].tolist(),
                    default=default_list,
                    help="Máximo recomendado: 20 ativos"
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
        index=1
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
    st.info("👈 **Comece selecionando ativos na barra lateral**")
    
    # Estatísticas
    st.subheader("📊 Ativos Disponíveis no Sistema")
    counts = asset_loader.count_assets()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📈 Ações", counts['Ação'])
    col2.metric("🏢 FIIs", counts['FII'])
    col3.metric("📊 ETFs", counts['ETF'])
    col4.metric("🌎 BDRs", counts['BDR'])
    col5.metric("📦 Total", counts['Total'])
    
    st.markdown("---")
    
    # Instruções
    st.subheader("📖 Como Usar")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **1️⃣ Configuração**
        - Selecione categorias de ativos
        - Escolha ativos específicos (até 20)
        - Defina o período de análise
        
        **2️⃣ Parâmetros (Opcional)**
        - Ajuste indicador Cacas Channel
        - Configure stop loss e alvo
        """)
    
    with col2:
        st.markdown("""
        **3️⃣ Análise**
        - Clique em 🚀 ANALISAR
        - Aguarde processamento
        - Visualize resultados
        
        **4️⃣ Resultados**
        - Veja convergências
        - Analise planos de trade
        - Exporte para CSV
        """)

elif analyze_button:
    # ========== PROCESSAMENTO ==========
    
    st.subheader("🔄 Processando Análise...")
    
    # Info inicial
    st.info(f"📊 Analisando {len(selected_tickers)} ativos no período de {period_label}")
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Inicializa
    indicator = CacasChannel(upper=upper, under=under, ema=ema)
    detector = ConvergenceDetector()
    risk_mgr = RiskManager(atr_multiplier=atr_mult)
    
    results = {}
    failed_tickers = []
    total = len(selected_tickers)
    
    for i, ticker in enumerate(selected_tickers):
        progress = (i + 1) / total
        progress_bar.progress(progress)
        status_text.text(f"📊 Processando: {ticker} ({i+1}/{total})")
        
        try:
            # Download
            daily_data = market_loader.get_daily_data(ticker, period=period)
            weekly_data = market_loader.get_weekly_data(ticker, period=period)
            
            # Valida
            if (market_loader.validate_dataframe(daily_data) and 
                market_loader.validate_dataframe(weekly_data)):
                
                # Calcula indicador
                daily_with_indicator = indicator.calculate_full(daily_data)
                weekly_with_indicator = indicator.calculate_full(weekly_data)
                
                # Detecta cruzamentos
                daily_with_indicator = indicator.detect_crossover(daily_with_indicator)
                weekly_with_indicator = indicator.detect_crossover(weekly_with_indicator)
                
                results[ticker] = {
                    'daily': daily_with_indicator,
                    'weekly': weekly_with_indicator
                }
            else:
                failed_tickers.append(ticker)
                
        except Exception as e:
            failed_tickers.append(ticker)
    
    progress_bar.empty()
    status_text.empty()
    
    # Resultado do processamento
    success_count = len(results)
    fail_count = len(failed_tickers)
    
    if success_count > 0:
        st.success(f"✅ **Sucesso!** {success_count}/{total} ativos processados")
        
        if fail_count > 0:
            with st.expander(f"⚠️ {fail_count} ativos sem dados disponíveis"):
                st.warning(f"**Ativos que falharam:** {', '.join(failed_tickers)}")
                st.info("""
                **💡 Possíveis causas:**
                - Ticker inválido ou incorreto
                - Ativo sem histórico no período selecionado
                - FII muito novo (< 6 meses)
                - Problemas temporários no Yahoo Finance
                
                **✅ Solução:**
                - Verifique se o ticker está correto
                - Tente outro período (ex: 6 meses)
                - Remova esses ativos da seleção
                """)
        
        # ========== ANÁLISE ==========
        st.markdown("---")
        st.subheader("📊 RESULTADOS DA ANÁLISE")
        
        # Escaneia
        convergence_results = detector.scan_multiple_assets(results)
        convergence_results = detector.sort_by_priority(convergence_results)
        
        # Tabela principal
        st.dataframe(
            convergence_results[['ticker', 'status', 'descricao']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "ticker": st.column_config.TextColumn("Ativo", width="small"),
                "status": st.column_config.TextColumn("Status", width="medium"),
                "descricao": st.column_config.TextColumn("Descrição", width="large")
            }
        )
        
        # ========== ESTATÍSTICAS ==========
        st.markdown("---")
        st.subheader("📈 Resumo dos Sinais")
        
        buy_signals = detector.get_buy_signals(convergence_results)
        sell_signals = detector.get_sell_signals(convergence_results)
        waiting = detector.get_waiting_signals(convergence_results)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🟢 Sinais de Compra", len(buy_signals))
        col2.metric("🔴 Sinais de Venda", len(sell_signals))
        col3.metric("🟡 Em Aguardo", len(waiting))
        col4.metric("📊 Total Analisado", len(convergence_results))
        
        # ========== DETALHES ==========
        if len(buy_signals) > 0:
            st.markdown("---")
            st.subheader("🟢 OPORTUNIDADES DE COMPRA")
            
            for idx, row in buy_signals.iterrows():
                ticker = row['ticker']
                
                with st.expander(f"📈 **{ticker}** - {row['status']}", expanded=False):
                    st.markdown(f"**{row['descricao']}**")
                    
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown("#### 📊 Análise Técnica")
                        daily_df = results[ticker]['daily']
                        latest = daily_df.iloc[-1]
                        
                        st.metric("Preço Atual", f"R$ {latest['Close']:.2f}")
                        st.metric("Sinal Diário", "Alta ✅" if latest['sinal'] == 1 else "Baixa ⏳")
                        
                    with col2:
                        st.markdown("#### 🎯 Plano de Trade")
                        trade_plan = risk_mgr.generate_trade_plan(
                            daily_df,
                            entry_type='long',
                            target_multiplier=target_mult
                        )
                        
                        if trade_plan:
                            st.metric("Stop Loss", f"R$ {trade_plan['stop_loss']['price']:.2f}")
                            st.metric("Alvo", f"R$ {trade_plan['target']['price']:.2f}")
                            st.metric("Risco/Retorno", f"1:{target_mult}")
        
        # ========== DOWNLOAD ==========
        st.markdown("---")
        st.subheader("💾 Exportar Resultados")
        
        csv = convergence_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Análise Completa (CSV)",
            data=csv,
            file_name=f"cacas_scanner_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    else:
        st.error("❌ **Nenhum ativo foi processado com sucesso**")
        
        st.markdown("""
        ### 🔧 Soluções:
        
        1. **Verifique os tickers**
           - Certifique-se que os códigos estão corretos
           - Exemplo correto: PETR4, VALE3, ITUB4
        
        2. **Tente outro período**
           - Alguns ativos não têm histórico longo
           - Experimente: 6 meses ou 1 ano
        
        3. **Selecione outros ativos**
           - Ativos líquidos funcionam melhor
           - Sugestão: PETR4, VALE3, ITUB4, BBDC4, BBAS3
        
        4. **Aguarde alguns minutos**
           - Pode ser problema temporário do Yahoo Finance
           - Tente novamente em 5-10 minutos
        """)
        
        if failed_tickers:
            st.warning(f"**Ativos testados:** {', '.join(failed_tickers)}")

else:
    st.info("👆 **Clique no botão 🚀 ANALISAR para processar os ativos selecionados**")
    
    if selected_tickers:
        st.success(f"✅ {len(selected_tickers)} ativos selecionados e prontos para análise")

# ========== FOOTER ==========
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888;'>
    <p><b>🎯 Cacas Channel Scanner v1.0.2</b> | Desenvolvido com ❤️ para traders brasileiros</p>
    <p>⚠️ <i>Sistema educacional - Não constitui recomendação de investimento</i></p>
    <p>📊 Powered by yfinance | 🚀 Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
