-- Pull requests metadata
CREATE TABLE IF NOT EXISTS pull_requests (
  id SERIAL PRIMARY KEY,
  pr_number INT NOT NULL,
  repo_full_name VARCHAR(255) NOT NULL,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(repo_full_name, pr_number)
);

-- Review comments posted
CREATE TABLE IF NOT EXISTS reviews (
  id SERIAL PRIMARY KEY,
  pr_id INT REFERENCES pull_requests(id) ON DELETE CASCADE,
  file_path VARCHAR(500),
  line_number INT,
  comment_text TEXT,
  posted_at TIMESTAMP DEFAULT NOW()
);

-- Track feedback acceptance (optional, for learning)
CREATE TABLE IF NOT EXISTS review_feedback (
  id SERIAL PRIMARY KEY,
  review_id INT REFERENCES reviews(id) ON DELETE CASCADE,
  feedback_type VARCHAR(50),  -- accepted, ignored, helpful, unhelpful
  recorded_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pull_requests_repo_pr ON pull_requests(repo_full_name, pr_number);
CREATE INDEX IF NOT EXISTS idx_pull_requests_status ON pull_requests(status);
CREATE INDEX IF NOT EXISTS idx_reviews_pr_id ON reviews(pr_id);
CREATE INDEX IF NOT EXISTS idx_review_feedback_review_id ON review_feedback(review_id);

