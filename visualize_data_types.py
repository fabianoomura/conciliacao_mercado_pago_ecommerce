import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import json

# Configurar encoding UTF-8
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Carregar dados
with open(r'C:\projetos_code\conciliacao_mercado_pago_ecommerce\ANALISE_TIPOS_DADOS_RESUMO.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Criar figura com múltiplos subplots
fig = plt.figure(figsize=(20, 12))
fig.suptitle('ANÁLISE DE TIPOS DE DADOS - MERCADO PAGO (Novembro 2025)', fontsize=20, fontweight='bold')

# 1. PAYMENT_METHODS - Pizza
ax1 = plt.subplot(2, 3, 1)
payment_methods = data['payment_methods']
labels = []
sizes = []
colors = []
explode = []

for pm, info in payment_methods.items():
    labels.append(f"{pm}\n{info['count']} ({info['percentage']:.1f}%)")
    sizes.append(info['count'])
    if info['include_in_reconciliation']:
        colors.append('#2ecc71')  # Verde - incluir
        explode.append(0)
    else:
        colors.append('#e74c3c')  # Vermelho - excluir
        explode.append(0.1)

ax1.pie(sizes, labels=labels, colors=colors, autopct='', startangle=90, explode=explode)
ax1.set_title('PAYMENT_METHOD\n(Arquivo Recebimentos)', fontsize=14, fontweight='bold')

# 2. TRANSACTION_TYPES - Pizza
ax2 = plt.subplot(2, 3, 2)
transaction_types = data['transaction_types']
labels = []
sizes = []
colors = []
explode = []

for tt, info in transaction_types.items():
    labels.append(f"{tt}\n{info['count']} ({info['percentage']:.1f}%)")
    sizes.append(info['count'])
    if info['include_in_reconciliation']:
        colors.append('#2ecc71')  # Verde - incluir
        explode.append(0)
    else:
        colors.append('#e74c3c')  # Vermelho - excluir
        explode.append(0.1)

ax2.pie(sizes, labels=labels, colors=colors, autopct='', startangle=90, explode=explode)
ax2.set_title('TRANSACTION_TYPE / DESCRIPTION\n(Arquivo Settlement)', fontsize=14, fontweight='bold')

# 3. Comparação de totais
ax3 = plt.subplot(2, 3, 3)
summary = data['insights']['summary']
categories = ['Total\nRecebimentos', 'Recebimentos\nVálidos', 'Total\nSettlement', 'Settlement\nVálidos']
values = [
    summary['total_recebimentos'],
    summary['recebimentos_valid_for_reconciliation'],
    summary['total_settlement'],
    summary['settlement_valid_for_reconciliation']
]
colors_bars = ['#3498db', '#2ecc71', '#3498db', '#2ecc71']

bars = ax3.bar(categories, values, color=colors_bars, edgecolor='black', linewidth=2)
for i, (bar, val) in enumerate(zip(bars, values)):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(val)}',
             ha='center', va='bottom', fontsize=12, fontweight='bold')

ax3.set_ylabel('Quantidade de Registros', fontsize=12)
ax3.set_title('Comparação de Totais', fontsize=14, fontweight='bold')
ax3.grid(axis='y', alpha=0.3)

# 4. Detalhamento de Payment Methods
ax4 = plt.subplot(2, 3, 4)
pm_data = []
for pm, info in payment_methods.items():
    pm_data.append({
        'method': pm,
        'count': info['count'],
        'include': info['include_in_reconciliation']
    })
df_pm = pd.DataFrame(pm_data)

# Separar em dois grupos
df_include = df_pm[df_pm['include'] == True].sort_values('count', ascending=True)
df_exclude = df_pm[df_pm['include'] == False].sort_values('count', ascending=True)

y_pos = 0
y_positions = []
labels_pm = []

for _, row in df_include.iterrows():
    ax4.barh(y_pos, row['count'], color='#2ecc71', edgecolor='black', linewidth=1)
    ax4.text(row['count'] + 10, y_pos, f"{row['method']}: {row['count']}",
             va='center', fontsize=10, fontweight='bold')
    y_positions.append(y_pos)
    labels_pm.append('')
    y_pos += 1

y_pos += 0.5  # Espaço

for _, row in df_exclude.iterrows():
    ax4.barh(y_pos, row['count'], color='#e74c3c', edgecolor='black', linewidth=1)
    ax4.text(row['count'] + 10, y_pos, f"{row['method']}: {row['count']}",
             va='center', fontsize=10, fontweight='bold')
    y_positions.append(y_pos)
    labels_pm.append('')
    y_pos += 1

ax4.set_yticks(y_positions)
ax4.set_yticklabels(labels_pm)
ax4.set_xlabel('Quantidade de Registros', fontsize=12)
ax4.set_title('Payment Methods Detalhados\n(Verde=Incluir, Vermelho=Excluir)', fontsize=14, fontweight='bold')
ax4.grid(axis='x', alpha=0.3)

# 5. Detalhamento de Transaction Types
ax5 = plt.subplot(2, 3, 5)
tt_data = []
for tt, info in transaction_types.items():
    tt_data.append({
        'type': tt,
        'count': info['count'],
        'include': info['include_in_reconciliation']
    })
df_tt = pd.DataFrame(tt_data)

# Separar em dois grupos
df_include_tt = df_tt[df_tt['include'] == True].sort_values('count', ascending=True)
df_exclude_tt = df_tt[df_tt['include'] == False].sort_values('count', ascending=True)

y_pos = 0
y_positions_tt = []
labels_tt = []

for _, row in df_include_tt.iterrows():
    ax5.barh(y_pos, row['count'], color='#2ecc71', edgecolor='black', linewidth=1)
    ax5.text(row['count'] + 10, y_pos, f"{row['type']}: {row['count']}",
             va='center', fontsize=10, fontweight='bold')
    y_positions_tt.append(y_pos)
    labels_tt.append('')
    y_pos += 1

y_pos += 0.5  # Espaço

for _, row in df_exclude_tt.iterrows():
    ax5.barh(y_pos, row['count'], color='#e74c3c', edgecolor='black', linewidth=1)
    ax5.text(row['count'] + 10, y_pos, f"{row['type']}: {row['count']}",
             va='center', fontsize=10, fontweight='bold')
    y_positions_tt.append(y_pos)
    labels_tt.append('')
    y_pos += 1

ax5.set_yticks(y_positions_tt)
ax5.set_yticklabels(labels_tt)
ax5.set_xlabel('Quantidade de Registros', fontsize=12)
ax5.set_title('Transaction Types Detalhados\n(Verde=Incluir, Vermelho=Excluir)', fontsize=14, fontweight='bold')
ax5.grid(axis='x', alpha=0.3)

# 6. Resumo de regras (texto)
ax6 = plt.subplot(2, 3, 6)
ax6.axis('off')

rules_text = """
REGRAS DE CONCILIAÇÃO

ARQUIVO RECEBIMENTOS:
✓ INCLUIR:
  • master, visa, elo, amex (1.207 registros)
  • RECORD_TYPE = 'release'
  • DESCRIPTION = 'payment'

✗ EXCLUIR:
  • available_money (112 registros)
  • DESCRIPTION = 'reserve_for_payout'

Campo: NET_CREDIT_AMOUNT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ARQUIVO SETTLEMENT:
✓ INCLUIR:
  • SETTLEMENT (381 registros)
  • REFUND (6 registros)

✗ EXCLUIR:
  • PAYOUTS (11 registros)
  • INSTALLMENT (1.244 registros) ⚠️
  • TRANSACTION_TYPE IS NULL

Campo: SETTLEMENT_NET_AMOUNT

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CRÍTICO: INSTALLMENT
• 75.76% dos registros são parcelas
• NÃO SOMAR (duplicaria valores!)
• Serve apenas para controle de fluxo
"""

ax6.text(0.1, 0.9, rules_text, fontsize=11, verticalalignment='top',
         family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout()
plt.savefig(r'C:\projetos_code\conciliacao_mercado_pago_ecommerce\data_types_analysis.png',
            dpi=300, bbox_inches='tight')
print("\nGráfico salvo em: C:\\projetos_code\\conciliacao_mercado_pago_ecommerce\\data_types_analysis.png")

plt.show()

print("\n" + "="*80)
print("VISUALIZAÇÃO CONCLUÍDA")
print("="*80)
