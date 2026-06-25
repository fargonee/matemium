import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import { env } from "@/lib/env";
import type { RootState } from "@/store";

export const emptySplitApi = createApi({
  baseQuery: fetchBaseQuery({
    baseUrl: env.apiUrl,
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.accessToken;
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      return headers;
    },
  }),
  endpoints: () => ({}),
});