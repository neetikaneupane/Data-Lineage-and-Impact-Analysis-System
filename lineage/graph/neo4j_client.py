import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


class Neo4jClient:
    def __init__(self):
        uri      = os.getenv("NEO4J_URI")
        user     = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def run(self, query: str, parameters: dict = None):
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def clear_all(self):
        self.run("MATCH (n) DETACH DELETE n")

    def create_indexes(self):
        indexes = [
            "CREATE INDEX column_id IF NOT EXISTS FOR (c:Column) ON (c.id)",
            "CREATE INDEX table_name IF NOT EXISTS FOR (t:Table) ON (t.name)",
            "CREATE INDEX file_path IF NOT EXISTS FOR (f:File) ON (f.path)",
        ]
        for idx in indexes:
            self.run(idx)
        print("Indexes created.")

    def create_constraints(self):
        constraints = [
            "CREATE CONSTRAINT column_id_unique IF NOT EXISTS FOR (c:Column) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT table_name_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT file_path_unique IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
        ]
        for constraint in constraints:
            self.run(constraint)
        print("Constraints created.")