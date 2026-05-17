# Database Schema: Jira Team Performance Analytics

**Status:** Implementation Ready  
**Database:** MySQL 8.0+  
**ORM:** SQLAlchemy 2.0  
**Migrations:** Alembic  

---

## Core Tables

### Users
```sql
CREATE TABLE users (
  id VARCHAR(36) PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  jira_user_id VARCHAR(255) NOT NULL UNIQUE,
  role ENUM('member', 'manager', 'admin') DEFAULT 'member',
  team_id VARCHAR(36),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_email (email),
  FOREIGN KEY (team_id) REFERENCES teams(id)
);
```

### Teams
```sql
CREATE TABLE teams (
  id VARCHAR(36) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  jira_project_key VARCHAR(10) NOT NULL UNIQUE,
  manager_id VARCHAR(36) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_manager_id (manager_id),
  FOREIGN KEY (manager_id) REFERENCES users(id)
);
```

### Credentials (Encrypted)
```sql
CREATE TABLE credentials (
  id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL UNIQUE,
  jira_instance_url VARCHAR(255) NOT NULL,
  jira_token_encrypted VARCHAR(1024) NOT NULL,
  token_expires_at TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### Tickets
```sql
CREATE TABLE tickets (
  id VARCHAR(36) PRIMARY KEY,
  team_id VARCHAR(36) NOT NULL,
  jira_key VARCHAR(20) NOT NULL UNIQUE,
  title VARCHAR(500) NOT NULL,
  assignee_id VARCHAR(36),
  status VARCHAR(50) NOT NULL,
  created_at DATETIME NOT NULL,
  resolved_at DATETIME,
  cycle_time_days DECIMAL(5, 2),
  bounced_count INT DEFAULT 0,
  last_synced DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_team_status (team_id, status),
  INDEX idx_assignee (assignee_id),
  INDEX idx_created (created_at),
  
  FOREIGN KEY (team_id) REFERENCES teams(id),
  FOREIGN KEY (assignee_id) REFERENCES users(id)
);
```

### TicketTransitions (Audit)
```sql
CREATE TABLE ticket_transitions (
  id VARCHAR(36) PRIMARY KEY,
  ticket_id VARCHAR(36) NOT NULL,
  from_status VARCHAR(50),
  to_status VARCHAR(50) NOT NULL,
  transitioned_at DATETIME NOT NULL,
  actor_id VARCHAR(36),
  
  INDEX idx_ticket (ticket_id),
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  FOREIGN KEY (actor_id) REFERENCES users(id)
);
```

### Metrics (Pre-calculated)
```sql
CREATE TABLE metrics (
  id VARCHAR(36) PRIMARY KEY,
  team_id VARCHAR(36) NOT NULL,
  date DATE NOT NULL,
  avg_cycle_time_days DECIMAL(5, 2),
  bounce_rate DECIMAL(5, 2),
  open_tickets INT,
  bottleneck_status VARCHAR(50),
  calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE KEY uk_team_date (team_id, date),
  FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
);
```

---

## Key Design Decisions

| Table | Strategy | Rationale |
|-------|----------|-----------|
| **Credentials** | Encrypted + indexed by user | Security: tokens never logged |
| **Tickets** | Denormalized (assignee cached) | Performance: avoid joins |
| **Metrics** | Pre-calculated daily | Speed: 4 KPIs load in <100ms |
| **Transitions** | Audit log (immutable) | Compliance: bounces tracked |

---

## Query Optimization

### Critical Indexes
```sql
-- Dashboard metrics
CREATE INDEX idx_team_resolved ON tickets(team_id, resolved_at);

-- Developer drill-down
CREATE INDEX idx_assignee_status ON tickets(assignee_id, status);

-- Bounce detection
CREATE INDEX idx_bounce_detection ON ticket_transitions(
  ticket_id, from_status, to_status
);
```

### Sample Queries

**Get Team Metrics:**
```sql
SELECT
  AVG(cycle_time_days) as avg_cycle,
  SUM(bounced_count) as bounces,
  COUNT(*) as completed
FROM tickets
WHERE team_id = 'team123'
  AND resolved_at >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

**Developer Stats:**
```sql
SELECT
  assignee_id,
  COUNT(*) as completed,
  AVG(cycle_time_days) as avg_cycle,
  SUM(bounced_count) as bounces
FROM tickets
WHERE team_id = 'team123'
GROUP BY assignee_id;
```

---

## Implementation Checklist

- [ ] Create all 6 tables
- [ ] Create indexes (team_status, assignee, created_at)
- [ ] Set up Alembic migrations
- [ ] Configure SQLAlchemy connection pooling
- [ ] Test queries with EXPLAIN ANALYZE
- [ ] Set up replication for HA
- [ ] Configure daily backups
- [ ] Load test with sample data (1M tickets)

---

**See also:** ARCHITECTURE.md, BACKEND-API.md, CELERY-ARCHITECTURE.md
