// Estado da aplicação
const appState = {
  processed: false,
  currentTab: "dashboard",
  currentCashflowView: "monthly",
};

// API Base URL
const API_URL = "http://localhost:9000/api";

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
  console.log("Sistema de Conciliação Mercado Pago iniciado");

  // Event Listeners
  document.getElementById("btnProcess").addEventListener("click", processData);
  document.getElementById("btnReset").addEventListener("click", resetData);
  document
    .getElementById("btnRefresh")
    .addEventListener("click", refreshStatus);

  // Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      switchTab(e.target.dataset.tab);
    });
  });

  // View Selector (Cashflow)
  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      switchCashflowView(e.target.dataset.view);
    });
  });

  // Carregar status inicial
  refreshStatus();
});

// Processar Dados
async function processData() {
  showLoading(true);
  showAlert("Processando dados... Isso pode levar alguns minutos.", "warning");

  try {
    const response = await fetch(`${API_URL}/process`, {
      method: "POST",
    });

    const data = await response.json();

    if (data.success) {
      appState.processed = true;
      showAlert("✓ Dados processados com sucesso!", "success");

      // Atualizar dashboard
      await loadDashboard(data.summary);

      // Atualizar status
      await refreshStatus();
    } else {
      showAlert("❌ Erro: " + data.error, "error");
    }
  } catch (error) {
    showAlert("❌ Erro ao processar: " + error.message, "error");
  } finally {
    showLoading(false);
  }
}

// Reset Data
async function resetData() {
  if (!confirm("Deseja limpar o cache? Você precisará reprocessar os dados.")) {
    return;
  }

  try {
    const response = await fetch(`${API_URL}/reset`);
    const data = await response.json();

    if (data.success) {
      appState.processed = false;
      showAlert("Cache limpo com sucesso!", "success");
      clearDashboard();
      refreshStatus();
    }
  } catch (error) {
    showAlert("Erro ao limpar cache: " + error.message, "error");
  }
}

// Refresh Status
async function refreshStatus() {
  try {
    const response = await fetch(`${API_URL}/status`);
    const data = await response.json();

    if (data.success) {
      document.getElementById("vendasCount").textContent =
        data.files.vendas.count;
      document.getElementById("recebimentosCount").textContent =
        data.files.recebimentos.count;
      document.getElementById("processStatus").textContent = data.processed
        ? "✓ Processado"
        : "⏳ Não processado";

      appState.processed = data.processed;
    }
  } catch (error) {
    console.error("Erro ao atualizar status:", error);
  }
}

// Load Dashboard
async function loadDashboard(summary) {
  try {
    // Carregar resumo de cashflow
    const cashflowResponse = await fetch(`${API_URL}/cashflow/summary`);
    const cashflowData = await cashflowResponse.json();

    if (cashflowData.success) {
      const { totals, overdue, upcoming_7_days } = cashflowData.data;

      // Atualizar cards
      const cards = document.querySelector("#summaryCards");
      cards.innerHTML = `
                <div class="card card-primary">
                    <h3>Total Esperado</h3>
                    <p class="card-value">R$ ${formatMoney(
                      totals.total_expected
                    )}</p>
                    <p class="card-label">${totals.count_total} parcelas</p>
                </div>
                <div class="card card-success">
                    <h3>Total Recebido</h3>
                    <p class="card-value">R$ ${formatMoney(
                      totals.total_received
                    )}</p>
                    <p class="card-label">${totals.count_received} parcelas</p>
                </div>
                <div class="card card-warning">
                    <h3>Pendente</h3>
                    <p class="card-value">R$ ${formatMoney(
                      totals.total_pending
                    )}</p>
                    <p class="card-label">${totals.count_pending} parcelas</p>
                </div>
                <div class="card card-danger">
                    <h3>Atrasado</h3>
                    <p class="card-value">R$ ${formatMoney(
                      overdue.total_amount
                    )}</p>
                    <p class="card-label">${overdue.count} parcelas</p>
                </div>
            `;

      // Próximos 7 dias
      const upcoming7DaysDiv = document.getElementById("upcoming7Days");
      if (upcoming_7_days.count > 0) {
        upcoming7DaysDiv.innerHTML = `
                    <p><strong>Você tem ${
                      upcoming_7_days.count
                    } parcelas para receber nos próximos 7 dias</strong></p>
                    <p>Valor total: <strong class="amount-positive">R$ ${formatMoney(
                      upcoming_7_days.total_amount
                    )}</strong></p>
                `;
      } else {
        upcoming7DaysDiv.innerHTML = `<p>Nenhuma parcela programada para os próximos 7 dias.</p>`;
      }

      // Resumo de processamento
      const processingSummaryDiv = document.getElementById("processingSummary");
      processingSummaryDiv.innerHTML = `
                <p><strong>Transações:</strong> ${
                  summary.sales.total_transactions
                }</p>
                <p><strong>Valor Total:</strong> R$ ${formatMoney(
                  summary.sales.total_amount
                )}</p>
                <p><strong>Tarifas:</strong> R$ ${formatMoney(
                  summary.sales.total_fees
                )}</p>
                <p><strong>Líquido:</strong> R$ ${formatMoney(
                  summary.sales.total_net
                )}</p>
                <hr style="margin: 15px 0; border: none; border-top: 1px solid #ddd;">
                <p><strong>Releases Processadas:</strong> ${
                  summary.releases.total_releases
                }</p>
                <p><strong>Pagamentos:</strong> ${
                  summary.releases.total_payments
                }</p>
                <p><strong>Estornos:</strong> ${
                  summary.releases.total_refunds
                }</p>
                <p><strong>Chargebacks:</strong> ${
                  summary.releases.total_chargebacks
                }</p>
            `;
    }
  } catch (error) {
    console.error("Erro ao carregar dashboard:", error);
  }
}

// Clear Dashboard
function clearDashboard() {
  document.querySelector("#summaryCards").innerHTML = `
        <div class="card card-primary"><h3>Total Esperado</h3><p class="card-value">R$ -</p><p class="card-label">-</p></div>
        <div class="card card-success"><h3>Total Recebido</h3><p class="card-value">R$ -</p><p class="card-label">-</p></div>
        <div class="card card-warning"><h3>Pendente</h3><p class="card-value">R$ -</p><p class="card-label">-</p></div>
        <div class="card card-danger"><h3>Atrasado</h3><p class="card-value">R$ -</p><p class="card-label">-</p></div>
    `;
  document.getElementById("upcoming7Days").innerHTML =
    "<p>Carregue os dados para visualizar</p>";
  document.getElementById("processingSummary").innerHTML =
    "<p>Carregue os dados para visualizar</p>";
}

// Load Overdue Installments
async function loadOverdueInstallments() {
  const container = document.getElementById("overdueContainer");

  try {
    // Buscar resumo do cashflow para pegar os atrasados
    const response = await fetch(`${API_URL}/cashflow/summary`);
    const result = await response.json();

    if (result.success && result.data.overdue.count > 0) {
      const overdue = result.data.overdue;

      let html = `
                <div class="alert alert-error">
                    <strong>⚠️ Atenção!</strong> Você tem ${
                      overdue.count
                    } parcelas atrasadas no valor total de R$ ${formatMoney(
        overdue.total_amount
      )}
                </div>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Data Esperada</th>
                                <th>Dias Atraso</th>
                                <th>Operation ID</th>
                                <th>Parcela</th>
                                <th>Valor Líquido</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

      const today = new Date();

      overdue.installments.forEach((item) => {
        const expectedDate = new Date(item.expected_date + "T00:00:00");
        const diffTime = Math.abs(today - expectedDate);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        html += `
                    <tr>
                        <td>${formatDate(item.expected_date)}</td>
                        <td><span class="amount-negative">${diffDays} dias</span></td>
                        <td><code>${item.operation_id}</code></td>
                        <td>${item.installment_label}</td>
                        <td class="amount-negative">R$ ${formatMoney(
                          item.net_amount
                        )}</td>
                        <td><span class="status-badge status-cancelled">Atrasado</span></td>
                    </tr>
                `;
      });

      html += "</tbody></table></div>";
      container.innerHTML = html;
    } else {
      container.innerHTML = `
                <div class="alert alert-success">
                    <strong>✓ Parabéns!</strong> Você não tem parcelas atrasadas.
                </div>
            `;
    }
  } catch (error) {
    container.innerHTML = '<p class="empty-state">Erro ao carregar dados</p>';
    console.error("Erro ao carregar atrasados:", error);
  }
}

// Switch Tab
async function switchTab(tabName) {
  appState.currentTab = tabName;

  // Atualizar botões
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.classList.remove("active");
    if (btn.dataset.tab === tabName) {
      btn.classList.add("active");
    }
  });

  // Atualizar painéis
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.remove("active");
  });
  document.getElementById(tabName).classList.add("active");

  // Carregar dados da aba
  if (appState.processed) {
    switch (tabName) {
      case "cashflow":
        await loadCashflow();
        break;
      case "overdue":
        await loadOverdueInstallments();
        break;
      case "pending":
        await loadPendingInstallments();
        break;
      case "received":
        await loadReceivedInstallments();
        break;
      case "transactions":
        await loadTransactions();
        break;
    }
  }
}

// Switch Cashflow View
async function switchCashflowView(view) {
  appState.currentCashflowView = view;

  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.classList.remove("active");
    if (btn.dataset.view === view) {
      btn.classList.add("active");
    }
  });

  await loadCashflow();
}

// Load Cashflow
async function loadCashflow() {
  const container = document.getElementById("cashflowContainer");
  const endpoint =
    appState.currentCashflowView === "monthly"
      ? "/cashflow/monthly"
      : "/cashflow/daily";

  try {
    const response = await fetch(`${API_URL}${endpoint}`);
    const result = await response.json();

    if (result.success && result.data.length > 0) {
      const maxValue = Math.max(...result.data.map((item) => item.expected));

      let html = '<div class="cashflow-chart">';

      result.data.forEach((item) => {
        const label =
          appState.currentCashflowView === "monthly" ? item.month : item.date;
        const percentage = (item.expected / maxValue) * 100;

        html += `
                    <div class="chart-bar">
                        <div class="chart-bar-label">
                            <span><strong>${label}</strong></span>
                            <span>Esperado: R$ ${formatMoney(
                              item.expected
                            )} | Recebido: R$ ${formatMoney(
          item.received
        )} | Pendente: R$ ${formatMoney(item.pending)}</span>
                        </div>
                        <div class="chart-bar-container">
                            <div class="chart-bar-fill" style="width: ${percentage}%">
                                R$ ${formatMoney(item.expected)}
                            </div>
                        </div>
                    </div>
                `;
      });

      html += "</div>";
      container.innerHTML = html;
    } else {
      container.innerHTML = '<p class="empty-state">Nenhum dado disponível</p>';
    }
  } catch (error) {
    container.innerHTML = '<p class="empty-state">Erro ao carregar dados</p>';
    console.error("Erro ao carregar cashflow:", error);
  }
}

// Load Pending Installments
async function loadPendingInstallments() {
  const container = document.getElementById("pendingContainer");

  try {
    const response = await fetch(`${API_URL}/installments/pending`);
    const result = await response.json();

    if (result.success && result.data.length > 0) {
      let html = `
                <p><strong>Total: ${result.count} parcelas pendentes</strong></p>
                <div class="table-container">
                    <table>
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

      result.data.forEach((item) => {
        html += `
                    <tr>
                        <td>${formatDate(item.expected_date)}</td>
                        <td><code>${item.operation_id}</code></td>
                        <td>${item.installment_label}</td>
                        <td class="amount-positive">R$ ${formatMoney(
                          item.net_amount
                        )}</td>
                        <td><span class="status-badge status-pending">Pendente</span></td>
                    </tr>
                `;
      });

      html += "</tbody></table></div>";
      container.innerHTML = html;
    } else {
      container.innerHTML =
        '<p class="empty-state">Nenhuma parcela pendente</p>';
    }
  } catch (error) {
    container.innerHTML = '<p class="empty-state">Erro ao carregar dados</p>';
    console.error("Erro ao carregar pendentes:", error);
  }
}

// Load Received Installments
async function loadReceivedInstallments() {
  const container = document.getElementById("receivedContainer");

  try {
    const response = await fetch(`${API_URL}/installments/received`);
    const result = await response.json();

    if (result.success && result.data.length > 0) {
      let html = `
                <p><strong>Total: ${result.count} parcelas recebidas</strong></p>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Data Recebida</th>
                                <th>Operation ID</th>
                                <th>Parcela</th>
                                <th>Valor Esperado</th>
                                <th>Valor Recebido</th>
                                <th>Diferença</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

      result.data.forEach((item) => {
        const diffClass =
          item.difference > 0
            ? "amount-positive"
            : item.difference < 0
            ? "amount-negative"
            : "";
        html += `
                    <tr>
                        <td>${formatDate(item.received_date)}</td>
                        <td><code>${item.operation_id}</code></td>
                        <td>${item.installment_label}</td>
                        <td>R$ ${formatMoney(item.net_amount)}</td>
                        <td>R$ ${formatMoney(item.received_amount)}</td>
                        <td class="${diffClass}">R$ ${formatMoney(
          item.difference || 0
        )}</td>
                    </tr>
                `;
      });

      html += "</tbody></table></div>";
      container.innerHTML = html;
    } else {
      container.innerHTML =
        '<p class="empty-state">Nenhuma parcela recebida</p>';
    }
  } catch (error) {
    container.innerHTML = '<p class="empty-state">Erro ao carregar dados</p>';
    console.error("Erro ao carregar recebidos:", error);
  }
}

// Load Transactions
async function loadTransactions() {
  const container = document.getElementById("transactionsContainer");

  try {
    const response = await fetch(`${API_URL}/transactions`);
    const result = await response.json();

    if (result.success && result.data.length > 0) {
      let html = `
                <p><strong>Total: ${result.count} transações</strong></p>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Operation ID</th>
                                <th>Status</th>
                                <th>Valor</th>
                                <th>Tarifa</th>
                                <th>Líquido</th>
                                <th>Parcelas</th>
                                <th>Tipo Pgto</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

      result.data.forEach((item) => {
        let statusClass = "status-received";
        if (item.status === "charged_back") statusClass = "status-cancelled";
        if (item.status === "refunded") statusClass = "status-cancelled";

        html += `
                    <tr>
                        <td>${formatDate(item.date_approved)}</td>
                        <td><code>${item.operation_id}</code></td>
                        <td><span class="status-badge ${statusClass}">${
          item.status
        }</span></td>
                        <td>R$ ${formatMoney(item.transaction_amount)}</td>
                        <td class="amount-negative">R$ ${formatMoney(
                          Math.abs(item.mercadopago_fee)
                        )}</td>
                        <td class="amount-positive">R$ ${formatMoney(
                          item.net_received_amount
                        )}</td>
                        <td>${item.installments}x</td>
                        <td>${item.payment_type}</td>
                    </tr>
                `;
      });

      html += "</tbody></table></div>";
      container.innerHTML = html;
    } else {
      container.innerHTML =
        '<p class="empty-state">Nenhuma transação encontrada</p>';
    }
  } catch (error) {
    container.innerHTML = '<p class="empty-state">Erro ao carregar dados</p>';
    console.error("Erro ao carregar transações:", error);
  }
}

// Utility Functions
function showLoading(show) {
  document.getElementById("loading").style.display = show ? "block" : "none";
}

function showAlert(message, type) {
  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type}`;
  alertDiv.textContent = message;

  const container = document.querySelector(".container");
  container.insertBefore(alertDiv, container.children[3]);

  setTimeout(() => {
    alertDiv.remove();
  }, 5000);
}

function formatMoney(value) {
  if (value === null || value === undefined) return "0,00";
  return parseFloat(value)
    .toFixed(2)
    .replace(".", ",")
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

function formatDate(dateStr) {
  if (!dateStr) return "-";

  try {
    const date = new Date(dateStr + "T00:00:00");
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
  } catch {
    return dateStr;
  }
}
