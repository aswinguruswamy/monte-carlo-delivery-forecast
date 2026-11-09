-- Made-up mini dump in the shape of TAWOS.sql (MCF-28). No real data.
DROP TABLE IF EXISTS `Issue`;
CREATE TABLE `Issue` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Issue_Key` varchar(512) DEFAULT NULL,
  `Title` varchar(512) DEFAULT NULL,
  `Description` mediumtext,
  `Type` varchar(128) DEFAULT NULL,
  `Status` varchar(128) DEFAULT NULL,
  `Resolution` varchar(128) DEFAULT NULL,
  `Resolution_Date` datetime DEFAULT NULL,
  `Story_Point` double DEFAULT NULL,
  `Creator_ID` int DEFAULT NULL,
  `Project_ID` int DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
LOCK TABLES `Issue` WRITE;
INSERT INTO `Issue` VALUES (1,'AA-1','Secret title, with (brackets)','It\'s a \"quote\", and a \\ slash\nnew line','Story','Closed','Fixed','2026-01-05 10:00:00',3,77,1),(2,'AA-2','T2','D2','Bug','Closed','Won\'t Fix','2026-01-06 11:00:00',NULL,78,1);
INSERT INTO `Issue` VALUES (3,'BB-1','T3',NULL,'Sub-task','Open',NULL,NULL,1.5,79,2),(4,'BB-2','x),(5,\'fake\'','D4','Epic','Resolved','Done','2026-02-01 00:00:00',8,80,2);
UNLOCK TABLES;
DROP TABLE IF EXISTS `Project`;
CREATE TABLE `Project` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Project_Key` varchar(128) DEFAULT NULL,
  `Name` varchar(512) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
LOCK TABLES `Project` WRITE;
INSERT INTO `Project` VALUES (1,'AA','Project A name'),(2,'BB','Project B name');
UNLOCK TABLES;
