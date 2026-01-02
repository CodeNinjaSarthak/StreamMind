export const QUOTA_TYPES = {
  POLL: 'poll',
  POST: 'post',
  EMBEDDING: 'embedding',
  ANSWER_GENERATION: 'answer_generation',
} as const;

export const QUOTA_LIMITS = {
  POLL_PER_HOUR: 1000,
  POST_PER_HOUR: 100,
  EMBEDDING_PER_DAY: 10000,
  ANSWER_GENERATION_PER_DAY: 500,
} as const;

export const QUOTA_COSTS = {
  POLL: 1,
  POST: 10,
  EMBEDDING: 1,
  ANSWER_GENERATION: 5,
} as const;

