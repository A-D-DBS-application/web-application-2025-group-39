-- DDL VOOR POSTGRESQL (SCHEMA PUBLIC)

-- 1. COMPANY
CREATE TABLE public.company (
    id_company SERIAL PRIMARY KEY, -- SERIAL: De primaire sleutel is een automatisch oplopende teller (auto-increment).
    company_name VARCHAR NOT NULL
);

-- 2. PROFILE
CREATE TABLE public.profile (
    id_profile SERIAL PRIMARY KEY,
    id_company INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL, -- UNIQUE: Zorgt ervoor dat geen twee profielen hetzelfde e-mailadres kunnen hebben.
    role VARCHAR,
    password_hash VARCHAR NOT NULL,
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_profile_company FOREIGN KEY (id_company)
        REFERENCES public.company (id_company)
        ON DELETE RESTRICT -- RESTRICT: Voorkomt dat een bedrijf wordt verwijderd zolang er nog profielen aan zijn gekoppeld.
);

-- 3. PROJECT
CREATE TABLE public.project (
    id_project SERIAL PRIMARY KEY,
    id_company INTEGER NOT NULL,
    project_name VARCHAR NOT NULL,
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- TtV Schalings limieten (Gebruikt REAL voor nauwkeurigheid)
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
    id_feature VARCHAR PRIMARY KEY, -- VARCHAR PRIMARY KEY: De sleutel is een String (UUID), wat ideaal is voor globaal unieke ID's die niet afhankelijk zijn van de database.
    id_company INTEGER NOT NULL,
    id_project INTEGER NOT NULL,
    
    name_feature VARCHAR NOT NULL,
    description TEXT,
    
    -- Financiële velden
    horizon INTEGER,
    extra_revenue INTEGER,
    -- ... (andere ROI/TTV velden) ...
    
    -- Calculated values
    quality_score REAL, -- REAL: Gebruikt floating-point voor de berekeningen van VECTR/Confidence scores.
    roi_percent REAL,
    ttv_weeks REAL,
    
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_feature_project FOREIGN KEY (id_project)
        REFERENCES public.project (id_project)
        ON DELETE CASCADE -- CASCADE: Als het Project wordt verwijderd, worden alle Features van dat project automatisch verwijderd.
);

-- 5. ROADMAP
CREATE TABLE public.roadmap (
    id_roadmap SERIAL PRIMARY KEY,
    id_project INTEGER NOT NULL,
    
    start_roadmap VARCHAR NOT NULL, -- Opmerking: Blijft VARCHAR (tekst) conform de ORM, maar DATE is technisch beter.
    end_roadmap VARCHAR NOT NULL,
    time_capacity REAL NOT NULL,    -- REAL: Maakt het mogelijk om decimalen (bijv. 2.5 FTE) op te slaan.
    budget_allocation REAL NOT NULL,
    
    createdat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_roadmap_project FOREIGN KEY (id_project)
        REFERENCES public.project (id_project)
        ON DELETE CASCADE -- CASCADE: Als het Project wordt verwijderd, worden alle Roadmaps ook verwijderd.
);

-- 6. MILESTONE
CREATE TABLE public.milestone (
    id_milestone SERIAL PRIMARY KEY,
    id_roadmap INTEGER NOT NULL,
    
    name VARCHAR NOT NULL,
    start_date DATE, -- DATE: Dit veld is correct gedefinieerd als een datumtype.
    end_date DATE,
    goal VARCHAR,
    status VARCHAR,
    
    CONSTRAINT fk_milestone_roadmap FOREIGN KEY (id_roadmap)
        REFERENCES public.roadmap (id_roadmap)
        ON DELETE CASCADE -- CASCADE: Als de Roadmap wordt verwijderd, worden alle Mijlpalen daarbinnen automatisch verwijderd.
);

-- 7. JUNCTION TABLE: MILESTONEFEATURE (M:N tussen Milestone en Features_ideas)
CREATE TABLE public.milestone_features (
    milestone_id INTEGER NOT NULL,
    feature_id VARCHAR NOT NULL,

    PRIMARY KEY (milestone_id, feature_id), -- COMPOSITE PRIMARY KEY: De combinatie van de twee sleutels identificeert elke rij uniek. Hierdoor kunnen we vastleggen dat een specifieke feature hoort bij een specifieke mijlpaal.

    CONSTRAINT fk_mf_milestone FOREIGN KEY (milestone_id)
        REFERENCES public.milestone (id_milestone)
        ON DELETE CASCADE, -- CASCADE: Als een Mijlpaal wordt verwijderd, worden de koppelingen in deze tabel ook verwijderd.

    CONSTRAINT fk_mf_feature FOREIGN KEY (feature_id)
        REFERENCES public.features_ideas (id_feature)
        ON DELETE CASCADE -- CASCADE: Als een Feature wordt verwijderd, wordt de koppeling met de Mijlpaal(en) verwijderd.
);


-- 8. EVIDENCE
CREATE TABLE public.evidence (
    id_evidence SERIAL PRIMARY KEY,
    id_feature VARCHAR NOT NULL,
    id_company INTEGER NOT NULL,
    
    title VARCHAR,
    -- ... (andere velden) ...
    
    old_confidence REAL,
    new_confidence REAL,
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_evidence_feature FOREIGN KEY (id_feature)
        REFERENCES public.features_ideas (id_feature)
        ON DELETE RESTRICT -- RESTRICT: Zorgt voor extra controle; het bewijs moet eerst worden losgekoppeld voordat de feature kan worden verwijderd (hoewel de ORM dit met CASCADE beheert).
);

-- 9. DECISION (met unieke constraint om dubbele stemmen te voorkomen)
CREATE TABLE public.decision (
    id_decision SERIAL PRIMARY KEY,
    id_feature VARCHAR NOT NULL,
    id_profile INTEGER NOT NULL,
    id_company INTEGER NOT NULL,
    
    decision_type VARCHAR(50) NOT NULL,
    reasoning TEXT, -- reasoning is optioneel (nullable=True)
    
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- UNIQUE CONSTRAINT: Zorgt ervoor dat één profiel (id_profile) slechts één beslissing/stem per feature (id_feature) kan geven.
    CONSTRAINT uq_decision_feature_profile UNIQUE (id_feature, id_profile), 
    
    CONSTRAINT fk_decision_feature FOREIGN KEY (id_feature)
        REFERENCES public.features_ideas (id_feature)
        ON DELETE CASCADE,

    CONSTRAINT fk_decision_profile FOREIGN KEY (id_profile)
        REFERENCES public.profile (id_profile)
        ON DELETE CASCADE
);

-- 10. PROJECT CHAT MESSAGE
CREATE TABLE public.project_chat_message (
    id_message SERIAL PRIMARY KEY,
    id_project INTEGER NOT NULL,
    id_profile INTEGER NOT NULL,
    
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chat_project FOREIGN KEY (id_project)
        REFERENCES public.project (id_project)
        ON DELETE CASCADE -- CASCADE: Als een Project wordt verwijderd, wordt de hele chatgeschiedenis ook verwijderd.
);