import axios from "axios";

const TOKEN_KEY = "erms_token";

export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api",
});

// Attach the token to every request. DRF expects "Authorization: Token <key>".
api.interceptors.request.use((config) => {
  const token = tokenStorage.get();
  if (token) config.headers.Authorization = `Token ${token}`;
  return config;
});

// A 401 means the token is dead (logged out elsewhere, DB reset). Drop it and go to login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes("/auth/login/")) {
      tokenStorage.clear();
      if (window.location.pathname !== "/login") window.location.assign("/login");
    }
    return Promise.reject(error);
  }
);

// Flatten nested DRF error payloads into one readable string.
function flatten(value) {
  if (Array.isArray(value)) return value.map(flatten).join(" ");
  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, v]) => `${key}: ${flatten(v)}`)
      .join("; ");
  }
  return String(value);
}

/**
 * Turn any axios failure into one predictable shape:
 *   { status, message, code, currentStatus, fieldErrors }
 * Backend business errors look like {detail, code, current_status};
 * DRF shape errors look like {field: ["msg"]}.
 */
export function toApiError(error) {
  if (!error.response) {
    return { status: 0, message: "Cannot reach the server. Is the backend running?", code: "network", currentStatus: null, fieldErrors: {} };
  }
  const { status, data } = error.response;
  const fieldErrors = {};
  let message = "";

  if (data && typeof data === "object") {
    if (data.detail !== undefined) {
      message = flatten(data.detail);
    } else if (data.non_field_errors) {
      message = flatten(data.non_field_errors);
    } else {
      for (const [field, errs] of Object.entries(data)) fieldErrors[field] = flatten(errs);
      message = Object.entries(fieldErrors)
        .map(([field, msg]) => `${field}: ${msg}`)
        .join(" ");
    }
  }
  if (!message) message = `Request failed (${status}).`;

  return {
    status,
    message,
    code: data?.code ?? null,
    currentStatus: data?.current_status ?? null,
    fieldErrors,
  };
}
