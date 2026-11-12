"use strict";

(() => {
  const AUTH=window.TRAINER_AUTH;
  const U=window.TrainerUI,T=U.t;
  const historyPositions=new Map();let acceptedHash=location.hash,restoringHash=false;
  const PORTAL_ROLE=AUTH.user.role==="mentor_admin"?"mentor":"learner";
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const copy = (value) => JSON.parse(JSON.stringify(value));
  const uid = () => window.crypto?.randomUUID?.() || `request_${Date.now()}_${Math.random().toString(36).slice(2, 14)}`;
  const identifier = (prefix) => `${prefix}_${uid().replace(/[^a-z0-9]/gi, "").slice(0, 12).toLowerCase()}`;
  const ICONS = {
    mic:'<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3M8 22h8"/>',
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
  const PHASES = {needs:window.TrainerI18n.t("dashboard.text_094"),capabilities:window.TrainerI18n.t("dashboard.text_096"),proposal:window.TrainerI18n.t("dashboard.text_098"),completed:window.TrainerI18n.t("dashboard.text_624")};
  const KNOWLEDGE = {known:window.TrainerI18n.t("dashboard.text_625"),undecided:window.TrainerI18n.t("dashboard.text_626"),does_not_know:window.TrainerI18n.t("dashboard.text_627"),refuses_to_disclose:window.TrainerI18n.t("dashboard.text_628"),not_applicable:window.TrainerI18n.t("dashboard.text_629")};
  const REVIEW = {not_submitted:window.TrainerI18n.t("dashboard.text_630"),submitted:window.TrainerI18n.t("dashboard.text_005"),reviewed:window.TrainerI18n.t("dashboard.text_004")};
  const state = {
    route:{role:"learner",view:"practice",id:null}, status:null, profiles:[], company:null, catalogue:[], sessions:[], scenarios:[], reviews:[],
    session:null, loading:true, error:null, menu:false, mode:"demo", modeChoice:null, generation:0, companyDraft:null, companyDirty:false,
    scenarioDraft:null, scenarioDraftKey:null, scenarioDirty:false, formError:null, saving:false, drafts:{}, noteDrafts:{},
    historyFilter:"all", historySearch:"", scenarioSearch:"", reviewFilter:"submitted", starting:null, exportBusy:null
  };
  const date = (value, withTime = false) => {
    if (!value) return "—";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "—";
    return new Intl.DateTimeFormat(window.TrainerI18n.locale, withTime ? {day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"} : {day:"2-digit",month:"short",year:"numeric"}).format(parsed);
  };
  const time = (value) => {
    const parsed = new Date(value || "");
    return Number.isNaN(parsed.getTime()) ? "" : new Intl.DateTimeFormat(window.TrainerI18n.locale,{hour:"2-digit",minute:"2-digit"}).format(parsed);
  };
  const initials = (name) => String(name || window.TrainerI18n.t("dashboard.text_001")).split(/\s+/).filter(Boolean).slice(0,2).map((x) => x[0]).join("").toUpperCase();
  const plural = (n, forms) => window.TrainerI18n.plural(n,forms);
  const modeLabel = mode => window.TrainerI18n.t(mode==="demo"?"clean.example":"dashboard.text_002");
  const modePill = (mode) => `<span class="pill ${mode !== "demo" ? "green" : "amber"}">${icon(mode !== "demo" ? "spark" : "book")}${modeLabel(mode)}</span>`;
  const canUseAI = () => Boolean(state.status?.ai?.configured && state.status?.ai?.live_enabled);
  const maxAIRequestsPerTurn = () => Number.isSafeInteger(state.status?.ai?.max_requests_per_turn)&&state.status.ai.max_requests_per_turn>0?state.status.ai.max_requests_per_turn:null;
  function syncNewSessionMode() {
    // This choice applies only to a new session. A saved session keeps its server mode.
    if(!canUseAI()) {state.mode="simple_actor";state.modeChoice=null;return;}
    state.mode="simple_actor";
  }
  const statusPill = session => session.status==='finished'?`<span class="pill review22-status-pill ${session.review_status==='submitted'?'amber':session.review_status==='reviewed'?'green':'dark'}">${window.TrainerI18n.t(session.review_status==='submitted'?'mentorNav.awaiting':session.review_status==='reviewed'?'mentorNav.reviewed':'review22.status_'+session.review_status)}</span>`:`<span class="pill green">${window.TrainerI18n.t('dashboard.text_007')}</span>`;
  const safeURL = (value) => { try {const u = new URL(value);return ["https:","http:"].includes(u.protocol) ? u.href : "";} catch (_) {return "";} };
  const studio=window.makeMentorStudio({api,esc,icon,toast,render,go});
  const draftFor = (id) => state.drafts[id] ||= {text:"",kind:"message",pending:null,error:null,sending:false};

  class APIError extends Error {
    constructor(message, code, status, fields=[]) {super(window.TrainerI18n.error({code}) || message);this.code = code;this.status = status;this.fields=fields;}
  }
  async function api(path, options = {}) {
    const headers = {Accept:"application/json", "X-UI-Locale":window.TrainerI18n.locale, "X-CSRF-Token":AUTH.csrf};
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    // Role is verified by server session, never by a browser header.
    let response;
    try {response = await fetch(path,{method:options.method || "GET",headers,credentials:"same-origin",body:options.body !== undefined ? JSON.stringify(options.body) : undefined});}
    catch (_) {throw new APIError(window.TrainerI18n.t("dashboard.text_008"),"NETWORK_ERROR",0);}
    let data;
    try {data = await response.json();} catch (_) {throw new APIError(window.TrainerI18n.t("dashboard.text_009"),"INVALID_RESPONSE",response.status);}
    if(response.status===401){location.replace("/login");throw new APIError(window.TrainerI18n.t("dashboard.text_010"),"AUTH_REQUIRED",401);}
    if (!response.ok) {
      const validation = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join("; ") : "";
      throw new APIError(data.error?.message || validation || (typeof data.detail === "string" ? data.detail : window.TrainerI18n.t("dashboard.text_011")),data.error?.code || "REQUEST_FAILED",response.status,data.error?.fields);
    }
    return data;
  }
  function toast(message, error = false) {
    const node = document.createElement("div");node.className = `toast${error ? " error" : ""}`;
    node.innerHTML = `${icon(error ? "alert" : "check")}<span>${esc(message)}</span><button aria-label="${window.TrainerI18n.t("dashboard.text_012")}">${icon("close")}</button>`;
    $("button",node).addEventListener("click",() => node.remove());
    $("#toast-region").appendChild(node);setTimeout(() => node.remove(),error ? 9000 : 5000);
  }
  function confirmDialog(title, text, confirmLabel = window.TrainerI18n.t("dashboard.text_013"), danger = false) {
    return new Promise((resolve) => {
      const dialog = $("#confirm-dialog");
      dialog.innerHTML = `<h2 id="dialog-title">${esc(title)}</h2><p>${esc(text)}</p><div class="actions"><button class="btn" data-dialog-cancel>${window.TrainerI18n.t("dashboard.text_014")}</button><button class="btn ${danger ? "danger" : "primary"}" data-dialog-confirm>${esc(confirmLabel)}</button></div>`;
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
    const role = PORTAL_ROLE;
    return {role,view:parts[1] || (role === "mentor" ? "overview" : "practice"),id:parts[2] ? decodeURIComponent(parts[2]) : null};
  }
  const learning=window.createLearning({state,api,esc,render,toast,icon});
  const conversation=window.createConversationScreen({state,esc,icon,draftFor,learning,date,time,languageName:l=>languageName(l),modeLabel});
  function go(path) {state.menu=false;if(location.hash === `#${path}`)loadRoute();else location.hash=path;}
  function captureDrafts() {
    if ($("#company-form")) state.companyDraft = readCompanyForm();
    if ($("#scenario-form")) state.scenarioDraft = readScenarioForm();
  }
  async function loadRoute() {
    if(restoringHash){restoringHash=false;return;}
    studio.capture();
    const next=getRoute();
    if(state.route.view==='history')historyPositions.set(state.historyFilter,window.scrollY);
    const leaving=next.view!==state.route.view||next.id!==state.route.id;
    if(leaving&&(studio.dirty()&&state.route.view==='personas'||state.companyDirty&&state.route.view==='company'||state.scenarioDirty&&state.route.view==='scenario')){
      captureDrafts();if(!window.confirm(T('leave_unsaved'))){restoringHash=true;location.hash=acceptedHash;return;}
    }
    if(window.TrainerVoice.busy()&&!window.confirm(window.TrainerI18n.t('dictation18.leave'))){restoringHash=true;location.hash=acceptedHash;return;}
    acceptedHash=location.hash;
    if(next.role==='learner'&&next.view==='history'){state.historyFilter=next.id||'all';if(state.route.view==='practice'||next.id==='new'&&state.route.view!=='history')state.historySearch='';}
    captureDrafts();const generation = ++state.generation;const previousRole = state.route.role;state.route = getRoute();state.menu=false;
    if (previousRole === "mentor" && state.route.role === "learner") {state.scenarios=[];state.scenarioDraft=null;state.scenarioDraftKey=null;state.scenarioDirty=false;state.formError=null;}
    window.TrainerVoice.cancel();
    state.loading=true;state.error=null;state.formError=null;render();
    try {
      const [status,initialCompany,materials] = await Promise.all([api("/api/status"),state.company?Promise.resolve(null):api("/api/company"),api("/api/materials")]);
      if(generation!==state.generation)return;
      state.status=status;state.materials=materials;window.TrainerMaterials=materials;if(initialCompany)state.company=initialCompany.company;
      syncNewSessionMode();
      const {role,view,id}=state.route;
      if(role==="mentor"&&["overview","employees","personas"].includes(view)){await studio.load(view,id);if(generation!==state.generation)return;await learning.load();state.loading=false;render();return;}
      if(role === "learner") {
        if(view === "practice") {
          const [catalogue,sessions,company,profiles] = await Promise.all([api("/api/scenarios"),api("/api/sessions"),api("/api/company"),api("/api/client-profiles")]);
          if(generation!==state.generation)return;state.catalogue=catalogue.scenarios;state.sessions=sessions.sessions;state.company=company.company;state.profiles=profiles.profiles;
        } else if(view === "history") {const data=await api("/api/sessions");if(generation!==state.generation)return;state.sessions=data.sessions;}
        else if(view === "session" && id) {const data=await api(`/api/sessions/${encodeURIComponent(id)}`);if(generation!==state.generation)return;state.session=data.session;}
        else if(view === "company") {const data=await api("/api/company");if(generation!==state.generation)return;state.company=data.company;}
        else throw new APIError(window.TrainerI18n.t("dashboard.text_015"),"NOT_FOUND",404);
      } else {
        if(view === "overview") {
          const [company,scenarios,reviews] = await Promise.all([api("/api/company"),api("/api/mentor/scenarios",{mentor:true}),api("/api/mentor/reviews",{mentor:true})]);
          if(generation!==state.generation)return;state.company=company.company;state.scenarios=scenarios.scenarios;state.reviews=reviews.sessions;
        } else if(view === "company") {
          const data=await api("/api/company");if(generation!==state.generation)return;state.company=data.company;
          if(!state.companyDraft || !state.companyDirty)state.companyDraft=copy(data.company);
        } else if(view === "scenarios" || view === "scenario") {
          const [data,company,pairs] = await Promise.all([api("/api/mentor/scenarios",{mentor:true}),api("/api/company"),api("/api/mentor/scenario-personas")]);state.pairs=pairs;
          if(generation!==state.generation)return;state.scenarios=data.scenarios;state.company=company.company;
          if(view === "scenario" && state.scenarioDraftKey!==id) {
            const selected = id === "new" ? blankScenario() : state.scenarios.find((s) => s.id===id);
            if(!selected)throw new APIError(window.TrainerI18n.t("dashboard.text_016"),"NOT_FOUND",404);
            state.scenarioDraft=copy(selected);state.scenarioDraftKey=id;state.scenarioDirty=false;
          }
        } else if(view === "reviews") {const data=await api("/api/mentor/reviews",{mentor:true});if(generation!==state.generation)return;state.reviews=data.sessions;}
        else if(view === "review" && id) {const data=await api(`/api/mentor/reviews/${encodeURIComponent(id)}`,{mentor:true});if(generation!==state.generation)return;state.session=data.session;}
        else if(view !== "setup") throw new APIError(window.TrainerI18n.t("dashboard.text_015"),"NOT_FOUND",404);
      }
      if(generation!==state.generation)return;
      await learning.load();state.loading=false;render();
      if(view !== "session" || state.session?.status !== "active") window.scrollTo({top:view==="history"?(historyPositions.get(state.historyFilter)||0):0,behavior:"auto"});
    } catch(error) {if(generation!==state.generation)return;state.loading=false;state.error=error;render();}
  }
  function navLabel() {
    const labels={employees:window.TrainerI18n.t("dashboard.text_019"),personas:window.TrainerI18n.t("dashboard.text_020"),practice:window.TrainerI18n.t("dashboard.text_025"),history:window.TrainerI18n.t("dashboard.text_026"),session:window.TrainerI18n.t("dashboard.text_632"),company:window.TrainerI18n.t("dashboard.text_021"),overview:window.TrainerI18n.t("dashboard.text_633"),scenarios:window.TrainerI18n.t("dashboard.text_022"),scenario:window.TrainerI18n.t("dashboard.text_634"),reviews:window.TrainerI18n.t("dashboard.text_023"),review:window.TrainerI18n.t("dashboard.text_635"),setup:window.TrainerI18n.t("dashboard.text_024")};
    return labels[state.route.view] || window.TrainerI18n.t("dashboard.text_017");
  }
  function historyMatches(s,filter){return filter==='all'||filter==='active'&&s.status==='active'||filter==='finished'&&s.status==='finished'||filter==='ready'&&s.status==='finished'&&s.review_status==='not_submitted'||filter==='submitted'&&s.review_status==='submitted'||filter==='reviewed'&&s.review_status==='reviewed'||filter==='new'&&learning.isNew(s.id);}
  function render() {
    conversation.capture();
    const role = state.route.role;const mentor = role === "mentor";const view = state.route.view;
    const nav = mentor ? [["overview","grid",window.TrainerI18n.t("dashboard.text_018")],["employees","user",window.TrainerI18n.t("dashboard.text_019")],["reviews","clipboard",window.TrainerI18n.t("dashboard.text_023")],["scenarios","book",window.TrainerI18n.t("dashboard.text_022")],["personas","user",window.TrainerI18n.t("dashboard.text_020")],["company","building",window.TrainerI18n.t("dashboard.text_021")],["setup","settings",window.TrainerI18n.t("dashboard.text_024")]] : [["practice","chat",window.TrainerI18n.t("dashboard.text_025")],["history","history",window.TrainerI18n.t("dashboard.text_026")],["company","building",window.TrainerI18n.t("dashboard.text_027")]];
    let page;
    if(state.loading)page=("<div class=\"loading-state\" role=\"status\"><span class=\"spinner\" aria-hidden=\"true\"></span>"+window.TrainerI18n.t("dashboard.text_028")+"</div>");
    else if(state.error)page=`<div class="card"><div class="empty-state"><div class="empty-icon">${icon("alert")}</div><h3>${window.TrainerI18n.t("dashboard.text_029")}</h3><p>${esc(state.error.message)}</p><button class="btn primary" data-action="reload">${icon("refresh")}${window.TrainerI18n.t("dashboard.text_030")}</button></div></div>`;
    else page=renderPage();
    const isChat=!state.loading&&!state.error&&view==="session"&&state.session?.status==="active";
    const languageBar=document.querySelector(".language-bar");if(languageBar)document.body.append(languageBar);
    $("#app").innerHTML=`<div class="app-shell"><div class="mobile-shade ${state.menu?"open":""}" data-action="menu-close"></div>
      <aside class="sidebar ${state.menu?"open":""}" id="sidebar" aria-label="${window.TrainerI18n.t("dashboard.text_035")}"><a class="brand" href="#${role}/${mentor?"overview":"practice"}" aria-label="Klare KI — ${window.TrainerI18n.t("dashboard.text_036")}"><span class="brand-mark" aria-hidden="true">K<span>·</span></span><div><div class="brand-text">klare ki</div><div class="brand-sub">${window.TrainerI18n.t("dashboard.text_037")}</div></div></a><p class="sidebar-label">${mentor?window.TrainerI18n.t("dashboard.text_031"):window.TrainerI18n.t("dashboard.text_032")}</p><nav class="nav-list">${nav.map(([key,ico,label])=>{const active=view===key||(key==="practice"&&view==="session")||(key==="scenarios"&&view==="scenario")||(key==="reviews"&&view==="review");return `<a class="nav-link ${active?"active":""}" href="#${role}/${key}" ${active?'aria-current="page"':""}>${icon(ico)}<span>${label}</span>${key==="reviews"&&state.reviews.filter(s=>s.review_status==="submitted").length?`<span class="nav-count">${state.reviews.filter(s=>s.review_status==="submitted").length}</span>`:""}</a>`;}).join("")}</nav><div class="sidebar-footer"><div class="sidebar-note"><span>${window.TrainerI18n.t("dashboard.text_038")}</span><p>${window.TrainerI18n.t("dashboard.text_039")}<br>${window.TrainerI18n.t("dashboard.text_040")}<br>${window.TrainerI18n.t("dashboard.text_041")}</p></div><div class="workspace-tag"><span class="status-dot"></span>${window.TrainerI18n.t("dashboard.text_042")}</div></div></aside>
      <div class="main-shell"><header class="topbar"><button class="menu-btn" data-action="menu" aria-label="${window.TrainerI18n.t("dashboard.text_043")}" aria-controls="sidebar" aria-expanded="${state.menu}">${icon("menu")}</button><div class="topbar-heading"><span>${window.TrainerI18n.t("dashboard.text_044")}</span><span class="truncate"><strong>${navLabel()}</strong></span></div><div class="topbar-actions">${learning.notification()}${learning.buttons()}<span class="local-label"><span class="status-dot"></span>${window.TrainerI18n.t("dashboard.text_045")}</span><div class="portal-user"><span class="caption">${esc(AUTH.user.display_name)} · ${mentor?window.TrainerI18n.t("dashboard.text_033"):window.TrainerI18n.t("dashboard.text_034")}</span><button class="btn small-btn" data-action="own-password">${window.TrainerI18n.t("dashboard.text_046")}</button><button class="btn small-btn" data-action="logout">${window.TrainerI18n.t("dashboard.text_047")}</button></div></div></header><main class="page ${isChat?"chat-page":""}" id="main-content" tabindex="-1">${page}</main></div></div>`;
    document.body.classList.toggle('conversation-screen',isChat);
    document.body.classList.toggle('mentor-screen',mentor);
    U.afterRender();
    const aside=$('#company-form .form-aside');if(aside){const help=document.createElement('details');help.className='card card-pad';help.innerHTML='<summary>'+window.TrainerI18n.t('a20.help')+'</summary>';aside.querySelectorAll(':scope>.card,:scope>.notice').forEach(el=>help.append(el));aside.prepend(help);}

    window.TrainerHeaderMenus.mount(learning);
    if(isChat){
      const sidebar=$('#sidebar'),controls=$('.topbar-actions');
      const close=document.createElement('button');close.className='btn conversation-drawer-close';close.dataset.action='menu-close';close.textContent=T('close');sidebar.prepend(close);
      controls.classList.add('conversation-drawer-controls');sidebar.append(controls);
    }
    conversation.afterRender(isChat);learning.mentorAfterRender();
    document.title=`${navLabel()} · Klare KI`;
  }
  function readonlyTraining(s){return `${pageHead(window.TrainerI18n.t("dashboard.text_048"),window.TrainerI18n.t("dashboard.text_049"),window.TrainerI18n.t("dashboard.text_050"))}<div class="actions gap-bottom">${["pdf","json","txt"].map(f=>`<button class="btn" data-action="export" data-format="${f}">${window.TrainerI18n.t("dashboard.text_051")} ${f.toUpperCase()}</button>`).join("")}</div><div class="card mentor-readonly"><div class="transcript">${s.messages.map(m=>messageHTML(m,s,true)).join("")}</div></div>`;}
  function passwordDialog(){
    const dialog=document.getElementById('confirm-dialog');dialog.innerHTML=("<h2>"+window.TrainerI18n.t("dashboard.text_052")+"</h2><form id=\"own-password-form\" class=\"dialog-fields\"><label>"+window.TrainerI18n.t("dashboard.text_053")+"<input id=\"own-old-password\" type=\"password\" autocomplete=\"current-password\" required></label><label>"+window.TrainerI18n.t("dashboard.text_054")+"<input id=\"own-new-password\" type=\"password\" autocomplete=\"new-password\" minlength=\"12\" maxlength=\"128\" required></label><p id=\"own-password-error\" role=\"alert\"></p><button class=\"btn primary\" type=\"submit\">"+window.TrainerI18n.t("dashboard.text_055")+"</button><button class=\"btn\" id=\"own-password-cancel\" type=\"button\">"+window.TrainerI18n.t("dashboard.text_014")+"</button></form>");dialog.showModal();document.getElementById('own-password-cancel').onclick=()=>dialog.close();document.getElementById('own-password-form').onsubmit=async e=>{e.preventDefault();try{await api('/api/auth/password',{method:'POST',body:{current_password:document.getElementById('own-old-password').value,new_password:document.getElementById('own-new-password').value}});location.reload();}catch(err){document.getElementById('own-password-error').textContent=err.message;}};
  }
  function renderPage() {
    const {role,view}=state.route;
    if(role==="learner") {
      if(view==="practice")return practicePage();
      if(view==="history")return historyPage();
      if(view==="company")return companyPage();
      if(view==="session")return state.session.status==="finished"?reportPage(state.session,false):chatPage(state.session);
    } else {
      if(view==="overview")return studio.overview();
      if(view==="employees")return studio.employees(state.route.id);
      if(view==="personas")return studio.personas(state.company);
      if(view==="company")return learning.importer()+companyEditor();
      if(view==="scenarios")return scenariosPage();
      if(view==="scenario")return scenarioEditor()+learning.guidanceEditor();
      if(view==="reviews")return reviewsPage();
      if(view==="review")return state.session.status==="finished"?reportPage(state.session,true):readonlyTraining(state.session);
      if(view==="setup")return setupPage();
    }
    return "";
  }
  const pageHead = (eyebrow,title,description,actions="") => `<div class="page-head"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1>${description?`<p>${esc(description)}</p>`:""}</div>${actions?`<div class="actions">${actions}</div>`:""}</div>`;
  const empty = (ico,title,description,action="") => `<div class="empty-state"><div class="empty-icon">${icon(ico)}</div><h3>${esc(title)}</h3><p>${esc(description)}</p>${action}</div>`;
  const statCard = (ico,value,label,description="") => `<div class="card stat-card"><div class="stat-icon">${icon(ico)}</div><div><div class="stat-value">${esc(typeof value==="number"?window.TrainerI18n.number(value):value)}</div><div class="stat-label">${esc(label)}</div>${description?`<div class="stat-description">${esc(description)}</div>`:""}</div></div>`;

  function newSessionModeNotice() {
    if(state.mode==="simple_actor")return `<div class="notice mode-notice"><div><strong>simple_actor — ${window.TrainerI18n.t("dashboard.text_056")}</strong><p>${window.TrainerI18n.t("dashboard.text_057")}</p></div></div>`;
    if(state.mode==="openai")return `<div class="notice mode-notice gap-bottom" aria-label="${window.TrainerI18n.t("dashboard.text_060")}">${icon("spark")}<div class="mode-notice-copy"><strong>${window.TrainerI18n.t("dashboard.text_061")}</strong><p>${window.TrainerI18n.t("dashboard.text_062")}${maxAIRequestsPerTurn()?` ${window.TrainerI18n.t("dashboard.text_058")} ${maxAIRequestsPerTurn()} ${window.TrainerI18n.t("dashboard.text_059")}`:""} ${window.TrainerI18n.t("dashboard.text_063")}</p></div></div>`;
    return `<div class="notice amber mode-notice gap-bottom" aria-label="${window.TrainerI18n.t("dashboard.text_060")}">${icon("info")}<div class="mode-notice-copy"><strong>${window.TrainerI18n.t("dashboard.text_067")}</strong><p>${window.TrainerI18n.t("dashboard.text_068")}</p><p>${canUseAI()?window.TrainerI18n.t("dashboard.text_064"):("OpenAI "+window.TrainerI18n.t("dashboard.text_065")+" <a class=\"text-link\" href=\"#mentor/setup\">"+window.TrainerI18n.t("dashboard.text_066")+"</a>")}</p></div></div>`;
  }

  function aiUsageMeta(s) {
    const natural=Number.isSafeInteger(s.natural_customer_turns)&&s.natural_customer_turns>=0?s.natural_customer_turns:null;
    const requests=Number.isSafeInteger(s.api_requests)&&s.api_requests>=0?s.api_requests:null;
    const requestLabel=requests!==null&&s.api_count_complete!==true?window.TrainerI18n.t("dashboard.text_069"):window.TrainerI18n.t("dashboard.text_070");
    return `<p class="mode-usage" aria-label="${window.TrainerI18n.t("dashboard.text_072")}"><span title="${window.TrainerI18n.t("dashboard.text_073")}">${window.TrainerI18n.t("dashboard.text_074")} <strong>${natural??window.TrainerI18n.t("dashboard.text_071")}</strong></span><span>${requestLabel}: <strong>${requests??window.TrainerI18n.t("dashboard.text_071")}</strong></span></p>`;
  }

  function sessionModeNotice(s,mentor=false) {
    if(PORTAL_ROLE==="learner")return s.status==="active"?`<div class="notice neutral"><p>${esc(window.TrainerI18n.t('chat.saved_notice'))}</p></div>`:'';
    const fields=[['clean.session_id',s.id],['clean.profile_id',s.client_profile?.id],['clean.scenario_id',s.scenario_id],['clean.materials_id',s.learning_context?.materials?.id]];
    return `<details class="card card-pad report-section"><summary>${window.TrainerI18n.t('clean.technical')}</summary><dl class="detail-list">${fields.filter(([,v])=>v).map(([k,v])=>`<div><dt>${window.TrainerI18n.t(k)}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>${implementationNotice(s,mentor)}<ul>${(s.report?.limitations||[]).map(item=>`<li>${esc(window.TrainerI18n.systemText(item))}</li>`).join('')}</ul></details>`;
  }
  function implementationNotice(s,mentor) {
    if(s.mode==="simple_actor") {
      const p=s.client_profile;
      return `<div class="notice mode-notice session-mode-notice"><div><strong>OpenAI · simple_actor · ${esc(p?.persona_name)} · ${window.TrainerI18n.t("dashboard.text_080")}${esc(p?.version)}</strong><p>${window.TrainerI18n.t("dashboard.text_081")}${esc(p?.persona_version)} · ${window.TrainerI18n.t("dashboard.text_077")}${esc(p?.scenario_version)} (${window.TrainerI18n.t("dashboard.text_082")}${esc(p?.source_revision)}). ${window.TrainerI18n.t("dashboard.text_083")}</p>${aiUsageMeta(s)}</div></div>`;
    }
    if(s.mode==="openai") {
      const message=s.status==="finished"?window.TrainerI18n.t("dashboard.text_084"):canUseAI()?window.TrainerI18n.t("dashboard.text_085"):window.TrainerI18n.t("dashboard.text_086");
      return `<div class="notice ${s.status!=="finished"&&!canUseAI()?"amber ":""}mode-notice session-mode-notice" aria-label="${window.TrainerI18n.t("dashboard.text_087")}">${icon("spark")}<div class="mode-notice-copy"><strong>${window.TrainerI18n.t("dashboard.text_088")}</strong><p>${message}</p>${aiUsageMeta(s)}</div></div>`;
    }
    const action=mentor?"":canUseAI()?`<button class="btn primary small-btn" data-action="start-openai" data-id="${esc(s.scenario_id)}" ${state.starting||draftFor(s.id).sending?'disabled':""}>${icon("spark")}${state.starting===s.scenario_id?window.TrainerI18n.t("dashboard.text_089"):window.TrainerI18n.t("dashboard.text_061")}</button>`:("<a class=\"btn small-btn\" href=\"#mentor/setup\">"+window.TrainerI18n.t("dashboard.text_066"))+icon("arrow")+'</a>';
    return `<div class="notice amber mode-notice session-mode-notice" aria-label="${window.TrainerI18n.t("dashboard.text_087")}">${icon("info")}<div class="mode-notice-copy"><strong>${window.TrainerI18n.t("dashboard.text_092")}</strong><p>${window.TrainerI18n.t("dashboard.text_093")}</p><p>${s.status==="finished"?window.TrainerI18n.t("dashboard.text_090"):window.TrainerI18n.t("dashboard.text_091")}</p></div>${action}</div>`;
  }

  const languageName = lang => ({de:"Deutsch",en:"English",ru:"Русский"})[lang] || lang;
  function trainingLanguage(s) {
    let selected='de';try{selected=localStorage.getItem('trainer.training.language')||'de';}catch(_){}
    return (s.training_languages||[s.language]).includes(selected)?selected:s.language;
  }
  function practicePage() {
    const active=state.sessions.filter(s=>s.status==="active");const finished=state.sessions.filter(s=>s.status==="finished");const reviewed=state.sessions.filter(s=>s.review_status==="reviewed");
    const companyReady=Boolean(state.company?.reviewed);
    const clients=state.catalogue.map(s=>({...s,...state.materials?.scenarios[s.id],company_name:state.materials?.company.name||s.company_name,personas:s.personas.map(p=>({...p,name:state.materials?.persona_labels[p.id]||p.name}))}));
    return `${pageHead('',T('practice_title'),T('practice_help'))}
      <nav class="practice-counts" aria-label="${T('practice_counts')}">${[['active',active.length,T('active')],['finished',finished.length,T('finished')],['reviewed',reviewed.length,T('reviewed')],['certificates',learning.certificateCount(),T('certificates')]].map(([filter,count,label])=>`<a href="#learner/history/${filter}"><strong>${count}</strong><span>${label}</span>${icon('arrow')}</a>`).join('')}</nav>
      <details class="training-guidance card card-pad"><summary>${T('rules')}</summary><p>${window.TrainerI18n.t('dashboard.text_119')}</p><ol>${['needs','capabilities','proposal'].map(k=>`<li>${esc(PHASES[k])}</li>`).join('')}</ol></details>
      ${active.length?`<div class="resume-banner"><span class="avatar small-avatar">${initials(active[0].customer_name)}</span><div><strong>${window.TrainerI18n.t("dashboard.text_100")}</strong><p>${esc(active[0].title)} · ${esc(PHASES[active[0].phase]||window.TrainerI18n.t("dashboard.text_007"))} · ${modeLabel(active[0].mode)}</p></div><a class="btn small-btn" href="#learner/session/${esc(active[0].id)}">${window.TrainerI18n.t("dashboard.text_013")}${icon("arrow")}</a></div>`:""}
      <div class="catalogue-toolbar"><h2>${window.TrainerI18n.t("dashboard.text_123")} <span class="section-count">${clients.length}</span></h2><div class="portal-meta">${window.TrainerI18n.t("learner.training.clients")}</div></div>
      <p class="caption gap-bottom">${window.TrainerI18n.t("dashboard.text_125")} ${esc(AUTH.user.display_name)}. ${window.TrainerI18n.t("dashboard.text_126")}</p>
      ${!canUseAI()?`<div class="notice amber gap-bottom"><p>${window.TrainerI18n.t("dashboard.text_101")}</p></div>`:""}${!companyReady?`<div class="notice amber gap-bottom">${icon("alert")}<p>${window.TrainerI18n.t("dashboard.text_102")}</p></div>`:""}
      <div class="scenario-grid">${clients.map((s,i)=>`<article class="card scenario-card"><div class="scenario-card-top"><span class="avatar tone-${i%3}">${esc(initials(s.customer_name))}</span><span class="scenario-number">${window.TrainerI18n.t("scenario.case_number",{number:String(i+1).padStart(2,"0")})}</span></div><h3>${esc(s.title)}</h3><div class="scenario-client">${esc(s.customer_name)}</div><p class="scenario-brief">${esc(s.public_brief)}</p><label>${window.TrainerI18n.t("training.language")}<select id="training-${esc(s.id)}" data-training-language>${(s.training_languages||[s.language]).map(lang=>`<option value="${lang}" ${lang===trainingLanguage(s)?"selected":""}>${esc(languageName(lang))}</option>`).join("")}</select></label><label>${window.TrainerI18n.t("dashboard.text_108")}<select id="persona-${esc(s.id)}">${(s.personas||[]).map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join("")}</select></label><div class="scenario-card-footer"><span class="caption">${esc(s.company_name||state.company?.name||window.TrainerI18n.t("dashboard.text_105"))}</span><button class="btn primary" data-action="start" data-id="${esc(s.id)}" ${!companyReady||state.starting||!canUseAI()?'disabled':""}>${state.starting===s.id?window.TrainerI18n.t("dashboard.text_089"):state.mode!=="demo"?window.TrainerI18n.t("dashboard.text_106"):window.TrainerI18n.t("dashboard.text_107")}${icon("arrow")}</button></div></article>`).join("")}</div>
      ${!clients.length?`<div class="card">${empty("book",window.TrainerI18n.t("dashboard.text_109"),window.TrainerI18n.t("dashboard.text_110"),window.TrainerI18n.t("dashboard.text_111"))}</div>`:""}
      `;

  }
  function historyPage() {
    const q=state.historySearch.toLowerCase();
    const sessions=state.sessions.filter(s=>(historyMatches(s,state.historyFilter))&&`${s.title} ${s.customer_name}`.toLowerCase().includes(q));
    return `${pageHead(window.TrainerI18n.t("dashboard.text_130"),window.TrainerI18n.t("dashboard.text_026"),window.TrainerI18n.t("dashboard.text_131"),'<a class="btn primary" href="#learner/practice">'+icon("plus")+(window.TrainerI18n.t("dashboard.text_132")+"</a>"))}<div class="toolbar"><div class="filter-tabs" role="group" aria-label="${window.TrainerI18n.t("dashboard.text_150")}">${[["all",T("all")],["active",T("active")],["ready",T("ready")],["submitted",T("submitted")],["reviewed",T("reviewed")],["certificates",T("certificates")],...(["finished"].includes(state.historyFilter)?[[state.historyFilter,T(state.historyFilter)]]:[])].map(([key,label])=>`<button class="filter-tab ${state.historyFilter===key?"active":""}" data-action="history-filter" data-filter="${key}" aria-pressed="${state.historyFilter===key}">${label} <span>${key==="certificates"?learning.certificateCount():state.sessions.filter(x=>historyMatches(x,key)&&`${x.title} ${x.customer_name}`.toLowerCase().includes(q)).length}</span></button>`).join("")}</div><span class="caption history-current-filter">${T(state.historyFilter)}</span><label class="search-box">${icon("search")}<span class="sr-only">${window.TrainerI18n.t("dashboard.text_151")}</span><input type="search" id="history-search" placeholder="${window.TrainerI18n.t("dashboard.text_152")}" value="${esc(state.historySearch)}" autocomplete="off"></label></div>${state.historyFilter==="certificates"?learning.certificates():`<div class="card table-wrap">${state.sessions.length?`<table class="data-table"><thead><tr><th>${window.TrainerI18n.t("dashboard.text_142")}</th><th>${window.TrainerI18n.t("dashboard.text_143")}</th><th>${window.TrainerI18n.t("dashboard.text_144")}</th><th>${window.TrainerI18n.t("dashboard.text_145")}</th><th><span class="sr-only">${window.TrainerI18n.t("dashboard.text_146")}</span></th></tr></thead><tbody>${sessions.map(s=>`<tr class="${learning.isNew(s.id)?'unread-review':''}"><td><span class="cell-title">${esc(s.title)}</span><span class="cell-sub">${esc(s.employee_name||s.customer_name)} · ${s.archived?window.TrainerI18n.t("dashboard.text_136"):""}${s.turn_count||0} ${plural(s.turn_count||0,[window.TrainerI18n.t("dashboard.text_137"),window.TrainerI18n.t("dashboard.text_138"),window.TrainerI18n.t("dashboard.text_139")])}</span></td><td class="nowrap">${date(s.created_at,true)}</td><td>${modePill(s.mode)}</td><td>${statusPill(s)}<span class="cell-sub">${window.TrainerI18n.t("ui16.ai_status")}: ${window.TrainerI18n.t("learning."+(s.analysis_status||"not_run"))}</span>${learning.isNew(s.id)?`<span class="pill amber">${T("new_review")}</span>`:""}</td><td><div class="table-actions"><a class="btn small-btn" href="#learner/session/${esc(s.id)}">${s.status==="active"?window.TrainerI18n.t("dashboard.text_013"):window.TrainerI18n.t("dashboard.text_140")}${icon("arrow")}</a></div></td></tr>`).join("")||("<tr><td class=\"empty-cell\" colspan=\"5\">"+window.TrainerI18n.t("dashboard.text_141")+"</td></tr>")}</tbody></table>`:empty("chat",window.TrainerI18n.t("dashboard.text_147"),window.TrainerI18n.t("dashboard.text_148"),("<a class=\"btn primary\" href=\"#learner/practice\">"+window.TrainerI18n.t("dashboard.text_149"))+icon("arrow")+'</a>')}</div>`}`;
  }
  function companyPage() {return learning.referencePage();}

  function stepper(phase) {
    const phases=["needs","capabilities","proposal"];const current=phase==="completed"?3:Math.max(0,phases.indexOf(phase));
    return `<div class="chat-stepper" aria-label="${window.TrainerI18n.t("dashboard.text_167")}">${phases.map((p,i)=>`<div class="chat-step ${i<current?"done":i===current?"current":""}" ${i===current?'aria-current="step"':""}><span class="chat-step-num">${i<current?icon("check"):i+1}</span><span>${PHASES[p]}</span></div>`).join("")}</div>`;
  }
  function messageHTML(message,session,transcript=false) {
    const learner=message.role==="learner";const name=learner?window.TrainerI18n.t("dashboard.text_168"):session.customer_name;
    return `<article class="message ${learner?"learner":"customer"}" ${transcript?`data-message-index="${session.messages.indexOf(message)}" data-transcript-turn="${Number(message.turn)||0}"`:""}><span class="avatar small-avatar">${learner?icon("user"):esc(initials(name))}</span><div class="message-content"><div class="message-author"><span>${esc(name)}</span>${message.at?`<time datetime="${esc(message.at)}">${time(message.at)}</time>`:""}${transcript&&learner?`<span>· ${window.TrainerI18n.t("dashboard.text_137")} ${Number(message.turn)||0}</span>`:""}</div><div class="message-bubble">${esc(message.text)}</div></div></article>`;
  }
  function chatPage(s) {return conversation.page(s);}
  function scrollChat() {requestAnimationFrame(()=>{const node=$("#chat-messages");if(node)node.scrollTop=node.scrollHeight;});}

  function overviewPage() {
    const waiting=state.reviews.filter(s=>s.review_status==="submitted");const c=state.company;
    return `${pageHead(window.TrainerI18n.t("dashboard.text_213"),window.TrainerI18n.t("dashboard.text_214"),window.TrainerI18n.t("dashboard.text_215"),'<a class="btn primary" href="#mentor/scenario/new">'+icon("plus")+(window.TrainerI18n.t("dashboard.text_216")+"</a>"))}<div class="stats-grid">${statCard("building",c?.reviewed?window.TrainerI18n.t("dashboard.text_217"):window.TrainerI18n.t("dashboard.text_218"),window.TrainerI18n.t("dashboard.text_219"),c?.name||window.TrainerI18n.t("dashboard.text_220"))}${statCard("book",state.scenarios.length,window.TrainerI18n.t("dashboard.text_221"),window.TrainerI18n.t("dashboard.text_222"))}${statCard("clipboard",waiting.length,window.TrainerI18n.t("dashboard.text_223"),window.TrainerI18n.t("dashboard.text_224"))}</div><div class="overview-grid"><section class="card"><div class="card-head"><h2>${window.TrainerI18n.t("dashboard.text_233")}</h2>${icon("target")}</div><div class="card-body"><ol class="setup-list"><li class="setup-item"><span class="setup-step">${c?.reviewed?icon("check"):"1"}</span><div><h4>${window.TrainerI18n.t("dashboard.text_234")}</h4><p>${window.TrainerI18n.t("dashboard.text_235")}</p><a class="text-link" href="#mentor/company">${c?.reviewed?window.TrainerI18n.t("dashboard.text_225"):window.TrainerI18n.t("dashboard.text_226")}${icon("arrow")}</a></div></li><li class="setup-item"><span class="setup-step">${state.scenarios.length?icon("check"):"2"}</span><div><h4>${window.TrainerI18n.t("dashboard.text_236")}</h4><p>${window.TrainerI18n.t("dashboard.text_237")}</p><a class="text-link" href="#mentor/scenarios">${window.TrainerI18n.t("dashboard.text_238")}${icon("arrow")}</a></div></li><li class="setup-item"><span class="setup-step">3</span><div><h4>${window.TrainerI18n.t("dashboard.text_239")}</h4><p>${window.TrainerI18n.t("dashboard.text_240")}</p><a class="text-link" href="#learner/practice">${window.TrainerI18n.t("dashboard.text_241")}${icon("arrow")}</a></div></li></ol></div></section><div><section class="card"><div class="card-head"><h2>${window.TrainerI18n.t("dashboard.text_242")}</h2><a class="text-link" href="#mentor/reviews">${window.TrainerI18n.t("dashboard.text_133")}${icon("arrow")}</a></div><div class="card-body">${waiting.length?`<div class="quiet-list">${waiting.slice(0,4).map(s=>`<div class="quiet-item"><span class="avatar small-avatar">${esc(initials(s.customer_name))}</span><div><h4>${esc(s.title)}</h4><p>${date(s.updated_at,true)} · ${modeLabel(s.mode)}</p></div><a class="btn small-btn" href="#mentor/review/${esc(s.id)}">${window.TrainerI18n.t("dashboard.text_227")}</a></div>`).join("")}</div>`:("<p class=\"small muted\">"+window.TrainerI18n.t("dashboard.text_228")+"</p>")}</div></section><section class="card card-pad gap-top"><div class="field-row-label"><h3>${window.TrainerI18n.t("dashboard.text_066")}</h3><span class="pill ${canUseAI()?"green":"amber"}">${canUseAI()?window.TrainerI18n.t("dashboard.text_229"):window.TrainerI18n.t("dashboard.text_230")}</span></div><p class="small muted">${canUseAI()?window.TrainerI18n.t("dashboard.text_231"):window.TrainerI18n.t("dashboard.text_232")}</p><a class="text-link" href="#mentor/setup">${window.TrainerI18n.t("dashboard.text_243")}${icon("arrow")}</a></section></div></div><div class="notice neutral gap-top">${icon("info")}<p>${window.TrainerI18n.t("dashboard.text_244")}</p></div>`;
  }
  function companyEditor() {
    const c=state.companyDraft||state.company;
    return `${pageHead(window.TrainerI18n.t("dashboard.text_245"),window.TrainerI18n.t("dashboard.text_246"),window.TrainerI18n.t("dashboard.text_247"),`<span class="pill ${c.reviewed?"green":"amber"}">${c.reviewed?window.TrainerI18n.t("dashboard.text_248"):window.TrainerI18n.t("dashboard.text_249")}</span>`)}<form id="company-form"><div class="form-layout"><div><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">01</span><h2>${window.TrainerI18n.t("dashboard.text_254")}</h2></div><div class="form-grid"><div class="form-field"><label for="company-name">${window.TrainerI18n.t("dashboard.text_255")} <span class="required-star">*</span></label><input id="company-name" name="name" type="text" maxlength="240" value="${esc(c.name)}" required></div><div class="form-field"><label for="company-source">${window.TrainerI18n.t("dashboard.text_256")}</label><input id="company-source" name="source_url" type="url" maxlength="2000" value="${esc(c.source_url)}" placeholder="https://company.de/services"><span class="field-hint">${window.TrainerI18n.t("dashboard.text_257")}</span></div><div class="form-field full"><label for="company-description">${window.TrainerI18n.t("dashboard.text_258")} <span class="required-star">*</span></label><textarea id="company-description" name="description" rows="6" maxlength="12000" required placeholder="${window.TrainerI18n.t("dashboard.text_259")}">${esc(c.description)}</textarea><span class="field-hint">${window.TrainerI18n.t("dashboard.text_260")}</span></div></div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">02</span><h2>${window.TrainerI18n.t("dashboard.text_261")}</h2></div><div id="service-rows">${c.services.map((service,i)=>serviceEditor(service,i)).join("")}</div><button class="btn soft small-btn" type="button" data-action="add-service" ${c.services.length>=20?'disabled':""}>${icon("plus")}${window.TrainerI18n.t("dashboard.text_262")}</button></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">03</span><h2>${window.TrainerI18n.t("dashboard.text_263")}</h2></div><div class="form-field"><label for="company-limitations">${window.TrainerI18n.t("dashboard.text_264")} <span class="required-star">*</span></label><textarea id="company-limitations" name="limitations" rows="4" maxlength="5000" required placeholder="${window.TrainerI18n.t("dashboard.text_265")}">${esc(c.limitations)}</textarea></div><label class="checkbox-line checkbox-panel"><input type="checkbox" id="company-reviewed" name="reviewed" ${c.reviewed?"checked":""}><span><strong>${window.TrainerI18n.t("dashboard.text_266")}</strong><small>${window.TrainerI18n.t("dashboard.text_267")}</small></span></label></section>${state.formError?`<div class="form-error" role="alert">${esc(state.formError)}</div>`:""}<div class="editor-savebar"><p class="draft-label">${state.companyDirty?window.TrainerI18n.t("dashboard.text_250"):window.TrainerI18n.t("a20.all_saved")}</p><button class="btn primary" type="submit" ${state.saving||!state.companyDirty?'disabled':""}>${icon("save")}${state.saving?window.TrainerI18n.t("dashboard.text_252"):window.TrainerI18n.t("dashboard.text_253")}</button></div></div><aside class="form-aside"><section class="card card-pad"><div class="aside-title">${window.TrainerI18n.t("dashboard.text_268")}</div><div class="aside-step"><span>01</span><div><strong>${window.TrainerI18n.t("dashboard.text_269")}</strong><p>${window.TrainerI18n.t("dashboard.text_270")}</p></div></div><div class="aside-step"><span>02</span><div><strong>${window.TrainerI18n.t("dashboard.text_271")}</strong><p>${window.TrainerI18n.t("dashboard.text_272")}</p></div></div><div class="aside-step"><span>03</span><div><strong>${window.TrainerI18n.t("dashboard.text_273")}</strong><p>${window.TrainerI18n.t("dashboard.text_274")}</p></div></div></section><div class="notice amber">${icon("info")}<p>${window.TrainerI18n.t("dashboard.text_275")}</p></div><div class="version-line">${icon("history")}${window.TrainerI18n.t("dashboard.text_276")}</div></aside></div></form>`;
  }
  function serviceEditor(service,i) {
    return `<fieldset class="service-row" data-service-id="${esc(service.id)}"><legend>${window.TrainerI18n.t("dashboard.text_278")} ${i+1}</legend><div class="nested-card-head"><strong>${esc(service.title||window.TrainerI18n.t("dashboard.text_277"))}</strong><button class="btn ghost danger" type="button" data-action="remove-service" data-index="${i}" aria-label="${window.TrainerI18n.t("dashboard.text_279")} ${i+1}" ${state.companyDraft?.services.length<=1?'disabled':""}>${icon("trash")}</button></div><div class="form-field"><label for="service-title-${i}">${window.TrainerI18n.t("dashboard.text_255")} <span class="required-star">*</span></label><input id="service-title-${i}" type="text" data-field="title" maxlength="240" value="${esc(service.title)}" required placeholder="${window.TrainerI18n.t("dashboard.text_280")}"></div><div class="form-field"><label for="service-description-${i}">${window.TrainerI18n.t("dashboard.text_281")} <span class="required-star">*</span></label><textarea id="service-description-${i}" class="compact" data-field="description" maxlength="3000" rows="2" required>${esc(service.description)}</textarea></div><div class="form-field"><label for="service-conditions-${i}">${window.TrainerI18n.t("dashboard.text_282")}</label><textarea id="service-conditions-${i}" class="compact" data-field="conditions" maxlength="3000" rows="2" placeholder="${window.TrainerI18n.t("dashboard.text_283")}">${esc(service.conditions)}</textarea></div></fieldset>`;
  }
  function readCompanyForm() {
    const form=$("#company-form");if(!form)return state.companyDraft;
    const original=state.companyDraft||state.company;
    return {id:original.id,revision:original.revision,name:$("#company-name",form).value,description:$("#company-description",form).value,source_url:$("#company-source",form).value,limitations:$("#company-limitations",form).value,reviewed:$("#company-reviewed",form).checked,services:$$(".service-row",form).map(row=>({id:row.dataset.serviceId,title:$("[data-field=title]",row).value,description:$("[data-field=description]",row).value,conditions:$("[data-field=conditions]",row).value}))};
  }
  function blankScenario() {
    const facts=[
      ["situation","needs",window.TrainerI18n.t("dashboard.text_284"),[window.TrainerI18n.t("dashboard.text_285"),window.TrainerI18n.t("dashboard.text_286"),window.TrainerI18n.t("dashboard.text_287")]],
      ["goal","needs",window.TrainerI18n.t("dashboard.text_288"),[window.TrainerI18n.t("dashboard.text_289"),window.TrainerI18n.t("dashboard.text_290"),window.TrainerI18n.t("dashboard.text_291")]],
      ["reason","needs",window.TrainerI18n.t("dashboard.text_292"),[window.TrainerI18n.t("dashboard.text_293"),window.TrainerI18n.t("dashboard.text_294"),window.TrainerI18n.t("dashboard.text_295")]],
      ["priority","needs",window.TrainerI18n.t("dashboard.text_296"),[window.TrainerI18n.t("dashboard.text_297"),window.TrainerI18n.t("dashboard.text_298")]],
      ["budget","capabilities",window.TrainerI18n.t("dashboard.text_299"),[window.TrainerI18n.t("dashboard.text_300"),window.TrainerI18n.t("dashboard.text_301"),window.TrainerI18n.t("dashboard.text_302")]],
      ["timing","capabilities",window.TrainerI18n.t("dashboard.text_303"),[window.TrainerI18n.t("dashboard.text_304"),window.TrainerI18n.t("dashboard.text_305"),window.TrainerI18n.t("dashboard.text_306")]],
      ["decision","capabilities",window.TrainerI18n.t("dashboard.text_307"),[window.TrainerI18n.t("dashboard.text_308"),window.TrainerI18n.t("dashboard.text_309"),window.TrainerI18n.t("dashboard.text_310")]]
    ].map(([id,stage,label,keywords])=>({id,stage,label,keywords,value:"",status:"known",required:true,material:true}));
    return {id:"",revision:1,company_id:state.company.id,title:"",customer_name:"",public_brief:"",opening:"",language:"ru",facts,allowed_outcomes:[],question_hints:[window.TrainerI18n.t("dashboard.text_644"),window.TrainerI18n.t("dashboard.text_195"),window.TrainerI18n.t("dashboard.text_645"),window.TrainerI18n.t("dashboard.text_646"),window.TrainerI18n.t("dashboard.text_647"),window.TrainerI18n.t("dashboard.text_648"),window.TrainerI18n.t("dashboard.text_649")]};
  }
  function pairAssignments() {
    return `<section class="card card-pad gap-top"><h2>${window.TrainerI18n.t("dashboard.text_312")}</h2><p>${window.TrainerI18n.t("dashboard.text_313")}</p>${state.scenarios.map(sc=>{const a=state.pairs?.assignments.find(a=>a.scenario_id===sc.id);return `<fieldset id="pair-${esc(sc.id)}"><legend>${esc(state.materials?.scenarios[sc.id]?.title||sc.title)}</legend>${(state.pairs?.profiles||[]).filter(p=>p.available).map(p=>`<label><input type="checkbox" value="${esc(p.id)}" ${a?.profile_ids.includes(p.id)?"checked":""}> ${esc(state.materials?.persona_labels[p.id]||p.name)}</label>`).join("")}<button class="btn small-btn" data-action="save-pair" data-id="${esc(sc.id)}">${window.TrainerI18n.t("dashboard.text_311")}</button></fieldset>`}).join("")}</section>`;
  }
  function scenariosPage() {
    const q=state.scenarioSearch.toLowerCase();const scenarios=state.scenarios.map(s=>({...s,...state.materials?.scenarios[s.id]})).filter(s=>`${s.title} ${s.customer_name}`.toLowerCase().includes(q));
    return `${pageHead(window.TrainerI18n.t("dashboard.text_314"),window.TrainerI18n.t("dashboard.text_315"),window.TrainerI18n.t("dashboard.text_316"),'<a class="btn primary" href="#mentor/scenario/new">'+icon("plus")+(window.TrainerI18n.t("dashboard.text_317")+"</a>"))}<div class="toolbar"><div class="caption">${state.scenarios.length} ${plural(state.scenarios.length,[window.TrainerI18n.t("dashboard.text_318"),window.TrainerI18n.t("dashboard.text_319"),window.TrainerI18n.t("dashboard.text_320")])} · ${window.TrainerI18n.t("dashboard.text_331")}</div><span class="caption history-current-filter">${T(state.historyFilter)}</span><label class="search-box">${icon("search")}<span class="sr-only">${window.TrainerI18n.t("dashboard.text_332")}</span><input id="scenario-search" type="search" value="${esc(state.scenarioSearch)}" placeholder="${window.TrainerI18n.t("dashboard.text_333")}" autocomplete="off"></label></div><div class="card table-wrap">${state.scenarios.length?`<table class="data-table"><thead><tr><th>${window.TrainerI18n.t("dashboard.text_326")}</th><th>${window.TrainerI18n.t("dashboard.text_327")}</th><th>${window.TrainerI18n.t("clean.technical")}</th><th><span class="sr-only">${window.TrainerI18n.t("dashboard.text_328")}</span></th></tr></thead><tbody>${scenarios.map(s=>`<tr><td><span class="cell-title">${esc(s.title)}</span><span class="cell-sub">${esc(s.customer_name)} · ${s.language==="de"?window.TrainerI18n.t("dashboard.text_321"):window.TrainerI18n.t("dashboard.text_192")}</span></td><td><span class="cell-title">${s.facts.filter(f=>f.stage==="needs").length} + ${s.facts.filter(f=>f.stage==="capabilities").length} ${window.TrainerI18n.t("dashboard.text_322")}</span><span class="cell-sub">${window.TrainerI18n.t("dashboard.text_323")}</span></td><td><details><summary>${window.TrainerI18n.t("clean.details")}</summary><p>ID: ${esc(s.id)} · v${s.revision}</p></details></td><td><div class="table-actions"><a class="btn small-btn" href="#mentor/scenario/${esc(s.id)}">${icon("edit")}${window.TrainerI18n.t("dashboard.text_055")}</a><button class="btn ghost icon-only danger" data-action="delete-scenario" data-id="${esc(s.id)}" aria-label="${window.TrainerI18n.t("dashboard.text_324")} ${esc(s.title)}">${icon("trash")}</button></div></td></tr>`).join("")||("<tr><td class=\"empty-cell\" colspan=\"4\">"+window.TrainerI18n.t("dashboard.text_325")+"</td></tr>")}</tbody></table>`:empty("book",window.TrainerI18n.t("dashboard.text_329"),window.TrainerI18n.t("dashboard.text_330"),'<a class="btn primary" href="#mentor/scenario/new">'+icon("plus")+(window.TrainerI18n.t("dashboard.text_317")+"</a>"))}</div><div class="notice neutral gap-top">${icon("lock")}<p>${window.TrainerI18n.t("dashboard.text_334")}</p></div>${pairAssignments()}`;
  }
  function scenarioEditor() {
    const s=state.scenarioDraft;const isNew=!s.id;
    return `${pageHead(window.TrainerI18n.t("dashboard.text_335"),isNew?window.TrainerI18n.t("dashboard.text_336"):s.title,window.TrainerI18n.t("dashboard.text_337"),'<a class="btn" href="#mentor/scenarios">'+icon("back")+(window.TrainerI18n.t("dashboard.text_338")+"</a>"))}<form id="scenario-form"><div class="form-layout"><div><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">01</span><h2>${window.TrainerI18n.t("dashboard.text_341")}</h2></div><div class="form-grid"><div class="form-field full"><label for="scenario-title">${window.TrainerI18n.t("dashboard.text_342")} <span class="required-star">*</span></label><input id="scenario-title" name="title" type="text" maxlength="240" value="${esc(s.title)}" placeholder="${window.TrainerI18n.t("dashboard.text_343")}" required></div><div class="form-field"><label for="customer-name">${window.TrainerI18n.t("dashboard.text_344")} <span class="required-star">*</span></label><input id="customer-name" type="text" maxlength="240" value="${esc(s.customer_name)}" required></div><div class="form-field"><label for="scenario-language">${window.TrainerI18n.t("dashboard.text_345")}</label><select id="scenario-language"><option value="ru" ${s.language==="ru"?"selected":""}>${window.TrainerI18n.t("dashboard.text_192")}</option><option value="en" ${s.language==="en"?"selected":""}>English</option><option value="de" ${s.language==="de"?"selected":""}>${window.TrainerI18n.t("dashboard.text_321")}</option></select></div><div class="form-field full"><label for="public-brief">${window.TrainerI18n.t("dashboard.text_346")} <span class="required-star">*</span></label><textarea id="public-brief" rows="3" maxlength="3000" required>${esc(s.public_brief)}</textarea><span class="field-hint">${window.TrainerI18n.t("dashboard.text_347")}</span></div><div class="form-field full"><label for="scenario-opening">${window.TrainerI18n.t("dashboard.text_348")} <span class="required-star">*</span></label><textarea id="scenario-opening" rows="2" class="compact" maxlength="2000" placeholder="${window.TrainerI18n.t("dashboard.text_349")}" required>${esc(s.opening)}</textarea></div></div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">02</span><h2>${window.TrainerI18n.t("dashboard.text_350")}</h2></div><div class="private-note">${icon("lock")}${window.TrainerI18n.t("dashboard.text_351")}</div><p class="small muted gap-bottom">${window.TrainerI18n.t("dashboard.text_352")}</p><div id="fact-rows">${s.facts.map((fact,i)=>factEditor(fact,i)).join("")}</div><div class="actions"><button class="btn soft small-btn" type="button" data-action="add-fact" data-stage="needs" ${s.facts.length>=20?'disabled':""}>${icon("plus")}${window.TrainerI18n.t("dashboard.text_353")}</button><button class="btn soft small-btn" type="button" data-action="add-fact" data-stage="capabilities" ${s.facts.length>=20?'disabled':""}>${icon("plus")}${window.TrainerI18n.t("dashboard.text_354")}</button></div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">03</span><h2>${window.TrainerI18n.t("dashboard.text_355")}</h2></div><p class="small muted">${window.TrainerI18n.t("dashboard.text_356")}</p><div class="outcomes-grid">${[...(state.company?.services||[]).map(service=>({id:service.id,title:service.title,description:service.conditions||service.description})),{id:"no_fit",title:window.TrainerI18n.t("dashboard.text_650"),description:window.TrainerI18n.t("dashboard.text_651")}].map(outcome=>`<label class="checkbox-line outcome-option"><input type="checkbox" name="outcome" value="${esc(outcome.id)}" ${s.allowed_outcomes.includes(outcome.id)?"checked":""}><span><strong>${esc(outcome.title)}</strong><small>${esc(outcome.description)}</small></span></label>`).join("")}</div></section><section class="card card-pad form-section"><div class="form-section-title"><span class="section-index">04</span><h2>${window.TrainerI18n.t("dashboard.text_357")}</h2></div><div class="form-field"><label for="question-hints">${window.TrainerI18n.t("dashboard.text_358")}</label><textarea id="question-hints" rows="7" maxlength="15000">${esc(s.question_hints.join("\n"))}</textarea><span class="field-hint">${window.TrainerI18n.t("dashboard.text_359")}</span></div></section>${state.formError?`<div class="form-error" role="alert">${esc(state.formError)}</div>`:""}<div class="editor-savebar"><p class="draft-label">${state.scenarioDirty?window.TrainerI18n.t("dashboard.text_250"):isNew?window.TrainerI18n.t("dashboard.text_339"):T("saved")}</p><button class="btn primary" type="submit" ${state.saving?'disabled':""}>${icon("save")}${state.saving?window.TrainerI18n.t("dashboard.text_252"):window.TrainerI18n.t("dashboard.text_340")}</button></div></div><aside class="form-aside"><section class="card card-pad"><div class="aside-title">${window.TrainerI18n.t("dashboard.text_360")}</div><div class="aside-step"><span>01</span><div><strong>${window.TrainerI18n.t("dashboard.text_094")}</strong><p>${window.TrainerI18n.t("dashboard.text_361")}</p></div></div><div class="aside-step"><span>02</span><div><strong>${window.TrainerI18n.t("dashboard.text_096")}</strong><p>${window.TrainerI18n.t("dashboard.text_362")}</p></div></div><div class="aside-step"><span>03</span><div><strong>${window.TrainerI18n.t("dashboard.text_098")}</strong><p>${window.TrainerI18n.t("dashboard.text_363")}</p></div></div></section><section class="card card-pad"><div class="aside-title">${window.TrainerI18n.t("dashboard.text_364")}</div><p class="small muted">${window.TrainerI18n.t("dashboard.text_365")}</p></section><div class="notice neutral">${icon("history")}<p>${window.TrainerI18n.t("dashboard.text_366")}</p></div></aside></div></form>`;
  }
  function factEditor(fact,i) {
    const na=fact.status==="not_applicable";
    const required=Boolean(fact.required&&!na);const material=required||(fact.material??true);
    return `<fieldset class="fact-row" data-fact-id="${esc(fact.id)}"><legend>${window.TrainerI18n.t("dashboard.text_367")} ${i+1}</legend><div class="nested-card-head"><span class="pill ${fact.stage==="needs"?"green":"amber"}">${fact.stage==="needs"?window.TrainerI18n.t("dashboard.text_094"):window.TrainerI18n.t("dashboard.text_096")}</span><button class="btn ghost danger" type="button" data-action="remove-fact" data-index="${i}" aria-label="${window.TrainerI18n.t("dashboard.text_368")} ${i+1}" ${state.scenarioDraft.facts.length<=2?'disabled':""}>${icon("trash")}</button></div><div class="form-grid"><div class="form-field"><label for="fact-label-${i}">${window.TrainerI18n.t("dashboard.text_369")} <span class="required-star">*</span></label><input id="fact-label-${i}" type="text" data-field="label" maxlength="240" value="${esc(fact.label)}" required></div><div class="form-field"><label for="fact-stage-${i}">${window.TrainerI18n.t("dashboard.text_370")}</label><select id="fact-stage-${i}" data-field="stage"><option value="needs" ${fact.stage==="needs"?"selected":""}>${window.TrainerI18n.t("dashboard.text_094")}</option><option value="capabilities" ${fact.stage==="capabilities"?"selected":""}>${window.TrainerI18n.t("dashboard.text_096")}</option></select></div><div class="form-field full"><label for="fact-status-${i}">${window.TrainerI18n.t("dashboard.text_371")}</label><select id="fact-status-${i}" data-field="status">${Object.entries(KNOWLEDGE).map(([key,label])=>`<option value="${key}" ${fact.status===key?"selected":""}>${label}</option>`).join("")}</select></div><div class="form-field full"><label for="fact-value-${i}">${window.TrainerI18n.t("dashboard.text_372")} <span class="required-star">*</span></label><textarea id="fact-value-${i}" data-field="value" rows="3" maxlength="2000" required placeholder="${window.TrainerI18n.t("dashboard.text_373")}">${esc(fact.value)}</textarea></div><div class="form-field full"><label for="fact-keywords-${i}">${window.TrainerI18n.t("dashboard.text_374")}</label><input id="fact-keywords-${i}" type="text" data-field="keywords" maxlength="2500" value="${esc(fact.keywords.join(", "))}" placeholder="${window.TrainerI18n.t("dashboard.text_375")}"><span class="field-hint">${window.TrainerI18n.t("dashboard.text_376")}</span></div><div class="form-field full"><label class="checkbox-line"><input type="checkbox" data-field="required" ${required?"checked":""} ${na?"disabled":""}><span>${window.TrainerI18n.t("dashboard.text_377")}</span></label></div><div class="form-field full"><label class="checkbox-line"><input type="checkbox" data-field="material" aria-describedby="fact-material-hint-${i}" ${material?"checked":""} ${required?"disabled":""}><span>${window.TrainerI18n.t("dashboard.text_378")}</span></label><span class="field-hint" id="fact-material-hint-${i}">${window.TrainerI18n.t("dashboard.text_379")}</span></div></div></fieldset>`;
  }
  function readScenarioForm() {
    const form=$("#scenario-form");if(!form)return state.scenarioDraft;
    const original=state.scenarioDraft;
    return {id:original.id,revision:original.revision,company_id:original.company_id,title:$("#scenario-title",form).value,customer_name:$("#customer-name",form).value,public_brief:$("#public-brief",form).value,opening:$("#scenario-opening",form).value,language:$("#scenario-language",form).value,
      facts:$$(".fact-row",form).map(row=>{
        const status=$("[data-field=status]",row).value;const required=$("[data-field=required]",row).checked&&status!=="not_applicable";
        return {id:row.dataset.factId,stage:$("[data-field=stage]",row).value,label:$("[data-field=label]",row).value,value:$("[data-field=value]",row).value,status,keywords:$("[data-field=keywords]",row).value.split(",").map(x=>x.trim()).filter(Boolean),required,material:required||($("[data-field=material]",row)?.checked??true)};
      }),
      allowed_outcomes:$$("input[name=outcome]:checked",form).map(node=>node.value),question_hints:$("#question-hints",form).value.split("\n").map(x=>x.trim()).filter(Boolean)};
  }
  function reviewsPage() {
    const sessions=state.reviews.filter(s=>(state.reviewFilter==="all"||s.review_status===state.reviewFilter)&&(!state.reviewEmployee||s.employee_id===state.reviewEmployee)&&(!state.reviewScenario||s.scenario_id===state.reviewScenario));
    return `${pageHead(window.TrainerI18n.t("dashboard.text_380"),window.TrainerI18n.t("dashboard.text_023"),window.TrainerI18n.t("dashboard.text_381"))}<div class="actions gap-bottom"><label>${window.TrainerI18n.t("learning.employee")}<select id="review-employee-filter"><option value="">—</option>${[...new Map(state.reviews.map(x=>[x.employee_id,x.employee_name])).entries()].map(([id,n])=>`<option value="${esc(id||"")}" ${state.reviewEmployee===id?"selected":""}>${esc(n)}</option>`).join("")}</select></label><label>${window.TrainerI18n.t("learning.scenario")}<select id="review-scenario-filter"><option value="">—</option>${[...new Map(state.reviews.map(x=>[x.scenario_id,x.title])).entries()].map(([id,n])=>`<option value="${esc(id)}" ${state.reviewScenario===id?"selected":""}>${esc(n)}</option>`).join("")}</select></label></div><div class="toolbar"><div class="filter-tabs" role="group" aria-label="${window.TrainerI18n.t("dashboard.text_386")}">${[["submitted",window.TrainerI18n.t("dashboard.text_223")],["reviewed",window.TrainerI18n.t("dashboard.text_135")],["all",window.TrainerI18n.t("dashboard.text_133")]].map(([key,label])=>`<button class="filter-tab ${state.reviewFilter===key?"active":""}" data-action="review-filter" data-filter="${key}" aria-pressed="${state.reviewFilter===key}">${label}${key==="submitted"?` · ${state.reviews.filter(s=>s.review_status==="submitted").length}`:""}</button>`).join("")}</div><button class="btn ghost small-btn" data-action="reload">${icon("refresh")}${window.TrainerI18n.t("dashboard.text_387")}</button></div><div class="card table-wrap">${sessions.length?`<table class="data-table"><thead><tr><th>${window.TrainerI18n.t("dashboard.text_383")}</th><th>${window.TrainerI18n.t("learning.employee")}</th><th>${window.TrainerI18n.t("dashboard.text_143")}</th><th>${window.TrainerI18n.t("dashboard.text_144")}</th><th>${window.TrainerI18n.t("dashboard.text_145")}</th><th><span class="sr-only">${window.TrainerI18n.t("dashboard.text_146")}</span></th></tr></thead><tbody>${sessions.map(s=>`<tr><td><span class="cell-title">${esc(s.title)}</span><span class="cell-sub">${esc(s.customer_name)} · ${s.turn_count||0} ${plural(s.turn_count||0,[window.TrainerI18n.t("dashboard.text_137"),window.TrainerI18n.t("dashboard.text_138"),window.TrainerI18n.t("dashboard.text_139")])}</span></td><td>${esc(s.employee_name||"—")}</td><td class="nowrap">${date(s.updated_at,true)}</td><td>${modePill(s.mode)}</td><td>${statusPill(s)}</td><td><div class="table-actions"><a class="btn small-btn ${s.review_status==="submitted"?"primary":""}" href="#mentor/review/${esc(s.id)}">${s.review_status==="submitted"?window.TrainerI18n.t("dashboard.text_218"):window.TrainerI18n.t("dashboard.text_382")}${icon("arrow")}</a></div></td></tr>`).join("")}</tbody></table>`:empty("clipboard",window.TrainerI18n.t("dashboard.text_384"),window.TrainerI18n.t("dashboard.text_385"))}</div>`;
  }
  function setupPage(){const a=state.status.ai;return `${pageHead(window.TrainerI18n.t("dashboard.text_388"),window.TrainerI18n.t("dashboard.text_024"),window.TrainerI18n.t("clean.connection_help"))}<section class="card card-pad"><h2>${window.TrainerI18n.t("dashboard.text_002")}</h2><p>${canUseAI()?window.TrainerI18n.t("clean.available"):window.TrainerI18n.t("clean.unavailable")}</p><p>${window.TrainerI18n.t("clean.mentor_hint")}</p><h3>${window.TrainerI18n.t("dashboard.text_397")}</h3><p>${a.transcription?.configured?window.TrainerI18n.t("clean.available"):window.TrainerI18n.t("clean.unavailable")} ${window.TrainerI18n.t("dashboard.text_399")}</p><details><summary>${window.TrainerI18n.t("clean.technical")}</summary><p>${window.TrainerI18n.t("dashboard.text_394")} ${esc(a.model)} · ${esc(state.status.version)}</p><p>${window.TrainerI18n.t("dashboard.text_396")}</p><p>${window.TrainerI18n.t("dashboard.text_394")} ${esc(a.transcription?.model||"—")}</p><button class="btn small-btn" data-action="voice-diagnostics">${window.TrainerI18n.t("dashboard.text_400")}</button><pre id="voice-diagnostics-result" class="studio-preview"></pre><h3>${window.TrainerI18n.t("dashboard.text_401")}</h3><p>${window.TrainerI18n.t("dashboard.text_402")} <code>scripts/local_installation.py key</code>; ${window.TrainerI18n.t("dashboard.text_403")}</p><p>${window.TrainerI18n.t("dashboard.text_404")}</p></details></section>`;}

  function outcomeLabel(session, outcome) {
    if(!outcome)return window.TrainerI18n.t("dashboard.text_405");
    if(outcome==="no_fit")return window.TrainerI18n.t("dashboard.text_406");
    return (session.company?.services||[]).find(service=>service.id===outcome)?.title || window.TrainerI18n.t("dashboard.text_174");
  }
  function findingLabel(type) {
    return ({early_proposal:window.TrainerI18n.t("dashboard.text_652"),premature_offer:window.TrainerI18n.t("dashboard.text_652"),premature_offer_detected:window.TrainerI18n.t("dashboard.text_652"),summary_rejected:window.TrainerI18n.t("dashboard.text_653"),summary_incomplete:window.TrainerI18n.t("dashboard.text_654"),summary_confirmed:window.TrainerI18n.t("dashboard.text_655"),needs_confirmed:window.TrainerI18n.t("dashboard.text_656"),capabilities_confirmed:window.TrainerI18n.t("dashboard.text_657"),proposal_rejected:window.TrainerI18n.t("dashboard.text_658"),proposal_accepted:window.TrainerI18n.t("dashboard.text_174"),uncertain:window.TrainerI18n.t("dashboard.text_659"),question_unmatched:window.TrainerI18n.t("dashboard.text_660"),fact_disclosed:window.TrainerI18n.t("dashboard.text_661"),invalid_evidence:window.TrainerI18n.t("dashboard.text_662"),unsupported_proposal:window.TrainerI18n.t("dashboard.text_663"),outcome_accepted:window.TrainerI18n.t("dashboard.text_664")})[type] || window.TrainerI18n.t("dashboard.text_407");
  }
  const REVIEW_STAGES=["needs","capabilities","proposal"];
  const REVIEW_RATINGS=["not_reviewed","completed","partial","not_completed"];
  const COMMERCIAL_OUTCOMES=["no_next_step","interested","diagnosis_tentative","visit_confirmed","repair_agreed","service_unavailable","customer_declined","order_confirmed","tentative_agreement","deferred_decision"];
  const COMPANY_FIT=["not_checked","within_scope","outside_scope","uncertain"];
  const reviewText=key=>window.TrainerI18n.t("review."+key);
  function stageRating(stage,s){
    return s.mode==="simple_actor"?reviewText("rating."+(stage.rating||"not_reviewed")):(stage.confirmed?window.TrainerI18n.t("dashboard.text_419"):window.TrainerI18n.t("dashboard.text_420"));
  }
  function reviewControls(s,report){
    const draft=state.learningDrafts?.[s.id]||s.decision_draft;
    const a=state.assessmentDrafts?.[s.id]||(draft?.assessment?.stages?draft.assessment:null)||report.assessment;
    const choices=(values,value,prefix)=>values.map(x=>`<option value="${x}" ${value===x?'selected':''}>${esc(reviewText(prefix+x))}</option>`).join("");
    return `<div class="mentor32-assessment">${REVIEW_STAGES.map((id,i)=>`<div><label for="review-${id}">${esc(window.TrainerI18n.systemText(report.stages[i].label))}</label><select id="review-${id}">${choices(REVIEW_RATINGS,a.stages[id],"rating.")}</select></div>`).join("")}
      <div><label for="review-commercial">${reviewText("commercial")}</label><select id="review-commercial"><option value="">${reviewText("unset")}</option>${choices(COMMERCIAL_OUTCOMES,a.commercial_outcome,"outcome.")}</select></div>
      <div><label for="review-fit">${reviewText("company_fit")}</label><select id="review-fit">${choices(COMPANY_FIT,a.company_fit,"fit.")}</select></div></div>`;
  }
  function reportPage(s, mentor) {
    if(!mentor)return learning.employeeReport(s,{messageHTML});
    return learning.mentorReport(s,{reviewControls,messageHTML});
  }

  async function startSession(id, mode=state.mode) {
    if(state.starting)return;
    if(!["demo","openai","simple_actor"].includes(mode))return;
    if(mode!=="demo"&&!canUseAI()) {toast(window.TrainerI18n.t("dashboard.text_471"),true);return;}
    const profileId=document.getElementById(`persona-${id}`)?.value||state.session?.client_profile?.id;
    const trainingLanguage=document.getElementById(`training-${id}`)?.value||state.session?.training_language;
    const generation=state.generation;state.starting=id;render();
    try {const result=await api("/api/sessions",{method:"POST",body:{scenario_id:id,mode,client_profile_id:profileId,training_language:trainingLanguage||null}});state.starting=null;if(generation===state.generation){state.session=result.session;go(`learner/session/${result.session.id}`);}else toast(window.TrainerI18n.t("dashboard.text_472"));}
    catch(error){state.starting=null;if(generation===state.generation)render();toast(error.message,true);}
  }
  async function sendMessage() {
    if(window.TrainerVoice.busy()){toast(window.TrainerI18n.t("dashboard.text_473"),true);return;}
    const session=state.session;if(!session||session.status!=="active")return;
    const draft=draftFor(session.id);if(draft.sending)return;
    const field=$("#message-text");if(field)draft.text=field.value;
    const text=draft.text.trim();if(!text)return;
    if(text.length>6000){toast(window.TrainerI18n.t("dashboard.text_474"),true);return;}
    if(!draft.pending||draft.pending.text!==text||draft.pending.kind!==draft.kind)draft.pending={text,kind:draft.kind,request_id:uid(),version:session.version};
    const payload={...draft.pending,kind:"message"};draft.sending=true;draft.error=null;render();scrollChat();
    try {
      const result=await api(`/api/sessions/${encodeURIComponent(session.id)}/messages`,{method:"POST",body:payload});
      draft.sending=false;draft.text="";draft.pending=null;draft.error=null;
      if(result.session.phase!==session.phase)draft.kind="message";
      if(state.session?.id===session.id)state.session=result.session;
      state.reviews=state.reviews.map(x=>x.id===session.id?{...x,review_status:result.session.review_status,reviewed_at:result.session.reviewed_at}:x);
      if(state.route.role==="learner"&&state.route.view==="session"&&state.route.id===session.id){render();scrollChat();requestAnimationFrame(()=>$("#message-text")?.focus());}
    } catch(error) {
      draft.sending=false;draft.error=error.message;
      if(error.status===409) {
        try {const result=await api(`/api/sessions/${encodeURIComponent(session.id)}`);if(state.session?.id===session.id)state.session=result.session;
      state.reviews=state.reviews.map(x=>x.id===session.id?{...x,review_status:result.session.review_status,reviewed_at:result.session.reviewed_at}:x);draft.pending=null;draft.error=`${error.message} ${window.TrainerI18n.t("dashboard.text_475")}`;} catch(_) {}
      }
      if(state.route.role==="learner"&&state.route.view==="session"&&state.route.id===session.id){render();scrollChat();requestAnimationFrame(()=>$("#message-text")?.focus());} else toast(error.message,true);
    }
  }
  async function finishSession() {
    const session=state.session;if(!session||session.status!=="active"||draftFor(session.id).sending)return;
    if(window.TrainerVoice.busy()&&!window.confirm(window.TrainerI18n.t("dictation18.leave")))return;
    if(session.phase!=="completed") {
      const accepted=await confirmDialog(window.TrainerI18n.t("dashboard.text_476"),window.TrainerI18n.t("dashboard.text_477"),window.TrainerI18n.t("dashboard.text_170"));
      if(!accepted)return;
    }
    window.TrainerVoice.cancel();
    try {const result=await api(`/api/sessions/${encodeURIComponent(session.id)}/finish`,{method:"POST"});state.session=result.session;render();window.scrollTo({top:0,behavior:"smooth"});}
    catch(error){toast(error.message,true);}
  }
  async function submitReview() {
    if(state.saving)return;state.saving=true;render();
    try {const result=await api(`/api/sessions/${encodeURIComponent(state.session.id)}/submit`,{method:"POST"});state.session=result.session;state.saving=false;render();toast(window.TrainerI18n.t("dashboard.text_478"));}
    catch(error){state.saving=false;render();toast(error.message,true);}
  }
  async function saveReview() {
    if(state.saving||state.session?.published_review||state.session?.review_status==='reviewed'||learning.mentorVoiceBusy())return;
    const session=state.session;
    learning.cancelMentorVoice();
    if(!$("#review-note")?.value.trim())return;
    state.saving=true;
    try {
      const pending=learning.saveDraft();render();
      const draft=await pending;
      state.noteDrafts[session.id]=draft.note;
      render();
      const body={note:draft.note,...(session.mode==="simple_actor"?{assessment:draft.assessment}:{})};
      const result=await api(`/api/mentor/reviews/${encodeURIComponent(session.id)}`,{method:"POST",body,mentor:true});
      adoptPublishedReview(session.id,result.session);
      toast(window.TrainerI18n.t("dashboard.text_479"));
    } catch(error) {
      // A lost response must be reconciled by reading, never by auto-reposting feedback.
      let published=false;
      try{const fresh=await api(`/api/mentor/reviews/${encodeURIComponent(session.id)}`,{mentor:true});
        if(fresh.session.published_review||fresh.session.review_status==='reviewed'){adoptPublishedReview(session.id,fresh.session);published=true;}
      }catch(_){}
      toast(published?window.TrainerI18n.t('mentor33.published'):error.message,!published);
    }
    finally {state.saving=false;render();}
  }
  function adoptPublishedReview(id,session){
    if(state.session?.id===id)state.session=session;
    state.reviews=state.reviews.map(x=>x.id===id?{...x,review_status:session.review_status,reviewed_at:session.reviewed_at}:x);
    delete state.assessmentDrafts?.[id];delete state.learningDrafts?.[id];delete state.noteDrafts[id];
  }
  async function exportSession(format) {
    if(!["pdf","txt","json"].includes(format)||state.exportBusy)return;
    const session=state.session;if(session.status!=="finished"&&PORTAL_ROLE!=="mentor")return;
    state.exportBusy=format;render();
    try {
      const response=await fetch(`/api/sessions/${encodeURIComponent(session.id)}/export.${format}?language=${encodeURIComponent($("#report-language")?.value||AUTH.user.locale)}`,{credentials:"same-origin"});
      if(!response.ok){let data;try{data=await response.json();}catch(_){}throw new Error(window.TrainerI18n.error(data?.error)||window.TrainerI18n.t("dashboard.text_480"));}
      const blob=await response.blob();if(!blob.size)throw new Error(window.TrainerI18n.t("dashboard.text_481"));
      const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=`klareki-dialog-${session.id.slice(0,12)}.${format}`;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);toast(window.TrainerI18n.t("dashboard.text_482"));
    } catch(error) {toast(error.message||window.TrainerI18n.t("dashboard.text_483"),true);}
    finally {state.exportBusy=null;render();}
  }
  async function saveCompany() {
    if(state.saving)return;
    state.companyDraft=readCompanyForm();state.formError=null;state.saving=true;render();
    try {
      const result=await api("/api/mentor/company",{method:"PUT",body:state.companyDraft,mentor:true});
      state.company=result.company;state.companyDraft=copy(result.company);state.companyDirty=false;state.saving=false;await learning.load();render();toast(window.TrainerI18n.t("dashboard.text_484"));
    } catch(error) {state.saving=false;state.formError=error.message;render();$(".form-error")?.scrollIntoView({behavior:"smooth",block:"center"});}
  }
  async function saveScenario() {
    if(state.saving)return;
    state.scenarioDraft=readScenarioForm();state.formError=null;const scenario=state.scenarioDraft;
    if(!scenario.allowed_outcomes.length){state.formError=window.TrainerI18n.t("dashboard.text_485");render();$(".form-error")?.scrollIntoView({behavior:"smooth",block:"center"});return;}
    if(scenario.question_hints.length>30||scenario.question_hints.some(q=>q.length>500)){state.formError=window.TrainerI18n.t("dashboard.text_486");render();return;}
    if(scenario.facts.some(f=>f.keywords.length>24||f.keywords.some(k=>k.length>100))){state.formError=window.TrainerI18n.t("dashboard.text_487");render();return;}
    state.saving=true;render();
    try {
      const result=await api("/api/mentor/scenarios",{method:"POST",body:scenario,mentor:true});
      state.scenarioDraft=copy(result.scenario);state.scenarioDraftKey=result.scenario.id;state.scenarioDirty=false;state.saving=false;toast(window.TrainerI18n.t("dashboard.text_488"));
      if(state.route.id!==result.scenario.id)go(`mentor/scenario/${result.scenario.id}`);else render();
    } catch(error) {state.saving=false;state.formError=error.message;render();$(".form-error")?.scrollIntoView({behavior:"smooth",block:"center"});}
  }
  async function deleteScenario(id) {
    const scenario=state.scenarios.find(s=>s.id===id);if(!scenario)return;
    if(!await confirmDialog(window.TrainerI18n.t("dashboard.text_489"),`«${scenario.title}» ${window.TrainerI18n.t("dashboard.text_490")}`,window.TrainerI18n.t("dashboard.text_491"),true))return;
    try {await api(`/api/mentor/scenarios/${encodeURIComponent(id)}`,{method:"DELETE",mentor:true});if(state.scenarioDraftKey===id){state.scenarioDraft=null;state.scenarioDraftKey=null;state.scenarioDirty=false;}toast(window.TrainerI18n.t("dashboard.text_492"));await loadRoute();}
    catch(error){toast(error.message,true);}
  }
  const stableData=v=>JSON.stringify(v,(_,value)=>value&&typeof value==='object'&&!Array.isArray(value)?Object.fromEntries(Object.keys(value).sort().map(k=>[k,value[k]])):value);
  function markCompanyDirty(fromDOM=false,reviewChanged=false) {
    if(fromDOM){
      let draft=readCompanyForm();
      if(!reviewChanged){const {reviewed,...edited}=draft,{reviewed:original,...baseline}=state.company;$('#company-reviewed').checked=stableData(edited)===stableData(baseline)?original:false;draft=readCompanyForm();}
      state.companyDraft=draft;
    }
    state.companyDirty=stableData(state.companyDraft)!==stableData(state.company);
    const label=$('#company-form .draft-label');if(label)label.textContent=window.TrainerI18n.t(state.companyDirty?'dashboard.text_250':'a20.all_saved');
    const button=$('#company-form button[type="submit"]');if(button)button.disabled=state.saving||!state.companyDirty;
  }
  function markScenarioDirty() {
    state.scenarioDirty=true;const label=$(".draft-label");if(label)label.textContent=window.TrainerI18n.t("dashboard.text_250");
  }
  function renderKeepFocus(id) {
    const current=document.getElementById(id);const start=current?.selectionStart;const end=current?.selectionEnd;
    render();const next=document.getElementById(id);next?.focus();if(start!=null&&next?.setSelectionRange)try{next.setSelectionRange(start,end);}catch(_){}
  }
  async function clickHandler(event) {
    const target=event.target.closest("[data-action]");if(!target||target.disabled)return;
    // Capture before actions mutate arrays; render must not restore the old DOM.
    captureDrafts();
    const action=target.dataset.action;
    if(await learning.handle(action,target))return;
    if(action==="menu") {state.menu=!state.menu;$("#sidebar").classList.toggle("open",state.menu);$(".mobile-shade").classList.toggle("open",state.menu);target.setAttribute("aria-expanded",String(state.menu));conversation.drawer(state.menu);return;}
    if(action==="menu-close") {state.menu=false;$("#sidebar").classList.remove("open");$(".mobile-shade").classList.remove("open");($("#kc-app .menu-btn")||$(".menu-btn"))?.setAttribute("aria-expanded","false");conversation.drawer(false);return;}
    if(action==="logout"){
      if(window.TrainerVoice.busy()&&!window.confirm(window.TrainerI18n.t("dictation18.leave")))return;
      if((PORTAL_ROLE==='learner'?(window.TrainerHasUnsavedChanges?.()||Object.keys(state.learningDrafts||{}).length):(state.companyDirty||state.scenarioDirty||studio.dirty()))&&!await confirmDialog(window.TrainerI18n.t("dashboard.text_493"),window.TrainerI18n.t("dashboard.text_494"),window.TrainerI18n.t("dashboard.text_047")))return;
      window.TrainerVoice.cancel();await api('/api/auth/logout',{method:'POST'});
      state.companyDirty=false;state.scenarioDirty=false;studio.cancelDraft();document.getElementById('app').replaceChildren();location.replace('/login');return;
    }
    if(action==="own-password"){if(window.TrainerVoice.busy()&&!window.confirm(window.TrainerI18n.t("dictation18.leave")))return;window.TrainerVoice.cancel();passwordDialog();return;}
    if(action.startsWith('studio-')||action.startsWith('employee-')){if(await studio.handle(action,target))return;}
    if(action==='voice-start'){
      const id=state.session.id;const status=text=>{const el=document.getElementById('voice-status');if(el)el.textContent=text;};
      await window.TrainerVoice.start({language:document.getElementById('voice-language').value,status,error:text=>{status(text);toast(text,true);},text:text=>{if(state.session?.id!==id)return;const field=document.getElementById('message-text');const draft=draftFor(id);const before=field?field.value:draft.text;draft.text=(before?before+'\n':'')+text;draft.pending=null;if(field){field.value=draft.text;field.dispatchEvent(new Event('input',{bubbles:true}));field.focus();}}});return;
    }
    if(action==='voice-diagnostics'){const data=await api('/api/mentor/transcription-diagnostics');document.getElementById('voice-diagnostics-result').textContent=JSON.stringify(data,null,2);return;}
    if(action==='diagnostics'){
      const data=await api('/api/mentor/reviews/'+encodeURIComponent(state.session.id)+'/diagnostics');
      const box=document.getElementById('diagnostics-result');if(box)box.textContent=JSON.stringify(data,null,2);return;
    }
    if(action==='voice-stop'){window.TrainerVoice.stop();return;}
    if(action==='voice-cancel'){window.TrainerVoice.cancel();return;}
    if(action==='save-pair'){
      const sid=target.dataset.id;const a=state.pairs.assignments.find(a=>a.scenario_id===sid);
      const ids=[...document.getElementById(`pair-${sid}`).querySelectorAll('input:checked')].map(i=>i.value);
      await api(`/api/mentor/scenarios/${encodeURIComponent(sid)}/personas`,{method:'PUT',body:{revision:a.revision,profile_ids:ids}});
      toast(window.TrainerI18n.t("dashboard.text_495"));await loadRoute();return;
    }
    if(action==="reload") {await loadRoute();return;}
    if(action==="mode") {const mode=target.dataset.mode;if(!["demo","openai","simple_actor"].includes(mode)||(mode!=="demo"&&!canUseAI()))return;state.mode=mode;state.modeChoice=mode;render();return;}
    if(action==="start-openai") {await startSession(target.dataset.id,"openai");return;}
    if(action==="start"||action==="repeat") {await startSession(target.dataset.id,target.dataset.mode||state.mode);return;}
    if(action==="history-filter") {go("learner/history/"+target.dataset.filter);return;}
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
      state.companyDraft.services.push({id:identifier("service"),title:"",description:"",conditions:""});state.companyDraft.reviewed=false;markCompanyDirty();render();const last=$$(".service-row").at(-1);if(last){U.openAncestors(last);last.open=true;}last?.scrollIntoView({behavior:"smooth",block:"center"});$("input",last)?.focus();return;
    }
    if(action==="remove-service") {
      state.companyDraft=readCompanyForm();if(state.companyDraft.services.length<=1)return;
      state.companyDraft.services.splice(Number(target.dataset.index),1);state.companyDraft.reviewed=false;markCompanyDirty();render();return;
    }
    if(action==="add-fact") {
      state.scenarioDraft=readScenarioForm();if(state.scenarioDraft.facts.length>=20)return;
      state.scenarioDraft.facts.push({id:identifier("fact"),stage:target.dataset.stage,label:"",value:"",status:"known",keywords:[],required:true,material:true});markScenarioDirty();render();const last=$$(".fact-row").at(-1);if(last){U.openAncestors(last);last.open=true;}last?.scrollIntoView({behavior:"smooth",block:"center"});$("input",last)?.focus();return;
    }
    if(action==="remove-fact") {
      state.scenarioDraft=readScenarioForm();if(state.scenarioDraft.facts.length<=2)return;state.scenarioDraft.facts.splice(Number(target.dataset.index),1);markScenarioDirty();render();return;
    }
    if(action==="delete-scenario") {await deleteScenario(target.dataset.id);}
  }
  function inputHandler(event) {
    if(event.target.closest("#studio-form")){studio.markDirty();return;}
    const target=event.target;
    if(target.id==="message-text"&&state.session) {
      const draft=draftFor(state.session.id);draft.text=target.value;
      if(draft.pending&&(draft.pending.text!==target.value.trim()))draft.pending=null;
      const send=$(".send-btn");if(send)send.disabled=draft.sending||window.TrainerVoice.busy()||!target.value.trim();return;
    }
    if(target.id==="history-search") {state.historySearch=target.value;renderKeepFocus("history-search");return;}
    if(target.id==="scenario-search") {state.scenarioSearch=target.value;renderKeepFocus("scenario-search");return;}
    if(target.id==="review-note"&&state.session){state.noteDrafts[state.session.id]=target.value;return;}
    if(target.closest("#company-form")) {
      markCompanyDirty(true,target.id==="company-reviewed");return;
    }
    if(target.closest("#scenario-form"))markScenarioDirty();
  }
  function changeHandler(event) {
    if(event.target.id==="studio-import"){studio.imported(event.target.files[0]);return;}
    if(event.target.closest("#studio-form")){studio.markDirty();return;}
    const target=event.target;
    if(target.id.startsWith("review-")&&state.session&&["needs","capabilities","proposal","commercial","fit"].some(x=>target.id==="review-"+x)){state.assessmentDrafts??={};state.assessmentDrafts[state.session.id]={stages:Object.fromEntries(REVIEW_STAGES.map(x=>[x,$("#review-"+x).value])),commercial_outcome:$("#review-commercial").value||null,company_fit:$("#review-fit").value};}
    if(target.id==="review-employee-filter"){state.reviewEmployee=target.value;render();return;}
    if(target.id==="review-scenario-filter"){state.reviewScenario=target.value;render();return;}
    if(target.matches('[data-training-language]')){try{localStorage.setItem('trainer.training.language',target.value);}catch(_){}return;}
    if(target.closest("#company-form"))markCompanyDirty(true,target.id==="company-reviewed");
    if(target.closest("#scenario-form")) {
      markScenarioDirty();
      if(target.matches("[data-field=status], [data-field=required]")) {
        const row=target.closest(".fact-row");const required=$("[data-field=required]",row);const material=$("[data-field=material]",row);
        required.disabled=$("[data-field=status]",row).value==="not_applicable";
        if(required.disabled)required.checked=false;
        material.disabled=required.checked;
        if(required.checked)material.checked=true;
      }
    }
  }
  function submitHandler(event) {
    const id=event.target.id;
    if(["company-form","scenario-form"].includes(id)&&!event.target.checkValidity()){event.preventDefault();U.revealError(event.target.querySelector(":invalid"));return;}
    if(id==="studio-form"){event.preventDefault();studio.save();return;}
    if(id==="employee-create"){event.preventDefault();studio.createEmployee(event.target);return;}
    if(["message-form","company-form","scenario-form","review-form"].includes(id))event.preventDefault();
    if(id==="message-form")sendMessage();
    else if(id==="company-form")saveCompany();
    else if(id==="scenario-form")saveScenario();
    else if(id==="review-form")saveReview();
  }
  $("#app").addEventListener("click",event=>{clickHandler(event).catch(error=>toast(error.message||window.TrainerI18n.t("dashboard.text_496"),true));});
  $("#app").addEventListener("input",inputHandler);
  $("#app").addEventListener("change",changeHandler);
  $("#app").addEventListener("submit",submitHandler);
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&state.menu){state.menu=false;$("#sidebar")?.classList.remove("open");$(".mobile-shade")?.classList.remove("open");($("#kc-app .menu-btn")||$(".menu-btn"))?.setAttribute("aria-expanded","false");($("#kc-app .menu-btn")||$(".menu-btn"))?.focus();conversation.drawer(false);}
    if(event.key==="Enter"&&(event.ctrlKey||event.metaKey)&&event.target.id==="message-text"){event.preventDefault();sendMessage();}
  });
  window.addEventListener("hashchange",loadRoute);
  window.TrainerHasUnsavedChanges=()=>state.companyDirty||state.scenarioDirty||studio.dirty()||Object.values(state.drafts).some(d=>d.text?.trim())||[...document.querySelectorAll("#employee-create input,#review-form textarea")].some(el=>el.value.length>0);
  window.addEventListener("beforeunload",event=>{if(!window.TrainerLocaleReload&&(window.TrainerVoice.busy()||state.companyDirty||state.scenarioDirty||studio.dirty()||Object.keys(state.learningDrafts||{}).length)){event.preventDefault();event.returnValue="";}});
  if(!location.hash)history.replaceState(null,"",`#${PORTAL_ROLE}/${PORTAL_ROLE==="mentor"?"overview":"practice"}`);
  loadRoute();
})();
