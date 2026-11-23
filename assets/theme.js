/* Sets the saved theme before the page paints, and marks the page as one that runs scripts (so the extras show).
   Light is the default; nothing is stored until the person chooses. */
document.documentElement.classList.add("js");
try { var t = localStorage.getItem("stallboard-theme"); if (t === "dark" || t === "light") document.documentElement.dataset.theme = t; } catch (e) { /* storage may be blocked */ }
