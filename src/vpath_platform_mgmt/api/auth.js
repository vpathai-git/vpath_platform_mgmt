"use strict";
/* Browser sign-in for the console.
 *
 * Two modes, chosen by the server via /api/auth-config — never guessed here.
 * In `dev` the header identity is kept exactly as it was (simulated engine
 * only). In `oidc` the console runs the authorization-code flow with PKCE
 * against Keycloak and sends a bearer token; the role then comes from the
 * token's claims, not from a dropdown.
 *
 * The access token lives in sessionStorage: it dies with the tab, and is
 * never written to localStorage or to a cookie.
 */
const VpathAuth = (() => {
  const TOKEN = "vpath.token";
  const VERIFIER = "vpath.pkce.verifier";
  const STATE = "vpath.pkce.state";
  const SCOPE = "openid profile";

  let config = {mode: "dev"};
  let meta = null;
  let identity = null;

  const b64url = (bytes) =>
    btoa(String.fromCharCode(...new Uint8Array(bytes)))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");

  const nonce = () => b64url(crypto.getRandomValues(new Uint8Array(32)));

  const challenge = async (verifier) =>
    b64url(await crypto.subtle.digest(
      "SHA-256", new TextEncoder().encode(verifier)));

  const redirectUri = () => location.origin + location.pathname;

  async function discover(issuer) {
    const url = issuer.replace(/\/$/, "") + "/.well-known/openid-configuration";
    let response;
    try {
      response = await fetch(url);
    } catch (err) {
      /* A bare "Failed to fetch" hides three different causes, and the advice
       * for each is different. Naming the wrong one costs an afternoon: a
       * cross-origin block cannot be fixed by accepting a certificate, and an
       * http:// address has no certificate to accept in the first place. */
      const target = new URL(url);
      const causes = [];
      if (target.origin !== location.origin) {
        causes.push(`this page is ${location.origin} but discovery points at ` +
          `${target.origin} — different origins, so the browser blocks it. ` +
          `Open the console at ${target.origin}, or set ` +
          `VPATH_MGMT_OIDC_BROWSER_ISSUER to this page's origin`);
      }
      if (target.protocol === "https:") {
        causes.push(`if ${target.origin} serves a self-signed certificate, ` +
          `open it directly once and accept the warning — a fetch() cannot`);
      }
      causes.push(`the console may have no route to Keycloak (SSH tunnel down` +
        `), which it reports as a 500 from its own relay`);
      throw new Error(`cannot reach Keycloak at ${target.origin} ` +
        `(${err.message}). Likely: ` + causes.join("; ") + ".");
    }
    if (!response.ok) {
      throw new Error(`OIDC discovery failed (${response.status}) at ${url}`);
    }
    return response.json();
  }

  async function begin() {
    const verifier = nonce();
    const state = nonce();
    sessionStorage.setItem(VERIFIER, verifier);
    sessionStorage.setItem(STATE, state);
    const url = new URL(meta.authorization_endpoint);
    const params = {
      response_type: "code",
      client_id: config.client_id,
      redirect_uri: redirectUri(),
      scope: SCOPE,
      state: state,
      code_challenge: await challenge(verifier),
      code_challenge_method: "S256",
    };
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    location.assign(url.toString());
  }

  async function complete(code, state) {
    const expected = sessionStorage.getItem(STATE);
    const verifier = sessionStorage.getItem(VERIFIER);
    sessionStorage.removeItem(STATE);
    sessionStorage.removeItem(VERIFIER);
    if (!expected || state !== expected) {
      throw new Error("sign-in state mismatch — the response was discarded");
    }
    if (!verifier) throw new Error("sign-in verifier missing — start again");
    const r = await fetch(meta.token_endpoint, {
      method: "POST",
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code: code,
        redirect_uri: redirectUri(),
        client_id: config.client_id,
        code_verifier: verifier,
      }),
    });
    if (!r.ok) {
      throw new Error(`token exchange failed (${r.status}): ${await r.text()}`);
    }
    const granted = await r.json();
    if (!granted.access_token) throw new Error("token response carried no token");
    sessionStorage.setItem(TOKEN, granted.access_token);
  }

  const token = () => sessionStorage.getItem(TOKEN);

  function forget() {
    sessionStorage.removeItem(TOKEN);
    identity = null;
  }

  async function whoami() {
    const r = await fetch("/api/me", {headers: headers()});
    if (r.status === 401) {
      /* Keycloak issued a token and the console refused it — a different
       * failure from "not signed in", and the only place the reason exists.
       * Swallowing it here leaves an empty console with no explanation. */
      let detail = "";
      try {
        detail = (await r.json()).detail || "";
      } catch (err) {
        detail = `HTTP ${r.status}`;
      }
      forget();
      throw new Error(`signed in, but the console rejected the token: ${detail}`);
    }
    if (!r.ok) throw new Error(`/api/me failed (${r.status})`);
    return r.json();
  }

  function headers() {
    const base = {"Content-Type": "application/json"};
    if (config.mode !== "oidc") {
      const actor = document.getElementById("actor");
      const role = document.getElementById("role");
      base["X-Dev-Actor"] = (actor && actor.value) || "you";
      base["X-Dev-Role"] = role ? role.value : "app-dev";
      return base;
    }
    const bearer = token();
    if (bearer) base["Authorization"] = "Bearer " + bearer;
    return base;
  }

  async function init() {
    const r = await fetch("/api/auth-config");
    if (!r.ok) throw new Error(`/api/auth-config failed (${r.status})`);
    config = await r.json();
    if (config.mode !== "oidc") {
      return {mode: config.mode, authenticated: true, identity: null};
    }
    /* Past this point the mode is settled, so a failure here must still
     * report mode "oidc": the console has to render its signed-out state,
     * never fall back to looking like a dev console it is not. */
    try {
      meta = await discover(config.issuer);
      const query = new URLSearchParams(location.search);
      if (query.get("error")) {
        const detail = query.get("error_description") || query.get("error");
        history.replaceState({}, "", redirectUri());
        throw new Error("sign-in refused by Keycloak: " + detail);
      }
      if (query.get("code")) {
        await complete(query.get("code"), query.get("state"));
        history.replaceState({}, "", redirectUri());
      }
      if (!token()) return {mode: "oidc", authenticated: false, identity: null};
      identity = await whoami();
      return {mode: "oidc", authenticated: identity !== null, identity: identity};
    } catch (err) {
      return {
        mode: "oidc", authenticated: false, identity: null,
        error: err.message || String(err),
      };
    }
  }

  return {
    init: init,
    headers: headers,
    signIn: begin,
    signOut: forget,
    mode: () => config.mode,
    identity: () => identity,
  };
})();
