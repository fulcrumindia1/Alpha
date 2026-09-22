-- ============================================================
-- FULCRUM-INDIA: Cluster A - Supabase Production Schema & RLS
-- Stack: Streamlit + Supabase (Auth + PostgreSQL + JSONB + RLS)
-- Core Mission: Record the complete story of an entrepreneur (Journey)
--               and coordinate the people helping that entrepreneur.
-- ============================================================

-- ─────────────────────────────────────────────────────────────
-- 0. EXTENSIONS
-- ─────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────────
-- 1. PROFILES (Relational Core + JSONB)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
    id            UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email         TEXT UNIQUE NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('aspirant', 'guide', 'sme', 'admin')) DEFAULT 'aspirant',
    full_name     TEXT NOT NULL,
    phone         TEXT,
    district      TEXT,
    state         TEXT DEFAULT 'Tamil Nadu',
    profile_data  JSONB DEFAULT '{}'::jsonb,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 2. RELATIONSHIPS (Admin Authority Assignment)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.relationships (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aspirant_id   UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    guide_id      UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    sme_id        UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    assigned_by   UUID REFERENCES public.profiles(id),
    status        TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'inactive')),
    notes         TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_aspirant_relationship UNIQUE (aspirant_id)
);

ALTER TABLE public.relationships ADD COLUMN IF NOT EXISTS sme_ids JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.relationships ADD COLUMN IF NOT EXISTS guide_ids JSONB DEFAULT '[]'::jsonb;

-- ─────────────────────────────────────────────────────────────
-- 3. JOURNEYS (The Entrepreneur's Movie Header)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.journeys (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aspirant_id   UUID UNIQUE NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    business_type TEXT,
    stage         TEXT DEFAULT 'idea',
    start_date    DATE DEFAULT CURRENT_DATE,
    status        TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'archived')),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 4. JOURNEY EVENTS (The Chronological Narrative Spine)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.journey_events (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    journey_id    UUID NOT NULL REFERENCES public.journeys(id) ON DELETE CASCADE,
    aspirant_id   UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    actor_id      UUID NOT NULL REFERENCES public.profiles(id),
    actor_role    TEXT NOT NULL CHECK (actor_role IN ('aspirant', 'guide', 'sme', 'admin', 'system')),
    event_type    TEXT NOT NULL,
    event_data    JSONB NOT NULL DEFAULT '{}'::jsonb,
    event_date    TIMESTAMPTZ DEFAULT NOW(),
    included_in_roadmap BOOLEAN DEFAULT TRUE,
    deleted_at    TIMESTAMPTZ,
    deleted_by    UUID REFERENCES public.profiles(id),
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Idempotent column addition for roadmap autonomy
ALTER TABLE public.journey_events ADD COLUMN IF NOT EXISTS included_in_roadmap BOOLEAN DEFAULT TRUE;

-- ─────────────────────────────────────────────────────────────
-- 5. HELP REQUESTS (Communication & Support Queue)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.help_requests (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aspirant_id        UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    subject            TEXT NOT NULL,
    message            TEXT NOT NULL,
    priority           TEXT DEFAULT 'MEDIUM' CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'URGENT')),
    status             TEXT DEFAULT 'OPEN',
    assigned_guide_id  UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    assigned_at        TIMESTAMPTZ,
    last_handled_at    TIMESTAMPTZ,
    escalated_at       TIMESTAMPTZ,
    escalation_reason  TEXT,
    resolved_by        UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    guide_response     TEXT,
    admin_response     TEXT,
    responded_by       UUID REFERENCES public.profiles(id),
    requester_id       UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    requester_role     TEXT DEFAULT 'aspirant',
    request_type       TEXT DEFAULT 'aspirant_consultation',
    admin_directive    TEXT,
    directive_issued_at TIMESTAMPTZ,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT help_requests_status_check CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED', 'PENDING_ADMIN', 'DIRECTIVE_ISSUED'))
);

-- Idempotent column additions for existing / partially initialized databases
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS assigned_guide_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS last_handled_at TIMESTAMPTZ;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMPTZ;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS escalation_reason TEXT;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS resolved_by UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS guide_response TEXT;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS admin_response TEXT;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS responded_by UUID REFERENCES public.profiles(id);
-- SME Support & Routing Columns
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'GENERAL';
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS assigned_sme_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS sme_response TEXT;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS target_role TEXT DEFAULT 'guide';
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS category_detail TEXT;
-- Mentor-to-Admin Directives & Inquiries Columns
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS requester_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS requester_role TEXT DEFAULT 'aspirant';
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS request_type TEXT DEFAULT 'aspirant_consultation';
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS admin_directive TEXT;
ALTER TABLE public.help_requests ADD COLUMN IF NOT EXISTS directive_issued_at TIMESTAMPTZ;

-- Idempotent status CHECK constraint update
DO $$
BEGIN
    ALTER TABLE public.help_requests DROP CONSTRAINT IF EXISTS help_requests_status_check;
    ALTER TABLE public.help_requests
        ADD CONSTRAINT help_requests_status_check
        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED', 'PENDING_ADMIN', 'DIRECTIVE_ISSUED'));
END $$;

-- ─────────────────────────────────────────────────────────────
-- 5B. NOTIFICATIONS (In-App Universal Alert System)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.notifications (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id            UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    actor_id           UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    title              TEXT NOT NULL,
    message            TEXT NOT NULL,
    notification_type  TEXT NOT NULL,
    link               TEXT,
    is_read            BOOLEAN DEFAULT FALSE,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 5C. ASSIGNMENT HISTORY (Roster Transition & Audit Log)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.assignment_history (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aspirant_id        UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    mentor_id          UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    mentor_role        TEXT NOT NULL CHECK (mentor_role IN ('guide', 'sme')),
    assigned_by        UUID REFERENCES public.profiles(id),
    action             TEXT NOT NULL CHECK (action IN ('ASSIGNED', 'REPLACED', 'UNASSIGNED')),
    previous_mentor_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    notes              TEXT,
    created_at         TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 6. SCHEMES (170 Authoritative Schemes Catalogue)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.schemes (
    id                  TEXT PRIMARY KEY,
    source_id           TEXT,
    name                TEXT NOT NULL,
    agency              TEXT,
    ministry            TEXT,
    scheme_type         TEXT,
    category_type       TEXT,
    funding_type        TEXT,
    stage               TEXT,
    amount              TEXT,
    brief               TEXT,
    description         TEXT,
    sectors             JSONB DEFAULT '[]'::jsonb,
    eligibility         JSONB DEFAULT '[]'::jsonb,
    terms               JSONB DEFAULT '[]'::jsonb,
    hidden_agenda       JSONB DEFAULT '[]'::jsonb,
    red_flags           JSONB DEFAULT '[]'::jsonb,
    process             TEXT,
    timeline            TEXT,
    success_rate        TEXT,
    contact             TEXT,
    state_scope         TEXT,
    geography           TEXT,
    application_url     TEXT,
    last_verified       TEXT,
    application_prompt  TEXT,
    source_dataset      TEXT DEFAULT 'Founder AI Digital Playbook 2026',
    status              TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'archived')),
    is_active           BOOLEAN DEFAULT TRUE,
    display_order       INTEGER DEFAULT 9999,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure display_order exists on partially initialized databases
ALTER TABLE public.schemes ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 9999;

-- ─────────────────────────────────────────────────────────────
-- 7. SCHEME RELEASES (Guide Governance & Visibility Gate)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.scheme_releases (
    id                    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aspirant_id           UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    guide_id              UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    scheme_id             TEXT NOT NULL REFERENCES public.schemes(id) ON DELETE CASCADE,
    status                TEXT NOT NULL DEFAULT 'RELEASED' CHECK (status IN ('DRAFT', 'RELEASED', 'WITHDRAWN')),
    guide_note            TEXT,
    guide_recommendation  TEXT,
    eligibility_summary   TEXT,
    released_at           TIMESTAMPTZ,
    released_by           UUID REFERENCES public.profiles(id),
    withdrawn_at          TIMESTAMPTZ,
    withdrawn_by          UUID REFERENCES public.profiles(id),
    created_at            TIMESTAMPTZ DEFAULT NOW(),
    updated_at            TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_aspirant_scheme_release UNIQUE (aspirant_id, scheme_id)
);

-- ─────────────────────────────────────────────────────────────
-- 8. ACTIVITY LOG (Audit Trail)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.activity_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES public.profiles(id),
    action      TEXT NOT NULL,
    entity      TEXT NOT NULL,
    entity_id   TEXT,
    details     JSONB DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- 9. INDEXES FOR HIGH-SPEED QUERIES
-- ─────────────────────────────────────────────────────────────
-- Profiles
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);

-- Relationships
CREATE INDEX IF NOT EXISTS idx_relationships_aspirant ON public.relationships(aspirant_id);
CREATE INDEX IF NOT EXISTS idx_relationships_guide ON public.relationships(guide_id);
CREATE INDEX IF NOT EXISTS idx_relationships_sme ON public.relationships(sme_id);

-- Journeys
CREATE INDEX IF NOT EXISTS idx_journeys_aspirant ON public.journeys(aspirant_id);

-- Journey Events
CREATE INDEX IF NOT EXISTS idx_journey_events_journey ON public.journey_events(journey_id, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_journey_events_aspirant ON public.journey_events(aspirant_id);

-- Help Requests
CREATE INDEX IF NOT EXISTS idx_help_requests_aspirant ON public.help_requests(aspirant_id);
CREATE INDEX IF NOT EXISTS idx_help_requests_status ON public.help_requests(status);
CREATE INDEX IF NOT EXISTS idx_help_requests_assigned_guide ON public.help_requests(assigned_guide_id);
CREATE INDEX IF NOT EXISTS idx_help_requests_assigned_sme ON public.help_requests(assigned_sme_id);
CREATE INDEX IF NOT EXISTS idx_help_requests_status_created ON public.help_requests(status, created_at);

-- Notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON public.notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON public.notifications(user_id, is_read);

-- Assignment History
CREATE INDEX IF NOT EXISTS idx_assignment_history_aspirant ON public.assignment_history(aspirant_id);
CREATE INDEX IF NOT EXISTS idx_assignment_history_mentor ON public.assignment_history(mentor_id);

-- Schemes
CREATE INDEX IF NOT EXISTS idx_schemes_active ON public.schemes(is_active);

-- Scheme Releases
CREATE INDEX IF NOT EXISTS idx_scheme_releases_aspirant ON public.scheme_releases(aspirant_id);
CREATE INDEX IF NOT EXISTS idx_scheme_releases_guide ON public.scheme_releases(guide_id);
CREATE INDEX IF NOT EXISTS idx_scheme_releases_scheme ON public.scheme_releases(scheme_id);
CREATE INDEX IF NOT EXISTS idx_scheme_releases_status ON public.scheme_releases(status);

-- ─────────────────────────────────────────────────────────────
-- 10. SECURITY DEFINER HELPER FUNCTIONS (Eliminates RLS Recursion)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.current_role()
RETURNS TEXT AS $$
BEGIN
    RETURN (SELECT role FROM public.profiles WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ─────────────────────────────────────────────────────────────
-- 11. AUTOMATION: PROFILE CREATION ON SUPABASE AUTH SIGNUP
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    user_full_name TEXT;
    user_role TEXT;
    user_phone TEXT;
    user_district TEXT;
BEGIN
    -- Extract full name from raw_user_meta_data if present, else fallback to email prefix
    user_full_name := COALESCE(
        NEW.raw_user_meta_data->>'full_name',
        split_part(NEW.email, '@', 1)
    );
    -- Extract role from metadata, strictly defaults to 'aspirant' for public signups
    user_role := COALESCE(
        NEW.raw_user_meta_data->>'role',
        'aspirant'
    );
    -- Extract phone and district
    user_phone := NEW.raw_user_meta_data->>'phone';
    user_district := COALESCE(NEW.raw_user_meta_data->>'district', 'Tamil Nadu');

    INSERT INTO public.profiles (id, email, full_name, role, phone, district, profile_data)
    VALUES (
        NEW.id,
        NEW.email,
        user_full_name,
        user_role,
        user_phone,
        user_district,
        jsonb_build_object(
            'personal', jsonb_build_object(
                'full_name', user_full_name,
                'email', NEW.email,
                'phone', user_phone,
                'district', user_district
            ),
            'business', jsonb_build_object(
                'business_name', user_full_name || '''s Enterprise',
                'stage', 'idea'
            ),
            'demographics', jsonb_build_object(
                'district', user_district,
                'state', 'Tamil Nadu'
            )
        )
    )
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email,
        full_name = COALESCE(public.profiles.full_name, EXCLUDED.full_name),
        phone = COALESCE(public.profiles.phone, EXCLUDED.phone),
        district = COALESCE(public.profiles.district, EXCLUDED.district);

    -- Auto-initialize Journey for Aspirants
    IF user_role = 'aspirant' THEN
        INSERT INTO public.journeys (aspirant_id, title, business_type, stage)
        VALUES (
            NEW.id,
            user_full_name || '''s Enterprise Journey',
            'Entrepreneurship',
            'idea'
        )
        ON CONFLICT (aspirant_id) DO NOTHING;

        -- Auto-initialize empty relationship record
        INSERT INTO public.relationships (aspirant_id)
        VALUES (NEW.id)
        ON CONFLICT (aspirant_id) DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ─────────────────────────────────────────────────────────────
-- 12. ROW LEVEL SECURITY (RLS) POLICIES
-- ─────────────────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.journeys ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.journey_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.help_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.schemes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scheme_releases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_log ENABLE ROW LEVEL SECURITY;

-- ── PROFILES POLICIES ──
DROP POLICY IF EXISTS "Admin full access profiles" ON public.profiles;
CREATE POLICY "Admin full access profiles" ON public.profiles
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Users read own profile" ON public.profiles;
CREATE POLICY "Users read own profile" ON public.profiles
    FOR SELECT TO authenticated USING (id = auth.uid());

DROP POLICY IF EXISTS "Users update own profile" ON public.profiles;
CREATE POLICY "Users update own profile" ON public.profiles
    FOR UPDATE TO authenticated USING (id = auth.uid()) WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "Guides read assigned aspirants profiles" ON public.profiles;
CREATE POLICY "Guides read assigned aspirants profiles" ON public.profiles
    FOR SELECT TO authenticated USING (
        id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
    );

DROP POLICY IF EXISTS "SMEs read assigned aspirants profiles" ON public.profiles;
CREATE POLICY "SMEs read assigned aspirants profiles" ON public.profiles
    FOR SELECT TO authenticated USING (
        id IN (SELECT aspirant_id FROM public.relationships WHERE sme_id = auth.uid())
    );

DROP POLICY IF EXISTS "Aspirants read assigned guide profile" ON public.profiles;
CREATE POLICY "Aspirants read assigned guide profile" ON public.profiles
    FOR SELECT TO authenticated USING (
        id IN (SELECT guide_id FROM public.relationships WHERE aspirant_id = auth.uid())
        OR id IN (SELECT sme_id FROM public.relationships WHERE aspirant_id = auth.uid())
    );

-- ── RELATIONSHIPS POLICIES ──
DROP POLICY IF EXISTS "Admin full access relationships" ON public.relationships;
CREATE POLICY "Admin full access relationships" ON public.relationships
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Aspirant view own relationship" ON public.relationships;
CREATE POLICY "Aspirant view own relationship" ON public.relationships
    FOR SELECT TO authenticated USING (aspirant_id = auth.uid());

DROP POLICY IF EXISTS "Guide view assigned relationships" ON public.relationships;
CREATE POLICY "Guide view assigned relationships" ON public.relationships
    FOR SELECT TO authenticated USING (guide_id = auth.uid());

DROP POLICY IF EXISTS "SME view assigned relationships" ON public.relationships;
CREATE POLICY "SME view assigned relationships" ON public.relationships
    FOR SELECT TO authenticated USING (sme_id = auth.uid());

-- ── JOURNEYS POLICIES ──
DROP POLICY IF EXISTS "Admin full access journeys" ON public.journeys;
CREATE POLICY "Admin full access journeys" ON public.journeys
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Aspirant manage own journey" ON public.journeys;
CREATE POLICY "Aspirant manage own journey" ON public.journeys
    FOR ALL TO authenticated USING (aspirant_id = auth.uid());

DROP POLICY IF EXISTS "Guide read assigned journeys" ON public.journeys;
CREATE POLICY "Guide read assigned journeys" ON public.journeys
    FOR SELECT TO authenticated USING (
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
    );

DROP POLICY IF EXISTS "SME read assigned journeys" ON public.journeys;
CREATE POLICY "SME read assigned journeys" ON public.journeys
    FOR SELECT TO authenticated USING (
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE sme_id = auth.uid())
    );

-- ── JOURNEY EVENTS POLICIES ──
DROP POLICY IF EXISTS "Admin full access journey events" ON public.journey_events;
CREATE POLICY "Admin full access journey events" ON public.journey_events
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Aspirant view own journey events" ON public.journey_events;
CREATE POLICY "Aspirant view own journey events" ON public.journey_events
    FOR SELECT TO authenticated USING (aspirant_id = auth.uid() AND deleted_at IS NULL);

DROP POLICY IF EXISTS "Aspirant insert own journey events" ON public.journey_events;
CREATE POLICY "Aspirant insert own journey events" ON public.journey_events
    FOR INSERT TO authenticated WITH CHECK (aspirant_id = auth.uid() AND actor_id = auth.uid());

DROP POLICY IF EXISTS "Aspirant update own manual journey events" ON public.journey_events;
CREATE POLICY "Aspirant update own manual journey events" ON public.journey_events
    FOR UPDATE TO authenticated USING (
        aspirant_id = auth.uid() AND actor_id = auth.uid() AND actor_role = 'aspirant'
    );

DROP POLICY IF EXISTS "Aspirant toggle roadmap inclusion on own journey events" ON public.journey_events;
CREATE POLICY "Aspirant toggle roadmap inclusion on own journey events" ON public.journey_events
    FOR UPDATE TO authenticated USING (
        aspirant_id = auth.uid()
    )
    WITH CHECK (
        aspirant_id = auth.uid()
    );

DROP POLICY IF EXISTS "Guide view assigned journey events" ON public.journey_events;
CREATE POLICY "Guide view assigned journey events" ON public.journey_events
    FOR SELECT TO authenticated USING (
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
        AND deleted_at IS NULL
    );

DROP POLICY IF EXISTS "Guide insert journey events" ON public.journey_events;
CREATE POLICY "Guide insert journey events" ON public.journey_events
    FOR INSERT TO authenticated WITH CHECK (
        actor_id = auth.uid() AND actor_role = 'guide' AND
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
    );

DROP POLICY IF EXISTS "Guide manage own journey events" ON public.journey_events;
CREATE POLICY "Guide manage own journey events" ON public.journey_events
    FOR UPDATE TO authenticated USING (actor_id = auth.uid() AND actor_role = 'guide');

DROP POLICY IF EXISTS "SME view assigned journey events" ON public.journey_events;
CREATE POLICY "SME view assigned journey events" ON public.journey_events
    FOR SELECT TO authenticated USING (
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE sme_id = auth.uid())
        AND deleted_at IS NULL
    );

DROP POLICY IF EXISTS "SME insert journey events" ON public.journey_events;
CREATE POLICY "SME insert journey events" ON public.journey_events
    FOR INSERT TO authenticated WITH CHECK (
        actor_id = auth.uid() AND actor_role = 'sme' AND
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE sme_id = auth.uid())
    );

-- ── HELP REQUESTS POLICIES ──
DROP POLICY IF EXISTS "Admin full access help requests" ON public.help_requests;
CREATE POLICY "Admin full access help requests" ON public.help_requests
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Aspirant view own help requests" ON public.help_requests;
CREATE POLICY "Aspirant view own help requests" ON public.help_requests
    FOR SELECT TO authenticated USING (aspirant_id = auth.uid());

DROP POLICY IF EXISTS "Aspirant insert own help requests" ON public.help_requests;
CREATE POLICY "Aspirant insert own help requests" ON public.help_requests
    FOR INSERT TO authenticated WITH CHECK (aspirant_id = auth.uid());

DROP POLICY IF EXISTS "Guides view assigned help requests" ON public.help_requests;
CREATE POLICY "Guides view assigned help requests" ON public.help_requests
    FOR SELECT TO authenticated USING (
        assigned_guide_id = auth.uid() OR
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
    );

DROP POLICY IF EXISTS "Guides update assigned help requests" ON public.help_requests;
CREATE POLICY "Guides update assigned help requests" ON public.help_requests
    FOR UPDATE TO authenticated USING (
        assigned_guide_id = auth.uid() OR
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
    );

DROP POLICY IF EXISTS "SMEs view assigned help requests" ON public.help_requests;
CREATE POLICY "SMEs view assigned help requests" ON public.help_requests
    FOR SELECT TO authenticated USING (
        assigned_sme_id = auth.uid() OR
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE sme_id = auth.uid())
    );

DROP POLICY IF EXISTS "SMEs update assigned help requests" ON public.help_requests;
CREATE POLICY "SMEs update assigned help requests" ON public.help_requests
    FOR UPDATE TO authenticated USING (
        assigned_sme_id = auth.uid() OR
        aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE sme_id = auth.uid())
    );

-- ── SCHEMES POLICIES ──
-- NOTE: Aspirants MUST NOT have direct SELECT on schemes table.
-- They access schemes ONLY through scheme_releases (Guide-gated governance).
DROP POLICY IF EXISTS "Authenticated read active schemes" ON public.schemes;
DROP POLICY IF EXISTS "Public read active schemes" ON public.schemes;

-- Admin: full CRUD (already exists via "Admin manage schemes" below, but explicit read too)
DROP POLICY IF EXISTS "Admin read all schemes" ON public.schemes;
CREATE POLICY "Admin read all schemes" ON public.schemes
    FOR SELECT TO authenticated USING (public.is_admin());

-- Guide: can read ALL active schemes (full catalogue for evaluation/gatekeeper role)
DROP POLICY IF EXISTS "Guide read active schemes" ON public.schemes;
CREATE POLICY "Guide read active schemes" ON public.schemes
    FOR SELECT TO authenticated
    USING (is_active = TRUE AND public.current_role() = 'guide');

DROP POLICY IF EXISTS "Admin manage schemes" ON public.schemes;
CREATE POLICY "Admin manage schemes" ON public.schemes
    FOR ALL TO authenticated USING (public.is_admin());

-- Sanitized view: excludes hidden_agenda, red_flags, application_prompt
-- Available for any future aspirant-facing direct reads if needed
CREATE OR REPLACE VIEW public.schemes_public
WITH (security_invoker = true) AS
SELECT
    id, source_id, name, agency, ministry, scheme_type,
    category_type, funding_type, stage, amount, brief, description,
    sectors, eligibility, terms, process, timeline, success_rate,
    contact, state_scope, geography, application_url, last_verified,
    source_dataset, status, is_active, display_order, created_at, updated_at
FROM public.schemes
WHERE is_active = TRUE;

-- ── SCHEME RELEASES POLICIES ──
DROP POLICY IF EXISTS "Admin full access scheme_releases" ON public.scheme_releases;
CREATE POLICY "Admin full access scheme_releases" ON public.scheme_releases
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Guides manage assigned aspirants scheme_releases" ON public.scheme_releases;
CREATE POLICY "Guides manage assigned aspirants scheme_releases" ON public.scheme_releases
    FOR ALL TO authenticated
    USING (
        guide_id = auth.uid()
        AND aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
    )
    WITH CHECK (
        guide_id = auth.uid()
        AND aspirant_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid())
    );

DROP POLICY IF EXISTS "Aspirants read own released schemes" ON public.scheme_releases;
CREATE POLICY "Aspirants read own released schemes" ON public.scheme_releases
    FOR SELECT TO authenticated
    USING (
        aspirant_id = auth.uid()
        AND status = 'RELEASED'
    );

-- ── ACTIVITY LOG POLICIES ──
DROP POLICY IF EXISTS "Admin full access activity log" ON public.activity_log;
CREATE POLICY "Admin full access activity log" ON public.activity_log
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Users insert activity log" ON public.activity_log;
CREATE POLICY "Users insert activity log" ON public.activity_log
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid() OR public.is_admin());

-- ── NOTIFICATIONS POLICIES ──
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin full access notifications" ON public.notifications;
CREATE POLICY "Admin full access notifications" ON public.notifications
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Users read own notifications" ON public.notifications;
CREATE POLICY "Users read own notifications" ON public.notifications
    FOR SELECT TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users update own notifications" ON public.notifications;
CREATE POLICY "Users update own notifications" ON public.notifications
    FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Authenticated insert notifications" ON public.notifications;
DROP POLICY IF EXISTS "Restricted insert notifications" ON public.notifications;
CREATE POLICY "Restricted insert notifications" ON public.notifications
    FOR INSERT TO authenticated
    WITH CHECK (
        public.is_admin() OR
        (actor_id = auth.uid() AND (
            user_id = auth.uid() OR
            user_id IN (SELECT guide_id FROM public.relationships WHERE aspirant_id = auth.uid()) OR
            user_id IN (SELECT sme_id FROM public.relationships WHERE aspirant_id = auth.uid()) OR
            user_id IN (SELECT aspirant_id FROM public.relationships WHERE guide_id = auth.uid() OR sme_id = auth.uid())
        ))
    );

-- ── ASSIGNMENT HISTORY POLICIES ──
ALTER TABLE public.assignment_history ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admin full access assignment_history" ON public.assignment_history;
CREATE POLICY "Admin full access assignment_history" ON public.assignment_history
    FOR ALL TO authenticated USING (public.is_admin());

DROP POLICY IF EXISTS "Mentors read related assignment_history" ON public.assignment_history;
CREATE POLICY "Mentors read related assignment_history" ON public.assignment_history
    FOR SELECT TO authenticated USING (
        mentor_id = auth.uid() OR previous_mentor_id = auth.uid()
    );

DROP POLICY IF EXISTS "Aspirants read own assignment_history" ON public.assignment_history;
CREATE POLICY "Aspirants read own assignment_history" ON public.assignment_history
    FOR SELECT TO authenticated USING (aspirant_id = auth.uid());

-- ─────────────────────────────────────────────────────────────
-- ─────────────────────────────────────────────────────────────
-- 13. MENTOR DIRECTIVES & TWO-TIER GOVERNANCE
-- ─────────────────────────────────────────────────────────────
-- Auto-escalation removed: Aspirants interact solely with Guides & SMEs.
-- Inquiries to Admin originate strictly from Guides/SMEs on behalf of an Aspirant.
-- Admin responds with official Administrative Directives to mentors.

-- ─────────────────────────────────────────────────────────────
-- 14. INITIAL ADMIN SEED HELPER (Execute with your admin email)
-- ─────────────────────────────────────────────────────────────
-- Example: To promote an existing user to admin:
-- UPDATE public.profiles SET role = 'admin' WHERE email = 'admin@fulcrum.in';
