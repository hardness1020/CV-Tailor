"""
Unit tests for GitHub agent error logging improvements.
Tests that detailed error messages are logged when GitHub API fails.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent


class TestGitHubErrorLogging:
    """Test error logging improvements in GitHubRepositoryAgent"""

    @pytest.mark.asyncio
    async def test_404_error_logging(self):
        """Test that 404 errors generate detailed log messages"""
        agent = GitHubRepositoryAgent()

        # Mock the requests.get call to return 404
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.json.return_value = {'message': 'Not Found'}

        # Mock requests.get in BOTH modules to prevent real API calls
        with patch('llm_services.services.core.document_loader_service.requests.get', return_value=mock_response):
            with patch('llm_services.services.core.github_repository_agent.requests.get', return_value=mock_response):
                with patch('llm_services.services.core.github_repository_agent.logger') as mock_logger:
                    # Mock doc_loader to avoid real API calls
                    with patch.object(agent.doc_loader, 'get_github_repo_stats', return_value={'languages': {}}):
                        result = await agent.analyze_repository(
                            repo_url="https://github.com/test/nonexistent",
                            user_id=1
                        )

                    # Verify error was logged
                    assert mock_logger.error.called
                    error_call = mock_logger.error.call_args[0][0]
                    assert 'GitHub API request failed' in error_call or 'GitHub Agent' in error_call
                    assert 'not found' in error_call.lower() or '404' in error_call

                    # Verify result contains detailed error
                    assert result.success is False
                    assert result.error_message
                    assert 'not found' in result.error_message.lower() or '404' in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_error_logging(self):
        """Test that rate limit errors (403) generate actionable messages"""
        agent = GitHubRepositoryAgent()

        # Mock the requests.get call to return 403 with rate limit headers
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': '1700000000'
        }
        mock_response.json.return_value = {'message': 'API rate limit exceeded'}

        # Mock requests.get in BOTH modules to prevent real API calls
        with patch('llm_services.services.core.document_loader_service.requests.get', return_value=mock_response):
            with patch('llm_services.services.core.github_repository_agent.requests.get', return_value=mock_response):
                with patch('llm_services.services.core.github_repository_agent.logger') as mock_logger:
                    with patch.object(agent.doc_loader, 'get_github_repo_stats', return_value={'languages': {}}):
                        result = await agent.analyze_repository(
                            repo_url="https://github.com/test/repo",
                            user_id=1
                        )

                    # Verify error was logged with rate limit details
                    assert mock_logger.error.called
                    error_call = mock_logger.error.call_args[0][0]
                    assert 'rate limit' in error_call.lower()

                    # Verify result contains rate limit info
                    assert result.success is False
                    assert 'rate limit' in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_invalid_url_error_logging(self):
        """Test that invalid URL format generates clear error message"""
        agent = GitHubRepositoryAgent()

        # Mock requests.get in BOTH modules to prevent real API calls (in case URL validation doesn't catch it)
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.json.return_value = {'message': 'Not Found'}

        with patch('llm_services.services.core.document_loader_service.requests.get', return_value=mock_response):
            with patch('llm_services.services.core.github_repository_agent.requests.get', return_value=mock_response):
                with patch('llm_services.services.core.github_repository_agent.logger') as mock_logger:
                    result = await agent.analyze_repository(
                        repo_url="https://invalid-site.com/not-github",
                        user_id=1
                    )

                    # Verify error was logged
                    assert mock_logger.error.called
                    error_call = mock_logger.error.call_args[0][0]
                    assert 'Invalid' in error_call or 'format' in error_call.lower()

                    # Verify result
                    assert result.success is False
                    assert result.error_message
                    assert 'invalid' in result.error_message.lower() or 'format' in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_auth_error_logging(self):
        """Test that 401 authentication errors generate actionable messages"""
        agent = GitHubRepositoryAgent()

        # Mock the requests.get call to return 401
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_response.json.return_value = {'message': 'Requires authentication'}

        # Mock requests.get in BOTH modules to prevent real API calls
        with patch('llm_services.services.core.document_loader_service.requests.get', return_value=mock_response):
            with patch('llm_services.services.core.github_repository_agent.requests.get', return_value=mock_response):
                with patch('llm_services.services.core.github_repository_agent.logger') as mock_logger:
                    with patch.object(agent.doc_loader, 'get_github_repo_stats', return_value={'languages': {}}):
                        result = await agent.analyze_repository(
                            repo_url="https://github.com/test/private",
                            user_id=1
                        )

                    # Verify error was logged
                    assert mock_logger.error.called
                    error_call = mock_logger.error.call_args[0][0]
                    assert 'authentication' in error_call.lower() or '401' in error_call

                    # Verify result contains auth guidance
                    assert result.success is False
                    assert 'authentication' in result.error_message.lower() or 'GITHUB_TOKEN' in result.error_message
