import os

def create_directory_structure():
    """Cria a estrutura de pastas do projeto"""
    directories = [
        'backend',
        'backend/processors',
        'backend/utils',
        'frontend',
        'frontend/static',
        'frontend/static/css',
        'frontend/static/js',
        'frontend/templates',
        'data',
        'data/vendas',
        'data/recebimentos'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Criado: {directory}")

def create_requirements():
    """Cria arquivo requirements.txt"""
    requirements = """Flask==3.0.0
Flask-CORS==4.0.0
openpyxl==3.1.2
python-dateutil==2.8.2
"""
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    
    print("✓ Arquivo 'requirements.txt' criado")

def create_gitignore():
    """Cria arquivo .gitignore"""
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# Arquivos de dados
data/vendas/*.xls
data/vendas/*.xlsx
data/recebimentos/*.xls
data/recebimentos/*.xlsx

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore)
    
    print("✓ Arquivo '.gitignore' criado")

def create_readme():
    """Cria arquivo README.md"""
    readme = """# Sistema de Conciliação Mercado Pago

Sistema para controle de recebíveis e conciliação de vendas do Mercado Pago.

## Instalação

1. Instalar dependências:
```bash
pip install -r requirements.txt
```

2. Executar setup (criar estrutura):
```bash
python setup.py
```

3. Iniciar o servidor:
```bash
python app.py
```

4. Acessar no navegador:
```
http://localhost:9000
```

## Uso

### Colocar Arquivos nas Pastas

1. **Arquivos de Vendas**: Coloque na pasta `data/vendas/`
   - Exemplo: 202501.xls, 202502.xls, etc.

2. **Arquivos de Recebimentos**: Coloque na pasta `data/recebimentos/`
   - Exemplo: reserverelease202501.xlsx, etc.

3. O sistema irá processar automaticamente todos os arquivos

## Estrutura do Projeto
```
mercadopago-reconciliation/
├── backend/
│   ├── processors/
│   └── utils/
├── frontend/
│   ├── static/
│   └── templates/
├── data/
│   ├── vendas/          <- Coloque arquivos .xls de vendas aqui
│   └── recebimentos/    <- Coloque arquivos .xlsx de recebimentos aqui
└── app.py
```
"""
    
    with open('README.md', 'w') as f:
        f.write(readme)
    
    print("✓ Arquivo 'README.md' criado")

def create_placeholder_files():
    """Cria arquivos .gitkeep para manter pastas vazias no git"""
    with open('data/vendas/.gitkeep', 'w') as f:
        f.write('')
    with open('data/recebimentos/.gitkeep', 'w') as f:
        f.write('')
    print("✓ Arquivos placeholder criados")

if __name__ == '__main__':
    print("=" * 60)
    print("SETUP - Sistema de Conciliação Mercado Pago")
    print("=" * 60)
    print()
    
    print("Criando estrutura de pastas...")
    create_directory_structure()
    print()
    
    print("Criando arquivos de configuração...")
    create_requirements()
    create_gitignore()
    create_readme()
    create_placeholder_files()
    print()
    
    print("=" * 60)
    print("✓ SETUP CONCLUÍDO COM SUCESSO!")
    print("=" * 60)
    print()
    print("Próximos passos:")
    print("1. Execute: pip install -r requirements.txt")
    print("2. Coloque seus arquivos nas pastas:")
    print("   - Vendas em: data/vendas/")
    print("   - Recebimentos em: data/recebimentos/")
    print("3. Aguarde os próximos códigos...")
    print()