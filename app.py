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
    data_cache['processed'] = False
    
    return jsonify({
        'success': True,
        'message': 'Cache limpo. Execute /api/process para reprocessar.'
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