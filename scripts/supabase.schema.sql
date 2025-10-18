-- Supabase Schema for Optimus Pipeline

-- Safe extension enablement
create extension if not exists "pgcrypto";
create extension if not exists "uuid-ossp";
create extension if not exists "vector";

-- Products table
create table if not exists public.products (
  id uuid primary key default uuid_generate_v4(),
  source_id text,
  title text not null,
  description text,
  product_type text,
  tags text[],
  vendor text,
  handle text,
  status text default 'pending',
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Pipeline runs
create table if not exists public.pipeline_runs (
  id uuid primary key default uuid_generate_v4(),
  product_id uuid references public.products(id) on delete cascade,
  stage text check (stage in ('normalize', 'rewrite', 'seo', 'tags', 'complete')),
  status text check (status in ('pending', 'running', 'done', 'error')) default 'pending',
  output jsonb,
  error text,
  started_at timestamp with time zone default now(),
  finished_at timestamp with time zone
);

-- Prompts table
create table if not exists public.prompts (
  id uuid primary key default uuid_generate_v4(),
  name text unique not null,
  content text not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Vector embeddings for products (optional, used for search)
create table if not exists public.product_embeddings (
  id uuid primary key default uuid_generate_v4(),
  product_id uuid references public.products(id) on delete cascade,
  embedding vector(1536),
  created_at timestamp with time zone default now()
);

-- Change log for product transformations
create table if not exists public.change_logs (
  id uuid primary key default uuid_generate_v4(),
  product_id uuid references public.products(id) on delete cascade,
  action text,
  old_data jsonb,
  new_data jsonb,
  created_at timestamp with time zone default now()
);

-- Audit view for dashboard
create view public.pipeline_summary as
select
  p.id as product_id,
  p.title,
  pr.stage,
  pr.status,
  pr.started_at,
  pr.finished_at
from public.pipeline_runs pr
join public.products p on pr.product_id = p.id;
