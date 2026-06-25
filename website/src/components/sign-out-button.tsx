import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { supabase } from "@/supabase/client";

export function SignOutButton() {
  const navigate = useNavigate();

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate("/");
  }

  return (
    <Button variant="secondary" size="sm" onClick={handleSignOut}>
      Sign out
    </Button>
  );
}