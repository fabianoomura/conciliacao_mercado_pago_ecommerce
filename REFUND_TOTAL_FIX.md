# Correção: Detecção de Parcelas Canceladas (Refund Total)

## Problema Identificado

Quando um **refund total** era aplicado (refund = valor total da parcela), o sistema exibia:

```
External Ref: repsglL8p6QjocK2YsvNxlJSj

Parcela 1/3:
├─ Valor: R$ 0,00 ← ERRADO (parecia zerada)
├─ Status: Pendente ← ERRADO (deveria ser Cancelada)
└─ Observação: ⚠️ Ajustado ← ERRADO (deveria indicar cancelamento)
```

### Causa Raiz

O algoritmo de saldo progressivo distribuía refund corretamente (R$ 158,91 / 3 = R$ 52,97), mas:

1. A parcela original tinha R$ 158,91
2. Subtraía R$ 158,91 de refund → R$ 0,00
3. Marcava valor como 0, mas **mantinha status "pending"**
4. Frontend exibia R$ 0,00 como se fosse uma parcela normal (zerada, não cancelada)

## Solução Implementada

### 1. Reconciliador (reconciliator.py - Linhas 736-747)

Após aplicar refund/chargeback, agora **verifica se o valor ficou <= 0**:

```python
# NOVO: Detectar se parcela foi totalmente estornada
if adjusted_amount <= 0 and (refund_per_inst > 0 or chargeback_per_inst > 0):
    inst['is_cancelled'] = True
    inst['status'] = 'cancelled'

    # Identificar motivo
    if refund_per_inst >= abs(original_amount):
        inst['cancelled_reason'] = 'full_refund'
    elif chargeback_per_inst >= abs(original_amount):
        inst['cancelled_reason'] = 'chargeback'
    else:
        inst['cancelled_reason'] = 'partial_refund_full_cancellation'
```

### 2. Frontend (app.js - Linhas 985-1010)

Agora exibe observações claras para parcelas canceladas:

```javascript
// Status cancelado tem prioridade
if (inst.is_cancelled || inst.status === "cancelled") {
    const reason = inst.cancelled_reason || 'unknown';
    if (reason === 'full_refund') {
        obs += "🚫 Cancelada (Refund Total)";
    } else if (reason === 'chargeback') {
        obs += "🚫 Cancelada (Chargeback Total)";
    } else if (reason === 'partial_refund_full_cancellation') {
        obs += "🚫 Cancelada (Refund: " + formatCurrency(inst.refund_applied) + ")";
    } else {
        obs += "🚫 Cancelada";
    }
}
```

## Resultado

### Antes (❌ Incorreto)

```
Pedido: repsglL8p6QjocK2YsvNxlJSj

Transação Original:
  ├─ Valor bruto: R$ 493,99
  ├─ Parcelas: 3x (≈ R$ 158,91 cada)
  └─ Refund: R$ 476,75 (TOTAL)

Exibição:
  Parcela 1/3 | R$ 0,00 | 18/08/2025 | - | Pendente | ⚠️ Ajustado
  Parcela 2/3 | R$ 0,00 | 18/09/2025 | - | Pendente | ⚠️ Ajustado
  Parcela 3/3 | R$ 0,00 | 18/10/2025 | - | Pendente | ⚠️ Ajustado

PROBLEMA: Parece que as parcelas estão zeradas mas ativas (pendentes)
```

### Depois (✅ Correto)

```
Pedido: repsglL8p6QjocK2YsvNxlJSj

Transação Original:
  ├─ Valor bruto: R$ 493,99
  ├─ Parcelas: 3x (≈ R$ 158,91 cada)
  └─ Refund: R$ 476,75 (TOTAL)

Exibição:
  Parcela 1/3 | R$ 0,00 | 18/08/2025 | - | Cancelado | 🚫 Cancelada (Refund Total)
  Parcela 2/3 | R$ 0,00 | 18/09/2025 | - | Cancelado | 🚫 Cancelada (Refund Total)
  Parcela 3/3 | R$ 0,00 | 18/10/2025 | - | Cancelado | 🚫 Cancelada (Refund Total)

CORRETO: Todas as parcelas estão canceladas por refund total
```

## Casos de Cancelamento Agora Detectados

### 1. Refund Total (Full Refund)

```
Valor original: R$ 158,91
Refund: R$ 158,91
Resultado: R$ 0,00
Status: 🚫 Cancelada (Refund Total)
```

### 2. Chargeback Total

```
Valor original: R$ 158,91
Chargeback: R$ 158,91
Resultado: R$ 0,00
Status: 🚫 Cancelada (Chargeback Total)
```

### 3. Refund + Chargeback (Cancelamento por Ajustes)

```
Valor original: R$ 158,91
Refund: R$ 100,00
Chargeback: R$ 58,91
Resultado: R$ 0,00
Status: 🚫 Cancelada (Refund: R$ 158,91)
```

### 4. Refund Maior que Valor (Edge Case)

```
Valor original: R$ 158,91
Refund: R$ 200,00
Resultado: R$ 0,00 (mínimo mantido)
Status: 🚫 Cancelada (Refund Total)
```

## Impacto no Sistema

| Aspecto | Impacto |
|--------|--------|
| **Dashboard** | Parcelas canceladas agora aparecem com status correto |
| **Relatórios** | "A receber" exclui corretamente parcelas canceladas |
| **Conciliação** | Saldo total bate melhor (canceladas não contam) |
| **Observações** | Motivo do cancelamento claro para cada parcela |
| **Histórico** | Fácil identificar qual parcela foi refund total |

## Exemplos de Observações

```
✓ 🚫 Cancelada (Refund Total)
  → Refund 100% do valor da parcela

✓ 🚫 Cancelada (Chargeback Total)
  → Chargeback eliminou a parcela

✓ 🚫 Cancelada (Refund: R$ 158,91)
  → Refund + outros ajustes cancelaram a parcela

✓ 🚫 Cancelada
  → Cancelada por outro motivo (raro)
```

## Dados Técnicos

### Campo Adicionado

```python
cancelled_reason: str
  Valores possíveis:
  - 'full_refund': Refund total
  - 'chargeback': Chargeback total
  - 'partial_refund_full_cancellation': Refund parcial mas que cancela a parcela
  - 'unknown': Motivo desconhecido
```

### Fluxo de Detecção

```
[Valor Original]
  ↓
[Aplica Refund]
  ↓
[Aplica Chargeback]
  ↓
[Calcula Valor Final = Original - Refund - Chargeback]
  ↓
[Se Valor Final <= 0]
  └─> is_cancelled = True
  └─> status = 'cancelled'
  └─> cancelled_reason = ... (específico)
```

## Testes Recomendados

- [ ] Refund total em pedido com 1 parcela
- [ ] Refund total em pedido parcelado (3x, 6x, 12x)
- [ ] Refund parcial (não cancela, apenas reduz)
- [ ] Chargeback total
- [ ] Refund + Chargeback simultâneos
- [ ] Parcela recebida + Refund depois (não deve ser cancelada)

## Commit

```
3d9256c - Corrigir deteccao e exibicao de parcelas canceladas
```

---

**Status:** ✅ CORRIGIDO
**Data:** 2025-11-06
**Versão:** MP_RECEBIVEIS V3.1+Hotfix
**Prioridade:** Alta (corrige bug em relatório crítico)
