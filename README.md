# Sistema de Conciliação Mercado Pago - V3.1 🚀

Sistema completo para processamento, conciliação e análise de transações do Mercado Pago com suporte a múltiplos tipos de pagamento, estornos, chargebacks e adiantamentos.

## ⚡ Principais Funcionalidades

✅ **Reconciliação Balance-Based V3.1** - Novos algoritmos que evitam falsos positivos
✅ **Suporte a Estornos Parciais e Totais** - Distribuição inteligente entre parcelas
✅ **Chargebacks e Reversões** - Rastreamento completo de disputas
✅ **Adiantamento de Crédito** - Detecção automática e cálculo de dias
✅ **Múltiplos Tipos de Pagamento** - PIX, Boleto, Cartão, Saldo MP, etc.
✅ **API RESTful Completa** - Endpoints para transações, parcelas e fluxo de caixa
✅ **Dashboard Web Interativo** - Visualização em tempo real dos dados

## 🚀 Quick Start

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Preparar Dados

Coloque seus arquivos do Mercado Pago nas pastas:

```
data/
├── settlement/      ← Settlement Reports (.xlsx)
└── recebimentos/    ← Releases/Recebimentos (.xlsx)
```

### 3. Executar

```bash
python app.py
```

Acesse: **http://localhost:9000**

## 📁 Estrutura do Projeto

```
mp_recebiveis/
├── app.py                              ← Backend Flask
├── setup.py                            ← Inicialização do projeto
├── requirements.txt                    ← Dependências
│
├── backend/
│   ├── processors/
│   │   ├── settlement_processor.py     ← Processa Settlement Reports
│   │   ├── releases_processor.py       ← Processa Releases/Recebimentos
│   │   ├── reconciliator.py            ← Conciliação Balance-Based V3.1
│   │   └── movements_processor.py      ← Processa movimentações especiais
│   │
│   └── utils/
│       └── cashflow.py                 ← Cálculo de fluxo de caixa
│
├── frontend/
│   ├── templates/
│   │   └── index.html                  ← Interface web
│   │
│   └── static/
│       ├── css/style.css               ← Estilos
│       └── js/app.js                   ← Lógica frontend
│
└── data/
    ├── settlement/                     ← Dados de settlement
    └── recebimentos/                   ← Dados de recebimentos
```

## 📊 Endpoints da API

### Status e Processamento
```
GET  /api/status          # Status do sistema
POST /api/process         # Processar dados
GET  /api/reset           # Limpar cache
GET  /api/summary         # Resumo completo
```

### Parcelas (Installments)
```
GET  /api/installments/pending     # Parcelas pendentes
GET  /api/installments/received    # Parcelas recebidas
GET  /api/installments/overdue     # Parcelas atrasadas
GET  /api/installments/advance     # Parcelas antecipadas
```

### Fluxo de Caixa
```
GET  /api/cashflow/daily       # Fluxo diário
GET  /api/cashflow/monthly     # Fluxo mensal
GET  /api/cashflow/upcoming    # Próximos 7 dias
```

### Transações
```
GET  /api/transactions         # Todas as transações
GET  /api/movements/advance_fees  # Taxas de antecipação
GET  /api/movements/payouts       # Saques
GET  /api/movements/chargebacks   # Chargebacks
GET  /api/movements/summary       # Resumo de movimentações
```

## 🔧 Configuração

### Variáveis de Ambiente (Opcional)

```bash
FLASK_ENV=production  # ou development
FLASK_PORT=9000
```

### Estrutura de Dados Esperada

**Settlement Reports:**
- Colunas: ID da Transação, Data, Tipo, Método de Pagamento, Valor, Taxa, Valor Líquido, Número de Parcelas
- Formato: .xlsx, .xls ou .csv
- Períodos: Arquivos mensais (202501s.xlsx, 202502s.xlsx, etc.)

**Releases/Recebimentos:**
- Colunas: Release ID, Data de Liberação, ID Transação, Valor Bruto, Taxa MP, Valor Líquido
- Formato: .xlsx
- Períodos: Arquivos mensais (202501r.xlsx, 202502r.xlsx, etc.)

## 📈 Algoritmo de Conciliação V3.1

A reconciliação é baseada em **saldo de pedido** (Balance-Based):

```
1. Agrupar transações por ID do pedido (external_reference)
2. Calcular:
   - Total esperado = Σ(valor_parcelas_ativas)
   - Total recebido = Σ(valor_payments)
3. Comparar saldos:
   - Se balanceiam (tol. R$0,02) → Pedido FECHADO
   - Se falta receber → Parcelas PENDENTES
   - Se vencido → Parcelas ATRASADAS
4. Distribuir estornos proporcionalmente
```

**Vantagens:**
- Tolera estornos parciais
- Detecta refunds não lineares
- Reduz falsos positivos de "atraso"
- Suporta múltiplos payments por pedido

## 🎯 Casos de Uso Suportados

### 1️⃣ Venda Simples Parcelada
- Múltiplas parcelas
- Recebimento conforme agendado
- Sem estornos ou chargebacks

### 2️⃣ Estorno Parcial
- Venda com reembolso total ou parcial
- Redistribuição proporcional entre parcelas
- Ajuste automático de valores

### 3️⃣ Chargeback/Disputa
- Contestação do cliente
- Reversão total ou parcial
- Rastreamento de status

### 4️⃣ Adiantamento de Crédito
- Recebimento antecipado de parcelas futuras
- Cálculo automático de dias de antecipação
- Taxas de antecipação processadas

### 5️⃣ Múltiplos Métodos de Pagamento
- PIX (taxa ~0,8%, liberação imediata)
- Boleto (taxa ~0,87%, D+3)
- Cartão Crédito (taxa ~2,99%)
- Saldo Mercado Pago (taxa variável)
- Crédito Mercado Livre

## 🔍 Troubleshooting

### "Valores não batem"
1. Verifique se há estornos no settlement não processados
2. Confirme que todos os arquivos foram carregados
3. Execute `/api/reset` e reprocesse

### "Parcelas não conciliam"
1. Valide o formato dos arquivos (colunas esperadas)
2. Confirme que external_reference existe em ambos os arquivos
3. Verifique se as datas estão em formato ISO (YYYY-MM-DD)

### "Datas incorretas"
1. Verifique o timezone do servidor
2. Confirme que money_release_date vem do settlement
3. Para parcelas recebidas, received_date vem do releases

## 📋 Requisitos

- Python 3.8+
- Flask 3.0.0
- openpyxl 3.1.2
- pandas 2.1.0
- Navegador moderno (Chrome, Firefox, Safari, Edge)

## 📝 Changelog V3.1

### ✅ Adicionado
- Reconciliador Balance-Based V3.1 (reduz falsos positivos)
- Corrigida data de exibição no frontend (timezone fix)
- Sorting automático das abas por data
- Cálculo correto de saldo pendente

### 🔧 Melhorado
- Parsing seguro de datas ISO com timezone
- Algoritmo de matching com 3 fases
- Distribuição não-linear de estornos
- Performance na reconciliação

### 🐛 Corrigido
- Exibição de pendentes em data errada (28/10 → 29/10)
- Atribui saldo pendente à última parcela (não distribuído linearmente)
- Timezone offset em formatação de datas JavaScript

## 📞 Suporte

**Versão:** 3.1
**Data:** Outubro 2025
**Linguagem:** Python 3.x + Flask + Vanilla JavaScript

---

**Sistema 100% funcional e testado com dados reais! 🚀**
