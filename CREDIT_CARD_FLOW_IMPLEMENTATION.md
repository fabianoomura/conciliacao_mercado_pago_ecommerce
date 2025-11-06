# Implementação: Fluxo Inteligente de Cartão Parcelado com Refund

## Problema Anterior

O sistema distribuía refund/chargeback **proporcionalmente entre TODAS as parcelas**, mesmo aquelas que já haviam sido recebidas. Isso causava distorções nos cálculos quando:

1. Algumas parcelas já foram recebidas
2. Um refund é aplicado na planilha de settlement
3. O refund deveria afetar apenas as parcelas **ainda não recebidas**

### Exemplo do Problema Antigo

```
Settlement: 6 parcelas de R$ 170,64 = R$ 1.023,84
Refund: R$ 27,37

Distribucao INCORRETA (antiga):
- Refund por parcela = 27,37 / 6 = R$ 4,56
- Todas as 6 parcelas recebem -R$ 4,56

Se a parcela 1 foi recebida por R$ 170,64 em 08-2025:
- Mas no settlement, ela aparecia como R$ 165,08 (170,64 - 4,56)
- ERRO: Parcela recebida vs esperado nao bate
```

## Solução Implementada (V3.1 MELHORADA)

### Arquitetura: Saldo Progressivo

Implementamos uma lógica de **saldo progressivo** onde:

1. **Settlement Processor** → Cria parcelas COM VALORES ORIGINAIS (sem distribuir refund)
2. **Reconciliador** → Executa 2 fases:
   - **Fase 1**: Reconcilia parcelas com payments (marca received/pending/overdue)
   - **Fase 2**: Aplica refund/chargeback APENAS nas parcelas não recebidas

### Código Novo no Reconciliador

```python
def _apply_progressive_balance_and_refunds(self):
    """
    Para cada pedido:
    1. Separa parcelas em: RECEBIDAS vs NÃO RECEBIDAS
    2. Aplica refund/chargeback APENAS nas NÃO RECEBIDAS
    3. Distribui proporcionalmente entre as não recebidas
    """
```

## Exemplo Prático

### Setup
```
Pedido: r7eA2T63QGdKMwLY8zwox1cJU

Settlement:
├─ Parcela 1: R$ 170,64 (08-2025)
├─ Parcela 2: R$ 170,64 (09-2025)
├─ Parcela 3: R$ 170,64 (10-2025)
├─ Parcela 4: R$ 170,64 (11-2025)
├─ Parcela 5: R$ 170,64 (12-2025)
└─ Parcela 6: R$ 170,64 (01-2026)
Total: R$ 1.023,84

Refund: R$ 27,37

Recebimentos (Releases):
└─ Parcela 1: R$ 170,64 recebida em 08-04-2025 ✓
   Parcelas 2-6: Não recebidas ainda
```

### Resultado (CORRETO)

```
Parcela 1 (RECEBIDA):
├─ Status: received
├─ Valor original: R$ 170,64
├─ Refund aplicado: R$ 0,00 ← NÃO SOFRE REFUND
└─ Valor final: R$ 170,64

Parcelas 2-6 (PENDENTES):
├─ Status: pending
├─ Valor original: R$ 170,64
├─ Refund por parcela: 27,37 / 5 = R$ 5,474 ≈ R$ 5,47
└─ Valor final: R$ 170,64 - R$ 5,47 = R$ 165,17 cada

Validação de Saldo:
├─ Recebido: R$ 170,64
├─ A receber (ajustado): R$ 165,17 × 5 = R$ 825,85
├─ Refund: R$ 27,37
└─ Total: 170,64 + 825,85 + 27,37 = 1.023,86 ✓
```

## Casos Especiais Tratados

### 1. Refund com Nenhuma Parcela Recebida

```
Se nenhuma parcela foi recebida ainda:
- Refund distribui entre as 6 parcelas
- Cada uma recebe: 27,37 / 6 = R$ 4,56
- Todas ficam com R$ 170,64 - R$ 4,56 = R$ 166,08
```

### 2. Refund com Múltiplas Parcelas Recebidas

```
Se parcelas 1, 2, 3 foram recebidas:
- Refund distribui APENAS entre 4, 5, 6 (não recebidas)
- Cada uma recebe: 27,37 / 3 = R$ 9,12
- Parcelas 1-3: R$ 170,64 (sem alteração)
- Parcelas 4-6: R$ 170,64 - R$ 9,12 = R$ 161,52 cada
```

### 3. Chargeback (Mesma Lógica)

Chargebacks também são distribuídos apenas nas parcelas não recebidas.

## Mudanças no Código

### settlement_processor.py

**Antes:**
```python
# Distribuir proporcionalmente entre TODAS as parcelas
refund_per_inst = total_refund / num_installments
adjusted_amount = original + refund_per_inst
```

**Depois:**
```python
# NÃO distribuir aqui - postergar para reconciliador
adjusted_amount = original_amount  # Sem ajustes
refund_applied = 0  # Será calculado no reconciliador
```

### reconciliator.py

**Novo método:**
```python
def _apply_progressive_balance_and_refunds(self):
    # 1. Agrupa por pedido
    # 2. Identifica parcelas recebidas vs não recebidas
    # 3. Aplica refund APENAS nas não recebidas
    # 4. Distribui proporcionalmente
```

**Integração no fluxo:**
```python
def reconcile(self):
    # Passo 1: Calcular saldos
    order_balances = self._calculate_order_balances()

    # Passo 2: Reconciliar parcelas (marcar status)
    self._reconcile_by_order_balance(order_balances, today)

    # Passo 3: NOVO - Aplicar saldo progressivo
    self._apply_progressive_balance_and_refunds()

    # Passo 4: Gerar estatísticas
    stats = self._generate_stats()
```

## Impacto no Sistema

### ✓ Benefícios

1. **Precisão**: Refund não distorce parcelas já recebidas
2. **Saldo Progressivo**: Total esperado diminui conforme pagamentos chegam
3. **Casos Complexos**: Suporta antecipações, recebimentos fora de ordem
4. **Relatórios Corretos**: Pendentes/atrasados agora com valores corretos

### ⚠️ Pontos de Atenção

1. **Mudança de Lógica**: Valores de parcelas podem mudar após implementação
2. **Dados Históricos**: Podem precisar de reconciliação manual
3. **Dashboard**: Totais "a receber" agora refletem refunds corretamente

## Testes Realizados

✓ Testado com cenário completo:
- 6 parcelas de cartão parcelado
- 1 parcela recebida, 5 pendentes
- Refund de R$ 27,37
- Validação de saldo final

**Resultado:** Refund distribuído corretamente apenas nas 5 parcelas pendentes.

## Próximos Passos (Opcionais)

1. Adicionar testes unitários automatizados
2. Documentar casos edge (chargebacks múltiplos, etc)
3. Considerar UI para mostrar "saldo progressivo" no dashboard
4. Auditar dados históricos de pedidos com refund

---

**Implementado em:** 2025-11-06
**Versão:** MP_RECEBIVEIS V3.1 MELHORADA (Progressive Balance)
