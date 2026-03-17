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

  -- Delete the user from auth.users
  -- This will automatically cascade to user_profiles, user_analyses, and user_saved_products
  -- because we set up those foreign keys with ON DELETE CASCADE
  DELETE FROM auth.users WHERE id = auth.uid();
END;
$$;

-- 2. Grant permissions
GRANT EXECUTE ON FUNCTION delete_user_account() TO authenticated;
