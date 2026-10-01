begin;

create extension if not exists vector with schema extensions;

create table if not exists public.documents (
    id uuid primary key,
    user_id uuid not null references public.app_users(id) on delete cascade,
    quote_id uuid null references public.app_cotizaciones(id) on delete set null,
    module_key text null,
    original_file_name text not null,
    storage_bucket text not null default 'quantia-documents',
    storage_object_path text not null unique,
    mime_type text not null,
    size_bytes bigint not null check (size_bytes > 0),
    file_checksum text not null check (char_length(file_checksum) = 64),
    status text not null default 'uploaded' check (
        status in ('uploaded', 'ocr_processing', 'ocr_completed', 'indexing', 'ready', 'failed')
    ),
    ocr_text text not null default '',
    ocr_metadata jsonb not null default '{}'::jsonb,
    embedding_model text null,
    processing_version text not null default 'ocr-rag-v1',
    chunk_count integer not null default 0 check (chunk_count >= 0),
    error_detail text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists documents_user_created_idx
    on public.documents (user_id, created_at desc);

create index if not exists documents_quote_idx
    on public.documents (quote_id)
    where quote_id is not null;

create index if not exists documents_checksum_idx
    on public.documents (user_id, file_checksum);

create table if not exists public.document_chunks (
    chunk_id text primary key,
    document_id uuid not null references public.documents(id) on delete cascade,
    chunk_index integer not null check (chunk_index >= 0),
    content text not null check (char_length(btrim(content)) > 0),
    embedding extensions.vector(384) not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (document_id, chunk_index)
);

create index if not exists document_chunks_document_idx
    on public.document_chunks (document_id, chunk_index);

create index if not exists document_chunks_embedding_hnsw_idx
    on public.document_chunks
    using hnsw (embedding extensions.vector_cosine_ops);

create or replace function public.set_document_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists documents_set_updated_at on public.documents;
create trigger documents_set_updated_at
before update on public.documents
for each row execute function public.set_document_updated_at();

create or replace function public.match_document_chunks(
    query_embedding extensions.vector(384),
    match_count integer,
    filter_document_id uuid
)
returns table (
    document_id uuid,
    chunk_id text,
    content text,
    embedding extensions.vector(384),
    metadata jsonb,
    chunk_index integer,
    similarity double precision
)
language sql
stable
set search_path = public, extensions
as $$
    select
        dc.document_id,
        dc.chunk_id,
        dc.content,
        dc.embedding,
        dc.metadata,
        dc.chunk_index,
        (1 - (dc.embedding <=> query_embedding))::double precision as similarity
    from public.document_chunks dc
    where dc.document_id = filter_document_id
    order by dc.embedding <=> query_embedding
    limit greatest(match_count, 0);
$$;

alter table public.documents enable row level security;
alter table public.document_chunks enable row level security;

revoke all on public.documents from anon, authenticated;
revoke all on public.document_chunks from anon, authenticated;
revoke all on function public.match_document_chunks(extensions.vector, integer, uuid) from public, anon, authenticated;
grant execute on function public.match_document_chunks(extensions.vector, integer, uuid) to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'quantia-documents',
    'quantia-documents',
    false,
    20971520,
    array[
        'application/pdf',
        'text/plain',
        'text/markdown',
        'application/json',
        'image/png',
        'image/jpeg',
        'image/bmp',
        'image/tiff'
    ]
)
on conflict (id) do update set
    public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

commit;
