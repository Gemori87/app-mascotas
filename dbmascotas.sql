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

-- Volcando estructura para tabla dbmascotas.perfil
CREATE TABLE IF NOT EXISTS `perfil` (
  `Idperfil` int(11) NOT NULL AUTO_INCREMENT,
  `descripc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `estado` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`Idperfil`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.perfil: ~3 rows (aproximadamente)
/*!40000 ALTER TABLE `perfil` DISABLE KEYS */;
INSERT IGNORE INTO `perfil` (`Idperfil`, `descripc`, `estado`) VALUES
	(1, 'Administrador', 1),
	(2, 'empleado', 1),
	(3, 'cliente', 1);
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
  PRIMARY KEY (`Idpersona`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.persona: ~4 rows (aproximadamente)
/*!40000 ALTER TABLE `persona` DISABLE KEYS */;
INSERT IGNORE INTO `persona` (`Idpersona`, `nom1`, `nom2`, `apell1`, `apell2`, `direccion`, `tele`, `movil`, `correo`, `fecha_nac`, `estado`) VALUES
	(1, 'Juan', 'David', 'Cardona', 'Osorio', 'Calle falsa 123', '3108757452', '3108757452', 'test1@compumoviljk.com', '1991-01-08', 1),
	(2, 'David', '', 'Osorio', '', 'Calle 9 #11-25 ', '3108757452', '3108757452', 'test2@compumoviljk.com', '1991-08-01', 1),
	(3, 'David', '', 'Osorio', '', 'Calle 9 #11-25 ', '3108757452', '3108757452', 'test3@compumoviljk.com', '1991-08-01', 1),
	(4, 'francisco', 'arley', 'campos', '', 'calle falsa 123', '3108757452', '3108757452', 'campos@compumoviljk.com', '2000-08-01', 1);
/*!40000 ALTER TABLE `persona` ENABLE KEYS */;

-- Volcando estructura para tabla dbmascotas.reset_tokens
CREATE TABLE IF NOT EXISTS `reset_tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `token` varchar(128) NOT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `usuario` (`Idusuario`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=latin1;

-- Volcando datos para la tabla dbmascotas.reset_tokens: ~0 rows (aproximadamente)
/*!40000 ALTER TABLE `reset_tokens` DISABLE KEYS */;
INSERT IGNORE INTO `reset_tokens` (`id`, `user_id`, `token`, `expires_at`) VALUES
	(1, 1, 'SLb4V5OPDAphQWh7yuADsFkqonFNxtbTs14sIczgz2Y', '2025-08-02 01:34:32'),
	(2, 1, 'nsnYV8T0pD22l95c9RMexEy3E0MmY6dlFW_shsvebs0', '2025-08-02 01:34:37'),
	(3, 1, 'YDq55umBUQXVjWwFrdKMW__7eWfJbtIDkZk-d5rY6HQ', '2025-08-02 01:36:47'),
	(4, 1, '2RT7RcMsM-NBZiX4_xWNz5QN3hfTBLfTGsnejTPN-VQ', '2025-08-02 01:36:57'),
	(5, 1, 'LhQbgt4QzjIzZh56nUxVRPB3S_QNHLd7GaLMsTCNUYE', '2025-08-02 01:37:01'),
	(6, 1, 'A3XnT2wOTuEZKm0INUzL9QCjrxzjBmcrwzwethQSjmg', '2025-08-02 01:38:50'),
	(7, 1, 'Oq_Fg_UkVKy1tfE8kUSOm4FoOGFl7bDE5MRH7PTFMyk', '2025-08-02 01:39:00'),
	(8, 1, 'Gdatoquj6PnEMx0ozRAClckLWXrI-LaizWmnBjfRuGE', '2025-08-02 01:40:09'),
	(9, 1, 'DTOebeGSiHur54WlwKukl6y5CHVIRBpmbwNOv8T31lU', '2025-08-02 01:40:16'),
	(10, 1, 'Lo8LkcToT7H0RwjQoOvacLrB5oyJvZQJmpr_sQtQlEw', '2025-08-02 01:42:09'),
	(11, 1, 'pbrjGNGl1julg2ZyHVRYE1e71xNBrt5fa0ff1p3hdnw', '2025-08-02 01:47:08'),
	(12, 1, 'ZGMilwRRreEn7X1P5fY_BrcYc2kFz-55wQaMAeTL0fs', '2025-08-02 01:47:22'),
	(13, 1, '2vznVlb3oF2RfFZF9hjw2GFsHYDpSQtmsncrhfw0JtQ', '2025-08-02 01:51:40');
/*!40000 ALTER TABLE `reset_tokens` ENABLE KEYS */;

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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Volcando datos para la tabla dbmascotas.usuario: ~2 rows (aproximadamente)
/*!40000 ALTER TABLE `usuario` DISABLE KEYS */;
INSERT IGNORE INTO `usuario` (`Idusuario`, `nombreu`, `contrasena`, `idperfil`, `Idpersona`, `estado`) VALUES
	(1, 'Juan20', '202020', 1, 1, 1),
	(2, 'Cardona10', '606060', 2, 2, 1);
/*!40000 ALTER TABLE `usuario` ENABLE KEYS */;

/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
