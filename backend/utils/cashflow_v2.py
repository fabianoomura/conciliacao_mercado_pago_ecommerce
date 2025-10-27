"""
Cashflow Calculator V2
Calcula fluxo de caixa considerando:
- Parcelas recebidas e pendentes
- Adiantamentos
- Estornos e chargebacks
- Status detalhados
"""

from datetime import datetime, timedelta
from collections import defaultdict

class CashFlowCalculatorV2:
    def __init__(self, installments):
        self.installments = installments
    
    def _get_installment_value(self, installment):
        """Retorna o valor da parcela (recebido ou estimado)"""
        # Se foi recebida, usar o valor recebido
        if installment.get('received_amount'):
            return installment['received_amount']
        
        # Se está pendente, usar o valor ajustado
        return installment.get('installment_net_amount', 0)
    
    def get_daily_cashflow(self, start_date=None, end_date=None):
        """Retorna fluxo de caixa diário"""
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        # Filtrar parcelas relevantes
        relevant_installments = [
            i for i in self.installments 
            if i['status'] in ['pending', 'received', 'received_advance', 'overdue']
        ]
        
        # Agrupar por data
        daily_flow = defaultdict(lambda: {
            'date': '',
            'expected': 0.0,
            'received': 0.0,
            'received_advance': 0.0,
            'pending': 0.0,
            'overdue': 0.0,
            'count_expected': 0,
            'count_received': 0,
            'count_received_advance': 0,
            'count_pending': 0,
            'count_overdue': 0
        })
        
        for installment in relevant_installments:
            # Data esperada ou recebida
            if installment['status'] in ['received', 'received_advance']:
                date = installment.get('received_date', '')[:10]
            else:
                date = installment.get('money_release_date', '')[:10]
            
            if not date:
                continue
            
            if end_date and date > end_date:
                continue
            
            if date >= start_date:
                daily_flow[date]['date'] = date
                
                value = self._get_installment_value(installment)
                status = installment['status']
                
                if status == 'received':
                    daily_flow[date]['received'] += value
                    daily_flow[date]['count_received'] += 1
                elif status == 'received_advance':
                    daily_flow[date]['received_advance'] += value
                    daily_flow[date]['count_received_advance'] += 1
                elif status == 'pending':
                    daily_flow[date]['pending'] += value
                    daily_flow[date]['count_pending'] += 1
                elif status == 'overdue':
                    daily_flow[date]['overdue'] += value
                    daily_flow[date]['count_overdue'] += 1
                
                daily_flow[date]['expected'] += value
                daily_flow[date]['count_expected'] += 1
        
        # Converter para lista e ordenar
        result = sorted(daily_flow.values(), key=lambda x: x['date'])
        
        # Arredondar valores
        for item in result:
            item['expected'] = round(item['expected'], 2)
            item['received'] = round(item['received'], 2)
            item['received_advance'] = round(item['received_advance'], 2)
            item['pending'] = round(item['pending'], 2)
            item['overdue'] = round(item['overdue'], 2)
        
        return result
    
    def get_monthly_cashflow(self, start_date=None, end_date=None):
        """Retorna fluxo de caixa mensal"""
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        # Filtrar parcelas relevantes
        relevant_installments = [
            i for i in self.installments 
            if i['status'] in ['pending', 'received', 'received_advance', 'overdue']
        ]
        
        # Agrupar por mês (YYYY-MM)
        monthly_flow = defaultdict(lambda: {
            'month': '',
            'expected': 0.0,
            'received': 0.0,
            'received_advance': 0.0,
            'pending': 0.0,
            'overdue': 0.0,
            'count_expected': 0,
            'count_received': 0,
            'count_received_advance': 0,
            'count_pending': 0,
            'count_overdue': 0
        })
        
        for installment in relevant_installments:
            # Data esperada ou recebida
            if installment['status'] in ['received', 'received_advance']:
                date = installment.get('received_date', '')
            else:
                date = installment.get('money_release_date', '')
            
            if not date:
                continue
            
            if end_date and date > end_date:
                continue
            
            if date >= start_date:
                # Extrair ano-mês
                month_key = date[:7]  # YYYY-MM
                
                monthly_flow[month_key]['month'] = month_key
                
                value = self._get_installment_value(installment)
                status = installment['status']
                
                if status == 'received':
                    monthly_flow[month_key]['received'] += value
                    monthly_flow[month_key]['count_received'] += 1
                elif status == 'received_advance':
                    monthly_flow[month_key]['received_advance'] += value
                    monthly_flow[month_key]['count_received_advance'] += 1
                elif status == 'pending':
                    monthly_flow[month_key]['pending'] += value
                    monthly_flow[month_key]['count_pending'] += 1
                elif status == 'overdue':
                    monthly_flow[month_key]['overdue'] += value
                    monthly_flow[month_key]['count_overdue'] += 1
                
                monthly_flow[month_key]['expected'] += value
                monthly_flow[month_key]['count_expected'] += 1
        
        # Converter para lista e ordenar
        result = sorted(monthly_flow.values(), key=lambda x: x['month'])
        
        # Arredondar valores
        for item in result:
            item['expected'] = round(item['expected'], 2)
            item['received'] = round(item['received'], 2)
            item['received_advance'] = round(item['received_advance'], 2)
            item['pending'] = round(item['pending'], 2)
            item['overdue'] = round(item['overdue'], 2)
        
        return result
    
    def get_summary_by_status(self):
        """Retorna resumo agrupado por status"""
        status_summary = defaultdict(lambda: {
            'count': 0,
            'total_amount': 0.0
        })
        
        for installment in self.installments:
            status = installment['status']
            status_summary[status]['count'] += 1
            
            value = self._get_installment_value(installment)
            status_summary[status]['total_amount'] += value
        
        # Arredondar valores
        for status in status_summary:
            status_summary[status]['total_amount'] = round(status_summary[status]['total_amount'], 2)
        
        return dict(status_summary)
    
    def get_overdue_installments(self):
        """Retorna parcelas atrasadas"""
        overdue = [
            i for i in self.installments 
            if i['status'] == 'overdue'
        ]
        
        total_overdue = sum(self._get_installment_value(i) for i in overdue)
        
        return {
            'count': len(overdue),
            'total_amount': round(total_overdue, 2),
            'installments': overdue
        }
    
    def get_upcoming_days(self, days=7):
        """Retorna parcelas dos próximos N dias"""
        today = datetime.now()
        end_date = (today + timedelta(days=days)).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        upcoming = [
            i for i in self.installments 
            if i['status'] == 'pending' and 
            i.get('money_release_date', '') and 
            today_str <= i['money_release_date'] <= end_date
        ]
        
        total_upcoming = sum(self._get_installment_value(i) for i in upcoming)
        
        return {
            'count': len(upcoming),
            'total_amount': round(total_upcoming, 2),
            'installments': sorted(upcoming, key=lambda x: x.get('money_release_date', ''))
        }
    
    def get_advance_summary(self):
        """Retorna resumo de parcelas antecipadas"""
        advance = [
            i for i in self.installments 
            if i['status'] == 'received_advance'
        ]
        
        if not advance:
            return {
                'count': 0,
                'total_amount': 0,
                'avg_days_advance': 0,
                'installments': []
            }
        
        total_amount = sum(i.get('received_amount', 0) for i in advance)
        avg_days = sum(i.get('days_advance', 0) for i in advance) / len(advance)
        
        return {
            'count': len(advance),
            'total_amount': round(total_amount, 2),
            'avg_days_advance': round(avg_days, 1),
            'installments': advance
        }
    
    def get_summary(self):
        """Retorna totais gerais"""
        total_expected = 0.0
        total_received = 0.0
        total_received_advance = 0.0
        total_pending = 0.0
        total_overdue = 0.0
        
        for i in self.installments:
            value = self._get_installment_value(i)
            status = i['status']
            
            if status in ['pending', 'received', 'received_advance', 'overdue']:
                total_expected += value
            
            if status == 'received':
                total_received += value
            elif status == 'received_advance':
                total_received_advance += value
            elif status == 'pending':
                total_pending += value
            elif status == 'overdue':
                total_overdue += value
        
        return {
            'total_expected': round(total_expected, 2),
            'total_received': round(total_received, 2),
            'total_received_advance': round(total_received_advance, 2),
            'total_pending': round(total_pending, 2),
            'total_overdue': round(total_overdue, 2),
            'count_total': len(self.installments),
            'count_received': len([i for i in self.installments if i['status'] == 'received']),
            'count_received_advance': len([i for i in self.installments if i['status'] == 'received_advance']),
            'count_pending': len([i for i in self.installments if i['status'] == 'pending']),
            'count_overdue': len([i for i in self.installments if i['status'] == 'overdue'])
        }