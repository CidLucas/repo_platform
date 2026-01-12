--
-- PostgreSQL database dump
--

\restrict N4WWai7V4GkGrUA4FLzzFamPpQU6RJ5piNXDtEP0BKA0gOArk7GDUlkvB1bMEbJ

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: tier_cliente_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tier_cliente_enum AS ENUM (
    'FREE',
    'BASIC',
    'PREMIUM',
    'ENTERPRISE',
    'SME'
);


--
-- Name: tipo_cliente_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipo_cliente_enum AS ENUM (
    'B2B',
    'B2C',
    'EXTERNO'
);


--
-- Name: tipofonte; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tipofonte AS ENUM (
    'URL'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: cliente_final; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cliente_final (
    id_externo character varying NOT NULL,
    nome character varying(255),
    metadados json,
    id integer NOT NULL,
    client_id uuid NOT NULL
);


--
-- Name: cliente_final_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cliente_final_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cliente_final_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cliente_final_id_seq OWNED BY public.cliente_final.id;


--
-- Name: cliente_vizu; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cliente_vizu (
    nome_empresa character varying(255) NOT NULL,
    tipo_cliente public.tipo_cliente_enum,
    tier public.tier_cliente_enum,
    id uuid NOT NULL,
    api_key character varying(255)
);


--
-- Name: configuracao_negocio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configuracao_negocio (
    horario_funcionamento json,
    prompt_base character varying,
    ferramenta_rag_habilitada boolean NOT NULL,
    ferramenta_sql_habilitada boolean NOT NULL,
    ferramenta_agendamento_habilitada boolean NOT NULL,
    id integer NOT NULL,
    client_id uuid NOT NULL
);


--
-- Name: configuracao_negocio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.configuracao_negocio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: configuracao_negocio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.configuracao_negocio_id_seq OWNED BY public.configuracao_negocio.id;


--
-- Name: credencial_servico_externo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credencial_servico_externo (
    nome_servico character varying NOT NULL,
    id integer NOT NULL,
    client_id uuid NOT NULL
);


--
-- Name: credencial_servico_externo_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.credencial_servico_externo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credencial_servico_externo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.credencial_servico_externo_id_seq OWNED BY public.credencial_servico_externo.id;


--
-- Name: fonte_de_dados; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fonte_de_dados (
    id integer NOT NULL,
    tipo_fonte public.tipofonte NOT NULL,
    caminho character varying NOT NULL,
    client_id uuid NOT NULL
);


--
-- Name: fonte_de_dados_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.fonte_de_dados_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fonte_de_dados_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.fonte_de_dados_id_seq OWNED BY public.fonte_de_dados.id;


--
-- Name: cliente_final id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_final ALTER COLUMN id SET DEFAULT nextval('public.cliente_final_id_seq'::regclass);


--
-- Name: configuracao_negocio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracao_negocio ALTER COLUMN id SET DEFAULT nextval('public.configuracao_negocio_id_seq'::regclass);


--
-- Name: credencial_servico_externo id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credencial_servico_externo ALTER COLUMN id SET DEFAULT nextval('public.credencial_servico_externo_id_seq'::regclass);


--
-- Name: fonte_de_dados id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fonte_de_dados ALTER COLUMN id SET DEFAULT nextval('public.fonte_de_dados_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: cliente_final cliente_final_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_final
    ADD CONSTRAINT cliente_final_pkey PRIMARY KEY (id);


--
-- Name: cliente_vizu cliente_vizu_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_vizu
    ADD CONSTRAINT cliente_vizu_pkey PRIMARY KEY (id);


--
-- Name: configuracao_negocio configuracao_negocio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracao_negocio
    ADD CONSTRAINT configuracao_negocio_pkey PRIMARY KEY (id);


--
-- Name: credencial_servico_externo credencial_servico_externo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credencial_servico_externo
    ADD CONSTRAINT credencial_servico_externo_pkey PRIMARY KEY (id);


--
-- Name: fonte_de_dados fonte_de_dados_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fonte_de_dados
    ADD CONSTRAINT fonte_de_dados_pkey PRIMARY KEY (id);


--
-- Name: ix_cliente_final_id_externo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cliente_final_id_externo ON public.cliente_final USING btree (id_externo);


--
-- Name: ix_cliente_vizu_api_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_cliente_vizu_api_key ON public.cliente_vizu USING btree (api_key);


--
-- Name: ix_configuracao_negocio_client_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_configuracao_negocio_client_id ON public.configuracao_negocio USING btree (client_id);


--
-- Name: cliente_final cliente_final_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_final
    ADD CONSTRAINT cliente_final_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.cliente_vizu(id);


--
-- Name: configuracao_negocio configuracao_negocio_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracao_negocio
    ADD CONSTRAINT configuracao_negocio_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.cliente_vizu(id);


--
-- Name: credencial_servico_externo credencial_servico_externo_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credencial_servico_externo
    ADD CONSTRAINT credencial_servico_externo_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.cliente_vizu(id);


--
-- Name: fonte_de_dados fonte_de_dados_client_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fonte_de_dados
    ADD CONSTRAINT fonte_de_dados_client_id_fkey FOREIGN KEY (client_id) REFERENCES public.cliente_vizu(id);


--
-- PostgreSQL database dump complete
--

\unrestrict N4WWai7V4GkGrUA4FLzzFamPpQU6RJ5piNXDtEP0BKA0gOArk7GDUlkvB1bMEbJ

