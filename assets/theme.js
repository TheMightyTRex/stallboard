/* Applies the saved display choices before the page paints, and marks the page as one that runs scripts (so the extras show).
   The choices are kept in this browser only (localStorage, inside try/catch); nothing is stored until the person chooses.
   components.js applies them again when the page has loaded and owns the Display and accessibility panel. */
(function () {
  var h = document.documentElement;
  h.classList.add("js");
  var p = {};
  try {
    p = JSON.parse(localStorage.getItem("stallboard-display") || "{}") || {};
    if (!p.theme) { var old = localStorage.getItem("stallboard-theme"); if (old === "dark" || old === "light") p.theme = old; }  /* the old colour switch */
  } catch (e) { /* storage may be blocked */ }
  var dark = false;
  if (p.theme === "dark") dark = true;
  if (p.theme === "system") { try { dark = window.matchMedia("(prefers-color-scheme: dark)").matches; } catch (e) { /* fine */ } }
  if (p.theme) h.dataset.theme = dark ? "dark" : "light";
  if (p.text === "125" || p.text === "150" || p.text === "175") h.classList.add("pref-text-" + p.text);
  if (p.motion === "on") h.classList.add("pref-motion");
  if (p.motion === "off") h.classList.add("pref-motion-off");
  if (p.contrast === true) h.classList.add("pref-contrast");
  if (p.underline === true) h.classList.add("pref-underline");
  if (p.spacing === true) h.classList.add("pref-spacing");
  if (p.shadows === true) h.dataset.shadows = "off";
})();
