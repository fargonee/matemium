import { useState } from "react";

import { useCreatePortalMutation } from "@/api/matemiumApi";
import { Button } from "@/components/ui/button";

interface ManageBillingButtonProps {
  hasSubscription: boolean;
}

export function ManageBillingButton({ hasSubscription }: ManageBillingButtonProps) {
  const [createPortal] = useCreatePortalMutation();
  const [loading, setLoading] = useState(false);

  async function openPortal() {
    setLoading(true);
    try {
      const result = await createPortal().unwrap();
      if (result.url) {
        window.location.href = result.url;
      }
    } finally {
      setLoading(false);
    }
  }

  if (!hasSubscription) {
    return (
      <Button variant="secondary" disabled>
        No active subscription
      </Button>
    );
  }

  return (
    <Button variant="secondary" onClick={openPortal} disabled={loading}>
      {loading ? "Opening…" : "Manage billing"}
    </Button>
  );
}