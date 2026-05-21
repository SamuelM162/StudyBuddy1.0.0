document.addEventListener("DOMContentLoaded", function () {
  const i18n = window.STUDYPEER_I18N || {};

  // === Light/Dark theme toggle ===
  const themeToggle = document.getElementById("themeToggle");
  const themeIcon = document.getElementById("themeIcon");
  const rootEl = document.documentElement;

  // Apply saved theme on load
  const savedTheme = localStorage.getItem("sb-theme") || "light";
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

    if (window.innerWidth < 992) {
      sbSetLinksMode("menu");
      return;
    }

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

    // The chat thread page owns its AJAX submit + clear behavior.
    // A global submit clearer can erase the draft before that handler reads it.
    if (chatFormEl.id === "chat-form") return;

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

  // === StudyPeer AI Assistant toggle & chat ===
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

    function escapeHtml(value) {
      return (value ?? "").toString().replace(/[&<>"']/g, function (char) {
        return {
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          "\"": "&quot;",
          "'": "&#39;",
        }[char];
      });
    }

    function renderInlineMarkdown(text) {
      const codeSpans = [];
      let working = (text ?? "").toString().replace(/`([^`\n]+)`/g, function (_, code) {
        const index = codeSpans.length;
        codeSpans.push(`<code>${escapeHtml(code)}</code>`);
        return `\u0000CODE${index}\u0000`;
      });

      let html = escapeHtml(working);
      html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+)\)/g, function (_, label, url) {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
      });
      html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      html = html.replace(/__([^_]+)__/g, "<strong>$1</strong>");
      html = html.replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>");
      html = html.replace(/(^|[\s(])_([^_\n]+)_/g, "$1<em>$2</em>");

      codeSpans.forEach(function (code, index) {
        html = html.replace(`\u0000CODE${index}\u0000`, code);
      });
      return html;
    }

    function renderAiMarkdown(markdown) {
      const lines = (markdown ?? "").toString().replace(/\r\n?/g, "\n").split("\n");
      const html = [];
      let paragraph = [];
      let listType = null;
      let inFence = false;
      let fenceLines = [];

      function flushParagraph() {
        if (!paragraph.length) return;
        html.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`);
        paragraph = [];
      }

      function closeList() {
        if (!listType) return;
        html.push(`</${listType}>`);
        listType = null;
      }

      lines.forEach(function (line) {
        if (/^\s*```/.test(line)) {
          if (inFence) {
            html.push(`<pre><code>${escapeHtml(fenceLines.join("\n"))}</code></pre>`);
            fenceLines = [];
            inFence = false;
          } else {
            flushParagraph();
            closeList();
            inFence = true;
          }
          return;
        }

        if (inFence) {
          fenceLines.push(line);
          return;
        }

        if (!line.trim()) {
          flushParagraph();
          closeList();
          return;
        }

        const heading = line.match(/^(#{1,6})\s+(.+)$/);
        if (heading) {
          flushParagraph();
          closeList();
          const level = heading[1].length;
          html.push(`<h${level}>${renderInlineMarkdown(heading[2].trim())}</h${level}>`);
          return;
        }

        const item = line.match(/^\s*((?:[-*+])|(?:\d+\.))\s+(.+)$/);
        if (item) {
          flushParagraph();
          const nextListType = /^\d+\./.test(item[1]) ? "ol" : "ul";
          if (listType !== nextListType) {
            closeList();
            html.push(`<${nextListType}>`);
            listType = nextListType;
          }
          html.push(`<li>${renderInlineMarkdown(item[2].trim())}</li>`);
          return;
        }

        closeList();
        paragraph.push(line.trim());
      });

      if (inFence) {
        html.push(`<pre><code>${escapeHtml(fenceLines.join("\n"))}</code></pre>`);
      }
      flushParagraph();
      closeList();

      return html.join("");
    }

    function appendAiMessage(role, text) {
      // role: 'me' | 'bot'
      const stick = isNearBottom(aiMessages);
      const node = document.createElement("div");
      node.classList.add("sb-ai-message");
      node.classList.add(role === "me" ? "sb-ai-message-user" : "sb-ai-message-bot");

      const safeText = (text ?? "").toString();
      if (role === "bot") {
        node.innerHTML = renderAiMarkdown(safeText);
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
        .then((response) => {
          if (!response.ok) throw new Error(`AI request failed: ${response.status}`);
          return response.json();
        })
        .then((data) => {
          appendAiMessage("bot", data.reply || i18n.noReply || "(no reply)");
        })
        .catch(() => {
          appendAiMessage("bot", i18n.aiError || "Error talking to AI.");
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
  function sbSetBlockButtonState(btn, blocked) {
    if (!btn) return;

    if (blocked) {
      btn.classList.add("is-blocked");
      btn.textContent = i18n.unblock || "Unblock";
      btn.setAttribute("aria-pressed", "true");
    } else {
      btn.classList.remove("is-blocked");
      btn.textContent = i18n.block || "Block";
      btn.setAttribute("aria-pressed", "false");
    }
  }

  async function sbRefreshBlockButtons() {
    const buttons = Array.from(document.querySelectorAll(".sb-block-btn[data-uid]"));
    if (!buttons.length) return;

    await Promise.all(buttons.map(async (btn) => {
      const uid = btn.dataset.uid || "";
      if (!uid) {
        sbSetBlockButtonState(btn, false);
        return;
      }

      try {
        const res = await fetch(`/social/api/is_blocked/${encodeURIComponent(uid)}?_=${Date.now()}`, {
          method: "GET",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          cache: "no-store",
          credentials: "same-origin",
        });

        if (!res.ok) throw new Error(`Block state API failed: ${res.status}`);

        const data = await res.json();
        sbSetBlockButtonState(btn, !!(data && data.ok === true && data.blocked === true));
      } catch (err) {
        console.error(err);
        sbSetBlockButtonState(btn, false);
      }
    }));
  }

  sbRefreshBlockButtons();

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
      (prevText.toLowerCase() === String(i18n.unblock || "Unblock").toLowerCase()) ||
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
      if (btn) {
        sbSetBlockButtonState(btn, blocked);
      } else if (blocked) {
        el.textContent = i18n.unblock || "Unblock";
        if (a) {
          a.setAttribute("href", `/social/unblock/${otherUid}`);
          a.setAttribute("aria-pressed", "true");
        }
      } else {
        el.textContent = i18n.block || "Block";
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
