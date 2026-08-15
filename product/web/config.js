// HavenHunt web chat widget (Ireland market).
// Talks to the HavenHunt API (product/web/api.py) when HH_API_URL is set.
// Otherwise it gracefully falls back to the Telegram bot.
window.HH_CONFIG = window.HH_CONFIG || {
  apiUrl: "",                       // e.g. "https://haven-hunt.onrender.com"
  telegramUrl: "https://t.me/haven_hunt_bot",
  siteUrl: "https://axelvibe.github.io/haven-hunt/"
};
