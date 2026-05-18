(function () {
  const statusEl = document.getElementById("status");
  const healthEl = document.getElementById("health");
  const btnStart = document.getElementById("btn-start");
  const btnHangup = document.getElementById("btn-hangup");
  const btnHealth = document.getElementById("btn-refresh-health");
  const chatLog = document.getElementById("chat-log");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatStatus = document.getElementById("chat-status");
  const chatSession = document.getElementById("chat-session");
  const btnResetChat = document.getElementById("btn-reset-chat");
  const chatChips = Array.from(document.querySelectorAll(".chip"));

  let device = null;
  let activeCall = null;
  let sessionId = null;

  function log(msg) {
    statusEl.textContent = msg;
    console.log("[voice-ui]", msg);
  }

  function setChatStatus(msg) {
    if (chatStatus) {
      chatStatus.textContent = msg;
    }
  }

  function ensureSessionId() {
    if (!chatSession) return null;
    const stored = localStorage.getItem("chat_session_id");
    if (stored) {
      sessionId = stored;
    } else {
      const rand = Math.random().toString(36).slice(2, 10);
      sessionId = "web-" + rand;
      localStorage.setItem("chat_session_id", sessionId);
    }
    chatSession.textContent = sessionId;
    return sessionId;
  }

  function resetChatSession() {
    if (!chatSession) return;
    const rand = Math.random().toString(36).slice(2, 10);
    sessionId = "web-" + rand;
    localStorage.setItem("chat_session_id", sessionId);
    chatSession.textContent = sessionId;
    if (chatLog) {
      chatLog.innerHTML = "";
    }
    addChatBubble("bot", "New session ready. Tell me what you want to shop.");
    setChatStatus("Fresh session started.");
  }

  function addChatBubble(role, text, audioUrl) {
    if (!chatLog) return null;
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble " + role;
    bubble.textContent = text;

    if (audioUrl) {
      const audioWrap = document.createElement("div");
      audioWrap.className = "chat-audio";
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = "Play voice";
      btn.addEventListener("click", () => {
        const audio = new Audio(audioUrl);
        audio.play().catch(() => {});
      });
      audioWrap.appendChild(btn);
      bubble.appendChild(audioWrap);
    }

    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
    return bubble;
  }

  function addTypingBubble() {
    return addChatBubble("bot", "Thinking...");
  }

  async function sendChat(query) {
    if (!query || !chatLog || !chatInput) return;
    const trimmed = query.trim();
    if (!trimmed) return;

    addChatBubble("user", trimmed);
    chatInput.value = "";
    chatInput.focus();
    setChatStatus("Pulling recommendations...");

    if (!sessionId) {
      ensureSessionId();
    }

    const typing = addTypingBubble();
    const submitBtn = document.getElementById("btn-send");
    if (submitBtn) submitBtn.disabled = true;
    chatInput.disabled = true;

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId || "default_session", query: trimmed }),
      });
      const data = await res.json().catch(() => ({}));
      if (typing && typing.parentNode) typing.parentNode.removeChild(typing);

      if (!res.ok) {
        addChatBubble("bot", data.detail || "Something went wrong. Try again.");
        setChatStatus("Issue talking to the assistant.");
        return;
      }

      addChatBubble("bot", data.response || "No response.", data.audio_url || null);
      setChatStatus("Ready for the next question.");
    } catch (e) {
      if (typing && typing.parentNode) typing.parentNode.removeChild(typing);
      addChatBubble("bot", "Network error. Please try again in a moment.");
      setChatStatus("Network error.");
    } finally {
      if (submitBtn) submitBtn.disabled = false;
      chatInput.disabled = false;
    }
  }

  async function refreshHealth() {
    healthEl.textContent = "Loading...";
    try {
      const r = await fetch("/api/health");
      const h = await r.json();
      healthEl.textContent = JSON.stringify(h, null, 2);
    } catch (e) {
      healthEl.textContent = "Health check failed: " + (e && e.message ? e.message : String(e));
    }
  }

  function getDeviceClass() {
    if (typeof Twilio !== "undefined" && Twilio.Device) {
      return Twilio.Device;
    }
    return null;
  }

  function formatTwilioError(err) {
    if (!err) return "Unknown error";
    const code = err.code != null ? " (code " + err.code + ")" : "";
    if (err.message) return err.message + code;
    try {
      return JSON.stringify(err) + code;
    } catch (_) {
      return String(err) + code;
    }
  }

  btnStart.addEventListener("click", async () => {
    const Device = getDeviceClass();
    if (!Device) {
      log("Twilio Voice SDK not loaded. Check the script tag / network (unpkg.com blocked?).");
      return;
    }

    btnStart.disabled = true;
    try {
      log("Requesting microphone...");
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (micErr) {
        log(
          "Microphone blocked or unavailable: " +
            (micErr && micErr.message ? micErr.message : String(micErr)) +
            " - allow mic for this site."
        );
        btnStart.disabled = false;
        return;
      }

      log("Fetching access token...");
      const headers = { "Content-Type": "application/json" };
      const secret = document.getElementById("token-secret").value.trim();
      if (secret) {
        headers["X-Token-Secret"] = secret;
      }

      const idRaw = document.getElementById("identity").value.trim();
      const body = idRaw ? JSON.stringify({ identity: idRaw }) : "{}";

      const res = await fetch("/api/twilio/token", { method: "POST", headers, body });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        log("Token error " + res.status + ": " + (data.detail || JSON.stringify(data)));
        btnStart.disabled = false;
        return;
      }

      const token = data.token;
      if (!token) {
        log("No token in response.");
        btnStart.disabled = false;
        return;
      }

      if (device) {
        try {
          device.destroy();
        } catch (_) {}
        device = null;
      }

      log("Initializing Twilio Device...");
      device = new Device(token, {
        logLevel: 1,
        codecPreferences: ["opus", "pcmu"],
      });

      device.on("registered", () => log("Registered - connecting call..."));
      device.on("unregistered", () => log("Device unregistered."));
      device.on("error", (err) => {
        log("Device error: " + formatTwilioError(err));
        btnHangup.disabled = true;
        btnStart.disabled = false;
      });
      device.on("disconnect", () => {
        activeCall = null;
        btnHangup.disabled = true;
        btnStart.disabled = false;
        log("Call ended.");
      });

      log("Starting call (TwiML App voice URL)...");
      activeCall = await device.connect({});
      if (activeCall && typeof activeCall.on === "function") {
        activeCall.on("error", (err) => {
          log("Call error: " + formatTwilioError(err));
        });
        activeCall.on("disconnect", () => {
          activeCall = null;
          btnHangup.disabled = true;
          btnStart.disabled = false;
        });
      }

      btnHangup.disabled = false;
      log("Connected - speak to the assistant.");
    } catch (e) {
      log("Error: " + formatTwilioError(e));
      console.error(e);
      btnStart.disabled = false;
      btnHangup.disabled = true;
    }
  });

  btnHangup.addEventListener("click", () => {
    if (activeCall && typeof activeCall.disconnect === "function") {
      try {
        activeCall.disconnect();
      } catch (_) {}
    }
    activeCall = null;
    btnHangup.disabled = true;
    btnStart.disabled = false;
    log("Hang up requested.");
  });

  btnHealth.addEventListener("click", refreshHealth);

  refreshHealth();

  if (chatForm && chatInput) {
    ensureSessionId();
    addChatBubble("bot", "Hi! Tell me what you are shopping for and I will curate options.");

    chatForm.addEventListener("submit", (event) => {
      event.preventDefault();
      sendChat(chatInput.value);
    });

    chatInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendChat(chatInput.value);
      }
    });
  }

  if (btnResetChat) {
    btnResetChat.addEventListener("click", resetChatSession);
  }

  chatChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt") || "";
      sendChat(prompt);
    });
  });
})();
