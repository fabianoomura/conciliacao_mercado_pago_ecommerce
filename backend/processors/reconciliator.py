from datetime import datetime

class Reconciliator:
    """Faz a conciliação entre parcelas calculadas e releases recebidas"""
    
    def __init__(self, installments, releases):
        self.installments = installments
        self.releases = releases
        self.reconciliation_results = []
        
    def reconcile(self):
        """Executa a conciliação completa usando SALDO DEVEDOR"""
        print("\nIniciando conciliação com abordagem de SALDO DEVEDOR...")
        
        # Filtrar apenas releases de pagamento
        payment_releases = [r for r in self.releases if r['description'] == 'payment']
        
        print(f"Parcelas a conciliar: {len(self.installments)}")
        print(f"Releases de pagamento: {len(payment_releases)}")
        
        # ========================================
        # ETAPA 1: INICIALIZAR SALDO DEVEDOR
        # ========================================
        
        # Criar dicionário de saldo por operation_id
        saldo_devedor = {}
        
        for installment in self.installments:
            operation_id = installment['operation_id']
            if operation_id not in saldo_devedor:
                # Inicializar saldo com o total líquido da transação
                saldo_devedor[operation_id] = {
                    'saldo_atual': installment['transaction_total_net'],
                    'saldo_inicial': installment['transaction_total_net'],
                    'parcelas_recebidas': 0,
                    'total_parcelas': installment['total_installments']
                }
        
        print(f"\nSaldos inicializados para {len(saldo_devedor)} transações")
        
        # ========================================
        # ETAPA 2: CRIAR ÍNDICE DE RELEASES
        # ========================================
        
        releases_index = {}
        releases_full_payment = {}
        
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
                total_installments = int(installments_raw)
                releases_full_payment[source_id] = {
                    'release': release,
                    'total_installments': total_installments
                }
        
        print(f"Índice de releases individuais: {len(releases_index)} chaves")
        print(f"Índice de pagamentos integrais: {len(releases_full_payment)} chaves")
        
        # ========================================
        # ETAPA 3: CONCILIAR E ATUALIZAR SALDOS
        # ========================================
        
        matched = 0
        pending = 0
        
        for installment in self.installments:
            # Pular parcelas canceladas (mas adicionar estimated_amount)
            if installment['status'] == 'cancelled':
                if installment.get('transaction_total_net'):
                    installment['estimated_amount'] = round(
                        installment['transaction_total_net'] / installment['total_installments'], 
                        2
                    )
                else:
                    installment['estimated_amount'] = 0.0
                continue
            
            operation_id = str(installment['operation_id']).strip()
            installment_label = str(installment['installment_label']).strip()
            
            # Obter saldo atual
            if operation_id not in saldo_devedor:
                print(f"  ⚠️ Operação {operation_id} sem saldo inicializado")
                pending += 1
                installment['status'] = 'pending'
                # Calcular valor estimado
                if installment.get('transaction_total_net'):
                    installment['estimated_amount'] = round(
                        installment['transaction_total_net'] / installment['total_installments'], 
                        2
                    )
                else:
                    installment['estimated_amount'] = 0.0
                continue
            
            saldo_info = saldo_devedor[operation_id]
            saldo_antes = saldo_info['saldo_atual']
            
            # Tentar encontrar release individual primeiro
            key = f"{operation_id}|{installment_label}"
            
            if key in releases_index:
                # Parcela encontrada individualmente
                release = releases_index[key]
                valor_recebido = release['net_credit_amount']
                
                # Atualizar saldo
                saldo_depois = saldo_antes - valor_recebido
                
                # Marcar como recebida
                installment['status'] = 'received'
                installment['received_date'] = self._parse_date(release['release_date'])
                installment['received_amount'] = valor_recebido
                installment['saldo_antes'] = round(saldo_antes, 2)
                installment['saldo_depois'] = round(saldo_depois, 2)
                installment['expected_amount'] = valor_recebido  # Para exibição
                installment['estimated_amount'] = valor_recebido  # Para exibição
                installment['difference'] = 0.0  # Sempre zero na nova lógica
                
                # Atualizar saldo devedor
                saldo_info['saldo_atual'] = saldo_depois
                saldo_info['parcelas_recebidas'] += 1
                
                matched += 1
                
            elif operation_id in releases_full_payment:
                # Pagamento integral encontrado
                full_payment = releases_full_payment[operation_id]
                release = full_payment['release']
                total_installments = full_payment['total_installments']
                
                # Verificar se essa parcela faz parte desse pagamento integral
                if installment['total_installments'] == total_installments:
                    # Dividir o valor total pelas parcelas
                    valor_recebido = release['net_credit_amount'] / total_installments
                    
                    # Atualizar saldo
                    saldo_depois = saldo_antes - valor_recebido
                    
                    # Marcar como recebida
                    installment['status'] = 'received'
                    installment['received_date'] = self._parse_date(release['release_date'])
                    installment['received_amount'] = valor_recebido
                    installment['saldo_antes'] = round(saldo_antes, 2)
                    installment['saldo_depois'] = round(saldo_depois, 2)
                    installment['expected_amount'] = valor_recebido
                    installment['estimated_amount'] = valor_recebido
                    installment['difference'] = 0.0
                    
                    # Atualizar saldo devedor
                    saldo_info['saldo_atual'] = saldo_depois
                    saldo_info['parcelas_recebidas'] += 1
                    
                    matched += 1
                else:
                    pending += 1
                    installment['status'] = 'pending'
                    installment['saldo_antes'] = round(saldo_antes, 2)
                    installment['saldo_depois'] = round(saldo_antes, 2)
                    # Calcular valor estimado
                    parcelas_restantes = installment['total_installments'] - installment['installment_number'] + 1
                    installment['estimated_amount'] = round(saldo_antes / parcelas_restantes, 2)
            else:
                # Parcela não encontrada
                pending += 1
                installment['status'] = 'pending'
                installment['saldo_antes'] = round(saldo_antes, 2)
                installment['saldo_depois'] = round(saldo_antes, 2)  # Saldo não muda
                # Calcular valor estimado
                parcelas_restantes = installment['total_installments'] - installment['installment_number'] + 1
                installment['estimated_amount'] = round(saldo_antes / parcelas_restantes, 2)
        
        # ========================================
        # ETAPA 4: VERIFICAR FECHAMENTO
        # ========================================
        
        print(f"\n=== VERIFICAÇÃO DE SALDOS ===")
        fechados_ok = 0
        for operation_id, info in saldo_devedor.items():
            if info['parcelas_recebidas'] == info['total_parcelas']:
                saldo_final = info['saldo_atual']
                if abs(saldo_final) > 0.10:  # Tolerância de 10 centavos
                    print(f"  ⚠️ Op {operation_id}: Saldo final = R$ {saldo_final:.2f} (esperado R$ 0,00)")
                else:
                    fechados_ok += 1
        
        if fechados_ok > 0:
            print(f"  ✓ {fechados_ok} transações fechadas corretamente")
        
        print(f"\n✓ Conciliação concluída:")
        print(f"  - Conciliadas: {matched}")
        print(f"  - Pendentes: {pending}")
        
        return {
            'matched': matched,
            'pending': pending,
            'divergent': 0,  # Não calculamos mais divergências individuais
            'total': matched + pending
        }

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
        """Retorna apenas itens com divergência (legacy - não usado mais)"""
        return []
    
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
        
        # ========================================
        # NOVA LÓGICA: DETECTAR PELO SALDO
        # ========================================
        
        # Criar índice de parcelas por operation_id
        parcelas_por_operacao = {}
        for installment in self.installments:
            op_id = installment['operation_id']
            if op_id not in parcelas_por_operacao:
                parcelas_por_operacao[op_id] = []
            parcelas_por_operacao[op_id].append(installment)
        
        # Verificar se alguma operação teve AUMENTO de saldo (indicador de reembolso)
        reembolsos_detectados = 0
        for op_id, parcelas in parcelas_por_operacao.items():
            # Ordenar por número da parcela
            parcelas_sorted = sorted(parcelas, key=lambda x: x['installment_number'])
            
            for i in range(1, len(parcelas_sorted)):
                parcela_anterior = parcelas_sorted[i-1]
                parcela_atual = parcelas_sorted[i]
                
                # Se ambas foram recebidas
                if (parcela_anterior.get('saldo_depois') is not None and 
                    parcela_atual.get('saldo_antes') is not None):
                    
                    # Se saldo aumentou = reembolso
                    if parcela_atual['saldo_antes'] > parcela_anterior['saldo_depois'] + 0.10:
                        diferenca = parcela_atual['saldo_antes'] - parcela_anterior['saldo_depois']
                        print(f"  🔄 Reembolso detectado em {op_id}: +R$ {diferenca:.2f}")
                        reembolsos_detectados += 1
                        break  # Só avisar uma vez por operação
        
        # Processar refunds explícitos
        for refund in refunds:
            source_id = refund['source_id']
            
            # Cancelar parcelas pendentes dessa transação
            for installment in self.installments:
                if installment['operation_id'] == source_id and installment['status'] == 'pending':
                    installment['status'] = 'cancelled_refund'
                    # Adicionar estimated_amount
                    if installment.get('transaction_total_net'):
                        installment['estimated_amount'] = 0.0
        
        # Processar chargebacks
        for chargeback in chargebacks:
            source_id = chargeback['source_id']
            
            # Cancelar parcelas pendentes dessa transação
            for installment in self.installments:
                if installment['operation_id'] == source_id and installment['status'] == 'pending':
                    installment['status'] = 'cancelled_chargeback'
                    if installment.get('transaction_total_net'):
                        installment['estimated_amount'] = 0.0
        
        # Processar chargeback cancels (reverter)
        for cancel in chargeback_cancels:
            source_id = cancel['source_id']
            
            # Reativar parcelas que foram canceladas por chargeback
            for installment in self.installments:
                if installment['operation_id'] == source_id and installment['status'] == 'cancelled_chargeback':
                    installment['status'] = 'pending'
                    # Recalcular estimated_amount
                    if installment.get('saldo_antes'):
                        parcelas_restantes = installment['total_installments'] - installment['installment_number'] + 1
                        installment['estimated_amount'] = round(installment['saldo_antes'] / parcelas_restantes, 2)
        
        if reembolsos_detectados > 0:
            print(f"  ℹ️ Total de {reembolsos_detectados} reembolsos detectados automaticamente")
        
        print("✓ Estornos e chargebacks processados")
    
    def get_summary(self):
        """Retorna resumo da conciliação"""
        if not self.installments:
            return None
        
        status_count = {}
        for installment in self.installments:
            status = installment['status']
            status_count[status] = status_count.get(status, 0) + 1
        
        # Calcular totais usando a nova estrutura
        total_expected = 0.0
        total_received = 0.0
        total_pending = 0.0
        
        for i in self.installments:
            # Para parcelas recebidas
            if i['status'] == 'received' and i.get('received_amount'):
                total_received += i['received_amount']
                total_expected += i['received_amount']
            
            # Para parcelas pendentes - usar estimated_amount
            elif i['status'] == 'pending':
                if i.get('estimated_amount'):
                    total_pending += i['estimated_amount']
                    total_expected += i['estimated_amount']
        
        return {
            'status_breakdown': status_count,
            'total_expected': round(total_expected, 2),
            'total_received': round(total_received, 2),
            'total_pending': round(total_pending, 2),
            'reconciliation_rate': round((status_count.get('received', 0) / len(self.installments) * 100), 2) if self.installments else 0
        }