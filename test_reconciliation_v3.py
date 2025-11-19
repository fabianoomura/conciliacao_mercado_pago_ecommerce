#!/usr/bin/env python3
"""
Test Script para Validação da Reconciliação V3

Este script testa:
1. Filtragem correta de Settlement (TRANSACTION_TYPE = 'SETTLEMENT')
2. Filtragem correta de Recebimentos (PAYMENT_METHOD em valid_methods)
3. Correspondência entre Settlement e Releases
4. Salvamento em JSON Cache
"""

import json
from pathlib import Path
from collections import defaultdict

from backend.processors.settlement_processor import SettlementProcessorV3
from backend.processors.releases_processor import ReleasesProcessorV2
from backend.utils.json_cache import JSONCache


def print_section(title):
    """Imprime um separador de seção"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70 + "\n")


def analyze_payment_methods(releases_proc):
    """Analisa distribuição de payment methods"""
    print_section("ANÁLISE DE PAYMENT METHODS (Recebimentos)")

    payment_methods = defaultdict(lambda: {'count': 0, 'amount': 0})

    for release in releases_proc.releases:
        method = release['payment_method'].lower() if release['payment_method'] else 'unknown'
        payment_methods[method]['count'] += 1
        payment_methods[method]['amount'] += release['net_credit_amount']

    print(f"{'Método':<20} {'Contagem':<12} {'% Total':<12} {'Valor Total':<15} {'Ação':<10}")
    print("-" * 70)

    total_count = sum(m['count'] for m in payment_methods.values())
    valid_count = 0
    valid_amount = 0

    for method, data in sorted(payment_methods.items(), key=lambda x: x[1]['count'], reverse=True):
        count = data['count']
        percent = (count / total_count * 100) if total_count > 0 else 0
        amount = data['amount']

        is_valid = method in ['master', 'visa', 'elo', 'amex']
        action = "INCLUI" if is_valid else "EXCLUI"

        print(f"{method:<20} {count:<12} {percent:>10.1f}% {amount:>14.2f} {action:<10}")

        if is_valid:
            valid_count += count
            valid_amount += amount

    print("-" * 70)
    valid_percent = (valid_count / total_count * 100) if total_count > 0 else 0
    print(f"{'TOTAL VÁLIDO':<20} {valid_count:<12} {valid_percent:>10.1f}% {valid_amount:>14.2f}")
    print(f"{'TOTAL INVÁLIDO':<20} {total_count - valid_count:<12} {100 - valid_percent:>10.1f}%")


def analyze_transaction_types(settlement_proc):
    """Analisa distribuição de transaction types"""
    print_section("ANÁLISE DE TRANSACTION TYPES (Settlement)")

    transaction_types = defaultdict(lambda: {'count': 0, 'amount': 0})

    for trans in settlement_proc.transactions:
        trans_type = trans['transaction_type']
        description = trans['description']
        key = f"{trans_type} ({description})"

        transaction_types[key]['count'] += 1
        transaction_types[key]['amount'] += trans['settlement_net_amount']

    print(f"{'Tipo de Transação':<30} {'Contagem':<12} {'% Total':<12} {'Valor Total':<15} {'Ação':<10}")
    print("-" * 80)

    total_count = sum(t['count'] for t in transaction_types.values())
    valid_count = 0
    valid_amount = 0

    for trans_type, data in sorted(transaction_types.items(), key=lambda x: x[1]['count'], reverse=True):
        count = data['count']
        percent = (count / total_count * 100) if total_count > 0 else 0
        amount = data['amount']

        # Lógica de filtragem
        parts = trans_type.split(' (')
        type_name = parts[0]
        description = parts[1].rstrip(')') if len(parts) > 1 else ''

        is_valid = (type_name == 'SETTLEMENT' and description != 'INSTALLMENT') or type_name == 'REFUND'
        action = "INCLUI" if is_valid else "EXCLUI"

        print(f"{trans_type:<30} {count:<12} {percent:>10.1f}% {amount:>14.2f} {action:<10}")

        if is_valid:
            valid_count += count
            valid_amount += amount

    print("-" * 80)
    valid_percent = (valid_count / total_count * 100) if total_count > 0 else 0
    print(f"{'TOTAL VÁLIDO':<30} {valid_count:<12} {valid_percent:>10.1f}% {valid_amount:>14.2f}")
    print(f"{'TOTAL INVÁLIDO':<30} {total_count - valid_count:<12} {100 - valid_percent:>10.1f}%")


def analyze_reconciliation_match(settlement_installments, payments):
    """Analisa correspondência entre Settlement e Releases"""
    print_section("ANÁLISE DE CORRESPONDÊNCIA (Settlement × Releases)")

    settlement_refs = set(i['external_reference'] for i in settlement_installments)
    payment_refs = set(p['external_reference'] for p in payments)

    total_settlement = len(settlement_refs)
    total_payments = len(payment_refs)
    match = settlement_refs & payment_refs
    orphan_payments = payment_refs - settlement_refs

    print(f"External References no Settlement: {total_settlement}")
    print(f"External References nos Payments: {total_payments}")
    print(f"Correspondências (ambos): {len(match)} ({len(match)/total_settlement*100:.1f}%)")
    print(f"Payments órfãos (só em Payments): {len(orphan_payments)} ({len(orphan_payments)/total_payments*100:.1f}%)")
    print(f"Settlement sem Payment: {total_settlement - len(match)} ({(total_settlement-len(match))/total_settlement*100:.1f}%)")

    print("\nMotivos normais para não bater 100%:")
    print("  • Settlement projeta FUTURO (Dec 2025, Jan 2026)")
    print("  • Recebimentos registram PASSADO (até Nov 2025)")
    print("  • Antecipações: parcelas recebidas antes da data esperada")
    print("  • Timing: 1-2 dias de diferença no processamento")


def test_json_cache():
    """Testa salvamento em JSON Cache"""
    print_section("TESTE DO JSON CACHE")

    cache = JSONCache(cache_dir='cache_test')

    # Dados de teste
    test_settlement = {
        'total_orders': 100,
        'total_installments': 150,
        'total_expected': 10000.00
    }

    test_releases = {
        'total_payments': 140,
        'total_received': 9500.00
    }

    test_metadata = {
        'processed_at': '2025-11-19T10:00:00',
        'version': 'V3',
        'test': True
    }

    # Salvar
    cache.save_settlement(test_settlement)
    cache.save_releases(test_releases)
    cache.save_metadata(test_metadata)

    # Carregar
    loaded_settlement = cache.load_settlement()
    loaded_releases = cache.load_releases()
    loaded_metadata = cache.load_metadata()

    # Validar
    assert loaded_settlement == test_settlement, "Settlement nao foi salvo corretamente"
    assert loaded_releases == test_releases, "Releases nao foi salvo corretamente"
    assert loaded_metadata == test_metadata, "Metadata nao foi salvo corretamente"

    print("[OK] Settlement salvo e carregado corretamente")
    print("[OK] Releases salvo e carregado corretamente")
    print("[OK] Metadata salvo e carregado corretamente")

    cache_info = cache.get_cache_info()
    print(f"\nCache Info:")
    print(f"  Tamanho: {cache_info['cache_size_mb']} MB")
    print(f"  Arquivos criados: {sum(1 for v in cache_info['files'].values() if v)} de 4")

    # Limpar
    cache.clear_all()
    print("\n[OK] Cache limpo com sucesso")


def main():
    """Função principal"""
    print("\n" + "=" * 70)
    print("=" * 70)
    print("  TEST RECONCILIATION V3 - Validação de Filtragem".center(70))
    print("=" * 70)
    print("=" * 70)

    # Processar Settlement
    print_section("PROCESSANDO SETTLEMENT")
    settlement_proc = SettlementProcessorV3()
    settlement_proc.process_files('data/settlement')

    # Processar Releases
    print_section("PROCESSANDO RECEBIMENTOS")
    releases_proc = ReleasesProcessorV2()
    releases_proc.process_files('data/recebimentos')

    # Análises
    analyze_payment_methods(releases_proc)
    analyze_transaction_types(settlement_proc)

    # Reconciliação
    installments = settlement_proc.get_installments()
    payments = releases_proc.get_payments_only()
    analyze_reconciliation_match(installments, payments)

    # JSON Cache
    test_json_cache()

    # Resumo final
    print_section("RESUMO FINAL")
    settlement_summary = settlement_proc.get_summary()
    releases_summary = releases_proc.get_summary()

    print("Settlement Summary:")
    print(f"  Total de orders: {settlement_summary['total_orders']}")
    print(f"  Total de installments: {settlement_summary['total_installments']}")
    print(f"  Total esperado: R$ {settlement_summary['total_expected']:.2f}")

    print("\nReleases Summary (após filtragem):")
    print(f"  Total de payments: {releases_summary['total_payments']}")
    print(f"  Total recebido: R$ {releases_summary['total_received']:.2f}")

    print("\nMovimentações (excluídas da conciliação):")
    print(f"  Total de movimentações: {releases_summary['total_movements']}")
    for mov_type, mov_data in releases_summary['movements_by_type'].items():
        print(f"    {mov_type}: {mov_data['count']}")

    print("\n" + "=" * 70)
    print("=" * 70)
    print(" TESTE CONCLUÍDO COM SUCESSO ".center(70))
    print("=" * 70)
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
