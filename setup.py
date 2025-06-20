from setuptools import setup, find_packages

setup(
    name="mcp-orchestrator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "mcp>=0.1.0",
        "numpy>=1.24.0",
        "requests>=2.31.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mcp-orchestrator=mcp_orchestrator.server:main",
        ],
    },
    author="Jordan Ehrig",
    author_email="jordan@example.com",
    description="Universal MCP router with intelligent tool discovery",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/SamuraiBuddha/mcp-orchestrator",
)