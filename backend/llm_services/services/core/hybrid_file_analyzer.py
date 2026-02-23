"""
HybridFileAnalyzer - Multi-format file parsing for GitHub repositories.
Implements ft-013-github-agent-traversal.md Phase 3 (Hybrid Analysis)

Analyzes multiple file types:
- Config files: package.json, requirements.txt, Cargo.toml, go.mod, pyproject.toml
- Source code: Python, JavaScript/TypeScript, Rust, Go (LLM-powered pattern detection)
- Infrastructure: Dockerfile, docker-compose.yml, CI/CD configs, Kubernetes
- Documentation: README, ARCHITECTURE, CONTRIBUTING

Cross-references findings for consistency checking and conflict resolution.
"""

import json
import re
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field, asdict
from langchain.schema import Document

from ..base.base_service import BaseLLMService
from ..infrastructure.simple_llm_executor import SimpleLLMExecutor

logger = logging.getLogger(__name__)


# Hybrid File Analyzer Configuration
# Optimized for $0.50/repo budget with GPT-5

# Source Code Analysis
SOURCE_ANALYSIS_MODEL = 'gpt-5'
SOURCE_ANALYSIS_MAX_TOKENS = 10000
SOURCE_ANALYSIS_MAX_FILES = 20
SOURCE_ANALYSIS_CHARS_PER_FILE = 3000

# Documentation Analysis
DOCS_ANALYSIS_MODEL = 'gpt-5'
DOCS_ANALYSIS_MAX_TOKENS = 10000
DOCS_ANALYSIS_MAX_DOCS = 12
DOCS_ANALYSIS_CHARS_PER_DOC = 5000


# Data classes for analysis results
@dataclass
class ConfigAnalysisResult:
    """Results from config file analysis"""
    technologies: List[str] = field(default_factory=list)
    dependency_count: int = 0
    build_tools: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    runtime_versions: Dict[str, str] = field(default_factory=dict)


@dataclass
class SourceAnalysisResult:
    """Results from source code analysis"""
    project_purpose: str = ""
    patterns: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    architecture_notes: str = ""


@dataclass
class InfrastructureAnalysisResult:
    """Results from infrastructure file analysis"""
    deployment: List[str] = field(default_factory=list)
    runtime: str = ""
    services: List[str] = field(default_factory=list)
    web_server: str = ""
    ci_cd: str = ""
    deployment_automation: bool = False
    scaling: Optional[int] = None


@dataclass
class DocumentationAnalysisResult:
    """Results from documentation analysis"""
    project_summary: str = ""
    key_features: List[str] = field(default_factory=list)
    tech_stack_mentioned: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    architecture_notes: str = ""
    project_type: str = ""


@dataclass
class HybridAnalysisResult:
    """Combined results from all file types"""
    config_analysis: Dict
    source_analysis: Dict
    infrastructure_analysis: Dict
    documentation_analysis: Dict
    consistency_score: float = 0.0
    confidence: float = 0.0
    refinement_iterations: int = 1
    conflict_notes: str = ""


class HybridFileAnalyzer(BaseLLMService):
    """
    Multi-format file analyzer for GitHub repositories (Phase 3: Hybrid Analysis).

    Analyzes different file types to extract comprehensive repository insights:
    - **Config files**: package.json, requirements.txt, Cargo.toml, go.mod, pyproject.toml
    - **Source code**: LLM-powered pattern detection for Python, JS/TS, Rust, Go
    - **Infrastructure**: Dockerfile, docker-compose.yml, CI/CD, Kubernetes manifests
    - **Documentation**: README, ARCHITECTURE, CONTRIBUTING files

    Cross-references findings across all file types for consistency checking and
    conflict resolution. Part of the 4-phase agent architecture (ft-013).

    Examples:
        >>> analyzer = HybridFileAnalyzer()
        >>> config_result = await analyzer.analyze_config_files(config_docs)
        >>> source_result = await analyzer.analyze_source_code(source_docs)
        >>>
        >>> # Cross-reference all findings
        >>> final = await analyzer.synthesize_insights(
        ...     config_result, source_result, infra_result, docs_result
        ... )
        >>> print(final.consistency_score)  # 0.0-1.0

    Attributes:
        llm_executor (SimpleLLMExecutor): Lightweight LLM execution helper
        config_parsers (Dict): Mapping of config filenames to parser functions
    """

    def __init__(self):
        """
        Initialize the HybridFileAnalyzer with LLM executor and config parsers.

        Sets up:
        - SimpleLLMExecutor for LLM-powered analysis (with client_manager)
        - Config parser registry for supported file types
        """
        super().__init__()
        self.llm_executor = SimpleLLMExecutor(client_manager=self.client_manager)
        self.config_parsers = {
            'package.json': self._parse_package_json,
            'requirements.txt': self._parse_requirements_txt,
            'Cargo.toml': self._parse_cargo_toml,
            'go.mod': self._parse_go_mod,
            'pyproject.toml': self._parse_pyproject_toml,
        }

    async def analyze_config_files(self, config_docs: List[Document]) -> Dict:
        """
        Analyze configuration files to extract technologies, dependencies, and build tools.

        Parses multiple config formats using specialized parsers:
        - package.json → Node.js, frameworks (React/Vue/Angular), build tools
        - requirements.txt → Python, frameworks (Django/Flask/FastAPI)
        - Cargo.toml → Rust, crates
        - go.mod → Go, modules
        - pyproject.toml → Python, Poetry, dependencies

        Args:
            config_docs (List[Document]): LangChain Document objects with config file contents.
                Each doc should have metadata['path'] indicating the filename.

        Returns:
            Dict: Analysis results with keys:
                - technologies (List[str]): Detected languages/frameworks (e.g., "Python", "Django")
                - dependency_count (int): Total number of dependencies
                - build_tools (List[str]): Build tools (e.g., "Webpack", "Poetry")
                - frameworks (List[str]): Application frameworks
                - runtime_versions (Dict): Runtime version specs (e.g., {"node": ">=18.0.0"})

        Examples:
            >>> docs = [Document(page_content=package_json_str, metadata={'path': 'package.json'})]
            >>> result = await analyzer.analyze_config_files(docs)
            >>> print(result['technologies'])
            ['Node.js', 'React', 'TypeScript']
            >>> print(result['dependency_count'])
            47
        """
        result = ConfigAnalysisResult()

        for doc in config_docs:
            file_path = doc.metadata.get('path', '')
            file_name = file_path.split('/')[-1]

            # Use specialized parser if available
            parser = self.config_parsers.get(file_name)
            if parser:
                try:
                    parsed = parser(doc.page_content)
                    result.technologies.extend(parsed.get('technologies', []))
                    result.dependency_count += parsed.get('dependency_count', 0)
                    result.build_tools.extend(parsed.get('build_tools', []))
                    result.frameworks.extend(parsed.get('frameworks', []))
                    result.runtime_versions.update(parsed.get('runtime_versions', {}))
                except Exception as e:
                    logger.warning(f"Failed to parse {file_name}: {e}")

        # Deduplicate technologies
        result.technologies = list(set(result.technologies))
        result.build_tools = list(set(result.build_tools))
        result.frameworks = list(set(result.frameworks))

        return asdict(result)

    def _parse_package_json(self, content: str) -> Dict:
        """Parse package.json for Node.js projects"""
        try:
            data = json.loads(content)
            technologies = ['Node.js', 'JavaScript']
            dependency_count = 0

            # Extract dependencies
            for dep_key in ['dependencies', 'devDependencies']:
                if dep_key in data:
                    deps = data[dep_key]
                    dependency_count += len(deps)

                    # Detect major frameworks
                    if 'next' in deps:
                        technologies.append('Next.js')
                    if 'react' in deps:
                        technologies.append('React')
                    if 'vue' in deps:
                        technologies.append('Vue.js')
                    if 'express' in deps:
                        technologies.append('Express')
                    if '@angular/core' in deps:
                        technologies.append('Angular')

            # Detect TypeScript
            if 'typescript' in data.get('devDependencies', {}) or \
               'typescript' in data.get('dependencies', {}):
                technologies.append('TypeScript')

            # Build tools
            build_tools = []
            if 'webpack' in data.get('devDependencies', {}):
                build_tools.append('Webpack')
            if 'vite' in data.get('devDependencies', {}):
                build_tools.append('Vite')

            return {
                'technologies': technologies,
                'dependency_count': dependency_count,
                'build_tools': build_tools,
                'frameworks': [],
                'runtime_versions': {}
            }
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in package.json: {e}")
            return {'technologies': [], 'dependency_count': 0, 'build_tools': [], 'frameworks': [], 'runtime_versions': {}}

    def _parse_requirements_txt(self, content: str) -> Dict:
        """Parse requirements.txt for Python projects"""
        technologies = ['Python']
        lines = content.strip().split('\n')
        dependencies = [line.strip() for line in lines if line.strip() and not line.startswith('#')]

        for dep in dependencies:
            dep_lower = dep.lower()
            if 'django' in dep_lower:
                technologies.append('Django')
                if 'djangorestframework' in dep_lower:
                    technologies.append('Django REST Framework')
            elif 'flask' in dep_lower:
                technologies.append('Flask')
            elif 'fastapi' in dep_lower:
                technologies.append('FastAPI')
            elif 'psycopg' in dep_lower or 'pg8000' in dep_lower:
                technologies.append('PostgreSQL')
            elif 'mysql' in dep_lower or 'pymysql' in dep_lower:
                technologies.append('MySQL')
            elif 'redis' in dep_lower:
                technologies.append('Redis')
            elif 'celery' in dep_lower:
                technologies.append('Celery')
            elif 'sqlalchemy' in dep_lower:
                technologies.append('SQLAlchemy')

        return {
            'technologies': technologies,
            'dependency_count': len(dependencies),
            'build_tools': [],
            'frameworks': [],
            'runtime_versions': {}
        }

    def _parse_cargo_toml(self, content: str) -> Dict:
        """Parse Cargo.toml for Rust projects"""
        technologies = ['Rust']

        # Simple regex-based parsing for dependencies (matches both inline and table format)
        # Matches: tokio = "1.0" OR tokio = { version = "1.0", ... }
        dep_pattern = r'(\w+)\s*='
        matches = re.findall(dep_pattern, content, re.IGNORECASE)

        dependency_names = [match for match in matches if match.lower() not in ['version', 'features', 'name', 'edition']]

        for dep in dependency_names:
            dep_lower = dep.lower()
            if 'tokio' in dep_lower:
                technologies.append('Tokio')
            elif 'axum' in dep_lower:
                technologies.append('Axum')
            elif 'actix' in dep_lower:
                technologies.append('Actix')
            elif 'rocket' in dep_lower:
                technologies.append('Rocket')
            elif 'serde' in dep_lower:
                technologies.append('Serde')
            elif 'sqlx' in dep_lower:
                # Check if PostgreSQL or MySQL
                if 'postgres' in content.lower():
                    technologies.append('PostgreSQL')

        return {
            'technologies': technologies,
            'dependency_count': len(dependency_names),
            'build_tools': ['Cargo'],
            'frameworks': [],
            'runtime_versions': {}
        }

    def _parse_go_mod(self, content: str) -> Dict:
        """Parse go.mod for Go projects"""
        technologies = ['Go']

        # Extract Go version
        version_match = re.search(r'go\s+([\d\.]+)', content)
        runtime_versions = {}
        if version_match:
            runtime_versions['Go'] = version_match.group(1)

        # Extract dependencies
        require_section = re.search(r'require\s*\((.*?)\)', content, re.DOTALL)
        dependencies = []

        if require_section:
            dep_lines = require_section.group(1).strip().split('\n')
            for line in dep_lines:
                if line.strip():
                    parts = line.strip().split()
                    if parts:
                        dep_name = parts[0]
                        dependencies.append(dep_name)

                        # Detect frameworks
                        if 'gin-gonic/gin' in dep_name:
                            technologies.append('Gin')
                        elif 'echo' in dep_name.lower():
                            technologies.append('Echo')
                        elif 'lib/pq' in dep_name:
                            technologies.append('PostgreSQL')
                        elif 'go-redis' in dep_name:
                            technologies.append('Redis')
                        elif 'gorm.io/gorm' in dep_name:
                            technologies.append('GORM')

        return {
            'technologies': technologies,
            'dependency_count': len(dependencies),
            'build_tools': [],
            'frameworks': [],
            'runtime_versions': runtime_versions
        }

    def _parse_pyproject_toml(self, content: str) -> Dict:
        """Parse pyproject.toml for modern Python projects"""
        technologies = ['Python']
        build_tools = []

        # Detect Poetry
        if '[tool.poetry]' in content:
            build_tools.append('Poetry')
            technologies.append('Poetry')  # Add to technologies as it's a key tool

        # Extract dependencies (handle version prefixes like ^, ~, >=)
        dep_pattern = r'(\w+)\s*=.*["\']([\^\~\>=]*[\d\.]+)["\']'
        matches = re.findall(dep_pattern, content, re.IGNORECASE)

        dependency_names = [match[0] for match in matches]

        for dep in dependency_names:
            dep_lower = dep.lower()
            if 'django' in dep_lower:
                technologies.append('Django')
            elif 'flask' in dep_lower:
                technologies.append('Flask')
            elif 'fastapi' in dep_lower:
                technologies.append('FastAPI')
            elif 'sqlalchemy' in dep_lower:
                technologies.append('SQLAlchemy')
            elif 'alembic' in dep_lower:
                technologies.append('Alembic')

        return {
            'technologies': technologies,
            'dependency_count': len(dependency_names),
            'build_tools': build_tools,
            'frameworks': [],
            'runtime_versions': {}
        }

    async def analyze_source_code(self, source_docs: List[Document]) -> Dict:
        """
        Analyze source code using LLM to detect patterns, architectures, and tech stack.

        Uses GPT-5-mini to analyze up to 5 source code files and detect:
        - Design patterns (MVC, Repository, Factory, Singleton, etc.)
        - Architectures (Microservices, Monolith, Event-Driven, Layered, etc.)
        - Technologies inferred from imports and usage patterns

        Args:
            source_docs (List[Document]): LangChain Document objects with source code.
                Analyzes first 5 files only to stay within token budget.

        Returns:
            Dict: Analysis results with keys:
                - patterns (List[str]): Detected design patterns (e.g., "MVC", "Repository")
                - technologies (List[str]): Inferred tech from code (e.g., "React Hooks", "async/await")
                - architecture_notes (str): Brief description of overall architecture

        Raises:
            OpenAIError: If LLM API call fails

        Examples:
            >>> docs = [Document(page_content=python_code, metadata={'path': 'views.py'})]
            >>> result = await analyzer.analyze_source_code(docs)
            >>> print(result['patterns'])
            ['MVC', 'Repository Pattern']
            >>> print(result['architecture_notes'])
            'Django REST API with service layer pattern'

        Note:
            Requires OPENAI_API_KEY environment variable.
        """
        if not source_docs:
            return asdict(SourceAnalysisResult())

        # Prepare source code samples for LLM
        code_samples = []
        for doc in source_docs[:SOURCE_ANALYSIS_MAX_FILES]:  # Analyze first 20 files (increased from 5)
            code_samples.append({
                'file': doc.metadata.get('path', 'unknown'),
                'content': doc.page_content[:SOURCE_ANALYSIS_CHARS_PER_FILE]  # First 3000 chars (increased from 500)
            })

        prompt = f"""Analyze these source code samples and extract structured information.

CRITICAL ANTI-HALLUCINATION RULES:
- ONLY extract information that is EXPLICITLY EVIDENT in the source code
- For EVERY extracted item (technologies, patterns), provide the exact SOURCE EVIDENCE from the code
- Include source location (file name, line numbers, code snippet)
- Assign a confidence score (0.0-1.0) based on how directly the code supports the item
- Confidence threshold: >= 0.8 required (only HIGH-CONFIDENCE extractions)
- Import-only technologies MUST get confidence <= 0.6 (will be filtered out)
- Technologies with import + actual usage get confidence >= 0.8 (will pass)
- CRITICAL: Confidence scoring for technologies:
  * Import + usage evidence = 0.8-0.98 (VALID, will be included)
  * Import only, no usage = 0.3-0.6 (REJECTED, will be filtered)
  * Inferred/assumed = < 0.3 (REJECTED)

Source code samples:
{json.dumps(code_samples, indent=2)}

Extract the following in JSON format with SOURCE ATTRIBUTION:

1. "project_purpose": A 2-3 sentence description inferred from code structure
   - What problem this code solves (main functionality)
   - What technologies/frameworks are used
   - What architectural approach is taken

2. "patterns": Array of pattern objects with SOURCE ATTRIBUTION
   - Each pattern must include:
     * "name": Pattern name (e.g., "MVC", "REST API", "Repository pattern")
     * "source_attribution": Object with:
       - "source_quote": Exact code snippet showing the pattern
       - "source_file": File name (e.g., "app.py")
       - "source_location": Full location with line numbers (e.g., "app.py:15-23")
       - "confidence": 0.0-1.0 (0.95+ for clear pattern, 0.5-0.7 for partial, <0.5 for weak)
       - "reasoning": Brief explanation of how code demonstrates the pattern
   - Only extract patterns that are CLEARLY implemented in the code
   - Example: {{"name": "REST API", "source_attribution": {{"source_quote": "@app.route('/api/users', methods=['GET', 'POST'])", "source_file": "app.py", "source_location": "app.py:25", "confidence": 0.98, "reasoning": "Flask route decorator for HTTP API endpoint"}}}}

3. "technologies": Array of technology objects with SOURCE ATTRIBUTION
   - Each technology must include:
     * "name": Technology name (e.g., "Django", "React", "PostgreSQL")
     * "source_attribution": Object with source_quote, source_file, source_location, confidence, reasoning
   - Only extract technologies that are ACTIVELY USED in the code (not just imported)
   - Look for: imports + usage, configuration, database connections, framework usage
   - VALID examples (import + usage, confidence >= 0.8):
     * {{"name": "Django", "source_attribution": {{"source_quote": "from django.db import models\\nclass User(models.Model):", "source_file": "models.py", "source_location": "models.py:1-5", "confidence": 0.97, "reasoning": "Import + ORM model definition shows Django usage"}}}}
     * {{"name": "React", "source_attribution": {{"source_quote": "import React from 'react'\\nfunction App() {{ return <div>...", "source_file": "App.tsx", "source_location": "App.tsx:1-5", "confidence": 0.96, "reasoning": "Import + JSX component shows React usage"}}}}
     * {{"name": "PostgreSQL", "source_attribution": {{"source_quote": "DATABASE_ENGINE = 'django.db.backends.postgresql'", "source_file": "settings.py", "source_location": "settings.py:78", "confidence": 0.95, "reasoning": "Explicit database configuration"}}}}
   - INVALID examples (import only, confidence <= 0.6, DO NOT INCLUDE):
     * {{"name": "TensorFlow", "source_attribution": {{"source_quote": "import tensorflow as tf", "source_file": "utils.py", "source_location": "utils.py:3", "confidence": 0.5, "reasoning": "Import only, no usage found"}}}}
     * {{"name": "FastAPI", "source_attribution": {{"source_quote": "from fastapi import FastAPI", "source_file": "app.py", "source_location": "app.py:1", "confidence": 0.4, "reasoning": "Imported but not instantiated or used"}}}}

4. "architecture_notes": Brief description of architectural approach (string, no attribution needed)
   - Examples: "Microservices with Docker", "Monolithic Django app", "Serverless Lambda functions"

CRITICAL: Only include items that have CONCRETE CODE EVIDENCE.
Every item in patterns and technologies arrays MUST have source_attribution with confidence >= 0.8, or it should be excluded.
HIGH-PRECISION MODE: We prioritize accuracy over completeness. Only extract technologies you are highly confident about.
Technologies with import-only evidence (no usage) should NOT be included (confidence will be < 0.8).

Return ONLY valid JSON with no preamble or explanation. Use this exact structure:
{{
    "project_purpose": "2-3 sentence description of what this code does",
    "patterns": [
        {{"name": "pattern1", "source_attribution": {{"source_quote": "code snippet", "source_file": "file.py", "source_location": "file.py:15-23", "confidence": 0.95, "reasoning": "explanation"}}}}
    ],
    "technologies": [
        {{"name": "tech1", "source_attribution": {{"source_quote": "code snippet", "source_file": "file.py", "source_location": "file.py:5", "confidence": 0.97, "reasoning": "explanation"}}}}
    ],
    "architecture_notes": "Brief architecture description"
}}
"""

        try:
            response = await self.llm_executor.execute(
                prompt=prompt,
                model_name=SOURCE_ANALYSIS_MODEL,  # GPT-5 for complex code reasoning
                max_tokens=SOURCE_ANALYSIS_MAX_TOKENS,  # 3000 for detailed analysis
                temperature=0.3
            )

            data = json.loads(response['content'])

            # ft-030: Extract attribution-enhanced data
            result = {
                'project_purpose': data.get('project_purpose', ''),
                'patterns': data.get('patterns', []),
                'technologies': data.get('technologies', []),
                'architecture_notes': data.get('architecture_notes', '')
            }

            # ft-030: Calculate source attribution metrics for code analysis
            code_attribution_metrics = self._calculate_github_code_attribution_metrics(result)
            result['attribution_coverage'] = code_attribution_metrics['coverage']
            result['inferred_item_ratio'] = code_attribution_metrics['inferred_ratio']
            result['total_items'] = code_attribution_metrics['total_items']
            result['attributed_items'] = code_attribution_metrics['attributed_items']

            logger.info(
                f"[Source Code Analysis] Attribution coverage: {code_attribution_metrics['coverage']:.1%}, "
                f"inferred ratio: {code_attribution_metrics['inferred_ratio']:.1%}"
            )

            return result

        except Exception as e:
            logger.error(f"Failed to analyze source code: {e}")
            return asdict(SourceAnalysisResult())

    async def analyze_infrastructure(self, infra_docs: List[Document]) -> Dict:
        """
        Parse infrastructure configuration files to extract deployment and runtime info.

        Analyzes multiple infrastructure file types:
        - Dockerfile → Base images, runtime detection, multi-stage builds
        - docker-compose.yml → Services, databases, networking
        - .github/workflows/*.yml → GitHub Actions CI/CD
        - .circleci/config.yml → CircleCI pipelines
        - Kubernetes manifests → Deployments, services, ingress

        Args:
            infra_docs (List[Document]): LangChain Document objects with infrastructure files.

        Returns:
            Dict: Analysis results with keys:
                - deployment (List[str]): Deployment platforms (e.g., "Docker", "Kubernetes")
                - runtime (List[str]): Runtime environments (e.g., "Python 3.11", "Node.js 18")
                - services (List[str]): External services (e.g., "PostgreSQL", "Redis", "Nginx")
                - ci_cd (List[str]): CI/CD platforms (e.g., "GitHub Actions", "CircleCI")

        Examples:
            >>> docs = [Document(page_content=dockerfile, metadata={'path': 'Dockerfile'})]
            >>> result = await analyzer.analyze_infrastructure(docs)
            >>> print(result['deployment'])
            ['Docker']
            >>> print(result['runtime'])
            ['Python 3.11']
            >>> print(result['services'])
            ['PostgreSQL', 'Redis']
        """
        result = InfrastructureAnalysisResult()

        for doc in infra_docs:
            file_path = doc.metadata.get('path', '')
            file_name = file_path.split('/')[-1]
            content = doc.page_content

            # Dockerfile analysis
            if 'dockerfile' in file_name.lower():
                result.deployment.append('Docker')
                # Extract base image for runtime detection
                from_match = re.search(r'FROM\s+([\w:\-\.]+)', content, re.IGNORECASE)
                if from_match:
                    base_image = from_match.group(1)
                    if 'python' in base_image:
                        version_match = re.search(r'python:([\d\.]+)', base_image)
                        if version_match:
                            result.runtime = f"Python {version_match.group(1)}"
                        else:
                            result.runtime = "Python"
                    elif 'node' in base_image:
                        version_match = re.search(r'node:([\d\.]+)', base_image)
                        if version_match:
                            result.runtime = f"Node.js {version_match.group(1)}"
                        else:
                            result.runtime = "Node.js"

                # Web server detection
                if 'gunicorn' in content.lower():
                    result.web_server = 'gunicorn'
                elif 'uvicorn' in content.lower():
                    result.web_server = 'uvicorn'
                elif 'nginx' in content.lower():
                    result.web_server = 'nginx'

            # docker-compose analysis
            elif 'docker-compose' in file_name.lower():
                result.deployment.append('Docker Compose')
                # Extract services by name
                services_match = re.search(r'services:\s+(.*?)(?=\n\w|\Z)', content, re.DOTALL)
                if services_match:
                    service_names = re.findall(r'^\s{2}(\w+):', services_match.group(1), re.MULTILINE)
                    for service in service_names:
                        if 'postgres' in service.lower():
                            result.services.append('PostgreSQL')
                        elif 'redis' in service.lower():
                            result.services.append('Redis')
                        elif 'mysql' in service.lower():
                            result.services.append('MySQL')

                # Also check image fields for database detection
                if 'postgres:' in content.lower() and 'PostgreSQL' not in result.services:
                    result.services.append('PostgreSQL')
                if 'mysql:' in content.lower() and 'MySQL' not in result.services:
                    result.services.append('MySQL')
                if 'redis:' in content.lower() and 'Redis' not in result.services:
                    result.services.append('Redis')

            # GitHub Actions analysis
            elif '.github/workflows' in file_path:
                result.ci_cd = 'GitHub Actions'
                result.deployment_automation = True

            # CircleCI analysis
            elif '.circleci/config' in file_path:
                result.ci_cd = 'CircleCI'
                result.deployment_automation = True

            # Kubernetes analysis
            elif file_path.endswith('.yml') or file_path.endswith('.yaml'):
                if 'kind: Deployment' in content or 'apiVersion: apps/v1' in content:
                    result.deployment.append('Kubernetes')
                    # Extract replica count for scaling info
                    replicas_match = re.search(r'replicas:\s+(\d+)', content)
                    if replicas_match:
                        result.scaling = int(replicas_match.group(1))

        # Deduplicate
        result.deployment = list(set(result.deployment))
        result.services = list(set(result.services))

        return asdict(result)

    async def analyze_documentation(self, doc_docs: List[Document]) -> Dict:
        """
        Analyze documentation using LLM to extract project summary, features, and tech stack.

        Uses GPT-5-mini to analyze README, ARCHITECTURE, CONTRIBUTING, and other docs.
        Extracts high-level project understanding that complements code analysis.

        Args:
            doc_docs (List[Document]): LangChain Document objects with documentation files.
                Analyzes first 3 docs, first 1000 chars each to stay within token budget.

        Returns:
            Dict: Analysis results with keys:
                - project_summary (str): 1-2 sentence project description
                - key_features (List[str]): Main features/capabilities
                - tech_stack_mentioned (List[str]): Technologies mentioned in docs
                - architecture_notes (str): High-level architecture description
                - project_type (str): Project category (e.g., "REST API", "CLI tool", "web app")

        Raises:
            OpenAIError: If LLM API call fails

        Examples:
            >>> docs = [Document(page_content=readme_md, metadata={'path': 'README.md'})]
            >>> result = await analyzer.analyze_documentation(docs)
            >>> print(result['project_summary'])
            'A full-stack job application tailoring platform using Django and React'
            >>> print(result['key_features'])
            ['CV generation', 'Cover letter writing', 'Artifact analysis']

        Note:
            Requires OPENAI_API_KEY environment variable.
        """
        if not doc_docs:
            logger.warning("[Documentation Analysis] No documentation files provided - returning empty result")
            return asdict(DocumentationAnalysisResult())

        # Combine all documentation (optimized for $0.50/repo budget)
        combined_docs = "\n\n".join([
            f"=== {doc.metadata.get('path', 'doc')} ===\n{doc.page_content[:DOCS_ANALYSIS_CHARS_PER_DOC]}"
            for doc in doc_docs[:DOCS_ANALYSIS_MAX_DOCS]  # First 12 docs (increased from 5)
        ])

        logger.warning(
            f"[Documentation Analysis] Analyzing {len(doc_docs[:DOCS_ANALYSIS_MAX_DOCS])} docs, "
            f"combined length: {len(combined_docs)} chars"
        )

        prompt = f"""Analyze this project documentation and extract structured information.

CRITICAL ANTI-HALLUCINATION RULES:
- ONLY extract information that is EXPLICITLY STATED in the documentation
- For EVERY extracted item (technologies, achievements, features), provide the exact SOURCE QUOTE from the documentation
- Include source location (file name, section heading, line context)
- Assign a confidence score (0.0-1.0) based on how directly the quote supports the item
- Confidence threshold: >= 0.8 required (only HIGH-CONFIDENCE extractions)
- DO NOT infer or assume information that is not directly stated
- HIGH-PRECISION MODE: We prioritize accuracy over completeness

Documentation:
{combined_docs}

Extract the following in JSON format with SOURCE ATTRIBUTION:

1. "project_summary": A concise 2-3 sentence project summary
   - Sentence 1: What the project does (main purpose)
   - Sentence 2: Key technologies or architectural approach
   - Sentence 3: Main use case or target audience (optional but preferred)

2. "key_features": Array of feature objects with SOURCE ATTRIBUTION
   - Each feature must include:
     * "text": Feature description
     * "source_attribution": Object with:
       - "source_quote": Exact quote from documentation
       - "source_file": File name (e.g., "README.md")
       - "source_location": Full location (e.g., "README.md:## Features")
       - "confidence": 0.0-1.0 (0.95+ for exact match, 0.8-0.9 for clear context, <0.8 rejected)
       - "reasoning": Brief explanation of how quote supports the feature
   - Only extract EXPLICITLY mentioned features
   - Example: {{"text": "Real-time collaboration", "source_attribution": {{"source_quote": "Support for real-time collaborative editing", "source_file": "README.md", "source_location": "README.md:## Features", "confidence": 0.98, "reasoning": "Direct mention in features section"}}}}

3. "tech_stack_mentioned": Array of technology objects with SOURCE ATTRIBUTION
   - Each technology must include:
     * "name": Technology name (e.g., "Django", "React", "PostgreSQL")
     * "source_attribution": Object with source_quote, source_file, source_location, confidence, reasoning
   - Only extract EXPLICITLY mentioned technologies
   - Include: programming languages, frameworks, databases, cloud platforms, tools
   - Examples:
     * {{"name": "Django", "source_attribution": {{"source_quote": "Built with Django 4.2", "source_file": "README.md", "source_location": "README.md:## Tech Stack", "confidence": 0.97, "reasoning": "Direct framework mention with version"}}}}
     * {{"name": "PostgreSQL", "source_attribution": {{"source_quote": "Uses PostgreSQL for data storage", "source_file": "ARCHITECTURE.md", "source_location": "ARCHITECTURE.md:Database", "confidence": 0.95, "reasoning": "Explicit database mention"}}}}

4. "achievements": Array of achievement objects with SOURCE ATTRIBUTION
   - MUST include specific numbers, percentages, scale metrics, or performance data
   - Each achievement must include:
     * "text": The achievement statement
     * "source_attribution": Object with source_quote, source_file, source_location, confidence, reasoning
   - Focus on: scale, performance, adoption, impact, efficiency
   - Examples of QUANTIFIED achievements:
     * {{"text": "Handles 100K+ concurrent users", "source_attribution": {{"source_quote": "Scales to support over 100,000 concurrent users", "source_file": "README.md", "source_location": "README.md:## Performance", "confidence": 0.98, "reasoning": "Direct quote with scale metric"}}}}
     * {{"text": "Reduced latency by 40%", "source_attribution": {{"source_quote": "Achieved 40% reduction in API response time", "source_file": "CHANGELOG.md", "source_location": "CHANGELOG.md:v2.0", "confidence": 0.95, "reasoning": "Specific percentage improvement"}}}}
     * {{"text": "Powers 50K+ active deployments", "source_attribution": {{"source_quote": "Used in over 50,000 production deployments", "source_file": "README.md", "source_location": "README.md:## Adoption", "confidence": 0.92, "reasoning": "Direct adoption metric"}}}}
   - If no quantified achievements exist in documentation, return empty array []

5. "project_type": String describing the project type (e.g., "REST API", "CLI tool", "web app", "library")

CRITICAL: Only include items that have CONCRETE EVIDENCE in the documentation.
Every item in tech_stack_mentioned, key_features, and achievements arrays MUST have source_attribution with confidence >= 0.8, or it should be excluded.
HIGH-PRECISION MODE: We prioritize accuracy over completeness. Only extract items you are highly confident about.

Return ONLY valid JSON with no preamble or explanation. Use this exact structure:
{{
    "project_summary": "2-3 sentence summary here",
    "key_features": [
        {{"text": "feature1", "source_attribution": {{"source_quote": "quote", "source_file": "README.md", "source_location": "README.md:## Features", "confidence": 0.95, "reasoning": "explanation"}}}}
    ],
    "tech_stack_mentioned": [
        {{"name": "tech1", "source_attribution": {{"source_quote": "quote", "source_file": "README.md", "source_location": "README.md:## Tech Stack", "confidence": 0.97, "reasoning": "explanation"}}}}
    ],
    "achievements": [
        {{"text": "achievement with metric", "source_attribution": {{"source_quote": "quote", "source_file": "README.md", "source_location": "README.md:## Performance", "confidence": 0.98, "reasoning": "explanation"}}}}
    ],
    "project_type": "type here"
}}
"""

        try:
            response = await self.llm_executor.execute(
                prompt=prompt,
                model_name=DOCS_ANALYSIS_MODEL,  # GPT-5 for quality summaries
                max_tokens=DOCS_ANALYSIS_MAX_TOKENS,  # 10000 for detailed understanding
            )

            data = json.loads(response['content'])

            # ft-030: Extract attribution-enhanced data
            result = {
                'project_summary': data.get('project_summary', ''),
                'key_features': data.get('key_features', []),
                'tech_stack_mentioned': data.get('tech_stack_mentioned', []),
                'achievements': data.get('achievements', []),
                'architecture_notes': '',
                'project_type': data.get('project_type', '')
            }

            # ft-030: Calculate source attribution metrics
            attribution_metrics = self._calculate_github_attribution_metrics(result)
            result['attribution_coverage'] = attribution_metrics['coverage']
            result['inferred_item_ratio'] = attribution_metrics['inferred_ratio']
            result['total_items'] = attribution_metrics['total_items']
            result['attributed_items'] = attribution_metrics['attributed_items']

            # Warn if summary is empty despite successful parsing
            if not result['project_summary']:
                logger.warning(
                    f"[Documentation Analysis] LLM returned empty project_summary. "
                    f"Response content: {response['content'][:200]}..."
                )
            else:
                logger.info(
                    f"[Documentation Analysis] Successfully extracted summary "
                    f"({len(result['project_summary'])} chars), "
                    f"attribution coverage: {attribution_metrics['coverage']:.1%}, "
                    f"inferred ratio: {attribution_metrics['inferred_ratio']:.1%}"
                )

            return result

        except json.JSONDecodeError as e:
            logger.warning(
                f"[Documentation Analysis] Failed to parse JSON from LLM response: {e}. "
                f"Response content: {response.get('content', '')[:500]}..."
            )
            return asdict(DocumentationAnalysisResult())
        except Exception as e:
            logger.warning(
                f"[Documentation Analysis] Failed to analyze documentation: {e}. "
                f"Returning empty result.",
                exc_info=True
            )
            return asdict(DocumentationAnalysisResult())

    def _infer_purpose_from_dependencies(self, config_analysis: Dict) -> str:
        """
        Infer project purpose from dependency analysis.

        Returns a basic project description based on detected technologies.
        Fallback when no documentation or source code purpose available.
        """
        technologies = set(t.lower() for t in config_analysis.get('technologies', []))

        # Web frameworks → Web application
        if technologies & {'react', 'next.js', 'vue', 'angular', 'svelte', 'nuxt', 'gatsby'}:
            return "A web application"

        # API frameworks → REST API
        if technologies & {'django rest framework', 'fastapi', 'express', 'flask-restful', 'graphql', 'nestjs'}:
            return "A REST API service"

        # CLI tools
        if technologies & {'click', 'argparse', 'commander', 'clap', 'cobra', 'yargs'}:
            return "A command-line tool"

        # Data/ML
        if technologies & {'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras'}:
            return "A data processing or machine learning project"

        # Backend frameworks
        if technologies & {'django', 'flask', 'rails', 'spring', 'laravel', 'fastapi'}:
            return "A backend web service"

        # Mobile
        if technologies & {'react native', 'flutter', 'swift', 'kotlin', 'swiftui'}:
            return "A mobile application"

        # Database/Storage
        if technologies & {'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch'}:
            return "A data storage or database project"

        # Default - use first technology
        tech_list = list(config_analysis.get('technologies', []))
        if tech_list:
            return f"A {tech_list[0]} project"

        return ""

    def _enrich_summary(
        self,
        base_summary: str,
        technologies: List[str],
        patterns: List[str],
        infra: Dict
    ) -> str:
        """
        Enrich base summary with architectural and technical context.

        Transforms basic summaries into informative 2-3 sentence descriptions.

        Example:
        Input: "A web application"
        Output: "A web application built with React, TypeScript, and Next.js,
                 containerized with Docker and using PostgreSQL for data storage"
        """
        if not base_summary:
            return ""

        enrichments = []

        # Add top 3 technologies (if not already mentioned)
        if technologies:
            tech_str = ', '.join(technologies[:3])
            if not any(tech.lower() in base_summary.lower() for tech in technologies[:3]):
                enrichments.append(f"built with {tech_str}")

        # Add deployment info
        deployment = infra.get('deployment', [])
        if 'Docker' in deployment:
            enrichments.append("containerized with Docker")
        elif 'Kubernetes' in deployment:
            enrichments.append("orchestrated with Kubernetes")

        # Add database
        services = infra.get('services', [])
        databases = [s for s in services if s in ['PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQLite']]
        if databases and databases[0].lower() not in base_summary.lower():
            enrichments.append(f"using {databases[0]} for data storage")

        # Combine (max 2 enrichments to keep it 2-3 sentences)
        if enrichments:
            return f"{base_summary}, {', '.join(enrichments[:2])}"

        return base_summary

    async def synthesize_insights(
        self,
        config,
        source,
        infra,
        docs
    ) -> HybridAnalysisResult:
        """
        Cross-reference all analysis results to detect conflicts and calculate consistency.

        This is the final synthesis step that:
        1. Aggregates technologies from all sources (config, source, infra, docs)
        2. Calculates consistency score based on cross-source agreement
        3. Detects conflicts (e.g., config says Django but source uses Flask)
        4. Applies fuzzy matching for partial tech names (e.g., "Django REST Framework" contains "Django")
        5. Boosts scores for reasonable agreement (≥50% → +50% boost, max 1.0)

        Consistency scoring logic:
        - For each technology, count how many sources mention it
        - Score = (sources mentioning / 4) averaged across all technologies
        - Boost by 50% if score ≥ 0.50 (accounts for expected gaps)

        Args:
            config (Dict): Config file analysis results (from analyze_config_files)
            source (Dict): Source code analysis results (from analyze_source_code)
            infra (Dict): Infrastructure analysis results (from analyze_infrastructure)
            docs (Dict): Documentation analysis results (from analyze_documentation)

        Returns:
            HybridAnalysisResult: Combined analysis with:
                - config_analysis (Dict): Original config results
                - source_analysis (Dict): Original source results
                - infrastructure_analysis (Dict): Original infra results
                - documentation_analysis (Dict): Original docs results
                - consistency_score (float): 0.0-1.0 consistency score
                - confidence (float): Overall confidence (based on consistency)
                - conflict_notes (str): Descriptions of any detected conflicts

        Examples:
            >>> config = await analyzer.analyze_config_files(config_docs)
            >>> source = await analyzer.analyze_source_code(source_docs)
            >>> infra = await analyzer.analyze_infrastructure(infra_docs)
            >>> docs = await analyzer.analyze_documentation(doc_docs)
            >>>
            >>> result = await analyzer.synthesize_insights(config, source, infra, docs)
            >>> print(result.consistency_score)
            0.91
            >>> print(result.conflict_notes)
            'Config mentions PostgreSQL, but infrastructure uses MySQL'

        Note:
            Accepts both dict and dataclass inputs for backwards compatibility.
        """
        # Convert dataclass to dict if needed
        if hasattr(config, '__dataclass_fields__'):
            config = asdict(config)
        if hasattr(source, '__dataclass_fields__'):
            source = asdict(source)
        if hasattr(infra, '__dataclass_fields__'):
            infra = asdict(infra)
        if hasattr(docs, '__dataclass_fields__'):
            docs = asdict(docs)

        # ===== MULTI-SOURCE SUMMARY GENERATION =====

        # Tier 1: Documentation summary (best quality)
        doc_summary = docs.get('project_summary', '').strip()

        # Tier 2: Source code purpose (good quality)
        source_purpose = source.get('project_purpose', '').strip()

        # Tier 3: Dependency-inferred purpose (basic quality)
        config_purpose = self._infer_purpose_from_dependencies(config)

        # Select best available summary
        if doc_summary:
            base_summary = doc_summary
            summary_source = 'documentation'
            logger.info(f"[Synthesis] Using documentation summary (highest quality): {len(doc_summary)} chars")
        elif source_purpose:
            base_summary = source_purpose
            summary_source = 'source_code'
            logger.info(f"[Synthesis] Using source code purpose (medium quality): {len(source_purpose)} chars")
        elif config_purpose:
            base_summary = config_purpose
            summary_source = 'config_inference'
            logger.info(f"[Synthesis] Using dependency-inferred purpose (basic quality): {len(config_purpose)} chars")
        else:
            base_summary = ""
            summary_source = 'none'
            logger.warning("[Synthesis] No summary sources available - will use GitHub metadata fallback")

        # Enrich summary with additional context (if summary is basic)
        if base_summary and summary_source in ['config_inference', 'none']:
            enriched_summary = self._enrich_summary(
                base_summary=base_summary,
                technologies=config.get('technologies', []),
                patterns=source.get('patterns', []),
                infra=infra
            )
        else:
            enriched_summary = base_summary

        # Update docs with enriched summary and source tracking
        docs = {
            **docs,
            'project_summary': enriched_summary,
            'summary_source': summary_source
        }

        # ft-030: Helper to extract tech names from attributed or string format
        def extract_tech_names(items):
            """Extract technology names, handling both strings and attributed dicts"""
            names = set()
            for item in items:
                if isinstance(item, str):
                    names.add(item.lower())
                elif isinstance(item, dict) and 'name' in item:
                    names.add(item['name'].lower())
            return names

        # Extract all technologies from each source (ft-030: handles attributed format)
        config_techs = extract_tech_names(config.get('technologies', []))
        source_techs = extract_tech_names(source.get('technologies', []))
        infra_services = set(s.lower() for s in infra.get('services', []) if isinstance(s, str))
        docs_techs = extract_tech_names(docs.get('tech_stack_mentioned', []))

        # ft-030 HIGH-PRECISION: Removed string matching fallback
        # Previously extracted from project_summary if tech_stack_mentioned empty
        # This created unattributed technologies (hallucinations from keyword presence)
        if not docs_techs:
            logger.debug(
                "[ft-030 HIGH-PRECISION] No technologies in documentation analysis. "
                "Accepting empty result (no keyword fallback)."
            )

        # Combine all tech mentions
        all_techs = config_techs | source_techs | infra_services | docs_techs

        # Calculate consistency: how many sources agree on each tech?
        # Use fuzzy matching: "Django REST Framework" contains "Django"
        consistency_scores = []
        conflicts = []

        def tech_mentioned(tech: str, tech_set: set) -> bool:
            """Check if tech is mentioned, including partial matches"""
            if tech in tech_set:
                return True
            # Check if any item in tech_set contains this tech as substring
            return any(tech in item or item in tech for item in tech_set)

        for tech in all_techs:
            sources_mentioning = sum([
                tech_mentioned(tech, config_techs),
                tech_mentioned(tech, source_techs),
                tech_mentioned(tech, infra_services),
                tech_mentioned(tech, docs_techs)
            ])
            consistency_scores.append(sources_mentioning / 4.0)  # 4 sources max

        # Detect conflicts (e.g., MySQL in config, PostgreSQL in source)
        db_techs = {'mysql', 'postgresql', 'sqlite', 'mongodb'}
        config_dbs = config_techs & db_techs
        source_dbs = source_techs & db_techs
        infra_dbs = infra_services & db_techs

        if config_dbs and source_dbs and config_dbs != source_dbs:
            conflicts.append(f"Database mismatch: config has {', '.join(sorted(config_dbs)).title()}, source has {', '.join(sorted(source_dbs)).title()}")

        # Frontend framework conflicts
        frontend_frameworks = {'react', 'vue', 'vue.js', 'angular'}
        config_frontend = config_techs & frontend_frameworks
        source_frontend = source_techs & frontend_frameworks

        if config_frontend and source_frontend and config_frontend != source_frontend:
            # Format with proper casing (capitalize first letter)
            config_names = ', '.join(t.title() if '.' not in t else t for t in sorted(config_frontend))
            source_names = ', '.join(t.title() if '.' not in t else t for t in sorted(source_frontend))
            conflicts.append(f"Frontend mismatch: config has {config_names}, source has {source_names}")

        # Calculate overall consistency score
        if consistency_scores:
            consistency_score = sum(consistency_scores) / len(consistency_scores)
            # Boost for reasonable agreement (accounts for expected gaps like app frameworks not in infra)
            if consistency_score >= 0.50:
                consistency_score = min(consistency_score * 1.50, 1.0)  # 50% boost, capped at 1.0
        else:
            consistency_score = 0.0

        # Lower score if conflicts detected
        if conflicts:
            consistency_score *= 0.75  # 25% penalty for conflicts

        # Calculate confidence (higher consistency = higher confidence)
        confidence = min(consistency_score * 1.1, 1.0)  # Slightly boost confidence

        return HybridAnalysisResult(
            config_analysis=config,
            source_analysis=source,
            infrastructure_analysis=infra,
            documentation_analysis=docs,
            consistency_score=consistency_score,
            confidence=confidence,
            conflict_notes="; ".join(conflicts) if conflicts else ""
        )

    def _calculate_github_attribution_metrics(self, extracted: Dict) -> Dict[str, float]:
        """
        Calculate source attribution quality metrics for GitHub extraction (ft-030).

        Analyzes the extracted data to compute:
        - Attribution coverage: % of items with source quotes (target >= 95%)
        - Inferred item ratio: % of low-confidence inferred items (target <= 20%)

        Args:
            extracted: Dictionary with key_features, tech_stack_mentioned, achievements arrays

        Returns:
            Dict with:
                - coverage: float (0.0-1.0) - percentage of items with source attribution
                - inferred_ratio: float (0.0-1.0) - percentage of items with low confidence
                - total_items: int - total number of extracted items
                - attributed_items: int - number of items with source quotes
        """
        total_items = 0
        attributed_items = 0
        inferred_items = 0

        # Count items in key_features
        for feature in extracted.get('key_features', []):
            total_items += 1
            if isinstance(feature, dict):
                attribution = feature.get('source_attribution')
                if attribution and attribution.get('source_quote'):
                    attributed_items += 1
                    if attribution.get('confidence', 0.0) < 0.5:
                        inferred_items += 1

        # Count items in tech_stack_mentioned
        for tech in extracted.get('tech_stack_mentioned', []):
            total_items += 1
            if isinstance(tech, dict):
                attribution = tech.get('source_attribution')
                if attribution and attribution.get('source_quote'):
                    attributed_items += 1
                    if attribution.get('confidence', 0.0) < 0.5:
                        inferred_items += 1

        # Count items in achievements
        for achievement in extracted.get('achievements', []):
            total_items += 1
            if isinstance(achievement, dict):
                attribution = achievement.get('source_attribution')
                if attribution and attribution.get('source_quote'):
                    attributed_items += 1
                    if attribution.get('confidence', 0.0) < 0.5:
                        inferred_items += 1

        # Calculate metrics
        coverage = attributed_items / total_items if total_items > 0 else 0.0
        inferred_ratio = inferred_items / total_items if total_items > 0 else 0.0

        return {
            'coverage': coverage,
            'inferred_ratio': inferred_ratio,
            'total_items': total_items,
            'attributed_items': attributed_items
        }

    def _calculate_github_code_attribution_metrics(self, extracted: Dict) -> Dict[str, float]:
        """
        Calculate source attribution quality metrics for GitHub code analysis (ft-030).

        Analyzes the extracted code analysis data to compute:
        - Attribution coverage: % of items with source code evidence (target >= 95%)
        - Inferred item ratio: % of low-confidence inferred items (target <= 20%)

        Args:
            extracted: Dictionary with patterns and technologies arrays

        Returns:
            Dict with:
                - coverage: float (0.0-1.0) - percentage of items with source attribution
                - inferred_ratio: float (0.0-1.0) - percentage of items with low confidence
                - total_items: int - total number of extracted items
                - attributed_items: int - number of items with source code evidence
        """
        total_items = 0
        attributed_items = 0
        inferred_items = 0

        # Count items in patterns
        for pattern in extracted.get('patterns', []):
            total_items += 1
            if isinstance(pattern, dict):
                attribution = pattern.get('source_attribution')
                if attribution and attribution.get('source_quote'):
                    attributed_items += 1
                    if attribution.get('confidence', 0.0) < 0.5:
                        inferred_items += 1

        # Count items in technologies
        for tech in extracted.get('technologies', []):
            total_items += 1
            if isinstance(tech, dict):
                attribution = tech.get('source_attribution')
                if attribution and attribution.get('source_quote'):
                    attributed_items += 1
                    if attribution.get('confidence', 0.0) < 0.5:
                        inferred_items += 1

        # Calculate metrics
        coverage = attributed_items / total_items if total_items > 0 else 0.0
        inferred_ratio = inferred_items / total_items if total_items > 0 else 0.0

        return {
            'coverage': coverage,
            'inferred_ratio': inferred_ratio,
            'total_items': total_items,
            'attributed_items': attributed_items
        }
