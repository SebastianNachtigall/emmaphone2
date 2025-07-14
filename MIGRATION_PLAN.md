# EmmaPhone2 Repository Restructuring Migration Plan

## 🎯 **Project Context**
This document outlines the safe migration from the current flat repository structure to a new organized structure that supports both web application and Raspberry Pi components.

**Current Status:** Working EmmaPhone2 web application with voice calling functionality deployed on Railway.

**Goal:** Restructure repository to support future Raspberry Pi development while maintaining web app functionality.

## 📁 **Target Structure**
```
emmaphone2/
├── web/                    # Web application (current root files)
│   ├── src/               # Current src/
│   ├── public/            # Current public/
│   ├── database/          # Current database/
│   └── package.json       # Current package.json
├── pi/                     # Raspberry Pi application (new)
│   ├── src/
│   ├── setup-wizard/      # WiFi setup interface
│   ├── hardware/          # GPIO, audio drivers
│   ├── systemd/           # Service files
│   └── package.json
├── shared/                 # Shared code between web and pi (new)
│   ├── auth/              # Authentication logic
│   ├── api/               # API interfaces
│   └── types/             # TypeScript definitions
├── services/               # Microservices (already exists)
│   └── livekit/           # LiveKit WebRTC service (already correct)
│       ├── Dockerfile
│       ├── livekit.yaml
│       └── start-livekit.sh
├── docs/                   # Documentation (current *.md files)
│   ├── migration/         # This plan and related docs
│   ├── pi-setup.md
│   └── deployment.md
├── docker/                 # Container configs (current docker files)
│   ├── web/               # Current Dockerfile
│   └── pi/                # Future Pi containers
└── README.md              # Updated main readme
```

## 🔍 **Critical Dependencies Analysis**

### **File Reference Summary (65+ references identified):**

**High Risk Dependencies:**
- `package.json` → `src/server.js` (entry point)
- `src/server.js` → `src/database.js` (module import)
- `src/database.js` → `database/schema.sql` (schema file)
- `public/index.html` → `public/js/*.js` (frontend assets)
- `public/login.html` → `public/css/*.css` (stylesheets)
- Docker files → source directories (build paths)

**Medium Risk Dependencies:**
- JavaScript API calls → backend endpoints
- Static file serving paths in Express
- SSL certificate paths
- Docker volume mounts

**Detailed File Reference Map:**
- `src/server.js`: 15+ file path references
- `public/index.html`: 4 script/link references (including `main-simple.js`)
- `public/login.html`: 3 script/link references
- Docker files: 12+ COPY/volume references
- JavaScript files: 35+ API endpoint references

**JavaScript File Cleanup Required:**
- Current: `main-simple.js` (active) + `main-old.js` (legacy)
- Target: `main.js` (clean naming) + remove legacy file
- HTML update needed: `s/main-simple.js/main.js/g`

## 📋 **Step-by-Step Migration Plan**

### **Phase 1: Preparation & Validation** ⚙️

**Step 1.1: Create Migration Branch**
```bash
git checkout -b refactor-file-structure
git push -u origin refactor-file-structure
```

**Step 1.2: Document Current State**
```bash
# Verify current functionality works
npm start  # Test server starts
# Manual test: login, contacts, voice calling
echo "✅ Verified working state" >> MIGRATION_LOG.md
git add . && git commit -m "Checkpoint: Working state before refactoring"
```

**Step 1.3: Create Rollback Points**
```bash
git tag checkpoint-start
git push --tags
```

### **Phase 2: Create New Structure** 🏗️

**Step 2.1: Create Target Directories**
```bash
mkdir -p web/src web/public web/database
mkdir -p pi/src pi/setup-wizard pi/hardware pi/systemd
mkdir -p shared/auth shared/api shared/types
mkdir -p docker/web docker/pi
mkdir -p docs/migration
mkdir -p services/livekit  # LiveKit service already exists, ensure target exists
```

**Step 2.2: Copy (Don't Move) Core Files**
```bash
# Copy to maintain working original during transition
cp -r src/ web/src/
cp -r public/ web/public/
cp -r database/ web/database/
cp package*.json web/
cp -r config/ web/config/
cp -r ssl/ web/ssl/ 2>/dev/null || echo "No ssl directory found"
cp -r certs/ web/certs/ 2>/dev/null || echo "No certs directory found"

# LiveKit service stays in services/livekit/ (already in correct location)
echo "✅ LiveKit service already correctly structured in services/livekit/"

git add . && git commit -m "Phase 2: Copy files to new web/ structure"
git tag checkpoint-phase2
```

### **Phase 3: Update Web App References** 🔧

**Step 3.1: Update Web Package.json**
```bash
cd web
# Edit package.json:
# "main": "src/server.js" (no change needed - relative path works)
# "start": "node src/server.js" (no change needed)
# Working directory will be web/ so paths are correct
cd ..
git add . && git commit -m "Phase 3.1: Verified web package.json paths"
```

**Step 3.2: Create New Docker Configuration**
```bash
# Move and update main Dockerfile
mv Dockerfile docker/web/Dockerfile

# Edit docker/web/Dockerfile:
# Change: COPY src/ ./src/ → COPY web/src/ ./src/
# Change: COPY public/ ./public/ → COPY web/public/ ./public/
# Change: COPY database/ ./database/ → COPY web/database/ ./database/
# Change: COPY package*.json ./ → COPY web/package*.json ./

git add . && git commit -m "Phase 3.2: Update Docker web configuration"
```

**Step 3.3: Update Docker Compose Files**
```bash
# Update docker-compose.yml:
# Change build context: build: . → build: ./docker/web
# Update volume mounts:
#   - ./src:/app/src → ./web/src:/app/src
#   - ./public:/app/public → ./web/public:/app/public
#   - ./data:/app/data → ./web/data:/app/data

# Update docker-compose.dev.yml similarly

# LiveKit service in docker-compose.yml should remain:
# livekit:
#   build: ./services/livekit  # Already correct path
#   depends_on: [redis]

git add . && git commit -m "Phase 3.3: Update Docker Compose configurations"
```

### **Phase 4: Test New Structure** ✅

**Step 4.1: Test Web App in New Location**
```bash
cd web
npm install
npm start &
sleep 5

# Test critical functionality:
curl -f http://localhost:3000/login.html || echo "❌ Login page failed"
curl -f http://localhost:3000/css/style.css || echo "❌ CSS failed"
curl -f http://localhost:3000/js/main-simple.js || echo "❌ JS failed"

pkill node
echo "✅ Web app functional from new location" >> ../MIGRATION_LOG.md
cd ..
```

**Step 4.2: Test Docker Build**
```bash
# Test new Docker configuration
docker-compose -f docker-compose.yml build web
docker-compose -f docker-compose.yml up -d web
sleep 10

# Test containerized app
curl -f http://localhost:8080/login.html || echo "❌ Container test failed"

docker-compose down
echo "✅ Docker build successful" >> MIGRATION_LOG.md
git add . && git commit -m "Phase 4: Verified new structure works"
git tag checkpoint-phase4
```

### **Phase 5: Create Shared Components** 🔄

**Step 5.1: Extract Authentication Logic**
```bash
# Create shared authentication module
mkdir -p shared/auth

# Extract common auth functions from web/src/server.js
# Create shared/auth/middleware.js with reusable auth logic
# Update web/src/server.js to use shared auth

git add . && git commit -m "Phase 5.1: Extract shared authentication"
```

**Step 5.2: Extract API Interfaces**
```bash
# Create shared API definitions
mkdir -p shared/api

# Extract API route definitions and types
# Create shared/api/endpoints.js
# Create shared/api/types.js for request/response types

git add . && git commit -m "Phase 5.2: Create shared API interfaces"
```

**Step 5.3: Clean Up JavaScript File Naming**
```bash
# Rename main-simple.js to main.js for clarity
cd web/public/js
mv main-simple.js main.js
rm main-old.js  # Remove legacy file

# Update HTML reference
cd ../..
sed -i '' 's/js\/main-simple.js/js\/main.js/g' index.html

git add . && git commit -m "Phase 5.3: Clean up JavaScript file naming"
git tag checkpoint-phase5
```

### **Phase 6: Clean Up Old Structure** 🗑️

**Step 6.1: Remove Original Files (After Verification)**
```bash
# ONLY after confirming new structure works for 24+ hours
# Remove old files:
rm -rf src/
rm -rf public/
rm -rf database/
rm package*.json
rm -rf config/
rm -rf ssl/ 2>/dev/null || echo "No ssl directory found"
rm -rf certs/ 2>/dev/null || echo "No certs directory found"

# Move remaining files to appropriate locations
mv *.md docs/ 2>/dev/null || echo "No markdown files in root"
mv docker-compose*.yml docker/ 2>/dev/null || echo "No docker-compose files in root"
mv livekit-*.yaml docker/ 2>/dev/null || echo "No livekit config files in root"

# IMPORTANT: Leave services/livekit/ untouched - it's already correctly structured
echo "✅ services/livekit/ remains in correct location for Railway deployment"

git add . && git commit -m "Phase 6: Remove old file structure"
git tag checkpoint-final
```

### **Phase 7: Initialize Pi Project** 🥧

**Step 7.1: Create Pi Project Structure**
```bash
cd pi
npm init -y

# Configure package.json for Pi
cat > package.json << EOF
{
  "name": "emmaphone2-pi",
  "version": "1.0.0",
  "description": "EmmaPhone2 Raspberry Pi Application",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js",
    "setup": "node src/setup-wizard/index.js"
  },
  "dependencies": {
    "express": "^4.18.0",
    "hostapd": "^1.0.0"
  }
}
EOF

# Create basic Pi structure
mkdir -p src/setup-wizard src/hardware src/audio systemd

cd ..
git add . && git commit -m "Phase 7: Initialize Pi project structure"
```

## 🛡️ **Safety Measures**

### **Rollback Commands:**
```bash
# If something breaks in any phase:
git reset --hard checkpoint-phaseN
git clean -fd

# If major issues occur:
git checkout main
git branch -D refactor-file-structure
```

### **Verification Script:**
```bash
#!/bin/bash
# verify-migration.sh
echo "🔍 Testing migration state..."

cd web
echo "Testing web app..."
npm start &
PID=$!
sleep 5

# Test critical endpoints
echo "Testing login page..."
curl -f http://localhost:3000/login.html > /dev/null && echo "✅ Login OK" || echo "❌ Login failed"

echo "Testing main app..."
curl -f http://localhost:3000/ > /dev/null && echo "✅ Main app OK" || echo "❌ Main app failed"

echo "Testing assets..."
curl -f http://localhost:3000/css/style.css > /dev/null && echo "✅ CSS OK" || echo "❌ CSS failed"
curl -f http://localhost:3000/js/main-simple.js > /dev/null && echo "✅ JS OK" || echo "❌ JS failed"

kill $PID
cd ..
echo "🎯 Verification complete"
```

## 📊 **Migration Risk Assessment**

| Phase | Risk Level | Time Est. | Rollback Ease | Critical Dependencies |
|-------|------------|-----------|---------------|----------------------|
| 1     | 🟢 Low     | 10 min    | ✅ Easy       | None                 |
| 2     | 🟢 Low     | 15 min    | ✅ Easy       | Disk space           |
| 3     | 🟡 Medium  | 30 min    | ✅ Easy       | Docker configs       |
| 4     | 🟡 Medium  | 20 min    | ⚠️ Moderate   | All file paths       |
| 5     | 🟢 Low     | 45 min    | ✅ Easy       | Code extraction      |
| 6     | 🔴 High    | 15 min    | ❌ Difficult  | File system          |
| 7     | 🟢 Low     | 30 min    | ✅ Easy       | None                 |

**Total Estimated Time:** 2.5-3 hours
**Recommended Approach:** Conservative with 24-hour verification between phases 4-6

## 🚀 **Post-Migration Next Steps**

1. **Pi Development Setup**
   - Set up Pi Zero 2 development environment
   - Implement WiFi setup wizard
   - Create hardware abstraction layer

2. **Shared Component Enhancement**
   - Expand shared authentication
   - Create common API client
   - Add TypeScript definitions

3. **CI/CD Updates**
   - Update build scripts for new structure
   - Configure separate deployment pipelines
   - Add cross-platform testing

## 📝 **Migration Log Template**

Create `MIGRATION_LOG.md` during execution:
```markdown
# Migration Execution Log

## Phase 1 - Preparation
- [ ] Branch created: `refactor-file-structure`
- [ ] Current state verified
- [ ] Checkpoint created: `checkpoint-start`

## Phase 2 - Structure Creation
- [ ] Directories created
- [ ] Files copied to web/
- [ ] Checkpoint created: `checkpoint-phase2`

## Phase 3 - Reference Updates
- [ ] Package.json updated
- [ ] Docker files updated
- [ ] Docker compose updated

## Phase 4 - Testing
- [ ] Web app tested from new location
- [ ] Docker build tested
- [ ] All functionality verified
- [ ] Checkpoint created: `checkpoint-phase4`

## Issues Encountered
[Document any problems and solutions here]

## Rollback Actions Taken
[Document any rollbacks here]
```

## 🔧 **For Future Claude Code Sessions**

**Quick Context:**
This migration plan restructures the EmmaPhone2 repository to support both web and Raspberry Pi development. The current working web application is deployed on Railway with full voice calling functionality.

**Important Railway Deployment Notes:**
- LiveKit service is already correctly structured in `services/livekit/`
- Railway builds from the subdirectory using the existing Dockerfile
- LiveKit configuration includes Railway-specific environment handling
- Do NOT move the `services/livekit/` directory during migration

**Current Status:** [UPDATE THIS WHEN STARTING]
- [ ] Not started
- [ ] In progress at Phase X
- [ ] Completed

**Critical Commands to Remember:**
- Test current state: `cd web && npm start`
- Rollback: `git reset --hard checkpoint-phaseN`
- Verify: `./verify-migration.sh`

**Important:** Always test web app functionality after each phase before proceeding.