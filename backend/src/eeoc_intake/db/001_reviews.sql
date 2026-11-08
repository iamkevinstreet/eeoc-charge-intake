-- The reviews database, version 1: every review with its extraction,
-- each field's latest decision, and every export, which is never
-- changed or deleted once written. Applied once, in order, by
-- api/store.py, which records it in schema_migrations.

create table reviews (
    review_id   text primary key check (review_id ~ '^[0-9a-f]{10}$'),
    source      text not null check (source ~ '^(sample|upload):'),
    demo        boolean not null,
    created_at  timestamptz not null,
    request_id  text not null,
    extraction  jsonb not null
);

create table decisions (
    review_id   text not null references reviews (review_id) on delete cascade,
    field       text not null,
    action      text not null check (action in ('accept', 'edit', 'reject')),
    value       jsonb,
    decided_at  timestamptz not null default now(),
    primary key (review_id, field)
);

create table exports (
    export_id    bigint generated always as identity primary key,
    review_id    text not null references reviews (review_id),
    exported_at  timestamptz not null,
    contract     text not null,
    payload      jsonb not null
);

create index exports_by_review on exports (review_id, exported_at);

-- An export is a record of what left the service: refuse any change.
create function refuse_export_change() returns trigger language plpgsql as $$
begin
    raise exception 'exports are append-only: % refused', tg_op;
end
$$;

create trigger exports_append_only
    before update or delete on exports
    for each row execute function refuse_export_change();
