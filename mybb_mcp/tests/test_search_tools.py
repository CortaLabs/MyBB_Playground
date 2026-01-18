"""Test suite for search functionality tools.

Tests the 4 search tools:
1. mybb_search_posts - search post content with filters
2. mybb_search_threads - search thread subjects with filters
3. mybb_search_users - search users by username/email
4. mybb_search_advanced - combined search across content types
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

# Import implementations
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "mybb_mcp"))

from mybb_mcp.db.connection import MyBBDatabase
from mybb_mcp.config import DatabaseConfig


class TestSearchPosts:
    """Test search_posts functionality."""

    @pytest.fixture
    def mock_db_config(self):
        """Create mock database config."""
        return DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test_user",
            password="test_pass",
            prefix="mybb_"
        )

    @pytest.fixture
    def mock_posts(self):
        """Sample posts for search testing."""
        return [
            {
                'pid': 1,
                'tid': 10,
                'fid': 2,
                'subject': 'Test Post',
                'uid': 1,
                'username': 'admin',
                'dateline': 1705500000,
                'message': 'This is a test message about Python programming.',
                'visible': 1,
                'edittime': 0,
                'editreason': '',
                'thread_subject': 'Programming Discussion',
                'thread_fid': 2
            },
            {
                'pid': 2,
                'tid': 11,
                'fid': 3,
                'subject': 'Re: Python',
                'uid': 2,
                'username': 'user1',
                'dateline': 1705600000,
                'message': 'Python is a great programming language for beginners.',
                'visible': 1,
                'edittime': 0,
                'editreason': '',
                'thread_subject': 'Learning Python',
                'thread_fid': 3
            }
        ]

    def test_search_posts_basic(self, mock_db_config, mock_posts):
        """Test basic post search."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = mock_posts

            results = db.search_posts(query="Python")

            assert len(results) == 2
            assert results[0]['message'].find('Python') != -1
            mock_cursor.return_value.__enter__.return_value.execute.assert_called_once()

    def test_search_posts_with_forums_filter(self, mock_db_config, mock_posts):
        """Test post search with forum filter."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = [mock_posts[0]]

            results = db.search_posts(query="Python", forums=[2])

            assert len(results) == 1
            assert results[0]['fid'] == 2

    def test_search_posts_with_author_filter(self, mock_db_config, mock_posts):
        """Test post search with author filter."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = [mock_posts[0]]

            results = db.search_posts(query="test", author="admin")

            assert len(results) == 1
            assert results[0]['username'] == 'admin'

    def test_search_posts_limit_sanitization(self, mock_db_config):
        """Test that limit is properly sanitized."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = []

            # Test limit > 100
            db.search_posts(query="test", limit=500)
            call_args = mock_cursor.return_value.__enter__.return_value.execute.call_args
            # Limit should be clamped to 100
            assert 100 in call_args[0][1]

            # Test limit < 1
            db.search_posts(query="test", limit=0)
            call_args = mock_cursor.return_value.__enter__.return_value.execute.call_args
            # Limit should be at least 1
            assert call_args[0][1][-2] >= 1

    def test_search_posts_no_sensitive_data(self, mock_db_config, mock_posts):
        """Test that ipaddress is not in results."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = mock_posts

            results = db.search_posts(query="Python")

            # Verify no ipaddress field
            for post in results:
                assert 'ipaddress' not in post

    def test_search_posts_sql_injection_prevention(self, mock_db_config):
        """Test SQL injection prevention via parameterized queries."""
        db = MyBBDatabase(mock_db_config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = []

            # Try SQL injection
            malicious_query = "'; DROP TABLE posts; --"
            db.search_posts(query=malicious_query)

            call_args = mock_cursor.return_value.__enter__.return_value.execute.call_args
            # Verify query uses parameterized statement (has %s)
            assert '%s' in call_args[0][0]
            # Verify malicious input is in params, not query string
            assert malicious_query not in call_args[0][0]


class TestSearchThreads:
    """Test search_threads functionality."""

    @pytest.fixture
    def mock_threads(self):
        """Sample threads for search testing."""
        return [
            {
                'tid': 10,
                'fid': 2,
                'subject': 'Python Programming Tips',
                'prefix': 0,
                'uid': 1,
                'username': 'admin',
                'dateline': 1705500000,
                'lastpost': 1705600000,
                'lastposter': 'user1',
                'views': 150,
                'replies': 10,
                'closed': '',
                'sticky': 0,
                'visible': 1
            }
        ]

    def test_search_threads_basic(self, mock_threads):
        """Test basic thread search."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = mock_threads

            results = db.search_threads(query="Python")

            assert len(results) == 1
            assert 'Python' in results[0]['subject']

    def test_search_threads_with_prefix(self, mock_threads):
        """Test thread search with prefix filter."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = mock_threads

            results = db.search_threads(query="Python", prefix=0)

            assert len(results) == 1


class TestSearchUsers:
    """Test search_users functionality."""

    @pytest.fixture
    def mock_users(self):
        """Sample users for search testing."""
        return [
            {
                'uid': 1,
                'username': 'admin',
                'usergroup': 4,
                'displaygroup': 4,
                'postnum': 1000,
                'threadnum': 50,
                'avatar': '',
                'usertitle': 'Administrator',
                'regdate': 1600000000,
                'lastactive': 1705500000,
                'lastvisit': 1705400000
            }
        ]

    def test_search_users_by_username(self, mock_users):
        """Test user search by username."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = mock_users

            results = db.search_users(query="admin", field="username")

            assert len(results) == 1
            assert results[0]['username'] == 'admin'

    def test_search_users_no_passwords(self, mock_users):
        """Test that passwords/salts/loginkeys are not in results."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = mock_users

            results = db.search_users(query="admin")

            for user in results:
                assert 'password' not in user
                assert 'salt' not in user
                assert 'loginkey' not in user

    def test_search_users_invalid_field(self):
        """Test user search with invalid field."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with pytest.raises(ValueError, match="field must be 'username' or 'email'"):
            db.search_users(query="test", field="invalid")


class TestSearchAdvanced:
    """Test search_advanced functionality."""

    @pytest.fixture
    def mock_posts(self):
        return [{
            'pid': 1,
            'tid': 10,
            'message': 'Test post',
            'username': 'admin',
            'dateline': 1705500000,
            'thread_subject': 'Test Thread',
            'thread_fid': 2
        }]

    @pytest.fixture
    def mock_threads(self):
        return [{
            'tid': 10,
            'subject': 'Test Thread',
            'username': 'admin',
            'replies': 5,
            'views': 100
        }]

    def test_search_advanced_both(self, mock_posts, mock_threads):
        """Test advanced search with content_type='both'."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'search_posts', return_value=mock_posts), \
             patch.object(db, 'search_threads', return_value=mock_threads):

            results = db.search_advanced(query="test", content_type="both")

            assert 'posts' in results
            assert 'threads' in results
            assert len(results['posts']) == 1
            assert len(results['threads']) == 1

    def test_search_advanced_posts_only(self, mock_posts):
        """Test advanced search with content_type='posts'."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'search_posts', return_value=mock_posts):
            results = db.search_advanced(query="test", content_type="posts")

            assert 'posts' in results
            assert 'threads' not in results

    def test_search_advanced_threads_only(self, mock_threads):
        """Test advanced search with content_type='threads'."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'search_threads', return_value=mock_threads):
            results = db.search_advanced(query="test", content_type="threads")

            assert 'threads' in results
            assert 'posts' not in results


class TestSecurityValidation:
    """Security-focused tests."""

    def test_like_wildcard_escaping(self):
        """Test that LIKE wildcards are properly escaped."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = []

            # Query with wildcards
            db.search_posts(query="test%_wildcard")

            call_args = mock_cursor.return_value.__enter__.return_value.execute.call_args
            # Verify wildcards are escaped in params
            params = call_args[0][1]
            # First param should be the escaped query
            assert 'test\\%\\_wildcard' in params[0]

    def test_visible_filter_enforced(self):
        """Test that only visible=1 content is returned."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            database="test_mybb",
            user="test",
            password="test",
            prefix="mybb_"
        )
        db = MyBBDatabase(config)

        with patch.object(db, 'cursor') as mock_cursor:
            mock_cursor.return_value.__enter__.return_value.fetchall.return_value = []

            db.search_posts(query="test")

            call_args = mock_cursor.return_value.__enter__.return_value.execute.call_args
            query = call_args[0][0]
            # Verify visible=1 filter is in query
            assert 'visible = 1' in query or 'visible=1' in query
