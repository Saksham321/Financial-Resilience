-- =============================================================================
-- TigerData / TimescaleDB & PostgreSQL Schema Initialization
-- Financial Resilience Engine
-- =============================================================================

-- 1. Enable Required Extensions safely
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- TimescaleDB (if supported by the target PostgreSQL instance)
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
        RAISE NOTICE 'TimescaleDB extension successfully enabled.';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'TimescaleDB extension could not be enabled: %. Standard PostgreSQL time-series partitioning will be used.', SQLERRM;
    END;
END $$;

-- PostGIS (for geographic spending and fraud location analysis)
DO $$
BEGIN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS postgis;
        RAISE NOTICE 'PostGIS extension successfully enabled.';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'PostGIS extension could not be enabled: %. Coordinate calculations will fallback to Haversine formula.', SQLERRM;
    END;
END $$;

-- 2. Create Logical Schemas
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS transactions;
CREATE SCHEMA IF NOT EXISTS shock_mediation;
CREATE SCHEMA IF NOT EXISTS predictive_planning;
CREATE SCHEMA IF NOT EXISTS behavioral_fraud;
CREATE SCHEMA IF NOT EXISTS subscriptions;
CREATE SCHEMA IF NOT EXISTS inflation;
CREATE SCHEMA IF NOT EXISTS expense_pyramid;
CREATE SCHEMA IF NOT EXISTS ai;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path to include core and public
SET search_path TO core, transactions, public;
