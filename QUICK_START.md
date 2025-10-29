# Quick Start - Sistema Mercado Pago V3.0

## Uso Rápido

### 1. Processar Dados

```python
from backend.processors.settlement_processor_v3 import SettlementProcessorV3
from backend.processors.releases_processor import ReleasesProcessorV2
from backend.processors.reconciliator import ReconciliatorV3

# Settlement
settlement = SettlementProcessorV3()
settlement.process_files('data/settlement')

# Releases
releases = ReleasesProcessorV2()
releases.process_files('data/recebimentos')

# Reconciliador
reconciliator = ReconciliatorV3(
    settlement.get_installments(),
    releases.get_payments_only(),
    settlement.order_balances
)
reconciliator.reconcile()

# Resultados
installments = reconciliator.installments
```

### 2. Verificar Parcelas

```python
# Todas as parcelas
for inst in installments[:5]:
    print(f"{inst['external_reference']} - {inst['status']}")

# Por status
received = [i for i in installments if i['status'] == 'received']
advance = [i for i in installments if i['status'] == 'received_advance']
pending = [i for i in installments if i['status'] == 'pending']
overdue = [i for i in installments if i['status'] == 'overdue']
cancelled = [i for i in installments if i['status'] == 'cancelled']

print(f"Recebidas: {len(received)}")
print(f"Antecipadas: {len(advance)} (R$ {sum(i['received_amount'] for i in advance):,.2f})")
print(f"Pendentes: {len(pending)}")
print(f"Atrasadas: {len(overdue)}")
print(f"Canceladas: {len(cancelled)}")
```

### 3. Analisar um Caso Específico

```python
case_id = 'rfAL3BtMX5VIS5AO7hLYfEFAH'

# Encontrar todas as parcelas do caso
case_insts = [i for i in installments if i['external_reference'] == case_id]

# Exibir detalhes
for inst in case_insts:
    print(f"\nParcela {inst['installment_number']}:")
    print(f"  Status: {inst['status']}")
    print(f"  Valor: R$ {inst['installment_net_amount']:.2f}")
    print(f"  Data Esperada: {inst['money_release_date']}")

    if inst['status'] in ['received', 'received_advance']:
        print(f"  Recebido: {inst['received_date']}")
        if inst['status'] == 'received_advance':
            print(f"  Antecipado: {inst['days_advance']} dias")
```

---

## Interpretação de Status

| Status | Significado | Cor |
|--------|-------------|-----|
| `received` | Parcela recebida na data esperada | Verde |
| `received_advance` | Parcela recebida antes do esperado | Verde (com ⚡) |
| `pending` | Aguardando recebimento (ainda não venceu) | Amarelo |
| `overdue` | Parcela atrasada | Vermelho |
| `cancelled` | Estornada/Cancelada (não será recebida) | Cinza |

---

## Campos Importantes

```python
installment = {
    'external_reference': 'rfAL3BtMX5VIS5AO7hLYfEFAH',  # ID da venda
    'installment_number': '1/6',                          # Parcela 1 de 6
    'status': 'received',                                  # Status atual
    'payment_method': 'master',                            # Cartão
    'payment_type': 'cartao_parcelado',                    # Tipo de pagamento

    # Valores
    'installment_net_amount_original': 252.04,             # Sem ajustes
    'installment_net_amount': 252.04,                      # Com ajustes (estorno, etc)
    'received_amount': 252.04,                             # O que foi realmente recebido

    # Datas
    'money_release_date': '2025-03-15',                    # Quando deveria chegar
    'approval_date': '2025-02-15',                         # Quando foi aprovado
    'received_date': '2025-03-15',                         # Quando realmente chegou

    # Adiantamentos
    'days_advance': 0,                                     # Dias antes (se received_advance)

    # Ajustes
    'refund_applied': 0.0,                                 # Estorno distribuído
    'chargeback_applied': 0.0,                             # Chargeback distribuído
    'has_adjustment': False,                               # Se teve ajuste
}
```

---

## Filtros Úteis

### Parcelas Atrasadas
```python
overdue = [i for i in installments
           if i['status'] == 'overdue']
print(f"Total Atrasado: R$ {sum(i['installment_net_amount'] for i in overdue):,.2f}")
```

### Parcelas Antecipadas
```python
advance = [i for i in installments
           if i['status'] == 'received_advance']
avg_days = sum(i.get('days_advance', 0) for i in advance) / len(advance)
print(f"Média de Antecipação: {avg_days:.0f} dias")
```

### Parcelas com Estorno
```python
with_refund = [i for i in installments
               if i['refund_applied'] > 0]
print(f"Parcelas com Estorno: {len(with_refund)}")
```

### Parcelas de um Período
```python
from datetime import datetime
period = [i for i in installments
          if '2025-10' in (i.get('received_date') or '')]
print(f"Recebidas em outubro/2025: {len(period)}")
```

### Por Método de Pagamento
```python
by_method = {}
for i in installments:
    method = i['payment_type']
    if method not in by_method:
        by_method[method] = []
    by_method[method].append(i)

for method, insts in by_method.items():
    total = sum(i['installment_net_amount'] for i in insts)
    print(f"{method}: {len(insts)} parcelas, R$ {total:,.2f}")
```

---

## Rodar Testes

```bash
# Testes dos 8 casos de estudo
python test_reconciliation.py

# Apenas a reconciliação
python -c "from backend.processors.settlement_processor_v3 import SettlementProcessorV3; ..."
```

---

## Documentação Completa

- **TEST_RESULTS.md** - Resultados detalhados dos 8 casos
- **RECONCILIATION_ANALYSIS.md** - Análise técnica profunda
- **ADVANCE_PAYMENTS_ANALYSIS.md** - Análise de adiantamentos
- **IMPLEMENTATION_SUMMARY.md** - Resumo da implementação

---

## Dúvidas Comuns

### P: Por que uma parcela é "overdue" mas foi paga?
**R**: Provavelmente é um bug do V2 antigo. Verifique se foi corrigido para V3. A parcela deve estar como "received" se foi paga.

### P: Como sei se uma parcela foi antecipada?
**R**: Procure por `status == 'received_advance'`. O campo `days_advance` mostra quantos dias foi antecipada.

### P: Parcelas têm valores diferentes do settlement?
**R**: Isso pode ser:
- Estorno distribuído proporcionalmente
- Chargeback reduzindo o valor
- Variação pequena por arredondamento (até R$ 0,02)
- Taxa de antecipação aplicada

### P: Como filtrar um período específico?
**R**: Use a data em `received_date` ou `money_release_date`:
```python
period = [i for i in installments
          if i.get('received_date', '').startswith('2025-10')]
```

### P: Quantas parcelas realmente estão atrasadas?
**R**:
```python
overdue_real = [i for i in installments if i['status'] == 'overdue']
print(f"Total: {len(overdue_real)}")  # 22 no sistema atual
```

---

## Performance

```
Tempo de processamento típico:
- Settlement (10 arquivos): 5-10 segundos
- Releases (10 arquivos): 3-5 segundos
- Reconciliação: 2-3 segundos

Total: ~10-20 segundos para 7.489 parcelas
```

---

## Suporte

Ver documentos de análise:
- Casos específicos → TEST_RESULTS.md
- Arquitetura → RECONCILIATION_ANALYSIS.md
- Adiantamentos → ADVANCE_PAYMENTS_ANALYSIS.md

---

**Versão**: 3.0
**Última Atualização**: 29 de outubro de 2025
