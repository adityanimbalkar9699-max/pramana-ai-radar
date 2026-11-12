/* Pramana AI Radar — Frontend Controller & 3D WebGL Spatial Constellation */

const state = {
  mode: "loading", // "api" | "static"
  section: "overview",
  theme: localStorage.getItem("pramana_theme") || "luminary",
  tools: [],
  pricingHistory: [],
  discoveryRuns: [],
  rejectedCandidates: [],
  weeklyReports: [],
  settings: {},
  compareKeys: new Set(),
  localSavedKeys: new Set(JSON.parse(localStorage.getItem("pramana_saved") || "[]")),
};

const SECTION_META = {
  overview: { title: "Overview — Top Ranked Free AI Tools", sub: "Verified discoveries ranked out of 100 with zero fake-free trials." },
  "web-free": { title: "⭐ Web-Only Free Tiers (Zero Laptop Install)", sub: "Pure in-browser free AI tools for PPT decks, short videos (10s–30s), UI building, image creation & music with live free quotas." },
  daily: { title: "Daily Discoveries", sub: "Most recently verified free AI tools added by autonomous daily runs." },
  weekly: { title: "Weekly Intelligence & Top 10", sub: "Comprehensive weekly briefings, Top 10 rankings, and downloadable PDF/CSV/Excel." },
  coding: { title: "AI Coding Tools", sub: "Free coding assistants, autonomous coding agents, databases, and backend tools." },
  models: { title: "AI Models & Free APIs", sub: "Open-weight LLMs, local inference engines, RAG vector DBs, and free API tiers." },
  image: { title: "Image & Design", sub: "Free image generators, 3D suites, UI/UX whiteboards, and design tools." },
  video: { title: "Video & Content", sub: "Free video creation, screen recording, subtitle pipelines, and content tools." },
  voice: { title: "Voice & Audio", sub: "Local & free TTS, Faster-Whisper STT, voice synthesis, and audio tooling." },
  productivity: { title: "Productivity & Research", sub: "PDF analysis, paper management, browser automation, and workflow engines." },
  agents: { title: "AI Agents & Multi-Agent Systems", sub: "Agent frameworks, multi-agent orchestration, and MCP server toolchains." },
  education: { title: "Education & Career", sub: "DSA practice, student packs, GPU notebooks, roadmaps, and hackathon tools." },
  opensource: { title: "Open Source Directory", sub: "OSI-licensed and open-weight tools you can inspect, fork, and self-host." },
  "free-apis": { title: "Free API Directory", sub: "Verified tools offering free developer APIs or local OpenAI-compatible endpoints." },
  pricing: { title: "Pricing Changes & Fake-Free Audit Log", sub: "Historical free-tier changes plus rejected trial/paywall traps." },
  saved: { title: "Saved Tools", sub: "Your bookmarked student toolkit for college projects, hackathons, and startups." },
  search: { title: "Advanced Search & Filters", sub: "Filter across all 20 verified fields, categories, licenses, and RTX 4050 VRAM fit." },
  sources: { title: "Research Sources & Run Telemetry", sub: "Multi-source discovery pipeline health across GitHub, Hugging Face, HN, and Reddit." },
  settings: { title: "Automation & Cloud Scheduling Settings", sub: "Notification channels, daily targets, and GitHub Actions cloud execution status." },
};

function esc(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function applyTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("pramana_theme", theme);
  document.querySelectorAll(".theme-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.themeTarget === theme);
  });
  render3DConstellation();
}

async function loadCatalog() {
  const modeBadge = document.getElementById("modeBadge");
  try {
    const res = await fetch("/api/catalog");
    if (!res.ok) throw new Error("API unavailable");
    const data = await res.json();
    state.mode = "api";
    modeBadge.textContent = "LIVE API MODE";
    hydrateState(data);
  } catch {
    try {
      const res = await fetch("./data/catalog.json");
      if (!res.ok) throw new Error("Static JSON missing");
      const data = await res.json();
      state.mode = "static";
      modeBadge.textContent = "CLOUD STATIC MODE (GITHUB PAGES)";
      hydrateState(data);
    } catch (err) {
      modeBadge.textContent = "OFFLINE / NO DATA";
      document.getElementById("mainContentArea").innerHTML = `<div class="panel-box"><h3>No verified catalog found yet</h3><p>Run <code>python -m pramana.cli daily</code> to populate the intelligence database.</p></div>`;
    }
  }
}

function hydrateState(data) {
  state.tools = (data.tools || []).map((t) => ({
    ...t,
    is_saved: Boolean(t.is_saved) || state.localSavedKeys.has(t.canonical_key),
  }));
  state.pricingHistory = data.pricing_history || [];
  state.discoveryRuns = data.discovery_runs || [];
  state.rejectedCandidates = data.rejected_candidates || [];
  state.weeklyReports = data.weekly_reports || [];
  state.settings = data.settings || {};

  populateCategoryFilter();
  updateKpis();
  renderCurrentSection();
  render3DConstellation();
}

function populateCategoryFilter() {
  const sel = document.getElementById("categoryFilter");
  const current = sel.value;
  const cats = [...new Set(state.tools.map((t) => t.category))].sort();
  sel.innerHTML = `<option value="all">All Categories (${state.tools.length})</option>` +
    cats.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  if ([...sel.options].some((o) => o.value === current)) sel.value = current;
}

function updateKpis() {
  const tools = state.tools;
  const freeCount = tools.filter((t) => t.is_genuinely_free).length;
  const osCount = tools.filter((t) => String(t.open_source_status).startsWith("Open Source")).length;
  const apiCount = tools.filter((t) => /free|local/i.test(String(t.api_availability))).length;
  const avg = tools.length ? (tools.reduce((s, t) => s + Number(t.score || 0), 0) / tools.length).toFixed(1) : "0.0";

  document.getElementById("kpiTotalTools").textContent = freeCount;
  document.getElementById("kpiOpenSource").textContent = osCount;
  document.getElementById("kpiFreeApis").textContent = apiCount;
  document.getElementById("kpiAvgScore").textContent = `${avg}`;
  document.getElementById("savedCountBadge").textContent = tools.filter((t) => t.is_saved).length;
  document.getElementById("compareCount").textContent = state.compareKeys.size;
}

function getFilteredTools() {
  const q = document.getElementById("globalSearchInput").value.trim().toLowerCase();
  const catSel = document.getElementById("categoryFilter").value;
  const vramSel = document.getElementById("vramFilter").value;
  const cadenceSel = document.getElementById("cadenceFilter")?.value || "all";
  const sortSel = document.getElementById("sortSelect").value;
  const onlyFree = document.getElementById("onlyFreeToggle").checked;
  const onlyOs = document.getElementById("onlyOpenSourceToggle").checked;
  const webOnly = document.getElementById("webOnlyToggle")?.checked || false;

  let list = state.tools.filter((t) => {
    if (onlyFree && !t.is_genuinely_free) return false;
    if (onlyOs && !String(t.open_source_status).startsWith("Open Source")) return false;
    if (catSel !== "all" && t.category !== catSel) return false;

    const fit = String(t.personalization?.can_run_on_laptop || "").toLowerCase();
    const isWeb = Boolean(t.web_only) || fit.includes("cloud") || fit.includes("browser") || fit.includes("zero-install");
    if (webOnly && !isWeb) return false;

    if (vramSel === "local" && !fit.includes("yes")) return false;
    if (vramSel === "cloud" && !fit.includes("cloud") && !fit.includes("browser")) return false;

    if (cadenceSel !== "all") {
      const toolCadence = String(t.free_quota_cadence || "");
      const limitsLower = String(t.free_usage_limits || "").toLowerCase();
      if (toolCadence !== cadenceSel && !limitsLower.includes(cadenceSel.toLowerCase().split(" ")[0])) {
        return false;
      }
    }

    // Section-scoped filtering
    const s = state.section;
    if (s === "web-free" && !isWeb) return false;
    if (s === "coding" && t.category !== "Coding and Development") return false;
    if (s === "models" && t.category !== "AI and Machine Learning") return false;
    if (s === "image" && t.category !== "Image and Design") return false;
    if (s === "video" && t.category !== "Video and Content") return false;
    if (s === "voice" && t.category !== "Audio and Voice") return false;
    if (s === "productivity" && t.category !== "Productivity and Research") return false;
    if (s === "education" && t.category !== "Career and Education") return false;
    if (s === "agents") {
      const blob = `${t.subcategory} ${t.short_description} ${(t.tags || []).join(" ")}`.toLowerCase();
      if (!blob.includes("agent") && !blob.includes("mcp")) return false;
    }
    if (s === "opensource" && !String(t.open_source_status).startsWith("Open Source")) return false;
    if (s === "free-apis" && !/free|local/i.test(String(t.api_availability))) return false;
    if (s === "saved" && !t.is_saved) return false;

    if (q) {
      const hay = `${t.name} ${t.category} ${t.subcategory} ${t.short_description} ${t.free_plan_details} ${t.free_usage_limits} ${t.best_student_use_case} ${(t.tags || []).join(" ")}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (state.section === "daily") {
    list = [...list].sort((a, b) => (b.discovery_date || "").localeCompare(a.discovery_date || "") || b.score - a.score);
  } else if (sortSel === "stars") {
    list = [...list].sort((a, b) => (b.stars || 0) - (a.stars || 0));
  } else if (sortSel === "newest") {
    list = [...list].sort((a, b) => (b.discovery_date || "").localeCompare(a.discovery_date || ""));
  } else {
    list = [...list].sort((a, b) => (b.score || 0) - (a.score || 0));
  }
  return list;
}

function renderToolCards(tools) {
  if (!tools.length) {
    return `<div class="panel-box"><p class="muted">No tools matched your active filters in this view. Try clearing search or switching filters.</p></div>`;
  }
  return `<div class="tools-grid">${tools.map((t) => {
    const p = t.personalization || {};
    const compared = state.compareKeys.has(t.canonical_key);
    const appUrl = t.direct_app_url || t.official_website;
    const isWeb = Boolean(t.web_only) || String(p.can_run_on_laptop || "").toLowerCase().includes("browser") || String(p.can_run_on_laptop || "").toLowerCase().includes("cloud");
    const cadence = t.free_quota_cadence && t.free_quota_cadence !== "UNKNOWN" ? t.free_quota_cadence : (t.free_tier_type || "Free Tier");
    return `
      <article class="tool-card">
        <div>
          <div class="card-top">
            <div>
              <h3 class="tool-title">${esc(t.name)}</h3>
              <div class="tool-subcat">${esc(t.category)} › ${esc(t.subcategory)}</div>
            </div>
            <div class="score-ring">${Number(t.score).toFixed(1)}/100</div>
          </div>
          <p class="tool-desc" style="margin-top:10px">${esc(t.short_description)}</p>
          <div class="pill-row" style="margin-top:10px">
            <span class="pill-tag pill-free">${esc(t.free_tier_type)}</span>
            <span class="pill-tag pill-quota">⏱ ${esc(cadence)}</span>
            ${isWeb ? `<span class="pill-tag pill-web">🌐 In-Browser App</span>` : `<span class="pill-tag pill-vram">${esc(p.can_run_on_laptop || "Local")}</span>`}
            ${t.stars ? `<span class="pill-tag">★ ${Number(t.stars).toLocaleString()}</span>` : ""}
          </div>
          <div class="quota-highlight" style="margin-top:10px">
            <div><strong>⚡ Verified Free Limits:</strong> ${esc(t.free_usage_limits)}</div>
            <div style="margin-top:4px;font-size:11.5px;color:var(--text-muted)"><strong>Card required:</strong> ${esc(t.credit_card_required)} • <strong>Stops safely at limit:</strong> Yes (no surprise billing)</div>
          </div>
          <div class="card-meta-box" style="margin-top:8px">
            <div><strong>Best Student Use:</strong> ${esc(t.best_student_use_case)}</div>
          </div>
        </div>
        <div class="card-actions">
          <div class="card-actions-left">
            <button class="btn" onclick="openToolModal('${esc(t.canonical_key)}')">Inspect</button>
            <button class="btn" onclick="toggleCompare('${esc(t.canonical_key)}')">${compared ? "✓" : "+"} Compare</button>
            <button class="btn" onclick="toggleSave('${esc(t.canonical_key)}')">${t.is_saved ? "★" : "☆"}</button>
          </div>
          <div class="card-actions-right">
            ${t.pricing_url && t.pricing_url !== appUrl ? `<a class="btn" href="${esc(t.pricing_url)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;font-size:11.5px">Limits ↗</a>` : ""}
            <a class="btn btn-primary" href="${esc(appUrl)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;font-weight:700">⚡ Launch Free ↗</a>
          </div>
        </div>
      </article>
    `;
  }).join("")}</div>`;
}

function renderWeeklySection() {
  const top10 = [...state.tools].filter((t) => t.is_genuinely_free).sort((a, b) => b.score - a.score).slice(0, 10);
  const latestRep = state.weeklyReports[0];
  return `
    <div class="panel-box">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
        <div>
          <h3 style="margin:0">Weekly Top 10 Ranked Free AI Tools ${latestRep ? `(${esc(latestRep.week_label)})` : ""}</h3>
          <p class="muted">Ranked by Free Functionality (25), Usefulness (20), Reliability (15), Student Value (15), Ease (10), Performance (10), Docs (5).</p>
        </div>
        <div style="display:flex;gap:8px">
          <button class="btn btn-primary" onclick="downloadWeeklyPdf()">Download Weekly PDF</button>
          ${state.mode === "api" ? `<button class="btn btn-accent" onclick="triggerRun('weekly')">Generate Fresh Weekly Report</button>` : ""}
        </div>
      </div>
      <div style="overflow-x:auto;margin-top:14px">
        <table class="data-table">
          <thead><tr><th>Rank</th><th>Tool</th><th>Category</th><th>Free Tier</th><th>Score</th><th>RTX 4050 6GB Fit</th><th>Justification</th></tr></thead>
          <tbody>
            ${top10.map((t, idx) => `
              <tr>
                <td><strong>#${idx + 1}</strong></td>
                <td><a href="${esc(t.official_website)}" target="_blank" rel="noopener noreferrer">${esc(t.name)}</a></td>
                <td>${esc(t.subcategory)}</td>
                <td><span class="pill-tag pill-free">${esc(t.free_tier_type)}</span></td>
                <td><strong>${Number(t.score).toFixed(1)}</strong></td>
                <td>${esc(t.personalization?.can_run_on_laptop || "UNKNOWN")}</td>
                <td>${esc(t.score_breakdown?.explanation || t.what_makes_it_useful)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderPricingSection() {
  return `
    <div class="panel-box">
      <h3 style="margin-top:0">Historical Free-Tier &amp; Pricing Change Log</h3>
      <div style="overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>Tool</th><th>Event</th><th>Old Plan</th><th>New Plan</th><th>Detected</th></tr></thead>
          <tbody>
            ${state.pricingHistory.slice(0, 40).map((h) => `
              <tr>
                <td><strong>${esc(h.tool_name)}</strong></td>
                <td><span class="pill-tag">${esc(h.change_type)}</span></td>
                <td>${esc(h.old_free_plan || "—")}</td>
                <td>${esc(h.new_free_plan)}</td>
                <td>${esc(h.detected_at)}</td>
              </tr>
            `).join("") || `<tr><td colspan="5" class="muted">No pricing history recorded yet.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
    <div class="panel-box">
      <h3 style="margin-top:0">Rejected Fake-Free / Trial-Only / Low-Score Candidates</h3>
      <p class="muted">Automatically blocked by the Pricing Verification Agent so paid ads never reach your recommendations.</p>
      <div style="overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>Candidate</th><th>Reason Blocked</th><th>URL</th><th>Rejected At</th></tr></thead>
          <tbody>
            ${state.rejectedCandidates.map((r) => `
              <tr>
                <td><strong>${esc(r.name)}</strong></td>
                <td>${esc(r.reason)}</td>
                <td><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.url)}</a></td>
                <td>${esc(r.rejected_at)}</td>
              </tr>
            `).join("") || `<tr><td colspan="4" class="muted">No fake-free traps rejected in the latest batch.</td></tr>`}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderSourcesSection() {
  return `
    <div class="panel-box">
      <h3 style="margin-top:0">Active Independent Research Sources</h3>
      <div class="detail-grid">
        <div class="detail-cell"><div class="detail-label">Source 1</div><div class="detail-val"><strong>GitHub Search &amp; Repo API</strong> — Rotating AI agents, MCP, RAG, local LLM, TTS &amp; coding repos.</div></div>
        <div class="detail-cell"><div class="detail-label">Source 2</div><div class="detail-val"><strong>Hugging Face Hub API</strong> — Trending open-weights models &amp; free hosted Spaces.</div></div>
        <div class="detail-cell"><div class="detail-label">Source 3</div><div class="detail-val"><strong>Hacker News (Algolia API)</strong> — Live Show HN developer &amp; open-source AI launches.</div></div>
        <div class="detail-cell"><div class="detail-label">Source 4</div><div class="detail-val"><strong>Reddit RSS Feeds</strong> — r/LocalLLaMA &amp; r/opensource community launches.</div></div>
        <div class="detail-cell"><div class="detail-label">Source 5</div><div class="detail-val"><strong>Official Pricing &amp; Docs Inspector</strong> — Live HTTP/HTML verification of /pricing, licenses &amp; CC traps.</div></div>
      </div>
    </div>
    <div class="panel-box">
      <h3 style="margin-top:0">Autonomous Execution Run History</h3>
      <div style="overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>Run ID</th><th>Type</th><th>Status</th><th>Scanned</th><th>Added</th><th>Rejected</th><th>Dups</th><th>Sources OK</th><th>Started</th></tr></thead>
          <tbody>
            ${state.discoveryRuns.map((r) => `
              <tr>
                <td>#${r.id}</td>
                <td>${esc(r.run_type)}</td>
                <td><span class="pill-tag pill-free">${esc(r.status)}</span></td>
                <td>${r.candidates_scanned}</td>
                <td><strong>${r.new_tools_added}</strong></td>
                <td>${r.rejected_fake_free}</td>
                <td>${r.duplicates_skipped}</td>
                <td>${esc((r.sources_succeeded || []).join(", "))}</td>
                <td>${esc(r.started_at)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderSettingsSection() {
  const tg = state.settings.notify_telegram_enabled !== "false";
  const em = state.settings.notify_email_enabled !== "false";
  return `
    <div class="panel-box">
      <h3 style="margin-top:0">Autonomous Cloud Execution (Laptop-Independent)</h3>
      <p class="muted">
        Local Antigravity processes cannot execute when your Windows 11 laptop is shut down.
        Pramana runs 100% independently in the cloud via <strong>GitHub Actions</strong> daily at 08:00 IST (02:30 UTC)
        and weekly on Sundays at 09:00 IST (03:30 UTC), committing updates to SQLite + JSON + PDF and publishing to GitHub Pages.
      </p>
      <div class="detail-grid" style="margin-top:14px">
        <div class="detail-cell"><div class="detail-label">Daily Schedule</div><div class="detail-val">02:30 UTC (08:00 IST) — Target ≥3 verified tools</div></div>
        <div class="detail-cell"><div class="detail-label">Weekly Schedule</div><div class="detail-val">Sunday 03:30 UTC (09:00 IST) — Top 10 + PDF</div></div>
        <div class="detail-cell"><div class="detail-label">Student Profile</div><div class="detail-val">3rd-Yr CE • India • Win11 • RTX 4050 6GB VRAM</div></div>
      </div>
    </div>
    <div class="panel-box">
      <h3 style="margin-top:0">Notification Channel Controls</h3>
      <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:14px">
        <label class="toggle-chip"><input type="checkbox" id="cfgTelegram" ${tg ? "checked" : ""}/> Enable Telegram Daily/Weekly Alerts</label>
        <label class="toggle-chip"><input type="checkbox" id="cfgEmail" ${em ? "checked" : ""}/> Enable SMTP Email + PDF Digest</label>
      </div>
      ${state.mode === "api"
        ? `<button class="btn btn-primary" onclick="saveSettings()">Save Notification Preferences</button>`
        : `<p class="muted">Running in static GitHub Pages mode. Configure secrets (<code>TELEGRAM_BOT_TOKEN</code>, <code>TELEGRAM_CHAT_ID</code>, <code>SMTP_USER</code>, <code>SMTP_PASS</code>) in GitHub Repository Settings → Secrets → Actions.</p>`
      }
    </div>
  `;
}

function renderCurrentSection() {
  const meta = SECTION_META[state.section] || SECTION_META.overview;
  document.getElementById("sectionTitle").textContent = meta.title;
  document.getElementById("sectionSubtitle").textContent = meta.sub;
  document.getElementById("heroPanel").style.display = state.section === "overview" ? "grid" : "none";

  const root = document.getElementById("mainContentArea");
  if (state.section === "weekly") {
    root.innerHTML = renderWeeklySection();
  } else if (state.section === "pricing") {
    root.innerHTML = renderPricingSection();
  } else if (state.section === "sources") {
    root.innerHTML = renderSourcesSection();
  } else if (state.section === "settings") {
    root.innerHTML = renderSettingsSection();
  } else {
    root.innerHTML = renderToolCards(getFilteredTools());
  }
}

window.openToolModal = function (canonicalKey) {
  const t = state.tools.find((x) => x.canonical_key === canonicalKey);
  if (!t) return;
  const bd = t.score_breakdown || {};
  const p = t.personalization || {};

  document.getElementById("modalCategory").textContent = `${t.category} › ${t.subcategory}`;
  document.getElementById("modalToolName").textContent = `${t.name} (${Number(t.score).toFixed(1)}/100)`;

  const fields = [
    ["1. Tool Name", t.name],
    ["2. Official Website", `<a href="${esc(t.official_website)}" target="_blank" rel="noopener noreferrer">${esc(t.official_website)}</a>`],
    ["3. Category / Subcategory", `${t.category} › ${t.subcategory}`],
    ["4. Short Description", t.short_description],
    ["5. Main Capabilities", (t.main_capabilities || []).join(" • ")],
    ["6. What Makes It Useful", t.what_makes_it_useful],
    ["7. Free-Plan Details", t.free_plan_details],
    ["8. Free Usage Limits", t.free_usage_limits],
    ["9. Credit Card Required", t.credit_card_required],
    ["10. Registration Required", t.registration_required],
    ["11. Open-Source Status", t.open_source_status],
    ["12. GitHub Repository", t.github_repository ? `<a href="${esc(t.github_repository)}" target="_blank" rel="noopener noreferrer">${esc(t.github_repository)}</a>` : "Not Applicable / Proprietary"],
    ["13. Supported OS", (t.supported_os || []).join(", ")],
    ["14. API Availability", t.api_availability],
    ["15. Local Installation", t.local_installation_available],
    ["16. Important Limitations", (t.important_limitations || []).join(" • ")],
    ["17. Privacy Considerations", t.privacy_considerations],
    ["18. Last Verification Date", t.last_verification_date],
    ["19. Official Documentation", t.official_documentation && t.official_documentation.startsWith("http") ? `<a href="${esc(t.official_documentation)}" target="_blank" rel="noopener noreferrer">${esc(t.official_documentation)}</a>` : t.official_documentation],
    ["20. Best Student Use Case", t.best_student_use_case],
  ];

  const rubric = [
    ["Free Functionality", bd.free_functionality || 0, 25],
    ["Practical Usefulness", bd.practical_usefulness || 0, 20],
    ["Reliability", bd.reliability || 0, 15],
    ["Student Value", bd.student_value || 0, 15],
    ["Ease of Use", bd.ease_of_use || 0, 10],
    ["Performance", bd.performance || 0, 10],
    ["Documentation", bd.documentation || 0, 5],
  ];

  const appUrl = t.direct_app_url || t.official_website;
  const pricingUrl = t.pricing_url || t.official_website;

  document.getElementById("modalBody").innerHTML = `
    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
      <a class="btn btn-primary" href="${esc(appUrl)}" target="_blank" rel="noopener noreferrer" style="font-size:13.5px;padding:9px 16px;text-decoration:none;font-weight:700">⚡ Launch Free Web App ↗</a>
      <a class="btn" href="${esc(pricingUrl)}" target="_blank" rel="noopener noreferrer" style="font-size:13px;padding:9px 14px;text-decoration:none">💳 View Official Pricing & Limits ↗</a>
    </div>

    <div class="panel-box" style="margin-bottom:14px">
      <h4 style="margin:0 0 8px">Free Quota Truth & What Happens at Limit</h4>
      <div class="quota-highlight">
        <div><strong>Verified Free Allowance:</strong> ${esc(t.free_usage_limits)}</div>
        <div style="margin-top:4px;font-size:12px"><strong>Reset Cadence:</strong> ${esc(t.free_quota_cadence || "Free Tier")} • <strong>Credit Card Required:</strong> ${esc(t.credit_card_required)}</div>
        <div style="margin-top:4px;font-size:11.5px;color:var(--text-muted)">Safe student guarantee: Execution pauses or queues when quota is reached; zero hidden subscription billing.</div>
      </div>
      <p style="margin:10px 0 6px;font-size:13px">${esc(p.how_to_use || "")}</p>
      <div class="pill-row">
        <span class="pill-tag pill-vram">Laptop Fit: ${esc(p.can_run_on_laptop || "UNKNOWN")}</span>
        <span class="pill-tag">Cloud Needed: ${esc(p.cloud_usage_necessary || "UNKNOWN")}</span>
        <span class="pill-tag">Track: ${esc(p.priority_track || "AI Engineering")}</span>
        <span class="pill-tag">India Available: ${esc(t.india_available || "UNKNOWN")}</span>
      </div>
    </div>

    <div class="panel-box" style="margin-bottom:14px">
      <h4 style="margin:0 0 10px">100-Point Empirical Scoring Breakdown</h4>
      ${rubric.map(([lbl, val, max]) => `
        <div class="rubric-bar-row">
          <span>${lbl}</span>
          <div class="rubric-track"><div class="rubric-fill" style="width:${Math.min(100, (val / max) * 100)}%"></div></div>
          <span style="font-family:JetBrains Mono,monospace;text-align:right">${val}/${max}</span>
        </div>
      `).join("")}
      <p class="muted" style="margin-top:8px">${esc(bd.explanation || "")}</p>
    </div>

    <h4 style="margin:0 0 10px">All 20 Verified Intelligence Fields</h4>
    <div class="detail-grid">
      ${fields.map(([k, v]) => `<div class="detail-cell"><div class="detail-label">${esc(k)}</div><div class="detail-val">${v.toString().includes("<a ") ? v : esc(v)}</div></div>`).join("")}
    </div>
  `;
  document.getElementById("toolModal").classList.remove("hidden");
};

window.toggleSave = async function (key) {
  const tool = state.tools.find((t) => t.canonical_key === key);
  if (!tool) return;
  const next = !tool.is_saved;
  tool.is_saved = next;
  if (next) state.localSavedKeys.add(key); else state.localSavedKeys.delete(key);
  localStorage.setItem("pramana_saved", JSON.stringify([...state.localSavedKeys]));

  if (state.mode === "api") {
    await fetch("/api/tools/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ canonical_key: key, saved: next }),
    }).catch(() => {});
  }
  updateKpis();
  renderCurrentSection();
};

window.toggleCompare = function (key) {
  if (state.compareKeys.has(key)) {
    state.compareKeys.delete(key);
  } else {
    if (state.compareKeys.size >= 4) {
      alert("You can compare up to 4 tools side by side.");
      return;
    }
    state.compareKeys.add(key);
  }
  updateKpis();
  renderCurrentSection();
};

function openCompareModal() {
  const chosen = state.tools.filter((t) => state.compareKeys.has(t.canonical_key));
  const body = document.getElementById("compareBody");
  if (!chosen.length) {
    body.innerHTML = `<p class="muted">Select "+ Compare" on 2 to 4 tool cards to inspect them side-by-side.</p>`;
  } else {
    const rows = [
      ["Score (/100)", (t) => `${t.score}/100`],
      ["Category", (t) => `${t.category} › ${t.subcategory}`],
      ["Free Tier Type", (t) => t.free_tier_type],
      ["Free Usage Limits", (t) => t.free_usage_limits],
      ["Credit Card Required", (t) => t.credit_card_required],
      ["Open Source", (t) => t.open_source_status],
      ["API Availability", (t) => t.api_availability],
      ["RTX 4050 6GB Fit", (t) => t.personalization?.can_run_on_laptop || "UNKNOWN"],
      ["India Available", (t) => t.india_available],
      ["Best Student Use Case", (t) => t.best_student_use_case],
    ];
    body.innerHTML = `
      <div style="overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>Attribute</th>${chosen.map((t) => `<th>${esc(t.name)}</th>`).join("")}</tr></thead>
          <tbody>
            ${rows.map(([lbl, fn]) => `<tr><td><strong>${esc(lbl)}</strong></td>${chosen.map((t) => `<td>${esc(fn(t))}</td>`).join("")}</tr>`).join("")}
          </tbody>
        </table>
      </div>
    `;
  }
  document.getElementById("compareModal").classList.remove("hidden");
}

window.triggerRun = async function (kind) {
  if (state.mode !== "api") {
    alert("Live on-demand runs require the local/cloud Flask server (`python -m pramana.cli serve`). On GitHub Pages, GitHub Actions runs automatically every day and week.");
    return;
  }
  const btn = document.getElementById("runDailyBtn");
  btn.disabled = true;
  btn.textContent = "Discovering...";
  try {
    const res = await fetch(`/api/run/${kind}`, { method: "POST" });
    const data = await res.json();
    await loadCatalog();
    alert(`Completed ${kind} run: added ${data.new_tools_added} verified tools (rejected ${data.rejected_fake_free || 0} non-free).`);
  } catch (err) {
    alert(`Run failed: ${err}`);
  } finally {
    btn.disabled = false;
    btn.textContent = "Run Live Discovery";
  }
};

window.saveSettings = async function () {
  const tg = document.getElementById("cfgTelegram")?.checked ?? true;
  const em = document.getElementById("cfgEmail")?.checked ?? true;
  await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      notify_telegram_enabled: String(tg),
      notify_email_enabled: String(em),
    }),
  });
  alert("Notification preferences saved.");
};

window.downloadWeeklyPdf = function () {
  if (state.mode === "api") {
    window.location.href = "/api/export/pdf";
  } else {
    window.open("./reports/latest-weekly-report.pdf", "_blank");
  }
};

/* Interactive 3D WebGL Spatial Constellation (Three.js + Graceful 2D Canvas Fallback) */
let threeAnimId = null;
function render3DConstellation() {
  const canvas = document.getElementById("radar3dCanvas");
  if (!canvas) return;
  if (threeAnimId) cancelAnimationFrame(threeAnimId);

  const width = canvas.clientWidth || 440;
  const height = canvas.clientHeight || 230;
  const tools = state.tools.slice(0, 32);

  if (typeof THREE === "undefined") {
    draw2DFallback(canvas, width, height, tools);
    return;
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  } catch {
    draw2DFallback(canvas, width, height, tools);
    return;
  }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(width, height, false);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(44, width / height, 0.1, 100);
  camera.position.set(0, 3.8, 9.2);
  camera.lookAt(0, 0, 0);

  const accentHex = state.theme === "sunset" ? 0xc2410c : state.theme === "carbon" ? 0x60a5fa : 0x1d4ed8;
  const secHex = state.theme === "sunset" ? 0x0f766e : 0x047857;

  scene.add(new THREE.AmbientLight(0xffffff, 0.95));
  const keyLight = new THREE.DirectionalLight(0xffffff, 1.15);
  keyLight.position.set(5, 8, 6);
  scene.add(keyLight);

  const group = new THREE.Group();
  scene.add(group);

  // Subtle architectural orbital rings
  const ringMat = new THREE.LineBasicMaterial({ color: accentHex, transparent: true, opacity: 0.25 });
  [2.2, 3.6].forEach((r) => {
    const pts = [];
    for (let i = 0; i <= 64; i++) {
      const a = (i / 64) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
    }
    group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), ringMat));
  });

  // Core studio crystal representing Pramana Verification Core
  const coreGeo = new THREE.OctahedronGeometry(0.65, 1);
  const coreMat = new THREE.MeshStandardMaterial({ color: accentHex, roughness: 0.22, metalness: 0.55 });
  const coreMesh = new THREE.Mesh(coreGeo, coreMat);
  group.add(coreMesh);

  // Plot each verified tool as an elevated orbital node
  const nodeGeo = new THREE.SphereGeometry(0.18, 16, 16);
  tools.forEach((t, idx) => {
    const angle = (idx / Math.max(1, tools.length)) * Math.PI * 2;
    const radius = 1.8 + ((idx % 3) * 0.85);
    const elevation = ((Number(t.score || 70) - 65) / 35) * 1.5;
    const isOs = String(t.open_source_status).startsWith("Open Source");
    const mat = new THREE.MeshStandardMaterial({
      color: isOs ? secHex : accentHex,
      roughness: 0.28,
      metalness: 0.35,
    });
    const node = new THREE.Mesh(nodeGeo, mat);
    node.position.set(Math.cos(angle) * radius, elevation, Math.sin(angle) * radius);
    group.add(node);
  });

  let dragging = false;
  let prevX = 0;
  canvas.onpointerdown = (e) => { dragging = true; prevX = e.clientX; };
  window.addEventListener("pointerup", () => { dragging = false; });
  window.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    group.rotation.y += (e.clientX - prevX) * 0.008;
    prevX = e.clientX;
  });

  const animate = () => {
    if (!dragging) group.rotation.y += 0.0035;
    coreMesh.rotation.y -= 0.008;
    renderer.render(scene, camera);
    threeAnimId = requestAnimationFrame(animate);
  };
  animate();
}

function draw2DFallback(canvas, width, height, tools) {
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, width, height);
  const cx = width / 2;
  const cy = height / 2;
  ctx.strokeStyle = "rgba(29,78,216,0.22)";
  [55, 95].forEach((r) => {
    ctx.beginPath();
    ctx.ellipse(cx, cy, r * 1.6, r * 0.72, 0, 0, Math.PI * 2);
    ctx.stroke();
  });
  tools.forEach((t, i) => {
    const a = (i / Math.max(1, tools.length)) * Math.PI * 2;
    const rx = 85 + (i % 3) * 38;
    const ry = 36 + (i % 3) * 18;
    ctx.fillStyle = String(t.open_source_status).startsWith("Open Source") ? "#047857" : "#1D4ED8";
    ctx.beginPath();
    ctx.arc(cx + Math.cos(a) * rx, cy + Math.sin(a) * ry, 5, 0, Math.PI * 2);
    ctx.fill();
  });
}

/* Wire Events */
document.addEventListener("DOMContentLoaded", () => {
  applyTheme(state.theme);

  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.section = btn.dataset.section;
      renderCurrentSection();
    });
  });

  document.querySelectorAll(".theme-btn").forEach((btn) => {
    btn.addEventListener("click", () => applyTheme(btn.dataset.themeTarget));
  });

  ["globalSearchInput", "categoryFilter", "vramFilter", "cadenceFilter", "sortSelect", "onlyFreeToggle", "onlyOpenSourceToggle", "webOnlyToggle"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", renderCurrentSection);
      el.addEventListener("change", renderCurrentSection);
    }
  });

  document.getElementById("runDailyBtn").addEventListener("click", () => triggerRun("daily"));
  document.getElementById("compareDrawerBtn").addEventListener("click", openCompareModal);
  document.getElementById("closeModalBtn").addEventListener("click", () => document.getElementById("toolModal").classList.add("hidden"));
  document.getElementById("closeCompareBtn").addEventListener("click", () => document.getElementById("compareModal").classList.add("hidden"));

  document.getElementById("exportCsvBtn").addEventListener("click", () => {
    window.location.href = state.mode === "api" ? "/api/export/csv" : "./reports/pramana_tools_export.csv";
  });
  document.getElementById("exportXlsxBtn").addEventListener("click", () => {
    window.location.href = state.mode === "api" ? "/api/export/xlsx" : "./reports/pramana_tools_export.xlsx";
  });
  document.getElementById("exportPdfBtn").addEventListener("click", window.downloadWeeklyPdf);

  loadCatalog();
});
