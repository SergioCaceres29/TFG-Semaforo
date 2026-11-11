-- Esquema de la base (docs/specs/diseno.md §5). No modificar sin aprobación.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS video (
    id_video        INTEGER PRIMARY KEY,
    nombre_archivo  TEXT NOT NULL,
    duracion_seg    REAL NOT NULL,
    fps             REAL NOT NULL,
    resolucion      TEXT NOT NULL,          -- ej. '1920x1080'
    fecha_captura   TEXT
);

CREATE TABLE IF NOT EXISTS zona_virtual (
    id_zona         INTEGER PRIMARY KEY,
    id_video        INTEGER NOT NULL REFERENCES video(id_video),
    nombre_carril   TEXT NOT NULL,
    vertices        TEXT NOT NULL,          -- JSON: [[x, y], ...] con al menos 3 puntos
    UNIQUE (id_video, nombre_carril)
);

CREATE TABLE IF NOT EXISTS clase_vehiculo (
    id_clase        INTEGER PRIMARY KEY,
    descripcion     TEXT NOT NULL UNIQUE    -- 'auto', 'moto', 'camion'
);

CREATE TABLE IF NOT EXISTS ejecucion (
    id_ejecucion     INTEGER PRIMARY KEY,
    fecha_hora       TEXT NOT NULL,
    version_modelo   TEXT NOT NULL,
    umbral_demanda   INTEGER NOT NULL CHECK (umbral_demanda >= 0),
    umbral_confianza REAL NOT NULL CHECK (umbral_confianza BETWEEN 0 AND 1),
    intervalo_seg    INTEGER NOT NULL CHECK (intervalo_seg > 0),
    verde_min        INTEGER NOT NULL CHECK (verde_min > 0),
    verde_max        INTEGER NOT NULL CHECK (verde_max >= verde_min),
    amarillo         INTEGER NOT NULL CHECK (amarillo > 0),
    estado           TEXT NOT NULL CHECK (estado IN ('Creada','EnEjecucion','Pausada','Finalizada','Abortada'))
);

CREATE TABLE IF NOT EXISTS ejecucion_video (        -- los 3 videos de una ejecución, uno por carril
    id_ejecucion     INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_video         INTEGER NOT NULL REFERENCES video(id_video),
    posicion         INTEGER NOT NULL CHECK (posicion BETWEEN 1 AND 3),
    PRIMARY KEY (id_ejecucion, posicion)
);

CREATE TABLE IF NOT EXISTS conteo (                 -- solo inserción (RNF-09)
    id_conteo        INTEGER PRIMARY KEY,
    id_ejecucion     INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_zona          INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    id_clase         INTEGER NOT NULL REFERENCES clase_vehiculo(id_clase),
    cantidad         INTEGER NOT NULL CHECK (cantidad >= 0),
    intervalo_inicio REAL NOT NULL,
    intervalo_fin    REAL NOT NULL CHECK (intervalo_fin > intervalo_inicio)
);

CREATE TABLE IF NOT EXISTS evento_fase (            -- solo inserción (RNF-09)
    id_evento        INTEGER PRIMARY KEY,
    id_ejecucion     INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_zona          INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    estado           TEXT NOT NULL CHECK (estado IN ('VERDE','AMARILLO','ROJO')),
    marca_tiempo     REAL NOT NULL,
    duracion         INTEGER NOT NULL CHECK (duracion >= 0),
    demanda_asociada INTEGER NOT NULL CHECK (demanda_asociada >= 0)
);

CREATE TABLE IF NOT EXISTS conteo_manual (
    id_conteo_manual    INTEGER PRIMARY KEY,
    id_video            INTEGER NOT NULL REFERENCES video(id_video),
    id_zona             INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    id_clase            INTEGER NOT NULL REFERENCES clase_vehiculo(id_clase),
    intervalo_inicio    REAL NOT NULL,
    intervalo_fin       REAL NOT NULL CHECK (intervalo_fin > intervalo_inicio),
    cantidad_referencia INTEGER NOT NULL CHECK (cantidad_referencia >= 0)
);

CREATE TABLE IF NOT EXISTS metrica_validacion (
    id_metrica    INTEGER PRIMARY KEY,
    id_ejecucion  INTEGER NOT NULL REFERENCES ejecucion(id_ejecucion),
    id_zona       INTEGER NOT NULL REFERENCES zona_virtual(id_zona),
    id_clase      INTEGER NOT NULL REFERENCES clase_vehiculo(id_clase),
    precision     REAL NOT NULL,     -- (1 - Σ|Ca - Cm| / ΣCm) × 100
    error_conteo  REAL NOT NULL      -- Σ|Ca - Cm|
);

-- RNF-09: bloqueo de UPDATE y DELETE en tablas históricas
CREATE TRIGGER IF NOT EXISTS conteo_sin_update BEFORE UPDATE ON conteo
BEGIN SELECT RAISE(ABORT, 'conteo es de solo insercion (RNF-09)'); END;
CREATE TRIGGER IF NOT EXISTS conteo_sin_delete BEFORE DELETE ON conteo
BEGIN SELECT RAISE(ABORT, 'conteo es de solo insercion (RNF-09)'); END;
CREATE TRIGGER IF NOT EXISTS evento_sin_update BEFORE UPDATE ON evento_fase
BEGIN SELECT RAISE(ABORT, 'evento_fase es de solo insercion (RNF-09)'); END;
CREATE TRIGGER IF NOT EXISTS evento_sin_delete BEFORE DELETE ON evento_fase
BEGIN SELECT RAISE(ABORT, 'evento_fase es de solo insercion (RNF-09)'); END;

INSERT OR IGNORE INTO clase_vehiculo (id_clase, descripcion) VALUES (1,'auto'), (2,'moto'), (3,'camion');
