"""
App.py V5 - Sistema de Conciliação Mercado Pago
Backend Flask completo com:
- Settlement Processor V3 (estornos, chargebacks, tipos de pagamento)
- Releases Processor V2 (separação de payments e movimentações)
- Reconciliator V5 (SOURCE_ID matching, todos tipos de pagamento)
- Movements Processor V2 (taxas, payouts, chargebacks)
- Cashflow V2 (fluxo com adiantamento)
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import os
from datetime import datetime

# Importar processadores
from backend.processors.settlement_processor import SettlementProcessorV3
from backend.processors.releases_processor import ReleasesProcessorV2
from backend.processors.reconciliator_v5 import ReconciliatorV5
from backend.processors.movements_processor import MovementsProcessorV2
from backend.utils.cashflow import CashFlowCalculatorV2
from backend.utils.json_cache import JSONCache

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

CORS(app)

# Cache global em memória
_cache = {
    'processed': False,
    'settlement_proc': None,
    'releases_proc': None,
    'reconciliator': None,
    'movements_proc': None,
    'cashflow': None
}

# Cache em JSON para persistência
_json_cache = JSONCache(cache_dir='cache')

def process_all_data():
    """Processa todos os dados e atualiza cache (memória + JSON)"""
    print("\n" + "="*70)
    print(" PROCESSANDO DADOS - V5 COM CACHE JSON")
    print("="*70)

    # 1. Processar Settlement
    print("\n1. PROCESSANDO SETTLEMENT...")
    settlement_proc = SettlementProcessorV3()
    settlement_proc.process_files('data/settlement')

    # 2. Processar Recebimentos
    print("\n2. PROCESSANDO RECEBIMENTOS...")
    releases_proc = ReleasesProcessorV2()
    releases_proc.process_files('data/recebimentos')

    # 3. Processar Movimentações
    print("\n3. PROCESSANDO MOVIMENTACOES...")
    movements = releases_proc.get_movements()
    movements_proc = MovementsProcessorV2(movements)

    # 4. Conciliar usando ReconciliatorV5 com SOURCE_ID
    print("\n4. CONCILIANDO COM V5 (SOURCE_ID)...")

    # Obter dados processados do settlement
    settlement_data = settlement_proc.releases  # Settlement tem field 'releases'

    # Obter todos os dados de recebimentos (including movements)
    releases_data = releases_proc.releases

    # Usar ReconciliatorV5 que faz matching por SOURCE_ID
    reconciliator = ReconciliatorV5()
    reconciliation_results = reconciliator.process(settlement_data, releases_data)

    # Manter referencias necessarias para compatibilidade com cache e rotas
    installments = settlement_proc.get_installments()

    # 5. Calcular Fluxo de Caixa
    print("\n5. CALCULANDO FLUXO DE CAIXA...")
    cashflow = CashFlowCalculatorV2(installments)

    # 6. Salvar em Cache JSON
    print("\n6. SALVANDO EM CACHE JSON...")

    settlement_summary = settlement_proc.get_summary()
    releases_summary = releases_proc.get_summary()

    # Usar resumo do ReconciliatorV5
    reconciliation_summary = reconciliator.get_summary()

    movements_summary = movements_proc.get_full_summary()
    cashflow_summary = cashflow.get_summary()

    # Preparar dados para cache JSON
    cache_data = {
        'settlement': settlement_summary,
        'releases': releases_summary,
        'reconciliation': reconciliation_summary,
        'movements': movements_summary,
        'cashflow': cashflow_summary,
        'metadata': {
            'processed_at': datetime.now().isoformat(),
            'version': 'V5',
            'cache_format': 'JSON'
        }
    }

    # Salvar cada componente
    _json_cache.save_settlement(settlement_summary)
    _json_cache.save_releases(releases_summary)
    _json_cache.save_reconciliation(reconciliation_summary)
    _json_cache.save_cashflow(cashflow_summary)
    _json_cache.save_metadata(cache_data['metadata'])

    # Atualizar cache em memória
    _cache['processed'] = True
    _cache['settlement_proc'] = settlement_proc
    _cache['releases_proc'] = releases_proc
    _cache['reconciliator'] = reconciliator
    _cache['movements_proc'] = movements_proc
    _cache['cashflow'] = cashflow

    print("\n" + "="*70)
    print(" PROCESSAMENTO CONCLUIDO!")
    print(f" Cache JSON salvo em: {_json_cache.cache_dir}")
    print(f" Tamanho do cache: {_json_cache.get_cache_size()} MB")
    print("="*70 + "\n")

# ========================================
# ROTAS
# ========================================

@app.route('/')
def index():
    """Página principal"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Rota de teste"""
    return jsonify({
        'status': 'OK',
        'version': 'V5 - Sistema com SOURCE_ID Matching',
        'message': 'Flask esta funcionando!',
        'features': [
            'SOURCE_ID como primary key',
            'Suporte a 4 tipos de pagamento',
            'Estornos e chargebacks',
            'Adiantamento de credito',
            'Taxas de antecipacao',
            'Status avancados'
        ]
    })

@app.route('/api/status')
def status():
    """Status do sistema"""
    settlement_files = 0
    recebimentos_files = 0
    
    if os.path.exists('data/settlement'):
        settlement_files = len([
            f for f in os.listdir('data/settlement') 
            if f.endswith(('.xlsx', '.xls', '.csv'))
        ])
    
    if os.path.exists('data/recebimentos'):
        recebimentos_files = len([
            f for f in os.listdir('data/recebimentos') 
            if f.endswith(('.xlsx', '.xls'))
        ])
    
    return jsonify({
        'processed': _cache['processed'],
        'settlement_files': settlement_files,
        'recebimentos_files': recebimentos_files,
        'version': 'V5'
    })

@app.route('/api/process', methods=['POST'])
def process():
    """Processar/reprocessar dados"""
    try:
        process_all_data()
        
        settlement_summary = _cache['settlement_proc'].get_summary()
        releases_summary = _cache['releases_proc'].get_summary()
        detailed_status = _cache['reconciliator'].get_summary()
        movements_summary = _cache['movements_proc'].get_full_summary()
        
        return jsonify({
            'success': True,
            'settlement': settlement_summary,
            'releases': releases_summary,
            'reconciliation': detailed_status,
            'movements': movements_summary,
            'version': 'V5'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/reset', methods=['GET'])
def reset():
    """Limpar cache (memória e JSON)"""
    # Limpar cache em memória
    _cache['processed'] = False
    _cache['settlement_proc'] = None
    _cache['releases_proc'] = None
    _cache['reconciliator'] = None
    _cache['movements_proc'] = None
    _cache['cashflow'] = None

    # Limpar cache em JSON
    _json_cache.clear_all()

    return jsonify({
        'success': True,
        'message': 'Cache limpo (memória e JSON)'
    })

@app.route('/api/cache/info', methods=['GET'])
def cache_info():
    """Informações sobre o cache JSON"""
    info = _json_cache.get_cache_info()

    return jsonify({
        'success': True,
        'cache_info': info
    })

@app.route('/api/summary')
def summary():
    """Resumo geral (para dashboard)"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    settlement_summary = _cache['settlement_proc'].get_summary()
    releases_summary = _cache['releases_proc'].get_summary()
    detailed_status = _cache['reconciliator'].get_detailed_status()
    movements_summary = _cache['movements_proc'].get_full_summary()
    cashflow_summary = _cache['cashflow'].get_summary()
    orphans = _cache['reconciliator'].get_orphan_payments()
    advances = _cache['reconciliator'].detect_advance_payments()
    
    return jsonify({
        'success': True,
        'settlement': settlement_summary,
        'releases': releases_summary,
        'reconciliation': detailed_status,
        'movements': movements_summary,
        'cashflow': cashflow_summary,
        'orphan_payments': {
            'count': orphans['count'],
            'total_amount': orphans['total_amount']
        },
        'advance_payments': {
            'count': len(advances),
            'total_orders': len(advances)
        },
        'version': 'V3'
    })

# ========================================
# TRANSAÇÕES E PARCELAS
# ========================================

@app.route('/api/transactions')
def transactions():
    """Lista todas as transações"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    transactions = _cache['settlement_proc'].get_transactions_summary()
    
    return jsonify({
        'success': True,
        'transactions': transactions
    })

@app.route('/api/installments/pending')
def pending_installments():
    """Parcelas pendentes - Ordenadas do mais antigo para o mais recente

    Mostra todas as parcelas com saldo pendente de receber (incluindo futuras)
    """
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400

    pending = _cache['reconciliator'].get_installments_by_status('pending')

    # Ordenar por data de vencimento (do mais antigo para o mais recente)
    pending_sorted = sorted(
        pending,
        key=lambda x: x.get('money_release_date') or '9999-12-31'
    )

    total = sum(i['installment_net_amount'] for i in pending_sorted)

    return jsonify({
        'success': True,
        'installments': pending_sorted,
        'count': len(pending_sorted),
        'total_amount': round(total, 2)
    })

@app.route('/api/installments/received')
def received_installments():
    """Parcelas recebidas - Ordenadas da mais recente para a mais antiga"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400

    received = _cache['reconciliator'].get_installments_by_status('received')
    received_advance = _cache['reconciliator'].get_installments_by_status('received_advance')

    all_received = received + received_advance

    # Ordenar por data de recebimento (do mais recente para o mais antigo)
    all_received_sorted = sorted(
        all_received,
        key=lambda x: x.get('received_date') or '0000-01-01',
        reverse=True
    )

    total = sum(i['received_amount'] for i in all_received_sorted)

    return jsonify({
        'success': True,
        'installments': all_received_sorted,
        'count': len(all_received_sorted),
        'count_normal': len(received),
        'count_advance': len(received_advance),
        'total_amount': round(total, 2)
    })

@app.route('/api/installments/overdue')
def overdue_installments():
    """Parcelas atrasadas - Ordenadas da mais antiga para a mais recente"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400

    overdue = _cache['reconciliator'].get_installments_by_status('overdue')

    # Ordenar por data de vencimento (do mais antigo para o mais recente)
    overdue_sorted = sorted(
        overdue,
        key=lambda x: x.get('money_release_date') or '9999-12-31'
    )

    total = sum(i['installment_net_amount'] for i in overdue_sorted)

    return jsonify({
        'success': True,
        'installments': overdue_sorted,
        'count': len(overdue_sorted),
        'total_amount': round(total, 2)
    })

@app.route('/api/installments/advance')
def advance_installments():
    """Parcelas recebidas antecipadamente - Ordenadas por dias de antecipação (maior primeiro)"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400

    advance = _cache['reconciliator'].get_installments_by_status('received_advance')

    # Ordenar por dias de antecipação (do maior para o menor)
    advance_sorted = sorted(
        advance,
        key=lambda x: x.get('days_advance') or 0,
        reverse=True
    )

    total = sum(i['received_amount'] for i in advance_sorted)

    if advance_sorted:
        avg_days = sum(i.get('days_advance', 0) for i in advance_sorted) / len(advance_sorted)
    else:
        avg_days = 0

    return jsonify({
        'success': True,
        'installments': advance_sorted,
        'count': len(advance_sorted),
        'total_amount': round(total, 2),
        'avg_days_advance': round(avg_days, 1)
    })

# ========================================
# FLUXO DE CAIXA
# ========================================

@app.route('/api/cashflow/monthly')
def cashflow_monthly():
    """Fluxo de caixa mensal"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    monthly = _cache['cashflow'].get_monthly_cashflow()
    
    return jsonify({
        'success': True,
        'cashflow': monthly
    })

@app.route('/api/cashflow/daily')
def cashflow_daily():
    """Fluxo de caixa diário"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    daily = _cache['cashflow'].get_daily_cashflow()
    
    return jsonify({
        'success': True,
        'cashflow': daily
    })

@app.route('/api/cashflow/upcoming')
def cashflow_upcoming():
    """Próximos recebimentos (7 dias)"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    upcoming = _cache['cashflow'].get_upcoming_days(7)
    
    return jsonify({
        'success': True,
        'upcoming': upcoming
    })

# ========================================
# CONCILIAÇÃO E VALIDAÇÃO
# ========================================

@app.route('/api/reconciliation')
def reconciliation():
    """Relatório completo de conciliação"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    report = _cache['reconciliator'].get_reconciliation_report()
    
    return jsonify({
        'success': True,
        'report': report
    })

@app.route('/api/orphan_payments')
def orphan_payments():
    """Payments órfãos (sem match)"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    orphans = _cache['reconciliator'].get_orphan_payments()
    
    return jsonify({
        'success': True,
        'orphans': orphans
    })

# ========================================
# MOVIMENTAÇÕES
# ========================================

@app.route('/api/movements/advance_fees')
def advance_fees():
    """Taxas de antecipação"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    fees = _cache['movements_proc'].get_advance_fees_summary()
    
    return jsonify({
        'success': True,
        'fees': fees
    })

@app.route('/api/movements/payouts')
def payouts():
    """Saques realizados"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    payouts = _cache['movements_proc'].get_payouts_summary()
    
    return jsonify({
        'success': True,
        'payouts': payouts
    })

@app.route('/api/movements/chargebacks')
def chargebacks():
    """Chargebacks"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400
    
    chargebacks = _cache['movements_proc'].get_chargebacks_summary()
    
    return jsonify({
        'success': True,
        'chargebacks': chargebacks
    })

@app.route('/api/movements/summary')
def movements_summary():
    """Resumo completo de movimentações"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400

    summary = _cache['movements_proc'].get_full_summary()

    return jsonify({
        'success': True,
        'movements': summary
    })

# ========================================
# DEBUG - Análise de External Reference
# ========================================

@app.route('/api/debug/reference/<external_ref>')
def debug_reference(external_ref):
    """Analisa detalhadamente uma external reference específica"""
    if not _cache['processed']:
        return jsonify({'error': 'Dados não processados'}), 400

    # Buscar no settlement
    settlement_installments = [
        i for i in _cache['settlement_proc'].installments
        if i['external_reference'] == external_ref
    ]

    # Buscar nos payments (apenas vendas válidas)
    payments_found = [
        p for p in _cache['releases_proc'].get_payments_only()
        if p.get('external_reference') == external_ref
    ]

    # Buscar TODAS as releases (incluindo movimentações)
    all_releases_found = [
        r for r in _cache['releases_proc'].releases
        if r.get('external_reference') == external_ref
    ]

    # Buscar order balance
    order_balance = _cache['settlement_proc'].order_balances.get(external_ref, {})

    # Buscar parcelas conciliadas
    reconciled_installments = [
        i for i in _cache['reconciliator'].installments
        if i['external_reference'] == external_ref
    ]

    return jsonify({
        'success': True,
        'external_reference': external_ref,
        'settlement': {
            'installments_count': len(settlement_installments),
            'installments': settlement_installments,
            'order_balance': order_balance
        },
        'releases': {
            'payments_count': len(payments_found),
            'payments': payments_found,
            'total_payments': sum(p.get('net_credit_amount', 0) for p in payments_found),
            'all_releases_count': len(all_releases_found),
            'all_releases': all_releases_found,
            'has_refund': any(r.get('description') == 'refund' for r in all_releases_found),
            'has_chargeback': any('chargeback' in r.get('description', '') for r in all_releases_found)
        },
        'reconciliation': {
            'installments_count': len(reconciled_installments),
            'installments': reconciled_installments,
            'summary': {
                'received': sum(1 for i in reconciled_installments if i['status'] == 'received'),
                'received_advance': sum(1 for i in reconciled_installments if i['status'] == 'received_advance'),
                'pending': sum(1 for i in reconciled_installments if i['status'] == 'pending'),
                'cancelled': sum(1 for i in reconciled_installments if i['status'] == 'cancelled')
            }
        }
    })

# ========================================
# INICIALIZAÇÃO
# ========================================

if __name__ == '__main__':
    print("="*70)
    print(" Sistema de Conciliacao Mercado Pago V5")
    print(" Versao Completa com:")
    print("    - SOURCE_ID como primary key")
    print("    - Suporte a 4 tipos de pagamento")
    print("    - Estornos e Chargebacks")
    print("    - Adiantamento de Credito")
    print("    - Taxas de Antecipacao")
    print("    - Status Avancados")
    print("="*70)
    print()
    print("Estrutura de pastas:")
    print(f"   Templates: {app.template_folder}")
    print(f"   Static: {app.static_folder}")
    print()
    print("Certifique-se de que os arquivos estao em:")
    print("   - data/settlement/")
    print("   - data/recebimentos/")
    print()
    print("Servidor rodando em: http://localhost:9000")
    print("Acesse o dashboard e clique em 'Processar Dados'")
    print()
    
    app.run(host='0.0.0.0', port=9000, debug=True)