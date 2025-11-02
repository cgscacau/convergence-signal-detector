"""
Script de teste para diagnosticar problemas com yfinance
"""

import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("🔍 DIAGNÓSTICO DE CONEXÃO YFINANCE")
print("=" * 60)

# Tickers para testar
test_tickers = [
    "PETR4.SA",
    "VALE3.SA", 
    "ITUB4.SA",
    "BBDC4.SA",
    "BBAS3.SA"
]

print("\n📊 Testando download com diferentes métodos...\n")

for ticker in test_tickers:
    print(f"\n{'=' * 60}")
    print(f"🎯 Testando: {ticker}")
    print('=' * 60)
    
    # MÉTODO 1: Ticker().history()
    print("\n[Método 1] Ticker().history()")
    try:
        stock = yf.Ticker(ticker)
        data1 = stock.history(period="1mo", interval="1d")
        
        if data1 is not None and not data1.empty:
            print(f"✅ SUCESSO! {len(data1)} dias baixados")
            print(f"   Último preço: R$ {data1['Close'].iloc[-1]:.2f}")
            print(f"   Colunas: {list(data1.columns)}")
        else:
            print("❌ FALHOU - DataFrame vazio")
    except Exception as e:
        print(f"❌ ERRO: {str(e)[:100]}")
    
    # MÉTODO 2: download()
    print("\n[Método 2] yf.download()")
    try:
        data2 = yf.download(
            ticker,
            period="1mo",
            progress=False,
            auto_adjust=False
        )
        
        if data2 is not None and not data2.empty:
            print(f"✅ SUCESSO! {len(data2)} dias baixados")
            print(f"   Último preço: R$ {data2['Close'].iloc[-1]:.2f}")
        else:
            print("❌ FALHOU - DataFrame vazio")
    except Exception as e:
        print(f"❌ ERRO: {str(e)[:100]}")
    
    # MÉTODO 3: Info do ticker
    print("\n[Método 3] Informações do ticker")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if info and 'longName' in info:
            print(f"✅ Ticker válido!")
            print(f"   Nome: {info.get('longName', 'N/A')}")
            print(f"   Setor: {info.get('sector', 'N/A')}")
        else:
            print("⚠️ Ticker pode estar inválido")
    except Exception as e:
        print(f"❌ ERRO: {str(e)[:100]}")

print("\n" + "=" * 60)
print("📋 RESUMO")
print("=" * 60)

print("\n✅ Se pelo menos 1 método funcionou: Código está OK")
print("❌ Se todos falharam: Pode ser:")
print("   1. Problema de conexão")
print("   2. Yahoo Finance bloqueado")
print("   3. Versão do yfinance incompatível")

print("\n🔧 Informações do sistema:")
print(f"   yfinance version: {yf.__version__}")

print("\n💡 PRÓXIMOS PASSOS:")
print("   1. Se funcionou: O app deve funcionar")
print("   2. Se falhou: Tente 'pip install --upgrade yfinance'")
print("   3. Se persistir: Use VPN ou aguarde alguns minutos")

print("\n" + "=" * 60)
