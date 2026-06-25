import { useEffect, type ReactNode } from "react";
import { useDispatch } from "react-redux";

import { clearSession, setSession } from "@/store/authSlice";
import { supabase } from "@/supabase/client";

export function AuthProvider({ children }: { children: ReactNode }) {
  const dispatch = useDispatch();

  useEffect(() => {
    async function syncSession() {
      const { data } = await supabase.auth.getSession();
      const session = data.session;
      dispatch(
        setSession({
          user: session?.user ?? null,
          accessToken: session?.access_token ?? null,
        })
      );
    }

    void syncSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        dispatch(
          setSession({
            user: session.user,
            accessToken: session.access_token,
          })
        );
      } else {
        dispatch(clearSession());
      }
    });

    return () => subscription.unsubscribe();
  }, [dispatch]);

  return children;
}