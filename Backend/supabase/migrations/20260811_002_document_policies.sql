begin;

-- La aplicacion rechaza duplicados antes de subir el binario. Este indice
-- garantiza la misma regla ante cargas concurrentes o multiples workers.
drop index if exists public.documents_checksum_idx;

create unique index if not exists documents_user_checksum_uidx
    on public.documents (user_id, file_checksum);

commit;
