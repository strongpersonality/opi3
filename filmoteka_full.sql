--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.24
-- Dumped by pg_dump version 9.6.24

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

DROP DATABASE IF EXISTS filmoteka;
--
-- Name: filmoteka; Type: DATABASE; Schema: -; Owner: -
--

CREATE DATABASE filmoteka WITH TEMPLATE = template0 ENCODING = 'UTF8' LC_COLLATE = 'en_US.UTF-8' LC_CTYPE = 'en_US.UTF-8';


\connect filmoteka

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
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: carriers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.carriers (
    id integer NOT NULL,
    film_id integer NOT NULL,
    type character varying(20) NOT NULL,
    condition character varying(20) DEFAULT 'Хорошее'::character varying NOT NULL,
    status character varying(20) DEFAULT 'Доступен'::character varying NOT NULL,
    date_bought date DEFAULT ('now'::text)::date NOT NULL,
    price numeric(10,2),
    CONSTRAINT carriers_condition_check CHECK (((condition)::text = ANY ((ARRAY['Отличное'::character varying, 'Хорошее'::character varying, 'Удовлетворительное'::character varying, 'Плохое'::character varying, 'Повреждено'::character varying])::text[]))),
    CONSTRAINT carriers_price_check CHECK ((price >= (0)::numeric)),
    CONSTRAINT carriers_status_check CHECK (((status)::text = ANY ((ARRAY['Доступен'::character varying, 'Выдан'::character varying, 'На реставрации'::character varying, 'Списан'::character varying])::text[]))),
    CONSTRAINT carriers_type_check CHECK (((type)::text = ANY ((ARRAY['DVD'::character varying, 'Blu-ray'::character varying, 'Цифровая копия'::character varying])::text[])))
);


--
-- Name: carriers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.carriers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: carriers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.carriers_id_seq OWNED BY public.carriers.id;


--
-- Name: directors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.directors (
    id integer NOT NULL,
    full_name character varying(150) NOT NULL
);


--
-- Name: directors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.directors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: directors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.directors_id_seq OWNED BY public.directors.id;


--
-- Name: film_genres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.film_genres (
    film_id integer NOT NULL,
    genre_id integer NOT NULL
);


--
-- Name: films; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.films (
    id integer NOT NULL,
    localized_name character varying(200) NOT NULL,
    original_name character varying(200),
    year_out smallint,
    director_id integer,
    length_minutes smallint,
    restriction character varying(5),
    description text,
    CONSTRAINT films_length_minutes_check CHECK ((length_minutes > 0)),
    CONSTRAINT films_restriction_check CHECK (((restriction)::text = ANY ((ARRAY['0+'::character varying, '6+'::character varying, '12+'::character varying, '16+'::character varying, '18+'::character varying])::text[]))),
    CONSTRAINT films_year_out_check CHECK (((year_out >= 1895) AND (year_out <= 2030)))
);


--
-- Name: films_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.films_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: films_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.films_id_seq OWNED BY public.films.id;


--
-- Name: genres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.genres (
    id integer NOT NULL,
    name character varying(64) NOT NULL
);


--
-- Name: genres_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.genres_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: genres_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.genres_id_seq OWNED BY public.genres.id;


--
-- Name: issues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.issues (
    id integer NOT NULL,
    reader_id integer NOT NULL,
    carrier_id integer NOT NULL,
    given_at date DEFAULT ('now'::text)::date NOT NULL,
    planned_return date NOT NULL,
    real_return date,
    status character varying(20) DEFAULT 'Активна'::character varying NOT NULL,
    CONSTRAINT issues_check CHECK ((planned_return > given_at)),
    CONSTRAINT issues_status_check CHECK (((status)::text = ANY ((ARRAY['Активна'::character varying, 'Завершена'::character varying, 'Просрочена'::character varying])::text[])))
);


--
-- Name: issues_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.issues_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: issues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.issues_id_seq OWNED BY public.issues.id;


--
-- Name: readers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.readers (
    id integer NOT NULL,
    fio character varying(150) NOT NULL,
    phone character varying(20),
    registration_date date DEFAULT ('now'::text)::date NOT NULL,
    status character varying(20) DEFAULT 'Активен'::character varying NOT NULL,
    permission_for_own_data boolean DEFAULT false NOT NULL,
    CONSTRAINT readers_status_check CHECK (((status)::text = ANY ((ARRAY['Активен'::character varying, 'Заблокирован'::character varying, 'Архив'::character varying])::text[])))
);


--
-- Name: readers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.readers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: readers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.readers_id_seq OWNED BY public.readers.id;


--
-- Name: reservations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reservations (
    id integer NOT NULL,
    reader_id integer NOT NULL,
    film_id integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    period daterange NOT NULL,
    status character varying(20) DEFAULT 'Подтверждено'::character varying NOT NULL,
    CONSTRAINT reservations_status_check CHECK (((status)::text = ANY ((ARRAY['Подтверждено'::character varying, 'Отменено'::character varying, 'Истекло'::character varying])::text[])))
);


--
-- Name: reservations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reservations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reservations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reservations_id_seq OWNED BY public.reservations.id;


--
-- Name: carriers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carriers ALTER COLUMN id SET DEFAULT nextval('public.carriers_id_seq'::regclass);


--
-- Name: directors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.directors ALTER COLUMN id SET DEFAULT nextval('public.directors_id_seq'::regclass);


--
-- Name: films id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.films ALTER COLUMN id SET DEFAULT nextval('public.films_id_seq'::regclass);


--
-- Name: genres id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.genres ALTER COLUMN id SET DEFAULT nextval('public.genres_id_seq'::regclass);


--
-- Name: issues id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.issues ALTER COLUMN id SET DEFAULT nextval('public.issues_id_seq'::regclass);


--
-- Name: readers id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.readers ALTER COLUMN id SET DEFAULT nextval('public.readers_id_seq'::regclass);


--
-- Name: reservations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations ALTER COLUMN id SET DEFAULT nextval('public.reservations_id_seq'::regclass);


--
-- Data for Name: carriers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.carriers (id, film_id, type, condition, status, date_bought, price) FROM stdin;
1	1	DVD	Хорошее	Доступен	2024-01-10	350.00
2	1	Blu-ray	Отличное	Доступен	2024-01-10	890.00
3	2	Цифровая копия	Отличное	Доступен	2024-03-20	0.00
4	3	DVD	Повреждено	На реставрации	2023-11-05	0.00
5	4	Blu-ray	Хорошее	Выдан	2024-02-14	950.00
6	5	DVD	Удовлетворительное	Доступен	2023-09-30	200.00
\.


--
-- Name: carriers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.carriers_id_seq', 6, true);


--
-- Data for Name: directors; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.directors (id, full_name) FROM stdin;
1	Квентин Тарантино
2	Кристофер Нолан
3	Стэнли Кубрик
4	Питер Джексон
5	Гай Ричи
\.


--
-- Name: directors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.directors_id_seq', 5, true);


--
-- Data for Name: film_genres; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.film_genres (film_id, genre_id) FROM stdin;
1	1
1	3
1	7
2	3
2	4
3	1
3	6
4	3
4	4
4	1
5	1
5	3
5	7
\.


--
-- Data for Name: films; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.films (id, localized_name, original_name, year_out, director_id, length_minutes, restriction, description) FROM stdin;
1	Криминальное чтиво	Pulp Fiction	1994	1	154	18+	Два гангстера в Лос-Анджелесе.
2	Начало	Inception	2010	2	148	12+	Вор, способный проникать в сны.
3	Сияние	The Shining	1980	3	146	16+	Писатель-алкоголик зимует в жутком отеле.
4	Властелин колец: Братство Кольца	The Lord of the Rings: The Fellowship of the Ring	2001	4	178	12+	Хоббит Фродо отправляется уничтожить Кольцо Всевластья.
5	Отступники	The Departed	2006	5	151	18+	Полицейский и мафиози внедряются друг в друга.
\.


--
-- Name: films_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.films_id_seq', 5, true);


--
-- Data for Name: genres; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.genres (id, name) FROM stdin;
1	Драма
2	Комедия
3	Боевик
4	Фантастика
5	Мультфильм
6	Триллер
7	Детектив
\.


--
-- Name: genres_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.genres_id_seq', 7, true);


--
-- Data for Name: issues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.issues (id, reader_id, carrier_id, given_at, planned_return, real_return, status) FROM stdin;
1	1	1	2025-11-28	2025-12-12	\N	Активна
2	2	5	2025-11-25	2025-12-09	\N	Активна
\.


--
-- Name: issues_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.issues_id_seq', 2, true);


--
-- Data for Name: readers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.readers (id, fio, phone, registration_date, status, permission_for_own_data) FROM stdin;
1	Иванов Иван Иванович	+7 (999) 123-45-67	2024-05-01	Активен	t
2	Петрова Мария Степановна	+7 (888) 765-43-21	2024-06-12	Активен	f
3	Сидоров Алексей Владимирович	+7 (777) 999-88-77	2023-12-03	Заблокирован	t
\.


--
-- Name: readers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.readers_id_seq', 3, true);


--
-- Data for Name: reservations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.reservations (id, reader_id, film_id, created_at, period, status) FROM stdin;
1	1	2	2025-11-29 10:59:13.529766	[2025-12-01,2025-12-08)	Подтверждено
2	2	4	2025-11-29 10:59:13.529766	[2025-12-05,2025-12-12)	Подтверждено
3	1	5	2025-11-29 10:59:13.529766	[2025-11-20,2025-11-27)	Истекло
\.


--
-- Name: reservations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.reservations_id_seq', 3, true);


--
-- Name: carriers carriers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carriers
    ADD CONSTRAINT carriers_pkey PRIMARY KEY (id);


--
-- Name: directors directors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.directors
    ADD CONSTRAINT directors_pkey PRIMARY KEY (id);


--
-- Name: film_genres film_genres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.film_genres
    ADD CONSTRAINT film_genres_pkey PRIMARY KEY (film_id, genre_id);


--
-- Name: films films_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.films
    ADD CONSTRAINT films_pkey PRIMARY KEY (id);


--
-- Name: genres genres_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.genres
    ADD CONSTRAINT genres_name_key UNIQUE (name);


--
-- Name: genres genres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.genres
    ADD CONSTRAINT genres_pkey PRIMARY KEY (id);


--
-- Name: issues issues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.issues
    ADD CONSTRAINT issues_pkey PRIMARY KEY (id);


--
-- Name: readers readers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.readers
    ADD CONSTRAINT readers_pkey PRIMARY KEY (id);


--
-- Name: reservations reservations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_pkey PRIMARY KEY (id);


--
-- Name: carriers carriers_film_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.carriers
    ADD CONSTRAINT carriers_film_id_fkey FOREIGN KEY (film_id) REFERENCES public.films(id) ON DELETE CASCADE;


--
-- Name: film_genres film_genres_film_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.film_genres
    ADD CONSTRAINT film_genres_film_id_fkey FOREIGN KEY (film_id) REFERENCES public.films(id) ON DELETE CASCADE;


--
-- Name: film_genres film_genres_genre_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.film_genres
    ADD CONSTRAINT film_genres_genre_id_fkey FOREIGN KEY (genre_id) REFERENCES public.genres(id) ON DELETE CASCADE;


--
-- Name: films films_director_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.films
    ADD CONSTRAINT films_director_id_fkey FOREIGN KEY (director_id) REFERENCES public.directors(id) ON DELETE SET NULL;


--
-- Name: issues issues_carrier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.issues
    ADD CONSTRAINT issues_carrier_id_fkey FOREIGN KEY (carrier_id) REFERENCES public.carriers(id) ON DELETE RESTRICT;


--
-- Name: issues issues_reader_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.issues
    ADD CONSTRAINT issues_reader_id_fkey FOREIGN KEY (reader_id) REFERENCES public.readers(id) ON DELETE RESTRICT;


--
-- Name: reservations reservations_film_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_film_id_fkey FOREIGN KEY (film_id) REFERENCES public.films(id) ON DELETE RESTRICT;


--
-- Name: reservations reservations_reader_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reservations
    ADD CONSTRAINT reservations_reader_id_fkey FOREIGN KEY (reader_id) REFERENCES public.readers(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

