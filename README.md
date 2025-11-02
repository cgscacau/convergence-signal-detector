# 🎯 Cacas Channel Scanner

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31+-FF4B4B.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![B3](https://img.shields.io/badge/Market-B3%20Brasil-yellow.svg)

**Scanner de convergências multi-timeframe para o mercado brasileiro**

[🚀 Demo Live](#) | [📖 Documentação](#funcionalidades) | [🐛 Report Bug](../../issues)

</div>

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Funcionalidades](#-funcionalidades)
- [Como Funciona](#-como-funciona)
- [Tecnologias](#-tecnologias)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Roadmap](#-roadmap)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)
- [Contato](#-contato)

---

## 🎯 Sobre o Projeto

O **Cacas Channel Scanner** é uma ferramenta de análise técnica que identifica automaticamente oportunidades de trading no mercado brasileiro (B3) através da convergência de sinais em múltiplos timeframes.

### 🔍 O que ele faz?

Analisa simultaneamente **gráficos semanais e diários** de centenas de ativos usando o indicador **Cacas Channel**, detectando:

- ✅ **Convergências de alta**: Quando ambos os timeframes estão alinhados para compra
- ❌ **Convergências de baixa**: Quando ambos os timeframes estão alinhados para venda  
- ⚡ **Setups ideais**: Cruzamentos que completam a convergência (sinais de entrada)
- 🎯 **Gestão de risco**: Stop loss e alvos calculados automaticamente via ATR

### 💡 Para quem é?

- Traders de posição (swing trade)
- Investidores que buscam pontos de entrada técnicos
- Analistas que precisam monitorar múltiplos ativos
- Quem deseja automatizar análises multi-timeframe

---

## ⚡ Funcionalidades

### 📊 Análise Técnica

- [x] **Indicador Cacas Channel** completo (baseado no Pine Script original)
- [x] **Multi-timeframe**: Análise simultânea semanal + diário
- [x] **Detector de convergências**: Identifica alinhamento entre timeframes
- [x] **Detector de cruzamentos**: Encontra setups de entrada ideais
- [x] **Volatilidade histórica**: Mensal, trimestral e anual
- [x] **ATR Stop Loss**: Cálculo automático de stop baseado em ATR × 1.5
- [x] **Alvos múltiplos**: 1.5x, 2x, 2.5x ou 3x o risco

### 🎨 Interface

- [x] **Gráficos interativos**: Visualização lado a lado (semanal + diário)
- [x] **Tabela de sinais**: Lista todos os ativos com status de convergência
- [x] **Filtros avançados**: Por tipo de ativo, período, liquidez
- [x] **Parâmetros ajustáveis**: Customize o indicador em tempo real
- [x] **Marcações visuais**: Entrada, stop e alvo nos gráficos
- [x] **Tema dark**: Interface otimizada para longas análises

### 📈 Cobertura de Ativos

- **~450 Ações**: PETR4, VALE3, ITUB4, BBAS3, etc.
- **~300 FIIs**: HGLG11, KNRI11, MXRF11, VISC11, etc.
- **~100 ETFs**: BOVA11, SMAL11, IVVB11, etc.
- **~200 BDRs**: AAPL34, MSFT34, GOGL34, TSLA34, etc.

**Total: Mais de 1.000 ativos da B3**

---

## 🔬 Como Funciona

### 📐 O Indicador Cacas Channel

O indicador é composto por 5 linhas principais:

