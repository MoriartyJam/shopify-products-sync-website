(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // Year
  const yearEl = $("#year");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  // Mobile menu
  const burger = $("#burger");
  const menu = $("#menu");
  if (burger && menu) {
    burger.addEventListener("click", () => {
      const isOpen = menu.classList.toggle("is-open");
      burger.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    // close on click
    $$("#menu a").forEach(a => a.addEventListener("click", () => {
      menu.classList.remove("is-open");
      burger.setAttribute("aria-expanded", "false");
    }));

    // close on outside click
    document.addEventListener("click", (e) => {
      const target = e.target;
      if (!menu.classList.contains("is-open")) return;
      if (target instanceof Node && !menu.contains(target) && !burger.contains(target)) {
        menu.classList.remove("is-open");
        burger.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Side active + correct anchor scrolling (fix for sticky header)
const headerEl = $(".header");
const sections = $$("[data-section]");
const sideItems = $$(".side__item");
const sideEl = $(".side");

const getHeaderH = () => headerEl ? Math.round(headerEl.getBoundingClientRect().height) : 0;

const setActiveSide = (id) => {
  sideItems.forEach(item => item.classList.toggle("is-active", item.dataset.side === id));
};

const updateActiveByScroll = () => {
  if (!sections.length || !sideItems.length) return;

  // точка "чтения" страницы: чуть ниже шапки
  const y = window.scrollY + getHeaderH() + 40;

  let currentId = sections[0].id;
  for (const s of sections) {
    if (s.offsetTop <= y) currentId = s.id;
  }
  setActiveSide(currentId);
};

const updateSideVisibility = () => {
  if (!sideEl || !sections.length) return;
  const triggerY = Math.max(0, sections[0].offsetTop - getHeaderH() - 24);
  sideEl.classList.toggle("is-hidden", window.scrollY < triggerY);
};

// throttle via rAF
let ticking = false;
const onScroll = () => {
  if (ticking) return;
  ticking = true;
  requestAnimationFrame(() => {
    updateSideVisibility();
    updateActiveByScroll();
    ticking = false;
  });
};

window.addEventListener("scroll", onScroll, { passive: true });
window.addEventListener("resize", () => {
  updateSideVisibility();
  updateActiveByScroll();
});
updateSideVisibility();
updateActiveByScroll();

const scrollToIdWithOffset = (id) => {
  const el = document.getElementById(id);
  if (!el) return;

  const y = el.getBoundingClientRect().top + window.pageYOffset - getHeaderH() - 16;
  window.scrollTo({ top: Math.max(0, y), behavior: "smooth" });
  setActiveSide(id);
};

// перехватываем клики по боковому меню (01..05)
sideItems.forEach(a => {
  a.addEventListener("click", (e) => {
    const href = a.getAttribute("href");
    if (!href || !href.startsWith("#")) return;
    const id = href.slice(1);
    if (!id) return;

    e.preventDefault();
    scrollToIdWithOffset(id);
    history.replaceState(null, "", "#" + id);
  });
});


  // Toast
  const toast = $("#toast");
  let toastTimer = null;
  function showToast(text) {
    if (!toast) return;
    toast.textContent = text;
    toast.classList.add("is-show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-show"), 2400);
  }

  // Modal
  const modal = $("#modal");
  function openModal() {
    if (!modal) return;
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
  }
  if (modal) {
    modal.addEventListener("click", (e) => {
      const t = e.target;
      if (!(t instanceof HTMLElement)) return;
      if (t.dataset.close === "1") closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal.classList.contains("is-open")) closeModal();
    });
  }

  // Blitz estimate
  const blitzForm = $("#blitzForm");
  const resTime = $("#resTime");
  const resBudget = $("#resBudget");

  function estimate({ type, scope, integrations, ui, deadline }) {
    // base in "points"
    let pts = 0;

    pts += (type === "public") ? 7 : 4;
    pts += (scope === "s") ? 2 : (scope === "m") ? 5 : 9;
    pts += (integrations === "0") ? 0 : (integrations === "1") ? 2 : 5;
    pts += (ui === "basic") ? 1 : 3;
    pts += (deadline === "soon") ? 2 : 0;

    // convert points to ranges (simple heuristic)
    // time: 1 pt ~ 2-4 days
    const minWeeks = Math.max(1, Math.round((pts * 2) / 5));
    const maxWeeks = Math.max(minWeeks + 1, Math.round((pts * 4) / 5));

    // budget: 1 pt ~ $200-350 (reduced by ~50%)
    const minUsd = Math.round(pts * 200);
    const maxUsd = Math.round(pts * 350);

    return {
      time: `${minWeeks}–${maxWeeks} тиж.`,
      budget: `$${minUsd.toLocaleString()} – $${maxUsd.toLocaleString()}`
    };
  }

  if (blitzForm) {
    blitzForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const fd = new FormData(blitzForm);
      const data = Object.fromEntries(fd.entries());
      const r = estimate(data);

      if (resTime) resTime.textContent = r.time;
      if (resBudget) resBudget.textContent = r.budget;

      showToast("Готово: бліц-оцінку пораховано ✅");
    });
  }

  // Cases slider (auto every 7s)
  const casesViewport = $("#casesViewport");
  const casesTrack = $("#casesTrack");
  const prevCaseBtn = $("#prevCase");
  const nextCaseBtn = $("#nextCase");
  let casePageIndex = 0;
  let caseTimer = null;

  function getCasesLayout() {
    if (!casesTrack || !casesViewport) return null;
    const slides = $$(".case--slide", casesTrack);
    if (!slides.length) return null;

    const slideWidth = slides[0].getBoundingClientRect().width;
    const trackStyles = getComputedStyle(casesTrack);
    const gap = parseFloat(trackStyles.columnGap || trackStyles.gap || "0") || 0;
    const step = slideWidth + gap;
    const visible = Math.max(1, Math.round((casesViewport.clientWidth + gap) / step));
    const pages = Math.max(1, Math.ceil(slides.length / visible));

    const pageStarts = Array.from({ length: pages }, (_, p) =>
      Math.min(p * visible, Math.max(0, slides.length - visible))
    );

    return { slides, step, pageStarts };
  }

  function setCasePage(pageIdx) {
    const layout = getCasesLayout();
    if (!layout || !layout.pageStarts.length) return;

    const totalPages = layout.pageStarts.length;
    casePageIndex = (pageIdx + totalPages) % totalPages;
    const startIndex = layout.pageStarts[casePageIndex];
    casesTrack.style.transform = `translateX(-${startIndex * layout.step}px)`;
  }

  function stopCaseAuto() {
    if (!caseTimer) return;
    clearInterval(caseTimer);
    caseTimer = null;
  }

  function startCaseAuto() {
    stopCaseAuto();
    const layout = getCasesLayout();
    if (!layout || layout.pageStarts.length < 2) return;
    caseTimer = setInterval(() => setCasePage(casePageIndex + 1), 7000);
  }

  if (casesViewport && casesTrack && prevCaseBtn && nextCaseBtn) {
    prevCaseBtn.addEventListener("click", () => {
      setCasePage(casePageIndex - 1);
      startCaseAuto();
    });

    nextCaseBtn.addEventListener("click", () => {
      setCasePage(casePageIndex + 1);
      startCaseAuto();
    });

    casesViewport.addEventListener("mouseenter", stopCaseAuto);
    casesViewport.addEventListener("mouseleave", startCaseAuto);
    casesViewport.addEventListener("focusin", stopCaseAuto);
    casesViewport.addEventListener("focusout", startCaseAuto);

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) stopCaseAuto();
      else startCaseAuto();
    });

    window.addEventListener("resize", () => setCasePage(casePageIndex));

    setCasePage(0);
    startCaseAuto();
  }

  // Reviews slider
  const viewport = $("#reviewViewport");
  const reviewTrack = $("#reviewTrack");
  const prevBtn = $("#prevReview");
  const nextBtn = $("#nextReview");
  let reviewPageIndex = 0;

  function getReviewsLayout() {
    if (!reviewTrack || !viewport) return null;
    const slides = $$(".review--slide", reviewTrack);
    if (!slides.length) return null;

    const slideWidth = slides[0].getBoundingClientRect().width;
    const trackStyles = getComputedStyle(reviewTrack);
    const gap = parseFloat(trackStyles.columnGap || trackStyles.gap || "0") || 0;
    const step = slideWidth + gap;
    const visible = Math.max(1, Math.round((viewport.clientWidth + gap) / step));
    const pages = Math.max(1, Math.ceil(slides.length / visible));

    const pageStarts = Array.from({ length: pages }, (_, p) =>
      Math.min(p * visible, Math.max(0, slides.length - visible))
    );

    return { step, pageStarts };
  }

  function setReviewPage(pageIdx) {
    const layout = getReviewsLayout();
    if (!layout || !layout.pageStarts.length) return;

    const totalPages = layout.pageStarts.length;
    reviewPageIndex = (pageIdx + totalPages) % totalPages;
    const startIndex = layout.pageStarts[reviewPageIndex];
    reviewTrack.style.transform = `translateX(-${startIndex * layout.step}px)`;
  }

  if (prevBtn && nextBtn && viewport && reviewTrack) {
    prevBtn.addEventListener("click", () => setReviewPage(reviewPageIndex - 1));
    nextBtn.addEventListener("click", () => setReviewPage(reviewPageIndex + 1));
    window.addEventListener("resize", () => setReviewPage(reviewPageIndex));
    setReviewPage(0);
  }

  // Contact form validation (demo)
  const contactForm = $("#contactForm");
  const LEADS_ENDPOINT = String(window.__QW_LEADS_ENDPOINT__ || "").trim();

  function setErr(name, msg) {
    const el = $(`[data-err-for="${name}"]`);
    if (el) el.textContent = msg || "";
  }

  function validateContact(form) {
    const name = $("#name")?.value.trim() || "";
    const phone = $("#phone")?.value.trim() || "";
    const email = $("#email")?.value.trim() || "";
    const message = $("#message")?.value.trim() || "";

    let ok = true;

    setErr("name", "");
    setErr("phone", "");
    setErr("email", "");
    setErr("message", "");

    if (name.length < 2) { setErr("name", "Вкажи ім’я (мін. 2 символи)."); ok = false; }
    if (phone && phone.length < 7) { setErr("phone", "Телефон має бути від 7 символів або залиш поле порожнім."); ok = false; }
    if (!/^\S+@\S+\.\S+$/.test(email)) { setErr("email", "Вкажи коректний e-mail."); ok = false; }
    if (message && message.length < 10) { setErr("message", "Опиши задачу детальніше (мін. 10 символів) або залиш поле порожнім."); ok = false; }

    return ok;
  }

  async function sendLeadToGoogleSheets(payload) {
    const body = {
      ...payload,
      created_at: new Date().toISOString(),
      page_url: window.location.href
    };

    // Preferred: normal CORS request with readable response.
    try {
      const res = await fetch(LEADS_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json;charset=UTF-8" },
        body: JSON.stringify(body)
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const raw = await res.text();
      if (raw) {
        try {
          const data = JSON.parse(raw);
          if (data && data.result === "error") {
            throw new Error(data.message || "Apps Script returned error");
          }
        } catch {
          // Non-JSON response is acceptable for Apps Script web apps.
        }
      }
      return;
    } catch {
      // Fallback for Apps Script deployments without CORS headers.
      await fetch(LEADS_ENDPOINT, {
        method: "POST",
        mode: "no-cors",
        headers: { "Content-Type": "text/plain;charset=UTF-8" },
        body: JSON.stringify(body)
      });
    }
  }

  if (contactForm) {
    contactForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      if (!LEADS_ENDPOINT) {
        showToast("Не налаштовано endpoint для заявок.");
        return;
      }

      if (!validateContact(contactForm)) {
        showToast("Перевір поля у формі 👀");
        return;
      }

      const payload = Object.fromEntries(new FormData(contactForm).entries());
      const submitBtn = contactForm.querySelector("button[type=\"submit\"]");
      const oldBtnText = submitBtn?.textContent || "Надіслати";

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Надсилаємо...";
      }

      try {
        await sendLeadToGoogleSheets(payload);
        contactForm.reset();
        showToast("Заявку надіслано ✅");
        openModal();
      } catch {
        showToast("Помилка відправки. Спробуй ще раз.");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = oldBtnText;
        }
      }
    });
  }

  // Close details when opening another (accordion behavior)
  const accordion = $("#accordion");
  if (accordion) {
    accordion.addEventListener("toggle", (e) => {
      const t = e.target;
      if (!(t instanceof HTMLDetailsElement)) return;
      if (!t.open) return;
      $$("details", accordion).forEach(d => {
        if (d !== t) d.open = false;
      });
    }, true);
  }
})();
