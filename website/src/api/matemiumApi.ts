import { emptySplitApi as api } from "./emptyApi";
const injectedRtkApi = api.injectEndpoints({
  endpoints: (build) => ({
    healthHealthGet: build.query<
      HealthHealthGetApiResponse,
      HealthHealthGetApiArg
    >({
      query: () => ({ url: `/health` }),
    }),
    issueTokenV1AuthTokenPost: build.mutation<
      IssueTokenV1AuthTokenPostApiResponse,
      IssueTokenV1AuthTokenPostApiArg
    >({
      query: (queryArg) => ({
        url: `/v1/auth/token`,
        method: "POST",
        body: queryArg.tokenRequest,
      }),
    }),
    exchangeSessionV1AuthSessionPost: build.mutation<
      ExchangeSessionV1AuthSessionPostApiResponse,
      ExchangeSessionV1AuthSessionPostApiArg
    >({
      query: (queryArg) => ({
        url: `/v1/auth/session`,
        method: "POST",
        body: queryArg.sessionRequest,
      }),
    }),
    verifyTokenV1AuthVerifyGet: build.query<
      VerifyTokenV1AuthVerifyGetApiResponse,
      VerifyTokenV1AuthVerifyGetApiArg
    >({
      query: () => ({ url: `/v1/auth/verify` }),
    }),
    getMe: build.query<GetMeApiResponse, GetMeApiArg>({
      query: () => ({ url: `/v1/me` }),
    }),
    createCheckout: build.mutation<
      CreateCheckoutApiResponse,
      CreateCheckoutApiArg
    >({
      query: (queryArg) => ({
        url: `/v1/billing/checkout`,
        method: "POST",
        body: queryArg.checkoutRequest,
      }),
    }),
    createPortal: build.mutation<CreatePortalApiResponse, CreatePortalApiArg>({
      query: () => ({ url: `/v1/billing/portal`, method: "POST" }),
    }),
    getAdminStats: build.query<GetAdminStatsApiResponse, GetAdminStatsApiArg>({
      query: () => ({ url: `/v1/admin/stats` }),
    }),
    getAdminUsers: build.query<GetAdminUsersApiResponse, GetAdminUsersApiArg>({
      query: () => ({ url: `/v1/admin/users` }),
    }),
    getAdminSubscriptions: build.query<
      GetAdminSubscriptionsApiResponse,
      GetAdminSubscriptionsApiArg
    >({
      query: () => ({ url: `/v1/admin/subscriptions` }),
    }),
    getAdminUser: build.query<GetAdminUserApiResponse, GetAdminUserApiArg>({
      query: (queryArg) => ({ url: `/v1/admin/users/${queryArg.userId}` }),
    }),
    updateAdminUser: build.mutation<UpdateAdminUserApiResponse, UpdateAdminUserApiArg>({
      query: (queryArg) => ({
        url: `/v1/admin/users/${queryArg.userId}`,
        method: "PATCH",
        body: queryArg.updateUserRequest,
      }),
    }),
    updateAdminSubscription: build.mutation<
      UpdateAdminSubscriptionApiResponse,
      UpdateAdminSubscriptionApiArg
    >({
      query: (queryArg) => ({
        url: `/v1/admin/subscriptions/${queryArg.subscriptionId}`,
        method: "PATCH",
        body: queryArg.updateSubscriptionRequest,
      }),
    }),
    getAdminLLM: build.query<GetAdminLLMApiResponse, GetAdminLLMApiArg>({
      query: () => ({ url: `/v1/admin/llm` }),
    }),
    lemonSqueezyWebhookV1WebhooksLemonsqueezyPost: build.mutation<
      LemonSqueezyWebhookV1WebhooksLemonsqueezyPostApiResponse,
      LemonSqueezyWebhookV1WebhooksLemonsqueezyPostApiArg
    >({
      query: () => ({ url: `/v1/webhooks/lemonsqueezy`, method: "POST" }),
    }),
    chatCompletionsV1ChatCompletionsPost: build.mutation<
      ChatCompletionsV1ChatCompletionsPostApiResponse,
      ChatCompletionsV1ChatCompletionsPostApiArg
    >({
      query: (queryArg) => ({
        url: `/v1/chat/completions`,
        method: "POST",
        body: queryArg.chatCompletionRequest,
      }),
    }),
  }),
  overrideExisting: false,
});
export { injectedRtkApi as matemiumApi };
export type HealthHealthGetApiResponse = /** status 200 Successful Response */ {
  [key: string]: any;
};
export type HealthHealthGetApiArg = void;
export type IssueTokenV1AuthTokenPostApiResponse =
  /** status 200 Successful Response */ TokenResponse;
export type IssueTokenV1AuthTokenPostApiArg = {
  tokenRequest: TokenRequest;
};
export type ExchangeSessionV1AuthSessionPostApiResponse =
  /** status 200 Successful Response */ TokenResponse;
export type ExchangeSessionV1AuthSessionPostApiArg = {
  sessionRequest: SessionRequest;
};
export type VerifyTokenV1AuthVerifyGetApiResponse =
  /** status 200 Successful Response */ TokenResponse;
export type VerifyTokenV1AuthVerifyGetApiArg = void;
export type GetMeApiResponse =
  /** status 200 Successful Response */ AccountResponse;
export type GetMeApiArg = void;
export type CreateCheckoutApiResponse =
  /** status 200 Successful Response */ UrlResponse;
export type CreateCheckoutApiArg = {
  checkoutRequest: CheckoutRequest;
};
export type CreatePortalApiResponse =
  /** status 200 Successful Response */ UrlResponse;
export type CreatePortalApiArg = void;
export type GetAdminStatsApiResponse =
  /** status 200 Successful Response */ AdminStats;
export type GetAdminStatsApiArg = void;
export type GetAdminUsersApiResponse =
  /** status 200 Successful Response */ ProfileRow[];
export type GetAdminUsersApiArg = void;
export type GetAdminSubscriptionsApiResponse =
  /** status 200 Successful Response */ SubscriptionRow[];
export type GetAdminSubscriptionsApiArg = void;
export type GetAdminUserApiResponse =
  /** status 200 Successful Response */ AdminUserDetail;
export type GetAdminUserApiArg = {
  userId: string;
};
export type UpdateAdminUserApiResponse =
  /** status 200 Successful Response */ AdminUserDetail;
export type UpdateAdminUserApiArg = {
  userId: string;
  updateUserRequest: UpdateUserRequest;
};
export type UpdateAdminSubscriptionApiResponse =
  /** status 200 Successful Response */ SubscriptionRow;
export type UpdateAdminSubscriptionApiArg = {
  subscriptionId: string;
  updateSubscriptionRequest: UpdateSubscriptionRequest;
};
export type GetAdminLLMApiResponse =
  /** status 200 Successful Response */ LLMInfo;
export type GetAdminLLMApiArg = void;
export type LemonSqueezyWebhookV1WebhooksLemonsqueezyPostApiResponse =
  /** status 200 Successful Response */ {
    [key: string]: boolean;
  };
export type LemonSqueezyWebhookV1WebhooksLemonsqueezyPostApiArg = void;
export type ChatCompletionsV1ChatCompletionsPostApiResponse =
  /** status 200 Successful Response */ ChatCompletionResponse;
export type ChatCompletionsV1ChatCompletionsPostApiArg = {
  chatCompletionRequest: ChatCompletionRequest;
};
export type TokenResponse = {
  access_token: string;
  token_type?: string;
  expires_in: number;
  email?: string | null;
  plan?: string | null;
};
export type ValidationError = {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: any;
  ctx?: object;
};
export type HttpValidationError = {
  detail?: ValidationError[];
};
export type TokenRequest = {
  email: string;
  password: string;
};
export type SessionRequest = {
  access_token: string;
};
export type MeResponse = {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  plan: string;
  lemon_customer_id?: string | null;
};
export type SubscriptionResponse = {
  status?: string | null;
  plan?: string | null;
  current_period_end?: string | null;
};
export type UsageResponse = {
  ai_calls_count?: number;
};
export type AccountResponse = {
  profile: MeResponse;
  subscription?: SubscriptionResponse | null;
  usage?: UsageResponse | null;
};
export type UrlResponse = {
  url: string;
};
export type CheckoutRequest = {
  plan_id?: string;
};
export type AdminStats = {
  total_users: number;
  pro_users: number;
  active_subscriptions: number;
};
export type AdminUserDetail = {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  plan: string;
  lemon_customer_id?: string | null;
  ai_calls_count?: number;
  created_at?: string | null;
  subscription?: SubscriptionRow | null;
};
export type UpdateUserRequest = {
  plan?: string | null;
  role?: string | null;
  ai_calls_count?: number | null;
};
export type UpdateSubscriptionRequest = {
  status?: string | null;
  plan?: string | null;
  current_period_end?: string | null;
  lemon_subscription_id?: string | null;
};
export type LLMInfo = {
  model: string;
  api_base: string;
  stub: boolean;
  prompt_loaded: boolean;
  total_ai_calls?: number;
};
export type ProfileRow = {
  id: string;
  email: string;
  full_name?: string | null;
  role: string;
  plan: string;
  created_at?: string | null;
};
export type SubscriptionRow = {
  id: string;
  user_id: string;
  lemon_subscription_id?: string | null;
  status: string;
  plan: string;
  current_period_end?: string | null;
};
export type ChatMessage = {
  role: string;
  content: string;
};
export type CodeEdit = {
  description: string;
  search?: string | null;
  replace?: string | null;
  full_file?: string | null;
};
export type ChatCompletionResponse = {
  id: string;
  message: ChatMessage;
  code_edit?: CodeEdit | null;
  model: string;
  stub?: boolean;
};
export type ChatCompletionRequest = {
  messages: ChatMessage[];
  project_id?: string | null;
  /** Current scenes.py content or selection for context */
  scenes_excerpt?: string | null;
};
export const {
  useHealthHealthGetQuery,
  useIssueTokenV1AuthTokenPostMutation,
  useExchangeSessionV1AuthSessionPostMutation,
  useVerifyTokenV1AuthVerifyGetQuery,
  useGetMeQuery,
  useCreateCheckoutMutation,
  useCreatePortalMutation,
  useGetAdminStatsQuery,
  useGetAdminUsersQuery,
  useGetAdminSubscriptionsQuery,
  useGetAdminUserQuery,
  useUpdateAdminUserMutation,
  useUpdateAdminSubscriptionMutation,
  useGetAdminLLMQuery,
  useLemonSqueezyWebhookV1WebhooksLemonsqueezyPostMutation,
  useChatCompletionsV1ChatCompletionsPostMutation,
} = injectedRtkApi;
