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
        'data/settlement',
        'data/recebimentos'
    ]

    print("Criando estrutura de pastas...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✓ {directory}")

def create_requirements():
    """Cria arquivo requirements.txt com dependências do projeto"""
    requirements = """Flask==3.0.0
Flask-CORS==4.0.0
openpyxl==3.1.2
python-dateutil==2.8.2
pandas==2.1.0
xlrd==2.0.1
"""

    if not os.path.exists('requirements.txt'):
        with open('requirements.txt', 'w') as f:
            f.write(requirements)
        print("  ✓ requirements.txt criado")
    else:
        print("  → requirements.txt já existe (não sobrescrito)")

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

# Arquivos de dados sensíveis
data/settlement/*.xls
data/settlement/*.xlsx
data/settlement/*.csv
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

    if not os.path.exists('.gitignore'):
        with open('.gitignore', 'w') as f:
            f.write(gitignore)
        print("  ✓ .gitignore criado")
    else:
        print("  → .gitignore já existe (não sobrescrito)")

def update_init_files():
    """Cria arquivo __init__.py nos módulos Python"""
    init_files = [
        'backend/__init__.py',
        'backend/processors/__init__.py',
        'backend/utils/__init__.py'
    ]

    for init_file in init_files:
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('')
            print(f"  ✓ {init_file} criado")

def create_placeholder_files():
    """Cria arquivos .gitkeep para manter pastas vazias no git"""
    placeholders = [
        'data/settlement/.gitkeep',
        'data/recebimentos/.gitkeep'
    ]

    for placeholder in placeholders:
        if not os.path.exists(placeholder):
            with open(placeholder, 'w') as f:
                f.write('')

    print("  ✓ Arquivos .gitkeep criados")

def print_summary():
    """Imprime resumo dos arquivos do sistema"""
    print("\nArquivos do sistema detectados:")

    # Verificar processadores
    processors = [
        'backend/processors/settlement_processor.py',
        'backend/processors/releases_processor.py',
        'backend/processors/reconciliator.py',
        'backend/processors/movements_processor.py'
    ]

    print("\n  Processadores:")
    for proc in processors:
        status = "✓" if os.path.exists(proc) else "✗"
        print(f"    {status} {proc}")

    # Verificar utils
    utils_files = [
        'backend/utils/cashflow.py'
    ]

    print("\n  Utils:")
    for file in utils_files:
        status = "✓" if os.path.exists(file) else "✗"
        print(f"    {status} {file}")

    # Verificar app
    app_status = "✓" if os.path.exists('app.py') else "✗"
    print(f"\n  Backend:")
    print(f"    {app_status} app.py")

    # Verificar frontend
    frontend_files = [
        'frontend/templates/index.html',
        'frontend/static/js/app.js',
        'frontend/static/css/style.css'
    ]

    print("\n  Frontend:")
    for file in frontend_files:
        status = "✓" if os.path.exists(file) else "✗"
        print(f"    {status} {file}")

if __name__ == '__main__':
    print("=" * 70)
    print(" SETUP - Sistema de Conciliação Mercado Pago V3.0")
    print("=" * 70)
    print()

    create_directory_structure()
    print()

    print("Configurando arquivos do projeto...")
    create_requirements()
    create_gitignore()
    update_init_files()
    create_placeholder_files()
    print()

    print_summary()

    print()
    print("=" * 70)
    print(" ✓ SETUP CONCLUÍDO COM SUCESSO!")
    print("=" * 70)
    print()
    print("Próximos passos:")
    print()
    print("  1. Instale as dependências:")
    print("     pip install -r requirements.txt")
    print()
    print("  2. Coloque seus arquivos do Mercado Pago nas pastas:")
    print("     → data/settlement/     (Settlement Reports - .xls/.xlsx/.csv)")
    print("     → data/recebimentos/   (Releases/Recebimentos - .xlsx)")
    print()
    print("  3. Inicie o servidor:")
    print("     python app.py")
    print()
    print("  4. Acesse no navegador:")
    print("     http://localhost:9000")
    print()
    print("=" * 70)
    print()