# LMS Technical Plan: Jankyard Academy

## Executive Summary

Transform Jankyard.ai from a collection of standalone prompt engineering challenges into a structured Learning Management System (LMS) for corporate prompt engineering training.

**Goal**: Create an e-learning platform that teaches practical prompt engineering skills through interactive, gamified lessons with measurable progress tracking.

---

## 1. Current Architecture Analysis

### 1.1 Existing Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CURRENT DATABASE SCHEMA                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐      ┌──────────────────┐      ┌───────────────────┐      │
│  │    users     │      │   submissions    │      │   leaderboard     │      │
│  ├──────────────┤      ├──────────────────┤      ├───────────────────┤      │
│  │ id (PK)      │──┐   │ id (PK)          │   ┌──│ id (PK)           │      │
│  │ username     │  │   │ user_id (FK)     │◄──┤  │ challenge_name    │      │
│  │ email        │  └──►│ challenge_name   │   │  │ user_id (FK)      │◄─────┤
│  │ hashed_pass  │      │ difficulty       │   │  │ username          │      │
│  │ is_active    │      │ score            │   │  │ difficulty        │      │
│  │ created_at   │      │ steps            │   │  │ best_score        │      │
│  └──────────────┘      │ success          │   │  │ best_steps        │      │
│                        │ status           │   └──│ submission_id(FK) │      │
│  ┌──────────────┐      │ logs (JSON)      │      │ updated_at        │      │
│  │ rate_limits  │      │ agent_code       │      └───────────────────┘      │
│  ├──────────────┤      │ error_message    │                                  │
│  │ id (PK)      │      │ created_at       │                                  │
│  │ identifier   │      └──────────────────┘                                  │
│  │ endpoint     │                                                            │
│  │ request_cnt  │                                                            │
│  │ window_start │                                                            │
│  └──────────────┘                                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Current Models Summary

| Model | Purpose | Fields | Notes |
|-------|---------|--------|-------|
| `User` | User accounts | id, username, email, hashed_password, is_active, created_at | Supports anonymous (null password) |
| `Submission` | Challenge attempts | id, user_id, challenge_name, difficulty, score, steps, success, status, logs, agent_code | Stores full execution logs as JSON |
| `LeaderboardEntry` | Best scores | id, challenge_name, user_id, username, difficulty, best_score, best_steps | Unique constraint on (challenge, user, difficulty) |
| `RateLimit` | API throttling | id, identifier, endpoint, request_count, window_start | Composite index for fast lookups |

### 1.2 Current Application Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                           FASTAPI APP                                │    │
│  │  main.py → Routers → Services → Repositories → Database             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ROUTES (app/routes/)                                                        │
│  ├── auth.py         → /auth/*        (login, register, token)              │
│  ├── challenges.py   → /challenges/*  (list, detail pages)                  │
│  ├── submissions.py  → /submit/*      (submit, stream results)              │
│  ├── leaderboard.py  → /leaderboard/* (rankings, progress)                  │
│  └── deps.py         → Dependencies   (get_current_user, etc.)              │
│                                                                              │
│  SERVICES (app/services/)                                                    │
│  ├── auth_service.py        → User registration, login, JWT                 │
│  ├── submission_service.py  → Create submissions, update leaderboard        │
│  ├── leaderboard_service.py → Query rankings by difficulty                  │
│  └── rate_limit_service.py  → Throttle API requests                         │
│                                                                              │
│  REPOSITORIES (app/repositories/)                                            │
│  ├── base.py           → Generic CRUD operations                            │
│  ├── user_repo.py      → User queries                                       │
│  ├── submission_repo.py → Submission queries                                │
│  └── leaderboard_repo.py → Leaderboard queries                              │
│                                                                              │
│  CHALLENGES (app/challenges/)                                                │
│  ├── base.py           → BaseChallenge abstract class + ChallengeRegistry   │
│  ├── firewall.py       → Filter bypass challenge (3 levels)                 │
│  ├── glitch.py         → Break the bot challenge (3 levels)                 │
│  ├── giga_chad.py      → Persuasion challenge (4 levels)                    │
│  ├── interrogation/    → Detective mystery (3 levels, package)              │
│  ├── debate_battle.py  → Debate challenge (2 levels)                        │
│  └── arena.py          → Combat challenge (2 levels)                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Current Frontend Architecture

```
TEMPLATES (app/templates/)
├── base.html                    → Base layout (nav, footer, auth JS)
├── index.html                   → Homepage
├── challenges.html              → Challenge list
├── challenges/
│   ├── firewall.html            → Challenge-specific UIs
│   ├── glitch.html
│   ├── giga_chad.html
│   ├── interrogation.html
│   ├── debate.html
│   └── arena.html
├── leaderboard_home.html        → Leaderboard list
├── leaderboard_detail.html      → Per-challenge leaderboard
├── login.html                   → Login form
└── register.html                → Registration form

STATIC (app/static/)
├── css/style.css                → Global styles
└── js/
    ├── main.js                  → Common utilities
    ├── fingerprint.js           → User fingerprinting
    └── challenge_handler.js     → Shared challenge logic
```

### 1.4 Key Architectural Patterns

| Pattern | Implementation | Notes |
|---------|----------------|-------|
| **Repository Pattern** | `BaseRepository` with CRUD | Generic typed repository |
| **Service Layer** | Business logic separated | Services use repositories |
| **Challenge Registry** | `@ChallengeRegistry.register` decorator | Auto-discovery of challenges |
| **SSE Streaming** | `stream_events()` generator | Real-time challenge updates |
| **JWT Auth** | Bearer tokens in localStorage | 7-day expiry |
| **Template Inheritance** | Jinja2 `{% extends "base.html" %}` | Consistent layout |

---

## 2. LMS Data Model Design

### 2.1 New Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NEW LMS DATABASE SCHEMA                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │    courses       │  NEW - Top-level course container                      │
│  ├──────────────────┤                                                        │
│  │ id (PK)          │                                                        │
│  │ slug             │  "prompt-engineering-fundamentals"                     │
│  │ title            │  "Prompt Engineering Fundamentals"                     │
│  │ description      │  Course overview text                                  │
│  │ thumbnail_url    │  Course image                                          │
│  │ is_published     │  Draft vs published                                    │
│  │ order            │  Display order                                         │
│  │ created_at       │                                                        │
│  │ updated_at       │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           │ 1:N                                                              │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │    modules       │  NEW - Groups of related lessons                       │
│  ├──────────────────┤                                                        │
│  │ id (PK)          │                                                        │
│  │ course_id (FK)   │──► courses.id                                          │
│  │ slug             │  "basics"                                              │
│  │ title            │  "Module 1: The Basics"                                │
│  │ description      │  Module overview                                       │
│  │ order            │  Order within course                                   │
│  │ unlock_after_id  │  FK to previous module (nullable)                      │
│  │ created_at       │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           │ 1:N                                                              │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │    lessons       │  NEW - Individual learning units                       │
│  ├──────────────────┤                                                        │
│  │ id (PK)          │                                                        │
│  │ module_id (FK)   │──► modules.id                                          │
│  │ slug             │  "being-specific"                                      │
│  │ title            │  "Lesson 1.2: Being Specific"                          │
│  │ content_md       │  Markdown content (concept explanation)                │
│  │ example_bad      │  Bad prompt example                                    │
│  │ example_good     │  Good prompt example                                   │
│  │ challenge_id     │  FK to existing challenge (nullable)                   │
│  │ challenge_config │  JSON config for challenge (difficulty, etc.)          │
│  │ order            │  Order within module                                   │
│  │ xp_reward        │  XP earned on completion                               │
│  │ estimated_mins   │  Estimated time to complete                            │
│  │ created_at       │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           │ 1:N                                                              │
│           ▼                                                                  │
│  ┌──────────────────┐                                                        │
│  │  lesson_quizzes  │  NEW - Quiz questions per lesson                       │
│  ├──────────────────┤                                                        │
│  │ id (PK)          │                                                        │
│  │ lesson_id (FK)   │──► lessons.id                                          │
│  │ question         │  Question text                                         │
│  │ options (JSON)   │  ["A", "B", "C", "D"]                                   │
│  │ correct_index    │  Index of correct answer                               │
│  │ explanation      │  Why this answer is correct                            │
│  │ order            │  Order within quiz                                     │
│  └──────────────────┘                                                        │
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │ user_progress    │  NEW - Track completion per user                       │
│  ├──────────────────┤                                                        │
│  │ id (PK)          │                                                        │
│  │ user_id (FK)     │──► users.id                                            │
│  │ lesson_id (FK)   │──► lessons.id                                          │
│  │ status           │  'not_started', 'in_progress', 'completed'             │
│  │ challenge_score  │  Best score on lesson challenge                        │
│  │ quiz_score       │  Quiz score (correct / total)                          │
│  │ attempts         │  Number of attempts                                    │
│  │ started_at       │                                                        │
│  │ completed_at     │                                                        │
│  │ UNIQUE(user_id, lesson_id)                                                │
│  └──────────────────┘                                                        │
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │ user_xp          │  NEW - Gamification XP tracking                        │
│  ├──────────────────┤                                                        │
│  │ id (PK)          │                                                        │
│  │ user_id (FK)     │──► users.id (UNIQUE)                                   │
│  │ total_xp         │  Cumulative XP                                         │
│  │ level            │  Computed level from XP                                │
│  │ updated_at       │                                                        │
│  └──────────────────┘                                                        │
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │ certificates     │  NEW - Completion certificates                         │
│  ├──────────────────┤                                                        │
│  │ id (PK)          │                                                        │
│  │ user_id (FK)     │──► users.id                                            │
│  │ course_id (FK)   │──► courses.id                                          │
│  │ certificate_uuid │  Unique verification code                              │
│  │ issued_at        │                                                        │
│  │ UNIQUE(user_id, course_id)                                                │
│  └──────────────────┘                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 New Models Summary

| Model | Purpose | Key Fields | Relationships |
|-------|---------|------------|---------------|
| `Course` | Course container | slug, title, description, is_published | Has many Modules |
| `Module` | Lesson grouping | course_id, title, order, unlock_after_id | Belongs to Course, has many Lessons |
| `Lesson` | Learning unit | module_id, content_md, challenge_id, xp_reward | Belongs to Module, has Quiz |
| `LessonQuiz` | Quiz questions | lesson_id, question, options, correct_index | Belongs to Lesson |
| `UserProgress` | Completion tracking | user_id, lesson_id, status, scores | Links User to Lesson |
| `UserXP` | Gamification | user_id, total_xp, level | One per User |
| `Certificate` | Completion proof | user_id, course_id, certificate_uuid | Links User to Course |

### 2.3 User Model Extension

```python
# Extend existing User model
class User(Base):
    # ... existing fields ...
    
    # NEW relationships
    progress = relationship("UserProgress", back_populates="user")
    xp = relationship("UserXP", back_populates="user", uselist=False)
    certificates = relationship("Certificate", back_populates="user")
    
    # NEW optional fields for corporate
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    role = Column(String(20), default="learner")  # learner, instructor, admin
```

---

## 3. API Design

### 3.1 New Route Structure

```
/api/v1/
├── /auth/*                    (existing)
├── /challenges/*              (existing)
├── /submissions/*             (existing)
├── /leaderboard/*             (existing)
│
├── /courses/                  NEW
│   ├── GET    /               List all published courses
│   ├── GET    /{slug}         Get course with modules
│   └── GET    /{slug}/progress Get user's progress in course
│
├── /modules/                  NEW
│   └── GET    /{id}           Get module with lessons
│
├── /lessons/                  NEW
│   ├── GET    /{id}           Get lesson content
│   ├── POST   /{id}/start     Mark lesson as started
│   ├── POST   /{id}/complete  Mark lesson as completed
│   └── POST   /{id}/quiz      Submit quiz answers
│
├── /progress/                 NEW
│   ├── GET    /               Get all user progress
│   ├── GET    /stats          Get user statistics (XP, level, etc.)
│   └── GET    /certificates   Get user's certificates
│
└── /admin/                    NEW (instructor/admin only)
    ├── /courses/              CRUD for courses
    ├── /modules/              CRUD for modules
    ├── /lessons/              CRUD for lessons
    └── /analytics/            Usage analytics
```

### 3.2 Key API Endpoints

```python
# Course endpoints
@router.get("/courses")
async def list_courses() -> List[CourseListResponse]:
    """List all published courses with progress indicators"""

@router.get("/courses/{slug}")
async def get_course(slug: str) -> CourseDetailResponse:
    """Get course with all modules and lessons (tree structure)"""

@router.get("/courses/{slug}/progress")
async def get_course_progress(slug: str, user: User) -> CourseProgressResponse:
    """Get user's progress in a specific course"""

# Lesson endpoints
@router.get("/lessons/{id}")
async def get_lesson(id: int) -> LessonDetailResponse:
    """Get lesson content, examples, and challenge config"""

@router.post("/lessons/{id}/start")
async def start_lesson(id: int, user: User) -> UserProgress:
    """Mark lesson as started (creates progress record)"""

@router.post("/lessons/{id}/complete")
async def complete_lesson(
    id: int, 
    user: User, 
    challenge_score: int = None
) -> LessonCompletionResponse:
    """Mark lesson complete, award XP, check module unlock"""

@router.post("/lessons/{id}/quiz")
async def submit_quiz(
    id: int, 
    user: User, 
    answers: List[int]
) -> QuizResultResponse:
    """Submit quiz answers, return score and explanations"""
```

### 3.3 Response Schemas

```python
class CourseListResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    thumbnail_url: Optional[str]
    module_count: int
    lesson_count: int
    estimated_hours: float
    progress_percent: Optional[float]  # If user is logged in

class CourseDetailResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    modules: List[ModuleResponse]

class ModuleResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    order: int
    is_unlocked: bool
    lessons: List[LessonSummaryResponse]

class LessonSummaryResponse(BaseModel):
    id: int
    slug: str
    title: str
    order: int
    xp_reward: int
    estimated_mins: int
    status: str  # not_started, in_progress, completed
    has_challenge: bool
    has_quiz: bool

class LessonDetailResponse(BaseModel):
    id: int
    title: str
    content_md: str
    example_bad: Optional[str]
    example_good: Optional[str]
    challenge_config: Optional[dict]
    quiz: Optional[List[QuizQuestionResponse]]
    xp_reward: int
    
class LessonCompletionResponse(BaseModel):
    success: bool
    xp_earned: int
    new_total_xp: int
    new_level: Optional[int]  # If leveled up
    next_lesson: Optional[LessonSummaryResponse]
    module_completed: bool
    course_completed: bool
    certificate_id: Optional[str]  # If course completed
```

---

## 4. Frontend Design

### 4.1 New Page Structure

```
/learn/                           Course catalog
/learn/{course-slug}/             Course overview
/learn/{course-slug}/{module}/    Module view
/learn/{course-slug}/{module}/{lesson}  Lesson view

/profile/                         User dashboard
/profile/progress/                Detailed progress
/profile/certificates/            Certificate gallery

/admin/                           Admin dashboard (instructors)
/admin/courses/                   Course management
/admin/courses/{id}/edit          Course editor
/admin/analytics/                 Usage analytics
```

### 4.2 New Templates

```
app/templates/
├── learn/
│   ├── catalog.html              Course catalog grid
│   ├── course.html               Course overview + module list
│   ├── module.html               Module overview + lesson list
│   └── lesson.html               Lesson viewer (content + challenge)
├── profile/
│   ├── dashboard.html            User stats, recent activity
│   ├── progress.html             Detailed progress by course
│   └── certificates.html         Certificate gallery
└── admin/
    ├── dashboard.html            Admin overview
    ├── course_list.html          Course management
    ├── course_edit.html          Course/module/lesson editor
    └── analytics.html            Usage charts
```

### 4.3 Lesson Viewer Component

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LESSON VIEWER UI                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Module 1: Basics  ▸  Lesson 2: Being Specific          [◀ Prev] [Next ▶]│
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │         📖 CONCEPT               │  │        🎮 PRACTICE                │ │
│  │  ─────────────────────────────   │  │  ─────────────────────────────   │ │
│  │                                  │  │                                  │ │
│  │  # Being Specific                │  │  [Challenge Interface]           │ │
│  │                                  │  │                                  │ │
│  │  Vague prompts produce vague     │  │  Your task: Get the AI to        │ │
│  │  results. The key to good...     │  │  output exactly this format:     │ │
│  │                                  │  │                                  │ │
│  │  ## Bad Example                  │  │  ┌────────────────────────────┐  │ │
│  │  ```                             │  │  │ Enter your prompt...       │  │ │
│  │  Write about dogs                │  │  └────────────────────────────┘  │ │
│  │  ```                             │  │                                  │ │
│  │                                  │  │  [Submit] [Hint]                 │ │
│  │  ## Good Example                 │  │                                  │ │
│  │  ```                             │  │  Score: 0/100                    │ │
│  │  Write a 100-word paragraph...   │  │  Attempts: 0                     │ │
│  │  ```                             │  │                                  │ │
│  │                                  │  │                                  │ │
│  └──────────────────────────────────┘  └──────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  📝 QUIZ (Complete challenge first)                      [Start Quiz]│    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Progress: [████████░░] 80%                    XP: +50 on completion │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Implementation Phases

### Phase 1: Database & Models (2-3 days)

**Tasks:**
1. Create Alembic migration for new tables
2. Implement new SQLAlchemy models
3. Create repositories for new models
4. Write unit tests for models

**Files to create:**
```
app/models/course.py
app/models/module.py
app/models/lesson.py
app/models/lesson_quiz.py
app/models/user_progress.py
app/models/user_xp.py
app/models/certificate.py
app/repositories/course_repo.py
app/repositories/lesson_repo.py
app/repositories/progress_repo.py
migrations/versions/xxx_add_lms_tables.py
```

**Acceptance Criteria:**
- [ ] All models created with proper relationships
- [ ] Migration runs successfully on dev database
- [ ] Repository CRUD operations work
- [ ] Unit tests pass

---

### Phase 2: Core Services (2-3 days)

**Tasks:**
1. Create CourseService (list, get, progress calculation)
2. Create LessonService (get content, mark complete)
3. Create ProgressService (XP tracking, level calculation)
4. Create QuizService (submit, score, explanations)
5. Integration with existing challenge system

**Files to create:**
```
app/services/course_service.py
app/services/lesson_service.py
app/services/progress_service.py
app/services/quiz_service.py
app/schemas/course.py
app/schemas/lesson.py
app/schemas/progress.py
```

**Acceptance Criteria:**
- [ ] Services handle all business logic
- [ ] XP/level calculation works correctly
- [ ] Challenge completion updates lesson progress
- [ ] Quiz scoring is accurate

---

### Phase 3: API Routes (2-3 days)

**Tasks:**
1. Create course routes (list, detail, progress)
2. Create lesson routes (get, start, complete, quiz)
3. Create progress routes (stats, certificates)
4. Add authentication/authorization
5. API documentation (OpenAPI)

**Files to create:**
```
app/routes/courses.py
app/routes/lessons.py
app/routes/progress.py
```

**Acceptance Criteria:**
- [ ] All endpoints respond correctly
- [ ] Authentication required for progress mutations
- [ ] OpenAPI docs are complete
- [ ] Integration tests pass

---

### Phase 4: Frontend - Course Catalog (2-3 days)

**Tasks:**
1. Create course catalog page (grid of courses)
2. Create course detail page (modules/lessons tree)
3. Add progress indicators
4. Mobile responsive design

**Files to create:**
```
app/templates/learn/catalog.html
app/templates/learn/course.html
app/static/css/learn.css
app/static/js/learn.js
```

**Acceptance Criteria:**
- [ ] Course catalog displays all published courses
- [ ] Course detail shows module/lesson hierarchy
- [ ] Progress indicators work for logged-in users
- [ ] Responsive on mobile

---

### Phase 5: Frontend - Lesson Viewer (3-4 days)

**Tasks:**
1. Create lesson viewer with content pane
2. Integrate existing challenge components
3. Create quiz UI component
4. Add completion flow (XP animation, next lesson)
5. Progress persistence

**Files to create:**
```
app/templates/learn/lesson.html
app/templates/components/quiz.html
app/static/js/lesson.js
app/static/js/quiz.js
```

**Acceptance Criteria:**
- [ ] Markdown content renders correctly
- [ ] Challenge integration works seamlessly
- [ ] Quiz submits and shows results
- [ ] Completion awards XP and unlocks next lesson

---

### Phase 6: User Dashboard (2 days)

**Tasks:**
1. Create user dashboard with stats
2. Create progress view by course
3. Create certificate gallery
4. Add XP/level display in navbar

**Files to create:**
```
app/templates/profile/dashboard.html
app/templates/profile/progress.html
app/templates/profile/certificates.html
```

**Acceptance Criteria:**
- [ ] Dashboard shows key stats
- [ ] Progress view shows completion by course
- [ ] Certificates display with verification links

---

### Phase 7: Admin Panel (3-4 days)

**Tasks:**
1. Create admin dashboard
2. Create course/module/lesson CRUD
3. Create content editor (Markdown preview)
4. Add analytics (basic usage charts)

**Files to create:**
```
app/templates/admin/dashboard.html
app/templates/admin/course_list.html
app/templates/admin/course_edit.html
app/templates/admin/analytics.html
app/routes/admin.py
app/services/admin_service.py
```

**Acceptance Criteria:**
- [ ] Admins can create/edit/delete courses
- [ ] Content editor has live preview
- [ ] Basic analytics display

---

### Phase 8: Content Creation (Ongoing)

**Tasks:**
1. Write Module 1: Basics (4 lessons)
2. Write Module 2: Output Control (4 lessons)
3. Write Module 3: Multi-Turn (4 lessons)
4. Write Module 4: Advanced (4 lessons)
5. Create quizzes for each lesson
6. Map existing challenges to lessons

**Deliverables:**
- 16 lessons with content
- 48+ quiz questions
- Challenge configurations per lesson

---

## 6. Technical Considerations

### 6.1 Database Migrations

```python
# migrations/versions/xxx_add_lms_tables.py

def upgrade():
    # Create courses table
    op.create_table('courses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('thumbnail_url', sa.String(500)),
        sa.Column('is_published', sa.Boolean(), default=False),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), onupdate=datetime.utcnow),
    )
    
    # Create modules table
    op.create_table('modules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id')),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('order', sa.Integer(), default=0),
        sa.Column('unlock_after_id', sa.Integer(), sa.ForeignKey('modules.id')),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
    )
    
    # ... continue for other tables
```

### 6.2 Challenge Integration

The existing challenge system can be reused by storing challenge configuration in lessons:

```python
class Lesson(Base):
    # ...
    challenge_id = Column(String(50))  # e.g., "firewall", "glitch"
    challenge_config = Column(JSON)    # e.g., {"difficulty": "LEVEL_1"}
```

When a lesson is loaded, the challenge is instantiated:

```python
def get_lesson_challenge(lesson: Lesson):
    if not lesson.challenge_id:
        return None
    
    config = lesson.challenge_config or {}
    return ChallengeRegistry.get_challenge(lesson.challenge_id, config)
```

### 6.3 XP & Leveling System

```python
# XP rewards
LESSON_COMPLETE_XP = 50
QUIZ_PERFECT_BONUS = 25
MODULE_COMPLETE_BONUS = 100
COURSE_COMPLETE_BONUS = 500

# Level thresholds (exponential)
def get_level(total_xp: int) -> int:
    """Calculate level from total XP"""
    # Level 1: 0 XP
    # Level 2: 100 XP
    # Level 3: 300 XP
    # Level 4: 600 XP
    # Level 5: 1000 XP
    # ...
    level = 1
    threshold = 100
    remaining = total_xp
    
    while remaining >= threshold:
        remaining -= threshold
        level += 1
        threshold = int(threshold * 1.5)
    
    return level
```

### 6.4 Authentication & Authorization

```python
# Role-based access
class UserRole(str, Enum):
    LEARNER = "learner"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"

def require_role(allowed_roles: List[UserRole]):
    """Dependency to require specific roles"""
    async def check_role(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check_role

# Usage
@router.post("/admin/courses")
async def create_course(
    data: CourseCreate,
    user: User = Depends(require_role([UserRole.ADMIN]))
):
    ...
```

---

## 7. Estimated Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Database & Models | 2-3 days | None |
| Phase 2: Core Services | 2-3 days | Phase 1 |
| Phase 3: API Routes | 2-3 days | Phase 2 |
| Phase 4: Course Catalog UI | 2-3 days | Phase 3 |
| Phase 5: Lesson Viewer UI | 3-4 days | Phase 4 |
| Phase 6: User Dashboard | 2 days | Phase 5 |
| Phase 7: Admin Panel | 3-4 days | Phase 5 |
| Phase 8: Content Creation | Ongoing | Phase 7 |

**Total estimated time: 16-22 days** (3-4 weeks)

---

## 8. Future Considerations

### 8.1 Corporate Features (Phase 2)
- Organization/team management
- Seat licenses
- SSO integration (SAML, OIDC)
- Custom branding
- Private courses
- Team analytics

### 8.2 Advanced Features (Phase 3)
- AI-powered hint system
- Adaptive difficulty
- Peer review/collaboration
- Discussion forums
- Mobile app
- Offline mode

### 8.3 Monetization
- Free tier (limited courses)
- Pro tier ($X/month)
- Team tier ($X/seat/month)
- Enterprise (custom pricing)

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Challenge integration complexity | Medium | High | Start with simple challenges, iterate |
| Content creation bottleneck | High | High | Create content templates, consider AI assistance |
| Performance with many users | Low | Medium | Add caching, optimize queries |
| Mobile responsiveness | Medium | Medium | Use responsive framework, test early |
| Admin panel scope creep | High | Medium | MVP first, add features incrementally |

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Course completion rate | >40% | % users who finish a started course |
| Lesson completion rate | >70% | % users who complete started lessons |
| Quiz pass rate | >80% | % quizzes passed on first attempt |
| User retention (7-day) | >30% | % users returning within 7 days |
| NPS score | >40 | User satisfaction survey |

---

## Appendix A: File Structure

```
app/
├── models/
│   ├── __init__.py          # Export all models
│   ├── user.py              # (existing)
│   ├── submission.py        # (existing)
│   ├── leaderboard.py       # (existing)
│   ├── course.py            # NEW
│   ├── module.py            # NEW
│   ├── lesson.py            # NEW
│   ├── lesson_quiz.py       # NEW
│   ├── user_progress.py     # NEW
│   ├── user_xp.py           # NEW
│   └── certificate.py       # NEW
│
├── repositories/
│   ├── course_repo.py       # NEW
│   ├── module_repo.py       # NEW
│   ├── lesson_repo.py       # NEW
│   └── progress_repo.py     # NEW
│
├── services/
│   ├── course_service.py    # NEW
│   ├── lesson_service.py    # NEW
│   ├── progress_service.py  # NEW
│   └── quiz_service.py      # NEW
│
├── routes/
│   ├── courses.py           # NEW
│   ├── lessons.py           # NEW
│   ├── progress.py          # NEW
│   └── admin.py             # NEW
│
├── schemas/
│   ├── course.py            # NEW
│   ├── lesson.py            # NEW
│   └── progress.py          # NEW
│
└── templates/
    ├── learn/
    │   ├── catalog.html     # NEW
    │   ├── course.html      # NEW
    │   └── lesson.html      # NEW
    ├── profile/
    │   ├── dashboard.html   # NEW
    │   └── certificates.html # NEW
    └── admin/
        ├── dashboard.html   # NEW
        └── course_edit.html # NEW
```

---

## Appendix B: Sample Curriculum

### Course: Prompt Engineering Fundamentals

**Module 1: The Basics**
- Lesson 1.1: What is Prompt Engineering?
- Lesson 1.2: Being Specific (Challenge: Format Enforcer)
- Lesson 1.3: Providing Context
- Lesson 1.4: Role Assignment (Challenge: Glitch L1)

**Module 2: Output Control**
- Lesson 2.1: Structured Output (JSON, Tables)
- Lesson 2.2: Length Control
- Lesson 2.3: Style and Tone
- Lesson 2.4: Format Templates (Challenge: Template Builder)

**Module 3: Multi-Turn Conversations**
- Lesson 3.1: Conversation Memory
- Lesson 3.2: Iterative Refinement
- Lesson 3.3: Error Recovery
- Lesson 3.4: Context Management (Challenge: Memory Test)

**Module 4: Advanced Techniques**
- Lesson 4.1: Chain-of-Thought Prompting
- Lesson 4.2: Few-Shot Learning
- Lesson 4.3: System Prompt Design
- Lesson 4.4: Red-Teaming (Challenge: Firewall L1-L3)
