document.addEventListener("DOMContentLoaded", function () {
  // === Light/Dark theme toggle ===
  const themeToggle = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");
  const rootEl = document.documentElement;

  // Apply saved theme on load
  const savedTheme = localStorage.getItem("sb-theme") || "dark";
  if (savedTheme === "dark") {
    rootEl.setAttribute("data-bs-theme", "dark");
    document.body.classList.add("dark-mode");
    if (themeIcon) themeIcon.textContent = "◑";
  } else {
    rootEl.setAttribute("data-bs-theme", "light");
    document.body.classList.remove("dark-mode");
    if (themeIcon) themeIcon.textContent = "◐";
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", function (e) {
      e.preventDefault();
      const current = rootEl.getAttribute("data-bs-theme") || "dark";
      const next = current === "dark" ? "light" : "dark";

      rootEl.setAttribute("data-bs-theme", next);

      if (next === "dark") {
        document.body.classList.add("dark-mode");
        if (themeIcon) themeIcon.textContent = "◑";
        localStorage.setItem("sb-theme", "dark");
      } else {
        document.body.classList.remove("dark-mode");
        if (themeIcon) themeIcon.textContent = "◐";
        localStorage.setItem("sb-theme", "light");
      }
    });
  }

  // === Global UI wiring (navbar, theme, etc.) ===

  // === Navbar "fit" logic (hamburger always present; links move into hamburger only when needed) ===
  const sbInlineLinks = document.getElementById("sbInlineLinks");
  const sbMenuLinks = document.getElementById("sbMenuLinks");
  const sbNavbar = document.querySelector(".sb-navbar");

  function sbSetLinksMode(mode) {
    // mode: "inline" (links visible on bar) or "menu" (links inside hamburger)
    if (!sbInlineLinks || !sbMenuLinks) return;

    if (mode === "menu") {
      sbInlineLinks.classList.add("d-none");
      sbMenuLinks.classList.remove("d-none");
    } else {
      sbInlineLinks.classList.remove("d-none");
      sbMenuLinks.classList.add("d-none");
    }
  }

  function sbUpdateNavbarFit() {
    if (!sbNavbar || !sbInlineLinks || !sbMenuLinks) return;

    // Temporarily show inline links so we can measure their natural width.
    const inlineWasHidden = sbInlineLinks.classList.contains("d-none");
    if (inlineWasHidden) sbInlineLinks.classList.remove("d-none");

    const container = sbNavbar.querySelector(".container-fluid") || sbNavbar;
    const brand = sbNavbar.querySelector(".navbar-brand");
    const toggler = sbNavbar.querySelector(".navbar-toggler");

    if (!brand || !toggler) {
      // Fallback: if we can't measure reliably, keep inline.
      sbSetLinksMode("inline");
      return;
    }

    // Available space for inline links between brand and toggler.
    const buffer = 24; // small safety padding
    const available = container.clientWidth - brand.offsetWidth - toggler.offsetWidth - buffer;

    // Required space for links.
    const required = sbInlineLinks.scrollWidth;

    const needsMenu = required > available;
    sbSetLinksMode(needsMenu ? "menu" : "inline");

    // Restore hidden state if it was hidden and we decided to stay in menu mode.
    // (sbSetLinksMode already applied final visibility.)
  }

  // Run on load and on resize (with light debouncing).
  let sbFitTimer = null;
  function sbScheduleFit() {
    if (sbFitTimer) clearTimeout(sbFitTimer);
    sbFitTimer = setTimeout(sbUpdateNavbarFit, 60);
  }

  sbScheduleFit();
  window.addEventListener("resize", sbScheduleFit);
  // Some layouts settle after fonts/styles load
  setTimeout(sbUpdateNavbarFit, 150);
  setTimeout(sbUpdateNavbarFit, 600);

  // === Normal chat: clear input after sending (do NOT override chat logic) ===
  // Some browsers restore form values on navigation/back-forward cache; we force-clear on load + submit.
  function sbWireChatInputClear() {
    // Common selectors for your chat thread form/input
    const chatFormEl =
      document.getElementById("chat-form") ||
      document.querySelector("form.sb-chat-form") ||
      document.querySelector("form[data-sb-chat-form]") ||
      document.querySelector("form[action*=\"/chat/\"]");

    if (!chatFormEl) return;

    const chatInputEl =
      document.getElementById("chat-input") ||
      chatFormEl.querySelector("#chat-input") ||
      chatFormEl.querySelector("input[name=\"text\"]") ||
      chatFormEl.querySelector("textarea[name=\"text\"]") ||
      chatFormEl.querySelector("input[name=\"message\"]") ||
      chatFormEl.querySelector("textarea[name=\"message\"]");

    if (!chatInputEl) return;

    // Force-clear any restored value on load
    chatInputEl.value = "";
    chatInputEl.setAttribute("value", "");
    chatInputEl.dispatchEvent(new Event("input", { bubbles: true }));

    // Clear immediately on submit (without preventing normal submit/redirect)
    chatFormEl.addEventListener("submit", function () {
      // Clear now + after current tick (covers Safari/Chrome restore quirks)
      chatInputEl.value = "";
      chatInputEl.setAttribute("value", "");
      chatInputEl.dispatchEvent(new Event("input", { bubbles: true }));

      // Keep focus in the input (otherwise button click steals focus)
      try {
        chatInputEl.focus({ preventScroll: true });
      } catch (_) {
        chatInputEl.focus();
      }

      setTimeout(() => {
        chatInputEl.value = "";
        chatInputEl.setAttribute("value", "");
        chatInputEl.dispatchEvent(new Event("input", { bubbles: true }));

        try {
          chatInputEl.focus({ preventScroll: true });
        } catch (_) {
          chatInputEl.focus();
        }
      }, 0);
    });
  }

  sbWireChatInputClear();

  // === StudyBuddy AI Assistant toggle & chat ===
  const aiWidget = document.getElementById("ai-widget");
  const aiBubble = document.getElementById("ai-bubble"); // floating messenger-style bubble
  const aiHeaderToggle = document.getElementById("ai-toggle"); // small "–" button in widget header
  const aiResizeBtn = document.querySelector(".sb-ai-toggle-size"); // optional maximize button
  const aiForm = document.getElementById("ai-form");
  const aiInput = document.getElementById("ai-input");
  const aiMessages = document.getElementById("ai-messages");

  // Single source of truth for widget visibility
  let aiIsOpen = false;

  // Ensure the widget never appears by CSS/layout alone
  if (aiWidget) {
    // If markup forgot the class, force closed on load
    aiWidget.classList.add("is-hidden");
  }

  if (aiWidget && aiMessages && aiInput && aiForm) {
    function isNearBottom(el, px = 48) {
      return el.scrollHeight - el.scrollTop - el.clientHeight <= px;
    }

    function scrollMessagesToBottom(force = false) {
      // Scroll ONLY inside the messages container (never the page)
      if (!aiMessages) return;
      if (force || isNearBottom(aiMessages)) {
        aiMessages.scrollTop = aiMessages.scrollHeight;
      }
    }

    function appendAiMessage(role, text) {
      // role: 'me' | 'bot'
      const stick = isNearBottom(aiMessages);
      const node = document.createElement("div");
      node.classList.add("sb-ai-message");
      node.classList.add(role === "me" ? "sb-ai-message-user" : "sb-ai-message-bot");

      const safeText = (text ?? "").toString();
      // Allow markdown rendering for bot if marked is available
      if (role === "bot" && window.marked) {
        node.innerHTML = window.marked.parse(safeText);
      } else {
        node.textContent = safeText;
      }

      aiMessages.appendChild(node);
      scrollMessagesToBottom(stick);
    }

    function showAiWidget() {
      aiIsOpen = true;
      aiWidget.classList.remove("is-hidden");
      requestAnimationFrame(() => {
        scrollMessagesToBottom(true);
        aiInput.focus();
      });
    }

    function hideAiWidget() {
      aiIsOpen = false;
      aiWidget.classList.add("is-hidden");
    }

    // Bubble toggles the widget
    if (aiBubble) {
      aiBubble.addEventListener("click", function (e) {
        e.preventDefault();
        if (aiIsOpen) hideAiWidget();
        else showAiWidget();
      });
    }

    // Header toggle: just close
    if (aiHeaderToggle) {
      aiHeaderToggle.addEventListener("click", function (e) {
        e.preventDefault();
        hideAiWidget();
      });
    }

    // Optional maximize (CSS class)
    if (aiResizeBtn) {
      aiResizeBtn.addEventListener("click", function (e) {
        e.preventDefault();
        aiWidget.classList.toggle("is-maximized");
        requestAnimationFrame(() => {
          scrollMessagesToBottom(true);
          aiInput.focus();
        });
      });
    }

    // Send question to AI
    aiForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const text = aiInput.value.trim();
      if (!text) return;

      appendAiMessage("me", text);

      // Clear the input reliably (works across browsers, avoids value sticking)
      aiInput.value = "";
      aiInput.setAttribute("value", "");
      if (aiForm && typeof aiForm.reset === "function") aiForm.reset();
      // Notify any listeners / ensure UI updates
      aiInput.dispatchEvent(new Event("input", { bubbles: true }));
      aiInput.dispatchEvent(new Event("change", { bubbles: true }));
      requestAnimationFrame(() => aiInput.focus());

      fetch("/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      })
        .then((response) => response.json())
        .then((data) => {
          appendAiMessage("bot", data.reply || "(no reply)");
        })
        .catch(() => {
          appendAiMessage("bot", "Error talking to AI.");
        });
    });

    // Mobile: prevent weird jumps; keep messages pinned only if already near bottom
    aiInput.addEventListener("focus", function () {
      requestAnimationFrame(() => scrollMessagesToBottom(false));
    });

    // Hard guard: prevent auto-open on resize/fullscreen/layout shifts
    const sbEnforceAiClosedIfNeeded = () => {
      if (!aiIsOpen) aiWidget.classList.add("is-hidden");
    };

    window.addEventListener("resize", () => {
      // Run after layout settles
      requestAnimationFrame(sbEnforceAiClosedIfNeeded);
      setTimeout(sbEnforceAiClosedIfNeeded, 80);
    });

    document.addEventListener("fullscreenchange", () => {
      requestAnimationFrame(sbEnforceAiClosedIfNeeded);
      setTimeout(sbEnforceAiClosedIfNeeded, 80);
    });
  }

  // === Block/Unblock (instant UI toggle, no reload) ===
  // Supports BOTH:
  // 1) buttons: <button class="sb-block-btn" data-uid="<other_uid>">Block</button>
  // 2) legacy links: <a href="/social/block/<uid>">Block</a> / <a href="/social/unblock/<uid>">Unblock</a>
  // Backend: POST /social/api/block/<uid> -> { ok: true, blocked: true/false }
  document.addEventListener("click", async (e) => {
    const target = e.target;

    // Case A: button
    const btn = (target && target.closest) ? target.closest(".sb-block-btn") : null;

    // Case B: legacy link
    const a = (!btn && target && target.closest) ? target.closest("a[href^='/social/block/'], a[href^='/social/unblock/']") : null;

    if (!btn && !a) return;

    e.preventDefault();
    e.stopPropagation();

    const el = btn || a;

    // Resolve UID
    let otherUid = "";
    if (btn) {
      otherUid = btn.dataset.uid || "";
    } else if (a) {
      const href = a.getAttribute("href") || "";
      // /social/block/<uid> or /social/unblock/<uid>
      const parts = href.split("/").filter(Boolean);
      otherUid = parts[2] || "";
    }

    if (!otherUid) return;

    const prevText = (el.textContent || "").trim();

    // Determine current UI state
    const wasBlocked = (
      (btn && btn.classList.contains("is-blocked")) ||
      (prevText.toLowerCase() === "unblock") ||
      (a && (a.getAttribute("href") || "").startsWith("/social/unblock/"))
    );

    // Disable while request
    el.setAttribute("aria-busy", "true");
    if (btn) btn.disabled = true;

    try {
      const res = await fetch(`/social/api/block/${encodeURIComponent(otherUid)}`,
        {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        }
      );

      if (!res.ok) {
        throw new Error(`Block API failed: ${res.status}`);
      }

      let blocked = null;
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      if (ct.includes("application/json")) {
        const data = await res.json();
        if (data && data.ok === true && typeof data.blocked === "boolean") {
          blocked = data.blocked;
        }
      }

      // Fallback: if backend didn't return JSON, assume toggle
      if (blocked === null) blocked = !wasBlocked;

      // Update UI
      if (blocked) {
        el.textContent = "Unblock";
        if (btn) {
          btn.classList.add("is-blocked");
          btn.setAttribute("aria-pressed", "true");
        }
        if (a) {
          a.setAttribute("href", `/social/unblock/${otherUid}`);
          a.setAttribute("aria-pressed", "true");
        }
      } else {
        el.textContent = "Block";
        if (btn) {
          btn.classList.remove("is-blocked");
          btn.setAttribute("aria-pressed", "false");
        }
        if (a) {
          a.setAttribute("href", `/social/block/${otherUid}`);
          a.setAttribute("aria-pressed", "false");
        }
      }
    } catch (err) {
      console.error(err);
      // revert text
      el.textContent = prevText;
    } finally {
      el.removeAttribute("aria-busy");
      if (btn) btn.disabled = false;
    }
  });
});
