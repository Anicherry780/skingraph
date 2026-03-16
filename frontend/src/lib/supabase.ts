import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

/** True when both env vars are present — auth features are enabled */
export const supabaseEnabled = !!(supabaseUrl && supabaseAnonKey);

if (!supabaseEnabled) {
  console.warn(
    "[SkinGraph] VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY is missing — auth features disabled."
  );
}

// Create a real client only when env vars exist; otherwise a dummy placeholder
// that will never actually be called (guarded by supabaseEnabled checks).
export const supabase: SupabaseClient = supabaseEnabled
  ? createClient(supabaseUrl!, supabaseAnonKey!)
  : (null as unknown as SupabaseClient);
