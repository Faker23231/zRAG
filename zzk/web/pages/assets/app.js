/* ============================================================
   zRAG — 前端交互
   首页 / 技术路线 / 单栏对话工作台 / 追问澄清
   ============================================================ */
(() => {
    "use strict";

    const LS_CONV = "zrag.conversations.v1";
    const LS_WIN = "zrag.windows.v1";
    // 单栏布局：同一时刻只保留一个对话窗口
    const MAX_WINDOWS = 1;

    const dom = {
        nav: document.getElementById("nav"),
        engine: document.getElementById("engine"),
        engineLabel: document.getElementById("engineLabel"),
        engineLabel2: document.getElementById("engineLabel2"),
        engineDot2: document.getElementById("engineDot2"),
        heroArt: document.getElementById("heroArt"),
        featureWorld: document.getElementById("featureWorld"),
        worldGrid: document.getElementById("worldGrid"),
        archiveGrid: document.getElementById("archiveGrid"),
        indexWall: document.getElementById("indexWall"),
        indexCount: document.getElementById("indexCount"),
        indexPrev: document.getElementById("indexPrev"),
        indexNext: document.getElementById("indexNext"),
        projectList: document.getElementById("projectList"),
        viewHome: document.getElementById("viewHome"),
        viewChat: document.getElementById("viewChat"),
        convList: document.getElementById("convList"),
        convCount: document.getElementById("convCount"),
        newConvBtn: document.getElementById("newConvBtn"),
        newMenu: document.getElementById("newMenu"),
        desk: document.getElementById("desk"),
        deskTitle: document.getElementById("deskTitle"),
        closeAll: document.getElementById("closeAll"),
        panes: document.getElementById("panes"),
        deskEmpty: document.getElementById("deskEmpty"),
        quickStarts: document.getElementById("quickStarts"),
        railToggle: document.getElementById("railToggle"),
        railClose: document.getElementById("railClose"),
        fileInput: document.getElementById("fileInput"),
        dropZone: document.getElementById("dropZone"),
        uploadIdle: document.getElementById("uploadIdle"),
        uploadProgress: document.getElementById("uploadProgress"),
        uploadName: document.getElementById("uploadName"),
        uploadSize: document.getElementById("uploadSize"),
        uploadPercent: document.getElementById("uploadPercent"),
        uploadBar: document.getElementById("uploadBar"),
        uploadSteps: document.getElementById("uploadSteps"),
        uploadActions: document.getElementById("uploadActions"),
        dragOverlay: document.getElementById("dragOverlay"),
        toasts: document.getElementById("toasts"),
        clarifyModal: document.getElementById("clarifyModal"),
        clarifyTitle: document.getElementById("clarifyTitle"),
        clarifyHint: document.getElementById("clarifyHint"),
        clarifyEntities: document.getElementById("clarifyEntities"),
        clarifyIntents: document.getElementById("clarifyIntents"),
        clarifyExtra: document.getElementById("clarifyExtra"),
        clarifySkip: document.getElementById("clarifySkip"),
        clarifySubmit: document.getElementById("clarifySubmit"),
        clarifyClose: document.getElementById("clarifyClose"),
    };
    dom.workspace = document.querySelector(".workspace");

    const state = {
        examples: [],
        projects: [],
        conversations: [],
        windows: [],
        active: null,
        featured: null,
        uploadToken: 0,
        busyUpload: false,
        confirmDelete: null,
        confirmTimer: 0,
        clarify: null,
    };

    const runtimes = new Map();

    const IMPORT_STEPS = [
        { key: "开始上传文件", label: "接收文件" },
        { key: "检查文件", label: "校验 PDF" },
        { key: "PDF转Markdown", label: "解析版式与正文" },
        { key: "Markdown图片处理", label: "提取并归档图片" },
        { key: "知识主体识别", label: "识别知识主体" },
        { key: "文档切分", label: "切分内容" },
        { key: "向量生成", label: "生成向量" },
        { key: "导入向量库", label: "写入索引" },
    ];

    // 问答链路的可视化步骤（与后端节点中文名对齐）
    const TRACE_FLOWS = {
        demo: [
            { label: "理解问题", match: ["理解问题"] },
            { label: "检索示例资料", match: ["检索示例资料"] },
            { label: "组织回答", match: ["组织回答", "生成答案"] },
        ],
        upload: [
            { label: "理解问题", match: ["理解问题与主体"] },
            { label: "多路召回", match: ["切片搜索", "切片搜索(假设性文档)", "网络搜索"] },
            { label: "RRF 融合", match: ["倒排融合"] },
            { label: "重排", match: ["重排序"] },
            { label: "生成答案", match: ["生成答案"] },
        ],
    };

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    /* ----------------------------------------------------------
       基础工具
       ---------------------------------------------------------- */

    const escapeHtml = (value) => String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");

    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    const formatSize = (bytes) => {
        if (!bytes) return "—";
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
        return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    };

    const formatDuration = (seconds) => {
        if (seconds == null) return "";
        if (seconds < 10) return `${seconds.toFixed(1)}s`;
        return `${Math.round(seconds)}s`;
    };

    const trimText = (value, max = 24) => {
        const text = String(value || "").replace(/\s+/g, " ").trim();
        return text.length > max ? `${text.slice(0, max)}…` : text;
    };

    function relativeTime(ts) {
        const diff = Date.now() - (ts || Date.now());
        if (diff < 60 * 1000) return "刚刚";
        if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`;
        if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`;
        const date = new Date(ts);
        return `${date.getMonth() + 1}/${date.getDate()}`;
    }

    function toast(message, timeout = 4200) {
        const el = document.createElement("div");
        el.className = "toast";
        el.innerHTML = `<span class="toast__dot"></span><span>${escapeHtml(message)}</span>`;
        dom.toasts.appendChild(el);
        setTimeout(() => {
            el.classList.add("is-out");
            setTimeout(() => el.remove(), 380);
        }, timeout);
    }

    function isSafeUrl(url) {
        const value = String(url || "").trim();
        return /^https?:\/\//i.test(value) || /^\/assets\//i.test(value) || /^data:image\//i.test(value);
    }

    function normalizeUrl(url) {
        return String(url || "").trim().replace(/\s/g, "%20");
    }

    /* ----------------------------------------------------------
       本地持久化
       ---------------------------------------------------------- */

    function persistConversations() {
        try {
            const lightweight = state.conversations.slice(0, 30).map((conv) => ({
                key: conv.key,
                sessionId: conv.sessionId,
                projectId: conv.projectId,
                kind: conv.kind,
                title: conv.title,
                baseTitle: conv.baseTitle,
                subtitle: conv.subtitle,
                description: conv.description,
                meta: conv.meta,
                questions: conv.questions,
                preview: conv.preview,
                createdAt: conv.createdAt,
                updatedAt: conv.updatedAt,
                answered: conv.answered,
                userTitled: conv.userTitled,
            }));
            localStorage.setItem(LS_CONV, JSON.stringify(lightweight));
        } catch (e) { /* ignore */ }
    }

    function loadConversations() {
        try {
            const raw = localStorage.getItem(LS_CONV);
            const items = raw ? JSON.parse(raw) : [];
            if (!Array.isArray(items)) return;
            state.conversations = items
                .filter((conv) => conv && conv.key && conv.sessionId && conv.projectId)
                .map((conv) => ({
                    ...conv,
                    title: conv.title || conv.baseTitle || "未命名对话",
                    baseTitle: conv.baseTitle || conv.title || "资料库",
                    questions: Array.isArray(conv.questions) ? conv.questions : [],
                    preview: conv.preview || "",
                    createdAt: conv.createdAt || Date.now(),
                    updatedAt: conv.updatedAt || Date.now(),
                }));
        } catch (e) {
            state.conversations = [];
        }
    }

    function persistWindows() {
        try {
            localStorage.setItem(LS_WIN, JSON.stringify({ windows: state.windows, active: state.active }));
        } catch (e) { /* ignore */ }
    }

    function loadWindowState() {
        try {
            const raw = localStorage.getItem(LS_WIN);
            if (!raw) return;
            const data = JSON.parse(raw);
            const keys = new Set(state.conversations.map((conv) => conv.key));
            state.windows = (Array.isArray(data.windows) ? data.windows : [])
                .filter((key) => keys.has(key))
                .slice(0, MAX_WINDOWS);
            // 单栏模式下，历史存档里的第二个窗口不能成为当前窗口
            state.active = state.windows.includes(data.active)
                ? data.active
                : (state.windows[0] || null);
        } catch (e) {
            state.windows = [];
            state.active = null;
        }
    }

    const convOf = (key) => state.conversations.find((conv) => conv.key === key) || null;

    /* ----------------------------------------------------------
       导航 / 视图
       ---------------------------------------------------------- */

    function setView(name, options = {}) {
        const apply = () => {
            dom.viewHome.hidden = name !== "home";
            dom.viewChat.hidden = name !== "chat";
            document.body.classList.toggle("is-workspace", name === "chat");
            if (name === "home") window.scrollTo({ top: 0, behavior: "auto" });
            if (name === "chat") {
                window.scrollTo({ top: 0, behavior: "auto" });
                ensureWindowsBuilt();
                applyLayout();
            }
            if (options.after) options.after();
        };

        if (!document.startViewTransition || reduceMotion) {
            apply();
            return;
        }
        document.startViewTransition(apply);
    }

    function scrollToSection(id) {
        if (!dom.viewChat.hidden) {
            setView("home", {
                after: () => {
                    requestAnimationFrame(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }));
                },
            });
            return;
        }
        document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    }

    function goHome() {
        closeNewMenu();
        setView("home");
    }

    function openWorkspace() {
        setView("chat", {
            after: () => {
                if (state.active) focusComposer(state.active);
            },
        });
    }

    function goCreate(openPicker = false) {
        if (!dom.viewChat.hidden) {
            setView("home", {
                after: () => {
                    document.getElementById("create")?.scrollIntoView({ behavior: "smooth" });
                    if (openPicker) setTimeout(pickFile, 520);
                },
            });
            return;
        }
        document.getElementById("create")?.scrollIntoView({ behavior: "smooth" });
        if (openPicker) setTimeout(pickFile, 460);
    }

    window.addEventListener("scroll", () => {
        dom.nav.classList.toggle("is-scrolled", window.scrollY > 8);
    }, { passive: true });

    document.addEventListener("click", (event) => {
        const target = event.target.closest("[data-action], [data-scroll]");
        if (!target) return;

        if (target.dataset.scroll) {
            event.preventDefault();
            scrollToSection(target.dataset.scroll);
            return;
        }

        switch (target.dataset.action) {
            case "home":
                event.preventDefault();
                goHome();
                break;
            case "open-workspace":
                openWorkspace();
                break;
            case "scroll-worlds":
                scrollToSection("worlds");
                break;
            case "upload":
                goCreate(true);
                break;
            case "pick-file":
                pickFile();
                break;
            case "refresh-projects":
                loadProjects(true);
                break;
            case "open-project":
                enterProject(target.dataset.id);
                break;
            case "delete-project":
                removeProject(target);
                break;
            default:
                break;
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        if (!dom.clarifyModal.hidden) {
            closeClarify(true);
            return;
        }
        if (!dom.newMenu.hidden) {
            closeNewMenu();
            return;
        }
    });

    /* ----------------------------------------------------------
       滚动出现动画
       ---------------------------------------------------------- */

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-in");
                revealObserver.unobserve(entry.target);
            }
        });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.06 });

    function observeReveals(root = document) {
        root.querySelectorAll(".reveal:not(.is-in)").forEach((el) => revealObserver.observe(el));
    }

    /* ----------------------------------------------------------
       健康状态
       ---------------------------------------------------------- */

    async function loadHealth() {
        try {
            const res = await fetch("/api/health");
            if (!res.ok) throw new Error("health failed");
            const data = await res.json();
            const ok = data.status === "ok";
            dom.engine.classList.toggle("is-ok", ok);
            dom.engine.classList.toggle("is-warn", !ok);
            dom.engineLabel.textContent = ok ? "引擎在线" : "示例可用";
            if (dom.engineLabel2) dom.engineLabel2.textContent = ok ? "引擎在线" : "示例可用";
            if (dom.engineDot2) {
                dom.engineDot2.classList.toggle("is-ok", ok);
                dom.engineDot2.classList.toggle("is-warn", !ok);
            }
            const detail = Object.entries(data.services || {})
                .map(([name, alive]) => `${name}: ${alive ? "在线" : "离线"}`)
                .join(" · ");
            dom.engine.title = detail || "服务状态";
        } catch (e) {
            dom.engineLabel.textContent = "未连接";
            if (dom.engineLabel2) dom.engineLabel2.textContent = "未连接";
            dom.engine.classList.remove("is-ok");
            dom.engine.classList.add("is-warn");
        }
    }

    /* ----------------------------------------------------------
       示例资料库
       ---------------------------------------------------------- */

    async function loadExamples() {
        try {
            const res = await fetch("/api/examples");
            if (!res.ok) throw new Error("加载示例失败");
            const data = await res.json();
            state.examples = Array.isArray(data.items) ? data.items : [];
            state.featured = state.examples.find((demo) => demo.featured) || state.examples[0] || null;
            renderExamples();
            renderStats();
            renderQuickStarts();
        } catch (e) {
            dom.worldGrid.innerHTML = `
                <div class="library__empty" style="grid-column:1/-1">
                    <strong>示例资料暂时没有加载出来</strong>
                    检查服务是否启动，然后刷新页面。
                    <div style="margin-top:14px"><button class="btn btn--small btn--quiet" data-retry-examples>重新加载</button></div>
                </div>`;
            dom.worldGrid.querySelector("[data-retry-examples]")?.addEventListener("click", loadExamples);
        }
    }

    function renderStats() {
        const demo = state.featured;
        if (!demo) return;
        const stats = demo.stats || {};
        if (dom.indexCount) {
            dom.indexCount.textContent = String(stats.entries || demo.index_terms?.length || 0);
        }
    }

    function renderExamples() {
        const featured = state.featured;
        const rest = state.examples.filter((demo) => demo.id !== featured?.id);

        if (!featured) {
            dom.featureWorld.innerHTML = `<div class="library__empty"><strong>还没有示例资料</strong>先创建一个属于你的项目吧。</div>`;
        } else {
            const images = (featured.hero_images && featured.hero_images.length)
                ? featured.hero_images
                : [featured.cover].filter(Boolean);
            const stats = featured.stats || {};
            const questions = (featured.questions || []).slice(0, 4);
            dom.featureWorld.innerHTML = `
                <article class="feature-world__card">
                    <div class="feature-world__art">
                        <img class="feature-world__art-main" src="${escapeHtml(normalizeUrl(images[0] || ""))}" alt="${escapeHtml(featured.title)}资料库封面" loading="lazy"/>
                        <div class="feature-world__thumbs">
                            ${images.slice(1, 3).map((url) => `<img src="${escapeHtml(normalizeUrl(url))}" alt="" loading="lazy"/>`).join("")}
                        </div>
                        <span class="feature-world__seal" aria-hidden="true">悟<br/>空</span>
                        <span class="feature-world__badge">深度示例</span>
                    </div>
                    <div class="feature-world__body">
                        <p class="eyebrow">${escapeHtml(featured.subtitle || "全图鉴知识库")}</p>
                        <h3 class="feature-world__title">${escapeHtml(featured.title)}</h3>
                        <p class="feature-world__tagline">${escapeHtml(featured.tagline || "")}</p>
                        <p class="feature-world__desc">${escapeHtml(featured.description || "")}</p>
                        <div class="feature-world__meta">
                            <span><strong>${escapeHtml(String(stats.entries || 0))}</strong> 图鉴条目</span>
                            <span><strong>${escapeHtml(String(featured.doc_count || 0))}</strong> 篇深度资料</span>
                            <span><strong>${escapeHtml(String(stats.images || 0))}</strong> 张原图</span>
                        </div>
                        <div class="feature-world__qs">
                            ${questions.map((q) => `<button type="button" data-feature-q="${escapeHtml(q)}">${escapeHtml(q)}</button>`).join("")}
                        </div>
                        <div class="feature-world__foot">
                            <button class="btn btn--primary btn--small" data-feature-enter>进入资料库</button>
                            <span>单栏专注 · 追问澄清</span>
                        </div>
                    </div>
                </article>`;

            dom.featureWorld.querySelector("[data-feature-enter]")?.addEventListener("click", () => enterDemo(featured.id));
            dom.featureWorld.querySelectorAll("[data-feature-q]").forEach((btn) => {
                btn.addEventListener("click", () => enterDemo(featured.id, btn.dataset.featureQ));
            });
        }

        dom.worldGrid.innerHTML = rest.map((demo, index) => {
            const accent = ["gold", "green", "teal", "blue"].includes(demo.accent) ? demo.accent : "blue";
            const cover = demo.cover ? normalizeUrl(demo.cover) : "";
            return `
            <article class="world world--library" role="button" tabindex="0"
                     data-demo="${escapeHtml(demo.id)}"
                     aria-label="进入 ${escapeHtml(demo.title)} 示例"
                     style="animation:fade-up .7s var(--ease) ${90 + index * 70}ms both">
                <div class="world__cover world__cover--${accent}">
                    ${cover
                        ? `<img class="world__cover-img" src="${escapeHtml(cover)}" alt="" loading="lazy"/>`
                        : `<div class="world__art" aria-hidden="true">
                               <span class="world__art-ring"></span>
                               <span class="world__glyph">${escapeHtml((demo.title || "?").slice(0, 1))}</span>
                           </div>`}
                    <span class="world__cover-tag">${escapeHtml(demo.subtitle || "知识库")}</span>
                </div>
                <div class="world__body">
                    <div class="world__title">
                        <strong>${escapeHtml(demo.title)}</strong>
                    </div>
                    <p class="world__desc">${escapeHtml(demo.tagline || demo.description || "")}</p>
                    <div class="world__meta">
                        <span>${escapeHtml(String(demo.doc_count || 0))} 篇资料</span>
                        <span class="world__enter">进入</span>
                    </div>
                </div>
            </article>`;
        }).join("");

        dom.worldGrid.querySelectorAll(".world").forEach((card) => {
            const enter = () => enterDemo(card.dataset.demo);
            card.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    enter();
                }
            });
            card.addEventListener("click", enter);
        });

        renderArchive();
    }

    function renderArchive() {
        const demo = state.featured;
        if (!demo) return;
        const sections = demo.sections || [];
        dom.archiveGrid.innerHTML = sections.map((section, index) => `
            <article class="archive-card" data-category="${escapeHtml(section.title)}" role="button" tabindex="0"
                     style="animation:fade-up .7s var(--ease) ${80 + index * 60}ms both">
                <div class="archive-card__img">
                    <img src="${escapeHtml(normalizeUrl(section.image || ""))}" alt="" loading="lazy"/>
                </div>
                <div class="archive-card__body">
                    <div class="archive-card__top">
                        <h3>${escapeHtml(section.title)}</h3>
                        <span>${escapeHtml(String(section.count || 0))}</span>
                    </div>
                    <p>${escapeHtml(section.desc || "")}</p>
                    <span class="archive-card__go">从这一章开始 →</span>
                </div>
            </article>`).join("");

        dom.archiveGrid.querySelectorAll(".archive-card").forEach((card) => {
            const open = () => {
                const category = card.dataset.category;
                const section = sections.find((item) => item.title === category);
                enterDemo(demo.id, section?.prompt || `帮我梳理「${category}」里最值得先看的内容。`);
            };
            card.addEventListener("click", open);
            card.addEventListener("keydown", (event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    open();
                }
            });
        });

        dom.indexWall.innerHTML = (demo.index_terms || []).map((term) => `
            <button type="button" class="index-term" data-term="${escapeHtml(term.name)}">
                <img src="${escapeHtml(normalizeUrl(term.image || ""))}" alt="" loading="lazy"/>
                <span>${escapeHtml(term.name)}</span>
            </button>`).join("");

        dom.indexWall.querySelectorAll("[data-term]").forEach((btn) => {
            btn.addEventListener("click", () => {
                enterDemo(demo.id, btn.dataset.term);
            });
        });
        bindIndexRail();
    }

    // 图鉴索引：按钮翻页 + 拖拽 + 方向键，支持横向滚动浏览
    function bindIndexRail() {
        const rail = dom.indexWall;
        const prev = dom.indexPrev;
        const next = dom.indexNext;
        if (!rail || !prev || !next) return;

        const page = () => Math.max(180, Math.round(rail.clientWidth * 0.72));
        const sync = () => {
            const max = rail.scrollWidth - rail.clientWidth;
            const scrollable = max > 4;
            const atStart = rail.scrollLeft <= 2;
            const atEnd = rail.scrollLeft >= max - 2;
            rail.classList.toggle("is-scrollable", scrollable);
            rail.classList.toggle("is-start", atStart);
            rail.classList.toggle("is-end", atEnd);
            prev.disabled = !scrollable || atStart;
            next.disabled = !scrollable || atEnd;
        };

        prev.onclick = () => rail.scrollBy({ left: -page(), behavior: reduceMotion ? "auto" : "smooth" });
        next.onclick = () => rail.scrollBy({ left: page(), behavior: reduceMotion ? "auto" : "smooth" });
        rail.onscroll = sync;
        rail.onkeydown = (event) => {
            if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
            event.preventDefault();
            rail.scrollBy({
                left: event.key === "ArrowLeft" ? -page() : page(),
                behavior: reduceMotion ? "auto" : "smooth",
            });
        };

        let dragging = false;
        let moved = false;
        let startX = 0;
        let startLeft = 0;

        rail.onpointerdown = (event) => {
            if (event.pointerType === "mouse" && event.button !== 0) return;
            dragging = true;
            moved = false;
            startX = event.clientX;
            startLeft = rail.scrollLeft;
            rail.classList.add("is-dragging");
        };
        rail.onpointermove = (event) => {
            if (!dragging) return;
            const dx = event.clientX - startX;
            if (Math.abs(dx) > 5) moved = true;
            rail.scrollLeft = startLeft - dx;
        };
        const endDrag = () => {
            if (!dragging) return;
            dragging = false;
            rail.classList.remove("is-dragging");
        };
        rail.onpointerup = endDrag;
        rail.onpointerleave = endDrag;
        rail.onpointercancel = endDrag;
        rail.addEventListener("click", (event) => {
            if (!moved) return;
            moved = false;
            event.preventDefault();
            event.stopPropagation();
        }, true);

        if (window.ResizeObserver) {
            const observer = new ResizeObserver(sync);
            observer.observe(rail);
        } else {
            window.addEventListener("resize", sync, { passive: true });
        }
        requestAnimationFrame(sync);
    }

    function renderQuickStarts() {
        const featured = state.featured;
        if (!featured || !dom.quickStarts) return;

        // 空工作台同时展示商品与游戏示例，避免把产品误解成单一游戏知识库
        const coffee = state.examples.find((demo) => demo.id === "coffee");
        const picks = [];
        const pushDemo = (demo, take = 2) => {
            if (!demo) return;
            (demo.questions || []).slice(0, take).forEach((question) => {
                if (picks.length < 4) picks.push({ demo, question });
            });
        };
        pushDemo(coffee, 2);
        pushDemo(featured, 2);
        state.examples.forEach((demo) => {
            if (demo !== coffee && demo !== featured) pushDemo(demo);
        });

        dom.quickStarts.innerHTML = picks.map(({ demo, question }, index) => `
            <button type="button" class="quick-start" data-demo-id="${escapeHtml(demo.id)}" data-quick="${escapeHtml(question)}">
                <span>0${index + 1}</span>
                <strong>${escapeHtml(question)}</strong>
            </button>`).join("");
        dom.quickStarts.querySelectorAll("[data-quick]").forEach((btn) => {
            btn.addEventListener("click", () => enterDemo(btn.dataset.demoId, btn.dataset.quick));
        });
    }

    function demoProject(demo) {
        return {
            kind: "demo",
            id: demo.id,
            title: demo.title,
            subtitle: demo.subtitle || "内置示例知识库",
            description: demo.tagline || demo.description || "",
            questions: demo.questions || [],
            meta: `示例资料库 · ${demo.doc_count || 0} 篇资料`,
            docCount: demo.doc_count || 0,
        };
    }

    function enterDemo(demoId, question = null, options = {}) {
        const demo = state.examples.find((item) => item.id === demoId);
        if (!demo) return;
        openForProject(demoProject(demo), question, options);
    }

    /* ----------------------------------------------------------
       我的项目
       ---------------------------------------------------------- */

    async function loadProjects(showToast = false) {
        try {
            const res = await fetch("/api/projects");
            if (!res.ok) throw new Error("加载项目失败");
            const data = await res.json();
            state.projects = Array.isArray(data.items) ? data.items : [];
            renderProjects();
            if (showToast) toast("项目列表已刷新");
        } catch (e) {
            if (showToast) toast("加载项目失败，请稍后再试");
        }
    }

    function renderProjects() {
        if (!state.projects.length) {
            dom.projectList.innerHTML = `
                <div class="library__empty">
                    <strong>还没有自己的项目</strong>
                    上传一份 PDF，zRAG 会把它变成可以追问的知识库。
                    <div style="margin-top:16px">
                        <button class="btn btn--small btn--primary" data-action="upload">上传 PDF</button>
                    </div>
                </div>`;
            return;
        }

        dom.projectList.innerHTML = state.projects.map((project) => {
            const status = project.status || "processing";
            const statusLabel = status === "ready" ? "可对话" : status === "failed" ? "导入失败" : "解析中";
            const statusClass = status === "ready" ? "is-ready" : status === "failed" ? "is-failed" : "is-processing";
            const title = escapeHtml(project.title || "未命名项目");
            const meta = [
                project.file_name ? escapeHtml(project.file_name) : "",
                project.doc_count ? `${project.doc_count} 个切片` : "",
                project.item_name ? `主体：${escapeHtml(project.item_name)}` : "",
            ].filter(Boolean).join(" · ");

            return `
            <article class="project">
                <div class="project__top">
                    <span class="project__icon">PDF</span>
                    <div style="min-width:0">
                        <p class="project__title">${title}</p>
                        <p class="project__meta">${meta || "等待导入进度"}</p>
                    </div>
                    <span class="project__status ${statusClass}"><i></i>${statusLabel}</span>
                </div>
                ${project.error ? `<p class="project__error">${escapeHtml(project.error)}</p>` : ""}
                <div class="project__foot">
                    <button class="btn ${status === "ready" ? "btn--primary" : "btn--quiet"}"
                            data-action="open-project" data-id="${escapeHtml(project.id)}"
                            ${status === "ready" ? "" : "disabled"}>
                        ${status === "ready" ? "进入对话" : "解析中…"}
                    </button>
                    <button class="project__delete" data-action="delete-project" data-id="${escapeHtml(project.id)}">删除</button>
                </div>
            </article>`;
        }).join("");
    }

    function enterProject(projectId, question = null, options = {}) {
        const project = state.projects.find((item) => item.id === projectId);
        if (!project || project.status !== "ready") return;
        openForProject({
            kind: "upload",
            id: project.id,
            title: project.title,
            subtitle: project.file_name || "PDF 项目",
            description: project.item_name ? `知识主体：${project.item_name}` : "基于你上传的 PDF",
            questions: [
                "这份资料主要讲了什么？",
                "帮我总结其中的关键要点。",
                "资料里有哪些步骤或注意事项？",
            ],
            meta: `我的项目 · ${project.doc_count || 0} 个切片`,
            docCount: project.doc_count || 0,
        }, question, options);
    }

    function removeProject(button) {
        const projectId = button.dataset.id;
        if (!projectId) return;
        if (!button.dataset.armed) {
            button.dataset.armed = "1";
            button.textContent = "确认删除？";
            setTimeout(() => {
                if (button.isConnected) {
                    delete button.dataset.armed;
                    button.textContent = "删除";
                }
            }, 3200);
            return;
        }

        fetch(`/api/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" })
            .then(async (res) => {
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    throw new Error(data.message || "删除失败");
                }
                toast("项目已删除");
                loadProjects();
            })
            .catch((e) => toast(e.message || "删除失败"));
    }

    /* ----------------------------------------------------------
       对话数据模型
       ---------------------------------------------------------- */

    function createConversation(project) {
        const now = Date.now();
        const conv = {
            key: `c_${now.toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
            sessionId: `sess_${project.id}_${Math.random().toString(36).slice(2, 10)}`,
            projectId: project.id,
            kind: project.kind || "demo",
            title: project.title,
            baseTitle: project.title,
            subtitle: project.subtitle || "",
            description: project.description || "",
            meta: project.meta || "",
            questions: project.questions || [],
            preview: "",
            createdAt: now,
            updatedAt: now,
            answered: false,
            userTitled: false,
            fresh: true,
        };
        state.conversations.unshift(conv);
        persistConversations();
        renderRail();
        return conv;
    }

    function openForProject(project, question = null, options = {}) {
        const existing = state.conversations
            .filter((conv) => conv.projectId === project.id && conv.kind === project.kind)
            .sort((a, b) => b.updatedAt - a.updatedAt)[0];

        let conv = existing;
        if (options.forceNew || !existing || (question && existing.answered)) {
            conv = createConversation(project);
        }
        openConversation(conv.key, { question });
    }

    function openConversation(key, options = {}) {
        const conv = convOf(key);
        if (!conv) return;

        if (!state.windows.includes(key)) {
            if (state.windows.length >= MAX_WINDOWS) {
                const victim = state.windows.find((item) => item !== state.active) || state.windows[0];
                closeWindow(victim, { silent: true });
            }
            state.windows.push(key);
            buildPane(conv);
        }

        setActive(key, { focus: !options.question });
        closeNewMenu();
        setView("chat");

        if (options.question) {
            setTimeout(() => sendMessage(key, options.question), reduceMotion ? 60 : 300);
        }
        persistWindows();
    }

    function setActive(key, options = {}) {
        const conv = convOf(key);
        if (!conv) return;
        state.active = key;
        dom.workspace?.classList.remove("is-rail-open");
        state.conversations.sort((a, b) => b.updatedAt - a.updatedAt);
        applyLayout();
        renderRail();
        renderTabs();
        dom.deskTitle.textContent = conv.title;
        persistWindows();
        if (options.focus) focusComposer(key);
    }

    function applyLayout() {
        runtimes.forEach((rt, key) => {
            rt.root.hidden = key !== state.active;
            rt.root.classList.toggle("is-active", key === state.active);
        });
        dom.desk.dataset.layout = "single";
        dom.deskEmpty.hidden = state.windows.length > 0;
        dom.panes.hidden = state.windows.length === 0;
    }

    function focusComposer(key) {
        const rt = runtimes.get(key);
        if (!rt) return;
        setTimeout(() => rt.input.focus(), reduceMotion ? 30 : 220);
    }

    function ensureWindowsBuilt() {
        state.windows.slice().forEach((key) => {
            const conv = convOf(key);
            if (!conv) {
                state.windows = state.windows.filter((item) => item !== key);
                return;
            }
            if (!runtimes.has(key)) buildPane(conv);
        });
        if (!state.windows.length) {
            state.active = null;
            dom.deskTitle.textContent = "未打开对话";
        } else if (!state.windows.includes(state.active)) {
            state.active = state.windows[0];
        }
        applyLayout();
        renderRail();
        renderTabs();
    }

    function closeWindow(key, options = {}) {
        const rt = runtimes.get(key);
        if (rt) {
            rt.stopVoice?.();
            if (rt.streaming) stopStreaming(key, false);
            rt.root.remove();
            runtimes.delete(key);
        }
        state.windows = state.windows.filter((item) => item !== key);
        if (state.active === key) {
            state.active = state.windows[0] || null;
        }
        if (!options.silent) {
            renderRail();
            renderTabs();
            applyLayout();
        }
        persistWindows();
        const next = convOf(state.active);
        dom.deskTitle.textContent = next ? next.title : "未打开对话";
    }

    function closeAllWindows() {
        if (!state.windows.length) return;
        state.windows.slice().forEach((key) => closeWindow(key, { silent: true }));
        state.active = null;
        renderRail();
        renderTabs();
        applyLayout();
        persistWindows();
        dom.deskTitle.textContent = "未打开对话";
        toast("对话已关闭，记录仍保留在左侧");
    }

    function deleteConversation(key) {
        if (state.confirmDelete !== key) {
            state.confirmDelete = key;
            clearTimeout(state.confirmTimer);
            state.confirmTimer = setTimeout(() => {
                state.confirmDelete = null;
                renderRail();
            }, 3200);
            renderRail();
            return;
        }
        state.confirmDelete = null;
        clearTimeout(state.confirmTimer);
        const conv = convOf(key);
        if (!conv) return;
        closeWindow(key, { silent: true });
        state.conversations = state.conversations.filter((item) => item.key !== key);
        persistConversations();
        fetch(`/api/history/${encodeURIComponent(conv.sessionId)}`, { method: "DELETE" }).catch(() => {});
        renderRail();
        renderTabs();
        applyLayout();
        persistWindows();
        toast("对话已删除");
    }

    /* ----------------------------------------------------------
       左侧对话列表
       ---------------------------------------------------------- */

    function renderRail() {
        state.conversations.sort((a, b) => b.updatedAt - a.updatedAt);
        if (dom.convCount) dom.convCount.textContent = String(state.conversations.length);

        if (!state.conversations.length) {
            dom.convList.innerHTML = `
                <div class="rail__empty">
                    <strong>还没有对话</strong>
                    <span>从上方新建一个，或回到首页选择一个示例资料库。</span>
                </div>`;
            return;
        }

        const groups = [
            { label: "已打开", items: state.conversations.filter((conv) => state.windows.includes(conv.key)) },
            { label: "最近", items: state.conversations.filter((conv) => !state.windows.includes(conv.key)) },
        ];

        dom.convList.innerHTML = groups.filter((group) => group.items.length).map((group) => `
            <div class="rail__group">
                <p class="rail__group-label">${group.label}</p>
                ${group.items.map((conv) => {
                    const rt = runtimes.get(conv.key);
                    const active = conv.key === state.active;
                    const armed = state.confirmDelete === conv.key;
                    return `
                    <div class="conv ${active ? "is-active" : ""}" data-conv="${escapeHtml(conv.key)}" role="button" tabindex="0">
                        <span class="conv__glyph ${conv.kind === "demo" ? "is-demo" : ""}">${conv.kind === "demo" ? "悟" : "P"}</span>
                        <div class="conv__body">
                            <p class="conv__title">${escapeHtml(trimText(conv.title, 22))}</p>
                            <p class="conv__preview">${escapeHtml(trimText(conv.preview || conv.baseTitle, 30))}</p>
                        </div>
                        <span class="conv__side">
                            ${rt?.streaming ? `<i class="conv__ping" aria-label="生成中"></i>` : `<time>${escapeHtml(relativeTime(conv.updatedAt))}</time>`}
                            <button class="conv__del ${armed ? "is-armed" : ""}" data-del="${escapeHtml(conv.key)}"
                                    aria-label="${armed ? "确认删除" : "删除对话"}">${armed ? "确认" : "×"}</button>
                        </span>
                    </div>`;
                }).join("")}
            </div>`).join("");
    }

    dom.convList.addEventListener("click", (event) => {
        const del = event.target.closest("[data-del]");
        if (del) {
            event.stopPropagation();
            deleteConversation(del.dataset.del);
            return;
        }
        const item = event.target.closest("[data-conv]");
        if (item) openConversation(item.dataset.conv);
    });

    dom.convList.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const item = event.target.closest("[data-conv]");
        if (!item) return;
        event.preventDefault();
        openConversation(item.dataset.conv);
    });

    /* ----------------------------------------------------------
       标签页
       ---------------------------------------------------------- */

    function renderTabs() {
        if (!dom.tabs) return;
        dom.tabs.innerHTML = state.windows.map((key) => {
            const conv = convOf(key);
            if (!conv) return "";
            const rt = runtimes.get(key);
            return `
            <div class="tab ${key === state.active ? "is-active" : ""}" data-tab="${escapeHtml(key)}" role="tab"
                 aria-selected="${key === state.active ? "true" : "false"}" tabindex="0">
                <span class="tab__dot ${rt?.streaming ? "is-busy" : ""}"></span>
                <span class="tab__title">${escapeHtml(trimText(conv.title, 18))}</span>
                <span class="tab__meta">${escapeHtml(conv.baseTitle)}</span>
                <button class="tab__close" data-tab-close="${escapeHtml(key)}" aria-label="关闭窗口">
                    <svg viewBox="0 0 12 12" fill="none"><path d="m3 3 6 6M9 3 3 9" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
                </button>
            </div>`;
        }).join("");
    }

    dom.tabs?.addEventListener("click", (event) => {
        const close = event.target.closest("[data-tab-close]");
        if (close) {
            event.stopPropagation();
            closeWindow(close.dataset.tabClose);
            return;
        }
        const tab = event.target.closest("[data-tab]");
        if (tab) setActive(tab.dataset.tab);
    });

    dom.tabs?.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        const tab = event.target.closest("[data-tab]");
        if (!tab) return;
        event.preventDefault();
        setActive(tab.dataset.tab);
    });

    dom.closeAll.addEventListener("click", closeAllWindows);

    dom.railToggle?.addEventListener("click", () => {
        dom.workspace?.classList.toggle("is-rail-open");
    });

    dom.railClose?.addEventListener("click", () => {
        dom.workspace?.classList.remove("is-rail-open");
    });

    document.addEventListener("click", (event) => {
        if (!dom.workspace?.classList.contains("is-rail-open")) return;
        if (event.target.closest(".rail") || event.target.closest("#railToggle")) return;
        dom.workspace.classList.remove("is-rail-open");
    });

    /* ----------------------------------------------------------
       新建对话菜单
       ---------------------------------------------------------- */

    function renderNewMenu() {
        const demos = state.examples.map((demo) => ({
            key: `demo:${demo.id}`,
            title: demo.title,
            hint: demo.featured ? "深度示例" : "示例",
            glyph: demo.featured ? "悟" : (demo.title || "?").slice(0, 1),
            featured: Boolean(demo.featured),
        }));
        const projects = state.projects.filter((p) => p.status === "ready").map((p) => ({
            key: `project:${p.id}`,
            title: p.title || "未命名项目",
            hint: `${p.doc_count || 0} 个切片`,
            glyph: "P",
            featured: false,
        }));

        dom.newMenu.innerHTML = `
            <div class="rail-menu__group">
                <p>资料库</p>
                ${demos.map((item) => `
                    <button role="menuitem" data-new="${escapeHtml(item.key)}" class="${item.featured ? "is-featured" : ""}">
                        <span>${escapeHtml(item.glyph)}</span>
                        <strong>${escapeHtml(item.title)}</strong>
                        <em>${escapeHtml(item.hint)}</em>
                    </button>`).join("")}
            </div>
            ${projects.length ? `
            <div class="rail-menu__group">
                <p>我的项目</p>
                ${projects.map((item) => `
                    <button role="menuitem" data-new="${escapeHtml(item.key)}">
                        <span>${escapeHtml(item.glyph)}</span>
                        <strong>${escapeHtml(item.title)}</strong>
                        <em>${escapeHtml(item.hint)}</em>
                    </button>`).join("")}
            </div>` : ""}
            <div class="rail-menu__foot">
                <button role="menuitem" data-new="upload">上传 PDF 新建项目</button>
            </div>`;
    }

    function closeNewMenu() {
        dom.newMenu.hidden = true;
        dom.newConvBtn.setAttribute("aria-expanded", "false");
    }

    dom.newConvBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        if (!dom.newMenu.hidden) {
            closeNewMenu();
            return;
        }
        renderNewMenu();
        dom.newMenu.hidden = false;
        dom.newConvBtn.setAttribute("aria-expanded", "true");
    });

    dom.newMenu.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-new]");
        if (!btn) return;
        const value = btn.dataset.new;
        closeNewMenu();
        if (value === "upload") {
            goCreate(true);
            return;
        }
        const [kind, id] = value.split(":");
        if (kind === "demo") enterDemo(id, null, { forceNew: true });
        if (kind === "project") enterProject(id, null, { forceNew: true });
    });

    document.addEventListener("click", (event) => {
        if (dom.newMenu.hidden) return;
        if (event.target.closest("#newMenu") || event.target.closest("#newConvBtn")) return;
        closeNewMenu();
    });

    /* ----------------------------------------------------------
       对话窗格
       ---------------------------------------------------------- */

    function buildPane(conv) {
        if (runtimes.has(conv.key)) return runtimes.get(conv.key);

        const el = document.createElement("section");
        el.className = "pane";
        el.dataset.key = conv.key;
        el.setAttribute("role", "tabpanel");
        el.setAttribute("aria-label", conv.title);
        el.innerHTML = `
            <header class="pane__top">
                <span class="pane__glyph ${conv.kind === "demo" ? "is-demo" : ""}">${conv.kind === "demo" ? "悟" : "PDF"}</span>
                <div class="pane__id">
                    <p class="pane__title">${escapeHtml(conv.title)}</p>
                    <p class="pane__meta">${escapeHtml(conv.meta || conv.subtitle || "")}</p>
                </div>
                <button class="pane__tool" data-pane-clear title="清空这个对话">清空</button>
                <button class="pane__close" data-pane-close aria-label="关闭窗口">
                    <svg viewBox="0 0 14 14" fill="none"><path d="m3.5 3.5 7 7M10.5 3.5l-7 7" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>
                </button>
            </header>
            <div class="pane__scroll">
                <div class="chat__intro" data-intro>
                    <p class="eyebrow">${conv.kind === "demo" ? "示例资料库" : "我的项目"}</p>
                    <h2>${escapeHtml(conv.baseTitle)}</h2>
                    <p>${escapeHtml(conv.description || conv.subtitle || "")}</p>
                    <div class="ask-chips" data-chips>
                        ${(conv.questions || []).slice(0, 4).map((q) => `<button type="button">${escapeHtml(q)}</button>`).join("")}
                    </div>
                    <p class="chat__intro-note">回答只基于本项目资料，引用可展开核对。</p>
                </div>
                <div class="messages" data-messages aria-live="polite"></div>
            </div>
            <div class="composer-wrap">
                <form class="composer" data-composer autocomplete="off">
                    <textarea rows="1" data-input placeholder="问点什么…也可以直接说话" aria-label="输入问题"></textarea>
                    <button class="mic" data-mic type="button" aria-label="语音输入" aria-pressed="false" title="语音输入（需要麦克风权限）">
                        <svg viewBox="0 0 20 20" fill="none"><rect x="7.6" y="2.6" width="4.8" height="9" rx="2.4" stroke="currentColor" stroke-width="1.5"/><path d="M4.8 9.2a5.2 5.2 0 0 0 10.4 0M10 14.4v3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                        <span class="mic__bars" aria-hidden="true"><i></i><i></i><i></i></span>
                    </button>
                    <button class="send" data-send type="submit" aria-label="发送">
                        <svg viewBox="0 0 20 20" fill="none"><path d="M10 15V5m0 0-4.2 4.2M10 5l4.2 4.2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                </form>
                <p class="composer__hint">Enter 发送 · Shift + Enter 换行 · 点麦克风可语音提问</p>
            </div>`;

        dom.panes.appendChild(el);

        const rt = {
            key: conv.key,
            conv,
            root: el,
            scroll: el.querySelector(".pane__scroll"),
            intro: el.querySelector("[data-intro]"),
            messages: el.querySelector("[data-messages]"),
            chips: el.querySelector("[data-chips]"),
            composer: el.querySelector("[data-composer]"),
            input: el.querySelector("[data-input]"),
            sendBtn: el.querySelector("[data-send]"),
            mic: el.querySelector("[data-mic]"),
            stopVoice: null,
            titleEl: el.querySelector(".pane__title"),
            metaEl: el.querySelector(".pane__meta"),
            streaming: false,
            es: null,
            node: null,
            raw: "",
            cancelStream: null,
            loaded: false,
            skipClarify: false,
            pending: null,
        };
        runtimes.set(conv.key, rt);

        rt.chips.querySelectorAll("button").forEach((chip) => {
            chip.addEventListener("click", () => sendMessage(conv.key, chip.textContent.trim()));
        });

        rt.input.addEventListener("input", () => resizeInput(rt.input));
        rt.input.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
                event.preventDefault();
                rt.composer.requestSubmit();
            }
        });
        rt.composer.addEventListener("submit", (event) => {
            event.preventDefault();
            rt.stopVoice?.();
            if (rt.streaming) {
                stopStreaming(conv.key, true);
                return;
            }
            const text = rt.input.value.trim();
            if (!text) return;
            sendMessage(conv.key, text);
        });
        rt.sendBtn.addEventListener("click", (event) => {
            if (rt.streaming) {
                event.preventDefault();
                stopStreaming(conv.key, true);
            }
        });

        setupVoice(rt);
        el.querySelector("[data-pane-close]").addEventListener("click", () => closeWindow(conv.key));
        el.querySelector("[data-pane-clear]").addEventListener("click", () => clearConversation(conv.key));
        el.addEventListener("pointerdown", () => {
            if (state.active !== conv.key) setActive(conv.key);
        }, { passive: true });

        if (conv.fresh) {
            rt.loaded = true;
        } else {
            loadHistory(conv.key);
        }

        applyLayout();
        return rt;
    }

    function resizeInput(input) {
        input.style.height = "auto";
        input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
    }

    /* ----------------------------------------------------------
       语音输入（Web Speech API）
       ---------------------------------------------------------- */

    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;

    function setupVoice(rt) {
        const btn = rt.mic;
        if (!btn) return;

        if (!SpeechRecognitionCtor) {
            btn.classList.add("is-unavailable");
            btn.title = "当前浏览器不支持语音输入";
            btn.addEventListener("click", () => toast("当前浏览器不支持语音输入，建议使用 Chrome 或 Edge"));
            return;
        }

        const rec = new SpeechRecognitionCtor();
        rec.lang = "zh-CN";
        rec.continuous = true;
        rec.interimResults = true;
        rec.maxAlternatives = 1;

        let listening = false;
        let manualStop = false;
        let baseText = "";
        let finalText = "";
        let interimText = "";
        let restartTimer = 0;

        const merge = () => {
            const speech = `${finalText}${interimText}`.trim();
            if (!baseText) return speech;
            if (!speech) return baseText;
            return /[\s，。！？；：,.!?;:]$/.test(baseText) ? `${baseText}${speech}` : `${baseText} ${speech}`;
        };

        const syncInput = () => {
            rt.input.value = merge();
            resizeInput(rt.input);
        };

        const setUi = (on) => {
            listening = on;
            btn.classList.toggle("is-listening", on);
            btn.setAttribute("aria-pressed", on ? "true" : "false");
            rt.composer.classList.toggle("is-listening", on);
            rt.input.placeholder = on ? "正在听…说完再点一次麦克风" : "问点什么…也可以直接说话";
        };

        const stop = (silent = false) => {
            manualStop = true;
            window.clearTimeout(restartTimer);
            if (listening) {
                try { rec.stop(); } catch (e) { /* ignore */ }
            }
            setUi(false);
            const merged = merge().trim();
            if (!silent && merged && merged !== baseText.trim()) {
                toast("语音已转成文字，确认后可以发送");
            }
            rt.input.focus();
        };
        rt.stopVoice = () => stop(true);

        const start = () => {
            baseText = rt.input.value.trim();
            finalText = "";
            interimText = "";
            manualStop = false;
            setUi(true);
            try {
                rec.start();
            } catch (e) {
                setUi(false);
                toast("麦克风启动失败，请稍后再试");
            }
        };

        btn.addEventListener("click", () => {
            if (listening) stop();
            else start();
        });

        rec.addEventListener("result", (event) => {
            let finalChunk = "";
            let interimChunk = "";
            for (let i = event.resultIndex; i < event.results.length; i += 1) {
                const item = event.results[i];
                if (!item || !item[0]) continue;
                if (item.isFinal) finalChunk += item[0].transcript;
                else interimChunk += item[0].transcript;
            }
            finalText += finalChunk;
            interimText = interimChunk;
            syncInput();
        });

        rec.addEventListener("error", (event) => {
            const code = event.error || "";
            manualStop = true;
            setUi(false);
            if (code === "not-allowed" || code === "service-not-allowed") {
                toast("麦克风权限被拒绝，请在浏览器地址栏重新授权");
            } else if (code === "no-speech") {
                toast("没有听到声音，可以再说一次");
            } else if (code === "audio-capture") {
                toast("没有检测到可用的麦克风");
            } else if (code === "network") {
                toast("语音服务网络异常，请稍后再试");
            } else if (code !== "aborted") {
                toast("语音输入失败，请重试");
            }
        });

        rec.addEventListener("end", () => {
            if (manualStop) {
                setUi(false);
                return;
            }
            restartTimer = window.setTimeout(() => {
                if (manualStop) return;
                try { rec.start(); } catch (e) { setUi(false); }
            }, 240);
        });

        rec.addEventListener("start", () => setUi(true));
    }

    function scrollToBottom(rt, force = false) {
        const el = rt.scroll;
        const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 140;
        if (!force && !nearBottom) return;
        requestAnimationFrame(() => {
            el.scrollTo({ top: el.scrollHeight, behavior: reduceMotion ? "auto" : "smooth" });
        });
    }

    async function loadHistory(key) {
        const rt = runtimes.get(key);
        if (!rt || rt.loaded) return;
        rt.loaded = true;
        try {
            const res = await fetch(`/api/history/${encodeURIComponent(rt.conv.sessionId)}`);
            if (!res.ok) return;
            const data = await res.json();
            const items = Array.isArray(data.items) ? data.items : [];
            if (!items.length) return;
            if (rt.streaming || rt.messages.children.length) return;

            rt.intro.hidden = true;
            rt.messages.innerHTML = "";
            items.forEach((item) => {
                if (item.role === "user") {
                    appendUserMessage(rt, item.text || "", false);
                } else {
                    const node = appendBotMessage(rt, { animate: false });
                    node.thinking.hidden = true;
                    node.answer.innerHTML = renderMarkdown(item.text || "");
                }
            });
            scrollToBottom(rt, true);
        } catch (e) { /* 历史加载失败不阻塞新对话 */ }
    }

    function hideIntro(rt) {
        rt.intro.hidden = true;
    }

    function appendUserMessage(rt, text, animate = true) {
        hideIntro(rt);
        const el = document.createElement("div");
        el.className = "msg msg--user";
        if (!animate) el.style.animation = "none";
        el.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
        rt.messages.appendChild(el);
        scrollToBottom(rt);
        return el;
    }

    function appendRefineNote(rt, text, anchorNode = null) {
        const el = document.createElement("div");
        el.className = "msg msg--refine";
        el.innerHTML = `<span>已细化追问</span>${escapeHtml(text)}`;
        if (anchorNode && anchorNode.isConnected) {
            anchorNode.insertAdjacentElement("afterend", el);
        } else {
            rt.messages.appendChild(el);
        }
        scrollToBottom(rt);
    }

    function appendBotMessage(rt, options = {}) {
        const el = document.createElement("div");
        el.className = "msg msg--bot";
        if (options.animate === false) el.style.animation = "none";
        el.innerHTML = `
            <div class="bot-avatar" aria-hidden="true">z</div>
            <div class="bot-body">
                <div class="bot-name">
                    <span>zRAG · 资料库</span>
                </div>
                <div class="bubble bubble--bot">
                    <div class="trace" data-trace hidden>
                        <div class="trace__head">
                            <span class="thinking" data-thinking>
                                <span class="thinking__bars"><i></i><i></i><i></i><i></i></span>
                                <span class="thinking__label" data-thinking-label>正在检索资料…</span>
                            </span>
                            <span class="trace__meta">
                                <span class="trace__pct" data-trace-pct>0%</span>
                                <span class="trace__timer" data-trace-timer>0.0s</span>
                            </span>
                        </div>
                        <div class="trace__track">
                            <span class="trace__rail"><i data-trace-beam></i></span>
                            <ol class="trace__steps" data-trace-steps></ol>
                        </div>
                    </div>
                    <div class="answer"></div>
                    <div class="extra"></div>
                </div>
            </div>`;
        rt.messages.appendChild(el);
        scrollToBottom(rt);
        return {
            root: el,
            bubble: el.querySelector(".bubble"),
            answer: el.querySelector(".answer"),
            thinking: el.querySelector("[data-thinking]"),
            thinkingLabel: el.querySelector("[data-thinking-label]"),
            stage: null,
            extra: el.querySelector(".extra"),
            traceEl: el.querySelector("[data-trace]"),
            traceSteps: el.querySelector("[data-trace-steps]"),
            traceBeam: el.querySelector("[data-trace-beam]"),
            tracePct: el.querySelector("[data-trace-pct]"),
            traceTimerEl: el.querySelector("[data-trace-timer]"),
            flow: null,
            traceTimer: 0,
            traceElapsed: 0,
            elapsedBase: 0,
            generating: false,
        };
    }

    function setStage(node, label) {
        if (!node) return;
        if (!label) {
            node.classList.remove("is-on");
            return;
        }
        node.textContent = label;
        node.classList.add("is-on");
    }

    /* ----------------------------------------------------------
       生成步骤进度动画
       ---------------------------------------------------------- */

    function traceStart(node, kind) {
        if (!node || !node.traceEl) return;
        const flow = TRACE_FLOWS[kind] || TRACE_FLOWS.upload;
        node.flow = flow;
        node.generating = false;
        node.traceEl.hidden = false;
        node.traceEl.classList.remove("is-done", "is-error", "is-stopped", "is-paused");
        node.traceEl.style.setProperty("--n", String(flow.length));
        node.traceSteps.innerHTML = flow.map((step, index) => `
            <li class="trace__step" data-step="${index}">
                <i class="trace__node"></i>
                <span>${escapeHtml(step.label)}</span>
            </li>`).join("");
        node.traceBeam.style.width = "0%";
        node.tracePct.textContent = "0%";
        node.elapsedBase = performance.now();
        node.traceElapsed = 0;
        node.traceTimerEl.textContent = "0.0s";
        window.clearInterval(node.traceTimer);
        node.traceTimer = window.setInterval(() => {
            node.traceElapsed = (performance.now() - node.elapsedBase) / 1000;
            node.traceTimerEl.textContent = `${node.traceElapsed.toFixed(1)}s`;
        }, 100);
        node.traceSteps.children[0]?.classList.add("is-active");
    }

    function traceSync(node, running = [], done = []) {
        if (!node || !node.flow || !node.traceSteps || node.generating) return;
        const hit = (list, step) => (step.match || []).some((name) => list.includes(name));
        const doneIdx = node.flow.map((step, i) => (hit(done, step) ? i : -1)).filter((i) => i >= 0);
        const runIdx = node.flow.map((step, i) => (hit(running, step) ? i : -1)).filter((i) => i >= 0);
        const reached = Math.max(-1, ...doneIdx, ...runIdx);

        let doneCount = 0;
        let activeIndex = -1;
        node.flow.forEach((step, i) => {
            const li = node.traceSteps.children[i];
            if (!li) return;
            const isDone = (doneIdx.includes(i) && !runIdx.includes(i)) || i < reached;
            const isActive = !isDone && (runIdx.includes(i) || i === reached);
            li.classList.toggle("is-done", isDone);
            li.classList.toggle("is-active", isActive);
            if (isDone) doneCount += 1;
            if (isActive) activeIndex = i;
        });

        const pct = Math.min(96, Math.round(((doneCount + (activeIndex >= 0 ? 0.5 : 0)) / node.flow.length) * 100));
        node.traceBeam.style.width = `${pct}%`;
        node.tracePct.textContent = `${pct}%`;
    }

    function traceLabel(node, text) {
        if (!node || !node.traceEl || !text) return;
        node.traceEl.classList.remove("is-paused");
        if (node.thinkingLabel) node.thinkingLabel.textContent = text;
    }

    function traceGenerating(node) {
        if (!node || !node.flow || node.generating) return;
        node.generating = true;
        Array.from(node.traceSteps.children).forEach((li, i) => {
            const last = i === node.flow.length - 1;
            li.classList.toggle("is-done", !last);
            li.classList.toggle("is-active", last);
        });
        node.traceBeam.style.width = "92%";
        node.tracePct.textContent = "92%";
        traceLabel(node, "正在逐 token 生成答案…");
    }

    function traceFinish(node, summary) {
        if (!node || !node.traceEl) return;
        window.clearInterval(node.traceTimer);
        node.traceTimer = 0;
        const total = Math.max(node.traceElapsed || 0, 0.1);
        node.traceEl.classList.add("is-done");
        node.traceEl.classList.remove("is-error", "is-stopped", "is-paused");
        Array.from(node.traceSteps.children).forEach((li) => {
            li.classList.add("is-done");
            li.classList.remove("is-active");
        });
        node.traceBeam.style.width = "100%";
        node.tracePct.textContent = "100%";
        if (node.thinkingLabel) node.thinkingLabel.textContent = summary || "已完成";
        node.traceTimerEl.textContent = `${total.toFixed(1)}s`;
    }

    function traceStop(node, message, mode = "stopped") {
        if (!node || !node.traceEl) return;
        window.clearInterval(node.traceTimer);
        node.traceTimer = 0;
        node.traceEl.classList.add(mode === "error" ? "is-error" : "is-stopped");
        node.traceEl.classList.remove("is-paused", "is-done");
        Array.from(node.traceSteps.children).forEach((li) => li.classList.remove("is-active"));
        if (message && node.thinkingLabel) node.thinkingLabel.textContent = message;
        node.traceTimerEl.textContent = "—";
    }

    function tracePause(node, message) {
        if (!node || !node.traceEl) return;
        window.clearInterval(node.traceTimer);
        node.traceTimer = 0;
        node.traceEl.classList.add("is-paused");
        Array.from(node.traceSteps.children).forEach((li) => li.classList.remove("is-active"));
        if (message && node.thinkingLabel) node.thinkingLabel.textContent = message;
    }

    function traceResume(node) {
        if (!node || !node.traceEl) return;
        node.traceEl.classList.remove("is-paused", "is-stopped", "is-error");
        if (!node.traceSteps.querySelector(".is-active")) {
            node.traceSteps.children[0]?.classList.add("is-active");
        }
        if (node.traceTimer || node.traceEl.classList.contains("is-done")) return;
        node.elapsedBase = performance.now() - (node.traceElapsed || 0) * 1000;
        node.traceTimer = window.setInterval(() => {
            node.traceElapsed = (performance.now() - node.elapsedBase) / 1000;
            node.traceTimerEl.textContent = `${node.traceElapsed.toFixed(1)}s`;
        }, 100);
    }

    function setStreaming(key, on) {
        const rt = runtimes.get(key);
        if (!rt) return;
        rt.streaming = on;
        rt.sendBtn.classList.toggle("is-stop", on);
        rt.sendBtn.disabled = false;
        rt.sendBtn.title = on ? "停止生成" : "发送";
        renderTabs();
        renderRail();
        updateTabMeta(key);
    }

    function updateTabMeta(key) {
        const conv = convOf(key);
        const rt = runtimes.get(key);
        if (!conv || !rt) return;
        rt.titleEl.textContent = conv.title;
        rt.metaEl.textContent = conv.meta || conv.subtitle || "";
        if (state.active === key) {
            dom.deskTitle.textContent = conv.title;
        }
    }

    function stopStreaming(key, notify = false) {
        const rt = runtimes.get(key);
        if (!rt) return;
        if (rt.es) {
            rt.es.close();
            rt.es = null;
        }
        if (rt.cancelStream) {
            rt.cancelStream();
            rt.cancelStream = null;
        }
        if (rt.node) {
            traceStop(rt.node, "已停止生成");
            rt.node = null;
        }
        setStreaming(key, false);
        if (notify) toast("已停止生成");
    }

    /* ----------------------------------------------------------
       发送与澄清
       ---------------------------------------------------------- */

    async function sendMessage(key, text) {
        const rt = runtimes.get(key);
        if (!rt) return;
        const message = String(text || "").trim();
        if (!message || rt.streaming) return;

        rt.input.value = "";
        resizeInput(rt.input);
        const userNode = appendUserMessage(rt, message);

        const conv = rt.conv;
        if (!conv.userTitled) {
            conv.userTitled = true;
            conv.title = trimText(message, 20);
            conv.updatedAt = Date.now();
            persistConversations();
            updateTabMeta(key);
        }

        const node = appendBotMessage(rt);
        rt.node = node;
        rt.raw = "";
        rt.skipClarify = false;
        traceStart(node, conv.kind);
        setStreaming(key, true);

        if (conv.kind === "demo") {
            node.thinkingLabel.textContent = "正在理解你的问题…";
            const clarify = await requestClarify(conv.projectId, message);
            if (clarify && clarify.needed && (clarify.entities || []).length) {
                setStreaming(key, false);
                tracePause(node, "等待你确认检索方向…");
                rt.pending = { node, original: message, userNode };
                openClarify(key, message, clarify);
                return;
            }
        }

        await requestAnswer(key, message, node);
    }

    async function requestClarify(projectId, message) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 2600);
        try {
            const res = await fetch("/api/clarify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ project_id: projectId, message }),
                signal: controller.signal,
            });
            if (!res.ok) return null;
            return await res.json();
        } catch (e) {
            return null;
        } finally {
            clearTimeout(timer);
        }
    }

    async function requestAnswer(key, message, node) {
        const rt = runtimes.get(key);
        if (!rt) return;
        rt.node = node;
        rt.raw = "";
        if (!node.flow) {
            traceStart(node, rt.conv.kind);
        } else {
            traceResume(node);
        }
        node.thinking.hidden = false;
        traceLabel(node, "正在理解你的问题…");
        setStreaming(key, true);
        node.answer.innerHTML = "";

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    project_id: rt.conv.projectId,
                    message,
                    session_id: rt.conv.sessionId,
                }),
            });

            if (!res.ok) {
                const data = await res.json().catch(() => ({}));
                throw new Error(data.message || "请求失败");
            }

            const data = await res.json();
            consumeStream(key, data.task_id, node);
        } catch (e) {
            finishWithError(rt, node, e.message || "请求失败");
        }
    }

    function consumeStream(key, taskId, node) {
        const rt = runtimes.get(key);
        if (!rt) return;
        const es = new EventSource(`/api/stream/${encodeURIComponent(taskId)}`);
        rt.es = es;
        let settled = false;
        let raw = "";
        let renderTimer = 0;

        const scheduleRender = () => {
            if (renderTimer) return;
            renderTimer = window.setTimeout(() => {
                renderTimer = 0;
                node.answer.innerHTML = `${renderMarkdown(raw)}<span class="caret"></span>`;
                scrollToBottom(rt);
            }, 55);
        };

        rt.cancelStream = () => {
            if (settled) return;
            settled = true;
            if (renderTimer) {
                clearTimeout(renderTimer);
                renderTimer = 0;
            }
            traceStop(node, "已停止生成");
            node.answer.innerHTML = renderMarkdown(raw || "已停止生成");
            rt.raw = raw;
        };

        const finalize = (finalData) => {
            if (settled) return;
            settled = true;
            rt.cancelStream = null;
            if (renderTimer) {
                clearTimeout(renderTimer);
                renderTimer = 0;
            }

            const answer = (finalData && typeof finalData.answer === "string" && finalData.answer.trim())
                ? finalData.answer
                : raw;

            const cited = Array.isArray(finalData?.sources) ? finalData.sources.length : 0;
            traceFinish(node, cited ? `已完成 · 引用 ${cited} 段资料` : "已完成");
            node.answer.innerHTML = renderMarkdown(answer || "（这次没有生成内容，可以再问一次）");
            renderExtras(node, finalData || {});

            rt.raw = answer;
            rt.node = null;
            rt.conv.answered = true;
            rt.conv.preview = trimText(stripMarkdown(answer), 60);
            rt.conv.updatedAt = Date.now();
            persistConversations();
            es.close();
            rt.es = null;
            setStreaming(key, false);
            updateTabMeta(key);
            renderRail();
            scrollToBottom(rt);
            setTimeout(() => rt.input.focus(), 60);
        };

        const fail = (message) => {
            if (settled) return;
            settled = true;
            rt.cancelStream = null;
            if (renderTimer) clearTimeout(renderTimer);
            es.close();
            rt.es = null;
            rt.node = null;
            setStreaming(key, false);
            traceStop(node, message, "error");
            node.bubble.classList.add("is-error");
            node.answer.innerHTML = `${renderMarkdown(raw)}<p style="margin-top:${raw ? "10px" : "0"}">${escapeHtml(message)}</p>`;
            scrollToBottom(rt);
        };

        es.addEventListener("progress", (event) => {
            try {
                const data = JSON.parse(event.data || "{}");
                const allRunning = data.running_list || [];
                const running = allRunning.filter((name) => name !== "生成答案");
                traceSync(node, allRunning, data.done_list || []);
                if (running.length) {
                    traceLabel(node, `正在${running.join(" · ")}…`);
                } else if (allRunning.includes("生成答案")) {
                    traceLabel(node, "正在组织答案…");
                } else if (data.status === "completed") {
                    traceLabel(node, "已核对原文");
                }
            } catch (e) { /* ignore */ }
        });

        es.addEventListener("delta", (event) => {
            try {
                const data = JSON.parse(event.data || "{}");
                const delta = data.delta || "";
                if (!delta) return;
                raw += delta;
                traceGenerating(node);
                scheduleRender();
            } catch (e) { /* ignore */ }
        });

        es.addEventListener("final", (event) => {
            try {
                finalize(JSON.parse(event.data || "{}"));
            } catch (e) {
                finalize({});
            }
        });

        es.addEventListener("error", (event) => {
            if (event.data) {
                try {
                    const data = JSON.parse(event.data);
                    fail(data.message || "服务执行失败，请重试");
                    return;
                } catch (e) { /* fallthrough */ }
            }
            if (!settled) fail("连接中断了，请重新提问");
        });
    }

    function renderExtras(node, data) {
        const pieces = [];
        const rawImages = Array.isArray(data.image_urls) ? data.image_urls : [];
        const images = Array.from(new Set(rawImages.map(normalizeUrl).filter(isSafeUrl)));

        if (images.length) {
            pieces.push(`<div class="bubble-images">${images.map((url) => `
                <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">
                    <img src="${escapeHtml(url)}" alt="参考资料图片" loading="lazy"/>
                </a>`).join("")}</div>`);
        }

        const sources = Array.isArray(data.sources) ? data.sources : [];
        if (sources.length) {
            pieces.push(`
                <details class="sources">
                    <summary>
                        <svg class="chev" viewBox="0 0 12 12" fill="none"><path d="M4 2.5 7.5 6 4 9.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
                        引用 ${sources.length} 段资料
                    </summary>
                    <div class="sources__list">
                        ${sources.map((source) => `
                            <div class="source">
                                ${source.image ? `<img class="source__thumb" src="${escapeHtml(normalizeUrl(source.image))}" alt="" loading="lazy"/>` : `<span class="source__index">${String(source.index).padStart(2, "0")}</span>`}
                                <div>
                                    <p class="source__title">${escapeHtml(source.title || "参考资料")}</p>
                                    <p class="source__snippet">${escapeHtml(source.content || "")}</p>
                                </div>
                            </div>`).join("")}
                    </div>
                </details>`);
        }

        node.extra.innerHTML = pieces.join("");
    }

    function finishWithError(rt, node, message) {
        traceStop(node, message, "error");
        node.bubble.classList.add("is-error");
        node.answer.innerHTML = `<p>${escapeHtml(message)}</p>`;
        rt.node = null;
        setStreaming(rt.key, false);
        scrollToBottom(rt);
    }

    async function clearConversation(key) {
        const rt = runtimes.get(key);
        if (!rt) return;
        if (rt.streaming) {
            toast("请先停止当前回答");
            return;
        }
        try {
            await fetch(`/api/history/${encodeURIComponent(rt.conv.sessionId)}`, { method: "DELETE" });
            rt.messages.innerHTML = "";
            rt.intro.hidden = false;
            rt.conv.preview = "";
            rt.conv.answered = false;
            rt.conv.updatedAt = Date.now();
            persistConversations();
            renderRail();
            toast("对话已清空");
            rt.input.focus();
        } catch (e) {
            toast("清空失败，请稍后重试");
        }
    }

    /* ----------------------------------------------------------
       澄清弹窗
       ---------------------------------------------------------- */

    function openClarify(key, original, data) {
        state.clarify = {
            key,
            original,
            entity: (data.matched_entities && data.matched_entities[0]) || "",
            intents: new Set(data.matched_intents || []),
            data,
        };

        dom.clarifyTitle.textContent = data.question || "再确认一下，你想了解哪一块？";
        dom.clarifyHint.textContent = data.hint || "";

        dom.clarifyEntities.innerHTML = (data.entities || []).map((item) => `
            <button type="button" class="clarify-chip ${item.name === state.clarify.entity ? "is-on" : ""}" data-entity="${escapeHtml(item.name)}">
                <strong>${escapeHtml(item.name)}</strong>
                <span>${escapeHtml(item.hint || "")}</span>
            </button>`).join("");

        dom.clarifyIntents.innerHTML = (data.intents || []).map((item) => `
            <button type="button" class="clarify-chip clarify-chip--intent ${state.clarify.intents.has(item.label) ? "is-on" : ""}" data-intent="${escapeHtml(item.label)}">
                <strong>${escapeHtml(item.label)}</strong>
                <span>${escapeHtml(item.value)}</span>
            </button>`).join("");

        dom.clarifyExtra.value = "";
        dom.clarifyModal.hidden = false;
        document.body.classList.add("is-modal");
        setTimeout(() => dom.clarifySubmit.focus(), 40);
    }

    function closeClarify(continueWithOriginal) {
        if (!state.clarify) {
            dom.clarifyModal.hidden = true;
            document.body.classList.remove("is-modal");
            return;
        }
        const { key, original } = state.clarify;
        const rt = runtimes.get(key);
        const pending = rt?.pending;
        state.clarify = null;
        dom.clarifyModal.hidden = true;
        document.body.classList.remove("is-modal");

        if (rt && pending && continueWithOriginal) {
            rt.pending = null;
            requestAnswer(key, original, pending.node);
        }
    }

    dom.clarifyEntities.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-entity]");
        if (!btn || !state.clarify) return;
        state.clarify.entity = state.clarify.entity === btn.dataset.entity ? "" : btn.dataset.entity;
        dom.clarifyEntities.querySelectorAll("[data-entity]").forEach((chip) => {
            chip.classList.toggle("is-on", chip.dataset.entity === state.clarify.entity);
        });
    });

    dom.clarifyIntents.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-intent]");
        if (!btn || !state.clarify) return;
        const label = btn.dataset.intent;
        if (state.clarify.intents.has(label)) state.clarify.intents.delete(label);
        else state.clarify.intents.add(label);
        btn.classList.toggle("is-on", state.clarify.intents.has(label));
    });

    dom.clarifySkip.addEventListener("click", () => closeClarify(true));
    dom.clarifyClose.addEventListener("click", () => closeClarify(true));

    dom.clarifyExtra.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
            event.preventDefault();
            dom.clarifySubmit.click();
        }
    });

    dom.clarifyModal.addEventListener("click", (event) => {
        if (event.target.closest("[data-close-modal]")) closeClarify(true);
    });

    dom.clarifySubmit.addEventListener("click", () => {
        if (!state.clarify) return;
        const { key, original, entity, intents, data } = state.clarify;
        const rt = runtimes.get(key);
        const pending = rt?.pending;
        if (!rt || !pending) {
            closeClarify(false);
            return;
        }

        const labels = [...intents];
        const values = labels.map((label) => (data.intents || []).find((item) => item.label === label)?.value || label);
        const extra = dom.clarifyExtra.value.trim();
        const parts = [];
        if (entity) parts.push(entity);
        if (values.length) parts.push(`想了解：${values.join("；")}`);
        if (extra) parts.push(`补充：${extra}`);

        let refined = parts.join("。");
        if (!entity && !values.length) refined = original;

        dom.clarifyModal.hidden = true;
        document.body.classList.remove("is-modal");
        state.clarify = null;
        rt.pending = null;

        if (refined && refined !== original) {
            appendRefineNote(rt, refined, pending.userNode);
        }
        requestAnswer(key, refined || original, pending.node);
    });

    /* ----------------------------------------------------------
       上传流程
       ---------------------------------------------------------- */

    function pickFile() {
        if (state.busyUpload) {
            toast("当前文件还在解析中，请稍候");
            return;
        }
        dom.fileInput.click();
    }

    dom.fileInput.addEventListener("change", (event) => {
        const file = event.target.files?.[0];
        event.target.value = "";
        if (file) handleFile(file);
    });

    function bindDragAndDrop() {
        let dragDepth = 0;

        window.addEventListener("dragenter", (event) => {
            if (!event.dataTransfer?.types?.includes("Files")) return;
            dragDepth += 1;
            dom.dragOverlay.classList.add("is-active");
        });

        window.addEventListener("dragleave", () => {
            dragDepth = Math.max(0, dragDepth - 1);
            if (dragDepth === 0) dom.dragOverlay.classList.remove("is-active");
        });

        window.addEventListener("dragover", (event) => {
            event.preventDefault();
            if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
        });

        window.addEventListener("drop", (event) => {
            event.preventDefault();
            dragDepth = 0;
            dom.dragOverlay.classList.remove("is-active");
            const file = event.dataTransfer?.files?.[0];
            if (!file) return;
            if (dom.viewChat.hidden) {
                handleFile(file);
            } else {
                goCreate(false);
                setTimeout(() => handleFile(file), reduceMotion ? 40 : 460);
            }
        });

        dom.dropZone.addEventListener("dragover", (event) => {
            event.preventDefault();
            dom.dropZone.classList.add("is-hover");
        });

        dom.dropZone.addEventListener("dragleave", () => dom.dropZone.classList.remove("is-hover"));
        dom.dropZone.addEventListener("drop", () => dom.dropZone.classList.remove("is-hover"));
    }

    function resetUploadPanel() {
        state.busyUpload = false;
        dom.uploadIdle.hidden = false;
        dom.uploadProgress.hidden = true;
        dom.uploadSteps.innerHTML = "";
        dom.uploadActions.innerHTML = "";
        setBar(0);
        dom.uploadPercent.textContent = "0%";
    }

    function setBar(percent) {
        const value = Math.max(0, Math.min(100, percent));
        dom.uploadBar.style.width = `${value}%`;
        dom.uploadPercent.textContent = `${Math.round(value)}%`;
    }

    function renderSteps(progress = {}, status = "processing") {
        const done = new Set(progress.done_list || []);
        const running = new Set(progress.running_list || []);
        const durations = progress.durations || {};

        dom.uploadSteps.innerHTML = IMPORT_STEPS.map((step) => {
            const isDone = done.has(step.key);
            const isRunning = !isDone && running.has(step.key);
            const cls = isDone ? "is-done" : isRunning ? "is-running" : "";
            const duration = durations[step.key] ? `<span class="dur">${formatDuration(durations[step.key])}</span>` : "";
            return `<li class="${cls}"><span class="dot"></span><span>${step.label}</span>${duration}</li>`;
        }).join("");

        let percent = (done.size / IMPORT_STEPS.length) * 100;
        if (running.size) percent += (100 / IMPORT_STEPS.length) * 0.45;
        if (status === "ready") percent = 100;
        if (status === "failed") percent = Math.max(percent, 8);
        setBar(status === "ready" ? 100 : Math.min(percent, 96));
    }

    function handleFile(file) {
        if (!file) return;
        if (!/\.pdf$/i.test(file.name) && file.type !== "application/pdf") {
            toast("目前只支持 PDF 文件");
            return;
        }
        if (file.size > 50 * 1024 * 1024) {
            toast("PDF 不能超过 50MB");
            return;
        }
        if (state.busyUpload) {
            toast("当前文件还在解析中，请稍候");
            return;
        }

        state.busyUpload = true;
        state.uploadToken += 1;
        const token = state.uploadToken;

        dom.uploadIdle.hidden = true;
        dom.uploadProgress.hidden = false;
        dom.uploadName.textContent = file.name;
        dom.uploadSize.textContent = `${formatSize(file.size)} · 准备上传`;
        dom.uploadActions.innerHTML = "";
        dom.uploadSteps.innerHTML = "";
        renderSteps({ done_list: ["开始上传文件"], running_list: [] }, "processing");
        setBar(4);

        const form = new FormData();
        form.append("file", file);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/projects");
        xhr.responseType = "json";

        xhr.upload.addEventListener("progress", (event) => {
            if (token !== state.uploadToken || !event.lengthComputable) return;
            const ratio = event.loaded / event.total;
            setBar(4 + ratio * 8);
            dom.uploadSize.textContent = `${formatSize(file.size)} · 上传中 ${Math.round(ratio * 100)}%`;
        });

        xhr.addEventListener("load", () => {
            if (token !== state.uploadToken) return;
            if (xhr.status < 200 || xhr.status >= 300) {
                const message = xhr.response?.message || "上传失败，请重试";
                failUpload(message);
                return;
            }
            const project = xhr.response?.project;
            if (!project) {
                failUpload("服务没有返回项目信息");
                return;
            }
            dom.uploadSize.textContent = `${formatSize(file.size)} · 正在解析`;
            loadProjects();
            pollProject(project.id, token);
        });

        xhr.addEventListener("error", () => {
            if (token === state.uploadToken) failUpload("网络中断，上传失败");
        });

        xhr.send(form);
    }

    function failUpload(message) {
        state.busyUpload = false;
        dom.uploadSize.textContent = message;
        dom.uploadPercent.textContent = "—";
        dom.uploadBar.style.width = "0%";
        dom.uploadActions.innerHTML = `
            <button class="btn btn--small btn--light" data-retry>重新选择文件</button>
            <button class="btn btn--small btn--link" data-reset style="color:rgba(255,255,255,.7)">返回</button>`;
        dom.uploadActions.querySelector("[data-retry]").addEventListener("click", () => {
            resetUploadPanel();
            pickFile();
        });
        dom.uploadActions.querySelector("[data-reset]").addEventListener("click", () => {
            resetUploadPanel();
        });
        toast(message);
    }

    async function pollProject(projectId, token) {
        const started = Date.now();
        const limit = 12 * 60 * 1000;

        while (token === state.uploadToken) {
            await sleep(1200);
            if (token !== state.uploadToken) return;

            try {
                const res = await fetch(`/api/projects/${encodeURIComponent(projectId)}/status`);
                if (!res.ok) throw new Error("状态查询失败");
                const snapshot = await res.json();
                renderSteps(snapshot.progress || {}, snapshot.status);

                if (snapshot.status === "ready") {
                    state.busyUpload = false;
                    dom.uploadSize.textContent = `已完成 · ${snapshot.doc_count || 0} 个切片${snapshot.item_name ? ` · ${snapshot.item_name}` : ""}`;
                    dom.uploadActions.innerHTML = `
                        <button class="btn btn--small btn--light" data-enter>进入对话</button>
                        <button class="btn btn--small btn--link" data-another style="color:rgba(255,255,255,.7)">再传一份</button>`;
                    dom.uploadActions.querySelector("[data-enter]").addEventListener("click", () => {
                        loadProjects();
                        const project = {
                            id: snapshot.id,
                            title: snapshot.title,
                            file_name: snapshot.file_name,
                            item_name: snapshot.item_name,
                            doc_count: snapshot.doc_count,
                            status: "ready",
                        };
                        state.projects = [project, ...state.projects.filter((p) => p.id !== project.id)];
                        enterProject(project.id);
                    });
                    dom.uploadActions.querySelector("[data-another]").addEventListener("click", () => {
                        resetUploadPanel();
                        dom.uploadIdle.style.display = "";
                        pickFile();
                    });
                    toast("项目解析完成，可以开始对话了");
                    loadProjects();
                    return;
                }

                if (snapshot.status === "failed") {
                    state.busyUpload = false;
                    dom.uploadSize.textContent = snapshot.error || "导入失败";
                    dom.uploadActions.innerHTML = `
                        <button class="btn btn--small btn--light" data-retry>重新选择文件</button>`;
                    dom.uploadActions.querySelector("[data-retry]").addEventListener("click", () => {
                        resetUploadPanel();
                        dom.uploadIdle.style.display = "";
                        pickFile();
                    });
                    toast(snapshot.error || "导入失败，请换一份 PDF 试试");
                    loadProjects();
                    return;
                }
            } catch (e) {
                if (Date.now() - started > limit) {
                    failUpload("解析时间过长，请稍后在「我的项目」里查看结果");
                    loadProjects();
                    return;
                }
            }

            if (Date.now() - started > limit) {
                failUpload("解析时间过长，请稍后在「我的项目」里查看结果");
                loadProjects();
                return;
            }
        }
    }

    /* ----------------------------------------------------------
       Markdown
       ---------------------------------------------------------- */

    function renderInline(text) {
        let out = escapeHtml(text);

        out = out.replace(/!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)/g, (match, alt, url) => {
            const safe = normalizeUrl(url);
            return isSafeUrl(safe)
                ? `<img src="${escapeHtml(safe)}" alt="${escapeHtml(alt)}" loading="lazy"/>`
                : match;
        });

        out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (match, label, url) => {
            return `<a href="${escapeHtml(normalizeUrl(url))}" target="_blank" rel="noopener noreferrer">${label}</a>`;
        });

        out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
        out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
        out = out.replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
        out = out.replace(/\[(?:切片\s*[:：]\s*)?(\d{1,2})\]/g, '<span class="cite">$1</span>');
        return out;
    }

    function renderMarkdown(text) {
        let source = String(text || "").replace(/\r\n?/g, "\n");
        source = source.replace(/【\s*图片\s*】[\s\S]*$/, "").trim();
        if (!source) return "";

        const lines = source.split("\n");
        const html = [];
        let paragraph = [];
        let listType = null;
        let inCode = false;
        let codeLines = [];

        const closeParagraph = () => {
            if (paragraph.length) {
                html.push(`<p>${paragraph.map(renderInline).join("<br/>")}</p>`);
                paragraph = [];
            }
        };

        const closeList = () => {
            if (listType) {
                html.push(`</${listType}>`);
                listType = null;
            }
        };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (/^\s*```/.test(line)) {
                if (inCode) {
                    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
                    codeLines = [];
                    inCode = false;
                } else {
                    closeParagraph();
                    closeList();
                    inCode = true;
                }
                continue;
            }

            if (inCode) {
                codeLines.push(line);
                continue;
            }

            if (!line.trim()) {
                closeParagraph();
                closeList();
                continue;
            }

            if (/^\s*\|.*\|\s*$/.test(line)) {
                closeParagraph();
                closeList();
                const rows = [];
                while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
                    rows.push(lines[i].trim());
                    i += 1;
                }
                i -= 1;

                const parseRow = (row) => row
                    .replace(/^\s*\|/, "")
                    .replace(/\|\s*$/, "")
                    .split("|")
                    .map((cell) => cell.trim());

                const hasSeparator = rows.length > 1 && /^[\s|:-]+$/.test(rows[1]);
                const head = parseRow(rows[0]);
                const body = rows.slice(hasSeparator ? 2 : 1).map(parseRow);

                html.push(`<div class="table-wrap"><table><thead><tr>${
                    head.map((cell) => `<th>${renderInline(cell)}</th>`).join("")
                }</tr></thead><tbody>${
                    body.map((cells) => `<tr>${cells.map((cell) => `<td>${renderInline(cell)}</td>`).join("")}</tr>`).join("")
                }</tbody></table></div>`);
                continue;
            }

            const heading = line.match(/^(#{1,6})\s+(.*)$/);
            if (heading) {
                closeParagraph();
                closeList();
                const level = Math.min(5, 2 + heading[1].length);
                html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
                continue;
            }

            if (/^\s*(---+|\*\*\*+)\s*$/.test(line)) {
                closeParagraph();
                closeList();
                html.push("<hr/>");
                continue;
            }

            if (/^\s*>\s?/.test(line)) {
                closeParagraph();
                closeList();
                html.push(`<blockquote>${renderInline(line.replace(/^\s*>\s?/, ""))}</blockquote>`);
                continue;
            }

            const ul = line.match(/^\s*[-*+]\s+(.*)$/);
            const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
            if (ul || ol) {
                closeParagraph();
                const wanted = ul ? "ul" : "ol";
                if (listType !== wanted) {
                    closeList();
                    html.push(`<${wanted}>`);
                    listType = wanted;
                }
                html.push(`<li>${renderInline((ul || ol)[1])}</li>`);
                continue;
            }

            closeList();
            paragraph.push(line.trim());
        }

        if (inCode) html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        closeParagraph();
        closeList();

        return html.join("");
    }

    function stripMarkdown(text) {
        return String(text || "")
            .replace(/```[\s\S]*?```/g, " ")
            .replace(/[#>*`_~\-|]/g, " ")
            .replace(/\[(\d{1,2})\]/g, " ")
            .replace(/\s+/g, " ")
            .trim();
    }

    /* ----------------------------------------------------------
       初始化
       ---------------------------------------------------------- */

    function init() {
        observeReveals();
        bindDragAndDrop();
        dom.dropZone.addEventListener("click", (event) => {
            if (event.target.closest("button") || !dom.uploadProgress.hidden) return;
            pickFile();
        });

        // 初始对话数据先恢复，示例数据随后补充
        loadConversations();
        loadWindowState();
        state.conversations.forEach((conv) => { conv.fresh = false; });

        loadHealth();
        loadExamples();
        loadProjects();

        ensureWindowsBuilt();
        applyLayout();
        renderRail();
        renderTabs();

        document.addEventListener("visibilitychange", () => {
            if (!document.hidden) loadProjects();
        });

        requestAnimationFrame(() => {
            document.querySelectorAll(".hero .reveal").forEach((el) => el.classList.add("is-in"));
        });

        // 从首页直接进入时，若上次有窗口则还原
        if (state.windows.length) {
            state.windows.forEach((key) => {
                const conv = convOf(key);
                if (conv) buildPane(conv);
            });
            applyLayout();
        }
    }

    init();
})();
