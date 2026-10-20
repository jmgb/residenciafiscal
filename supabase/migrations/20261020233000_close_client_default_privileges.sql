-- =============================================================================
-- Cerrar los privilegios por defecto de anon/authenticated en public (2026-10-21)
--
-- Las tablas nuevas que creaba postgres en public nacían con todos los
-- privilegios para anon/authenticated, y sus secuencias con USAGE/SELECT/UPDATE.
-- Hoy public no tiene tablas (los datos viven en private, solo por RPC), así que
-- era un riesgo latente. Supabase retira esos defaults el 2026-10-30; esto lo
-- adelanta y quita también TRUNCATE/REFERENCES/TRIGGER/MAINTAIN. service_role
-- conserva el acceso (default del esquema + default global de 2026-10-21).
-- Las funciones no cambian: siguen naciendo con EXECUTE para PUBLIC, y la
-- convención de REVOKE ALL + GRANT EXECUTE por función sigue vigente.
-- Autoprueba: crea una tabla de prueba en una subtransacción, comprueba que
-- anon/authenticated no tienen ningún privilegio y que service_role tiene CRUD,
-- y la deshace.
-- Rollback (estado anterior exacto):
--   ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
--     GRANT ALL ON TABLES TO anon, authenticated;
--   ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
--     GRANT ALL ON SEQUENCES TO anon, authenticated;
-- =============================================================================

DO $guard$
BEGIN
  IF current_user <> 'postgres' THEN
    RAISE EXCEPTION 'must run as postgres, not %', current_user;
  END IF;
END
$guard$;

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE ALL ON SEQUENCES FROM anon, authenticated;

DO $verify$
DECLARE
  role_name text;
  priv text;
  found text[] := '{}';
BEGIN
  BEGIN
    CREATE TABLE public._client_default_probe (id bigserial PRIMARY KEY);
    FOREACH role_name IN ARRAY ARRAY['anon', 'authenticated'] LOOP
      FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE',
                                  'REFERENCES', 'TRIGGER', 'MAINTAIN'] LOOP
        IF has_table_privilege(role_name, 'public._client_default_probe', priv) THEN
          found := found || (role_name || ' table ' || priv);
        END IF;
      END LOOP;
      FOREACH priv IN ARRAY ARRAY['USAGE', 'SELECT', 'UPDATE'] LOOP
        IF has_sequence_privilege(role_name, 'public._client_default_probe_id_seq', priv) THEN
          found := found || (role_name || ' sequence ' || priv);
        END IF;
      END LOOP;
    END LOOP;
    FOREACH priv IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE'] LOOP
      IF NOT has_table_privilege('service_role', 'public._client_default_probe', priv) THEN
        found := found || ('service_role lacks table ' || priv);
      END IF;
    END LOOP;
    RAISE EXCEPTION 'client_default_selftest_rollback';
  EXCEPTION WHEN raise_exception THEN
    IF SQLERRM <> 'client_default_selftest_rollback' THEN
      RAISE;
    END IF;
  END;
  IF cardinality(found) > 0 THEN
    RAISE EXCEPTION 'client default privileges self-test failed: %', found;
  END IF;
  IF to_regclass('public._client_default_probe') IS NOT NULL THEN
    RAISE EXCEPTION 'self-test probe table was not rolled back';
  END IF;
END
$verify$;
