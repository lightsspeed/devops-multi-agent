#!/usr/bin/env bash

# Create directory tree
mkdir -p devops-multi-agent/backend/src/devops_agents/agents
mkdir -p devops-multi-agent/backend/tests
mkdir -p devops-multi-agent/frontend/src/{components/ui,pages,lib,hooks,services}
mkdir -p devops-multi-agent/frontend/public
mkdir -p devops-multi-agent/docs

cd devops-multi-agent

# Backend files
touch backend/src/devops_agents/{__init__.py,config.py,state.py,graph.py}
touch backend/src/devops_agents/agents/{__init__.py,kubernetes.py,aws.py,linux.py}
touch backend/tests/__init__.py
echo "Monorepo folder structure created successfully!".ts,components.json}
Monorepo folder structure created successfully!
devops-multi-agent (feature/phase-01-three-agents #) $ #!/usr/bin/env bash

# 1. Create new directory structure
mkdir -p backend/src/devops_agents/agents
mkdir -p backend/tests
mkdir -p frontend/src/{components/ui,pages,lib,hooks,services}
mkdir -p frontend/public docs

# 2. Move existing Python backend files into backend/
mv src/* backend/src/ 2>/dev/null || true
rm -rf src
mv tests/* backend/tests/ 2>/dev/null || true
rm -rf tests
mv pyproject.toml langgraph.json .env.example backend/ 2>/dev/null || true

echo "Directory structure updated successfully!"config.ts,components.json}inux.py}
mkdir: cannot create directory ‘backend’: No such file or directory
mkdir: cannot create directory ‘backend’: No such file or directory
mkdir: cannot create directory ‘frontend’: No such file or directory
mkdir: cannot create directory ‘frontend/src/pages’: No such file or directory
mkdir: cannot create directory ‘frontend/src/lib’: No such file or directory
mkdir: cannot create directory ‘frontend/src/hooks’: No such file or directory
mkdir: cannot create directory ‘frontend’: No such file or directory
mkdir: cannot create directory ‘frontend’: No such file or directory
mkdir: cannot create directory ‘docs’: No such file or directory
touch: cannot touch 'backend/src/devops_agents/agents/__init__.py': No such file or directory
touch: cannot touch 'backend/src/devops_agents/agents/kubernetes.py': No such file or directory
touch: cannot touch 'backend/src/devops_agents/agents/aws.py': No such file or directory
touch: cannot touch 'backend/src/devops_agents/agents/linux.py': No such file or directory
touch: cannot touch 'frontend/src/App.tsx': No such file or directory
touch: cannot touch 'frontend/src/main.tsx': No such file or directory
touch: cannot touch 'frontend/package.json': No such file or directory
touch: cannot touch 'frontend/tsconfig.json': No such file or directory
touch: cannot touch 'frontend/vite.config.ts': No such file or directory
touch: cannot touch 'frontend/components.json': No such file or directory
Directory structure updated successfully!