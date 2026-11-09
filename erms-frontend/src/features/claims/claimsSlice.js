import { createAsyncThunk, createSlice, isAnyOf } from "@reduxjs/toolkit";
import { api, toApiError } from "../../api/client";

/**
 * Small factory so every thunk has the same try/catch and error shape.
 * `fn` receives the thunk argument and returns the data to put in the store.
 */
const request = (type, fn) =>
  createAsyncThunk(type, async (arg, { rejectWithValue }) => {
    try {
      return await fn(arg);
    } catch (err) {
      return rejectWithValue(toApiError(err));
    }
  });

const getClaim = async (id) => (await api.get(`/claims/${id}/`)).data;

// --- reads ----------------------------------------------------------------

export const fetchClaims = request("claims/fetchList", async (params = {}) => (await api.get("/claims/", { params })).data);
export const fetchClaim = request("claims/fetchOne", getClaim);
export const fetchEvents = request("claims/fetchEvents", async (id) => (await api.get(`/claims/${id}/events/`)).data);

// --- mutations that return the updated claim detail -----------------------

export const createClaim = request("claims/create", async (body) => (await api.post("/claims/", body)).data);
export const updateClaim = request("claims/update", async ({ id, body }) => (await api.patch(`/claims/${id}/`, body)).data);

// Item endpoints return the item, not the claim; totals live on the claim, so re-read it.
export const addItem = request("claims/addItem", async ({ id, body }) => {
  await api.post(`/claims/${id}/items/`, body); // body is JSON or FormData (when a receipt is attached)
  return getClaim(id);
});
export const updateItem = request("claims/updateItem", async ({ id, itemId, body }) => {
  await api.patch(`/claims/${id}/items/${itemId}/`, body);
  return getClaim(id);
});
export const removeItem = request("claims/removeItem", async ({ id, itemId }) => {
  await api.delete(`/claims/${id}/items/${itemId}/`);
  return getClaim(id);
});

export const submitClaim = request("claims/submit", async (id) => (await api.post(`/claims/${id}/submit/`)).data);
export const approveClaim = request("claims/approve", async ({ id, body }) => (await api.post(`/claims/${id}/approve/`, body)).data);
export const rejectClaim = request("claims/reject", async ({ id, comment }) => (await api.post(`/claims/${id}/reject/`, { comment })).data);
export const reopenClaim = request("claims/reopen", async (id) => (await api.post(`/claims/${id}/reopen/`)).data);
export const payClaim = request("claims/pay", async ({ id, payment_reference }) => (await api.post(`/claims/${id}/pay/`, { payment_reference })).data);

// Delete returns nothing useful, so it is handled separately below.
export const deleteClaim = request("claims/delete", async (id) => {
  await api.delete(`/claims/${id}/`);
  return id;
});

const CLAIM_MUTATIONS = [createClaim, updateClaim, addItem, updateItem, removeItem, submitClaim, approveClaim, rejectClaim, reopenClaim, payClaim];

// --- slice ----------------------------------------------------------------

const initialState = {
  list: { items: [], count: 0, hasNext: false, hasPrevious: false, status: "idle", error: null },
  current: { claim: null, events: [], status: "idle", error: null },
  // Tracks the most recent mutation so pages can show a spinner or a 409/400 message.
  action: { status: "idle", error: null },
};

const claimsSlice = createSlice({
  name: "claims",
  initialState,
  reducers: {
    clearCurrent(state) {
      state.current = initialState.current;
      state.action = initialState.action;
    },
    clearActionError(state) {
      state.action.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // list
      .addCase(fetchClaims.pending, (state) => {
        state.list.status = "loading";
        state.list.error = null;
      })
      .addCase(fetchClaims.fulfilled, (state, action) => {
        state.list.status = "succeeded";
        state.list.items = action.payload.results; // DRF pagination envelope
        state.list.count = action.payload.count;
        // next/previous are URLs or null; we only need to know if they exist.
        state.list.hasNext = Boolean(action.payload.next);
        state.list.hasPrevious = Boolean(action.payload.previous);
      })
      .addCase(fetchClaims.rejected, (state, action) => {
        state.list.status = "failed";
        state.list.error = action.payload;
      })
      // detail
      .addCase(fetchClaim.pending, (state) => {
        state.current.status = "loading";
        state.current.error = null;
      })
      .addCase(fetchClaim.fulfilled, (state, action) => {
        state.current.status = "succeeded";
        state.current.claim = action.payload;
      })
      .addCase(fetchClaim.rejected, (state, action) => {
        state.current.status = "failed";
        state.current.error = action.payload;
      })
      .addCase(fetchEvents.fulfilled, (state, action) => {
        state.current.events = action.payload;
      })
      // delete
      .addCase(deleteClaim.pending, (state) => {
        state.action = { status: "loading", error: null };
      })
      .addCase(deleteClaim.fulfilled, (state) => {
        state.action.status = "succeeded";
        state.current.claim = null;
      })
      .addCase(deleteClaim.rejected, (state, action) => {
        state.action = { status: "failed", error: action.payload };
      })
      // every mutation that returns a claim is handled the same way
      .addMatcher(isAnyOf(...CLAIM_MUTATIONS.map((t) => t.pending)), (state) => {
        state.action = { status: "loading", error: null };
      })
      .addMatcher(isAnyOf(...CLAIM_MUTATIONS.map((t) => t.fulfilled)), (state, action) => {
        state.action.status = "succeeded";
        state.current.claim = action.payload;
      })
      .addMatcher(isAnyOf(...CLAIM_MUTATIONS.map((t) => t.rejected)), (state, action) => {
        state.action = { status: "failed", error: action.payload };
      });
  },
});

export const { clearCurrent, clearActionError } = claimsSlice.actions;
export default claimsSlice.reducer;
