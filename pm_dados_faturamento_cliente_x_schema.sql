--
-- PostgreSQL database dump
--

\restrict LTG1XA0nsRasRpaMWGfiyWmpuuqORVWKR1HH3dk6IgEWPFhqruSSsgznxUd5fhm

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: pm_dados_faturamento_cliente_x; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.pm_dados_faturamento_cliente_x (
    order_id text,
    data_transacao timestamp without time zone,
    quantidade text,
    valor_unitario text,
    valor_total_emitter text,
    valor_total_receiver text,
    emitter_nome text,
    emitter_cidade text,
    emitter_estado text,
    receiver_nome text,
    receiver_cidade text,
    raw_product_description text,
    raw_product_category text,
    raw_ncm text,
    raw_cfop text,
    emitter_cnpj text,
    emitter_telefone text,
    receiver_cnpj text,
    receiver_telefone text,
    receiver_estado text
);


ALTER TABLE public.pm_dados_faturamento_cliente_x OWNER TO "user";

--
-- PostgreSQL database dump complete
--

\unrestrict LTG1XA0nsRasRpaMWGfiyWmpuuqORVWKR1HH3dk6IgEWPFhqruSSsgznxUd5fhm

