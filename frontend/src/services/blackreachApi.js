// src/services/blackreachApi.js
import { fetchJSON } from "./apiClient";

// ensure consistent leading slash
function path(p) {
  return p.startsWith("/") ? p : `/${p}`;
}

// (optional safety) encode path params
function enc(v) {
  return encodeURIComponent(String(v));
}

/**
 * ✅ Demo fallback polyline (IIT → Seth Sarai)
 * Used ONLY if caller forgets to send polyline.
 */
const DEMO_POLYLINE_FALLBACK = "}hfmDsucvMHMROs@yDBOvCeAMe@BQLIJAp@a@N_@b@}A\\}@tAoFF[z@aDbA_Dx@kDk@Yl@wBDYsGoCqCaAH[zCjApQhHdDx@`E`A~Ar@jB`AzBr@tFzBd@TvAh@`@LdBp@xCx@zBj@ZNbCfB`@\\l@`@jD|ClAnAd@t@fEvHtGxLj@t@nDhDjA~ABJlBzA\\\\h@VrBnAb@f@e@RwCPMzKFbAJd@VVZJ|DQz@?"

export const blackreachApi = {
  // ─────────────────────────────
  // journey
  // ─────────────────────────────
  journey: {
    plan: (payload, opts) =>
      fetchJSON(path("/journey/plan"), {
        method: "POST",
        body: payload,
        ...opts,
      }),

    price: (payload, opts) =>
      fetchJSON(path("/journey/price"), {
        method: "POST",
        body: payload,
        ...opts,
      }),
  },

  // ─────────────────────────────
  // booking
  // ─────────────────────────────
  booking: {
    confirm: (payload, opts) =>
      fetchJSON(path("/booking/confirm"), {
        method: "POST",
        body: payload,
        ...opts,
      }),
  },

  // ─────────────────────────────
  // tracking
  // ─────────────────────────────
  tracking: {
    update: (payload, opts) =>
      fetchJSON(path("/tracking/update"), {
        method: "POST",
        body: payload,
        ...opts,
      }),

    latest: (bookingId, opts) =>
      fetchJSON(path(`/tracking/latest/${enc(bookingId)}`), {
        method: "GET",
        ...opts,
      }),
  },

  // ─────────────────────────────
  // lookahead ✅ FIXED: /lookahead/500m expects bookingId + polyline
  // ─────────────────────────────
 lookahead: {
  m500: (payload = {}, opts) => {
    const body = {
      bookingId: payload.bookingId,
      distance_m: payload.distance_m ?? 500,
      sample_fracs: payload.sample_fracs ?? [0.25, 0.6, 1],
      places_radius_m: payload.places_radius_m ?? 200,
      places_max_results: payload.places_max_results ?? 20,
      osm_radius_m: payload.osm_radius_m ?? 500,
      micro_distance_m: payload.micro_distance_m ?? 100,
      store_segment_points_max: payload.store_segment_points_max ?? 60,
    };

    return fetchJSON(path("/lookahead/500m"), {
      method: "POST",
      body,
      ...opts,
    });
  },
},

  // ─────────────────────────────
  // gemini
  // ─────────────────────────────
  gemini: {
    run: (bookingId, payload, opts) =>
      fetchJSON(path(`/gemini/run/${enc(bookingId)}`), {
        method: "POST",
        body: payload,
        ...opts,
      }),
  },

  // ─────────────────────────────
  // chat
  // ─────────────────────────────
  chat: {
    get: (bookingId, opts) =>
      fetchJSON(path(`/chat/${enc(bookingId)}`), {
        method: "GET",
        ...opts,
      }),

    send: (bookingId, payload, opts) =>
      fetchJSON(path(`/chat/${enc(bookingId)}/send`), {
        method: "POST",
        body: payload,
        ...opts,
      }),
  },

  // ─────────────────────────────
  // case
  // ─────────────────────────────
  case: {
    get: (bookingId, opts) =>
      fetchJSON(path(`/case/${enc(bookingId)}`), {
        method: "GET",
        ...opts,
      }),

    resolve: (bookingId, opts) =>
      fetchJSON(path(`/case/${enc(bookingId)}/resolve`), {
        method: "POST",
        ...opts,
      }),
  },
};
