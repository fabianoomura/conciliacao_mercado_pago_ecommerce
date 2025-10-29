/**
 * Frontend JavaScript V3 - VERSÃO FINAL
 * Sistema de Conciliação Mercado Pago
 *
 * Correções:
 * - Suporte a fluxo diário
 * - Exibição de parcelas canceladas
 * - Formatação correta de parcelas
 */

// Estado global
const state = {
  processed: false,
  currentTab: "dashboard",
  data: null,
};

// ========================================
// INICIALIZAÇÃO
// ========================================

document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 Frontend V3 FINAL iniciado");

  setupEventListeners();
  loadStatus();
});

function setupEventListeners() {
  // Botões principais
  document
    .getElementById("btn-process")
    ?.addEventListener("click", processData);
  document.getElementById("btn-clear")?.addEventListener("click", clearCache);
  document
    .getElementById("btn-refresh")
    ?.addEventListener("click", loadSummary);

  // Tabs
  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      switchTab(e.target.dataset.tab);
    });
  });
}

// ========================================
// API CALLS
// ========================================

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    const data = await response.json();

    state.processed = data.processed;
    updateStatusDisplay(data);

    if (data.processed) {
      await loadSummary();
    }
  } catch (error) {
    console.error("Erro ao carregar status:", error);
    showError("Erro ao conectar com o servidor");
  }
}

async function processData() {
  const btn = document.getElementById("btn-process");
  const originalText = btn.innerHTML;

  try {
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';

    showInfo("Processando dados... Isso pode levar alguns segundos.");

    const response = await fetch("/api/process", {
      method: "POST",
    });

    const data = await response.json();

    if (data.success) {
      showSuccess("Dados processados com sucesso!");
      state.processed = true;
      await loadSummary();
    } else {
      throw new Error(data.error || "Erro desconhecido");
    }
  } catch (error) {
    console.error("Erro ao processar:", error);
    showError(`Erro ao processar dados: ${error.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

async function clearCache() {
  try {
    const response = await fetch("/api/reset");
    const data = await response.json();

    if (data.success) {
      showSuccess("Cache limpo com sucesso!");
      state.processed = false;
      clearAllData();
      await loadStatus();
    }
  } catch (error) {
    console.error("Erro ao limpar cache:", error);
    showError("Erro ao limpar cache");
  }
}

async function loadSummary() {
  if (!state.processed) {
    console.log("Dados não processados ainda");
    return;
  }

  try {
    showInfo("Carregando dados...");

    const response = await fetch("/api/summary");
    const data = await response.json();

    if (data.success) {
      state.data = data;
      updateDashboard(data);
      hideMessage();
    } else {
      throw new Error("Erro ao carregar resumo");
    }
  } catch (error) {
    console.error("Erro ao carregar resumo:", error);
    showError("Erro ao carregar dados do resumo");
  }
}

// ========================================
// ATUALIZAÇÃO DO DASHBOARD
// ========================================

function updateStatusDisplay(status) {
  const statusEl = document.getElementById("system-status");
  if (statusEl) {
    if (status.processed) {
      statusEl.textContent = "Processado";
      statusEl.className = "badge badge-success";
    } else {
      statusEl.textContent = "Não processado";
      statusEl.className = "badge badge-warning";
    }
  }
}

function updateDashboard(data) {
  console.log("📊 Atualizando dashboard com dados V3:", data);

  const cashflow = data.cashflow || {};
  const reconciliation = data.reconciliation || {};
  const statusBreakdown = reconciliation.status_breakdown || {};

  // Totais principais
  const totalExpected = cashflow.total_expected || 0;
  const totalReceived =
    (cashflow.total_received || 0) + (cashflow.total_received_advance || 0);
  const totalPending = cashflow.total_pending || 0;
  const totalOverdue = cashflow.total_overdue || 0;

  // Contadores
  const countTotal = cashflow.count_active || cashflow.count_total || 0;
  const countReceived =
    (cashflow.count_received || 0) + (cashflow.count_received_advance || 0);
  const countPending = cashflow.count_pending || 0;
  const countOverdue = cashflow.count_overdue || 0;
  const countCancelled = cashflow.count_cancelled || 0;

  // Atualizar cards principais
  updateCard("total-expected", totalExpected, countTotal);
  updateCard("total-received", totalReceived, countReceived, totalExpected);
  updateCard("total-pending", totalPending, countPending, totalExpected);
  updateCard("total-overdue", totalOverdue, countOverdue, totalExpected);

  // Informações do sistema
  updateSystemInfo(data, countCancelled);

  // Atualizar outras abas se necessário
  if (state.currentTab !== "dashboard") {
    loadTabData(state.currentTab);
  }
}

function updateCard(cardId, value, count, total = null) {
  const valueEl = document.getElementById(`${cardId}-value`);
  const countEl = document.getElementById(`${cardId}-count`);
  const percentEl = document.getElementById(`${cardId}-percent`);

  if (valueEl) {
    valueEl.textContent = formatCurrency(value);
  }

  if (countEl) {
    countEl.textContent = `${count} parcelas`;
  }

  if (percentEl && total && total > 0) {
    const percent = ((value / total) * 100).toFixed(1);
    percentEl.textContent = `${percent}% do esperado`;
  }
}

function updateSystemInfo(data, countCancelled) {
  const infoEl = document.getElementById("system-info");
  if (!infoEl) return;

  const cashflow = data.cashflow || {};
  const settlement = data.settlement || {};
  const releases = data.releases || {};
  const movements = data.movements || {};

  const advanceInfo =
    cashflow.count_received_advance > 0
      ? `<div class="info-item"><strong>Parcelas Antecipadas:</strong> ${cashflow.count_received_advance}</div>`
      : "";

  const cancelledInfo =
    countCancelled > 0
      ? `<div class="info-item"><strong>Parcelas Canceladas:</strong> ${countCancelled}</div>`
      : "";

  const chargebackInfo = movements.chargebacks?.net_chargeback
    ? `<div class="info-item"><strong>Chargebacks Líquido:</strong> ${formatCurrency(
        movements.chargebacks.net_chargeback
      )}</div>`
    : "";

  const feesInfo = movements.advance_fees?.total_amount
    ? `<div class="info-item"><strong>Taxas de Antecipação:</strong> ${formatCurrency(
        movements.advance_fees.total_amount
      )}</div>`
    : "";

  infoEl.innerHTML = `
        <div class="info-item">
            <strong>Total Esperado:</strong> ${formatCurrency(
              cashflow.total_expected || 0
            )}
        </div>
        <div class="info-item">
            <strong>Total Recebido:</strong> ${formatCurrency(
              (cashflow.total_received || 0) +
                (cashflow.total_received_advance || 0)
            )}
        </div>
        <div class="info-item">
            <strong>Total Pendente:</strong> ${formatCurrency(
              cashflow.total_pending || 0
            )}
        </div>
        <div class="info-item">
            <strong>Total Atrasado:</strong> ${formatCurrency(
              cashflow.total_overdue || 0
            )}
        </div>
        ${advanceInfo}
        ${cancelledInfo}
        ${chargebackInfo}
        ${feesInfo}
        <div class="info-separator"></div>
        <div class="info-item">
            <strong>Total de Pedidos:</strong> ${settlement.total_orders || 0}
        </div>
        <div class="info-item">
            <strong>Total de Parcelas:</strong> ${
              settlement.total_installments || 0
            }
        </div>
        <div class="info-item">
            <strong>Parcelas Ativas:</strong> ${cashflow.count_active || 0}
        </div>
        <div class="info-item">
            <strong>Payments Recebidos:</strong> ${releases.total_payments || 0}
        </div>
    `;
}

// ========================================
// NAVEGAÇÃO POR ABAS
// ========================================

function switchTab(tabName) {
  state.currentTab = tabName;

  document.querySelectorAll(".tab-button").forEach((btn) => {
    if (btn.dataset.tab === tabName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  document.querySelectorAll(".tab-content").forEach((content) => {
    if (content.id === `tab-${tabName}`) {
      content.classList.add("active");
    } else {
      content.classList.remove("active");
    }
  });

  if (state.processed) {
    loadTabData(tabName);
  }
}

async function loadTabData(tabName) {
  try {
    switch (tabName) {
      case "cashflow":
        await loadCashflowData();
        break;
      case "overdue":
        await loadOverdueData();
        break;
      case "pending":
        await loadPendingData();
        break;
      case "received":
        await loadReceivedData();
        break;
      case "transactions":
        await loadTransactionsData();
        break;
      case "reconciliation":
        await loadReconciliationData();
        break;
    }
  } catch (error) {
    console.error(`Erro ao carregar dados da aba ${tabName}:`, error);
    showError(`Erro ao carregar dados: ${error.message}`);
  }
}

async function loadCashflowData() {
  // Carregar fluxo mensal
  const monthlyResponse = await fetch("/api/cashflow/monthly");
  const monthlyData = await monthlyResponse.json();

  if (monthlyData.success) {
    renderCashflowChart(monthlyData.cashflow);
  }

  // Carregar fluxo diário
  const today = new Date();
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(today.getDate() - 30);
  const startDate = thirtyDaysAgo.toISOString().split("T")[0];

  const dailyResponse = await fetch(
    `/api/cashflow/daily?start_date=${startDate}`
  );
  const dailyData = await dailyResponse.json();

  if (dailyData.success) {
    renderDailyCashflow(dailyData.cashflow);
  }
}

async function loadOverdueData() {
  const response = await fetch("/api/installments/overdue");
  const data = await response.json();

  if (data.success) {
    renderInstallmentsTable("overdue-table", data.installments, "atrasadas");
  }
}

async function loadPendingData() {
  const response = await fetch("/api/installments/pending");
  const data = await response.json();

  if (data.success) {
    renderInstallmentsTable("pending-table", data.installments, "pendentes");
  }
}

async function loadReceivedData() {
  const response = await fetch("/api/installments/received");
  const data = await response.json();

  if (data.success) {
    renderInstallmentsTable("received-table", data.installments, "recebidas");
  }
}

async function loadTransactionsData() {
  const response = await fetch("/api/transactions");
  const data = await response.json();

  if (data.success) {
    renderTransactionsTable(data.transactions);
  }
}

async function loadReconciliationData() {
  const response = await fetch("/api/reconciliation");
  const data = await response.json();

  if (data.success) {
    renderReconciliationReport(data.report);
  }
}

// ========================================
// RENDERIZAÇÃO DE TABELAS
// ========================================

function renderInstallmentsTable(tableId, installments, title) {
  const container = document.getElementById(tableId);
  if (!container) return;

  const total = installments.reduce(
    (sum, i) => sum + (i.received_amount || i.installment_net_amount || 0),
    0
  );

  let html = `
        <div class="table-header">
            <h3>Parcelas ${title} (${installments.length})</h3>
            <p>Total: ${formatCurrency(total)}</p>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>External Ref</th>
                    <th>Parcela</th>
                    <th>Valor</th>
                    <th>Data Prevista</th>
                    <th>Data Recebida</th>
                    <th>Status</th>
                    <th>Observações</th>
                </tr>
            </thead>
            <tbody>
    `;

  installments.forEach((inst) => {
    const value = inst.received_amount || inst.installment_net_amount || 0;
    const statusClass = getStatusClass(inst.status);
    const statusLabel = getStatusLabel(inst.status);

    // Usar installment_display se existir, senão criar manualmente
    const installmentDisplay =
      inst.installment_display ||
      `${inst.installment_number}/${inst.total_installments}`;

    let obs = "";
    if (inst.has_adjustment) {
      obs += "⚠️ Ajustado ";
    }
    if (inst.status === "received_advance") {
      obs += `⚡ Antecipado ${inst.days_advance} dias`;
    }
    if (inst.refund_applied > 0) {
      obs += `🔄 Estorno: ${formatCurrency(inst.refund_applied)}`;
    }
    if (inst.chargeback_applied > 0) {
      obs += `❌ Chargeback: ${formatCurrency(inst.chargeback_applied)}`;
    }

    html += `
            <tr>
                <td><code>${inst.external_reference}</code></td>
                <td>${installmentDisplay}</td>
                <td><strong>${formatCurrency(value)}</strong></td>
                <td>${formatDate(inst.money_release_date)}</td>
                <td>${
                  inst.received_date ? formatDate(inst.received_date) : "-"
                }</td>
                <td><span class="badge ${statusClass}">${statusLabel}</span></td>
                <td>${obs}</td>
            </tr>
        `;
  });

  html += `
            </tbody>
        </table>
    `;

  container.innerHTML = html;
}

function renderCashflowChart(cashflow) {
  const container = document.getElementById("cashflow-chart");
  if (!container) return;

  let html = `
        <div class="table-header">
            <h3>Fluxo de Caixa Mensal</h3>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Mês</th>
                    <th>Esperado</th>
                    <th>Recebido</th>
                    <th>Antecipado</th>
                    <th>Pendente</th>
                    <th>Atrasado</th>
                </tr>
            </thead>
            <tbody>
    `;

  cashflow.forEach((month) => {
    html += `
            <tr>
                <td><strong>${month.month}</strong></td>
                <td>${formatCurrency(month.expected)}</td>
                <td class="text-success">${formatCurrency(month.received)}</td>
                <td class="text-info">${formatCurrency(
                  month.received_advance
                )}</td>
                <td class="text-warning">${formatCurrency(month.pending)}</td>
                <td class="text-danger">${formatCurrency(month.overdue)}</td>
            </tr>
        `;
  });

  html += `
            </tbody>
        </table>
    `;

  container.innerHTML = html;
}

function renderDailyCashflow(dailyFlow) {
  const container = document.getElementById("daily-cashflow");
  if (!container) {
    // Se não existir o elemento, adicionar após o mensal
    const chartContainer = document.getElementById("cashflow-chart");
    if (chartContainer) {
      const newDiv = document.createElement("div");
      newDiv.id = "daily-cashflow";
      newDiv.style.marginTop = "30px";
      chartContainer.parentNode.appendChild(newDiv);
    } else {
      return;
    }
  }

  const targetContainer = document.getElementById("daily-cashflow");

  let html = `
        <div class="table-header" style="margin-top: 30px;">
            <h3>Fluxo de Caixa Diário (Últimos 30 dias)</h3>
            <p>${dailyFlow.length} dias com movimentação</p>
        </div>
        <div class="daily-flow-grid">
    `;

  dailyFlow.forEach((day) => {
    const hasData = day.expected > 0;

    if (hasData) {
      html += `
                <div class="daily-card">
                    <div class="daily-header">
                        <strong>${formatDate(day.date)}</strong>
                        <span class="daily-total">${formatCurrency(
                          day.expected
                        )}</span>
                    </div>
                    <div class="daily-stats">
                        ${
                          day.received > 0
                            ? `<span class="badge badge-success">✓ ${formatCurrency(
                                day.received
                              )}</span>`
                            : ""
                        }
                        ${
                          day.received_advance > 0
                            ? `<span class="badge badge-info">⚡ ${formatCurrency(
                                day.received_advance
                              )}</span>`
                            : ""
                        }
                        ${
                          day.pending > 0
                            ? `<span class="badge badge-warning">⏳ ${formatCurrency(
                                day.pending
                              )}</span>`
                            : ""
                        }
                        ${
                          day.overdue > 0
                            ? `<span class="badge badge-danger">⚠️ ${formatCurrency(
                                day.overdue
                              )}</span>`
                            : ""
                        }
                    </div>
                    <div class="daily-count">
                        <small>${day.count_expected} parcela(s)</small>
                    </div>
                </div>
            `;
    }
  });

  html += `
        </div>
    `;

  targetContainer.innerHTML = html;
}

function renderTransactionsTable(transactions) {
  const container = document.getElementById("transactions-table");
  if (!container) return;

  let html = `
        <div class="table-header">
            <h3>Transações por Tipo</h3>
        </div>
    `;

  for (const [type, data] of Object.entries(transactions)) {
    html += `
            <div class="transaction-group">
                <h4>${type} (${data.count})</h4>
                <p>Total: ${formatCurrency(data.total_amount)}</p>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>External Ref</th>
                            <th>Valor Bruto</th>
                            <th>Valor Líquido</th>
                            <th>Método</th>
                            <th>Data</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

    data.transactions.slice(0, 10).forEach((trans) => {
      html += `
                <tr>
                    <td><code>${trans.external_reference}</code></td>
                    <td>${formatCurrency(trans.amount)}</td>
                    <td>${formatCurrency(trans.net_amount)}</td>
                    <td>${trans.payment_method}</td>
                    <td>${formatDate(trans.date)}</td>
                </tr>
            `;
    });

    html += `
                    </tbody>
                </table>
            </div>
        `;
  }

  container.innerHTML = html;
}

function renderReconciliationReport(report) {
  const container = document.getElementById("reconciliation-report");
  if (!container) return;

  const detailed = report.detailed_status || {};
  const validation = report.validation || {};
  const orphans = report.orphan_payments || {};
  const advances = report.advance_payments || {};

  let html = `
        <div class="reconciliation-summary">
            <h3>Relatório de Conciliação V3</h3>
            
            <div class="summary-cards">
                <div class="summary-card">
                    <h4>Validação de Valores</h4>
                    <p>Esperado: ${formatCurrency(
                      validation.installments_vs_payments
                        ?.installments_received || 0
                    )}</p>
                    <p>Payments: ${formatCurrency(
                      validation.installments_vs_payments?.payments_filtered ||
                        0
                    )}</p>
                    <p>Diferença: ${formatCurrency(
                      validation.installments_vs_payments?.difference || 0
                    )}</p>
                    <p class="${
                      validation.installments_vs_payments?.is_valid
                        ? "text-success"
                        : "text-danger"
                    }">
                        ${
                          validation.installments_vs_payments?.is_valid
                            ? "✅ Válido"
                            : "❌ Divergência"
                        }
                    </p>
                </div>
                
                <div class="summary-card">
                    <h4>Payments Órfãos</h4>
                    <p>Quantidade: ${orphans.count || 0}</p>
                    <p>Total: ${formatCurrency(orphans.total_amount || 0)}</p>
                </div>
                
                <div class="summary-card">
                    <h4>Adiantamentos</h4>
                    <p>Pedidos: ${advances.count || 0}</p>
                </div>
            </div>
        </div>
    `;

  container.innerHTML = html;
}

// ========================================
// UTILIDADES
// ========================================

function formatCurrency(value) {
  if (value === null || value === undefined) return "R$ 0,00";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}

function formatDate(dateString) {
  if (!dateString) return "-";
  try {
    // Handle YYYY-MM-DD format without timezone conversion
    // Split the date string and parse it directly to avoid timezone issues
    if (typeof dateString === 'string' && dateString.match(/^\d{4}-\d{2}-\d{2}/)) {
      const [year, month, day] = dateString.substring(0, 10).split('-');
      // Create date with explicit UTC components to avoid timezone shift
      const date = new Date(year + '-' + month + '-' + day + 'T00:00:00Z');
      // Format as pt-BR: DD/MM/YYYY
      const d = String(date.getUTCDate()).padStart(2, '0');
      const m = String(date.getUTCMonth() + 1).padStart(2, '0');
      const y = date.getUTCFullYear();
      return `${d}/${m}/${y}`;
    }

    // Fallback for other formats
    const date = new Date(dateString);
    return date.toLocaleDateString("pt-BR");
  } catch {
    return dateString;
  }
}

function getStatusClass(status) {
  const classes = {
    received: "badge-success",
    received_advance: "badge-info",
    pending: "badge-warning",
    overdue: "badge-danger",
    cancelled: "badge-secondary",
  };
  return classes[status] || "badge-secondary";
}

function getStatusLabel(status) {
  const labels = {
    received: "Recebido",
    received_advance: "Antecipado",
    pending: "Pendente",
    overdue: "Atrasado",
    cancelled: "Cancelado",
  };
  return labels[status] || status;
}

function clearAllData() {
  [
    "total-expected",
    "total-received",
    "total-pending",
    "total-overdue",
  ].forEach((id) => {
    updateCard(id, 0, 0);
  });

  const infoEl = document.getElementById("system-info");
  if (infoEl) {
    infoEl.innerHTML = "<p>Dados não processados</p>";
  }
}

// ========================================
// NOTIFICAÇÕES
// ========================================

function showSuccess(message) {
  showNotification(message, "success");
}

function showError(message) {
  showNotification(message, "error");
}

function showInfo(message) {
  showNotification(message, "info");
}

function showNotification(message, type = "info") {
  console.log(`[${type.toUpperCase()}] ${message}`);

  const notifEl = document.getElementById("notification");
  if (notifEl) {
    notifEl.textContent = message;
    notifEl.className = `notification notification-${type} show`;

    setTimeout(() => {
      notifEl.classList.remove("show");
    }, 3000);
  }
}

function hideMessage() {
  const notifEl = document.getElementById("notification");
  if (notifEl) {
    notifEl.classList.remove("show");
  }
}
