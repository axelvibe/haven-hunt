/* HavenHunt web chat widget */
(function () {
  "use strict";

  const cfg = window.HH_CONFIG || {};
  const box = document.getElementById("messages");
  const form = document.getElementById("chatform");
  const input = document.getElementById("chatinput");
  const foot = document.getElementById("chatfoot");

  const escaper = document.createElement("div");
  const esc = (s) => {
    escaper.textContent = s;
    return escaper.innerHTML;
  };

  function addMsg(text, who) {
    const el = document.createElement("div");
    el.className = "msg " + who;
    el.textContent = text;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    return el;
  }

  function addBotHtml(htmlStr) {
    const el = document.createElement("div");
    el.className = "msg bot";
    el.innerHTML = htmlStr;
    box.appendChild(el);
    box.scrollTop = box.scrollHeight;
    return el;
  }

  function listingCard(l) {
    const price = l.listing_type === "rent"
      ? "€" + Number(l.price).toLocaleString() + "/mo"
      : "€" + Number(l.price).toLocaleString();
    const beds = (l.beds === null || l.beds === undefined)
      ? "beds not recorded"
      : String(l.beds) + " bed";
    const size = (l.sqft === null || l.sqft === undefined)
      ? ""
      : " · " + Number(l.sqft).toLocaleString() + " sq ft";
    const img = l.image_url
      ? '<img src="' + esc(l.image_url) + '" alt="" style="width:100%;border-radius:10px;margin-top:6px">'
      : "";
    const mapLink = (l.lat && l.lng)
      ? ' · <a href="https://www.google.com/maps/search/?api=1&query=' +
        l.lat + "," + l.lng + '" target="_blank" rel="noopener">🗺️ map</a>'
      : "";
    return (
      '<div style="border:1px solid #243349;border-radius:12px;padding:10px;margin-top:8px;max-width:80%">' +
      "<b>" + esc(l.title) + "</b><br>" +
      "📍 " + esc(l.neighborhood + ", " + l.city + ", " + l.county) + mapLink + "<br>" +
      "💰 " + price + " · 🛏 " + esc(beds) + size +
      img +
      "</div>"
    );
  }

  function ask(query) {
    if (cfg.apiUrl) {
      return fetch(cfg.apiUrl.replace(/\/$/, "") + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query })
      }).then(function (r) { return r.json(); });
    }
    return Promise.reject(new Error("no-api"));
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;

    addMsg(q, "user");
    input.value = "";
    const typing = addMsg("…", "bot");

    ask(q).then(function (data) {
      typing.textContent = data.answer || "No answer.";
      (data.listings || []).forEach(function (l) {
        try {
          if (l.type_label) { /* keep */ }
        } catch (_) {}
        if (l.image_url) {
          const beds = (l.beds === null || l.beds === undefined)
            ? "beds not recorded" : l.beds + " bed";
          const mapLink = (l.lat && l.lng)
            ? '<br><a href="https://www.google.com/maps/search/?api=1&query=' +
              l.lat + "," + l.lng + '" target="_blank" rel="noopener">🗺️ View on Google Maps</a>'
            : "";
          const html =
            "<div style='border:1px solid #243349;border-radius:12px;padding:8px;margin-top:8px;max-width:80%'>" +
            "<img src='" + esc(l.image_url) + "' alt='" + esc(l.title) + "' style='width:100%;border-radius:8px'>" +
            "<div style='margin-top:6px'><b>" + esc(l.title) + "</b><br>📍 " +
            esc(l.neighborhood) + ", " + esc(l.city) + ", " + esc(l.county) + "<br>🛏 " +
            esc(beds) + mapLink + "</div></div>";
          addBotHtml(html);
        }
      });
    }).catch(function (err) {
      if (err && err.message === "no-api") {
        typing.textContent =
          "The live API isn't running yet. " +
          "Message the bot on Telegram to search right now!";
        addBotHtml(
          "👉 <a href='" + esc(cfg.telegramUrl) + "' target='_blank' rel='noopener'><b>Open HavenHunt on Telegram</b></a>"
        );
        foot.textContent =
          "Tip: set HH_API_URL (see config.js) to enable in-page search.";
      } else {
        typing.textContent = "Something went wrong. Please try again.";
      }
    });
  });

  foot.textContent = cfg.apiUrl
    ? "Live search is connected to the HavenHunt API (PPR sales data)."
    : "In-page live search needs HH_API_URL — you can still chat on Telegram.";

  const pulse = document.getElementById("pulse");
  const pulseText = document.getElementById("pulse-text");
  if (pulse && pulseText && cfg.apiUrl) {
    fetch(cfg.apiUrl.replace(/\/$/, "") + "/stats", { method: "GET" })
      .then(function (r) { return r.json(); })
      .then(function (s) {
        if (s && s.national && s.national.index != null) {
          const y = s.latest_period.slice(0, 4), m = s.latest_period.slice(4);
          const yoy = s.national.change_12m;
          pulseText.textContent =
            "index " + s.national.index.toFixed(1) + " (Base 2015=100) · " +
            "+" + yoy.toFixed(1) + "% vs a year ago · " + m + "/" + y +
            " · source: " + s.source;
          pulse.hidden = false;
        }
      })
      .catch(function () { pulse.hidden = true; });
  }
})();
