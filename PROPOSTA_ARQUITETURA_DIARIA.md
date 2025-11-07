# Proposta de Arquitetura: Processamento por DIA

## 🎯 Problemas Atuais

1. **Ler tudo de uma vez** → 10K+ transações simultaneamente
2. **Sem persistência** → perder dados se falhar
3. **Difícil debugar** → quando falha, não sabe em qual dia
4. **Sem histórico** → não sabe o que já foi processado
5. **Muitos erros acumulados** → sem rastreabilidade

---

## 💡 Solução Proposta: Processamento Diário com Persistência

### Opção A: SQLite (Recomendado para MVP)

```
┌─────────────────────────────────────────────────────────────────┐
│ SQLite Database (data/mp_recebiveis.db)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ TABELAS:                                                        │
│ ├─ processing_log                                              │
│ │  ├─ date (YYYYMMDD)                                          │
│ │  ├─ status (pending, processing, completed, failed)         │
│ │  ├─ settlement_count (int)                                  │
│ │  ├─ recebimentos_count (int)                                │
│ │  └─ error_msg (text)                                        │
│ │                                                               │
│ ├─ settlements                                                  │
│ │  ├─ id (PK)                                                  │
│ │  ├─ date                                                     │
│ │  ├─ source_id                                               │
│ │  ├─ external_reference                                      │
│ │  ├─ transaction_type                                        │
│ │  ├─ amount                                                  │
│ │  ├─ refund_amount                                           │
│ │  ├─ chargeback_amount                                       │
│ │  └─ raw_data (JSON)                                         │
│ │                                                               │
│ ├─ recebimentos                                                │
│ │  ├─ id (PK)                                                  │
│ │  ├─ date                                                     │
│ │  ├─ release_date                                            │
│ │  ├─ external_reference                                      │
│ │  ├─ description                                             │
│ │  ├─ amount                                                  │
│ │  ├─ payment_type                                            │
│ │  └─ raw_data (JSON)                                         │
│ │                                                               │
│ ├─ installments                                                │
│ │  ├─ id (PK)                                                  │
│ │  ├─ processing_date                                         │
│ │  ├─ external_reference (FK)                                 │
│ │  ├─ installment_number                                      │
│ │  ├─ total_installments                                      │
│ │  ├─ amount_original                                         │
│ │  ├─ amount_final                                            │
│ │  ├─ refund_applied                                          │
│ │  ├─ status                                                  │
│ │  └─ received_date                                           │
│ │                                                               │
│ └─ reconciliation_results                                      │
│    ├─ id (PK)                                                  │
│    ├─ date                                                     │
│    ├─ external_reference (FK)                                 │
│    ├─ status                                                  │
│    ├─ received_amount                                         │
│    ├─ expected_amount                                         │
│    ├─ difference                                              │
│    └─ error_msg                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Vantagens:**
- ✅ Sem dependências externas
- ✅ Fácil de deployar
- ✅ Rápido para MVP
- ✅ Suporta queries complexas
- ✅ Arquivo único (backup fácil)

**Desvantagens:**
- ⚠️ Não é distribuído
- ⚠️ Performance limitada em grandes volumes
- ⚠️ Concorrência limitada

---

### Opção B: PostgreSQL (Recomendado para Produção)

```
docker-compose.yml
└─ PostgreSQL 14
   ├─ Schemas:
   │  ├─ settlement
   │  ├─ recebimentos
   │  └─ reconciliation
   │
   ├─ Tabelas: (mesmo que SQLite, mas otimizadas)
   ├─ Índices: por date, external_reference, status
   ├─ Partições: por mês (settlement_202501, settlement_202502, etc.)
   └─ Backups: automáticos diários
```

**Vantagens:**
- ✅ Distribuído
- ✅ Alta performance
- ✅ Escalável
- ✅ Segurança
- ✅ Backups nativos
- ✅ Pronto para múltiplos usuários

**Desvantagens:**
- ⚠️ Precisa infra (Docker/Cloud)
- ⚠️ Setup mais complexo
- ⚠️ Custo operacional

---

### Opção C: Híbrida (Recomendado para Melhor Solução)

```
Sistema de Processamento em Fases
├── FASE 1: Ingestion (Banco de Dados)
│   ├─ Ler settlement do dia
│   ├─ Salvar em settlement_staging
│   ├─ Ler recebimentos do dia
│   └─ Salvar em recebimentos_staging
│
├── FASE 2: Processamento em Memória (Cache)
│   ├─ Carregar settlement_staging
│   ├─ Carregar recebimentos_staging
│   ├─ Processar (settlement processor → reconciliador)
│   └─ Calcular status de cada parcela
│
├── FASE 3: Persistência (Banco de Dados)
│   ├─ Salvar installments finais
│   ├─ Salvar reconciliation_results
│   ├─ Marcar processing_log como 'completed'
│   └─ Limpar staging tables
│
└── FASE 4: API (Queries do Banco)
    ├─ GET /api/orders?date=YYYYMMDD
    ├─ GET /api/installments?date=YYYYMMDD&status=pending
    └─ GET /api/cashflow?date_start&date_end
```

---

## 🔄 Fluxo de Processamento Diário Recomendado

### Arquitetura Proposta:

```python
class DailyProcessor:
    """Processa dados dia a dia"""

    def __init__(self, db_path, data_dir):
        self.db = Database(db_path)
        self.data_dir = data_dir

    def run(self):
        """Executa para todos os dias faltando"""
        pending_dates = self.db.get_pending_dates()

        for date in pending_dates:
            try:
                self.process_day(date)
            except Exception as e:
                self.db.log_error(date, str(e))

    def process_day(self, date: str):  # YYYYMMDD
        """Processa um dia específico"""

        print(f"📅 Processando {date}...")

        # PASSO 1: Ler do arquivo
        settlement_data = self._read_settlement(date)
        recebimento_data = self._read_recebimento(date)

        self.db.save_staging_settlement(date, settlement_data)
        self.db.save_staging_recebimento(date, recebimento_data)

        # PASSO 2: Processar em memória
        installments = self._process_settlement(settlement_data)
        payments = self._process_recebimento(recebimento_data)

        # PASSO 3: Conciliar
        results = self._reconcile(installments, payments)

        # PASSO 4: Salvar resultados finais
        self.db.save_installments(date, results['installments'])
        self.db.save_reconciliation(date, results['summary'])

        # PASSO 5: Marcar como completo
        self.db.mark_date_completed(date)

        print(f"✅ {date}: {len(results['installments'])} parcelas, {results['summary']['matched']} conciliadas")
```

---

## 📋 Estrutura de Diretórios

```
data/
├── settlement/          (Excel brutos)
│   ├── 202501s.xlsx
│   └── ...
│
├── recebimentos/        (Excel brutos)
│   ├── 202501r.xlsx
│   └── ...
│
├── processed/           (Copias processadas)
│   ├── settlement/
│   │   ├── 202501s_processed.json
│   │   └── ...
│   └── recebimentos/
│       ├── 202501r_processed.json
│       └── ...
│
├── logs/                (Logs de processamento)
│   ├── 2025-01-15.log
│   ├── 2025-01-16.log
│   └── ...
│
└── mp_recebiveis.db     (SQLite)
    └── (tabelas acima)
```

---

## 🛠️ Implementação Recomendada

### Passo 1: Criar o Schema SQL

```sql
-- Para SQLite
CREATE TABLE processing_log (
    date TEXT PRIMARY KEY,
    status TEXT DEFAULT 'pending',
    settlement_count INT,
    recebimentos_count INT,
    installments_count INT,
    reconciliation_count INT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_msg TEXT
);

CREATE TABLE settlements (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    source_id TEXT,
    external_reference TEXT NOT NULL,
    transaction_type TEXT,
    amount REAL,
    refund_amount REAL,
    chargeback_amount REAL,
    raw_data TEXT,  -- JSON
    INDEX idx_date (date),
    INDEX idx_external_ref (external_reference)
);

CREATE TABLE installments (
    id INTEGER PRIMARY KEY,
    processing_date TEXT NOT NULL,
    external_reference TEXT NOT NULL,
    installment_number TEXT,
    total_installments INT,
    amount_original REAL,
    amount_final REAL,
    refund_applied REAL,
    status TEXT,
    received_date TEXT,
    raw_data TEXT,  -- JSON
    INDEX idx_date (processing_date),
    INDEX idx_external_ref (external_reference),
    INDEX idx_status (status)
);

-- E assim por diante...
```

### Passo 2: Criar Database Manager

```python
class DatabaseManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)

    def get_pending_dates(self) -> List[str]:
        """Retorna datas que ainda não foram processadas"""
        query = """
        SELECT DISTINCT strftime('%Y%m%d', ORIGIN_DATE) as date
        FROM settlements
        WHERE date NOT IN (SELECT date FROM processing_log WHERE status = 'completed')
        ORDER BY date
        """
        return self.query(query)

    def mark_date_processing(self, date: str):
        """Marca data como 'processando'"""
        self.execute(
            "INSERT INTO processing_log (date, status, started_at) VALUES (?, ?, ?)",
            (date, 'processing', datetime.now())
        )

    def mark_date_completed(self, date: str):
        """Marca data como 'completa'"""
        self.execute(
            "UPDATE processing_log SET status = 'completed', completed_at = ? WHERE date = ?",
            (datetime.now(), date)
        )
```

### Passo 3: Adaptar Processadores

```python
class SettlementProcessor:
    def process_by_date(self, date: str, df: DataFrame):
        """Processa settlement apenas do dia especificado"""
        df_day = df[df['ORIGIN_DATE'].dt.strftime('%Y%m%d') == date]

        installments = []
        for _, row in df_day.iterrows():
            installment = self._create_installment(row)
            installments.append(installment)

        return installments
```

---

## 🎯 Minha Recomendação

### Para MVP (Próximas 2 semanas):

**Usar SQLite + Processamento Diário**

```
Benefícios:
├─ Rápido de implementar
├─ Sem dependências externas
├─ Fácil de debugar (ver o que foi processado cada dia)
├─ Suporta rollback (se erro, volta ao início do dia)
├─ Preparação para PostgreSQL depois
└─ Custo zero
```

### Para Produção (Depois):

**Migrar para PostgreSQL**

```
Benefícios:
├─ Multi-usuário
├─ Alta performance
├─ Escalável
├─ Backups automáticos
├─ Pronto para múltiplas instâncias
└─ Segurança robusta
```

---

## 📊 Exemplo de Fluxo Diário

```
Dia 2025-01-15:

1. Sistema verifica: "Há dados novos de 2025-01-15?"
   └─ Sim! settlement_202501s.xlsx tem 10 transações de 15/01
   └─ Sim! recebimentos_202501r.xlsx tem 5 transações de 15/01

2. Marca data como "processando"
   └─ INSERT INTO processing_log VALUES ('20250115', 'processing', ...)

3. Lê dados do dia
   └─ Settlement: 10 transações
   └─ Recebimentos: 5 transações

4. Processa em memória
   └─ Settlement Processor: 10 transações → 25 parcelas
   └─ Releases Processor: 5 transações → 5 payments + 0 movements

5. Concilia
   └─ Reconciliador: 25 parcelas + 5 payments → 25 parcelas com status

6. Salva no banco
   └─ INSERT INTO installments (25 linhas)
   └─ INSERT INTO reconciliation_results (25 linhas)
   └─ UPDATE processing_log SET status = 'completed'

7. Resultado:
   ✅ 20250115: 10 settlement + 5 recebimentos = 25 parcelas conciliadas

Dia 2025-01-16: Repete para o próximo dia...
```

---

## ⚠️ Benefícios de Processar por Dia

1. **Isolamento**: Um dia ruim não quebra todos
2. **Rastreabilidade**: Você sabe EXATAMENTE qual dia falhou
3. **Recuperação**: Se falhar dia 5, reprocessa só dia 5
4. **Debug**: Mais fácil encontrar o erro
5. **Performance**: Dados em chunks menores = menos memória
6. **Auditoria**: Log completo de o que foi processado
7. **Backfill**: Pode processar histórico dia a dia
8. **Incrementalidade**: Processa só o que não foi processado ainda

---

## ✅ Checklist de Implementação

- [ ] Criar schema SQL (settlement, installments, reconciliation_results)
- [ ] Criar DatabaseManager com métodos básicos
- [ ] Adaptar SettlementProcessor para processar por data
- [ ] Adaptar ReleasesProcessor para processar por data
- [ ] Criar DailyProcessor que orquestra tudo
- [ ] Adicionar logging detalhado
- [ ] Adicionar rollback/retry logic
- [ ] Criar migrations para schema
- [ ] Testar com dados de um único dia
- [ ] Testar com dados de múltiplos dias
- [ ] Criar API para consultar resultados
- [ ] Documentar schema do banco

---

## 💻 Próximos Passos

1. **Qual opção você prefere?**
   - A (SQLite) - Rápido, MVP
   - B (PostgreSQL) - Production, escalável
   - C (Híbrida) - Melhor balanço

2. **Quer começar com SQLite agora e migrar depois?**

3. **Ou prefere ir direto para PostgreSQL?**

Me diga e começamos a implementação! 🚀
