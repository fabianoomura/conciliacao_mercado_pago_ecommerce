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
        Executa a conciliação completa
        """
        print("\n   Iniciando conciliação (V3 - FIXED)...")
        
        matched = 0
        unmatched = 0
        overdue = 0
        advance = 0
        cancelled = 0
        today = datetime.now().date()
        
        for installment in self.installments:
            # Verificar se foi cancelada por estorno total
            if installment.get('is_cancelled', False):
                installment['status'] = 'cancelled'
                cancelled += 1
                continue
            
            ref = installment.get('external_reference', '')
            inst_number = installment.get('installment_number', '')
            release_date = self._parse_date_safe(installment.get('money_release_date'))
            
            # Valor esperado (já ajustado com estornos)
            expected_amount = installment.get('installment_net_amount', 0)
            
            # Se valor for muito baixo após ajustes, considerar cancelada
            if expected_amount < 1.0:
                installment['status'] = 'cancelled'
                installment['is_cancelled'] = True
                installment['cancelled_reason'] = 'low_amount'
                cancelled += 1
                continue
            
            # Buscar payments candidatos
            candidate_payments = self.payments_by_ref.get(ref, [])
            
            if not candidate_payments:
                # Sem payment - verificar status
                if release_date and release_date < today:
                    installment['status'] = 'overdue'
                    overdue += 1
                else:
                    installment['status'] = 'pending'
                unmatched += 1
                continue
            
            # Tentar match
            matched_payment = None
            total_inst = installment.get('total_installments', 1)

            # Estratégia: Match por INSTALLMENT_NUMBER + VALOR (com tolerância)
            # Primeiro tentar match exato por parcela
            for payment in candidate_payments:
                payment_inst = str(payment.get('installments', ''))
                payment_amount = payment.get('net_credit_amount', 0)

                # Limpar formatação do payment (ex: "1/6" -> "1")
                if '/' in payment_inst:
                    payment_inst_clean = payment_inst.split('/')[0].strip()
                else:
                    payment_inst_clean = payment_inst.strip()

                # Verificar se é match de parcela
                is_number_match = (payment_inst_clean == inst_number)

                # Verificar se valor bate com tolerância
                diff = abs(payment_amount - expected_amount)
                percent_diff = (diff / expected_amount * 100) if expected_amount > 0 else 0

                # Aceitar match se:
                # 1. Número bate E valor bate (tolerância <= 0.02 ou <= 10/5%)
                # 2. OU Para single payments (1/1): apenas valor bate (flexível com número)
                is_amount_match = (diff <= 0.02) or (diff <= 10.00 and percent_diff <= 5.0)

                if is_number_match and is_amount_match:
                    matched_payment = payment
                    break

            # Se não encontrou match por número, tentar match apenas por valor (para single payments)
            if not matched_payment and total_inst == 1:
                for payment in candidate_payments:
                    payment_amount = payment.get('net_credit_amount', 0)
                    diff = abs(payment_amount - expected_amount)
                    percent_diff = (diff / expected_amount * 100) if expected_amount > 0 else 0

                    is_amount_match = (diff <= 0.02) or (diff <= 10.00 and percent_diff <= 5.0)

                    if is_amount_match:
                        matched_payment = payment
                        break
            
            if matched_payment:
                payment_date = self._parse_date_safe(matched_payment['release_date'])
                
                # Detectar adiantamento
                if release_date and payment_date and payment_date < release_date:
                    days_advance = (release_date - payment_date).days
                    installment['status'] = 'received_advance'
                    installment['days_advance'] = days_advance
                    advance += 1
                else:
                    installment['status'] = 'received'
                
                installment['received_amount'] = matched_payment['net_credit_amount']
                installment['received_date'] = matched_payment['release_date']
                installment['source_id'] = matched_payment.get('source_id', '')
                matched += 1
            else:
                # Não encontrou match
                if release_date and release_date < today:
                    installment['status'] = 'overdue'
                    overdue += 1
                else:
                    installment['status'] = 'pending'
                unmatched += 1
        
        print(f"    Parcelas conciliadas: {matched}")
        print(f"    Parcelas antecipadas: {advance}")
        print(f"     Parcelas pendentes: {unmatched - overdue}")
        print(f"    Parcelas atrasadas: {overdue}")
        print(f"    Parcelas canceladas: {cancelled}")
        
        return {
            'total_installments': len(self.installments),
            'matched': matched,
            'advance': advance,
            'pending': unmatched - overdue,
            'overdue': overdue,
            'cancelled': cancelled,
            'match_rate': (matched / len(self.installments) * 100) if self.installments else 0
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