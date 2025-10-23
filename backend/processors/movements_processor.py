"""
Processador de Movimentações do Mercado Pago
Processa reserve_for_debt_payment, fee-release_in_advance, reserve_for_payout e payout
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

class MovementsProcessor:
    def __init__(self):
        self.movements = []
        self.payouts = []
        self.advance_fees = []
        self.reserves = []
        
    def process_files(self, directory):
        """Processa todos os arquivos de recebimentos incluindo movimentações"""
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"⚠️  Diretório não encontrado: {directory}")
            return []
        
        all_movements = []
        files = list(directory_path.glob('*.xls*'))
        
        print(f"\n📂 Processando movimentações de {len(files)} arquivo(s)...")
        
        for file_path in files:
            try:
                df = pd.read_excel(file_path)
                movements = self._process_movements_file(df, file_path.name)
                all_movements.extend(movements)
                print(f"   ✓ {file_path.name}: {len(movements)} movimentações")
            except Exception as e:
                print(f"   ❌ Erro ao processar {file_path.name}: {str(e)}")
        
        self.movements = all_movements
        self._categorize_movements()
        
        return all_movements
    
    def _process_movements_file(self, df, filename):
        """Processa um arquivo de movimentações"""
        movements = []
        
        for idx, row in df.iterrows():
            try:
                # Pular linhas que são payments normais (já processadas)
                record_type = str(row.get('RECORD_TYPE', '')).strip().lower()
                description = str(row.get('DESCRIPTION', '')).strip().lower()
                
                # Só processar movimentações especiais
                if description not in ['reserve_for_debt_payment', 'fee-release_in_advance', 
                                       'reserve_for_payout', 'payout']:
                    continue
                
                movement = {
                    'release_date': self._parse_date(row.get('RELEASE_DATE')),
                    'source_id': str(row.get('SOURCE_ID', '')),
                    'external_reference': str(row.get('EXTERNAL_REFERENCE', '')),
                    'record_type': record_type,
                    'description': description,
                    'net_credit': self._parse_float(row.get('NET_CREDIT_AMOUNT', 0)),
                    'net_debit': self._parse_float(row.get('NET_DEBIT_AMOUNT', 0)),
                    'gross_amount': self._parse_float(row.get('GROSS_AMOUNT', 0)),
                    'mp_fee': self._parse_float(row.get('MP_FEE_AMOUNT', 0)),
                    'financing_fee': self._parse_float(row.get('FINANCING_FEE_AMOUNT', 0)),
                    'payment_method': str(row.get('PAYMENT_METHOD', '')),
                    'approval_date': self._parse_date(row.get('APPROVAL_DATE')),
                    'currency': str(row.get('CURRENCY', 'BRL')),
                    'file_source': filename
                }
                
                movements.append(movement)
                
            except Exception as e:
                print(f"      ⚠️  Erro na linha {idx}: {str(e)}")
                continue
        
        return movements
    
    def _categorize_movements(self):
        """Categoriza as movimentações por tipo"""
        self.payouts = []
        self.advance_fees = []
        self.reserves = []
        
        for mov in self.movements:
            desc = mov['description']
            
            if desc == 'payout':
                self.payouts.append(mov)
            elif desc == 'fee-release_in_advance':
                self.advance_fees.append(mov)
            elif desc == 'reserve_for_debt_payment' or desc == 'reserve_for_payout':
                self.reserves.append(mov)
    
    def get_payouts_summary(self):
        """Retorna resumo dos saques"""
        if not self.payouts:
            return {
                'total_payouts': 0,
                'total_amount': 0,
                'payouts': []
            }
        
        payouts_list = []
        total_amount = 0
        
        for payout in self.payouts:
            amount = abs(payout['net_debit'])
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
            'total_payouts': len(payouts_list),
            'total_amount': total_amount,
            'payouts': payouts_list
        }
    
    def get_advance_fees_summary(self):
        """Retorna resumo das taxas de antecipação"""
        if not self.advance_fees:
            return {
                'total_fees': 0,
                'total_amount': 0,
                'fees': []
            }
        
        fees_list = []
        total_amount = 0
        
        for fee in self.advance_fees:
            amount = abs(fee['mp_fee'])
            total_amount += amount
            
            fees_list.append({
                'date': fee['release_date'],
                'source_id': fee['source_id'],
                'amount': amount,
                'gross_amount': fee['gross_amount']
            })
        
        # Ordenar por data
        fees_list.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            'total_fees': len(fees_list),
            'total_amount': total_amount,
            'fees': fees_list
        }
    
    def get_reserves_summary(self):
        """Retorna resumo das reservas"""
        # Agrupar reservas por source_id para ver o fluxo completo
        reserves_by_source = {}
        
        for reserve in self.reserves:
            source_id = reserve['source_id']
            
            if source_id not in reserves_by_source:
                reserves_by_source[source_id] = {
                    'source_id': source_id,
                    'description': reserve['description'],
                    'credits': 0,
                    'debits': 0,
                    'net': 0,
                    'last_date': reserve['release_date'],
                    'transactions': []
                }
            
            reserves_by_source[source_id]['credits'] += reserve['net_credit']
            reserves_by_source[source_id]['debits'] += reserve['net_debit']
            reserves_by_source[source_id]['net'] = (
                reserves_by_source[source_id]['credits'] - 
                abs(reserves_by_source[source_id]['debits'])
            )
            reserves_by_source[source_id]['transactions'].append({
                'date': reserve['release_date'],
                'credit': reserve['net_credit'],
                'debit': reserve['net_debit'],
                'type': reserve['description']
            })
        
        reserves_list = list(reserves_by_source.values())
        reserves_list.sort(key=lambda x: x['last_date'], reverse=True)
        
        return {
            'total_sources': len(reserves_list),
            'reserves': reserves_list
        }
    
    def get_full_reconciliation(self):
        """Retorna conciliação completa com todas as movimentações"""
        payouts_summary = self.get_payouts_summary()
        fees_summary = self.get_advance_fees_summary()
        reserves_summary = self.get_reserves_summary()
        
        return {
            'payouts': payouts_summary,
            'advance_fees': fees_summary,
            'reserves': reserves_summary,
            'total_movements': len(self.movements),
            'summary': {
                'total_payouts': payouts_summary['total_amount'],
                'total_fees': fees_summary['total_amount'],
                'net_transferred': payouts_summary['total_amount'] - fees_summary['total_amount']
            }
        }
    
    def validate_against_releases(self, releases):
        """Valida movimentações contra os releases normais"""
        # Calcular total recebido de vendas
        total_received = sum(r.get('net_credit_amount', 0) for r in releases 
                            if r.get('description') == 'payment')
        
        # Calcular total sacado
        payouts = self.get_payouts_summary()
        total_withdrawn = payouts['total_amount']
        
        # Calcular taxas
        fees = self.get_advance_fees_summary()
        total_fees = fees['total_amount']
        
        # Saldo esperado no MP
        expected_balance = total_received - total_withdrawn - total_fees
        
        return {
            'total_received': total_received,
            'total_withdrawn': total_withdrawn,
            'total_fees': total_fees,
            'expected_balance': expected_balance,
            'validation': {
                'is_valid': expected_balance >= 0,
                'difference': expected_balance
            }
        }
    
    def _parse_date(self, date_value):
        """Converte valor para data"""
        if pd.isna(date_value):
            return None
        
        if isinstance(date_value, str):
            try:
                # Formato ISO
                return datetime.fromisoformat(date_value.replace('Z', '+00:00')).date().isoformat()
            except:
                return None
        
        if isinstance(date_value, datetime):
            return date_value.date().isoformat()
        
        return None
    
    def _parse_float(self, value):
        """Converte valor para float"""
        if pd.isna(value):
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            try:
                # Remover espaços e trocar vírgula por ponto
                value = value.strip().replace(',', '.')
                return float(value)
            except:
                return 0.0
        
        return 0.0
    
    def get_summary(self):
        """Retorna resumo geral"""
        payouts = self.get_payouts_summary()
        fees = self.get_advance_fees_summary()
        
        return {
            'total_movements': len(self.movements),
            'total_payouts': payouts['total_payouts'],
            'total_payout_amount': payouts['total_amount'],
            'total_advance_fees': fees['total_fees'],
            'total_fees_amount': fees['total_amount'],
            'net_amount': payouts['total_amount'] - fees['total_amount']
        }