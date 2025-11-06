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
  receivedInstallments: [], // Armazena todas as parcelas recebidas
  allTransactions: [], // Armazena todas as transações
  transactionTypes: new Set(), // Tipos de transações disponíveis
  paymentMethods: new Set(), // Métodos de pagamento disponíveis
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

  // Botões de toggle do fluxo de caixa
  document.getElementById("btn-monthly")?.addEventListener("click", () => {
    switchCashflowView("monthly");
  });
  document.getElementById("btn-daily")?.addEventListener("click", () => {
    switchCashflowView("daily");
  });

  // Filtros de recebidos
  document.getElementById("btn-apply-received-filter")?.addEventListener("click", applyReceivedFilters);
  document.getElementById("btn-clear-received-filter")?.addEventListener("click", clearReceivedFilters);

  // Filtros de transações
  document.getElementById("btn-apply-transaction-filter")?.addEventListener("click", applyTransactionFilters);
  document.getElementById("btn-clear-transaction-filter")?.addEventListener("click", clearTransactionFilters);

  // Debug de external reference
  document.getElementById("btn-debug-reference")?.addEventListener("click", debugExternalReference);
  document.getElementById("debug-external-ref")?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      debugExternalReference();
    }
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
    renderMonthlyCashflow(monthlyData.cashflow);
  }

  // Carregar fluxo diário
  const dailyResponse = await fetch("/api/cashflow/daily");
  const dailyData = await dailyResponse.json();

  if (dailyData.success) {
    renderDailyCashflow(dailyData.cashflow);
  }
}

function switchCashflowView(viewType) {
  const monthlyBtn = document.getElementById("btn-monthly");
  const dailyBtn = document.getElementById("btn-daily");
  const monthlyView = document.getElementById("cashflow-monthly-view");
  const dailyView = document.getElementById("cashflow-daily-view");

  if (viewType === "monthly") {
    monthlyBtn?.classList.add("active");
    dailyBtn?.classList.remove("active");
    if (monthlyView) monthlyView.style.display = "block";
    if (dailyView) dailyView.style.display = "none";
  } else {
    dailyBtn?.classList.add("active");
    monthlyBtn?.classList.remove("active");
    if (monthlyView) monthlyView.style.display = "none";
    if (dailyView) dailyView.style.display = "block";
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
    // Armazenar dados no estado para filtros
    state.receivedInstallments = data.installments;
    renderInstallmentsTable("received-table", data.installments, "recebidas");
  }
}

function applyReceivedFilters() {
  if (!state.receivedInstallments || state.receivedInstallments.length === 0) {
    showInfo("Nenhuma parcela recebida para filtrar");
    return;
  }

  // Obter valores dos filtros
  const typeFilter = document.getElementById("filter-received-type")?.value || "all";
  const dateStartFilter = document.getElementById("filter-received-date-start")?.value || "";
  const dateEndFilter = document.getElementById("filter-received-date-end")?.value || "";
  const minValueFilter = parseFloat(document.getElementById("filter-received-min-value")?.value) || 0;
  const maxValueFilter = parseFloat(document.getElementById("filter-received-max-value")?.value) || Infinity;

  // Aplicar filtros
  let filtered = state.receivedInstallments.filter(inst => {
    // Filtro por tipo
    if (typeFilter !== "all" && inst.status !== typeFilter) {
      return false;
    }

    // Filtro por data de recebimento
    const receivedDate = inst.received_date ? inst.received_date.substring(0, 10) : "";
    if (dateStartFilter && receivedDate < dateStartFilter) {
      return false;
    }
    if (dateEndFilter && receivedDate > dateEndFilter) {
      return false;
    }

    // Filtro por valor
    const value = inst.received_amount || 0;
    if (value < minValueFilter || value > maxValueFilter) {
      return false;
    }

    return true;
  });

  // Renderizar tabela filtrada
  renderInstallmentsTable("received-table", filtered, "recebidas (filtradas)");
  showSuccess(`${filtered.length} parcelas encontradas`);
}

function clearReceivedFilters() {
  // Limpar campos
  document.getElementById("filter-received-type").value = "all";
  document.getElementById("filter-received-date-start").value = "";
  document.getElementById("filter-received-date-end").value = "";
  document.getElementById("filter-received-min-value").value = "";
  document.getElementById("filter-received-max-value").value = "";

  // Recarregar tabela completa
  if (state.receivedInstallments && state.receivedInstallments.length > 0) {
    renderInstallmentsTable("received-table", state.receivedInstallments, "recebidas");
    showSuccess("Filtros limpos");
  }
}

async function loadTransactionsData() {
  const response = await fetch("/api/transactions");
  const data = await response.json();

  if (data.success) {
    // Processar transações e armazenar no estado
    state.allTransactions = [];
    state.transactionTypes = new Set();
    state.paymentMethods = new Set();

    for (const [type, typeData] of Object.entries(data.transactions)) {
      state.transactionTypes.add(type);

      typeData.transactions.forEach(trans => {
        state.allTransactions.push({
          ...trans,
          type: type
        });
        state.paymentMethods.add(trans.payment_method);
      });
    }

    // Ordenar por data (mais recente primeiro)
    state.allTransactions.sort((a, b) => {
      const dateA = a.date || '0000-01-01';
      const dateB = b.date || '0000-01-01';
      return dateB.localeCompare(dateA);
    });

    // Popular filtros dinâmicos
    populateTransactionFilters();

    // Renderizar tabela
    renderTransactionsTable(data.transactions);
  }
}

function populateTransactionFilters() {
  // Popular select de tipos
  const typeSelect = document.getElementById("filter-transaction-type");
  if (typeSelect) {
    // Limpar opções existentes (exceto "Todos")
    while (typeSelect.options.length > 1) {
      typeSelect.remove(1);
    }

    // Adicionar tipos únicos
    Array.from(state.transactionTypes).sort().forEach(type => {
      const option = document.createElement("option");
      option.value = type;
      option.textContent = type;
      typeSelect.appendChild(option);
    });
  }

  // Popular select de métodos
  const methodSelect = document.getElementById("filter-transaction-method");
  if (methodSelect) {
    // Limpar opções existentes (exceto "Todos")
    while (methodSelect.options.length > 1) {
      methodSelect.remove(1);
    }

    // Adicionar métodos únicos
    Array.from(state.paymentMethods).sort().forEach(method => {
      const option = document.createElement("option");
      option.value = method;
      option.textContent = method;
      methodSelect.appendChild(option);
    });
  }
}

function applyTransactionFilters() {
  if (!state.allTransactions || state.allTransactions.length === 0) {
    showInfo("Nenhuma transação para filtrar");
    return;
  }

  // Obter valores dos filtros
  const typeFilter = document.getElementById("filter-transaction-type")?.value || "all";
  const methodFilter = document.getElementById("filter-transaction-method")?.value || "all";
  const dateStartFilter = document.getElementById("filter-transaction-date-start")?.value || "";
  const dateEndFilter = document.getElementById("filter-transaction-date-end")?.value || "";
  const minValueFilter = parseFloat(document.getElementById("filter-transaction-min-value")?.value) || 0;
  const maxValueFilter = parseFloat(document.getElementById("filter-transaction-max-value")?.value) || Infinity;

  // Aplicar filtros
  let filtered = state.allTransactions.filter(trans => {
    // Filtro por tipo
    if (typeFilter !== "all" && trans.type !== typeFilter) {
      return false;
    }

    // Filtro por método de pagamento
    if (methodFilter !== "all" && trans.payment_method !== methodFilter) {
      return false;
    }

    // Filtro por data
    const transDate = trans.date ? trans.date.substring(0, 10) : "";
    if (dateStartFilter && transDate < dateStartFilter) {
      return false;
    }
    if (dateEndFilter && transDate > dateEndFilter) {
      return false;
    }

    // Filtro por valor líquido
    const value = trans.net_amount || 0;
    if (value < minValueFilter || value > maxValueFilter) {
      return false;
    }

    return true;
  });

  // Agrupar por tipo novamente para renderizar
  const groupedFiltered = {};
  filtered.forEach(trans => {
    if (!groupedFiltered[trans.type]) {
      groupedFiltered[trans.type] = {
        count: 0,
        total_amount: 0,
        transactions: []
      };
    }
    groupedFiltered[trans.type].count++;
    groupedFiltered[trans.type].total_amount += trans.net_amount;
    groupedFiltered[trans.type].transactions.push(trans);
  });

  // Renderizar tabela filtrada
  renderTransactionsTable(groupedFiltered, true);
  showSuccess(`${filtered.length} transações encontradas`);
}

function clearTransactionFilters() {
  // Limpar campos
  document.getElementById("filter-transaction-type").value = "all";
  document.getElementById("filter-transaction-method").value = "all";
  document.getElementById("filter-transaction-date-start").value = "";
  document.getElementById("filter-transaction-date-end").value = "";
  document.getElementById("filter-transaction-min-value").value = "";
  document.getElementById("filter-transaction-max-value").value = "";

  // Recarregar dados
  if (state.allTransactions && state.allTransactions.length > 0) {
    loadTransactionsData();
    showSuccess("Filtros limpos");
  }
}

async function loadReconciliationData() {
  const response = await fetch("/api/reconciliation");
  const data = await response.json();

  if (data.success) {
    renderReconciliationReport(data.report);
  }
}

async function debugExternalReference() {
  const input = document.getElementById("debug-external-ref");
  const resultsContainer = document.getElementById("debug-results");

  if (!input || !resultsContainer) return;

  const externalRef = input.value.trim();

  if (!externalRef) {
    showError("Digite uma external reference para analisar");
    return;
  }

  try {
    resultsContainer.innerHTML = '<p>Analisando...</p>';

    const response = await fetch(`/api/debug/reference/${encodeURIComponent(externalRef)}`);
    const data = await response.json();

    if (data.success) {
      renderDebugResults(data);
      showSuccess("Análise concluída");
    } else {
      throw new Error(data.error || "Erro ao analisar");
    }
  } catch (error) {
    console.error("Erro ao debugar reference:", error);
    showError(`Erro ao analisar: ${error.message}`);
    resultsContainer.innerHTML = `<p class="text-danger">Erro: ${error.message}</p>`;
  }
}

function renderDebugResults(data) {
  const container = document.getElementById("debug-results");
  if (!container) return;

  const settlement = data.settlement || {};
  const releases = data.releases || {};
  const reconciliation = data.reconciliation || {};

  const settlementTotal = settlement.installments?.reduce(
    (sum, i) => sum + (i.installment_net_amount || 0), 0
  ) || 0;

  const settlementReceived = settlement.installments?.filter(
    i => i.status === 'received' || i.status === 'received_advance'
  ).reduce((sum, i) => sum + (i.received_amount || 0), 0) || 0;

  const hasDivergence = Math.abs(settlementReceived - releases.total_payments) > 0.01;

  let html = `
    <div class="debug-results-box ${hasDivergence ? 'debug-error' : 'debug-success'}">
      <h4>📋 Análise: ${data.external_reference}</h4>

      <!-- Resumo Rápido -->
      <div class="debug-summary">
        <div class="debug-summary-item">
          <strong>Status:</strong>
          <span class="${hasDivergence ? 'text-danger' : 'text-success'}">
            ${hasDivergence ? '❌ DIVERGÊNCIA' : '✅ CONCILIADO'}
          </span>
        </div>
        ${hasDivergence ? `
        <div class="debug-summary-item">
          <strong>Diferença:</strong>
          <span class="text-danger">${formatCurrency(Math.abs(settlementReceived - releases.total_payments))}</span>
        </div>
        ` : ''}
      </div>

      <!-- Settlement -->
      <div class="debug-section">
        <h5>📊 Settlement (Esperado)</h5>
        <table class="data-table">
          <tbody>
            <tr>
              <td>Parcelas no Settlement:</td>
              <td class="text-right"><strong>${settlement.installments_count || 0}</strong></td>
            </tr>
            <tr>
              <td>Valor Total Líquido:</td>
              <td class="text-right">${formatCurrency(settlementTotal)}</td>
            </tr>
            <tr>
              <td>Valor Recebido:</td>
              <td class="text-right"><strong>${formatCurrency(settlementReceived)}</strong></td>
            </tr>
          </tbody>
        </table>

        ${settlement.order_balance ? `
        <p class="info-text" style="margin-top: 10px;">
          Order Balance: Total Net = ${formatCurrency(settlement.order_balance.total_net || 0)} |
          Refunded = ${formatCurrency(settlement.order_balance.refunded || 0)} |
          Chargeback = ${formatCurrency(settlement.order_balance.chargeback || 0)}
        </p>
        ` : ''}
      </div>

      <!-- Releases -->
      <div class="debug-section">
        <h5>💳 Releases (Arquivo de Liberações)</h5>
        <table class="data-table">
          <tbody>
            <tr>
              <td>Total de Linhas no Releases:</td>
              <td class="text-right"><strong>${releases.all_releases_count || 0}</strong></td>
            </tr>
            <tr>
              <td>Payments Válidos (vendas):</td>
              <td class="text-right"><strong>${releases.payments_count || 0}</strong></td>
            </tr>
            <tr>
              <td>Total de Payments:</td>
              <td class="text-right"><strong>${formatCurrency(releases.total_payments || 0)}</strong></td>
            </tr>
            ${releases.has_refund ? `
            <tr class="row-warning">
              <td>⚠️ Contém REFUND</td>
              <td class="text-right text-warning"><strong>SIM</strong></td>
            </tr>
            ` : ''}
            ${releases.has_chargeback ? `
            <tr class="row-warning">
              <td>⚠️ Contém CHARGEBACK</td>
              <td class="text-right text-warning"><strong>SIM</strong></td>
            </tr>
            ` : ''}
          </tbody>
        </table>
      </div>

      <!-- Comparação -->
      <div class="debug-section ${hasDivergence ? 'section-error' : ''}">
        <h5>⚖️ Comparação</h5>
        <table class="data-table">
          <tbody>
            <tr>
              <td><strong>Settlement (Recebido)</strong></td>
              <td class="text-right"><strong>${formatCurrency(settlementReceived)}</strong></td>
            </tr>
            <tr>
              <td><strong>Releases (Payments)</strong></td>
              <td class="text-right"><strong>${formatCurrency(releases.total_payments || 0)}</strong></td>
            </tr>
            <tr class="${hasDivergence ? 'row-error' : 'row-success'}">
              <td><strong>Diferença</strong></td>
              <td class="text-right ${hasDivergence ? 'text-danger' : 'text-success'}">
                <strong>${formatCurrency(Math.abs(settlementReceived - (releases.total_payments || 0)))}</strong>
                ${hasDivergence ? ' ❌' : ' ✅'}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Detalhes das Parcelas -->
      ${settlement.installments && settlement.installments.length > 0 ? `
      <div class="debug-section">
        <h5>📝 Detalhes das Parcelas</h5>
        <table class="data-table">
          <thead>
            <tr>
              <th>Parcela</th>
              <th>Status</th>
              <th>Valor Líquido</th>
              <th>Valor Recebido</th>
              <th>Data Prevista</th>
              <th>Data Recebida</th>
            </tr>
          </thead>
          <tbody>
            ${settlement.installments.map(inst => `
              <tr>
                <td>${inst.installment_number}/${inst.total_installments}</td>
                <td><span class="badge ${getStatusClass(inst.status)}">${getStatusLabel(inst.status)}</span></td>
                <td>${formatCurrency(inst.installment_net_amount || 0)}</td>
                <td>${inst.received_amount ? formatCurrency(inst.received_amount) : '-'}</td>
                <td>${formatDate(inst.money_release_date)}</td>
                <td>${inst.received_date ? formatDate(inst.received_date) : '-'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      ` : ''}

      <!-- TODAS as Linhas do Releases -->
      ${releases.all_releases && releases.all_releases.length > 0 ? `
      <div class="debug-section">
        <h5>📄 TODAS as Linhas do Releases (${releases.all_releases_count})</h5>
        <p class="info-text">Esta tabela mostra TODAS as linhas encontradas no arquivo releases, incluindo refunds, chargebacks, e movimentações.</p>
        <table class="data-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Descrição</th>
              <th>Tipo</th>
              <th>Crédito</th>
              <th>Débito</th>
              <th>Líquido</th>
              <th>Source ID</th>
            </tr>
          </thead>
          <tbody>
            ${releases.all_releases.map(rel => {
              const isRefund = rel.description === 'refund';
              const isChargeback = rel.description && rel.description.includes('chargeback');
              const isPayment = rel.description === 'payment';
              const rowClass = isRefund || isChargeback ? 'row-warning' : (isPayment ? '' : 'row-light');

              return `
              <tr class="${rowClass}">
                <td>${formatDate(rel.settlement_date)}</td>
                <td>
                  <span class="badge ${isPayment ? 'badge-success' : (isRefund || isChargeback ? 'badge-danger' : 'badge-secondary')}">
                    ${rel.description || '-'}
                  </span>
                </td>
                <td>${rel.record_type || '-'}</td>
                <td class="text-right">${rel.net_credit_amount > 0 ? formatCurrency(rel.net_credit_amount) : '-'}</td>
                <td class="text-right">${rel.net_debit_amount > 0 ? formatCurrency(rel.net_debit_amount) : '-'}</td>
                <td class="text-right"><strong>${formatCurrency((rel.net_credit_amount || 0) - (rel.net_debit_amount || 0))}</strong></td>
                <td><code>${rel.source_id || '-'}</code></td>
              </tr>
            `}).join('')}
          </tbody>
        </table>
        <p class="info-text" style="margin-top: 10px;">
          <strong>Legenda:</strong>
          <span class="badge badge-success">payment</span> = Venda válida (usado na conciliação) |
          <span class="badge badge-danger">refund/chargeback</span> = Estorno/Contestação (NÃO usado) |
          <span class="badge badge-secondary">outros</span> = Movimentação interna
        </p>
      </div>
      ` : ''}

      <!-- Detalhes dos Payments (apenas válidos) -->
      ${releases.payments && releases.payments.length > 0 ? `
      <div class="debug-section">
        <h5>💰 Payments Válidos (Usados na Conciliação)</h5>
        <table class="data-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Tipo</th>
              <th>Valor Bruto</th>
              <th>Valor Líquido</th>
              <th>Source ID</th>
            </tr>
          </thead>
          <tbody>
            ${releases.payments.map(payment => `
              <tr>
                <td>${formatDate(payment.settlement_date)}</td>
                <td>${payment.record_type || '-'}</td>
                <td>${formatCurrency(payment.gross_amount || 0)}</td>
                <td><strong>${formatCurrency(payment.net_credit_amount || 0)}</strong></td>
                <td><code>${payment.source_id || '-'}</code></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      ` : releases.all_releases_count > 0 ? `
      <div class="debug-section section-error">
        <h5>⚠️ PROBLEMA: Nenhum Payment Válido</h5>
        <p class="text-danger">
          <strong>O releases tem ${releases.all_releases_count} linha(s), mas NENHUMA é um "payment" válido!</strong>
        </p>
        <p>Isso significa que todas as linhas são refunds, chargebacks, ou outras movimentações que não representam vendas.</p>
        <p><strong>CONCLUSÃO:</strong> Por isso o sistema está mostrando a parcela como PENDENTE - não há payment para conciliar!</p>
      </div>
      ` : ''}
    </div>
  `;

  container.innerHTML = html;
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

    // Status cancelado tem prioridade
    if (inst.is_cancelled || inst.status === "cancelled") {
      const reason = inst.cancelled_reason || 'unknown';
      if (reason === 'full_refund') {
        obs += "🚫 Cancelada (Refund Total)";
      } else if (reason === 'chargeback') {
        obs += "🚫 Cancelada (Chargeback Total)";
      } else if (reason === 'partial_refund_full_cancellation') {
        obs += "🚫 Cancelada (Refund: " + formatCurrency(inst.refund_applied) + ")";
      } else {
        obs += "🚫 Cancelada";
      }
    } else {
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

function renderMonthlyCashflow(cashflow) {
  const container = document.getElementById("cashflow-monthly-view");
  if (!container) return;

  // Calcular total a receber
  const totalToReceive = cashflow.reduce((sum, month) => sum + (month.to_receive || 0), 0);

  let html = `
        <div class="table-header">
            <h3>Fluxo de Caixa Mensal - A Receber</h3>
            <p>Total: ${formatCurrency(totalToReceive)}</p>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Mês</th>
                    <th>A Receber</th>
                    <th>Pendente</th>
                    <th>Atrasado</th>
                    <th>Parcelas</th>
                </tr>
            </thead>
            <tbody>
    `;

  cashflow.forEach((month) => {
    html += `
            <tr>
                <td><strong>${month.month}</strong></td>
                <td><strong>${formatCurrency(month.to_receive)}</strong></td>
                <td class="text-warning">${formatCurrency(month.pending)}</td>
                <td class="text-danger">${formatCurrency(month.overdue)}</td>
                <td>${month.count_to_receive}</td>
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
  const container = document.getElementById("cashflow-daily-view");
  if (!container) return;

  // Filtrar apenas dias com dados a receber
  const daysWithData = dailyFlow.filter(day => day.to_receive > 0);

  // Calcular total a receber
  const totalToReceive = daysWithData.reduce((sum, day) => sum + (day.to_receive || 0), 0);

  let html = `
        <div class="table-header">
            <h3>Fluxo de Caixa Diário - A Receber</h3>
            <p>${daysWithData.length} dias com recebimentos | Total: ${formatCurrency(totalToReceive)}</p>
        </div>
        <table class="data-table">
            <thead>
                <tr>
                    <th>Data</th>
                    <th>A Receber</th>
                    <th>Pendente</th>
                    <th>Atrasado</th>
                    <th>Parcelas</th>
                </tr>
            </thead>
            <tbody>
    `;

  daysWithData.forEach((day) => {
    html += `
            <tr>
                <td><strong>${formatDate(day.date)}</strong></td>
                <td><strong>${formatCurrency(day.to_receive)}</strong></td>
                <td class="text-warning">${formatCurrency(day.pending)}</td>
                <td class="text-danger">${formatCurrency(day.overdue)}</td>
                <td>${day.count_to_receive}</td>
            </tr>
        `;
  });

  html += `
            </tbody>
        </table>
    `;

  container.innerHTML = html;
}

function renderTransactionsTable(transactions, isFiltered = false) {
  const container = document.getElementById("transactions-table");
  if (!container) return;

  const title = isFiltered ? "Transações Filtradas" : "Transações por Tipo";

  let html = `
        <div class="table-header">
            <h3>${title}</h3>
        </div>
    `;

  for (const [type, data] of Object.entries(transactions)) {
    // Ordenar transações por data (mais recente primeiro)
    const sortedTransactions = [...data.transactions].sort((a, b) => {
      const dateA = a.date || '0000-01-01';
      const dateB = b.date || '0000-01-01';
      return dateB.localeCompare(dateA);
    });

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

    // Mostrar todas se filtrado, senão limitar a 10
    const transactionsToShow = isFiltered ? sortedTransactions : sortedTransactions.slice(0, 10);

    transactionsToShow.forEach((trans) => {
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
  const summary = detailed.summary || {};
  const statusBreakdown = detailed.status_breakdown || {};
  const validation = report.validation || {};
  const installmentsVsPayments = validation.installments_vs_payments || {};
  const orphans = report.orphan_payments || {};
  const advances = report.advance_payments || {};
  const adjustments = report.adjustments_analysis || {};

  const isDivergent = !installmentsVsPayments.is_valid;
  const difference = installmentsVsPayments.difference || 0;

  let html = `
        <div class="reconciliation-summary">
            <h3>Relatório de Conciliação V3</h3>

            <!-- Status Geral -->
            <div class="summary-cards">
                <div class="summary-card ${isDivergent ? 'card-danger' : 'card-success'}">
                    <h4>Status da Conciliação</h4>
                    <p class="reconciliation-status ${isDivergent ? 'text-danger' : 'text-success'}">
                        ${isDivergent ? '❌ DIVERGÊNCIA ENCONTRADA' : '✅ CONCILIADO'}
                    </p>
                    ${isDivergent ? `<p><strong>Diferença: ${formatCurrency(Math.abs(difference))}</strong></p>` : ''}
                </div>

                <div class="summary-card">
                    <h4>Parcelas Totais</h4>
                    <p>Total: ${summary.total_installments || 0}</p>
                    <p>Ativas: ${summary.active_installments || 0}</p>
                    <p>Canceladas: ${summary.cancelled_installments || 0}</p>
                </div>

                <div class="summary-card">
                    <h4>Valores Totais</h4>
                    <p>Esperado: ${formatCurrency(summary.total_expected || 0)}</p>
                    <p>Recebido: ${formatCurrency(summary.total_received || 0)}</p>
                    <p>Pendente: ${formatCurrency(summary.total_pending || 0)}</p>
                </div>
            </div>

            <!-- Breakdown por Status -->
            <div class="reconciliation-section">
                <h4>Breakdown por Status</h4>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Status</th>
                            <th>Quantidade</th>
                            <th>Valor Total</th>
                            <th>Percentual</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><span class="badge badge-success">Recebido</span></td>
                            <td>${statusBreakdown.received?.count || 0}</td>
                            <td>${formatCurrency(statusBreakdown.received?.amount || 0)}</td>
                            <td>${statusBreakdown.received?.percentage || 0}%</td>
                        </tr>
                        <tr>
                            <td><span class="badge badge-info">Antecipado</span></td>
                            <td>${statusBreakdown.received_advance?.count || 0}</td>
                            <td>${formatCurrency(statusBreakdown.received_advance?.amount || 0)}</td>
                            <td>${statusBreakdown.received_advance?.percentage || 0}%</td>
                        </tr>
                        <tr>
                            <td><span class="badge badge-warning">Pendente</span></td>
                            <td>${statusBreakdown.pending?.count || 0}</td>
                            <td>${formatCurrency(statusBreakdown.pending?.amount || 0)}</td>
                            <td>${statusBreakdown.pending?.percentage || 0}%</td>
                        </tr>
                        <tr>
                            <td><span class="badge badge-danger">Atrasado</span></td>
                            <td>${statusBreakdown.overdue?.count || 0}</td>
                            <td>${formatCurrency(statusBreakdown.overdue?.amount || 0)}</td>
                            <td>${statusBreakdown.overdue?.percentage || 0}%</td>
                        </tr>
                        <tr>
                            <td><span class="badge badge-secondary">Cancelado</span></td>
                            <td>${statusBreakdown.cancelled?.count || 0}</td>
                            <td>R$ 0,00</td>
                            <td>${statusBreakdown.cancelled?.percentage || 0}%</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Validação: Installments vs Payments -->
            <div class="reconciliation-section ${isDivergent ? 'section-error' : ''}">
                <h4>Validação: Parcelas Recebidas vs Payments</h4>
                <table class="data-table">
                    <tbody>
                        <tr>
                            <td><strong>Parcelas Recebidas (Settlement)</strong></td>
                            <td class="text-right"><strong>${formatCurrency(installmentsVsPayments.installments_received || 0)}</strong></td>
                        </tr>
                        <tr>
                            <td>Payments Totais (Releases)</td>
                            <td class="text-right">${formatCurrency(installmentsVsPayments.payments_all || 0)}</td>
                        </tr>
                        <tr>
                            <td>(-) Payments Órfãos</td>
                            <td class="text-right text-danger">(${formatCurrency(installmentsVsPayments.payments_orphan || 0)})</td>
                        </tr>
                        <tr class="table-separator">
                            <td><strong>Payments Filtrados</strong></td>
                            <td class="text-right"><strong>${formatCurrency(installmentsVsPayments.payments_filtered || 0)}</strong></td>
                        </tr>
                        <tr class="${isDivergent ? 'row-error' : 'row-success'}">
                            <td><strong>Diferença</strong></td>
                            <td class="text-right ${isDivergent ? 'text-danger' : 'text-success'}">
                                <strong>${formatCurrency(Math.abs(difference))}</strong>
                                ${isDivergent ? ' ❌' : ' ✅'}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Ajustes Aplicados -->
            ${summary.total_refund_applied > 0 || summary.total_chargeback_applied > 0 ? `
            <div class="reconciliation-section">
                <h4>Ajustes Aplicados</h4>
                <table class="data-table">
                    <tbody>
                        <tr>
                            <td>Estornos Aplicados</td>
                            <td class="text-right text-warning">${formatCurrency(summary.total_refund_applied || 0)}</td>
                        </tr>
                        <tr>
                            <td>Chargebacks Aplicados</td>
                            <td class="text-right text-danger">${formatCurrency(summary.total_chargeback_applied || 0)}</td>
                        </tr>
                        <tr>
                            <td><strong>Total de Ajustes</strong></td>
                            <td class="text-right"><strong>${formatCurrency((summary.total_refund_applied || 0) + (summary.total_chargeback_applied || 0))}</strong></td>
                        </tr>
                    </tbody>
                </table>
                <p class="info-text">Pedidos com ajustes: ${adjustments.orders_with_adjustments || 0}</p>
            </div>
            ` : ''}

            <!-- Payments Órfãos -->
            ${orphans.count > 0 ? `
            <div class="reconciliation-section section-warning">
                <h4>⚠️ Payments Órfãos (Sem Match)</h4>
                <p>Quantidade: <strong>${orphans.count}</strong></p>
                <p>Valor Total: <strong>${formatCurrency(orphans.total_amount || 0)}</strong></p>
                <p class="info-text">Payments que não foram associados a nenhuma parcela do settlement.</p>
            </div>
            ` : ''}

            <!-- Adiantamentos -->
            ${advances.count > 0 ? `
            <div class="reconciliation-section">
                <h4>⚡ Adiantamentos Detectados</h4>
                <p>Pedidos com antecipação: <strong>${advances.count}</strong></p>
                ${statusBreakdown.received_advance?.avg_days_advance ?
                    `<p>Média de dias antecipados: <strong>${statusBreakdown.received_advance.avg_days_advance}</strong></p>` : ''}
            </div>
            ` : ''}
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
