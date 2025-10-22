# Sistema de Conciliação Mercado Pago

Um sistema completo para controle de recebíveis, conciliação de vendas e projeção de fluxo de caixa para transações do Mercado Pago.

## 📋 Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Contribuindo](#contribuindo)

## 🎯 Sobre o Projeto

O Sistema de Conciliação Mercado Pago foi desenvolvido para resolver uma limitação operacional crítica: **o Mercado Pago não fornece arquivos com os lançamentos futuros de vendas parceladas**.

### 🔍 Contexto

O Mercado Pago disponibiliza dois arquivos principais:

- **Arquivo de Vendas** – Lista todas as transações, porém apenas a primeira parcela
- **Arquivo de Liberações** – Apresenta somente os valores efetivamente creditados

Esta estrutura impossibilita o controle previsional de fluxo de caixa, problema que nosso sistema resolve.

### 🎯 Objetivos

- ✅ Processar arquivos de vendas e gerar automaticamente as parcelas futuras
- ✅ Confrontar parcelas previstas com recebimentos efetivos
- ✅ Projeção detalhada do fluxo de caixa (diário/mensal)
- ✅ Identificação de divergências, atrasos, estornos e chargebacks

## ⚡ Funcionalidades

### 📊 Painel de Controle
- Indicadores consolidados de valores previstos, recebidos e pendentes
- Identificação de parcelas vencidas
- Projeção de recebimentos dos próximos dias

### 💰 Fluxo de Caixa
- Visualização agregada por dia ou mês
- Comparativo entre valores previstos e efetivamente recebidos

### 📋 Controle de Parcelas
- Listagem de parcelas pendentes e recebidas
- Detecção automática de divergências de valor

### 🔄 Conciliação Automática
- Conciliação automática entre arquivos de vendas e liberações
- Tratamento de estornos (refunds) e chargebacks
- Compatibilidade com todos os meios de pagamento (cartão, PIX, boleto, etc.)

### 📈 Relatórios
- Histórico completo de transações
- Filtros e visualizações configuráveis

## 📋 Pré-requisitos

### Software
- **Python 3.8+**
- **Pip** (gerenciador de pacotes Python)

### Arquivos do Mercado Pago
São necessários dois tipos de arquivos de exportação:

1. **Arquivo de Vendas** (export-activities)
   - Formato: `.xls` ou `.xlsx`
   - Diretório: `data/vendas/`

2. **Arquivo de Liberações** (reserve release)
   - Formato: `.xlsx`
   - Diretório: `data/recebimentos/`

## 🚀 Instalação

1. **Clone o repositório**
   ```bash
   git clone https://github.com/seu-usuario/mercadopago-reconciliation.git
   cd mercadopago-reconciliation
   ```

2. **Execute o setup**
   ```bash
   python setup.py
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

### 📦 Dependências Principais
- Flask
- Flask-CORS
- openpyxl
- python-dateutil

## 💻 Como Usar

### 🏁 Primeira Execução

1. **Organize os arquivos**
   ```
   data/
   ├── vendas/
   └── recebimentos/
   ```

2. **Inicie o servidor**
   ```bash
   python app.py
   ```

3. **Acesse a aplicação**
   ```
   http://localhost:9000
   ```

4. **Processe os dados**
   - Utilize o botão "Processar Dados" para iniciar
   - O sistema realizará:
     - ✅ Leitura e cálculo das parcelas futuras
     - ✅ Conciliação dos recebimentos
     - ✅ Geração da projeção de fluxo de caixa

### 📅 Utilização Diária

1. Baixe os novos arquivos de vendas e liberações do Mercado Pago
2. Salve-os nas respectivas pastas (`vendas/` e `recebimentos/`)
3. Execute o processamento para atualizar os dados

## 📁 Estrutura do Projeto

```
mercadopago-reconciliation/
│
├── app.py                    # Aplicação principal Flask
├── setup.py                  # Script de configuração inicial
├── requirements.txt          # Dependências do projeto
├── README.md                # Documentação
│
├── backend/                  # Lógica de negócio
│   ├── processors/          # Processadores de dados
│   │   ├── sales_processor.py      # Processamento de vendas
│   │   ├── releases_processor.py   # Processamento de liberações
│   │   └── reconciliator.py        # Motor de conciliação
│   └── utils/              # Utilitários
│       └── cashflow.py     # Cálculos de fluxo de caixa
│
├── frontend/               # Interface web
│   ├── static/            # Arquivos estáticos
│   │   ├── css/          # Estilos
│   │   └── js/           # Scripts JavaScript
│   └── templates/         # Templates HTML
│
└── data/                  # Diretório de dados
    ├── vendas/           # Arquivos de vendas do MP
    └── recebimentos/     # Arquivos de liberações do MP
```

## 🤝 Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

**Desenvolvido com ❤️ para facilitar a gestão financeira de vendas no Mercado Pago**
