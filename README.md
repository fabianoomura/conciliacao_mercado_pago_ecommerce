Sistema de Conciliação Mercado Pago

Sistema desenvolvido para controle de recebíveis, conciliação de vendas e projeção de fluxo de caixa provenientes do Mercado Pago.

Índice

Sobre o Projeto

Funcionalidades

Requisitos

Instalação

Como Usar

Estrutura do Projeto

API Endpoints

Troubleshooting

Contribuindo

Licença

Autor

Sobre o Projeto

O Sistema de Conciliação Mercado Pago foi desenvolvido para resolver uma limitação operacional: o Mercado Pago não fornece arquivos com os lançamentos futuros de vendas parceladas.

O sistema tem como objetivo:

Processar arquivos de vendas e gerar automaticamente as parcelas futuras.

Confrontar as parcelas previstas com os recebimentos efetivos.

Projeção detalhada do fluxo de caixa (por dia ou mês).

Identificação de divergências, atrasos, estornos e chargebacks.

Contexto

O Mercado Pago disponibiliza dois arquivos principais:

Arquivo de Vendas – lista todas as transações, porém somente a primeira parcela.

Arquivo de Liberações – apresenta apenas os valores efetivamente creditados.

Essa estrutura impossibilita o controle previsional de fluxo de caixa.
O sistema soluciona o problema ao calcular e registrar todas as parcelas futuras com base nas vendas originais.

Funcionalidades
Painel de Controle

Indicadores consolidados de valores previstos, recebidos e pendentes.

Identificação de parcelas vencidas.

Projeção de recebimentos dos próximos dias.

Fluxo de Caixa

Visualização agregada por dia ou por mês.

Comparativo entre valores previstos e efetivamente recebidos.

Controle de Parcelas

Listagem de parcelas pendentes e recebidas.

Detecção automática de divergências de valor.

Conciliação Automática

Conciliação automática entre arquivos de vendas e liberações.

Tratamento de estornos (refunds) e chargebacks.

Compatibilidade com todos os meios de pagamento (cartão, PIX, boleto, etc.).

Relatórios

Histórico completo de transações.

Filtros e visualizações configuráveis.

Requisitos
Software

Python 3.8 ou superior

Pip (gerenciador de pacotes Python)

Arquivos do Mercado Pago

São necessários dois tipos de arquivos de exportação:

Arquivo de Vendas (export-activities)

Formato: .xls ou .xlsx

Local: data/vendas/

Arquivo de Liberações (reserve release)

Formato: .xlsx

Local: data/recebimentos/

Instalação

1. Obter o Projeto
   git clone https://github.com/seu-usuario/mercadopago-reconciliation.git
   cd mercadopago-reconciliation

2. Executar o Setup
   python setup.py

3. Instalar Dependências
   pip install -r requirements.txt

Dependências principais:

Flask

Flask-CORS

openpyxl

python-dateutil

Como Usar
Primeira Execução

Organize os arquivos conforme o modelo:

data/
├── vendas/
└── recebimentos/

Inicie o servidor:

python app.py

Acesse:

http://localhost:9000

Utilize o botão “Processar Dados” para iniciar o processamento.

O sistema realizará:

Leitura e cálculo das parcelas futuras.

Conciliação dos recebimentos.

Geração da projeção de fluxo de caixa.

Utilização Diária

Baixe os novos arquivos de vendas e liberações do Mercado Pago.

Salve-os nas respectivas pastas (vendas e recebimentos).

Execute o processamento para atualizar os dados.

Estrutura do Projeto
mercadopago-reconciliation/
│
├── app.py
├── setup.py
├── requirements.txt
├── README.md
│
├── backend/
│ ├── processors/
│ │ ├── sales_processor.py
│ │ ├── releases_processor.py
│ │ └── reconciliator.py
│ └── utils/
│ └── cashflow.py
│
├── frontend/
│ ├── static/
│ │ ├── css/
│ │ └── js/
│ └── templates/
│
└── data/
├── vendas/
└── recebimentos/
