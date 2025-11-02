from config import supabase

def get_user_profile(user_id: str):
    res = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
    if res.data:
        return res.data[0]
    return None