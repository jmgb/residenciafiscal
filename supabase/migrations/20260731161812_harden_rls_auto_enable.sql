-- El proyecto nuevo trae esta función SECURITY DEFINER con EXECUTE público.
-- El trigger interno se ejecuta como propietario y no necesita exponerla por API.
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable()
    FROM PUBLIC, anon, authenticated, service_role;
