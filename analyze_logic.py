import pandas as pd
import json

# Ler os arquivos
settlement_file = "c:/projetos_code/conciliacao_mercado_pago_ecommerce/data/settlement/202511s.xlsx"
recebimentos_file = "c:/projetos_code/conciliacao_mercado_pago_ecommerce/data/recebimentos/202511r.xlsx"

settlement_df = pd.read_excel(settlement_file)
recebimentos_df = pd.read_excel(recebimentos_file)

print("="*80)
print("ANÁLISE DE LÓGICA E ESTRUTURA")
print("="*80)

# SETTLEMENT - Análise de duplicatas por EXTERNAL_REFERENCE
print("\n" + "="*80)
print("SETTLEMENT - Análise de EXTERNAL_REFERENCE")
print("="*80)
ext_ref_counts = settlement_df['EXTERNAL_REFERENCE'].value_counts()
duplicated_refs = ext_ref_counts[ext_ref_counts > 1]
print(f"Total de EXTERNAL_REFERENCE únicos: {settlement_df['EXTERNAL_REFERENCE'].nunique()}")
print(f"EXTERNAL_REFERENCE com múltiplas linhas: {len(duplicated_refs)}")
print(f"\nExemplos de EXTERNAL_REFERENCE duplicados:")
for ref, count in duplicated_refs.head(5).items():
    print(f"  {ref}: {count} linhas")
    subset = settlement_df[settlement_df['EXTERNAL_REFERENCE'] == ref][
        ['EXTERNAL_REFERENCE', 'SOURCE_ID', 'DESCRIPTION', 'INSTALLMENT_NUMBER',
         'TRANSACTION_AMOUNT', 'SETTLEMENT_NET_AMOUNT', 'INSTALLMENT_NET_AMOUNT']
    ]
    print(subset.to_string(index=False))
    print()

# Análise dos tipos de TRANSACTION_TYPE no Settlement
print("\n" + "="*80)
print("SETTLEMENT - Tipos de transação")
print("="*80)
print(settlement_df['TRANSACTION_TYPE'].value_counts())
print(f"\nDetalhes dos tipos:")
for ttype in settlement_df['TRANSACTION_TYPE'].dropna().unique():
    count = len(settlement_df[settlement_df['TRANSACTION_TYPE'] == ttype])
    print(f"\n{ttype}: {count} linhas")
    subset = settlement_df[settlement_df['TRANSACTION_TYPE'] == ttype].head(2)[
        ['EXTERNAL_REFERENCE', 'TRANSACTION_TYPE', 'DESCRIPTION',
         'TRANSACTION_AMOUNT', 'SETTLEMENT_NET_AMOUNT', 'INSTALLMENT_NET_AMOUNT']
    ]
    print(subset.to_string(index=False))

# Análise de DESCRIPTION no Settlement
print("\n" + "="*80)
print("SETTLEMENT - Valores únicos de DESCRIPTION")
print("="*80)
print(settlement_df['DESCRIPTION'].value_counts())

# Análise de INSTALLMENT_NUMBER no Settlement
print("\n" + "="*80)
print("SETTLEMENT - Valores de INSTALLMENT_NUMBER")
print("="*80)
print(settlement_df['INSTALLMENT_NUMBER'].value_counts().head(10))

# RECEBIMENTOS - Análise de RECORD_TYPE
print("\n" + "="*80)
print("RECEBIMENTOS - Tipos de registro")
print("="*80)
print(recebimentos_df['RECORD_TYPE'].value_counts())
print(f"\nDetalhes dos tipos:")
for rtype in recebimentos_df['RECORD_TYPE'].unique():
    count = len(recebimentos_df[recebimentos_df['RECORD_TYPE'] == rtype])
    print(f"\n{rtype}: {count} linhas")
    subset = recebimentos_df[recebimentos_df['RECORD_TYPE'] == rtype].head(2)[
        ['EXTERNAL_REFERENCE', 'RECORD_TYPE', 'DESCRIPTION',
         'NET_CREDIT_AMOUNT', 'GROSS_AMOUNT', 'INSTALLMENTS']
    ]
    print(subset.to_string(index=False))

# Análise de DESCRIPTION no Recebimentos
print("\n" + "="*80)
print("RECEBIMENTOS - Valores de DESCRIPTION")
print("="*80)
print(recebimentos_df['DESCRIPTION'].value_counts())

# Análise de INSTALLMENTS no Recebimentos
print("\n" + "="*80)
print("RECEBIMENTOS - Valores de INSTALLMENTS")
print("="*80)
print(recebimentos_df['INSTALLMENTS'].value_counts().head(15))

# Análise de valores financeiros
print("\n" + "="*80)
print("SETTLEMENT - Análise de valores financeiros")
print("="*80)
print(f"Soma TRANSACTION_AMOUNT: R$ {settlement_df['TRANSACTION_AMOUNT'].sum():.2f}")
print(f"Soma SETTLEMENT_NET_AMOUNT: R$ {settlement_df['SETTLEMENT_NET_AMOUNT'].sum():.2f}")
print(f"Soma FEE_AMOUNT: R$ {settlement_df['FEE_AMOUNT'].sum():.2f}")
print(f"Soma INSTALLMENT_NET_AMOUNT: R$ {settlement_df['INSTALLMENT_NET_AMOUNT'].sum():.2f}")

print("\n" + "="*80)
print("RECEBIMENTOS - Análise de valores financeiros")
print("="*80)
print(f"Soma NET_CREDIT_AMOUNT: R$ {recebimentos_df['NET_CREDIT_AMOUNT'].sum():.2f}")
print(f"Soma NET_DEBIT_AMOUNT: R$ {recebimentos_df['NET_DEBIT_AMOUNT'].sum():.2f}")
print(f"Soma GROSS_AMOUNT: R$ {recebimentos_df['GROSS_AMOUNT'].sum():.2f}")
print(f"Soma MP_FEE_AMOUNT: R$ {recebimentos_df['MP_FEE_AMOUNT'].sum():.2f}")

# Análise de chaves: SOURCE_ID e EXTERNAL_REFERENCE
print("\n" + "="*80)
print("SETTLEMENT - Análise de chave composta SOURCE_ID + EXTERNAL_REFERENCE")
print("="*80)
settlement_df['CHAVE_COMPOSTA'] = settlement_df['SOURCE_ID'].astype(str) + '_' + settlement_df['EXTERNAL_REFERENCE'].fillna('NULL')
duplicates_source_ext = settlement_df['CHAVE_COMPOSTA'].value_counts()
duplicates_source_ext = duplicates_source_ext[duplicates_source_ext > 1]
print(f"Combinações SOURCE_ID + EXTERNAL_REFERENCE duplicadas: {len(duplicates_source_ext)}")

print("\n" + "="*80)
print("RECEBIMENTOS - Análise de chave composta SOURCE_ID + EXTERNAL_REFERENCE")
print("="*80)
recebimentos_df['CHAVE_COMPOSTA'] = recebimentos_df['SOURCE_ID'].fillna(0).astype(str) + '_' + recebimentos_df['EXTERNAL_REFERENCE'].fillna('NULL')
duplicates_rec = recebimentos_df['CHAVE_COMPOSTA'].value_counts()
duplicates_rec = duplicates_rec[duplicates_rec > 1]
print(f"Combinações SOURCE_ID + EXTERNAL_REFERENCE duplicadas: {len(duplicates_rec)}")

# Verificar se SOURCE_ID é único
print("\n" + "="*80)
print("SETTLEMENT - SOURCE_ID como chave primária?")
print("="*80)
print(f"SOURCE_ID únicos: {settlement_df['SOURCE_ID'].nunique()}")
print(f"Total de linhas: {len(settlement_df)}")
print(f"SOURCE_ID é chave primária? {settlement_df['SOURCE_ID'].nunique() == len(settlement_df)}")

source_id_counts = settlement_df['SOURCE_ID'].value_counts()
duplicated_source_ids = source_id_counts[source_id_counts > 1]
print(f"SOURCE_ID com múltiplas linhas: {len(duplicated_source_ids)}")
if len(duplicated_source_ids) > 0:
    print(f"\nExemplos de SOURCE_ID duplicados:")
    for sid, count in duplicated_source_ids.head(3).items():
        print(f"\n  SOURCE_ID {sid}: {count} linhas")
        subset = settlement_df[settlement_df['SOURCE_ID'] == sid][
            ['SOURCE_ID', 'EXTERNAL_REFERENCE', 'DESCRIPTION', 'INSTALLMENT_NUMBER',
             'TRANSACTION_AMOUNT', 'INSTALLMENT_NET_AMOUNT']
        ]
        print(subset.to_string(index=False))

print("\n" + "="*80)
print("RECEBIMENTOS - SOURCE_ID como chave primária?")
print("="*80)
print(f"SOURCE_ID únicos (não nulos): {recebimentos_df['SOURCE_ID'].dropna().nunique()}")
print(f"Total de linhas: {len(recebimentos_df)}")
print(f"SOURCE_ID é chave primária? {recebimentos_df['SOURCE_ID'].dropna().nunique() == len(recebimentos_df[recebimentos_df['SOURCE_ID'].notna()])}")

# Análise de correspondência entre arquivos
print("\n" + "="*80)
print("CORRESPONDÊNCIA ENTRE ARQUIVOS")
print("="*80)

# EXTERNAL_REFERENCE
settlement_refs = set(settlement_df['EXTERNAL_REFERENCE'].dropna())
recebimentos_refs = set(recebimentos_df['EXTERNAL_REFERENCE'].dropna())

print(f"\nEXTERNAL_REFERENCE em Settlement: {len(settlement_refs)}")
print(f"EXTERNAL_REFERENCE em Recebimentos: {len(recebimentos_refs)}")
print(f"EXTERNAL_REFERENCE em ambos: {len(settlement_refs.intersection(recebimentos_refs))}")
print(f"EXTERNAL_REFERENCE apenas em Settlement: {len(settlement_refs - recebimentos_refs)}")
print(f"EXTERNAL_REFERENCE apenas em Recebimentos: {len(recebimentos_refs - settlement_refs)}")

# SOURCE_ID
settlement_sources = set(settlement_df['SOURCE_ID'].dropna())
recebimentos_sources = set(recebimentos_df['SOURCE_ID'].dropna())

print(f"\nSOURCE_ID em Settlement: {len(settlement_sources)}")
print(f"SOURCE_ID em Recebimentos: {len(recebimentos_sources)}")
print(f"SOURCE_ID em ambos: {len(settlement_sources.intersection(recebimentos_sources))}")
print(f"SOURCE_ID apenas em Settlement: {len(settlement_sources - recebimentos_sources)}")
print(f"SOURCE_ID apenas em Recebimentos: {len(recebimentos_sources - settlement_sources)}")
