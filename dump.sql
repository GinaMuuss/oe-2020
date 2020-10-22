
Use oe;
LOCK TABLES `questions` WRITE;
/*!40000 ALTER TABLE `questions` DISABLE KEYS */;
INSERT INTO `questions` VALUES ('aaa','NEW','Richtig ist b'),('caa','NEW','Richtig ist c');
/*!40000 ALTER TABLE `questions` ENABLE KEYS */;
UNLOCK TABLES;

LOCK TABLES `answer_options` WRITE;
/*!40000 ALTER TABLE `answer_options` DISABLE KEYS */;
INSERT INTO `answer_options` VALUES ('a','a',0,0,'aaa'),('a1','a',0,0,'caa'),('b','b',1,1,'aaa'),('b1','b',0,0,'caa'),('c','c',0,0,'aaa'),('c1','c',1,1,'caa'),('d','d',0,0,'aaa'),('d1','d',0,0,'caa');
/*!40000 ALTER TABLE `answer_options` ENABLE KEYS */;
UNLOCK TABLES;
