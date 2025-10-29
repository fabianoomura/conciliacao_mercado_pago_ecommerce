"""
App.py V3 - Sistema de Conciliação Mercado Pago
Backend Flask completo com:
- Settlement Processor V3 (estornos, chargebacks, tipos de pagamento)
- Releases Processor V2 (separação de payments e movimentações)
- Reconciliator V3 (adiantamento, status avançados)
- Movements Processor V2 (taxas, payouts, chargebacks)
- Cashflow V2 (fluxo com adiantamento)
"""

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import os

# Importar processadores
from backend.processors.settlement_processor import SettlementProcessorV3
from backend.processors.releases_processor import ReleasesProcessorV2
from backend.processors.reconciliator import ReconciliatorV3
from backend.processors.movements_processor import MovementsProcessorV2
from backend.utils.cashflow import CashFlowCalculatorV2

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

CORS(app)

# Cache global
_cache = {
    'processed': False,
    'settlement_proc': None,
    'releases_proc': None,
    'reconciliator': None,
    'movements_proc': None,
    'cashflow': None
}

def process_all_data():
    """Processa todos os dados e atualiza cache"""
    print("\n" + "="*70)
    print(" 🔄 PROCESSANDO DADOS - V3")
    print("="*70)
    
    # 1. Processar Settlement
    print("\n1️⃣  PROCESSANDO SETTLEMENT...")
    settlement_proc = SettlementProcessorV3()
    settlement_proc.process_files('data/settlement')
    
    # 2. Processar Recebimentos
    print("\n2️⃣  PROCESSANDO RECEBIMENTOS...")
    releases_proc = ReleasesProcessorV2()
    releases_proc.process_files('data/recebimentos')
    
    # 3. Processar Movimentações
    print("\n3️⃣  PROCESSANDO MOVIMENTAÇÕES...")
    movements = releases_proc.get_movements()
    movements_proc = MovementsProcessorV2(movements)
    
    # 4. Conciliar
    print("\n4️⃣  CONCILIANDO...")
    installments = settlement_proc.get_installments()
    payments = releases_proc.get_payments_only()
    order_balances = settlement_proc.order_balances
    
    reconciliator = ReconciliatorV3(installments, payments, order_balances)
    reconciliator.reconcile()
    
    # 5. Calcular Fluxo de Caixa
    print("\n5️⃣  CALCULANDO FLUXO DE CAIXA...")
    cashflow = CashFlowCalculatorV2(installments)
    
    # Atualizar cache
    _cache['processed'] = True
    _cache['settlement_proc'] = settlement_proc
    _cache['releases_proc'] = releases_proc
    _cache['reconciliator'] = reconciliator
    _cache['movements_proc'] = movements_proc
    _cache['cashflow'] = cashflow
    
    print("\n" + "="*70)
    print(" ✅ PROCESSAMENTO CONCLUÍDO!")
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
        'version': 'V3 - Sistema Completo',
        'message': 'Flask está funcionando!',
        'features': [
            'Estornos e chargebacks',
            'Adiantamento de crédito',
            'Taxas de antecipação',
            'Múltiplos tipos de pagamento',
            'Status avançados'
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
        'version': 'V3'
    })

@app.route('/api/process', methods=['POST'])
def process():
    """Processar/reprocessar dados"""
    try:
        process_all_data()
        
        settlement_summary = _cache['settlement_proc'].get_summary()
        releases_summary = _cache['releases_proc'].get_summary()
        detailed_status = _cache['reconciliator'].get_detailed_status()
        movements_summary = _cache['movements_proc'].get_full_summary()
        
        return jsonify({
            'success': True,
            'settlement': settlement_summary,
            'releases': releases_summary,
            'reconciliation': detailed_status,
            'movements': movements_summary,
            'version': 'V3'
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
    """Limpar cache"""
    _cache['processed'] = False
    _cache['settlement_proc'] = None
    _cache['releases_proc'] = None
    _cache['reconciliator'] = None
    _cache['movements_proc'] = None
    _cache['cashflow'] = None
    
    return jsonify({
        'success': True,
        'message': 'Cache limpo'
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
# INICIALIZAÇÃO
# ========================================

if __name__ == '__main__':
    print("="*70)
    print(" 💰 Sistema de Conciliação Mercado Pago V3")
    print(" ✅ Versão Completa com:")
    print("    - Estornos e Chargebacks")
    print("    - Adiantamento de Crédito")
    print("    - Taxas de Antecipação")
    print("    - Múltiplos Tipos de Pagamento")
    print("    - Status Avançados")
    print("="*70)
    print()
    print("📂 Estrutura de pastas:")
    print(f"   Templates: {app.template_folder}")
    print(f"   Static: {app.static_folder}")
    print()
    print("📂 Certifique-se de que os arquivos estão em:")
    print("   - data/settlement/")
    print("   - data/recebimentos/")
    print()
    print("🚀 Servidor rodando em: http://localhost:9000")
    print("📊 Acesse o dashboard e clique em 'Processar Dados'")
    print()
    
    app.run(host='0.0.0.0', port=9000, debug=True)