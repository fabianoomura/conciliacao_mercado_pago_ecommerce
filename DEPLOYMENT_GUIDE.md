# Guia de Deploy - MP Recebiveis V3.1 (Saldo Progressivo)

## 📋 Pré-requisitos

- ✓ Python 3.8+
- ✓ Flask 3.0.0
- ✓ pandas 2.1.0
- ✓ openpyxl 3.1.2
- ✓ Navegador moderno
- ✓ Porta 9000 disponível

---

## 🚀 Deploy Steps

### 1. Backup dos Dados

```bash
# Criar backup da pasta data
cp -r data data_backup_$(date +%Y%m%d_%H%M%S)

# Criar backup do cache (se houver)
cp -r .cache .cache_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
```

### 2. Pull do Código

```bash
# Atualizar repositório
git pull origin main

# Verificar se está tudo OK
git status
```

**Commits esperados:**
```
- 240a2cc Saldo progressivo
- 3d9256c Detecção de canceladas
- 3813d31 Garantia de status
```

### 3. Instalar/Atualizar Dependências

```bash
# Instalar dependencies
pip install -r requirements.txt

# Ou atualizar se necessário
pip install --upgrade -r requirements.txt
```

### 4. Validar Código

```bash
# Validar sintaxe Python
python -m py_compile app.py
python -m py_compile backend/processors/*.py

# Validar imports
python -c "from app import app; print('✓ App OK')"
```

### 5. Testes Rápidos (Opcional)

```bash
# Test 1: Syntax check
python -m py_compile backend/processors/reconciliator.py
echo "✓ Syntax OK"

# Test 2: Import check
python -c "from backend.processors.reconciliator import ReconciliatorV3; print('✓ Import OK')"
```

### 6. Iniciar o Serviço

```bash
# Desenvolvimento (com debug)
python app.py

# Produção (com Gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:9000 app:app
```

### 7. Validar no Dashboard

```
Abrir: http://localhost:9000

Clicar em "Processar Dados" e validar:
  ✓ Processamento completa sem erros
  ✓ Dashboard carrega dados
  ✓ Totais fazem sentido
  ✓ Parcelas com refund total mostram "Cancelado"
```

---

## 🔍 Testes de Sanidade

### Teste 1: Procesar Dados

```bash
curl -X POST http://localhost:9000/api/process
```

**Esperado:**
- Status 200
- Response com dados processados

### Teste 2: Verificar Resumo

```bash
curl http://localhost:9000/api/summary
```

**Esperado:**
- Status 200
- Campo `total_cancelled` > 0 (se houver refunds)
- Campo `total_pending` >= 0

### Teste 3: Verificar Parcelas Canceladas

```bash
curl http://localhost:9000/api/debug/reference/repsglL8p6QjocK2YsvNxlJSj
```

**Esperado:**
- Status 200
- Parcelas com `status: 'cancelled'`
- Campo `is_cancelled: true`

---

## 📊 Rollback (Se Necessário)

### Reverter Últimas Mudanças

```bash
# Ver commits
git log --oneline -10

# Reverter para commit anterior
git reset --hard 240a2cc

# Ou reverter apenas um arquivo
git checkout 240a2cc -- backend/processors/reconciliator.py
```

### Restaurar Backup

```bash
# Se algo der errado
rm -rf data
cp -r data_backup_TIMESTAMP data
```

---

## 🐳 Deploy com Docker (Opcional)

### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 9000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:9000", "app:app"]
```

### Build e Run

```bash
# Build
docker build -t mp-recebiveis:v3.1 .

# Run
docker run -p 9000:9000 \
  -v $(pwd)/data:/app/data \
  mp-recebiveis:v3.1
```

---

## 🔧 Configuração em Produção

### Environment Variables

```bash
# .env
FLASK_ENV=production
DEBUG=False
WORKERS=4
BIND=0.0.0.0:9000
```

### Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Cache static files
    location /static/ {
        expires 1d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Systemd Service (Linux)

```ini
[Unit]
Description=MP Recebiveis API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/app
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:9000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 📈 Monitoramento

### Verificar Logs

```bash
# Se usando systemd
sudo journalctl -u mp-recebiveis -f

# Se usando direto
tail -f app.log
```

### Health Check

```bash
# Script de health check
#!/bin/bash
curl -s http://localhost:9000/api/status > /dev/null
if [ $? -eq 0 ]; then
  echo "✓ Service healthy"
else
  echo "✗ Service down"
  # Reiniciar
  systemctl restart mp-recebiveis
fi
```

---

## 🚨 Troubleshooting

### Erro: "Address already in use"

```bash
# Encontrar processo usando porta 9000
lsof -i :9000

# Matar processo
kill -9 <PID>
```

### Erro: "ModuleNotFoundError"

```bash
# Reinstalar dependências
pip install --upgrade -r requirements.txt --force-reinstall
```

### Erro: "Data not processing"

```bash
# Verificar estrutura de diretórios
ls -la data/settlement/
ls -la data/recebimentos/

# Verificar permissões
chmod -R 755 data/
```

### Dashboard não carrega dados

```bash
# 1. Limpar cache do navegador (Ctrl+Shift+Del)
# 2. Verificar console do navegador (F12)
# 3. Chamar /api/reset para limpar cache backend
curl http://localhost:9000/api/reset
```

---

## ✅ Checklist Pré-Deploy

- [ ] Code review completado
- [ ] Testes passando
- [ ] Backup dos dados criado
- [ ] Dependências atualizadas
- [ ] Código validado (syntax, imports)
- [ ] Variáveis de ambiente configuradas
- [ ] Nginx/proxy configurado
- [ ] Logs ativados
- [ ] Health check implementado
- [ ] Plano de rollback documentado

---

## 📝 Documentação de Referência

- [FINAL_ADJUSTMENTS_SUMMARY.md](./FINAL_ADJUSTMENTS_SUMMARY.md) - Resumo das mudanças
- [VALIDATION_CHECKLIST.md](./VALIDATION_CHECKLIST.md) - Testes a executar
- [README.md](./README.md) - Documentação geral

---

## 🎯 Verificação Pós-Deploy

### Imediatamente Após Deploy

```bash
# 1. Verificar status
curl http://localhost:9000/api/status

# 2. Processar dados
curl -X POST http://localhost:9000/api/process

# 3. Verificar canceladas
curl http://localhost:9000/api/installments/cancelled

# 4. Verificar totais
curl http://localhost:9000/api/summary
```

### Após 1 Hora

- [ ] Verificar logs de erro
- [ ] Validar processamento de dados
- [ ] Testar com dados reais (refund total)

### Após 1 Dia

- [ ] Validar performance
- [ ] Verificar se canceladas aparecem corretamente
- [ ] Confirmar que atrasadas não incluem canceladas

---

## 🚀 Conclusão

Deploy concluído com sucesso!

O sistema agora:
- ✓ Trata saldo progressivo corretamente
- ✓ Detecta parcelas canceladas
- ✓ Garante status correto
- ✓ Exibe informações precisas

**Status: PRONTO PARA PRODUÇÃO ✅**

---

**Data de Deploy:** _______________
**Responsável:** _______________
**Observações:** _______________
