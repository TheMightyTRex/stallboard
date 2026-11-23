/* Starts Snaglist (snaglist.js, version 0.6.0, MIT) for Stallboard. A report opens a new issue in
   TheMightyTRex/stallboard, labelled feedback, for the person to post from their own GitHub account.
   Nothing else is set: no email, no server, no token. Snaglist keeps nothing of what people type. */
Snaglist.start({
  app: "Stallboard",
  language: "en-GB",
  send: { github: { repo: "TheMightyTRex/stallboard" }, email: null, endpoint: null, qr: false, copy: true, download: true },
  labels: ["feedback"],
});
