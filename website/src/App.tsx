import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "@/components/AuthProvider";
import { AdminLayout } from "@/layouts/AdminLayout";
import { DashboardLayout } from "@/layouts/DashboardLayout";
import { RootLayout } from "@/layouts/RootLayout";
import { AdminLLMPage } from "@/pages/admin/AdminLLMPage";
import { AdminOverviewPage } from "@/pages/admin/AdminOverviewPage";
import { AdminUsersPage } from "@/pages/admin/AdminUsersPage";
import { AuthCallbackPage } from "@/pages/AuthCallbackPage";
import { DashboardAccountPage } from "@/pages/dashboard/DashboardAccountPage";
import { DashboardBillingPage } from "@/pages/dashboard/DashboardBillingPage";
import { DashboardDownloadsPage } from "@/pages/dashboard/DashboardDownloadsPage";
import { DashboardOverviewPage } from "@/pages/dashboard/DashboardOverviewPage";
import { DashboardUsagePage } from "@/pages/dashboard/DashboardUsagePage";
import { AcceptableUsePage } from "@/pages/AcceptableUsePage";
import { EULAPage } from "@/pages/EULAPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { PricingPage } from "@/pages/PricingPage";
import { PrivacyPolicyPage } from "@/pages/PrivacyPolicyPage";
import { RefundPolicyPage } from "@/pages/RefundPolicyPage";
import { TermsOfServicePage } from "@/pages/TermsOfServicePage";
import { AdminGuard } from "@/routes/AdminGuard";
import { AuthGuard } from "@/routes/AuthGuard";

export function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <AuthProvider>
        <Routes>
          <Route element={<RootLayout />}>
            <Route index element={<HomePage />} />
            <Route path="pricing" element={<PricingPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="auth/callback" element={<AuthCallbackPage />} />

            {/* Legal / Policy pages */}
            <Route path="privacy" element={<PrivacyPolicyPage />} />
            <Route path="terms" element={<TermsOfServicePage />} />
            <Route path="refund" element={<RefundPolicyPage />} />
            <Route path="license" element={<EULAPage />} />
            <Route path="acceptable-use" element={<AcceptableUsePage />} />

            <Route element={<AuthGuard />}>
              <Route path="dashboard" element={<DashboardLayout />}>
                <Route index element={<DashboardOverviewPage />} />
                <Route path="usage" element={<DashboardUsagePage />} />
                <Route path="billing" element={<DashboardBillingPage />} />
                <Route path="downloads" element={<DashboardDownloadsPage />} />
                <Route path="account" element={<DashboardAccountPage />} />
              </Route>
            </Route>

            <Route element={<AdminGuard />}>
              <Route path="admin" element={<AdminLayout />}>
                <Route index element={<AdminOverviewPage />} />
                <Route path="users" element={<AdminUsersPage />} />
                <Route path="llm" element={<AdminLLMPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
