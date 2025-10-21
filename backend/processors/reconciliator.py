from datetime import datetime

class Reconciliator:
    """Faz a conciliação entre parcelas calculadas e releases recebidas"""
    
    def __init__(self, installments, releases):
        self.installments = installments
        self.releases = releases
        self.reconciliation_results = []
        
    def reconcile(self):
        """Executa a conciliação completa"""
        print("\nIniciando conciliação...")
        
        # Filtrar apenas releases de pagamento
        payment_releases = [r for r in self.releases if r['description'] == 'payment']
        
        print(f"Parcelas a conciliar: {len(self.installments)}")
        print(f"Releases de pagamento: {len(payment_releases)}")
        
        # Criar índice de releases por source_id + installments
        releases_index = {}
        releases_full_payment = {}  # Para pagamentos integrais
        
        for release in payment_releases:
            source_id = str(release['source_id']).strip()
            installments_raw = str(release['installments']).strip()
            
            # Normalizar campo installments
            if not installments_raw or installments_raw == '' or installments_raw == '1':
                # Pagamento à vista
                installments_normalized = '1/1'
                key = f"{source_id}|{installments_normalized}"
                releases_index[key] = release
                
            elif '/' in installments_raw:
                # Formato normal: "1/6", "2/6", etc
                key = f"{source_id}|{installments_raw}"
                releases_index[key] = release
                
            else:
                # Só número sem barra (ex: "3")
                # Significa que liberou TODAS as parcelas de uma vez
                # Guardar em índice separado
                total_installments = int(installments_raw)
                releases_full_payment[source_id] = {
                    'release': release,
                    'total_installments': total_installments
                }
        
        print(f"Índice de releases individuais: {len(releases_index)} chaves")
        print(f"Índice de pagamentos integrais: {len(releases_full_payment)} chaves")
        
        # Conciliar cada parcela
        matched = 0
        pending = 0
        divergent = 0
        
        for installment in self.installments:
            # Pular parcelas canceladas
            if installment['status'] == 'cancelled':
                continue
            
            operation_id = str(installment['operation_id']).strip()
            installment_label = str(installment['installment_label']).strip()
            
            # Tentar encontrar release individual primeiro
            key = f"{operation_id}|{installment_label}"
            
            if key in releases_index:
                # Parcela encontrada individualmente
                release = releases_index[key]
                self._mark_as_received(installment, release, matched, divergent)
                matched += 1
                
            elif operation_id in releases_full_payment:
                # Pagamento integral encontrado
                full_payment = releases_full_payment[operation_id]
                release = full_payment['release']
                total_installments = full_payment['total_installments']
                
                # Verificar se essa parcela faz parte desse pagamento integral
                if installment['total_installments'] == total_installments:
                    # Dividir o valor total pelas parcelas
                    self._mark_as_received(installment, release, matched, divergent)
                    matched += 1
                else:
                    pending += 1
                    installment['status'] = 'pending'
            else:
                # Parcela não encontrada
                pending += 1
                installment['status'] = 'pending'
        
        print(f"\n✓ Conciliação concluída:")
        print(f"  - Conciliadas: {matched}")
        print(f"  - Pendentes: {pending}")
        print(f"  - Divergentes: {divergent}")
        
        return {
            'matched': matched,
            'pending': pending,
            'divergent': divergent,
            'total': matched + pending + divergent
        }

    def _mark_as_received(self, installment, release, matched, divergent):
        """Marca uma parcela como recebida"""
        installment['status'] = 'received'
        installment['received_date'] = self._parse_date(release['release_date'])
        installment['received_amount'] = release['net_credit_amount'] / installment['total_installments']
        
        # Calcular diferença
        expected = installment['net_amount']
        received = installment['received_amount']
        difference = round(received - expected, 2)
        installment['difference'] = difference
        
        # Classificar status
        if abs(difference) <= 0.02:
            status = 'matched'
        else:
            status = 'divergent'
        
        self.reconciliation_results.append({
            'operation_id': installment['operation_id'],
            'installment_label': installment['installment_label'],
            'expected_date': installment['expected_date'],
            'expected_amount': expected,
            'received_date': installment['received_date'],
            'received_amount': received,
            'difference': difference,
            'status': status
        })
    
    def _parse_date(self, date_str):
        """Parseia data para formato padrão"""
        if not date_str:
            return None
        
        try:
            if isinstance(date_str, str):
                # Remover timezone e milissegundos
                date_str = date_str.split('.')[0].replace('T', ' ')
                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%Y-%m-%d')
            return None
        except:
            return None
    
    def get_divergent_items(self):
        """Retorna apenas itens com divergência"""
        return [r for r in self.reconciliation_results if r['status'] == 'divergent']
    
    def get_pending_items(self):
        """Retorna apenas itens pendentes"""
        return [i for i in self.installments if i['status'] == 'pending']
    
    def process_refunds_and_chargebacks(self):
        """Processa estornos e chargebacks dos releases"""
        print("\nProcessando estornos e chargebacks...")
        
        refunds = [r for r in self.releases if r['description'] == 'refund']
        chargebacks = [r for r in self.releases if r['description'] == 'chargeback']
        chargeback_cancels = [r for r in self.releases if r['description'] == 'chargeback_cancel']
        
        print(f"  - Refunds: {len(refunds)}")
        print(f"  - Chargebacks: {len(chargebacks)}")
        print(f"  - Chargeback Cancels: {len(chargeback_cancels)}")
        
        # Processar refunds
        for refund in refunds:
            source_id = refund['source_id']
            refund_amount = abs(refund['net_debit_amount'])
            
            # Cancelar parcelas pendentes dessa transação
            for installment in self.installments:
                if installment['operation_id'] == source_id and installment['status'] == 'pending':
                    installment['status'] = 'cancelled_refund'
        
        # Processar chargebacks
        for chargeback in chargebacks:
            source_id = chargeback['source_id']
            
            # Cancelar parcelas pendentes dessa transação
            for installment in self.installments:
                if installment['operation_id'] == source_id and installment['status'] == 'pending':
                    installment['status'] = 'cancelled_chargeback'
        
        # Processar chargeback cancels (reverter)
        for cancel in chargeback_cancels:
            source_id = cancel['source_id']
            
            # Reativar parcelas que foram canceladas por chargeback
            for installment in self.installments:
                if installment['operation_id'] == source_id and installment['status'] == 'cancelled_chargeback':
                    installment['status'] = 'pending'
        
        print("✓ Estornos e chargebacks processados")
    
    def get_summary(self):
        """Retorna resumo da conciliação"""
        if not self.installments:
            return None
        
        status_count = {}
        for installment in self.installments:
            status = installment['status']
            status_count[status] = status_count.get(status, 0) + 1
        
        total_expected = sum(i['net_amount'] for i in self.installments if i['status'] != 'cancelled')
        total_received = sum(i['received_amount'] for i in self.installments if i['received_amount'])
        total_pending = sum(i['net_amount'] for i in self.installments if i['status'] == 'pending')
        
        return {
            'status_breakdown': status_count,
            'total_expected': round(total_expected, 2),
            'total_received': round(total_received, 2),
            'total_pending': round(total_pending, 2),
            'reconciliation_rate': round((status_count.get('received', 0) / len(self.installments) * 100), 2) if self.installments else 0
        }