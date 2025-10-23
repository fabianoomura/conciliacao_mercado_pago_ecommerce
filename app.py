from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
import shutil
import sys

# Adicionar diretório backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from processors.sales_processor import SalesProcessor
from processors.releases_processor import ReleasesProcessor
from processors.reconciliator import Reconciliator
from processors.movements_processor import MovementsProcessor
from utils.cashflow import CashFlowCalculator

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')
CORS(app)

# Variáveis globais para armazenar dados processados
data_cache = {
    'transactions': [],
    'installments': [],
    'releases': [],
    'movements': [],
    'payouts': [],
    'advance_fees': [],
    'processed': False,
    'last_update': None
}

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_data():
    """Processa todos os arquivos de vendas e recebimentos"""
    try:
        print("\n" + "="*60)
        print("INICIANDO PROCESSAMENTO")
        print("="*60)
        
        # 1. Processar vendas
        print("\n1. PROCESSANDO VENDAS...")
        sales_processor = SalesProcessor()
        sales_data = sales_processor.process_files('data/vendas')
        
        data_cache['transactions'] = sales_data['transactions']
        data_cache['installments'] = sales_data['installments']
        
        sales_summary = sales_processor.get_summary()
        
        # 2. Processar recebimentos
        print("\n2. PROCESSANDO RECEBIMENTOS...")
        releases_processor = ReleasesProcessor()
        releases = releases_processor.process_files('data/recebimentos')
        
        data_cache['releases'] = releases
        
        releases_summary = releases_processor.get_summary()
        
        # 2.1. Processar movimentações (saques, taxas, reservas)
        print("\n2.1. PROCESSANDO MOVIMENTAÇÕES DO MP...")
        movements_processor = MovementsProcessor()
        movements = movements_processor.process_files('data/recebimentos')
        
        data_cache['movements'] = movements
        
        movements_summary = movements_processor.get_summary()
        payouts_data = movements_processor.get_payouts_summary()
        fees_data = movements_processor.get_advance_fees_summary()
        
        data_cache['payouts'] = payouts_data['payouts']
        data_cache['advance_fees'] = fees_data['fees']
        
        # 3. Fazer conciliação
        print("\n3. EXECUTANDO CONCILIAÇÃO...")
        reconciliator = Reconciliator(data_cache['installments'], data_cache['releases'])
        reconciliation_summary = reconciliator.reconcile()
        
        # 4. Processar estornos e chargebacks
        reconciliator.process_refunds_and_chargebacks()
        
        reconciliation_detail = reconciliator.get_summary()
        
        # 5. Calcular fluxo de caixa
        print("\n4. CALCULANDO FLUXO DE CAIXA...")
        cashflow = CashFlowCalculator(data_cache['installments'])
        cashflow_totals = cashflow.get_totals()
        
        data_cache['processed'] = True
        
        print("\n" + "="*60)
        print("✓ PROCESSAMENTO CONCLUÍDO COM SUCESSO")
        print("="*60)
        
        return jsonify({
            'success': True,
            'message': 'Dados processados com sucesso',
            'summary': {
                'sales': sales_summary,
                'releases': releases_summary,
                'movements': movements_summary,
                'payouts': payouts_data,
                'advance_fees': fees_data,
                'reconciliation': reconciliation_summary,
                'reconciliation_detail': reconciliation_detail,
                'cashflow': cashflow_totals
            }
        })
        
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cashflow/daily')
def get_daily_cashflow():
    """Retorna fluxo de caixa diário"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados. Execute /api/process primeiro'}), 400
    
    cashflow = CashFlowCalculator(data_cache['installments'])
    daily = cashflow.get_daily_cashflow()
    
    return jsonify({
        'success': True,
        'data': daily
    })

@app.route('/api/cashflow/monthly')
def get_monthly_cashflow():
    """Retorna fluxo de caixa mensal"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados. Execute /api/process primeiro'}), 400
    
    cashflow = CashFlowCalculator(data_cache['installments'])
    monthly = cashflow.get_monthly_cashflow()
    
    return jsonify({
        'success': True,
        'data': monthly
    })

@app.route('/api/cashflow/summary')
def get_cashflow_summary():
    """Retorna resumo do fluxo de caixa"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados. Execute /api/process primeiro'}), 400
    
    cashflow = CashFlowCalculator(data_cache['installments'])
    
    totals = cashflow.get_totals()
    overdue = cashflow.get_overdue_installments()
    upcoming = cashflow.get_upcoming_7_days()
    status_summary = cashflow.get_summary_by_status()
    
    return jsonify({
        'success': True,
        'data': {
            'totals': totals,
            'overdue': overdue,
            'upcoming_7_days': upcoming,
            'by_status': status_summary
        }
    })

@app.route('/api/installments/pending')
def get_pending_installments():
    """Retorna todas as parcelas pendentes"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    pending = [i for i in data_cache['installments'] if i['status'] == 'pending']
    pending_sorted = sorted(pending, key=lambda x: x['expected_date'])
    
    return jsonify({
        'success': True,
        'count': len(pending_sorted),
        'data': pending_sorted
    })

@app.route('/api/installments/received')
def get_received_installments():
    """Retorna todas as parcelas recebidas"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    received = [i for i in data_cache['installments'] if i['status'] == 'received']
    received_sorted = sorted(received, key=lambda x: x['received_date'], reverse=True)
    
    return jsonify({
        'success': True,
        'count': len(received_sorted),
        'data': received_sorted
    })

@app.route('/api/reconciliation/divergent')
def get_divergent_items():
    """Retorna itens com divergência"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    divergent = [
        i for i in data_cache['installments'] 
        if i['status'] == 'received' and i['difference'] and abs(i['difference']) > 0.02
    ]
    
    return jsonify({
        'success': True,
        'count': len(divergent),
        'data': divergent
    })

@app.route('/api/transactions')
def get_transactions():
    """Retorna todas as transações"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    return jsonify({
        'success': True,
        'count': len(data_cache['transactions']),
        'data': data_cache['transactions']
    })

@app.route('/api/transactions/summary')
def get_transactions_summary():
    """Retorna transações com resumo de parcelas recebidas/pendentes"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    # Criar dicionário de parcelas por operation_id
    installments_by_op = {}
    for inst in data_cache['installments']:
        op_id = inst['operation_id']
        if op_id not in installments_by_op:
            installments_by_op[op_id] = []
        installments_by_op[op_id].append(inst)
    
    # Enriquecer transações com info de parcelas
    enriched_transactions = []
    for trans in data_cache['transactions']:
        op_id = trans['operation_id']
        
        # Buscar parcelas desta transação
        installments = installments_by_op.get(op_id, [])
        
        # Calcular totais
        total_received = sum(i.get('received_amount', 0) for i in installments if i['status'] == 'received')
        total_pending = sum(i.get('estimated_amount', 0) for i in installments if i['status'] == 'pending')
        
        # Verificar se tem reembolso
        has_refund = trans['amount_refunded'] > 0 or trans['status'] == 'refunded'
        
        enriched_trans = {
            **trans,
            'received_amount': round(total_received, 2),
            'pending_amount': round(total_pending, 2),
            'has_refund': has_refund,
            'installments_received': len([i for i in installments if i['status'] == 'received']),
            'installments_pending': len([i for i in installments if i['status'] == 'pending']),
            'installments_cancelled': len([i for i in installments if 'cancelled' in i['status']])
        }
        
        enriched_transactions.append(enriched_trans)
    
    return jsonify({
        'success': True,
        'count': len(enriched_transactions),
        'data': enriched_transactions
    })

@app.route('/api/status')
def get_status():
    """Retorna status do sistema"""
    vendas_dir = 'data/vendas'
    recebimentos_dir = 'data/recebimentos'
    
    vendas_files = []
    recebimentos_files = []
    
    if os.path.exists(vendas_dir):
        vendas_files = [f for f in os.listdir(vendas_dir) if f.endswith(('.xls', '.xlsx'))]
    
    if os.path.exists(recebimentos_dir):
        recebimentos_files = [f for f in os.listdir(recebimentos_dir) if f.endswith(('.xls', '.xlsx'))]
    
    return jsonify({
        'success': True,
        'processed': data_cache['processed'],
        'files': {
            'vendas': {
                'count': len(vendas_files),
                'files': sorted(vendas_files)
            },
            'recebimentos': {
                'count': len(recebimentos_files),
                'files': sorted(recebimentos_files)
            }
        }
    })

@app.route('/api/reset')
def reset_data():
    """Limpa o cache de dados"""
    data_cache['transactions'] = []
    data_cache['installments'] = []
    data_cache['releases'] = []
    data_cache['movements'] = []
    data_cache['payouts'] = []
    data_cache['advance_fees'] = []
    data_cache['processed'] = False
    
    return jsonify({
        'success': True,
        'message': 'Cache limpo. Execute /api/process para reprocessar.'
    })

@app.route('/api/payouts')
def get_payouts():
    """Retorna todos os saques realizados"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    payouts = data_cache.get('payouts', [])
    total_amount = sum(p.get('amount', 0) for p in payouts)
    
    return jsonify({
        'success': True,
        'count': len(payouts),
        'total_amount': total_amount,
        'data': payouts
    })

@app.route('/api/advance-fees')
def get_advance_fees():
    """Retorna todas as taxas de antecipação"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    fees = data_cache.get('advance_fees', [])
    total_amount = sum(f.get('amount', 0) for f in fees)
    
    return jsonify({
        'success': True,
        'count': len(fees),
        'total_amount': total_amount,
        'data': fees
    })

@app.route('/api/movements')
def get_movements():
    """Retorna todas as movimentações"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    movements = data_cache.get('movements', [])
    
    return jsonify({
        'success': True,
        'count': len(movements),
        'data': movements
    })

@app.route('/api/reconciliation/full')
def get_full_reconciliation():
    """Retorna conciliação completa incluindo movimentações"""
    if not data_cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    # Calcular totais de vendas
    total_sales = sum(t.get('transaction_amount', 0) for t in data_cache['transactions'])
    total_net = sum(t.get('net_received_amount', 0) for t in data_cache['transactions'])
    total_fees = sum(abs(t.get('mercadopago_fee', 0)) for t in data_cache['transactions'])
    
    # Criar set de operation_ids das transações processadas
    known_operation_ids = set(t['operation_id'] for t in data_cache['transactions'])
    
    # Calcular totais de PARCELAS (correto!)
    received_inst = [i for i in data_cache['installments'] if i['status'] == 'received']
    pending_inst = [i for i in data_cache['installments'] if i['status'] == 'pending']
    
    total_inst_received = sum(i.get('received_amount', 0) for i in received_inst)
    total_inst_pending = sum(i.get('estimated_amount', 0) for i in pending_inst)
    total_inst_expected = total_inst_received + total_inst_pending
    
    # Calcular totais de recebimentos (releases de payments)
    payment_releases = [r for r in data_cache['releases'] if r.get('description') == 'payment']
    total_received_all = sum(r.get('net_credit_amount', 0) for r in payment_releases)
    
    # FILTRAR apenas releases de vendas conhecidas
    filtered_releases = [
        r for r in payment_releases 
        if r.get('external_reference', '') in known_operation_ids
    ]
    total_received_filtered = sum(r.get('net_credit_amount', 0) for r in filtered_releases)
    
    # Releases órfãos (sem venda correspondente)
    orphan_releases = [
        r for r in payment_releases 
        if r.get('external_reference', '') not in known_operation_ids and r.get('external_reference', '')
    ]
    total_orphan = sum(r.get('net_credit_amount', 0) for r in orphan_releases)
    
    # Calcular saques e taxas
    total_payouts = sum(p.get('amount', 0) for p in data_cache.get('payouts', []))
    total_advance_fees = sum(f.get('amount', 0) for f in data_cache.get('advance_fees', []))
    
    # Saldo esperado no MP
    expected_mp_balance = total_received_all - total_payouts
    
    # VALIDAÇÃO CORRETA: Vendas devem bater com parcelas geradas
    validation_sales_vs_installments = abs(total_net - total_inst_expected) < 1.0
    diff_sales_vs_installments = round(total_net - total_inst_expected, 2)
    
    # VALIDAÇÃO: Parcelas recebidas devem bater com releases FILTRADOS
    validation_inst_vs_releases = abs(total_inst_received - total_received_filtered) < 1.0
    diff_inst_vs_releases = round(total_inst_received - total_received_filtered, 2)
    
    return jsonify({
        'success': True,
        'data': {
            'sales': {
                'total_gross': total_sales,
                'total_net': total_net,
                'total_mp_fees': total_fees,
                'transactions_count': len(data_cache['transactions'])
            },
            'installments': {
                'total_expected': total_inst_expected,
                'total_received': total_inst_received,
                'total_pending': total_inst_pending,
                'count_received': len(received_inst),
                'count_pending': len(pending_inst)
            },
            'releases': {
                'total_all': total_received_all,
                'total_filtered': total_received_filtered,
                'total_orphan': total_orphan,
                'count_all': len(payment_releases),
                'count_filtered': len(filtered_releases),
                'count_orphan': len(orphan_releases)
            },
            'withdrawals': {
                'total_payouts': total_payouts,
                'total_advance_fees': total_advance_fees,
                'net_withdrawn': total_payouts
            },
            'balance': {
                'expected_mp_balance': expected_mp_balance,
                'total_fees_paid': total_fees + total_advance_fees
            },
            'validation': {
                'sales_vs_installments': {
                    'is_valid': validation_sales_vs_installments,
                    'difference': diff_sales_vs_installments,
                    'message': 'Vendas vs Parcelas Geradas'
                },
                'installments_vs_releases': {
                    'is_valid': validation_inst_vs_releases,
                    'difference': diff_inst_vs_releases,
                    'message': 'Parcelas Recebidas vs Releases (Filtrados)'
                }
            },
            'warnings': {
                'has_orphan_releases': total_orphan > 0,
                'orphan_amount': total_orphan,
                'orphan_count': len(orphan_releases),
                'message': f'Encontrados R$ {total_orphan:.2f} em recebimentos de vendas não processadas (provavelmente de períodos anteriores)'
            }
        }
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("Sistema de Conciliação Mercado Pago")
    print("="*60)
    print("\n🚀 Servidor iniciando em http://localhost:9000")
    print("\n📁 Certifique-se de ter arquivos em:")
    print("   - data/vendas/")
    print("   - data/recebimentos/")
    print("\n" + "="*60 + "\n")

    # Escutar apenas em localhost para evitar conflitos de porta
    app.run(host='127.0.0.1', port=9000, debug=True, use_reloader=False)