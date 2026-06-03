import pytest
from src.utils.sql_parser import validate_sql, get_table_names, format_sql


class TestSQLValidation:

    def test_valid_select(self):
        r = validate_sql("SELECT * FROM orders LIMIT 10")
        assert r.is_valid
        assert r.risk_level == "safe"

    def test_select_without_limit_warns(self):
        r = validate_sql("SELECT * FROM orders")
        assert r.is_valid
        assert r.risk_level == "warning"

    def test_block_delete(self):
        r = validate_sql("DELETE FROM orders WHERE order_id = 1")
        assert not r.is_valid
        assert r.risk_level == "blocked"
        assert "DELETE" in r.error_message

    def test_block_drop(self):
        r = validate_sql("DROP TABLE orders")
        assert not r.is_valid
        assert r.risk_level == "blocked"

    def test_block_insert(self):
        r = validate_sql("INSERT INTO orders VALUES (1, 2, '2024-01-01')")
        assert not r.is_valid
        assert r.risk_level == "blocked"

    def test_block_truncate(self):
        r = validate_sql("TRUNCATE TABLE orders")
        assert not r.is_valid
        assert r.risk_level == "blocked"

    def test_block_dangerous_function(self):
        r = validate_sql("SELECT pg_sleep(10)")
        assert not r.is_valid
        assert r.risk_level == "blocked"

    def test_syntax_error(self):
        r = validate_sql("SELEC FROM WHERE!!!!")
        assert not r.is_valid
        assert r.risk_level == "blocked"

    def test_deep_subquery_warns(self):
        sql = "SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM orders))))"
        r = validate_sql(sql)
        assert r.is_valid
        assert len(r.warnings) > 0


class TestGetTableNames:

    def test_simple_select(self):
        tables = get_table_names("SELECT * FROM orders WHERE order_id = 1")
        assert "orders" in tables

    def test_join(self):
        sql = "SELECT * FROM orders o JOIN customers c ON o.customer_id = c.customer_id"
        tables = get_table_names(sql)
        assert "orders" in tables
        assert "customers" in tables

    def test_invalid_sql(self):
        tables = get_table_names("NOT A VALID SQL")
        assert tables == []
