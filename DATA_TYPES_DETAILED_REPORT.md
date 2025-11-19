# RELATÓRIO DETALHADO - TIPOS DE DADOS MERCADO PAGO

**Data de Análise:** 2025-11-19
**Arquivo Recebimentos:** 202511r.xlsx (1.319 registros)
**Arquivo Settlement:** 202511s.xlsx (1.642 registros)

---

## 1. PAYMENT_METHOD (Arquivo Recebimentos)

### Valores Encontrados e Distribuição:

| PAYMENT_METHOD | Quantidade | Percentual | Categoria | Impacto na Conciliação |
|----------------|------------|------------|-----------|------------------------|
| **master** | 679 | 51.48% | Cartão de Crédito Mastercard | SIM - Afeta taxas e prazos |
| **visa** | 474 | 35.94% | Cartão de Crédito Visa | SIM - Afeta taxas e prazos |
| **available_money** | 112 | 8.49% | Saldo Disponível / Transferências | SIM - Operações internas |
| **elo** | 31 | 2.35% | Cartão de Crédito Elo | SIM - Afeta taxas e prazos |
| **amex** | 21 | 1.59% | Cartão de Crédito American Express | SIM - Afeta taxas e prazos |

### Detalhamento por Tipo:

#### 1.1 Cartões de Crédito (master, visa, elo, amex)
- **Total:** 1.205 transações (91.36%)
- **Características:**
  - Sempre tem INSTALLMENTS (ex: "2/3", "4/6", "1/1")
  - Sempre tem MP_FEE_AMOUNT (taxa do Mercado Pago)
  - RECORD_TYPE: "release"
  - DESCRIPTION: "payment"
- **Exemplo de valores:**
  - GROSS_AMOUNT: 353.87
  - MP_FEE_AMOUNT: -12.35
  - NET_CREDIT_AMOUNT: 341.52
- **Impacto na Conciliação:**
  - Cada parcela gera um lançamento separado
  - A taxa varia conforme a bandeira e número de parcelas
  - Data de liberação (RELEASE_DATE) pode ser diferente da aprovação (APPROVAL_DATE)

#### 1.2 Available Money (Saldo Disponível)
- **Total:** 112 transações (8.49%)
- **Características:**
  - DESCRIPTION: "reserve_for_payout"
  - Valores negativos em NET_DEBIT_AMOUNT
  - MP_FEE_AMOUNT: 0.00 (sem taxa)
  - Sem EXTERNAL_REFERENCE
- **Exemplo:**
  - NET_DEBIT_AMOUNT: 8031.00
  - GROSS_AMOUNT: -8031.00
  - DESCRIPTION: "reserve_for_payout"
- **Impacto na Conciliação:**
  - Representa transferências de saldo para conta bancária
  - NÃO é uma venda, mas uma movimentação interna
  - Deve ser EXCLUÍDO da conciliação de vendas
  - Deve ser rastreado separadamente para controle de saques

---

## 2. TRANSACTION_TYPE (Arquivo Settlement)

### Estrutura Importante:
O arquivo Settlement tem **DUAS** maneiras de identificar o tipo de transação:
1. **TRANSACTION_TYPE** - Tipo principal (381 SETTLEMENT, 11 PAYOUTS, 6 REFUND)
2. **DESCRIPTION** - Detalhamento adicional (1.244 INSTALLMENT)

### 2.1 TRANSACTION_TYPE: SETTLEMENT
- **Quantidade:** 381 transações (23.20%)
- **Descrição:** Liberação inicial de valores recebidos
- **Características:**
  - PAYMENT_METHOD_TYPE: "credit_card"
  - TRANSACTION_AMOUNT: Positivo (ex: 111.68)
  - FEE_AMOUNT: Negativo (ex: -3.45)
  - SETTLEMENT_NET_AMOUNT: Valor líquido após taxas
  - MONEY_RELEASE_DATE: Data futura de liberação
- **Exemplo:**
  ```
  TRANSACTION_AMOUNT: 111.68
  FEE_AMOUNT: -3.45
  SETTLEMENT_NET_AMOUNT: 108.23
  MONEY_RELEASE_DATE: 2025-12-01
  ```
- **Impacto na Conciliação:**
  - CRÍTICO - Este é o registro principal da venda
  - Usar SETTLEMENT_NET_AMOUNT para conciliação
  - Data de liberação pode ser até 30 dias após a venda

### 2.2 TRANSACTION_TYPE: PAYOUTS
- **Quantidade:** 11 transações (0.67%)
- **Descrição:** Transferência de saldo para conta bancária
- **Características:**
  - PAYMENT_METHOD_TYPE: " " (vazio)
  - TRANSACTION_AMOUNT: Negativo (ex: -8031.00)
  - FEE_AMOUNT: 0.00 (sem taxa)
  - SETTLEMENT_NET_AMOUNT: Negativo
  - MONEY_RELEASE_DATE: NaN (não tem data futura)
- **Exemplo:**
  ```
  TRANSACTION_AMOUNT: -8031.00
  FEE_AMOUNT: 0.00
  SETTLEMENT_NET_AMOUNT: -8031.00
  ```
- **Impacto na Conciliação:**
  - NÃO DEVE SER INCLUÍDO na conciliação de vendas
  - Representa apenas movimentação de saldo
  - Corresponde aos registros "available_money" do arquivo Recebimentos

### 2.3 TRANSACTION_TYPE: REFUND
- **Quantidade:** 6 transações (0.37%)
- **Descrição:** Estorno de pagamento ao cliente
- **Características:**
  - PAYMENT_METHOD_TYPE: "credit_card"
  - TRANSACTION_AMOUNT: Negativo (ex: -556.74)
  - FEE_AMOUNT: Positivo (ex: +19.43) - Taxa devolvida
  - SETTLEMENT_NET_AMOUNT: Negativo
  - Tem "refund_id" no METADATA
- **Exemplo:**
  ```
  TRANSACTION_AMOUNT: -556.74
  FEE_AMOUNT: 19.43 (taxa devolvida)
  SETTLEMENT_NET_AMOUNT: -537.31
  INSTALLMENTS: 5 (todas as parcelas estornadas)
  ```
- **Impacto na Conciliação:**
  - CRÍTICO - Deve ser SUBTRAÍDO das vendas
  - A taxa é parcialmente devolvida
  - Pode cancelar uma venda parcelada inteira

### 2.4 DESCRIPTION: INSTALLMENT
- **Quantidade:** 1.244 transações (75.76%)
- **Descrição:** Parcelas futuras de vendas parceladas
- **Características:**
  - TRANSACTION_TYPE: NaN (vazio)
  - TRANSACTION_AMOUNT: 0.00
  - PAYMENT_METHOD_TYPE: NaN
  - INSTALLMENT_NUMBER: Número da parcela (ex: "1/1", "2/3")
  - INSTALLMENT_NET_AMOUNT: Valor líquido da parcela
  - MONEY_RELEASE_DATE: Data futura de liberação
- **Exemplo:**
  ```
  DESCRIPTION: INSTALLMENT
  INSTALLMENT_NUMBER: 1/2
  INSTALLMENT_NET_AMOUNT: 119.06
  MONEY_RELEASE_DATE: 2025-12-01
  TRANSACTION_AMOUNT: 0.00
  ```
- **Impacto na Conciliação:**
  - CRÍTICO - Representa parcelas futuras da mesma venda
  - NÃO DEVE SER SOMADO ao total (duplicaria valores)
  - Serve para controlar quando cada parcela será liberada
  - Está relacionado ao SETTLEMENT principal via EXTERNAL_REFERENCE

---

## 3. ESTRUTURA DE PARCELAS NO SETTLEMENT

### Como funciona:

Para uma venda parcelada em 2x:
1. **Registro 1 (SETTLEMENT):**
   - TRANSACTION_TYPE: SETTLEMENT
   - TRANSACTION_AMOUNT: 246.73 (valor total)
   - SETTLEMENT_NET_AMOUNT: 238.12
   - INSTALLMENTS: 2

2. **Registro 2 (INSTALLMENT 1/2):**
   - DESCRIPTION: INSTALLMENT
   - INSTALLMENT_NUMBER: 1/2
   - INSTALLMENT_NET_AMOUNT: 119.06
   - MONEY_RELEASE_DATE: 2025-12-01

3. **Registro 3 (INSTALLMENT 2/2):**
   - DESCRIPTION: INSTALLMENT
   - INSTALLMENT_NUMBER: 2/2
   - INSTALLMENT_NET_AMOUNT: 119.06
   - MONEY_RELEASE_DATE: 2026-01-01

**IMPORTANTE:**
- O SETTLEMENT_NET_AMOUNT (238.12) = INSTALLMENT_NET_AMOUNT 1/2 (119.06) + INSTALLMENT_NET_AMOUNT 2/2 (119.06)
- Para conciliação, usar APENAS o SETTLEMENT_NET_AMOUNT
- Os registros INSTALLMENT são para controle de fluxo de caixa futuro

---

## 4. RESPOSTA JSON CONSOLIDADA

```json
{
  "payment_methods": {
    "master": {
      "count": 679,
      "percentage": 51.48,
      "description": "Cartão de Crédito Mastercard",
      "affects_reconciliation": true,
      "notes": "Afeta taxas (média 3.5%) e prazos de liberação",
      "example": {
        "GROSS_AMOUNT": "353.87",
        "MP_FEE_AMOUNT": "-12.35",
        "NET_CREDIT_AMOUNT": "341.52",
        "INSTALLMENTS": "2/3"
      }
    },
    "visa": {
      "count": 474,
      "percentage": 35.94,
      "description": "Cartão de Crédito Visa",
      "affects_reconciliation": true,
      "notes": "Afeta taxas (média 3.5%) e prazos de liberação",
      "example": {
        "GROSS_AMOUNT": "170.30",
        "MP_FEE_AMOUNT": "-11.49",
        "NET_CREDIT_AMOUNT": "158.81",
        "INSTALLMENTS": "4/6"
      }
    },
    "available_money": {
      "count": 112,
      "percentage": 8.49,
      "description": "Saldo Disponível - Transferências para conta bancária",
      "affects_reconciliation": false,
      "notes": "NÃO incluir na conciliação de vendas - são saques/transferências",
      "example": {
        "DESCRIPTION": "reserve_for_payout",
        "NET_DEBIT_AMOUNT": "8031.00",
        "GROSS_AMOUNT": "-8031.00"
      }
    },
    "elo": {
      "count": 31,
      "percentage": 2.35,
      "description": "Cartão de Crédito Elo",
      "affects_reconciliation": true,
      "notes": "Afeta taxas (média 3.5%) e prazos de liberação",
      "example": {
        "GROSS_AMOUNT": "147.96",
        "MP_FEE_AMOUNT": "-9.98",
        "NET_CREDIT_AMOUNT": "137.98",
        "INSTALLMENTS": "4/5"
      }
    },
    "amex": {
      "count": 21,
      "percentage": 1.59,
      "description": "Cartão de Crédito American Express",
      "affects_reconciliation": true,
      "notes": "Afeta taxas (média 4%) e prazos de liberação",
      "example": {
        "GROSS_AMOUNT": "125.20",
        "MP_FEE_AMOUNT": "-8.44",
        "NET_CREDIT_AMOUNT": "116.76",
        "INSTALLMENTS": "6/6"
      }
    }
  },
  "transaction_types": {
    "SETTLEMENT": {
      "count": 381,
      "percentage": 23.20,
      "description": "Liberação de valores recebidos - registro principal da venda",
      "affects_reconciliation": true,
      "critical": true,
      "notes": "Usar SETTLEMENT_NET_AMOUNT para conciliação. É o registro principal da venda.",
      "example": {
        "TRANSACTION_AMOUNT": "111.68",
        "FEE_AMOUNT": "-3.45",
        "SETTLEMENT_NET_AMOUNT": "108.23",
        "MONEY_RELEASE_DATE": "2025-12-01"
      }
    },
    "PAYOUTS": {
      "count": 11,
      "percentage": 0.67,
      "description": "Transferência de saldo para conta bancária",
      "affects_reconciliation": false,
      "critical": false,
      "notes": "NÃO incluir na conciliação de vendas - apenas movimentação de saldo",
      "example": {
        "TRANSACTION_AMOUNT": "-8031.00",
        "FEE_AMOUNT": "0.00",
        "SETTLEMENT_NET_AMOUNT": "-8031.00"
      }
    },
    "REFUND": {
      "count": 6,
      "percentage": 0.37,
      "description": "Estorno de pagamento - devolução ao cliente",
      "affects_reconciliation": true,
      "critical": true,
      "notes": "SUBTRAIR das vendas. Taxa é parcialmente devolvida.",
      "example": {
        "TRANSACTION_AMOUNT": "-556.74",
        "FEE_AMOUNT": "19.43",
        "SETTLEMENT_NET_AMOUNT": "-537.31",
        "INSTALLMENTS": "5"
      }
    },
    "INSTALLMENT": {
      "count": 1244,
      "percentage": 75.76,
      "description": "Parcelas futuras de vendas parceladas",
      "affects_reconciliation": false,
      "critical": true,
      "notes": "NÃO SOMAR ao total (duplicaria). Serve para controle de fluxo de caixa futuro.",
      "example": {
        "DESCRIPTION": "INSTALLMENT",
        "INSTALLMENT_NUMBER": "1/2",
        "INSTALLMENT_NET_AMOUNT": "119.06",
        "MONEY_RELEASE_DATE": "2025-12-01",
        "TRANSACTION_AMOUNT": "0.00"
      }
    }
  },
  "insights": {
    "payment_methods_affect_reconciliation": true,
    "payment_methods_notes": "Os métodos de pagamento afetam as taxas aplicadas pelo Mercado Pago. Cartões de crédito têm taxas entre 3.5% e 4%, enquanto 'available_money' não tem taxa mas representa saques que NÃO devem ser incluídos na conciliação de vendas.",

    "transaction_types_affect_reconciliation": true,
    "transaction_types_notes": "Os tipos de transação são CRÍTICOS para conciliação: SETTLEMENT adiciona valores (usar SETTLEMENT_NET_AMOUNT), REFUND subtrai valores, PAYOUTS não devem ser incluídos, e INSTALLMENT NÃO deve ser somado pois duplicaria os valores já contabilizados no SETTLEMENT.",

    "critical_rules": {
      "rule_1": "Para conciliação, usar APENAS registros com TRANSACTION_TYPE = 'SETTLEMENT' ou 'REFUND'",
      "rule_2": "EXCLUIR registros com TRANSACTION_TYPE = 'PAYOUTS'",
      "rule_3": "EXCLUIR registros com DESCRIPTION = 'INSTALLMENT' (são apenas controle de parcelas futuras)",
      "rule_4": "EXCLUIR registros de Recebimentos com PAYMENT_METHOD = 'available_money' E DESCRIPTION = 'reserve_for_payout'",
      "rule_5": "Para vendas parceladas, usar SETTLEMENT_NET_AMOUNT do registro principal, NÃO somar as parcelas individuais",
      "rule_6": "REFUND deve ser SUBTRAÍDO do total de vendas"
    },

    "summary": {
      "total_recebimentos": 1319,
      "total_settlement": 1642,
      "recebimentos_vendas": 1207,
      "recebimentos_saques": 112,
      "settlement_vendas": 381,
      "settlement_refunds": 6,
      "settlement_payouts": 11,
      "settlement_installments": 1244,
      "unique_payment_methods": 5,
      "unique_transaction_types": 3
    },

    "reconciliation_formula": {
      "description": "Fórmula correta para conciliação",
      "recebimentos": "SUM(NET_CREDIT_AMOUNT) WHERE PAYMENT_METHOD IN ('master','visa','elo','amex')",
      "settlement": "SUM(SETTLEMENT_NET_AMOUNT) WHERE TRANSACTION_TYPE IN ('SETTLEMENT','REFUND')",
      "exclude_from_both": [
        "PAYMENT_METHOD = 'available_money' no Recebimentos",
        "TRANSACTION_TYPE = 'PAYOUTS' no Settlement",
        "DESCRIPTION = 'INSTALLMENT' no Settlement"
      ]
    }
  }
}
```

---

## 5. RECOMENDAÇÕES PARA CONCILIAÇÃO

### 5.1 Arquivo Recebimentos (202511r.xlsx)
```sql
-- Filtros para incluir na conciliação:
WHERE PAYMENT_METHOD IN ('master', 'visa', 'elo', 'amex')
  AND RECORD_TYPE = 'release'
  AND DESCRIPTION = 'payment'

-- Usar o campo:
SUM(NET_CREDIT_AMOUNT)
```

### 5.2 Arquivo Settlement (202511s.xlsx)
```sql
-- Filtros para incluir na conciliação:
WHERE TRANSACTION_TYPE IN ('SETTLEMENT', 'REFUND')
  AND DESCRIPTION IS NULL  -- Excluir INSTALLMENT

-- Usar o campo:
SUM(SETTLEMENT_NET_AMOUNT)
```

### 5.3 Validações Importantes
1. Total de registros no Settlement deve ser MAIOR que Recebimentos (devido aos INSTALLMENTs)
2. Excluir PAYOUTS (transferências bancárias)
3. Excluir INSTALLMENT (duplicaria valores)
4. Excluir available_money do Recebimentos (saques)
5. Verificar se REFUND já está descontado ou precisa ser subtraído

---

## 6. CONCLUSÕES

### Descobertas Importantes:
1. **INSTALLMENT não é um tipo de transação, mas uma DESCRIÇÃO de parcelas futuras**
2. **75.76% dos registros no Settlement são INSTALLMENTs que NÃO devem ser somados**
3. **available_money e PAYOUTS são a mesma coisa: transferências bancárias**
4. **O Settlement tem MAIS registros que Recebimentos devido às parcelas individualizadas**

### Campos Críticos para Conciliação:
- **Recebimentos:** NET_CREDIT_AMOUNT (após taxas)
- **Settlement:** SETTLEMENT_NET_AMOUNT (após taxas)
- **Chave de relacionamento:** EXTERNAL_REFERENCE (liga os dois arquivos)

### Próximos Passos:
1. Atualizar o código de conciliação para aplicar os filtros corretos
2. Testar a conciliação com os dados de 202511
3. Validar se as parcelas estão sendo tratadas corretamente
4. Verificar se REFUND precisa ser subtraído separadamente
