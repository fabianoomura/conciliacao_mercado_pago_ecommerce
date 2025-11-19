"""
Exporter - Gera relatórios em TXT e JSON
Suporta exportação de todos os dados processados (Settlement, Releases, Reconciliação, Movimentações)
"""

import json
import os
from datetime import datetime
from pathlib import Path


class ReportExporter:
    """Exporta dados de reconciliação em múltiplos formatos (TXT, JSON)"""

    def __init__(self, output_dir='reports'):
        self.output_dir = output_dir
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """Cria diretório de saída se não existir"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def export_all(self, settlement_summary, releases_summary, reconciliation_summary,
                   movements_summary, cashflow_summary):
        """
        Exporta todos os dados em TXT e JSON
        Retorna: dict com caminhos dos arquivos gerados
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results = {}

        # Exportar em TXT
        txt_file = self._export_txt(
            settlement_summary, releases_summary, reconciliation_summary,
            movements_summary, cashflow_summary, timestamp
        )
        results['txt'] = txt_file

        # Exportar em JSON
        json_file = self._export_json(
            settlement_summary, releases_summary, reconciliation_summary,
            movements_summary, cashflow_summary, timestamp
        )
        results['json'] = json_file

        return results

    def _export_txt(self, settlement_summary, releases_summary, reconciliation_summary,
                    movements_summary, cashflow_summary, timestamp):
        """Exporta dados em formato TXT"""
        filepath = os.path.join(self.output_dir, f'relatorio_{timestamp}.txt')

        with open(filepath, 'w', encoding='utf-8') as f:
            # Cabeçalho
            f.write('='*80 + '\n')
            f.write('RELATORIO DE RECONCILIACAO - MERCADO PAGO\n')
            f.write('='*80 + '\n\n')
            f.write(f'Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}\n')
            f.write(f'Versao: V5 (SOURCE_ID Matching)\n')
            f.write('-'*80 + '\n\n')

            # Settlement
            f.write('1. SETTLEMENT\n')
            f.write('-'*80 + '\n')
            self._write_settlement_txt(f, settlement_summary)
            f.write('\n\n')

            # Releases/Recebimentos
            f.write('2. RECEBIMENTOS\n')
            f.write('-'*80 + '\n')
            self._write_releases_txt(f, releases_summary)
            f.write('\n\n')

            # Reconciliação
            f.write('3. RECONCILIACAO\n')
            f.write('-'*80 + '\n')
            self._write_reconciliation_txt(f, reconciliation_summary)
            f.write('\n\n')

            # Movimentações
            f.write('4. MOVIMENTACOES\n')
            f.write('-'*80 + '\n')
            self._write_movements_txt(f, movements_summary)
            f.write('\n\n')

            # Cashflow
            f.write('5. FLUXO DE CAIXA\n')
            f.write('-'*80 + '\n')
            self._write_cashflow_txt(f, cashflow_summary)
            f.write('\n\n')

            # Resumo Final
            f.write('6. RESUMO EXECUTIVO\n')
            f.write('-'*80 + '\n')
            self._write_executive_summary_txt(f, settlement_summary, releases_summary,
                                             reconciliation_summary, movements_summary)
            f.write('\n')
            f.write('='*80 + '\n')
            f.write('FIM DO RELATORIO\n')
            f.write('='*80 + '\n')

        print(f"[EXPORT] Arquivo TXT gerado: {filepath}")
        return filepath

    def _write_settlement_txt(self, f, settlement_summary):
        """Escreve seção Settlement em TXT"""
        f.write(f"  Total de registros: {settlement_summary.get('total_records', 0)}\n")
        f.write(f"  Valor total (Settlement Net): R$ {settlement_summary.get('total_settlement_net', 0):.2f}\n")
        f.write(f"  Valor bruto: R$ {settlement_summary.get('total_gross_amount', 0):.2f}\n")
        f.write(f"  Taxas cobradas: R$ {settlement_summary.get('total_fees', 0):.2f}\n")

        if 'payment_types' in settlement_summary and settlement_summary['payment_types']:
            f.write(f"\n  Tipos de pagamento:\n")
            for ptype, count in settlement_summary['payment_types'].items():
                f.write(f"    - {ptype}: {count}\n")

    def _write_releases_txt(self, f, releases_summary):
        """Escreve seção Releases em TXT"""
        f.write(f"  Total de registros: {releases_summary.get('total_records', 0)}\n")
        f.write(f"  Pagamentos: {releases_summary.get('payments', 0)}\n")
        f.write(f"  Refunds: {releases_summary.get('refunds', 0)}\n")
        f.write(f"  Chargebacks: {releases_summary.get('chargebacks', 0)}\n")
        f.write(f"  Movimentações: {releases_summary.get('movements', 0)}\n")
        f.write(f"  Valor total (net credit): R$ {releases_summary.get('total_net_credit', 0):.2f}\n")

    def _write_reconciliation_txt(self, f, reconciliation_summary):
        """Escreve seção Reconciliação em TXT"""
        total = reconciliation_summary.get('total', 0)
        matched = reconciliation_summary.get('matched', 0)
        refunded = reconciliation_summary.get('refunded', 0)
        chargeback_reversed = reconciliation_summary.get('chargeback_reversed', 0)
        chargeback_pending = reconciliation_summary.get('chargeback_pending', 0)
        pending = reconciliation_summary.get('pending', 0)
        mismatch = reconciliation_summary.get('mismatch', 0)
        orphan_settlement = reconciliation_summary.get('orphan_settlement', 0)
        orphan_releases = reconciliation_summary.get('orphan_releases', 0)

        f.write(f"  Total de transacoes: {total}\n")
        f.write(f"  Conciliadas (balanço zero): {matched} ({self._percentage(matched, total)}%)\n")
        f.write(f"  Refundidas: {refunded} ({self._percentage(refunded, total)}%)\n")
        f.write(f"  Chargeback Revertido: {chargeback_reversed} ({self._percentage(chargeback_reversed, total)}%)\n")
        f.write(f"  Chargeback Pendente: {chargeback_pending} ({self._percentage(chargeback_pending, total)}%)\n")
        f.write(f"  Pendentes (não liberadas): {pending} ({self._percentage(pending, total)}%)\n")
        f.write(f"  Mismatch (valores não batem): {mismatch} ({self._percentage(mismatch, total)}%)\n")
        f.write(f"  Orfãs Settlement (sem release): {orphan_settlement} ({self._percentage(orphan_settlement, total)}%)\n")
        f.write(f"  Orfãs Releases (sem settlement): {orphan_releases} ({self._percentage(orphan_releases, total)}%)\n")

        # Taxa de sucesso
        success_rate = self._percentage(matched + refunded + chargeback_reversed + chargeback_pending + pending, total)
        f.write(f"\n  Taxa de sucesso (sem mismatch/orphans): {success_rate}%\n")

    def _write_movements_txt(self, f, movements_summary):
        """Escreve seção Movimentações em TXT"""
        f.write(f"  Taxas cobradas: {movements_summary.get('fees_count', 0)}\n")
        f.write(f"  Valor total em taxas: R$ {movements_summary.get('total_fees', 0):.2f}\n")
        f.write(f"  Payouts: {movements_summary.get('payouts_count', 0)}\n")
        f.write(f"  Valor total em payouts: R$ {movements_summary.get('total_payouts', 0):.2f}\n")
        f.write(f"  Adiantamentos: {movements_summary.get('advances_count', 0)}\n")
        f.write(f"  Valor total em adiantamentos: R$ {movements_summary.get('total_advances', 0):.2f}\n")

    def _write_cashflow_txt(self, f, cashflow_summary):
        """Escreve seção Cashflow em TXT"""
        f.write(f"  Saldo total recebido: R$ {cashflow_summary.get('total_received', 0):.2f}\n")
        f.write(f"  Saldo a receber: R$ {cashflow_summary.get('pending_amount', 0):.2f}\n")
        f.write(f"  Saldo adiantado: R$ {cashflow_summary.get('advance_amount', 0):.2f}\n")

    def _write_executive_summary_txt(self, f, settlement_summary, releases_summary,
                                     reconciliation_summary, movements_summary):
        """Escreve resumo executivo em TXT"""
        total_recon = reconciliation_summary.get('total', 0)
        matched = reconciliation_summary.get('matched', 0)
        mismatch = reconciliation_summary.get('mismatch', 0)
        orphans = reconciliation_summary.get('orphan_settlement', 0) + reconciliation_summary.get('orphan_releases', 0)

        f.write(f"\n  Estatísticas Gerais:\n")
        f.write(f"    - Transações processadas: {total_recon}\n")
        f.write(f"    - Taxa de conciliação: {self._percentage(matched, total_recon)}%\n")
        f.write(f"    - Problemas encontrados: {mismatch + orphans}\n")
        f.write(f"      * Mismatches: {mismatch}\n")
        f.write(f"      * Órfãs: {orphans}\n")

        settlement_value = settlement_summary.get('total_settlement_net', 0)
        releases_value = releases_summary.get('total_net_credit', 0)
        difference = abs(settlement_value - releases_value)

        f.write(f"\n  Balanço Financeiro:\n")
        f.write(f"    - Settlement Total: R$ {settlement_value:.2f}\n")
        f.write(f"    - Releases Total: R$ {releases_value:.2f}\n")
        f.write(f"    - Diferença: R$ {difference:.2f}\n")

        if difference < 0.01:
            f.write(f"    - Status: BALANCEADO\n")
        else:
            f.write(f"    - Status: DESBALANCEADO (atenção!)\n")

    def _export_json(self, settlement_summary, releases_summary, reconciliation_summary,
                     movements_summary, cashflow_summary, timestamp):
        """Exporta dados em formato JSON"""
        filepath = os.path.join(self.output_dir, f'relatorio_{timestamp}.json')

        data = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'version': 'V5',
                'format': 'JSON'
            },
            'settlement': settlement_summary,
            'releases': releases_summary,
            'reconciliation': reconciliation_summary,
            'movements': movements_summary,
            'cashflow': cashflow_summary
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[EXPORT] Arquivo JSON gerado: {filepath}")
        return filepath

    def _percentage(self, value, total):
        """Calcula percentual"""
        if total == 0:
            return 0.0
        return round((value / total) * 100, 2)

    def get_recent_exports(self, limit=10):
        """Retorna lista dos arquivos exportados mais recentes"""
        if not os.path.exists(self.output_dir):
            return []

        files = []
        for filename in os.listdir(self.output_dir):
            filepath = os.path.join(self.output_dir, filename)
            if os.path.isfile(filepath):
                files.append({
                    'name': filename,
                    'path': filepath,
                    'size_kb': os.path.getsize(filepath) / 1024,
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
                })

        # Ordenar por data modificação, mais recentes primeiro
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files[:limit]
