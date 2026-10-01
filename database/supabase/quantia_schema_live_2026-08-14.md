# Estructura viva de Supabase ? Quantia

- Fecha de extracci?n: `2026-08-14` (`America/Mexico_City`).
- Proyecto: `Quantia` (`aifhkabgejwwxvurffqi`).
- PostgreSQL: `17.6.1.084`.
- PostgREST: `14.4`.
- Fuente: introspecci?n oficial de Supabase/PostgREST con acceso de servicio, sin lectura del contenido de las filas.
- Alcance detallado de este documento: esquema `public` y configuraci?n de buckets. Los esquemas administrados `auth` y `storage` est?n completos en el archivo TypeScript complementario.

## Resumen

- Tablas `public`: **46**.
- Funciones RPC p?blicas: **2**.
- Buckets: **1**.
- Vistas p?blicas expuestas: **0**.
- Enums p?blicos: **0**.

## Tablas del esquema public

### `app_cotizaciones`

Registros actuales: `21`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `user_id` | `uuid` | S? | `?` | FK ? `app_users.id` |
| `user_email` | `text` | No | `?` | ? |
| `status` | `text` | No | `draft` | ? |
| `modulo` | `text` | No | `vivienda` | ? |
| `subtipo` | `text` | S? | `?` | ? |
| `current_step` | `text` | S? | `?` | ? |
| `flow_version` | `text` | No | `v4` | ? |
| `payload_json` | `jsonb` | No | `?` | ? |
| `resumen_json` | `jsonb` | No | `?` | ? |
| `total` | `numeric` | No | `0` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `app_users`

Registros actuales: `2`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `nombre` | `text` | No | `?` | ? |
| `email` | `text` | No | `?` | ? |
| `telefono` | `text` | S? | `?` | ? |
| `profesion` | `text` | S? | `?` | ? |
| `alias` | `text` | S? | `?` | ? |
| `direccion` | `text` | S? | `?` | ? |
| `perfil` | `text` | No | `oficial` | ? |
| `password_hash` | `text` | No | `` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_categories`

Registros actuales: `14`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `module_id` | `uuid` | No | `?` | FK ? `catalog_modules.id` |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `sort_order` | `integer` | No | `0` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_concept_aliases`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_id` | `uuid` | No | `?` | FK ? `catalog_concepts.id` |
| `alias` | `text` | No | `?` | ? |
| `alias_type` | `text` | No | `busqueda` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_concept_documents`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_id` | `uuid` | No | `?` | FK ? `catalog_concepts.id` |
| `document_type` | `text` | No | `?` | ? |
| `title` | `text` | No | `?` | ? |
| `file_url` | `text` | S? | `?` | ? |
| `notes` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_concept_space_types`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_id` | `uuid` | No | `?` | FK ? `catalog_concepts.id` |
| `space_type_id` | `uuid` | No | `?` | FK ? `catalog_space_types.id` |
| `applicability_mode` | `text` | No | `compatible` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_concept_specifications`

Registros actuales: `99`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_id` | `uuid` | No | `?` | FK ? `catalog_concepts.id` |
| `jurisdiction` | `text` | No | `?` | ? |
| `mode` | `text` | No | `tecnico` | ? |
| `version` | `text` | S? | `?` | ? |
| `normative_basis_json` | `jsonb` | No | `?` | ? |
| `technical_specification` | `text` | S? | `?` | ? |
| `official_specification` | `text` | S? | `?` | ? |
| `volumetry_rules_json` | `jsonb` | No | `?` | ? |
| `validation_rules_json` | `jsonb` | No | `?` | ? |
| `output_template_json` | `jsonb` | No | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_concept_systems`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_id` | `uuid` | No | `?` | FK ? `catalog_concepts.id` |
| `construction_system_id` | `uuid` | No | `?` | FK ? `catalog_construction_systems.id` |
| `applicability_mode` | `text` | No | `compatible` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_concepts`

Registros actuales: `102`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `partida_id` | `uuid` | S? | `?` | FK ? `catalog_partidas.id` |
| `subalcance_id` | `uuid` | S? | `?` | ? |
| `unit_id` | `uuid` | S? | `?` | FK ? `catalog_units.id` |
| `code` | `text` | No | `?` | ? |
| `technical_description` | `text` | S? | `?` | ? |
| `official_description` | `text` | S? | `?` | ? |
| `finish_level` | `text` | S? | `?` | ? |
| `applies_private_housing` | `boolean` | No | `True` | ? |
| `is_optional` | `boolean` | No | `False` | ? |
| `requires_space_context` | `boolean` | No | `False` | ? |
| `requires_system_context` | `boolean` | No | `False` | ? |
| `requires_normative_validation` | `boolean` | No | `True` | ? |
| `quantification_mode` | `text` | No | `directa` | ? |
| `default_formula_code` | `text` | S? | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `notes` | `text` | S? | `?` | ? |
| `metadata_json` | `jsonb` | No | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_construction_systems`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `partida_id` | `uuid` | S? | `?` | FK ? `catalog_partidas.id` |
| `system_group` | `text` | No | `?` | ? |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `compatibility_json` | `jsonb` | No | `?` | ? |
| `volumetry_json` | `jsonb` | No | `?` | ? |
| `needs_engineering_validation` | `boolean` | No | `False` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_jurisdictions`

Registros actuales: `1`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `jurisdiction_type` | `text` | No | `?` | ? |
| `state_code` | `text` | S? | `?` | ? |
| `municipality_name` | `text` | S? | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_modules`

Registros actuales: `1`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `sort_order` | `integer` | No | `0` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_normative_sources`

Registros actuales: `1`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `jurisdiction_id` | `uuid` | S? | `?` | FK ? `catalog_jurisdictions.id` |
| `code` | `text` | No | `?` | ? |
| `title` | `text` | No | `?` | ? |
| `short_name` | `text` | S? | `?` | ? |
| `source_type` | `text` | No | `?` | ? |
| `publication_date` | `date` | S? | `?` | ? |
| `effective_date` | `date` | S? | `?` | ? |
| `source_url` | `text` | S? | `?` | ? |
| `notes` | `text` | S? | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_partidas`

Registros actuales: `14`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `module_id` | `uuid` | No | `?` | FK ? `catalog_modules.id` |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `sort_order` | `integer` | No | `0` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_space_types`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `is_habitable` | `boolean` | No | `False` | ? |
| `is_service` | `boolean` | No | `False` | ? |
| `is_exterior` | `boolean` | No | `False` | ? |
| `sort_order` | `integer` | No | `0` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_system_types`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `system_group` | `text` | No | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `catalog_units`

Registros actuales: `8`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `symbol` | `text` | S? | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `document_chunks`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `chunk_id` | `text` | No | `?` | PK |
| `document_id` | `uuid` | No | `?` | FK ? `documents.id` |
| `chunk_index` | `integer` | No | `?` | ? |
| `content` | `text` | No | `?` | ? |
| `embedding` | `extensions.vector(384)` | No | `?` | ? |
| `metadata` | `jsonb` | No | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `now()` | ? |

### `documents`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `?` | PK |
| `user_id` | `uuid` | No | `?` | FK ? `app_users.id` |
| `quote_id` | `uuid` | S? | `?` | FK ? `app_cotizaciones.id` |
| `module_key` | `text` | S? | `?` | ? |
| `original_file_name` | `text` | No | `?` | ? |
| `storage_bucket` | `text` | No | `quantia-documents` | ? |
| `storage_object_path` | `text` | No | `?` | ? |
| `mime_type` | `text` | No | `?` | ? |
| `size_bytes` | `bigint` | No | `?` | ? |
| `file_checksum` | `text` | No | `?` | ? |
| `status` | `text` | No | `uploaded` | ? |
| `ocr_text` | `text` | No | `` | ? |
| `ocr_metadata` | `jsonb` | No | `?` | ? |
| `embedding_model` | `text` | S? | `?` | ? |
| `processing_version` | `text` | No | `ocr-rag-v1` | ? |
| `chunk_count` | `integer` | No | `0` | ? |
| `error_detail` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `now()` | ? |
| `updated_at` | `timestamp with time zone` | No | `now()` | ? |

### `engine_activation_rules`

Registros actuales: `102`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `concept_spec_id` | `uuid` | No | `?` | FK ? `engine_concept_specs.id` |
| `rule_name` | `text` | No | `?` | ? |
| `priority` | `integer` | No | `100` | ? |
| `activation_type` | `text` | No | `?` | ? |
| `type_intervention` | `text` | S? | `?` | ? |
| `scope` | `text` | S? | `?` | ? |
| `applies_from_level` | `integer` | S? | `?` | ? |
| `applies_to_level` | `integer` | S? | `?` | ? |
| `trigger_json` | `jsonb` | No | `?` | ? |
| `condition_json` | `jsonb` | No | `?` | ? |
| `derivation_json` | `jsonb` | No | `?` | ? |
| `invalidates_json` | `jsonb` | No | `?` | ? |
| `alerts_json` | `jsonb` | No | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `output_action_json` | `jsonb` | No | `?` | ? |
| `stop_on_error` | `boolean` | No | `False` | ? |

### `engine_concept_spec_sources`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_spec_id` | `uuid` | No | `?` | FK ? `engine_concept_specs.id` |
| `source_id` | `uuid` | No | `?` | FK ? `catalog_normative_sources.id` |
| `clause_reference` | `text` | S? | `?` | ? |
| `source_role` | `text` | No | `referencia` | ? |
| `notes` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `engine_concept_spec_space_types`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_spec_id` | `uuid` | No | `?` | FK ? `engine_concept_specs.id` |
| `space_type_id` | `uuid` | No | `?` | FK ? `catalog_space_types.id` |
| `applicability` | `text` | No | `compatible` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `engine_concept_spec_systems`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_spec_id` | `uuid` | No | `?` | FK ? `engine_concept_specs.id` |
| `system_type_id` | `uuid` | No | `?` | FK ? `catalog_system_types.id` |
| `applicability` | `text` | No | `compatible` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `engine_concept_specs`

Registros actuales: `102`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_id` | `uuid` | No | `?` | FK ? `catalog_concepts.id` |
| `spec_profile_id` | `uuid` | No | `?` | FK ? `engine_spec_profiles.id` |
| `section_type_id` | `uuid` | S? | `?` | FK ? `engine_section_types.id` |
| `concrete_spec_id` | `uuid` | S? | `?` | FK ? `engine_material_specs.id` |
| `formwork_spec_id` | `uuid` | S? | `?` | FK ? `engine_material_specs.id` |
| `reinforcement_spec_id` | `uuid` | S? | `?` | FK ? `engine_reinforcement_specs.id` |
| `formula_id` | `uuid` | S? | `?` | FK ? `engine_formulas.id` |
| `spec_code` | `text` | No | `?` | ? |
| `spec_name` | `text` | No | `?` | ? |
| `application_mode` | `text` | No | `automatico` | ? |
| `output_mode` | `text` | No | `base` | ? |
| `applies_first_level_only` | `boolean` | No | `False` | ? |
| `requires_project_definition` | `boolean` | No | `False` | ? |
| `allows_user_override` | `boolean` | No | `False` | ? |
| `default_quantity_mode` | `text` | No | `?` | ? |
| `technical_scope_text` | `text` | S? | `?` | ? |
| `quality_text` | `text` | S? | `?` | ? |
| `includes_text` | `text` | S? | `?` | ? |
| `excludes_text` | `text` | S? | `?` | ? |
| `normative_notes` | `text` | S? | `?` | ? |
| `inference_strategy` | `text` | S? | `?` | ? |
| `parameter_defaults` | `jsonb` | No | `?` | ? |
| `parameter_rules` | `jsonb` | No | `?` | ? |
| `validations_json` | `jsonb` | No | `?` | ? |
| `dependencies_json` | `jsonb` | No | `?` | ? |
| `exclusions_json` | `jsonb` | No | `?` | ? |
| `metadata_json` | `jsonb` | No | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `quantity_multiplier` | `numeric` | S? | `?` | ? |
| `notes` | `text` | S? | `?` | ? |
| `execution_priority` | `integer` | S? | `?` | ? |

### `engine_formulas`

Registros actuales: `7`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `expression` | `text` | No | `?` | ? |
| `result_unit_symbol` | `text` | S? | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `variables_schema` | `jsonb` | No | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `engine_material_specs`

Registros actuales: `1`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `material_group` | `text` | No | `?` | ? |
| `material_name` | `text` | No | `?` | ? |
| `strength_value` | `numeric` | S? | `?` | ? |
| `strength_unit` | `text` | S? | `?` | ? |
| `quality_grade` | `text` | S? | `?` | ? |
| `commercial_variant` | `text` | S? | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `engine_reinforcement_specs`

Registros actuales: `1`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `reinforcement_type` | `text` | No | `?` | ? |
| `longitudinal_bars` | `text` | S? | `?` | ? |
| `stirrups` | `text` | S? | `?` | ? |
| `spacing_cm` | `numeric` | S? | `?` | ? |
| `commercial_name` | `text` | S? | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `engine_section_types`

Registros actuales: `1`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `section_group` | `text` | No | `?` | ? |
| `width_m` | `numeric` | S? | `?` | ? |
| `height_m` | `numeric` | S? | `?` | ? |
| `depth_m` | `numeric` | S? | `?` | ? |
| `thickness_m` | `numeric` | S? | `?` | ? |
| `diameter_mm` | `numeric` | S? | `?` | ? |
| `area_m2` | `numeric` | S? | `?` | ? |
| `volume_factor` | `numeric` | S? | `?` | ? |
| `description` | `text` | S? | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `engine_spec_profiles`

Registros actuales: `7`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `profile_group` | `text` | No | `?` | ? |
| `geometry_kind` | `text` | No | `?` | ? |
| `unit_formula_symbol` | `text` | S? | `?` | ? |
| `applies_first_level_only` | `boolean` | No | `False` | ? |
| `description` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `price_concept_bases`

Registros actuales: `389`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `concept_spec_id` | `uuid` | No | `?` | FK ? `engine_concept_specs.id` |
| `region_id` | `uuid` | S? | `?` | FK ? `price_regions.id` |
| `source_name` | `text` | S? | `?` | ? |
| `unit_price` | `numeric` | S? | `?` | ? |
| `valid_from` | `date` | S? | `?` | ? |
| `valid_to` | `date` | S? | `?` | ? |
| `notes` | `text` | S? | `?` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `price_regions`

Registros actuales: `1`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `code` | `text` | No | `?` | ? |
| `state_code` | `text` | S? | `?` | ? |
| `municipality_name` | `text` | S? | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `currency` | `text` | No | `MXN` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `profiles`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |

### `simulation_alerts`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `run_id` | `uuid` | S? | `?` | FK ? `simulation_inference_runs.id` |
| `alert_level` | `text` | No | `?` | ? |
| `source_type` | `text` | No | `?` | ? |
| `source_reference` | `text` | S? | `?` | ? |
| `message` | `text` | No | `?` | ? |
| `metadata_json` | `jsonb` | No | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_concept_dependencies`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_concept_id` | `uuid` | No | `?` | FK ? `simulation_concepts.id` |
| `depends_on_simulation_concept_id` | `uuid` | No | `?` | FK ? `simulation_concepts.id` |
| `dependency_role` | `text` | No | `relacionado` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_concepts`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |

### `simulation_inference_runs`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `run_status` | `text` | No | `draft` | ? |
| `triggered_by` | `uuid` | S? | `?` | FK ? `profiles.id` |
| `rule_snapshot` | `jsonb` | No | `?` | ? |
| `notes` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_levels`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `level_number` | `integer` | No | `?` | ? |
| `name` | `text` | No | `?` | ? |
| `elevation_m` | `numeric` | S? | `?` | ? |
| `clear_height_m` | `numeric` | S? | `?` | ? |
| `is_roof` | `boolean` | No | `False` | ? |
| `is_active` | `boolean` | No | `True` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_openings`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `face_id` | `uuid` | No | `?` | FK ? `simulation_space_faces.id` |
| `opening_type` | `text` | No | `?` | ? |
| `width_m` | `numeric` | No | `?` | ? |
| `height_m` | `numeric` | No | `?` | ? |
| `sill_height_m` | `numeric` | S? | `?` | ? |
| `quantity` | `integer` | No | `1` | ? |
| `area_m2` | `numeric` | S? | `?` | ? |
| `is_exterior` | `boolean` | No | `False` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_space_adjacencies`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `face_id` | `uuid` | No | `?` | FK ? `simulation_space_faces.id` |
| `adjacent_space_id` | `uuid` | S? | `?` | FK ? `simulation_spaces.id` |
| `adjacency_type` | `text` | No | `?` | ? |
| `notes` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_space_faces`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `space_id` | `uuid` | No | `?` | FK ? `simulation_spaces.id` |
| `face_code` | `text` | No | `?` | ? |
| `orientation` | `text` | S? | `?` | ? |
| `length_m` | `numeric` | S? | `?` | ? |
| `height_m` | `numeric` | S? | `?` | ? |
| `gross_area_m2` | `numeric` | S? | `?` | ? |
| `net_area_m2` | `numeric` | S? | `?` | ? |
| `thickness_m` | `numeric` | S? | `?` | ? |
| `face_type` | `text` | No | `muro` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_space_openings`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `space_id` | `uuid` | No | `?` | FK ? `simulation_spaces.id` |
| `face_id` | `uuid` | S? | `?` | FK ? `simulation_space_faces.id` |
| `opening_type` | `text` | No | `?` | ? |
| `width_m` | `numeric` | S? | `?` | ? |
| `height_m` | `numeric` | S? | `?` | ? |
| `quantity` | `integer` | No | `1` | ? |
| `is_existing` | `boolean` | No | `False` | ? |
| `metadata_json` | `jsonb` | No | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_space_services`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `space_id` | `uuid` | No | `?` | FK ? `simulation_spaces.id` |
| `service_type` | `text` | No | `?` | ? |
| `service_key` | `text` | No | `?` | ? |
| `quantity` | `integer` | No | `1` | ? |
| `is_required` | `boolean` | No | `True` | ? |
| `source` | `text` | No | `inference` | ? |
| `metadata_json` | `jsonb` | No | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_spaces`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |

### `simulation_systems`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `system_type_id` | `uuid` | No | `?` | FK ? `catalog_system_types.id` |
| `level_id` | `uuid` | S? | `?` | FK ? `simulation_levels.id` |
| `applies_to_space_id` | `uuid` | S? | `?` | FK ? `simulation_spaces.id` |
| `name` | `text` | No | `?` | ? |
| `configuration_json` | `jsonb` | No | `?` | ? |
| `notes` | `text` | S? | `?` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulation_user_inputs`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |
| `simulation_id` | `uuid` | No | `?` | FK ? `simulations.id` |
| `input_scope` | `text` | No | `?` | ? |
| `level_id` | `uuid` | S? | `?` | FK ? `simulation_levels.id` |
| `space_id` | `uuid` | S? | `?` | FK ? `simulation_spaces.id` |
| `face_id` | `uuid` | S? | `?` | FK ? `simulation_space_faces.id` |
| `system_id` | `uuid` | S? | `?` | FK ? `simulation_systems.id` |
| `key` | `text` | No | `?` | ? |
| `value_json` | `jsonb` | No | `?` | ? |
| `source` | `text` | No | `usuario` | ? |
| `created_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |
| `updated_at` | `timestamp with time zone` | No | `timezone('utc'::text, now())` | ? |

### `simulations`

Registros actuales: `0`.

| Columna | Tipo PostgreSQL | Nulo | Default | Clave / referencia |
|---|---|:---:|---|---|
| `id` | `uuid` | No | `gen_random_uuid()` | PK |

## Funciones RPC p?blicas

### `get_latest_quote_draft`

| Par?metro | Tipo | Obligatorio |
|---|---|:---:|
| `p_modulo` | `text` | No |
| `p_subtipo` | `text` | No |
| `p_user_email` | `text` | S? |

### `match_document_chunks`

| Par?metro | Tipo | Obligatorio |
|---|---|:---:|
| `filter_document_id` | `uuid` | S? |
| `match_count` | `integer` | S? |
| `query_embedding` | `extensions.vector` | S? |

## Supabase Storage

### Bucket `quantia-documents`

- ID: `quantia-documents`.
- P?blico: `no`.
- L?mite por archivo: `20971520` bytes.
- MIME permitidos: `application/pdf`, `text/plain`, `text/markdown`, `application/json`, `image/png`, `image/jpeg`, `image/bmp`, `image/tiff`.
- Creado: `2026-08-12T02:45:13.599Z`.
- Actualizado: `2026-08-12T02:45:13.599Z`.

## Esquemas administrados por Supabase

El archivo `quantia_database_live_2026-08-14.types.ts` contiene la estructura exacta generada por Supabase para:

- `auth`: 23 tablas, sus columnas, nulabilidad, enums y relaciones.
- `public`: 46 tablas, 2 funciones y todas las relaciones expuestas.
- `storage`: 8 tablas, funciones, relaciones y el enum `buckettype`.

## L?mite de la extracci?n

La estructura l?gica (tablas, columnas, tipos, nulabilidad, defaults, PK, FK y firmas RPC) proviene del esquema vivo. Los metadatos f?sicos no publicados por la API ??ndices no asociados a PK, restricciones CHECK, cuerpos de triggers, pol?ticas RLS y GRANT detallados? requieren un `pg_dump` o acceso SQL directo. El intento de `db dump` fue rechazado por la configuraci?n del rol temporal de la CLI del proyecto; no se alteraron privilegios.
