import openpyxl
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
import re
import xml.etree.ElementTree as ET

class SalesProcessor:
    """Processa arquivos de vendas do Mercado Pago"""
    
    def __init__(self):
        self.transactions = []
        self.installments = []
        
    def process_files(self, directory='data/vendas'):
        """Processa todos os arquivos .xls e .xlsx na pasta de vendas"""
        if not os.path.exists(directory):
            raise Exception(f"Diretório não encontrado: {directory}")
        
        files = [f for f in os.listdir(directory) if f.endswith(('.xls', '.xlsx'))]
        
        if not files:
            raise Exception(f"Nenhum arquivo encontrado em {directory}")
        
        print(f"Encontrados {len(files)} arquivos de vendas")
        
        for filename in sorted(files):
            filepath = os.path.join(directory, filename)
            print(f"Processando: {filename}")
            self._process_file(filepath, filename)
        
        print(f"\nTotal de transações processadas: {len(self.transactions)}")
        print(f"Total de parcelas geradas: {len(self.installments)}")
        
        return {
            'transactions': self.transactions,
            'installments': self.installments
        }
    
    def _process_file(self, filepath, filename):
        """Processa um arquivo individual de vendas"""
        try:
            # Tentar detectar o tipo de arquivo lendo os primeiros bytes
            with open(filepath, 'rb') as f:
                header = f.read(8)
            
            # Verificar se é XML (Excel 2003)
            if header.startswith(b'<?xml') or header.startswith(b'\xef\xbb\xbf<?xml'):
                print(f"  ℹ️ Detectado formato Excel 2003 XML")
                self._process_xml_file(filepath, filename)
            else:
                # Tentar como xlsx/xls binário
                try:
                    workbook = openpyxl.load_workbook(filepath, data_only=True)
                    self._process_xlsx_file(workbook, filename)
                    workbook.close()
                except:
                    # Última tentativa: usar pandas (lê quase tudo)
                    print(f"  ℹ️ Tentando com pandas...")
                    self._process_with_pandas(filepath, filename)
            
        except Exception as e:
            print(f"  ❌ Erro ao processar arquivo {filename}: {str(e)}")
            raise

    def _process_xlsx_file(self, workbook, filename):
        """Processa arquivo XLSX usando openpyxl"""
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
                transaction = self._parse_transaction(row, col_map, filename)
                
                # Filtrar apenas status válidos
                if transaction['status'] in ['approved', 'charged_back', 'refunded']:
                    self.transactions.append(transaction)
                    
                    # Gerar parcelas futuras
                    installments = self._generate_installments(transaction)
                    self.installments.extend(installments)
                    
            except Exception as e:
                print(f"  ⚠️ Erro na linha {row_idx}: {str(e)}")
                continue

    def _process_xml_file(self, filepath, filename):
        """Processa arquivo XML (Excel 2003) usando pandas"""
        import pandas as pd
        
        try:
            # Ler XML do Excel 2003 - NÃO usar engine, deixar pandas detectar
            # Pandas detecta automaticamente XML do Excel
            df = pd.read_excel(filepath, engine=None)
        except:
            try:
                # Alternativa: forçar leitura como HTML (Excel 2003 XML é similar)
                import xml.etree.ElementTree as ET
                import pandas as pd
                
                # Parse XML manualmente
                tree = ET.parse(filepath)
                root = tree.getroot()
                
                # Namespace do Excel XML
                ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
                
                # Encontrar todas as linhas
                rows_data = []
                worksheet = root.find('.//ss:Worksheet', ns)
                if worksheet is not None:
                    table = worksheet.find('.//ss:Table', ns)
                    if table is not None:
                        rows = table.findall('.//ss:Row', ns)
                        
                        for row in rows:
                            cells = row.findall('.//ss:Cell', ns)
                            row_data = []
                            for cell in cells:
                                data = cell.find('.//ss:Data', ns)
                                if data is not None and data.text:
                                    row_data.append(data.text)
                                else:
                                    row_data.append('')
                            if row_data:
                                rows_data.append(row_data)
                
                if not rows_data:
                    raise Exception("Não foi possível ler dados do XML")
                
                # Primeira linha são os headers
                headers = rows_data[0]
                data_rows = rows_data[1:]
                
                df = pd.DataFrame(data_rows, columns=headers)
            except Exception as e:
                print(f"  ⚠️ Erro ao ler XML: {str(e)}")
                raise
        
        # Processar DataFrame
        headers = df.columns.tolist()
        col_map = self._map_columns(headers)
        
        # Processar cada linha
        for idx, row in df.iterrows():
            try:
                row_list = row.tolist()
                transaction = self._parse_transaction(row_list, col_map, filename)
                
                if transaction['status'] in ['approved', 'charged_back', 'refunded']:
                    self.transactions.append(transaction)
                    installments = self._generate_installments(transaction)
                    self.installments.extend(installments)
                    
            except Exception as e:
                print(f"  ⚠️ Erro na linha {idx + 2}: {str(e)}")
                continue

    def _process_with_pandas(self, filepath, filename):
        """Processa arquivo usando pandas (aceita vários formatos)"""
        import pandas as pd
        
        try:
            # Tentar ler como Excel
            df = pd.read_excel(filepath)
        except:
            # Tentar ler como CSV
            df = pd.read_csv(filepath, sep='\t')
        
        # Converter para lista de listas
        headers = df.columns.tolist()
        col_map = self._map_columns(headers)
        
        # Processar cada linha
        for idx, row in df.iterrows():
            try:
                row_list = row.tolist()
                transaction = self._parse_transaction(row_list, col_map, filename)
                
                if transaction['status'] in ['approved', 'charged_back', 'refunded']:
                    self.transactions.append(transaction)
                    installments = self._generate_installments(transaction)
                    self.installments.extend(installments)
                    
            except Exception as e:
                print(f"  ⚠️ Erro na linha {idx + 2}: {str(e)}")
                continue
    
    def _map_columns(self, headers):
        """Mapeia os nomes das colunas para índices"""
        col_map = {}
        
        # Dicionário de mapeamento (nome da coluna -> chave)
        mapping = {
            'Data da compra (date_created)': 'date_created',
            'Data de creditação (date_approved)': 'date_approved',
            'Data de liberação do dinheiro (date_released)': 'date_released',
            'Código de referência (external_reference)': 'external_reference',
            'Número da transação do Mercado Pago (operation_id)': 'operation_id',
            'Status da operação (status)': 'status',
            'Detalhe do status da operação (status_detail)': 'status_detail',
            'Tipo de operação (operation_type)': 'operation_type',
            'Valor do produto (transaction_amount)': 'transaction_amount',
            'Tarifa do Mercado Pago (mercadopago_fee)': 'mercadopago_fee',
            'Tarifa pelo uso da plataforma de terceiros (marketplace_fee)': 'marketplace_fee',
            'Frete (shipping_cost)': 'shipping_cost',
            'Desconto para a sua contraparte (coupon_fee)': 'coupon_fee',
            'Valor total recebido (net_received_amount)': 'net_received_amount',
            'Parcelas (installments)': 'installments',
            'Meio de pagamento (payment_type)': 'payment_type',
            'Valor devolvido (amount_refunded)': 'amount_refunded',
            'Operador que devolveu o dinheiro (refund_operator)': 'refund_operator',
            'Número da reclamação (claim_id)': 'claim_id',
            'Número da contestação (chargeback_id)': 'chargeback_id',
            'Plataforma (marketplace)': 'marketplace',
            'Custos de parcelamento (financing_fee)': 'financing_fee'
        }
        
        for idx, header in enumerate(headers):
            if header in mapping:
                col_map[mapping[header]] = idx
        
        return col_map
    
    def _parse_transaction(self, row, col_map, filename):
        """Converte uma linha em um dicionário de transação"""
        
        def get_value(key, default=None):
            if key in col_map:
                value = row[col_map[key]]
                return value if value is not None else default
            return default
        
        def parse_float(value):
            if value is None or value == '':
                return 0.0
            try:
                return float(str(value).replace(',', '.'))
            except:
                return 0.0
        
        def parse_int(value):
            if value is None or value == '':
                return 1
            try:
                return int(value)
            except:
                return 1
        
        def parse_date(value):
            if not value:
                return None
            try:
                if isinstance(value, datetime):
                    return value.strftime('%Y-%m-%d %H:%M:%S')
                return str(value)
            except:
                return None
        
        transaction = {
            'operation_id': str(get_value('operation_id', '')),
            'external_reference': str(get_value('external_reference', '')),
            'date_created': parse_date(get_value('date_created')),
            'date_approved': parse_date(get_value('date_approved')),
            'date_released': parse_date(get_value('date_released')),
            'status': str(get_value('status', '')),
            'status_detail': str(get_value('status_detail', '')),
            'operation_type': str(get_value('operation_type', '')),
            'transaction_amount': parse_float(get_value('transaction_amount')),
            'mercadopago_fee': parse_float(get_value('mercadopago_fee')),
            'marketplace_fee': parse_float(get_value('marketplace_fee')),
            'shipping_cost': parse_float(get_value('shipping_cost')),
            'coupon_fee': parse_float(get_value('coupon_fee')),
            'net_received_amount': parse_float(get_value('net_received_amount')),
            'installments': parse_int(get_value('installments')),
            'payment_type': str(get_value('payment_type', '')),
            'amount_refunded': parse_float(get_value('amount_refunded')),
            'refund_operator': str(get_value('refund_operator', '')),
            'claim_id': str(get_value('claim_id', '')),
            'chargeback_id': str(get_value('chargeback_id', '')),
            'marketplace': str(get_value('marketplace', '')),
            'financing_fee': parse_float(get_value('financing_fee')),
            'file_source': filename
        }
        
        return transaction
    
    def _generate_installments(self, transaction):
        """Gera parcelas futuras para uma transação"""
        installments = []
        
        operation_id = transaction['operation_id']
        total_installments = transaction['installments']
        date_approved = transaction['date_approved']
        
        if not date_approved:
            return installments
        
        # Calcular valores por parcela
        gross_per_installment = transaction['transaction_amount'] / total_installments
        net_per_installment = transaction['net_received_amount'] / total_installments
        fee_per_installment = abs(transaction['mercadopago_fee']) / total_installments
        
        # Parsear data de aprovação
        try:
            if isinstance(date_approved, str):
                # Tentar diferentes formatos
                for fmt in ['%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y']:
                    try:
                        approval_date = datetime.strptime(date_approved.split('.')[0], fmt)
                        break
                    except:
                        continue
            else:
                approval_date = date_approved
        except:
            print(f"  ⚠️ Erro ao parsear data de aprovação: {date_approved}")
            return installments
        
        # Gerar cada parcela
        for i in range(1, total_installments + 1):
            # Calcular data esperada (data de aprovação + N meses)
            # Parcela 1: aprovação + 1 mês
            # Parcela 2: aprovação + 2 meses
            # Parcela 3: aprovação + 3 meses
            expected_date = approval_date + relativedelta(months=i)
            
            # Determinar status inicial
            status = 'pending'
            
            # Se for refunded ou charged_back com settled, cancelar parcelas futuras
            if transaction['status'] == 'refunded':
                status = 'cancelled'
            elif transaction['status'] == 'charged_back' and transaction['status_detail'] == 'settled':
                status = 'cancelled'
            
            installment = {
                'operation_id': operation_id,
                'installment_number': i,
                'total_installments': total_installments,
                'installment_label': f"{i}/{total_installments}",
                'expected_date': expected_date.strftime('%Y-%m-%d'),
                'gross_amount': round(gross_per_installment, 2),
                'fee_amount': round(fee_per_installment, 2),
                'net_amount': round(net_per_installment, 2),
                'status': status,
                'received_date': None,
                'received_amount': None,
                'difference': None
            }
            
            installments.append(installment)
        
        return installments
    
    def get_summary(self):
        """Retorna resumo das transações processadas"""
        if not self.transactions:
            return None
        
        total_amount = sum(t['transaction_amount'] for t in self.transactions)
        total_fees = sum(abs(t['mercadopago_fee']) for t in self.transactions)
        total_net = sum(t['net_received_amount'] for t in self.transactions)
        
        status_count = {}
        for t in self.transactions:
            status = t['status']
            status_count[status] = status_count.get(status, 0) + 1
        
        return {
            'total_transactions': len(self.transactions),
            'total_amount': round(total_amount, 2),
            'total_fees': round(total_fees, 2),
            'total_net': round(total_net, 2),
            'status_breakdown': status_count,
            'total_installments': len(self.installments),
            'pending_installments': len([i for i in self.installments if i['status'] == 'pending'])
        }