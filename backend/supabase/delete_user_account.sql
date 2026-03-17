-- RUN THIS SCRIPT IN THE SUPABASE SQL EDITOR

-- 1. Create a secure function to delete a user's own account
CREATE OR REPLACE FUNCTION delete_user_account()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  -- Check if the user is authenticated
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  -- Delete all related data first to prevent foreign key constraint violations
  DELETE FROM public.user_profiles WHERE id = auth.uid();
  DELETE FROM public.user_analyses WHERE user_id = auth.uid();
  DELETE FROM public.user_saved_products WHERE user_id = auth.uid();

  -- Finally delete the user from auth.users
  DELETE FROM auth.users WHERE id = auth.uid();
END;
$$;

-- 2. Grant permissions
GRANT EXECUTE ON FUNCTION delete_user_account() TO authenticated;
