import pandas as pd
import json
import sys
from collections import Counter
from pathlib import Path

# Configurar encoding UTF-8 para saída
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Caminhos dos arquivos
recebimentos_file = r'C:\projetos_code\conciliacao_mercado_pago_ecommerce\data\recebimentos\202511r.xlsx'
settlement_file = r'C:\projetos_code\conciliacao_mercado_pago_ecommerce\data\settlement\202511s.xlsx'

print("=" * 80)
print("ANÁLISE DE TIPOS DE DADOS - MERCADO PAGO")
print("=" * 80)

# Análise do arquivo de Recebimentos
print("\n1. ANALISANDO ARQUIVO DE RECEBIMENTOS (202511r.xlsx)")
print("-" * 80)

df_recebimentos = pd.read_excel(recebimentos_file)
print(f"\nColunas disponíveis: {list(df_recebimentos.columns)}")
print(f"Total de registros: {len(df_recebimentos)}")

# Procurar coluna de método de pagamento
payment_method_columns = [col for col in df_recebimentos.columns if 'PAYMENT' in col.upper() or 'METODO' in col.upper() or 'FORMA' in col.upper()]
print(f"\nColunas relacionadas a pagamento encontradas: {payment_method_columns}")

# Análise de PAYMENT_METHOD
payment_methods = {}
if payment_method_columns:
    for col in payment_method_columns:
        print(f"\n--- Analisando coluna: {col} ---")
        value_counts = df_recebimentos[col].value_counts()
        print(f"\nValores únicos encontrados: {len(value_counts)}")
        print("\nDistribuição completa:")
        for value, count in value_counts.items():
            print(f"  {value}: {count} ({count/len(df_recebimentos)*100:.2f}%)")

            # Guardar exemplos
            example_row = df_recebimentos[df_recebimentos[col] == value].iloc[0].to_dict()

            # Categorizar
            description = ""
            category = ""
            if pd.notna(value):
                value_str = str(value).lower()
                if 'credit' in value_str or 'credito' in value_str or 'visa' in value_str or 'master' in value_str:
                    category = "CARTÃO DE CRÉDITO"
                    description = "Pagamento via cartão de crédito"
                elif 'debit' in value_str or 'debito' in value_str:
                    category = "CARTÃO DE DÉBITO"
                    description = "Pagamento via cartão de débito"
                elif 'pix' in value_str:
                    category = "PIX"
                    description = "Pagamento instantâneo via PIX"
                elif 'boleto' in value_str:
                    category = "BOLETO"
                    description = "Pagamento via boleto bancário"
                elif 'account' in value_str or 'conta' in value_str:
                    category = "CONTA MERCADO PAGO"
                    description = "Pagamento via saldo em conta Mercado Pago"
                else:
                    category = "OUTRO"
                    description = "Método de pagamento não categorizado"
            else:
                category = "NÃO INFORMADO"
                description = "Método de pagamento não informado"

            payment_methods[str(value)] = {
                "count": int(count),
                "percentage": float(count/len(df_recebimentos)*100),
                "category": category,
                "description": description,
                "example": {k: str(v) for k, v in example_row.items()}
            }

# Mostrar algumas linhas de exemplo
print("\n\nExemplo de registros (primeiras 5 linhas):")
try:
    print(df_recebimentos.head().to_string())
except:
    print("(Erro ao exibir - caracteres especiais)")
    print(df_recebimentos.head()[['RELEASE_DATE', 'PAYMENT_METHOD', 'NET_CREDIT_AMOUNT', 'DESCRIPTION']].to_dict('records'))

# Análise do arquivo de Settlement
print("\n\n2. ANALISANDO ARQUIVO DE SETTLEMENT (202511s.xlsx)")
print("-" * 80)

df_settlement = pd.read_excel(settlement_file)
print(f"\nColunas disponíveis: {list(df_settlement.columns)}")
print(f"Total de registros: {len(df_settlement)}")

# Procurar coluna de tipo de transação
transaction_type_columns = [col for col in df_settlement.columns
                            if 'TYPE' in col.upper() or 'TIPO' in col.upper()
                            or 'DESCRIPTION' in col.upper() or 'DESCRI' in col.upper()]
print(f"\nColunas relacionadas a tipo de transação encontradas: {transaction_type_columns}")

# Análise de TRANSACTION_TYPE
transaction_types = {}
if transaction_type_columns:
    for col in transaction_type_columns:
        print(f"\n--- Analisando coluna: {col} ---")
        value_counts = df_settlement[col].value_counts()
        print(f"\nValores únicos encontrados: {len(value_counts)}")
        print("\nDistribuição completa:")
        for value, count in value_counts.items():
            print(f"  {value}: {count} ({count/len(df_settlement)*100:.2f}%)")

            # Guardar exemplos
            example_row = df_settlement[df_settlement[col] == value].iloc[0].to_dict()

            # Categorizar e explicar
            description = ""
            affects_reconciliation = False
            category = ""

            if pd.notna(value):
                value_str = str(value).lower()

                if 'settlement' in value_str or 'liquidação' in value_str or 'liberação' in value_str:
                    category = "SETTLEMENT"
                    description = "Liberação de valores recebidos - valores que entram na conta"
                    affects_reconciliation = True
                elif 'refund' in value_str or 'estorno' in value_str or 'devolução' in value_str:
                    category = "REFUND"
                    description = "Estorno de pagamento - devolução ao cliente"
                    affects_reconciliation = True
                elif 'chargeback' in value_str:
                    category = "CHARGEBACK"
                    description = "Contestação de pagamento pelo cliente"
                    affects_reconciliation = True
                elif 'fee' in value_str or 'taxa' in value_str or 'tarifa' in value_str:
                    category = "FEE"
                    description = "Taxas cobradas pelo Mercado Pago"
                    affects_reconciliation = True
                elif 'payout' in value_str or 'saque' in value_str or 'transferência' in value_str:
                    category = "PAYOUT"
                    description = "Transferência de valores para conta bancária"
                    affects_reconciliation = False
                elif 'payment' in value_str or 'pagamento' in value_str:
                    category = "PAYMENT"
                    description = "Registro de pagamento recebido"
                    affects_reconciliation = True
                elif 'reversal' in value_str or 'reversão' in value_str:
                    category = "REVERSAL"
                    description = "Reversão de transação"
                    affects_reconciliation = True
                elif 'adjustment' in value_str or 'ajuste' in value_str:
                    category = "ADJUSTMENT"
                    description = "Ajuste de valores"
                    affects_reconciliation = True
                else:
                    category = "OTHER"
                    description = "Tipo de transação não categorizado"
                    affects_reconciliation = False
            else:
                category = "NOT_INFORMED"
                description = "Tipo de transação não informado"
                affects_reconciliation = False

            transaction_types[str(value)] = {
                "count": int(count),
                "percentage": float(count/len(df_settlement)*100),
                "category": category,
                "description": description,
                "affects_reconciliation": affects_reconciliation,
                "example": {k: str(v) for k, v in example_row.items()}
            }

# Mostrar algumas linhas de exemplo
print("\n\nExemplo de registros (primeiras 5 linhas):")
try:
    print(df_settlement.head().to_string())
except:
    print("(Erro ao exibir - caracteres especiais)")
    # Mostrar apenas colunas principais
    main_cols = [col for col in df_settlement.columns if any(x in col.upper() for x in ['DATE', 'TYPE', 'DESCRIPTION', 'AMOUNT', 'ID'])][:5]
    if main_cols:
        print(df_settlement.head()[main_cols].to_dict('records'))

# Criar JSON final
print("\n\n3. GERANDO JSON CONSOLIDADO")
print("-" * 80)

result = {
    "payment_methods": payment_methods,
    "transaction_types": transaction_types,
    "insights": {
        "payment_methods_affect_reconciliation": True,
        "payment_methods_notes": "Os métodos de pagamento podem afetar prazos de liberação e taxas aplicadas",
        "transaction_types_affect_reconciliation": True,
        "transaction_types_notes": "Os tipos de transação são CRÍTICOS para conciliação: SETTLEMENT adiciona valores, REFUND/CHARGEBACK subtraem, FEES reduzem o valor líquido",
        "summary": {
            "total_recebimentos": len(df_recebimentos),
            "total_settlement": len(df_settlement),
            "unique_payment_methods": len(payment_methods),
            "unique_transaction_types": len(transaction_types)
        }
    }
}

# Salvar JSON
output_file = r'C:\projetos_code\conciliacao_mercado_pago_ecommerce\data_types_analysis.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"\nJSON salvo em: {output_file}")
print("\n" + "=" * 80)
print("ANÁLISE CONCLUÍDA!")
print("=" * 80)

# Exibir resumo
print("\n\nRESUMO EXECUTIVO:")
print("-" * 80)
print(f"Total de registros em Recebimentos: {len(df_recebimentos)}")
print(f"Total de registros em Settlement: {len(df_settlement)}")
print(f"\nMétodos de pagamento únicos: {len(payment_methods)}")
for method, data in list(payment_methods.items())[:10]:
    print(f"  - {method} ({data['category']}): {data['count']} registros ({data['percentage']:.2f}%)")
print(f"\nTipos de transação únicos: {len(transaction_types)}")
for ttype, data in list(transaction_types.items())[:10]:
    print(f"  - {ttype} ({data['category']}): {data['count']} registros ({data['percentage']:.2f}%)")
    print(f"    Afeta conciliação: {'SIM' if data['affects_reconciliation'] else 'NÃO'}")
