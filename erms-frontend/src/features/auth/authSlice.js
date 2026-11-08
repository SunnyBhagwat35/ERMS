import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, tokenStorage, toApiError } from "../../api/client";

// --- thunks ---------------------------------------------------------------

export const login = createAsyncThunk("auth/login", async (credentials, { rejectWithValue }) => {
  try {
    const { data } = await api.post("/auth/login/", credentials); // {token, user}
    tokenStorage.set(data.token);
    return data;
  } catch (err) {
    return rejectWithValue(toApiError(err));
  }
});

// Called on page refresh: we still have a token but no user object in memory.
export const fetchMe = createAsyncThunk("auth/fetchMe", async (
  _, { rejectWithValue }) => {
  try {
    const { data } = await api.get("/auth/me/");
    return data;
  } catch (err) {
    tokenStorage.clear();
    return rejectWithValue(toApiError(err));
  }
});

export const logout = createAsyncThunk("auth/logout", async () => {
  try {
    await api.post("/auth/logout/");
  } catch {
    // Token may already be invalid; we log out locally regardless.
  }
  tokenStorage.clear();
});

// --- slice ----------------------------------------------------------------

const initialState = {
  token: tokenStorage.get(),
  user: null,
  status: "idle", // idle | loading | succeeded | failed
  error: null,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    clearAuthError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.token = action.payload.token;
        state.user = action.payload.user;
      })
      .addCase(login.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload;
      })
      .addCase(fetchMe.fulfilled, (state, action) => {
        state.user = action.payload;
      })
      .addCase(fetchMe.rejected, (state) => {
        state.token = null;
        state.user = null;
      })
      .addCase(logout.fulfilled, (state) => {
        state.token = null;
        state.user = null;
        state.status = "idle";
      });
  },
});

export const { clearAuthError } = authSlice.actions;
export const selectUser = (state) => state.auth.user;
export const selectIsApprover = (state) => state.auth.user?.role === "APPROVER";
export default authSlice.reducer;
