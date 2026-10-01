export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.4"
  }
  auth: {
    Tables: {
      audit_log_entries: {
        Row: {
          created_at: string | null
          id: string
          instance_id: string | null
          ip_address: string
          payload: Json | null
        }
        Insert: {
          created_at?: string | null
          id: string
          instance_id?: string | null
          ip_address?: string
          payload?: Json | null
        }
        Update: {
          created_at?: string | null
          id?: string
          instance_id?: string | null
          ip_address?: string
          payload?: Json | null
        }
        Relationships: []
      }
      custom_oauth_providers: {
        Row: {
          acceptable_client_ids: string[]
          attribute_mapping: Json
          authorization_params: Json
          authorization_url: string | null
          cached_discovery: Json | null
          client_id: string
          client_secret: string
          created_at: string
          custom_claims_allowlist: string[]
          discovery_cached_at: string | null
          discovery_url: string | null
          email_optional: boolean
          enabled: boolean
          id: string
          identifier: string
          issuer: string | null
          jwks_uri: string | null
          name: string
          pkce_enabled: boolean
          provider_type: string
          scopes: string[]
          skip_nonce_check: boolean
          token_url: string | null
          updated_at: string
          userinfo_url: string | null
        }
        Insert: {
          acceptable_client_ids?: string[]
          attribute_mapping?: Json
          authorization_params?: Json
          authorization_url?: string | null
          cached_discovery?: Json | null
          client_id: string
          client_secret: string
          created_at?: string
          custom_claims_allowlist?: string[]
          discovery_cached_at?: string | null
          discovery_url?: string | null
          email_optional?: boolean
          enabled?: boolean
          id?: string
          identifier: string
          issuer?: string | null
          jwks_uri?: string | null
          name: string
          pkce_enabled?: boolean
          provider_type: string
          scopes?: string[]
          skip_nonce_check?: boolean
          token_url?: string | null
          updated_at?: string
          userinfo_url?: string | null
        }
        Update: {
          acceptable_client_ids?: string[]
          attribute_mapping?: Json
          authorization_params?: Json
          authorization_url?: string | null
          cached_discovery?: Json | null
          client_id?: string
          client_secret?: string
          created_at?: string
          custom_claims_allowlist?: string[]
          discovery_cached_at?: string | null
          discovery_url?: string | null
          email_optional?: boolean
          enabled?: boolean
          id?: string
          identifier?: string
          issuer?: string | null
          jwks_uri?: string | null
          name?: string
          pkce_enabled?: boolean
          provider_type?: string
          scopes?: string[]
          skip_nonce_check?: boolean
          token_url?: string | null
          updated_at?: string
          userinfo_url?: string | null
        }
        Relationships: []
      }
      flow_state: {
        Row: {
          auth_code: string | null
          auth_code_issued_at: string | null
          authentication_method: string
          code_challenge: string | null
          code_challenge_method:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null
          created_at: string | null
          email_optional: boolean
          id: string
          invite_token: string | null
          linking_target_id: string | null
          oauth_client_state_id: string | null
          provider_access_token: string | null
          provider_refresh_token: string | null
          provider_type: string
          referrer: string | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          auth_code?: string | null
          auth_code_issued_at?: string | null
          authentication_method: string
          code_challenge?: string | null
          code_challenge_method?:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null
          created_at?: string | null
          email_optional?: boolean
          id: string
          invite_token?: string | null
          linking_target_id?: string | null
          oauth_client_state_id?: string | null
          provider_access_token?: string | null
          provider_refresh_token?: string | null
          provider_type: string
          referrer?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          auth_code?: string | null
          auth_code_issued_at?: string | null
          authentication_method?: string
          code_challenge?: string | null
          code_challenge_method?:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null
          created_at?: string | null
          email_optional?: boolean
          id?: string
          invite_token?: string | null
          linking_target_id?: string | null
          oauth_client_state_id?: string | null
          provider_access_token?: string | null
          provider_refresh_token?: string | null
          provider_type?: string
          referrer?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      identities: {
        Row: {
          created_at: string | null
          email: string | null
          id: string
          identity_data: Json
          last_sign_in_at: string | null
          provider: string
          provider_id: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          created_at?: string | null
          email?: string | null
          id?: string
          identity_data: Json
          last_sign_in_at?: string | null
          provider: string
          provider_id: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          created_at?: string | null
          email?: string | null
          id?: string
          identity_data?: Json
          last_sign_in_at?: string | null
          provider?: string
          provider_id?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "identities_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      instances: {
        Row: {
          created_at: string | null
          id: string
          raw_base_config: string | null
          updated_at: string | null
          uuid: string | null
        }
        Insert: {
          created_at?: string | null
          id: string
          raw_base_config?: string | null
          updated_at?: string | null
          uuid?: string | null
        }
        Update: {
          created_at?: string | null
          id?: string
          raw_base_config?: string | null
          updated_at?: string | null
          uuid?: string | null
        }
        Relationships: []
      }
      mfa_amr_claims: {
        Row: {
          authentication_method: string
          created_at: string
          id: string
          session_id: string
          updated_at: string
        }
        Insert: {
          authentication_method: string
          created_at: string
          id: string
          session_id: string
          updated_at: string
        }
        Update: {
          authentication_method?: string
          created_at?: string
          id?: string
          session_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "mfa_amr_claims_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      mfa_challenges: {
        Row: {
          created_at: string
          factor_id: string
          id: string
          ip_address: unknown
          otp_code: string | null
          verified_at: string | null
          web_authn_session_data: Json | null
        }
        Insert: {
          created_at: string
          factor_id: string
          id: string
          ip_address: unknown
          otp_code?: string | null
          verified_at?: string | null
          web_authn_session_data?: Json | null
        }
        Update: {
          created_at?: string
          factor_id?: string
          id?: string
          ip_address?: unknown
          otp_code?: string | null
          verified_at?: string | null
          web_authn_session_data?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "mfa_challenges_auth_factor_id_fkey"
            columns: ["factor_id"]
            isOneToOne: false
            referencedRelation: "mfa_factors"
            referencedColumns: ["id"]
          },
        ]
      }
      mfa_factors: {
        Row: {
          created_at: string
          factor_type: Database["auth"]["Enums"]["factor_type"]
          friendly_name: string | null
          id: string
          last_challenged_at: string | null
          last_webauthn_challenge_data: Json | null
          phone: string | null
          secret: string | null
          status: Database["auth"]["Enums"]["factor_status"]
          updated_at: string
          user_id: string
          web_authn_aaguid: string | null
          web_authn_credential: Json | null
        }
        Insert: {
          created_at: string
          factor_type: Database["auth"]["Enums"]["factor_type"]
          friendly_name?: string | null
          id: string
          last_challenged_at?: string | null
          last_webauthn_challenge_data?: Json | null
          phone?: string | null
          secret?: string | null
          status: Database["auth"]["Enums"]["factor_status"]
          updated_at: string
          user_id: string
          web_authn_aaguid?: string | null
          web_authn_credential?: Json | null
        }
        Update: {
          created_at?: string
          factor_type?: Database["auth"]["Enums"]["factor_type"]
          friendly_name?: string | null
          id?: string
          last_challenged_at?: string | null
          last_webauthn_challenge_data?: Json | null
          phone?: string | null
          secret?: string | null
          status?: Database["auth"]["Enums"]["factor_status"]
          updated_at?: string
          user_id?: string
          web_authn_aaguid?: string | null
          web_authn_credential?: Json | null
        }
        Relationships: [
          {
            foreignKeyName: "mfa_factors_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      oauth_authorizations: {
        Row: {
          approved_at: string | null
          authorization_code: string | null
          authorization_id: string
          client_id: string
          code_challenge: string | null
          code_challenge_method:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null
          created_at: string
          expires_at: string
          id: string
          nonce: string | null
          redirect_uri: string
          resource: string | null
          response_type: Database["auth"]["Enums"]["oauth_response_type"]
          scope: string
          state: string | null
          status: Database["auth"]["Enums"]["oauth_authorization_status"]
          user_id: string | null
        }
        Insert: {
          approved_at?: string | null
          authorization_code?: string | null
          authorization_id: string
          client_id: string
          code_challenge?: string | null
          code_challenge_method?:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null
          created_at?: string
          expires_at?: string
          id: string
          nonce?: string | null
          redirect_uri: string
          resource?: string | null
          response_type?: Database["auth"]["Enums"]["oauth_response_type"]
          scope: string
          state?: string | null
          status?: Database["auth"]["Enums"]["oauth_authorization_status"]
          user_id?: string | null
        }
        Update: {
          approved_at?: string | null
          authorization_code?: string | null
          authorization_id?: string
          client_id?: string
          code_challenge?: string | null
          code_challenge_method?:
            | Database["auth"]["Enums"]["code_challenge_method"]
            | null
          created_at?: string
          expires_at?: string
          id?: string
          nonce?: string | null
          redirect_uri?: string
          resource?: string | null
          response_type?: Database["auth"]["Enums"]["oauth_response_type"]
          scope?: string
          state?: string | null
          status?: Database["auth"]["Enums"]["oauth_authorization_status"]
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "oauth_authorizations_client_id_fkey"
            columns: ["client_id"]
            isOneToOne: false
            referencedRelation: "oauth_clients"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "oauth_authorizations_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      oauth_client_states: {
        Row: {
          code_verifier: string | null
          created_at: string
          id: string
          provider_type: string
        }
        Insert: {
          code_verifier?: string | null
          created_at: string
          id: string
          provider_type: string
        }
        Update: {
          code_verifier?: string | null
          created_at?: string
          id?: string
          provider_type?: string
        }
        Relationships: []
      }
      oauth_clients: {
        Row: {
          client_name: string | null
          client_secret_hash: string | null
          client_type: Database["auth"]["Enums"]["oauth_client_type"]
          client_uri: string | null
          created_at: string
          deleted_at: string | null
          grant_types: string
          id: string
          logo_uri: string | null
          redirect_uris: string
          registration_type: Database["auth"]["Enums"]["oauth_registration_type"]
          token_endpoint_auth_method: string
          updated_at: string
        }
        Insert: {
          client_name?: string | null
          client_secret_hash?: string | null
          client_type?: Database["auth"]["Enums"]["oauth_client_type"]
          client_uri?: string | null
          created_at?: string
          deleted_at?: string | null
          grant_types: string
          id: string
          logo_uri?: string | null
          redirect_uris: string
          registration_type: Database["auth"]["Enums"]["oauth_registration_type"]
          token_endpoint_auth_method: string
          updated_at?: string
        }
        Update: {
          client_name?: string | null
          client_secret_hash?: string | null
          client_type?: Database["auth"]["Enums"]["oauth_client_type"]
          client_uri?: string | null
          created_at?: string
          deleted_at?: string | null
          grant_types?: string
          id?: string
          logo_uri?: string | null
          redirect_uris?: string
          registration_type?: Database["auth"]["Enums"]["oauth_registration_type"]
          token_endpoint_auth_method?: string
          updated_at?: string
        }
        Relationships: []
      }
      oauth_consents: {
        Row: {
          client_id: string
          granted_at: string
          id: string
          revoked_at: string | null
          scopes: string
          user_id: string
        }
        Insert: {
          client_id: string
          granted_at?: string
          id: string
          revoked_at?: string | null
          scopes: string
          user_id: string
        }
        Update: {
          client_id?: string
          granted_at?: string
          id?: string
          revoked_at?: string | null
          scopes?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "oauth_consents_client_id_fkey"
            columns: ["client_id"]
            isOneToOne: false
            referencedRelation: "oauth_clients"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "oauth_consents_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      one_time_tokens: {
        Row: {
          created_at: string
          id: string
          relates_to: string
          token_hash: string
          token_type: Database["auth"]["Enums"]["one_time_token_type"]
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          id: string
          relates_to: string
          token_hash: string
          token_type: Database["auth"]["Enums"]["one_time_token_type"]
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          relates_to?: string
          token_hash?: string
          token_type?: Database["auth"]["Enums"]["one_time_token_type"]
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "one_time_tokens_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      refresh_tokens: {
        Row: {
          created_at: string | null
          id: number
          instance_id: string | null
          parent: string | null
          revoked: boolean | null
          session_id: string | null
          token: string | null
          updated_at: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string | null
          id?: number
          instance_id?: string | null
          parent?: string | null
          revoked?: boolean | null
          session_id?: string | null
          token?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string | null
          id?: number
          instance_id?: string | null
          parent?: string | null
          revoked?: boolean | null
          session_id?: string | null
          token?: string | null
          updated_at?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "refresh_tokens_session_id_fkey"
            columns: ["session_id"]
            isOneToOne: false
            referencedRelation: "sessions"
            referencedColumns: ["id"]
          },
        ]
      }
      saml_providers: {
        Row: {
          attribute_mapping: Json | null
          created_at: string | null
          entity_id: string
          id: string
          metadata_url: string | null
          metadata_xml: string
          name_id_format: string | null
          sso_provider_id: string
          updated_at: string | null
        }
        Insert: {
          attribute_mapping?: Json | null
          created_at?: string | null
          entity_id: string
          id: string
          metadata_url?: string | null
          metadata_xml: string
          name_id_format?: string | null
          sso_provider_id: string
          updated_at?: string | null
        }
        Update: {
          attribute_mapping?: Json | null
          created_at?: string | null
          entity_id?: string
          id?: string
          metadata_url?: string | null
          metadata_xml?: string
          name_id_format?: string | null
          sso_provider_id?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "saml_providers_sso_provider_id_fkey"
            columns: ["sso_provider_id"]
            isOneToOne: false
            referencedRelation: "sso_providers"
            referencedColumns: ["id"]
          },
        ]
      }
      saml_relay_states: {
        Row: {
          created_at: string | null
          flow_state_id: string | null
          for_email: string | null
          id: string
          redirect_to: string | null
          request_id: string
          sso_provider_id: string
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          flow_state_id?: string | null
          for_email?: string | null
          id: string
          redirect_to?: string | null
          request_id: string
          sso_provider_id: string
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          flow_state_id?: string | null
          for_email?: string | null
          id?: string
          redirect_to?: string | null
          request_id?: string
          sso_provider_id?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "saml_relay_states_flow_state_id_fkey"
            columns: ["flow_state_id"]
            isOneToOne: false
            referencedRelation: "flow_state"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "saml_relay_states_sso_provider_id_fkey"
            columns: ["sso_provider_id"]
            isOneToOne: false
            referencedRelation: "sso_providers"
            referencedColumns: ["id"]
          },
        ]
      }
      schema_migrations: {
        Row: {
          version: string
        }
        Insert: {
          version: string
        }
        Update: {
          version?: string
        }
        Relationships: []
      }
      sessions: {
        Row: {
          aal: Database["auth"]["Enums"]["aal_level"] | null
          created_at: string | null
          factor_id: string | null
          id: string
          ip: unknown
          not_after: string | null
          oauth_client_id: string | null
          refresh_token_counter: number | null
          refresh_token_hmac_key: string | null
          refreshed_at: string | null
          scopes: string | null
          tag: string | null
          updated_at: string | null
          user_agent: string | null
          user_id: string
        }
        Insert: {
          aal?: Database["auth"]["Enums"]["aal_level"] | null
          created_at?: string | null
          factor_id?: string | null
          id: string
          ip?: unknown
          not_after?: string | null
          oauth_client_id?: string | null
          refresh_token_counter?: number | null
          refresh_token_hmac_key?: string | null
          refreshed_at?: string | null
          scopes?: string | null
          tag?: string | null
          updated_at?: string | null
          user_agent?: string | null
          user_id: string
        }
        Update: {
          aal?: Database["auth"]["Enums"]["aal_level"] | null
          created_at?: string | null
          factor_id?: string | null
          id?: string
          ip?: unknown
          not_after?: string | null
          oauth_client_id?: string | null
          refresh_token_counter?: number | null
          refresh_token_hmac_key?: string | null
          refreshed_at?: string | null
          scopes?: string | null
          tag?: string | null
          updated_at?: string | null
          user_agent?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "sessions_oauth_client_id_fkey"
            columns: ["oauth_client_id"]
            isOneToOne: false
            referencedRelation: "oauth_clients"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sessions_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      sso_domains: {
        Row: {
          created_at: string | null
          domain: string
          id: string
          sso_provider_id: string
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          domain: string
          id: string
          sso_provider_id: string
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          domain?: string
          id?: string
          sso_provider_id?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "sso_domains_sso_provider_id_fkey"
            columns: ["sso_provider_id"]
            isOneToOne: false
            referencedRelation: "sso_providers"
            referencedColumns: ["id"]
          },
        ]
      }
      sso_providers: {
        Row: {
          created_at: string | null
          disabled: boolean | null
          id: string
          resource_id: string | null
          updated_at: string | null
        }
        Insert: {
          created_at?: string | null
          disabled?: boolean | null
          id: string
          resource_id?: string | null
          updated_at?: string | null
        }
        Update: {
          created_at?: string | null
          disabled?: boolean | null
          id?: string
          resource_id?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      users: {
        Row: {
          aud: string | null
          banned_until: string | null
          confirmation_sent_at: string | null
          confirmation_token: string | null
          confirmed_at: string | null
          created_at: string | null
          deleted_at: string | null
          email: string | null
          email_change: string | null
          email_change_confirm_status: number | null
          email_change_sent_at: string | null
          email_change_token_current: string | null
          email_change_token_new: string | null
          email_confirmed_at: string | null
          encrypted_password: string | null
          id: string
          instance_id: string | null
          invited_at: string | null
          is_anonymous: boolean
          is_sso_user: boolean
          is_super_admin: boolean | null
          last_sign_in_at: string | null
          phone: string | null
          phone_change: string | null
          phone_change_sent_at: string | null
          phone_change_token: string | null
          phone_confirmed_at: string | null
          raw_app_meta_data: Json | null
          raw_user_meta_data: Json | null
          reauthentication_sent_at: string | null
          reauthentication_token: string | null
          recovery_sent_at: string | null
          recovery_token: string | null
          role: string | null
          updated_at: string | null
        }
        Insert: {
          aud?: string | null
          banned_until?: string | null
          confirmation_sent_at?: string | null
          confirmation_token?: string | null
          confirmed_at?: string | null
          created_at?: string | null
          deleted_at?: string | null
          email?: string | null
          email_change?: string | null
          email_change_confirm_status?: number | null
          email_change_sent_at?: string | null
          email_change_token_current?: string | null
          email_change_token_new?: string | null
          email_confirmed_at?: string | null
          encrypted_password?: string | null
          id: string
          instance_id?: string | null
          invited_at?: string | null
          is_anonymous?: boolean
          is_sso_user?: boolean
          is_super_admin?: boolean | null
          last_sign_in_at?: string | null
          phone?: string | null
          phone_change?: string | null
          phone_change_sent_at?: string | null
          phone_change_token?: string | null
          phone_confirmed_at?: string | null
          raw_app_meta_data?: Json | null
          raw_user_meta_data?: Json | null
          reauthentication_sent_at?: string | null
          reauthentication_token?: string | null
          recovery_sent_at?: string | null
          recovery_token?: string | null
          role?: string | null
          updated_at?: string | null
        }
        Update: {
          aud?: string | null
          banned_until?: string | null
          confirmation_sent_at?: string | null
          confirmation_token?: string | null
          confirmed_at?: string | null
          created_at?: string | null
          deleted_at?: string | null
          email?: string | null
          email_change?: string | null
          email_change_confirm_status?: number | null
          email_change_sent_at?: string | null
          email_change_token_current?: string | null
          email_change_token_new?: string | null
          email_confirmed_at?: string | null
          encrypted_password?: string | null
          id?: string
          instance_id?: string | null
          invited_at?: string | null
          is_anonymous?: boolean
          is_sso_user?: boolean
          is_super_admin?: boolean | null
          last_sign_in_at?: string | null
          phone?: string | null
          phone_change?: string | null
          phone_change_sent_at?: string | null
          phone_change_token?: string | null
          phone_confirmed_at?: string | null
          raw_app_meta_data?: Json | null
          raw_user_meta_data?: Json | null
          reauthentication_sent_at?: string | null
          reauthentication_token?: string | null
          recovery_sent_at?: string | null
          recovery_token?: string | null
          role?: string | null
          updated_at?: string | null
        }
        Relationships: []
      }
      webauthn_challenges: {
        Row: {
          challenge_type: string
          created_at: string
          expires_at: string
          id: string
          session_data: Json
          user_id: string | null
        }
        Insert: {
          challenge_type: string
          created_at?: string
          expires_at: string
          id?: string
          session_data: Json
          user_id?: string | null
        }
        Update: {
          challenge_type?: string
          created_at?: string
          expires_at?: string
          id?: string
          session_data?: Json
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "webauthn_challenges_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      webauthn_credentials: {
        Row: {
          aaguid: string | null
          attestation_type: string
          backed_up: boolean
          backup_eligible: boolean
          created_at: string
          credential_id: string
          friendly_name: string
          id: string
          last_used_at: string | null
          public_key: string
          sign_count: number
          transports: Json
          updated_at: string
          user_id: string
        }
        Insert: {
          aaguid?: string | null
          attestation_type?: string
          backed_up?: boolean
          backup_eligible?: boolean
          created_at?: string
          credential_id: string
          friendly_name?: string
          id?: string
          last_used_at?: string | null
          public_key: string
          sign_count?: number
          transports?: Json
          updated_at?: string
          user_id: string
        }
        Update: {
          aaguid?: string | null
          attestation_type?: string
          backed_up?: boolean
          backup_eligible?: boolean
          created_at?: string
          credential_id?: string
          friendly_name?: string
          id?: string
          last_used_at?: string | null
          public_key?: string
          sign_count?: number
          transports?: Json
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "webauthn_credentials_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      email: { Args: never; Returns: string }
      jwt: { Args: never; Returns: Json }
      role: { Args: never; Returns: string }
      uid: { Args: never; Returns: string }
    }
    Enums: {
      aal_level: "aal1" | "aal2" | "aal3"
      code_challenge_method: "s256" | "plain"
      factor_status: "unverified" | "verified"
      factor_type: "totp" | "webauthn" | "phone"
      oauth_authorization_status: "pending" | "approved" | "denied" | "expired"
      oauth_client_type: "public" | "confidential"
      oauth_registration_type: "dynamic" | "manual"
      oauth_response_type: "code"
      one_time_token_type:
        | "confirmation_token"
        | "reauthentication_token"
        | "recovery_token"
        | "email_change_token_new"
        | "email_change_token_current"
        | "phone_change_token"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  public: {
    Tables: {
      app_cotizaciones: {
        Row: {
          created_at: string
          current_step: string | null
          flow_version: string
          id: string
          modulo: string
          payload_json: Json
          resumen_json: Json
          status: string
          subtipo: string | null
          total: number
          updated_at: string
          user_email: string
          user_id: string | null
        }
        Insert: {
          created_at?: string
          current_step?: string | null
          flow_version?: string
          id?: string
          modulo?: string
          payload_json?: Json
          resumen_json?: Json
          status?: string
          subtipo?: string | null
          total?: number
          updated_at?: string
          user_email: string
          user_id?: string | null
        }
        Update: {
          created_at?: string
          current_step?: string | null
          flow_version?: string
          id?: string
          modulo?: string
          payload_json?: Json
          resumen_json?: Json
          status?: string
          subtipo?: string | null
          total?: number
          updated_at?: string
          user_email?: string
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "app_cotizaciones_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "app_users"
            referencedColumns: ["id"]
          },
        ]
      }
      app_users: {
        Row: {
          alias: string | null
          created_at: string
          direccion: string | null
          email: string
          id: string
          is_active: boolean
          nombre: string
          password_hash: string
          perfil: string
          profesion: string | null
          telefono: string | null
          updated_at: string
        }
        Insert: {
          alias?: string | null
          created_at?: string
          direccion?: string | null
          email: string
          id?: string
          is_active?: boolean
          nombre: string
          password_hash?: string
          perfil?: string
          profesion?: string | null
          telefono?: string | null
          updated_at?: string
        }
        Update: {
          alias?: string | null
          created_at?: string
          direccion?: string | null
          email?: string
          id?: string
          is_active?: boolean
          nombre?: string
          password_hash?: string
          perfil?: string
          profesion?: string | null
          telefono?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      catalog_categories: {
        Row: {
          code: string
          created_at: string
          description: string | null
          id: string
          is_active: boolean
          module_id: string
          name: string
          sort_order: number
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          module_id: string
          name: string
          sort_order?: number
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          module_id?: string
          name?: string
          sort_order?: number
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_categories_module_id_fkey"
            columns: ["module_id"]
            isOneToOne: false
            referencedRelation: "catalog_modules"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_concept_aliases: {
        Row: {
          alias: string
          alias_type: string
          concept_id: string
          created_at: string
          id: string
        }
        Insert: {
          alias: string
          alias_type?: string
          concept_id: string
          created_at?: string
          id?: string
        }
        Update: {
          alias?: string
          alias_type?: string
          concept_id?: string
          created_at?: string
          id?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_concept_aliases_concept_id_fkey"
            columns: ["concept_id"]
            isOneToOne: false
            referencedRelation: "catalog_concepts"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_concept_documents: {
        Row: {
          concept_id: string
          created_at: string
          document_type: string
          file_url: string | null
          id: string
          notes: string | null
          title: string
        }
        Insert: {
          concept_id: string
          created_at?: string
          document_type: string
          file_url?: string | null
          id?: string
          notes?: string | null
          title: string
        }
        Update: {
          concept_id?: string
          created_at?: string
          document_type?: string
          file_url?: string | null
          id?: string
          notes?: string | null
          title?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_concept_documents_concept_id_fkey"
            columns: ["concept_id"]
            isOneToOne: false
            referencedRelation: "catalog_concepts"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_concept_space_types: {
        Row: {
          applicability_mode: string
          concept_id: string
          created_at: string
          id: string
          space_type_id: string
        }
        Insert: {
          applicability_mode?: string
          concept_id: string
          created_at?: string
          id?: string
          space_type_id: string
        }
        Update: {
          applicability_mode?: string
          concept_id?: string
          created_at?: string
          id?: string
          space_type_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_concept_space_types_concept_id_fkey"
            columns: ["concept_id"]
            isOneToOne: false
            referencedRelation: "catalog_concepts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "catalog_concept_space_types_space_type_id_fkey"
            columns: ["space_type_id"]
            isOneToOne: false
            referencedRelation: "catalog_space_types"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_concept_specifications: {
        Row: {
          concept_id: string
          created_at: string
          id: string
          is_active: boolean
          jurisdiction: string
          mode: string
          normative_basis_json: Json
          official_specification: string | null
          output_template_json: Json
          technical_specification: string | null
          updated_at: string
          validation_rules_json: Json
          version: string | null
          volumetry_rules_json: Json
        }
        Insert: {
          concept_id: string
          created_at?: string
          id?: string
          is_active?: boolean
          jurisdiction: string
          mode?: string
          normative_basis_json?: Json
          official_specification?: string | null
          output_template_json?: Json
          technical_specification?: string | null
          updated_at?: string
          validation_rules_json?: Json
          version?: string | null
          volumetry_rules_json?: Json
        }
        Update: {
          concept_id?: string
          created_at?: string
          id?: string
          is_active?: boolean
          jurisdiction?: string
          mode?: string
          normative_basis_json?: Json
          official_specification?: string | null
          output_template_json?: Json
          technical_specification?: string | null
          updated_at?: string
          validation_rules_json?: Json
          version?: string | null
          volumetry_rules_json?: Json
        }
        Relationships: [
          {
            foreignKeyName: "catalog_concept_specifications_concept_id_fkey"
            columns: ["concept_id"]
            isOneToOne: false
            referencedRelation: "catalog_concepts"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_concept_systems: {
        Row: {
          applicability_mode: string
          concept_id: string
          construction_system_id: string
          created_at: string
          id: string
        }
        Insert: {
          applicability_mode?: string
          concept_id: string
          construction_system_id: string
          created_at?: string
          id?: string
        }
        Update: {
          applicability_mode?: string
          concept_id?: string
          construction_system_id?: string
          created_at?: string
          id?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_concept_systems_concept_id_fkey"
            columns: ["concept_id"]
            isOneToOne: false
            referencedRelation: "catalog_concepts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "catalog_concept_systems_construction_system_id_fkey"
            columns: ["construction_system_id"]
            isOneToOne: false
            referencedRelation: "catalog_construction_systems"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_concepts: {
        Row: {
          applies_private_housing: boolean
          code: string
          created_at: string
          default_formula_code: string | null
          finish_level: string | null
          id: string
          is_active: boolean
          is_optional: boolean
          metadata_json: Json
          notes: string | null
          official_description: string | null
          partida_id: string | null
          quantification_mode: string
          requires_normative_validation: boolean
          requires_space_context: boolean
          requires_system_context: boolean
          subalcance_id: string | null
          technical_description: string | null
          unit_id: string | null
          updated_at: string
        }
        Insert: {
          applies_private_housing?: boolean
          code: string
          created_at?: string
          default_formula_code?: string | null
          finish_level?: string | null
          id?: string
          is_active?: boolean
          is_optional?: boolean
          metadata_json?: Json
          notes?: string | null
          official_description?: string | null
          partida_id?: string | null
          quantification_mode?: string
          requires_normative_validation?: boolean
          requires_space_context?: boolean
          requires_system_context?: boolean
          subalcance_id?: string | null
          technical_description?: string | null
          unit_id?: string | null
          updated_at?: string
        }
        Update: {
          applies_private_housing?: boolean
          code?: string
          created_at?: string
          default_formula_code?: string | null
          finish_level?: string | null
          id?: string
          is_active?: boolean
          is_optional?: boolean
          metadata_json?: Json
          notes?: string | null
          official_description?: string | null
          partida_id?: string | null
          quantification_mode?: string
          requires_normative_validation?: boolean
          requires_space_context?: boolean
          requires_system_context?: boolean
          subalcance_id?: string | null
          technical_description?: string | null
          unit_id?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_concepts_partida_id_fkey"
            columns: ["partida_id"]
            isOneToOne: false
            referencedRelation: "catalog_partidas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "catalog_concepts_unit_id_fkey"
            columns: ["unit_id"]
            isOneToOne: false
            referencedRelation: "catalog_units"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_construction_systems: {
        Row: {
          code: string
          compatibility_json: Json
          created_at: string
          description: string | null
          id: string
          is_active: boolean
          name: string
          needs_engineering_validation: boolean
          partida_id: string | null
          system_group: string
          updated_at: string
          volumetry_json: Json
        }
        Insert: {
          code: string
          compatibility_json?: Json
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name: string
          needs_engineering_validation?: boolean
          partida_id?: string | null
          system_group: string
          updated_at?: string
          volumetry_json?: Json
        }
        Update: {
          code?: string
          compatibility_json?: Json
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name?: string
          needs_engineering_validation?: boolean
          partida_id?: string | null
          system_group?: string
          updated_at?: string
          volumetry_json?: Json
        }
        Relationships: [
          {
            foreignKeyName: "catalog_construction_systems_partida_id_fkey"
            columns: ["partida_id"]
            isOneToOne: false
            referencedRelation: "catalog_partidas"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_jurisdictions: {
        Row: {
          code: string
          created_at: string
          id: string
          is_active: boolean
          jurisdiction_type: string
          municipality_name: string | null
          name: string
          state_code: string | null
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          id?: string
          is_active?: boolean
          jurisdiction_type: string
          municipality_name?: string | null
          name: string
          state_code?: string | null
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          id?: string
          is_active?: boolean
          jurisdiction_type?: string
          municipality_name?: string | null
          name?: string
          state_code?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      catalog_modules: {
        Row: {
          code: string
          created_at: string
          description: string | null
          id: string
          is_active: boolean
          name: string
          sort_order: number
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name: string
          sort_order?: number
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name?: string
          sort_order?: number
          updated_at?: string
        }
        Relationships: []
      }
      catalog_normative_sources: {
        Row: {
          code: string
          created_at: string
          effective_date: string | null
          id: string
          is_active: boolean
          jurisdiction_id: string | null
          notes: string | null
          publication_date: string | null
          short_name: string | null
          source_type: string
          source_url: string | null
          title: string
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          effective_date?: string | null
          id?: string
          is_active?: boolean
          jurisdiction_id?: string | null
          notes?: string | null
          publication_date?: string | null
          short_name?: string | null
          source_type: string
          source_url?: string | null
          title: string
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          effective_date?: string | null
          id?: string
          is_active?: boolean
          jurisdiction_id?: string | null
          notes?: string | null
          publication_date?: string | null
          short_name?: string | null
          source_type?: string
          source_url?: string | null
          title?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_normative_sources_jurisdiction_id_fkey"
            columns: ["jurisdiction_id"]
            isOneToOne: false
            referencedRelation: "catalog_jurisdictions"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_partidas: {
        Row: {
          code: string
          created_at: string
          description: string | null
          id: string
          is_active: boolean
          module_id: string
          name: string
          sort_order: number
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          module_id: string
          name: string
          sort_order?: number
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          module_id?: string
          name?: string
          sort_order?: number
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "catalog_partidas_module_id_fkey"
            columns: ["module_id"]
            isOneToOne: false
            referencedRelation: "catalog_modules"
            referencedColumns: ["id"]
          },
        ]
      }
      catalog_space_types: {
        Row: {
          code: string
          created_at: string
          description: string | null
          id: string
          is_active: boolean
          is_exterior: boolean
          is_habitable: boolean
          is_service: boolean
          name: string
          sort_order: number
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          is_exterior?: boolean
          is_habitable?: boolean
          is_service?: boolean
          name: string
          sort_order?: number
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          is_exterior?: boolean
          is_habitable?: boolean
          is_service?: boolean
          name?: string
          sort_order?: number
          updated_at?: string
        }
        Relationships: []
      }
      catalog_system_types: {
        Row: {
          code: string
          created_at: string
          description: string | null
          id: string
          is_active: boolean
          name: string
          system_group: string
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name: string
          system_group: string
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name?: string
          system_group?: string
          updated_at?: string
        }
        Relationships: []
      }
      catalog_units: {
        Row: {
          code: string
          created_at: string
          description: string | null
          id: string
          is_active: boolean
          name: string
          symbol: string | null
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name: string
          symbol?: string | null
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          id?: string
          is_active?: boolean
          name?: string
          symbol?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      document_chunks: {
        Row: {
          chunk_id: string
          chunk_index: number
          content: string
          created_at: string
          document_id: string
          embedding: string
          metadata: Json
        }
        Insert: {
          chunk_id: string
          chunk_index: number
          content: string
          created_at?: string
          document_id: string
          embedding: string
          metadata?: Json
        }
        Update: {
          chunk_id?: string
          chunk_index?: number
          content?: string
          created_at?: string
          document_id?: string
          embedding?: string
          metadata?: Json
        }
        Relationships: [
          {
            foreignKeyName: "document_chunks_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      documents: {
        Row: {
          chunk_count: number
          created_at: string
          embedding_model: string | null
          error_detail: string | null
          file_checksum: string
          id: string
          mime_type: string
          module_key: string | null
          ocr_metadata: Json
          ocr_text: string
          original_file_name: string
          processing_version: string
          quote_id: string | null
          size_bytes: number
          status: string
          storage_bucket: string
          storage_object_path: string
          updated_at: string
          user_id: string
        }
        Insert: {
          chunk_count?: number
          created_at?: string
          embedding_model?: string | null
          error_detail?: string | null
          file_checksum: string
          id: string
          mime_type: string
          module_key?: string | null
          ocr_metadata?: Json
          ocr_text?: string
          original_file_name: string
          processing_version?: string
          quote_id?: string | null
          size_bytes: number
          status?: string
          storage_bucket?: string
          storage_object_path: string
          updated_at?: string
          user_id: string
        }
        Update: {
          chunk_count?: number
          created_at?: string
          embedding_model?: string | null
          error_detail?: string | null
          file_checksum?: string
          id?: string
          mime_type?: string
          module_key?: string | null
          ocr_metadata?: Json
          ocr_text?: string
          original_file_name?: string
          processing_version?: string
          quote_id?: string | null
          size_bytes?: number
          status?: string
          storage_bucket?: string
          storage_object_path?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "documents_quote_id_fkey"
            columns: ["quote_id"]
            isOneToOne: false
            referencedRelation: "app_cotizaciones"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "documents_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "app_users"
            referencedColumns: ["id"]
          },
        ]
      }
      engine_activation_rules: {
        Row: {
          activation_type: string
          alerts_json: Json
          applies_from_level: number | null
          applies_to_level: number | null
          code: string
          concept_spec_id: string
          condition_json: Json
          created_at: string
          derivation_json: Json
          id: string
          invalidates_json: Json
          is_active: boolean
          output_action_json: Json
          priority: number
          rule_name: string
          scope: string | null
          stop_on_error: boolean
          trigger_json: Json
          type_intervention: string | null
          updated_at: string
        }
        Insert: {
          activation_type: string
          alerts_json?: Json
          applies_from_level?: number | null
          applies_to_level?: number | null
          code: string
          concept_spec_id: string
          condition_json?: Json
          created_at?: string
          derivation_json?: Json
          id?: string
          invalidates_json?: Json
          is_active?: boolean
          output_action_json?: Json
          priority?: number
          rule_name: string
          scope?: string | null
          stop_on_error?: boolean
          trigger_json?: Json
          type_intervention?: string | null
          updated_at?: string
        }
        Update: {
          activation_type?: string
          alerts_json?: Json
          applies_from_level?: number | null
          applies_to_level?: number | null
          code?: string
          concept_spec_id?: string
          condition_json?: Json
          created_at?: string
          derivation_json?: Json
          id?: string
          invalidates_json?: Json
          is_active?: boolean
          output_action_json?: Json
          priority?: number
          rule_name?: string
          scope?: string | null
          stop_on_error?: boolean
          trigger_json?: Json
          type_intervention?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "engine_activation_rules_concept_spec_id_fkey"
            columns: ["concept_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_concept_specs"
            referencedColumns: ["id"]
          },
        ]
      }
      engine_concept_spec_sources: {
        Row: {
          clause_reference: string | null
          concept_spec_id: string
          created_at: string
          id: string
          notes: string | null
          source_id: string
          source_role: string
        }
        Insert: {
          clause_reference?: string | null
          concept_spec_id: string
          created_at?: string
          id?: string
          notes?: string | null
          source_id: string
          source_role?: string
        }
        Update: {
          clause_reference?: string | null
          concept_spec_id?: string
          created_at?: string
          id?: string
          notes?: string | null
          source_id?: string
          source_role?: string
        }
        Relationships: [
          {
            foreignKeyName: "engine_concept_spec_sources_concept_spec_id_fkey"
            columns: ["concept_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_concept_specs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_spec_sources_source_id_fkey"
            columns: ["source_id"]
            isOneToOne: false
            referencedRelation: "catalog_normative_sources"
            referencedColumns: ["id"]
          },
        ]
      }
      engine_concept_spec_space_types: {
        Row: {
          applicability: string
          concept_spec_id: string
          created_at: string
          id: string
          space_type_id: string
        }
        Insert: {
          applicability?: string
          concept_spec_id: string
          created_at?: string
          id?: string
          space_type_id: string
        }
        Update: {
          applicability?: string
          concept_spec_id?: string
          created_at?: string
          id?: string
          space_type_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "engine_concept_spec_space_types_concept_spec_id_fkey"
            columns: ["concept_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_concept_specs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_spec_space_types_space_type_id_fkey"
            columns: ["space_type_id"]
            isOneToOne: false
            referencedRelation: "catalog_space_types"
            referencedColumns: ["id"]
          },
        ]
      }
      engine_concept_spec_systems: {
        Row: {
          applicability: string
          concept_spec_id: string
          created_at: string
          id: string
          system_type_id: string
        }
        Insert: {
          applicability?: string
          concept_spec_id: string
          created_at?: string
          id?: string
          system_type_id: string
        }
        Update: {
          applicability?: string
          concept_spec_id?: string
          created_at?: string
          id?: string
          system_type_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "engine_concept_spec_systems_concept_spec_id_fkey"
            columns: ["concept_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_concept_specs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_spec_systems_system_type_id_fkey"
            columns: ["system_type_id"]
            isOneToOne: false
            referencedRelation: "catalog_system_types"
            referencedColumns: ["id"]
          },
        ]
      }
      engine_concept_specs: {
        Row: {
          allows_user_override: boolean
          application_mode: string
          applies_first_level_only: boolean
          concept_id: string
          concrete_spec_id: string | null
          created_at: string
          default_quantity_mode: string
          dependencies_json: Json
          excludes_text: string | null
          exclusions_json: Json
          execution_priority: number | null
          formula_id: string | null
          formwork_spec_id: string | null
          id: string
          includes_text: string | null
          inference_strategy: string | null
          is_active: boolean
          metadata_json: Json
          normative_notes: string | null
          notes: string | null
          output_mode: string
          parameter_defaults: Json
          parameter_rules: Json
          quality_text: string | null
          quantity_multiplier: number | null
          reinforcement_spec_id: string | null
          requires_project_definition: boolean
          section_type_id: string | null
          spec_code: string
          spec_name: string
          spec_profile_id: string
          technical_scope_text: string | null
          updated_at: string
          validations_json: Json
        }
        Insert: {
          allows_user_override?: boolean
          application_mode?: string
          applies_first_level_only?: boolean
          concept_id: string
          concrete_spec_id?: string | null
          created_at?: string
          default_quantity_mode: string
          dependencies_json?: Json
          excludes_text?: string | null
          exclusions_json?: Json
          execution_priority?: number | null
          formula_id?: string | null
          formwork_spec_id?: string | null
          id?: string
          includes_text?: string | null
          inference_strategy?: string | null
          is_active?: boolean
          metadata_json?: Json
          normative_notes?: string | null
          notes?: string | null
          output_mode?: string
          parameter_defaults?: Json
          parameter_rules?: Json
          quality_text?: string | null
          quantity_multiplier?: number | null
          reinforcement_spec_id?: string | null
          requires_project_definition?: boolean
          section_type_id?: string | null
          spec_code: string
          spec_name: string
          spec_profile_id: string
          technical_scope_text?: string | null
          updated_at?: string
          validations_json?: Json
        }
        Update: {
          allows_user_override?: boolean
          application_mode?: string
          applies_first_level_only?: boolean
          concept_id?: string
          concrete_spec_id?: string | null
          created_at?: string
          default_quantity_mode?: string
          dependencies_json?: Json
          excludes_text?: string | null
          exclusions_json?: Json
          execution_priority?: number | null
          formula_id?: string | null
          formwork_spec_id?: string | null
          id?: string
          includes_text?: string | null
          inference_strategy?: string | null
          is_active?: boolean
          metadata_json?: Json
          normative_notes?: string | null
          notes?: string | null
          output_mode?: string
          parameter_defaults?: Json
          parameter_rules?: Json
          quality_text?: string | null
          quantity_multiplier?: number | null
          reinforcement_spec_id?: string | null
          requires_project_definition?: boolean
          section_type_id?: string | null
          spec_code?: string
          spec_name?: string
          spec_profile_id?: string
          technical_scope_text?: string | null
          updated_at?: string
          validations_json?: Json
        }
        Relationships: [
          {
            foreignKeyName: "engine_concept_specs_concept_id_fkey"
            columns: ["concept_id"]
            isOneToOne: false
            referencedRelation: "catalog_concepts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_specs_concrete_spec_id_fkey"
            columns: ["concrete_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_material_specs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_specs_formula_id_fkey"
            columns: ["formula_id"]
            isOneToOne: false
            referencedRelation: "engine_formulas"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_specs_formwork_spec_id_fkey"
            columns: ["formwork_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_material_specs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_specs_reinforcement_spec_id_fkey"
            columns: ["reinforcement_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_reinforcement_specs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_specs_section_type_id_fkey"
            columns: ["section_type_id"]
            isOneToOne: false
            referencedRelation: "engine_section_types"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "engine_concept_specs_spec_profile_id_fkey"
            columns: ["spec_profile_id"]
            isOneToOne: false
            referencedRelation: "engine_spec_profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      engine_formulas: {
        Row: {
          code: string
          created_at: string
          description: string | null
          expression: string
          id: string
          name: string
          result_unit_symbol: string | null
          updated_at: string
          variables_schema: Json
        }
        Insert: {
          code: string
          created_at?: string
          description?: string | null
          expression: string
          id?: string
          name: string
          result_unit_symbol?: string | null
          updated_at?: string
          variables_schema?: Json
        }
        Update: {
          code?: string
          created_at?: string
          description?: string | null
          expression?: string
          id?: string
          name?: string
          result_unit_symbol?: string | null
          updated_at?: string
          variables_schema?: Json
        }
        Relationships: []
      }
      engine_material_specs: {
        Row: {
          code: string
          commercial_variant: string | null
          created_at: string
          description: string | null
          id: string
          material_group: string
          material_name: string
          quality_grade: string | null
          strength_unit: string | null
          strength_value: number | null
          updated_at: string
        }
        Insert: {
          code: string
          commercial_variant?: string | null
          created_at?: string
          description?: string | null
          id?: string
          material_group: string
          material_name: string
          quality_grade?: string | null
          strength_unit?: string | null
          strength_value?: number | null
          updated_at?: string
        }
        Update: {
          code?: string
          commercial_variant?: string | null
          created_at?: string
          description?: string | null
          id?: string
          material_group?: string
          material_name?: string
          quality_grade?: string | null
          strength_unit?: string | null
          strength_value?: number | null
          updated_at?: string
        }
        Relationships: []
      }
      engine_reinforcement_specs: {
        Row: {
          code: string
          commercial_name: string | null
          created_at: string
          description: string | null
          id: string
          longitudinal_bars: string | null
          reinforcement_type: string
          spacing_cm: number | null
          stirrups: string | null
          updated_at: string
        }
        Insert: {
          code: string
          commercial_name?: string | null
          created_at?: string
          description?: string | null
          id?: string
          longitudinal_bars?: string | null
          reinforcement_type: string
          spacing_cm?: number | null
          stirrups?: string | null
          updated_at?: string
        }
        Update: {
          code?: string
          commercial_name?: string | null
          created_at?: string
          description?: string | null
          id?: string
          longitudinal_bars?: string | null
          reinforcement_type?: string
          spacing_cm?: number | null
          stirrups?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      engine_section_types: {
        Row: {
          area_m2: number | null
          code: string
          created_at: string
          depth_m: number | null
          description: string | null
          diameter_mm: number | null
          height_m: number | null
          id: string
          is_active: boolean
          name: string
          section_group: string
          thickness_m: number | null
          updated_at: string
          volume_factor: number | null
          width_m: number | null
        }
        Insert: {
          area_m2?: number | null
          code: string
          created_at?: string
          depth_m?: number | null
          description?: string | null
          diameter_mm?: number | null
          height_m?: number | null
          id?: string
          is_active?: boolean
          name: string
          section_group: string
          thickness_m?: number | null
          updated_at?: string
          volume_factor?: number | null
          width_m?: number | null
        }
        Update: {
          area_m2?: number | null
          code?: string
          created_at?: string
          depth_m?: number | null
          description?: string | null
          diameter_mm?: number | null
          height_m?: number | null
          id?: string
          is_active?: boolean
          name?: string
          section_group?: string
          thickness_m?: number | null
          updated_at?: string
          volume_factor?: number | null
          width_m?: number | null
        }
        Relationships: []
      }
      engine_spec_profiles: {
        Row: {
          applies_first_level_only: boolean
          code: string
          created_at: string
          description: string | null
          geometry_kind: string
          id: string
          name: string
          profile_group: string
          unit_formula_symbol: string | null
          updated_at: string
        }
        Insert: {
          applies_first_level_only?: boolean
          code: string
          created_at?: string
          description?: string | null
          geometry_kind: string
          id?: string
          name: string
          profile_group: string
          unit_formula_symbol?: string | null
          updated_at?: string
        }
        Update: {
          applies_first_level_only?: boolean
          code?: string
          created_at?: string
          description?: string | null
          geometry_kind?: string
          id?: string
          name?: string
          profile_group?: string
          unit_formula_symbol?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      price_concept_bases: {
        Row: {
          concept_spec_id: string
          created_at: string
          id: string
          is_active: boolean
          notes: string | null
          region_id: string | null
          source_name: string | null
          unit_price: number | null
          updated_at: string
          valid_from: string | null
          valid_to: string | null
        }
        Insert: {
          concept_spec_id: string
          created_at?: string
          id?: string
          is_active?: boolean
          notes?: string | null
          region_id?: string | null
          source_name?: string | null
          unit_price?: number | null
          updated_at?: string
          valid_from?: string | null
          valid_to?: string | null
        }
        Update: {
          concept_spec_id?: string
          created_at?: string
          id?: string
          is_active?: boolean
          notes?: string | null
          region_id?: string | null
          source_name?: string | null
          unit_price?: number | null
          updated_at?: string
          valid_from?: string | null
          valid_to?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "price_concept_bases_concept_spec_id_fkey"
            columns: ["concept_spec_id"]
            isOneToOne: false
            referencedRelation: "engine_concept_specs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "price_concept_bases_region_id_fkey"
            columns: ["region_id"]
            isOneToOne: false
            referencedRelation: "price_regions"
            referencedColumns: ["id"]
          },
        ]
      }
      price_regions: {
        Row: {
          code: string
          created_at: string
          currency: string
          id: string
          is_active: boolean
          municipality_name: string | null
          name: string
          state_code: string | null
          updated_at: string
        }
        Insert: {
          code: string
          created_at?: string
          currency?: string
          id?: string
          is_active?: boolean
          municipality_name?: string | null
          name: string
          state_code?: string | null
          updated_at?: string
        }
        Update: {
          code?: string
          created_at?: string
          currency?: string
          id?: string
          is_active?: boolean
          municipality_name?: string | null
          name?: string
          state_code?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      profiles: {
        Row: {
          id: string
        }
        Insert: {
          id?: string
        }
        Update: {
          id?: string
        }
        Relationships: []
      }
      simulation_alerts: {
        Row: {
          alert_level: string
          created_at: string
          id: string
          message: string
          metadata_json: Json
          run_id: string | null
          simulation_id: string
          source_reference: string | null
          source_type: string
        }
        Insert: {
          alert_level: string
          created_at?: string
          id?: string
          message: string
          metadata_json?: Json
          run_id?: string | null
          simulation_id: string
          source_reference?: string | null
          source_type: string
        }
        Update: {
          alert_level?: string
          created_at?: string
          id?: string
          message?: string
          metadata_json?: Json
          run_id?: string | null
          simulation_id?: string
          source_reference?: string | null
          source_type?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulation_alerts_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: false
            referencedRelation: "simulation_inference_runs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_alerts_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_concept_dependencies: {
        Row: {
          created_at: string
          dependency_role: string
          depends_on_simulation_concept_id: string
          id: string
          simulation_concept_id: string
        }
        Insert: {
          created_at?: string
          dependency_role?: string
          depends_on_simulation_concept_id: string
          id?: string
          simulation_concept_id: string
        }
        Update: {
          created_at?: string
          dependency_role?: string
          depends_on_simulation_concept_id?: string
          id?: string
          simulation_concept_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulation_concept_dependenci_depends_on_simulation_concep_fkey"
            columns: ["depends_on_simulation_concept_id"]
            isOneToOne: false
            referencedRelation: "simulation_concepts"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_concept_dependencies_simulation_concept_id_fkey"
            columns: ["simulation_concept_id"]
            isOneToOne: false
            referencedRelation: "simulation_concepts"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_concepts: {
        Row: {
          id: string
        }
        Insert: {
          id?: string
        }
        Update: {
          id?: string
        }
        Relationships: []
      }
      simulation_inference_runs: {
        Row: {
          created_at: string
          id: string
          notes: string | null
          rule_snapshot: Json
          run_status: string
          simulation_id: string
          triggered_by: string | null
        }
        Insert: {
          created_at?: string
          id?: string
          notes?: string | null
          rule_snapshot?: Json
          run_status?: string
          simulation_id: string
          triggered_by?: string | null
        }
        Update: {
          created_at?: string
          id?: string
          notes?: string | null
          rule_snapshot?: Json
          run_status?: string
          simulation_id?: string
          triggered_by?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "simulation_inference_runs_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_inference_runs_triggered_by_fkey"
            columns: ["triggered_by"]
            isOneToOne: false
            referencedRelation: "profiles"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_levels: {
        Row: {
          clear_height_m: number | null
          created_at: string
          elevation_m: number | null
          id: string
          is_active: boolean
          is_roof: boolean
          level_number: number
          name: string
          simulation_id: string
          updated_at: string
        }
        Insert: {
          clear_height_m?: number | null
          created_at?: string
          elevation_m?: number | null
          id?: string
          is_active?: boolean
          is_roof?: boolean
          level_number: number
          name: string
          simulation_id: string
          updated_at?: string
        }
        Update: {
          clear_height_m?: number | null
          created_at?: string
          elevation_m?: number | null
          id?: string
          is_active?: boolean
          is_roof?: boolean
          level_number?: number
          name?: string
          simulation_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulation_levels_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_openings: {
        Row: {
          area_m2: number | null
          created_at: string
          face_id: string
          height_m: number
          id: string
          is_exterior: boolean
          opening_type: string
          quantity: number
          sill_height_m: number | null
          simulation_id: string
          updated_at: string
          width_m: number
        }
        Insert: {
          area_m2?: number | null
          created_at?: string
          face_id: string
          height_m: number
          id?: string
          is_exterior?: boolean
          opening_type: string
          quantity?: number
          sill_height_m?: number | null
          simulation_id: string
          updated_at?: string
          width_m: number
        }
        Update: {
          area_m2?: number | null
          created_at?: string
          face_id?: string
          height_m?: number
          id?: string
          is_exterior?: boolean
          opening_type?: string
          quantity?: number
          sill_height_m?: number | null
          simulation_id?: string
          updated_at?: string
          width_m?: number
        }
        Relationships: [
          {
            foreignKeyName: "simulation_openings_face_id_fkey"
            columns: ["face_id"]
            isOneToOne: false
            referencedRelation: "simulation_space_faces"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_openings_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_space_adjacencies: {
        Row: {
          adjacency_type: string
          adjacent_space_id: string | null
          created_at: string
          face_id: string
          id: string
          notes: string | null
          simulation_id: string
        }
        Insert: {
          adjacency_type: string
          adjacent_space_id?: string | null
          created_at?: string
          face_id: string
          id?: string
          notes?: string | null
          simulation_id: string
        }
        Update: {
          adjacency_type?: string
          adjacent_space_id?: string | null
          created_at?: string
          face_id?: string
          id?: string
          notes?: string | null
          simulation_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulation_space_adjacencies_adjacent_space_id_fkey"
            columns: ["adjacent_space_id"]
            isOneToOne: false
            referencedRelation: "simulation_spaces"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_space_adjacencies_face_id_fkey"
            columns: ["face_id"]
            isOneToOne: true
            referencedRelation: "simulation_space_faces"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_space_adjacencies_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_space_faces: {
        Row: {
          created_at: string
          face_code: string
          face_type: string
          gross_area_m2: number | null
          height_m: number | null
          id: string
          length_m: number | null
          net_area_m2: number | null
          orientation: string | null
          simulation_id: string
          space_id: string
          thickness_m: number | null
          updated_at: string
        }
        Insert: {
          created_at?: string
          face_code: string
          face_type?: string
          gross_area_m2?: number | null
          height_m?: number | null
          id?: string
          length_m?: number | null
          net_area_m2?: number | null
          orientation?: string | null
          simulation_id: string
          space_id: string
          thickness_m?: number | null
          updated_at?: string
        }
        Update: {
          created_at?: string
          face_code?: string
          face_type?: string
          gross_area_m2?: number | null
          height_m?: number | null
          id?: string
          length_m?: number | null
          net_area_m2?: number | null
          orientation?: string | null
          simulation_id?: string
          space_id?: string
          thickness_m?: number | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulation_space_faces_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_space_faces_space_id_fkey"
            columns: ["space_id"]
            isOneToOne: false
            referencedRelation: "simulation_spaces"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_space_openings: {
        Row: {
          created_at: string
          face_id: string | null
          height_m: number | null
          id: string
          is_existing: boolean
          metadata_json: Json
          opening_type: string
          quantity: number
          simulation_id: string
          space_id: string
          updated_at: string
          width_m: number | null
        }
        Insert: {
          created_at?: string
          face_id?: string | null
          height_m?: number | null
          id?: string
          is_existing?: boolean
          metadata_json?: Json
          opening_type: string
          quantity?: number
          simulation_id: string
          space_id: string
          updated_at?: string
          width_m?: number | null
        }
        Update: {
          created_at?: string
          face_id?: string | null
          height_m?: number | null
          id?: string
          is_existing?: boolean
          metadata_json?: Json
          opening_type?: string
          quantity?: number
          simulation_id?: string
          space_id?: string
          updated_at?: string
          width_m?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "simulation_space_openings_face_id_fkey"
            columns: ["face_id"]
            isOneToOne: false
            referencedRelation: "simulation_space_faces"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_space_openings_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_space_openings_space_id_fkey"
            columns: ["space_id"]
            isOneToOne: false
            referencedRelation: "simulation_spaces"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_space_services: {
        Row: {
          created_at: string
          id: string
          is_required: boolean
          metadata_json: Json
          quantity: number
          service_key: string
          service_type: string
          simulation_id: string
          source: string
          space_id: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          id?: string
          is_required?: boolean
          metadata_json?: Json
          quantity?: number
          service_key: string
          service_type: string
          simulation_id: string
          source?: string
          space_id: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          is_required?: boolean
          metadata_json?: Json
          quantity?: number
          service_key?: string
          service_type?: string
          simulation_id?: string
          source?: string
          space_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulation_space_services_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_space_services_space_id_fkey"
            columns: ["space_id"]
            isOneToOne: false
            referencedRelation: "simulation_spaces"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_spaces: {
        Row: {
          id: string
        }
        Insert: {
          id?: string
        }
        Update: {
          id?: string
        }
        Relationships: []
      }
      simulation_systems: {
        Row: {
          applies_to_space_id: string | null
          configuration_json: Json
          created_at: string
          id: string
          level_id: string | null
          name: string
          notes: string | null
          simulation_id: string
          system_type_id: string
          updated_at: string
        }
        Insert: {
          applies_to_space_id?: string | null
          configuration_json?: Json
          created_at?: string
          id?: string
          level_id?: string | null
          name: string
          notes?: string | null
          simulation_id: string
          system_type_id: string
          updated_at?: string
        }
        Update: {
          applies_to_space_id?: string | null
          configuration_json?: Json
          created_at?: string
          id?: string
          level_id?: string | null
          name?: string
          notes?: string | null
          simulation_id?: string
          system_type_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "simulation_systems_applies_to_space_id_fkey"
            columns: ["applies_to_space_id"]
            isOneToOne: false
            referencedRelation: "simulation_spaces"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_systems_level_id_fkey"
            columns: ["level_id"]
            isOneToOne: false
            referencedRelation: "simulation_levels"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_systems_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_systems_system_type_id_fkey"
            columns: ["system_type_id"]
            isOneToOne: false
            referencedRelation: "catalog_system_types"
            referencedColumns: ["id"]
          },
        ]
      }
      simulation_user_inputs: {
        Row: {
          created_at: string
          face_id: string | null
          id: string
          input_scope: string
          key: string
          level_id: string | null
          simulation_id: string
          source: string
          space_id: string | null
          system_id: string | null
          updated_at: string
          value_json: Json
        }
        Insert: {
          created_at?: string
          face_id?: string | null
          id?: string
          input_scope: string
          key: string
          level_id?: string | null
          simulation_id: string
          source?: string
          space_id?: string | null
          system_id?: string | null
          updated_at?: string
          value_json?: Json
        }
        Update: {
          created_at?: string
          face_id?: string | null
          id?: string
          input_scope?: string
          key?: string
          level_id?: string | null
          simulation_id?: string
          source?: string
          space_id?: string | null
          system_id?: string | null
          updated_at?: string
          value_json?: Json
        }
        Relationships: [
          {
            foreignKeyName: "simulation_user_inputs_face_id_fkey"
            columns: ["face_id"]
            isOneToOne: false
            referencedRelation: "simulation_space_faces"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_user_inputs_level_id_fkey"
            columns: ["level_id"]
            isOneToOne: false
            referencedRelation: "simulation_levels"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_user_inputs_simulation_id_fkey"
            columns: ["simulation_id"]
            isOneToOne: false
            referencedRelation: "simulations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_user_inputs_space_id_fkey"
            columns: ["space_id"]
            isOneToOne: false
            referencedRelation: "simulation_spaces"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "simulation_user_inputs_system_id_fkey"
            columns: ["system_id"]
            isOneToOne: false
            referencedRelation: "simulation_systems"
            referencedColumns: ["id"]
          },
        ]
      }
      simulations: {
        Row: {
          id: string
        }
        Insert: {
          id?: string
        }
        Update: {
          id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      get_latest_quote_draft: {
        Args: { p_modulo?: string; p_subtipo?: string; p_user_email: string }
        Returns: {
          created_at: string
          current_step: string | null
          flow_version: string
          id: string
          modulo: string
          payload_json: Json
          resumen_json: Json
          status: string
          subtipo: string | null
          total: number
          updated_at: string
          user_email: string
          user_id: string | null
        }[]
        SetofOptions: {
          from: "*"
          to: "app_cotizaciones"
          isOneToOne: false
          isSetofReturn: true
        }
      }
      match_document_chunks: {
        Args: {
          filter_document_id: string
          match_count: number
          query_embedding: string
        }
        Returns: {
          chunk_id: string
          chunk_index: number
          content: string
          document_id: string
          embedding: string
          metadata: Json
          similarity: number
        }[]
      }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
  storage: {
    Tables: {
      buckets: {
        Row: {
          allowed_mime_types: string[] | null
          avif_autodetection: boolean | null
          created_at: string | null
          file_size_limit: number | null
          id: string
          name: string
          owner: string | null
          owner_id: string | null
          public: boolean | null
          type: Database["storage"]["Enums"]["buckettype"]
          updated_at: string | null
        }
        Insert: {
          allowed_mime_types?: string[] | null
          avif_autodetection?: boolean | null
          created_at?: string | null
          file_size_limit?: number | null
          id: string
          name: string
          owner?: string | null
          owner_id?: string | null
          public?: boolean | null
          type?: Database["storage"]["Enums"]["buckettype"]
          updated_at?: string | null
        }
        Update: {
          allowed_mime_types?: string[] | null
          avif_autodetection?: boolean | null
          created_at?: string | null
          file_size_limit?: number | null
          id?: string
          name?: string
          owner?: string | null
          owner_id?: string | null
          public?: boolean | null
          type?: Database["storage"]["Enums"]["buckettype"]
          updated_at?: string | null
        }
        Relationships: []
      }
      buckets_analytics: {
        Row: {
          created_at: string
          deleted_at: string | null
          format: string
          id: string
          name: string
          type: Database["storage"]["Enums"]["buckettype"]
          updated_at: string
        }
        Insert: {
          created_at?: string
          deleted_at?: string | null
          format?: string
          id?: string
          name: string
          type?: Database["storage"]["Enums"]["buckettype"]
          updated_at?: string
        }
        Update: {
          created_at?: string
          deleted_at?: string | null
          format?: string
          id?: string
          name?: string
          type?: Database["storage"]["Enums"]["buckettype"]
          updated_at?: string
        }
        Relationships: []
      }
      buckets_vectors: {
        Row: {
          created_at: string
          id: string
          type: Database["storage"]["Enums"]["buckettype"]
          updated_at: string
        }
        Insert: {
          created_at?: string
          id: string
          type?: Database["storage"]["Enums"]["buckettype"]
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          type?: Database["storage"]["Enums"]["buckettype"]
          updated_at?: string
        }
        Relationships: []
      }
      migrations: {
        Row: {
          executed_at: string | null
          hash: string
          id: number
          name: string
        }
        Insert: {
          executed_at?: string | null
          hash: string
          id: number
          name: string
        }
        Update: {
          executed_at?: string | null
          hash?: string
          id?: number
          name?: string
        }
        Relationships: []
      }
      objects: {
        Row: {
          bucket_id: string | null
          created_at: string | null
          id: string
          last_accessed_at: string | null
          metadata: Json | null
          name: string | null
          owner: string | null
          owner_id: string | null
          path_tokens: string[] | null
          updated_at: string | null
          user_metadata: Json | null
          version: string | null
        }
        Insert: {
          bucket_id?: string | null
          created_at?: string | null
          id?: string
          last_accessed_at?: string | null
          metadata?: Json | null
          name?: string | null
          owner?: string | null
          owner_id?: string | null
          path_tokens?: string[] | null
          updated_at?: string | null
          user_metadata?: Json | null
          version?: string | null
        }
        Update: {
          bucket_id?: string | null
          created_at?: string | null
          id?: string
          last_accessed_at?: string | null
          metadata?: Json | null
          name?: string | null
          owner?: string | null
          owner_id?: string | null
          path_tokens?: string[] | null
          updated_at?: string | null
          user_metadata?: Json | null
          version?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "objects_bucketId_fkey"
            columns: ["bucket_id"]
            isOneToOne: false
            referencedRelation: "buckets"
            referencedColumns: ["id"]
          },
        ]
      }
      s3_multipart_uploads: {
        Row: {
          bucket_id: string
          created_at: string
          id: string
          in_progress_size: number
          key: string
          metadata: Json | null
          owner_id: string | null
          upload_signature: string
          user_metadata: Json | null
          version: string
        }
        Insert: {
          bucket_id: string
          created_at?: string
          id: string
          in_progress_size?: number
          key: string
          metadata?: Json | null
          owner_id?: string | null
          upload_signature: string
          user_metadata?: Json | null
          version: string
        }
        Update: {
          bucket_id?: string
          created_at?: string
          id?: string
          in_progress_size?: number
          key?: string
          metadata?: Json | null
          owner_id?: string | null
          upload_signature?: string
          user_metadata?: Json | null
          version?: string
        }
        Relationships: [
          {
            foreignKeyName: "s3_multipart_uploads_bucket_id_fkey"
            columns: ["bucket_id"]
            isOneToOne: false
            referencedRelation: "buckets"
            referencedColumns: ["id"]
          },
        ]
      }
      s3_multipart_uploads_parts: {
        Row: {
          bucket_id: string
          created_at: string
          etag: string
          id: string
          key: string
          owner_id: string | null
          part_number: number
          size: number
          upload_id: string
          version: string
        }
        Insert: {
          bucket_id: string
          created_at?: string
          etag: string
          id?: string
          key: string
          owner_id?: string | null
          part_number: number
          size?: number
          upload_id: string
          version: string
        }
        Update: {
          bucket_id?: string
          created_at?: string
          etag?: string
          id?: string
          key?: string
          owner_id?: string | null
          part_number?: number
          size?: number
          upload_id?: string
          version?: string
        }
        Relationships: [
          {
            foreignKeyName: "s3_multipart_uploads_parts_bucket_id_fkey"
            columns: ["bucket_id"]
            isOneToOne: false
            referencedRelation: "buckets"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "s3_multipart_uploads_parts_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "s3_multipart_uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      vector_indexes: {
        Row: {
          bucket_id: string
          created_at: string
          data_type: string
          dimension: number
          distance_metric: string
          id: string
          metadata_configuration: Json | null
          name: string
          updated_at: string
        }
        Insert: {
          bucket_id: string
          created_at?: string
          data_type: string
          dimension: number
          distance_metric: string
          id?: string
          metadata_configuration?: Json | null
          name: string
          updated_at?: string
        }
        Update: {
          bucket_id?: string
          created_at?: string
          data_type?: string
          dimension?: number
          distance_metric?: string
          id?: string
          metadata_configuration?: Json | null
          name?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "vector_indexes_bucket_id_fkey"
            columns: ["bucket_id"]
            isOneToOne: false
            referencedRelation: "buckets_vectors"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      allow_any_operation: {
        Args: { expected_operations: string[] }
        Returns: boolean
      }
      allow_only_operation: {
        Args: { expected_operation: string }
        Returns: boolean
      }
      can_insert_object: {
        Args: { bucketid: string; metadata: Json; name: string; owner: string }
        Returns: undefined
      }
      extension: { Args: { name: string }; Returns: string }
      filename: { Args: { name: string }; Returns: string }
      foldername: { Args: { name: string }; Returns: string[] }
      get_common_prefix: {
        Args: { p_delimiter: string; p_key: string; p_prefix: string }
        Returns: string
      }
      get_size_by_bucket: {
        Args: never
        Returns: {
          bucket_id: string
          size: number
        }[]
      }
      list_multipart_uploads_with_delimiter: {
        Args: {
          bucket_id: string
          delimiter_param: string
          max_keys?: number
          next_key_token?: string
          next_upload_token?: string
          prefix_param: string
        }
        Returns: {
          created_at: string
          id: string
          key: string
        }[]
      }
      list_objects_with_delimiter: {
        Args: {
          _bucket_id: string
          delimiter_param: string
          max_keys?: number
          next_token?: string
          prefix_param: string
          sort_order?: string
          start_after?: string
        }
        Returns: {
          created_at: string
          id: string
          last_accessed_at: string
          metadata: Json
          name: string
          updated_at: string
        }[]
      }
      operation: { Args: never; Returns: string }
      search: {
        Args: {
          bucketname: string
          levels?: number
          limits?: number
          offsets?: number
          prefix: string
          search?: string
          sortcolumn?: string
          sortorder?: string
        }
        Returns: {
          created_at: string
          id: string
          last_accessed_at: string
          metadata: Json
          name: string
          updated_at: string
        }[]
      }
      search_by_timestamp: {
        Args: {
          p_bucket_id: string
          p_level: number
          p_limit: number
          p_prefix: string
          p_sort_column: string
          p_sort_column_after: string
          p_sort_order: string
          p_start_after: string
        }
        Returns: {
          created_at: string
          id: string
          key: string
          last_accessed_at: string
          metadata: Json
          name: string
          updated_at: string
        }[]
      }
      search_v2: {
        Args: {
          bucket_name: string
          levels?: number
          limits?: number
          prefix: string
          sort_column?: string
          sort_column_after?: string
          sort_order?: string
          start_after?: string
        }
        Returns: {
          created_at: string
          id: string
          key: string
          last_accessed_at: string
          metadata: Json
          name: string
          updated_at: string
        }[]
      }
    }
    Enums: {
      buckettype: "STANDARD" | "ANALYTICS" | "VECTOR"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  auth: {
    Enums: {
      aal_level: ["aal1", "aal2", "aal3"],
      code_challenge_method: ["s256", "plain"],
      factor_status: ["unverified", "verified"],
      factor_type: ["totp", "webauthn", "phone"],
      oauth_authorization_status: ["pending", "approved", "denied", "expired"],
      oauth_client_type: ["public", "confidential"],
      oauth_registration_type: ["dynamic", "manual"],
      oauth_response_type: ["code"],
      one_time_token_type: [
        "confirmation_token",
        "reauthentication_token",
        "recovery_token",
        "email_change_token_new",
        "email_change_token_current",
        "phone_change_token",
      ],
    },
  },
  public: {
    Enums: {},
  },
  storage: {
    Enums: {
      buckettype: ["STANDARD", "ANALYTICS", "VECTOR"],
    },
  },
} as const
