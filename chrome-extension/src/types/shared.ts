export interface Comment {
  id: number;
  youtube_comment_id: string;
  author_name: string;
  text: string;
  is_question: boolean;
  is_answered: boolean;
}

export interface Cluster {
  id: number;
  session_id: number;
  title: string;
  description?: string;
  similarity_threshold: number;
}

export interface Answer {
  id: number;
  cluster_id: number;
  comment_id?: number;
  text: string;
  is_posted: boolean;
}

export interface StreamingSession {
  id: number;
  teacher_id: number;
  youtube_video_id: string;
  title?: string;
  is_active: boolean;
}

