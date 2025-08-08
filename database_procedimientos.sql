

-- Tabla de tipos de procedimientos (catálogo)
CREATE TABLE IF NOT EXISTS tipoprocedimiento (
    Idprocedimiento INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    precio DECIMAL(10,2),
    estado BOOLEAN DEFAULT TRUE,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- Tabla de mascotas (si no existe)
CREATE TABLE IF NOT EXISTS mascota (
    Idmascota INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    especie VARCHAR(50) NOT NULL,
    raza VARCHAR(100),
    fecha_nacimiento DATE,
    sexo ENUM('Macho', 'Hembra'),
    color VARCHAR(50),
    peso DECIMAL(5,2),
    iddueno INT NOT NULL,
    estado BOOLEAN DEFAULT TRUE,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_dueno (iddueno),
    CONSTRAINT fk_mascota_dueno FOREIGN KEY (iddueno) REFERENCES persona (Idpersona)
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- Tabla de procedimientos aplicados a mascotas (ya existe según tu definición)
CREATE TABLE IF NOT EXISTS procedimientomascota (
    Idregistro INT AUTO_INCREMENT PRIMARY KEY,
    idmascota INT NOT NULL,
    idprocedimiento INT NOT NULL,
    fecha DATE NOT NULL,
    observacion VARCHAR(255) NULL DEFAULT NULL,
    idveterinario INT NULL DEFAULT NULL,
    estado TINYINT(1) NULL DEFAULT 1,
    INDEX idmascota (idmascota),
    INDEX idprocedimiento (idprocedimiento),
    INDEX idveterinario (idveterinario),
    CONSTRAINT procedimientomascota_ibfk_1 FOREIGN KEY (idmascota) REFERENCES mascota (Idmascota),
    CONSTRAINT procedimientomascota_ibfk_2 FOREIGN KEY (idprocedimiento) REFERENCES tipoprocedimiento (Idprocedimiento),
    CONSTRAINT procedimientomascota_ibfk_3 FOREIGN KEY (idveterinario) REFERENCES persona (Idpersona)
) ENGINE=InnoDB COLLATE=utf8mb4_unicode_ci;

-- Insertar tipos de procedimientos de ejemplo
INSERT IGNORE INTO tipoprocedimiento (nombre, descripcion, precio, estado) VALUES
('Consulta General', 'Consulta médica veterinaria general para revisión de rutina', 35.00, TRUE),
('Vacunación Antirrábica', 'Aplicación de vacuna antirrábica para perros y gatos', 25.00, TRUE),
('Vacunación Triple/Quíntuple', 'Vacunación múltiple contra enfermedades comunes', 30.00, TRUE),
('Desparasitación Interna', 'Tratamiento antiparasitario interno para mascotas', 20.00, TRUE),
('Desparasitación Externa', 'Tratamiento contra pulgas, garrapatas y otros parásitos externos', 18.00, TRUE),
('Limpieza Dental', 'Limpieza dental profesional para mascotas', 80.00, TRUE),
('Cirugía Menor', 'Procedimientos quirúrgicos menores (suturas, extracciones)', 150.00, TRUE),
('Esterilización/Castración', 'Procedimiento de esterilización o castración', 200.00, TRUE),
('Análisis de Sangre', 'Examen de laboratorio - análisis sanguíneo completo', 45.00, TRUE),
('Radiografía', 'Estudio radiológico para diagnóstico', 60.00, TRUE),
('Ecografía', 'Estudio ecográfico para diagnóstico', 70.00, TRUE),
('Curación de Heridas', 'Tratamiento y curación de heridas menores', 25.00, TRUE),
('Control Post-Operatorio', 'Revisión y seguimiento después de cirugías', 30.00, TRUE),
('Corte de Uñas', 'Corte profesional de uñas', 10.00, TRUE),
('Baño y Peluquería', 'Servicio de higiene y estética para mascotas', 40.00, TRUE);

-- Insertar mascotas de ejemplo (opcional)
INSERT IGNORE INTO mascota (nombre, especie, raza, fecha_nacimiento, sexo, color, peso, iddueno, estado) VALUES
('Max', 'Perro', 'Labrador', '2020-03-15', 'Macho', 'Dorado', 25.50, 1, TRUE),
('Luna', 'Gato', 'Persa', '2021-07-22', 'Hembra', 'Blanco', 4.20, 1, TRUE),
('Rocky', 'Perro', 'Pastor Alemán', '2019-11-08', 'Macho', 'Negro y Marrón', 32.00, 2, TRUE),
('Mimi', 'Gato', 'Siamés', '2022-01-10', 'Hembra', 'Crema', 3.80, 2, TRUE);

-- Insertar algunos registros de procedimientos de ejemplo (opcional)
INSERT IGNORE INTO procedimientomascota (idmascota, idprocedimiento, fecha, observacion, idveterinario, estado) VALUES
(1, 1, '2024-12-01', 'Revisión general normal, mascota en buen estado', 1, TRUE),
(1, 2, '2024-12-01', 'Vacuna antirrábica aplicada sin complicaciones', 1, TRUE),
(2, 1, '2024-12-02', 'Consulta por pérdida de apetito, se receta tratamiento', 1, TRUE),
(3, 4, '2024-12-03', 'Desparasitación interna de rutina', 1, TRUE),
(4, 14, '2024-12-04', 'Corte de uñas regular, comportamiento tranquilo', 1, TRUE);
