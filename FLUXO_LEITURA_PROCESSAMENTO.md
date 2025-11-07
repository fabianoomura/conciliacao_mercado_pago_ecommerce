# Fluxo Completo de Leitura e Processamento - MP Recebíveis V3

## 📋 Resumo Executivo

O sistema processa dados de pagamento em 5 etapas principais:

1. **Settlement** - Lê transações aprovadas (pedidos + parcelas + refunds/chargebacks)
2. **Recebimentos** - Lê quando o dinheiro foi de fato recebido
3. **Movimentações** - Separa operações internas (não geram parcelas)
4. **Conciliação** - Faz match entre o que foi vendido vs o que foi recebido
5. **Fluxo de Caixa** - Calcula posição financeira

---

## 📂 Estrutura de Arquivos

```
data/
├── settlement/          ← Arquivo: TRANSAÇÕES VENDIDAS
│   ├── 202501s.xlsx     (Settlement = "o que foi vendido")
│   ├── 202502s.xlsx
│   └── ...
│
└── recebimentos/        ← Arquivo: DINHEIRO RECEBIDO
    ├── 202501r.xlsx     (Recebimentos = "o que foi recebido")
    ├── 202502r.xlsx
    └── ...
```

---

## 🔄 ETAPA 1: PROCESSAMENTO DO SETTLEMENT

### Entrada
- **Arquivo**: `data/settlement/*.xlsx`
- **Conteúdo**: Relatório da Mercado Pago com todas as transações aprovadas

### Saída
- **installments**: Lista de parcelas individuais
- **order_balances**: Resumo por pedido com totais e refunds

### O que acontece

#### 1.1 Leitura dos Arquivos
```
settlement_processor.process_files('data/settlement')
    ↓
Para cada arquivo .xlsx:
    - Ler com pandas.read_excel()
    - Converter para lista de dicionários
    - Extrair transações
```

#### 1.2 Organização por Pedido
```
Raw Transactions
    ↓
Agrupar por external_reference (ID do pedido)
    ↓
Para cada pedido:
    - Encontrar transação SETTLEMENT (pedido principal)
    - Encontrar linhas INSTALLMENT (parcelas)
    - Encontrar REFUND (estornos)
    - Encontrar CHARGEBACK (chargebacks)
```

**Exemplo de dados no Excel:**

| Row | TRANSACTION_TYPE | DESCRIPTION | EXTERNAL_REFERENCE | INSTALLMENT_NUMBER | INSTALLMENT_NET_AMOUNT | SETTLEMENT_NET_AMOUNT |
|-----|------------------|-------------|-------------------|-------------------|----------------------|----------------------|
| 284 | SETTLEMENT       | -           | r6cdyoYvCPGNvo... | -                 | 0.00               | 431.58              |
| 285 | -                | INSTALLMENT | r6cdyoYvCPGNvo... | 1/4               | 107.89             | 0.00                |
| 286 | -                | INSTALLMENT | r6cdyoYvCPGNvo... | 2/4               | 107.89             | 0.00                |
| 287 | -                | INSTALLMENT | r6cdyoYvCPGNvo... | 3/4               | 107.89             | 0.00                |
| 288 | -                | INSTALLMENT | r6cdyoYvCPGNvo... | 4/4               | 107.91             | 0.00                |
| ... | ... | ... | ... | ... | ... | ... |
| 1514| REFUND           | -           | r6cdyoYvCPGNvo... | -                 | 0.00               | -121.02             |

#### 1.3 Criação de Estruturas

**A. Para Pagamentos Parcelados (multi-installment):**

```python
# NÃO aplica ajustes aqui - deixa para o reconciliador!

installment = {
    'external_reference': 'r6cdyoYvCPGNvo...',
    'installment_number': '4',
    'total_installments': 4,
    'installment_net_amount_original': 107.91,   # Original
    'installment_net_amount': 107.91,            # Sem ajuste por enquanto
    'refund_applied': 0,                         # Será calculado depois
    'chargeback_applied': 0,                     # Será calculado depois
    'status': 'pending',
    'money_release_date': '2025-11-04',          # Quando parcela libera
    'approval_date': '2025-07-04'                # Quando foi aprovada
}
```

**B. Para Pagamentos à Vista (single installment):**

```python
# APLICA ajustes AQUI imediatamente

installment = {
    'external_reference': '...',
    'installment_number': '1',
    'total_installments': 1,
    'installment_net_amount_original': 500.00,
    'installment_net_amount': 378.98,     # Já descontou refund!
    'refund_applied': 121.02,             # Já aplicado
    'chargeback_applied': 0,
    'status': 'pending'
}
```

**C. Order Balance (agregado por pedido):**

```python
order_balances['r6cdyoYvCPGNvo...'] = {
    'total_gross': 447.19,          # Valor bruto da venda
    'total_net': 431.58,            # Após taxas
    'total_fee': -15.61,            # Taxa Mercado Pago
    'refunded': 121.02,             # Total de refund
    'refund_date': '2025-07-21',    # Quando refund foi aprovado
    'chargeback': 0,
    'chargeback_date': None,
    'final_net': 310.56,            # 431.58 - 121.02 (o que sobra)
    'installments': 4,              # 4 parcelas
    'payment_method': 'master',
    'payment_type': 'cartao_parcelado',
    'has_refund': True,
    'has_chargeback': False
}
```

### ⚠️ Erros Comuns no Settlement

1. **Refund/Chargeback duplicado**: Se há múltiplas linhas REFUND, todas são somadas ✓
2. **Parcelas com valores diferentes**: Sistema aceita (7 parcelas de R$100 + 1 de R$98 = R$798) ✓
3. **Refund em pagamento à vista**: Ajustado imediatamente no installment ✓
4. **Refund em parcelado**: NÃO é ajustado aqui, vai pro reconciliador ✓

---

## 💰 ETAPA 2: PROCESSAMENTO DE RECEBIMENTOS

### Entrada
- **Arquivo**: `data/recebimentos/*.xlsx`
- **Conteúdo**: Quando o dinheiro foi de fato recebido/liberado

### Saída
- **payments_only**: Pagamentos que geram receivables (match com installments)
- **movements**: Operações internas (não precisam match)

### O que acontece

#### 2.1 Leitura e Categorização

```
releases_processor.process_files('data/recebimentos')
    ↓
Para cada linha do Excel:
    - Extrair dados em formato padronizado
    - Categorizar como PAYMENT ou MOVEMENT
```

#### 2.2 Separação: Payment vs Movement

**PAYMENTS** (geram parcelas, precisam match):
```
description = 'payment'          → Venda normal
description = 'release'          → Liberação de saldo
record_type = 'SETTLEMENT'       → Programada
description = 'credit_card'      → Cartão de crédito
description = 'pix'              → PIX
description = 'boleto'           → Boleto
```

**MOVEMENTS** (operações internas, não precisam match):
```
description = 'refund'           → Estorno
description = 'chargeback'       → Chargeback
description = 'payout'           → Saque
description = 'reserve_...'      → Reservas
description = 'fee-...'          → Taxas
```

#### 2.3 Estrutura de um Payment

```python
payment = {
    'release_date': '2025-07-21',          # ⭐ QUANDO RECEBEU (para match)
    'approval_date': '2025-07-04',         # Quando foi aprovado
    'source_id': '116844842253',           # ID único da transação
    'external_reference': 'r6cdyoYvCPGNvo...', # ⭐ LINK COM INSTALLMENT
    'description': 'payment',              # Tipo
    'net_credit_amount': 107.89,           # ⭐ QUANTO RECEBEU
    'net_debit_amount': 0,
    'payment_method': 'master',
    'installments': '1',
    'currency': 'BRL'
}
```

### 📅 release_date vs approval_date

| Campo | O quê | Quando | Exemplo |
|-------|-------|--------|---------|
| **approval_date** | Quando venda foi aprovada | Data da compra | 2025-07-04 |
| **release_date** | Quando dinheiro foi recebido | Data do depósito | 2025-07-21 |

**Importante**: O `release_date` é o que importa para **conciliação**, porque representa quando o dinheiro realmente chegou.

---

## 🔍 ETAPA 3: PROCESSAMENTO DE MOVIMENTAÇÕES

### O que faz
```
movements_processor = MovementsProcessorV2(movements_list)
```

Processa operações internas da conta:
- Chargebacks (devoluções por disputa)
- Payouts (saques)
- Reservas
- Taxas especiais

**Não impacta as parcelas, apenas informativo.**

---

## ⚖️ ETAPA 4: CONCILIAÇÃO (O Coração do Sistema)

### O Problema
```
Settlement (o que foi vendido)          Recebimentos (o que foi recebido)
─────────────────────────             ────────────────────────────────
Parcela 1/4: R$ 107.89     ←Match→    Recebimento 1: R$ 107.89 (21/07)
Parcela 2/4: R$ 107.89     ←Match→    Recebimento 2: R$ 67.55  (04/08)
Parcela 3/4: R$ 107.89     ←Match→    Recebimento 3: R$ 67.55  (04/09)
Parcela 4/4: R$ 107.91     ←Match→    (ainda não chegou!)
```

**Questões a responder:**
1. Qual recebimento corresponde a qual parcela?
2. Parcelas recebidas antes do vencimento (adiantadas)?
3. Parcelas após vencimento (atrasadas)?
4. Parcelas nunca recebidas (pendentes)?
5. Refunds que precisam ser distribuídos entre as parcelas?

### Fluxo de Conciliação

```python
reconciliator = ReconciliatorV3(installments, payments, order_balances)
reconciliator.reconcile()
```

#### Passo 1: Calcular Saldos por Pedido

```python
_calculate_order_balances()
    ↓
Para cada pedido:
    Saldo Esperado = sum(installment_net_amount_original)
    Saldo Recebido = sum(payment net_credit_amount)
    Diferença = Saldo Esperado - Saldo Recebido
```

#### Passo 2: Reconciliar por Saldo

```python
_reconcile_by_order_balance(order_balances, today)
    ↓
Para cada pedido:
    1. Ordenar pagamentos por data (mais antigos primeiro)
    2. Ordenar parcelas por vencimento
    3. Fazer match: pagamento 1 → parcela 1, etc.
    4. Calcular status:
       - received: recebeu na data certa
       - received_advance: recebeu antes (adiantado)
       - overdue: venceu mas não recebeu
       - pending: ainda não recebeu
```

**Exemplo de Match:**

```
Parcelas:                       Pagamentos:
1/4 (libera 04/08) R$ 107.89    Pag 1 (21/07) R$ 107.89  ← Match! (adiantado!)
2/4 (libera 04/09) R$ 107.89    Pag 2 (04/08) R$ 67.55   ← Parcial!
3/4 (libera 04/10) R$ 107.89    Pag 3 (04/09) R$ 67.55   ← Parcial!
4/4 (libera 04/11) R$ 107.91    (falta R$ 73.36 e a 4ª parcela)

Status Final:
1/4 → received_advance (chegou dia 21/07, libera 04/08)
2/4 → received (chegou parcial no 04/08, completa no 04/09)
3/4 → received (chegou no 04/09)
4/4 → pending (não chegou nada ainda)
```

#### Passo 3: Aplicar Saldo Progressivo com Refunds

```python
_apply_progressive_balance_and_refunds()
    ↓
Para cada pedido com refund:
    1. Comparar refund_date com first_payment_date
    2. Se refund_date <= first_payment_date:
       → Distribuir refund em TODAS as parcelas
    3. Se refund_date > first_payment_date:
       → Distribuir refund APENAS em parcelas não recebidas
    4. Calcular refund por parcela = total_refund / num_parcelas
    5. Aplicar: new_amount = original_amount - refund_per_parcel
    6. Se result <= 0 → marcar como cancelada
```

**Exemplo com Refund:**

```
Ordem: r6cdyoYvCPGNvo...
├── Refund total: R$ 121.02
├── Refund date: 2025-07-21
├── First payment date: 2025-07-21  ← IGUAL! Usa <=
├── Decision: Distribuir em TODAS as 4 parcelas
├── Refund por parcela: 121.02 / 4 = R$ 30.255
└── Resultado:
    1/4: 107.89 - 30.255 = R$ 77.635  → status: received
    2/4: 107.89 - 30.255 = R$ 77.635  → status: received
    3/4: 107.89 - 30.255 = R$ 77.635  → status: received_advance
    4/4: 107.91 - 30.255 = R$ 77.655  → status: pending
```

#### Passo 4: Garantir Status Correto de Canceladas

```python
_ensure_cancelled_status()
    ↓
Para cada parcela com is_cancelled = True:
    Forçar status = 'cancelled'
    (pode ter sido marked como 'overdue' antes, agora corrige)
```

#### Passo 5: Gerar Estatísticas

```python
Resultado Final:
├── Pedidos fechados: 1183  (recebeu 100%)
├── Pedidos abertos: 1053   (recebeu parcialmente)
├── Parcelas conciliadas: 5125  (received)
├── Parcelas antecipadas: 2340  (received_advance)
├── Parcelas pendentes: 2458    (pending)
├── Parcelas atrasadas: 12      (overdue)
└── Parcelas canceladas: 95     (cancelled)
```

### ⚠️ Erros Comuns na Conciliação

1. **Refund não distribuído corretamente**
   - ❌ Problema: `refund_date < first_payment_date` (sem =)
   - ✓ Solução: `refund_date <= first_payment_date`

2. **Parcelas marked como "overdue" que são "cancelled"**
   - ❌ Problema: Verificação de status antiga
   - ✓ Solução: `_ensure_cancelled_status()` força correção

3. **Parcelas com payment ZERO mas não marcadas como recebidas**
   - ❌ Problema: Só conta pagamento quando `net_credit_amount > 0`
   - ✓ Solução: Verificar se há payment_date mesmo com valor 0

4. **Adiantamento não detectado**
   - ❌ Problema: Comparação errada entre release_date e money_release_date
   - ✓ Solução: Sempre comparar com data de vencimento da parcela

---

## 📊 ETAPA 5: FLUXO DE CAIXA

### O que faz
```python
cashflow = CashFlowCalculatorV2(installments)
```

Calcula a posição financeira:
- Quando cada parcela libera dinheiro
- Quanto estava liberado em cada data
- Projeções futuras

---

## 🐛 ERROS CONHECIDOS A INVESTIGAR

### 1. Parcelas com status errado
- [ ] Verificar se `_ensure_cancelled_status()` está sendo chamada
- [ ] Confirmar que `is_cancelled` e `status` estão sincronizados
- [ ] Checar se há parcelas "overdue" que deveriam ser "cancelled"

### 2. Refunds não somando corretamente
- [ ] Verificar se há múltiplas linhas REFUND no settlement
- [ ] Confirmar que `order_balances['refunded']` tem valor correto
- [ ] Testar cálculo de `refund_per_inst` = total / num_parcelas

### 3. Pagamentos não encontrando parcelas
- [ ] Verificar se `external_reference` é igual em settlement e recebimentos
- [ ] Confirmar que datas estão em formato correto (YYYY-MM-DD)
- [ ] Checar se há payments com `net_credit_amount = 0`

### 4. Adiantamentos (received_advance) incorretos
- [ ] Verificar comparação entre `release_date` (payment) vs `money_release_date` (installment)
- [ ] Confirmar que parcela anterior recebeu para ser adiantada
- [ ] Checar se `today` está sendo usado corretamente

### 5. Data/Hora mismatches
- [ ] Settlement tem `approval_date` como datetime com timezone
- [ ] Recebimentos tem `release_date` como data simples
- [ ] Reconciliador compara datas depois de converter - OK ✓

---

## 📈 Exemplos de Dados Reais

### Settlement Excel Típico
```
external_ref: r7eA2T63QGdKMwLY8zwox1cJU
transaction_type: SETTLEMENT
payment_method: master
installments: 3
total_gross: 300.00
total_net: 287.50
fee: -12.50
approval_date: 2025-09-15T10:30:00

├── INSTALLMENT 1/3: 95.83 (libera 2025-10-04)
├── INSTALLMENT 2/3: 95.84 (libera 2025-11-04)
├── INSTALLMENT 3/3: 95.83 (libera 2025-12-04)
└── REFUND: -85.00 (2025-09-20)
```

### Recebimentos Excel Típico
```
external_ref: r7eA2T63QGdKMwLY8zwox1cJU
description: payment
release_date: 2025-10-04
approval_date: 2025-09-15
net_credit_amount: 95.83
```

### Resultado Esperado
```
Parcela 1/3: R$ 95.83 - (85/3) = R$ 66.50 → received
Parcela 2/3: R$ 95.84 - (85/3) = R$ 66.50 → pending
Parcela 3/3: R$ 95.83 - (85/3) = R$ 66.50 → pending
```

---

## 🎯 Checklist de Validação

- [ ] Todos os Settlement files podem ser lidos
- [ ] Todas as parcelas têm installment_net_amount_original > 0
- [ ] order_balances tem refund_date para refunds
- [ ] Todos os Recebimentos files podem ser lidos
- [ ] Payments tem external_reference que existe no installments
- [ ] Pagamentos estão em ordem cronológica
- [ ] Refunds são distribuídos corretamente por data
- [ ] Parcelas canceladas têm is_cancelled = True E status = 'cancelled'
- [ ] Estatísticas de saída fazem sentido

---

## 📞 Suporte

Erros frequentes:
1. `UnicodeEncodeError` ao imprimir parcelas → Use UTF-8
2. `KeyError: 'refunded'` → order_balances não tem key
3. `TypeError: '<' not supported` → Datas em formato diferente
4. Parcelas não matching → external_reference com espaços ou caracteres especiais

