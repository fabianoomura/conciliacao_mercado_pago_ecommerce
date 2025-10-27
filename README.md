# Sistema de Conciliação Mercado Pago - V3.0 🚀

Sistema completo e robusto para processamento, conciliação e análise de transações do Mercado Pago.

---

## 🎯 NOVIDADES DA VERSÃO 3.0

### ✅ Funcionalidades Implementadas

#### 1. **Estornos Parciais e Totais (REFUND)**

- Detecção automática de estornos no settlement
- Distribuição proporcional do estorno entre todas as parcelas
- Ajuste de valores nas parcelas afetadas
- Devolução parcial de taxas pelo MP

#### 2. **Chargebacks e Reversões**

- Suporte a CHARGEBACK (contestação do cliente)
- Suporte a CHARGEBACK_CANCEL (ganhou a disputa)
- Controle de valores estornados e revertidos
- Tracking completo do fluxo de contestação

#### 3. **Adiantamento de Crédito**

- Detecção automática de parcelas antecipadas
- Identificação de parcelas fora de ordem
- Cálculo de dias de antecipação
- Status especial: `received_advance`

#### 4. **Taxas de Antecipação**

- Processamento de `fee-release_in_advance`
- Cálculo de taxa efetiva de adiantamento
- Separação de movimentações internas vs payments

#### 5. **Múltiplos Tipos de Pagamento**

- PIX (liberação imediata, taxa ~0,8%)
- Boleto (D+3, taxa ~0,87%)
- Saldo Mercado Pago (imediato, taxa ~2,99%)
- Crédito Mercado Livre (parcelado s/ juros, recebe à vista)
- Cartão Crédito Parcelado (mensal)
- Cartão Crédito à Vista
- Cartão Débito

#### 6. **Status Avançados**

- `pending` - Aguardando liberação
- `received` - Recebido na data prevista
- `received_advance` - Recebido antecipadamente
- `overdue` - Atrasado
- `cancelled` - Cancelado (estorno/chargeback)

---

## 📁 ARQUIVOS CRIADOS

### Processadores:

1. **`settlement_processor_v3.py`** ⭐

   - Processa Settlement Reports
   - Detecta e distribui estornos
   - Processa chargebacks
   - Identifica tipos de pagamento
   - Gera parcelas com valores ajustados

2. **`releases_processor_v2.py`** ⭐

   - Processa arquivos de recebimentos
   - Separa payments de movimentações internas
   - Extrai taxas de antecipação
   - Processa chargebacks nos releases

3. **`reconciliator_v3.py`** ⭐

   - Concilia parcelas com payments
   - Detecta adiantamentos
   - Calcula dias de antecipação
   - Identifica payments órfãos
   - Validação completa

4. **`movements_processor_v2.py`** ⭐

   - Processa movimentações especiais
   - Taxas de antecipação
   - Saques (payouts)
   - Reservas
   - Chargebacks

5. **`cashflow_v2.py`** ⭐

   - Fluxo de caixa diário/mensal
   - Considera adiantamentos
   - Separa por status
   - Próximos recebimentos

6. **`app_v3.py`** ⭐
   - Backend Flask completo
   - API RESTful
   - Integração de todos os processadores

---

## 🔧 INSTALAÇÃO

### 1. Estrutura de Pastas

```
mp_recebiveis/
├── app_v3.py                           ← Backend principal (NOVO!)
├── backend/
│   ├── processors/
│   │   ├── settlement_processor_v3.py  ← NOVO!
│   │   ├── releases_processor_v2.py    ← NOVO!
│   │   ├── reconciliator_v3.py         ← NOVO!
│   │   └── movements_processor_v2.py   ← NOVO!
│   └── utils/
│       └── cashflow_v2.py              ← NOVO!
├── frontend/
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── css/
│       └── js/
└── data/
    ├── settlement/      ← Seus arquivos .xls/.xlsx/.csv
    └── recebimentos/    ← Seus arquivos .xls/.xlsx
```

### 2. Substituir Arquivos

**IMPORTANTE:** Substitua os arquivos antigos pelos novos:

```bash
# Backup dos antigos (recomendado)
mv backend/processors/settlement_processor_v2.py backend/processors/settlement_processor_v2_OLD.py
mv backend/processors/releases_processor.py backend/processors/releases_processor_OLD.py
mv backend/processors/reconciliator_v2.py backend/processors/reconciliator_v2_OLD.py

# Copiar novos processadores
cp settlement_processor_v3.py backend/processors/
cp releases_processor_v2.py backend/processors/
cp reconciliator_v3.py backend/processors/
cp movements_processor_v2.py backend/processors/
cp cashflow_v2.py backend/utils/

# Substituir app.py
mv app.py app_OLD.py
cp app_v3.py app.py
```

### 3. Executar

```bash
python app.py
```

Acesse: **http://localhost:9000**

---

## 📊 CASOS DE USO SUPORTADOS

### 1️⃣ **Venda Normal Parcelada**

```
Settlement:
- Transação: R$ 1.427,13
- Taxa: -R$ 49,81
- Líquido: R$ 1.377,32
- Parcelas: 6x R$ 229,55

Releases:
- 6 payments de R$ 229,55 cada
- Status: received

✅ Conciliação: 100%
```

### 2️⃣ **Venda com Estorno Parcial**

```
Settlement:
- Venda: R$ 1.377,32 (6x)
- Estorno: -R$ 135,68
- Novo Total: R$ 1.241,64

Ajuste por parcela:
- Original: R$ 229,55
- Ajustado: R$ 206,94 (-R$ 22,61)

Releases:
- 6 payments de R$ 206,94 cada
- Status: received

✅ Conciliação: 100%
```

### 3️⃣ **Chargeback Total**

```
Settlement:
- Venda: R$ 1.176,26 (6x)
- Chargeback 1: -R$ 1.133,54
- Chargeback 2: -R$ 42,72
- Total: -R$ 1.176,26

Status: cancelled
✅ Venda totalmente cancelada
```

### 4️⃣ **Adiantamento de Crédito**

```
Settlement:
- Venda 22/09: R$ 555,76 (5x)
- Parcela 1/5: vencimento 22/10
- Parcela 2/5: vencimento 22/11
- Parcela 3/5: vencimento 22/12

Releases:
- 22/10 19:46: Parcela 2/5 (ADIANTADA!)
- 22/10 19:57: Parcela 3/5 (ADIANTADA!)
- 22/10 20:05: Parcela 1/5

Status:
- 2/5: received_advance (30 dias de antecipação)
- 3/5: received_advance (60 dias de antecipação)
- 1/5: received

Taxa de Antecipação:
- fee-release_in_advance: R$ 904,19
```

### 5️⃣ **Pagamento PIX**

```
Settlement:
- Método: bank_transfer → pix
- Valor: R$ 252,18
- Taxa: -R$ 2,02 (0,8%)
- Líquido: R$ 250,16
- Liberação: IMEDIATA

Releases:
- 1 payment de R$ 250,16
- Mesmo dia da venda

✅ PIX identificado automaticamente
```

---

## 🔍 API ENDPOINTS

### Status e Processamento

```
GET  /api/status          # Status do sistema
POST /api/process         # Processar dados
GET  /api/reset           # Limpar cache
GET  /api/summary         # Resumo completo
```

### Transações e Parcelas

```
GET  /api/transactions              # Todas as transações
GET  /api/installments/pending      # Parcelas pendentes
GET  /api/installments/received     # Parcelas recebidas
GET  /api/installments/overdue      # Parcelas atrasadas
GET  /api/installments/advance      # Parcelas antecipadas (NOVO!)
```

### Fluxo de Caixa

```
GET  /api/cashflow/monthly    # Fluxo mensal
GET  /api/cashflow/daily      # Fluxo diário (NOVO!)
GET  /api/cashflow/upcoming   # Próximos 7 dias (NOVO!)
```

### Conciliação

```
GET  /api/reconciliation      # Relatório completo
GET  /api/orphan_payments     # Payments órfãos
```

### Movimentações (NOVO!)

```
GET  /api/movements/advance_fees  # Taxas de antecipação
GET  /api/movements/payouts       # Saques
GET  /api/movements/chargebacks   # Chargebacks
GET  /api/movements/summary       # Resumo completo
```

---

## 📈 MELHORIAS NA CONCILIAÇÃO

### ✅ Antes (V2):

```python
# Match simples
if external_ref == payment.ref and valor == payment.valor:
    status = 'received'
```

### ⭐ Agora (V3):

```python
# Match inteligente
if external_ref == payment.ref and abs(valor - payment.valor) <= 0.02:
    if payment.date < expected_date:
        status = 'received_advance'
        days_advance = (expected_date - payment.date).days
    else:
        status = 'received'

    # Considera estornos
    adjusted_amount = original_amount + refund_applied
```

---

## 🎯 VALIDAÇÕES IMPLEMENTADAS

### 1. **Validação de Valores**

```python
Total Esperado = Total Recebido + Total Pendente + Total Atrasado
```

### 2. **Validação de Payments**

```python
Total Payments = Parcelas Recebidas + Payments Órfãos
```

### 3. **Validação de Movimentações**

```python
Saldo MP = Total Recebido - Saques - Taxas Antecipação - Chargebacks
```

---

## 🐛 TROUBLESHOOTING

### Erro: "Valores não batem"

1. Verifique se há estornos não processados
2. Confira se todos os arquivos foram carregados
3. Execute `/api/reconciliation` para ver detalhes
4. Verifique payments órfãos em `/api/orphan_payments`

### Erro: "Parcelas não conciliam"

1. Verifique se o formato dos arquivos está correto
2. Confirme se as datas estão no formato ISO
3. Execute `/api/reset` e reprocesse

### Taxa de antecipação não aparece

1. Verifique se o arquivo de releases contém `fee-release_in_advance`
2. Confirme que está usando `ReleasesProcessorV2`
3. Consulte `/api/movements/advance_fees`

---

## 📝 CHANGELOG V3.0

### Adicionado ✅

- Suporte completo a estornos parciais e totais
- Suporte a chargebacks e reversões
- Detecção automática de adiantamento de crédito
- Processamento de taxas de antecipação
- Identificação de múltiplos tipos de pagamento
- Status avançados (received_advance, overdue, etc)
- Fluxo de caixa com adiantamento
- Validações cruzadas completas
- API endpoints para movimentações

### Melhorado 🔧

- Match de parcelas com tolerância de R$ 0,02
- Distribuição proporcional de estornos
- Performance no processamento de grandes volumes
- Separação clara entre payments e movimentações
- Detecção de payments órfãos

### Corrigido 🐛

- Conciliação de parcelas fora de ordem
- Valores ajustados com estorno
- Match de parcelas com datas diferentes
- Performance com múltiplos arquivos

---

## 🚀 PRÓXIMOS PASSOS

Sugestões para V4.0:

1. **Dashboard Web Interativo**

   - Gráficos de fluxo de caixa
   - Filtros por período/tipo de pagamento
   - Drill-down em transações

2. **Alertas Automáticos**

   - Parcelas atrasadas
   - Chargebacks
   - Valores divergentes

3. **Exportação**

   - Excel consolidado
   - PDF com relatórios
   - CSV customizados

4. **Integrações**
   - API do Mercado Pago (direto)
   - Sistemas ERP
   - Bancos (OFX/CNAB)

---

## 📞 SUPORTE

Sistema desenvolvido para facilitar a gestão financeira e conciliação de recebíveis do Mercado Pago.

**Versão:** 3.0  
**Data:** Outubro 2025  
**Linguagem:** Python 3.x + Flask

---

## 🎉 CONCLUSÃO

O Sistema V3.0 está **100% funcional** e suporta:

✅ Todos os tipos de pagamento do Mercado Pago  
✅ Estornos parciais e totais  
✅ Chargebacks e reversões  
✅ Adiantamento de crédito  
✅ Taxas de antecipação  
✅ Múltiplos status de parcelas  
✅ Validação completa de valores  
✅ API RESTful completa

**Testado com dados reais fornecidos! 🚀**
