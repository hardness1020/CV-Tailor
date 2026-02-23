"""
Sample job description data for testing.
"""

SAMPLE_JOB_DESCRIPTION = {
    'raw_content': '''
    Software Engineer position at Tech Corp.
    Requirements: Python, Django, React, 5+ years experience.
    Responsibilities: Build web applications, lead technical projects.
    Benefits: Competitive salary, remote work, health insurance.
    ''',
    'company_name': 'Tech Corp',
    'role_title': 'Software Engineer'
}

SAMPLE_JOB_PARSED_DATA = {
    'company_name': 'Tech Corp',
    'role_title': 'Software Engineer',
    'must_have_skills': ['Python', 'Django', 'React'],
    'nice_to_have_skills': ['Docker', 'Kubernetes', 'AWS'],
    'responsibilities': [
        'Build web applications',
        'Lead technical projects',
        'Collaborate with cross-functional teams'
    ],
    'required_experience_years': 5,
    'benefits': ['Competitive salary', 'Remote work', 'Health insurance']
}

SAMPLE_JOB_WITH_REQUIREMENTS = {
    'raw_content': '''
    Senior Backend Engineer - AI Startup

    Requirements:
    - 7+ years of Python development experience
    - Expert knowledge of Django and Django REST Framework
    - Experience with PostgreSQL and database optimization
    - Strong understanding of distributed systems
    - Experience with LLM integration (OpenAI, Anthropic)

    Nice to have:
    - Experience with vector databases (pgvector, Pinecone)
    - Background in machine learning or NLP
    - Open source contributions

    Responsibilities:
    - Design and implement scalable backend APIs
    - Optimize database queries and performance
    - Integrate LLM services into production systems
    - Mentor junior engineers
    ''',
    'company_name': 'AI Startup Inc',
    'role_title': 'Senior Backend Engineer'
}

SAMPLE_DATA_SCIENTIST_JOB = {
    'raw_content': '''
    Data Scientist - Machine Learning Team

    We're looking for a Data Scientist to join our ML team.

    Must have:
    - Python programming (NumPy, Pandas, Scikit-learn)
    - Machine learning model development and deployment
    - Statistical analysis and experimentation
    - 3+ years of industry experience

    Preferred:
    - Deep learning (PyTorch or TensorFlow)
    - NLP or computer vision experience
    - Cloud platforms (AWS, GCP)
    ''',
    'company_name': 'Big Corp',
    'role_title': 'Data Scientist'
}
