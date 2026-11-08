import { configureStore } from "@reduxjs/toolkit";
import authReducer from "../features/auth/authSlice";
import claimsReducer from "../features/claims/claimsSlice";
import categoriesReducer from "../features/categories/categoriesSlice";

// state.auth, state.claims, state.categories — one slice per backend concern.
export const store = configureStore({
  reducer: {
    auth: authReducer,
    claims: claimsReducer,
    categories: categoriesReducer,
  },
});
