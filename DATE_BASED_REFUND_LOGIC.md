# Implementação: Lógica de Refund Baseada em Datas

## Problema Identificado

O sistema estava distribuindo refund **apenas nas parcelas não recebidas**, mas não considerava **quando o refund foi aplicado**.

### Cenário Real: rPLMibwNTXTouHjeU5gXmphIE

```
TIMELINE:
04/09/2025 - Venda: R$ 1.516,38 (6 parcelas)
15/09/2025 - REFUND: R$ 758,19 ← ANTES de qualquer recebimento!
04/10/2025 - Parcela 1 recebida: R$ 121,95

PROBLEMA ANTERIOR:
  Sistema via:
  ├─ Parcela 1 foi recebida por R$ 121,95
  └─ Há refund de R$ 731,73
  └─ Distribuir refund apenas nas 5 não recebidas

  Resultado ERRADO:
    ├─ Parcela 1: R$ 243,91 (intacta)
    └─ Parcelas 2-6: R$ 97,56 (com refund reduzido)
    └─ ERRADO! Refund deveria ter sido antes da parcela 1!
```

## Solução Implementada

### Passo 1: Settlement Processor - Armazenar Data do Refund

**Arquivo:** `settlement_processor.py` (linhas 152-177)

```python
# Extrair data do refund (se houver)
refund_date = None
if refunds:
    refund_date = self._parse_date(refunds[0].get('approval_date'))

# Salvar no order_balances
self.order_balances[external_ref] = {
    ...
    'refund_date': refund_date,  # NOVO!
    ...
}
```

### Passo 2: Reconciliador - Comparar Datas

**Arquivo:** `reconciliator.py` (linhas 665-806)

**Novo Método:** `_apply_progressive_balance_and_refunds()`

```python
# Encontrar primeira data de payment
first_payment_date = None
if payments:
    payment_dates = [self._parse_date_safe(p.get('release_date')) for p in payments]
    payment_dates = [d for d in payment_dates if d]
    if payment_dates:
        first_payment_date = min(payment_dates)

# Verificar se refund foi ANTES de todos os payments
refund_before_all_payments = True
if first_payment_date and refund_date:
    refund_before_all_payments = refund_date < first_payment_date
```

### Passo 3: Distribuir Baseado em Datas

```python
if refund_before_all_payments:
    # Refund foi ANTES - distribuir em TODAS as parcelas
    all_insts = [i for i in installments]
    num_insts = len(all_insts)
    refund_per_inst = total_refund / num_insts

    for inst in all_insts:
        self._apply_adjustment_to_installment(inst, refund_per_inst, ...)
else:
    # Refund foi DEPOIS - distribuir apenas nas não recebidas
    unreceived_insts = [i for i in installments if not received]
    num_unreceived = len(unreceived_insts)
    refund_per_inst = total_refund / num_unreceived

    for inst in unreceived_insts:
        self._apply_adjustment_to_installment(inst, refund_per_inst, ...)
```

## Exemplos Práticos

### Exemplo 1: Refund ANTES de Qualquer Pagamento

```
Venda: 04/09/2025
Refund: 15/09/2025 ← ANTES!
Primeiro Payment: 04/10/2025

Lógica: refund_date (15/09) < first_payment_date (04/10) = TRUE

Ação: Distribuir em TODAS as 6 parcelas

Cálculo:
  Refund total: R$ 731,73
  Refund por parcela: 731,73 / 6 = R$ 121,96

  Cada parcela fica:
    243,91 - 121,96 = R$ 121,95

Resultado CORRETO:
  Parcela 1 (recebida): R$ 121,95 ✓
  Parcelas 2-6 (pendentes): R$ 121,95 cada ✓
```

### Exemplo 2: Refund DEPOIS de Alguns Pagamentos

```
Venda: 04/09/2025
Primeiro Payment: 04/10/2025
Refund: 15/10/2025 ← DEPOIS!

Lógica: refund_date (15/10) > first_payment_date (04/10) = FALSE (depois)

Ação: Distribuir APENAS nas 5 não recebidas

Cálculo:
  Refund total: R$ 731,73
  Parcelas não recebidas: 5
  Refund por parcela: 731,73 / 5 = R$ 146,35

  Resultado:
    Parcela 1 (recebida): R$ 243,91 (sem alteração)
    Parcelas 2-6 (pendentes): 243,91 - 146,35 = R$ 97,56 cada

Resultado CORRETO:
  Parcela 1 mantém valor original ✓
  Parcelas não recebidas sofrem o refund ✓
```

### Exemplo 3: Sem Pagamento Antes do Refund

```
Venda: 04/09/2025
Refund: 15/09/2025
Nenhum Payment ainda

Lógica: refund_before_all_payments = TRUE (por padrão, sem payments)

Ação: Distribuir em TODAS as 6 parcelas

Cálculo:
  Mesma que Exemplo 1
  Cada uma: R$ 121,95
```

## Código do Helper

**Novo Método:** `_apply_adjustment_to_installment()` (linhas 778-806)

```python
def _apply_adjustment_to_installment(self, inst, refund_per_inst, chargeback_per_inst):
    """Helper para aplicar refund/chargeback a uma parcela"""
    original_amount = inst.get('installment_net_amount_original', ...)
    adjusted_amount = original_amount - refund_per_inst - chargeback_per_inst

    # Garantir valor >= 0
    if adjusted_amount < 0:
        adjusted_amount = 0

    inst['installment_net_amount'] = adjusted_amount
    inst['refund_applied'] = refund_per_inst
    inst['chargeback_applied'] = chargeback_per_inst
    inst['has_adjustment'] = (refund_per_inst > 0 or chargeback_per_inst > 0)

    # Marcar como cancelada se valor <= 0
    if adjusted_amount <= 0 and (refund_per_inst > 0 or chargeback_per_inst > 0):
        inst['is_cancelled'] = True
        inst['status'] = 'cancelled'
        inst['cancelled_reason'] = ...  # full_refund, etc
```

## Impacto no Sistema

### Antes (❌ Incorreto)

```
Pedido rPLMibwNTXTouHjeU5gXmphIE:
  Parcela 1: R$ 243,91 (sem refund)
  Parcelas 2-6: R$ 97,56 (com refund)

  ERRADO: Refund foi antes da parcela 1!
```

### Depois (✅ Correto)

```
Pedido rPLMibwNTXTouHjeU5gXmphIE:
  Parcela 1: R$ 121,95 (com refund)
  Parcelas 2-6: R$ 121,95 (com refund)

  CORRETO: Todas têm refund distribuído
```

## Casos Tratados

✓ **Refund antes de qualquer payment** → Distribui em todas
✓ **Refund depois de alguns pagamentos** → Distribui apenas nas não recebidas
✓ **Sem pagamento antes do refund** → Distribui em todas (padrão)
✓ **Múltiplos refunds** → Usa data do primeiro
✓ **Chargebacks** → Mesma lógica que refund

## Testes Validados

- [x] Refund antes de 1º payment
- [x] Refund depois de alguns payments
- [x] Sem pagamento antes
- [x] Múltiplos ajustes
- [x] Cancelamento automático

## Campos Adicionados

```python
order_balances[ref] = {
    ...
    'refund_date': str or None,  # Data de aprovação do refund
    'chargeback_date': str or None,  # Data de aprovação do chargeback
    ...
}
```

## Commit

```
9e5a93f - Implementar analise de datas para refund (antes vs depois)
```

---

**Status:** ✅ IMPLEMENTADO E VALIDADO
**Data:** 2025-11-06
**Versão:** MP_RECEBIVEIS V3.2 (Date-Based Refund Logic)
**Prioridade:** Alta (corrige distribuição incorreta de refunds)
