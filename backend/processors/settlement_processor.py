"""
Settlement Processor V3 - VERSÃO COMPLETA
Processa Settlement Reports do Mercado Pago com:
- Suporte a estornos parciais e totais (REFUND)
- Suporte a chargebacks e reversões (CHARGEBACK/CHARGEBACK_CANCEL)
- Distribuição proporcional de ajustes nas parcelas
- Controle de saldo por pedido
- Detecção de tipos de pagamento (PIX, Boleto, Cartão, etc)
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from collections import defaultdict

class SettlementProcessorV3:
    def __init__(self):
        self.transactions = []
        self.installments = []
        self.order_balances = {}
        self.payment_types = {}
        
    def process_files(self, directory):
        """Processa todos os arquivos de settlement"""
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"  Diretório não encontrado: {directory}")
            return []
        
        all_data = []
        files = list(directory_path.glob('*.*'))
        files = [f for f in files if f.suffix.lower() in ['.xls', '.xlsx', '.csv']]
        
        print(f"\nProcessando {len(files)} arquivo(s) de settlement...")
        
        for file_path in sorted(files):
            try:
                if file_path.suffix.lower() == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                data = self._process_settlement_file(df, file_path.name)
                all_data.extend(data)
                print(f"    {file_path.name}: {len(data)} linhas")
            except Exception as e:
                print(f"    Erro ao processar {file_path.name}: {str(e)}")
        
        self.transactions = all_data
        self._process_orders()
        
        print(f"\nProcessamento concluído:")
        print(f"   Total de transações: {len(self.transactions)}")
        print(f"   Total de pedidos: {len(self.order_balances)}")
        print(f"   Total de parcelas: {len(self.installments)}")
        
        return all_data
    
    def _process_settlement_file(self, df, filename):
        """Processa um arquivo de settlement"""
        data = []
        
        for idx, row in df.iterrows():
            try:
                transaction = {
                    'external_reference': str(row.get('EXTERNAL_REFERENCE', '')),
                    'source_id': str(row.get('SOURCE_ID', '')),
                    'user_id': str(row.get('USER_ID', '')),
                    'payment_method_type': str(row.get('PAYMENT_METHOD_TYPE', '')),
                    'payment_method': str(row.get('PAYMENT_METHOD', '')),
                    'transaction_type': str(row.get('TRANSACTION_TYPE', '')),
                    'description': str(row.get('DESCRIPTION', '')),
                    'transaction_amount': self._parse_float(row.get('TRANSACTION_AMOUNT', 0)),
                    'fee_amount': self._parse_float(row.get('FEE_AMOUNT', 0)),
                    'settlement_net_amount': self._parse_float(row.get('SETTLEMENT_NET_AMOUNT', 0)),
                    'installments': int(row.get('INSTALLMENTS', 1)) if pd.notna(row.get('INSTALLMENTS')) else 1,
                    'installment_number': str(row.get('INSTALLMENT_NUMBER', '')),
                    'installment_net_amount': self._parse_float(row.get('INSTALLMENT_NET_AMOUNT', 0)),
                    'approval_date': self._parse_date(row.get('APPROVAL_DATE')),
                    'money_release_date': self._parse_date(row.get('MONEY_RELEASE_DATE')),
                    'refund_id': str(row.get('REFUND_ID', '')),
                    'currency': str(row.get('CURRENCY', 'BRL')),
                    'file_source': filename
                }
                
                data.append(transaction)
                
            except Exception as e:
                print(f"        Erro na linha {idx}: {str(e)}")
                continue
        
        return data
    
    def _process_orders(self):
        """Processa pedidos agrupando transações e gerando parcelas"""
        print("\nProcessando pedidos e gerando parcelas...")
        
        # Agrupar por EXTERNAL_REFERENCE
        orders = defaultdict(list)
        for trans in self.transactions:
            ref = trans['external_reference']
            if ref and ref != 'nan':
                orders[ref].append(trans)
        
        # Processar cada pedido
        for ref, transactions in orders.items():
            self._process_single_order(ref, transactions)
        
        print(f"    {len(orders)} pedidos processados")
        print(f"    {len(self.installments)} parcelas geradas")
    
    def _process_single_order(self, external_ref, transactions):
        """Processa um pedido individual"""

        # Separar por tipo de transação
        settlement = None
        refunds = []
        chargebacks = []
        chargeback_cancels = []
        installment_lines = []

        for trans in transactions:
            trans_type = trans['transaction_type']
            description = trans['description']

            if trans_type == 'SETTLEMENT' and description != 'INSTALLMENT':
                settlement = trans
            elif trans_type == 'REFUND':
                refunds.append(trans)
            elif trans_type == 'CHARGEBACK':
                chargebacks.append(trans)
            elif trans_type == 'CHARGEBACK_CANCEL':
                chargeback_cancels.append(trans)
            elif description == 'INSTALLMENT':
                installment_lines.append(trans)

        if not settlement:
            return

        # Identificar tipo de pagamento
        payment_type = self._identify_payment_type(settlement)
        self.payment_types[external_ref] = payment_type

        # Calcular valores
        total_gross = settlement['transaction_amount']
        total_net = settlement['settlement_net_amount']
        total_refunded = sum(r['settlement_net_amount'] for r in refunds)
        total_chargeback = sum(c['settlement_net_amount'] for c in chargebacks)
        total_chargeback_cancel = sum(c['settlement_net_amount'] for c in chargeback_cancels)

        # Saldo final considerando estornos e chargebacks
        final_net = total_net + total_refunded + total_chargeback + total_chargeback_cancel

        # Salvar saldo do pedido
        self.order_balances[external_ref] = {
            'transaction_date': settlement['approval_date'],
            'payment_method': settlement['payment_method'],
            'payment_type': payment_type,
            'total_gross': total_gross,
            'total_net': total_net,
            'total_fee': settlement['fee_amount'],
            'refunded': abs(total_refunded),
            'chargeback': abs(total_chargeback),
            'chargeback_reversed': abs(total_chargeback_cancel),
            'final_net': final_net,
            'installments': settlement['installments'],
            'has_refund': len(refunds) > 0,
            'has_chargeback': len(chargebacks) > 0,
            'has_chargeback_cancel': len(chargeback_cancels) > 0
        }

        # Gerar parcelas
        # Verificar se há linhas INSTALLMENT (linhas com DESCRIPTION = 'INSTALLMENT')
        if installment_lines:
            # Caso 1: Parcelas já vêm separadas no settlement com linhas INSTALLMENT
            # Cada linha tem INSTALLMENT_NUMBER (ex: 1/6, 2/6) e INSTALLMENT_NET_AMOUNT
            self._create_installments_from_lines(
                external_ref,
                settlement,
                installment_lines,
                total_refunded,
                total_chargeback,
                total_chargeback_cancel
            )
        else:
            # Caso 2: Pagamento sem linhas INSTALLMENT separadas
            # Pode ser: PIX, Boleto, Saldo MP, Crédito ML, ou single installment
            # Neste caso, criar uma única parcela (1/1)
            self._create_single_installment(
                external_ref,
                settlement,
                total_refunded,
                total_chargeback,
                total_chargeback_cancel
            )
    
    def _create_installments_from_lines(self, external_ref, settlement, installment_lines,
                                       total_refunded, total_chargeback, total_chargeback_cancel):
        """Cria parcelas a partir das linhas INSTALLMENT do settlement

        IMPORTANTE: NÃO distribuir refund/chargeback aqui!
        O reconciliador fará isso baseado em quais parcelas foram realmente recebidas.
        Aqui apenas guardar o valor original de cada parcela.
        """

        num_installments = len(installment_lines)

        for inst_line in installment_lines:
            original_amount = inst_line['installment_net_amount']

            # NÃO aplicar ajustes aqui - manter valor original
            # O reconciliador distribuirá refund/chargeback apenas nas parcelas não recebidas
            adjusted_amount = original_amount

            installment = {
                'external_reference': external_ref,
                'source_id': settlement['source_id'],
                'payment_method': settlement['payment_method'],
                'payment_type': self.payment_types.get(external_ref, 'unknown'),
                'installment_number': inst_line['installment_number'],
                'total_installments': num_installments,
                'installment_net_amount_original': original_amount,
                'installment_net_amount': adjusted_amount,  # Sem ajustes por enquanto
                'money_release_date': inst_line['money_release_date'],
                'approval_date': settlement['approval_date'],
                'refund_applied': 0,  # Será calculado no reconciliador
                'chargeback_applied': 0,  # Será calculado no reconciliador
                'chargeback_cancel_applied': 0,  # Será calculado no reconciliador
                'has_adjustment': False,  # Será atualizado no reconciliador
                'status': 'pending',
                'received_amount': 0,
                'received_date': None,
                'currency': settlement['currency']
            }

            self.installments.append(installment)
    
    def _create_single_installment(self, external_ref, settlement, 
                                  total_refunded, total_chargeback, total_chargeback_cancel):
        """Cria uma única parcela (pagamento à vista)"""
        
        original_amount = settlement['settlement_net_amount']
        adjusted_amount = (
            original_amount + 
            total_refunded + 
            total_chargeback +
            total_chargeback_cancel
        )
        
        installment = {
            'external_reference': external_ref,
            'source_id': settlement['source_id'],
            'payment_method': settlement['payment_method'],
            'payment_type': self.payment_types.get(external_ref, 'unknown'),
            'installment_number': '1',
            'total_installments': 1,
            'installment_net_amount_original': original_amount,
            'installment_net_amount': adjusted_amount,
            'money_release_date': settlement['money_release_date'],
            'approval_date': settlement['approval_date'],
            'refund_applied': abs(total_refunded),
            'chargeback_applied': abs(total_chargeback),
            'chargeback_cancel_applied': abs(total_chargeback_cancel),
            'has_adjustment': (total_refunded != 0 or 
                             total_chargeback != 0 or
                             total_chargeback_cancel != 0),
            'status': 'pending',
            'received_amount': 0,
            'received_date': None,
            'currency': settlement['currency']
        }
        
        self.installments.append(installment)
    
    def _identify_payment_type(self, settlement):
        """Identifica o tipo de pagamento"""
        method_type = settlement['payment_method_type'].lower()
        method = settlement['payment_method'].lower()
        installments = settlement['installments']
        
        # PIX
        if method == 'pix':
            return 'pix'
        
        # Boleto
        if method_type == 'ticket' or 'bol' in method:
            return 'boleto'
        
        # Saldo Mercado Pago
        if method == 'available_money':
            return 'saldo_mp'
        
        # Crédito Mercado Livre (parcelado sem juros)
        if method == 'consumer_credits':
            return 'credito_ml'
        
        # Cartão de Crédito Parcelado
        if method_type == 'credit_card' and installments > 1:
            return 'cartao_parcelado'
        
        # Cartão de Crédito à Vista
        if method_type == 'credit_card' and installments == 1:
            return 'cartao_avista'
        
        # Cartão de Débito
        if method_type == 'debit_card':
            return 'cartao_debito'
        
        return 'outros'
    
    def get_installments(self):
        """Retorna todas as parcelas"""
        return self.installments
    
    def get_transactions_summary(self):
        """Retorna resumo de transações"""
        transactions_by_type = defaultdict(lambda: {
            'count': 0,
            'total_amount': 0,
            'transactions': []
        })
        
        for trans in self.transactions:
            trans_type = trans['transaction_type']
            
            if trans_type == 'SETTLEMENT' and trans['description'] != 'INSTALLMENT':
                transactions_by_type[trans_type]['count'] += 1
                transactions_by_type[trans_type]['total_amount'] += trans['settlement_net_amount']
                transactions_by_type[trans_type]['transactions'].append({
                    'external_reference': trans['external_reference'],
                    'amount': trans['transaction_amount'],
                    'net_amount': trans['settlement_net_amount'],
                    'payment_method': trans['payment_method'],
                    'date': trans['approval_date']
                })
        
        return dict(transactions_by_type)
    
    def get_summary(self):
        """Retorna resumo geral"""
        total_orders = len(self.order_balances)
        total_installments = len(self.installments)
        
        total_expected = sum(i['installment_net_amount'] for i in self.installments)
        total_refunded = sum(b['refunded'] for b in self.order_balances.values())
        total_chargeback = sum(b['chargeback'] for b in self.order_balances.values())
        
        orders_with_refund = sum(1 for b in self.order_balances.values() if b['has_refund'])
        orders_with_chargeback = sum(1 for b in self.order_balances.values() if b['has_chargeback'])
        
        # Por tipo de pagamento
        payment_types_summary = defaultdict(lambda: {'count': 0, 'amount': 0})
        for ref, balance in self.order_balances.items():
            ptype = balance['payment_type']
            payment_types_summary[ptype]['count'] += 1
            payment_types_summary[ptype]['amount'] += balance['final_net']
        
        return {
            'total_orders': total_orders,
            'total_installments': total_installments,
            'total_expected': round(total_expected, 2),
            'total_refunded': round(total_refunded, 2),
            'total_chargeback': round(total_chargeback, 2),
            'orders_with_refund': orders_with_refund,
            'orders_with_chargeback': orders_with_chargeback,
            'payment_types': dict(payment_types_summary)
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