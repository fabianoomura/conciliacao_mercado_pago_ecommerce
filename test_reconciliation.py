"""
Test script para validar as correções de reconciliação
Testa os 8 casos de estudo identificados
"""

import sys
sys.path.insert(0, 'backend')

import pandas as pd
from processors.settlement_processor_v3 import SettlementProcessorV3
from processors.releases_processor import ReleasesProcessorV2
from processors.reconciliator import ReconciliatorV3
from pathlib import Path

# 8 casos de estudo
CASE_STUDIES = {
    'rfAL3BtMX5VIS5AO7hLYfEFAH': 'Pagamento simples (Crédito ML)',
    'r7vupmouAXJ35MCHektHkManu': 'Pagamento simples (Crédito ML)',
    'rXDDR9d8sxEL6OrAhYO8BRnjt': 'Cartão crédito 6 parcelas',
    'rqcHGYJAjdaVmO0TFoOAhmvqX': 'Cartão crédito com INSTALLMENT lines',
    'ruLkBthqAs1b2PlqInWfFN0Hy': 'Estorno parcial antes de pagamentos',
    'rGVXXyarflOWxL9wLzHPi2ScV': 'Estorno complexo com reservas',
    'rRYe4YOykFg4DtpY3WPelodab': 'Chargeback com reversão',
    'rdkcKaTV02K1hxAHIUTVL80Cx': 'Estorno total (não aparece em recebimentos)',
}

def print_section(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def process_data():
    """Processa os dados de settlement e recebimentos"""
    print_section("PROCESSANDO DADOS")

    # Settlement
    print("\nProcessando Settlement...")
    settlement_proc = SettlementProcessorV3()
    settlement_data = settlement_proc.process_files('data/settlement')

    # Releases
    print("\nProcessando Releases...")
    releases_proc = ReleasesProcessorV2()
    releases_data = releases_proc.process_files('data/recebimentos')

    # Reconciliação
    print("\nProcessando Reconciliação...")
    settlement_installments = settlement_proc.get_installments()
    payments = releases_proc.get_payments_only()
    reconciliator = ReconciliatorV3(settlement_installments, payments, settlement_proc.order_balances)
    summary = reconciliator.reconcile()

    # Os installments são modificados no lugar pelo reconciliator
    installments = reconciliator.installments

    return settlement_proc, releases_proc, reconciliator, installments

def analyze_case_study(case_id, case_description, settlement_proc, releases_proc, reconciliator, installments):
    """Analisa um caso específico"""

    print_section(f"CASO: {case_id}")
    print(f"Tipo: {case_description}")

    # Encontrar settlement para este caso
    settlement_data = [t for t in settlement_proc.transactions if t['external_reference'] == case_id]

    if not settlement_data:
        print(f"[ERRO] Nenhum settlement encontrado para {case_id}")
        return None

    print(f"\nDados do Settlement ({len(settlement_data)} linhas):")
    for i, trans in enumerate(settlement_data):
        print(f"\n  Linha {i+1}:")
        print(f"    TRANSACTION_TYPE: {trans['transaction_type']}")
        print(f"    DESCRIPTION: {trans['description']}")
        print(f"    PAYMENT_METHOD: {trans['payment_method']}")
        print(f"    TRANSACTION_AMOUNT: R$ {trans['transaction_amount']:.2f}")
        print(f"    FEE_AMOUNT: R$ {trans['fee_amount']:.2f}")
        print(f"    SETTLEMENT_NET_AMOUNT: R$ {trans['settlement_net_amount']:.2f}")
        print(f"    INSTALLMENTS: {trans['installments']}")
        print(f"    INSTALLMENT_NUMBER: {trans['installment_number']}")
        print(f"    INSTALLMENT_NET_AMOUNT: R$ {trans['installment_net_amount']:.2f}")

    # Encontrar parcelas para este caso
    case_installments = [inst for inst in installments if inst['external_reference'] == case_id]

    print(f"\nParcelas Geradas ({len(case_installments)} parcelas):")
    for inst in case_installments:
        print(f"\n  Parcela {inst['installment_number']}:")
        print(f"    Status: {inst['status']}")
        print(f"    Valor Original: R$ {inst['installment_net_amount_original']:.2f}")
        print(f"    Valor Ajustado: R$ {inst['installment_net_amount']:.2f}")
        print(f"    Data Esperada: {inst['money_release_date']}")
        if inst.get('received_date'):
            print(f"    Data Recebida: {inst['received_date']}")
        if inst.get('refund_applied') > 0:
            print(f"    Estorno Aplicado: R$ {inst['refund_applied']:.2f}")
        if inst.get('chargeback_applied') > 0:
            print(f"    Chargeback: R$ {inst['chargeback_applied']:.2f}")

    # Encontrar payments para este caso
    payments = [p for p in releases_proc.payments_only if p['external_reference'] == case_id]

    print(f"\nPayments Recebidos ({len(payments)} payments):")
    for i, payment in enumerate(payments):
        print(f"\n  Payment {i+1}:")
        print(f"    Parcela: {payment.get('installments', 'N/A')}")
        print(f"    Valor: R$ {payment['net_credit_amount']:.2f}")
        print(f"    Data: {payment['release_date']}")

    # Resumo de matching
    print(f"\nResumo de Matching:")
    total_parcelas = len(case_installments)
    matched = sum(1 for inst in case_installments if inst['status'] in ['received', 'received_advance'])
    pending = sum(1 for inst in case_installments if inst['status'] == 'pending')
    overdue = sum(1 for inst in case_installments if inst['status'] == 'overdue')
    cancelled = sum(1 for inst in case_installments if inst['status'] == 'cancelled')

    print(f"  Total Parcelas: {total_parcelas}")
    print(f"  Recebidas: {matched}")
    print(f"  Pendentes: {pending}")
    print(f"  Atrasadas: {overdue}")
    print(f"  Canceladas: {cancelled}")

    total_value_expected = sum(inst['installment_net_amount'] for inst in case_installments)
    total_value_received = sum(inst['received_amount'] for inst in case_installments if inst.get('received_amount', 0) > 0)

    print(f"\n  Valor Esperado (Total): R$ {total_value_expected:.2f}")
    print(f"  Valor Recebido: R$ {total_value_received:.2f}")

    if total_parcelas > 0 and overdue == 0:
        print(f"\n  [PASS] Nenhuma parcela marcada como atrasada")
    elif overdue > 0:
        print(f"\n  [FAIL] {overdue} parcela(s) marcada(s) como atrasada")

    return {
        'case_id': case_id,
        'total_parcelas': total_parcelas,
        'matched': matched,
        'pending': pending,
        'overdue': overdue,
        'cancelled': cancelled,
        'total_value_expected': total_value_expected,
        'total_value_received': total_value_received,
    }

def main():
    """Executa os testes"""
    print("\n" + "=" * 80)
    print(" TESTE DE RECONCILIAÇÃO - SISTEMA MERCADO PAGO V3.0")
    print("=" * 80)

    # Processar dados
    settlement_proc, releases_proc, reconciliator, installments = process_data()

    # Analisar cada caso de estudo
    results = []
    for case_id, case_description in CASE_STUDIES.items():
        result = analyze_case_study(
            case_id,
            case_description,
            settlement_proc,
            releases_proc,
            reconciliator,
            installments
        )
        if result:
            results.append(result)

    # Relatório final
    print_section("RELATÓRIO FINAL")

    print("\nResultados dos 8 Casos de Estudo:")
    print("\n{:<30} {:<10} {:<10} {:<10} {:<10}".format(
        "Caso", "Total", "Recebidas", "Atrasadas", "Canceladas"
    ))
    print("-" * 70)

    total_overdue = 0
    for result in results:
        case_short = result['case_id'][:20]
        print("{:<30} {:<10} {:<10} {:<10} {:<10}".format(
            case_short,
            result['total_parcelas'],
            result['matched'],
            result['overdue'],
            result['cancelled']
        ))
        total_overdue += result['overdue']

    print("-" * 70)
    print(f"\nTotal de Parcelas Atrasadas (PROBLEMA): {total_overdue}")

    if total_overdue == 0:
        print("\n[SUCCESS] Nenhuma parcela incorretamente marcada como atrasada!")
    else:
        print(f"\n[FAILURE] Ainda há {total_overdue} parcela(s) incorretamente marcada(s) como atrasada")

    print("\n" + "=" * 80 + "\n")

if __name__ == '__main__':
    main()
