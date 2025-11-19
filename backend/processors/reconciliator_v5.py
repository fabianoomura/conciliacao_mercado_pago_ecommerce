"""
Reconciliador V5 - Com SOURCE_ID e Suporte a 4 Payment Types
Implementa lógica completa de reconciliação de cartão de crédito
"""

from collections import defaultdict
from datetime import datetime


class ReconciliatorV5:
    """Reconcilia Settlement com Recebimentos usando SOURCE_ID"""

    def __init__(self):
        self.results = {
            'matched': [],
            'refunded': [],
            'chargeback_pending': [],
            'chargeback_reversed': [],
            'pending': [],
            'mismatch': [],
            'orphan_settlement': [],
            'orphan_releases': []
        }
        self.settlement_by_source = {}
        self.releases_by_source = {}

    def process(self, settlement_data, releases_data):
        """Processa dados de Settlement e Recebimentos"""
        print("\n[RECONCILIACAO V5] Iniciando reconciliação por SOURCE_ID...")

        # Organizar dados por SOURCE_ID
        self._organize_settlement(settlement_data)
        self._organize_releases(releases_data)

        # Reconciliar cada transação
        all_sources = set(self.settlement_by_source.keys()) | set(self.releases_by_source.keys())

        for source_id in all_sources:
            if source_id and source_id != 'nan':
                self._reconcile_source(source_id)

        # Resumo
        self._print_summary()
        return self.results

    def _organize_settlement(self, settlement_data):
        """Organiza dados de Settlement por SOURCE_ID"""
        print("  [1/3] Organizando Settlement por SOURCE_ID...")

        for item in settlement_data:
            source_id = str(item.get('source_id', '')).strip()
            if source_id and source_id != 'nan':
                if source_id not in self.settlement_by_source:
                    self.settlement_by_source[source_id] = {
                        'settlement': None,
                        'installments': [],
                        'refunds': [],
                        'chargebacks': [],
                        'chargeback_cancels': []
                    }

                trans_type = str(item.get('transaction_type', '')).strip().upper()
                description = str(item.get('description', '')).strip().lower()

                if trans_type == 'SETTLEMENT' and description != 'INSTALLMENT':
                    self.settlement_by_source[source_id]['settlement'] = item
                elif description == 'INSTALLMENT':
                    self.settlement_by_source[source_id]['installments'].append(item)
                elif trans_type == 'REFUND':
                    self.settlement_by_source[source_id]['refunds'].append(item)
                elif trans_type == 'CHARGEBACK':
                    self.settlement_by_source[source_id]['chargebacks'].append(item)
                elif trans_type == 'CHARGEBACK_CANCEL':
                    self.settlement_by_source[source_id]['chargeback_cancels'].append(item)

        print(f"     Encontrados {len(self.settlement_by_source)} SOURCE_IDs únicos no Settlement")

    def _organize_releases(self, releases_data):
        """Organiza dados de Recebimentos por SOURCE_ID"""
        print("  [2/3] Organizando Recebimentos por SOURCE_ID...")

        for item in releases_data:
            source_id = str(item.get('source_id', '')).strip()
            if source_id and source_id != 'nan':
                if source_id not in self.releases_by_source:
                    self.releases_by_source[source_id] = {
                        'payments': [],
                        'refunds': [],
                        'chargebacks': [],
                        'chargeback_cancels': [],
                        'movements': []
                    }

                description = str(item.get('description', '')).strip().lower()

                if description == 'payment':
                    self.releases_by_source[source_id]['payments'].append(item)
                elif description == 'refund':
                    self.releases_by_source[source_id]['refunds'].append(item)
                elif description == 'chargeback':
                    self.releases_by_source[source_id]['chargebacks'].append(item)
                elif description == 'chargeback_cancel':
                    self.releases_by_source[source_id]['chargeback_cancels'].append(item)
                else:
                    # reserve_for_refund, reserve_for_chargeback, etc
                    self.releases_by_source[source_id]['movements'].append(item)

        print(f"     Encontrados {len(self.releases_by_source)} SOURCE_IDs únicos em Recebimentos")

    def _reconcile_source(self, source_id):
        """Reconcilia um SOURCE_ID específico"""
        settlement_data = self.settlement_by_source.get(source_id)
        releases_data = self.releases_by_source.get(source_id)

        # Caso: Apenas Settlement
        if settlement_data and not releases_data:
            self.results['orphan_settlement'].append({
                'source_id': source_id,
                'settlement': settlement_data
            })
            return

        # Caso: Apenas Recebimentos
        if releases_data and not settlement_data:
            self.results['orphan_releases'].append({
                'source_id': source_id,
                'releases': releases_data
            })
            return

        # Caso: Ambos existem - fazer reconciliação completa
        result = self._match_settlement_releases(source_id, settlement_data, releases_data)
        status = result['status']

        self.results[status].append(result)

    def _match_settlement_releases(self, source_id, settlement_data, releases_data):
        """Faz match entre Settlement e Recebimentos"""
        settlement = settlement_data['settlement']
        installments = settlement_data['installments']
        refunds_settlement = settlement_data['refunds']
        chargebacks = settlement_data['chargebacks']
        chargeback_cancels = settlement_data['chargeback_cancels']

        payments = releases_data['payments']
        refunds_releases = releases_data['refunds']
        chargebacks_releases = releases_data['chargebacks']
        chargeback_cancels_releases = releases_data['chargeback_cancels']

        # Calcular balanços
        if settlement:
            settlement_net = float(settlement.get('settlement_net_amount', 0))
        else:
            settlement_net = 0

        # Somar refunds Settlement
        for refund in refunds_settlement:
            settlement_net += float(refund.get('settlement_net_amount', 0))

        # Somar chargebacks
        for chargeback in chargebacks:
            settlement_net += float(chargeback.get('settlement_net_amount', 0))

        # Somar chargeback_cancels
        for cancel in chargeback_cancels:
            settlement_net += float(cancel.get('settlement_net_amount', 0))

        # Calcular balanço de Recebimentos
        releases_net = 0.0

        for payment in payments:
            releases_net += float(payment.get('net_credit_amount', 0))

        for refund in refunds_releases:
            # Refund em Releases tem net_debit_amount (dinheiro saindo para o cliente)
            # Ao calcular o balanço, isso reduz o saldo recebido
            releases_net -= float(refund.get('net_debit_amount', 0))

        for chargeback in chargebacks_releases:
            # Chargeback em Releases tem net_debit_amount (dinheiro saindo)
            releases_net -= float(chargeback.get('net_debit_amount', 0))

        for cancel in chargeback_cancels_releases:
            # Chargeback Cancel em Releases tem net_credit_amount (dinheiro voltando)
            releases_net += float(cancel.get('net_credit_amount', 0))

        # Determinar status
        tolerance = 0.01  # tolerância para arredondamento
        settlement_net_rounded = round(settlement_net, 2)
        releases_net_rounded = round(releases_net, 2)

        # REGRA ESPECIAL: Se nao há payments em releases mas há refunds/chargebacks
        # Isso significa uma ordem cancelada antes de qualquer liberação
        # Nesse caso, o balanço de Settlement deve ser zero (payment - refund = 0)
        # e Releases mostra apenas os refunds/chargebacks que saíram
        if not payments and not chargebacks_releases and not chargeback_cancels_releases:
            # Sem payments e sem chargebacks em releases
            # So refunds - verificar se Settlement fechou em zero
            if settlement_net_rounded == 0.0 and (refunds_settlement or refunds_releases):
                # Ordem foi cancelada totalmente
                status = 'refunded'
            else:
                status = 'mismatch'
        elif abs(settlement_net_rounded - releases_net_rounded) < tolerance:
            # Valores batem - determinar status específico
            # Prioridade: chargebacks > refunds > pending > matched
            if chargeback_cancels_releases:
                # Tem reversão de chargeback
                status = 'chargeback_reversed'
            elif chargebacks_releases:
                # Tem chargeback sem reversão
                status = 'chargeback_pending'
            elif refunds_releases or refunds_settlement:
                # Tem refund(s)
                status = 'refunded'
            elif not payments and installments:
                # Tem parcelas não liberadas ainda
                status = 'pending'
            else:
                # Tudo Ok, balanço fechado
                status = 'matched'
        else:
            status = 'mismatch'

        return {
            'status': status,
            'source_id': source_id,
            'settlement_net': settlement_net_rounded,
            'releases_net': releases_net_rounded,
            'difference': abs(settlement_net_rounded - releases_net_rounded),
            'settlement': settlement,
            'installments': installments,
            'payments': payments,
            'refunds': {
                'settlement': refunds_settlement,
                'releases': refunds_releases
            },
            'chargebacks': {
                'settlement': chargebacks,
                'releases': chargebacks_releases
            },
            'chargeback_cancels': {
                'settlement': chargeback_cancels,
                'releases': chargeback_cancels_releases
            }
        }

    def _print_summary(self):
        """Imprime resumo dos resultados"""
        print("\n" + "=" * 80)
        print("RESUMO DA RECONCILIACAO V5")
        print("=" * 80)

        total = sum(len(v) if isinstance(v, list) else 0 for v in self.results.values())

        print(f"\n  Conciliadas (balanço zero):     {len(self.results['matched']):6d}")
        print(f"  Refundidas:                     {len(self.results['refunded']):6d}")
        print(f"  Chargeback Revertido:           {len(self.results['chargeback_reversed']):6d}")
        print(f"  Chargeback Pendente:            {len(self.results['chargeback_pending']):6d}")
        print(f"  Pendentes (não liberadas):      {len(self.results['pending']):6d}")
        print(f"  Mismatch (valores não batem):   {len(self.results['mismatch']):6d}")
        print(f"  Orfãs Settlement (sem release): {len(self.results['orphan_settlement']):6d}")
        print(f"  Orfãs Releases (sem settlement):{len(self.results['orphan_releases']):6d}")
        print(f"  " + "-" * 76)
        print(f"  TOTAL:                          {total:6d}")

        # Mostrar mismatches se houver
        if self.results['mismatch']:
            print(f"\n  AVISO: {len(self.results['mismatch'])} transacoes nao batem!")
            for item in self.results['mismatch'][:5]:
                print(f"    SOURCE_ID: {item['source_id']}")
                print(f"      Settlement: R$ {item['settlement_net']:.2f}")
                print(f"      Releases:   R$ {item['releases_net']:.2f}")
                print(f"      Diferenca:  R$ {item['difference']:.2f}")
            if len(self.results['mismatch']) > 5:
                print(f"    ... e mais {len(self.results['mismatch']) - 5}")

    def get_results(self):
        """Retorna resultados da reconciliação"""
        return self.results

    def get_summary(self):
        """Retorna resumo dos resultados"""
        return {
            'matched': len(self.results['matched']),
            'refunded': len(self.results['refunded']),
            'chargeback_reversed': len(self.results['chargeback_reversed']),
            'chargeback_pending': len(self.results['chargeback_pending']),
            'pending': len(self.results['pending']),
            'mismatch': len(self.results['mismatch']),
            'orphan_settlement': len(self.results['orphan_settlement']),
            'orphan_releases': len(self.results['orphan_releases']),
            'total': sum(len(v) if isinstance(v, list) else 0 for v in self.results.values())
        }
