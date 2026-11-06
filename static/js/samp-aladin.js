// Send a sky position to Aladin Desktop over SAMP (Web Profile) and lock
// all of Aladin's sky views to it (position, zoom and rotation).
//
// The hub asks the user to approve each new registration, so we register once,
// keep the registration in localStorage, and reuse it on later pages. If Aladin
// (and its hub) has been restarted, the stored registration is rejected and we
// register again, which shows the approval prompt once more.
(function () {
  const APP_NAME = "VAST Pipeline";
  const META = {
    "samp.name": APP_NAME,
    "samp.description.text": "VAST Pipeline web interface",
  };
  const STORAGE_KEY = "vast-pipeline:samp-reginfo";
  const noop = () => {};

  function loadRegInfo() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch (e) { return null; }
  }
  function saveRegInfo(regInfo) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(regInfo)); } catch (e) {}
  }
  function forgetRegInfo() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
  }

  // New registration: this is the step that shows the approval prompt.
  function registerNew(onConn, onFail) {
    samp.register(
      APP_NAME,
      (conn) => {
        conn.declareMetadata([META], noop, noop);
        saveRegInfo(conn.regInfo);
        onConn(conn);
      },
      onFail
    );
  }

  // Reuse a stored registration if the hub still recognises it.
  // Explicit error handlers matter here: without them sampjs closes
  // (and unregisters) the connection on any failed call.
  function withConnection(onConn, onFail) {
    const regInfo = loadRegInfo();
    if (!regInfo) {
      registerNew(onConn, onFail);
      return;
    }
    const conn = new samp.Connection(regInfo);
    conn.getRegisteredClients(
      [],
      () => onConn(conn),                                        // still valid: no prompt
      () => { forgetRegInfo(); registerNew(onConn, onFail); }    // stale (Aladin restarted)
    );
  }

  function formatCoord(ra, dec) {
    const sign = dec < 0 ? "-" : "+";
    return `${ra.toFixed(6)} ${sign}${Math.abs(dec).toFixed(6)}`;
  }

  function buildScript(ra, dec, fovArcmin) {
    return [
      "match off",                     // 'match' is a toggle in Aladin: reset it first
      formatCoord(ra, dec),            // centre the current view on the source
      `zoom ${fovArcmin.toFixed(2)}arcmin`,
      "match",                         // lock all sky views: position, scale, rotation
    ].join("; ");
  }

  // onResult(status, err): status is "ok", "no-aladin", "no-hub" or "error"
  window.sendToAladinDesktop = function (ra, dec, fovArcmin, onResult) {
    const msg = new samp.Message("script.aladin.send", {
      script: buildScript(ra, dec, fovArcmin),
    });
    withConnection(
      (conn) => conn.notifyAll(
        [msg],
        (recipients) => onResult(recipients && recipients.length ? "ok" : "no-aladin"),
        (err) => onResult("error", err)
      ),
      (err) => onResult("no-hub", err)
    );
  };
})();
