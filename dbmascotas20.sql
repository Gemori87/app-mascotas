-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Versión del servidor:         10.2.3-MariaDB-log - mariadb.org binary distribution
-- SO del servidor:              Win32
-- HeidiSQL Versión:             9.4.0.5125
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;


-- Volcando estructura de base de datos para dbmascotas
CREATE DATABASE IF NOT EXISTS `dbmascotas` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;
USE `dbmascotas`;

-- Volcando estructura para tabla dbmascotas.cita
CREATE TABLE IF NOT EXISTS `cita` (
  `Idcita` int(11) NOT NULL AUTO_INCREMENT,
  `idmascota` int(11) NOT NULL,
  `idduenio` int(11) NOT NULL,
  `idveterinario` int(11) NOT NULL,
  `fecha` datetime NOT NULL,
  `motivo` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idcita`),
  KEY `idmascota` (`idmascota`),
  KEY `idduenio` (`idduenio`),
  KEY `idveterinario` (`idveterinario`),
  CONSTRAINT `cita_ibfk_1` FOREIGN KEY (`idmascota`) REFERENCES `mascota` (`Idmascota`),
  CONSTRAINT `cita_ibfk_2` FOREIGN KEY (`idduenio`) REFERENCES `persona` (`Idpersona`),
  CONSTRAINT `cita_ibfk_3` FOREIGN KEY (`idveterinario`) REFERENCES `persona` (`Idpersona`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.cita: ~1 rows (aproximadamente)
/*!40000 ALTER TABLE `cita` DISABLE KEYS */;
INSERT IGNORE INTO `cita` (`Idcita`, `idmascota`, `idduenio`, `idveterinario`, `fecha`, `motivo`, `estado`) VALUES
	(1, 1, 1, 1, '2025-08-08 07:00:00', 'vacunacion para max ', 1);
/*!40000 ALTER TABLE `cita` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.mascota
CREATE TABLE IF NOT EXISTS `mascota` (
  `Idmascota` int(11) NOT NULL AUTO_INCREMENT,
  `codigo` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fecha_nac` date DEFAULT NULL,
  `caracteristicas` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  `idraza` int(11) DEFAULT NULL,
  `idduenio` int(11) NOT NULL,
  `idveterinario` int(11) DEFAULT NULL,
  PRIMARY KEY (`Idmascota`),
  UNIQUE KEY `codigo` (`codigo`),
  KEY `idraza` (`idraza`),
  KEY `idduenio` (`idduenio`),
  CONSTRAINT `mascota_ibfk_1` FOREIGN KEY (`idraza`) REFERENCES `raza` (`Idraza`),
  CONSTRAINT `mascota_ibfk_2` FOREIGN KEY (`idduenio`) REFERENCES `persona` (`Idpersona`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.mascota: ~1 rows (aproximadamente)
/*!40000 ALTER TABLE `mascota` DISABLE KEYS */;
INSERT IGNORE INTO `mascota` (`Idmascota`, `codigo`, `nombre`, `fecha_nac`, `caracteristicas`, `estado`, `idraza`, `idduenio`, `idveterinario`) VALUES
	(1, '01', 'max', '2024-07-07', '', 1, 1, 1, 1);
/*!40000 ALTER TABLE `mascota` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.mascotaenfermedad
CREATE TABLE IF NOT EXISTS `mascotaenfermedad` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `idmascota` int(11) NOT NULL,
  `idenfermedad` int(11) NOT NULL,
  `fecha` date DEFAULT NULL,
  `observacion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idmascota` (`idmascota`),
  KEY `idenfermedad` (`idenfermedad`),
  CONSTRAINT `mascotaenfermedad_ibfk_1` FOREIGN KEY (`idmascota`) REFERENCES `mascota` (`Idmascota`),
  CONSTRAINT `mascotaenfermedad_ibfk_2` FOREIGN KEY (`idenfermedad`) REFERENCES `tipoenfermedad` (`Idenfermedad`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.mascotaenfermedad: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `mascotaenfermedad` DISABLE KEYS */;
INSERT IGNORE INTO `mascotaenfermedad` (`id`, `idmascota`, `idenfermedad`, `fecha`, `observacion`) VALUES
	(1, 1, 1, '2025-08-07', NULL);
/*!40000 ALTER TABLE `mascotaenfermedad` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.mascotamedicamento
CREATE TABLE IF NOT EXISTS `mascotamedicamento` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `idmascota` int(11) NOT NULL,
  `idmedicamento` int(11) NOT NULL,
  `fecha` date DEFAULT NULL,
  `observacion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idmascota` (`idmascota`),
  KEY `idmedicamento` (`idmedicamento`),
  CONSTRAINT `mascotamedicamento_ibfk_1` FOREIGN KEY (`idmascota`) REFERENCES `mascota` (`Idmascota`),
  CONSTRAINT `mascotamedicamento_ibfk_2` FOREIGN KEY (`idmedicamento`) REFERENCES `medicamento` (`Idmedicamento`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.mascotamedicamento: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `mascotamedicamento` DISABLE KEYS */;
/*!40000 ALTER TABLE `mascotamedicamento` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.medicamento
CREATE TABLE IF NOT EXISTS `medicamento` (
  `Idmedicamento` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `presentacion` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idmedicamento`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.medicamento: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `medicamento` DISABLE KEYS */;
INSERT IGNORE INTO `medicamento` (`Idmedicamento`, `nombre`, `presentacion`, `estado`) VALUES
	(1, 'moxi', '20ml', 1);
/*!40000 ALTER TABLE `medicamento` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.perfil
CREATE TABLE IF NOT EXISTS `perfil` (
  `Idperfil` int(11) NOT NULL AUTO_INCREMENT,
  `descripc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`Idperfil`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.perfil: ~3 rows (aproximadamente)
/*!40000 ALTER TABLE `perfil` DISABLE KEYS */;
INSERT IGNORE INTO `perfil` (`Idperfil`, `descripc`, `estado`) VALUES
	(1, 'Administrador', 1),
	(2, 'empleado', 1),
	(3, 'cliente', 1),
	(4, 'Adoptantes', 1),
	(5, 'medico', 1);
/*!40000 ALTER TABLE `perfil` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.persona
CREATE TABLE IF NOT EXISTS `persona` (
  `Idpersona` int(11) NOT NULL AUTO_INCREMENT,
  `nom1` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nom2` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `apell1` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `apell2` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `direccion` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tele` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `movil` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `correo` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fecha_nac` date DEFAULT NULL,
  `estado` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`Idpersona`),
  UNIQUE KEY `correo` (`correo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.persona: ~5 rows (aproximadamente)
/*!40000 ALTER TABLE `persona` DISABLE KEYS */;
INSERT IGNORE INTO `persona` (`Idpersona`, `nom1`, `nom2`, `apell1`, `apell2`, `direccion`, `tele`, `movil`, `correo`, `fecha_nac`, `estado`) VALUES
	(1, 'Juan', 'David', 'Cardona', 'Osorio', 'calle falsa 123', '3108757452', '3108757452', 'test@compumoviljk.com', '1991-08-01', 1),
	(2, 'Diana', '', 'echeverria', '', 'calle falsa 123', '3108757452', '3108757452', 'test1@compumoviljk.com', '1991-10-25', 1),
	(3, 'valeria', '', 'perez', '', 'calle falsa 123', '3108757452', '3108757452', 'test10@compumoviljk.com', '1991-12-01', 1),
	(4, 'pepito', '', 'cardona', '', 'calle falsa 123', '3108757452', '', 'test111011@compumoviljk.com', '2000-01-01', 1),
	(5, 'Ana', '', 'cardona', '', 'calle falsa 123', '3108757452', '', 'campos@compumoviljk.com', '2000-01-01', 1);
/*!40000 ALTER TABLE `persona` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.procedimientomascota
CREATE TABLE IF NOT EXISTS `procedimientomascota` (
  `Idregistro` int(11) NOT NULL AUTO_INCREMENT,
  `idmascota` int(11) NOT NULL,
  `idprocedimiento` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `observacion` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idveterinario` int(11) DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idregistro`),
  KEY `idmascota` (`idmascota`),
  KEY `idprocedimiento` (`idprocedimiento`),
  KEY `idveterinario` (`idveterinario`),
  CONSTRAINT `procedimientomascota_ibfk_1` FOREIGN KEY (`idmascota`) REFERENCES `mascota` (`Idmascota`),
  CONSTRAINT `procedimientomascota_ibfk_2` FOREIGN KEY (`idprocedimiento`) REFERENCES `tipoprocedimiento` (`Idprocedimiento`),
  CONSTRAINT `procedimientomascota_ibfk_3` FOREIGN KEY (`idveterinario`) REFERENCES `persona` (`Idpersona`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.procedimientomascota: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `procedimientomascota` DISABLE KEYS */;
/*!40000 ALTER TABLE `procedimientomascota` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.raza
CREATE TABLE IF NOT EXISTS `raza` (
  `Idraza` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idraza`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.raza: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `raza` DISABLE KEYS */;
INSERT IGNORE INTO `raza` (`Idraza`, `nombre`, `estado`) VALUES
	(1, 'Pastor aleman ', 1);
/*!40000 ALTER TABLE `raza` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.reset_tokens
CREATE TABLE IF NOT EXISTS `reset_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `token` varchar(128) NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `usuario` (`Idusuario`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla dbmascotas.reset_tokens: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `reset_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `reset_tokens` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.tipoenfermedad
CREATE TABLE IF NOT EXISTS `tipoenfermedad` (
  `Idenfermedad` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `observaciones` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idenfermedad`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.tipoenfermedad: ~2 rows (aproximadamente)
/*!40000 ALTER TABLE `tipoenfermedad` DISABLE KEYS */;
INSERT IGNORE INTO `tipoenfermedad` (`Idenfermedad`, `nombre`, `observaciones`, `estado`) VALUES
	(1, 'Moquillo', NULL, 1),
	(2, 'Sarna', NULL, 1),
	(3, 'Parvovirosis', 'dfhsdfghdfghj', 0);
/*!40000 ALTER TABLE `tipoenfermedad` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.tipoprocedimiento
CREATE TABLE IF NOT EXISTS `tipoprocedimiento` (
  `Idprocedimiento` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idprocedimiento`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.tipoprocedimiento: ~2 rows (aproximadamente)
/*!40000 ALTER TABLE `tipoprocedimiento` DISABLE KEYS */;
INSERT IGNORE INTO `tipoprocedimiento` (`Idprocedimiento`, `nombre`, `estado`) VALUES
	(1, 'ecografia', 0),
	(2, 'Cirugia', 1),
	(3, 'Vacuna', 1);
/*!40000 ALTER TABLE `tipoprocedimiento` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.usuario
CREATE TABLE IF NOT EXISTS `usuario` (
  `Idusuario` int(11) NOT NULL AUTO_INCREMENT,
  `nombreu` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contrasena` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `idperfil` int(11) NOT NULL,
  `Idpersona` int(11) NOT NULL,
  `estado` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`Idusuario`),
  UNIQUE KEY `uq_usuario_nombreu` (`nombreu`),
  KEY `idperfil` (`idperfil`),
  KEY `Idpersona` (`Idpersona`),
  CONSTRAINT `usuario_ibfk_1` FOREIGN KEY (`idperfil`) REFERENCES `perfil` (`Idperfil`),
  CONSTRAINT `usuario_ibfk_2` FOREIGN KEY (`Idpersona`) REFERENCES `persona` (`Idpersona`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.usuario: ~3 rows (aproximadamente)
/*!40000 ALTER TABLE `usuario` DISABLE KEYS */;
INSERT IGNORE INTO `usuario` (`Idusuario`, `nombreu`, `contrasena`, `idperfil`, `Idpersona`, `estado`) VALUES
	(1, 'Juan201', '202020', 1, 1, 1),
	(2, 'Juan20', '202020', 2, 2, 1),
	(4, 'Valeria', '202020', 1, 3, 1);
/*!40000 ALTER TABLE `usuario` ENABLE KEYS */;

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
