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

  // === StudyBuddy AI Assistant toggle & chat ===
  const aiWidget = document.getElementById("ai-widget");
  const aiBubble = document.getElementById("ai-bubble"); // floating messenger-style bubble
  const aiHeaderToggle = document.getElementById("ai-toggle"); // small "–" button in widget header
  const aiResizeBtn = document.querySelector(".sb-ai-toggle-size"); // optional maximize button
  const aiForm = document.getElementById("ai-form");
  const aiInput = document.getElementById("ai-input");
  const aiMessages = document.getElementById("ai-messages");

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
  aiWidget.classList.remove("is-hidden");
  requestAnimationFrame(() => {
    scrollMessagesToBottom(true);
    aiInput.focus();
  });
}

function hideAiWidget() {
  aiWidget.classList.add("is-hidden");
}




    // Bubble toggles the widget
    if (aiBubble) {
      aiBubble.addEventListener("click", function (e) {
        e.preventDefault();
        const hidden = (aiWidget.style.display === "none") || (getComputedStyle(aiWidget).display === "none");
        if (hidden) showAiWidget(); else hideAiWidget();
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
      const text = (aiInput.value || "").trim();
      if (!text) return;

      aiInput.value = "";
      appendAiMessage("me", text);

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
  }
});
