# Checklist de Validação - Fluxo de Cartão com Refund

Use este checklist para validar que todas as correções foram implementadas corretamente.

---

## ✅ Correção 1: Saldo Progressivo

### Testes Unitários

- [ ] **Test 1.1:** Cartão 6x com refund parcial (1ª parcela recebida)
  ```
  Setup: 6x de R$ 170,64 = R$ 1.023,84
         Refund: R$ 27,37
         Recebida: Parcela 1 (R$ 170,64)

  Esperado:
    - Parcela 1: R$ 170,64 (sem alteração)
    - Parcelas 2-6: R$ 165,17 cada (refund de R$ 5,47)
    - Total: 170,64 + (5 × 165,17) + 27,37 = 1.023,84 ✓

  Validar:
    [ ] Valor de parcela 1 não foi alterado
    [ ] Parcelas 2-6 têm refund de R$ 5,47
    [ ] Saldo total fecha
  ```

- [ ] **Test 1.2:** Cartão 3x com refund total (nenhuma recebida)
  ```
  Setup: 3x de R$ 158,91 = R$ 476,73
         Refund: R$ 476,75 (TOTAL)
         Recebida: Nenhuma

  Esperado:
    - Parcelas 1-3: R$ 0,00 (refund total)
    - Status: cancelled
    - Observação: "🚫 Cancelada (Refund Total)"

  Validar:
    [ ] Todas as parcelas têm valor = 0
    [ ] Todas marcadas como cancelled
    [ ] Observação correta
  ```

- [ ] **Test 1.3:** Cartão 2x com refund maior que valor individual
  ```
  Setup: 2x de R$ 100,00 = R$ 200,00
         Refund: R$ 150,00
         Recebida: Nenhuma

  Esperado:
    - Parcela 1: R$ 100 - 75 = R$ 25,00
    - Parcela 2: R$ 100 - 75 = R$ 25,00
    - Total: 50 + 150 (refund) = 200 ✓

  Validar:
    [ ] Refund dividido proporcionalmente
    [ ] Nenhuma parcela fica negativa
    [ ] Valores finais corretos
  ```

---

## ✅ Correção 2: Detecção de Canceladas

### Testes Unitários

- [ ] **Test 2.1:** Refund Total
  ```
  Setup: Parcela de R$ 158,91 com refund de R$ 158,91

  Esperado:
    - Valor final: R$ 0,00
    - is_cancelled: True
    - status: 'cancelled'
    - cancelled_reason: 'full_refund'

  Validar:
    [ ] is_cancelled está True
    [ ] status é 'cancelled'
    [ ] cancelled_reason é 'full_refund'
  ```

- [ ] **Test 2.2:** Chargeback Total
  ```
  Setup: Parcela de R$ 158,91 com chargeback de R$ 158,91

  Esperado:
    - Valor final: R$ 0,00
    - is_cancelled: True
    - cancelled_reason: 'chargeback'

  Validar:
    [ ] cancelled_reason é 'chargeback'
    [ ] Status correto
  ```

- [ ] **Test 2.3:** Refund + Chargeback (total)
  ```
  Setup: Parcela de R$ 158,91
         Refund: R$ 100,00
         Chargeback: R$ 58,91

  Esperado:
    - Valor final: R$ 0,00
    - cancelled_reason: 'partial_refund_full_cancellation'

  Validar:
    [ ] Soma de ajustes cancela parcela
    [ ] cancelled_reason correto
  ```

---

## ✅ Correção 3: Garantia de Status Cancelado

### Testes Integrados

- [ ] **Test 3.1:** Data Passada + Refund Total
  ```
  Setup: Parcela com data passada (02/03/2025)
         Refund total (cancela)
         Sem payment

  Fluxo:
    Passo 1: _mark_order_open
      ├─ Data < hoje
      ├─ Sem payment
      └─ Marca como 'overdue' ← AQUI

    Passo 2: _apply_progressive_balance_and_refunds
      └─ Marca como 'cancelled' ← AQUI

    Passo 3: _ensure_cancelled_status ← NOVO
      └─ FORÇA status = 'cancelled' ✓

    Resultado: Status é 'cancelled', não 'overdue'

  Esperado:
    - Status final: 'cancelled'
    - Observação: "🚫 Cancelada (Refund Total)"
    - NÃO deve aparecer em "Atrasadas"

  Validar:
    [ ] Status é 'cancelled'
    [ ] Não aparece em "Atrasadas"
    [ ] Frontend exibe emoji correto
  ```

- [ ] **Test 3.2:** Data Futura + Refund Total
  ```
  Setup: Parcela com data futura (02/12/2025)
         Refund total (cancela)

  Esperado:
    - Status: 'cancelled'
    - Não aparece em "Pendentes" nem "Atrasadas"

  Validar:
    [ ] Status correto
    [ ] Filtros excluem canceladas
  ```

---

## 🧪 Testes no Dashboard

### Visualização

- [ ] **Test D.1:** Resumo de Totais
  ```
  Validar:
    [ ] Total Esperado = Recebido + A Receber + Cancelado
    [ ] Total A Receber não inclui canceladas
    [ ] Total Atrasado não inclui canceladas
  ```

- [ ] **Test D.2:** Tabela de Parcelas
  ```
  Validar:
    [ ] Canceladas aparecem com status "Cancelado"
    [ ] Valor exibido é R$ 0,00
    [ ] Observação mostra motivo (Refund Total, etc)
    [ ] Não aparecem como "Atrasado"
  ```

- [ ] **Test D.3:** Abas de Filtro
  ```
  Validar:
    [ ] Aba "Pendentes" não inclui canceladas
    [ ] Aba "Atrasadas" não inclui canceladas
    [ ] Aba "Canceladas" existe e mostra todas
    [ ] Contadores (badges) estão corretos
  ```

---

## 📊 Testes com Dados Reais

### External Reference: repsglL8p6QjocK2YsvNxlJSj

- [ ] **Test R.1:** Validar Cancelamento Triplo
  ```
  Pedido: repsglL8p6QjocK2YsvNxlJSj
  Parcelas: 3x de R$ 158,91
  Refund: R$ 476,75 (total)

  Esperado:
    Parcela 1/3: R$ 0,00 - 🚫 Cancelada (Refund Total)
    Parcela 2/3: R$ 0,00 - 🚫 Cancelada (Refund Total)
    Parcela 3/3: R$ 0,00 - 🚫 Cancelada (Refund Total)

  Validar:
    [ ] Todas com status "Cancelado"
    [ ] Todas com valor R$ 0,00
    [ ] Observação mostra "Refund Total"
    [ ] Não aparecem em "Atrasadas"
  ```

### External Reference: rZMGU7lD2zcFAKoADJFZjTcZn

- [ ] **Test R.2:** Validar Cancelamento com Data Passada
  ```
  Pedido: rZMGU7lD2zcFAKoADJFZjTcZn
  Parcelas: 2x (data passada)
  Refund: total

  Validar:
    [ ] Ambas mostram status "Cancelado"
    [ ] NÃO aparecem em "Atrasadas"
    [ ] Frontend exibe corretamente
  ```

---

## 🔍 Testes de Regressão

### Pedidos Normais (sem refund)

- [ ] **Test N.1:** Cartão sem refund
  ```
  Setup: Cartão 3x sem refund

  Validar:
    [ ] Parcelas mantêm valor original
    [ ] Status correto (received/pending/overdue)
    [ ] Sem "Cancelado" falso
  ```

- [ ] **Test N.2:** PIX sem refund
  ```
  Setup: PIX única parcela sem refund

  Validar:
    [ ] Funciona normalmente
    [ ] Não afetado pelas mudanças
  ```

- [ ] **Test N.3:** Boleto sem refund
  ```
  Setup: Boleto sem refund

  Validar:
    [ ] Funciona normalmente
  ```

---

## 📈 Testes de Performance

- [ ] **Test P.1:** Processar 1000+ parcelas
  ```
  Validar:
    [ ] Sem erro
    [ ] Tempo de processamento razoável (< 5s)
    [ ] Memória sob controle
  ```

- [ ] **Test P.2:** Múltiplos refunds no mesmo pedido
  ```
  Setup: Pedido com múltiplos ajustes

  Validar:
    [ ] Processa corretamente
    [ ] Sem duplicação de refunds
  ```

---

## ✅ Checklist Final

### Código

- [ ] Syntax OK: `python -m py_compile backend/processors/reconciliator.py`
- [ ] Syntax OK: `python -m py_compile backend/processors/settlement_processor.py`
- [ ] Syntax OK: `python -m py_compile frontend/static/js/app.js`
- [ ] Imports OK: Sem módulos faltando
- [ ] Git Status: Tudo commitado

### Documentação

- [ ] CREDIT_CARD_FLOW_IMPLEMENTATION.md ✓
- [ ] IMPLEMENTATION_SUMMARY_V3.1.md ✓
- [ ] CREDIT_CARD_FLOW_DIAGRAM.txt ✓
- [ ] REFUND_TOTAL_FIX.md ✓
- [ ] CANCELLED_STATUS_FIX.md ✓
- [ ] FINAL_ADJUSTMENTS_SUMMARY.md ✓

### Commits

- [ ] 240a2cc - Saldo progressivo
- [ ] b090f1c - Documentação saldo progressivo
- [ ] 067ce18 - Resumo visual
- [ ] 64e0df8 - Diagrama ASCII
- [ ] 3d9256c - Detecção de canceladas
- [ ] 41cf410 - Documentação detecção
- [ ] 3813d31 - Garantia de status
- [ ] fa7433f - Documentação status
- [ ] d42908b - Sumário final

### Pronto para Produção

- [ ] Todas as correções implementadas ✓
- [ ] Documentação completa ✓
- [ ] Testes passando ✓
- [ ] Git clean ✓
- [ ] **Status: 🚀 PRONTO PARA PRODUÇÃO**

---

**Data de Validação:** _______________
**Responsável:** _______________
**Aprovação:** _______________
