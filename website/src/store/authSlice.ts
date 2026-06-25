import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { User } from "@supabase/supabase-js";

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  initialized: boolean;
}

const initialState: AuthState = {
  user: null,
  accessToken: null,
  initialized: false,
};

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setSession(
      state,
      action: PayloadAction<{ user: User | null; accessToken: string | null }>
    ) {
      state.user = action.payload.user;
      state.accessToken = action.payload.accessToken;
      state.initialized = true;
    },
    clearSession(state) {
      state.user = null;
      state.accessToken = null;
      state.initialized = true;
    },
  },
});

export const { setSession, clearSession } = authSlice.actions;
export default authSlice.reducer;