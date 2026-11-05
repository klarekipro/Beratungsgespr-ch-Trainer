"use strict";

(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const copy = (value) => JSON.parse(JSON.stringify(value));
  const uid = () => window.crypto?.randomUUID?.() || `request_${Date.now()}_${Math.random().toString(36).slice(2, 14)}`;
  const identifier = (prefix) => `${prefix}_${uid().replace(/[^a-z0-9]/gi, "").slice(0, 12).toLowerCase()}`;
  const ICONS = {
    grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    chat:'<path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6A8.4 8.4 0 0 1 12.5 3h.5a8.5 8.5 0 0 1 8 8v.5Z"/><path d="M8 10h8M8 14h5"/>',
    history:'<path d="M3 11a9 9 0 1 1 2.7 7M3 4v7h7"/><path d="M12 7v5l3 2"/>',
    building:'<path d="M4 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16M17 9h3v12M2 21h20M8 7h1M12 7h1M8 11h1M12 11h1M8 15h1M12 15h1M9 21v-3h4v3"/>',
    book:'<path d="M12 6c-2.5-2-6-2.5-9-1v14c3-1.5 6.5-1 9 1 2.5-2 6-2.5 9-1V5c-3-1.5-6.5-1-9 1Zm0 0v14"/>',
    clipboard:'<path d="M9 4H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-4"/><rect x="9" y="2" width="6" height="4" rx="1"/><path d="m8 13 3 3 5-6"/>',
    settings:'<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="m9 3-.7 2-2 .9L4 5.5 2.5 8l1.5 1.7v2.6L2.5 14 4 16.5l2.3-.4 2 .9.7 2h3l.7-2 2-.9 2.3.4 1.5-2.5-1.5-1.7V9.7L18.5 8 17 5.5l-2.3.4-2-.9L12 3Z" transform="translate(1 1)"/>',
    user:'<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    mentor:'<path d="m3 8 9-5 9 5-9 5-9-5Zm4 3v6c3 2 7 2 10 0v-6M21 8v7"/>',
    arrow:'<path d="M5 12h14m-5-5 5 5-5 5"/>',
    back:'<path d="M19 12H5m5-5-5 5 5 5"/>',
    chevron:'<path d="m6 9 6 6 6-6"/>',
    check:'<path d="m5 12 4 4L19 6"/>',
    plus:'<path d="M12 5v14M5 12h14"/>',
    close:'<path d="m6 6 12 12M6 18 18 6"/>',
    edit:'<path d="m14 5 5 5M4 20l4-1 12-12a2.8 2.8 0 0 0-4-4L4 15v5Z"/>',
    trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 1 1 8 0v3M12 14v3"/>',
    info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
    alert:'<path d="m10.3 3.9-8.1 14a2 2 0 0 0 1.7 3h16.2a2 2 0 0 0 1.7-3l-8.1-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    send:'<path d="m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13"/>',
    file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
    download:'<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/>',
    refresh:'<path d="M20 7a9 9 0 0 0-15-2L2 8m0-6v6h6M4 17a9 9 0 0 0 15 2l3-3m0 6v-6h-6"/>',
    search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    spark:'<path d="m12 3 2.8 6.2L21 12l-6.2 2.8L12 21l-2.8-6.2L3 12l6.2-2.8L12 3ZM20 2v4M18 4h4"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    tool:'<path d="M14.7 6.3a5.4 5.4 0 0 0-6.8 6.8L3 18a2.1 2.1 0 1 0 3 3l4.9-4.9a5.4 5.4 0 0 0 6.8-6.8l-3.2 3.2-3-3 3.2-3.2Z"/>',
    menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
    eye:'<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    link:'<path d="m10 13 4-4M8 16l-2 2a3.5 3.5 0 0 1-5-5l5-5a3.5 3.5 0 0 1 5 0M16 8l2-2a3.5 3.5 0 0 1 5 5l-5 5a3.5 3.5 0 0 1-5 0" transform="translate(0 -1) scale(.95)"/>',
    save:'<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h12l4 4v12a2 2 0 0 1-2 2Z"/><path d="M7 3v6h10V3M7 21v-8h10v8"/>'
  };
  const icon = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.info}</svg>`;
  const PHASES = {needs:"Потребности",capabilities:"Возможности",proposal:"Предложение",completed:"Консультация завершена"};
  const KNOWLEDGE = {known:"Известно клиенту",undecided:"Ещё не определено",does_not_know:"Клиент не знает",refuses_to_disclose:"Не готов раскрыть",not_applicable:"Не относится к ситуации"};
  const REVIEW = {not_submitted:"Не отправлено",submitted:"На проверке",reviewed:"Есть отзыв"};
  const state = {
    route:{role:"learner",view:"practice",id:null}, status:null, company:null, catalogue:[], sessions:[], scenarios:[], reviews:[],
    session:null, loading:true, error:null, menu:false, mode:"demo", generation:0, companyDraft:null, companyDirty:false,
    scenarioDraft:null, scenarioDraftKey:null, scenarioDirty:false, formError:null, saving:false, drafts:{}, noteDrafts:{},
    historyFilter:"all", historySearch:"", scenarioSearch:"", reviewFilter:"submitted", starting:null, exportBusy:null
  };
  const date = (value, withTime = false) => {
    if (!value) return "—";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "—";
    return new Intl.DateTimeFormat("ru-RU", withTime ? {day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"} : {day:"2-digit",month:"short",year:"numeric"}).format(parsed);
  };
  const time = (value) => {
    const parsed = new Date(value || "");
    return Number.isNaN(parsed.getTime()) ? "" : new Intl.DateTimeFormat("ru-RU",{hour:"2-digit",minute:"2-digit"}).format(parsed);
  };
  const initials = (name) => String(name || "Клиент").split(/\s+/).filter(Boolean).slice(0,2).map((x) => x[0]).join("").toUpperCase();
  const plural = (n, forms) => forms[n % 10 === 1 && n % 100 !== 11 ? 0 : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? 1 : 2];
  const modeLabel = (mode) => mode === "openai" ? "OpenAI" : "Сценарный режим";
  const modePill = (mode) => `<span class="pill ${mode === "openai" ? "green" : "amber"}">${icon(mode === "openai" ? "spark" : "book")}${modeLabel(mode)}</span>`;
  const canUseAI = () => Boolean(state.status?.ai?.configured && state.status?.ai?.live_enabled);
  const statusPill = (session) => session.review_status === "reviewed" ? '<span class="pill green">Есть отзыв</span>' : session.review_status === "submitted" ? '<span class="pill amber">На проверке</span>' : session.status === "finished" ? '<span class="pill dark">Завершено</span>' : '<span class="pill green">В процессе</span>';
  const safeURL = (value) => { try {const u = new URL(value);return ["https:","http:"].includes(u.protocol) ? u.href : "";} catch (_) {return "";} };
  const draftFor = (id) => state.drafts[id] ||= {text:"",kind:"message",pending:null,error:null,sending:false};

  class APIError extends Error {
    constructor(message, code, status) {super(message);this.code = code;this.status = status;}
  }
  async function api(path, options = {}) {
    const headers = {Accept:"application/json"};
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (options.mentor) headers["X-Workspace-Role"] = "mentor";
    let response;
    try {response = await fetch(path,{method:options.method || "GET",headers,credentials:"same-origin",body:options.body !== undefined ? JSON.stringify(options.body) : undefined});}
    catch (_) {throw new APIError("Сервер недоступен. Проверьте соединение и повторите действие.","NETWORK_ERROR",0);}
    let data;
    try {data = await response.json();} catch (_) {throw new APIError("Сервер вернул ответ, который не удалось прочитать.","INVALID_RESPONSE",response.status);}
    if (!response.ok) {
      const validation = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join("; ") : "";
      throw new APIError(data.error?.message || validation || (typeof data.detail === "string" ? data.detail : "Не удалось выполнить действие. Попробуйте ещё раз."),data.error?.code || "REQUEST_FAILED",response.status);
    }
    return data;
  }
  function toast(message, error = false) {
    const node = document.createElement("div");node.className = `toast${error ? " error" : ""}`;
    node.innerHTML = `${icon(error ? "alert" : "check")}<span>${esc(message)}</span><button aria-label="Закрыть уведомление">${icon("close")}</button>`;
    $("button",node).addEventListener("click",() => node.remove());
    $("#toast-region").appendChild(node);setTimeout(() => node.remove(),error ? 9000 : 5000);
  }
  function confirmDialog(title, text, confirmLabel = "Продолжить", danger = false) {
    return new Promise((resolve) => {
      const dialog = $("#confirm-dialog");
      dialog.innerHTML = `<h2 id="dialog-title">${esc(title)}</h2><p>${esc(text)}</p><div class="actions"><button class="btn" data-dialog-cancel>Отмена</button><button class="btn ${danger ? "danger" : "primary"}" data-dialog-confirm>${esc(confirmLabel)}</button></div>`;
      let done = false;
      const close = (value) => {if(done)return;done=true;dialog.close();dialog.removeEventListener("cancel",cancel);resolve(value);};
      const cancel = (event) => {event.preventDefault();close(false);};
      $("[data-dialog-cancel]",dialog).addEventListener("click",() => close(false));
      $("[data-dialog-confirm]",dialog).addEventListener("click",() => close(true));
      dialog.addEventListener("cancel",cancel);dialog.showModal();
    });
  }
  function getRoute() {
    const parts = location.hash.replace(/^#\/?/,"").split("/").filter(Boolean);
    const role = parts[0] === "mentor" ? "mentor" : "learner";
    return {role,view:parts[1] || (role === "mentor" ? "overview" : "practice"),id:parts[2] ? decodeURIComponent(parts[2]) : null};
  }
  function go(path) {state.menu=false;if(location.hash === `#${path}`)loadRoute();else location.hash=path;}
  function captureDrafts() {
    if ($("#company-form")) state.companyDraft = readCompanyForm();
    if ($("#scenario-form")) state.scenarioDraft = readScenarioForm();
  }
  async function loadRoute() {
    captureDrafts();const generation = ++state.generation;const previousRole = state.route.role;state.route = getRoute();state.menu=false;
    if (previousRole === "mentor" && state.route.role === "learner") {state.scenarios=[];state.scenarioDraft=null;state.scenarioDraftKey=null;state.scenarioDirty=false;state.formError=null;}
    try {localStorage.setItem("klareki-workspace",state.route.role);} catch (_) {}
    state.loading=true;state.error=null;state.formError=null;render();
    try {
      if(!state.status) {const [status,company] = await Promise.all([api("/api/status"),api("/api/company")]);state.status=status;state.company=company.company;}
      const {role,view,id}=state.route;
      if(role === "learner") {
        if(view === "practice") {
          const [catalogue,sessions,company] = await Promise.all([api("/api/scenarios"),api("/api/sessions"),api("/api/company")]);
          if(generation!==state.generation)return;state.catalogue=catalogue.scenarios;state.sessions=sessions.sessions;state.company=company.company;
        } else if(view === "history") {const data=await api("/api/sessions");if(generation!==state.generation)return;state.sessions=data.sessions;}
        else if(view === "session" && id) {const data=await api(`/api/sessions/${encodeURIComponent(id)}`);if(generation!==state.generation)return;state.session=data.session;}
        else if(view === "company") {const data=await api("/api/company");if(generation!==state.generation)return;state.company=data.company;}
        else throw new APIError("Эта страница не найдена.","NOT_FOUND",404);
      } else {
        if(view === "overview") {
          const [company,scenarios,reviews] = await Promise.all([api("/api/company"),api("/api/mentor/scenarios",{mentor:true}),api("/api/mentor/reviews",{mentor:true})]);
          if(generation!==state.generation)return;state.company=company.company;state.scenarios=scenarios.scenarios;state.reviews=reviews.sessions;
        } else if(view === "company") {
          const data=await api("/api/company");if(generation!==state.generation)return;state.company=data.company;
          if(!state.companyDraft || !state.companyDirty)state.companyDraft=copy(data.company);
        } else if(view === "scenarios" || view === "scenario") {
          const [data,company] = await Promise.all([api("/api/mentor/scenarios",{mentor:true}),api("/api/company")]);
          if(generation!==state.generation)return;state.scenarios=data.scenarios;state.company=company.company;
          if(view === "scenario" && state.scenarioDraftKey!==id) {
            const selected = id === "new" ? blankScenario() : state.scenarios.find((s) => s.id===id);
            if(!selected)throw new APIError("Сценарий не найден. Возможно, он был удалён.","NOT_FOUND",404);
            state.scenarioDraft=copy(selected);state.scenarioDraftKey=id;state.scenarioDirty=false;
          }
        } else if(view === "reviews") {const data=await api("/api/mentor/reviews",{mentor:true});if(generation!==state.generation)return;state.reviews=data.sessions;}
        else if(view === "review" && id) {const data=await api(`/api/mentor/reviews/${encodeURIComponent(id)}`,{mentor:true});if(generation!==state.generation)return;state.session=data.session;}
        else if(view === "setup") {const status=await api("/api/status");if(generation!==state.generation)return;state.status=status;}
        else throw new APIError("Эта страница не найдена.","NOT_FOUND",404);
      }
      if(generation!==state.generation)return;
      if(!canUseAI())state.mode="demo";
      state.loading=false;render();
      if(view === "session" && state.session?.status === "active") scrollChat();
      else window.scrollTo({top:0,behavior:"auto"});
    } catch(error) {if(generation!==state.generation)return;state.loading=false;state.error=error;render();}
  }
  function navLabel() {
    const labels={practice:"Тренировка",history:"Мои беседы",session:"Консультация",company:"Компания",overview:"Обзор",scenarios:"Сценарии",scenario:"Редактор сценария",reviews:"Проверка бесед",review:"Разбор беседы",setup:"Подключение AI"};
    return labels[state.route.view] || "Рабочее пространство";
  }
  function render() {
    const role = state.route.role;const mentor = role === "mentor";const view = state.route.view;
    const nav = mentor ? [["overview","grid","Обзор"],["company","building","Компания"],["scenarios","book","Сценарии"],["reviews","clipboard","Проверка бесед"],["setup","settings","Подключение AI"]] : [["practice","chat","Тренировка"],["history","history","Мои беседы"],["company","building","О компании"]];
    let page;
    if(state.loading)page='<div class="loading-state" role="status"><span class="spinner" aria-hidden="true"></span>Загружаем рабочее пространство…</div>';
    else if(state.error)page=`<div class="card"><div class="empty-state"><div class="empty-icon">${icon("alert")}</div><h3>Не удалось открыть страницу</h3><p>${esc(state.error.message)}</p><button class="btn primary" data-action="reload">${icon("refresh")}Попробовать снова</button></div></div>`;
    else page=renderPage();
    const isChat=!state.loading&&!state.error&&view==="session"&&state.session?.status==="active";
    $("#app").innerHTML=`<div class="app-shell"><div class="mobile-shade ${state.menu?"open":""}" data-action="menu-close"></div>
      <aside class="sidebar ${state.menu?"open":""}" id="sidebar" aria-label="Основная навигация"><a class="brand" href="#${role}/${mentor?"overview":"practice"}" aria-label="Klare KI — начало"><span class="brand-mark" aria-hidden="true">K<span>·</span></span><div><div class="brand-text">klare ki</div><div class="brand-sub">Consultation studio</div></div></a><p class="sidebar-label">${mentor?"Мастерская наставника":"Практика консультации"}</p><nav class="nav-list">${nav.map(([key,ico,label])=>{const active=view===key||(key==="practice"&&view==="session")||(key==="scenarios"&&view==="scenario")||(key==="reviews"&&view==="review");return `<a class="nav-link ${active?"active":""}" href="#${role}/${key}" ${active?'aria-current="page"':""}>${icon(ico)}<span>${label}</span>${key==="reviews"&&state.reviews.filter(s=>s.review_status==="submitted").length?`<span class="nav-count">${state.reviews.filter(s=>s.review_status==="submitted").length}</span>`:""}</a>`;}).join("")}</nav><div class="sidebar-footer"><div class="sidebar-note"><span>Порядок имеет значение</span><p>Выяснить потребности.<br>Понять возможности.<br>Обосновать предложение.</p></div><div class="workspace-tag"><span class="status-dot"></span>Локальный прототип${state.status?.version?` · ${esc(state.status.version)}`:""}</div></div></aside>
      <div class="main-shell"><header class="topbar"><button class="menu-btn" data-action="menu" aria-label="Открыть навигацию" aria-controls="sidebar" aria-expanded="${state.menu}">${icon("menu")}</button><div class="topbar-heading"><span>Тренажёр консультации</span><span class="truncate"><strong>${navLabel()}</strong></span></div><div class="topbar-actions"><span class="local-label"><span class="status-dot"></span>Локальная практика</span><div class="role-switch" role="group" aria-label="Рабочее пространство"><button class="role-btn ${mentor?"":"active"}" data-action="role" data-role="learner" aria-pressed="${!mentor}">${icon("user")}Ученик</button><button class="role-btn ${mentor?"active":""}" data-action="role" data-role="mentor" aria-pressed="${mentor}">${icon("mentor")}Наставник</button></div></div></header><main class="page ${isChat?"chat-page":""}" id="main-content" tabindex="-1">${page}</main></div></div>`;
    document.title=`${navLabel()} · Klare KI`;
  }
  function renderPage() {
    const {role,view}=state.route;
    if(role==="learner") {
      if(view==="practice")return practicePage();
      if(view==="history")return historyPage();
      if(view==="company")return companyPage();
      if(view==="session")return state.session.status==="finished"?reportPage(state.session,false):chatPage(state.session);
    } else {
      if(view==="overview")return overviewPage();
      if(view==="company")return companyEditor();
      if(view==="scenarios")return scenariosPage();
      if(view==="scenario")return scenarioEditor();
      if(view==="reviews")return reviewsPage();
      if(view==="review")return reportPage(state.session,true);
      if(view==="setup")return setupPage();
    }
    return "";
  }
  const pageHead = (eyebrow,title,description,actions="") => `<div class="page-head"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1>${description?`<p>${esc(description)}</p>`:""}</div>${actions?`<div class="actions">${actions}</div>`:""}</div>`;
  const empty = (ico,title,description,action="") => `<div class="empty-state"><div class="empty-icon">${icon(ico)}</div><h3>${esc(title)}</h3><p>${esc(description)}</p>${action}</div>`;
  const statCard = (ico,value,label,description="") => `<div class="card stat-card"><div class="stat-icon">${icon(ico)}</div><div><div class="stat-value">${esc(value)}</div><div class="stat-label">${esc(label)}</div>${description?`<div class="stat-description">${esc(description)}</div>`:""}</div></div>`;

  function practicePage() {
    const active=state.sessions.filter(s=>s.status==="active");const finished=state.sessions.filter(s=>s.status==="finished");const reviewed=state.sessions.filter(s=>s.review_status==="reviewed");
    const companyReady=Boolean(state.company?.reviewed);
    return `<section class="hero"><div class="hero-copy"><div class="eyebrow">Разговор, в котором есть смысл</div><h1>Сначала понять.<br><em>Потом предложить.</em></h1><p>Практикуйте вопросы, проверяйте своё понимание клиента и находите решение, которое ему подходит.</p><div class="hero-meta"><span>${icon("user")}Вы — сотрудник компании</span><span>${icon("chat")}Начните с вопросов</span></div></div><div class="hero-path" aria-label="Три этапа консультации">${[["01","Потребности","Что действительно нужно клиенту"],["02","Возможности","Какие условия нужно учесть"],["03","Предложение","Какое действие обосновано"]].map(([n,t,d])=>`<div class="path-item"><span class="path-number">${n}</span><div><strong>${t}</strong><small>${d}</small></div></div>`).join("")}</div></section>
      ${active.length?`<div class="resume-banner"><span class="avatar small-avatar">${initials(active[0].customer_name)}</span><div><strong>У вас есть незавершённая беседа</strong><p>${esc(active[0].title)} · ${esc(PHASES[active[0].phase]||"В процессе")}</p></div><a class="btn small-btn" href="#learner/session/${esc(active[0].id)}">Продолжить${icon("arrow")}</a></div>`:""}
      <div class="catalogue-toolbar"><h2>Выберите собеседника <span class="section-count">${state.catalogue.length}</span></h2><div class="mode-control" role="group" aria-label="Режим новой беседы"><button class="mode-option ${state.mode==="demo"?"active":""}" data-action="mode" data-mode="demo" aria-pressed="${state.mode==="demo"}">${icon("book")}Сценарный режим</button><button class="mode-option ${state.mode==="openai"?"active":""}" data-action="mode" data-mode="openai" aria-pressed="${state.mode==="openai"}" ${!canUseAI()?'disabled title="OpenAI ещё не подключён на сервере"':""}>${icon("spark")}OpenAI${!canUseAI()?icon("lock"):""}</button></div></div>
      ${!companyReady?`<div class="notice amber gap-bottom">${icon("alert")}<p>Перед тренировкой наставнику нужно проверить описание и возможности компании. <a class="text-link" href="#mentor/company">Открыть карточку компании</a></p></div>`:""}
      <div class="scenario-grid">${state.catalogue.map((s,i)=>`<article class="card scenario-card"><div class="scenario-card-top"><span class="avatar tone-${i%3}">${esc(initials(s.customer_name))}</span><span class="scenario-number">CASE ${String(i+1).padStart(2,"0")}</span></div><h3>${esc(s.title)}</h3><div class="scenario-client">${esc(s.customer_name)} · ${s.language==="de"?"На немецком":"На русском"}</div><p class="scenario-brief">${esc(s.public_brief)}</p><div class="scenario-card-footer"><span class="caption">${esc(s.company_name||state.company?.name||"Учебная компания")}</span><button class="btn primary" data-action="start" data-id="${esc(s.id)}" ${!companyReady||state.starting?'disabled':""}>${state.starting===s.id?"Начинаем…":"Начать беседу"}${icon("arrow")}</button></div></article>`).join("")}</div>
      ${!state.catalogue.length?`<div class="card">${empty("book","Пока нет сценариев","Наставник может создать первый учебный случай в редакторе.",'<a class="btn primary" href="#mentor/scenarios">К сценариям</a>')}</div>`:""}
      <div class="notice neutral gap-top">${icon("info")}<p>${state.mode==="demo"?'Сценарный режим использует заранее описанные ответы и ограниченное распознавание фраз. Это техническая практика без вызовов AI. Для свободных формулировок подключите OpenAI в пространстве наставника.':'OpenAI помогает понимать смысл ваших реплик. Ответы клиента опираются на утверждённый сценарий. API-запросы оплачиваются в вашем аккаунте OpenAI.'}</p></div>
      <div class="section-heading"><h2>Ваша практика</h2><a class="text-link" href="#learner/history">Все беседы${icon("arrow")}</a></div><div class="stats-grid">${statCard("chat",active.length,"В процессе","Можно продолжить")}${statCard("check",finished.length,"Завершено","Доступен подробный разбор")}${statCard("mentor",reviewed.length,"С отзывом наставника","Отправьте беседу на проверку")}</div><div class="footer-note">${icon("target")}Цель — обоснованная консультация. Честный отказ тоже может быть правильным исходом.</div>`;
  }
  function historyPage() {
    const q=state.historySearch.toLowerCase();
    const sessions=state.sessions.filter(s=>(state.historyFilter==="all"||s.status===state.historyFilter||(state.historyFilter==="reviewed"&&s.review_status==="reviewed"))&&`${s.title} ${s.customer_name}`.toLowerCase().includes(q));
    return `${pageHead("Личная практика","Мои беседы","Продолжайте разговоры, возвращайтесь к разбору и учитывайте обратную связь.",'<a class="btn primary" href="#learner/practice">'+icon("plus")+'Новая беседа</a>')}<div class="toolbar"><div class="filter-tabs" role="group" aria-label="Фильтр бесед">${[["all","Все"],["active","В процессе"],["finished","Завершённые"],["reviewed","С отзывом"]].map(([key,label])=>`<button class="filter-tab ${state.historyFilter===key?"active":""}" data-action="history-filter" data-filter="${key}" aria-pressed="${state.historyFilter===key}">${label}</button>`).join("")}</div><label class="search-box">${icon("search")}<span class="sr-only">Найти беседу</span><input type="search" id="history-search" placeholder="Найти беседу…" value="${esc(state.historySearch)}" autocomplete="off"></label></div><div class="card table-wrap">${state.sessions.length?`<table class="data-table"><thead><tr><th>Беседа</th><th>Дата</th><th>Режим</th><th>Статус</th><th><span class="sr-only">Действие</span></th></tr></thead><tbody>${sessions.map(s=>`<tr><td><span class="cell-title">${esc(s.title)}</span><span class="cell-sub">${esc(s.customer_name)} · ${s.turn_count||0} ${plural(s.turn_count||0,["ход","хода","ходов"])}</span></td><td class="nowrap">${date(s.created_at,true)}</td><td>${modePill(s.mode)}</td><td>${statusPill(s)}</td><td><div class="table-actions"><a class="btn small-btn" href="#learner/session/${esc(s.id)}">${s.status==="active"?"Продолжить":"Разбор"}${icon("arrow")}</a></div></td></tr>`).join("")||'<tr><td class="empty-cell" colspan="5">По этому запросу беседы не найдены.</td></tr>'}</tbody></table>`:empty("chat","Здесь появятся ваши беседы","Выберите клиента и начните первую консультацию. Всё сохранится автоматически.",'<a class="btn primary" href="#learner/practice">Выбрать клиента'+icon("arrow")+'</a>')}</div>`;
  }
  function companyPage() {
    const c=state.company;if(!c)return empty("building","Компания не настроена","Откройте пространство наставника и заполните карточку компании.");
    return `${pageHead("Ваши возможности","О компании","Во время консультации предлагайте только те услуги и условия, которые компания может выполнить.")}<section class="card card-pad"><div class="company-profile-header"><div class="company-monogram">${esc(initials(c.name))}</div><div><h2>${esc(c.name)}</h2><div class="actions"><span class="pill ${c.reviewed?"green":"amber"}">${c.reviewed?"Проверено наставником":"Требуется проверка"}</span><span class="caption">Версия ${c.revision}</span></div></div></div><p class="company-description">${esc(c.description)}</p>${safeURL(c.source_url)?`<div class="gap-top"><span class="caption">Источник: </span><a class="source-link" href="${esc(safeURL(c.source_url))}" target="_blank" rel="noopener noreferrer">${esc(c.source_url)}</a></div>`:""}</section><div class="section-heading"><h2>Услуги и условия</h2><p>${c.services.length} ${plural(c.services.length,["услуга","услуги","услуг"])}</p></div><div class="service-grid">${c.services.map(s=>`<article class="card service-card">${icon("tool")}<h3>${esc(s.title)}</h3><p>${esc(s.description)}</p>${s.conditions?`<div class="service-conditions"><strong>Перед предложением</strong>${esc(s.conditions)}</div>`:""}</article>`).join("")}</div><section class="card card-pad gap-top"><h3>Границы возможностей</h3><p class="company-description">${esc(c.limitations)}</p></section>`;
  }

  function stepper(phase) {
    const phases=["needs","capabilities","proposal"];const current=phase==="completed"?3:Math.max(0,phases.indexOf(phase));
    return `<div class="chat-stepper" aria-label="Этапы консультации">${phases.map((p,i)=>`<div class="chat-step ${i<current?"done":i===current?"current":""}" ${i===current?'aria-current="step"':""}><span class="chat-step-num">${i<current?icon("check"):i+1}</span><span>${PHASES[p]}</span></div>`).join("")}</div>`;
  }
  function messageHTML(message,session,transcript=false) {
    const learner=message.role==="learner";const name=learner?"Вы":session.customer_name;
    return `<article class="message ${learner?"learner":"customer"}" ${transcript?`data-transcript-turn="${Number(message.turn)||0}"`:""}><span class="avatar small-avatar">${learner?icon("user"):esc(initials(name))}</span><div class="message-content"><div class="message-author"><span>${esc(name)}</span>${message.at?`<time datetime="${esc(message.at)}">${time(message.at)}</time>`:""}${transcript&&learner?`<span>· ход ${Number(message.turn)||0}</span>`:""}</div><div class="message-bubble">${esc(message.text)}</div></div></article>`;
  }
  function chatPage(s) {
    const draft=draftFor(s.id);const limit=state.status?.limits?.max_turns||30;const complete=s.phase==="completed";const exhausted=s.turn_count>=limit;
    const phaseInfo={needs:["01","Понять потребность","Выясните, зачем пришёл клиент и что для него важно. Затем кратко сформулируйте услышанное и проверьте своё понимание."],capabilities:["02","Выяснить возможности","Уточните условия, сроки и порядок принятия решения. Неизвестность тоже нужно ясно обозначить и учесть."],proposal:["03","Обосновать предложение","Свяжите итоговое действие с потребностями клиента, его ограничениями и возможностями компании."],completed:["03","Подвести итог","Консультация дошла до итогового действия. Откройте разбор, чтобы увидеть, на чём оно основано."]}[s.phase]||["01","Потребности",""];
    return `<div class="chat-topline"><a class="back-link" href="#learner/practice">${icon("back")}К выбору клиента</a><button class="btn small-btn ${complete?"green":""}" data-action="finish" ${draft.sending?'disabled':""}>${icon("clipboard")}${complete?"Открыть разбор":"Завершить и разобрать"}</button></div><div class="chat-layout"><section class="card conversation" aria-label="Беседа с клиентом"><header class="conversation-header"><span class="avatar large">${esc(initials(s.customer_name))}</span><div class="conversation-heading"><h1>${esc(s.customer_name)}</h1><p>${esc(s.title)}</p></div>${modePill(s.mode)}</header>${stepper(s.phase)}<div class="messages" id="chat-messages" role="log" aria-label="Сообщения беседы" aria-live="polite" aria-relevant="additions"><div class="chat-date">${date(s.created_at)}</div>${s.messages.map(m=>messageHTML(m,s)).join("")}${draft.sending?`<article class="message customer"><span class="avatar small-avatar">${esc(initials(s.customer_name))}</span><div class="message-content"><div class="message-author">${s.mode==="openai"?"Проверяем смысл реплики…":"Готовим ответ…"}</div><div class="message-bubble"><div class="message-typing" role="status" aria-label="Ожидание ответа"><span></span><span></span><span></span></div></div></div></article>`:""}${complete?`<div class="message-system">${icon("check")}Итоговое действие рассмотрено</div>`:""}</div>
      ${complete||exhausted?`<div class="complete-chat-panel"><h3>${complete?"Можно перейти к разбору":"Достигнут лимит беседы"}</h3><p>${complete?"Посмотрите, какие сведения были выяснены и как вы пришли к предложению.":"Откройте разбор текущей попытки. Для продолжения практики начните новую беседу."}</p><button class="btn primary" data-action="finish">${icon("clipboard")}Открыть разбор</button></div>`:`<form class="composer" id="message-form"><div class="composer-types" role="group" aria-label="Тип вашей реплики"><span class="composer-types-label">Ваша реплика</span>${[["message","chat","Вопрос"],["summary","clipboard","Резюме"],["proposal","target","Предложение"]].map(([kind,ico,label])=>`<button type="button" class="kind-btn ${draft.kind===kind?"active":""}" data-action="kind" data-kind="${kind}" aria-pressed="${draft.kind===kind}" ${draft.sending?'disabled':""}>${icon(ico)}${label}</button>`).join("")}</div><div class="composer-field"><label class="sr-only" for="message-text">Ваша реплика клиенту</label><textarea id="message-text" name="message" maxlength="6000" rows="2" placeholder="${draft.kind==="summary"?"Своими словами сформулируйте, что вы выяснили…":draft.kind==="proposal"?"Предложите действие и объясните, на какие сведения опираетесь…":"Напишите свой вопрос клиенту…"}" required ${draft.sending?'disabled':""}>${esc(draft.text)}</textarea><button class="send-btn" type="submit" aria-label="Отправить реплику" ${draft.sending||!draft.text.trim()?'disabled':""}>${draft.sending?icon("clock"):icon("arrow")}</button></div><div class="composer-bottom"><span>${draft.kind==="summary"&&s.mode==="demo"?"В сценарном режиме опирайтесь на формулировки из ответов клиента.":"Беседа сохраняется после каждого ответа"}</span><span><kbd>Ctrl</kbd> + <kbd>Enter</kbd> · ${s.turn_count}/${limit}</span></div>${draft.error?`<div class="notice error" role="alert">${icon("alert")}<div><p>${esc(draft.error)}</p><button class="text-link" type="button" data-action="retry-message">Повторить отправку</button></div></div>`:""}</form>`}</section>
      <aside class="chat-aside"><section class="card card-pad phase-card"><div class="phase-number">${phaseInfo[0]}</div><div class="stage-title">Текущий этап</div><h3>${phaseInfo[1]}</h3><p>${phaseInfo[2]}</p></section><section class="card card-pad"><h3>Как вести разговор</h3>${[["Потребности",["Что для вас сейчас самое важное?","Какой результат вы хотите получить?","Почему вы обратились именно к нам?"]],["Возможности",["Как вы планируете принимать решение?","Какие сроки нужно учесть?","Бюджет определён или сначала нужна оценка?"]],["Проверка понимания",["Правильно ли я понял, что…","Что я упустил или понял неточно?","Сначала подтвердите потребности, затем ограничения."]]].map(([label,items],i)=>`<details class="guide-details" ${i===0&&s.phase==="needs"?"open":""}><summary>${label}</summary><ul>${items.map(item=>`<li>${item}</li>`).join("")}</ul></details>`).join("")}</section><section class="card card-pad"><div class="field-row-label"><h3>Возможности компании</h3>${icon("building")}</div><p><strong>${esc(s.company?.name||"Компания")}</strong></p><details class="guide-details"><summary>Услуги и условия</summary>${(s.company?.services||[]).map(service=>`<div class="company-mini-service"><strong>${esc(service.title)}</strong><p>${esc(service.description)}</p>${service.conditions?`<p><strong>Условия:</strong> ${esc(service.conditions)}</p>`:""}</div>`).join("")}</details><details class="guide-details"><summary>Ограничения</summary><p class="gap-top">${esc(s.company?.limitations||"Не указаны")}</p></details></section>${s.mode==="demo"?`<div class="notice neutral">${icon("info")}<p>Сценарный режим — проверка механики. Свободное понимание речи AI здесь не проверяется.</p></div>`:""}</aside></div>`;
  }
  function scrollChat() {requestAnimationFrame(()=>{const node=$("#chat-messages");if(node)node.scrollTop=node.scrollHeight;});}

  function overviewPage() {
    const waiting=state.reviews.filter(s=>s.review_status==="submitted");const c=state.company;
    return `${pageHead("Пространство наставника","Подготовка и разбор","Создайте реальную основу консультации, подготовьте учебный случай и дайте сотруднику обратную связь.",'<a class="btn primary" href="#mentor/scenario/new">'+icon("plus")+'Новый сценарий</a>')}<div class="stats-grid">${statCard("building",c?.reviewed?"Готово":"Проверить","Карточка компании",c?.name||"Заполните описание")}${statCard("book",state.scenarios.length,"Учебных сценариев","С отдельной ситуацией клиента")}${statCard("clipboard",waiting.length,"Ожидают проверки","Отправлены учениками")}</div><div class="overview-grid"><section class="card"><div class="card-head"><h2>От подготовки к практике</h2>${icon("target")}</div><div class="card-body"><ol class="setup-list"><li class="setup-item"><span class="setup-step">${c?.reviewed?icon("check"):"1"}</span><div><h4>Описать возможности компании</h4><p>Услуги, условия, ограничения. Можно вставить текст с сайта и проверить его перед тренировкой.</p><a class="text-link" href="#mentor/company">${c?.reviewed?"Открыть карточку":"Подготовить компанию"}${icon("arrow")}</a></div></li><li class="setup-item"><span class="setup-step">${state.scenarios.length?icon("check"):"2"}</span><div><h4>Подготовить ситуацию клиента</h4><p>Потребности и возможности, известные факты и неопределённости. Клиент может ещё не знать свой бюджет.</p><a class="text-link" href="#mentor/scenarios">Открыть сценарии${icon("arrow")}</a></div></li><li class="setup-item"><span class="setup-step">3</span><div><h4>Провести беседу и обсудить результат</h4><p>Ученик выясняет сведения, подтверждает понимание и обосновывает итоговое действие.</p><a class="text-link" href="#learner/practice">Перейти к практике${icon("arrow")}</a></div></li></ol></div></section><div><section class="card"><div class="card-head"><h2>Беседы на проверку</h2><a class="text-link" href="#mentor/reviews">Все${icon("arrow")}</a></div><div class="card-body">${waiting.length?`<div class="quiet-list">${waiting.slice(0,4).map(s=>`<div class="quiet-item"><span class="avatar small-avatar">${esc(initials(s.customer_name))}</span><div><h4>${esc(s.title)}</h4><p>${date(s.updated_at,true)} · ${modeLabel(s.mode)}</p></div><a class="btn small-btn" href="#mentor/review/${esc(s.id)}">Разобрать</a></div>`).join("")}</div>`:'<p class="small muted">Пока здесь пусто. Завершённая беседа появится после того, как ученик отправит её наставнику.</p>'}</div></section><section class="card card-pad gap-top"><div class="field-row-label"><h3>Подключение OpenAI</h3><span class="pill ${canUseAI()?"green":"amber"}">${canUseAI()?"Настроено":"Не подключено"}</span></div><p class="small muted">${canUseAI()?"Можно начать разговор с AI-распознаванием реплик. Реальную беседу запускает ученик.":"Сейчас доступен сценарный режим без API. Для свободной беседы нужен серверный ключ OpenAI."}</p><a class="text-link" href="#mentor/setup">Открыть настройки${icon("arrow")}</a></section></div></div><div class="notice neutral gap-top">${icon("info")}<p>Это два рабочих пространства одного локального владельца. Переключение роли не является входом отдельного пользователя.</p></div>`;
  }
  function companyEditor() {
    const c=state.companyDraft||state.company;
    return `${pageHead("Основа консультации","Компания и её возможности","Здесь определяется, что сотрудник вправе предложить клиенту. Сведения будут доступны ученику во время беседы.",`<span class="pill ${c.reviewed?"green":"amber"}">${c.reviewed?"Проверено":"Нужно проверить"}</span>`)}<form id="company-form"><div class="form-layout"><div><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">01</span><h2>Описание компании</h2></div><div class="form-grid"><div class="form-field"><label for="company-name">Название <span class="required-star">*</span></label><input id="company-name" name="name" type="text" maxlength="240" value="${esc(c.name)}" required></div><div class="form-field"><label for="company-source">Сайт или источник</label><input id="company-source" name="source_url" type="url" maxlength="2000" value="${esc(c.source_url)}" placeholder="https://company.de/services"><span class="field-hint">Ссылка сохраняется как источник. Страница не загружается автоматически.</span></div><div class="form-field full"><label for="company-description">Описание или текст с сайта <span class="required-star">*</span></label><textarea id="company-description" name="description" rows="6" maxlength="12000" required placeholder="Вставьте описание компании, затем проверьте услуги и условия ниже.">${esc(c.description)}</textarea><span class="field-hint">Опишите сферу работы, клиентов и специализацию. Не добавляйте неподтверждённые возможности.</span></div></div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">02</span><h2>Услуги и условия предложения</h2></div><div id="service-rows">${c.services.map((service,i)=>serviceEditor(service,i)).join("")}</div><button class="btn soft small-btn" type="button" data-action="add-service" ${c.services.length>=20?'disabled':""}>${icon("plus")}Добавить услугу</button></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">03</span><h2>Ограничения и проверка</h2></div><div class="form-field"><label for="company-limitations">Чего компания не делает <span class="required-star">*</span></label><textarea id="company-limitations" name="limitations" rows="4" maxlength="5000" required placeholder="Например: не ремонтирует промышленное оборудование; стоимость определяется после диагностики.">${esc(c.limitations)}</textarea></div><label class="checkbox-line checkbox-panel"><input type="checkbox" id="company-reviewed" name="reviewed" ${c.reviewed?"checked":""}><span><strong>Я проверил описание, услуги и ограничения</strong><small>Эта версия станет основой новых бесед. Текущие беседы сохранят свои исходные условия.</small></span></label></section>${state.formError?`<div class="form-error" role="alert">${esc(state.formError)}</div>`:""}<div class="editor-savebar"><p class="draft-label">${state.companyDirty?"Есть несохранённые изменения":"Текущая версия: "+c.revision}</p><button class="btn primary" type="submit" ${state.saving?'disabled':""}>${icon("save")}${state.saving?"Сохраняем…":"Сохранить компанию"}</button></div></div><aside class="form-aside"><section class="card card-pad"><div class="aside-title">Достаточно ясных границ</div><div class="aside-step"><span>01</span><div><strong>Что можно сделать</strong><p>Назовите конкретную услугу и её содержание.</p></div></div><div class="aside-step"><span>02</span><div><strong>При каких условиях</strong><p>Например, после осмотра, согласования стоимости или уточнения срока.</p></div></div><div class="aside-step"><span>03</span><div><strong>Когда нужно отказаться</strong><p>Опишите пределы специализации и обещаний сотрудника.</p></div></div></section><div class="notice amber">${icon("info")}<p>Текст с сайта — исходный материал. Перед практикой наставник подтверждает актуальность условий.</p></div><div class="version-line">${icon("history")}Версии сохраняются в снимках бесед</div></aside></div></form>`;
  }
  function serviceEditor(service,i) {
    return `<fieldset class="service-row" data-service-id="${esc(service.id)}"><legend>Услуга ${i+1}</legend><div class="nested-card-head"><strong>${esc(service.title||"Новая услуга")}</strong><button class="btn ghost danger" type="button" data-action="remove-service" data-index="${i}" aria-label="Удалить услугу ${i+1}" ${state.companyDraft?.services.length<=1?'disabled':""}>${icon("trash")}</button></div><div class="form-field"><label for="service-title-${i}">Название <span class="required-star">*</span></label><input id="service-title-${i}" type="text" data-field="title" maxlength="240" value="${esc(service.title)}" required placeholder="Например, диагностика оборудования"></div><div class="form-field"><label for="service-description-${i}">Что входит <span class="required-star">*</span></label><textarea id="service-description-${i}" class="compact" data-field="description" maxlength="3000" rows="2" required>${esc(service.description)}</textarea></div><div class="form-field"><label for="service-conditions-${i}">Условия и необходимые уточнения</label><textarea id="service-conditions-${i}" class="compact" data-field="conditions" maxlength="3000" rows="2" placeholder="Что необходимо выяснить или согласовать до предложения этой услуги?">${esc(service.conditions)}</textarea></div></fieldset>`;
  }
  function readCompanyForm() {
    const form=$("#company-form");if(!form)return state.companyDraft;
    const original=state.companyDraft||state.company;
    return {id:original.id,revision:original.revision,name:$("#company-name",form).value,description:$("#company-description",form).value,source_url:$("#company-source",form).value,limitations:$("#company-limitations",form).value,reviewed:$("#company-reviewed",form).checked,services:$$(".service-row",form).map(row=>({id:row.dataset.serviceId,title:$("[data-field=title]",row).value,description:$("[data-field=description]",row).value,conditions:$("[data-field=conditions]",row).value}))};
  }
  function blankScenario() {
    const facts=[
      ["situation","needs","Ситуация клиента",["произошло","случилось","проблема"]],
      ["goal","needs","Желаемый результат",["результат","хотите","цель"]],
      ["reason","needs","Причина обращения",["обратились","почему","предыдущ"]],
      ["priority","needs","Что особенно важно",["важно","приоритет"]],
      ["budget","capabilities","Финансовые условия",["бюджет","сумма","потратить"]],
      ["timing","capabilities","Сроки",["срок","когда","ждать"]],
      ["decision","capabilities","Принятие решения",["решение","согласовать","кто"]]
    ].map(([id,stage,label,keywords])=>({id,stage,label,keywords,value:"",status:"known",required:true}));
    return {id:"",revision:1,company_id:state.company.id,title:"",customer_name:"",public_brief:"",opening:"",language:"ru",facts,allowed_outcomes:[],question_hints:["Что привело вас к нам?","Какой результат вы хотите получить?","Что для вас особенно важно?","Правильно ли я понял вашу потребность?","Какие сроки и финансовые условия нужно учесть?","Как вы будете принимать решение?","Верно ли я сформулировал ваши ограничения?"]};
  }
  function scenariosPage() {
    const q=state.scenarioSearch.toLowerCase();const scenarios=state.scenarios.filter(s=>`${s.title} ${s.customer_name}`.toLowerCase().includes(q));
    return `${pageHead("Учебный материал","Сценарии клиентов","У каждого клиента — последовательная ситуация, собственные потребности и допустимые итоги консультации.",'<a class="btn primary" href="#mentor/scenario/new">'+icon("plus")+'Создать сценарий</a>')}<div class="toolbar"><div class="caption">${state.scenarios.length} ${plural(state.scenarios.length,["сценарий","сценария","сценариев"])} · изменения применяются к новым беседам</div><label class="search-box">${icon("search")}<span class="sr-only">Найти сценарий</span><input id="scenario-search" type="search" value="${esc(state.scenarioSearch)}" placeholder="Название или клиент…" autocomplete="off"></label></div><div class="card table-wrap">${state.scenarios.length?`<table class="data-table"><thead><tr><th>Сценарий</th><th>Содержание</th><th>Версия</th><th><span class="sr-only">Действия</span></th></tr></thead><tbody>${scenarios.map(s=>`<tr><td><span class="cell-title">${esc(s.title)}</span><span class="cell-sub">${esc(s.customer_name)} · ${s.language==="de"?"Немецкий":"Русский"}</span></td><td><span class="cell-title">${s.facts.filter(f=>f.stage==="needs").length} + ${s.facts.filter(f=>f.stage==="capabilities").length} сведений</span><span class="cell-sub">Потребности + возможности</span></td><td><span class="pill dark">v${s.revision}</span></td><td><div class="table-actions"><a class="btn small-btn" href="#mentor/scenario/${esc(s.id)}">${icon("edit")}Изменить</a><button class="btn ghost icon-only danger" data-action="delete-scenario" data-id="${esc(s.id)}" aria-label="Удалить сценарий ${esc(s.title)}">${icon("trash")}</button></div></td></tr>`).join("")||'<tr><td class="empty-cell" colspan="4">Сценарии не найдены.</td></tr>'}</tbody></table>`:empty("book","Подготовьте первого клиента","Опишите исходную ситуацию, потребности, ограничения и допустимые итоговые действия.",'<a class="btn primary" href="#mentor/scenario/new">'+icon("plus")+'Создать сценарий</a>')}</div><div class="notice neutral gap-top">${icon("lock")}<p>Скрытые сведения доступны в редакторе наставника. Во время активной беседы ученику передаются только открытая ситуация и ответы клиента.</p></div>`;
  }
  function scenarioEditor() {
    const s=state.scenarioDraft;const isNew=!s.id;
    return `${pageHead("Редактор наставника",isNew?"Новый учебный случай":s.title,"Опишите ситуацию до начала беседы. Клиент будет последовательно опираться на эти сведения.",'<a class="btn" href="#mentor/scenarios">'+icon("back")+'К сценариям</a>')}<form id="scenario-form"><div class="form-layout"><div><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">01</span><h2>То, что видит ученик</h2></div><div class="form-grid"><div class="form-field full"><label for="scenario-title">Название случая <span class="required-star">*</span></label><input id="scenario-title" name="title" type="text" maxlength="240" value="${esc(s.title)}" placeholder="Например: печь снова вышла из строя" required></div><div class="form-field"><label for="customer-name">Имя клиента <span class="required-star">*</span></label><input id="customer-name" type="text" maxlength="240" value="${esc(s.customer_name)}" required></div><div class="form-field"><label for="scenario-language">Язык клиента</label><select id="scenario-language"><option value="ru" ${s.language==="ru"?"selected":""}>Русский</option><option value="de" ${s.language==="de"?"selected":""}>Немецкий</option></select></div><div class="form-field full"><label for="public-brief">Краткая открытая ситуация <span class="required-star">*</span></label><textarea id="public-brief" rows="3" maxlength="3000" required>${esc(s.public_brief)}</textarea><span class="field-hint">Без скрытого бюджета, мотивов и готового правильного ответа.</span></div><div class="form-field full"><label for="scenario-opening">Первая реплика клиента <span class="required-star">*</span></label><textarea id="scenario-opening" rows="2" class="compact" maxlength="2000" placeholder="Здравствуйте. У меня опять возникла проблема с печью." required>${esc(s.opening)}</textarea></div></div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">02</span><h2>Реальность клиента</h2></div><div class="private-note">${icon("lock")}Скрытая часть карточки · только для наставника</div><p class="small muted gap-bottom">Для каждого существенного вопроса укажите ответ клиента или явную неопределённость. «Не определил бюджет» и незаполненное поле — разные вещи.</p><div id="fact-rows">${s.facts.map((fact,i)=>factEditor(fact,i)).join("")}</div><div class="actions"><button class="btn soft small-btn" type="button" data-action="add-fact" data-stage="needs" ${s.facts.length>=20?'disabled':""}>${icon("plus")}Потребность</button><button class="btn soft small-btn" type="button" data-action="add-fact" data-stage="capabilities" ${s.facts.length>=20?'disabled':""}>${icon("plus")}Возможность или ограничение</button></div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">03</span><h2>Допустимые итоговые действия</h2></div><p class="small muted">Отметьте действия, которые могут быть обоснованы после выяснения потребностей и возможностей этого клиента.</p><div class="outcomes-grid">${[...(state.company?.services||[]).map(service=>({id:service.id,title:service.title,description:service.conditions||service.description})),{id:"no_fit",title:"Честный отказ / компания не может помочь",description:"Этот исход допустим, если возможности компании не соответствуют ситуации клиента."}].map(outcome=>`<label class="checkbox-line outcome-option"><input type="checkbox" name="outcome" value="${esc(outcome.id)}" ${s.allowed_outcomes.includes(outcome.id)?"checked":""}><span><strong>${esc(outcome.title)}</strong><small>${esc(outcome.description)}</small></span></label>`).join("")}</div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">04</span><h2>Вопросы для подготовки</h2></div><div class="form-field"><label for="question-hints">План вопросов наставника</label><textarea id="question-hints" rows="7" maxlength="15000">${esc(s.question_hints.join("\n"))}</textarea><span class="field-hint">По одному вопросу на строку, максимум 30. Этот план остаётся в редакторе и не раскрывается в активной беседе.</span></div></section>${state.formError?`<div class="form-error" role="alert">${esc(state.formError)}</div>`:""}<div class="editor-savebar"><p class="draft-label">${state.scenarioDirty?"Есть несохранённые изменения":isNew?"Новый сценарий ещё не сохранён":"Текущая версия: "+s.revision}</p><button class="btn primary" type="submit" ${state.saving?'disabled':""}>${icon("save")}${state.saving?"Сохраняем…":"Сохранить сценарий"}</button></div></div><aside class="form-aside"><section class="card card-pad"><div class="aside-title">Три обязательных этапа</div><div class="aside-step"><span>01</span><div><strong>Потребности</strong><p>Что произошло, зачем пришёл клиент и какой результат ему нужен.</p></div></div><div class="aside-step"><span>02</span><div><strong>Возможности</strong><p>Финансы, сроки, полномочия и другие существенные ограничения.</p></div></div><div class="aside-step"><span>03</span><div><strong>Предложение</strong><p>Только после подтверждения первых двух этапов.</p></div></div></section><section class="card card-pad"><div class="aside-title">Как описать неизвестность</div><p class="small muted">Выберите «Ещё не определено» и напишите реальный ответ клиента: «Сумму пока не определил, сначала хочу понять варианты».</p></section><div class="notice neutral">${icon("history")}<p>Изменения не переписывают уже начатые беседы. Каждая попытка хранит свою версию случая.</p></div></aside></div></form>`;
  }
  function factEditor(fact,i) {
    const na=fact.status==="not_applicable";
    return `<fieldset class="fact-row" data-fact-id="${esc(fact.id)}"><legend>Сведение ${i+1}</legend><div class="nested-card-head"><span class="pill ${fact.stage==="needs"?"green":"amber"}">${fact.stage==="needs"?"Потребности":"Возможности"}</span><button class="btn ghost danger" type="button" data-action="remove-fact" data-index="${i}" aria-label="Удалить сведение ${i+1}" ${state.scenarioDraft.facts.length<=2?'disabled':""}>${icon("trash")}</button></div><div class="form-grid"><div class="form-field"><label for="fact-label-${i}">О чём нужно спросить <span class="required-star">*</span></label><input id="fact-label-${i}" type="text" data-field="label" maxlength="240" value="${esc(fact.label)}" required></div><div class="form-field"><label for="fact-stage-${i}">Этап</label><select id="fact-stage-${i}" data-field="stage"><option value="needs" ${fact.stage==="needs"?"selected":""}>Потребности</option><option value="capabilities" ${fact.stage==="capabilities"?"selected":""}>Возможности</option></select></div><div class="form-field full"><label for="fact-status-${i}">Состояние клиента</label><select id="fact-status-${i}" data-field="status">${Object.entries(KNOWLEDGE).map(([key,label])=>`<option value="${key}" ${fact.status===key?"selected":""}>${label}</option>`).join("")}</select></div><div class="form-field full"><label for="fact-value-${i}">Что клиент может ответить <span class="required-star">*</span></label><textarea id="fact-value-${i}" data-field="value" rows="3" maxlength="2000" required placeholder="Ответ от первого лица, без добавления неописанных обстоятельств.">${esc(fact.value)}</textarea></div><div class="form-field full"><label for="fact-keywords-${i}">Слова для сценарного режима</label><input id="fact-keywords-${i}" type="text" data-field="keywords" maxlength="2500" value="${esc(fact.keywords.join(", "))}" placeholder="бюджет, сумма, расходы"><span class="field-hint">Через запятую. Для OpenAI вопрос оценивается по смыслу; эти слова нужны ограниченному режиму без API.</span></div><div class="form-field full"><label class="checkbox-line"><input type="checkbox" data-field="required" ${fact.required&&!na?"checked":""} ${na?"disabled":""}><span>Обязательно выяснить перед завершением этапа</span></label></div></div></fieldset>`;
  }
  function readScenarioForm() {
    const form=$("#scenario-form");if(!form)return state.scenarioDraft;
    const original=state.scenarioDraft;
    return {id:original.id,revision:original.revision,company_id:original.company_id,title:$("#scenario-title",form).value,customer_name:$("#customer-name",form).value,public_brief:$("#public-brief",form).value,opening:$("#scenario-opening",form).value,language:$("#scenario-language",form).value,
      facts:$$(".fact-row",form).map(row=>({id:row.dataset.factId,stage:$("[data-field=stage]",row).value,label:$("[data-field=label]",row).value,value:$("[data-field=value]",row).value,status:$("[data-field=status]",row).value,keywords:$("[data-field=keywords]",row).value.split(",").map(x=>x.trim()).filter(Boolean),required:$("[data-field=required]",row).checked&&$("[data-field=status]",row).value!=="not_applicable"})),
      allowed_outcomes:$$("input[name=outcome]:checked",form).map(node=>node.value),question_hints:$("#question-hints",form).value.split("\n").map(x=>x.trim()).filter(Boolean)};
  }
  function reviewsPage() {
    const sessions=state.reviews.filter(s=>state.reviewFilter==="all"||s.review_status===state.reviewFilter);
    return `${pageHead("Обратная связь","Проверка бесед","Здесь находятся только беседы, которые ученик завершил и отправил на рассмотрение.")}<div class="toolbar"><div class="filter-tabs" role="group" aria-label="Статус проверки">${[["submitted","Ожидают проверки"],["reviewed","С отзывом"],["all","Все"]].map(([key,label])=>`<button class="filter-tab ${state.reviewFilter===key?"active":""}" data-action="review-filter" data-filter="${key}" aria-pressed="${state.reviewFilter===key}">${label}${key==="submitted"?` · ${state.reviews.filter(s=>s.review_status==="submitted").length}`:""}</button>`).join("")}</div><button class="btn ghost small-btn" data-action="reload">${icon("refresh")}Обновить</button></div><div class="card table-wrap">${sessions.length?`<table class="data-table"><thead><tr><th>Учебный случай</th><th>Дата</th><th>Режим</th><th>Статус</th><th><span class="sr-only">Действие</span></th></tr></thead><tbody>${sessions.map(s=>`<tr><td><span class="cell-title">${esc(s.title)}</span><span class="cell-sub">${esc(s.customer_name)} · ${s.turn_count||0} ${plural(s.turn_count||0,["ход","хода","ходов"])}</span></td><td class="nowrap">${date(s.updated_at,true)}</td><td>${modePill(s.mode)}</td><td>${statusPill(s)}</td><td><div class="table-actions"><a class="btn small-btn ${s.review_status==="submitted"?"primary":""}" href="#mentor/review/${esc(s.id)}">${s.review_status==="submitted"?"Проверить":"Открыть"}${icon("arrow")}</a></div></td></tr>`).join("")}</tbody></table>`:empty("clipboard","Бесед в этой очереди пока нет","После завершения ученик может отправить беседу наставнику. Расшифровка и разбор останутся внутри приложения.")}</div>`;
  }
  function setupPage() {
    const status=state.status;const configured=canUseAI();
    return `${pageHead("Подключение","AI и рабочее пространство","Состояние подключения проверяется на сервере. Интерфейс не принимает и не хранит API-ключ.",'<button class="btn" data-action="reload">'+icon("refresh")+'Обновить статус</button>')}<section class="card connection-card"><div class="connection-logo">${icon("spark")}</div><div><h2>OpenAI</h2><p>${configured?"Подключение настроено на сервере. Выберите OpenAI перед началом новой беседы.":"Для свободного понимания вопросов настройте ключ и модель на Python-сервере."}</p><p class="caption">Состояние конфигурации не является результатом платной проверки API.</p></div><div class="right"><span class="pill ${configured?"green":"amber"}">${configured?"Настроено":"Ожидает настройки"}</span></div></section><div class="settings-grid"><section class="card"><div class="card-head"><h2>Подключение на сервере</h2>${icon("lock")}</div><div class="card-body"><ol class="setup-list"><li class="setup-item"><span class="setup-step">1</span><div><h4>Подготовьте ключ OpenAI</h4><p>Задайте <code class="inline-code">OPENAI_API_KEY</code> в защищённом окружении сервера. Ключ не вставляется в карточку компании, сценарий или чат.</p></div></li><li class="setup-item"><span class="setup-step">2</span><div><h4>Укажите модель и включите режим</h4><p>Настройте <code class="inline-code">OPENAI_MODEL</code> и параметры запуска из инструкции проекта. Перезапустите приложение.</p></div></li><li class="setup-item"><span class="setup-step">3</span><div><h4>Начните отдельную беседу</h4><p>Обновите статус и выберите OpenAI в пространстве ученика. Запросы оплачиваются вашим API-аккаунтом.</p></div></li></ol></div></section><div><section class="card"><div class="card-head"><h2>Текущие параметры</h2></div><div class="card-body"><dl class="detail-list"><div><dt>Модель</dt><dd>${esc(status.ai?.model||"Не указана")}</dd></div><div><dt>Ключ настроен</dt><dd>${status.ai?.configured?"Да":"Нет"}</dd></div><div><dt>Режим OpenAI</dt><dd>${status.ai?.live_enabled?"Разрешён сервером":"Выключен"}</dd></div><div><dt>Лимит ходов</dt><dd>${status.limits?.max_turns||"—"}</dd></div><div><dt>Лимит попыток API</dt><dd>${status.limits?.max_live_attempts||"—"} на беседу</dd></div><div><dt>Сохранение</dt><dd>SQLite · локально</dd></div><div><dt>Версия</dt><dd>${esc(status.version||"—")}</dd></div></dl></div></section><div class="notice neutral gap-top">${icon("info")}<p>Сценарный режим доступен без AI и не расходует API-бюджет. При ошибке OpenAI приложение не подменяет ответ сценарным.</p></div><div class="notice amber gap-top">${icon("user")}<p>Две роли здесь — рабочие пространства локального владельца. Для нескольких пользователей потребуются отдельный вход и проверка прав.</p></div></div></div>`;
  }

  function outcomeLabel(session, outcome) {
    if(!outcome)return "Итоговое действие пока не подтверждено";
    if(outcome==="no_fit")return "Компания не может помочь в этой ситуации";
    return (session.company?.services||[]).find(service=>service.id===outcome)?.title || "Итоговое действие рассмотрено";
  }
  function findingLabel(type) {
    return ({early_proposal:"Преждевременное предложение",premature_offer:"Преждевременное предложение",premature_offer_detected:"Преждевременное предложение",summary_rejected:"Резюме требует уточнения",summary_incomplete:"Недостаточно выясненных сведений",summary_confirmed:"Понимание подтверждено",needs_confirmed:"Потребности подтверждены",capabilities_confirmed:"Возможности подтверждены",proposal_rejected:"Предложение требует обоснования",proposal_accepted:"Итоговое действие рассмотрено",uncertain:"Неоднозначная реплика",question_unmatched:"Вопрос требует уточнения",fact_disclosed:"Получены сведения",invalid_evidence:"Не удалось подтвердить понимание",unsupported_proposal:"Необоснованное предложение",outcome_accepted:"Обоснованное итоговое действие"})[type] || "Наблюдение по беседе";
  }
  function reportPage(s, mentor) {
    const report=s.report||{status:"incomplete",summary:"Разбор этой беседы пока недоступен.",stages:[],findings:[],facts:[],outcome:null,limitations:[]};
    const completed=report.status==="complete";
    return `<div class="chat-topline"><a class="back-link" href="#${mentor?"mentor/reviews":"learner/history"}">${icon("back")}${mentor?"К очереди проверок":"К моим беседам"}</a><div class="actions">${modePill(s.mode)}${statusPill(s)}</div></div><section class="card report-hero ${completed?"":"incomplete"}"><div><div class="eyebrow">${mentor?"Работа с учеником":"Разбор консультации"}</div><h1>${completed?"Все этапы пройдены":"Есть над чем поработать"}</h1><p>${esc(report.summary)}</p><div class="report-meta"><span>${icon("user")}${esc(s.customer_name)}</span><span>${icon("clock")}${date(s.created_at,true)}</span><span>${icon("chat")}${s.turn_count||0} ${plural(s.turn_count||0,["ход","хода","ходов"])}</span></div></div><div class="report-symbol">${icon(completed?"check":"target")}</div></section><div class="report-layout"><div><section class="card card-pad report-section"><h2>Путь консультации</h2><div class="stage-results">${(report.stages||[]).map((stage,i)=>`<div class="stage-result ${stage.confirmed?"confirmed":""}"><span class="stage-result-icon">${stage.confirmed?icon("check"):String(i+1).padStart(2,"0")}</span><div><strong>${esc(stage.label)}</strong><span class="caption">${stage.confirmed?"Подтверждено в этой попытке":"Пока не подтверждено"}</span></div><span class="pill ${stage.confirmed?"green":""}">${stage.confirmed?"Пройдено":"Не завершено"}</span></div>`).join("")}</div><div class="notice neutral gap-top">${icon("target")}<p><strong>Итог:</strong> ${esc(outcomeLabel(s,report.outcome))}</p></div></section><section class="card card-pad report-section"><h2>Моменты для разбора</h2>${report.findings?.length?report.findings.map(f=>`<div class="finding"><span class="finding-icon">${icon(["summary_confirmed","needs_confirmed","capabilities_confirmed","proposal_accepted","outcome_accepted"].includes(f.type)?"check":"info")}</span><div><div class="finding-label">${findingLabel(f.type)}</div><p>${esc(f.detail)}</p>${Number(f.turn)>0?`<button class="text-link" data-action="show-turn" data-turn="${Number(f.turn)}">Посмотреть ход ${Number(f.turn)}${icon("arrow")}</button>`:""}</div></div>`).join(""):'<p class="small muted">В этой попытке нет отдельных событий для разбора. Сверьте полноту этапов и содержание разговора ниже.</p>'}</section><section class="card card-pad report-section"><h2>Что удалось выяснить</h2><p class="small muted gap-bottom">Теперь скрытая часть случая доступна для разбора. Неопределённость клиента сохраняется как отдельное состояние.</p>${(report.facts||[]).map(f=>`<div class="fact-result"><div class="fact-result-top"><strong>${esc(f.label)}</strong><span class="pill ${f.discovered?"green":"amber"}">${f.discovered?"Выяснено":"Не выяснено"}</span></div><p>${esc(f.value)}</p><div class="fact-meta">${f.stage==="needs"?"Потребности":"Возможности"} · ${esc(KNOWLEDGE[f.status]||f.status)}</div></div>`).join("")}</section><details class="card transcript-details report-section" id="report-transcript"><summary><span>Полная расшифровка · ${s.messages.length} ${plural(s.messages.length,["сообщение","сообщения","сообщений"])}</span>${icon("chevron")}</summary><div class="transcript">${s.messages.map(m=>messageHTML(m,s,true)).join("")}</div></details></div><aside class="report-aside"><section class="card card-pad"><h3>Сохранить разбор</h3><p>Расшифровка, результат этапов и сведения о режиме беседы.</p><div class="export-buttons">${[["pdf","PDF-документ","Для чтения"],["txt","Текстовая расшифровка","TXT"],["json","Данные беседы","JSON"]].map(([format,label,suffix])=>`<button class="btn" data-action="export" data-format="${format}" ${state.exportBusy?'disabled':""}>${icon("download")}${state.exportBusy===format?"Готовим…":label}<span>${suffix}</span></button>`).join("")}</div></section>
      ${mentor?`<section class="card card-pad review-card"><h3>${s.review_status==="reviewed"?"Отзыв наставника":"Дать обратную связь"}</h3><p>Отметьте удачные вопросы, пропущенные уточнения и один фокус следующей попытки.</p><form id="review-form"><label class="sr-only" for="review-note">Отзыв наставника</label><textarea id="review-note" class="review-textarea" maxlength="6000" required placeholder="Что получилось? Где стоило уточнить? Над чем поработать дальше?">${esc(state.noteDrafts[s.id]??s.review_note??"")}</textarea><button class="btn primary gap-top" type="submit" ${state.saving?'disabled':""}>${icon("check")}${state.saving?"Сохраняем…":"Сохранить отзыв"}</button></form></section>`:`<section class="card card-pad review-card"><h3>Обратная связь наставника</h3>${s.review_status==="reviewed"?`<div class="review-note">${esc(s.review_note)}</div>`:s.review_status==="submitted"?`<p>Беседа находится в очереди наставника. Отзыв появится здесь после проверки.</p><span class="pill amber">${icon("clock")}На проверке</span><button class="text-link gap-top" data-action="reload">Обновить${icon("refresh")}</button>`:`<p>Передайте завершённую беседу на рассмотрение. Она появится в пространстве наставника.</p><button class="btn primary" data-action="submit-review" ${state.saving?'disabled':""}>${icon("send")}${state.saving?"Отправляем…":"Отправить наставнику"}</button><p class="caption gap-top">Внутри приложения, без отправки по почте.</p>`}</section>`}
      <section class="card card-pad"><h3>Как читать этот результат</h3><ul class="limitations">${(report.limitations||[]).map(item=>`<li>${esc(item)}</li>`).join("")||'<li>Результат относится к конкретной попытке и не доказывает перенос навыка в реальную консультацию.</li>'}</ul></section>${!mentor?`<section class="card card-pad"><h3>Следующая попытка</h3><p>Повтор поможет отработать формулировки. Другой случай проверит способ рассуждения.</p><div class="export-buttons"><button class="btn" data-action="repeat" data-id="${esc(s.scenario_id)}" data-mode="${esc(s.mode)}" ${state.starting?'disabled':""}>${icon("refresh")}Повторить случай</button><a class="btn ghost" href="#learner/practice">Выбрать другого клиента${icon("arrow")}</a></div></section>`:""}</aside></div>`;
  }

  async function startSession(id, mode=state.mode) {
    if(state.starting)return;
    const generation=state.generation;state.starting=id;render();
    try {const result=await api("/api/sessions",{method:"POST",body:{scenario_id:id,mode}});state.starting=null;if(generation===state.generation){state.session=result.session;go(`learner/session/${result.session.id}`);}else toast("Беседа создана. Она доступна в разделе «Мои беседы».");}
    catch(error){state.starting=null;if(generation===state.generation)render();toast(error.message,true);}
  }
  async function sendMessage() {
    const session=state.session;if(!session||session.status!=="active")return;
    const draft=draftFor(session.id);if(draft.sending)return;
    const field=$("#message-text");if(field)draft.text=field.value;
    const text=draft.text.trim();if(!text)return;
    if(text.length>6000){toast("Реплика не должна быть длиннее 6000 символов.",true);return;}
    if(!draft.pending||draft.pending.text!==text||draft.pending.kind!==draft.kind)draft.pending={text,kind:draft.kind,request_id:uid(),version:session.version};
    const payload={...draft.pending};draft.sending=true;draft.error=null;render();scrollChat();
    try {
      const result=await api(`/api/sessions/${encodeURIComponent(session.id)}/messages`,{method:"POST",body:payload});
      draft.sending=false;draft.text="";draft.pending=null;draft.error=null;
      if(result.session.phase!==session.phase)draft.kind="message";
      if(state.session?.id===session.id)state.session=result.session;
      if(state.route.role==="learner"&&state.route.view==="session"&&state.route.id===session.id){render();scrollChat();requestAnimationFrame(()=>$("#message-text")?.focus());}
    } catch(error) {
      draft.sending=false;draft.error=error.message;
      if(error.status===409) {
        try {const result=await api(`/api/sessions/${encodeURIComponent(session.id)}`);if(state.session?.id===session.id)state.session=result.session;draft.pending=null;draft.error=`${error.message} Актуальная беседа загружена; проверьте её перед повторной отправкой.`;} catch(_) {}
      }
      if(state.route.role==="learner"&&state.route.view==="session"&&state.route.id===session.id){render();scrollChat();requestAnimationFrame(()=>$("#message-text")?.focus());} else toast(error.message,true);
    }
  }
  async function finishSession() {
    const session=state.session;if(!session||session.status!=="active"||draftFor(session.id).sending)return;
    if(session.phase!=="completed") {
      const accepted=await confirmDialog("Завершить эту попытку?","После завершения откроются разбор и скрытые сведения клиента. Продолжить эту же беседу уже нельзя, но можно начать новую попытку.","Завершить и разобрать");
      if(!accepted)return;
    }
    try {const result=await api(`/api/sessions/${encodeURIComponent(session.id)}/finish`,{method:"POST"});state.session=result.session;render();window.scrollTo({top:0,behavior:"smooth"});}
    catch(error){toast(error.message,true);}
  }
  async function submitReview() {
    if(state.saving)return;state.saving=true;render();
    try {const result=await api(`/api/sessions/${encodeURIComponent(state.session.id)}/submit`,{method:"POST"});state.session=result.session;state.saving=false;render();toast("Беседа добавлена в очередь наставника.");}
    catch(error){state.saving=false;render();toast(error.message,true);}
  }
  async function saveReview() {
    const session=state.session;const note=$("#review-note")?.value.trim();if(!note||state.saving)return;
    state.noteDrafts[session.id]=note;state.saving=true;render();
    try {const result=await api(`/api/mentor/reviews/${encodeURIComponent(session.id)}`,{method:"POST",body:{note},mentor:true});state.session=result.session;state.saving=false;render();toast("Отзыв сохранён. Он доступен ученику в разборе беседы.");}
    catch(error){state.saving=false;render();toast(error.message,true);}
  }
  async function exportSession(format) {
    if(!["pdf","txt","json"].includes(format)||state.exportBusy)return;
    const session=state.session;if(session.status!=="finished")return;
    state.exportBusy=format;render();
    try {
      const response=await fetch(`/api/sessions/${encodeURIComponent(session.id)}/export.${format}`,{credentials:"same-origin"});
      if(!response.ok){let data;try{data=await response.json();}catch(_){}throw new Error(data?.error?.message||"Не удалось подготовить документ.");}
      const blob=await response.blob();if(!blob.size)throw new Error("Получен пустой файл. Повторите экспорт.");
      const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`klareki-dialog-${session.id.slice(0,12)}.${format}`;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);toast("Документ подготовлен для скачивания.");
    } catch(error) {toast(error.message||"Не удалось скачать документ.",true);}
    finally {state.exportBusy=null;render();}
  }
  async function saveCompany() {
    if(state.saving)return;
    state.companyDraft=readCompanyForm();state.formError=null;state.saving=true;render();
    try {
      const result=await api("/api/mentor/company",{method:"PUT",body:state.companyDraft,mentor:true});
      state.company=result.company;state.companyDraft=copy(result.company);state.companyDirty=false;state.saving=false;render();toast("Компания сохранена. Новые беседы будут использовать эту версию.");
    } catch(error) {state.saving=false;state.formError=error.message;render();$(".form-error")?.scrollIntoView({behavior:"smooth",block:"center"});}
  }
  async function saveScenario() {
    if(state.saving)return;
    state.scenarioDraft=readScenarioForm();state.formError=null;const scenario=state.scenarioDraft;
    if(!scenario.allowed_outcomes.length){state.formError="Выберите хотя бы одно допустимое итоговое действие.";render();$(".form-error")?.scrollIntoView({behavior:"smooth",block:"center"});return;}
    if(scenario.question_hints.length>30||scenario.question_hints.some(q=>q.length>500)){state.formError="Можно сохранить до 30 вопросов, не длиннее 500 символов каждый.";render();return;}
    if(scenario.facts.some(f=>f.keywords.length>24||f.keywords.some(k=>k.length>100))){state.formError="Для одного сведения можно указать до 24 ключевых фраз, каждая — не длиннее 100 символов.";render();return;}
    state.saving=true;render();
    try {
      const result=await api("/api/mentor/scenarios",{method:"POST",body:scenario,mentor:true});
      state.scenarioDraft=copy(result.scenario);state.scenarioDraftKey=result.scenario.id;state.scenarioDirty=false;state.saving=false;toast("Сценарий сохранён. Изменения действуют для новых бесед.");
      if(state.route.id!==result.scenario.id)go(`mentor/scenario/${result.scenario.id}`);else render();
    } catch(error) {state.saving=false;state.formError=error.message;render();$(".form-error")?.scrollIntoView({behavior:"smooth",block:"center"});}
  }
  async function deleteScenario(id) {
    const scenario=state.scenarios.find(s=>s.id===id);if(!scenario)return;
    if(!await confirmDialog("Удалить сценарий?",`«${scenario.title}» исчезнет из каталога новых бесед. Уже начатые и завершённые попытки сохранят свои исходные карточки.`,"Удалить",true))return;
    try {await api(`/api/mentor/scenarios/${encodeURIComponent(id)}`,{method:"DELETE",mentor:true});if(state.scenarioDraftKey===id){state.scenarioDraft=null;state.scenarioDraftKey=null;state.scenarioDirty=false;}toast("Сценарий удалён из каталога.");await loadRoute();}
    catch(error){toast(error.message,true);}
  }
  function markCompanyDirty() {
    state.companyDirty=true;const label=$(".draft-label");if(label)label.textContent="Есть несохранённые изменения";
  }
  function markScenarioDirty() {
    state.scenarioDirty=true;const label=$(".draft-label");if(label)label.textContent="Есть несохранённые изменения";
  }
  function renderKeepFocus(id) {
    const current=document.getElementById(id);const start=current?.selectionStart;const end=current?.selectionEnd;
    render();const next=document.getElementById(id);next?.focus();if(start!=null&&next?.setSelectionRange)try{next.setSelectionRange(start,end);}catch(_){}
  }
  async function clickHandler(event) {
    const target=event.target.closest("[data-action]");if(!target||target.disabled)return;
    const action=target.dataset.action;
    if(action==="menu") {state.menu=!state.menu;$("#sidebar").classList.toggle("open",state.menu);$(".mobile-shade").classList.toggle("open",state.menu);target.setAttribute("aria-expanded",String(state.menu));return;}
    if(action==="menu-close") {state.menu=false;$("#sidebar").classList.remove("open");$(".mobile-shade").classList.remove("open");$(".menu-btn")?.setAttribute("aria-expanded","false");return;}
    if(action==="role") {go(`${target.dataset.role}/${target.dataset.role==="mentor"?"overview":"practice"}`);return;}
    if(action==="reload") {await loadRoute();return;}
    if(action==="mode") {if(target.dataset.mode==="openai"&&!canUseAI())return;state.mode=target.dataset.mode;render();return;}
    if(action==="start"||action==="repeat") {await startSession(target.dataset.id,target.dataset.mode||state.mode);return;}
    if(action==="history-filter") {state.historyFilter=target.dataset.filter;render();return;}
    if(action==="review-filter") {state.reviewFilter=target.dataset.filter;render();return;}
    if(action==="kind") {
      const draft=draftFor(state.session.id);draft.text=$("#message-text")?.value||draft.text;draft.kind=target.dataset.kind;draft.pending=null;draft.error=null;render();scrollChat();$("#message-text")?.focus();return;
    }
    if(action==="retry-message") {await sendMessage();return;}
    if(action==="finish") {await finishSession();return;}
    if(action==="submit-review") {await submitReview();return;}
    if(action==="export") {await exportSession(target.dataset.format);return;}
    if(action==="show-turn") {
      const details=$("#report-transcript");details.open=true;
      const row=$(`[data-transcript-turn="${Number(target.dataset.turn)}"]`,details);(row||details).scrollIntoView({behavior:"smooth",block:"center"});return;
    }
    if(action==="add-service") {
      state.companyDraft=readCompanyForm();if(state.companyDraft.services.length>=20)return;
      state.companyDraft.services.push({id:identifier("service"),title:"",description:"",conditions:""});state.companyDraft.reviewed=false;markCompanyDirty();render();const last=$$(".service-row").at(-1);last?.scrollIntoView({behavior:"smooth",block:"center"});$("input",last)?.focus();return;
    }
    if(action==="remove-service") {
      state.companyDraft=readCompanyForm();if(state.companyDraft.services.length<=1)return;
      state.companyDraft.services.splice(Number(target.dataset.index),1);state.companyDraft.reviewed=false;markCompanyDirty();render();return;
    }
    if(action==="add-fact") {
      state.scenarioDraft=readScenarioForm();if(state.scenarioDraft.facts.length>=20)return;
      state.scenarioDraft.facts.push({id:identifier("fact"),stage:target.dataset.stage,label:"",value:"",status:"known",keywords:[],required:true});markScenarioDirty();render();const last=$$(".fact-row").at(-1);last?.scrollIntoView({behavior:"smooth",block:"center"});$("input",last)?.focus();return;
    }
    if(action==="remove-fact") {
      state.scenarioDraft=readScenarioForm();if(state.scenarioDraft.facts.length<=2)return;state.scenarioDraft.facts.splice(Number(target.dataset.index),1);markScenarioDirty();render();return;
    }
    if(action==="delete-scenario") {await deleteScenario(target.dataset.id);}
  }
  function inputHandler(event) {
    const target=event.target;
    if(target.id==="message-text"&&state.session) {
      const draft=draftFor(state.session.id);draft.text=target.value;
      if(draft.pending&&(draft.pending.text!==target.value.trim()))draft.pending=null;
      const send=$(".send-btn");if(send)send.disabled=draft.sending||!target.value.trim();return;
    }
    if(target.id==="history-search") {state.historySearch=target.value;renderKeepFocus("history-search");return;}
    if(target.id==="scenario-search") {state.scenarioSearch=target.value;renderKeepFocus("scenario-search");return;}
    if(target.id==="review-note"&&state.session){state.noteDrafts[state.session.id]=target.value;return;}
    if(target.closest("#company-form")) {
      markCompanyDirty();if(target.id!=="company-reviewed")$("#company-reviewed").checked=false;return;
    }
    if(target.closest("#scenario-form"))markScenarioDirty();
  }
  function changeHandler(event) {
    const target=event.target;
    if(target.closest("#company-form"))markCompanyDirty();
    if(target.closest("#scenario-form")) {
      markScenarioDirty();
      if(target.matches("[data-field=status]")) {
        const row=target.closest(".fact-row");const required=$("[data-field=required]",row);required.disabled=target.value==="not_applicable";if(required.disabled)required.checked=false;
      }
    }
  }
  function submitHandler(event) {
    const id=event.target.id;
    if(["message-form","company-form","scenario-form","review-form"].includes(id))event.preventDefault();
    if(id==="message-form")sendMessage();
    else if(id==="company-form")saveCompany();
    else if(id==="scenario-form")saveScenario();
    else if(id==="review-form")saveReview();
  }
  $("#app").addEventListener("click",event=>{clickHandler(event).catch(error=>toast(error.message||"Не удалось выполнить действие.",true));});
  $("#app").addEventListener("input",inputHandler);
  $("#app").addEventListener("change",changeHandler);
  $("#app").addEventListener("submit",submitHandler);
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&state.menu){state.menu=false;$("#sidebar")?.classList.remove("open");$(".mobile-shade")?.classList.remove("open");$(".menu-btn")?.setAttribute("aria-expanded","false");$(".menu-btn")?.focus();}
    if(event.key==="Enter"&&(event.ctrlKey||event.metaKey)&&event.target.id==="message-text"){event.preventDefault();sendMessage();}
  });
  window.addEventListener("hashchange",loadRoute);
  window.addEventListener("beforeunload",event=>{if(state.companyDirty||state.scenarioDirty){event.preventDefault();event.returnValue="";}});
  if(!location.hash) {let workspace="learner";try{workspace=localStorage.getItem("klareki-workspace")==="mentor"?"mentor":"learner";}catch(_){}history.replaceState(null,"",`#${workspace}/${workspace==="mentor"?"overview":"practice"}`);}
  loadRoute();
})();
