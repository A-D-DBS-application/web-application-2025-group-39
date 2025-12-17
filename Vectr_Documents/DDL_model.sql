-- 1. COMPANY
CREATE TABLE public.company (
    id_company SERIAL PRIMARY KEY,              -- SERIAL maakt automatisch 1, 2, 3... aan.
    company_name VARCHAR NOT NULL
);

-- 2. PROFILE
CREATE TABLE public.profile (
    id_profile SERIAL PRIMARY KEY,
    id_company INTEGER NOT NULL,
    
    name VARCHAR NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,                                             -- UNIQUE: Voorkomt dat 2 gebruikers hetzelfde e-mailadres hebben.
    role VARCHAR,
    password_hash VARCHAR NOT NULL,
    
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),       -- 'DEFAULT (NOW() AT TIME ZONE 'utc')' zorgt dat de huidige tijd automatisch wordt ingevuld.

    -- RELATIE NAAR COMPANY:
    CONSTRAINT fk_profile_company FOREIGN KEY (id_company)
        REFERENCES public.company (id_company)
        ON DELETE RESTRICT                                                          -- ON DELETE RESTRICT: Dit is een veiligheidsmaatregel. Je mag een Company NIET verwijderen, zolang er nog Profiles aan gekoppeld zijn. Je moet eerst de profiles verwijderen.
);

-- 3. PROJECT
CREATE TABLE public.project (
    id_project SERIAL PRIMARY KEY,
    id_company INTEGER NOT NULL,
    project_name VARCHAR NOT NULL,
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    
    -- TtV Schaling limieten (Floating point getallen voor decimalen)
    ttm_low_limit REAL,
    ttm_high_limit REAL,
    ttbv_low_limit REAL,
    ttbv_high_limit REAL,

    CONSTRAINT fk_project_company FOREIGN KEY (id_company)
        REFERENCES public.company (id_company)
        ON DELETE RESTRICT
);

-- 4. FEATURES_IDEAS
CREATE TABLE public.features_ideas (
    id_feature VARCHAR PRIMARY KEY, 
    
    id_company INTEGER NOT NULL,
    id_project INTEGER NOT NULL,
    
    name_feature VARCHAR NOT NULL,
    description TEXT,
    
    -- Financiële velden (INTEGER is vaak veiliger dan FLOAT voor geld om afrondingsfouten te voorkomen)
    horizon INTEGER,
    extra_revenue INTEGER,
    churn_reduction INTEGER,
    cost_savings INTEGER,
    investment_hours INTEGER,
    hourly_rate INTEGER,
    opex INTEGER,
    other_costs INTEGER,

    -- Time to Value (weken)
    ttm_weeks INTEGER,
    ttbv_weeks INTEGER,

    -- Calculated values (REAL = Float)
    quality_score REAL,
    roi_percent REAL,
    ttv_weeks REAL,
    
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    warning_dismissed BOOLEAN NOT NULL DEFAULT FALSE,

    -- RELATIE 1: De Company
    CONSTRAINT fk_feature_company FOREIGN KEY (id_company)
        REFERENCES public.company (id_company)
        ON DELETE RESTRICT,

    -- RELATIE 2: Het Project
    CONSTRAINT fk_feature_project FOREIGN KEY (id_project)
        REFERENCES public.project (id_project)
        ON DELETE CASCADE                                                                 -- ON DELETE CASCADE: Als je een Project verwijdert, worden alle bijbehorende, Features AUTOMATISCH ook verwijderd.
);

-- 5. ROADMAP
CREATE TABLE public.roadmap (
    id_roadmap SERIAL PRIMARY KEY,
    id_project INTEGER NOT NULL,
    
    start_roadmap DATE NOT NULL,
    end_roadmap DATE NOT NULL,
    
    time_capacity REAL NOT NULL,
    budget_allocation REAL NOT NULL,
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),

    CONSTRAINT fk_roadmap_project FOREIGN KEY (id_project)
        REFERENCES public.project (id_project)
        ON DELETE CASCADE
);

-- 6. MILESTONE
CREATE TABLE public.milestone (
    id_milestone SERIAL PRIMARY KEY,
    id_roadmap INTEGER NOT NULL,
    
    name VARCHAR NOT NULL,
    start_date DATE,
    end_date DATE,
    goal VARCHAR,
    status VARCHAR,

    CONSTRAINT fk_milestone_roadmap FOREIGN KEY (id_roadmap)
        REFERENCES public.roadmap (id_roadmap)
        ON DELETE CASCADE
);

-- 7. MILESTONE_FEATURES (KOPPELTABEL / JUNCTION TABLE), Dit regelt de Veel-op-Veel (M:N) relatie.
CREATE TABLE public.milestone_features (
    id_milestone INTEGER NOT NULL,
    id_feature VARCHAR NOT NULL,

    -- COMPOSITE PRIMARY KEY:
    PRIMARY KEY (id_milestone, id_feature),

    -- FK constraints met CASCADE:
    CONSTRAINT fk_mf_milestone FOREIGN KEY (id_milestone)
        REFERENCES public.milestone (id_milestone)
        ON DELETE CASCADE,                                                      -- Als de milestone verdwijnt -> verbinding weg.

    CONSTRAINT fk_mf_feature FOREIGN KEY (id_feature)
        REFERENCES public.features_ideas (id_feature)
        ON DELETE CASCADE                                                      -- Als de feature verdwijnt -> verbinding weg.
);

-- 8. EVIDENCE
CREATE TABLE public.evidence (
    id_evidence SERIAL PRIMARY KEY,
    id_feature VARCHAR NOT NULL,

    title VARCHAR,
    type VARCHAR,
    source VARCHAR,
    description TEXT,
    attachment_url TEXT,
    
    old_confidence REAL,
    new_confidence REAL,
    
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),

    CONSTRAINT fk_evidence_feature FOREIGN KEY (id_feature)
        REFERENCES public.features_ideas (id_feature)
        ON DELETE RESTRICT,                                                     -- RESTRICT: Je kunt een feature niet wissen zolang er nog bewijs aan hangt (veiligheid).

    CONSTRAINT fk_evidence_company FOREIGN KEY (id_company)
        REFERENCES public.company (id_company)
        ON DELETE RESTRICT
);

-- 9. DECISION
CREATE TABLE public.decision (
    id_decision SERIAL PRIMARY KEY,
    id_feature VARCHAR NOT NULL,
    id_profile INTEGER NOT NULL,
    id_company INTEGER NOT NULL,
    
    decision_type VARCHAR(50) NOT NULL,
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),

    -- UNIQUE CONSTRAINT (Complex):
    -- Dit dwingt af dat één profiel (id_profile) maar EEN keer een beslissing mag nemen 
    -- voor een specifieke feature (id_feature).
    -- Als ze opnieuw proberen te stemmen, geeft de database een foutmelding.
    CONSTRAINT uq_decision_feature_profile UNIQUE (id_feature, id_profile),

    CONSTRAINT fk_decision_feature FOREIGN KEY (id_feature)
        REFERENCES public.features_ideas (id_feature)
        ON DELETE CASCADE,

    CONSTRAINT fk_decision_profile FOREIGN KEY (id_profile)
        REFERENCES public.profile (id_profile)
        ON DELETE CASCADE,

    CONSTRAINT fk_decision_company FOREIGN KEY (id_company)
        REFERENCES public.company (id_company)
        ON DELETE RESTRICT
);

-- 10. PROJECT_CHAT_MESSAGE
CREATE TABLE public.project_chat_message (
    id_message SERIAL PRIMARY KEY,
    id_project INTEGER NOT NULL,
    id_profile INTEGER NOT NULL,
    
    content TEXT NOT NULL,
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),

    CONSTRAINT fk_chat_project FOREIGN KEY (id_project)
        REFERENCES public.project (id_project)
        ON DELETE CASCADE,                                                      -- Als project weg is, mag de chatgeschiedenis ook weg.

    CONSTRAINT fk_chat_profile FOREIGN KEY (id_profile)
        REFERENCES public.profile (id_profile)
        ON DELETE CASCADE
);