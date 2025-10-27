"""
Releases Processor V2 - VERSÃO MELHORADA
Processa arquivos de recebimentos do Mercado Pago
Separa payments de movimentações internas
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

class ReleasesProcessorV2:
    def __init__(self):
        self.releases = []
        self.payments_only = []
        self.movements = []
        
    def process_files(self, directory):
        """Processa todos os arquivos de recebimentos"""
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"⚠️  Diretório não encontrado: {directory}")
            return []
        
        all_releases = []
        files = list(directory_path.glob('*.*'))
        files = [f for f in files if f.suffix.lower() in ['.xls', '.xlsx', '.csv']]
        
        print(f"\n📂 Processando {len(files)} arquivo(s) de recebimentos...")
        
        for file_path in sorted(files):
            try:
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                releases = self._process_releases_file(df, file_path.name)
                all_releases.extend(releases)
                print(f"   ✓ {file_path.name}: {len(releases)} releases")
            except Exception as e:
                print(f"   ❌ Erro ao processar {file_path.name}: {str(e)}")
        
        self.releases = all_releases
        self._categorize_releases()
        
        print(f"\n📊 Resumo do processamento:")
        print(f"   Total de releases: {len(all_releases)}")
        print(f"   Payments (vendas): {len(self.payments_only)}")
        print(f"   Movimentações: {len(self.movements)}")
        
        return all_releases
    
    def _process_releases_file(self, df, filename):
        """Processa um arquivo de recebimentos"""
        releases = []
        
        for idx, row in df.iterrows():
            try:
                description = str(row.get('DESCRIPTION', '')).strip().lower()
                
                release = {
                    'release_date': self._parse_date(row.get('RELEASE_DATE')),
                    'source_id': str(row.get('SOURCE_ID', '')),
                    'external_reference': str(row.get('EXTERNAL_REFERENCE', '')),
                    'record_type': str(row.get('RECORD_TYPE', '')).strip().lower(),
                    'description': description,
                    'net_credit_amount': self._parse_float(row.get('NET_CREDIT_AMOUNT', 0)),
                    'net_debit_amount': self._parse_float(row.get('NET_DEBIT_AMOUNT', 0)),
                    'gross_amount': self._parse_float(row.get('GROSS_AMOUNT', 0)),
                    'mp_fee': self._parse_float(row.get('MP_FEE_AMOUNT', 0)),
                    'financing_fee': self._parse_float(row.get('FINANCING_FEE_AMOUNT', 0)),
                    'installments': str(row.get('INSTALLMENTS', '1')),
                    'payment_method': str(row.get('PAYMENT_METHOD', '')),
                    'approval_date': self._parse_date(row.get('APPROVAL_DATE')),
                    'refund_id': str(row.get('REFUND_ID', '')),
                    'currency': str(row.get('CURRENCY', 'BRL')),
                    'file_source': filename
                }
                
                releases.append(release)
                
            except Exception as e:
                print(f"      ⚠️  Erro na linha {idx}: {str(e)}")
                continue
        
        return releases
    
    def _categorize_releases(self):
        """Separa payments de movimentações internas"""
        self.payments_only = []
        self.movements = []
        
        # Lista de movimentações internas que NÃO geram parcelas
        internal_movements = [
            'reserve_for_debt_payment',
            'fee-release_in_advance',
            'release_in_advance',
            'reserve_for_payout',
            'payout',
            'chargeback',
            'chargeback_cancel',
            'reserve_for_chargeback',
            'refund'
        ]
        
        for release in self.releases:
            desc = release['description']
            
            if desc == 'payment':
                # APENAS payments geram parcelas!
                self.payments_only.append(release)
            elif desc in internal_movements or desc.startswith('reserve_') or desc.startswith('fee-'):
                # Movimentações internas - NÃO geram parcelas
                self.movements.append(release)
            else:
                # Desconhecido - logar para investigação
                print(f"      ⚠️  Descrição desconhecida: {desc}")
                self.movements.append(release)
    
    def get_payments_only(self):
        """Retorna APENAS os payments (para conciliação)"""
        return self.payments_only
    
    def get_movements(self):
        """Retorna movimentações internas"""
        return self.movements
    
    def get_summary(self):
        """Retorna resumo dos recebimentos"""
        total_received = sum(r['net_credit_amount'] for r in self.payments_only)
        total_payments = len(self.payments_only)
        
        # Movimentações por tipo
        movements_by_type = {}
        for mov in self.movements:
            desc = mov['description']
            if desc not in movements_by_type:
                movements_by_type[desc] = {
                    'count': 0,
                    'total_credit': 0,
                    'total_debit': 0
                }
            movements_by_type[desc]['count'] += 1
            movements_by_type[desc]['total_credit'] += mov['net_credit_amount']
            movements_by_type[desc]['total_debit'] += mov['net_debit_amount']
        
        return {
            'total_releases': len(self.releases),
            'total_payments': total_payments,
            'total_received': round(total_received, 2),
            'total_movements': len(self.movements),
            'movements_by_type': movements_by_type
        }
    
    def get_advance_fees(self):
        """Retorna taxas de antecipação"""
        advance_fees = [
            m for m in self.movements 
            if 'advance' in m['description'] and 'fee' in m['description']
        ]
        
        total_fees = sum(m['net_debit_amount'] for m in advance_fees)
        
        return {
            'count': len(advance_fees),
            'total_amount': round(total_fees, 2),
            'fees': advance_fees
        }
    
    def get_payouts(self):
        """Retorna saques"""
        payouts = [m for m in self.movements if m['description'] == 'payout']
        total_payouts = sum(abs(m['net_debit_amount']) for m in payouts)
        
        return {
            'count': len(payouts),
            'total_amount': round(total_payouts, 2),
            'payouts': payouts
        }
    
    def get_chargebacks(self):
        """Retorna chargebacks"""
        chargebacks = [m for m in self.movements if 'chargeback' in m['description']]
        
        chargeback_applied = sum(
            abs(m['net_debit_amount']) 
            for m in chargebacks 
            if m['description'] == 'chargeback'
        )
        
        chargeback_reversed = sum(
            m['net_credit_amount'] 
            for m in chargebacks 
            if m['description'] == 'chargeback_cancel'
        )
        
        return {
            'count': len(chargebacks),
            'chargeback_applied': round(chargeback_applied, 2),
            'chargeback_reversed': round(chargeback_reversed, 2),
            'net_chargeback': round(chargeback_applied - chargeback_reversed, 2),
            'chargebacks': chargebacks
        }
    
    def _parse_date(self, date_value):
        """Converte valor para data ISO"""
        if pd.isna(date_value):
            return None
        
        if isinstance(date_value, str):
            try:
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
                value = value.strip().replace(',', '.')
                return float(value)
            except:
                return 0.0
        
        return 0.0