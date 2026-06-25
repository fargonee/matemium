import { configureStore } from "@reduxjs/toolkit";

import { emptySplitApi } from "@/api/emptyApi";
import "@/api/matemiumApi";
import authReducer from "@/store/authSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    [emptySplitApi.reducerPath]: emptySplitApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(emptySplitApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;