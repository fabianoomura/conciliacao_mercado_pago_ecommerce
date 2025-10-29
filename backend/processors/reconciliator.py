"""
Reconciliator V3 - VERSÃO FINAL CORRIGIDA
- Formatação correta de parcelas (1/2 em vez de 1/2/2)
- Detecção automática de parcelas canceladas (estorno total)
- Separação de parcelas ativas vs canceladas
- Status detalhados (received, received_advance, pending, overdue, cancelled)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

class ReconciliatorV3:
    def __init__(self, settlement_installments, payments, order_balances=None):
        self.installments = settlement_installments
        self.payments = payments
        self.order_balances = order_balances or {}
        self._create_indexes()
        self._fix_installment_formatting()
        
    def _create_indexes(self):
        """Cria índices para otimizar buscas"""
        self.payments_by_ref = {}
        for payment in self.payments:
            ref = payment.get('external_reference', '')
            if ref and ref != 'nan' and ref != '':
                if ref not in self.payments_by_ref:
                    self.payments_by_ref[ref] = []
                self.payments_by_ref[ref].append(payment)
        
        print(f"\n    Índice criado: {len(self.payments_by_ref)} references únicas nos payments")
    
    def _fix_installment_formatting(self):
        """Corrige formatação de parcelas e identifica canceladas"""
        for installment in self.installments:
            # Corrigir formato de installment_number
            inst_num = str(installment.get('installment_number', '1')).strip()
            total_inst = installment.get('total_installments', 1)
            
            # Remover formatação duplicada como "1/5/5" -> "1/5"
            if '/' in inst_num:
                parts = inst_num.split('/')
                inst_num = parts[0].strip()  # Pegar apenas o primeiro número
            
            # Converter para int e voltar para string (remove zeros à esquerda, etc)
            try:
                inst_num = str(int(inst_num))
            except:
                inst_num = '1'
            
            # Atualizar com formato correto
            installment['installment_number'] = inst_num
            installment['installment_display'] = f"{inst_num}/{total_inst}"
            
            # Também corrigir o campo original se existir
            if 'installments' in installment:
                installment['installments'] = f"{inst_num}/{total_inst}"
            
            # Verificar se a parcela foi totalmente estornada/cancelada
            amount = installment.get('installment_net_amount', 0)
            original_amount = installment.get('installment_net_amount_original', amount)
            
            # Se valor for 0 ou negativo, marcar como cancelada
            if amount <= 0:
                installment['is_cancelled'] = True
                
                # Verificar motivo do cancelamento
                refund = installment.get('refund_applied', 0)
                chargeback = installment.get('chargeback_applied', 0)
                
                if refund > 0 and refund >= abs(original_amount):
                    installment['cancelled_reason'] = 'full_refund'
                elif chargeback > 0 and chargeback >= abs(original_amount):
                    installment['cancelled_reason'] = 'chargeback'
                else:
                    installment['cancelled_reason'] = 'unknown'
            else:
                installment['is_cancelled'] = False
    
    def _parse_date_safe(self, date_value):
        """Parse date safely to date object"""
        if not date_value:
            return None
        if isinstance(date_value, str):
            try:
                return datetime.fromisoformat(date_value).date()
            except:
                return None
        if isinstance(date_value, datetime):
            return date_value.date()
        return date_value
    
    def reconcile(self):
        """
        Executa a conciliação baseada em SALDO DE PEDIDO
        Nova lógica (V3.1):
        - Agrupa por external_reference (pedido)
        - Calcula saldo esperado vs saldo recebido
        - Permite valores diferentes quando há estornos/adiantamentos
        - Marca pedido como FECHADO quando saldo bate
        """
        print("\n   Iniciando conciliação (V3.1 - BALANCE BASED)...")

        today = datetime.now().date()

        # Passo 1: Calcular saldos por pedido
        order_balances = self._calculate_order_balances()

        # Passo 2: Reconciliar cada pedido
        self._reconcile_by_order_balance(order_balances, today)

        # Passo 3: Gerar estatísticas
        stats = self._generate_stats()

        print(f"    Pedidos fechados: {stats['closed_orders']}")
        print(f"    Pedidos abertos: {stats['open_orders']}")
        print(f"    Parcelas conciliadas: {stats['matched']}")
        print(f"    Parcelas antecipadas: {stats['advance']}")
        print(f"     Parcelas pendentes: {stats['pending']}")
        print(f"    Parcelas atrasadas: {stats['overdue']}")
        print(f"    Parcelas canceladas: {stats['cancelled']}")

        return {
            'total_installments': len(self.installments),
            'matched': stats['matched'],
            'advance': stats['advance'],
            'pending': stats['pending'],
            'overdue': stats['overdue'],
            'cancelled': stats['cancelled'],
            'closed_orders': stats['closed_orders'],
            'open_orders': stats['open_orders'],
            'match_rate': (stats['matched'] / len(self.installments) * 100) if self.installments else 0
        }

    def _calculate_order_balances(self):
        """Calcula saldo esperado vs recebido por pedido"""
        order_balances = {}

        # Agrupar parcelas por pedido
        for inst in self.installments:
            ref = inst.get('external_reference', '')
            if not ref:
                continue

            if ref not in order_balances:
                order_balances[ref] = {
                    'expected_total': 0,
                    'received_total': 0,
                    'installments': [],
                    'payments': []
                }

            # Ignorar parcelas canceladas no cálculo
            if not inst.get('is_cancelled', False) and inst.get('installment_net_amount', 0) > 0:
                order_balances[ref]['expected_total'] += inst.get('installment_net_amount', 0)

            order_balances[ref]['installments'].append(inst)

        # Agrupar payments por pedido
        for payment in self.payments:
            ref = payment.get('external_reference', '')
            if not ref or ref not in order_balances:
                continue

            order_balances[ref]['received_total'] += payment.get('net_credit_amount', 0)
            order_balances[ref]['payments'].append(payment)

        return order_balances

    def _reconcile_by_order_balance(self, order_balances, today):
        """Reconcilia parcelas baseado em saldo de pedido"""

        for ref, balance in order_balances.items():
            expected = balance['expected_total']
            received = balance['received_total']
            installments = balance['installments']
            payments = balance['payments']

            # Calcular status do pedido
            diff = received - expected
            tolerance = 0.02  # R$ 0.02 de tolerância

            if abs(diff) <= tolerance:
                # Pedido FECHADO - saldo bate
                order_status = 'CLOSED'
                self._mark_order_closed(installments, payments, today)
            elif received > expected:
                # Recebeu MAIS que esperado - possível erro
                order_status = 'ERROR'
                self._mark_order_error(installments, payments, today, received - expected)
            else:
                # Pedido ABERTO - faltam receber
                order_status = 'OPEN'
                self._mark_order_open(installments, payments, today)

            # Atualizar campo de status do pedido
            for inst in installments:
                inst['order_balance_status'] = order_status
                inst['order_expected_total'] = expected
                inst['order_received_total'] = received

    def _mark_order_closed(self, installments, payments, today):
        """Marca todas as parcelas como recebidas quando pedido está fechado"""

        # Agrupar payments por parcela
        payments_by_inst = defaultdict(list)
        for payment in payments:
            # Tentar extrair número da parcela
            inst_str = str(payment.get('installments', ''))
            if '/' in inst_str:
                inst_num = inst_str.split('/')[0].strip()
            else:
                inst_num = inst_str.strip()

            payments_by_inst[inst_num].append(payment)

        # Marcar parcelas
        for inst in installments:
            # Ignorar canceladas
            if inst.get('is_cancelled', False):
                inst['status'] = 'cancelled'
                continue

            inst_num = inst.get('installment_number', '')
            release_date = self._parse_date_safe(inst.get('money_release_date'))

            # Procurar payment para esta parcela
            matched_payment = None
            if inst_num in payments_by_inst:
                # Preferir payment com mesmo número
                matched_payment = payments_by_inst[inst_num][0]
            elif len(payments) > 0:
                # Se não encontrou por número, usar primeiro payment disponível
                # (para casos com valores diferentes)
                matched_payment = payments[0]

            if matched_payment:
                payment_date = self._parse_date_safe(matched_payment.get('release_date'))

                # Detectar adiantamento
                if release_date and payment_date and payment_date < release_date:
                    days_advance = (release_date - payment_date).days
                    inst['status'] = 'received_advance'
                    inst['days_advance'] = days_advance
                else:
                    inst['status'] = 'received'

                inst['received_amount'] = matched_payment.get('net_credit_amount', 0)
                inst['received_date'] = matched_payment.get('release_date')
                inst['source_id'] = matched_payment.get('source_id', '')

                # Remover de payments utilizados (para não usar 2x)
                if matched_payment in payments:
                    payments.remove(matched_payment)
            else:
                inst['status'] = 'received'  # Pedido fechado, mas sem payment específico

    def _mark_order_open(self, installments, payments, today):
        """Marca parcelas de um pedido aberto (incompleto)

        Lógica inteligente:
        - Se há pagamentos, tenta fazer match
        - Se há pagamentos mas não bate exatamente, marca como 'pending' até data limite
        - Se passou data esperada E não há payments, marca como 'overdue'
        """

        # Verificar se há algum payment para este pedido
        has_any_payment = len(payments) > 0
        last_payment_date = None
        if has_any_payment:
            dates = [self._parse_date_safe(p.get('release_date')) for p in payments]
            dates = [d for d in dates if d]
            if dates:
                last_payment_date = max(dates)

        # Manter a lógica atual de matching por parcela
        for inst in installments:
            # Ignorar canceladas
            if inst.get('is_cancelled', False):
                inst['status'] = 'cancelled'
                continue

            ref = inst.get('external_reference', '')
            inst_number = inst.get('installment_number', '')
            release_date = self._parse_date_safe(inst.get('money_release_date'))
            expected_amount = inst.get('installment_net_amount', 0)

            if expected_amount < 1.0:
                inst['status'] = 'cancelled'
                inst['is_cancelled'] = True
                continue

            # Tentar match por parcela
            matched_payment = self._find_matching_payment(
                ref, inst_number, expected_amount, payments
            )

            if matched_payment:
                payment_date = self._parse_date_safe(matched_payment.get('release_date'))

                if release_date and payment_date and payment_date < release_date:
                    days_advance = (release_date - payment_date).days
                    inst['status'] = 'received_advance'
                    inst['days_advance'] = days_advance
                else:
                    inst['status'] = 'received'

                inst['received_amount'] = matched_payment.get('net_credit_amount', 0)
                inst['received_date'] = matched_payment.get('release_date')
                inst['source_id'] = matched_payment.get('source_id', '')
            else:
                # Sem match exato
                if has_any_payment:
                    # Há payments, mas não batem exatamente
                    # Isso pode ser por estorno ou distribuição diferente
                    if release_date and release_date >= today:
                        # Data no futuro: não deverias aparecer em pendentes ainda
                        inst['status'] = 'pending'  # Data não venceu
                    elif release_date and release_date < today:
                        # Se passou do esperado, mas há evidência de pagamento
                        # Marcar como 'pending' (mais tolerante que overdue)
                        inst['status'] = 'pending'
                        inst['_note'] = 'Pendente: há pagamentos mas distribuição diferente'
                    else:
                        inst['status'] = 'pending'
                else:
                    # Sem pagamentos
                    if release_date and release_date < today:
                        inst['status'] = 'overdue'
                    else:
                        inst['status'] = 'pending'

    def _mark_order_error(self, installments, payments, today, excess):
        """Marca pedido com erro (recebeu mais que esperado)"""

        for inst in installments:
            if inst.get('is_cancelled', False):
                inst['status'] = 'cancelled'
            else:
                inst['status'] = 'received'
                inst['_note'] = f'ERRO: Recebeu R$ {excess:.2f} a mais'

    def _find_matching_payment(self, ref, inst_number, expected_amount, all_payments):
        """Encontra payment que corresponde à parcela (com tolerância)

        Estratégia de matching:
        1. Procura por número + valor exato (tolerância pequena)
        2. Procura por número + valor maior (casos de adiantamento)
        3. Procura por valor similar (casos com estorno/distribuição diferente)
        """

        candidate_payments = self.payments_by_ref.get(ref, [])

        if not candidate_payments:
            return None

        total_inst = 1  # Default
        for inst in self.installments:
            if inst.get('external_reference') == ref:
                total_inst = inst.get('total_installments', 1)
                break

        # Fase 1: Match por número + valor (tolerância pequena)
        for payment in candidate_payments:
            payment_inst = str(payment.get('installments', ''))
            payment_amount = payment.get('net_credit_amount', 0)

            # Limpar formatação
            if '/' in payment_inst:
                payment_inst_clean = payment_inst.split('/')[0].strip()
            else:
                payment_inst_clean = payment_inst.strip()

            # Verificar match
            is_number_match = (payment_inst_clean == inst_number)
            diff = abs(payment_amount - expected_amount)
            percent_diff = (diff / expected_amount * 100) if expected_amount > 0 else 0
            is_amount_match = (diff <= 0.02) or (diff <= 10.00 and percent_diff <= 5.0)

            if is_number_match and is_amount_match:
                return payment

        # Fase 2: Match por número (mesmo que valor diferente - casos com estorno)
        # Se há pagamentos com o número certo, usar mesmo que valor seja diferente
        for payment in candidate_payments:
            payment_inst = str(payment.get('installments', ''))

            # Limpar formatação
            if '/' in payment_inst:
                payment_inst_clean = payment_inst.split('/')[0].strip()
            else:
                payment_inst_clean = payment_inst.strip()

            if payment_inst_clean == inst_number:
                # Encontrou payment com número certo, mesmo que valor seja diferente
                return payment

        # Fase 3: Match apenas por valor (para single payments)
        if total_inst == 1:
            for payment in candidate_payments:
                payment_amount = payment.get('net_credit_amount', 0)
                diff = abs(payment_amount - expected_amount)
                percent_diff = (diff / expected_amount * 100) if expected_amount > 0 else 0
                is_amount_match = (diff <= 0.02) or (diff <= 10.00 and percent_diff <= 5.0)

                if is_amount_match:
                    return payment

        return None

    def _generate_stats(self):
        """Gera estatísticas de reconciliação"""

        matched = 0
        advance = 0
        pending = 0
        overdue = 0
        cancelled = 0
        closed_orders = set()
        open_orders = set()

        for inst in self.installments:
            status = inst.get('status', '')
            ref = inst.get('external_reference', '')
            order_status = inst.get('order_balance_status', '')

            if status == 'received' or status == 'received_advance':
                matched += 1
                if status == 'received_advance':
                    advance += 1
                if order_status == 'CLOSED':
                    closed_orders.add(ref)
            elif status == 'pending':
                pending += 1
                open_orders.add(ref)
            elif status == 'overdue':
                overdue += 1
                open_orders.add(ref)
            elif status == 'cancelled':
                cancelled += 1

        return {
            'matched': matched,
            'advance': advance,
            'pending': pending,
            'overdue': overdue,
            'cancelled': cancelled,
            'closed_orders': len(closed_orders),
            'open_orders': len(open_orders)
        }
    
    def detect_advance_payments(self):
        """
        Detecta adiantamentos de crédito
        """
        advances = []
        
        # Agrupar payments por ref e data
        grouped = defaultdict(list)
        for payment in self.payments:
            ref = payment.get('external_reference', '')
            date = payment.get('release_date', '')[:10] if payment.get('release_date') else ''
            
            if ref and date:
                grouped[(ref, date)].append(payment)
        
        # Detectar adiantamentos
        for (ref, date), payments_list in grouped.items():
            if len(payments_list) >= 2:
                installments_nums = []
                for p in payments_list:
                    inst = p.get('installments', '')
                    if '/' in inst:
                        try:
                            num = int(inst.split('/')[0])
                            installments_nums.append(num)
                        except:
                            pass
                
                if installments_nums and installments_nums != sorted(installments_nums):
                    total_amount = sum(p['net_credit_amount'] for p in payments_list)
                    
                    advances.append({
                        'external_reference': ref,
                        'date': date,
                        'installments_received': len(payments_list),
                        'installments': installments_nums,
                        'out_of_order': True,
                        'total_amount': round(total_amount, 2)
                    })
        
        return advances
    
    def get_detailed_status(self):
        """Retorna status detalhado da conciliação"""
        received = [i for i in self.installments if i['status'] == 'received']
        received_advance = [i for i in self.installments if i['status'] == 'received_advance']
        pending = [i for i in self.installments if i['status'] == 'pending']
        overdue = [i for i in self.installments if i['status'] == 'overdue']
        cancelled = [i for i in self.installments if i['status'] == 'cancelled']
        
        # Calcular totais apenas de parcelas ativas
        active_installments = [i for i in self.installments if i['status'] != 'cancelled']
        
        total_expected = sum(i.get('installment_net_amount', 0) for i in active_installments)
        total_received = sum(i.get('received_amount', 0) for i in received + received_advance)
        total_pending = sum(i.get('installment_net_amount', 0) for i in pending)
        total_overdue = sum(i.get('installment_net_amount', 0) for i in overdue)
        
        # Total de ajustes aplicados
        total_refund_applied = sum(i.get('refund_applied', 0) for i in active_installments)
        total_chargeback_applied = sum(i.get('chargeback_applied', 0) for i in active_installments)
        
        return {
            'summary': {
                'total_installments': len(self.installments),
                'active_installments': len(active_installments),
                'cancelled_installments': len(cancelled),
                'total_expected': round(total_expected, 2),
                'total_received': round(total_received, 2),
                'total_pending': round(total_pending, 2),
                'total_overdue': round(total_overdue, 2),
                'total_refund_applied': round(total_refund_applied, 2),
                'total_chargeback_applied': round(total_chargeback_applied, 2)
            },
            'status_breakdown': {
                'received': {
                    'count': len(received),
                    'amount': round(sum(i.get('received_amount', 0) for i in received), 2),
                    'percentage': round((len(received) / len(active_installments) * 100), 2) if active_installments else 0
                },
                'received_advance': {
                    'count': len(received_advance),
                    'amount': round(sum(i.get('received_amount', 0) for i in received_advance), 2),
                    'percentage': round((len(received_advance) / len(active_installments) * 100), 2) if active_installments else 0,
                    'avg_days_advance': round(sum(i.get('days_advance', 0) for i in received_advance) / len(received_advance), 1) if received_advance else 0
                },
                'pending': {
                    'count': len(pending),
                    'amount': round(total_pending, 2),
                    'percentage': round((len(pending) / len(active_installments) * 100), 2) if active_installments else 0
                },
                'overdue': {
                    'count': len(overdue),
                    'amount': round(total_overdue, 2),
                    'percentage': round((len(overdue) / len(active_installments) * 100), 2) if active_installments else 0
                },
                'cancelled': {
                    'count': len(cancelled),
                    'amount': 0,
                    'percentage': round((len(cancelled) / len(self.installments) * 100), 2) if self.installments else 0
                }
            },
            'validation': {
                'expected_vs_received_pending': {
                    'expected': round(total_expected, 2),
                    'received_plus_pending': round(total_received + total_pending + total_overdue, 2),
                    'difference': round(total_expected - (total_received + total_pending + total_overdue), 2),
                    'is_valid': abs(total_expected - (total_received + total_pending + total_overdue)) < 1.0
                }
            }
        }
    
    def get_orphan_payments(self):
        """Retorna payments órfãos"""
        matched_source_ids = set()
        for inst in self.installments:
            if inst['status'] in ['received', 'received_advance']:
                source_id = inst.get('source_id', '')
                if source_id:
                    matched_source_ids.add(source_id)
        
        known_refs = set(inst['external_reference'] for inst in self.installments)
        
        orphan_payments = []
        for payment in self.payments:
            source_id = str(payment.get('source_id', ''))
            ref = payment.get('external_reference', '')
            
            if source_id not in matched_source_ids and ref not in known_refs:
                orphan_payments.append(payment)
        
        total_orphan = sum(p.get('net_credit_amount', 0) for p in orphan_payments)
        
        return {
            'count': len(orphan_payments),
            'total_amount': round(total_orphan, 2),
            'payments': orphan_payments
        }
    
    def get_reconciliation_report(self):
        """Gera relatório completo de conciliação"""
        detailed = self.get_detailed_status()
        orphans = self.get_orphan_payments()
        advances = self.detect_advance_payments()
        
        total_payments_all = sum(p.get('net_credit_amount', 0) for p in self.payments)
        total_payments_filtered = total_payments_all - orphans['total_amount']
        
        # Análise de pedidos com ajustes
        orders_with_adjustments = []
        for ref, balance in self.order_balances.items():
            if balance.get('refunded', 0) > 0 or balance.get('chargeback', 0) > 0:
                order_insts = [i for i in self.installments if i['external_reference'] == ref]
                
                orders_with_adjustments.append({
                    'external_reference': ref,
                    'total_net': balance['total_net'],
                    'refunded': balance.get('refunded', 0),
                    'chargeback': balance.get('chargeback', 0),
                    'final_net': balance['final_net'],
                    'installments_count': len(order_insts),
                    'cancelled_count': len([i for i in order_insts if i.get('is_cancelled')])
                })
        
        return {
            'detailed_status': detailed,
            'orphan_payments': orphans,
            'advance_payments': {
                'count': len(advances),
                'details': advances
            },
            'validation': {
                'installments_vs_payments': {
                    'installments_received': detailed['summary']['total_received'],
                    'payments_filtered': round(total_payments_filtered, 2),
                    'payments_all': round(total_payments_all, 2),
                    'payments_orphan': orphans['total_amount'],
                    'difference': round(detailed['summary']['total_received'] - total_payments_filtered, 2),
                    'is_valid': abs(detailed['summary']['total_received'] - total_payments_filtered) < 1.0
                }
            },
            'adjustments_analysis': {
                'orders_with_adjustments': len(orders_with_adjustments),
                'total_refunded': sum(o['refunded'] for o in orders_with_adjustments),
                'total_chargeback': sum(o['chargeback'] for o in orders_with_adjustments),
                'orders_fully_cancelled': len([o for o in orders_with_adjustments if o['cancelled_count'] == o['installments_count']]),
                'details': orders_with_adjustments
            }
        }
    
    def get_installments_by_status(self, status):
        """Retorna parcelas filtradas por status"""
        return [i for i in self.installments if i['status'] == status]