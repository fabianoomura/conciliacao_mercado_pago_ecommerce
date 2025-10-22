// Estado global
let currentView = "monthly";
let currentTab = "dashboard";
let transactionFilter = "all"; // Filtro de transações: all, pending, complete, refunded

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  loadStatus();
});

function setupEventListeners() {
  // Botões
  document.getElementById("btnProcess").addEventListener("click", processData);
  document.getElementById("btnReset").addEventListener("click", resetCache);
  document.getElementById("btnRefresh").addEventListener("click", loadStatus);

  // Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  // Views do Cashflow
  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchCashflowView(btn.dataset.view));
  });
}

function switchTab(tabName) {
  // Atualizar botões
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });

  // Atualizar conteúdo
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === tabName);
  });

  currentTab = tabName;

  // Carregar dados específicos da tab
  loadTabData(tabName);
}

function switchCashflowView(view) {
  currentView = view;

  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === view);
  });

  loadCashflow();
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();

    if (data.success) {
      document.getElementById("vendasCount").textContent =
        data.files.vendas.count;
      document.getElementById("recebimentosCount").textContent =
        data.files.recebimentos.count;
      document.getElementById("processStatus").textContent = data.processed
        ? "✓ Processado"
        : "Não processado";

      if (data.processed) {
        loadDashboard();
      }
    }
  } catch (error) {
    showError("Erro ao carregar status: " + error.message);
  }
}

async function processData() {
  const loading = document.getElementById("loading");
  const btnProcess = document.getElementById("btnProcess");

  loading.style.display = "block";
  btnProcess.disabled = true;

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (data.success) {
      showSuccess("✓ Dados processados com sucesso!");
      loadStatus();
      loadDashboard();
    } else {
      showError("❌ Erro ao processar: " + data.error);
    }
  } catch (error) {
    showError("❌ Erro ao processar: " + error.message);
  } finally {
    loading.style.display = "none";
    btnProcess.disabled = false;
  }
}

async function resetCache() {
  if (confirm("Deseja limpar o cache? Será necessário reprocessar os dados.")) {
    try {
      const response = await fetch("/api/reset");
      const data = await response.json();

      if (data.success) {
        showSuccess("✓ Cache limpo!");
        location.reload();
      }
    } catch (error) {
      showError("Erro ao limpar cache: " + error.message);
    }
  }
}

async function loadDashboard() {
  try {
    const response = await fetch("/api/cashflow/summary");
    const data = await response.json();

    if (data.success) {
      updateSummaryCards(data.data);
      updateUpcoming7Days(data.data.upcoming_7_days);
    }
  } catch (error) {
    console.error("Erro ao carregar dashboard:", error);
  }
}

function updateSummaryCards(data) {
  const cards = document.querySelectorAll("#summaryCards .card");

  if (cards[0]) {
    cards[0].querySelector(".card-value").textContent = formatCurrency(
      data.totals.total_expected
    );
    cards[0].querySelector(
      ".card-label"
    ).textContent = `${data.totals.count_total} parcelas`;
  }

  if (cards[1]) {
    cards[1].querySelector(".card-value").textContent = formatCurrency(
      data.totals.total_received
    );
    cards[1].querySelector(
      ".card-label"
    ).textContent = `${data.totals.count_received} parcelas`;
  }

  if (cards[2]) {
    cards[2].querySelector(".card-value").textContent = formatCurrency(
      data.totals.total_pending
    );
    cards[2].querySelector(
      ".card-label"
    ).textContent = `${data.totals.count_pending} parcelas`;
  }

  if (cards[3] && data.overdue) {
    cards[3].querySelector(".card-value").textContent = formatCurrency(
      data.overdue.total_amount
    );
    cards[3].querySelector(
      ".card-label"
    ).textContent = `${data.overdue.count} parcelas`;
  }
}

function updateUpcoming7Days(data) {
  const container = document.getElementById("upcoming7Days");

  if (!data || data.count === 0) {
    container.innerHTML =
      "<p>Nenhuma parcela prevista para os próximos 7 dias</p>";
    return;
  }

  container.innerHTML = `
        <h4>💰 ${formatCurrency(data.total_amount)}</h4>
        <p>${data.count} parcela(s) prevista(s)</p>
    `;
}

async function loadTabData(tabName) {
  switch (tabName) {
    case "cashflow":
      loadCashflow();
      break;
    case "pending":
      loadPending();
      break;
    case "received":
      loadReceived();
      break;
    case "transactions":
      loadTransactions();
      break;
    case "overdue":
      loadOverdue();
      break;
  }
}

async function loadCashflow() {
  try {
    const endpoint =
      currentView === "monthly"
        ? "/api/cashflow/monthly"
        : "/api/cashflow/daily";
    const response = await fetch(endpoint);
    const data = await response.json();

    if (data.success) {
      renderCashflow(data.data);
    }
  } catch (error) {
    console.error("Erro ao carregar fluxo de caixa:", error);
  }
}

function renderCashflow(data) {
  const container = document.getElementById("cashflowContainer");

  if (!data || data.length === 0) {
    container.innerHTML =
      '<p class="empty-state">Nenhum dado de fluxo de caixa disponível</p>';
    return;
  }

  let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>${currentView === "monthly" ? "Mês" : "Data"}</th>
                    <th>Esperado</th>
                    <th>Recebido</th>
                    <th>Pendente</th>
                    <th>Parcelas</th>
                </tr>
            </thead>
            <tbody>
    `;

  data.forEach((item) => {
    const dateLabel =
      currentView === "monthly"
        ? formatMonth(item.month)
        : formatDate(item.date);
    html += `
            <tr>
                <td>${dateLabel}</td>
                <td>${formatCurrency(item.expected)}</td>
                <td class="success">${formatCurrency(item.received)}</td>
                <td class="warning">${formatCurrency(item.pending)}</td>
                <td>${item.count_expected}</td>
            </tr>
        `;
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

async function loadPending() {
  try {
    const response = await fetch("/api/installments/pending");
    const data = await response.json();

    if (data.success) {
      renderPending(data.data);
    }
  } catch (error) {
    console.error("Erro ao carregar pendentes:", error);
  }
}

function renderPending(data) {
  const container = document.getElementById("pendingContainer");

  if (!data || data.length === 0) {
    container.innerHTML = '<p class="empty-state">Nenhuma parcela pendente</p>';
    return;
  }

  let html = `
        <p><strong>Total: ${data.length} parcelas pendentes</strong></p>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Data Esperada</th>
                    <th>Operation ID</th>
                    <th>Parcela</th>
                    <th>Valor Líquido</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    `;

  data.forEach((item) => {
    const valor = item.estimated_amount || 0;
    html += `
            <tr>
                <td>${formatDate(item.expected_date)}</td>
                <td><code>${item.operation_id}</code></td>
                <td>${item.installment_label}</td>
                <td>${formatCurrency(valor)}</td>
                <td><span class="badge badge-warning">Pendente</span></td>
            </tr>
        `;
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

async function loadReceived() {
  try {
    const response = await fetch("/api/installments/received");
    const data = await response.json();

    if (data.success) {
      renderReceived(data.data);
    }
  } catch (error) {
    console.error("Erro ao carregar recebidos:", error);
  }
}

function renderReceived(data) {
  const container = document.getElementById("receivedContainer");

  if (!data || data.length === 0) {
    container.innerHTML = '<p class="empty-state">Nenhuma parcela recebida</p>';
    return;
  }

  let html = `
        <p><strong>Total: ${data.length} parcelas recebidas</strong></p>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Data Recebida</th>
                    <th>Operation ID</th>
                    <th>Parcela</th>
                    <th>Valor Recebido</th>
                    <th>Saldo Antes</th>
                    <th>Saldo Depois</th>
                </tr>
            </thead>
            <tbody>
    `;

  data.forEach((item) => {
    html += `
            <tr>
                <td>${formatDate(item.received_date)}</td>
                <td><code>${item.operation_id}</code></td>
                <td>${item.installment_label}</td>
                <td class="success">${formatCurrency(item.received_amount)}</td>
                <td>${formatCurrency(item.saldo_antes || 0)}</td>
                <td>${formatCurrency(item.saldo_depois || 0)}</td>
            </tr>
        `;
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

async function loadTransactions() {
  try {
    const response = await fetch("/api/transactions/summary");
    const data = await response.json();

    if (data.success) {
      renderTransactions(data.data);
    }
  } catch (error) {
    console.error("Erro ao carregar transações:", error);
  }
}

function renderTransactions(data) {
  const container = document.getElementById("transactionsContainer");

  if (!data || data.length === 0) {
    container.innerHTML =
      '<p class="empty-state">Nenhuma transação encontrada</p>';
    return;
  }

  // Ordenar por data (mais antigas primeiro)
  const sortedData = [...data].sort((a, b) => {
    const dateA = new Date(a.date_created || "2000-01-01");
    const dateB = new Date(b.date_created || "2000-01-01");
    return dateA - dateB;
  });

  // Filtrar baseado no filtro selecionado
  let filteredData = sortedData;
  if (transactionFilter === "pending") {
    filteredData = sortedData.filter((t) => t.pending_amount > 0);
  } else if (transactionFilter === "complete") {
    filteredData = sortedData.filter(
      (t) => t.pending_amount === 0 && t.status === "approved"
    );
  } else if (transactionFilter === "refunded") {
    filteredData = sortedData.filter(
      (t) => t.status === "refunded" || t.has_refund
    );
  }

  let html = `
        <div style="margin-bottom: 20px;">
            <strong>Total: ${filteredData.length} transações</strong>
            <div class="filter-buttons" style="margin-top: 10px;">
                <button class="btn-filter ${
                  transactionFilter === "all" ? "active" : ""
                }" onclick="setTransactionFilter('all')">📋 Todas</button>
                <button class="btn-filter ${
                  transactionFilter === "pending" ? "active" : ""
                }" onclick="setTransactionFilter('pending')">⏳ Com Pendências</button>
                <button class="btn-filter ${
                  transactionFilter === "complete" ? "active" : ""
                }" onclick="setTransactionFilter('complete')">✅ Completas</button>
                <button class="btn-filter ${
                  transactionFilter === "refunded" ? "active" : ""
                }" onclick="setTransactionFilter('refunded')">🔄 Reembolsadas</button>
            </div>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Data ↑</th>
                    <th>Operation ID</th>
                    <th>Status</th>
                    <th>Valor</th>
                    <th>Tarifa</th>
                    <th>Líquido</th>
                    <th>Pendente</th>
                    <th>Recebido</th>
                    <th>%</th>
                    <th>Parcelas</th>
                    <th>Tipo</th>
                </tr>
            </thead>
            <tbody>
    `;

  filteredData.forEach((item) => {
    // Calcular percentual recebido
    const percentReceived =
      item.net_received_amount > 0
        ? Math.round((item.received_amount / item.net_received_amount) * 100)
        : 0;

    // Determinar badge de status
    let statusBadge = "";
    let statusIcon = "";

    if (item.status === "refunded" || item.has_refund) {
      statusBadge = "badge-danger";
      statusIcon = "🔄 Reembolsado";
    } else if (item.pending_amount === 0 && item.status === "approved") {
      statusBadge = "badge-success";
      statusIcon = "✅ Completo";
    } else if (item.pending_amount > 0 && item.status === "approved") {
      statusBadge = "badge-warning";
      statusIcon = "⏳ Pendente";
    } else {
      statusBadge = "badge-secondary";
      statusIcon = item.status;
    }

    html += `
            <tr>
                <td>${formatDate(item.date_created)}</td>
                <td><code>${item.operation_id}</code></td>
                <td><span class="badge ${statusBadge}">${statusIcon}</span></td>
                <td>${formatCurrency(item.transaction_amount)}</td>
                <td class="danger">${formatCurrency(
                  Math.abs(item.mercadopago_fee)
                )}</td>
                <td class="success">${formatCurrency(
                  item.net_received_amount
                )}</td>
                <td class="warning"><strong>${formatCurrency(
                  item.pending_amount
                )}</strong></td>
                <td class="success">${formatCurrency(item.received_amount)}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${percentReceived}%"></div>
                        <span class="progress-text">${percentReceived}%</span>
                    </div>
                </td>
                <td>${item.installments}x</td>
                <td>${item.payment_type}</td>
            </tr>
        `;
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

// Função para mudar filtro de transações
function setTransactionFilter(filter) {
  transactionFilter = filter;
  loadTransactions();
}

// Tornar função global
window.setTransactionFilter = setTransactionFilter;

async function loadOverdue() {
  try {
    const response = await fetch("/api/cashflow/summary");
    const data = await response.json();

    if (data.success && data.data.overdue) {
      renderOverdue(data.data.overdue.installments || []);
    }
  } catch (error) {
    console.error("Erro ao carregar atrasados:", error);
  }
}

function renderOverdue(data) {
  const container = document.getElementById("overdueContainer");

  if (!data || data.length === 0) {
    container.innerHTML =
      '<p class="empty-state">✓ Nenhuma parcela atrasada</p>';
    return;
  }

  let html = `
        <p><strong>⚠️ Total: ${data.length} parcelas atrasadas</strong></p>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Data Esperada</th>
                    <th>Operation ID</th>
                    <th>Parcela</th>
                    <th>Valor</th>
                    <th>Dias Atraso</th>
                </tr>
            </thead>
            <tbody>
    `;

  const today = new Date();

  data.forEach((item) => {
    const expectedDate = new Date(item.expected_date);
    const diffDays = Math.floor((today - expectedDate) / (1000 * 60 * 60 * 24));
    const valor = item.estimated_amount || 0;

    html += `
            <tr>
                <td>${formatDate(item.expected_date)}</td>
                <td><code>${item.operation_id}</code></td>
                <td>${item.installment_label}</td>
                <td class="danger">${formatCurrency(valor)}</td>
                <td><span class="badge badge-danger">${diffDays} dias</span></td>
            </tr>
        `;
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

// Utilitários
function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value || 0);
}

function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  const date = new Date(dateStr + "T00:00:00");
  return date.toLocaleDateString("pt-BR");
}

function formatMonth(monthStr) {
  if (!monthStr) return "N/A";
  const [year, month] = monthStr.split("-");
  const months = [
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
  ];
  return `${months[parseInt(month) - 1]}/${year}`;
}

function showSuccess(message) {
  alert(message);
}

function showError(message) {
  alert(message);
}
