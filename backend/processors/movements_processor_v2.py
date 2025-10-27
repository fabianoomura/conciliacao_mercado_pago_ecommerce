"""
Movements Processor V2
Processa movimentações especiais do Mercado Pago:
- Taxas de antecipação (fee-release_in_advance)
- Saques (payout)
- Reservas (reserve_for_debt_payment, reserve_for_payout)
- Chargebacks nos releases
"""

from datetime import datetime
from collections import defaultdict

class MovementsProcessorV2:
    def __init__(self, movements):
        """
        Inicializa com lista de movimentações
        movements: lista retornada por ReleasesProcessor.get_movements()
        """
        self.movements = movements
        self._categorize()
        
    def _categorize(self):
        """Categoriza movimentações por tipo"""
        self.advance_fees = []
        self.payouts = []
        self.reserves = []
        self.chargebacks = []
        
        for mov in self.movements:
            desc = mov['description']
            
            if 'advance' in desc and 'fee' in desc:
                self.advance_fees.append(mov)
            elif desc == 'payout':
                self.payouts.append(mov)
            elif desc.startswith('reserve_'):
                self.reserves.append(mov)
            elif 'chargeback' in desc:
                self.chargebacks.append(mov)
    
    def get_advance_fees_summary(self):
        """Retorna resumo das taxas de antecipação"""
        if not self.advance_fees:
            return {
                'total_fees': 0,
                'total_amount': 0,
                'count': 0,
                'fees': []
            }
        
        fees_list = []
        total_amount = 0
        
        for fee in self.advance_fees:
            amount = abs(fee['net_debit_amount'])
            total_amount += amount
            
            fees_list.append({
                'date': fee['release_date'],
                'source_id': fee['source_id'],
                'amount': amount,
                'gross_amount': fee['gross_amount'],
                'mp_fee': abs(fee['mp_fee'])
            })
        
        # Ordenar por data
        fees_list.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'count': len(fees_list),
            'total_amount': round(total_amount, 2),
            'fees': fees_list
        }
    
    def get_payouts_summary(self):
        """Retorna resumo dos saques"""
        if not self.payouts:
            return {
                'count': 0,
                'total_amount': 0,
                'payouts': []
            }
        
        payouts_list = []
        total_amount = 0
        
        for payout in self.payouts:
            amount = abs(payout['net_debit_amount'])
            total_amount += amount
            
            payouts_list.append({
                'date': payout['release_date'],
                'source_id': payout['source_id'],
                'amount': amount,
                'gross_amount': payout['gross_amount']
            })
        
        # Ordenar por data
        payouts_list.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'count': len(payouts_list),
            'total_amount': round(total_amount, 2),
            'payouts': payouts_list
        }
    
    def get_reserves_summary(self):
        """Retorna resumo das reservas"""
        # Agrupar reservas por tipo
        reserves_by_type = defaultdict(lambda: {
            'count': 0,
            'total_credit': 0,
            'total_debit': 0,
            'net': 0,
            'items': []
        })
        
        for reserve in self.reserves:
            rtype = reserve['description']
            
            reserves_by_type[rtype]['count'] += 1
            reserves_by_type[rtype]['total_credit'] += reserve['net_credit_amount']
            reserves_by_type[rtype]['total_debit'] += reserve['net_debit_amount']
            reserves_by_type[rtype]['net'] = (
                reserves_by_type[rtype]['total_credit'] - 
                abs(reserves_by_type[rtype]['total_debit'])
            )
            
            reserves_by_type[rtype]['items'].append({
                'date': reserve['release_date'],
                'source_id': reserve['source_id'],
                'credit': reserve['net_credit_amount'],
                'debit': reserve['net_debit_amount']
            })
        
        return dict(reserves_by_type)
    
    def get_chargebacks_summary(self):
        """Retorna resumo dos chargebacks"""
        if not self.chargebacks:
            return {
                'count': 0,
                'chargeback_applied': 0,
                'chargeback_reversed': 0,
                'net_chargeback': 0,
                'chargebacks': []
            }
        
        chargeback_applied = 0
        chargeback_reversed = 0
        chargebacks_list = []
        
        for cb in self.chargebacks:
            desc = cb['description']
            
            if desc == 'chargeback':
                amount = abs(cb['net_debit_amount'])
                chargeback_applied += amount
                
                chargebacks_list.append({
                    'type': 'applied',
                    'date': cb['release_date'],
                    'source_id': cb['source_id'],
                    'external_reference': cb['external_reference'],
                    'amount': amount
                })
            
            elif desc == 'chargeback_cancel':
                amount = cb['net_credit_amount']
                chargeback_reversed += amount
                
                chargebacks_list.append({
                    'type': 'reversed',
                    'date': cb['release_date'],
                    'source_id': cb['source_id'],
                    'external_reference': cb['external_reference'],
                    'amount': amount
                })
        
        # Ordenar por data
        chargebacks_list.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'count': len(chargebacks_list),
            'chargeback_applied': round(chargeback_applied, 2),
            'chargeback_reversed': round(chargeback_reversed, 2),
            'net_chargeback': round(chargeback_applied - chargeback_reversed, 2),
            'chargebacks': chargebacks_list
        }
    
    def get_full_summary(self):
        """Retorna resumo completo de todas as movimentações"""
        advance_fees = self.get_advance_fees_summary()
        payouts = self.get_payouts_summary()
        reserves = self.get_reserves_summary()
        chargebacks = self.get_chargebacks_summary()
        
        return {
            'total_movements': len(self.movements),
            'advance_fees': advance_fees,
            'payouts': payouts,
            'reserves': reserves,
            'chargebacks': chargebacks,
            'financial_summary': {
                'total_fees_paid': advance_fees['total_amount'],
                'total_withdrawn': payouts['total_amount'],
                'net_chargeback': chargebacks['net_chargeback']
            }
        }
    
    def validate_against_payments(self, total_received_from_payments):
        """
        Valida movimentações contra o total de payments recebidos
        """
        advance_fees = self.get_advance_fees_summary()
        payouts = self.get_payouts_summary()
        chargebacks = self.get_chargebacks_summary()
        
        # Saldo esperado no MP
        expected_balance = (
            total_received_from_payments - 
            payouts['total_amount'] - 
            advance_fees['total_amount'] -
            chargebacks['net_chargeback']
        )
        
        return {
            'total_received': total_received_from_payments,
            'total_fees': advance_fees['total_amount'],
            'total_withdrawn': payouts['total_amount'],
            'net_chargeback': chargebacks['net_chargeback'],
            'expected_balance': round(expected_balance, 2),
            'validation': {
                'is_valid': expected_balance >= -1.0,  # Tolerância de R$ 1
                'balance': round(expected_balance, 2)
            }
        }
    
    def get_advance_fee_rate(self, advance_payments_amount):
        """
        Calcula a taxa efetiva de antecipação
        """
        fees = self.get_advance_fees_summary()
        
        if advance_payments_amount > 0 and fees['total_amount'] > 0:
            rate = (fees['total_amount'] / advance_payments_amount) * 100
            return {
                'advance_amount': advance_payments_amount,
                'fee_amount': fees['total_amount'],
                'rate_percentage': round(rate, 2)
            }
        
        return {
            'advance_amount': 0,
            'fee_amount': 0,
            'rate_percentage': 0
        }