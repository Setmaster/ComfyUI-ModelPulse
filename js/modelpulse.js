import { app } from "../../scripts/app.js";

/**
 * ModelPulse - Usage Tracker Extension
 *
 * Displays model usage statistics in a sidebar panel.
 */

// State management
let currentTimeframe = "all";
let currentSort = "last_used";
let searchQuery = "";
let usageData = null;
let isLoading = false;
let showSettings = false;

// Settings with defaults
let settings = {
    staleThresholdDays: 30,
};

// Load settings from localStorage
function loadSettings() {
    try {
        const saved = localStorage.getItem("modelpulse_settings");
        if (saved) {
            settings = { ...settings, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.warn("[ModelPulse] Failed to load settings:", e);
    }
}

// Save settings to localStorage
function saveSettings() {
    try {
        localStorage.setItem("modelpulse_settings", JSON.stringify(settings));
    } catch (e) {
        console.warn("[ModelPulse] Failed to save settings:", e);
    }
}

// Initialize settings on load
loadSettings();

/**
 * Fetch usage data from the API
 */
async function fetchUsageData(timeframe = "all", sortBy = "last_used") {
    try {
        const response = await fetch(
            `/modelpulse/usage?timeframe=${timeframe}&sort=${sortBy}`
        );
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("[ModelPulse] Error fetching usage data:", error);
        return null;
    }
}

/**
 * Format ISO date to relative time string
 */
function formatLastUsed(isoDate) {
    if (!isoDate) return "Never";

    const date = new Date(isoDate);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 30) return `${diffDays}d ago`;

    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths < 12) return `${diffMonths}mo ago`;

    const diffYears = Math.floor(diffDays / 365);
    return `${diffYears}y ago`;
}

/**
 * Get category display info
 */
function getCategoryInfo(category) {
    const categories = {
        checkpoint: { name: "Checkpoints", icon: "📦" },
        lora: { name: "LoRAs", icon: "✨" },
        vae: { name: "VAEs", icon: "⚙️" },
        controlnet: { name: "ControlNets", icon: "🎛️" },
        clip: { name: "CLIP", icon: "💬" },
        unet: { name: "UNETs", icon: "🖥️" },
        upscaler: { name: "Upscalers", icon: "🔍" },
        style_model: { name: "Style Models", icon: "🎨" },
        gligen: { name: "GLIGEN", icon: "📐" },
        gguf: { name: "GGUF", icon: "🗜️" },
    };
    return categories[category] || { name: category, icon: "📁" };
}

/**
 * Check if a model is stale (unused for > threshold days)
 */
function isStale(lastUsed) {
    if (!lastUsed) return true;
    const date = new Date(lastUsed);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    return diffDays > settings.staleThresholdDays;
}

/**
 * Filter models by search query
 */
function filterModels(models, query) {
    if (!query || !query.trim()) return models;
    const lowerQuery = query.toLowerCase().trim();
    return models.filter(model =>
        model.name.toLowerCase().includes(lowerQuery) ||
        model.category.toLowerCase().includes(lowerQuery)
    );
}

/**
 * Group models by category
 */
function groupByCategory(models) {
    const groups = {};
    for (const model of models) {
        const cat = model.category;
        if (!groups[cat]) {
            groups[cat] = [];
        }
        groups[cat].push(model);
    }
    return groups;
}

/**
 * Create the styles for the UI
 */
function createStyles() {
    const style = document.createElement("style");
    style.textContent = `
        .modelpulse-container {
            display: flex;
            flex-direction: column;
            height: 100%;
            font-family: var(--comfy-font, sans-serif);
            font-size: 13px;
            color: var(--input-text, #ddd);
        }

        .modelpulse-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid var(--border-color, #444);
        }

        .modelpulse-title {
            font-size: 15px;
            font-weight: 600;
        }

        .modelpulse-refresh {
            background: transparent;
            border: none;
            color: var(--input-text, #ddd);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 14px;
        }

        .modelpulse-refresh:hover {
            background: var(--comfy-menu-bg-hover, #333);
        }

        .modelpulse-refresh.loading {
            opacity: 0.5;
            cursor: wait;
        }

        .modelpulse-tabs {
            display: flex;
            border-bottom: 1px solid var(--border-color, #444);
        }

        .modelpulse-tab {
            flex: 1;
            padding: 10px;
            text-align: center;
            cursor: pointer;
            background: transparent;
            border: none;
            color: var(--input-text, #ddd);
            border-bottom: 2px solid transparent;
            transition: all 0.15s ease;
        }

        .modelpulse-tab:hover {
            background: var(--comfy-menu-bg-hover, #333);
        }

        .modelpulse-tab.active {
            border-bottom-color: var(--primary-color, #4a9eff);
            color: var(--primary-color, #4a9eff);
        }

        .modelpulse-controls {
            display: flex;
            padding: 8px 12px;
            gap: 8px;
            align-items: center;
            border-bottom: 1px solid var(--border-color, #444);
        }

        .modelpulse-sort-label {
            font-size: 12px;
            color: var(--descrip-text, #999);
        }

        .modelpulse-sort {
            flex: 1;
            padding: 6px 8px;
            background: var(--comfy-input-bg, #222);
            border: 1px solid var(--border-color, #444);
            border-radius: 4px;
            color: var(--input-text, #ddd);
            font-size: 12px;
            cursor: pointer;
        }

        .modelpulse-list {
            flex: 1;
            overflow-y: auto;
            padding: 8px 0;
        }

        .modelpulse-category {
            margin-bottom: 4px;
        }

        .modelpulse-category-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: var(--comfy-menu-bg, #2a2a2a);
            cursor: pointer;
            user-select: none;
        }

        .modelpulse-category-header:hover {
            background: var(--comfy-menu-bg-hover, #333);
        }

        .modelpulse-category-icon {
            font-size: 14px;
        }

        .modelpulse-category-name {
            flex: 1;
            font-weight: 500;
        }

        .modelpulse-category-count {
            font-size: 11px;
            color: var(--descrip-text, #999);
            background: var(--comfy-input-bg, #222);
            padding: 2px 6px;
            border-radius: 10px;
        }

        .modelpulse-category-arrow {
            font-size: 10px;
            transition: transform 0.15s ease;
        }

        .modelpulse-category.collapsed .modelpulse-category-arrow {
            transform: rotate(-90deg);
        }

        .modelpulse-category-models {
            display: block;
        }

        .modelpulse-category.collapsed .modelpulse-category-models {
            display: none;
        }

        .modelpulse-model {
            display: flex;
            flex-direction: column;
            padding: 10px 12px 10px 32px;
            border-bottom: 1px solid var(--border-color, #333);
            cursor: default;
        }

        .modelpulse-model:hover {
            background: var(--comfy-menu-bg-hover, #333);
        }

        .modelpulse-model-name {
            font-weight: 500;
            margin-bottom: 4px;
            word-break: break-all;
        }

        .modelpulse-model-stats {
            display: flex;
            gap: 16px;
            font-size: 11px;
            color: var(--descrip-text, #999);
        }

        .modelpulse-model.stale .modelpulse-model-name {
            color: var(--error-text, #ff6b6b);
        }

        .modelpulse-model.stale .modelpulse-last-used {
            color: var(--error-text, #ff6b6b);
        }

        .modelpulse-empty {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 200px;
            color: var(--descrip-text, #999);
            text-align: center;
            padding: 20px;
        }

        .modelpulse-empty-icon {
            font-size: 48px;
            margin-bottom: 12px;
            opacity: 0.5;
        }

        .modelpulse-loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100px;
            color: var(--descrip-text, #999);
        }

        .modelpulse-search-container {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color, #444);
        }

        .modelpulse-search {
            width: 100%;
            padding: 8px 10px;
            background: var(--comfy-input-bg, #222);
            border: 1px solid var(--border-color, #444);
            border-radius: 4px;
            color: var(--input-text, #ddd);
            font-size: 13px;
            box-sizing: border-box;
        }

        .modelpulse-search:focus {
            outline: none;
            border-color: var(--primary-color, #4a9eff);
        }

        .modelpulse-search::placeholder {
            color: var(--descrip-text, #999);
        }

        .modelpulse-header-buttons {
            display: flex;
            gap: 4px;
        }

        .modelpulse-settings-btn {
            background: transparent;
            border: none;
            color: var(--input-text, #ddd);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 14px;
        }

        .modelpulse-settings-btn:hover {
            background: var(--comfy-menu-bg-hover, #333);
        }

        .modelpulse-settings-panel {
            padding: 12px;
            background: var(--comfy-menu-bg, #2a2a2a);
            border-bottom: 1px solid var(--border-color, #444);
        }

        .modelpulse-settings-title {
            font-weight: 600;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modelpulse-settings-close {
            background: transparent;
            border: none;
            color: var(--input-text, #ddd);
            cursor: pointer;
            font-size: 16px;
            padding: 2px 6px;
            border-radius: 4px;
        }

        .modelpulse-settings-close:hover {
            background: var(--comfy-menu-bg-hover, #333);
        }

        .modelpulse-setting-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }

        .modelpulse-setting-row:last-child {
            margin-bottom: 0;
        }

        .modelpulse-setting-label {
            font-size: 12px;
            color: var(--input-text, #ddd);
        }

        .modelpulse-setting-input {
            width: 60px;
            padding: 4px 8px;
            background: var(--comfy-input-bg, #222);
            border: 1px solid var(--border-color, #444);
            border-radius: 4px;
            color: var(--input-text, #ddd);
            font-size: 12px;
            text-align: center;
        }

        .modelpulse-setting-input:focus {
            outline: none;
            border-color: var(--primary-color, #4a9eff);
        }

        .modelpulse-no-results {
            padding: 20px;
            text-align: center;
            color: var(--descrip-text, #999);
            font-size: 12px;
        }
    `;
    return style;
}

/**
 * Render the ModelPulse UI into the container element
 */
async function renderModelPulseUI(container) {
    // Add styles
    container.appendChild(createStyles());

    // Create main container
    const main = document.createElement("div");
    main.className = "modelpulse-container";
    container.appendChild(main);

    // Header
    const header = document.createElement("div");
    header.className = "modelpulse-header";
    header.innerHTML = `
        <span class="modelpulse-title">Usage</span>
        <div class="modelpulse-header-buttons">
            <button class="modelpulse-settings-btn" title="Settings">⚙</button>
            <button class="modelpulse-refresh" title="Refresh">↻</button>
        </div>
    `;
    main.appendChild(header);

    // Settings panel (hidden by default)
    const settingsPanel = document.createElement("div");
    settingsPanel.className = "modelpulse-settings-panel";
    settingsPanel.style.display = "none";
    settingsPanel.innerHTML = `
        <div class="modelpulse-settings-title">
            <span>Settings</span>
            <button class="modelpulse-settings-close">×</button>
        </div>
        <div class="modelpulse-setting-row">
            <label class="modelpulse-setting-label">Stale threshold (days)</label>
            <input type="number" class="modelpulse-setting-input" id="stale-threshold"
                   value="${settings.staleThresholdDays}" min="1" max="365">
        </div>
    `;
    main.appendChild(settingsPanel);

    // Search bar
    const searchContainer = document.createElement("div");
    searchContainer.className = "modelpulse-search-container";
    searchContainer.innerHTML = `
        <input type="text" class="modelpulse-search" placeholder="Search models..." value="${searchQuery}">
    `;
    main.appendChild(searchContainer);

    // Timeframe tabs
    const tabs = document.createElement("div");
    tabs.className = "modelpulse-tabs";
    tabs.innerHTML = `
        <button class="modelpulse-tab ${currentTimeframe === 'all' ? 'active' : ''}" data-timeframe="all">All Time</button>
        <button class="modelpulse-tab ${currentTimeframe === 'month' ? 'active' : ''}" data-timeframe="month">Month</button>
        <button class="modelpulse-tab ${currentTimeframe === 'week' ? 'active' : ''}" data-timeframe="week">Week</button>
    `;
    main.appendChild(tabs);

    // Controls (sort dropdown)
    const controls = document.createElement("div");
    controls.className = "modelpulse-controls";
    controls.innerHTML = `
        <span class="modelpulse-sort-label">Sort:</span>
        <select class="modelpulse-sort">
            <option value="last_used" ${currentSort === 'last_used' ? 'selected' : ''}>Last Used</option>
            <option value="usage_count" ${currentSort === 'usage_count' ? 'selected' : ''}>Usage Count</option>
            <option value="name" ${currentSort === 'name' ? 'selected' : ''}>Name</option>
        </select>
    `;
    main.appendChild(controls);

    // Model list container
    const list = document.createElement("div");
    list.className = "modelpulse-list";
    main.appendChild(list);

    // Event handlers
    const refreshBtn = header.querySelector(".modelpulse-refresh");
    const settingsBtn = header.querySelector(".modelpulse-settings-btn");
    const settingsClose = settingsPanel.querySelector(".modelpulse-settings-close");
    const staleThresholdInput = settingsPanel.querySelector("#stale-threshold");
    const searchInput = searchContainer.querySelector(".modelpulse-search");

    refreshBtn.addEventListener("click", () => refreshData(list, refreshBtn));

    // Settings toggle
    settingsBtn.addEventListener("click", () => {
        showSettings = !showSettings;
        settingsPanel.style.display = showSettings ? "block" : "none";
    });

    settingsClose.addEventListener("click", () => {
        showSettings = false;
        settingsPanel.style.display = "none";
    });

    // Settings change handler
    staleThresholdInput.addEventListener("change", () => {
        const value = parseInt(staleThresholdInput.value, 10);
        if (value >= 1 && value <= 365) {
            settings.staleThresholdDays = value;
            saveSettings();
            renderModelList(list); // Re-render to update stale highlighting
        }
    });

    // Search handler with debounce
    let searchTimeout;
    searchInput.addEventListener("input", () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchQuery = searchInput.value;
            renderModelList(list);
        }, 200);
    });

    tabs.addEventListener("click", (e) => {
        const tab = e.target.closest(".modelpulse-tab");
        if (tab) {
            currentTimeframe = tab.dataset.timeframe;
            tabs.querySelectorAll(".modelpulse-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            refreshData(list, refreshBtn);
        }
    });

    const sortSelect = controls.querySelector(".modelpulse-sort");
    sortSelect.addEventListener("change", () => {
        currentSort = sortSelect.value;
        refreshData(list, refreshBtn);
    });

    // Initial load
    await refreshData(list, refreshBtn);
}

/**
 * Refresh the data and re-render the list
 */
async function refreshData(listContainer, refreshBtn) {
    if (isLoading) return;

    isLoading = true;
    refreshBtn.classList.add("loading");
    listContainer.innerHTML = '<div class="modelpulse-loading">Loading...</div>';

    try {
        usageData = await fetchUsageData(currentTimeframe, currentSort);
        renderModelList(listContainer);
    } catch (error) {
        listContainer.innerHTML = `
            <div class="modelpulse-empty">
                <div class="modelpulse-empty-icon">⚠️</div>
                <div>Error loading data</div>
            </div>
        `;
    } finally {
        isLoading = false;
        refreshBtn.classList.remove("loading");
    }
}

/**
 * Render the model list grouped by category
 */
function renderModelList(container) {
    container.innerHTML = "";

    if (!usageData || !usageData.models || usageData.models.length === 0) {
        container.innerHTML = `
            <div class="modelpulse-empty">
                <div class="modelpulse-empty-icon">📊</div>
                <div>No model usage recorded yet</div>
                <div style="margin-top: 8px; font-size: 11px;">Run some workflows to start tracking</div>
            </div>
        `;
        return;
    }

    // Apply search filter
    const filteredModels = filterModels(usageData.models, searchQuery);

    if (filteredModels.length === 0) {
        container.innerHTML = `
            <div class="modelpulse-no-results">
                No models found matching "${searchQuery}"
            </div>
        `;
        return;
    }

    const grouped = groupByCategory(filteredModels);

    // Sort categories by total usage
    const sortedCategories = Object.keys(grouped).sort((a, b) => {
        const aTotal = grouped[a].reduce((sum, m) => sum + m.timeframe_count, 0);
        const bTotal = grouped[b].reduce((sum, m) => sum + m.timeframe_count, 0);
        return bTotal - aTotal;
    });

    for (const category of sortedCategories) {
        const models = grouped[category];
        const catInfo = getCategoryInfo(category);

        const catDiv = document.createElement("div");
        catDiv.className = "modelpulse-category";

        // Category header
        const catHeader = document.createElement("div");
        catHeader.className = "modelpulse-category-header";
        catHeader.innerHTML = `
            <span class="modelpulse-category-icon">${catInfo.icon}</span>
            <span class="modelpulse-category-name">${catInfo.name}</span>
            <span class="modelpulse-category-count">${models.length}</span>
            <span class="modelpulse-category-arrow">▼</span>
        `;
        catHeader.addEventListener("click", () => {
            catDiv.classList.toggle("collapsed");
        });
        catDiv.appendChild(catHeader);

        // Models list
        const modelsDiv = document.createElement("div");
        modelsDiv.className = "modelpulse-category-models";

        for (const model of models) {
            const modelDiv = document.createElement("div");
            modelDiv.className = "modelpulse-model";
            if (isStale(model.last_used)) {
                modelDiv.classList.add("stale");
            }

            const countLabel = currentTimeframe === "all" ? "Uses" : "Uses (period)";
            const count = currentTimeframe === "all" ? model.usage_count : model.timeframe_count;

            modelDiv.innerHTML = `
                <div class="modelpulse-model-name" title="${model.model_id}">${model.name}</div>
                <div class="modelpulse-model-stats">
                    <span class="modelpulse-usage">${countLabel}: ${count}</span>
                    <span class="modelpulse-last-used">Last: ${formatLastUsed(model.last_used)}</span>
                </div>
            `;
            modelsDiv.appendChild(modelDiv);
        }

        catDiv.appendChild(modelsDiv);
        container.appendChild(catDiv);
    }
}

// Register the extension
app.registerExtension({
    name: "ModelPulse",
    async setup() {
        // Register sidebar tab
        app.extensionManager.registerSidebarTab({
            id: "modelpulse",
            icon: "pi pi-chart-bar",
            title: "Usage",
            tooltip: "Track model usage frequency",
            type: "custom",
            render: (el) => {
                renderModelPulseUI(el);
            }
        });

        console.log("[ModelPulse] Extension loaded");
    }
});
