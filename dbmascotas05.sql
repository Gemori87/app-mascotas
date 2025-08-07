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
CREATE DATABASE IF NOT EXISTS `dbmascotas05` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;
USE `dbmascotas05`;

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
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.persona: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `persona` DISABLE KEYS */;
/*!40000 ALTER TABLE `persona` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.perfil
CREATE TABLE IF NOT EXISTS `perfil` (
  `Idperfil` int(11) NOT NULL AUTO_INCREMENT,
  `descripc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`Idperfil`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.perfil: ~4 rows (aproximadamente)
/*!40000 ALTER TABLE `perfil` DISABLE KEYS */;
INSERT IGNORE INTO `perfil` (`Idperfil`, `descripc`, `estado`) VALUES
	(1, 'Administrador', 1),
	(2, 'empleado', 1),
	(3, 'cliente', 1),
	(4, 'Adoptantes', 1);
/*!40000 ALTER TABLE `perfil` ENABLE KEYS */;


-- Volcando estructura para tabla dbmascotas.raza
CREATE TABLE IF NOT EXISTS `raza` (
  `Idraza` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idraza`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
-- Volcando datos para la tabla dbmascotas.raza: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `raza` DISABLE KEYS */;
/*!40000 ALTER TABLE `raza` ENABLE KEYS */;

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
  PRIMARY KEY (`Idmascota`),
  UNIQUE KEY `codigo` (`codigo`),
  KEY `idraza` (`idraza`),
  KEY `idduenio` (`idduenio`),
  CONSTRAINT `mascota_ibfk_1` FOREIGN KEY (`idraza`) REFERENCES `raza` (`Idraza`),
  CONSTRAINT `mascota_ibfk_2` FOREIGN KEY (`idduenio`) REFERENCES `persona` (`Idpersona`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando estructura para tabla dbmascotas.tipoenfermedad
CREATE TABLE IF NOT EXISTS `tipoenfermedad` (
  `Idenfermedad` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `observaciones` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idenfermedad`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.tipoenfermedad: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `tipoenfermedad` DISABLE KEYS */;
/*!40000 ALTER TABLE `tipoenfermedad` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.medicamento
CREATE TABLE IF NOT EXISTS `medicamento` (
  `Idmedicamento` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `presentacion` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idmedicamento`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.medicamento: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `medicamento` DISABLE KEYS */;
/*!40000 ALTER TABLE `medicamento` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.usuario
CREATE TABLE IF NOT EXISTS `usuario` (
  `Idusuario` int(11) NOT NULL AUTO_INCREMENT,
  `nombreu` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `contrasena` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `idperfil` int(11) NOT NULL,
  `Idpersona` int(11) NOT NULL,
  `estado` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`Idusuario`),
  KEY `idperfil` (`idperfil`),
  KEY `Idpersona` (`Idpersona`),
  CONSTRAINT `usuario_ibfk_1` FOREIGN KEY (`idperfil`) REFERENCES `perfil` (`Idperfil`),
  CONSTRAINT `usuario_ibfk_2` FOREIGN KEY (`Idpersona`) REFERENCES `persona` (`Idpersona`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.usuario: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `usuario` DISABLE KEYS */;
/*!40000 ALTER TABLE `usuario` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.reset_tokens
CREATE TABLE IF NOT EXISTS `reset_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `token` varchar(128) NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `usuario` (`Idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla dbmascotas.reset_tokens: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `reset_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `reset_tokens` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.tipoprocedimiento
CREATE TABLE IF NOT EXISTS `tipoprocedimiento` (
  `Idprocedimiento` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`Idprocedimiento`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.tipoprocedimiento: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `tipoprocedimiento` DISABLE KEYS */;
/*!40000 ALTER TABLE `tipoprocedimiento` ENABLE KEYS */;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.mascotaenfermedad: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `mascotaenfermedad` DISABLE KEYS */;
/*!40000 ALTER TABLE `mascotaenfermedad` ENABLE KEYS */;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.cita: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `cita` DISABLE KEYS */;
/*!40000 ALTER TABLE `cita` ENABLE KEYS */;

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
