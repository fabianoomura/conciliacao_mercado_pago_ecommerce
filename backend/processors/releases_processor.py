import openpyxl
from datetime import datetime
import os

class ReleasesProcessor:
    """Processa arquivos de liberações/recebimentos do Mercado Pago"""
    
    def __init__(self):
        self.releases = []
        
    def process_files(self, directory='data/recebimentos'):
        """Processa todos os arquivos .xls e .xlsx na pasta de recebimentos"""
        if not os.path.exists(directory):
            raise Exception(f"Diretório não encontrado: {directory}")
        
        files = [f for f in os.listdir(directory) if f.endswith(('.xls', '.xlsx'))]
        
        if not files:
            raise Exception(f"Nenhum arquivo encontrado em {directory}")
        
        print(f"Encontrados {len(files)} arquivos de recebimentos")
        
        for filename in sorted(files):
            filepath = os.path.join(directory, filename)
            print(f"Processando: {filename}")
            self._process_file(filepath, filename)
        
        print(f"\nTotal de releases processadas: {len(self.releases)}")
        
        return self.releases
    
    def _process_file(self, filepath, filename):
        """Processa um arquivo individual de recebimentos"""
        try:
            workbook = openpyxl.load_workbook(filepath, data_only=True)
            sheet = workbook.active
            
            # Ler cabeçalhos (primeira linha)
            headers = []
            for cell in sheet[1]:
                headers.append(cell.value)
            
            # Mapear índices das colunas importantes
            col_map = self._map_columns(headers)
            
            # Processar cada linha (pular cabeçalho)
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    # Verificar se deve pular essa linha
                    if self._should_skip_row(row, col_map):
                        continue
                    
                    release = self._parse_release(row, col_map, filename)
                    
                    # Apenas processar releases de pagamento e operações relevantes
                    if release['record_type'] == 'release':
                        self.releases.append(release)
                        
                except Exception as e:
                    print(f"  ⚠️ Erro na linha {row_idx}: {str(e)}")
                    continue
            
            workbook.close()
            
        except Exception as e:
            print(f"  ❌ Erro ao processar arquivo {filename}: {str(e)}")
            raise
    
    def _map_columns(self, headers):
        """Mapeia os nomes das colunas para índices"""
        col_map = {}
        
        # Dicionário de mapeamento
        mapping = {
            'RELEASE_DATE': 'release_date',
            'SOURCE_ID': 'source_id',
            'EXTERNAL_REFERENCE': 'external_reference',
            'RECORD_TYPE': 'record_type',
            'DESCRIPTION': 'description',
            'NET_CREDIT_AMOUNT': 'net_credit_amount',
            'NET_DEBIT_AMOUNT': 'net_debit_amount',
            'GROSS_AMOUNT': 'gross_amount',
            'SELLER_AMOUNT': 'seller_amount',
            'MP_FEE_AMOUNT': 'mp_fee_amount',
            'FINANCING_FEE_AMOUNT': 'financing_fee_amount',
            'SHIPPING_FEE_AMOUNT': 'shipping_fee_amount',
            'TAXES_AMOUNT': 'taxes_amount',
            'COUPON_AMOUNT': 'coupon_amount',
            'INSTALLMENTS': 'installments',
            'PAYMENT_METHOD': 'payment_method',
            'APPROVAL_DATE': 'approval_date',
            'REFUND_ID': 'refund_id',
            'EFFECTIVE_COUPON_AMOUNT': 'effective_coupon_amount'
        }
        
        for idx, header in enumerate(headers):
            if header in mapping:
                col_map[mapping[header]] = idx
        
        return col_map
    
    def _should_skip_row(self, row, col_map):
        """Verifica se a linha deve ser ignorada"""
        # Pular linha se RECORD_TYPE (coluna D, índice 3) for 'initial_available_balance' ou 'total'
        if 'record_type' in col_map:
            record_type = row[col_map['record_type']]
            if record_type in ['initial_available_balance', 'total']:
                return True
        
        # Pular se SOURCE_ID estiver vazio
        if 'source_id' in col_map:
            source_id = row[col_map['source_id']]
            if not source_id or source_id == '':
                return True
        
        return False
    
    def _parse_release(self, row, col_map, filename):
        """Converte uma linha em um dicionário de release"""
        
        def get_value(key, default=None):
            if key in col_map:
                value = row[col_map[key]]
                return value if value is not None else default
            return default
        
        def parse_float(value):
            if value is None or value == '':
                return 0.0
            try:
                # Se for string, substituir vírgula por ponto
                if isinstance(value, str):
                    value = value.replace(',', '.')
                return float(value)
            except:
                return 0.0
        
        def parse_date(value):
            if not value:
                return None
            try:
                if isinstance(value, datetime):
                    return value.strftime('%Y-%m-%d %H:%M:%S')
                # Tentar parsear string com formato ISO
                if isinstance(value, str):
                    # Remover timezone se existir
                    value = value.split('.')[0].replace('T', ' ')
                    return value
                return str(value)
            except:
                return None
        
        release = {
            'release_date': parse_date(get_value('release_date')),
            'source_id': str(get_value('source_id', '')),
            'external_reference': str(get_value('external_reference', '')),
            'record_type': str(get_value('record_type', '')),
            'description': str(get_value('description', '')),
            'net_credit_amount': parse_float(get_value('net_credit_amount')),
            'net_debit_amount': parse_float(get_value('net_debit_amount')),
            'gross_amount': parse_float(get_value('gross_amount')),
            'seller_amount': parse_float(get_value('seller_amount')),
            'mp_fee_amount': parse_float(get_value('mp_fee_amount')),
            'financing_fee_amount': parse_float(get_value('financing_fee_amount')),
            'shipping_fee_amount': parse_float(get_value('shipping_fee_amount')),
            'taxes_amount': parse_float(get_value('taxes_amount')),
            'coupon_amount': parse_float(get_value('coupon_amount')),
            'installments': str(get_value('installments', '')),
            'payment_method': str(get_value('payment_method', '')),
            'approval_date': parse_date(get_value('approval_date')),
            'refund_id': str(get_value('refund_id', '')),
            'effective_coupon_amount': parse_float(get_value('effective_coupon_amount')),
            'file_source': filename
        }
        
        return release
    
    def get_summary(self):
        """Retorna resumo das releases processadas"""
        if not self.releases:
            return None
        
        # Filtrar apenas pagamentos efetivos (não reservas)
        payments = [r for r in self.releases if r['description'] == 'payment']
        refunds = [r for r in self.releases if r['description'] == 'refund']
        chargebacks = [r for r in self.releases if r['description'] == 'chargeback']
        
        total_credit = sum(r['net_credit_amount'] for r in payments)
        total_debit = sum(r['net_debit_amount'] for r in refunds + chargebacks)
        
        description_count = {}
        for r in self.releases:
            desc = r['description']
            description_count[desc] = description_count.get(desc, 0) + 1
        
        return {
            'total_releases': len(self.releases),
            'total_payments': len(payments),
            'total_refunds': len(refunds),
            'total_chargebacks': len(chargebacks),
            'total_credit': round(total_credit, 2),
            'total_debit': round(total_debit, 2),
            'net_amount': round(total_credit - total_debit, 2),
            'description_breakdown': description_count
        }