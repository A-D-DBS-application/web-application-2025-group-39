CREATE TABLE public.company (
    id_company   SERIAL PRIMARY KEY,
    company_name VARCHAR NOT NULL
);

CREATE TABLE public.profile (
    id_profile    SERIAL PRIMARY KEY,
    name          VARCHAR NOT NULL,
    email         VARCHAR,
    role          VARCHAR,
    password_hash VARCHAR NOT NULL,
    id_company    INTEGER NOT NULL,
    createdat     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_profile_company
        FOREIGN KEY (id_company)
        REFERENCES public.company (id_company)
);
