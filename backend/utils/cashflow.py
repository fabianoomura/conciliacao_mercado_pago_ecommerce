from datetime import datetime, timedelta
from collections import defaultdict

class CashFlowCalculator:
    """Calcula o fluxo de caixa futuro baseado nas parcelas"""
    
    def __init__(self, installments):
        self.installments = installments
    
    def get_daily_cashflow(self, start_date=None, end_date=None):
        """Retorna fluxo de caixa diário"""
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        # Filtrar apenas parcelas pendentes ou recebidas
        relevant_installments = [
            i for i in self.installments 
            if i['status'] in ['pending', 'received']
        ]
        
        # Agrupar por data
        daily_flow = defaultdict(lambda: {
            'date': '',
            'expected': 0.0,
            'received': 0.0,
            'pending': 0.0,
            'count_expected': 0,
            'count_received': 0,
            'count_pending': 0
        })
        
        for installment in relevant_installments:
            # Data esperada
            expected_date = installment['expected_date']
            
            if end_date and expected_date > end_date:
                continue
            
            if expected_date >= start_date:
                daily_flow[expected_date]['date'] = expected_date
                
                if installment['status'] == 'received':
                    daily_flow[expected_date]['received'] += installment['received_amount'] or 0
                    daily_flow[expected_date]['count_received'] += 1
                else:
                    daily_flow[expected_date]['pending'] += installment['net_amount']
                    daily_flow[expected_date]['count_pending'] += 1
                
                daily_flow[expected_date]['expected'] += installment['net_amount']
                daily_flow[expected_date]['count_expected'] += 1
        
        # Converter para lista e ordenar
        result = sorted(daily_flow.values(), key=lambda x: x['date'])
        
        # Arredondar valores
        for item in result:
            item['expected'] = round(item['expected'], 2)
            item['received'] = round(item['received'], 2)
            item['pending'] = round(item['pending'], 2)
        
        return result
    
    def get_monthly_cashflow(self, start_date=None, end_date=None):
        """Retorna fluxo de caixa mensal"""
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
        
        # Filtrar apenas parcelas pendentes ou recebidas
        relevant_installments = [
            i for i in self.installments 
            if i['status'] in ['pending', 'received']
        ]
        
        # Agrupar por mês (YYYY-MM)
        monthly_flow = defaultdict(lambda: {
            'month': '',
            'expected': 0.0,
            'received': 0.0,
            'pending': 0.0,
            'count_expected': 0,
            'count_received': 0,
            'count_pending': 0
        })
        
        for installment in relevant_installments:
            expected_date = installment['expected_date']
            
            if end_date and expected_date > end_date:
                continue
            
            if expected_date >= start_date:
                # Extrair ano-mês
                month_key = expected_date[:7]  # YYYY-MM
                
                monthly_flow[month_key]['month'] = month_key
                
                if installment['status'] == 'received':
                    monthly_flow[month_key]['received'] += installment['received_amount'] or 0
                    monthly_flow[month_key]['count_received'] += 1
                else:
                    monthly_flow[month_key]['pending'] += installment['net_amount']
                    monthly_flow[month_key]['count_pending'] += 1
                
                monthly_flow[month_key]['expected'] += installment['net_amount']
                monthly_flow[month_key]['count_expected'] += 1
        
        # Converter para lista e ordenar
        result = sorted(monthly_flow.values(), key=lambda x: x['month'])
        
        # Arredondar valores
        for item in result:
            item['expected'] = round(item['expected'], 2)
            item['received'] = round(item['received'], 2)
            item['pending'] = round(item['pending'], 2)
        
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
            
            if installment['status'] == 'received':
                status_summary[status]['total_amount'] += installment['received_amount'] or 0
            else:
                status_summary[status]['total_amount'] += installment['net_amount']
        
        # Arredondar valores
        for status in status_summary:
            status_summary[status]['total_amount'] = round(status_summary[status]['total_amount'], 2)
        
        return dict(status_summary)
    
    def get_overdue_installments(self):
        """Retorna parcelas atrasadas (pendentes com data passada)"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        overdue = [
            i for i in self.installments 
            if i['status'] == 'pending' and i['expected_date'] < today
        ]
        
        total_overdue = sum(i['net_amount'] for i in overdue)
        
        return {
            'count': len(overdue),
            'total_amount': round(total_overdue, 2),
            'installments': overdue
        }
    
    def get_upcoming_7_days(self):
        """Retorna parcelas dos próximos 7 dias"""
        today = datetime.now()
        end_date = (today + timedelta(days=7)).strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d')
        
        upcoming = [
            i for i in self.installments 
            if i['status'] == 'pending' and today_str <= i['expected_date'] <= end_date
        ]
        
        total_upcoming = sum(i['net_amount'] for i in upcoming)
        
        return {
            'count': len(upcoming),
            'total_amount': round(total_upcoming, 2),
            'installments': sorted(upcoming, key=lambda x: x['expected_date'])
        }
    
    def get_totals(self):
        """Retorna totais gerais"""
        total_expected = sum(
            i['net_amount'] for i in self.installments 
            if i['status'] in ['pending', 'received']
        )
        
        total_received = sum(
            i['received_amount'] for i in self.installments 
            if i['status'] == 'received' and i['received_amount']
        )
        
        total_pending = sum(
            i['net_amount'] for i in self.installments 
            if i['status'] == 'pending'
        )
        
        total_cancelled = sum(
            i['net_amount'] for i in self.installments 
            if 'cancelled' in i['status']
        )
        
        return {
            'total_expected': round(total_expected, 2),
            'total_received': round(total_received, 2),
            'total_pending': round(total_pending, 2),
            'total_cancelled': round(total_cancelled, 2),
            'count_total': len(self.installments),
            'count_received': len([i for i in self.installments if i['status'] == 'received']),
            'count_pending': len([i for i in self.installments if i['status'] == 'pending']),
            'count_cancelled': len([i for i in self.installments if 'cancelled' in i['status']])
        }