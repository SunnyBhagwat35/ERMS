import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, toApiError } from "../../api/client";

export const fetchCategories = createAsyncThunk(
  "categories/fetch",
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.get("/categories/");
      return data;
    } catch (err) {
      return rejectWithValue(toApiError(err));
    }
  },
  {
    // Categories rarely change; don't refetch if we already have them.
    condition: (_, { getState }) => getState().categories.status !== "succeeded",
  }
);

const categoriesSlice = createSlice({
  name: "categories",
  initialState: { items: [], status: "idle", error: null },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCategories.pending, (state) => {
        state.status = "loading";
      })
      .addCase(fetchCategories.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.items = action.payload;
      })
      .addCase(fetchCategories.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.payload;
      });
  },
});

export default categoriesSlice.reducer;
