"""
Sample artifact data for testing.
"""

SAMPLE_ARTIFACTS_DATA = [
    {
        'id': 1,
        'title': 'Backend API Development',
        'description': 'Built REST APIs using Python and Django for e-commerce platform',
        'artifact_type': 'project',
        'technologies': ['Python', 'Django', 'PostgreSQL', 'Redis'],
        'start_date': '2023-01-01',
        'end_date': '2023-12-31',
        'achievements': [
            'Reduced API response time by 40%',
            'Implemented caching strategy',
            'Handled 10M+ requests per day'
        ]
    },
    {
        'id': 2,
        'title': 'Frontend React App',
        'description': 'Developed responsive web application using React and TypeScript',
        'artifact_type': 'project',
        'technologies': ['React', 'TypeScript', 'Tailwind CSS', 'Redux'],
        'start_date': '2022-06-01',
        'end_date': '2022-12-31',
        'achievements': [
            'Improved user engagement by 25%',
            'Achieved 95+ Lighthouse score',
            'Implemented real-time features with WebSockets'
        ]
    },
    {
        'id': 3,
        'title': 'Machine Learning Pipeline',
        'description': 'Built end-to-end ML pipeline for recommendation system',
        'artifact_type': 'project',
        'technologies': ['Python', 'PyTorch', 'scikit-learn', 'Airflow'],
        'start_date': '2023-03-01',
        'end_date': '2023-09-30',
        'achievements': [
            'Improved recommendation accuracy by 30%',
            'Processed 1M+ user interactions daily',
            'Reduced training time by 50% with optimization'
        ]
    }
]

SAMPLE_ENHANCED_ARTIFACT = {
    'title': 'Full Stack Web Application',
    'content_type': 'project',
    'raw_content': '''
    Full Stack Web Application - E-commerce Platform

    Role: Lead Developer (Jan 2023 - Present)

    Technologies:
    - Backend: Python, Django, Django REST Framework, PostgreSQL, Redis
    - Frontend: React, TypeScript, Tailwind CSS
    - DevOps: Docker, AWS (EC2, S3, RDS), CI/CD with GitHub Actions

    Key Achievements:
    - Architected and built a scalable e-commerce platform serving 100K+ users
    - Implemented real-time inventory management system with 99.9% accuracy
    - Reduced page load time by 60% through optimization and caching
    - Led team of 4 developers in agile development process
    - Integrated payment gateway (Stripe) processing $1M+ monthly transactions

    Technical Highlights:
    - RESTful API design with comprehensive documentation
    - Implemented JWT authentication and role-based access control
    - Built automated testing suite with 85% code coverage
    - Optimized database queries reducing response time from 2s to 200ms
    ''',
    'enriched_keywords': ['scalable architecture', 'team leadership', 'performance optimization'],
    'total_chunks': 3
}

SAMPLE_ARTIFACT_CHUNKS = [
    {
        'chunk_index': 0,
        'content': 'Full Stack Web Application - E-commerce Platform. Role: Lead Developer. Technologies: Python, Django, React, TypeScript, PostgreSQL, Redis, Docker, AWS.',
        'content_hash': 'hash_0'
    },
    {
        'chunk_index': 1,
        'content': 'Key Achievements: Architected scalable platform serving 100K+ users. Implemented real-time inventory with 99.9% accuracy. Reduced page load time by 60%. Led team of 4 developers.',
        'content_hash': 'hash_1'
    },
    {
        'chunk_index': 2,
        'content': 'Technical Highlights: RESTful API design. JWT authentication and RBAC. 85% test coverage. Database optimization (2s to 200ms response time). Stripe payment integration ($1M+ monthly).',
        'content_hash': 'hash_2'
    }
]

SAMPLE_GITHUB_PROJECT = {
    'title': 'Open Source Django Library',
    'description': 'Contributed to popular Django authentication library',
    'artifact_type': 'github',
    'url': 'https://github.com/example/django-auth',
    'technologies': ['Python', 'Django', 'OAuth', 'JWT'],
    'contributions': [
        'Added support for multi-factor authentication',
        'Fixed critical security vulnerability (CVE-2023-XXXX)',
        'Improved documentation and added examples'
    ]
}

SAMPLE_RESUME_PDF = {
    'title': 'Software Engineer Resume',
    'content_type': 'pdf',
    'raw_content': '''
    John Doe
    Software Engineer
    john.doe@email.com | LinkedIn: linkedin.com/in/johndoe

    EXPERIENCE

    Senior Software Engineer - Tech Corp (2020-Present)
    - Led development of microservices architecture serving 1M+ users
    - Reduced system latency by 40% through caching and optimization
    - Mentored 3 junior developers and conducted code reviews

    Software Engineer - Startup Inc (2018-2020)
    - Built RESTful APIs using Python and Django
    - Implemented CI/CD pipeline with automated testing
    - Collaborated with product team on feature development

    EDUCATION

    B.S. Computer Science - University of Technology (2014-2018)
    - GPA: 3.8/4.0
    - Focus: Software Engineering, Databases

    SKILLS

    Languages: Python, JavaScript, TypeScript, SQL
    Frameworks: Django, React, FastAPI, Express
    Tools: Docker, Git, AWS, PostgreSQL, Redis
    '''
}
