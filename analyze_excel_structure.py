import pandas as pd
import json
from pathlib import Path

def analyze_excel(file_path, file_type):
    """Analisa a estrutura de um arquivo Excel em detalhes"""
    print(f"\n{'='*80}")
    print(f"Analisando: {file_type} - {file_path}")
    print(f"{'='*80}\n")

    # Ler o arquivo
    df = pd.read_excel(file_path)

    analysis = {
        "arquivo": str(file_path),
        "tipo": file_type,
        "total_linhas": len(df),
        "total_colunas": len(df.columns),
        "colunas": {}
    }

    # Análise de cada coluna
    for col in df.columns:
        col_analysis = {
            "nome_coluna": col,
            "tipo_dados": str(df[col].dtype),
            "valores_nulos": int(df[col].isnull().sum()),
            "valores_nao_nulos": int(df[col].notnull().sum()),
            "percentual_nulos": round(df[col].isnull().sum() / len(df) * 100, 2),
            "valores_unicos": int(df[col].nunique()),
            "primeiros_3_valores": []
        }

        # Pegar primeiros 3 valores (convertendo para tipos serializáveis)
        for val in df[col].head(3):
            if pd.isna(val):
                col_analysis["primeiros_3_valores"].append(None)
            elif isinstance(val, (pd.Timestamp, pd.DatetimeTZDtype)):
                col_analysis["primeiros_3_valores"].append(str(val))
            elif isinstance(val, (int, float)):
                col_analysis["primeiros_3_valores"].append(float(val) if not pd.isna(val) else None)
            else:
                col_analysis["primeiros_3_valores"].append(str(val))

        analysis["colunas"][col] = col_analysis

    # Verificar duplicatas em colunas candidatas a chave primária
    potential_keys = []
    for col in df.columns:
        if df[col].nunique() == len(df) and df[col].notnull().all():
            potential_keys.append(col)

    analysis["chaves_primarias_candidatas"] = potential_keys

    # Verificar duplicatas gerais (todas as colunas)
    duplicates_count = df.duplicated().sum()
    analysis["linhas_duplicadas_completas"] = int(duplicates_count)

    # Primeiras 3 linhas completas como exemplo
    analysis["exemplo_primeiras_3_linhas"] = []
    for idx in range(min(3, len(df))):
        row_dict = {}
        for col in df.columns:
            val = df.iloc[idx][col]
            if pd.isna(val):
                row_dict[col] = None
            elif isinstance(val, (pd.Timestamp, pd.DatetimeTZDtype)):
                row_dict[col] = str(val)
            elif isinstance(val, (int, float)):
                row_dict[col] = float(val) if not pd.isna(val) else None
            else:
                row_dict[col] = str(val)
        analysis["exemplo_primeiras_3_linhas"].append(row_dict)

    return analysis, df

# Arquivos a analisar
settlement_file = "c:/projetos_code/conciliacao_mercado_pago_ecommerce/data/settlement/202511s.xlsx"
recebimentos_file = "c:/projetos_code/conciliacao_mercado_pago_ecommerce/data/recebimentos/202511r.xlsx"

# Analisar ambos os arquivos
settlement_analysis, settlement_df = analyze_excel(settlement_file, "Settlement (Esperado)")
recebimentos_analysis, recebimentos_df = analyze_excel(recebimentos_file, "Recebimentos/Releases (Recebido)")

# Criar análise completa
full_analysis = {
    "settlement": settlement_analysis,
    "recebimentos": recebimentos_analysis
}

# Salvar JSON
output_file = "c:/projetos_code/conciliacao_mercado_pago_ecommerce/analise_estrutura_excel.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(full_analysis, f, indent=2, ensure_ascii=False)

print(f"\n{'='*80}")
print(f"ANÁLISE COMPLETA SALVA EM: {output_file}")
print(f"{'='*80}\n")

# Imprimir resumo
print("\n" + "="*80)
print("RESUMO - SETTLEMENT (Esperado)")
print("="*80)
print(f"Total de linhas: {settlement_analysis['total_linhas']}")
print(f"Total de colunas: {settlement_analysis['total_colunas']}")
print(f"Colunas: {list(settlement_analysis['colunas'].keys())}")
print(f"Chaves primárias candidatas: {settlement_analysis['chaves_primarias_candidatas']}")
print(f"Linhas duplicadas completas: {settlement_analysis['linhas_duplicadas_completas']}")

print("\n" + "="*80)
print("RESUMO - RECEBIMENTOS (Recebido)")
print("="*80)
print(f"Total de linhas: {recebimentos_analysis['total_linhas']}")
print(f"Total de colunas: {recebimentos_analysis['total_colunas']}")
print(f"Colunas: {list(recebimentos_analysis['colunas'].keys())}")
print(f"Chaves primárias candidatas: {recebimentos_analysis['chaves_primarias_candidatas']}")
print(f"Linhas duplicadas completas: {recebimentos_analysis['linhas_duplicadas_completas']}")

print("\n" + "="*80)
print("DETALHES DAS COLUNAS - SETTLEMENT")
print("="*80)
for col_name, col_info in settlement_analysis['colunas'].items():
    print(f"\n{col_name}:")
    print(f"  Tipo: {col_info['tipo_dados']}")
    print(f"  Nulos: {col_info['valores_nulos']} ({col_info['percentual_nulos']}%)")
    print(f"  Valores únicos: {col_info['valores_unicos']}")
    print(f"  Primeiros 3: {col_info['primeiros_3_valores']}")

print("\n" + "="*80)
print("DETALHES DAS COLUNAS - RECEBIMENTOS")
print("="*80)
for col_name, col_info in recebimentos_analysis['colunas'].items():
    print(f"\n{col_name}:")
    print(f"  Tipo: {col_info['tipo_dados']}")
    print(f"  Nulos: {col_info['valores_nulos']} ({col_info['percentual_nulos']}%)")
    print(f"  Valores únicos: {col_info['valores_unicos']}")
    print(f"  Primeiros 3: {col_info['primeiros_3_valores']}")

print("\n" + "="*80)
print("EXEMPLO LINHA 1 - SETTLEMENT")
print("="*80)
if settlement_analysis['exemplo_primeiras_3_linhas']:
    for key, value in settlement_analysis['exemplo_primeiras_3_linhas'][0].items():
        print(f"{key}: {value}")

print("\n" + "="*80)
print("EXEMPLO LINHA 1 - RECEBIMENTOS")
print("="*80)
if recebimentos_analysis['exemplo_primeiras_3_linhas']:
    for key, value in recebimentos_analysis['exemplo_primeiras_3_linhas'][0].items():
        print(f"{key}: {value}")
