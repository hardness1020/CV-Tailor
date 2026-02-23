"""
Mock API response data for testing LLM integrations.
"""

MOCK_OPENAI_RESPONSES = {
    'job_parsing': {
        'choices': [{
            'message': {
                'content': '{"company_name": "Tech Corp", "role_title": "Software Engineer", "must_have_skills": ["Python", "Django", "React"], "nice_to_have_skills": ["Docker", "AWS"], "required_experience_years": 5}'
            },
            'finish_reason': 'stop'
        }],
        'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
        'model': 'gpt-5',
        'id': 'chatcmpl-test123'
    },
    'cv_generation': {
        'choices': [{
            'message': {
                'content': '{"professional_summary": "Experienced software engineer with 5+ years building web applications", "key_skills": ["Python", "Django", "React", "PostgreSQL"], "tailored_experience": [{"company": "Tech Corp", "role": "Senior Engineer", "bullets": ["Led API development", "Improved performance by 40%"]}]}'
            },
            'finish_reason': 'stop'
        }],
        'usage': {'prompt_tokens': 200, 'completion_tokens': 100, 'total_tokens': 300},
        'model': 'gpt-5',
        'id': 'chatcmpl-test456'
    },
    'cover_letter': {
        'choices': [{
            'message': {
                'content': 'Dear Hiring Manager,\n\nI am writing to express my strong interest in the Software Engineer position at Tech Corp. With over 5 years of experience in full-stack development, I am confident I can contribute to your team.\n\nBest regards,\nJohn Doe'
            },
            'finish_reason': 'stop'
        }],
        'usage': {'prompt_tokens': 150, 'completion_tokens': 80, 'total_tokens': 230},
        'model': 'gpt-5',
        'id': 'chatcmpl-test789'
    },
    'embedding': {
        'data': [{'embedding': [0.1] * 1536, 'index': 0}],
        'usage': {'prompt_tokens': 50, 'total_tokens': 50},
        'model': 'text-embedding-3-small'
    },
    'artifact_enhancement': {
        'choices': [{
            'message': {
                'content': '{"enriched_keywords": ["scalable systems", "API design", "performance optimization"], "technical_highlights": ["Reduced latency by 40%", "Implemented caching strategy"], "suggested_improvements": ["Add specific metrics", "Highlight leadership experience"]}'
            },
            'finish_reason': 'stop'
        }],
        'usage': {'prompt_tokens': 180, 'completion_tokens': 90, 'total_tokens': 270},
        'model': 'gpt-5',
        'id': 'chatcmpl-test101'
    }
}

MOCK_ANTHROPIC_RESPONSES = {
    'job_parsing': {
        'content': [{
            'type': 'text',
            'text': '{"company_name": "AI Startup", "role_title": "ML Engineer", "must_have_skills": ["Python", "PyTorch", "NLP"], "nice_to_have_skills": ["Kubernetes", "MLOps"], "required_experience_years": 3}'
        }],
        'usage': {'input_tokens': 120, 'output_tokens': 60},
        'model': 'claude-sonnet-4',
        'id': 'msg_test123',
        'stop_reason': 'end_turn'
    },
    'cv_generation': {
        'content': [{
            'type': 'text',
            'text': '{"professional_summary": "Machine learning engineer specializing in NLP and deep learning", "key_skills": ["Python", "PyTorch", "TensorFlow", "NLP"], "tailored_experience": [{"company": "AI Startup", "role": "ML Engineer", "bullets": ["Built NLP models", "Deployed to production"]}]}'
        }],
        'usage': {'input_tokens': 250, 'output_tokens': 120},
        'model': 'claude-sonnet-4',
        'id': 'msg_test456',
        'stop_reason': 'end_turn'
    },
    'cover_letter': {
        'content': [{
            'type': 'text',
            'text': 'Dear Hiring Manager,\n\nI am excited to apply for the ML Engineer position at AI Startup. My experience with PyTorch and NLP aligns perfectly with your requirements.\n\nSincerely,\nJane Smith'
        }],
        'usage': {'input_tokens': 180, 'output_tokens': 100},
        'model': 'claude-sonnet-4',
        'id': 'msg_test789',
        'stop_reason': 'end_turn'
    }
}

MOCK_EMBEDDING_RESPONSE = {
    'openai': {
        'data': [
            {'embedding': [0.1] * 1536, 'index': 0}
        ],
        'usage': {'prompt_tokens': 50, 'total_tokens': 50},
        'model': 'text-embedding-3-small'
    },
    'anthropic': {
        # Anthropic doesn't have embeddings API, placeholder for future
        'data': None
    }
}

MOCK_ERROR_RESPONSES = {
    'rate_limit': {
        'error': {
            'message': 'Rate limit exceeded. Please try again later.',
            'type': 'rate_limit_error',
            'code': 'rate_limit_exceeded'
        }
    },
    'invalid_api_key': {
        'error': {
            'message': 'Invalid API key provided.',
            'type': 'invalid_request_error',
            'code': 'invalid_api_key'
        }
    },
    'timeout': {
        'error': {
            'message': 'Request timed out.',
            'type': 'timeout_error',
            'code': 'timeout'
        }
    },
    'server_error': {
        'error': {
            'message': 'Internal server error.',
            'type': 'server_error',
            'code': 'internal_error'
        }
    }
}

# Mock response builder helpers
def build_mock_chat_response(content: str, model: str = 'gpt-5', prompt_tokens: int = 100, completion_tokens: int = 50):
    """Build a mock OpenAI chat completion response."""
    return {
        'choices': [{
            'message': {'content': content},
            'finish_reason': 'stop'
        }],
        'usage': {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens
        },
        'model': model,
        'id': f'chatcmpl-mock-{model}'
    }

def build_mock_embedding_response(embedding: list = None, model: str = 'text-embedding-3-small'):
    """Build a mock OpenAI embedding response."""
    if embedding is None:
        embedding = [0.1] * 1536
    return {
        'data': [{'embedding': embedding, 'index': 0}],
        'usage': {'prompt_tokens': 50, 'total_tokens': 50},
        'model': model
    }

def build_mock_anthropic_response(content: str, model: str = 'claude-sonnet-4', input_tokens: int = 100, output_tokens: int = 50):
    """Build a mock Anthropic message response."""
    return {
        'content': [{'type': 'text', 'text': content}],
        'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens},
        'model': model,
        'id': f'msg-mock-{model}',
        'stop_reason': 'end_turn'
    }
