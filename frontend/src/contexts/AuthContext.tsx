import React, { createContext, useContext, useEffect, useState } from "react";
import { supabase, supabaseEnabled } from "../lib/supabase";
import type { User, Session } from "@supabase/supabase-js";

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  signUp: (email: string, password: string) => Promise<{ error: string | null }>;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  deleteAccount: () => Promise<{ error: string | null }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // If Supabase isn't configured, skip auth entirely
    if (!supabaseEnabled) {
      setLoading(false);
      return;
    }

    // Get initial session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setUser(s?.user ?? null);
      if (s?.user) ensureProfile(s.user.id);
      setLoading(false);
    });

    // Listen for changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      setSession(s);
      setUser(s?.user ?? null);
      if (s?.user) ensureProfile(s.user.id);
    });

    return () => subscription.unsubscribe();
  }, []);

  /** Create a user_profiles row if it doesn't exist yet */
  async function ensureProfile(userId: string) {
    if (!supabaseEnabled) return;
    const { data } = await supabase
      .from("user_profiles")
      .select("id")
      .eq("id", userId)
      .single();

    if (!data) {
      await supabase.from("user_profiles").insert({ id: userId });
    }
  }

  const signUp = async (email: string, password: string) => {
    if (!supabaseEnabled) return { error: "Auth is not configured" };
    const { error } = await supabase.auth.signUp({ email, password });
    return { error: error?.message ?? null };
  };

  const signIn = async (email: string, password: string) => {
    if (!supabaseEnabled) return { error: "Auth is not configured" };
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return { error: error?.message ?? null };
  };

  const signInWithGoogle = async () => {
    if (!supabaseEnabled) return;
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin + "/dashboard" },
    });
  };

  const signOut = async () => {
    if (!supabaseEnabled) return;
    await supabase.auth.signOut();
  };

  const deleteAccount = async () => {
    if (!supabaseEnabled) return { error: "Auth is not configured" };
    // Call the secure Postgres function (RPC) we will create in the database
    const { error } = await supabase.rpc('delete_user_account');
    if (!error) {
      // If it succeeded, clear local state and log out
      setUser(null);
      setSession(null);
      await supabase.auth.signOut();
    }
    return { error: error?.message ?? null };
  };

  return (
    <AuthContext.Provider
      value={{ user, session, loading, signUp, signIn, signInWithGoogle, signOut, deleteAccount }}
    >
      {children}
    </AuthContext.Provider>
  );
};
