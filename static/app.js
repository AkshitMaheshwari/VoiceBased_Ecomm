(function () {
  const statusEl = document.getElementById("status");
  const healthEl = document.getElementById("health");
  const btnStart = document.getElementById("btn-start");
  const btnHangup = document.getElementById("btn-hangup");
  const btnHealth = document.getElementById("btn-refresh-health");

  let device = null;
  let activeCall = null;

  function log(msg) {
    statusEl.textContent = msg;
    console.log("[voice-ui]", msg);
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
})();
